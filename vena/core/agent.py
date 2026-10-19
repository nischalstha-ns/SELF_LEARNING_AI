"""VenaAgent: the main perceive → think → plan → act → verify → learn loop.

Phase 1 skeleton: the class and all six stage methods exist with their final
signatures, wired to the Phase 1 pieces that are real today (config, store,
registry). The intelligent implementations land in later phases:
  - think()   → Phase 2 (core/brain.py: LLM providers + router)
  - perceive()→ Phase 4/5 (perception/, voice/)
  - plan()/act()/verify() → Phase 7 (planner drives the loop)
  - learn()   → Phase 6 (memory/ service)

Until then, run() executes a bounded single pass so the skeleton is runnable
and testable without any later phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .config import Settings
from .logging import get_logger
from .planner import Planner, RouterLike
from .types import AgentEvent, Message, Role
from ..memory.store import Store
from ..tools.registry import ToolRegistry

log = get_logger("agent")


@dataclass
class Observation:
    """Everything the agent knows at the start of a turn."""
    user_text: str
    history: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)  # screen/voice state (later phases)


@dataclass
class Outcome:
    """What happened, for the learn() stage."""
    success: bool
    summary: str
    steps: list[dict[str, Any]] = field(default_factory=list)


class VenaAgent:
    def __init__(self, settings: Optional[Settings] = None,
                 store: Optional[Store] = None,
                 registry: Optional[ToolRegistry] = None,
                 router: Optional[RouterLike] = None,
                 migrations_dir: Optional[str] = None):
        self.settings = settings or Settings()
        # Store is optional: without a migrations dir we run memoryless.
        # (Phase 6 wires the full memory service here.)
        self.store = store
        if self.store is None and migrations_dir:
            self.store = Store(self.settings.db_path, migrations_dir)
        self.registry = registry or (
            ToolRegistry(self.store.conn) if self.store else None)
        self.router = router
        self.planner: Optional[Planner] = None
        if self.router is not None and self.registry is not None:
            self.planner = Planner(self.router, self.registry,
                                   max_iterations=self.settings.max_iterations,
                                   task_timeout_s=self.settings.task_timeout_s)

    # -- the six stages ----------------------------------------------------

    def perceive(self, user_text: str, history: Optional[list[Message]] = None) -> Observation:
        """Gather input: user text now; screen/voice/microphone in later phases."""
        return Observation(user_text=user_text, history=list(history or []))

    def think(self, obs: Observation) -> str:
        """Decide what to do. Phase 2 replaces this stub with the LLM brain."""
        return obs.user_text

    def plan(self, goal: str, history: Optional[list[Message]] = None):
        """Run the bounded planner loop. Yields AgentEvents (Phase 7 owns the logic)."""
        if self.planner is None:
            raise RuntimeError("plan() needs a router (Phase 2, core/brain.py)")
        yield from self.planner.run(goal, history=history)

    def act(self, tool_name: str, arguments: dict[str, Any],
            task_id: Optional[str] = None):
        """Execute one tool call through the permission-gated registry."""
        if self.registry is None:
            raise RuntimeError("act() needs a ToolRegistry (needs a Store)")
        return self.registry.execute(tool_name, arguments, task_id=task_id)

    def verify(self, step_desc: str, result) -> tuple[bool, str]:
        """Independently check a tool result. Phase 7 extends per-tool verifiers."""
        from .planner import verify_step
        from .types import PlanStep
        step = PlanStep(id="adhoc", description=step_desc,
                        tool=getattr(result, "name", None))
        return verify_step(step, result)

    def learn(self, outcome: Outcome) -> None:
        """Record the outcome for future recall. Phase 6 persists to memory."""
        log.info("learn: success=%s summary=%s", outcome.success, outcome.summary[:120])

    # -- main loop ----------------------------------------------------------

    def run(self, user_text: str, history: Optional[list[Message]] = None):
        """One full turn: perceive → think → plan → act → verify → learn.

        Yields AgentEvents; the last one has kind 'done'. In Phase 1 without a
        router this runs the think/act path directly for smoke-testing.
        """
        obs = self.perceive(user_text, history)
        goal = self.think(obs)
        events: list[AgentEvent] = []
        if self.planner is not None:
            for ev in self.plan(goal, history=obs.history):
                events.append(ev)
                yield ev
            done = events[-1]
            outcome = Outcome(success=done.payload.get("status") == "done",
                              summary=done.payload.get("summary", ""),
                              steps=done.payload.get("steps", []))
        else:
            # No brain yet: acknowledge so the skeleton is runnable.
            summary = f"received: {goal}"
            ev = AgentEvent("done", {"status": "done", "summary": summary, "steps": []})
            events.append(ev)
            yield ev
            outcome = Outcome(success=True, summary=summary)
        self.learn(outcome)
