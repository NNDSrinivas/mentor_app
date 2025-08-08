import os
from pathlib import Path

import pytesseract
import pytest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.screen_record import ScreenAnalyzer


@pytest.fixture(autouse=True)
def reset_tesseract_cmd():
    """Reset pytesseract command after each test."""
    original = pytesseract.pytesseract.tesseract_cmd
    yield
    pytesseract.pytesseract.tesseract_cmd = original


def test_override_path(tmp_path, monkeypatch):
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.delenv("TESSERACT_PATH", raising=False)
    fake_bin = tmp_path / "tess"
    fake_bin.write_text("")

    analyzer = ScreenAnalyzer(tesseract_path=str(fake_bin))

    assert analyzer.tesseract_cmd == str(fake_bin)
    assert pytesseract.pytesseract.tesseract_cmd == str(fake_bin)


def test_env_path(tmp_path, monkeypatch):
    fake_bin = tmp_path / "tessenv"
    fake_bin.write_text("")
    monkeypatch.setenv("TESSERACT_CMD", str(fake_bin))

    analyzer = ScreenAnalyzer()

    assert analyzer.tesseract_cmd == str(fake_bin)
    assert pytesseract.pytesseract.tesseract_cmd == str(fake_bin)


def test_missing_path(monkeypatch, caplog):
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.delenv("TESSERACT_PATH", raising=False)
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    caplog.set_level("ERROR")

    analyzer = ScreenAnalyzer()

    assert analyzer.tesseract_cmd is None
    assert "Tesseract binary not found" in caplog.text
