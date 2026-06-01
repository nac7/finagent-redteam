"""Model-agnostic agent interface.

The runner owns the sandbox and the tool-execution loop; an ``AgentModel`` only
has to turn a message list + tool specs into the next assistant turn. This keeps
the whole pipeline testable with a scripted fake model — no API calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class AgentModel(ABC):
    @abstractmethod
    def complete(
        self, messages: list[dict], tools: list[dict]
    ) -> AssistantTurn:  # pragma: no cover
        raise NotImplementedError
