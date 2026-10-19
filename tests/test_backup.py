"""Tests for vena/service/backup.py."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from tests._stubs import install_stubs, uninstall_stubs

_state = install_stubs()
try:
    from vena.core.errors import VenaError
    from vena.service import backup as backup_mod
    from vena.service.schema import ensure_schema
finally:
    pass


def tearDownModule():
    uninstall_stubs(_state)


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        ensure_schema(self.conn)
        self.conn.execute(
            "INSERT INTO workflows(id, name, description, steps_json)"
            " VALUES ('w1','demo','','[]')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_backup_and_list(self):
        manifest = backup_mod.backup(self.conn, self.tmp.name, label="t1")
        self.assertTrue(manifest["name"].startswith("vena-"))
        self.assertTrue(manifest["name"].endswith("-t1.db"))
        self.assertGreater(manifest["bytes"], 0)
        self.assertEqual(manifest["row_counts"]["workflows"], 1)
        listed = backup_mod.list_backups(self.tmp.name)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["name"], manifest["name"])

    def test_backup_label_validation(self):
        with self.assertRaises(VenaError):
            backup_mod.backup(self.conn, self.tmp.name, label="../evil")

    def test_restore_roundtrip(self):
        manifest = backup_mod.backup(self.conn, self.tmp.name)
        # change the live DB, then restore
        self.conn.execute("DELETE FROM workflows")
        self.conn.commit()
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0], 0)
        result = backup_mod.restore(self.conn, self.tmp.name, manifest["name"])
        self.assertTrue(result["ok"])
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0], 1)

    def test_restore_rejects_bad_name(self):
        with self.assertRaises(VenaError):
            backup_mod.restore(self.conn, self.tmp.name, "../evil.db")
        with self.assertRaises(VenaError):
            backup_mod.restore(self.conn, self.tmp.name, "missing.db")

    def test_restore_rejects_non_db(self):
        bad = os.path.join(self.tmp.name, "backups", "fake.db")
        os.makedirs(os.path.dirname(bad), exist_ok=True)
        with open(bad, "wb") as f:
            f.write(b"not a database at all")
        with self.assertRaises(VenaError):
            backup_mod.restore(self.conn, self.tmp.name, "fake.db")


if __name__ == "__main__":
    unittest.main()
