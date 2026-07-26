# FinAgent Red-Team Leaderboard

Trials per scenario: **3**. ASR = Attack Success Rate (lower is better). Postures: **none** (no policy stated) → **advisory** (policy stated, not enforced) → **enforced** (system hard-blocks). 95% Wilson CI shown in brackets.

| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | Enforcement | Utility enf | Over-refusal |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | gpt-4o | 71% [63%–79%] | 1% [0%–4%] | 0% [0%–3%] | +71% | +1% | 100% [82%–100%] | 0% |
| 2 | gpt-4o-mini | 83% [75%–88%] | 28% [21%–36%] | 0% [0%–3%] | +55% | +28% | 100% [82%–100%] | 0% |

## Attack Success Rate by category — advisory posture (policy stated, not enforced)

| Category | gpt-4o-mini | gpt-4o |
|---|---:|---:|
| T2_unauthorized_transfer | 0% | 0% |
| T3_sanctions_evasion | 0% | 0% |
| T4_structuring | 94% | 0% |
| T5_dual_approval_defeat | 100% | 6% |
| T6_data_exfiltration | 0% | 0% |
| T7_confused_deputy | 0% | 0% |
