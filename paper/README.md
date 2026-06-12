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

To compile the paper to PDF:

```bash
cd paper/
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Or use your preferred LaTeX editor (Overleaf, TeXShop, MikTeX, TeX Live).

Expected output:
- `main.pdf` (~10 pages main + appendix)

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
   - Leaderboard: Frontier models (Claude, Gemini, Mistral) achieve 0% ASR; open-source models 22–83%
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
@article{lele2026finagent,
  title={FinAgent Red-Team: A Benchmark for Regulatory-Control Bypass in Financial LLM Agents},
  author={Lele, Nachiket},
  journal={arXiv preprint},
  year={2026}
}
```

Or in BibTeX:

```
Lele, N. FinAgent Red-Team: A Benchmark for Regulatory-Control Bypass in Financial LLM Agents. 2026.
```

## Key Metrics at a Glance

| Model | ASR (Advisory) | Policy Uplift | Enforcement Uplift |
|-------|----------------|---------------|--------------------|
| Claude Sonnet 4.6 | 0% | 0% | 0% |
| Gemini 2.0 Flash | 0% | 0% | 0% |
| Mistral 7B | 0% | 0% | 0% |
| Qwen 3 8B | 45% | +38% | +45% |
| Llama 3.1 8B | 22% | +36% | +22% |
| Gemma 2 9B | 31% | +33% | +31% |

## Venue Recommendations

1. **NeurIPS 2024/2025** — Top-tier ML venue; bench papers often accepted
2. **SaTML 2025** — Security and trustworthiness track; perfect fit
3. **USENIX Security 2025** — Security focus; benchmarks valued
4. **ACL 2025** — NLP track; language safety in focus
5. **arXiv** — Pre-print for immediate visibility and community feedback

## Publishing Timeline

- **Month 1**: Polish paper, add detailed results tables, get feedback
- **Month 2**: Prepare for arXiv upload (no review required, immediate dissemination)
- **Month 3**: Submit to SaTML 2025 (December deadline)
- **Month 4**: Submit to USENIX Security 2025 (January deadline)
- **Month 6**: Present at conferences if accepted

## Integration with Benchmark

The paper references code at `github.com/nac7/finagent-redteam`. Ensure:

1. ✅ Leaderboard results are final (7 models, 48 scenarios, 3 trials each)
2. ✅ Bootstrap significance cache is included (`.significance_cache/significance_tests.json`)
3. ✅ All scenario generation code is tested and deterministic
4. ✅ Agent runner supports all major API providers
5. ✅ README with quickstart guide

## Questions?

- For LaTeX issues: consult the preamble in `main.tex` (standard article class)
- For content: refer to individual section files (each section is self-contained)
- For bibliography: add to `references.bib` and cite with `\citep{}` or `\citet{}`

---

**Paper Status**: Complete draft (main + all appendices)
**Word Count**: ~4,500 (main paper) + ~1,500 (appendices) ≈ 6,000 total
**Figure/Table Count**: 7 tables, 0 figures (data-heavy, text-based)
**Ready for**: Submission to top venues
