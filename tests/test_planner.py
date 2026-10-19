"""Tests: planner — bounded loop, done/input signals, loop detection, cancel.

The router is faked (FakeRouter satisfies planner.RouterLike); the real
ModelRouter arrives with core/brain.py in Phase 2.
"""
import os
import sqlite3
import unittest

from vena.core.planner import Planner, RouterLike, verify_step
from vena.core.types import (Message, Permission, PlanStep, ProviderResponse,
                             Role, ToolCall, ToolResult, ToolStatus)
from vena.tools.registry import ToolRegistry, ToolSpec

MIGRATIONS = os.path.join(os.path.dirname(__file__), "..", "data", "migrations")


class FakeRouter:
    """Scripted stand-in for the Phase 2 ModelRouter."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def complete(self, messages, tools=None, require_local=False):
        self.calls += 1
        if self.script:
            return self.script.pop(0)
        return ProviderResponse(text="out of script")


def make_planner(script, **kw):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(open(os.path.join(
        os.path.abspath(MIGRATIONS), "001_initial.sql")).read())
    reg = ToolRegistry(conn)
    reg.register(ToolSpec(
        name="get_time", description="clock", schema={"type": "object"},
        handler=lambda a: {"utc": "2026-01-01T00:00:00Z"},
        default_permission=Permission.OBSERVE))
    router = FakeRouter(script)
    assert isinstance(router, RouterLike)  # duck-type contract holds
    planner = Planner(router, reg, max_iterations=kw.get("max_iterations", 8),
                      task_timeout_s=kw.get("task_timeout_s", 30.0))
    return planner, router


def run_all(planner, text, **kw):
    return list(planner.run(text, **kw))


class PlannerTest(unittest.TestCase):
    def test_done_signal(self):
        p, _ = make_planner([ProviderResponse(text="all good")])
        events = run_all(p, "hi")
        done = events[-1]
        self.assertEqual(done.kind, "done")
        self.assertEqual(done.payload["status"], "done")

    def test_tool_then_done(self):
        p, _ = make_planner([
            ProviderResponse(tool_calls=[ToolCall(name="get_time", arguments={})]),
            ProviderResponse(tool_calls=[ToolCall(
                name="planner_control",
                arguments={"action": "done", "summary": "time fetched"})]),
        ])
        events = run_all(p, "what time is it")
        kinds = [e.kind for e in events]
        self.assertIn("tool_call", kinds)
        self.assertIn("tool_result", kinds)
        done = events[-1]
        self.assertEqual(done.payload["status"], "done")
        self.assertEqual(done.payload["summary"], "time fetched")

    def test_need_input_pauses(self):
        p, _ = make_planner([ProviderResponse(
            tool_calls=[ToolCall(name="planner_control",
                                 arguments={"action": "need_input",
                                            "question": "which file?"})])])
        events = run_all(p, "do thing")
        done = events[-1]
        self.assertEqual(done.payload["status"], "awaiting_input")
        self.assertEqual(done.payload["summary"], "which file?")

    def test_loop_detection(self):
        p, _ = make_planner(
            [ProviderResponse(tool_calls=[ToolCall(name="get_time", arguments={})])] * 5,
            max_iterations=8)
        events = run_all(p, "loop me")
        done = events[-1]
        self.assertEqual(done.payload["status"], "failed")
        self.assertIn("loop detected", done.payload["summary"])

    def test_max_iterations(self):
        # get_time with distinct args bypasses loop detection, so the
        # iteration cap is what stops the run.
        p2_router = FakeRouter([
            ProviderResponse(tool_calls=[ToolCall(name="get_time", arguments={"n": i})])
            for i in range(20)])
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(open(os.path.join(
            os.path.abspath(MIGRATIONS), "001_initial.sql")).read())
        reg = ToolRegistry(conn)
        reg.register(ToolSpec(
            name="get_time", description="clock",
            schema={"type": "object",
                    "properties": {"n": {"type": "integer"}}},
            handler=lambda a: {"n": a.get("n")}))
        p2 = Planner(p2_router, reg, max_iterations=3, task_timeout_s=30.0)
        events = list(p2.run("go"))
        done = events[-1]
        self.assertEqual(done.payload["status"], "failed")
        self.assertIn("3 iterations", done.payload["summary"])

    def test_retry_budget(self):
        # Identical tool+args would trip loop detection at 3 repeats, so use
        # max_step_retries=0: the 2nd identical attempt exhausts the budget.
        def fail(a):
            raise RuntimeError("always fails")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(open(os.path.join(
            os.path.abspath(MIGRATIONS), "001_initial.sql")).read())
        reg = ToolRegistry(conn)
        reg.register(ToolSpec(name="flaky", description="f",
                              schema={"type": "object"},
                              handler=fail))
        router = FakeRouter([
            ProviderResponse(tool_calls=[ToolCall(name="flaky", arguments={})])
        ] * 10)
        p = Planner(router, reg, max_iterations=10, task_timeout_s=30.0,
                    max_step_retries=0)
        events = list(p.run("try it"))
        errors = [e for e in events if e.kind == "error"]
        self.assertTrue(any("retry budget exhausted" in e.payload["error"]
                            for e in errors))

    def test_cancel(self):
        p, _ = make_planner([ProviderResponse(
            tool_calls=[ToolCall(name="get_time", arguments={})])] * 10)
        gen = p.run("go")
        first = next(gen)  # status event
        self.assertEqual(first.kind, "status")
        p.cancel()  # user hits stop mid-task
        rest = list(gen)
        self.assertEqual(rest[-1].kind, "done")
        self.assertEqual(rest[-1].payload["status"], "cancelled")

    def test_elevated_denied_without_approver(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(open(os.path.join(
            os.path.abspath(MIGRATIONS), "001_initial.sql")).read())
        reg = ToolRegistry(conn)
        reg.register(ToolSpec(name="danger", description="d",
                              schema={"type": "object"},
                              handler=lambda a: {"x": 1},
                              default_permission=Permission.ELEVATED))
        p = Planner(FakeRouter([
            ProviderResponse(tool_calls=[ToolCall(name="danger", arguments={})])]),
            reg, max_iterations=4, task_timeout_s=30.0)
        events = list(p.run("do danger"))
        done = events[-1]
        self.assertEqual(done.payload["status"], "awaiting_approval")

    def test_verify_step_ok(self):
        step = PlanStep(id="s0", description="t", tool="get_time", arguments={})
        ok, note = verify_step(
            step, ToolResult("c1", "get_time", ToolStatus.OK, data={"utc": "x"}))
        self.assertTrue(ok)

    def test_verify_step_tool_error(self):
        step = PlanStep(id="s0", description="t", tool="get_time", arguments={})
        ok, note = verify_step(
            step, ToolResult("c1", "get_time", ToolStatus.ERROR, error="boom"))
        self.assertFalse(ok)
        self.assertIn("boom", note)


if __name__ == "__main__":
    unittest.main()
