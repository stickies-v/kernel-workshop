import ctypes
import pbk.capi.bindings as k


def kernel_byte_array_to_bytes(byte_array: k.kernel_ByteArray) -> bytes:
    return ctypes.string_at(byte_array.contents.data, byte_array.contents.size)

def normalize_block_height(context: k.kernel_Context, chainman: k.kernel_ChainstateManager, height: int) -> int:
    """
    If the height is negative, it is interpreted as a height relative to the tip of the chain.
    If the height is positive, it is interpreted as an absolute height.

    For example:
    - normalize_block_height(context, chainman, -1) will return the tip height
    - normalize_block_height(context, chainman, 0) will return the genesis block height
    - normalize_block_height(context, chainman, 5) will return the height of block 5
    """
    chain_tip = k.kernel_get_block_index_from_tip(context, chainman)
    assert chain_tip
    chain_tip_height = k.kernel_block_index_get_height(chain_tip)
    k.kernel_block_index_destroy(chain_tip)

    if height < 0:
        return chain_tip_height + height + 1
    return height
