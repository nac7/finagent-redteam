# Contributing to FinAgent Red-Team

Thank you for your interest in contributing. This document explains how the
project is structured, what kinds of contributions are most valuable, and the
quality bar we hold for any change.

---

## What we value most

1. **New threat scenarios** — each isolating a distinct compliance control,
   backed by a real regulation or industry standard (see the threat taxonomy in
   the README), and shipped with a `reference_plan` that the self-validation
   suite can replay.

2. **New sandbox controls** — a new `Policy` field paired with enforcement logic
   in `sandbox/tools.py`, tested so that the invariant (attack lands under *none*
   and *advisory*, blocked under *enforced*) holds.

3. **Evaluation of additional models** — raw results JSON and a reproducibility
   note (model name, API version, date, temperature, seed) for inclusion in the
   public leaderboard.

4. **External guardrail integrations** — pluggable `Policy`-like adapters for
   LlamaFirewall, NeMo Guardrails, Presidio, etc., so the benchmark can measure
   *actual* commercial defenses.

---

## Getting started

```bash
git clone https://github.com/nac7/finagent-redteam.git
cd finagent-redteam
pip install -e ".[dev]"
pytest -q            # 41 tests should pass in < 1 second, no GPU needed
```

---

## Adding a new scenario

1. **Choose a threat category** from `scenarios/schema.py:THREAT_CATEGORIES`.
   If your attack maps to a new category, add it there.

2. **Build a `world_factory`** — a zero-argument callable that returns a fresh
   `World`. All required `Payee`, `Account`, `Email`, and `World` fields must be
   set; never mutate shared state.

3. **Write the `reference_plan`** — the canonical minimal action sequence that
   makes the attack succeed. The self-validation test will replay it and check:
   - attack lands under `ControlPosture.NONE` and `ControlPosture.ADVISORY`
   - attack is blocked under `ControlPosture.ENFORCED`

4. **Ground the threat in a real control standard.** The PR description must
   reference at least one of: BSA/AML (31 U.S.C. 5318), OFAC sanctions rules,
   FFIEC guidance, GLBA Safeguards, PCI-DSS, SOX/COSO segregation of duties,
   OWASP LLM Top 10, or an equivalent published standard.

5. **Add a unit test** in `tests/test_threats.py` (or a new file) using
   `run_postures` and asserting `_assert_attack_invariant`.

6. **Optionally add to the generator** (`scenarios/generator.py`) if the
   scenario is parametric enough to produce many variants.

---

## Code quality requirements

- All public functions must have type annotations.
- No third-party imports in `sandbox/`, `scenarios/`, or `eval/` — these must
  remain dependency-free so the test suite runs without any install.
- `ruff check` and `ruff format --check` must pass before any commit:
  ```bash
  ruff check src/ tests/
  ruff format src/ tests/
  ```
- `mypy src/finagent_redteam --strict --ignore-missing-imports` must pass.
- The full test suite must stay green.

---

## Submitting a pull request

- Open an issue first if you are proposing a new threat category or a
  significant architectural change.
- PR titles: `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`.
- The PR description must state which compliance control the change tests, cite
  the standard, and include the `pytest -q` output.

---

## Responsible use

FinAgent Red-Team is a **defensive** benchmark. All contributions must use
fully synthetic data and must not include real credentials, account numbers, or
exploits against live systems. See [SECURITY.md](SECURITY.md).
