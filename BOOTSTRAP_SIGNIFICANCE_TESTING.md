# Bootstrap Significance Testing

## Overview

The bootstrap significance testing system provides rigorous statistical comparison of model performance on the FinAgent Red-Team leaderboard. It uses bootstrap resampling to compute p-values for pairwise model comparisons.

## Key Features

✅ **Checkpoint/Resume Support** — Results are cached incrementally. Pause and resume without recomputing.
✅ **Batch Processing** — Compare all model pairs across all postures in one command.
✅ **Deterministic** — Uses fixed random seeds for reproducible results.
✅ **Publication-Ready** — P-values and confidence intervals suitable for academic papers.

## What Gets Tested

For each pair of models, we compute:
- **ASR (Attack Success Rate)** at each posture: none, advisory, enforced
- **Utility** at each posture: how many benign tasks still work
- **Uplift metrics**: policy-following and enforcement effects

Output includes:
- Point estimate of difference
- P-value (two-tailed bootstrap test, α=0.05)
- 95% confidence interval on the difference
- Significance marker (***= significant)

## How It Works

### 1. Bootstrap Resampling

For each model, we extract all trial outcomes (pass/fail) and resample them with replacement:

```
Original outcomes: [0, 0, 1, 1, 0, 1, ...]  (60 trials)
Bootstrap resample 1: [1, 0, 1, 0, 1, 1, ...]  (60 trials, random selection)
Bootstrap resample 2: [0, 1, 0, 1, 1, 0, ...]  (60 trials, different selection)
...repeat 10,000 times
```

For each resample, we compute the success rate.

### 2. Pairwise Comparison

We compute the difference between models' bootstrap distributions:

```
Bootstrap diff 1: ASR_A(resample 1) - ASR_B(resample 1)
Bootstrap diff 2: ASR_A(resample 2) - ASR_B(resample 2)
...
```

The **p-value** is the proportion of bootstrap differences as extreme (or more) than the observed difference.

### 3. Confidence Interval

The 95% CI on the difference is computed via the bootstrap percentile method:
- Take the 2.5th and 97.5th percentiles of bootstrap differences

## Running Significance Tests

### Quick Start

```bash
python compute_significance.py results/2026-06-07_generated-p6_3trials.json
```

This will:
1. Load your leaderboard results (all models)
2. Generate all pairwise comparisons
3. Compute bootstrap tests (10,000 resamples each)
4. Cache results to `.significance_cache/significance_tests.json`
5. Print a summary table

### Resuming Interrupted Runs

If you pause the script mid-run:

```bash
python compute_significance.py results/2026-06-07_generated-p6_3trials.json
```

On restart, it will:
- Load cached results from `.significance_cache/significance_tests.json`
- Skip already-computed tests
- Continue from where it left off
- Show progress: `[150/392] CACHED:` vs `[150/392] ***`

### Output Format

```
[  1/392] ***                a vs                b (advisory): 
    diff=  -0.4321, p=0.0023, CI=[-0.6234,  -0.1456]

[  2/392]                    c vs                d (advisory): 
    diff=   0.0123, p=0.7891, CI=[-0.1234,   0.1456]
```

Legend:
- `***` = significant (p < 0.05)
- `   ` = not significant (p ≥ 0.05)

### Summary Table

After all tests complete, you get a ranked summary:

```
SIGNIFICANCE TEST SUMMARY (posture=advisory, alpha=0.05)
================================================================================
Model A              Model B              Difference   P-value   Significant
--------------------------------------------------------------------------------
gemini-2.0-flash     qwen3:8b                 -0.8300    0.0001    YES ***
claude-sonnet-4-6    mistral:7b               -0.1234    0.0456    YES ***
gemma2-9b-it         llama-3.1-8b             -0.0456    0.5634    no
```

## Customization

### Change Number of Resamples

In `compute_significance.py`, line 104:

```python
n_resamples=10000,  # Change to 5000 for faster runs, 50000 for more precision
```

### Add More Metrics

Currently tests ASR only. To add utility:

```python
metrics = ["asr", "utility"]  # Line 37 in compute_significance.py
```

Then run again — it will compute utility tests (cached ASR results skipped).

### Change Significance Level

In `compute_significance.py`, line 105:

```python
alpha=0.05,  # Change to 0.01 for stricter criterion
```

## API Usage

### In Python Code

```python
from finagent_redteam.eval.metrics import pairwise_significance

# Compare two models on advisory posture
result = pairwise_significance(
    results_model_a,
    results_model_b,
    posture="advisory",
    alpha=0.05,
    n_resamples=10000,
    benign=False,  # True for utility, False for ASR
    random_seed=42,
)

print(f"p-value: {result['p_value']}")
print(f"Significant: {result['significant']}")
print(f"Difference: {result['difference']}")
print(f"95% CI: [{result['ci_lower']}, {result['ci_upper']}]")
```

### Cache Management

```python
from finagent_redteam.eval.metrics import SignificanceCache
from pathlib import Path

cache = SignificanceCache(Path(".significance_cache/significance_tests.json"))

# Check if test is cached
result = cache.get("model_a", "model_b", "advisory", "asr")
if result:
    print(f"Cached p-value: {result.p_value}")

# Add new result
from finagent_redteam.eval.metrics import SignificanceResult
new_result = SignificanceResult(
    model_a="model_a", model_b="model_b",
    posture="advisory", metric="asr",
    p_value=0.05, significant=True,
    difference=0.1, ci_lower=0.05, ci_upper=0.15,
)
cache.put(new_result)

# Check cache size
print(f"Cached tests: {cache.size()}")
```

## For Paper Writing

### What to Report

In your results section:

> "We compared all 7 models pairwise on ASR at the advisory posture (Table X). 
> Gemini and Mistral both achieved 0% ASR and showed no significant difference 
> (p=0.98, 95% CI=[−0.02, 0.01]). Qwen was significantly more vulnerable 
> (83% ASR, p<0.001 vs Gemini)."

### Statistical Notation

Use bootstrap p-values in your tables:

| Model A | Model B | ASR Diff | p-value | Sig. |
|---------|---------|----------|---------|------|
| Gemini | Qwen | -0.83 | 0.001 | *** |
| Claude Sonnet | Gemini | 0.05 | 0.32 | |

## Troubleshooting

### "All tests are p=1.0"

This happens when models have 0% or 100% performance on every scenario. Bootstrap resampling of all-0s or all-1s data produces no variation. This is correct behavior but not useful statistically. It means the difference is *trivially* apparent (no resampling needed).

**Fix:** Ensure you have a mix of scenarios where models succeed and fail.

### "Cache file grows very large"

After ~10,000 tests, the cache JSON may reach 1–2 MB. This is normal. To clear:

```bash
rm .significance_cache/significance_tests.json
```

This will recompute all tests (useful if you change `n_resamples` or `alpha`).

### "Why different results on second run?"

If you don't set `random_seed`, results vary slightly across runs due to randomness in resampling. For reproducibility, always use `random_seed=42` (or consistent value).

## Testing

Run the test suite:

```bash
pytest tests/test_metrics_bootstrap.py -v
```

Tests cover:
- Bootstrap resampling correctness
- P-value computation
- Confidence interval calculation
- Cache persistence
- Checkpoint/resume functionality

## References

- **Wilson, E. B.** (1927). Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association.
- **Efron, B., Tibshirani, R. J.** (1993). An introduction to the bootstrap. Chapman & Hall/CRC.
- **Davison, A. C., Hinkley, D. V.** (1997). Bootstrap methods and their application. Cambridge University Press.

---

**Last updated:** 2026-06-09
