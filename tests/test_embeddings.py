"""Tests for vena.memory.embeddings (Phase 6: memory)."""
from __future__ import annotations

import contextlib
import json
import math
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from vena.core.errors import ProviderError, ProviderUnavailable
from vena.memory import embeddings
from vena.memory.embeddings import (
    MockEmbeddings,
    OpenAIEmbeddings,
    cosine_similarity,
)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_POST(self):  # noqa: N802
        payload = self.server.payload
        status = getattr(self.server, "status", 200)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def canned_server(payload: bytes, status: int = 200):
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    srv.payload = payload
    srv.status = status
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        t.join()


class CosineTests(unittest.TestCase):
    def test_identical(self):
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)

    def test_orthogonal(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_zero_vector(self):
        self.assertEqual(cosine_similarity([0, 0], [1, 2]), 0.0)

    def test_opposite(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)


class MockEmbeddingsTests(unittest.TestCase):
    def test_deterministic(self):
        e = MockEmbeddings()
        self.assertEqual(e.embed(["hello world"]), e.embed(["hello world"]))

    def test_normalized(self):
        e = MockEmbeddings()
        # non-empty texts -> unit vectors; empty text -> zero vector
        for vec in e.embed(["some text here", "another one"]):
            norm = math.sqrt(sum(x * x for x in vec))
            self.assertAlmostEqual(norm, 1.0, places=6)
        self.assertEqual(e.embed([""])[0], [0.0] * e.dims)

    def test_batch_order_and_dims(self):
        e = MockEmbeddings()
        vecs = e.embed(["a", "b c", "d e f"])
        self.assertEqual(len(vecs), 3)
        self.assertTrue(all(len(v) == e.dims == 128 for v in vecs))

    def test_similar_texts_score_higher(self):
        e = MockEmbeddings()
        q = e.embed(["buy milk tomorrow"])[0]
        close = e.embed(["buy milk today"])[0]
        far = e.embed(["quantum chromodynamics lecture"])[0]
        self.assertGreater(cosine_similarity(q, close), cosine_similarity(q, far))


class OpenAIEmbeddingsTests(unittest.TestCase):
    def test_parses_response(self):
        body = {"data": [
            {"index": 1, "embedding": [0.1, 0.2]},
            {"index": 0, "embedding": [0.3, 0.4]},
        ]}
        with canned_server(json.dumps(body).encode()) as srv:
            e = OpenAIEmbeddings(f"http://127.0.0.1:{srv.server_port}", "m")
            vecs = e.embed(["x", "y"])
        # sorted by index -> original input order preserved
        self.assertEqual(vecs, [[0.3, 0.4], [0.1, 0.2]])
        self.assertEqual(e.dims, 2)

    def test_empty_input(self):
        e = OpenAIEmbeddings("http://127.0.0.1:1", "m")
        self.assertEqual(e.embed([]), [])

    def test_http_error(self):
        with canned_server(b"{}", status=500) as srv:
            e = OpenAIEmbeddings(f"http://127.0.0.1:{srv.server_port}", "m")
            with self.assertRaises(ProviderError):
                e.embed(["x"])

    def test_unreachable(self):
        e = OpenAIEmbeddings("http://127.0.0.1:1", "m")
        with self.assertRaises(ProviderUnavailable):
            e.embed(["x"], timeout_s=1.0)


if __name__ == "__main__":
    unittest.main()
