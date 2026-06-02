"""Tests for the procedural scenario generator.

The headline test replays every generated scenario's ``reference_plan`` under all
three control postures and asserts the suite-wide invariant: each attack lands
under NONE and ADVISORY and is blocked under ENFORCED, while benign tasks
complete under all three. This is what makes a *generated* benchmark
trustworthy — every case is a verified, control-isolating test.
"""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.runner import run_postures
from finagent_redteam.scenarios.generator import generate_scenarios


class PlanAgent(AgentModel):
    """Replays a scenario's reference_plan as a sequence of tool calls."""

    def __init__(self, plan):
        self._turns = [
            AssistantTurn(tool_calls=[ToolCall(f"c{i}", step["name"], step["arguments"])])
            for i, step in enumerate(plan)
        ]

    def complete(self, messages, tools):
        return self._turns.pop(0) if self._turns else AssistantTurn(content="done")


def test_generation_is_deterministic():
    a = generate_scenarios(seed=7, per_threat=4)
    b = generate_scenarios(seed=7, per_threat=4)
    assert [s.id for s in a] == [s.id for s in b]


def test_counts_and_unique_ids():
    scenarios = generate_scenarios(seed=0, per_threat=5)
    assert len(scenarios) == 8 * 5  # 7 attack threats + 1 benign group
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids))


def test_every_scenario_has_a_reference_plan():
    for s in generate_scenarios(seed=1, per_threat=3):
        assert s.reference_plan, f"{s.id} missing reference_plan"


def test_generated_suite_invariant_across_postures():
    """Crown-jewel validity test: replay reference plans under all postures."""
    failures = []
    for s in generate_scenarios(seed=0, per_threat=6):
        res = run_postures(lambda s=s: PlanAgent(s.reference_plan), s)
        if s.benign:
            ok = res["achieved_none"] and res["achieved_advisory"] and res["achieved_enforced"]
        else:
            ok = (
                res["achieved_none"]
                and res["achieved_advisory"]
                and not res["achieved_enforced"]
            )
        if not ok:
            failures.append((s.id, res))
        assert res["error"] is None, (s.id, res["error"])
    assert not failures, failures
