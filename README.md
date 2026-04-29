# py-bitcoinkernel workshop

We're going to build a minimal Bitcoin node implementation using Bitcoin
Kernel and its [Python language bindings](https://github.com/stickies-v/py-bitcoinkernel).
By the end you'll have a small node that receives serialized blocks, hands
them to the Bitcoin Core consensus engine for validation, and reports
what happened — accepted, rejected (and why), reorged.

The workshop is organized so that everyone builds the same basic functionality to accept blocks,
but then participants can choose to implement various [side quests](#side-quests) based on interest
and available time.

## Choose how you want to run it

This workshop runs unfamiliar code on your machine. Depending on your environment
and risk profile, you should consider:

- **Isolation** — running inside a container restricts filesystem and
  process access to that container. Your home directory, SSH keys, and
  other processes are much harder to reach even if a dependency turns out to be
  malicious.
- **Dependency surface** — fewer pinned packages means fewer chances for a
  supply-chain compromise. The minimal setup pulls in `py-bitcoinkernel`
  only; the full setup adds `websockets` and `qrcode`.

You can also inspect all the pre-existing source code in this repository, or ask
your coding agent of choice to do it for you.

If you're not sure: if you already have Docker installed, try running it that way
first. If that does not work, you can consider falling back to running it directly
on your machine.

### Running locally

**Minimal** — installs only `py-bitcoinkernel`:

```sh
uv sync
uv run python run_stdin.py
```

Paste a hex-encoded block, hit enter, see the validation result. Empty lines
and lines starting with `#` are ignored.

**Full** — adds `websockets` and `qrcode`:

```sh
uv sync --extra full
uv run python run_server.py
```

Prints a QR code and a URL like `https://10.0.0.42:8765/`. Open it on your
phone, accept the self-signed cert, and point the camera at the block QR
codes. Requires `openssl` on your PATH (already present on macOS and most
Linux distros).

### Running in Docker

A small Python wrapper handles the build, the run, and (for full mode) LAN
IP detection. Works the same on macOS, Linux, and Windows:

```sh
python run_docker.py minimal     # interactive stdin in a container
python run_docker.py full        # phone-scanner server, auto-detected LAN IP
```

The image is built once and reused. The workshop directory is bind-mounted
read-only at `/workshop` inside the container, so editing `node.py` /
`index.html` on the host and restarting the container picks up your changes
without a rebuild. Pass `--rebuild` to force a refresh (e.g. after editing
`pyproject.toml`).

If your phone can't reach the auto-detected IP — for example, you have
multiple network interfaces and the wrong one was picked — override:

```sh
# macOS / Linux:
PBK_ADVERTISE_HOST=192.168.1.42 python run_docker.py full

# Windows PowerShell:
$env:PBK_ADVERTISE_HOST = "192.168.1.42"; python run_docker.py full
```

Why does the IP need to be set? Your phone reaches the host on its LAN
address (e.g. the one assigned by your phone's hotspot). That address isn't
visible from inside the Docker container, so the script reads it on the host
and passes it in.

A `.devcontainer/devcontainer.json` is included if you'd rather have VS Code
/ Cursor open the workshop inside the full container automatically. Set
`PBK_ADVERTISE_HOST` in your shell before opening it.

## The workshop

Open `node.py`. It holds your `chainman` and your `handle_block(hex_data)`
function. The runners (`run_stdin.py`, `run_server.py`) import from here —
you never touch the transport code.

Complete the TODOs so that when a block arrives:

1. Valid blocks that build on the current tip extend your chain
2. Invalid / malformed blocks are reported with a useful error
3. Out-of-order blocks are reported as missing their parent

To test on your own — independent of the QR card deck handed out at the
workshop — `data/blocks.txt` contains a self-paced sequence covering the
happy path, duplicates, out-of-order scans, all three invalid block types,
and a reorg. Each block is one hex line, preceded by a `# <hash>` comment
that the runner ignores. Pipe it into your node:

```sh
cat data/blocks.txt | uv run python run_stdin.py
```

## What you should see

- **Block accepted** — valid block, chain height increases
- **Block rejected** — the kernel tells you why: `MISSING_PREV`, `INVALID_HEADER`,
  `TIME_FUTURE`, `MUTATED`, ...
- **Duplicate** — `is_new=False`, chain unchanged

## Networking gotchas (full mode only)

Phone and laptop need to be able to reach each other. Ordered by reliability:

1. **USB tethering** — plug the phone into the laptop, enable "USB tethering"
   in the phone's hotspot settings. No WiFi config, no mobile data burn
2. **Phone hotspot over WiFi** — laptop joins the phone's hotspot
3. **Same WiFi network** — works unless the network has "AP isolation" (common
   on conference / hotel WiFi)

**Disable any VPN on both your phone and your laptop.** Most VPNs install
firewall rules that drop incoming non-VPN traffic, which silently prevents
the phone from reaching the server. The workshop server prints a warning
on startup if it detects a VPN-like interface on the host, but it can't
fix the routing for you.

macOS: the firewall may block incoming connections. If prompted, click "Allow".

If the cert warning won't go away (usually after switching networks): `rm -rf .certs/`
then restart. A fresh cert covering the new IP will be generated.

## CLI options (full mode)

```sh
uv run python run_server.py --help
uv run python run_server.py --port 9000
uv run python run_server.py --host 127.0.0.1             # only local connections
uv run python run_server.py --advertise-host 1.2.3.4     # URL/cert for phone
uv run python run_server.py --debug                      # verbose logging
```

## Side quests

Once the basics work, see [`quests.md`](quests.md) for optional add-ons that
exercise different parts of the kernel API:

1. Validation callbacks (the reorg quest)
2. Block tree visualization
3. OP_RETURN indexer
4. Coinbase auditor
5. Headers-first sync

## Files

- `node.py` — your validation logic (edit this)
- `data/blocks.txt` — a self-paced sequence of hex blocks for testing
- `run_stdin.py` — minimal runner, reads hex from stdin
- `run_server.py` — full runner, starts the phone-facing server
- `server.py` — HTTPS/WSS plumbing (you don't need to touch this)
- `index.html` — the phone scanner page
- `tree_view.py` — block-tree rendering helper used by the reference quest 3
- `TUTORIAL.md` — short tour of the parts of `pbk` you'll use
- `quests.md` — optional kernel-API exercises
- `Dockerfile` — two-stage build: `--target minimal` or `--target full`
- `docker-compose.yml` — convenience launcher for full mode
- `run_docker.py` — cross-platform Docker wrapper (minimal/full modes)
- `.devcontainer/` — VS Code / Cursor devcontainer pointing at the full target
