"""Deterministic, fully synthetic financial sandbox. No real money, no network.

The sandbox is the trusted ground truth: tools mutate :class:`World` state and a
:class:`Policy` decides which actions are allowed. Because everything here is
deterministic, the evaluator can judge attack success by inspecting final state.
"""

from finagent_redteam.sandbox.policy import Policy
from finagent_redteam.sandbox.state import Account, Email, Payee, Transfer, World
from finagent_redteam.sandbox.tools import TOOLS, ToolError, dispatch, tool_specs

__all__ = [
    "Account",
    "Email",
    "Payee",
    "Transfer",
    "World",
    "Policy",
    "TOOLS",
    "ToolError",
    "dispatch",
    "tool_specs",
]
