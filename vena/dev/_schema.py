"""SQLite schema for the developer skill (mirrors NEXUS migration 004_dev)."""
from __future__ import annotations

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_index(
  root       TEXT NOT NULL,
  path       TEXT NOT NULL,
  language   TEXT NOT NULL DEFAULT '',
  symbols    TEXT NOT NULL DEFAULT '[]',
  lines      INTEGER NOT NULL DEFAULT 0,
  mtime      REAL NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (root, path)
);

CREATE TABLE IF NOT EXISTS patches(
  id         TEXT PRIMARY KEY,
  root       TEXT NOT NULL,
  edits_json TEXT NOT NULL DEFAULT '[]',
  diff_text  TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'proposed'
             CHECK (status IN ('proposed','applied','discarded','stale')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  applied_at TEXT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create dev tables if missing. Safe to call on every open."""
    conn.executescript(_SCHEMA)
    conn.commit()


__all__ = ["ensure_schema"]
