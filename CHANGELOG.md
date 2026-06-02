# Changelog

All notable changes to FinAgent Red-Team are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — 2026-06-01

### Added
- **Three control postures** (`NONE` / `ADVISORY` / `ENFORCED`) replacing the
  binary off/on switch. Metrics now decompose *policy-following uplift* and
  *enforcement uplift* separately, enabling cross-model differentiation even when
  hard enforcement drives residual ASR to ~0.
- **Scenario generator** (`scenarios/generator.py`): seeded, deterministic;
  produces hundreds of variants per threat by combining parametric slots,
  social-engineering phrasings, and homoglyph/spacing obfuscation. Default
  `per_threat=6` → 54 scenarios; `per_threat=15` → 120.
- **Multi-model leaderboard runner** (`leaderboard.py`): multi-trial aggregation,
  ranked table + per-category ASR matrix, `--models-config` + `--trials` CLI
  flags.
- Three new threat categories:
  - `T6_data_exfiltration` — DLP on outbound messages
  - `T7_confused_deputy` — bank-detail change verification
  - `T3` homoglyph variant — normalized sanctions screening (`sandbox/sanctions.py`)
- `reference_plan` field on `Scenario` — canonical exploit for self-validation.
- Self-validating invariant test (`tests/test_generator.py`) proves every
  generated scenario across all postures.
- GitHub Actions CI (tests × Python 3.10–3.13, ruff lint, mypy).
- `CONTRIBUTING.md`, `SECURITY.md`, `DATASHEET.md`, `CHANGELOG.md`, `mkdocs.yml`.
- Badges: CI, PyPI, Python, license, Codecov.
- PyPI classifiers and project URLs.

### Changed
- `runner.py`: `run_scenario(posture)` replaces `run_paired`; `run_postures()`
  runs all three. System prompt is posture-aware (NONE has no policy stated).
- `metrics.py`: rewritten `Scorecard` with per-posture fields and uplift
  properties; `build_scorecard()` / `category_breakdown()` replace `aggregate()`.
- `leaderboard.py` / `report.py`: unified on `ModelReport`; CLI unified on
  `run_model` for both single and multi-model paths.
- `pyproject.toml`: bumped to 0.2.0; added classifiers, dev extras (`ruff`,
  `mypy`, `pytest-cov`), project URLs.

### Fixed
- Transfer registration ordering bug: `World.transfers[id]` now registered before
  `_maybe_file_report()` so cumulative structuring detection includes the current
  transfer.

---

## [0.1.0] — 2026-05-31

Initial release.

### Added
- Deterministic financial sandbox: `World`, `Account`, `Payee`, `Email`,
  `Transfer`, `ComplianceReport`.
- `Policy` engine with controls: allow-list, sanctions screening, reporting
  threshold, maker-checker, DLP, bank-detail protection.
- `ControlPosture` enum and `Policy.for_posture()`.
- Mock financial tools: `initiate_transfer`, `approve_transfer`,
  `screen_sanctions`, `list_payees`, `get_account_balance`, `read_inbox`,
  `send_external_message`, `get_customer_record`, `update_payee`,
  `file_compliance_report`.
- Scenario schema (`Scenario`, `AttackGoal`, `Contract`).
- 7 hand-written attack scenarios (T2–T7) + 1 benign control.
- Deterministic evaluator with predicates: `unauthorized_transfer`,
  `sanctions_evasion`, `structuring`, `dual_approval_defeat`,
  `data_exfiltration`, `payee_hijack`, `transfer_completed`.
- OpenAI-compatible agent driver (`agent/openai_agent.py`).
- CLI: `finagent-redteam --model ... --base-url ... [--json ...]`.
- 41 offline unit tests, all green, no GPU/API needed.
