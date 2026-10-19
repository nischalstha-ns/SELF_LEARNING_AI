"""Active window detection — platform-appropriate, mock fallback.

Windows: ctypes GetForegroundWindow + GetWindowText.
Linux:   `xdotool getactivewindow getwindowname` when installed.
macOS:   osascript frontmost application.
Anything else (or missing helpers): MockWindowDetector with a fixed answer.
"""
from __future__ import annotations

import logging
import platform
import shutil
import subprocess

from ._base import WindowInfo

log = logging.getLogger("vena.perception.window")

_OS = platform.system()


class VenaError(Exception):
    pass


class WindowDetector:
    """Detect the currently focused window. Override per platform."""

    name = "base"

    def active_window(self) -> WindowInfo:
        raise NotImplementedError


class MockWindowDetector(WindowDetector):
    name = "mock"

    def __init__(self, title: str = "Mock Window", app_name: str = "mock"):
        self._title, self._app = title, app_name

    def active_window(self) -> WindowInfo:
        return WindowInfo(title=self._title, app_name=self._app,
                          source=self.name)


class WindowsDetector(WindowDetector):
    name = "windows"

    def active_window(self) -> WindowInfo:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            raise VenaError("no foreground window")
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return WindowInfo(title=buf.value or "(untitled)", app_name="",
                          source=self.name)


class LinuxDetector(WindowDetector):
    name = "linux"

    def active_window(self) -> WindowInfo:
        if not shutil.which("xdotool"):
            raise VenaError("xdotool not installed")
        try:
            p = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                               capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired as e:
            raise VenaError("window query timed out") from e
        if p.returncode != 0:
            raise VenaError("xdotool failed")
        return WindowInfo(title=p.stdout.strip() or "(untitled)", app_name="",
                          source=self.name)


class MacDetector(WindowDetector):
    name = "macos"

    def active_window(self) -> WindowInfo:
        try:
            p = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of '
                 '(first process whose frontmost is true)'],
                capture_output=True, text=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise VenaError(f"osascript failed: {e}") from e
        return WindowInfo(title="", app_name=p.stdout.strip(),
                          source=self.name)


def default_detector() -> WindowDetector:
    """Best detector for this OS; mock when nothing real is available."""
    try:
        if _OS == "Windows":
            return WindowsDetector()
        if _OS == "Darwin":
            return MacDetector()
        if _OS == "Linux" and shutil.which("xdotool"):
            return LinuxDetector()
    except Exception as e:  # never crash on detector construction
        log.debug("detector init failed: %s", e)
    return MockWindowDetector()


__all__ = ["WindowDetector", "MockWindowDetector", "WindowsDetector",
           "LinuxDetector", "MacDetector", "VenaError", "default_detector"]
