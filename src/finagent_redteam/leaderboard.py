"""Multi-model leaderboard.

Runs the scenario suite across several models, each scenario repeated for
``trials`` independent runs (models are stochastic, so a single run is not a
defensible measurement), and aggregates into a ranked leaderboard plus a
per-threat-category attack-success matrix.

Aggregation and rendering are pure and offline-testable; only the agent drivers
touch a model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from finagent_redteam.agent.base import AgentModel
from finagent_redteam.eval.metrics import (
    CategoryStat,
    Scorecard,
    build_scorecard,
    category_breakdown,
)
from finagent_redteam.runner import run_scenario
from finagent_redteam.sandbox.policy import Policy
from finagent_redteam.scenarios.schema import Scenario

AgentFactory = Callable[[], AgentModel]


@dataclass
class ScenarioTrialResult:
    scenario_id: str
    category: str
    benign: bool
    n_trials: int
    successes_off: int
    successes_on: int
    errors: int = 0

    @property
    def rate_off(self) -> float:
        return self.successes_off / self.n_trials if self.n_trials else 0.0

    @property
    def rate_on(self) -> float:
        return self.successes_on / self.n_trials if self.n_trials else 0.0


@dataclass
class ModelReport:
    model: str
    results: list[ScenarioTrialResult] = field(default_factory=list)

    def scorecard(self) -> Scorecard:
        return build_scorecard(self.model, self.results)

    def categories(self) -> list[CategoryStat]:
        return category_breakdown(self.results)


def run_scenario_trials(
    agent_factory: AgentFactory,
    scenario: Scenario,
    trials: int = 1,
    max_steps: int = 8,
) -> ScenarioTrialResult:
    """Run one scenario ``trials`` times with guardrails off and on.

    ``agent_factory`` is called once per run so stateful drivers (e.g. a scripted
    test agent) get a fresh instance; for real, stateless model drivers it can
    simply return the same agent.
    """
    succ_off = succ_on = errors = 0
    for _ in range(trials):
        off = run_scenario(agent_factory(), scenario, Policy.guardrails_off(), max_steps)
        on = run_scenario(agent_factory(), scenario, Policy.guardrails_on(), max_steps)
        errors += bool(off.error) + bool(on.error)
        succ_off += int(off.outcome.achieved)
        succ_on += int(on.outcome.achieved)
    return ScenarioTrialResult(
        scenario_id=scenario.id,
        category=scenario.category,
        benign=scenario.benign,
        n_trials=trials,
        successes_off=succ_off,
        successes_on=succ_on,
        errors=errors,
    )


def run_model(
    model: str,
    agent_factory: AgentFactory,
    scenarios: list[Scenario],
    trials: int = 1,
    max_steps: int = 8,
) -> ModelReport:
    results = [
        run_scenario_trials(agent_factory, s, trials=trials, max_steps=max_steps)
        for s in scenarios
    ]
    return ModelReport(model=model, results=results)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_markdown(reports: list[ModelReport], trials: int) -> str:
    cards = [(r, r.scorecard()) for r in reports]
    # Rank by residual risk after controls (ASR on), then by intrinsic
    # susceptibility (ASR off) — which is the metric that actually varies by
    # model when controls are deterministically enforced — then by utility.
    ranked = sorted(
        cards,
        key=lambda rc: (
            rc[1].asr_guardrails_on,
            rc[1].asr_guardrails_off,
            -rc[1].utility_guardrails_on,
        ),
    )

    lines = [
        "# FinAgent Red-Team Leaderboard",
        "",
        f"Trials per scenario: **{trials}**. Lower ASR and higher utility are better.",
        "",
        "| Rank | Model | ASR off | ASR on | Defense efficacy | Utility on | Over-refusal |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for i, (r, c) in enumerate(ranked, 1):
        lines.append(
            f"| {i} | {r.model} | {c.asr_guardrails_off:.0%} | {c.asr_guardrails_on:.0%} "
            f"| {c.defense_efficacy:+.0%} | {c.utility_guardrails_on:.0%} "
            f"| {c.over_refusal_cost:.0%} |"
        )

    # Per-category ASR matrix (guardrails on) — attack categories only.
    categories = sorted(
        {res.category for r, _ in cards for res in r.results if not res.benign}
    )
    if categories:
        lines += [
            "",
            "## Attack Success Rate by category (guardrails ON)",
            "",
            "| Category | " + " | ".join(r.model for r, _ in cards) + " |",
            "|---|" + "|".join(["---:"] * len(cards)) + "|",
        ]
        for cat in categories:
            cells = []
            for r, _ in cards:
                rs = [x for x in r.results if x.category == cat and not x.benign]
                val = sum(x.rate_on for x in rs) / len(rs) if rs else 0.0
                cells.append(f"{val:.0%}")
            lines.append(f"| {cat} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_json(reports: list[ModelReport], trials: int) -> str:
    payload = {"trials": trials, "models": []}
    for r in reports:
        c = r.scorecard()
        payload["models"].append(
            {
                "model": r.model,
                "scorecard": {
                    "asr_guardrails_off": c.asr_guardrails_off,
                    "asr_guardrails_on": c.asr_guardrails_on,
                    "utility_guardrails_off": c.utility_guardrails_off,
                    "utility_guardrails_on": c.utility_guardrails_on,
                    "defense_efficacy": c.defense_efficacy,
                    "over_refusal_cost": c.over_refusal_cost,
                },
                "categories": [
                    {
                        "category": cs.category,
                        "n_scenarios": cs.n_scenarios,
                        "asr_off": cs.asr_off,
                        "asr_on": cs.asr_on,
                    }
                    for cs in r.categories()
                ],
                "scenarios": [
                    {
                        "scenario_id": x.scenario_id,
                        "category": x.category,
                        "benign": x.benign,
                        "n_trials": x.n_trials,
                        "rate_off": x.rate_off,
                        "rate_on": x.rate_on,
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
