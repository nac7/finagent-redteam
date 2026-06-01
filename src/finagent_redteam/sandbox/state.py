"""Synthetic world state for the financial sandbox."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Account:
    id: str
    owner: str
    balance: float
    currency: str = "USD"


@dataclass
class Payee:
    id: str
    name: str
    account_number: str
    # Allow-listed payees are pre-approved counterparties (e.g. known vendors).
    allowlisted: bool = False
    # Ground-truth sanctions status (the agent does not see this directly; it
    # must screen). Used by the sandbox and evaluator, never leaked to the model.
    sanctioned: bool = False


@dataclass
class Transfer:
    id: str
    from_account: str
    to_payee: str
    amount: float
    status: str  # "pending" | "executed" | "blocked"
    initiated_by: str
    approved_by: str | None = None
    blocked_reason: str | None = None


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str
    # If True, this message originates from an untrusted external party and is a
    # potential indirect-prompt-injection vector (the agent should not treat its
    # contents as authoritative instructions).
    untrusted: bool = False


@dataclass
class ComplianceReport:
    kind: str  # e.g. "CTR" (currency transaction report), "SAR"
    payee: str
    amount: float
    note: str = ""


@dataclass
class World:
    """The full mutable state the sandbox tools operate on."""

    accounts: dict[str, Account] = field(default_factory=dict)
    payees: dict[str, Payee] = field(default_factory=dict)
    transfers: dict[str, Transfer] = field(default_factory=dict)
    inbox: list[Email] = field(default_factory=list)
    # Compliance reports filed (e.g. structuring/over-threshold detection).
    reports: list[ComplianceReport] = field(default_factory=list)
    # Append-only log of every tool action, for transcripts and debugging.
    audit_log: list[dict] = field(default_factory=list)
    # Data the agent sent to an external recipient (exfiltration channel).
    exfiltrated: list[str] = field(default_factory=list)
    _counter: int = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def log(self, action: str, **details) -> None:
        self.audit_log.append({"action": action, **details})

    def executed_transfers_to(self, payee_id: str) -> list[Transfer]:
        return [
            t
            for t in self.transfers.values()
            if t.to_payee == payee_id and t.status == "executed"
        ]
