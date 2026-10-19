#!/usr/bin/env python3
"""Run Vena — one command to start everything.

Starts the local HTTP service on 127.0.0.1 (loopback only, never LAN).
Voice engines are chosen from VENA_* environment variables (see
.env.example); everything defaults to safe mocks so Vena always starts,
even with no API keys or audio hardware.

Usage:
    python run_vena.py
    VENA_PORT=8765 python run_vena.py
"""
from __future__ import annotations

import os
import sys

MIN_PYTHON = (3, 10)


def _check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        sys.exit(f"Vena needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
                 f"(found {sys.version.split()[0]})")


def _build_voice():
    """Assemble the voice pipeline from env config. Mock-first: Vena
    must start even with no STT server, TTS engine, or microphone."""
    from vena.voice.pipeline import VoicePipeline
    from vena.voice.player import CommandPlayer, MockPlayer
    from vena.voice.stt import MockSTT, WhisperAPI
    from vena.voice.tts import CommandTTS, MockTTS
    from vena.voice.wakeword import SoundDeviceMic

    stt_kind = os.environ.get("VENA_STT", "mock").lower()
    if stt_kind == "whisper_api":
        stt = WhisperAPI(
            base_url=os.environ.get("VENA_WHISPER_URL", "http://127.0.0.1:8000"),
            model=os.environ.get("VENA_WHISPER_MODEL", "whisper-1"),
            api_key=os.environ.get("VENA_WHISPER_API_KEY") or None,
            language=os.environ.get("VENA_WHISPER_LANGUAGE", ""))
    else:
        stt = MockSTT()
    print(f"[vena] STT engine: {stt.name}")

    tts_kind = os.environ.get("VENA_TTS", "mock").lower()
    tts_command = os.environ.get("VENA_TTS_COMMAND", "")
    if tts_kind == "command" and tts_command:
        tts = CommandTTS(tts_command)
    else:
        tts = MockTTS()
    print(f"[vena] TTS engine: {tts.name}")

    player_command = os.environ.get("VENA_PLAYER_COMMAND", "")
    player = CommandPlayer(player_command) if player_command else MockPlayer()
    print(f"[vena] audio player: {player.name}")

    mic = None
    if os.environ.get("VENA_MIC", "0") == "1":
        try:
            mic = SoundDeviceMic()
            mic.start()
            mic.stop()  # probe only; pipeline opens it per turn
            print("[vena] microphone: sounddevice")
        except Exception as e:
            print(f"[vena] microphone unavailable ({e}); voice input disabled")
            mic = None
    else:
        print("[vena] microphone: disabled (set VENA_MIC=1 to enable)")
    return VoicePipeline(stt=stt, tts=tts, player=player, mic=mic)


def _build_registry(service):
    """Create the tool registry and register every tool spec."""
    from vena.tools.registry import ToolRegistry
    from vena.tools import files, commands, apps, browser, system
    from vena.dev import tools as dev_tools
    from vena.vision import digit_skill

    approved_roots = [r for r in
                      os.environ.get("VENA_APPROVED_ROOTS", os.path.expanduser("~")).split(":")
                      if r.strip()]
    allowed_commands = [c.strip() for c in
                        os.environ.get("VENA_ALLOWED_COMMANDS", "ls,dir,echo,python,git").split(",")
                        if c.strip()]

    registry = ToolRegistry(service.conn)
    # Core laptop-control tools (each make_specs reads VENA_* env itself).
    for spec in files.make_specs(approved_roots):
        registry.register(spec)
    for spec in commands.make_specs(allowed_commands):
        registry.register(spec)
    for spec in apps.make_specs():
        registry.register(spec)
    for spec in browser.make_specs():
        registry.register(spec)
    for spec in system.make_specs(approved_roots):
        registry.register(spec)
    # Developer skill needs a context (shares the service DB connection).
    dev_ctx = dev_tools.DevContext(service.conn, approved_roots, allowed_commands)
    for spec in dev_tools.make_specs(dev_ctx):
        registry.register(spec)
    # Vena's signature skill: the MNIST digit recognizer as a tool.
    for spec in digit_skill.make_specs():
        registry.register(spec)
    print(f"[vena] tool registry: {len(registry.specs())} tools")
    return registry


def _build_brain():
    from vena.core.brain import build_router
    router = build_router()
    print(f"[vena] brain: {type(router).__name__}")
    return router


def _build_memory(service):
    from vena.memory.service import MemoryService
    # Reuse the service DB connection (migrations already applied by
    # create_service) — one DB file, no split-brain. MemoryService only
    # needs a `.conn` attribute, so adapt the raw connection.
    class _ConnHolder:
        def __init__(self, conn):
            self.conn = conn
    memories = MemoryService(_ConnHolder(service.conn))
    print("[vena] memory service: ready")
    return memories


def main() -> None:
    _check_python()
    # run from the repo root no matter where the script is invoked from
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.getcwd())

    from vena.service.app import ServiceSettings, create_service, serve

    settings = ServiceSettings()
    settings.validate()
    service = create_service(settings)

    # Wire every subsystem: registry -> workflows, brain -> chat,
    # memory service -> /memories, voice pipeline -> /voice/*.
    try:
        registry = _build_registry(service)
        service.attach_registry(registry)
        service.attach_workflows(registry)
    except Exception as e:
        print(f"[vena] tools/workflows disabled: {e}")

    try:
        service.attach_brain(_build_brain())
    except Exception as e:
        print(f"[vena] chat disabled: {e}")

    try:
        service.attach_memory(_build_memory(service))
    except Exception as e:
        print(f"[vena] memories disabled: {e}")

    if os.environ.get("VENA_VOICE_ENABLED", "1") == "1":
        try:
            service.attach_voice(_build_voice())
        except Exception as e:
            print(f"[vena] voice disabled: {e}")

    print(f"[vena] data dir: {settings.data_dir}")
    print(f"[vena] workflows: {'wired' if service._wf_store else 'disabled'}")
    print(f"[vena] chat: {'wired' if service._router else 'disabled'}")
    print(f"[vena] memories: {'wired' if service._memories else 'disabled'}")

    server = serve(settings, service)
    host, port = server.server_address
    print(f"[vena] listening on http://{host}:{port} (loopback only)")
    print("[vena] endpoints: /health /chat /chat/stream /memories/* "
          "/permissions /voice/* /workflows/* /pairing/* /devices "
          "/backup /backups /restore /tasks")
    print("[vena] press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[vena] stopped")


if __name__ == "__main__":
    main()
