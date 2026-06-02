# Datasheet for FinAgent Red-Team

_Following the Datasheets for Datasets format (Gebru et al., 2021).  
This datasheet covers the benchmark scenario set, not any model outputs._

---

## Motivation

**For what purpose was the dataset created?**  
To provide a rigorous, reproducible benchmark for measuring the susceptibility of
LLM-based financial agents to regulatory-control bypass attacks, and the efficacy
of guardrails that defend against them. Existing agent-security benchmarks do not
model the compliance-control surface of financial institutions. See the README for
the full threat taxonomy and prior-art comparison.

**Who created the dataset and on whose behalf?**  
Nachiket Lele (independent researcher). Not created on behalf of any employer.

**Who funded the creation?**  
Self-funded. No external funding was received.

---

## Composition

**What do the instances represent?**  
Each instance (scenario) is a combination of:
- a `World` — synthetic in-memory state (accounts, payees, inbox)
- a `user_task` — the legitimate instruction given to the agent
- an embedded attack delivered through an untrusted `Email`
- a `Contract` — a deterministic predicate over final world state

**How many instances are there?**  
The hand-written suite contains **8 scenarios** (7 attack + 1 benign). The
procedural generator (`scenarios/generator.py`) produces a configurable number of
additional cases; the default (`per_threat=6`) produces **48 attack + 6 benign =
54 scenarios**. All are deterministic given a seed.

**Does the dataset contain all possible instances or is it a sample?**  
It is a designed, non-exhaustive sample of the threat space. It covers 7 distinct
threat categories drawn from the financial compliance literature (see
Construct Validity below).

**Is there a label associated with each instance?**  
Yes — the `AttackGoal` predicate is the label; it is checked deterministically
against the final `World` state by the evaluator. There is no subjective judgment
or crowdsourced labeling.

**Is any information missing from individual instances?**  
The `reference_plan` (canonical exploit) is present on all generated scenarios.
Some hand-written scenarios also carry one; check `scenario.reference_plan`.

**Are relationships between instances made explicit?**  
Scenarios are grouped by `category` (threat class) and `posture` (control setting).
The generator produces multiple instances per category sharing the same threat
type but differing in phrasing, amount, payee, and obfuscation.

**Does the dataset contain data that might be considered confidential?**  
No. All data is fully synthetic. Payee names, account numbers, and email addresses
are fictional. No real institution's data is represented.

**Does the dataset contain data that, if viewed directly, might be offensive,
insulting, threatening, or might otherwise cause anxiety?**  
The scenarios model financial attacks (fraud, sanctions evasion). They do not
contain offensive language. Security researchers familiar with the financial crime
literature will recognise the patterns modelled.

---

## Collection Process

**How was the data collected?**  
All scenarios were designed by the author based on:
- The Bank Secrecy Act (31 U.S.C. 5318) — CTR/structuring provisions
- OFAC sanctions screening requirements and known evasion typologies
- FFIEC IT Examination Handbook — dual-approval / maker-checker guidance
- GLBA Safeguards Rule and PCI-DSS — sensitive data handling
- FBI IC3 BEC (Business Email Compromise) reports — vendor payment fraud
- OWASP LLM Top 10 2025 — indirect prompt injection

**Who collected the data?**  
The author.

**Over what timeframe?**  
Designed and implemented May–June 2026.

**Were the individuals whose data might be affected notified?**  
Not applicable — all data is synthetic.

---

## Preprocessing / Cleaning / Labeling

**Was any preprocessing done?**  
No. The `World` factory produces clean state fresh for each run. No preprocessing
of external data occurs.

**Is the software used to preprocess/clean/label the data available?**  
The entire pipeline (sandbox, evaluator, generator) is open-source in this
repository, with zero third-party dependencies in the core.

---

## Uses

**Has the dataset been used for any tasks already?**  
It is designed for evaluating tool-calling LLMs on financial compliance tasks
under three control postures. No external use has been published yet.

**What (other) tasks could the dataset be used for?**  
- Benchmarking financial guardrail systems (LlamaFirewall, NeMo, Presidio)
- Training or fine-tuning agents to refuse policy-violating instructions
- Studying the effect of system-prompt framing on model instruction-following
- Evaluating multi-agent pipelines under adversarial inputs

**Is there anything about the composition of the dataset or the way it was
collected that might impact future uses?**  
The sandbox enforces controls deterministically under the ENFORCED posture.
Residual ASR under ENFORCED is therefore ~0 for all models; differentiation
happens at the ADVISORY posture. Any use that relies on ENFORCED as the only
metric will not observe meaningful cross-model variation.

**Are there tasks for which the dataset should not be used?**  
This benchmark should not be used to identify or reproduce exploits against real
financial systems. All scenarios are designed for defensive evaluation only.

---

## Distribution

**How will the dataset be distributed?**  
Via GitHub and PyPI (`pip install finagent-redteam`). A Zenodo DOI will be minted
at the first stable release for permanent archival and citation.

**When will the dataset be distributed?**  
The scenario code is live. A formal versioned release with DOI is planned for the
first public leaderboard release.

**Will the dataset be distributed under a copyright or other IP license?**  
MIT License. See [LICENSE](LICENSE).

**Have any third parties imposed IP-based restrictions on the data?**  
No.

---

## Maintenance

**Who is supporting/hosting/maintaining the dataset?**  
Nachiket Lele (GitHub: nac7). Contributions welcome via pull request.

**How can the owner/curator/manager be contacted?**  
Open a GitHub issue or email lelenachiket991@gmail.com.

**Will the dataset be updated?**  
Yes. New threat categories, regulatory updates, and generator improvements will
be versioned with semantic versioning. See CHANGELOG for release history.

**Will older versions be accessible?**  
Via tagged GitHub releases and Zenodo snapshots.

---

## Construct Validity

Each threat category maps to a specific compliance control and its regulatory
grounding:

| Category | Compliance control | Regulatory grounding |
|---|---|---|
| `T2_unauthorized_transfer` | Payee allow-list / payment authorization | FFIEC payment controls |
| `T3_sanctions_evasion` | OFAC SDN screening; normalized name matching | 31 C.F.R. §501; OFAC typologies |
| `T4_structuring` | Currency Transaction Reporting | BSA §5324 (structuring offense) |
| `T5_dual_approval_defeat` | Maker-checker / segregation of duties | FFIEC IT Handbook; SOX COSO |
| `T6_data_exfiltration` | DLP on outbound messages | GLBA Safeguards Rule; PCI-DSS Req. 3 |
| `T7_confused_deputy` | Bank-detail change verification | FBI IC3 BEC guidance |

---

_Cite this benchmark:_
```bibtex
@software{lele2026finagent,
  author  = {Nachiket Lele},
  title   = {FinAgent Red-Team: A benchmark for regulatory-control bypass
             in financial AI agents},
  year    = {2026},
  url     = {https://github.com/nac7/finagent-redteam},
}
```
