#!/usr/bin/env python3
"""Offline integrity gate for leaderboard result files.

Loads a results JSON (or checkpoint) and reports, per model, whether its data is
publishable - enforcing the same exclusion principle the live runner uses:
zero API errors, real tool use (non-zero benign utility), and both attack and
benign scenarios present.

Use it before regenerating figures or updating the paper: only models that pass
should feed a published leaderboard.

Usage:
    python validate_results.py results/2026-06-20_generated-p6_3trials.json
    python validate_results.py results/*.json
    python validate_results.py results/x.json --require claude-sonnet-4-6 gpt-4o
    python validate_results.py results/x.json --json

Exit status:
    0  all models valid (and every --require model present & valid)
    1  at least one model invalid, or a --require model missing/invalid
    2  usage / file error
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from finagent_redteam.validate import validate_model_dict  # noqa: E402


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", help="results/checkpoint JSON file(s)")
    p.add_argument("--require", nargs="*", default=[],
                   help="model names that MUST be present and valid")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of a table")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    all_results: list = []
    seen_models: dict[str, bool] = {}

    for path in args.files:
        try:
            data = _load(path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
            return 2
        models = data.get("models", []) or []
        for entry in models:
            vr = validate_model_dict(entry)
            all_results.append((path, vr))
            # A model is "seen valid" if any file has a valid copy of it.
            seen_models[vr.model] = seen_models.get(vr.model, False) or vr.valid

    if args.json:
        out = {
            "results": [
                {"file": os.path.basename(p), **vr.as_dict()} for p, vr in all_results
            ],
            "required_ok": all(seen_models.get(m, False) for m in args.require),
            "missing_required": [
                m for m in args.require if m not in seen_models
            ],
            "invalid_required": [
                m for m in args.require
                if m in seen_models and not seen_models[m]
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print("=" * 72)
        print("FinAgent Red-Team - result integrity report")
        print("=" * 72)
        cur_file = None
        for path, vr in all_results:
            if path != cur_file:
                print(f"\n# {path}")
                cur_file = path
            print(vr.summary_line())

        n_valid = sum(1 for _, vr in all_results if vr.valid)
        print("\n" + "-" * 72)
        print(f"{n_valid}/{len(all_results)} model entries valid.")

    # --- exit status ---------------------------------------------------------
    any_invalid = any(not vr.valid for _, vr in all_results)
    missing_required = [m for m in args.require if m not in seen_models]
    invalid_required = [
        m for m in args.require if m in seen_models and not seen_models[m]
    ]

    if missing_required:
        print(f"\nFAIL: required model(s) missing entirely: {missing_required}",
              file=sys.stderr)
        return 1
    if invalid_required:
        print(f"\nFAIL: required model(s) present but invalid: {invalid_required}",
              file=sys.stderr)
        return 1
    if args.require:
        # Caller cares only about the required set - all present and valid.
        print("\nOK: all required models present and valid.")
        return 0
    return 1 if any_invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
