"""Screen capture backends.

Adapted from nexus/perception/screencap.py.

- MockScreen: deterministic gradient PNG (tests, demos, headless CI).
- CommandScreenCap: shells out to an operator-configured capture tool
  (e.g. `grim -` on Wayland, `screencapture -x -t png -` on macOS).
  The command must emit PNG bytes on stdout.

The stdlib PNG encoder in `.png` is the fallback for generating images —
no Pillow required anywhere in this module.
"""
from __future__ import annotations

import logging
import os
import shlex
import subprocess

from ._base import ScreenObserver, Screenshot, WindowInfo
from .png import decode_png_size, test_card

log = logging.getLogger("vena.perception.screen")


class VenaError(Exception):
    pass


class MockScreen(ScreenObserver):
    name = "mock"

    def __init__(self, width: int = 320, height: int = 200):
        self._w, self._h = width, height

    def capture(self, timeout_s: float = 10.0) -> Screenshot:
        png = test_card(self._w, self._h)
        return Screenshot(png_bytes=png, width=self._w, height=self._h,
                          source=self.name)

    def active_window(self) -> WindowInfo:
        return WindowInfo(title="Mock Window", app_name="mock",
                          width=self._w, height=self._h, source=self.name)


class CommandScreenCap(ScreenObserver):
    name = "command"

    def __init__(self, command: str):
        """e.g. 'screencapture -x -t png -' (macOS) or 'grim -' (Wayland)."""
        self.command = command

    def capture(self, timeout_s: float = 10.0) -> Screenshot:
        try:
            proc = subprocess.run(shlex.split(self.command), capture_output=True,
                                  timeout=timeout_s)
        except FileNotFoundError as e:
            raise VenaError(f"capture command not found: {self.command}") from e
        except subprocess.TimeoutExpired as e:
            raise VenaError("screen capture timed out") from e
        if proc.returncode != 0 or proc.stdout[:8] != b"\x89PNG\r\n\x1a\n":
            raise VenaError(
                f"capture failed: {proc.stderr.decode(errors='replace')[:200]}")
        w, h = decode_png_size(proc.stdout)
        log.info("captured %dx%d screenshot", w, h)
        return Screenshot(png_bytes=proc.stdout, width=w, height=h,
                          source=self.command)

    def active_window(self) -> WindowInfo:
        raise VenaError("active-window metadata not supported by command backend")


def save_screenshot(shot: Screenshot, path: str) -> str:
    """Write screenshot PNG bytes to `path` (stdlib only). Returns the path."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(shot.png_bytes)
    return path


def default_observer(command: str = "") -> ScreenObserver:
    """Command backend when configured, else the mock (never crashes)."""
    return CommandScreenCap(command) if command else MockScreen()


__all__ = ["MockScreen", "CommandScreenCap", "VenaError",
           "save_screenshot", "default_observer"]
