"""Render benchmark results as a Markdown scorecard or JSON."""

from __future__ import annotations

import json

from finagent_redteam.eval.metrics import Scorecard


def _attack_mark(success: bool) -> str:
    return "🔴 attack succeeded" if success else "🟢 blocked"


def _benign_mark(success: bool) -> str:
    return "🟢 completed" if success else "🔴 over-refused"


def to_markdown(model: str, paired: list[dict], card: Scorecard) -> str:
    lines = [
        f"# FinAgent Red-Team scorecard — `{model}`",
        "",
        f"Attack scenarios: **{card.n_attack}** · Benign scenarios: **{card.n_benign}**",
        "",
        "| Metric | Guardrails OFF | Guardrails ON |",
        "|---|---:|---:|",
        f"| Attack Success Rate (lower better) | {card.asr_guardrails_off:.0%} | "
        f"{card.asr_guardrails_on:.0%} |",
        f"| Utility / benign completed (higher better) | "
        f"{card.utility_guardrails_off:.0%} | {card.utility_guardrails_on:.0%} |",
        "",
        f"**Defense efficacy:** {card.defense_efficacy:+.0%} ASR reduction when "
        "guardrails are enabled.  "
        f"**Over-refusal cost:** {card.over_refusal_cost:.0%} utility lost.",
        "",
        "| Scenario | Category | OFF | ON |",
        "|---|---|---|---|",
    ]
    for r in paired:
        mark = _benign_mark if r["benign"] else _attack_mark
        lines.append(
            f"| {r['scenario_id']} | {r['category']} | "
            f"{mark(r['success_off'])} | {mark(r['success_on'])} |"
        )
    return "\n".join(lines)


def to_json(model: str, paired: list[dict], card: Scorecard) -> str:
    return json.dumps(
        {
            "model": model,
            "scorecard": {
                "n_attack": card.n_attack,
                "n_benign": card.n_benign,
                "asr_guardrails_off": card.asr_guardrails_off,
                "asr_guardrails_on": card.asr_guardrails_on,
                "utility_guardrails_off": card.utility_guardrails_off,
                "utility_guardrails_on": card.utility_guardrails_on,
                "defense_efficacy": card.defense_efficacy,
                "over_refusal_cost": card.over_refusal_cost,
            },
            "scenarios": paired,
        },
        indent=2,
    )
