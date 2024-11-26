import json

import pbk
from common.args import parse_args
from common.process import analyze_block


def main():
    args = parse_args()
    frequencies = {}

    chain_man = pbk.load_chainman(args.datadir, args.chain_type)
    # Iterate over all blocks from start to end height, and fetch the block and undo data so it can
    # be analyzed with `analyze_block`.
    for block_index in pbk.block_index_generator(chain_man, start=args.start_height, end=args.end_height):
        undo = chain_man.read_block_undo_from_disk(block_index)
        block_data = chain_man.read_block_from_disk(block_index).data
        # add empty list for coinbase transaction
        prevouts = [[]] + [[output.script_pubkey.data for output in tx.iter_outputs()] for tx in undo.iter_transactions()]
        block_results = analyze_block(block_data, prevouts)
        if block_results:
            frequencies[block_index.height] = block_results

    with open(args.output, "w") as f:
        json.dump(frequencies, f)
        print(f"Last block {block_index}, output written to {args.output.absolute()}")

if __name__ == "__main__":
    main()
