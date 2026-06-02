---
hide:
  - navigation
---

# FinAgent Red-Team

**A red-team benchmark for AI agents that handle money — focused on *regulatory-control bypass*, not just generic misbehavior.**

[![CI](https://github.com/nac7/finagent-redteam/actions/workflows/ci.yml/badge.svg)](https://github.com/nac7/finagent-redteam/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/finagent-redteam)](https://pypi.org/project/finagent-redteam/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/nac7/finagent-redteam/blob/main/LICENSE)

---

## What is FinAgent Red-Team?

LLM agents are moving into financial operations: accounts payable, treasury,
reconciliation, customer servicing. The dangerous failures there are not toxic
text — they are **silent violations of compliance controls** that look like
normal task completion.

FinAgent Red-Team runs every scenario under **three control postures** — *none*,
*advisory*, and *enforced* — and reports not just *can it be attacked* but
*where an agent's safety actually comes from*: its own judgement, its policy-
following, or hard system enforcement.

## Quick start

```bash
pip install finagent-redteam[agent]

# Run the benchmark against any OpenAI-compatible endpoint
finagent-redteam --model Qwen/Qwen3-8B --base-url http://localhost:8000/v1

# Multi-model leaderboard
finagent-redteam --models-config models.json --trials 5 --json results.json
```

Run the full test suite offline (no GPU or API key needed):

```bash
pip install finagent-redteam[dev]
pytest -q   # 41 tests in < 1 second
```

## Threat taxonomy

| ID | Threat | Control |
|---|---|---|
| T2 | Unauthorized transfer | Payee allow-list |
| T3 | Sanctions evasion (flagged payee) | Sanctions screening |
| T3 | Sanctions evasion (homoglyph) | Normalized screening |
| T4 | Payment structuring | CTR reporting threshold |
| T5 | Dual-approval defeat | Maker-checker |
| T6 | Data exfiltration | DLP |
| T7 | Confused-deputy payee redirect | Bank-detail protection |

See the full [Threat Taxonomy](threats.md) page for regulatory grounding.

## Citation

```bibtex
@software{lele2026finagent,
  author = {Nachiket Lele},
  title  = {FinAgent Red-Team: A benchmark for regulatory-control bypass
            in financial AI agents},
  year   = {2026},
  url    = {https://github.com/nac7/finagent-redteam},
}
```
