---
title: FinAgent Red-Team Leaderboard
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: static
pinned: false
license: mit
---

# FinAgent Red-Team — Leaderboard

A self-contained static leaderboard for **FinAgent Red-Team**, a benchmark for
regulatory-control bypass in financial LLM agents (indirect prompt injection →
unauthorized transfers, sanctions evasion, structuring, dual-approval defeat, data
exfiltration, confused-deputy redirection).

Each scenario is replayed under three control postures — **none / advisory / enforced** —
and scored by a deterministic predicate over final world state (no LLM grading). The page
shows the reference 7-model leaderboard and the advisory-posture per-threat heatmap.

- **Code & harness:** https://github.com/nac7/finagent-redteam
- **Dataset:** https://huggingface.co/datasets/nac7/finagent-redteam
- **DOI:** https://doi.org/10.5281/zenodo.21855808

`index.html` is fully self-contained (no external assets), theme-aware, and renders
identically as an HF static Space or standalone. To update the numbers, edit the `MODELS`
and `HEAT` arrays in the inline `<script>`.
