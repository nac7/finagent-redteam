# FinAgent Red-Team Leaderboard

Trials per scenario: **3**. ASR = Attack Success Rate (lower is better). Postures: **none** (no policy stated) → **advisory** (policy stated, not enforced) → **enforced** (system hard-blocks). 95% Wilson CI shown in brackets.

| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | Enforcement | Utility enf | Over-refusal |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | llama3.1:8b | 0% [0%–3%] | 0% [0%–3%] | 0% [0%–3%] | +0% | +0% | 50% [29%–71%] | 50% |
| 2 | llama-3.1-8b-instant | 43% [29%–58%] | 21% [12%–36%] | 0% [0%–8%] | +21% | +21% | 100% [61%–100%] | 0% |
| 3 | qwen3:8b | 83% [76%–89%] | 45% [37%–54%] | 0% [0%–3%] | +38% | +45% | 100% [82%–100%] | 0% |

## Attack Success Rate by category — advisory posture (policy stated, not enforced)

| Category | qwen3:8b | llama3.1:8b | llama-3.1-8b-instant |
|---|---:|---:|---:|
| T2_unauthorized_transfer | 0% | 0% | 0% |
| T3_sanctions_evasion | 25% | 0% | 25% |
| T4_structuring | 83% | 0% | 17% |
| T5_dual_approval_defeat | 100% | 0% | 67% |
| T6_data_exfiltration | 56% | 0% | 17% |
| T7_confused_deputy | 28% | 0% | 0% |
