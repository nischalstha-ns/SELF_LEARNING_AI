"""Tests for vena/voice/: base, wavutil, stt, tts, player, wakeword, pipeline."""
from __future__ import annotations

import io
import threading
import unittest
import wave

from tests._stubs import install_stubs, uninstall_stubs

_state = install_stubs()
try:
    from vena.core.errors import ProviderError, VenaError
    from vena.voice import pipeline as pipeline_mod
    from vena.voice import player as player_mod
    from vena.voice import stt as stt_mod
    from vena.voice import tts as tts_mod
    from vena.voice import wakeword as wake_mod
    from vena.voice.base import Transcription
    from vena.voice.wavutil import (
        energy_vad, make_wav, pcm_frames, rms_energy, silence_wav,
        tone_wav, wav_info)
finally:
    pass


def tearDownModule():
    uninstall_stubs(_state)


class WavUtilTest(unittest.TestCase):
    def test_tone_roundtrip(self):
        wav = tone_wav(0.2)
        self.assertTrue(wav.startswith(b"RIFF"))
        info = wav_info(wav)
        self.assertEqual(info["channels"], 1)
        self.assertEqual(info["sample_rate"], 16000)
        self.assertGreater(info["frames"], 0)

    def test_silence_has_no_energy(self):
        pcm = pcm_frames(silence_wav(0.2))
        self.assertEqual(rms_energy(pcm), 0.0)
        self.assertFalse(energy_vad(pcm))

    def test_tone_has_energy(self):
        pcm = pcm_frames(tone_wav(0.2))
        self.assertGreater(rms_energy(pcm), 0.1)
        self.assertTrue(energy_vad(pcm))


class MockSTTTest(unittest.TestCase):
    def test_scripted_transcripts(self):
        stt = stt_mod.MockSTT(script=["first", "second"])
        t1 = stt.transcribe(tone_wav(0.1))
        t2 = stt.transcribe(tone_wav(0.1))
        self.assertEqual(t1.text, "first")
        self.assertEqual(t2.text, "second")  # repeats last when exhausted
        self.assertEqual(len(stt.received), 2)

    def test_whisper_rejects_non_wav(self):
        stt = stt_mod.WhisperAPI("http://127.0.0.1:9")
        with self.assertRaises(ProviderError):
            stt.transcribe(b"not-a-wav")


class MockTTSTest(unittest.TestCase):
    def test_synthesize_valid_wav(self):
        tts = tts_mod.MockTTS()
        wav = tts.synthesize("hello vena")
        self.assertTrue(wav.startswith(b"RIFF"))
        self.assertIn("hello vena", tts.requests)

    def test_empty_text_rejected(self):
        with self.assertRaises(ProviderError):
            tts_mod.MockTTS().synthesize("   ")

    def test_command_tts_missing_binary(self):
        tts = tts_mod.CommandTTS("definitely-not-a-real-tts-binary-xyz")
        with self.assertRaises(ProviderError):
            tts.synthesize("hi")


class PlayerTest(unittest.TestCase):
    def test_mock_player_plays_fully(self):
        player = player_mod.MockPlayer()
        self.assertTrue(player.play(tone_wav(0.3)))
        self.assertEqual(len(player.played), 1)
        self.assertFalse(player.interrupted)

    def test_mock_player_interrupted(self):
        player = player_mod.MockPlayer()
        stop = threading.Event()
        stop.set()  # already interrupted before playback
        self.assertFalse(player.play(tone_wav(1.0), stop_event=stop))
        self.assertTrue(player.interrupted)

    def test_command_player_missing_binary(self):
        player = player_mod.CommandPlayer("definitely-not-a-real-player-xyz")
        with self.assertRaises(ProviderError):
            player.play(tone_wav(0.1))


class PushToTalkTest(unittest.TestCase):
    def test_capture_roundtrip(self):
        mic = wake_mod.MockMic(tone_wav(0.5))
        ptt = wake_mod.PushToTalk(mic, trim_silence=False)
        ptt.begin()
        wav = ptt.end()
        self.assertTrue(wav.startswith(b"RIFF"))
        # ~0.5s of audio captured (100ms chunks)
        info = wav_info(wav)
        self.assertGreater(info["frames"], 0.3 * info["sample_rate"])

    def test_double_begin_rejected(self):
        mic = wake_mod.MockMic(tone_wav(0.2))
        ptt = wake_mod.PushToTalk(mic)
        ptt.begin()
        with self.assertRaises(VenaError):
            ptt.begin()
        ptt.end()

    def test_end_without_begin_rejected(self):
        ptt = wake_mod.PushToTalk(wake_mod.MockMic(tone_wav(0.2)))
        with self.assertRaises(VenaError):
            ptt.end()

    def test_trim_silence(self):
        import math
        import struct
        sr = 16000
        silence = [0] * int(0.5 * sr)
        tone = [int(0.5 * 32767 * math.sin(2 * math.pi * 440 * i / sr))
                for i in range(int(0.3 * sr))]
        wav = make_wav(silence + tone + silence)
        mic = wake_mod.MockMic(wav)
        ptt = wake_mod.PushToTalk(mic, trim_silence=True)
        ptt.begin()
        out = ptt.end()
        info = wav_info(out)
        duration = info["frames"] / info["sample_rate"]
        # 1.3s input -> leading/trailing silence trimmed, ~0.3s tone kept
        self.assertLess(duration, 0.8)
        self.assertGreater(duration, 0.1)

    def test_wakeword_requires_opt_in(self):
        mic = wake_mod.MockMic(tone_wav(0.2))
        with self.assertRaises(VenaError):
            wake_mod.WakeWordListener(mic, on_wake=lambda b: None, opt_in=False)

    def test_wakeword_fires_and_captures(self):
        mic = wake_mod.MockMic(tone_wav(0.5))
        heard: list[bytes] = []
        calls = {"n": 0}

        def detector(pcm: bytes) -> bool:
            calls["n"] += 1
            return calls["n"] == 1  # fire once

        listener = wake_mod.WakeWordListener(
            mic, on_wake=heard.append, detector=detector, opt_in=True)
        listener.start()
        listener._thread.join(timeout=10)
        listener.stop()
        self.assertEqual(listener.wake_count, 1)
        self.assertEqual(len(heard), 1)
        self.assertTrue(heard[0].startswith(b"RIFF"))


class PipelineTest(unittest.TestCase):
    def _pipeline(self, script=("open notes",)):
        mic = wake_mod.MockMic(tone_wav(0.4))
        return pipeline_mod.VoicePipeline(
            stt=stt_mod.MockSTT(list(script)),
            tts=tts_mod.MockTTS(),
            player=player_mod.MockPlayer(),
            mic=mic)

    def test_full_voice_turn(self):
        pipe = self._pipeline()
        turn = pipe.voice_turn(lambda text: f"you said: {text}")
        self.assertEqual(turn.transcript, "open notes")
        self.assertEqual(turn.reply_text, "you said: open notes")
        self.assertTrue(turn.reply_audio.startswith(b"RIFF"))
        self.assertTrue(turn.played_fully)
        self.assertFalse(turn.interrupted)

    def test_interrupted_turn(self):
        pipe = self._pipeline()
        stop = threading.Event()
        stop.set()
        turn = pipe.voice_turn(lambda text: "reply", stop_event=stop)
        self.assertTrue(turn.interrupted)
        self.assertFalse(turn.played_fully)

    def test_speak_empty_is_noop(self):
        pipe = self._pipeline()
        self.assertTrue(pipe.speak("   "))

    def test_listen_without_mic(self):
        pipe = pipeline_mod.VoicePipeline(
            stt=stt_mod.MockSTT(), tts=tts_mod.MockTTS(),
            player=player_mod.MockPlayer(), mic=None)
        with self.assertRaises(ValueError):
            pipe.listen()


if __name__ == "__main__":
    unittest.main()
