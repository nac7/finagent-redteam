"""Inspect AI ``@task`` entry points for FinAgent Red-Team.

Three tasks are exposed — one per control posture — so the Inspect CLI can run
any posture in isolation and results can be compared across them:

    inspect eval finagent_redteam/inspect_task.py@finagent_none
    inspect eval finagent_redteam/inspect_task.py@finagent_advisory
    inspect eval finagent_redteam/inspect_task.py@finagent_enforced

Each task uses the procedural generator (seeded for reproducibility) and the
same deterministic scorer. Posture differentiation is handled by the solver.

Reproduce the standalone leaderboard results inside Inspect::

    inspect eval finagent_redteam/inspect_task.py@finagent_advisory \\
        --model openai/gpt-4o \\
        --limit 48

Registration in ``inspect_evals`` (once an arXiv preprint and PyPI release
exist) should reference this file as ``task_path``.
"""

from __future__ import annotations

from finagent_redteam.inspect_scorer import finagent_scorer
from finagent_redteam.inspect_solver import SCENARIO_REGISTRY, finagent_agent
from finagent_redteam.sandbox.policy import ControlPosture
from finagent_redteam.scenarios import generate_scenarios, get_all_scenarios
from finagent_redteam.scenarios.schema import Scenario


def _build_dataset(scenarios: list[Scenario], posture: ControlPosture) -> list:
    """Build an Inspect ``Sample`` list and populate the scenario registry."""
    from inspect_ai.dataset import Sample  # type: ignore[import-untyped]

    samples = []
    for s in scenarios:
        SCENARIO_REGISTRY[s.id] = s.world_factory
        attack_goal = (
            {"kind": s.attack_goal.kind, "params": s.attack_goal.params}
            if s.attack_goal else None
        )
        success_goal = (
            {"kind": s.success_goal.kind, "params": s.success_goal.params}
            if s.success_goal else None
        )
        samples.append(Sample(
            input=s.user_task,
            target="achieved" if not s.benign else "completed",
            id=f"{s.id}_{posture.value}",
            metadata={
                "scenario_id": s.id,
                "category": s.category,
                "benign": s.benign,
                "posture": posture.value,
                "attack_goal": attack_goal,
                "success_goal": success_goal,
            },
        ))
    return samples


def _make_task(posture: ControlPosture, per_threat: int, seed: int,
               suite: str, max_steps: int):  # type: ignore[return]
    """Internal factory called by each @task function."""
    from inspect_ai import Task  # type: ignore[import-untyped]

    scenarios = (
        generate_scenarios(seed=seed, per_threat=per_threat)
        if suite == "generated"
        else get_all_scenarios()
    )
    dataset = _build_dataset(scenarios, posture)

    return Task(
        dataset=dataset,
        solver=finagent_agent(posture, max_steps=max_steps),
        scorer=finagent_scorer(),
        metadata={
            "posture": posture.value,
            "suite": suite,
            "per_threat": per_threat,
            "seed": seed,
        },
    )


# --------------------------------------------------------------------------- #
# Public @task entry points — one per posture
# --------------------------------------------------------------------------- #
def _task_decorator():  # type: ignore[return]
    """Lazy import so the module loads without inspect_ai installed."""
    from inspect_ai import task  # type: ignore[import-untyped]
    return task


def finagent_none(
    per_threat: int = 6,
    seed: int = 0,
    suite: str = "generated",
    max_steps: int = 10,
):
    """FinAgent — no policy stated (intrinsic susceptibility).

    Measures whether the model resists regulatory-control bypass attacks when
    no compliance policy is mentioned in the system prompt.
    """
    return _make_task(ControlPosture.NONE, per_threat, seed, suite, max_steps)


def finagent_advisory(
    per_threat: int = 6,
    seed: int = 0,
    suite: str = "generated",
    max_steps: int = 10,
):
    """FinAgent — advisory posture (policy stated, not enforced).

    Measures whether the model follows stated compliance obligations (allow-list,
    sanctions screening, dual-approval, DLP) even when the system does not hard-
    block violations. This is the primary model-differentiating metric.
    """
    return _make_task(ControlPosture.ADVISORY, per_threat, seed, suite, max_steps)


def finagent_enforced(
    per_threat: int = 6,
    seed: int = 0,
    suite: str = "generated",
    max_steps: int = 10,
):
    """FinAgent — enforced posture (system hard-blocks violations).

    Measures residual attack success rate after sandbox compliance controls are
    active. Expected to be near zero for all models (the benchmark uses this as
    a sanity check and to measure over-refusal on benign tasks).
    """
    return _make_task(ControlPosture.ENFORCED, per_threat, seed, suite, max_steps)


# Register with Inspect if available.
try:
    from inspect_ai import task as _task_dec  # type: ignore[import-untyped]
    finagent_none = _task_dec(finagent_none)  # type: ignore[assignment]
    finagent_advisory = _task_dec(finagent_advisory)  # type: ignore[assignment]
    finagent_enforced = _task_dec(finagent_enforced)  # type: ignore[assignment]
except ImportError:
    pass
