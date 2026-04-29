"""Validating Bitcoin node — receives hex-encoded blocks, validates with the kernel.

You implement two things in this file:

  1. `chainman` — a `pbk.ChainstateManager` instance.
  2. `handle_block(hex_data)` — async function returning a JSON-serializable
     dict. Runners (`run_stdin.py`, `run_server.py`) import these and feed
     blocks in via whichever transport they support.

See TUTORIAL.md for a tour of the relevant pbk APIs, and quests.md for
optional add-ons once the basic node works.
"""

import atexit
import logging
import sys
import tempfile
from pathlib import Path

import pbk


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATADIR = Path(tempfile.mkdtemp(prefix="pbk-node-"))

log = logging.getLogger("node")


# ---------------------------------------------------------------------------
# Kernel logging — pipe libbitcoinkernel's own logs into Python's stdlib
# logging under the `bitcoinkernel.<CATEGORY>` namespace. Useful for seeing
# what the kernel is doing under the hood.
# ---------------------------------------------------------------------------

_kernel_logs = pbk.KernelLogViewer(categories=[pbk.LogCategory.VALIDATION])
atexit.register(lambda: _kernel_logs.__dict__.pop("conn", None))


# ---------------------------------------------------------------------------
# Consensus params, used by Block.check() below.
# ---------------------------------------------------------------------------

CONSENSUS_PARAMS = pbk.ChainParameters(pbk.ChainType.REGTEST).consensus_params


# ---------------------------------------------------------------------------
# TODO 1: create the ChainstateManager.
#
# `pbk.load_chainman(datadir, chain_type)` opens (or creates) a chainstate
# in the given directory. Use REGTEST.
# ---------------------------------------------------------------------------

chainman = ...  # TODO


print(f"Datadir: {DATADIR}\n", file=sys.stderr)


# ---------------------------------------------------------------------------
# TODO 2: implement handle_block.
#
# It receives a hex string (one scanned QR / one pasted line) and must
# return a JSON-serializable dict. The runners forward this dict back to
# the user — whatever you put in it is what shows up.
#
# A reasonable shape:
#   {"accepted": True,  "is_new": bool, "height": int}        on success
#   {"accepted": False, "error": str, ...}                    on failure
#
# Two kinds of failure to distinguish:
#
#   1. The block is structurally invalid (bad PoW, bad merkle root, bad
#      coinbase, …). `block.check(CONSENSUS_PARAMS, pbk.BlockCheckFlags.ALL)`
#      runs the context-free checks and returns a BlockValidationState whose
#      `block_validation_result` carries the specific reason.
#
#   2. The block is structurally valid but doesn't connect — its parent
#      isn't in our chain yet. `chainman.process_block(block)` raises
#      `pbk.ProcessBlockException` with an opaque integer code; for our
#      purposes you can assume that means MISSING_PREV.
#
# Keep `handle_block` async — even if your body doesn't use `await`, the
# server runner expects to call it as a coroutine.
# ---------------------------------------------------------------------------

async def handle_block(hex_data: str) -> dict:
    raise NotImplementedError("TODO: implement handle_block")
