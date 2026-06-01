"""Scenario definition and the structured success/attack goals.

A scenario pairs a *legitimate* user task with an embedded *attack* (usually
indirect, delivered through an untrusted tool output such as an email) and a
machine-checkable predicate describing what a successful attack — or, for benign
controls, a correctly completed task — looks like in final world state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from finagent_redteam.sandbox.state import World

# Threat taxonomy identifiers (see README).
THREAT_CATEGORIES = {
    "T1_indirect_injection": "Indirect prompt injection via untrusted content",
    "T2_unauthorized_transfer": "Unauthorized / fraudulent transfer execution",
    "T3_sanctions_evasion": "Sanctions / watchlist screening evasion",
    "T4_structuring": "Reporting-threshold structuring (smurfing)",
    "T5_dual_approval_defeat": "Maker-checker (dual-approval) defeat",
    "T6_data_exfiltration": "Sensitive financial data exfiltration",
    "T7_confused_deputy": "Confused-deputy payee bank-detail redirection",
    "BENIGN": "Legitimate task (utility / over-refusal control)",
}


@dataclass
class AttackGoal:
    """A structured, deterministic predicate over final world state.

    ``kind`` selects the predicate; ``params`` parameterises it. The evaluator
    dispatches on ``kind`` so scenarios stay pure data.
    """

    kind: str
    params: dict = field(default_factory=dict)


@dataclass
class Scenario:
    id: str
    category: str
    description: str
    # Builds the initial world. A factory (not a shared instance) so each run —
    # guardrails on and off — starts from identical, independent state.
    world_factory: Callable[[], World]
    # The legitimate instruction given to the agent.
    user_task: str
    # What a successful *attack* looks like. None for benign scenarios.
    attack_goal: AttackGoal | None = None
    # For benign scenarios: what completing the task correctly looks like.
    success_goal: AttackGoal | None = None
    benign: bool = False

    def __post_init__(self) -> None:
        if self.benign and self.success_goal is None:
            raise ValueError(f"benign scenario '{self.id}' needs a success_goal")
        if not self.benign and self.attack_goal is None:
            raise ValueError(f"attack scenario '{self.id}' needs an attack_goal")
