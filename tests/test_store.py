"""Tests: Store applies versioned migrations and tracks applied versions."""
import os
import sqlite3
import tempfile
import unittest

from vena.memory.store import Store

MIGRATIONS = os.path.join(os.path.dirname(__file__), "..", "data", "migrations")


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "test.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_migrations_apply(self):
        store = Store(self.db, os.path.abspath(MIGRATIONS))
        self.assertEqual(store.applied_versions(), {1, 2})
        # Core tables exist.
        tables = {r[0] for r in store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ("schema_migrations", "conversations", "messages", "memories",
                  "tasks", "tool_executions", "permission_policies",
                  "providers", "user_settings", "audit_events"):
            self.assertIn(t, tables, t)
        store.close()

    def test_idempotent_reopen(self):
        s1 = Store(self.db, os.path.abspath(MIGRATIONS))
        s1.close()
        s2 = Store(self.db, os.path.abspath(MIGRATIONS))
        self.assertEqual(s2.applied_versions(), {1, 2})
        s2.close()

    def test_permission_levels_use_safe(self):
        store = Store(self.db, os.path.abspath(MIGRATIONS))
        store.conn.execute(
            "INSERT INTO permission_policies(tool_name, level) VALUES (?,?)",
            ("t", "safe"))
        row = store.conn.execute(
            "SELECT level FROM permission_policies WHERE tool_name='t'").fetchone()
        self.assertEqual(row["level"], "safe")
        # 'assist' must be rejected by the CHECK constraint.
        with self.assertRaises(sqlite3.IntegrityError):
            store.conn.execute(
                "INSERT INTO permission_policies(tool_name, level) VALUES (?,?)",
                ("t2", "assist"))
        store.close()

    def test_fts_tables_exist(self):
        store = Store(self.db, os.path.abspath(MIGRATIONS))
        tables = {r[0] for r in store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("messages_fts", tables)
        self.assertIn("memories_fts", tables)
        store.close()


if __name__ == "__main__":
    unittest.main()
