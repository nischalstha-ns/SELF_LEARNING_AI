"""Tests for vena.automation — mock backend, key safety, failsafe."""
import unittest

from vena.automation.mouse_keyboard import (MockAutomation,
                                            PyAutoGUIBackend, VenaError,
                                            check_button, check_keys,
                                            default_automation)
from vena.automation.safety import (FailSafe, FailSafeTripped,
                                    assert_safe_hotkey)


class MockBackendTest(unittest.TestCase):
    def test_records_actions(self):
        m = MockAutomation()
        m.click(10, 20)
        m.type_text("hi")
        m.press_keys(["ctrl", "c"])
        m.scroll(0, 5)
        kinds = [a.kind for a in m.actions]
        self.assertEqual(kinds, ["click", "type", "key", "scroll"])
        self.assertEqual(m.actions[0].params, {"x": 10, "y": 20, "button": "left"})

    def test_double_and_right_click(self):
        m = MockAutomation()
        m.double_click(1, 2)
        m.right_click(3, 4)
        self.assertEqual(m.actions[0].kind, "double_click")
        self.assertEqual(m.actions[1].params["button"], "right")

    def test_bad_button(self):
        with self.assertRaises(VenaError):
            MockAutomation().click(0, 0, button="sideways")

    def test_type_limit(self):
        with self.assertRaises(VenaError):
            MockAutomation().type_text("x" * 10001)


class KeySafetyTest(unittest.TestCase):
    def test_ctrl_alt_delete_blocked(self):
        with self.assertRaises(VenaError):
            check_keys(["ctrl", "alt", "Delete"])
        with self.assertRaises(VenaError):
            assert_safe_hotkey(["Ctrl", "Alt", "Delete"])

    def test_lock_combos_blocked(self):
        with self.assertRaises(VenaError):
            assert_safe_hotkey(["super", "l"])

    def test_unknown_key_blocked(self):
        with self.assertRaises(VenaError):
            check_keys(["HyperHyper"])

    def test_printable_char_ok(self):
        check_keys(["a", "Enter", "ctrl"])  # must not raise

    def test_check_button_ok(self):
        check_button("left")  # must not raise


class FailSafeTest(unittest.TestCase):
    def test_trip_blocks_actions(self):
        fs = FailSafe(MockAutomation())
        fs.trip("test")
        self.assertTrue(fs.tripped)
        with self.assertRaises(FailSafeTripped):
            fs.click(1, 2)

    def test_reset_allows_again(self):
        fs = FailSafe(MockAutomation())
        fs.trip()
        fs.reset()
        fs.click(1, 2)  # must not raise
        self.assertFalse(fs.tripped)

    def test_delegates_to_backend(self):
        back = MockAutomation()
        fs = FailSafe(back)
        fs.type_text("abc")
        self.assertEqual(back.actions[0].params, {"text": "abc"})


class DefaultBackendTest(unittest.TestCase):
    def test_default_never_crashes(self):
        b = default_automation()
        self.assertTrue(hasattr(b, "click"))

    def test_pyautogui_available_flag_honest(self):
        try:
            import pyautogui  # noqa: F401
            expected = True
        except ImportError:
            expected = False
        self.assertEqual(PyAutoGUIBackend.available(), expected)


if __name__ == "__main__":
    unittest.main()
