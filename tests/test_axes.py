"""Tests for the diversity axes and the stratified grid enumerator."""

import pytest

from finagent_redteam.scenarios.axes import (
    StepMode,
    Tier,
    Vector,
    stratified_grid,
)

AXES = {
    "tier": [Tier.EASY, Tier.MEDIUM, Tier.HARD],
    "vector": [Vector.EMAIL, Vector.CHAT, Vector.TICKET],
}
PRODUCT = 3 * 3  # |tier| * |vector|


def test_grid_is_deterministic():
    a = stratified_grid(AXES, n=20, seed=0)
    b = stratified_grid(AXES, n=20, seed=0)
    assert a == b


def test_grid_seed_changes_order():
    a = stratified_grid(AXES, n=PRODUCT, seed=0)
    b = stratified_grid(AXES, n=PRODUCT, seed=1)
    # Same set of cells, (almost surely) different order.
    assert {tuple(sorted(c.items())) for c in a} == {tuple(sorted(c.items())) for c in b}
    assert a != b


def test_grid_covers_every_cell_before_repeating():
    cells = stratified_grid(AXES, n=PRODUCT, seed=3)
    seen = {tuple(sorted(c.items())) for c in cells}
    assert len(seen) == PRODUCT  # first full pass hits all combinations


def test_grid_repeats_are_balanced():
    n = PRODUCT * 3
    cells = stratified_grid(AXES, n=n, seed=5)
    from collections import Counter

    counts = Counter(tuple(sorted(c.items())) for c in cells)
    assert set(counts.values()) == {3}  # perfectly even at an exact multiple


def test_grid_uneven_counts_differ_by_at_most_one():
    cells = stratified_grid(AXES, n=PRODUCT + 1, seed=5)
    from collections import Counter

    counts = Counter(tuple(sorted(c.items())) for c in cells)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_grid_each_cell_has_all_axes():
    for cell in stratified_grid(AXES, n=12, seed=2):
        assert set(cell.keys()) == {"tier", "vector"}


def test_grid_empty_axis_rejected():
    with pytest.raises(ValueError):
        stratified_grid({"tier": []}, n=1, seed=0)


def test_grid_zero_n():
    assert stratified_grid(AXES, n=0, seed=0) == []


def test_enum_values_are_stable_strings():
    # These string values land in scenario IDs / reports; pin them.
    assert Vector.EMAIL.value == "email"
    assert Tier.HARD.value == "hard"
    assert StepMode.CHAIN.value == "chain"
    assert len(list(Vector)) == 7
    assert len(list(Tier)) == 3
    assert len(list(StepMode)) == 4
