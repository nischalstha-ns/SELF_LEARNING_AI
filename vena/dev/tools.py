"""Developer-agent tools for the registry.

Adapted from nexus/dev/tools.py.

- index_project / search_code / find_symbol: OBSERVE (read-only)
- propose_patch: OBSERVE (computes a diff, writes nothing)
- discard_patch: OBSERVE
- apply_patch: EXECUTE (writes files, all-or-nothing)
- run_tests: EXECUTE (allowlisted test command, no shell, cwd=root)
"""
from __future__ import annotations

import logging
import os
import re
import subprocess

from ..tools._compat import Permission, ToolSpec, make_spec
from ..tools._jail import _ensure_roots, _resolve
from .indexer import ProjectIndexer
from .patcher import Patcher, VenaError

log = logging.getLogger("vena.dev.tools")


class DevContext:
    def __init__(self, conn, approved_roots: list[str],
                 allowed_commands: list[str], default_test_command: str = ""):
        self.indexer = ProjectIndexer(conn, approved_roots)
        self.patcher = Patcher(conn, approved_roots)
        self.roots = approved_roots
        self.allowed_commands = allowed_commands
        self.default_test_command = default_test_command


def _default_root(roots: list[str]) -> str:
    return roots[0] if roots else "~"


def search_code(roots: list[str], pattern: str, root: str = "",
                max_hits: int = 100) -> dict:
    """Regex-search file contents under a jailed root (pure function)."""
    base = _resolve(roots, root or _default_root(roots))
    try:
        rx = re.compile(pattern)
    except re.error as e:
        raise VenaError(f"bad regex: {e}")
    hits, truncated = [], False
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules",
                                    ".venv", "venv", "dist", "build"}]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    for ln, line in enumerate(f, 1):
                        if rx.search(line):
                            hits.append({"path": os.path.relpath(full, base),
                                         "line": ln,
                                         "text": line.strip()[:200]})
                            if len(hits) >= max_hits:
                                truncated = True
                                break
            except OSError:
                continue
            if truncated:
                break
        if truncated:
            break
    return {"hits": hits, "truncated": truncated}


def run_tests(roots: list[str], allowed_commands: list[str], root: str = "",
              command: str = "", timeout_s: float = 300.0,
              default_command: str = "") -> dict:
    """Run an allowlisted test command (no shell) under a jailed root."""
    abs_root = _resolve(roots, root or _default_root(roots))
    cmd = (command or default_command or "python -m unittest discover").strip()
    parts = cmd.split()
    if not parts or parts[0] not in allowed_commands:
        raise VenaError(
            f"command '{parts[0] if parts else ''}' not in allowlist: "
            f"{allowed_commands}")
    if not os.path.isdir(abs_root):
        raise VenaError(f"not a directory: {root}")
    try:
        proc = subprocess.run(parts, cwd=abs_root, capture_output=True,
                              timeout=timeout_s, shell=False)
    except subprocess.TimeoutExpired:
        raise VenaError("tests timed out")
    out = (proc.stdout.decode(errors="replace")
           + proc.stderr.decode(errors="replace"))[-8000:]
    return {"root": abs_root, "command": cmd,
            "returncode": proc.returncode, "passed": proc.returncode == 0,
            "output": out}


def make_specs(ctx: DevContext) -> list[ToolSpec]:
    roots = _ensure_roots(ctx.roots)
    S = {"type": "string"}

    def h_index(a):
        return ctx.indexer.index(a.get("root", _default_root(roots)))

    def h_find(a):
        return {"matches": ctx.indexer.find_symbol(
            a.get("root", _default_root(roots)),
            a["name"], int(a.get("limit", 20)))}

    def h_search(a):
        return search_code(roots, a["pattern"], a.get("root", ""))

    def h_propose(a):
        return ctx.patcher.propose(a.get("root", _default_root(roots)),
                                   a["edits"])

    def h_apply(a):
        return ctx.patcher.apply(a["patch_id"])

    def h_discard(a):
        ctx.patcher.discard(a["patch_id"])
        return {"ok": True}

    def h_tests(a):
        return run_tests(roots, ctx.allowed_commands, a.get("root", ""),
                         a.get("command", ""), float(a.get("timeout_s", 300)),
                         ctx.default_test_command)

    return [
        make_spec("index_project",
                  "Index a project root (jailed): file list + Python symbols.",
                  {"root": S}, permission=Permission.OBSERVE, handler=h_index),
        make_spec("find_symbol",
                  "Find where a function/class name is defined in the index.",
                  {"root": S, "name": S, "limit": {"type": "integer"}},
                  ("name",), Permission.OBSERVE, h_find),
        make_spec("search_code",
                  "Regex-search file contents under a project root (max 100 hits).",
                  {"root": S, "pattern": S}, ("pattern",),
                  Permission.OBSERVE, h_search),
        make_spec("propose_patch",
                  "Propose code edits; returns patch id + unified diff. Writes nothing.",
                  {"root": S, "edits": {"type": "array"}}, ("edits",),
                  Permission.OBSERVE, h_propose),
        make_spec("discard_patch", "Discard a proposed patch without applying it.",
                  {"patch_id": S}, ("patch_id",),
                  Permission.OBSERVE, h_discard),
        make_spec("apply_patch",
                  "Apply a proposed patch (all-or-nothing; rejects stale patches).",
                  {"patch_id": S}, ("patch_id",),
                  Permission.EXECUTE, h_apply),
        make_spec("run_tests",
                  "Run the project's test command (allowlisted, no shell).",
                  {"root": S, "command": S, "timeout_s": {"type": "number"}},
                  permission=Permission.EXECUTE, handler=h_tests),
    ]


__all__ = ["DevContext", "search_code", "run_tests", "make_specs"]
