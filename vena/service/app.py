"""Vena local HTTP service (loopback only).

Endpoints (all JSON unless noted):
  GET  /health
  POST /voice/transcribe   (raw WAV bytes in body -> {text, ...})
  POST /voice/synthesize   {text} -> audio/wav bytes
  GET  /voice/status
  GET  /workflows
  POST /workflows           {name, description?, steps?} | {from_task, name}
  GET  /workflows/{id}
  PATCH /workflows/{id}     {name?, description?, steps?}
  DELETE /workflows/{id}
  POST /workflows/{id}/replay {dry_run?, checkpoint?}
  GET  /workflow-runs/{id}
  POST /workflow-runs/{id}/revert
  GET  /tasks /tasks/{id}   (task history)
  POST /pairing/code         (one-time code for the companion app)
  POST /pairing/redeem      {code, device_name} -> {device_token} (shown once)
  GET  /devices
  DELETE /devices/{id}      (revoke a device)
  -- companion (requires: Authorization: Bearer <device_token>) --
  GET  /companion/status
  GET  /companion/notifications?since=
  POST /backup {label?}     (online DB backup, no downtime)
  GET  /backups
  POST /restore {name}       (restore into the live DB)
  -- not yet wired (sibling phases) -> 501 with a clear message --
  POST /chat  POST /chat/stream  GET /memories/*  GET|POST /permissions/*

Subsystems that depend on sibling phases (brain, memory, tool
registry) are attached via attach_*(); until then their endpoints
answer 501 naming what's missing — never a crash, never a hang.

Security: binds 127.0.0.1 ONLY (startup refuses anything else).
Request bodies are size-capped (413 beyond the cap).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .. import __version__
from ..companion.pairing import CompanionService
from ..core.errors import BodyTooLarge, VenaError
from ..core.logging import get_logger
from ..workflows.recorder import WorkflowStore
from ..workflows.replay import WorkflowReplayer
from . import backup as backup_mod
from .schema import ensure_schema

log = get_logger("vena.service")

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass
class ServiceSettings:
    host: str = field(default_factory=lambda: _env("VENA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("VENA_PORT", 8765))
    data_dir: str = field(default_factory=lambda: _env("VENA_DATA_DIR", "./data"))
    max_json_body: int = field(
        default_factory=lambda: _env_int("VENA_MAX_JSON_BODY_MB", 10) * 1024 * 1024)
    max_audio_body: int = field(
        default_factory=lambda: _env_int("VENA_MAX_AUDIO_BODY_MB", 100) * 1024 * 1024)

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "vena.db")

    def validate(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            raise VenaError(
                f"refusing to bind {self.host}: Vena only serves loopback "
                f"({_LOOPBACK_HOSTS})")


class VenaService:
    """Holds DB + subsystems; the HTTP handler delegates here."""

    def __init__(self, conn: sqlite3.Connection, settings: ServiceSettings):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.settings = settings
        self.data_dir = settings.data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        ensure_schema(self.conn)
        self.companion = CompanionService(self.conn)
        self.voice = None          # attach_voice()
        self._wf_store = None      # attach_workflows()
        self._wf_replayer = None
        self._router = None        # attach_brain()
        self._registry = None      # attach_registry()
        self._memories = None      # attach_memory()
        self._planner_factory = None
        self._lock = threading.Lock()

    # -- subsystem wiring (sibling phases plug in here) --
    def attach_voice(self, pipeline) -> None:
        self.voice = pipeline

    def attach_workflows(self, registry) -> None:
        self._wf_store = WorkflowStore(self.conn, registry)
        self._wf_replayer = WorkflowReplayer(self.conn, registry, self.data_dir,
                                             store=self._wf_store)

    # -- brain / planner / registry / memory wiring (all phases complete) --
    def attach_brain(self, router) -> None:
        """Attach the model router (vena.core.brain.ModelRouter)."""
        from vena.core.planner import Planner
        self._router = router
        # Planner is created per-turn so concurrent chats don't share state.
        self._planner_factory = lambda: Planner(router, self._require_registry())

    def attach_registry(self, registry) -> None:
        self._registry = registry

    def attach_memory(self, memory_service) -> None:
        self._memories = memory_service

    def _require_brain(self):
        if getattr(self, "_router", None) is None:
            raise _NotWired("brain (model router) not attached")
        return self._router

    def _require_registry(self):
        if getattr(self, "_registry", None) is None:
            raise _NotWired("tool registry not attached")
        return self._registry

    def _require_memories(self):
        if getattr(self, "_memories", None) is None:
            raise _NotWired("memory service not attached")
        return self._memories

    def new_planner(self):
        self._require_brain()
        return self._planner_factory()

    def _require_voice(self):
        if self.voice is None:
            raise _NotWired("voice pipeline not attached")
        return self.voice

    def _require_workflows(self):
        if self._wf_store is None or self._wf_replayer is None:
            raise _NotWired("tool registry not attached (workflows unavailable)")
        return self._wf_store, self._wf_replayer

    def health(self) -> dict:
        return {"ok": True, "version": __version__,
                "subsystems": {
                    "voice": self.voice is not None,
                    "workflows": self._wf_store is not None,
                    "companion": True,
                    "backup": True,
                    "chat": getattr(self, "_router", None) is not None,
                    "memories": getattr(self, "_memories", None) is not None,
                }}

    # -- tasks (history; planner-owned rows appear here too) --
    def list_tasks(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, title, status, created_at, updated_at FROM tasks"
            " ORDER BY updated_at DESC LIMIT ?",
            (max(1, min(limit, 200)),)).fetchall()
        return [dict(r) for r in rows]

    def get_task(self, task_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise VenaError(f"unknown task '{task_id}'")
        return dict(row)


class _NotWired(VenaError):
    """Subsystem not attached yet (sibling phase). Maps to HTTP 501."""


class _Handler(BaseHTTPRequestHandler):
    service: VenaService  # set by serve()
    settings: ServiceSettings

    # -- helpers --
    def log_message(self, fmt, *args):  # route through our logger
        log.info("%s %s", self.command, self.path.split("?")[0])

    def _send(self, code: int, obj, content_type: str = "application/json") -> None:
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code: int, message: str):
        self._send(code, {"error": message})

    def _read_limited(self, max_bytes: int) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length > max_bytes:
            raise BodyTooLarge(f"body exceeds {max_bytes} bytes")
        # read in chunks so a lying Content-Length can't over-allocate
        remaining = length
        chunks = []
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _json_body(self) -> dict:
        raw = self._read_limited(self.settings.max_json_body)
        if not raw:
            return {}
        try:
            obj = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError) as e:
            raise VenaError(f"invalid JSON: {e}")
        return obj if isinstance(obj, dict) else {}

    def _query(self) -> dict:
        return dict(urllib.parse.parse_qsl(
            urllib.parse.urlsplit(self.path).query))

    def _bearer(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

    def _companion_auth(self) -> dict:
        device = self.service.companion.authenticate(self._bearer())
        if device is None:
            raise _AuthError("invalid or missing device token")
        return device

    # -- dispatch (each request runs in its own thread; the service lock
    # serializes DB access) --
    def do_GET(self):
        try:
            with self.service._lock:
                self._route_get()
        except _AuthError as e:
            self._err(401, str(e))
        except _NotWired as e:
            self._err(501, str(e))
        except BodyTooLarge as e:
            self._err(413, str(e))
        except VenaError as e:
            self._err(400, str(e))
        except Exception:
            log.exception("GET %s failed", self.path)
            self._err(500, "internal error")

    def do_POST(self):
        try:
            with self.service._lock:
                self._route_post()
        except _AuthError as e:
            self._err(401, str(e))
        except _NotWired as e:
            self._err(501, str(e))
        except BodyTooLarge as e:
            self._err(413, str(e))
        except VenaError as e:
            self._err(400, str(e))
        except Exception:
            log.exception("POST %s failed", self.path)
            self._err(500, "internal error")

    def do_PATCH(self):
        try:
            with self.service._lock:
                self._do_patch()
        except _NotWired as e:
            self._err(501, str(e))
        except VenaError as e:
            self._err(400, str(e))
        except Exception:
            log.exception("PATCH %s failed", self.path)
            self._err(500, "internal error")

    def _do_patch(self):
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/workflows/"):
            wf_id = path[len("/workflows/"):].strip("/")
            store, _ = self.service._require_workflows()
            body = self._json_body()
            self._send(200, store.update_workflow(
                wf_id, name=body.get("name"),
                description=body.get("description"),
                steps=body.get("steps")))
        else:
            self._err(404, "not found")

    def do_DELETE(self):
        try:
            with self.service._lock:
                self._do_delete()
        except _NotWired as e:
            self._err(501, str(e))
        except VenaError as e:
            self._err(400, str(e))
        except Exception:
            log.exception("DELETE %s failed", self.path)
            self._err(500, "internal error")

    def _do_delete(self):
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/workflows/"):
            wf_id = path[len("/workflows/"):].strip("/")
            store, _ = self.service._require_workflows()
            store.delete_workflow(wf_id)
            self._send(200, {"ok": True})
        elif path.startswith("/devices/"):
            device_id = path[len("/devices/"):].strip("/")
            self.service.companion.revoke(device_id)
            self._send(200, {"ok": True})
        else:
            self._err(404, "not found")

    # -- GET routes --
    def _route_get(self):
        svc = self.service
        path = urllib.parse.urlsplit(self.path).path.rstrip("/") or "/"
        q = self._query()

        if path == "/health":
            return self._send(200, svc.health())
        if path == "/voice/status":
            voice = svc._require_voice()
            return self._send(200, {"enabled": True,
                                    "stt": voice.stt.name,
                                    "tts": voice.tts.name,
                                    "player": voice.player.name,
                                    "mic": voice.mic.name if voice.mic else None})
        if path == "/workflows":
            store, _ = svc._require_workflows()
            return self._send(200, store.list_workflows())
        if path.startswith("/workflows/"):
            store, _ = svc._require_workflows()
            return self._send(200, store.get_workflow(
                path[len("/workflows/"):].strip("/")))
        if path.startswith("/workflow-runs/"):
            _, replayer = svc._require_workflows()
            return self._send(200, replayer.get_run(
                path[len("/workflow-runs/"):].strip("/")))
        if path == "/tasks":
            return self._send(200, svc.list_tasks(
                int(q.get("limit", 50))))
        if path.startswith("/tasks/"):
            return self._send(200, svc.get_task(
                path[len("/tasks/"):].strip("/")))
        if path == "/devices":
            return self._send(200, svc.companion.list_devices())
        if path == "/companion/status":
            device = self._companion_auth()
            return self._send(200, {
                "device": {"id": device["id"], "name": device["name"]},
                "unread_notifications": svc.companion.unread_count(),
                "health": svc.health()})
        if path == "/companion/notifications":
            self._companion_auth()
            since = int(q.get("since", 0))
            return self._send(200, svc.companion.list_notifications(since_id=since))
        if path == "/backups":
            return self._send(200, backup_mod.list_backups(svc.data_dir))
        if path == "/memories" or path.startswith("/memories/"):
            return self._route_memories(svc, path, q)
        if path == "/permissions" or path.startswith("/permissions/"):
            return self._route_permissions(svc, path)
        return self._err(404, "not found")

    def _route_memories(self, svc, path, q):
        mem = svc._require_memories()
        sub = path[len("/memories"):].strip("/")
        if sub == "" or sub == "search":
            query = q.get("q", "")
            if not query:
                return self._err(400, "q is required")
            return self._send(200, mem.recall(
                query, limit=int(q.get("limit", 5))))
        if sub == "pending":
            return self._send(200, mem.list_pending(
                limit=int(q.get("limit", 50))))
        if sub.startswith("approve/"):
            mem.approve(sub[len("approve/"):])
            return self._send(200, {"ok": True})
        return self._err(404, "not found")

    def _route_permissions(self, svc, path):
        reg = svc._require_registry()
        sub = path[len("/permissions"):].strip("/")
        if sub == "":
            return self._send(200, [
                {"name": s.name, "permission": s.default_permission.value,
                 "description": s.description}
                for s in reg.specs()])
        # GET /permissions/<tool> returns its level; use POST to change
        for s in reg.specs():
            if s.name == sub:
                return self._send(200, {"name": s.name,
                                        "permission": s.default_permission.value})
        return self._err(404, f"unknown tool '{sub}'")

    # -- POST routes --
    def _route_post(self):
        svc = self.service
        path = urllib.parse.urlsplit(self.path).path.rstrip("/") or "/"

        if path == "/voice/transcribe":
            voice = svc._require_voice()
            wav_bytes = self._read_limited(svc.settings.max_audio_body)
            if wav_bytes[:4] != b"RIFF":
                return self._err(400, "body must be WAV audio")
            t = voice.stt.transcribe(wav_bytes)
            return self._send(200, {"text": t.text, "language": t.language,
                                    "confidence": t.confidence})
        if path == "/voice/synthesize":
            voice = svc._require_voice()
            body = self._json_body()
            text = body.get("text", "")
            if not text.strip():
                return self._err(400, "text is required")
            wav_bytes = voice.tts.synthesize(text)
            return self._send(200, wav_bytes, content_type="audio/wav")
        if path == "/workflows":
            store, _ = svc._require_workflows()
            body = self._json_body()
            if "from_task" in body:
                return self._send(200, store.record_from_task(
                    body["from_task"], body.get("name", ""),
                    body.get("description", "")))
            return self._send(200, store.create_workflow(
                body.get("name", ""), body.get("description", ""),
                body.get("steps", [])))
        if path.endswith("/replay") and path.startswith("/workflows/"):
            _, replayer = svc._require_workflows()
            wf_id = path[len("/workflows/"):-len("/replay")].strip("/")
            body = self._json_body()
            return self._send(200, replayer.replay(
                wf_id, dry_run=bool(body.get("dry_run", False)),
                checkpoint=bool(body.get("checkpoint", True))))
        if path.endswith("/revert") and path.startswith("/workflow-runs/"):
            _, replayer = svc._require_workflows()
            run_id = path[len("/workflow-runs/"):-len("/revert")].strip("/")
            return self._send(200, replayer.revert_run(run_id))
        if path == "/pairing/code":
            return self._send(200, svc.companion.create_pairing_code())
        if path == "/pairing/redeem":
            body = self._json_body()
            return self._send(200, svc.companion.redeem(
                body.get("code", ""), body.get("device_name", "")))
        if path.startswith("/companion/notifications/") and path.endswith("/read"):
            self._companion_auth()
            nid = path[len("/companion/notifications/"):-len("/read")].strip("/")
            svc.companion.mark_read(int(nid))
            return self._send(200, {"ok": True})
        if path == "/backup":
            body = self._json_body()
            return self._send(200, backup_mod.backup(
                svc.conn, svc.data_dir, body.get("label", "")))
        if path == "/restore":
            body = self._json_body()
            if not body.get("name"):
                return self._err(400, "name is required")
            return self._send(200, backup_mod.restore(
                svc.conn, svc.data_dir, body["name"]))
        if path in ("/chat", "/chat/stream"):
            return self._route_chat(svc, path)
        return self._err(404, "not found")

    def _route_chat(self, svc, path):
        """Run one planner turn. /chat returns the final summary;
        /chat/stream streams planner events as Server-Sent Events."""
        planner = svc.new_planner()
        body = self._json_body()
        message = body.get("message", "")
        if not message.strip():
            return self._err(400, "message is required")
        if path == "/chat/stream":
            return self._stream_planner(planner, message)
        # Non-streaming: run to completion, return the final event.
        final = None
        for event in planner.run(message):
            final = event
        if final is None:
            return self._send(200, {"status": "done", "summary": ""})
        return self._send(200, {"status": final.payload.get("status", "done"),
                                "summary": final.payload.get("summary", ""),
                                "steps": final.payload.get("steps", [])})

    def _stream_planner(self, planner, message):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for event in planner.run(message):
                line = f"event: {event.kind}\ndata: {json.dumps(event.payload)}\n\n"
                self.wfile.write(line.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client went away; the turn keeps no server-side state


class _AuthError(VenaError):
    pass


def create_service(settings: ServiceSettings | None = None) -> VenaService:
    settings = settings or ServiceSettings()
    settings.validate()
    os.makedirs(settings.data_dir, exist_ok=True)
    # The Store opens the DB (check_same_thread=False: the
    # ThreadingHTTPServer handles each request in its own thread; the
    # handler holds service._lock around every request) and applies the
    # versioned migrations (conversations, memories, permission_policies,
    # ...) onto this connection, shared by the registry and memory service.
    from vena.memory.store import Store
    migrations_dir = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "migrations"))
    if not os.path.isdir(migrations_dir):
        # Fallback: repo-root-relative (run_vena.py chdirs to repo root).
        migrations_dir = os.path.join(os.getcwd(), "data", "migrations")
    store = Store(settings.db_path, migrations_dir)
    return VenaService(store.conn, settings)


def serve(settings: ServiceSettings | None = None,
          service: VenaService | None = None) -> ThreadingHTTPServer:
    """Start the loopback-only HTTP server. Raises if host isn't loopback."""
    settings = settings or ServiceSettings()
    settings.validate()  # NEVER serve on 0.0.0.0 / LAN
    service = service or create_service(settings)
    handler = type("VenaHandler", (_Handler,), {})
    handler.service = service
    handler.settings = settings
    server = ThreadingHTTPServer((settings.host, settings.port), handler)
    log.info("Vena listening on %s:%d (loopback only)",
             settings.host, server.server_port)
    return server
