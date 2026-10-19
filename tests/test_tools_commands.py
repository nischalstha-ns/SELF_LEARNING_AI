"""Tests for vena.tools.commands — allowlist enforcement, no shell."""
import os
import tempfile
import unittest

from vena.tools import commands


class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.roots = [self.tmp.name]
        self.allowed = ["echo", "python3", "ls"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowed_command(self):
        r = commands.run_command(self.allowed, "echo hello", approved_roots=self.roots)
        self.assertEqual(r["returncode"], 0)
        self.assertIn("hello", r["stdout"])

    def test_blocked_command(self):
        with self.assertRaises(PermissionError):
            commands.run_command(self.allowed, "rm -rf /", approved_roots=self.roots)

    def test_blocked_prefix_trick(self):
        # 'echox' must not pass as 'echo'
        with self.assertRaises(PermissionError):
            commands.run_command(self.allowed, ["echox", "hi"],
                                 approved_roots=self.roots)

    def test_list_form(self):
        r = commands.run_command(self.allowed, ["echo", "a", "b"],
                                 approved_roots=self.roots)
        self.assertIn("a b", r["stdout"])

    def test_cwd_jailed(self):
        with self.assertRaises(PermissionError):
            commands.run_command(self.allowed, "echo hi", cwd="/etc",
                                 approved_roots=self.roots)

    def test_cwd_inside_ok(self):
        sub = os.path.join(self.tmp.name, "work")
        os.makedirs(sub)
        r = commands.run_command(self.allowed, "echo hi", cwd=sub,
                                 approved_roots=self.roots)
        self.assertEqual(r["returncode"], 0)

    def test_empty_command(self):
        with self.assertRaises(ValueError):
            commands.run_command(self.allowed, "", approved_roots=self.roots)

    def test_specs(self):
        specs = commands.make_specs(self.allowed, self.roots)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].name, "run_command")
        self.assertEqual(specs[0].default_permission.value, "execute")
        # handler goes through the allowlist too
        out = specs[0].handler({"command": "echo spec-ok"})
        self.assertIn("spec-ok", out["stdout"])


if __name__ == "__main__":
    unittest.main()
