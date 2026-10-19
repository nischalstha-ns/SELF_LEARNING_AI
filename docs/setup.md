# Vena — Setup Guide

Everything you need to get Vena running from a fresh clone.

## 1. Requirements

| What | Needs |
|---|---|
| Core + service + voice (mock) | Python 3.10+, no pip packages |
| Microphone capture | `pip install sounddevice` (optional) |
| Speech out loud | `espeak-ng` or any TTS writing WAV to stdout (optional) |
| Real speech-to-text | Any OpenAI-compatible `/audio/transcriptions` endpoint (optional) |
| Digit skill (MNIST) | `pip install torch torchvision Pillow` (optional) |

Check Python: `python --version` (needs 3.10+).

## 2. Clone and verify

```bash
git clone <your-vena-repo-url>
cd vena-build
python -m unittest discover -s tests
```

Expected: `OK` — every module ships with tests.

## 3. Configure (optional)

```bash
cp .env.example .env   # then edit it
```

Out of the box Vena runs fully on mocks: the service starts, the
voice endpoints synthesize test tones, and transcription returns a
scripted reply. Nothing phones home.

To get real voices:

```bash
# speech-to-text via a local whisper server
VENA_STT=whisper_api
VENA_WHISPER_URL=http://127.0.0.1:8000

# speech output via espeak-ng
VENA_TTS=command
VENA_TTS_COMMAND=espeak-ng --stdout -v en

# playback (Linux example)
VENA_PLAYER_COMMAND=aplay

# microphone (needs `pip install sounddevice`)
VENA_MIC=1
```

On Windows, `run_vena.bat` creates `.env` from `.env.example` on
first run automatically.

## 4. Start everything

```bash
python run_vena.py
# [vena] listening on http://127.0.0.1:8765 (loopback only)
```

Windows: double-click `run_vena.bat`.

The service **only binds loopback** — it refuses to listen on LAN
addresses. The database (`data/vena.db`) is created on first start.

## 5. Try it

```bash
# health + subsystem status
curl -s localhost:8765/health | python -m json.tool

# text to speech -> speech.wav (mock: a short tone)
curl -s -X POST localhost:8765/voice/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello, I am Vena."}' -o speech.wav

# transcribe it back (mock STT returns a scripted reply)
curl -s -X POST localhost:8765/voice/transcribe \
  --data-binary @speech.wav | python -m json.tool

# record a workflow, then dry-run it
curl -s -X POST localhost:8765/workflows \
  -H 'Content-Type: application/json' \
  -d '{"name": "demo", "steps": []}'   # steps need the tool-registry phase
```

## 6. Phone companion (optional)

The service never opens a LAN port. To reach it from your phone, use
a tunnel **you** control (`adb reverse` or Tailscale), then:

```bash
# 1. desktop: create a one-time pairing code
curl -s -X POST localhost:8765/pairing/code
# {"code": "KQ7X2M4P", "expires_at": "..."}   # expires in 10 minutes

# 2. phone: redeem it once -> device token (shown once, store it safely)
curl -s -X POST localhost:8765/pairing/redeem \
  -H 'Content-Type: application/json' \
  -d '{"code": "KQ7X2M4P", "device_name": "my phone"}'

# 3. phone: use the token
curl -s localhost:8765/companion/status \
  -H 'Authorization: Bearer vena_...'
```

Only SHA-256 hashes of codes/tokens are stored server-side.

## 7. Backup & restore

```bash
curl -s -X POST localhost:8765/backup \
  -H 'Content-Type: application/json' -d '{"label": "before-experiment"}'
curl -s localhost:8765/backups | python -m json.tool
curl -s -X POST localhost:8765/restore \
  -H 'Content-Type: application/json' -d '{"name": "vena-20240101-120000-before-experiment.db"}'
```

Backups use SQLite's online backup API — no downtime, no restart.

## Troubleshooting

| Problem | Fix |
|---|---|
| `refusing to bind ...` | `VENA_HOST` must be `127.0.0.1`, `localhost`, or `::1` |
| `voice pipeline not attached` (501) | Set `VENA_VOICE_ENABLED=1` (default) |
| `workflows unavailable` (501) | Tool-registry phase not landed yet |
| `microphone unavailable` | `pip install sounddevice`, set `VENA_MIC=1` |
| `TTS command not found` | Install `espeak-ng` or fix `VENA_TTS_COMMAND` |
| HTTP 413 | Body exceeded `VENA_MAX_JSON_BODY_MB` / `VENA_MAX_AUDIO_BODY_MB` |
| HTTP 401 on `/companion/*` | Pair the device first; send `Authorization: Bearer <token>` |
