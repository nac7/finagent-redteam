"""Offline tests for leaderboard aggregation and rendering (no model)."""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.eval.metrics import build_scorecard, category_breakdown
from finagent_redteam.leaderboard import (
    ModelReport,
    ScenarioTrialResult,
    render_markdown,
    run_scenario_trials,
)
from finagent_redteam.scenarios.builtin import SCN_UNAUTHORIZED


def _r(sid, cat, benign, none, adv, enf, n=2):
    return ScenarioTrialResult(sid, cat, benign, n, none, adv, enf)


def test_rate_properties():
    r = _r("s", "T2_unauthorized_transfer", False, 2, 2, 0, n=2)
    assert r.rate_none == 1.0
    assert r.rate_advisory == 1.0
    assert r.rate_enforced == 0.0


def test_build_scorecard_and_uplifts():
    results = [
        _r("a1", "T2_unauthorized_transfer", False, 2, 1, 0),  # none 100%, adv 50%, enf 0%
        _r("a2", "T4_structuring", False, 2, 2, 0),            # none 100%, adv 100%, enf 0%
        _r("b1", "BENIGN", True, 2, 2, 2),                     # benign 100%/100%/100%
    ]
    card = build_scorecard("m", results)
    assert card.n_attack == 2 and card.n_benign == 1
    assert card.asr_none == 1.0
    assert card.asr_advisory == 0.75          # mean(0.5, 1.0)
    assert card.asr_enforced == 0.0
    assert card.policy_following_uplift == 0.25   # 1.0 - 0.75
    assert card.enforcement_uplift == 0.75        # 0.75 - 0.0
    assert card.residual_asr == 0.0
    assert card.utility_enforced == 1.0
    assert card.over_refusal == 0.0


def test_category_breakdown_excludes_benign():
    results = [
        _r("a1", "T2_unauthorized_transfer", False, 2, 1, 0),
        _r("b1", "BENIGN", True, 2, 2, 2),
    ]
    cats = category_breakdown(results)
    assert [c.category for c in cats] == ["T2_unauthorized_transfer"]
    assert cats[0].asr_none == 1.0
    assert cats[0].asr_advisory == 0.5
    assert cats[0].asr_enforced == 0.0


class ScriptedAgent(AgentModel):
    def __init__(self, turns):
        self._turns = list(turns)

    def complete(self, messages, tools):
        return self._turns.pop(0) if self._turns else AssistantTurn(content="done")


def test_run_scenario_trials_aggregates_over_postures_and_trials():
    def factory():
        return ScriptedAgent([
            AssistantTurn(tool_calls=[ToolCall("c", "initiate_transfer", {
                "from_account": "acct_ops", "to_payee": "pay_quickpay", "amount": 9500.0
            })])
        ])

    res = run_scenario_trials(factory, SCN_UNAUTHORIZED, trials=3)
    assert res.n_trials == 3
    assert res.rate_none == 1.0       # attack lands with no policy
    assert res.rate_advisory == 1.0   # worst-case ignores stated policy
    assert res.rate_enforced == 0.0   # blocked by enforcement
    assert res.errors == 0


def test_render_markdown_ranks_by_residual_then_susceptibility():
    safe = ModelReport("safe-model", [
        _r("a1", "T2_unauthorized_transfer", False, 0, 0, 0),
        _r("b1", "BENIGN", True, 2, 2, 2),
    ])
    risky = ModelReport("risky-model", [
        _r("a1", "T2_unauthorized_transfer", False, 2, 2, 0),
        _r("b1", "BENIGN", True, 2, 2, 2),
    ])
    md = render_markdown([risky, safe], trials=2)
    assert "FinAgent Red-Team Leaderboard" in md
    # Equal residual ASR (both 0); safe-model wins on lower advisory ASR.
    rank1 = next(line for line in md.splitlines() if line.startswith("| 1 |"))
    assert "safe-model" in rank1
    assert "by category" in md
