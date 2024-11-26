"""
This module provides shared, general functionality for processing
bytes representing blocks and prevouts. It should not be modified by
the user as part of the workshop.
"""

import json
from pathlib import Path
from typing import List

from bitcoin.core import CBlock, CTransaction
from bitcoin.core.script import CScript, OPCODE_NAMES


def parse_opcodes(script):
    """Extract non-data push OP_CODES from a script, and label them with their name."""
    return [OPCODE_NAMES.get(op, f"OP_UNKNOWN({op})") for op in script if isinstance(op, int) and op >= 0x61]


def get_tapscript(witness):
    """Extract TapScript from the witness stack."""
    # In Taproot, the second-to-last witness item is the embedded script
    witness_stack = list(witness)
    if len(witness_stack) >= 2:
        # Check if Annex exists, and remove it if so
        if witness_stack[-1][0] == 0x50:
            witness_stack.pop()
        return CScript(witness_stack[-2])
    return None

def process_transaction(tx: CTransaction, prevouts: List[CScript], opcode_counts: dict = None):
    """Analyze a transaction for Taproot Tapscript OP_CODE usage."""
    assert len(tx.vin) == len(prevouts), f"Number of inputs ({len(tx.vin)}) and prevouts ({len(prevouts)}) must match"

    opcode_counts = {} if opcode_counts is None else opcode_counts
    if tx.wit.is_null():
        return opcode_counts

    for vin_idx, prevout in enumerate(prevouts):
        if prevout.witness_version() != 1:
            continue  # TapScript only
        witness = tx.wit.vtxinwit[vin_idx].scriptWitness
        tapscript = get_tapscript(witness)
        if tapscript:
            for opcode in parse_opcodes(tapscript):
                opcode_counts[opcode] = opcode_counts.get(opcode, 0) + 1

    return opcode_counts


def analyze_block(block: bytes, prevouts: List[List[bytes]]):
    """Analyze a block for Taproot Tapscript OP_CODE usage.

    Args:
        block_bytes (bytes): Raw serialized block data.
        prevouts (List[List[bytes]]): Nested list of serialized prevout scripts.
            - Outer list size: number of transactions in the block.
            - Inner list size: number of outputs in each transaction.

    Returns:
        dict: OP_CODE frequencies.
    """
    opcode_counts = {}
    cblock = CBlock.deserialize(block)

    assert len(prevouts) == len(cblock.vtx), f"Number of transactions ({len(cblock.vtx)}) and prevouts ({len(prevouts)}) must match"

    for tx_idx, tx in enumerate(cblock.vtx):
        if tx.is_coinbase():
            continue
        tx_prevouts = [CScript(prevout) for prevout in prevouts[tx_idx]]
        process_transaction(tx, tx_prevouts, opcode_counts)
    return opcode_counts

def process_block(block: bytes, prevouts: List[List[bytes]], path: Path):
    """Analyze a block for Taproot Tapscript OP_CODE usage."""
    opcode_counts = analyze_block(block, prevouts)
    if not opcode_counts:
        return

    with open(path, "w") as file:
        json.dump({"op_code_frequencies": opcode_counts}, file)

    return opcode_counts
