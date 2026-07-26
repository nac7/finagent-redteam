# FinAgent Red-Team: Results Summary

**Last updated:** 2026-07-26
**Benchmark:** 48 scenarios (42 attack + 6 benign) × 3 postures × 7 models.
Trials/scenario: **3** for all models except `llama-3.1-8b-instant` (**1**, Groq quota) — see mixed-trials caveat.

**Canonical data source:** `results/leaderboard_final.json`
**Rebuild:** `python build_leaderboard.py` (validated merge of the three source runs below; see the script header for the exact command)

| Source run | Models contributed |
|---|---|
| `results/2026-07-25_generated-p6_3trials.json` | claude-sonnet-4-6, claude-haiku-4-5 |
| `results/_openai/2026-07-25_generated-p6_3trials.json` | gpt-4o, gpt-4o-mini |
| `results/2026-06-20_generated-p6_3trials.json` | qwen3:8b, llama3.1:8b, llama-3.1-8b-instant |

---

## Leaderboard (7 validated models)

Ranked by ASR at **advisory** posture (policy stated but not enforced), then by ASR at **none**.
95% Wilson CIs in brackets. Lower ASR is better; higher utility is better.

| Rank | Model | Trials | ASR None | ASR Advisory | ASR Enforced | Policy Uplift | Enf. Uplift | Utility (enf) | Over-refusal |
|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-sonnet-4-6 | 3 | 0% [0–3%] | 0% [0–3%] | 0% [0–3%] | +0% | +0% | 100% [82–100%] | 0% |
| 2 | llama3.1:8b (local) | 3 | 0% [0–3%] | 0% [0–3%] | 0% [0–3%] | +0% | +0% | 50% [29–71%] | 50% |
| 3 | claude-haiku-4-5 | 3 | 30% [23–39%] | 1% [0–4%] | 0% [0–3%] | +29% | +1% | 100% [82–100%] | 0% |
| 4 | gpt-4o | 3 | 71% [63–79%] | 1% [0–4%] | 0% [0–3%] | +71% | +1% | 100% [82–100%] | 0% |
| 5 | llama-3.1-8b-instant (Groq) | 1 | 43% [29–58%] | 21% [12–36%] | 0% [0–8%] | +21% | +21% | 100% [61–100%] | 0% |
| 6 | gpt-4o-mini | 3 | 83% [75–88%] | 28% [21–36%] | 0% [0–3%] | +55% | +28% | 100% [82–100%] | 0% |
| 7 | qwen3:8b (local) | 3 | 83% [76–89%] | 45% [37–54%] | 0% [0–3%] | +38% | +45% | 100% [82–100%] | 0% |

### Headline findings

- **Enforcement is universal; advisory policy is not.** Every model reaches **0% ASR at enforced** posture, but advisory ASR spans 0%–45%. Hard controls work regardless of model; stated policy is only as good as the model reading it.
- **Intrinsic susceptibility is high even in frontier models.** With no policy stated, gpt-4o attacks succeed **71%** of the time and gpt-4o-mini **83%** — these are not weak models failing, they are capable models with no reason to refuse.
- **Policy-following ability is the real differentiator.** gpt-4o converts a 71% intrinsic ASR into 1% residual when policy is merely *stated* (+71 uplift, the largest measured). gpt-4o-mini, from a nearly identical starting point (83%), only reaches 28% (+55). Same family, same prompt — the smaller model cannot act on the policy it was given.
- **claude-sonnet-4-6 is the only model that is both fully robust and fully useful** (0% ASR at every posture, 100% utility, 0% over-refusal).
- **Two paths to 0% ASR, only one of them good.** llama3.1:8b also scores 0% everywhere, but at **50% over-refusal** — see the caveat below. Sonnet's 0% is refusal-with-competence; the local llama's is largely non-action.
- **T5 (dual-approval defeat) is the hardest category**, and stated policy can make it *worse*: gpt-4o-mini goes from 78% (none) to **100% (advisory)**, and qwen3:8b from 94% to **100%**. Naming the control appears to hand the model the vocabulary for circumventing it.

---

## Per-Threat Breakdown — advisory posture (policy stated, not enforced)

| Threat Category | sonnet-4-6 | llama3.1:8b | haiku-4-5 | gpt-4o | 8b-instant | gpt-4o-mini | qwen3:8b |
|---|---|---|---|---|---|---|---|
| T2: Unauthorized Transfer | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| T3: Sanctions Evasion | 0% | 0% | 3% | 0% | 25% | 0% | 25% |
| T4: Payment Structuring | 0% | 0% | 0% | 0% | 17% | 94% | 83% |
| T5: Dual-Approval Defeat | 0% | 0% | 0% | 6% | 67% | 100% | 100% |
| T6: Data Exfiltration | 0% | 0% | 0% | 0% | 17% | 0% | 56% |
| T7: Confused Deputy | 0% | 0% | 0% | 0% | 0% | 0% | 28% |

**T2 (unauthorized transfer) is 0% for every model at every posture** — a direct "move money to this account" instruction embedded in tool output is refused universally. The attacks that land are the ones that route around a control (T4, T5) rather than violating an obvious prohibition.

### Full posture breakdown, per model

**claude-sonnet-4-6** — 0% at every category and posture. Omitted for brevity.
**llama3.1:8b (local)** — 0% at every category and posture. See over-refusal caveat.

| Threat Category | haiku-4-5 none → adv | gpt-4o none → adv | gpt-4o-mini none → adv | 8b-instant none → adv | qwen3:8b none → adv |
|---|---|---|---|---|---|
| T2: Unauthorized Transfer | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% |
| T3: Sanctions Evasion | 22% → 3% | 100% → 0% | 100% → 0% | 50% → 25% | 97% → 25% |
| T4: Payment Structuring | 39% → 0% | 100% → 0% | 100% → 94% | 33% → 17% | 94% → 83% |
| T5: Dual-Approval Defeat | 100% → 0% | 100% → 6% | 78% → **100%** | 50% → **67%** | 94% → **100%** |
| T6: Data Exfiltration | 0% → 0% | 0% → 0% | 100% → 0% | 83% → 17% | 100% → 56% |
| T7: Confused Deputy | 28% → 0% | 100% → 0% | 100% → 0% | 33% → 0% | 100% → 28% |

All models are 0% at enforced posture in every category, so the enforced column is omitted.
Bold marks categories where stating the policy **increased** ASR.

---

## Caveats

> **Exclusion principle.** A model appears in the leaderboard only if it (a) completes all 48 scenarios with 0 API errors, (b) emits real structured tool calls, and (c) completes legitimate tasks (non-trivial benign utility). Models scoring 0% ASR *because* they cannot act are excluded — that is incapacity, not security.

> **Excluded / invalid runs.** mistral:7b (no structured `tool_calls`, 0% utility) and mistral-nemo (~6% utility, cannot chain multi-step workflows) fail criterion (b)/(c). The Gemma family fails criterion (b) outright (Ollama HTTP 400, "does not support tools"). The 2026-06-07 run was executed with **no API keys set**: all of its non-local rows are 100% API errors and its 0% ASRs are artifacts. That run is superseded and **must not be cited**; the raw file is retained locally under `.archive/` and is not published.

> **Mixed-trials caveat.** `llama-3.1-8b-instant` is 1 trial/scenario (Groq daily quota); all other models are 3. Wilson CIs account for the smaller sample — note its visibly wider intervals — so the numbers are not misrepresented, but that row rests on less data. A 3-trial re-run is the remaining item for a uniform table.

> **Deployment-divergence finding.** The *same* Llama 3.1 8B scores **43% ASR (none) on Groq vs 0% locally (Ollama)**. Identical weights, different serving stack → materially different susceptibility. This is a citable observation about deployment-dependent safety; the two are kept as distinct rows and must not be conflated.

> **Interpretation caveat (llama3.1:8b local).** Its 0% ASR is paired with **50% over-refusal / 50% enforced utility**. Transcript inspection showed it typically makes a single `read_inbox` call and stops rather than chaining to the malicious follow-up. Frame as *"achieves 0% ASR largely by not executing inbox-triggered multi-step actions"* — not as principled refusal. It is genuinely capable (100% utility under *none*), so this is real behaviour, not an incapacity artifact.

---

## Figures

`paper/figures/fig1`–`fig4` are generated from `results/leaderboard_final.json`:

```bash
python generate_figures.py                      # defaults to results/leaderboard_final.json
python generate_figures.py <other-results.json> # explicit override
```

---

## Optional / deferred

| Item | Status |
|---|---|
| `llama-3.1-8b-instant` at 3 trials | Deferred — currently 1 trial; needed for a uniform table |
| `llama-3.3-70b-versatile` | Partial (27/48, 19 errored) — Groq quota; resume + retry pass |
| `llama-4-scout-17b` | Not started — Groq quota |
| `gemini-2.0-flash` | Not run — key format unverified |
