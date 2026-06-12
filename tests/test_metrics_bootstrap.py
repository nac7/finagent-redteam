"""Tests for bootstrap significance testing."""

import json
import tempfile
from pathlib import Path

import pytest

from finagent_redteam.eval.metrics import (
    bootstrap_resample,
    pairwise_significance,
    SignificanceCache,
    SignificanceResult,
)


class MockResult:
    """Mock scenario result for testing."""

    def __init__(self, benign=False, successes_none=0, successes_advisory=0,
                 successes_enforced=0, n_trials=3, category="test"):
        self.benign = benign
        self.successes_none = successes_none
        self.successes_advisory = successes_advisory
        self.successes_enforced = successes_enforced
        self.n_trials = n_trials
        self.category = category


def test_bootstrap_resample_all_zeros():
    """Bootstrap from all zeros should return all zeros."""
    outcomes = [0, 0, 0, 0, 0]
    stats = bootstrap_resample(outcomes, n_resamples=100, random_seed=42)
    assert all(s == 0.0 for s in stats)


def test_bootstrap_resample_all_ones():
    """Bootstrap from all ones should return all ones."""
    outcomes = [1, 1, 1, 1, 1]
    stats = bootstrap_resample(outcomes, n_resamples=100, random_seed=42)
    assert all(s == 1.0 for s in stats)


def test_bootstrap_resample_mixed():
    """Bootstrap from mixed outcomes should produce distribution."""
    outcomes = [0, 0, 0, 1, 1]  # 40% success rate
    stats = bootstrap_resample(outcomes, n_resamples=1000, random_seed=42)
    assert len(stats) == 1000
    assert all(0.0 <= s <= 1.0 for s in stats)
    # Mean should be close to 0.4
    mean_stat = sum(stats) / len(stats)
    assert 0.3 < mean_stat < 0.5


def test_bootstrap_resample_reproducibility():
    """Same seed should produce same results."""
    outcomes = [0, 1, 0, 1, 1]
    stats1 = bootstrap_resample(outcomes, n_resamples=100, random_seed=42)
    stats2 = bootstrap_resample(outcomes, n_resamples=100, random_seed=42)
    assert stats1 == stats2


def test_pairwise_significance_identical_results():
    """Identical models should have p-value close to 1.0."""
    # Both models: 50% success rate
    results_a = [
        MockResult(benign=False, successes_advisory=1, n_trials=3)  # 33% success
        for _ in range(6)
    ]
    results_b = [
        MockResult(benign=False, successes_advisory=1, n_trials=3)  # 33% success
        for _ in range(6)
    ]

    result = pairwise_significance(
        results_a, results_b, posture="advisory",
        n_resamples=1000, random_seed=42
    )

    assert result["p_value"] == 1.0 or result["p_value"] > 0.05
    assert not result["significant"]
    assert abs(result["difference"]) < 0.01


def test_pairwise_significance_different_results():
    """Substantially different models show large effect sizes."""
    # Model A: 0% success rate
    results_a = [
        MockResult(benign=False, successes_advisory=0, n_trials=3)
        for _ in range(42)
    ]
    # Model B: 100% success rate
    results_b = [
        MockResult(benign=False, successes_advisory=3, n_trials=3)
        for _ in range(42)
    ]

    result = pairwise_significance(
        results_a, results_b, posture="advisory",
        n_resamples=1000, random_seed=42
    )

    # Difference should be -100% (model A is 0%, model B is 100%)
    assert result["difference"] == -1.0
    # CI should reflect the complete separation
    assert result["ci_lower"] == -1.0
    assert result["ci_upper"] == -1.0


def test_pairwise_significance_ci_contains_difference():
    """CI should contain the observed difference."""
    results_a = [
        MockResult(benign=False, successes_advisory=0, n_trials=3)
        for _ in range(3)
    ]
    results_b = [
        MockResult(benign=False, successes_advisory=3, n_trials=3)
        for _ in range(3)
    ]

    result = pairwise_significance(
        results_a, results_b, posture="advisory",
        n_resamples=1000, random_seed=42
    )

    # CI should contain (roughly) the observed difference
    assert result["ci_lower"] <= result["difference"] <= result["ci_upper"]


def test_significance_cache_store_and_retrieve():
    """Cache should store and retrieve results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "cache.json"
        cache = SignificanceCache(cache_file)

        result = SignificanceResult(
            model_a="model_a",
            model_b="model_b",
            posture="advisory",
            metric="asr",
            p_value=0.05,
            significant=True,
            difference=0.1,
            ci_lower=0.05,
            ci_upper=0.15,
        )

        cache.put(result)
        assert cache.size() == 1

        # Retrieve
        retrieved = cache.get("model_a", "model_b", "advisory", "asr")
        assert retrieved is not None
        assert retrieved.p_value == 0.05
        assert retrieved.significant


def test_significance_cache_persistence():
    """Cache should persist across instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "cache.json"

        # Create and populate cache
        cache1 = SignificanceCache(cache_file)
        result = SignificanceResult(
            model_a="a", model_b="b", posture="advisory", metric="asr",
            p_value=0.03, significant=True,
            difference=0.2, ci_lower=0.1, ci_upper=0.3,
        )
        cache1.put(result)

        # Create new instance and verify it loads
        cache2 = SignificanceCache(cache_file)
        assert cache2.size() == 1
        retrieved = cache2.get("a", "b", "advisory", "asr")
        assert retrieved is not None
        assert retrieved.p_value == 0.03


def test_significance_cache_multiple_results():
    """Cache should handle multiple results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "cache.json"
        cache = SignificanceCache(cache_file)

        # Store multiple results
        for i in range(5):
            result = SignificanceResult(
                model_a=f"model_a",
                model_b=f"model_{i}",
                posture="advisory",
                metric="asr",
                p_value=0.01 * i,
                significant=i < 3,
                difference=0.1 * i,
                ci_lower=0.0,
                ci_upper=0.2,
            )
            cache.put(result)

        assert cache.size() == 5

        # Verify all are retrievable
        for i in range(5):
            retrieved = cache.get("model_a", f"model_{i}", "advisory", "asr")
            assert retrieved is not None
            assert retrieved.p_value == 0.01 * i


def test_pairwise_significance_utility():
    """Pairwise test should work for utility metrics."""
    # Benign results (utility metric)
    results_a = [
        MockResult(benign=True, successes_advisory=0, n_trials=3)
        for _ in range(3)
    ]
    results_b = [
        MockResult(benign=True, successes_advisory=3, n_trials=3)
        for _ in range(3)
    ]

    result = pairwise_significance(
        results_a, results_b, posture="advisory",
        n_resamples=500, benign=True, random_seed=42
    )

    assert isinstance(result, dict)
    assert "p_value" in result
    assert "significant" in result
