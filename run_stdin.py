"""Minimal runner: read hex-encoded blocks from stdin, one per line.

Zero extra dependencies beyond py-bitcoinkernel and the Python standard library.
Paste a hex string, hit enter, see the result. Empty lines and lines starting
with '#' are ignored. Ctrl+C or Ctrl+D to exit.

Usage:
    uv run python run_stdin.py
"""

from __future__ import annotations

import asyncio
import json
import sys

from node import handle_block


PROMPT = "» "


def _emit_prompt() -> None:
    if sys.stdin.isatty():
        sys.stderr.write(PROMPT)
        sys.stderr.flush()


def main() -> None:
    print("Paste hex-encoded blocks (one per line). Ctrl+D / Ctrl+C to exit.\n", file=sys.stderr)
    try:
        _emit_prompt()
        for line in sys.stdin:
            hex_data = line.strip()
            if not hex_data or hex_data.startswith("#"):
                _emit_prompt()
                continue
            result = asyncio.run(handle_block(hex_data))
            print(json.dumps(result))
            _emit_prompt()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
