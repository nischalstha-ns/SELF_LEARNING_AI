"""Test-only stand-ins for sibling-phase modules.

The voice/workflows/companion/service phases import from
vena.core.*, vena.tools.registry and vena.planner.engine, which are
owned by sibling phases and may not exist yet. These stubs mirror the
NEXUS semantics the code was adapted from (see ADAPT.md).

Two rules keep this safe:
1. One-shot install: stub classes are created ONCE per process, so
   `assertRaises(VenaError)` in a test always matches the class the
   production code raises.
2. Never shadow real modules: if `vena.core.errors` (etc.) actually
   exists on disk, it is left alone and the real module is used.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
import types
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

_MISSING = object()

_STUB_NAMES = (
    "vena.core.errors",
    "vena.core.logging",
    "vena.core.types",
    "vena.tools.registry",
    "vena.planner",
    "vena.planner.engine",
)

_refcount = 0


def _spec_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _make_errors() -> types.ModuleType:
    mod = types.ModuleType("vena.core.errors")

    class VenaError(Exception):
        pass

    class ProviderError(VenaError):
        pass

    class ProviderUnavailable(ProviderError):
        pass

    class BodyTooLarge(VenaError):
        pass

    mod.VenaError = VenaError
    mod.ProviderError = ProviderError
    mod.ProviderUnavailable = ProviderUnavailable
    mod.BodyTooLarge = BodyTooLarge
    return mod


def _make_logging() -> types.ModuleType:
    mod = types.ModuleType("vena.core.logging")

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

    mod.get_logger = get_logger
    return mod


def _make_types() -> types.ModuleType:
    mod = types.ModuleType("vena.core.types")

    class Permission(str, Enum):
        OBSERVE = "observe"
        ASSIST = "assist"
        EXECUTE = "execute"
        ELEVATED = "elevated"

    class TaskStatus(str, Enum):
        PENDING = "pending"
        RUNNING = "running"
        AWAITING_APPROVAL = "awaiting_approval"
        AWAITING_INPUT = "awaiting_input"
        DONE = "done"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class ToolStatus(str, Enum):
        OK = "ok"
        ERROR = "error"
        DENIED = "denied"
        TIMEOUT = "timeout"
        CANCELLED = "cancelled"

    @dataclass
    class PlanStep:
        id: str
        description: str
        tool: Optional[str] = None
        arguments: Dict[str, Any] = field(default_factory=dict)
        requires_approval: bool = False
        status: str = "pending"
        attempts: int = 0
        verify_note: Optional[str] = None

    mod.Permission = Permission
    mod.TaskStatus = TaskStatus
    mod.ToolStatus = ToolStatus
    mod.PlanStep = PlanStep
    return mod


def _make_registry() -> types.ModuleType:
    mod = types.ModuleType("vena.tools.registry")

    Approver = Callable[[str, Dict[str, Any]], bool]

    class ToolRegistry:
        def validate(self, name: str, arguments: dict) -> None:
            raise NotImplementedError

        def policy(self, tool_name: str):
            raise NotImplementedError

        def execute(self, name: str, arguments: dict, task_id=None,
                    approver=None, approved_by=None):
            raise NotImplementedError

    mod.Approver = Approver
    mod.ToolRegistry = ToolRegistry
    return mod


def _make_planner() -> tuple[types.ModuleType, types.ModuleType]:
    pkg = types.ModuleType("vena.planner")
    pkg.__path__ = []  # mark as package so submodule import works
    eng = types.ModuleType("vena.planner.engine")

    def verify_step(step, result) -> tuple[bool, str]:
        return True, "stub verified"

    eng.verify_step = verify_step
    return pkg, eng


def _do_install() -> None:
    if not _spec_exists("vena.core.errors"):
        sys.modules["vena.core.errors"] = _make_errors()
    if not _spec_exists("vena.core.logging"):
        sys.modules["vena.core.logging"] = _make_logging()
    if not _spec_exists("vena.core.types"):
        sys.modules["vena.core.types"] = _make_types()
    if not _spec_exists("vena.tools.registry"):
        sys.modules["vena.tools.registry"] = _make_registry()
    if not _spec_exists("vena.planner.engine"):
        if not _spec_exists("vena.planner"):
            pkg, eng = _make_planner()
            sys.modules["vena.planner"] = pkg
            sys.modules["vena.planner.engine"] = eng
        else:
            _, eng = _make_planner()
            sys.modules["vena.planner.engine"] = eng


def install_stubs() -> dict:
    """Inject stub modules (one-shot). Returns saved state for
    uninstall_stubs()."""
    global _refcount
    saved = {name: sys.modules.get(name, _MISSING) for name in _STUB_NAMES}
    if _refcount == 0:
        _do_install()
    _refcount += 1
    return saved


def uninstall_stubs(saved: dict) -> None:
    """Release one install_stubs() hold; restores the previous
    sys.modules state only when the last holder releases."""
    global _refcount
    _refcount = max(0, _refcount - 1)
    if _refcount == 0:
        for name, mod in saved.items():
            if mod is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod


# -- reusable fakes -----------------------------------------------------

class FakeResult:
    def __init__(self, status, data=None, error=None, duration_ms=1):
        self.status = status
        self.data = data or {}
        self.error = error
        self.duration_ms = duration_ms


class FakeRegistry:
    """Controllable ToolRegistry stand-in for workflow tests."""

    def __init__(self, policies=None, results=None):
        from vena.core.types import Permission
        self._Permission = Permission
        self.policies = dict(policies or {})
        self.results = dict(results or {})
        self.validated: list[tuple] = []
        self.executed: list[tuple] = []

    def validate(self, name, arguments):
        from vena.core.errors import VenaError
        self.validated.append((name, arguments))
        if name not in self.policies:
            raise VenaError(f"unknown tool '{name}'")

    def policy(self, tool_name):
        return self.policies.get(tool_name, self._Permission.EXECUTE)

    def execute(self, name, arguments, task_id=None, approver=None,
                approved_by=None):
        from vena.core.types import ToolStatus
        self.executed.append((name, arguments))
        res = self.results.get(name)
        if isinstance(res, Exception):
            raise res
        if res is not None:
            return res
        return FakeResult(ToolStatus.OK, data={"ok": True})
