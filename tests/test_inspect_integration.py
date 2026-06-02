"""Offline tests for the Inspect AI integration layer.

These tests verify the integration logic without requiring ``inspect_ai``
to be installed — they mock the Inspect imports and test the dataset
building, scorer logic, and tool dispatch that FinAgent adds on top of
its existing deterministic core.
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from finagent_redteam.sandbox.policy import ControlPosture, Policy
from finagent_redteam.sandbox.state import Account, Payee, World
from finagent_redteam.scenarios.builtin import SCN_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Helpers to mock inspect_ai without installing it
# ---------------------------------------------------------------------------

def _mock_inspect():
    """Register a minimal inspect_ai stub so integration modules can import."""
    if "inspect_ai" in sys.modules:
        return  # already installed or mocked

    pkg = types.ModuleType("inspect_ai")
    pkg.task = lambda f: f
    pkg.Task = MagicMock

    dataset_mod = types.ModuleType("inspect_ai.dataset")
    dataset_mod.Sample = MagicMock

    tool_mod = types.ModuleType("inspect_ai.tool")
    # @tool must return a factory (callable -> Tool-like)
    tool_mod.tool = lambda f: (lambda *a, **kw: MagicMock(name=f.__name__))
    tool_mod.ToolResult = str

    scorer_mod = types.ModuleType("inspect_ai.scorer")
    scorer_mod.Score = MagicMock
    scorer_mod.Scorer = MagicMock
    scorer_mod.accuracy = MagicMock(return_value=[])
    scorer_mod.scorer = lambda **kw: (lambda f: f)

    solver_mod = types.ModuleType("inspect_ai.solver")
    solver_mod.TaskState = MagicMock
    solver_mod.Generate = MagicMock
    solver_mod.react = MagicMock(return_value=MagicMock())
    solver_mod.solver = lambda f: f
    solver_mod.system_message = MagicMock()

    for name, mod in [
        ("inspect_ai", pkg),
        ("inspect_ai.dataset", dataset_mod),
        ("inspect_ai.tool", tool_mod),
        ("inspect_ai.scorer", scorer_mod),
        ("inspect_ai.solver", solver_mod),
    ]:
        sys.modules[name] = mod


# ---------------------------------------------------------------------------
# Tool dispatch tests (no inspect_ai needed at this level)
# ---------------------------------------------------------------------------

def _world_with_payee(allowlisted: bool = True) -> World:
    w = World()
    w.accounts["a"] = Account("a", "Acme", 100_000.0)
    w.payees["p"] = Payee("p", "Vendor", "123", allowlisted=allowlisted)
    return w


def test_inspect_tools_initiate_transfer_returns_json():
    _mock_inspect()
    from finagent_redteam.inspect_tools import make_sandbox_tools

    world = _world_with_payee()
    policy = Policy.for_posture(ControlPosture.ENFORCED)
    tools = make_sandbox_tools(world, policy)
    # Tools are MagicMock instances under the stub; just verify creation succeeds.
    assert isinstance(tools, list)
    assert len(tools) == 11  # 11 sandbox tools exposed


def test_inspect_tools_sandbox_dispatch_executes():
    """Verify the sandbox dispatch works even without inspect_ai installed.

    We call the underlying sandbox function directly to test dispatch logic.
    """
    import finagent_redteam.sandbox.tools as _st

    world = _world_with_payee()
    policy = Policy.for_posture(ControlPosture.ENFORCED)  # hard-blocks non-allowlisted

    # Small transfer to allowlisted payee should execute.
    res = _st.initiate_transfer(world, policy, "agent",
                                from_account="a", to_payee="p", amount=500.0)
    assert res["status"] == "executed"

    # Non-allowlisted payee blocked under ENFORCED policy.
    world2 = _world_with_payee(allowlisted=False)
    res2 = _st.initiate_transfer(world2, policy, "agent",
                                 from_account="a", to_payee="p", amount=500.0)
    assert res2["status"] == "blocked"


# ---------------------------------------------------------------------------
# Scorer logic tests
# ---------------------------------------------------------------------------

def test_scorer_returns_1_when_attack_achieved():
    _mock_inspect()

    # Import scorer module after mock is in place
    if "finagent_redteam.inspect_scorer" in sys.modules:
        del sys.modules["finagent_redteam.inspect_scorer"]

    from inspect_ai.scorer import Score  # type: ignore[import-untyped]

    from finagent_redteam.eval.evaluator import GoalOutcome

    # Directly test the scoring predicate logic.
    from finagent_redteam.eval.evaluator import evaluate_goal
    from finagent_redteam.sandbox.state import Transfer
    from finagent_redteam.scenarios.schema import AttackGoal

    world = World()
    world.transfers["t"] = Transfer("t", "a", "attacker", 500.0, "executed", "agent")
    goal = AttackGoal("unauthorized_transfer", {"to_payee": "attacker"})
    outcome = evaluate_goal(world, goal)
    assert outcome.achieved is True


def test_scorer_returns_0_when_attack_blocked():
    from finagent_redteam.eval.evaluator import evaluate_goal
    from finagent_redteam.sandbox.state import Transfer
    from finagent_redteam.scenarios.schema import AttackGoal

    world = World()
    world.transfers["t"] = Transfer("t", "a", "attacker", 500.0, "blocked", "agent")
    goal = AttackGoal("unauthorized_transfer", {"to_payee": "attacker"})
    outcome = evaluate_goal(world, goal)
    assert outcome.achieved is False


# ---------------------------------------------------------------------------
# Dataset building tests
# ---------------------------------------------------------------------------

def test_build_dataset_populates_registry():
    _mock_inspect()

    if "finagent_redteam.inspect_task" in sys.modules:
        del sys.modules["finagent_redteam.inspect_task"]

    from finagent_redteam.inspect_solver import SCENARIO_REGISTRY
    from finagent_redteam.inspect_task import _build_dataset
    from finagent_redteam.scenarios.builtin import BUILTIN_SCENARIOS

    SCENARIO_REGISTRY.clear()
    _build_dataset(BUILTIN_SCENARIOS, ControlPosture.ADVISORY)

    # Every scenario should be registered.
    for s in BUILTIN_SCENARIOS:
        assert s.id in SCENARIO_REGISTRY, f"{s.id} missing from registry"


def test_scenario_registry_world_factory_creates_fresh_world():
    """Each call to the factory should return an independent World."""
    from finagent_redteam.inspect_solver import SCENARIO_REGISTRY
    from finagent_redteam.inspect_task import _build_dataset
    from finagent_redteam.scenarios.builtin import BUILTIN_SCENARIOS

    SCENARIO_REGISTRY.clear()
    _build_dataset(BUILTIN_SCENARIOS, ControlPosture.ADVISORY)

    sid = BUILTIN_SCENARIOS[0].id
    factory = SCENARIO_REGISTRY[sid]
    w1 = factory()
    w2 = factory()
    assert w1 is not w2, "world_factory must return a new World each call"
