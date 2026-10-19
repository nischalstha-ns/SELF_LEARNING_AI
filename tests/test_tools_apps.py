"""Tests for vena.tools.apps — allowlist + protected processes."""
import unittest

from vena.tools import apps


class AppsTest(unittest.TestCase):
    def test_open_not_allowlisted(self):
        with self.assertRaises(PermissionError):
            apps.open_app({"gedit": "gedit"}, "rm")

    def test_open_case_insensitive_lookup(self):
        # allowlist hit, but the launch itself may fail on this box —
        # we only assert the allowlist gate passes (no PermissionError).
        try:
            apps.open_app({"no-such-app-xyz": "no-such-app-xyz"},
                          "NO-SUCH-APP-XYZ")
        except PermissionError:
            self.fail("allowlist should have matched case-insensitively")
        except Exception:
            pass  # launch failure is fine; gate passed

    def test_close_protected(self):
        for name in ("python3", "init", "explorer.exe"):
            with self.assertRaises(PermissionError):
                apps.close_app(name)

    def test_close_empty(self):
        with self.assertRaises(ValueError):
            apps.close_app("  ")

    def test_list_apps_shape(self):
        try:
            r = apps.list_apps()
        except Exception as e:
            self.skipTest(f"list_apps unsupported here: {e}")
        self.assertIn("apps", r)
        self.assertIsInstance(r["apps"], list)

    def test_specs_permissions(self):
        specs = apps.make_specs({"calc": "calc"})
        perms = {s.name: s.default_permission.value for s in specs}
        self.assertEqual(perms["list_apps"], "observe")
        self.assertEqual(perms["open_app"], "execute")
        self.assertEqual(perms["close_app"], "elevated")
        self.assertEqual(perms["focus_app"], "execute")


if __name__ == "__main__":
    unittest.main()
