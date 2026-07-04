"""Tests for the app_namespace() helper (the single source of the toolkit's
filesystem/label namespace)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from loop_registry import app_namespace


def test_app_namespace_default(monkeypatch):
    monkeypatch.delenv("KADENCE_NAMESPACE", raising=False)
    assert app_namespace() == "kadence"


def test_app_namespace_override(monkeypatch):
    monkeypatch.setenv("KADENCE_NAMESPACE", "ai-sdlc")
    assert app_namespace() == "ai-sdlc"


def test_app_namespace_blank_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KADENCE_NAMESPACE", "   ")
    assert app_namespace() == "kadence"
