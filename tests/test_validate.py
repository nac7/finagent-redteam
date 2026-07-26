"""Tests for the result-integrity gate (finagent_redteam.validate).

These encode the exclusion principle that keeps invalid data out of the paper:
a model is valid only with 0 errors, non-zero benign utility, and both scenario
kinds present.
"""

from __future__ import annotations

from dataclasses import dataclass

from finagent_redteam.validate import (
    evaluate_validity,
    validate_model_dict,
    validate_model_report,
)


# --------------------------------------------------------------------------- #
# evaluate_validity — the core predicate
# --------------------------------------------------------------------------- #
def test_clean_model_is_valid():
    vr = evaluate_validity(
        "good", errors_total=0, n_attack=42, n_benign=6,
        utility_none=1.0, scenarios_no_data=0,
    )
    assert vr.valid
    assert vr.reasons == []
    assert vr.warnings == []


def test_all_errored_is_invalid():
    # The June-2026 failure: no key -> every trial errors -> bogus 0% ASR.
    vr = evaluate_validity(
        "claude-no-key", errors_total=144, n_attack=42, n_benign=6,
        utility_none=0.0, scenarios_no_data=48,
    )
    assert not vr.valid
    # Both the error taint and the incapacity signal should fire.
    assert any("error" in r.lower() for r in vr.reasons)
    assert any("utility" in r.lower() for r in vr.reasons)


def test_incapable_model_is_invalid_even_with_zero_errors():
    # mistral:7b case: runs cleanly but emits prose, never acts -> 0 utility.
    vr = evaluate_validity(
        "mistral:7b", errors_total=0, n_attack=42, n_benign=6,
        utility_none=0.0, scenarios_no_data=0,
    )
    assert not vr.valid
    assert any("incapacity" in r.lower() for r in vr.reasons)


def test_missing_benign_is_invalid():
    vr = evaluate_validity(
        "attack-only", errors_total=0, n_attack=42, n_benign=0,
        utility_none=None, scenarios_no_data=0,
    )
    assert not vr.valid
    assert any("benign" in r.lower() for r in vr.reasons)


def test_missing_attack_is_invalid():
    vr = evaluate_validity(
        "benign-only", errors_total=0, n_attack=0, n_benign=6,
        utility_none=1.0, scenarios_no_data=0,
    )
    assert not vr.valid
    assert any("attack" in r.lower() for r in vr.reasons)


def test_low_utility_is_valid_but_warned():
    # mistral-nemo case: can act but rarely completes -> admitted with a warning.
    vr = evaluate_validity(
        "mistral-nemo", errors_total=0, n_attack=42, n_benign=6,
        utility_none=0.06, scenarios_no_data=0,
    )
    assert vr.valid
    assert any("low benign utility" in w.lower() for w in vr.warnings)


def test_partial_errors_are_invalid():
    # Even a handful of errors taint the run (they deflate ASR silently).
    vr = evaluate_validity(
        "flaky", errors_total=9, n_attack=42, n_benign=6,
        utility_none=1.0, scenarios_no_data=0,
    )
    assert not vr.valid


# --------------------------------------------------------------------------- #
# validate_model_report — live ModelReport adapter
# --------------------------------------------------------------------------- #
@dataclass
class _FakeResult:
    benign: bool
    errors: int
    valid_trials: int


class _FakeScorecard:
    def __init__(self, utility_none):
        self.utility_none = utility_none


class _FakeReport:
    def __init__(self, model, results, utility_none):
        self.model = model
        self.results = results
        self._u = utility_none

    def scorecard(self):
        return _FakeScorecard(self._u)


def test_validate_model_report_clean():
    results = [_FakeResult(False, 0, 3) for _ in range(42)] + [
        _FakeResult(True, 0, 3) for _ in range(6)
    ]
    vr = validate_model_report(_FakeReport("m", results, 1.0))
    assert vr.valid
    assert vr.n_attack == 42 and vr.n_benign == 6


def test_validate_model_report_all_errored():
    results = [_FakeResult(False, 3, 0) for _ in range(42)] + [
        _FakeResult(True, 3, 0) for _ in range(6)
    ]
    vr = validate_model_report(_FakeReport("m", results, 0.0))
    assert not vr.valid
    assert vr.errors_total == 144
    assert vr.scenarios_no_data == 48


# --------------------------------------------------------------------------- #
# validate_model_dict — results-file JSON adapter
# --------------------------------------------------------------------------- #
def _dict_entry(model, utility_none, *, benign_errors=0, attack_errors=0, n_trials=3):
    scenarios = []
    for _ in range(42):
        scenarios.append({
            "benign": False, "n_trials": n_trials, "errors": attack_errors,
            "valid_trials": max(n_trials - attack_errors, 0),
        })
    for _ in range(6):
        scenarios.append({
            "benign": True, "n_trials": n_trials, "errors": benign_errors,
            "valid_trials": max(n_trials - benign_errors, 0),
        })
    return {"model": model, "scorecard": {"utility_none": utility_none},
            "scenarios": scenarios}


def test_validate_model_dict_clean():
    vr = validate_model_dict(_dict_entry("good", 1.0))
    assert vr.valid


def test_validate_model_dict_keyless_artifact():
    # Mirrors the polluted 2026-06-07 rows: every scenario errored, utility 0.
    vr = validate_model_dict(
        _dict_entry("claude-sonnet-4-6", 0.0, benign_errors=3, attack_errors=3)
    )
    assert not vr.valid
    assert vr.errors_total == 144
