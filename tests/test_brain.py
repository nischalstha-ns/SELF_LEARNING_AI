"""Tests for vena.core.brain (Phase 2: chat brain).

Covers: MockProvider scripting, OpenAICompatibleProvider complete() parsing,
streaming SSE with fragmented tool-call reassembly (against a local HTTP
server — no network), OllamaProvider defaults, ModelRouter failover /
auth-fail-fast / offline-only filtering, and the VENA_* env factory.
"""
from __future__ import annotations

import contextlib
import json
import os
import threading
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, HTTPServer

from vena.core import brain
from vena.core.errors import ProviderAuthError, ProviderError, ProviderUnavailable
from vena.core.types import Message, ProviderResponse, Role, ToolCall


def _msg(text: str = "hello") -> list[Message]:
    return [Message(role=Role.USER, content=text)]


# ---------------------------------------------------------------------------
# Tiny canned HTTP server for provider wire-format tests
# ---------------------------------------------------------------------------

class _CannedHandler(BaseHTTPRequestHandler):
    """Serves whatever bytes are in server.payload for any POST."""
    protocol_version = "HTTP/1.0"

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.server.seen_bodies.append(self.rfile.read(length))
        payload = self.server.payload
        status = getattr(self.server, "status", 200)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence test noise
        pass


@contextlib.contextmanager
def canned_server(payload: bytes, status: int = 200):
    srv = HTTPServer(("127.0.0.1", 0), _CannedHandler)
    srv.payload = payload
    srv.status = status
    srv.seen_bodies = []
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        t.join()


def _env(**overrides):
    """Patch os.environ: clear all VENA_ vars, then apply overrides."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith("VENA_")}
    clean.update({f"VENA_{k}": v for k, v in overrides.items()})
    return unittest.mock.patch.dict(os.environ, clean, clear=True)


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------

class MockProviderTests(unittest.TestCase):
    def test_scripted_then_fallback(self):
        p = brain.MockProvider(script=[ProviderResponse(text="first")])
        self.assertEqual(p.complete(_msg()).text, "first")
        # script exhausted -> fallback repeats forever, never crashes
        self.assertEqual(p.complete(_msg()).text, "mock reply")
        self.assertEqual(p.complete(_msg()).text, "mock reply")

    def test_calls_recorded(self):
        p = brain.MockProvider()
        p.complete(_msg("hi"))
        self.assertEqual(p.calls[0][0].content, "hi")

    def test_script_tool_call(self):
        p = brain.MockProvider()
        p.script_tool_call("read_file", {"path": "/tmp/x"}, text="reading")
        r = p.complete(_msg())
        self.assertEqual(r.tool_calls[0].name, "read_file")
        self.assertEqual(r.tool_calls[0].arguments, {"path": "/tmp/x"})

    def test_health_never_raises(self):
        self.assertTrue(brain.MockProvider().health_check().reachable)


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider: complete()
# ---------------------------------------------------------------------------

class OpenAICompleteTests(unittest.TestCase):
    def test_parses_text_and_tool_calls(self):
        body = {
            "model": "m",
            "choices": [{"message": {
                "content": "done",
                "tool_calls": [{"id": "c1", "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "/a"})}}]}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        }
        with canned_server(json.dumps(body).encode()) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            r = p.complete(_msg(), tools=[{"type": "function"}])
        self.assertEqual(r.text, "done")
        self.assertEqual(r.tool_calls[0].name, "read_file")
        self.assertEqual(r.tool_calls[0].arguments, {"path": "/a"})
        self.assertEqual(r.tool_calls[0].call_id, "c1")
        self.assertEqual(r.usage["prompt_tokens"], 3)
        # tools were actually sent in the payload
        sent = json.loads(srv.seen_bodies[0])
        self.assertIn("tools", sent)
        self.assertEqual(sent["model"], "m")

    def test_bad_tool_arguments_kept_raw(self):
        body = {"choices": [{"message": {
            "content": "",
            "tool_calls": [{"id": "c1", "function": {
                "name": "x", "arguments": "{not json"}}]}}]}
        with canned_server(json.dumps(body).encode()) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            r = p.complete(_msg())
        self.assertIn("_raw", r.tool_calls[0].arguments)

    def test_auth_error(self):
        with canned_server(b"{}", status=401) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            with self.assertRaises(ProviderAuthError):
                p.complete(_msg())

    def test_unreachable(self):
        p = brain.OpenAICompatibleProvider("http://127.0.0.1:1", "m")
        with self.assertRaises(ProviderUnavailable):
            p.complete(_msg(), timeout_s=1.0)

    def test_health_check_false_on_refused(self):
        p = brain.OpenAICompatibleProvider("http://127.0.0.1:1", "m")
        self.assertFalse(p.health_check(timeout_s=1.0).reachable)


# ---------------------------------------------------------------------------
# Streaming with fragmented tool-call reassembly
# ---------------------------------------------------------------------------

def _sse(*chunks: str) -> bytes:
    return "".join(f"data: {c}\n\n" for c in chunks).encode() + b"data: [DONE]\n\n"


class StreamingTests(unittest.TestCase):
    def test_text_deltas_stream(self):
        payload = _sse(
            json.dumps({"model": "m", "choices": [{"delta": {"content": "Hel"}}]}),
            json.dumps({"choices": [{"delta": {"content": "lo"}}]}),
        )
        with canned_server(payload) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            chunks = list(p.stream_complete(_msg()))
        texts = [c.text for c in chunks[:-1]]
        self.assertEqual(texts, ["Hel", "lo"])
        self.assertEqual(chunks[-1].text, "Hello")  # final = full text

    def test_fragmented_tool_call_reassembled(self):
        # tool-call arguments split across two SSE chunks (the real-world case)
        chunk1 = {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "call_9",
             "function": {"name": "read_file", "arguments": '{"pa'}}]}}]}
        chunk2 = {"choices": [{"delta": {"tool_calls": [
            {"index": 0,
             "function": {"arguments": 'th": "/tmp/x"}'}}]}}]}
        payload = _sse(json.dumps(chunk1), json.dumps(chunk2))
        with canned_server(payload) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            chunks = list(p.stream_complete(_msg()))
        final = chunks[-1]
        self.assertEqual(len(final.tool_calls), 1)
        tc = final.tool_calls[0]
        self.assertEqual(tc.name, "read_file")
        self.assertEqual(tc.arguments, {"path": "/tmp/x"})
        self.assertEqual(tc.call_id, "call_9")

    def test_stream_auth_error(self):
        with canned_server(b"{}", status=403) as srv:
            p = brain.OpenAICompatibleProvider(
                f"http://127.0.0.1:{srv.server_port}", "m")
            with self.assertRaises(ProviderAuthError):
                list(p.stream_complete(_msg()))


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class OllamaProviderTests(unittest.TestCase):
    def test_defaults(self):
        p = brain.OllamaProvider("llama3.1")
        self.assertEqual(p.name, "ollama")
        self.assertTrue(p.is_local)
        self.assertEqual(p.base_url, "http://127.0.0.1:11434/v1")
        self.assertEqual(p.model_id, "llama3.1")

    def test_env_base_url_override(self):
        with _env(OLLAMA_BASE_URL="http://x:11434/v1"):
            p = brain.OllamaProvider("m")
        self.assertEqual(p.base_url, "http://x:11434/v1")


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------

class _FailingProvider(brain.AIProvider):
    name = "failing"

    def __init__(self, exc: Exception, is_local: bool = False):
        self.exc = exc
        self.is_local = is_local
        self.attempts = 0

    def complete(self, messages, tools=None, timeout_s=60.0, **kw):
        self.attempts += 1
        raise self.exc

    def health_check(self, timeout_s=5.0):
        return brain.HealthStatus(False, "down")


class RouterTests(unittest.TestCase):
    def test_failover(self):
        bad = _FailingProvider(ProviderUnavailable("down"))
        good = brain.MockProvider(script=[ProviderResponse(text="ok")])
        r = brain.ModelRouter([bad, good], max_retries=0).complete(_msg())
        self.assertEqual(r.text, "ok")

    def test_auth_error_fails_fast(self):
        bad = _FailingProvider(ProviderAuthError("bad key"))
        good = brain.MockProvider()
        router = brain.ModelRouter([bad, good], max_retries=3)
        with self.assertRaises(ProviderAuthError):
            router.complete(_msg())
        self.assertEqual(good.calls, [])  # never tried the next provider

    def test_offline_only_filters_remote(self):
        remote = brain.MockProvider(script=[ProviderResponse(text="remote")],
                                    is_local=False)
        local = brain.MockProvider(script=[ProviderResponse(text="local")])
        r = brain.ModelRouter([remote, local], offline_only=True).complete(_msg())
        self.assertEqual(r.text, "local")

    def test_no_candidates(self):
        remote = brain.MockProvider(is_local=False)
        with self.assertRaises(ProviderUnavailable):
            brain.ModelRouter([remote], offline_only=True).complete(_msg())

    def test_require_local_flag(self):
        remote = brain.MockProvider(script=[ProviderResponse(text="remote")],
                                    is_local=False)
        local = brain.MockProvider(script=[ProviderResponse(text="local")])
        r = brain.ModelRouter([remote, local]).complete(_msg(), require_local=True)
        self.assertEqual(r.text, "local")

    def test_empty_providers_rejected(self):
        with self.assertRaises(ValueError):
            brain.ModelRouter([])


# ---------------------------------------------------------------------------
# Env factory
# ---------------------------------------------------------------------------

class EnvFactoryTests(unittest.TestCase):
    def test_default_is_mock(self):
        with _env():
            providers, offline = brain.providers_from_env()
        self.assertEqual(len(providers), 1)
        self.assertIsInstance(providers[0], brain.MockProvider)
        self.assertFalse(offline)

    def test_unknown_provider_falls_back_to_mock(self):
        with _env(PROVIDER="nonsense"):
            providers, _ = brain.providers_from_env()
        self.assertIsInstance(providers[0], brain.MockProvider)

    def test_ollama(self):
        with _env(PROVIDER="ollama", OLLAMA_MODEL="phi3"):
            providers, _ = brain.providers_from_env()
        self.assertIsInstance(providers[0], brain.OllamaProvider)
        self.assertTrue(providers[0].is_local)
        self.assertEqual(providers[0].model_id, "phi3")

    def test_openai_no_key_does_not_crash(self):
        with _env(PROVIDER="openai", OPENAI_MODEL="gpt-x"):
            providers, _ = brain.providers_from_env()
        p = providers[0]
        self.assertFalse(p.is_local)
        self.assertNotIn("Authorization", p._headers())  # no key -> no header

    def test_offline_only_flag(self):
        with _env(PROVIDER="mock", OFFLINE_ONLY="1"):
            _, offline = brain.providers_from_env()
        self.assertTrue(offline)

    def test_build_router(self):
        with _env(PROVIDER="mock", REQUEST_TIMEOUT_S="5", MAX_RETRIES="1"):
            router = brain.build_router()
        self.assertIsInstance(router, brain.ModelRouter)
        self.assertEqual(router.timeout_s, 5.0)
        self.assertEqual(router.max_retries, 1)


if __name__ == "__main__":
    unittest.main()
