"""Inspect AI custom solver for FinAgent.

The ``finagent_agent`` solver does three things per sample:

1. Creates a fresh ``World`` from the scenario's ``world_factory`` (looked up
   from the module-level registry populated when the dataset was built).
2. Creates a ``Policy`` for the requested ``ControlPosture``.
3. Binds the sandbox tools to that (world, policy) pair and runs an Inspect
   ``react()`` agent loop — the same LLM → tool-call → result → LLM loop as the
   standalone runner, but driven entirely by Inspect.

The World is stored in ``TaskState.store["world"]`` so ``finagent_scorer``
can read it after the loop completes.

``SCENARIO_REGISTRY`` is populated by ``_build_dataset`` (in inspect_task.py).
It maps scenario_id → world_factory callable.  Keeping it at module level means
it survives across the solver coroutines that Inspect may run concurrently;
each sample gets its own World instance, so there is no shared mutable state.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from finagent_redteam.runner import SYSTEM_PROMPT_NONE, SYSTEM_PROMPT_POLICY
from finagent_redteam.sandbox.policy import ControlPosture, Policy

# Populated by _build_dataset() before inspect eval runs.
SCENARIO_REGISTRY: dict[str, Callable[[], Any]] = {}


def _system_prompt(posture: ControlPosture) -> str:
    return SYSTEM_PROMPT_NONE if posture is ControlPosture.NONE else SYSTEM_PROMPT_POLICY


def finagent_agent(posture: ControlPosture, max_steps: int = 10):  # type: ignore[return]
    """Return an Inspect ``Solver`` that runs the FinAgent sandbox for one sample."""
    from inspect_ai.solver import Generate, TaskState, react, solver, system_message  # type: ignore[import-untyped]

    from finagent_redteam.inspect_tools import make_sandbox_tools

    @solver
    def _agent(max_steps: int = max_steps) -> Any:  # type: ignore[return]
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            meta: dict = state.metadata or {}
            scenario_id: str = meta.get("scenario_id", "")

            factory = SCENARIO_REGISTRY.get(scenario_id)
            if factory is None:
                # Should never happen; guard against misconfigured dataset.
                state.completed = True
                return state

            world = factory()
            policy = Policy.for_posture(posture)

            # Persist world in store for the scorer.
            state.store.set("world", world)

            # Build tools bound to this sample's world+policy.
            tools = make_sandbox_tools(world, policy)

            # Inject the posture-appropriate system message, then run ReAct loop.
            sys_msg = system_message(_system_prompt(posture))
            agent_loop = react(
                tools=tools,
                max_attempts=max_steps,
            )
            state = await sys_msg(state, generate)
            state = await agent_loop(state, generate)
            return state

        return solve

    return _agent()
