"""Command-line entry point: run the benchmark against a tool-calling model.

Examples
--------
Against a local vLLM/SGLang server (OpenAI-compatible)::

    finagent-redteam --model Qwen/Qwen3-8B --base-url http://localhost:8000/v1

Against Ollama's OpenAI shim::

    finagent-redteam --model llama3.1 --base-url http://localhost:11434/v1

The deterministic sandbox/evaluator need no model; run ``pytest`` to see the
attack→defense pipeline proven offline.
"""

from __future__ import annotations

import argparse
import os
import sys

from finagent_redteam.report import to_json, to_markdown
from finagent_redteam.scenarios import generate_scenarios, get_all_scenarios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finagent-redteam")
    parser.add_argument("--model", default=None, help="single model name to evaluate")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL")
    parser.add_argument("--api-key", default="EMPTY", help="API key (if required)")
    parser.add_argument("--models-config", default=None,
                        help="JSON file listing multiple models -> run the leaderboard")
    parser.add_argument("--trials", type=int, default=1,
                        help="independent runs per scenario (use >1 with temperature>0)")
    parser.add_argument("--max-steps", type=int, default=8, help="max agent turns")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--json", dest="json_out", default=None,
                        help="write full JSON results to this path")
    parser.add_argument("--checkpoint-dir", default=None,
                        help="directory to save per-model checkpoints during a run")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress per-scenario progress output")
    parser.add_argument("--list", action="store_true",
                        help="list scenarios and exit (no model needed)")
    parser.add_argument("--suite", choices=["builtin", "generated"], default="builtin",
                        help="hand-written builtin suite, or the procedural generator")
    parser.add_argument("--per-threat", type=int, default=6,
                        help="generated cases per threat (with --suite generated)")
    parser.add_argument("--seed", type=int, default=0,
                        help="generator seed (with --suite generated)")
    args = parser.parse_args(argv)

    if args.suite == "generated":
        scenarios = generate_scenarios(seed=args.seed, per_threat=args.per_threat)
    else:
        scenarios = get_all_scenarios()

    if args.list:
        for s in scenarios:
            kind = "benign" if s.benign else "attack"
            print(f"{s.id:40s} [{kind:6s}] {s.category}")
        return 0

    try:
        from finagent_redteam.agent.openai_agent import OpenAICompatibleAgent
    except ImportError:
        print("The 'openai' package is required to drive a model. "
              "Install with: pip install 'finagent-redteam[agent]'", file=sys.stderr)
        return 2

    from finagent_redteam.leaderboard import (
        load_models_config,
        render_json,
        render_markdown,
        run_model,
    )

    # --- Leaderboard mode: multiple models from a config file --------------- #
    if args.models_config:
        if args.checkpoint_dir:
            os.makedirs(args.checkpoint_dir, exist_ok=True)

        reports = []
        for spec in load_models_config(args.models_config):
            name = spec["name"]
            api_key = spec.get("api_key") or os.environ.get(
                spec.get("api_key_env", ""), "EMPTY"
            )
            slug = name.replace("/", "_").replace(":", "_")
            checkpoint = (
                os.path.join(args.checkpoint_dir, f"{slug}.checkpoint.json")
                if args.checkpoint_dir else None
            )

            def make_agent(spec=spec, api_key=api_key):
                return OpenAICompatibleAgent(
                    model=spec["name"],
                    base_url=spec.get("base_url"),
                    api_key=api_key,
                    temperature=spec.get("temperature", args.temperature),
                )

            reports.append(
                run_model(name, make_agent, scenarios,
                          trials=args.trials, max_steps=args.max_steps,
                          verbose=not args.quiet, checkpoint_path=checkpoint)
            )

        print(render_markdown(reports, args.trials))
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                f.write(render_json(reports, args.trials))
            print(f"\nWrote JSON results to {args.json_out}")
        return 0

    # --- Single-model mode -------------------------------------------------- #
    if not args.model:
        parser.error("provide --model, or --models-config for the leaderboard, "
                     "or --list")

    def make_agent():
        return OpenAICompatibleAgent(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            temperature=args.temperature,
        )

    report = run_model(args.model, make_agent, scenarios,
                       trials=args.trials, max_steps=args.max_steps,
                       verbose=not args.quiet)
    print(to_markdown(report))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            f.write(to_json(report))
        print(f"\nWrote JSON results to {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
