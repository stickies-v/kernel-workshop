import pbk
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
DEFAULT_OUTPUT = PROJECT_DIR / "data" / "op_code" / "block_frequencies.json"
DEFAULT_CHAIN_TYPE = "signet"

import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Run the pbk main function with optional datadir and chain_type.")
    parser.add_argument("--datadir", required=True, type=Path, help="Path to the data directory which contains the blocks/ and chainstate/ directories of a Bitcoin Core datadir")
    parser.add_argument("--chain_type", type=str, default=DEFAULT_CHAIN_TYPE, 
                        choices=[ct.name.lower() for ct in pbk.ChainType], 
                        help="Type of blockchain network")
    parser.add_argument("--start_height", type=int, default=1, help="Start block index (must not be 0, negative values indicate value relative to the chain tip) (default: block 1)")
    parser.add_argument("--end_height", type=int, default=-1, help="End block index (inclusive, negative values indicate value relative to the chain tip) (default: chain tip)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to the output file")

    args = parser.parse_args()

    args.datadir = validate_datadir(args.datadir)
    args.chain_type = convert_chain_type(args.chain_type)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    return args

def validate_datadir(datadir: Path):
    if not datadir.exists():
        print(f"Error: The specified datadir '{datadir}' does not exist.")
        sys.exit(1)
    if not ((datadir / "blocks").exists() and (datadir /"chainstate").exists()):
        print(f"Error: The specified datadir '{datadir}' does not appear to be a valid Bitcoin Core datadir. It must contain 'blocks/' and 'chainstate/' directories.")
        sys.exit(1)
    return datadir

def convert_chain_type(chain_type_str):
    try:
        return pbk.ChainType[chain_type_str.upper()]
    except KeyError:
        print(f"Error: Invalid chain_type '{chain_type_str}'. Valid options are: {', '.join(ct.name.lower() for ct in pbk.ChainType)}.")
        sys.exit(1)
