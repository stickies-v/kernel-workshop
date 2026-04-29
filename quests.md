# Side quests

Once your node is processing blocks and you've reached chain B's tip, here are
optional add-ons that exercise different parts of the kernel API. Pick whichever
most pique your interest, they're independent from each other.

## Where does the output go?

For quests that produce output, generally the easiest approach will be to use one of:

- **Node terminal**: `print()` from anywhere in `node.py` and it shows up in
  the terminal you launched the runner from. Best for live events you want
  to see as they happen (callbacks firing, reorgs, etc.).
- **A flat file alongside the chainstate**: append a line per block to
  something like `<DATADIR>/op_returns.txt` or `<DATADIR>/coinbase.csv`.
  Your node prints its `Datadir:` on startup; `watch -n 1 cat …/<file>` it
  from a second shell, or `cat`/`grep`/`column` it after the workshop. Best
  for accumulating facts you'll want to query later.

---

## 1. Validation callbacks

[`pbk.ValidationInterfaceCallbacks`](https://stickies-v.github.io/py-bitcoinkernel/api/validation/#pbk.ValidationInterfaceCallbacks)
lets you hook into the kernel's validation events. The two most striking:

- `block_connected(user_data, block, entry)` — fires when a block becomes part
  of the best chain.
- `block_disconnected(user_data, block, entry)` — fires when a block leaves
  the best chain (i.e. a reorg is happening).

When chain B overtakes chain A, you'll see a burst of `block_disconnected`s
followed by a burst of `block_connected`s.

## 2. Block tree visualization

Render every chain the kernel knows about — including orphan forks — to
`block_tree.txt` next to the chainstate, so you can `watch -n 1 cat
<DATADIR>/block_tree.txt` from another shell.

[`chainman.block_tree_entries`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.BlockTreeEntryMap)
is a hash-keyed map of every known [`BlockTreeEntry`](https://stickies-v.github.io/py-bitcoinkernel/api/block/#pbk.BlockTreeEntry),
but it only supports lookup, not enumeration. So you have to track tips
yourself: when a new block arrives, its parent stops being a tip and the
new block becomes one. Maintain a set of tip hashes; walk back from each
via `entry.previous` to render its chain. The active chain's tip is
`chainman.best_entry`; the rest are forks.

Refresh the file from `handle_block` after a successful `process_block`,
*not* from `block_connected` — `block_connected` only fires when a block
joins the **active** chain, so siblings being built on a non-best fork
wouldn't trigger it and would be invisible until the fork wins.

If adding a new block grows the tip set (i.e. its parent wasn't already a
tip), a new fork has just started — a one-time event worth logging.

## 3. OP_RETURN indexer

Some blocks have OP_RETURN outputs hiding text. Walk every block on the
active chain, scan its outputs (via `tx.outputs[i].script_pubkey` —
[`TransactionOutput.script_pubkey`](https://stickies-v.github.io/py-bitcoinkernel/api/transaction/#pbk.TransactionOutput)),
and decode anything that looks like ASCII.

OP_RETURN outputs start with the byte `0x6a`; the rest of the script is the
payload (after a length-prefix byte for short payloads).

Drive this from the `block_connected` callback (quest 1), not from
`handle_block`: that way you index only blocks that are on the best chain,
and you get reorg-awareness for free — `block_disconnected` lets you drop
the row when a block leaves.

## 4. Coinbase auditor

The block subsidy on regtest is 50 BTC (5_000_000_000 sat — no halving over
our short chain). Every coinbase claims some amount in its outputs; the
output total can be *less* than the subsidy if a miner forgoes some of it.
Two of the workshop blocks have something interesting going on here.

A few things to note:

- The first transaction of each block is the coinbase.
- Coinbases also carry a witness-commitment OP_RETURN output — script
  prefix `6a24aa21a9ed`, value 0 — that you should exclude when summing
  the claimed amount.
- Same shape as the OP_RETURN indexer: hook `block_connected` /
  `block_disconnected` so the file reflects the active chain.

## 5. Headers-first sync

Real Bitcoin nodes don't download full blocks before knowing whether they
even want them. They sync the **header chain** first — 80 bytes per block,
just enough to verify proof-of-work and the chain's structure — then fetch
bodies for the chain that wins. The kernel exposes the same primitive via
[`process_block_header`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager.process_block_header).

Call it *before* `process_block` in your `handle_block`. The kernel keeps
two pointers into the same tree: the header tip
([`chainman.best_entry`](https://stickies-v.github.io/py-bitcoinkernel/api/chain/#pbk.ChainstateManager.best_entry)),
which is the deepest block whose header has been accepted, and the
validated tip (`chainman.get_active_chain().height`), which is the deepest
block whose body has been fully validated against the UTXO set. The
validated tip is always at or behind the header tip; out-of-order scanning
extends the header tip ahead.

Same opaque-exception caveat as `process_block`: failures (missing prev,
bad PoW, etc.) raise `pbk.ProcessBlockHeaderException` rather than returning
a structured state. Reuse the `block_checked`-callback trick if you want
the specific reason.
