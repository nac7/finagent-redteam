# Contributing

See [CONTRIBUTING.md](https://github.com/nac7/finagent-redteam/blob/main/CONTRIBUTING.md) on GitHub for the full guide.

Key points:

- **New scenarios** must cite a real regulation, carry a `reference_plan`, and pass the posture invariant test.
- **No third-party deps** in `sandbox/`, `scenarios/`, or `eval/`.
- Run `ruff check src/ tests/` and `pytest -q` before opening a PR.
