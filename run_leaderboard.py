#!/usr/bin/env python3
"""
FinAgent Red-Team - multi-model leaderboard runner.

Usage:
    # Free, local (requires Ollama + pulled models):
    python run_leaderboard.py --config models/ollama_local.json

    # Cloud APIs (set env vars first):
    python run_leaderboard.py --config models/api_models.json

    # Full paper leaderboard (local + API):
    python run_leaderboard.py --config models/paper_full.json --trials 5

    # Quick smoke test against one Ollama model:
    python run_leaderboard.py --config models/ollama_local.json \
        --models llama3.1:8b --per-threat 2 --trials 1

Outputs:
    results/<date>_<suite>_<N>trials.json   - full results + leaderboard
    results/<date>_<suite>_<N>trials.md     - leaderboard markdown (for README)
    checkpoints/<model>.checkpoint.json     - one per model, updated live
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import date

# Make src importable when run from the project root without installing.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from finagent_redteam.leaderboard import (
    load_models_config,
    render_json,
    render_markdown,
    run_model,
)
from finagent_redteam.scenarios import generate_scenarios, get_all_scenarios
from finagent_redteam.validate import validate_model_report

try:
    import track_progress as _tracker
except ImportError:
    _tracker = None


def _update_progress() -> None:
    if _tracker is not None:
        try:
            _tracker.update_progress_md()
        except Exception:
            pass


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the FinAgent Red-Team multi-model leaderboard."
    )
    p.add_argument("--config", required=True,
                   help="path to a models JSON config (models/*.json)")
    p.add_argument("--models", nargs="*",
                   help="subset of model names to run (default: all in config)")
    p.add_argument("--suite", choices=["builtin", "generated"], default="generated",
                   help="scenario suite (default: generated)")
    p.add_argument("--per-threat", type=int, default=6,
                   help="scenarios per threat for the generated suite (default: 6)")
    p.add_argument("--seed", type=int, default=0,
                   help="generator seed (default: 0)")
    p.add_argument("--trials", type=int, default=5,
                   help="independent trials per scenario (default: 5)")
    p.add_argument("--temperature", type=float, default=0.7,
                   help="sampling temperature (default: 0.7)")
    p.add_argument("--max-steps", type=int, default=10,
                   help="max agent turns per scenario (default: 10)")
    p.add_argument("--out-dir", default="results",
                   help="directory for output files (default: results/)")
    p.add_argument("--checkpoint-dir", default="checkpoints",
                   help="directory for checkpoint files (default: checkpoints/)")
    p.add_argument("--quiet", action="store_true",
                   help="suppress per-scenario progress")
    p.add_argument("--inter-scenario-delay", type=float, default=0.0,
                   help="seconds to pause between scenarios so a provider's "
                        "rate/quota window can recover (e.g. 45 for Groq free tier)")
    return p.parse_args()


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    sys.stdout.buffer.write(line.encode(sys.stdout.encoding or "utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def main() -> int:
    args = _parse_args()

    # --- Load scenario suite ------------------------------------------------
    if args.suite == "generated":
        scenarios = generate_scenarios(seed=args.seed, per_threat=args.per_threat)
        suite_tag = f"generated-p{args.per_threat}"
    else:
        scenarios = get_all_scenarios()
        suite_tag = "builtin"

    attack = sum(1 for s in scenarios if not s.benign)
    benign = sum(1 for s in scenarios if s.benign)
    total_calls = len(scenarios) * 3 * args.trials  # 3 postures
    _log(f"Suite: {suite_tag}  |  {attack} attack + {benign} benign = {len(scenarios)} scenarios")
    _log(f"Trials: {args.trials}  |  Total agent calls per model: {total_calls}")

    # --- Load model configs --------------------------------------------------
    all_specs = load_models_config(args.config)
    if args.models:
        all_specs = [s for s in all_specs if s["name"] in args.models]
        if not all_specs:
            print(f"ERROR: none of {args.models} found in {args.config}", file=sys.stderr)
            return 1

    _log(f"Models: {[s['name'] for s in all_specs]}")

    # --- Pre-flight: refuse to run cloud models with no credentials ----------
    # The June-2026 corruption came from running key-less cloud models: every
    # call errored, yet errored trials contribute no successes, so the scorecard
    # recorded a bogus 0% ASR. Skip such models up front rather than burning a
    # full run to produce data that must be thrown away.
    runnable_specs: list = []
    skipped_no_key: list = []
    for spec in all_specs:
        key_env = spec.get("api_key_env")
        has_inline_key = bool(spec.get("api_key"))
        needs_key = bool(key_env) and not has_inline_key
        if needs_key and not os.environ.get(key_env):
            skipped_no_key.append((spec["name"], key_env))
            continue
        runnable_specs.append(spec)

    if skipped_no_key:
        _log("!! SKIPPING models with no API key set (would produce invalid 0% data):")
        for name, env in skipped_no_key:
            _log(f"     - {name}  (set ${env})")
    if not runnable_specs:
        print("ERROR: no runnable models - every requested model is missing its "
              "API key. Set the required env vars and retry.", file=sys.stderr)
        return 1
    all_specs = runnable_specs

    # --- Set up output directories ------------------------------------------
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    # Snapshot current state before any model runs.
    _update_progress()

    # --- Import agent driver (needs openai package) --------------------------
    try:
        from finagent_redteam.agent.openai_agent import OpenAICompatibleAgent
    except ImportError:
        print("ERROR: 'openai' package not installed. Run: pip install finagent-redteam[agent]",
              file=sys.stderr)
        return 2

    # --- Run each model -------------------------------------------------------
    reports: list = []
    # Map model name → partial report (updated after every scenario, not just
    # after a model finishes).  Used to write incremental results to disk so a
    # pause mid-model doesn't lose already-completed scenario data.
    partial_reports: dict = {}
    # model name -> ValidationResult, filled after each model completes.
    validations: dict = {}
    t_start = time.monotonic()

    # Setup for incremental results writing
    today = date.today().isoformat()
    suite_tag = f"generated-p{args.per_threat}" if args.suite == "generated" else "builtin"
    stem = f"{today}_{suite_tag}_{args.trials}trials"

    # Generate run_hash from scenario IDs and seed for reproducibility
    scenario_ids = "|".join(s.id for s in scenarios)
    run_hash_input = f"{scenario_ids}|seed={args.seed}"
    run_hash = hashlib.sha256(run_hash_input.encode()).hexdigest()[:16]

    # Get runner version from package metadata
    try:
        import importlib.metadata
        runner_version = importlib.metadata.version("finagent-redteam")
    except (ImportError, importlib.metadata.PackageNotFoundError):
        runner_version = "dev"

    metadata = {
        "date": today,
        "suite": args.suite,
        "per_threat": args.per_threat if args.suite == "generated" else None,
        "seed": args.seed,
        "run_hash": run_hash,
        "runner_version": runner_version,
        "trials": args.trials,
        "temperature": args.temperature,
        "max_steps": args.max_steps,
    }
    json_path = os.path.join(args.out_dir, f"{stem}.json")
    md_path = os.path.join(args.out_dir, f"{stem}.md")

    def _write_outputs(done_reports: list) -> None:
        """Persist JSON (all models, validation-annotated) and Markdown.

        The Markdown leaderboard - the artifact that feeds the README and paper -
        contains ONLY models that pass validation, so invalid data can never be
        published. The JSON keeps every model but tags each with its verdict.
        """
        payload = json.loads(render_json(done_reports, args.trials))
        payload["metadata"] = metadata
        for entry in payload.get("models", []):
            vr = validations.get(entry.get("model"))
            if vr is not None:
                entry["validation"] = vr.as_dict()
        payload["validation_summary"] = {
            "valid": [m for m, vr in validations.items() if vr.valid],
            "invalid": [m for m, vr in validations.items() if not vr.valid],
        }
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

        valid_reports = [r for r in done_reports if validations.get(r.model) is None
                         or validations[r.model].valid]
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(valid_reports, args.trials))
            fh.write("\n")
            invalid = [m for m, vr in validations.items() if not vr.valid]
            if invalid:
                fh.write(
                    "\n> **Excluded from this leaderboard (failed validation):** "
                    + ", ".join(invalid) + ". See the JSON `validation` blocks for reasons.\n"
                )

    for i, spec in enumerate(all_specs, 1):
        name = spec["name"]
        slug = name.replace("/", "_").replace(":", "_")
        api_key = spec.get("api_key") or os.environ.get(
            spec.get("api_key_env", ""), "EMPTY"
        )
        checkpoint = os.path.join(args.checkpoint_dir, f"{slug}.checkpoint.json")

        _log(f"-- Model {i}/{len(all_specs)}: {name}")

        def make_agent(spec: dict = spec, api_key: str = api_key):
            return OpenAICompatibleAgent(
                model=spec["name"],
                base_url=spec.get("base_url"),
                api_key=api_key,
                temperature=spec.get("temperature", args.temperature),
                extra_body=spec.get("extra_body"),
            )

        def _flush_incremental(partial: "ModelReport", _name: str = name) -> None:
            """Write results file after every scenario, not just per-model."""
            partial_reports[_name] = partial
            # Merge: completed models from reports[] + partial progress from
            # any model that's still running.  Completed entries take priority.
            completed_names = {r.model for r in reports}
            merged = list(reports)
            for m, r in partial_reports.items():
                if m not in completed_names:
                    merged.append(r)
            if not merged:
                return
            try:
                payload = json.loads(render_json(merged, args.trials))
                payload["metadata"] = metadata
                with open(json_path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2)
            except Exception:
                pass  # never let a flush error crash the run

        try:
            report = run_model(
                name, make_agent, scenarios,
                trials=args.trials, max_steps=args.max_steps,
                verbose=not args.quiet, checkpoint_path=checkpoint,
                on_checkpoint=_flush_incremental,
                inter_scenario_delay=args.inter_scenario_delay,
            )
            reports.append(report)
            partial_reports.pop(name, None)

            # --- Post-run integrity gate -------------------------------------
            vr = validate_model_report(report)
            validations[name] = vr
            if vr.valid:
                _log(f"  VALID {name}"
                     + (f"  ({'; '.join(vr.warnings)})" if vr.warnings else ""))
            else:
                _log(f"  !! INVALID {name} - EXCLUDED from the published leaderboard:")
                for reason in vr.reasons:
                    _log(f"       - {reason}")

            # Final write after model completes: also update markdown.
            _write_outputs(reports)
            _log(f"  Results saved -> {json_path}")
        except Exception as e:  # noqa: BLE001
            _log(f"  !! FAILED: {e}  (skipping, checkpoint preserved at {checkpoint})")
            continue
        finally:
            # Refresh progress MD after every model (success or failure).
            _update_progress()

    if not reports:
        print("ERROR: no models completed successfully.", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - t_start
    _log(f"Done in {elapsed / 60:.1f} min  →  {json_path}")
    _log(f"Leaderboard  →  {md_path}")

    # Validation summary - the integrity bottom line.
    valid_names = [m for m, vr in validations.items() if vr.valid]
    invalid_names = [m for m, vr in validations.items() if not vr.valid]
    _log(f"Validation: {len(valid_names)} valid, {len(invalid_names)} invalid.")
    if invalid_names:
        _log(f"  Excluded (invalid): {invalid_names}")
    if skipped_no_key:
        _log(f"  Skipped (no key): {[n for n, _ in skipped_no_key]}")

    # Print the published (valid-only) leaderboard to stdout.
    valid_reports = [r for r in reports if validations.get(r.model) is None
                     or validations[r.model].valid]
    md_out = "\n" + render_markdown(valid_reports, args.trials) + "\n"
    sys.stdout.buffer.write(md_out.encode(sys.stdout.encoding or "utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
