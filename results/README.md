# Results

This directory contains leaderboard results from benchmark runs.
Each file is a timestamped JSON produced by the CLI.

## File naming convention

```
results/<date>_<suite>_<trials>trials.json
# e.g.
results/2026-06-15_generated-p6_5trials.json
```

## JSON schema (top-level)

```jsonc
{
  "metadata": {
    "date": "2026-06-15",
    "suite": "generated",
    "per_threat": 6,
    "trials": 5,
    "seed": 0,
    "temperature": 0.7,
    "finagent_version": "0.2.0"
  },
  "models": [
    {
      "model": "gpt-4o",
      "scorecard": { ... },   // see Scorecard fields below
      "categories": [ ... ],  // per CategoryStat
      "scenarios": [ ... ]    // per ScenarioTrialResult
    }
  ]
}
```

### Scorecard fields

| Field | Description |
|---|---|
| `asr_none` | ASR with no policy stated (intrinsic susceptibility) |
| `asr_advisory` | ASR with policy stated but not enforced |
| `asr_enforced` | ASR with system hard-blocks (residual risk) |
| `utility_none` / `utility_advisory` / `utility_enforced` | Benign task completion |
| `policy_following_uplift` | `asr_none − asr_advisory` |
| `enforcement_uplift` | `asr_advisory − asr_enforced` |
| `residual_asr` | `asr_enforced` |
| `over_refusal` | `utility_none − utility_enforced` |

## Reproducibility requirements

Any result file committed to this directory must include:

- Model name **and** snapshot/version (e.g. `gpt-4o-2026-05-13`)
- API or Ollama endpoint URL
- Temperature and seed
- Number of trials (minimum 5 for publishable results)
- `finagent_redteam` package version
- Date of run

## Submitting your results

1. Run the benchmark and save JSON output:
   ```bash
   finagent-redteam \
     --models-config models/paper_full.json \
     --suite generated --per-threat 6 --seed 0 \
     --trials 5 --temperature 0.7 \
     --checkpoint-dir checkpoints/ \
     --json results/2026-06-15_generated-p6_5trials.json
   ```
2. Open a pull request adding your results JSON to this directory.
3. The PR description must include the model version/snapshot date, API, and
   the `pytest -q` output showing 41 tests passing on the same code version.
