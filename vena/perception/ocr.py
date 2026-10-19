"""OCR backends.

Adapted from nexus/perception/ocr.py.

- MockOCR: scripted text blocks (tests, demos).
- TesseractOCR: shells out to `tesseract` (must be installed separately)
  with TSV output for bounding boxes. Raises a clear error when the
  binary is missing instead of crashing.
"""
from __future__ import annotations

import csv
import logging
import os
import subprocess
import tempfile

from ._base import OCReader, TextBlock

log = logging.getLogger("vena.perception.ocr")


class VenaError(Exception):
    pass


class MockOCR(OCReader):
    name = "mock"

    def __init__(self, script: list[TextBlock] | None = None):
        self.script = script or [TextBlock(text="mock text", x=10, y=10,
                                           width=100, height=20, confidence=1.0)]
        self.seen: list[bytes] = []

    def read_text(self, png_bytes: bytes, timeout_s: float = 30.0) -> list[TextBlock]:
        self.seen.append(png_bytes)
        return list(self.script)


class TesseractOCR(OCReader):
    name = "tesseract"

    def __init__(self, language: str = "eng"):
        self.language = language

    @staticmethod
    def available() -> bool:
        """True when the tesseract binary exists on PATH."""
        import shutil
        return shutil.which("tesseract") is not None

    def read_text(self, png_bytes: bytes, timeout_s: float = 30.0) -> list[TextBlock]:
        if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            raise VenaError("OCR input must be PNG bytes")
        with tempfile.TemporaryDirectory() as tmp:
            img = os.path.join(tmp, "img.png")
            with open(img, "wb") as f:
                f.write(png_bytes)
            out = os.path.join(tmp, "out")
            cmd = ["tesseract", img, out, "-l", self.language, "tsv"]
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
            except FileNotFoundError as e:
                raise VenaError(
                    "tesseract is not installed (apt install tesseract-ocr)") from e
            except subprocess.TimeoutExpired as e:
                raise VenaError("OCR timed out") from e
            if proc.returncode != 0:
                raise VenaError(
                    f"OCR failed: {proc.stderr.decode(errors='replace')[:200]}")
            blocks = []
            with open(out + ".tsv", encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    if row.get("level") == "5" and row.get("text", "").strip():
                        try:
                            blocks.append(TextBlock(
                                text=row["text"].strip(),
                                x=int(row["left"]), y=int(row["top"]),
                                width=int(row["width"]), height=int(row["height"]),
                                confidence=float(row.get("conf") or 0) / 100.0))
                        except (ValueError, KeyError):
                            continue
        log.info("OCR found %d words", len(blocks))
        return blocks


def default_reader(language: str = "eng") -> OCReader:
    """Tesseract when installed, else the mock (never crashes)."""
    return TesseractOCR(language) if TesseractOCR.available() else MockOCR()


__all__ = ["MockOCR", "TesseractOCR", "VenaError", "default_reader"]
