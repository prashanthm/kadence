"""Tests for pr_fix_cron's firing-lock wiring — a manual force-fire must not run
concurrently with the scheduled cron (they'd collide on the same PR's worktree)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pr_fix_cron as cron  # noqa: E402
import loop_firing_lock as lfl  # noqa: E402


def _write_config(tmp_path: Path) -> str:
    p = tmp_path / "pr-comment-fix-loop.yaml"
    p.write_text("github_user: x\nrepos: []\n", encoding="utf-8")
    return str(p)


def test_busy_when_lock_already_held(tmp_path, monkeypatch):
    monkeypatch.setattr(lfl, "_lock_path", lambda name: tmp_path / f"{name}.lock")
    config_path = _write_config(tmp_path)

    called = {"fire": False}

    def _boom(*a, **k):
        called["fire"] = True
        raise AssertionError("fire() must not run while another firing holds the lock")

    monkeypatch.setattr(cron, "fire", _boom)
    monkeypatch.setattr(sys, "argv", ["x", "--config", config_path, "--json"])

    with lfl.firing_lock(cron.LOOP_NAME):
        rc = cron.main()

    assert rc is None or rc == 0


def test_fire_runs_when_lock_is_free(tmp_path, monkeypatch):
    monkeypatch.setattr(lfl, "_lock_path", lambda name: tmp_path / f"{name}.lock")
    config_path = _write_config(tmp_path)

    called = {"fire": False}

    def _fake_fire(*a, **k):
        called["fire"] = True
        return {"outcome": "no_work"}

    monkeypatch.setattr(cron, "fire", _fake_fire)
    monkeypatch.setattr(sys, "argv", ["x", "--config", config_path, "--json"])

    cron.main()

    assert called["fire"] is True
