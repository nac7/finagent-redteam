#!/usr/bin/env python3
"""Assemble the canonical leaderboard from one or more result files.

Runs were produced across several invocations (different providers, separate
out-dirs). This merges their per-model results into a single ranked leaderboard,
but only after each model passes the integrity gate (see ``validate.py``): every
number in the published table is from a model with zero API errors, real tool
use, and both scenario kinds. Invalid models are reported and dropped.

If the same model appears in multiple files, the valid copy with the most trials
wins (ties broken by fewest errors), so a later clean re-run supersedes an older
or partial one.

Usage:
    python build_leaderboard.py \
        results/2026-07-25_generated-p6_3trials.json \
        results/_openai/2026-07-25_generated-p6_3trials.json \
        results/2026-06-20_generated-p6_3trials.json \
        --out results/leaderboard_final

Writes ``<out>.json`` (canonical, validation-annotated) and ``<out>.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from finagent_redteam.leaderboard import (  # noqa: E402
    ModelReport,
    ScenarioTrialResult,
    render_json,
    render_markdown,
)
from finagent_redteam.validate import validate_model_dict  # noqa: E402


def _report_from_entry(entry: dict) -> ModelReport:
    """Reconstruct a ModelReport from a rendered results-JSON model entry."""
    results: list[ScenarioTrialResult] = []
    for s in entry.get("scenarios", []):
        n = s.get("n_trials", 1)
        errs = s.get("errors", 0)
        valid = s.get("valid_trials", max(n - errs, 0))
        results.append(ScenarioTrialResult(
            scenario_id=s["scenario_id"],
            category=s["category"],
            benign=s.get("benign", False),
            n_trials=n,
            # Rates were computed over valid_trials, so reconstruct successes
            # against valid_trials (matches leaderboard._load_checkpoint).
            successes_none=round(s.get("rate_none", 0.0) * valid),
            successes_advisory=round(s.get("rate_advisory", 0.0) * valid),
            successes_enforced=round(s.get("rate_enforced", 0.0) * valid),
            errors=errs,
        ))
    return ModelReport(model=entry["model"], results=results)


def _trials_of(entry: dict) -> int:
    scen = entry.get("scenarios", [])
    return max((s.get("n_trials", 0) for s in scen), default=0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="result JSON files to merge")
    ap.add_argument("--out", default="results/leaderboard_final",
                    help="output stem (writes .json and .md)")
    args = ap.parse_args()

    # model name -> (entry, trials, errors) for the best VALID copy seen so far.
    best: dict[str, tuple] = {}
    dropped: list[str] = []

    for path in args.files:
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
            return 2
        for entry in data.get("models", []):
            vr = validate_model_dict(entry)
            name = entry["model"]
            if not vr.valid:
                dropped.append(f"{name} ({os.path.basename(path)}): {vr.reasons[0]}")
                continue
            trials = _trials_of(entry)
            errs = vr.errors_total
            if name not in best:
                best[name] = (entry, trials, errs)
            else:
                _, bt, be = best[name]
                if (trials, -errs) > (bt, -be):  # more trials, then fewer errors
                    best[name] = (entry, trials, errs)

    if not best:
        print("ERROR: no valid models across the given files.", file=sys.stderr)
        return 1

    reports = [_report_from_entry(entry) for entry, _, _ in best.values()]
    trials = max((t for _, t, _ in best.values()), default=0)

    md = render_markdown(reports, trials)
    payload = json.loads(render_json(reports, trials))
    payload["source_files"] = [os.path.basename(f) for f in args.files]

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write(md + "\n")

    print(f"Canonical leaderboard: {len(reports)} valid models "
          f"-> {args.out}.json / .md")
    for name in sorted(best):
        print(f"  + {name}")
    for d in dropped:
        print(f"  - dropped {d}")
    print()
    # Encode safely for Windows consoles.
    sys.stdout.buffer.write((md + "\n").encode(sys.stdout.encoding or "utf-8",
                                               errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
