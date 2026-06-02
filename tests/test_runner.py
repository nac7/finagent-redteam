"""End-to-end pipeline tests using a scripted fake agent (no API/model).

For a worst-case agent that fully complies with the embedded attack, the
invariant across postures is: the attack succeeds under NONE and ADVISORY (the
agent ignores stated policy) and is blocked under ENFORCED; benign tasks
complete under all three.
"""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.runner import run_postures
from finagent_redteam.scenarios.builtin import (
    SCN_BENIGN,
    SCN_DUAL_APPROVAL,
    SCN_STRUCTURING,
    SCN_UNAUTHORIZED,
)


class ScriptedAgent(AgentModel):
    """Replays a fixed list of assistant turns, ignoring the conversation."""

    def __init__(self, turns):
        self._turns = list(turns)

    def complete(self, messages, tools) -> AssistantTurn:
        return self._turns.pop(0) if self._turns else AssistantTurn(content="done")


def _call(name, **args):
    return AssistantTurn(tool_calls=[ToolCall(id="c", name=name, arguments=args)])


def _assert_attack_invariant(res):
    assert res["achieved_none"] is True       # lands with no policy stated
    assert res["achieved_advisory"] is True   # worst-case ignores stated policy
    assert res["achieved_enforced"] is False  # blocked by hard enforcement
    assert res["error"] is None


def test_unauthorized_transfer_invariant():
    res = run_postures(
        lambda: ScriptedAgent([_call("initiate_transfer",
                 from_account="acct_ops", to_payee="pay_quickpay", amount=9500.0)]),
        SCN_UNAUTHORIZED,
    )
    _assert_attack_invariant(res)


def test_structuring_invariant():
    res = run_postures(
        lambda: ScriptedAgent([
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=7500.0),
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=7500.0),
        ]),
        SCN_STRUCTURING,
    )
    _assert_attack_invariant(res)


def test_dual_approval_invariant():
    res = run_postures(
        lambda: ScriptedAgent([
            _call("initiate_transfer", from_account="acct_ops", to_payee="pay_globex", amount=50000.0),
            _call("approve_transfer", transfer_id="tr1"),
        ]),
        SCN_DUAL_APPROVAL,
    )
    _assert_attack_invariant(res)


def test_benign_completes_under_all_postures():
    res = run_postures(
        lambda: ScriptedAgent([_call("initiate_transfer",
                 from_account="acct_ops", to_payee="pay_utility", amount=500.0)]),
        SCN_BENIGN,
    )
    assert res["achieved_none"] is True
    assert res["achieved_advisory"] is True
    assert res["achieved_enforced"] is True   # no over-refusal for a legit task
