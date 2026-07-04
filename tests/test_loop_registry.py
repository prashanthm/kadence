"""Tests for loop_registry.py — the engineering-work-loop family descriptors."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import loop_registry as reg  # noqa: E402


def test_four_family_loops_present():
    assert set(reg.LOOPS) == {
        "spec-loop",
        "implement-loop",
        "pr-review-loop",
        "pr-comment-fix-loop",
    }


def test_default_and_family_resolve_to_implement_loop(monkeypatch):
    monkeypatch.delenv("ENGINEERING_LOOP_NAME", raising=False)
    assert reg.resolve_loop_name(None) == "implement-loop"
    assert reg.resolve_loop_name("") == "implement-loop"
    # the family umbrella name is not a concrete loop → default member
    assert reg.resolve_loop_name("engineering-work-loop") == "implement-loop"


def test_env_selects_loop(monkeypatch):
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "spec-loop")
    assert reg.resolve_loop_name(None) == "spec-loop"
    # explicit arg overrides the env
    assert reg.resolve_loop_name("implement-loop") == "implement-loop"


def test_descriptor_fields():
    spec = reg.get_loop("spec-loop")
    assert spec.prompt == "spec-loop.prompt.md"
    assert spec.skill == "spec-author"
    assert spec.status_gate == "Ready for Spec"
    impl = reg.get_loop("implement-loop")
    assert impl.prompt == "implement-loop.prompt.md"
    assert impl.skill == "implement"
    assert impl.status_gate == "Ready for Dev"


def test_engine_driven_vs_self_hosted():
    assert reg.is_engine_driven("implement-loop")
    assert reg.is_engine_driven("spec-loop")
    assert not reg.is_engine_driven("pr-review-loop")
    assert not reg.is_engine_driven("pr-comment-fix-loop")
    # self-hosted loops carry no engine prompt
    assert reg.get_loop("pr-review-loop").prompt is None
    assert reg.get_loop("pr-comment-fix-loop").prompt is None


def test_unknown_loop_raises():
    with pytest.raises(SystemExit):
        reg.get_loop("nope-loop")


def test_engine_prompts_exist_on_disk():
    prompts = Path(__file__).resolve().parents[1] / ".github" / "prompts"
    for name in reg.ENGINE_DRIVEN:
        p = reg.get_loop(name).prompt
        assert p is not None
        assert (prompts / p).is_file(), f"missing prompt for {name}: {p}"
