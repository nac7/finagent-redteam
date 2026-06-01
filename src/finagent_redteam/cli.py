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

from finagent_redteam.eval.metrics import aggregate
from finagent_redteam.report import to_json, to_markdown
from finagent_redteam.runner import run_paired
from finagent_redteam.scenarios import get_all_scenarios


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
    parser.add_argument("--list", action="store_true",
                        help="list scenarios and exit (no model needed)")
    args = parser.parse_args(argv)

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

    # --- Leaderboard mode: multiple models from a config file --------------- #
    if args.models_config:
        from finagent_redteam.leaderboard import (
            load_models_config,
            render_json,
            render_markdown,
            run_model,
        )

        reports = []
        for spec in load_models_config(args.models_config):
            name = spec["name"]
            api_key = spec.get("api_key") or os.environ.get(
                spec.get("api_key_env", ""), "EMPTY"
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
                          trials=args.trials, max_steps=args.max_steps)
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

    agent = OpenAICompatibleAgent(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        temperature=args.temperature,
    )
    paired = [run_paired(agent, s, max_steps=args.max_steps) for s in scenarios]
    card = aggregate(args.model, paired)

    print(to_markdown(args.model, paired, card))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            f.write(to_json(args.model, paired, card))
        print(f"\nWrote JSON results to {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
