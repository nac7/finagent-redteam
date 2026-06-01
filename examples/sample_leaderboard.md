> **Illustrative sample** — synthetic numbers showing the output format, NOT real model results. Regenerate with real models via `finagent-redteam --models-config examples/models.example.json --trials 5`.

# FinAgent Red-Team Leaderboard

Trials per scenario: **5**. Lower ASR and higher utility are better.

| Rank | Model | ASR off | ASR on | Defense efficacy | Utility on | Over-refusal |
|---|---|---:|---:|---:|---:|---:|
| 1 | frontier-model-A | 23% | 0% | +23% | 100% | 0% |
| 2 | open-model-B | 89% | 0% | +89% | 80% | 20% |

## Attack Success Rate by category (guardrails ON)

| Category | frontier-model-A | open-model-B |
|---|---:|---:|
| T2_unauthorized_transfer | 0% | 0% |
| T3_sanctions_evasion | 0% | 0% |
| T4_structuring | 0% | 0% |
| T5_dual_approval_defeat | 0% | 0% |
| T6_data_exfiltration | 0% | 0% |
| T7_confused_deputy | 0% | 0% |
