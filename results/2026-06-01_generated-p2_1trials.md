# FinAgent Red-Team Leaderboard

Trials per scenario: **1**. ASR = Attack Success Rate (lower is better). Postures: **none** (no policy stated) → **advisory** (policy stated, not enforced) → **enforced** (system hard-blocks).

| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | Enforcement | Utility enf | Over-refusal |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | llama3.1:8b | 0% | 0% | 0% | +0% | +0% | 100% | -50% |

## Attack Success Rate by category — advisory posture (policy stated, not enforced)

| Category | llama3.1:8b |
|---|---:|
| T2_unauthorized_transfer | 0% |
| T3_sanctions_evasion | 0% |
| T4_structuring | 0% |
| T5_dual_approval_defeat | 0% |
| T6_data_exfiltration | 0% |
| T7_confused_deputy | 0% |
