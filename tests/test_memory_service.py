"""Tests for vena.memory.service.MemoryService (Phase 6: memory).

Store strategy: use the real vena.memory.store.Store when it exists
(owned by another agent); otherwise fall back to a minimal test-local
store built from the exact NEXUS schema, so the service logic is verified
now and the same tests run unchanged once the real store lands.
"""
from __future__ import annotations

import os
import sqlite3
import unittest

from vena.core.errors import MemoryError
from vena.core.types import Role
from vena.memory import service
from vena.memory.embeddings import MockEmbeddings
from vena.memory.service import MemoryService

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE conversations (
  id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
  project_id TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
  role TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', tool_name TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE VIRTUAL TABLE messages_fts USING fts5(content, conversation_id UNINDEXED);
CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL,
  root_path TEXT NOT NULL DEFAULT '');
CREATE TABLE memories (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL,
  consent TEXT NOT NULL DEFAULT 'explicit', project_id TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE VIRTUAL TABLE memories_fts USING fts5(content, kind UNINDEXED);
CREATE TABLE memory_embeddings (
  memory_id TEXT PRIMARY KEY, embedding_json TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT '');
CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', plan_json TEXT NOT NULL DEFAULT '[]');
CREATE TABLE tool_executions (id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_name TEXT NOT NULL);
CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL);
"""


class _LocalStore:
    """Minimal stand-in until vena.memory.store lands. Same schema."""

    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)

    @property
    def conn(self):
        return self._conn


def _make_store():
    """Prefer the real Store; fall back to the local one if it is missing
    or its migrations don't yet cover the tables the service needs
    (memory_embeddings arrives with migration 002)."""
    try:
        from vena.memory.store import Store as RealStore
    except ImportError:
        return _LocalStore()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mig = os.path.join(here, "data", "migrations")
    try:
        store = RealStore(":memory:", migrations_dir=mig)
        tables = {r[0] for r in
                  store.conn.execute("SELECT name FROM sqlite_master"
                                     " WHERE type='table'").fetchall()}
        if {"memories", "memories_fts", "memory_embeddings"} <= tables:
            return store
    except Exception:
        pass
    return _LocalStore()


class ServiceTestBase(unittest.TestCase):
    def setUp(self):
        self.svc = MemoryService(_make_store())
        self.emb = MockEmbeddings()


class ConversationTests(ServiceTestBase):
    def test_round_trip(self):
        cid = self.svc.create_conversation("test")
        self.svc.add_message(cid, Role.USER, "hello")
        self.svc.add_message(cid, Role.ASSISTANT, "hi there")
        msgs = self.svc.get_messages(cid)
        self.assertEqual([m.content for m in msgs], ["hello", "hi there"])
        self.assertEqual(msgs[0].role, Role.USER)

    def test_search_messages(self):
        cid = self.svc.create_conversation()
        self.svc.add_message(cid, Role.USER, "the capital of France is Paris")
        hits = self.svc.search_messages("Paris")
        self.assertEqual(len(hits), 1)
        self.assertIn("Paris", hits[0]["snip"])


class RememberRecallTests(ServiceTestBase):
    def test_remember_and_recall(self):
        mid = self.svc.remember("fact", "my exam is on friday")
        hits = self.svc.recall("friday")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], mid)

    def test_kind_filter(self):
        self.svc.remember("preference", "i like strong tea")
        self.svc.remember("fact", "tea was invented in china")
        hits = self.svc.recall("tea", kind="preference")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["kind"], "preference")

    def test_bad_kind_and_consent(self):
        with self.assertRaises(MemoryError):
            self.svc.remember("nope", "x")
        with self.assertRaises(MemoryError):
            self.svc.remember("fact", "x", consent="maybe")

    def test_pending_excluded_until_approved(self):
        mid = self.svc.remember("fact", "user birthday is march third",
                                consent="inferred-pending")
        self.assertEqual(self.svc.recall("birthday"), [])  # hidden
        pending = self.svc.list_pending()
        self.assertEqual([p["id"] for p in pending], [mid])
        self.svc.approve(mid)  # user reviews -> now visible
        self.assertEqual(len(self.svc.recall("birthday")), 1)
        self.assertEqual(self.svc.list_pending(), [])

    def test_approve_non_pending_raises(self):
        mid = self.svc.remember("fact", "explicit fact")
        with self.assertRaises(MemoryError):
            self.svc.approve(mid)
        with self.assertRaises(MemoryError):
            self.svc.approve("does-not-exist")

    def test_forget(self):
        mid = self.svc.remember("fact", "temporary note here")
        self.assertTrue(self.svc.forget(mid))
        self.assertEqual(self.svc.recall("temporary"), [])
        self.assertFalse(self.svc.forget(mid))  # already gone
        self.assertFalse(self.svc.forget("nope"))

    def test_update_memory(self):
        mid = self.svc.remember("fact", "the sky is green")
        updated = self.svc.update_memory(mid, content="the sky is blue")
        self.assertEqual(updated["content"], "the sky is blue")
        self.assertEqual(len(self.svc.recall("blue")), 1)
        self.assertEqual(self.svc.recall("green"), [])

    def test_update_validations(self):
        mid = self.svc.remember("fact", "something")
        with self.assertRaises(MemoryError):
            self.svc.update_memory(mid)
        with self.assertRaises(MemoryError):
            self.svc.update_memory(mid, content="  ")
        with self.assertRaises(MemoryError):
            self.svc.update_memory(mid, kind="nope")
        with self.assertRaises(MemoryError):
            self.svc.update_memory("missing", content="x")

    def test_update_keeps_consent(self):
        mid = self.svc.remember("fact", "inferred thing", consent="inferred-pending")
        self.svc.update_memory(mid, content="inferred thing edited")
        row = self.svc.get_memory(mid)
        self.assertEqual(row["consent"], "inferred-pending")  # still needs review


class SemanticTests(ServiceTestBase):
    def test_ensure_embeddings_backfills(self):
        self.svc.remember("fact", "buy milk tomorrow morning")
        self.svc.remember("fact", "quantum physics lecture notes")
        added = self.svc.ensure_embeddings(self.emb)
        self.assertEqual(added, 2)
        self.assertEqual(self.svc.ensure_embeddings(self.emb), 0)  # idempotent

    def test_recall_semantic(self):
        self.svc.remember("fact", "buy milk tomorrow morning")
        self.svc.remember("fact", "quantum physics lecture notes")
        hits = self.svc.recall_semantic("buy milk", self.emb)
        self.assertTrue(hits)
        self.assertIn("milk", hits[0]["content"])
        self.assertGreater(hits[0]["score"], 0)

    def test_semantic_excludes_pending(self):
        self.svc.remember("fact", "buy milk tomorrow", consent="inferred-pending")
        hits = self.svc.recall_semantic("buy milk", self.emb)
        self.assertEqual(hits, [])

    def test_update_invalidates_embedding(self):
        mid = self.svc.remember("fact", "buy milk tomorrow morning")
        self.svc.ensure_embeddings(self.emb)
        self.svc.update_memory(mid, content="completely different zebra xylophone")
        # embedding was invalidated; semantic recall re-backfills lazily
        hits = self.svc.recall_semantic("zebra", self.emb)
        self.assertTrue(any(h["id"] == mid for h in hits))

    def test_hybrid_without_embedder(self):
        self.svc.remember("fact", "my exam is on friday")
        hits = self.svc.recall_hybrid("friday")  # degrades to keyword
        self.assertEqual(len(hits), 1)

    def test_hybrid_with_embedder(self):
        self.svc.remember("fact", "my exam is on friday")
        self.svc.remember("fact", "unrelated zebra fact")
        hits = self.svc.recall_hybrid("friday", self.emb)
        self.assertTrue(hits)
        self.assertIn("friday", hits[0]["content"])


class UserControlTests(ServiceTestBase):
    def test_export_and_wipe(self):
        cid = self.svc.create_conversation("c")
        self.svc.add_message(cid, Role.USER, "hi")
        self.svc.remember("fact", "some fact")
        data = self.svc.export_user_data()
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(len(data["memories"]), 1)
        self.svc.delete_user_data()
        data = self.svc.export_user_data()
        self.assertEqual(data["conversations"], [])
        self.assertEqual(data["memories"], [])

    def test_needs_store(self):
        with self.assertRaises(MemoryError):
            MemoryService(None)

    def test_store_import_resolves(self):
        # service.py imports vena.memory.store.Store when available,
        # else degrades to None (documented dependency, other agent owns it)
        try:
            from vena.memory.store import Store as RealStore
        except ImportError:
            RealStore = None
        self.assertIs(service.Store, RealStore)


if __name__ == "__main__":
    unittest.main()
