"""OpenAI-compatible agent driver.

Works against any endpoint that speaks the OpenAI chat-completions API with tool
calling: hosted OpenAI, a local vLLM/SGLang server, Ollama's OpenAI shim, etc.
Import is isolated here so the offline core/test-suite never needs ``openai``.

``extra_body`` lets callers pass provider-specific parameters that are not part of
the standard OpenAI schema. The primary use-case is disabling qwen3's chain-of-
thought mode to keep latency manageable:

    OpenAICompatibleAgent("qwen3:8b", extra_body={"think": False})

Ollama forwards unknown top-level keys to the underlying model runner, so this
suppresses the ``<think>...</think>`` prefix that otherwise adds minutes per call.
"""

from __future__ import annotations

import json
import time
from typing import Any

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall

_RETRYABLE = (429, 500, 502, 503, 529)


class OpenAICompatibleAgent(AgentModel):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str = "EMPTY",
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        extra_body: dict[str, Any] | None = None,
    ):
        from openai import OpenAI  # lazy: only needed to actually drive a model

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_body = extra_body or {}

    def complete(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=self.temperature,
                    extra_body=self.extra_body or None,
                )
                msg = resp.choices[0].message
                tool_calls: list[ToolCall] = []
                for tc in msg.tool_calls or []:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(
                        ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                    )
                return AssistantTurn(content=msg.content, tool_calls=tool_calls)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                status = getattr(getattr(e, "response", None), "status_code", None)
                if attempt < self.max_retries and (status in _RETRYABLE or status is None):
                    wait = self.retry_delay * (2 ** attempt)
                    time.sleep(wait)
                else:
                    break
        raise RuntimeError(f"API call failed after {self.max_retries + 1} attempts") \
            from last_exc
