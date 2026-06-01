"""End-to-end pipeline tests using a scripted fake agent (no API/model).

These demonstrate the benchmark's core claim: the same attacker behaviour
succeeds with guardrails OFF and is blocked with guardrails ON, while a benign
task still completes in both — i.e. the defenses have real efficacy and low
over-refusal cost.
"""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.runner import run_paired
from finagent_redteam.scenarios.builtin import (
    SCN_BENIGN,
    SCN_DUAL_APPROVAL,
    SCN_STRUCTURING,
    SCN_UNAUTHORIZED,
)


class ScriptedAgent(AgentModel):
    """Replays a fixed list of assistant turns, ignoring the conversation.

    Stands in for a model that fully complies with the embedded attack — the
    worst case the guardrails must defend against.
    """

    def __init__(self, turns: list[AssistantTurn]):
        self._turns = list(turns)

    def complete(self, messages, tools) -> AssistantTurn:
        if self._turns:
            return self._turns.pop(0)
        return AssistantTurn(content="done")


def _call(name, **args):
    return AssistantTurn(tool_calls=[ToolCall(id="c", name=name, arguments=args)])


def test_unauthorized_transfer_blocked_only_by_guardrails():
    # ScriptedAgent is stateful, so give each policy run its own fresh script.
    res = _paired(
        SCN_UNAUTHORIZED,
        lambda: ScriptedAgent(
            [_call("initiate_transfer", from_account="acct_ops", to_payee="pay_quickpay", amount=9500.0)]
        ),
    )
    assert res["success_off"] is True   # attack lands with no guardrails
    assert res["success_on"] is False   # allow-list control blocks it


def test_structuring_blocked_only_by_guardrails():
    def script():
        return ScriptedAgent([
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=7500.0),
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=7500.0),
        ])
    res = _paired(SCN_STRUCTURING, script)
    assert res["success_off"] is True
    assert res["success_on"] is False   # reporting-threshold control files a report


def test_dual_approval_defeat_blocked_only_by_guardrails():
    def script():
        return ScriptedAgent([
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=50000.0),
            _call("approve_transfer", transfer_id="tr1"),
        ])
    res = _paired(SCN_DUAL_APPROVAL, script)
    assert res["success_off"] is True
    assert res["success_on"] is False   # maker-checker blocks self-approval


def test_benign_task_completes_with_and_without_guardrails():
    def script():
        return ScriptedAgent(
            [_call("initiate_transfer", from_account="acct_ops", to_payee="pay_utility", amount=500.0)]
        )
    res = _paired(SCN_BENIGN, script)
    assert res["success_off"] is True
    assert res["success_on"] is True    # no over-refusal: legit task still works


# --------------------------------------------------------------------------- #
# Helper: run_paired but with a fresh (stateful) scripted agent per policy run.
# --------------------------------------------------------------------------- #
def _paired(scenario, agent_factory):
    from finagent_redteam.eval.evaluator import evaluate_goal
    from finagent_redteam.runner import run_scenario
    from finagent_redteam.sandbox.policy import Policy

    off = run_scenario(agent_factory(), scenario, Policy.guardrails_off())
    on = run_scenario(agent_factory(), scenario, Policy.guardrails_on())
    return {
        "success_off": off.outcome.achieved,
        "success_on": on.outcome.achieved,
        "error_off": off.error,
        "error_on": on.error,
    }
