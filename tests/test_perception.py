"""Tests for vena.perception — screen, png, ocr, window."""
import os
import tempfile
import unittest

from vena.perception import png
from vena.perception._base import Screenshot, TextBlock, WindowInfo
from vena.perception.ocr import MockOCR, TesseractOCR, default_reader
from vena.perception.screen import (CommandScreenCap, MockScreen,
                                    default_observer, save_screenshot)
from vena.perception.window import MockWindowDetector, default_detector


class PngTest(unittest.TestCase):
    def test_encode_decode_size(self):
        raw = bytes([10, 20, 30] * (16 * 8))
        blob = png.encode_png(16, 8, raw)
        self.assertEqual(png.decode_png_size(blob), (16, 8))

    def test_bad_png(self):
        with self.assertRaises(ValueError):
            png.decode_png_size(b"not a png")

    def test_card_deterministic(self):
        self.assertEqual(png.test_card(32, 16), png.test_card(32, 16))
        w, h = png.decode_png_size(png.test_card(32, 16))
        self.assertEqual((w, h), (32, 16))


class ScreenTest(unittest.TestCase):
    def test_mock_capture(self):
        shot = MockScreen(64, 48).capture()
        self.assertIsInstance(shot, Screenshot)
        self.assertEqual((shot.width, shot.height), (64, 48))
        self.assertTrue(shot.png_bytes.startswith(b"\x89PNG"))

    def test_mock_active_window(self):
        w = MockScreen().active_window()
        self.assertIsInstance(w, WindowInfo)
        self.assertEqual(w.source, "mock")

    def test_command_missing_binary(self):
        cap = CommandScreenCap("no-such-capture-bin-xyz -")
        with self.assertRaises(Exception):
            cap.capture(timeout_s=2)

    def test_save_screenshot(self):
        shot = MockScreen(16, 16).capture()
        with tempfile.TemporaryDirectory() as d:
            p = save_screenshot(shot, os.path.join(d, "s.png"))
            self.assertTrue(os.path.isfile(p))
            with open(p, "rb") as f:
                self.assertTrue(f.read(8).startswith(b"\x89PNG"))

    def test_default_observer(self):
        self.assertIsInstance(default_observer(), MockScreen)
        self.assertIsInstance(default_observer("grim -"), CommandScreenCap)


class OcrTest(unittest.TestCase):
    def test_mock(self):
        blocks = MockOCR().read_text(b"\x89PNG\r\n\x1a\nfake")
        self.assertTrue(blocks)
        self.assertIsInstance(blocks[0], TextBlock)

    def test_mock_records_seen(self):
        m = MockOCR()
        m.read_text(b"bytes1")
        self.assertEqual(m.seen, [b"bytes1"])

    def test_tesseract_rejects_non_png(self):
        with self.assertRaises(Exception):
            TesseractOCR().read_text(b"nope")

    def test_default_reader_never_crashes(self):
        r = default_reader()
        self.assertTrue(hasattr(r, "read_text"))


class WindowTest(unittest.TestCase):
    def test_mock(self):
        w = MockWindowDetector("My App", "myapp").active_window()
        self.assertEqual(w.title, "My App")
        self.assertEqual(w.app_name, "myapp")

    def test_default_detector_never_crashes(self):
        d = default_detector()
        w = d.active_window()  # may raise on exotic setups; mock otherwise
        self.assertIsInstance(w, WindowInfo)


if __name__ == "__main__":
    unittest.main()
