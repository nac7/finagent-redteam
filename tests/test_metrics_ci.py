"""Tests for Wilson confidence intervals in the benchmark scorecard."""

import math

import pytest

from finagent_redteam.eval.metrics import (
    CI,
    CategoryStat,
    Scorecard,
    build_scorecard,
    category_breakdown,
    wilson_ci,
)
from finagent_redteam.leaderboard import ModelReport, ScenarioTrialResult, render_markdown


# ---------------------------------------------------------------------------
# wilson_ci — unit tests against known values
# ---------------------------------------------------------------------------

def test_wilson_ci_known_proportion():
    """50 successes / 100 trials → CI centred near 0.50."""
    ci = wilson_ci(50, 100)
    assert ci.lower < 0.50 < ci.upper
    # Standard result is approximately [0.40, 0.60]
    assert abs(ci.lower - 0.404) < 0.005
    assert abs(ci.upper - 0.596) < 0.005


def test_wilson_ci_zero_trials():
    """No data → uninformative [0, 1] interval."""
    ci = wilson_ci(0, 0)
    assert ci == CI(0.0, 1.0)


def test_wilson_ci_zero_successes():
    """All failures → lower bound is 0."""
    ci = wilson_ci(0, 20)
    assert ci.lower == 0.0
    assert ci.upper > 0.0


def test_wilson_ci_all_successes():
    """All successes → upper bound is 1."""
    ci = wilson_ci(10, 10)
    assert ci.upper == 1.0
    assert ci.lower < 1.0


def test_wilson_ci_stays_in_unit_interval():
    """Bounds must always be within [0, 1] for any inputs."""
    for k, n in [(0, 1), (1, 1), (0, 100), (100, 100), (1, 1000), (999, 1000)]:
        ci = wilson_ci(k, n)
        assert 0.0 <= ci.lower <= ci.upper <= 1.0


def test_wilson_ci_width_shrinks_with_more_trials():
    """More trials → narrower interval (all else equal)."""
    ci_small = wilson_ci(5, 10)
    ci_large = wilson_ci(50, 100)
    assert ci_large.width() < ci_small.width()


def test_wilson_ci_symmetric_around_half():
    """At p=0.5 the interval is symmetric."""
    ci = wilson_ci(50, 100)
    midpoint = (ci.lower + ci.upper) / 2
    assert abs(midpoint - 0.50) < 0.01


def test_wilson_ci_str_format():
    """String representation matches expected format."""
    ci = CI(0.293, 0.547)
    assert str(ci) == "[29%–55%]"


def test_ci_as_dict():
    """as_dict returns rounded lower/upper keys."""
    ci = CI(0.29312, 0.54678)
    d = ci.as_dict()
    assert set(d.keys()) == {"lower", "upper"}
    assert d["lower"] == round(0.29312, 4)
    assert d["upper"] == round(0.54678, 4)


# ---------------------------------------------------------------------------
# build_scorecard — CIs computed and non-trivial
# ---------------------------------------------------------------------------

def _make_result(sid, cat, benign, n, k_none, k_adv, k_enf):
    """Helper: ScenarioTrialResult with explicit success counts."""
    return ScenarioTrialResult(sid, cat, benign, n, k_none, k_adv, k_enf)


def test_scorecard_has_ci_fields():
    """build_scorecard populates all six CI fields."""
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 3, 2, 1, 0),
        _make_result("a2", "T4_structuring",           False, 3, 3, 3, 0),
        _make_result("b1", "BENIGN",                   True,  3, 3, 3, 3),
    ]
    card = build_scorecard("m", results)
    for attr in (
        "asr_none_ci", "asr_advisory_ci", "asr_enforced_ci",
        "utility_none_ci", "utility_advisory_ci", "utility_enforced_ci",
    ):
        ci = getattr(card, attr)
        assert isinstance(ci, CI)
        assert 0.0 <= ci.lower <= ci.upper <= 1.0


def test_scorecard_ci_point_estimate_inside_interval():
    """The point estimate must lie inside its own confidence interval."""
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 3, 2, 1, 0),
        _make_result("a2", "T4_structuring",           False, 3, 3, 3, 0),
        _make_result("b1", "BENIGN",                   True,  3, 3, 3, 2),
    ]
    card = build_scorecard("m", results)
    assert card.asr_none_ci.lower <= card.asr_none <= card.asr_none_ci.upper
    assert card.asr_advisory_ci.lower <= card.asr_advisory <= card.asr_advisory_ci.upper
    assert card.asr_enforced_ci.lower <= card.asr_enforced <= card.asr_enforced_ci.upper
    assert card.utility_enforced_ci.lower <= card.utility_enforced <= card.utility_enforced_ci.upper


def test_scorecard_enforced_zero_asr_ci():
    """When enforced ASR is 0 across all trials lower bound should be 0."""
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 5, 4, 2, 0),
        _make_result("a2", "T4_structuring",           False, 5, 5, 5, 0),
        _make_result("b1", "BENIGN",                   True,  5, 5, 5, 5),
    ]
    card = build_scorecard("m", results)
    assert card.asr_enforced == 0.0
    assert card.asr_enforced_ci.lower == 0.0
    assert card.asr_enforced_ci.upper > 0.0  # finite upper bound


def test_scorecard_ci_tighter_with_more_trials():
    """More trials per scenario → narrower CI for the same observed rate."""
    def _card(n_trials):
        k = n_trials // 2  # always 50% success rate
        results = [_make_result("a1", "T2_unauthorized_transfer", False, n_trials, k, k, 0)]
        return build_scorecard("m", results)

    card_few  = _card(4)
    card_many = _card(40)
    assert card_many.asr_none_ci.width() < card_few.asr_none_ci.width()


def test_scorecard_no_attack_results():
    """All-benign results produce default CIs (no division by zero)."""
    results = [_make_result("b1", "BENIGN", True, 3, 3, 3, 3)]
    card = build_scorecard("m", results)
    assert card.n_attack == 0
    assert card.asr_none_ci == CI(0.0, 1.0)


# ---------------------------------------------------------------------------
# category_breakdown — per-category CIs
# ---------------------------------------------------------------------------

def test_category_ci_populated():
    """category_breakdown attaches CIs to each CategoryStat."""
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 3, 2, 1, 0),
        _make_result("a2", "T2_unauthorized_transfer", False, 3, 3, 0, 0),
        _make_result("b1", "BENIGN",                   True,  3, 3, 3, 3),
    ]
    cats = category_breakdown(results)
    assert len(cats) == 1
    cat = cats[0]
    assert isinstance(cat.asr_none_ci, CI)
    assert isinstance(cat.asr_advisory_ci, CI)
    assert isinstance(cat.asr_enforced_ci, CI)
    # Point estimate must be inside CI
    assert cat.asr_none_ci.lower <= cat.asr_none <= cat.asr_none_ci.upper


# ---------------------------------------------------------------------------
# render_markdown — CIs appear in output
# ---------------------------------------------------------------------------

def test_render_markdown_contains_ci_brackets():
    """Rendered markdown should contain Wilson CI notation."""
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 5, 3, 2, 0),
        _make_result("b1", "BENIGN",                   True,  5, 5, 5, 4),
    ]
    report = ModelReport("test-model", results)
    md = render_markdown([report], trials=5)
    assert "[" in md and "%" in md  # CI brackets present
    assert "Wilson CI" in md        # legend mentions Wilson


def test_render_markdown_ci_values_are_plausible():
    """CI lower < point estimate < CI upper in the rendered row."""
    # 4/5 successes → ASR none = 80%, CI roughly [44%, 96%]
    results = [
        _make_result("a1", "T2_unauthorized_transfer", False, 5, 4, 4, 0),
        _make_result("b1", "BENIGN",                   True,  5, 5, 5, 5),
    ]
    report = ModelReport("test-model", results)
    md = render_markdown([report], trials=5)
    row = next(line for line in md.splitlines() if "test-model" in line)
    # Row should contain the 80% point estimate and CI brackets
    assert "80%" in row
    assert "[" in row
