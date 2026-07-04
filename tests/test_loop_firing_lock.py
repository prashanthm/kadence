"""Tests for loop_firing_lock — shared per-loop mutual exclusion for the
self-hosted loops (pr-review-loop, pr-comment-fix-loop)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import loop_firing_lock as lfl  # noqa: E402


def test_firing_lock_is_mutually_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(lfl, "_lock_path", lambda name: tmp_path / f"{name}.lock")
    with lfl.firing_lock("pr-review-loop") as a1:
        assert a1 is True
        with lfl.firing_lock("pr-review-loop") as a2:
            assert a2 is False  # already held -> busy
    # released -> re-acquire succeeds
    with lfl.firing_lock("pr-review-loop") as a3:
        assert a3 is True


def test_different_loop_names_do_not_collide(tmp_path, monkeypatch):
    # pr-review-loop and pr-comment-fix-loop firing concurrently must NOT block
    # each other — they operate on different PRs/worktrees entirely.
    monkeypatch.setattr(lfl, "_lock_path", lambda name: tmp_path / f"{name}.lock")
    with lfl.firing_lock("pr-review-loop") as a1:
        assert a1 is True
        with lfl.firing_lock("pr-comment-fix-loop") as a2:
            assert a2 is True  # distinct lock file -> no collision


def test_lock_path_is_per_loop_name(tmp_path):
    p1 = lfl._lock_path("pr-review-loop")
    p2 = lfl._lock_path("pr-comment-fix-loop")
    assert p1 != p2
    assert p1.name == "pr-review-loop.pylock"
    assert p2.name == "pr-comment-fix-loop.pylock"


def test_lock_path_never_collides_with_the_shell_wrapper_lock(tmp_path):
    # pr-review-loop-cron.sh / pr-comment-fix-loop-cron.sh already own a mkdir-based
    # DIRECTORY lock at the bare "<loop-name>.lock" path — this module's file lock must
    # use a different suffix, or open(lock_file, "w") raises IsADirectoryError against
    # the shell wrapper's live lock every single firing (the exact regression this
    # guards against).
    for name in ("pr-review-loop", "pr-comment-fix-loop"):
        assert lfl._lock_path(name).suffix != ".lock"
