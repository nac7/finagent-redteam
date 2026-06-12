#!/usr/bin/env python3
"""
Compute pairwise bootstrap significance tests for leaderboard models.

Supports checkpoint/resume: results are saved incrementally so you can pause
and resume without losing progress or recomputing tests.

Usage:
    python compute_significance.py results/2026-06-07_generated-p6_3trials.json
"""

import json
import sys
from pathlib import Path
from itertools import combinations

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finagent_redteam.eval.metrics import (
    pairwise_significance,
    SignificanceCache,
    SignificanceResult,
)


def load_results(results_file: Path):
    """Load results JSON and extract model data."""
    with open(results_file, "r") as f:
        data = json.load(f)

    # Parse scenario results for each model
    models_data = {}
    for model_entry in data.get("models", []):
        model_name = model_entry["model"]
        # Each model has a "scenarios" list with results
        models_data[model_name] = model_entry.get("scenarios", [])

    return models_data


def convert_scenario_to_result_obj(scenario_dict):
    """Convert scenario dict to result object with required attributes."""
    class ScenarioResult:
        def __init__(self, scenario_dict):
            self.scenario_id = scenario_dict.get("scenario_id", "")
            self.category = scenario_dict.get("category", "unknown")
            self.benign = scenario_dict.get("benign", False)
            self.n_trials = scenario_dict.get("n_trials", 3)

            # Extract successes from rate fields (rate * n_trials)
            # Results JSON stores rates, not raw counts
            self.successes_none = round(scenario_dict.get("rate_none", 0.0) * self.n_trials)
            self.successes_advisory = round(scenario_dict.get("rate_advisory", 0.0) * self.n_trials)
            self.successes_enforced = round(scenario_dict.get("rate_enforced", 0.0) * self.n_trials)

    return ScenarioResult(scenario_dict)


def main():
    results_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/2026-06-07_generated-p6_3trials.json")

    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}", file=sys.stderr)
        return 1

    print(f"Loading results from {results_file}...")
    models_data = load_results(results_file)
    model_names = list(models_data.keys())

    if len(model_names) < 2:
        print(f"Error: Need at least 2 models, found {len(model_names)}", file=sys.stderr)
        return 1

    print(f"Found {len(model_names)} models: {', '.join(model_names)}")
    print()

    # Initialize cache
    cache_dir = results_file.parent / ".significance_cache"
    cache_file = cache_dir / "significance_tests.json"
    cache = SignificanceCache(cache_file)
    print(f"Cache: {cache_file} ({cache.size()} cached results)")

    # Generate all pairwise comparisons
    postures = ["none", "advisory", "enforced"]
    metrics = ["asr"]  # We focus on ASR; utility can be added similarly

    all_pairs = list(combinations(sorted(model_names), 2))
    all_tests = []
    for model_a, model_b in all_pairs:
        for posture in postures:
            for metric in metrics:
                all_tests.append((model_a, model_b, posture, metric))

    print(f"Total tests to run: {len(all_tests)}")
    print(f"Already cached: {cache.size()}")
    print()

    # Run tests, skipping cached ones
    completed = 0
    skipped = 0

    for i, (model_a, model_b, posture, metric) in enumerate(all_tests, 1):
        # Check cache
        cached = cache.get(model_a, model_b, posture, metric)
        if cached:
            skipped += 1
            print(f"[{i:3d}/{len(all_tests)}] CACHED: {model_a} vs {model_b} ({posture}) — p={cached.p_value:.4f}")
            continue

        # Convert scenario results to result objects
        results_a = [
            convert_scenario_to_result_obj(s)
            for s in models_data[model_a]
        ]
        results_b = [
            convert_scenario_to_result_obj(s)
            for s in models_data[model_b]
        ]

        # Compute significance test
        test_result = pairwise_significance(
            results_a, results_b,
            posture=posture,
            alpha=0.05,
            n_resamples=10000,
            benign=(metric == "utility"),
            random_seed=42,  # For reproducibility
        )

        result = SignificanceResult(
            model_a=model_a,
            model_b=model_b,
            posture=posture,
            metric=metric,
            p_value=test_result["p_value"],
            significant=test_result["significant"],
            difference=test_result["difference"],
            ci_lower=test_result["ci_lower"],
            ci_upper=test_result["ci_upper"],
        )

        # Save to cache
        cache.put(result)
        completed += 1

        # Print result
        sig_marker = "***" if result.significant else "   "
        print(
            f"[{i:3d}/{len(all_tests)}] {sig_marker} {model_a:20s} vs {model_b:20s} "
            f"({posture:9s}): diff={result.difference:7.4f}, p={result.p_value:7.4f}, "
            f"CI=[{result.ci_lower:7.4f}, {result.ci_upper:7.4f}]"
        )

    print()
    print(f"Completed: {completed} new tests")
    print(f"Cached: {skipped} tests (reused)")
    print(f"Total cached: {cache.size()}")
    print(f"Results saved to: {cache_file}")

    # Generate summary table
    print("\n" + "=" * 80)
    print("SIGNIFICANCE TEST SUMMARY (posture=advisory, alpha=0.05)")
    print("=" * 80)

    # Get all advisory/asr results
    advisory_results = [
        r for r in cache.results.values()
        if r.posture == "advisory" and r.metric == "asr"
    ]

    if advisory_results:
        print(f"{'Model A':<20} {'Model B':<20} {'Difference':>12} {'P-value':>10} {'Significant':>12}")
        print("-" * 80)
        for r in sorted(advisory_results, key=lambda x: x.p_value):
            sig = "YES ***" if r.significant else "no"
            print(
                f"{r.model_a:<20} {r.model_b:<20} {r.difference:>12.4f} {r.p_value:>10.4f} {sig:>12}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
