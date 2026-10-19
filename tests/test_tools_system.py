"""Tests for vena.tools.system — graceful degradation everywhere."""
import os
import tempfile
import unittest

from vena.tools import system


class SystemTest(unittest.TestCase):
    def test_get_time(self):
        t = system.get_time()
        self.assertIn("utc", t)
        self.assertIn("T", t["utc"])

    def test_disk_usage_jailed(self):
        with tempfile.TemporaryDirectory() as root:
            u = system.disk_usage([root], "")
            self.assertGreater(u["total_gb"], 0)
            self.assertGreaterEqual(u["free_gb"], 0)
            with self.assertRaises(PermissionError):
                system.disk_usage([root], "/etc")

    def test_memory_info_shape(self):
        m = system.memory_info()
        self.assertIn("available", m)
        if m["available"]:
            self.assertGreater(m["total_mb"], 0)

    def test_battery_shape(self):
        b = system.battery_info()
        self.assertIn("available", b)

    def test_volume_get_shape(self):
        v = system.get_volume()
        self.assertIn("available", v)

    def test_set_volume_range(self):
        with self.assertRaises(ValueError):
            system.set_volume(101)
        with self.assertRaises(ValueError):
            system.set_volume(-1)

    def test_brightness_degrades(self):
        b = system.get_brightness()
        self.assertFalse(b["available"])

    def test_clipboard_set_limit(self):
        with self.assertRaises(ValueError):
            system.clipboard_set("x" * 100_001)

    def test_specs(self):
        specs = system.make_specs()
        perms = {s.name: s.default_permission.value for s in specs}
        self.assertEqual(perms["get_time"], "observe")
        self.assertEqual(perms["clipboard_set"], "execute")
        self.assertEqual(perms["set_volume"], "execute")
        self.assertEqual(perms["notify"], "execute")
        self.assertGreaterEqual(len(specs), 9)


if __name__ == "__main__":
    unittest.main()
