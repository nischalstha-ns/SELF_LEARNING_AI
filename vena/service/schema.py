"""Database schema for Vena's own subsystems.

Creates the tables owned by the voice/workflows/companion/service
phases with CREATE TABLE IF NOT EXISTS — never drops or alters, so
sibling phases' migrations can extend these tables later without
conflict.

Why here and not in a migration runner: the migration system belongs
to the memory phase (sibling). The service must be able to start and
serve its own endpoints even before that lands.
"""
from __future__ import annotations

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS workflows(
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  description     TEXT NOT NULL DEFAULT '',
  steps_json      TEXT NOT NULL DEFAULT '[]',
  created_from_task TEXT NULL REFERENCES tasks(id) ON DELETE SET NULL,
  created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS workflow_runs(
  id              TEXT PRIMARY KEY,
  workflow_id     TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  task_id         TEXT NULL REFERENCES tasks(id) ON DELETE SET NULL,
  status          TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running','awaiting_approval','done','failed','cancelled','reverted')),
  dry_run         INTEGER NOT NULL DEFAULT 0,
  checkpoint_dir  TEXT NULL,
  result_json     TEXT NOT NULL DEFAULT '{}',
  created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS pairing_codes(
  code_hash  TEXT PRIMARY KEY,
  expires_at TEXT NOT NULL,
  used       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS devices(
  id         TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen  TEXT NULL
);

CREATE TABLE IF NOT EXISTS notifications(
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,
  title      TEXT NOT NULL,
  body       TEXT NOT NULL DEFAULT '',
  payload    TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  read_at    TEXT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create Vena's subsystem tables if they don't exist yet."""
    conn.executescript(_SCHEMA)
    conn.commit()
