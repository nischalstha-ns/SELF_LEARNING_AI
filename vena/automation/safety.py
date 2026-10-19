"""Automation safety rails — checked before any real input is sent.

Hard limits (never crossed, even if a task prompt asks):
- Ctrl+Alt+Del is never sent.
- OS lock / login bypass combos are never sent (Win+L, Ctrl+Alt+Del).
- Failsafe: with pyautogui, slamming the mouse into a screen corner aborts
  the current action (pyautogui.FAILSAFE). `FailSafe` below exposes the same
  idea for the mock backend: trip() marks the backend stopped and every
  subsequent action raises until reset().
"""
from __future__ import annotations

import logging

log = logging.getLogger("vena.automation.safety")


class VenaError(Exception):
    pass


# Combos that must never be emitted, in any order/case.
_FORBIDDEN_COMBOS: tuple[frozenset[str], ...] = (
    frozenset({"ctrl", "alt", "delete"}),   # secure attention sequence
    frozenset({"super", "l"}),              # Windows lock screen
    frozenset({"ctrl", "alt", "l"}),        # common lock shortcut
)


def assert_safe_hotkey(keys: list[str]) -> None:
    """Raise VenaError if `keys` form a forbidden OS-level combo."""
    lowered = frozenset(k.lower() for k in keys)
    for combo in _FORBIDDEN_COMBOS:
        if combo <= lowered:
            raise VenaError(
                f"forbidden key combo blocked: {'+'.join(sorted(combo))}")
    # Single Delete/ctrl+alt+delete variants are caught by check_keys too;
    # this is the last line of defence at the automation layer.


class FailSafe:
    """Software failsafe mirroring pyautogui's corner-stop.

    Wrap a backend: `guarded.click(...)` etc. raise FailSafeTripped once
    trip() has been called (e.g. by a UI "STOP" button or watchdog).
    """

    def __init__(self, backend):
        self._backend = backend
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    def trip(self, reason: str = "manual stop") -> None:
        self._tripped = True
        log.warning("failsafe tripped: %s", reason)

    def reset(self) -> None:
        self._tripped = False

    def _guard(self, action: str):
        if self._tripped:
            raise FailSafeTripped(
                f"failsafe is tripped — '{action}' blocked until reset()")

    def __getattr__(self, name: str):
        # Delegate everything else to the wrapped backend, guarded.
        if name.startswith("_"):
            raise AttributeError(name)
        target = getattr(self._backend, name)
        if not callable(target):
            return target

        def _wrapped(*a, **k):
            self._guard(name)
            return target(*a, **k)

        return _wrapped


class FailSafeTripped(VenaError):
    """Raised when input is attempted after the failsafe tripped."""


__all__ = ["assert_safe_hotkey", "FailSafe", "FailSafeTripped", "VenaError"]
