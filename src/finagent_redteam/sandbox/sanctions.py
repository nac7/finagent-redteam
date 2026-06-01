"""Sanctions screening helpers.

Real screening must defeat *obfuscation*: adversaries register entities under
homoglyph or alias spellings (Cyrillic/Greek look-alikes, zero-width characters)
so a naive exact-match — or a stale "is_sanctioned" flag set at onboarding —
misses them. ``normalize_name`` folds those tricks away before matching, which is
exactly the capability the "guardrails on" policy is meant to add.
"""

from __future__ import annotations

from finagent_redteam.sandbox.state import Payee, World

# Common homoglyphs mapped to their Latin look-alikes (keys are lower-case;
# upper-case variants fold to these via str.casefold()).
_HOMOGLYPHS = {
    # Cyrillic
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "ѕ": "s", "і": "i", "ј": "j", "т": "t", "к": "k", "м": "m", "н": "h",
    # Greek
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "ν": "v", "τ": "t", "ι": "i",
    "κ": "k", "μ": "m", "β": "b",
}

# Zero-width / invisible characters used to break string matching.
_INVISIBLE = {"​", "‌", "‍", "﻿", "­"}


def normalize_name(name: str) -> str:
    """Casefold, map homoglyphs to Latin, drop invisibles, keep alphanumerics."""
    folded = name.casefold()
    mapped = "".join(_HOMOGLYPHS.get(ch, ch) for ch in folded if ch not in _INVISIBLE)
    return "".join(ch for ch in mapped if ch.isalnum())


def is_watchlisted(world: World, payee: Payee) -> bool:
    """True if the payee's (normalized) name matches a watchlist entry."""
    target = normalize_name(payee.name)
    return any(normalize_name(w) == target for w in world.sanctions_watchlist)


def is_sanctioned_effective(world: World, payee: Payee) -> bool:
    """A payee is effectively sanctioned if flagged OR caught by normalized
    watchlist matching (the latter is what robust screening adds)."""
    return payee.sanctioned or is_watchlisted(world, payee)
