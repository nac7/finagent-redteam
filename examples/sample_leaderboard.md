> **Illustrative sample** — synthetic numbers showing the output format, NOT real model results. Regenerate with real models via `finagent-redteam --models-config examples/models.example.json --trials 5`.

# FinAgent Red-Team Leaderboard

Trials per scenario: **5**. ASR = Attack Success Rate (lower is better). Postures: **none** (no policy stated) → **advisory** (policy stated, not enforced) → **enforced** (system hard-blocks).

| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | Enforcement | Utility enf | Over-refusal |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | frontier-model-A | 54% | 23% | 0% | +31% | +23% | 100% | 0% |
| 2 | open-model-B | 97% | 89% | 0% | +9% | +89% | 80% | 20% |

## Attack Success Rate by category — advisory posture (policy stated, not enforced)

| Category | frontier-model-A | open-model-B |
|---|---:|---:|
| T2_unauthorized_transfer | 20% | 100% |
| T3_sanctions_evasion | 30% | 90% |
| T4_structuring | 20% | 80% |
| T5_dual_approval_defeat | 20% | 100% |
| T6_data_exfiltration | 0% | 60% |
| T7_confused_deputy | 40% | 100% |
