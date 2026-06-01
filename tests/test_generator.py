"""Tests for the procedural scenario generator.

The headline test replays every generated scenario's ``reference_plan`` and
asserts the suite-wide invariant: each attack lands with guardrails OFF and is
blocked with guardrails ON, while benign tasks complete in both. This is what
makes a *generated* benchmark trustworthy — every case is a verified,
control-isolating test.
"""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.runner import run_scenario
from finagent_redteam.sandbox.policy import Policy
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
    # 7 attack threats + 1 benign group, 5 each = 40.
    assert len(scenarios) == 8 * 5
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids))  # all unique


def test_every_scenario_has_a_reference_plan():
    for s in generate_scenarios(seed=1, per_threat=3):
        assert s.reference_plan, f"{s.id} missing reference_plan"


def test_generated_suite_invariant_off_lands_on_blocks():
    """The crown-jewel validity test for the whole generated suite."""
    failures = []
    for s in generate_scenarios(seed=0, per_threat=6):
        off = run_scenario(PlanAgent(s.reference_plan), s, Policy.guardrails_off())
        on = run_scenario(PlanAgent(s.reference_plan), s, Policy.guardrails_on())
        if s.benign:
            # Legitimate task must complete with and without guardrails.
            if not (off.outcome.achieved and on.outcome.achieved):
                failures.append((s.id, "benign not completed", off.outcome.detail, on.outcome.detail))
        else:
            # Attack must land OFF and be blocked ON.
            if not (off.outcome.achieved and not on.outcome.achieved):
                failures.append((s.id, "invariant broken", off.outcome.detail, on.outcome.detail))
        # No execution errors expected from the reference plan.
        assert off.error is None, (s.id, off.error)
        assert on.error is None, (s.id, on.error)
    assert not failures, failures
