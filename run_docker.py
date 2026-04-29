#!/usr/bin/env python3
"""Build and run the workshop node in a Docker container.

Usage:
    python run_docker.py minimal     # interactive stdin runner
    python run_docker.py full        # phone-scanner server (auto-detects LAN IP)

The image is rebuilt only on first run; subsequent runs reuse it. Edit
node.py / index.html on the host and just restart the container — the
workshop directory is bind-mounted read-only at /workshop. Pass --rebuild
to force a refresh (e.g. after editing pyproject.toml).

Override the detected IP with the PBK_ADVERTISE_HOST env var if needed.

Cross-platform: works on macOS, Linux, and Windows. Requires Docker CLI on PATH.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys


MINIMAL_IMAGE = "pbk-workshop:minimal"


def detect_lan_ip() -> str | None:
    """Return the IP of the interface that would route to a public address.

    On a phone hotspot the active LAN interface is the one with the default
    route, so this picks the right address regardless of OS.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are sent — connect() on a UDP socket just sets the
        # destination and lets us read the chosen source via getsockname().
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
    if ip in ("0.0.0.0", "127.0.0.1"):
        return None
    return ip


def image_exists(name: str) -> bool:
    rc = subprocess.call(
        ["docker", "image", "inspect", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return rc == 0


def run(cmd: list[str], **kwargs) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, **kwargs)


def cmd_minimal(rebuild: bool) -> int:
    if rebuild or not image_exists(MINIMAL_IMAGE):
        rc = run(["docker", "build", "--target", "minimal", "-t", MINIMAL_IMAGE, "."])
        if rc != 0:
            return rc
    return run([
        "docker", "run", "--rm", "-it",
        "--mount", f"type=bind,source={os.getcwd()},target=/workshop,readonly",
        MINIMAL_IMAGE,
    ])


def cmd_full(rebuild: bool) -> int:
    advertise_host = os.environ.get("PBK_ADVERTISE_HOST")
    if not advertise_host:
        advertise_host = detect_lan_ip()
    if not advertise_host:
        print(
            "Could not auto-detect a LAN IP. Set PBK_ADVERTISE_HOST manually:\n"
            "    PBK_ADVERTISE_HOST=192.168.1.42 python run_docker.py full",
            file=sys.stderr,
        )
        return 1

    print(f"Using PBK_ADVERTISE_HOST={advertise_host}")
    print("  → if your phone can't reach this address, override:")
    print(f"    PBK_ADVERTISE_HOST=<your-LAN-IP> python run_docker.py full\n")

    env = os.environ.copy()
    env["PBK_ADVERTISE_HOST"] = advertise_host
    cmd = ["docker", "compose", "up"]
    if rebuild:
        cmd.append("--build")
    return subprocess.call(cmd, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("minimal", "full"))
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="force an image rebuild (default: rebuild only if image missing)",
    )
    args = parser.parse_args()
    try:
        return cmd_minimal(args.rebuild) if args.mode == "minimal" else cmd_full(args.rebuild)
    except KeyboardInterrupt:
        # Ctrl-C is propagated to the docker subprocess, which shuts the
        # container down gracefully. Don't dump a traceback over its output.
        return 130


if __name__ == "__main__":
    sys.exit(main())
