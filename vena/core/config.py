"""Configuration from environment variables. No secrets in code, ever.

Every setting reads from a VENA_-prefixed env var with a safe default, so a
fresh clone runs without any setup. Secrets (API keys) are NOT read here —
they go through SecretStore (core/secrets.py), which prefers the OS keyring.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from .errors import ConfigError


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError as e:
        raise ConfigError(f"{name} must be an integer") from e


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError as e:
        raise ConfigError(f"{name} must be a number") from e


@dataclass
class Settings:
    # Paths
    data_dir: str = field(default_factory=lambda: os.environ.get("VENA_DATA_DIR", "./data"))
    # Model routing (brain.py reads these in Phase 2)
    default_provider: str = field(default_factory=lambda: os.environ.get("VENA_PROVIDER", "mock"))
    offline_only: bool = field(default_factory=lambda: os.environ.get("VENA_OFFLINE_ONLY", "0") == "1")
    request_timeout_s: float = field(default_factory=lambda: _float("VENA_REQUEST_TIMEOUT_S", 60.0))
    max_retries: int = field(default_factory=lambda: _int("VENA_MAX_RETRIES", 2))
    # Planner bounds
    max_iterations: int = field(default_factory=lambda: _int("VENA_MAX_ITERATIONS", 12))
    task_timeout_s: float = field(default_factory=lambda: _float("VENA_TASK_TIMEOUT_S", 300.0))
    tool_timeout_s: float = field(default_factory=lambda: _float("VENA_TOOL_TIMEOUT_S", 60.0))
    # Tool sandbox: file tools are jailed to these roots; commands to this allowlist.
    approved_roots: List[str] = field(default_factory=lambda: [
        p for p in os.environ.get("VENA_APPROVED_ROOTS", "").split(os.pathsep) if p
    ])
    allowed_commands: List[str] = field(default_factory=lambda: [
        c for c in os.environ.get("VENA_ALLOWED_COMMANDS", "ls,dir,echo,python,python3,pytest,git").split(",") if c
    ])
    # Server (always loopback; the service refuses to bind elsewhere)
    host: str = field(default_factory=lambda: os.environ.get("VENA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _int("VENA_PORT", 8765))

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "vena.db")
