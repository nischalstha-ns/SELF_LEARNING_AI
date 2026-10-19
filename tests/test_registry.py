"""Tests: tool registry — permissions, validation, audit.

Uses the Vena 001 migration (permission levels observe|safe|execute|elevated).
"""
import os
import sqlite3
import tempfile
import unittest

from vena.core.errors import ToolError, VenaError
from vena.core.types import Permission, ToolResult, ToolStatus
from vena.tools.registry import ToolRegistry, ToolSpec

MIGRATIONS = os.path.join(os.path.dirname(__file__), "..", "data", "migrations")


def make_registry():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(open(os.path.join(
        os.path.abspath(MIGRATIONS), "001_initial.sql")).read())
    return ToolRegistry(conn), conn


def echo_spec(permission=Permission.OBSERVE):
    return ToolSpec(
        name="echo_tool", description="echoes",
        schema={"type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"], "additionalProperties": False},
        handler=lambda a: {"echo": a["text"]},
        default_permission=permission)


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.reg, self.conn = make_registry()
        self.reg.register(echo_spec())

    def test_observe_tool_runs(self):
        r = self.reg.execute("echo_tool", {"text": "hi"})
        self.assertEqual(r.status, ToolStatus.OK)
        self.assertEqual(r.data["echo"], "hi")

    def test_unknown_tool(self):
        r = self.reg.execute("nope", {})
        self.assertEqual(r.status, ToolStatus.ERROR)
        self.assertIn("unknown tool", r.error)

    def test_validation_missing_required(self):
        r = self.reg.execute("echo_tool", {})
        self.assertEqual(r.status, ToolStatus.ERROR)
        self.assertIn("required", r.error)

    def test_validation_wrong_type(self):
        r = self.reg.execute("echo_tool", {"text": 123})
        self.assertEqual(r.status, ToolStatus.ERROR)
        self.assertIn("must be string", r.error)

    def test_validation_extra_arg_rejected(self):
        r = self.reg.execute("echo_tool", {"text": "x", "bogus": 1})
        self.assertEqual(r.status, ToolStatus.ERROR)
        self.assertIn("not allowed", r.error)

    def test_safe_tool_executes(self):
        # SAFE is a real, executable level (reversible actions) — unlike the
        # old suggestion-only level it replaces.
        self.reg.register(ToolSpec(
            name="dry", description="d", schema={"type": "object"},
            handler=lambda a: {"ran": True}, default_permission=Permission.SAFE))
        r = self.reg.execute("dry", {})
        self.assertEqual(r.status, ToolStatus.OK)
        self.assertTrue(r.data["ran"])

    def test_elevated_requires_approver(self):
        self.reg.register(ToolSpec(
            name="danger", description="d", schema={"type": "object"},
            handler=lambda a: {"x": 1}, default_permission=Permission.ELEVATED))
        denied = self.reg.execute("danger", {})
        self.assertEqual(denied.status, ToolStatus.DENIED)
        self.assertTrue(denied.needs_approval)
        allowed = self.reg.execute("danger", {}, approver=lambda n, a: True,
                                   approved_by="test-user")
        self.assertEqual(allowed.status, ToolStatus.OK)

    def test_audit_rows_written(self):
        self.conn.execute("INSERT INTO tasks(id, title) VALUES ('t1','x')")
        self.conn.commit()
        self.reg.execute("echo_tool", {"text": "hi"}, task_id="t1")
        rows = self.conn.execute("SELECT * FROM tool_executions").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tool_name"], "echo_tool")
        self.assertEqual(rows[0]["permission"], "observe")
        audit = self.conn.execute("SELECT * FROM audit_events").fetchall()
        self.assertTrue(any(a["category"] == "tool" for a in audit))

    def test_audit_without_task_row(self):
        # A task_id with no tasks row must not fail the audit insert.
        r = self.reg.execute("echo_tool", {"text": "hi"}, task_id="ghost")
        self.assertEqual(r.status, ToolStatus.OK)
        rows = self.conn.execute("SELECT task_id FROM tool_executions").fetchall()
        self.assertIsNone(rows[0]["task_id"])

    def test_policy_change(self):
        self.reg.set_policy("echo_tool", Permission.ELEVATED)
        r = self.reg.execute("echo_tool", {"text": "hi"})
        self.assertEqual(r.status, ToolStatus.DENIED)
        with self.assertRaises(ToolError):
            self.reg.set_policy("nope", Permission.OBSERVE)

    def test_specs_for_model_includes_safe(self):
        self.reg.register(ToolSpec(
            name="dry", description="d", schema={"type": "object"},
            handler=lambda a: {}, default_permission=Permission.SAFE))
        names = {s["function"]["name"] for s in self.reg.specs_for_model()}
        self.assertIn("echo_tool", names)
        self.assertIn("dry", names)

    def test_validate_raises_for_unknown(self):
        with self.assertRaises(VenaError):
            self.reg.validate("nope", {})

    def test_handler_exception_becomes_error(self):
        def boom(a):
            raise RuntimeError("kaboom")
        self.reg.register(ToolSpec(
            name="boom", description="b", schema={"type": "object"}, handler=boom))
        r = self.reg.execute("boom", {})
        self.assertEqual(r.status, ToolStatus.ERROR)
        self.assertIn("kaboom", r.error)

    def test_timeout(self):
        import time

        def slow(a):
            time.sleep(5)
            return {}
        self.reg.register(ToolSpec(
            name="slow", description="s", schema={"type": "object"},
            handler=slow, timeout_s=0.2))
        r = self.reg.execute("slow", {})
        self.assertEqual(r.status, ToolStatus.TIMEOUT)


if __name__ == "__main__":
    unittest.main()
