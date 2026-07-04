#!/usr/bin/env python3
"""Shared per-loop firing lock (fcntl.flock-based), so a manual force-fire and the
scheduled cron for the SAME loop never run concurrently against the same PR/worktree.

engineering_work_loop_cron.py (spec-loop, implement-loop) has its own copy of this
keyed off loop_stem() (the engineering-work-loop family registry). pr-review-loop and
pr-comment-fix-loop are self-hosted (no shared engine, no registry) — this module
gives them the same protection keyed off a fixed loop name instead.

NOTE: `pr-review-loop-cron.sh` / `pr-comment-fix-loop-cron.sh` already carry their own
mkdir-based single-instance lock at `~/.local/share/ai-sdlc/<loop-name>.lock` (a
DIRECTORY containing a `pid` file, with PID-liveness + mtime-based staleness reaping —
predates this module). This lock is a SEPARATE, complementary guard for direct Python
invocation (bypassing the .sh wrapper, e.g. tests or a future non-shell entry point) —
it deliberately uses a distinct suffixed path so it never collides with the shell
wrapper's directory lock at the bare `<loop-name>.lock` path.
"""
from __future__ import annotations

import contextlib
import os
from pathlib import Path


def _lock_path(loop_name: str) -> Path:
    d = Path.home() / ".local/share/ai-sdlc"
    return d / f"{loop_name}.pylock"


@contextlib.contextmanager
def firing_lock(loop_name: str):
    """Acquire `loop_name`'s firing lock (non-blocking). Yields True if acquired,
    False if another firing already holds it — the caller should exit as 'busy'
    rather than run concurrently. Best-effort no-op on platforms without fcntl."""
    lock_file = _lock_path(loop_name)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:  # Windows: no flock — fall back to permissive (documented gap)
        yield True
        return
    fh = open(lock_file, "w")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            fh.write(str(os.getpid()))
            fh.flush()
        except OSError:
            pass
        yield True
    finally:
        with contextlib.suppress(Exception):
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()
