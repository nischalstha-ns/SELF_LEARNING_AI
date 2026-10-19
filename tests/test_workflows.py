"""Tests for vena/workflows/: recorder.py and replay.py."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest

from tests._stubs import FakeRegistry, FakeResult, install_stubs, uninstall_stubs

_state = install_stubs()
try:
    from vena.core.errors import VenaError
    from vena.core.types import Permission, ToolStatus
    from vena.service.schema import ensure_schema
    from vena.workflows.recorder import WorkflowStore
    from vena.workflows.replay import WorkflowReplayer
finally:
    pass


def tearDownModule():
    uninstall_stubs(_state)

STEPS = [
    {"tool": "read_file", "arguments": {"path": "/tmp/a.txt"}},
    {"tool": "write_file", "arguments": {"path": "/tmp/b.txt", "content": "hi"}},
]


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    conn.execute(
        "CREATE TABLE tool_executions("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " task_id TEXT NOT NULL, tool_name TEXT NOT NULL,"
        " args_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'ok')")
    return conn


def make_registry(**kw):
    policies = {"read_file": Permission.EXECUTE,
                "write_file": Permission.EXECUTE,
                "click_at": Permission.ELEVATED}
    policies.update(kw.get("policies", {}))
    return FakeRegistry(policies=policies, results=kw.get("results"))


class RecorderTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_db()
        self.reg = make_registry()
        self.store = WorkflowStore(self.conn, self.reg)

    def tearDown(self):
        self.conn.close()

    def test_create_and_get(self):
        wf = self.store.create_workflow("demo", "desc", STEPS)
        self.assertEqual(wf["name"], "demo")
        self.assertEqual(len(wf["steps"]), 2)
        fetched = self.store.get_workflow(wf["id"])
        self.assertEqual(fetched["steps"], STEPS)

    def test_create_rejects_empty_name(self):
        with self.assertRaises(VenaError):
            self.store.create_workflow("  ", "", STEPS)

    def test_create_rejects_empty_steps(self):
        with self.assertRaises(VenaError):
            self.store.create_workflow("x", "", [])

    def test_create_rejects_unknown_tool(self):
        with self.assertRaises(VenaError):
            self.store.create_workflow("x", "",
                                       [{"tool": "nope", "arguments": {}}])

    def test_create_rejects_bad_arguments(self):
        with self.assertRaises(VenaError):
            self.store.create_workflow("x", "",
                                       [{"tool": "read_file",
                                         "arguments": "not-a-dict"}])

    def test_update(self):
        wf = self.store.create_workflow("demo", "", STEPS)
        updated = self.store.update_workflow(wf["id"], name="renamed")
        self.assertEqual(updated["name"], "renamed")
        with self.assertRaises(VenaError):
            self.store.update_workflow(wf["id"], name="  ")

    def test_delete(self):
        wf = self.store.create_workflow("demo", "", STEPS)
        self.store.delete_workflow(wf["id"])
        with self.assertRaises(VenaError):
            self.store.get_workflow(wf["id"])
        with self.assertRaises(VenaError):
            self.store.delete_workflow(wf["id"])

    def test_list(self):
        self.store.create_workflow("a", "", STEPS)
        self.store.create_workflow("b", "", STEPS)
        rows = self.store.list_workflows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["steps"], 2)

    def test_record_from_task(self):
        self.conn.execute(
            "INSERT INTO tasks(id, title, status) VALUES ('t1','task','done')")
        self.conn.execute(
            "INSERT INTO tool_executions(task_id, tool_name, args_json, status)"
            " VALUES ('t1','read_file','{\"path\": \"/x\"}','ok')")
        self.conn.execute(
            "INSERT INTO tool_executions(task_id, tool_name, args_json, status)"
            " VALUES ('t1','write_file','{\"path\": \"/y\"}','error')")
        self.conn.commit()
        wf = self.store.record_from_task("t1", "from-task")
        # only the successful execution is recorded
        self.assertEqual(len(wf["steps"]), 1)
        self.assertEqual(wf["steps"][0]["tool"], "read_file")

    def test_record_from_task_unknown(self):
        with self.assertRaises(VenaError):
            self.store.record_from_task("missing", "x")

    def test_record_from_task_no_success(self):
        self.conn.execute(
            "INSERT INTO tasks(id, title, status) VALUES ('t2','task','failed')")
        self.conn.commit()
        with self.assertRaises(VenaError):
            self.store.record_from_task("t2", "x")


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = make_db()
        self.reg = make_registry()
        self.store = WorkflowStore(self.conn, self.reg)
        self.replayer = WorkflowReplayer(self.conn, self.reg, self.tmp.name,
                                         store=self.store)
        self.wf = self.store.create_workflow("demo", "", STEPS)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_dry_run_executes_nothing(self):
        result = self.replayer.replay(self.wf["id"], dry_run=True)
        self.assertEqual(result["status"], "done")
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.reg.executed, [])
        self.assertEqual([s["status"] for s in result["steps"]],
                         ["dry_run_ok", "dry_run_ok"])

    def test_replay_success(self):
        result = self.replayer.replay(self.wf["id"])
        self.assertEqual(result["status"], "done")
        self.assertIsNone(result["failed_at"])
        self.assertEqual(len(self.reg.executed), 2)
        self.assertEqual(self.reg.executed[0][0], "read_file")

    def test_replay_stops_on_first_failure(self):
        failing = make_registry(results={
            "read_file": FakeResult(ToolStatus.ERROR, error="boom")})
        store = WorkflowStore(self.conn, failing)
        wf = store.create_workflow("faildemo", "", STEPS)
        replayer = WorkflowReplayer(self.conn, failing, self.tmp.name,
                                    store=store)
        result = replayer.replay(wf["id"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_at"], 0)
        self.assertEqual(len(failing.executed), 1)  # second step never ran

    def test_elevated_step_needs_approval(self):
        steps = [{"tool": "click_at", "arguments": {"x": 1, "y": 2}}]
        wf = self.store.create_workflow("elev", "", steps)
        # no approver -> awaiting_approval, nothing executed
        result = self.replayer.replay(wf["id"])
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertEqual(result["failed_at"], 0)
        self.assertEqual(self.reg.executed, [])
        # approver says yes -> runs
        result = self.replayer.replay(wf["id"], approver=lambda t, a: True)
        self.assertEqual(result["status"], "done")

    def test_safe_level_step_runs(self):
        # SAFE (reversible) steps run without approval, like EXECUTE
        reg = make_registry(policies={"preview": Permission.SAFE})
        store = WorkflowStore(self.conn, reg)
        wf = store.create_workflow("safe", "",
                                   [{"tool": "preview", "arguments": {}}])
        replayer = WorkflowReplayer(self.conn, reg, self.tmp.name, store=store)
        result = replayer.replay(wf["id"])
        self.assertEqual(result["status"], "done")

    def test_checkpoint_and_revert(self):
        target = os.path.join(self.tmp.name, "target.txt")
        with open(target, "w") as f:
            f.write("original")
        wf = self.store.create_workflow(
            "ckpt", "", [{"tool": "write_file",
                          "arguments": {"path": target, "content": "new"}}])
        result = self.replayer.replay(wf["id"], checkpoint=True)
        self.assertEqual(result["status"], "done")
        run_id = result["run_id"]
        reverted = self.replayer.revert_run(run_id)
        # fake registry didn't actually write, but checkpoint backed up
        # the original file; revert restores it
        self.assertIn(target, reverted["restored"])
        with open(target) as f:
            self.assertEqual(f.read(), "original")

    def test_revert_run_without_checkpoints(self):
        result = self.replayer.replay(self.wf["id"], checkpoint=False)
        with self.assertRaises(VenaError):
            self.replayer.revert_run(result["run_id"])

    def test_revert_unknown_run(self):
        with self.assertRaises(VenaError):
            self.replayer.revert_run("nope")

    def test_get_run(self):
        result = self.replayer.replay(self.wf["id"], dry_run=True)
        run = self.replayer.get_run(result["run_id"])
        self.assertEqual(run["workflow_id"], self.wf["id"])
        self.assertIn("steps", run["result"])
        with self.assertRaises(VenaError):
            self.replayer.get_run("nope")

    def test_replay_unknown_workflow(self):
        with self.assertRaises(VenaError):
            self.replayer.replay("nope")


if __name__ == "__main__":
    unittest.main()
