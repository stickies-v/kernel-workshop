"""HTTPS + WSS server plumbing.

You don't need to read this file — it's the boring networking layer that lets your
phone talk to your laptop. All you care about is the `run()` function: pass it a
callback, and it will call your callback with each block hex string it receives from
the phone. Your callback returns a dict describing what happened, which the server
sends back to the phone.

Single-port design: both the scanner HTML page and the WebSocket connection share
the same port, so phones only need to accept the self-signed TLS certificate once.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import socket
import ssl
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path

import qrcode
import websockets
from websockets.http11 import Response
from websockets.datastructures import Headers


# Cert dir defaults to the workshop directory but can be overridden via
# PBK_CERT_DIR — useful when /workshop is bind-mounted read-only inside Docker.
CERT_DIR = Path(os.environ.get("PBK_CERT_DIR", Path(__file__).parent / ".certs"))
INDEX_HTML = Path(__file__).parent / "index.html"

log = logging.getLogger("pbk-node")

# Private IP ranges the laptop's interface is likely to land in. Including all of them
# in the cert's SANs means the cert stays valid across WiFi/hotspot/tethering changes.
COMMON_PRIVATE_RANGES = [
    "10.0.0.1", "192.168.0.1", "192.168.1.1", "172.16.0.1", "172.17.0.1",
]

BlockHandler = Callable[[str], Awaitable[dict]]


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    finally:
        s.close()


# Common VPN tunnel interface name prefixes by platform. If we find one with an
# assigned IP, the user's machine is likely behind a VPN — which typically
# blocks incoming LAN traffic and prevents the phone from reaching the server.
_VPN_IFACE_PREFIXES = ("utun", "tun", "tap", "wg", "ppp", "ipsec")


def _detect_vpn_interfaces() -> list[str]:
    """Return names of interfaces that look like active VPN tunnels."""
    try:
        # ifconfig is on macOS, BSD, and most Linux distros (net-tools).
        out = subprocess.run(
            ["ifconfig"], capture_output=True, text=True, check=False
        ).stdout
    except FileNotFoundError:
        return []
    found: list[str] = []
    current: str | None = None
    has_ip = False
    for line in out.splitlines():
        if line and not line[0].isspace():
            if current and has_ip:
                found.append(current)
            current = line.split(":", 1)[0].split()[0]
            has_ip = False
        elif current and " inet " in line:
            has_ip = True
    if current and has_ip:
        found.append(current)
    return [n for n in found if n.startswith(_VPN_IFACE_PREFIXES)]


def _cert_covers_ip(cert_path: Path, ip: str) -> bool:
    """Return True if `ip` appears in the cert's subjectAltName list."""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout", "-text"],
            capture_output=True,
            text=True,
            check=True,
        )
        return f"IP Address:{ip}" in result.stdout
    except subprocess.CalledProcessError:
        return False


def _is_ip(s: str) -> bool:
    """True if `s` is an IPv4 address literal."""
    parts = s.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _ensure_cert(extra_ip: str | None = None) -> tuple[Path, Path]:
    """Create or refresh the self-signed cert so it covers the current local IP.

    If `extra_ip` is given (and is an IPv4 literal) it's included in the SANs too —
    useful when running behind Docker's NAT, where the advertised host differs
    from the container's own IP.
    """
    CERT_DIR.mkdir(exist_ok=True)
    cert = CERT_DIR / "cert.pem"
    key = CERT_DIR / "key.pem"
    current_ip = _get_local_ip()
    need_ips = {current_ip}
    if extra_ip and _is_ip(extra_ip):
        need_ips.add(extra_ip)

    if cert.exists() and key.exists() and all(_cert_covers_ip(cert, ip) for ip in need_ips):
        log.debug("Using existing cert at %s (covers %s)", cert, ", ".join(sorted(need_ips)))
        return cert, key

    sans = {*need_ips, "127.0.0.1", *COMMON_PRIVATE_RANGES}
    san_arg = ",".join(f"IP:{ip}" for ip in sorted(sans))

    log.info("Generating self-signed cert for %s", ", ".join(sorted(need_ips)))
    log.debug("Cert SANs: %s", san_arg)
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key), "-out", str(cert),
            "-days", "30", "-nodes",
            "-subj", "/CN=pbk-node",
            "-addext", f"subjectAltName={san_arg}",
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


def _make_ssl_context(extra_ip: str | None = None) -> ssl.SSLContext:
    cert, key = _ensure_cert(extra_ip=extra_ip)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    return ctx


def _serve_static(path: str) -> Response:
    if path == "/":
        body = INDEX_HTML.read_bytes()
        headers = Headers([("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return Response(200, "OK", headers, body)
    log.debug("404 for path %s", path)
    headers = Headers([("Content-Length", "0")])
    return Response(404, "Not Found", headers, b"")


def _print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    qr.print_ascii(invert=True)


def _summarize(response: dict) -> str:
    if response.get("accepted"):
        return f"accepted (new={response.get('is_new')}, height={response.get('height')})"
    return f"rejected ({response.get('error', 'unknown')})"


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet the websockets library itself unless we're explicitly debugging.
    if not debug:
        logging.getLogger("websockets").setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal validating Bitcoin node — receives blocks over WebSocket from a phone scanner",
    )
    parser.add_argument("--host", default="0.0.0.0", help="interface to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="port to listen on (default: 8765)")
    parser.add_argument(
        "--advertise-host",
        default=os.environ.get("PBK_ADVERTISE_HOST"),
        help=(
            "IP/hostname printed in the QR code and used in the cert SANs. "
            "Defaults to auto-detected LAN IP. Set this (or PBK_ADVERTISE_HOST) "
            "when running in Docker so the phone reaches the host, not the container."
        ),
    )
    parser.add_argument("--debug", action="store_true", help="enable verbose debug logging")
    return parser.parse_args()


def run(
    handle_block: BlockHandler,
    host: str | None = None,
    port: int | None = None,
    debug: bool | None = None,
    advertise_host: str | None = None,
) -> None:
    """Start the node server.

    Serves both the scanner page and the WebSocket on a single HTTPS port. Phones
    navigate to https://<advertise-host>:<port>/ to scan QRs; the same page upgrades
    its connection to a WebSocket on the same port. For each scanned block, the
    server calls `handle_block(hex)` and sends the return value back as JSON.

    Configurable via CLI flags (`--host`, `--port`, `--advertise-host`, `--debug`)
    or by passing explicit arguments. Explicit arguments win over CLI flags.
    """
    args = _parse_args()
    bind_host = host if host is not None else args.host
    bind_port = port if port is not None else args.port
    debug_mode = debug if debug is not None else args.debug
    advertised = advertise_host if advertise_host is not None else args.advertise_host
    _configure_logging(debug_mode)
    # Resolve the advertised address once, up front — used by both the cert and the QR.
    printed_host = advertised or (_get_local_ip() if bind_host in ("0.0.0.0", "") else bind_host)
    ssl_ctx = _make_ssl_context(extra_ip=printed_host)

    async def _ws_handler(ws):
        peer = ws.remote_address[0] if ws.remote_address else "?"
        log.info("Phone connected (%s)", peer)
        try:
            async for message in ws:
                log.debug("Received %d chars from %s", len(message), peer)
                try:
                    response = await handle_block(message.strip())
                    if not isinstance(response, dict):
                        raise TypeError(
                            f"handle_block must return a dict, got {type(response).__name__}"
                        )
                except Exception as e:
                    log.exception("handle_block raised %s", type(e).__name__)
                    response = {"accepted": False, "error": f"{type(e).__name__}: {e}"}
                log.info("%s → %s", peer, _summarize(response))
                await ws.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed as e:
            log.debug("Connection closed (%s): %s", peer, e)
        log.info("Phone disconnected (%s)", peer)

    def _process_request(connection, request) -> Response | None:
        upgrade = request.headers.get("Upgrade", "").lower()
        if upgrade != "websocket":
            log.debug("HTTP %s %s", request.method if hasattr(request, "method") else "GET", request.path)
            return _serve_static(request.path)
        return None

    url = f"https://{printed_host}:{bind_port}/"
    _print_qr(url)
    print(f"\nScan the QR code above, or open this URL on your phone: {url}")
    print("Accept the self-signed certificate warning when prompted.\n")
    log.info("Listening on %s (bound to %s:%d)", url, bind_host, bind_port)
    log.debug("Debug logging enabled")
    vpn_ifaces = _detect_vpn_interfaces()
    if vpn_ifaces:
        log.warning(
            "VPN-like interface(s) active: %s — your phone may be unable to "
            "reach this server. Disable VPNs on both phone and laptop if you "
            "see connection failures.",
            ", ".join(vpn_ifaces),
        )

    async def _serve():
        async with websockets.serve(
            _ws_handler,
            bind_host,
            bind_port,
            ssl=ssl_ctx,
            process_request=_process_request,
        ):
            await asyncio.Future()

    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        log.info("Shutting down")
