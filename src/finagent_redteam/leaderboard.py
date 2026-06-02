"""Multi-model leaderboard.

Runs the scenario suite across several models, each scenario repeated for
``trials`` independent runs (models are stochastic, so a single run is not a
defensible measurement) under all three control postures, and aggregates into a
ranked leaderboard plus a per-threat-category attack-success matrix.

Aggregation and rendering are pure and offline-testable; only the agent drivers
touch a model.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from finagent_redteam.agent.base import AgentModel
from finagent_redteam.eval.metrics import (
    CategoryStat,
    Scorecard,
    build_scorecard,
    category_breakdown,
)
from finagent_redteam.runner import run_postures
from finagent_redteam.scenarios.schema import Scenario

AgentFactory = Callable[[], AgentModel]


@dataclass
class ScenarioTrialResult:
    scenario_id: str
    category: str
    benign: bool
    n_trials: int
    successes_none: int
    successes_advisory: int
    successes_enforced: int
    errors: int = 0

    @property
    def rate_none(self) -> float:
        return self.successes_none / self.n_trials if self.n_trials else 0.0

    @property
    def rate_advisory(self) -> float:
        return self.successes_advisory / self.n_trials if self.n_trials else 0.0

    @property
    def rate_enforced(self) -> float:
        return self.successes_enforced / self.n_trials if self.n_trials else 0.0


@dataclass
class ModelReport:
    model: str
    results: list[ScenarioTrialResult] = field(default_factory=list)

    def scorecard(self) -> Scorecard:
        return build_scorecard(self.model, self.results)

    def categories(self) -> list[CategoryStat]:
        return category_breakdown(self.results)


def _log(msg: str) -> None:
    """Write a timestamped progress line to stderr (visible in terminals)."""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def run_scenario_trials(
    agent_factory: AgentFactory,
    scenario: Scenario,
    trials: int = 1,
    max_steps: int = 8,
    verbose: bool = False,
) -> ScenarioTrialResult:
    sn = sa = se = errors = 0
    for t in range(trials):
        if verbose:
            kind = "benign" if scenario.benign else "attack"
            _log(f"  {scenario.id} [{kind}] trial {t + 1}/{trials}")
        res = run_postures(agent_factory, scenario, max_steps)
        sn += int(res["achieved_none"])
        sa += int(res["achieved_advisory"])
        se += int(res["achieved_enforced"])
        errors += int(bool(res["error"]))
        if verbose and res["error"]:
            _log(f"    !! error: {res['error']}")
    return ScenarioTrialResult(
        scenario_id=scenario.id,
        category=scenario.category,
        benign=scenario.benign,
        n_trials=trials,
        successes_none=sn,
        successes_advisory=sa,
        successes_enforced=se,
        errors=errors,
    )


def run_model(
    model: str,
    agent_factory: AgentFactory,
    scenarios: list[Scenario],
    trials: int = 1,
    max_steps: int = 8,
    verbose: bool = True,
    checkpoint_path: str | None = None,
) -> ModelReport:
    """Run all scenarios for one model.

    ``verbose`` streams per-scenario progress to stderr.
    ``checkpoint_path`` saves intermediate JSON after every scenario so a crash
    loses at most one scenario's work.
    """
    if verbose:
        _log(f"▶ {model}  ({len(scenarios)} scenarios × {trials} trials × 3 postures)")

    results: list[ScenarioTrialResult] = []
    t0 = time.monotonic()

    for i, s in enumerate(scenarios, 1):
        if verbose:
            pct = int(100 * (i - 1) / len(scenarios))
            _log(f"  [{pct:3d}%] {i}/{len(scenarios)} {s.id}")
        r = run_scenario_trials(agent_factory, s, trials=trials,
                                max_steps=max_steps, verbose=False)
        results.append(r)

        if checkpoint_path:
            _save_checkpoint(checkpoint_path, model, results, trials)

    elapsed = time.monotonic() - t0
    report = ModelReport(model=model, results=results)
    if verbose:
        c = report.scorecard()
        _log(
            f"  ✓ {model}  asr(none)={c.asr_none:.0%} "
            f"asr(adv)={c.asr_advisory:.0%} "
            f"asr(enf)={c.asr_enforced:.0%} "
            f"utility={c.utility_enforced:.0%}  "
            f"[{elapsed:.0f}s]"
        )
    return report


def _save_checkpoint(path: str, model: str, results: list[ScenarioTrialResult],
                     trials: int) -> None:
    """Write a partial ModelReport to disk so a crash loses at most 1 scenario."""
    report = ModelReport(model=model, results=results)
    data = {
        "checkpoint": True,
        "model": model,
        "completed_scenarios": len(results),
        **json.loads(render_json([report], trials)),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_markdown(reports: list[ModelReport], trials: int) -> str:
    cards = [(r, r.scorecard()) for r in reports]
    # Rank by residual risk (enforced), then susceptibility under stated policy
    # (advisory), then intrinsic (none), then utility.
    ranked = sorted(
        cards,
        key=lambda rc: (
            rc[1].asr_enforced,
            rc[1].asr_advisory,
            rc[1].asr_none,
            -rc[1].utility_enforced,
        ),
    )

    lines = [
        "# FinAgent Red-Team Leaderboard",
        "",
        f"Trials per scenario: **{trials}**. ASR = Attack Success Rate (lower is "
        "better). Postures: **none** (no policy stated) → **advisory** (policy "
        "stated, not enforced) → **enforced** (system hard-blocks).",
        "",
        "| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | "
        "Enforcement | Utility enf | Over-refusal |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, (r, c) in enumerate(ranked, 1):
        lines.append(
            f"| {i} | {r.model} | {c.asr_none:.0%} | {c.asr_advisory:.0%} "
            f"| {c.asr_enforced:.0%} | {c.policy_following_uplift:+.0%} "
            f"| {c.enforcement_uplift:+.0%} | {c.utility_enforced:.0%} "
            f"| {c.over_refusal:.0%} |"
        )

    # Per-category ASR under ADVISORY (where models differ most).
    categories = sorted(
        {res.category for r, _ in cards for res in r.results if not res.benign}
    )
    if categories:
        lines += [
            "",
            "## Attack Success Rate by category — advisory posture (policy stated, not enforced)",
            "",
            "| Category | " + " | ".join(r.model for r, _ in cards) + " |",
            "|---|" + "|".join(["---:"] * len(cards)) + "|",
        ]
        for cat in categories:
            cells = []
            for r, _ in cards:
                rs = [x for x in r.results if x.category == cat and not x.benign]
                val = sum(x.rate_advisory for x in rs) / len(rs) if rs else 0.0
                cells.append(f"{val:.0%}")
            lines.append(f"| {cat} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _scorecard_dict(c: Scorecard) -> dict:
    return {
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
    }


def render_json(reports: list[ModelReport], trials: int) -> str:
    payload = {"trials": trials, "models": []}
    for r in reports:
        payload["models"].append(
            {
                "model": r.model,
                "scorecard": _scorecard_dict(r.scorecard()),
                "categories": [
                    {
                        "category": cs.category,
                        "n_scenarios": cs.n_scenarios,
                        "asr_none": cs.asr_none,
                        "asr_advisory": cs.asr_advisory,
                        "asr_enforced": cs.asr_enforced,
                    }
                    for cs in r.categories()
                ],
                "scenarios": [
                    {
                        "scenario_id": x.scenario_id,
                        "category": x.category,
                        "benign": x.benign,
                        "n_trials": x.n_trials,
                        "rate_none": x.rate_none,
                        "rate_advisory": x.rate_advisory,
                        "rate_enforced": x.rate_enforced,
                        "errors": x.errors,
                    }
                    for x in r.results
                ],
            }
        )
    return json.dumps(payload, indent=2)


def load_models_config(path: str) -> list[dict]:
    """Load a models config: ``{"models": [{"name", "base_url", "api_key"|"api_key_env"}]}``."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    models = data.get("models", [])
    if not models:
        raise ValueError(f"no 'models' entries found in {path}")
    return models
