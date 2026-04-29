# py-bitcoinkernel quick tour

Pointers into [`py-bitcoinkernel`](https://stickies-v.github.io/py-bitcoinkernel/)
(`pbk`), the Python bindings for Bitcoin Core's `bitcoinkernel`. The full
[API reference](https://stickies-v.github.io/py-bitcoinkernel/api/chain/) is
the source of truth.

---

## Chainstate manager

A [`ChainstateManager`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager)
owns the block tree and the UTXO set. You can use it to submit block (headers), iterate the block
tree, and more.

`pbk.load_chainman` opens or creates one in a directory:

```py
import pbk

chainman = pbk.load_chainman("/path/to/datadir", pbk.ChainType.REGTEST)
```

[`ChainType`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainType):
`MAINNET`, `TESTNET`, `TESTNET_4`, `SIGNET`, `REGTEST`. The datadir is held
exclusively. For more control (worker threads, in-memory databases, wiping),
use [`ChainstateManagerOptions`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManagerOptions)
with a [`Context`](https://stickies-v.github.io/py-bitcoinkernel/api/context/#pbk.Context).

---

## Logging

`bitcoinkernel` emits the same structured logs a Bitcoin Core full node
does — proof-of-work checks, UTXO updates, validation failures, reorgs.
[`pbk.KernelLogViewer`](https://stickies-v.github.io/py-bitcoinkernel/api/logging/#pbk.KernelLogViewer)
forwards them into Python's stdlib `logging` under the
`bitcoinkernel.<CATEGORY>` namespace.

```py
import logging

logging.basicConfig(level=logging.INFO) # logging MUST be configured before the viewer is instantiated
viewer = pbk.KernelLogViewer(categories=[pbk.LogCategory.VALIDATION])
# Keep `viewer` alive — garbage collection tears down the bridge.
```

Each [`LogCategory`](https://stickies-v.github.io/py-bitcoinkernel/api/logging/#pbk.LogCategory)
is a child logger you can filter or route independently. Categories:
`VALIDATION`, `BLOCKSTORAGE`, `COINDB`, `BENCH`, `MEMPOOL`, `PRUNE`, `KERNEL`,
`ALL`.

Note: `bitcoinkernel` logging should only be used as an informational tool, e.g. in case of debugging.
It is not part of the interface, and log strings can change at any time.

---

## Submitting blocks

### Full blocks

[`chainman.process_block(block)`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager.process_block)
runs the full validation pipeline. Returns `True` if the block was new,
`False` if already known. Raises
[`ProcessBlockException`](https://stickies-v.github.io/py-bitcoinkernel/api/exception/#pbk.ProcessBlockException)
if the block could not be added, e.g. because the previous block is not yet added, or because the
block is invalid.

```py
block = pbk.Block(bytes.fromhex(hex_data))
try:
    is_new = chainman.process_block(block)
except pbk.ProcessBlockException:
    pass
```

The exception only carries an opaque integer code. The reason
(`MISSING_PREV`, `INVALID_HEADER`, `MUTATED`, `TIME_FUTURE`, `CONSENSUS`, …)
is delivered via:

- the kernel's logs (see #logging), or
- a [`block_checked` callback](#capturing-the-rejection-reason).

### Headers only

[`chainman.process_block_header(header)`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager.process_block_header)
validates only the block header, which can be used for headers-first sync.

```py
try:
    state = chainman.process_block_header(block.block_header)
except pbk.ProcessBlockHeaderException:
    pass   # most failures (missing prev, bad PoW, ...) end up here
```

On success returns a [`BlockValidationState`](https://stickies-v.github.io/py-bitcoinkernel/api/validation/#pbk.BlockValidationState),
which in practice will be `VALID` — anything else raises.

---

## Reading the chain

[`chainman.get_active_chain()`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager.get_active_chain)
returns a [`Chain`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.Chain) —
a sequence of the active chain, indexed by height.

```py
chain = chainman.get_active_chain()
chain.height                                 # tip height
chain.block_tree_entries[0]                  # genesis
chain.block_tree_entries[-1]                 # tip
for entry in chain.block_tree_entries:
    ...
```

Each entry is a [`BlockTreeEntry`](https://stickies-v.github.io/py-bitcoinkernel/api/block/#pbk.BlockTreeEntry):

```py
entry.height               # int
entry.block_hash           # BlockHash
entry.block_header         # BlockHeader
entry.previous             # BlockTreeEntry, or None at genesis
```

Read full block bytes from disk via
[`chainman.blocks`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.BlockMap):

```py
block = chainman.blocks[entry]
```

The kernel also tracks orphan entries off the active chain. Look up by hash
via the [`BlockTreeEntryMap`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.BlockTreeEntryMap):

```py
chainman.block_tree_entries[some_hash]       # KeyError if unknown
chainman.best_entry                          # most-work tip
```

`best_entry` is the header chain tip; it can run ahead of the active
validated chain when headers have arrived without their bodies.

`chainman.block_tree_entries` is lookup-only — no enumeration. Track tips
yourself if you need to enumerate forks (see below).

---

## Walking blocks and transactions

[`Block`](https://stickies-v.github.io/py-bitcoinkernel/api/block/#pbk.Block) —
construct from bytes or read from disk:

```py
block = pbk.Block(raw_bytes)
block.block_hash             # BlockHash
block.block_header           # BlockHeader
for tx in block.transactions:
    for txin in tx.inputs:
        txin.out_point.txid
        txin.out_point.index
    for txout in tx.outputs:
        txout.amount                 # sat
        bytes(txout.script_pubkey)   # raw scriptPubkey
```

See
[`Transaction`](https://stickies-v.github.io/py-bitcoinkernel/api/transaction/#pbk.Transaction),
[`TransactionInput`](https://stickies-v.github.io/py-bitcoinkernel/api/transaction/#pbk.TransactionInput),
[`TransactionOutput`](https://stickies-v.github.io/py-bitcoinkernel/api/transaction/#pbk.TransactionOutput).

[`BlockHeader`](https://stickies-v.github.io/py-bitcoinkernel/api/block/#pbk.BlockHeader):

```py
header = block.block_header                  # or pbk.BlockHeader(80_bytes)
header.block_hash                            # BlockHash
header.prev_hash                             # BlockHash
header.timestamp                             # datetime
header.bits                                  # int (compact PoW target)
header.version                               # int
header.nonce                                 # int
```

---

## Validation callbacks

[`pbk.ValidationInterfaceCallbacks`](https://stickies-v.github.io/py-bitcoinkernel/api/validation/#pbk.ValidationInterfaceCallbacks),
passed as the third argument to `load_chainman`:

```py
def on_checked(user_data, block, state):
    ...   # fires once per process_block

def on_connected(user_data, block, entry):
    ...   # fires when a block joins the active chain

def on_disconnected(user_data, block, entry):
    ...   # fires when a block leaves the active chain (reorg)

callbacks = pbk.ValidationInterfaceCallbacks(
    block_checked=on_checked,
    block_connected=on_connected,
    block_disconnected=on_disconnected,
)
chainman = pbk.load_chainman(datadir, pbk.ChainType.REGTEST, callbacks)
```

- `block_connected` fires only for the **active** chain. Blocks joining a
  non-best fork are silent until that fork wins.
- `block_disconnected` fires once per dropped block during a reorg, deepest
  tip first.
- `block_checked` fires once per `process_block`, regardless of outcome.

### Capturing the rejection reason

`process_block` raises with an opaque code, but `block_checked` fires inside
the same call with a structured
[`BlockValidationResult`](https://stickies-v.github.io/py-bitcoinkernel/api/validation/#pbk.BlockValidationResult).
Capture it from the callback, read it after the call returns.

```py
last_result = None

def on_checked(user_data, block, state):
    nonlocal last_result
    last_result = state.block_validation_result   # IntEnum, by value

callbacks = pbk.ValidationInterfaceCallbacks(block_checked=on_checked)
chainman = pbk.load_chainman(datadir, pbk.ChainType.REGTEST, callbacks)

try:
    chainman.process_block(block)
except pbk.ProcessBlockException:
    print(last_result.name)        # e.g. "MISSING_PREV"
```

Copy the value out, not the state object — see next section.

---

## Lifetimes for callback arguments

Some callback arguments and property values are **views** into kernel-owned
memory, valid only for the duration of the callback. Holding a reference past
that point reads freed memory.

The `state` argument to `block_checked` is one such view:

```py
saved = None

def on_checked(user_data, block, state):
    nonlocal saved
    saved = state                       # WRONG — view will be freed

saved.block_validation_result          # garbage / segfault risk
```

Copy primitive values out inside the callback:

```py
last_result = None

def on_checked(user_data, block, state):
    nonlocal last_result
    last_result = state.block_validation_result   # IntEnum, by value
```

---

## Tracking fork tips

The block-tree map is lookup-only. To enumerate fork tips, maintain them
yourself: a tip is a hash nobody has built on. On each new block, its parent
is no longer a tip; the new block is.

```py
tips = set()
tips.add(str(chainman.get_active_chain().block_tree_entries[0].block_hash))

def record(block):
    tips.discard(str(block.block_header.prev_hash))
    tips.add(str(block.block_hash))
```

If adding a block grows the set, the parent wasn't a tip — a new fork has
started.

To traverse a fork, walk `entry.previous` from a tip.

---

## Pointers

- [API reference](https://stickies-v.github.io/py-bitcoinkernel/)
- The C kernel header: `depend/bitcoin/src/kernel/bitcoinkernel.h` in the
  [pbk repo](https://github.com/stickies-v/py-bitcoinkernel)
