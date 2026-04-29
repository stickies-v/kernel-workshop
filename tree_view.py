"""Render the active chain plus any orphan fork tips as a horizontal tree.

Each block is a small square (`▪`). The active chain is on top; fork tips
branch out below from their last common ancestor with the active chain.

`render_tree` returns a multi-line string. `node.py` writes it to a file
(`block_tree.txt`) so participants can `watch -n 1 cat block_tree.txt` in
a separate terminal and not pollute the node's stdout.

Compact, width-aware: when a chain doesn't fit, the middle blocks collapse
to "▪▪ ⋯ N more ⋯ ▪▪".
"""

from __future__ import annotations

from collections.abc import Iterable

import pbk


SQUARE = "▪"


def _walk_back(tip: pbk.BlockTreeEntry) -> list[tuple[int, str]]:
    """Walk backward from `tip` to genesis. Returns [(height, short_hash), ...]
    in genesis-first order."""
    chain = []
    entry: pbk.BlockTreeEntry | None = tip
    while entry is not None:
        chain.append((entry.height, str(entry.block_hash)[:6]))
        # entry.previous returns the parent or None at genesis.
        try:
            entry = entry.previous
        except Exception:
            entry = None
    return list(reversed(chain))


def _render_chain(chain: list[tuple[int, str]], available: int) -> str:
    """Render one chain as a row of squares. Collapse the middle if needed."""
    n = len(chain)
    # Each block is "▪ " except the last (no trailing space). Width = 2*n - 1.
    if 2 * n - 1 <= available:
        return " ".join(SQUARE for _ in chain)

    # Collapse: keep K squares at each end, "⋯ N more ⋯" between them.
    # Reserve space for " ⋯ N more ⋯ " between the two segments.
    # Solve roughly: 2K + len(separator) ≤ available.
    edge = 3
    middle = f" ⋯ {n - 2 * edge} more ⋯ "
    return (
        " ".join(SQUARE for _ in range(edge))
        + middle
        + " ".join(SQUARE for _ in range(edge))
    )


def _label_line(chain: list[tuple[int, str]], rendered: str) -> str:
    """Label the first and last block under the rendered chain."""
    if not chain:
        return ""
    first_h, first_short = chain[0]
    last_h, last_short = chain[-1]
    if len(chain) == 1:
        return f"{first_short} (h={first_h})"
    # Pad so the last label sits under the last square.
    left = f"{first_short} (h={first_h})"
    right = f"{last_short} (h={last_h})"
    pad = max(1, len(rendered) - len(left) - len(right))
    return left + " " * pad + right


def render_tree(
    active_tip: pbk.BlockTreeEntry,
    fork_tips: Iterable[pbk.BlockTreeEntry] = (),
    width: int = 100,
) -> str:
    """Return a multi-line string showing the active chain and any orphan tips."""
    available = max(20, width - 2)
    lines: list[str] = []

    active_chain = _walk_back(active_tip)
    rendered = _render_chain(active_chain, available)
    lines.append(f"chain (active tip: h={active_tip.height}):")
    lines.append("  " + rendered)
    lines.append("  " + _label_line(active_chain, rendered))

    active_hashes = {h for _, h in active_chain}

    # Build the orphan branch (heights+hashes) for each fork tip.
    branches: list[list[tuple[int, str]]] = []
    for fork_tip in fork_tips:
        fork_chain = _walk_back(fork_tip)
        diverge_idx = next(
            (i for i, (_, h) in enumerate(fork_chain) if h not in active_hashes),
            len(fork_chain),
        )
        if diverge_idx == len(fork_chain):
            continue  # Fork is fully on the active chain (shouldn't happen)
        branches.append(fork_chain[diverge_idx:])

    # Drop branches whose blocks are a subset of a longer branch — they're the
    # same fork observed at an earlier point in a disconnect sequence.
    branches.sort(key=len, reverse=True)
    distinct: list[list[tuple[int, str]]] = []
    for b in branches:
        if any(set(map(tuple, b)).issubset(set(map(tuple, longer))) for longer in distinct):
            continue
        distinct.append(b)

    for branch in distinct:
        # Indent so the branch lines up with where it diverged from active.
        # Active is rendered as "▪ ▪ ▪ ..." — 2*height columns to reach height i.
        indent_cols = 2 * branch[0][0]
        rendered_branch = _render_chain(branch, available - indent_cols)
        lines.append("  " + " " * indent_cols + rendered_branch + "   ← orphan")
        # Label the orphan tip under the last square of the branch.
        tip_h, tip_short = branch[-1]
        tip_label = f"{tip_short} (h={tip_h})"
        # The branch's last square sits at column len(rendered_branch) - 1
        # within the indented region; right-pad so the label ends there.
        label_col = indent_cols + len(rendered_branch) - len(tip_label)
        lines.append("  " + " " * max(0, label_col) + tip_label)

    return "\n".join(lines) + "\n"
