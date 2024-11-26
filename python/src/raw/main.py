import json
import typing
from pathlib import Path

import pbk.capi.bindings as k
from common.args import parse_args
from common.process import analyze_block
from raw.util import kernel_byte_array_to_bytes, normalize_block_height

if typing.TYPE_CHECKING:
    import argparse

def make_context(args: 'argparse.Namespace') -> k.kernel_Context:
    """
    To create a context, we can use the `kernel_context_create`
    function. To instantiate a context, we first need to create a
    context options object, and then set the chain parameters on that
    options object. The chain parameters are created based on the chain
    type, which is part of `args`.
    
    Make sure all kernel objects that are created in this function are
    cleaned up to avoid leaking memory. We can't do that for the context
    object, so the user has to ensure that's done manually later.
    """
    # WSTASK 1: implement make_context, don't forget to clean up kernel
    # objects created here (context_opts and chain_params)
    datadir = args.datadir
    context_opts = ...
    chain_params = ...
    context = ...

    """
    Once the context is created, the context options and chain
    parameters are no longer necessary, so we can clean them up here.
    The context itself needs to be destroyed by the user manually.
    """
    ...

    return context

def make_chainman(context: k.kernel_Context, datadir: Path) -> k.kernel_ChainstateManager:
    """
    To create a ChainstateManager, we first need to instantiate
    ChainstateManagerOptions and BlockManagerOptions objects. Once the
    ChainstateManager is constructed, we can load it after we
    instantiate a ChainstateLoadOptions object.

    Make sure all kernel objects that are created in this function are
    cleaned up to avoid leaking memory. We can't do that for the
    chainstate_manager object, so the user has to ensure that's done
    manually later. 
    """
    blocksdir = datadir / "blocks/"

    # WSTASK 2: implement make_chainman, don't forget to clean up kernel
    # objects created here (chainman_opts, blockman_opts, chainstate_load_opts)
    chainman_opts = ...
    blockman_opts = ...
    chainstate_manager = ...
    chainstate_load_opts = ...
    assert k.kernel_chainstate_manager_load_chainstate(context, chainstate_load_opts, chainstate_manager)

    """
    We have our chainstate_manager, so we can clean up the now
    unnecessary options objects.
    The chainstate_manager needs to be destroyed by the user manually.
    """
    ...

    return chainstate_manager

def get_block_data_prevouts(
        context: k.kernel_Context,
        chainstate_manager: k.kernel_ChainstateManager,
        block_index: k.kernel_BlockIndex
) -> typing.Tuple[bytes, typing.List[typing.List[bytes]]]:
    """Get the block data and the prevouts of a block."""

    """
    First, we'll use the BlockUndo data which stores the prevouts for
    each transaction in a block.

    As always, destroy any kernel objects we don't need anymore.
    """
    # WSTASK 4: implement get_block_data_prevouts
    undo = ...
    # add empty list for coinbase transaction
    prevouts = [[]] + [get_outputs_from_undo_transaction(undo, tx_idx) for tx_idx in range(k.kernel_block_undo_size(undo))]
    k.kernel_block_undo_destroy(undo)

    """
    Next, we'll read the Block data from disk. This is where the
    witness data (that contains the TapScript) is stored.

    As always, destroy any kernel objects we don't need anymore.
    """
    block = ... # read block from disk
    block_byte_arr = ... # copy the opaque block pointer into a bytearray we can access
    block_bytes = kernel_byte_array_to_bytes(block_byte_arr)
    # don't forget to clean up

    return block_bytes, prevouts

def block_index_iterator(
        context: k.kernel_Context,
        chainman: k.kernel_ChainstateManager,
        start_height: int,
        end_height: int
) -> typing.Generator[k.kernel_BlockIndex, None, None]:
    """
    Helper function to iterate (lazily, using a generator) over a range of
    block indices, specified by `start_height` and `end_height`.

    Make sure all kernel objects that are created in this function are
    cleaned up to avoid leaking memory.
    """
    # WSTASK 3: implement block_index_iterator
    try:
        start_height = normalize_block_height(context, chainman, start_height)
        end_height = normalize_block_height(context, chainman, end_height)
        assert start_height <= end_height, f"start_height ({start_height}) must be less than or equal to end_height ({end_height})"
        block_index = ... # get block_index for start_height
        while block_index and ... <= end_height:  # use kernel to get the height of the block_index
            yield block_index
            previous_block_index = block_index
            block_index = ...  # get next block_index (and don't forget to clean up the previous_block_index)

    finally:
        if block_index is not None:
            k.kernel_block_index_destroy(block_index)

def get_outputs_from_undo_transaction(undo: k.kernel_BlockUndo, tx_idx: int) -> typing.List[bytes]:
    """Get all of a transaction outputs, using a BlockUndo and the index of the transaction."""
    output_bytes = []
    for output_idx in range(k.kernel_get_transaction_undo_size(undo, tx_idx)):
        output = k.kernel_get_undo_output_by_index(undo, tx_idx, output_idx)
        output_bytes.append(transaction_output_to_bytes(output))
        k.kernel_transaction_output_destroy(output)
    return output_bytes

def transaction_output_to_bytes(output: k.kernel_TransactionOutput) -> bytes:
    """Get the scriptpubkey of an output as bytes. """
    
    # WSTASK 5: implement transaction_output_to_bytes
    # 1. copy the scriptpubkey from the output
    # 2. copy the scriptpubkey data into a bytearray
    # 3. convert the bytearray to bytes
    # 4. clean up
    # Note: if you chain steps 1 and 2 into a single expression, you
    # won't be able to clean up the scriptpubkey.
    spk = ...
    byte_arr = ...
    bytes = kernel_byte_array_to_bytes(byte_arr)

    return bytes

def main():
    args = parse_args()

    context = make_context(args)  # make sure to destroy at the end
    chainstate_manager = make_chainman(context, args.datadir)  # make sure to destroy at the end

    """
    Now we can iterate over the blocks we're interested in, getting the
    block data and the prevouts for each block. We can pass these to
    `analyze_block`, which will calculate the TapScript OP_CODE
    frequencies.
    """
    frequencies = {}
    for block_index in block_index_iterator(context, chainstate_manager, args.start_height, args.end_height):
        block_bytes, prevouts = get_block_data_prevouts(context, chainstate_manager, block_index)
        result = analyze_block(block_bytes, prevouts)
        if result:
            block_height = k.kernel_block_index_get_height(block_index)
            frequencies[block_height] = result

    """
    Cleanly tear down all kernel objects before quitting.
    """
    k.kernel_chainstate_manager_destroy(chainstate_manager, context)
    k.kernel_context_destroy(context)

    """
    Write the frequencies to a file.
    """
    with open(args.output, "w") as f:
        json.dump(frequencies, f)
        print(f"Output written to {args.output.absolute()}")

if __name__ == '__main__':
    main()
