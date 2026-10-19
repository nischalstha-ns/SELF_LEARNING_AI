"""Mouse/keyboard backends.

Adapted from nexus/perception/automation.py.

- MockAutomation: records every action for tests, dry-runs, demos.
  This is the default — real input must be opted into explicitly.
- PyAutoGUIBackend: real input via pyautogui (pip install pyautogui),
  only constructed when the library imports cleanly.
"""
from __future__ import annotations

import logging

from ..perception._base import AutomationBackend, InputAction
from .safety import VenaError

log = logging.getLogger("vena.automation.mouse_keyboard")


_ALLOWED_BUTTONS = ("left", "right", "middle")
# Conservative key vocabulary — no raw keycodes. OS-reserved combos are
# blocked separately in vena/automation/safety.py.
_ALLOWED_KEYS = {
    "Enter", "Tab", "Escape", "BackSpace", "Delete",
    "Up", "Down", "Left", "Right", "Home", "End",
    "Page_Up", "Page_Down", "F1", "F2", "F3", "F4", "F5", "F6",
    "F7", "F8", "F9", "F10", "F11", "F12",
    "ctrl", "alt", "shift", "super",
}


def check_keys(keys: list[str]) -> None:
    """Validate a key list against the allowed vocabulary."""
    for k in keys:
        if k not in _ALLOWED_KEYS and not (len(k) == 1 and k.isprintable()):
            raise VenaError(f"key '{k}' is not in the allowed vocabulary")
    lowered = [k.lower() for k in keys]
    if "ctrl" in lowered and "alt" in lowered and "delete" in lowered:
        raise VenaError("ctrl+alt+delete is never sent")


def check_button(button: str) -> None:
    if button not in _ALLOWED_BUTTONS:
        raise VenaError(f"button '{button}' not allowed")


class MockAutomation(AutomationBackend):
    name = "mock"

    def __init__(self):
        self.actions: list[InputAction] = []

    def click(self, x: int, y: int, button: str = "left") -> None:
        check_button(button)
        self.actions.append(InputAction("click", {"x": x, "y": y, "button": button}))

    def double_click(self, x: int, y: int) -> None:
        self.actions.append(InputAction("double_click", {"x": x, "y": y}))

    def right_click(self, x: int, y: int) -> None:
        self.click(x, y, button="right")

    def type_text(self, text: str) -> None:
        if len(text) > 10000:
            raise VenaError("type_text limited to 10000 chars per call")
        self.actions.append(InputAction("type", {"text": text}))

    def press_keys(self, keys: list[str]) -> None:
        check_keys(keys)
        self.actions.append(InputAction("key", {"keys": list(keys)}))

    def scroll(self, dx: int, dy: int) -> None:
        self.actions.append(InputAction("scroll", {"dx": dx, "dy": dy}))


class PyAutoGUIBackend(AutomationBackend):
    """Real input via pyautogui. Failsafe stays ON; safety checks apply."""
    name = "pyautogui"

    def __init__(self):
        try:
            import pyautogui  # type: ignore
        except ImportError as e:
            raise VenaError(
                "pyautogui is not installed (pip install pyautogui)") from e
        self._pg = pyautogui
        self._pg.FAILSAFE = True  # corner-stop stays armed
        self._pg.PAUSE = 0.05

    @staticmethod
    def available() -> bool:
        try:
            import pyautogui  # noqa: F401
            return True
        except ImportError:
            return False

    def click(self, x: int, y: int, button: str = "left") -> None:
        check_button(button)
        self._pg.click(x, y, button=button)

    def double_click(self, x: int, y: int) -> None:
        self._pg.doubleClick(x, y)

    def right_click(self, x: int, y: int) -> None:
        self.click(x, y, button="right")

    def type_text(self, text: str) -> None:
        if len(text) > 10000:
            raise VenaError("type_text limited to 10000 chars per call")
        self._pg.typewrite(text)

    def press_keys(self, keys: list[str]) -> None:
        from .safety import assert_safe_hotkey
        check_keys(keys)
        assert_safe_hotkey(keys)
        self._pg.hotkey(*keys)

    def scroll(self, dx: int, dy: int) -> None:
        # pyautogui scrolls vertically; horizontal via hscroll where supported
        if dy:
            self._pg.scroll(dy)
        if dx and hasattr(self._pg, "hscroll"):
            self._pg.hscroll(dx)


def default_automation() -> AutomationBackend:
    """Real backend when pyautogui is installed, else the mock."""
    if PyAutoGUIBackend.available():
        try:
            return PyAutoGUIBackend()
        except VenaError as e:
            log.debug("pyautogui backend failed: %s", e)
    return MockAutomation()


__all__ = ["MockAutomation", "PyAutoGUIBackend", "VenaError",
           "check_keys", "check_button", "default_automation"]
