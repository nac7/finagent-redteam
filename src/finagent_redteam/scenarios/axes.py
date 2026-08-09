"""Diversity axes and a seeded, stratified grid enumerator.

Phase 1 scales the suite by varying scenarios along orthogonal axes — delivery
*vector*, difficulty *tier*, and *step mode* — instead of drawing parameters at
random (which repeats combinations and leaves gaps). :func:`stratified_grid`
enumerates cells so that **every** combination in the Cartesian product is
covered once before any combination repeats, deterministically for a given seed.

This is the primitive the Week-2 builders consume: ask for ``n`` cells over a set
of axes and receive an even, gap-free, reproducible spread.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any


class Vector(str, Enum):
    """Untrusted surface the injection is delivered through."""

    EMAIL = "email"
    INVOICE_PDF = "invoice_pdf_text"
    CHAT = "chat_message"
    TICKET = "support_ticket"
    CALENDAR = "calendar_invite"
    ERP_MEMO = "erp_memo_field"
    DOC_COMMENT = "document_comment"


class Tier(str, Enum):
    """Attack difficulty: how overt the ask and how much cover/obfuscation."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class StepMode(str, Enum):
    """Shape of the attacker action sequence (length of the reference_plan)."""

    SINGLE = "single"   # one malicious tool call
    CHAIN = "chain"     # two+ malicious calls (e.g. update_payee -> transfer)
    PIVOT = "pivot"     # benign-looking step first, then the malicious action
    SPLIT = "split"     # N sub-threshold calls (structuring)


def stratified_grid(
    axes: Mapping[str, Sequence[Any]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Return ``n`` cells covering the Cartesian product of ``axes`` evenly.

    Every combination appears once before any repeats; per-cell counts differ by
    at most one. Deterministic for a given ``seed`` and axis layout.

    Args:
        axes: ordered mapping of axis name -> its allowed values (each non-empty).
        n: number of cells to emit (may exceed the product size -> even repeats).
        seed: reproducibility seed.

    Returns:
        A list of ``n`` dicts, each mapping every axis name to one chosen value.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    names = list(axes.keys())
    value_lists = [list(axes[k]) for k in names]
    if not names or any(len(v) == 0 for v in value_lists):
        raise ValueError("each axis needs at least one value")

    product = [dict(zip(names, combo)) for combo in itertools.product(*value_lists)]
    # String seed keeps determinism while decoupling different axis layouts.
    layout = "|".join(f"{k}:{len(v)}" for k, v in zip(names, value_lists))
    rng = random.Random(f"grid|{seed}|{layout}")
    order = product[:]
    rng.shuffle(order)
    # Cycle the shuffled product: first pass covers all cells, then even repeats.
    return [dict(order[i % len(order)]) for i in range(n)]
