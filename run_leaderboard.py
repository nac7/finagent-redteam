#!/usr/bin/env python3
"""
FinAgent Red-Team — multi-model leaderboard runner.

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
    results/<date>_<suite>_<N>trials.json   — full results + leaderboard
    results/<date>_<suite>_<N>trials.md     — leaderboard markdown (for README)
    checkpoints/<model>.checkpoint.json     — one per model, updated live
"""

from __future__ import annotations

import argparse
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

    # --- Set up output directories ------------------------------------------
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    # --- Import agent driver (needs openai package) --------------------------
    try:
        from finagent_redteam.agent.openai_agent import OpenAICompatibleAgent
    except ImportError:
        print("ERROR: 'openai' package not installed. Run: pip install finagent-redteam[agent]",
              file=sys.stderr)
        return 2

    # --- Run each model -------------------------------------------------------
    reports = []
    t_start = time.monotonic()

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

        try:
            report = run_model(
                name, make_agent, scenarios,
                trials=args.trials, max_steps=args.max_steps,
                verbose=not args.quiet, checkpoint_path=checkpoint,
            )
            reports.append(report)
        except Exception as e:  # noqa: BLE001
            _log(f"  !! FAILED: {e}  (skipping, checkpoint preserved at {checkpoint})")
            continue

    if not reports:
        print("ERROR: no models completed successfully.", file=sys.stderr)
        return 1

    # --- Write outputs --------------------------------------------------------
    today = date.today().isoformat()
    stem = f"{today}_{suite_tag}_{args.trials}trials"

    metadata = {
        "date": today,
        "suite": args.suite,
        "per_threat": args.per_threat if args.suite == "generated" else None,
        "seed": args.seed,
        "trials": args.trials,
        "temperature": args.temperature,
        "max_steps": args.max_steps,
    }

    json_payload = json.loads(render_json(reports, args.trials))
    json_payload["metadata"] = metadata

    json_path = os.path.join(args.out_dir, f"{stem}.json")
    md_path   = os.path.join(args.out_dir, f"{stem}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(reports, args.trials))
        f.write("\n")

    elapsed = time.monotonic() - t_start
    _log(f"Done in {elapsed / 60:.1f} min  →  {json_path}")
    _log(f"Leaderboard  →  {md_path}")

    # Print markdown to stdout (encode safely for Windows terminals).
    md_out = "\n" + render_markdown(reports, args.trials) + "\n"
    sys.stdout.buffer.write(md_out.encode(sys.stdout.encoding or "utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
