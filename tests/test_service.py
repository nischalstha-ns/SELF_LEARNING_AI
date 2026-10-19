"""Tests for vena/service/app.py — real HTTP server, loopback only."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from tests._stubs import FakeRegistry, install_stubs, uninstall_stubs

_state = install_stubs()
try:
    from vena.core.errors import VenaError
    from vena.core.types import Permission
    from vena.service.app import ServiceSettings, create_service, serve
    from vena.voice.wavutil import tone_wav
    from vena.voice.pipeline import VoicePipeline
    from vena.voice.player import MockPlayer
    from vena.voice.stt import MockSTT
    from vena.voice.tts import MockTTS
    from vena.voice.wakeword import MockMic
finally:
    pass


def tearDownModule():
    uninstall_stubs(_state)


def http(method, url, body=None, headers=None, raw=False):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            return resp.status, data, ctype
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = ServiceSettings(host="127.0.0.1", port=0,
                                        data_dir=self.tmp.name,
                                        max_json_body=1024)
        self.service = create_service(self.settings)
        self.service.attach_voice(VoicePipeline(
            stt=MockSTT(["hello from mic"]),
            tts=MockTTS(), player=MockPlayer(),
            mic=MockMic(tone_wav(0.2))))
        self.service.attach_workflows(FakeRegistry(
            policies={"read_file": Permission.EXECUTE,
                      "write_file": Permission.EXECUTE,
                      "click_at": Permission.ELEVATED}))
        self.server = serve(self.settings, self.service)
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.service.conn.close()
        self.tmp.cleanup()

    # -- basics --
    def test_health(self):
        code, data, _ = http("GET", self.base + "/health")
        self.assertEqual(code, 200)
        body = json.loads(data)
        self.assertTrue(body["ok"])
        self.assertTrue(body["subsystems"]["voice"])
        self.assertTrue(body["subsystems"]["workflows"])
        self.assertFalse(body["subsystems"]["chat"])

    def test_404(self):
        code, data, _ = http("GET", self.base + "/nope")
        self.assertEqual(code, 404)

    def test_unwired_endpoints_501(self):
        for method, path in [("POST", "/chat"), ("POST", "/chat/stream"),
                             ("GET", "/memories"), ("GET", "/permissions")]:
            code, _, _ = http(method, self.base + path,
                              body=b"{}" if method == "POST" else None,
                              headers={"Content-Type": "application/json"})
            self.assertEqual(code, 501, path)

    def test_json_body_too_large_413(self):
        big = b'{"x": "' + b"y" * 2048 + b'"}'
        code, _, _ = http("POST", self.base + "/voice/synthesize", body=big,
                          headers={"Content-Type": "application/json"})
        self.assertEqual(code, 413)

    def test_loopback_only_enforced(self):
        with self.assertRaises(VenaError):
            ServiceSettings(host="0.0.0.0", port=0).validate()

    # -- voice --
    def test_voice_status(self):
        code, data, _ = http("GET", self.base + "/voice/status")
        self.assertEqual(code, 200)
        body = json.loads(data)
        self.assertEqual(body["stt"], "mock")

    def test_synthesize_returns_wav(self):
        code, data, ctype = http(
            "POST", self.base + "/voice/synthesize",
            body=json.dumps({"text": "hi vena"}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 200)
        self.assertIn("audio/wav", ctype)
        self.assertTrue(data.startswith(b"RIFF"))

    def test_synthesize_requires_text(self):
        code, _, _ = http("POST", self.base + "/voice/synthesize",
                          body=b"{}",
                          headers={"Content-Type": "application/json"})
        self.assertEqual(code, 400)

    def test_transcribe(self):
        code, data, _ = http("POST", self.base + "/voice/transcribe",
                             body=tone_wav(0.2))
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)["text"], "hello from mic")

    def test_transcribe_rejects_non_wav(self):
        code, _, _ = http("POST", self.base + "/voice/transcribe",
                          body=b"garbage")
        self.assertEqual(code, 400)

    # -- workflows --
    def test_workflow_crud_and_replay(self):
        # create
        code, data, _ = http(
            "POST", self.base + "/workflows",
            body=json.dumps({"name": "w1", "steps": [
                {"tool": "read_file", "arguments": {"path": "/a"}}]}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 200)
        wf_id = json.loads(data)["id"]
        # list + get
        code, data, _ = http("GET", self.base + "/workflows")
        self.assertEqual(len(json.loads(data)), 1)
        code, data, _ = http("GET", self.base + f"/workflows/{wf_id}")
        self.assertEqual(json.loads(data)["name"], "w1")
        # dry-run replay
        code, data, _ = http(
            "POST", self.base + f"/workflows/{wf_id}/replay",
            body=json.dumps({"dry_run": True}).encode(),
            headers={"Content-Type": "application/json"})
        body = json.loads(data)
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "done")
        self.assertTrue(body["dry_run"])
        # real replay
        code, data, _ = http(
            "POST", self.base + f"/workflows/{wf_id}/replay",
            body=b"{}",
            headers={"Content-Type": "application/json"})
        body = json.loads(data)
        self.assertEqual(body["status"], "done")
        # run detail + delete
        code, data, _ = http("GET", self.base + f"/workflow-runs/{body['run_id']}")
        self.assertEqual(code, 200)
        code, _, _ = http("DELETE", self.base + f"/workflows/{wf_id}")
        self.assertEqual(code, 200)

    def test_workflow_replay_unknown(self):
        code, _, _ = http("POST", self.base + "/workflows/nope/replay",
                          body=b"{}",
                          headers={"Content-Type": "application/json"})
        self.assertEqual(code, 400)

    # -- pairing + companion --
    def test_pairing_flow(self):
        code, data, _ = http("POST", self.base + "/pairing/code")
        self.assertEqual(code, 200)
        pairing_code = json.loads(data)["code"]
        code, data, _ = http(
            "POST", self.base + "/pairing/redeem",
            body=json.dumps({"code": pairing_code,
                             "device_name": "test phone"}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 200)
        token = json.loads(data)["device_token"]
        # companion status with token
        code, data, _ = http(
            "GET", self.base + "/companion/status",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)["device"]["name"], "test phone")
        # without token -> 401
        code, _, _ = http("GET", self.base + "/companion/status")
        self.assertEqual(code, 401)
        # devices list + revoke
        code, data, _ = http("GET", self.base + "/devices")
        device_id = json.loads(data)[0]["id"]
        code, _, _ = http("DELETE", self.base + f"/devices/{device_id}")
        self.assertEqual(code, 200)
        code, _, _ = http(
            "GET", self.base + "/companion/status",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(code, 401)

    def test_redeem_bad_code(self):
        code, _, _ = http(
            "POST", self.base + "/pairing/redeem",
            body=json.dumps({"code": "NOPE1234",
                             "device_name": "x"}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 400)

    # -- backup --
    def test_backup_flow(self):
        code, data, _ = http(
            "POST", self.base + "/backup",
            body=json.dumps({"label": "t"}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 200)
        name = json.loads(data)["name"]
        code, data, _ = http("GET", self.base + "/backups")
        self.assertEqual(len(json.loads(data)), 1)
        code, data, _ = http(
            "POST", self.base + "/restore",
            body=json.dumps({"name": name}).encode(),
            headers={"Content-Type": "application/json"})
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(data)["ok"])

    # -- tasks --
    def test_tasks_list(self):
        code, data, _ = http("GET", self.base + "/tasks")
        self.assertEqual(code, 200)
        self.assertIsInstance(json.loads(data), list)


if __name__ == "__main__":
    unittest.main()
