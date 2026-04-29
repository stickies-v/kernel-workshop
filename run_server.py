"""Full runner: serves the phone scanner page and receives blocks over WebSocket.

Requires the `full` extra (websockets + qrcode for the terminal QR).

Usage:
    uv sync --extra full
    uv run python run_server.py
"""

import server
from node import handle_block


if __name__ == "__main__":
    server.run(handle_block)
