"""Render a single model's results (a ModelReport) as Markdown or JSON.

Multi-model leaderboard rendering lives in ``leaderboard.py``; this module is
the detailed single-model view, including a per-scenario breakdown across the
three control postures.
"""

from __future__ import annotations

import json


def to_markdown(report) -> str:
    """``report`` is a leaderboard.ModelReport (duck-typed to avoid a cycle)."""
    c = report.scorecard()
    lines = [
        f"# FinAgent Red-Team report — `{report.model}`",
        "",
        f"Attack scenarios: **{c.n_attack}** · Benign scenarios: **{c.n_benign}**",
        "",
        "| Posture | Attack Success Rate | Utility |",
        "|---|---:|---:|",
        f"| none (no policy stated) | {c.asr_none:.0%} | {c.utility_none:.0%} |",
        f"| advisory (stated, not enforced) | {c.asr_advisory:.0%} | {c.utility_advisory:.0%} |",
        f"| enforced (system hard-blocks) | {c.asr_enforced:.0%} | {c.utility_enforced:.0%} |",
        "",
        f"**Policy-following uplift:** {c.policy_following_uplift:+.0%} "
        "(ASR reduction from merely stating policy)  ",
        f"**Enforcement uplift:** {c.enforcement_uplift:+.0%} "
        "(additional reduction from hard enforcement)  ",
        f"**Residual ASR:** {c.residual_asr:.0%}  ·  "
        f"**Over-refusal:** {c.over_refusal:.0%}",
        "",
        "| Scenario | Category | none | advisory | enforced |",
        "|---|---|---:|---:|---:|",
    ]
    for r in report.results:
        lines.append(
            f"| {r.scenario_id} | {r.category} | {r.rate_none:.0%} "
            f"| {r.rate_advisory:.0%} | {r.rate_enforced:.0%} |"
        )

    # Stratified ASR by diversity axis (only if the suite carries strata).
    for axis, title in (("tier", "difficulty tier"),
                        ("vector", "injection vector"),
                        ("step_mode", "step mode")):
        rows = report.strata(axis)
        if not rows:
            continue
        lines += [
            "",
            f"## ASR by {title}",
            f"| {axis} | n | none | advisory | enforced |",
            "|---|---:|---:|---:|---:|",
        ]
        for s in rows:
            lines.append(
                f"| {s.value} | {s.n_scenarios} | {s.asr_none:.0%} "
                f"| {s.asr_advisory:.0%} | {s.asr_enforced:.0%} |"
            )

    disp = report.dispersion("none")
    if disp:
        lines += [
            "",
            "## Surface-form sensitivity (within-category ASR dispersion, posture=none)",
            "_Spread of per-scenario ASR across a category's framings/phrasings/params;"
            " higher = more sensitive to how the same attack is dressed up._",
            "| category | n | mean ASR | SD | spread |",
            "|---|---:|---:|---:|---:|",
        ]
        for d in disp:
            lines.append(
                f"| {d.category} | {d.n_scenarios} | {d.mean_asr:.0%} "
                f"| {d.sd_asr:.2f} | {d.spread:.0%} |"
            )
    return "\n".join(lines)


def to_json(report) -> str:
    c = report.scorecard()
    return json.dumps(
        {
            "model": report.model,
            "scorecard": {
                "n_attack": c.n_attack,
                "n_benign": c.n_benign,
                "asr_none": c.asr_none,
                "asr_advisory": c.asr_advisory,
                "asr_enforced": c.asr_enforced,
                "utility_none": c.utility_none,
                "utility_advisory": c.utility_advisory,
                "utility_enforced": c.utility_enforced,
                "policy_following_uplift": c.policy_following_uplift,
                "enforcement_uplift": c.enforcement_uplift,
                "residual_asr": c.residual_asr,
                "over_refusal": c.over_refusal,
            },
            "scenarios": [
                {
                    "scenario_id": r.scenario_id,
                    "category": r.category,
                    "benign": r.benign,
                    "strata": r.strata,
                    "rate_none": r.rate_none,
                    "rate_advisory": r.rate_advisory,
                    "rate_enforced": r.rate_enforced,
                }
                for r in report.results
            ],
            "strata": {
                axis: [
                    {
                        "value": s.value,
                        "n_scenarios": s.n_scenarios,
                        "asr_none": s.asr_none,
                        "asr_advisory": s.asr_advisory,
                        "asr_enforced": s.asr_enforced,
                        "asr_none_ci": s.asr_none_ci.as_dict(),
                        "asr_enforced_ci": s.asr_enforced_ci.as_dict(),
                    }
                    for s in report.strata(axis)
                ]
                for axis in ("tier", "vector", "step_mode", "style")
            },
            "asr_dispersion_none": [
                {
                    "category": d.category,
                    "n_scenarios": d.n_scenarios,
                    "mean_asr": d.mean_asr,
                    "sd_asr": d.sd_asr,
                    "spread": d.spread,
                }
                for d in report.dispersion("none")
            ],
        },
        indent=2,
    )
