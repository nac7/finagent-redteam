# FinAgent Red-Team: Academic Paper

This directory contains the LaTeX source for the FinAgent Red-Team benchmark paper, ready for submission to top-tier venues (NeurIPS, SaTML, USENIX Security).

## Structure

```
paper/
├── main.tex                          # Main document (preamble + section orchestration)
├── references.bib                    # BibTeX bibliography (40+ citations)
├── sections/
│   ├── threats.tex                   # Threat taxonomy: T1–T7 categories with real-world impact
│   ├── methodology.tex               # Evaluation framework: 3 postures, metrics, statistical methods
│   ├── results.tex                   # Leaderboard: 7 models, per-threat breakdown, uplift analysis
│   ├── case_studies.tex              # 4 detailed case studies showing where models break
│   ├── appendix_scenarios.tex        # All 48 scenarios (42 attack + 6 benign)
│   ├── appendix_stats.tex            # Bootstrap significance testing, power analysis
│   └── appendix_tables.tex           # Full pairwise comparison table (63 tests)
└── README.md                         # This file
```

## Compilation

The paper uses the **NeurIPS 2026 workshop style**. The 2026 class **requires a
track option** plus a `\workshoptitle{}`; `main.tex` is already set for FLMSec:

```latex
\usepackage[sglblindworkshop, nonanonymous]{neurips_2026}
\workshoptitle{Foundations of Language Model Security (FLMSec)}
```

The official `neurips_2026.sty` is **not** vendored here — pull it from the NeurIPS
2026 formatting bundle and place it in this `paper/` directory first:

```bash
cd paper/
curl -L -o nrps.zip https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip
unzip -j nrps.zip 'neurips_2026.sty' -d . && rm nrps.zip
```

Then compile. Tectonic is the least-fuss route (auto-fetches packages, runs bibtex):

```bash
tectonic -X compile main.tex          # one command, produces main.pdf
```

Or the classic toolchain / Overleaf (upload the whole `paper/` folder incl. the `.sty`):

```bash
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Notes:
- For a **double-blind** venue, use `[sglblindworkshop]` (or `[dblblindworkshop]`)
  **without** `nonanonymous` — names are dropped automatically.
- The style loads `hyperref` itself; our explicit `\usepackage{hyperref}` coexists
  cleanly with Tectonic 0.17, but drop it if a classic run warns of an option clash.
- `\S` in `references.bib` must be brace-protected (`{\S}`) or the `plainnat` bst
  lowercases it to an undefined `\s`. Raw Unicode (×, ≈) is not in the Times fonts —
  use `$\times$` / `$\approx$`.
- **Page limit — met.** FLMSec allows **8 pp excluding references** (appendices,
  placed after the bibliography, are supplementary and outside the limit). The body
  now ends on p.8 (references begin on p.9); total PDF with appendices is 19 pp.
  The body carries Tables 1--4; all four figures and the full stats/scenario tables
  live in the appendix. If the body grows again, re-check with the page map before
  submitting.

## Content Summary

### Main Paper (8 pages)

1. **Title & Abstract**: Problem statement, contributions, 7 threat categories, 7 models, key results
2. **Introduction**: Motivation (silent compliance violations), contributions (threat taxonomy, 3-posture framework, deterministic evaluation)
3. **Threat Taxonomy** (§2): Table 1 with 7 categories (unauthorized transfer, sanctions evasion, structuring, dual-approval defeat, exfiltration, confused deputy, prompt injection)
4. **Methodology** (§3): 
   - Scenario design (deterministic evaluation, no LLM grading)
   - 3-posture framework (none/advisory/enforced)
   - Metrics (ASR, Wilson score CIs, uplift)
   - Bootstrap significance testing (10,000 resamples)
   - Experimental setup (7 models, 48 scenarios, 3 trials)
5. **Results** (§4):
   - Leaderboard: capability does not track safety — a frontier model (GPT-4o) reaches 71% no-policy ASR, while Claude Sonnet resists at 0%; stated policy leaves a 28–45% residual for weaker models; hard enforcement drives ASR to 0% for all seven
   - Per-threat breakdown
   - Utility/over-refusal analysis
   - Statistical significance (bootstrap tests)
6. **Case Studies** (§5): 4 examples showing where vulnerable models fail
7. **Related Work, Limitations, Responsible Disclosure, Open Source, Conclusion**

### Appendices (4+ pages)

- **Appendix A**: All 48 scenario details
- **Appendix B**: Statistical methods (Wilson intervals, bootstrap procedure, power analysis)
- **Appendix C**: Full pairwise comparison table (63 tests) + threat-specific results + uplift + utility breakdowns

## Submission Checklist

- [ ] Compile to PDF locally and verify formatting
- [ ] Check references against https://scholar.google.com/ (verify citations)
- [ ] Verify table references (`\ref{tab:...}`) are correct
- [ ] Check cross-references (`\ref{sec:...}`, `\ref{app:...}`)
- [ ] Ensure no overfull/underfull hbox warnings
- [ ] Verify appendix numbering and section references
- [ ] Add abstract keyword keywords (already included)
- [ ] Anonymize author information if required (for blind review venues)
- [ ] Create supplementary materials (code, data, benchmark)

## Citation Format

For use in your own papers:

```bibtex
@misc{lele2026finagent,
  title={FinAgent Red-Team: A Benchmark for Regulatory-Control Bypass in Financial LLM Agents},
  author={Lele, Nachiket},
  year={2026},
  howpublished={\url{https://github.com/nac7/finagent-redteam}},
  note={Software archived on Zenodo, DOI: 10.5281/zenodo.21855808}
}
```

Or in BibTeX:

```
Lele, N. FinAgent Red-Team: A Benchmark for Regulatory-Control Bypass in Financial LLM Agents. 2026.
```

## Key Metrics at a Glance

Seven models pass the integrity gate (zero API errors, real tool calls, non-zero
benign utility) and appear in the leaderboard. Numbers below are the reported
run (48 scenarios × 3 postures × 3 trials; the Groq-served Llama is single-trial).

| Model | ASR (Advisory) | Policy Uplift | Enforcement Uplift |
|-------|----------------|---------------|--------------------|
| Claude Sonnet 4.6 | 0% | +0% | +0% |
| Claude Haiku 4.5 | 1% | +29% | +1% |
| GPT-4o | 1% | +71% | +1% |
| Llama 3.1 8B (local) | 0% | +0% | +0% |
| Llama 3.1 8B (Groq) | 21% | +21% | +21% |
| GPT-4o-mini | 28% | +55% | +28% |
| Qwen 3 8B | 45% | +38% | +45% |

## Venue Recommendations

1. **FLMSec @ NeurIPS 2026** — Foundations of Language Model Security workshop; direct scope match (evaluation methodologies, attacks/defenses, security-utility trade-offs). Non-archival (compatible with a later archival submission). Deadline Aug 22, 2026.
2. **Who Verifies the Agents? @ NeurIPS 2026** — agent evaluation / environment-grounded verification; non-archival. Deadline Aug 29, 2026.
3. **NeurIPS Datasets & Benchmarks (2027 cycle)** — archival upgrade target once the suite is scaled up.
4. **SaTML** — Security and trustworthiness track; strong fit for the archival version.

## Publishing Timeline

- **Now**: Fix integrity items, trim to workshop page limit, submit current 7-model results to FLMSec (non-archival).
- **Fall 2026**: Fold in reviewer feedback; scale the suite (scenarios + uniform model coverage) toward the archival version.
- **2027**: Submit the scaled version to an archival Datasets & Benchmarks venue.

## Integration with Benchmark

The paper references code at `github.com/nac7/finagent-redteam`. Ensure:

1. ✅ Leaderboard results are final (7 models, 48 scenarios, 3 trials each)
2. ✅ Bootstrap significance cache is included (`.significance_cache/significance_tests.json`)
3. ✅ All scenario generation code is tested and deterministic
4. ✅ Agent runner supports all major API providers
5. ✅ README with quickstart guide

## Questions?

- For LaTeX issues: consult the preamble in `main.tex` (NeurIPS 2026 workshop style)
- For content: refer to individual section files (each section is self-contained)
- For bibliography: add to `references.bib` and cite with `\citep{}` or `\citet{}`

---

**Paper Status**: Complete draft (main + all appendices)
**Word Count**: ~4,500 (main paper) + ~1,500 (appendices) ≈ 6,000 total
**Figure/Table Count**: 7 tables, 0 figures (data-heavy, text-based)
**Ready for**: Submission to top venues
