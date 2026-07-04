#!/usr/bin/env python3
"""Orchestration for engineering work loop cron firings."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from discover_engineering_work_candidates import discover
from engineering_work_loop_config import load_config, resolve_config_path, toolkit_root
from engineering_work_loop_setup import is_windows, resolve_bash
from engineering_work_loop_status import (
    append_state_log_entry,
    build_firing_report,
    build_item_report,
    build_report,
    write_firing_report,
)


import contextlib


def _lock_path() -> Path:
    """Per-loop, per-instance lock file so only ONE firing of a given family loop
    runs at a time. Manual force-fires and the scheduled cron then can't collide on
    the same worktree/branch (the #122 collision). Derives from loop_stem()."""
    from engineering_work_loop_config import loop_stem

    d = Path.home() / ".local/share/ai-sdlc"
    return d / f"{loop_stem()}.lock"


@contextlib.contextmanager
def firing_lock():
    """Acquire the loop's firing lock (non-blocking). Yields True if acquired, False
    if another firing already holds it — the caller should then exit as 'busy' rather
    than run concurrently. Best-effort no-op on platforms without fcntl."""
    lock_file = _lock_path()
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


def ensure_dirs(cfg: dict[str, Any]) -> None:
    from engineering_work_loop_status import status_paths

    paths = status_paths(cfg)
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    worktree_root = (cfg.get("git") or {}).get("worktree_root")
    if worktree_root:
        Path(str(worktree_root).replace("~", str(Path.home()))).mkdir(
            parents=True, exist_ok=True
        )


def run_agent_command(script_dir: Path) -> list[str]:
    script = str(script_dir / "engineering-work-loop.sh")
    if is_windows():
        return [resolve_bash(), script]
    return [script]


def run_agent(
    script_dir: Path,
    config_path: str,
    *,
    force_issue: int | None = None,
    clone_path: str | None = None,
    base_ref: str | None = None,
    backend: str | None = None,
) -> tuple[int, str]:
    env = {**os.environ, "ENGINEERING_LOOP_CONFIG": config_path}
    if force_issue is not None:
        env["ENGINEERING_LOOP_FORCE_ISSUE"] = str(force_issue)
    if clone_path:
        env["ENGINEERING_LOOP_CLONE_PATH"] = clone_path
    if base_ref:
        env["ENGINEERING_LOOP_BASE_REF"] = base_ref
    if backend:
        env["AGENT_BACKEND_OVERRIDE"] = backend
    proc = subprocess.run(
        run_agent_command(script_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_agent_with_fallback(
    script_dir: Path,
    config_path: str,
    *,
    force_issue: int | None = None,
    clone_path: str | None = None,
    base_ref: str | None = None,
) -> tuple[int, str, str]:
    """Run the agent, falling through the backend chain on failure.

    Returns (exit_code, combined_output, backend_used). Stops at the first
    backend that exits 0; otherwise returns the last attempt's result.
    """
    from loop_agent_config import BACKEND_FALLBACK_CHAIN
    from engineering_work_loop_config import load_config

    # Honor the OPERATOR's configured backend FIRST, then fall through to the rest of
    # the chain on failure. Without this the loop always tried cursor first (chain[0])
    # and AGENT_BACKEND_OVERRIDE clobbered the config — so `agent_backend: claude` ran
    # cursor. Configured backend leads; the remaining chain is the fallback order.
    try:
        configured = str(load_config(config_path).get("agent_backend", "")).lower().strip()
    except Exception:
        configured = ""
    chain: tuple[str, ...] = BACKEND_FALLBACK_CHAIN
    if configured in BACKEND_FALLBACK_CHAIN:
        chain = (configured,) + tuple(b for b in BACKEND_FALLBACK_CHAIN if b != configured)

    last: tuple[int, str, str] = (1, "no backend attempted", chain[0])
    attempts: list[str] = []
    for backend in chain:
        code, out = run_agent(
            script_dir,
            config_path,
            force_issue=force_issue,
            clone_path=clone_path,
            base_ref=base_ref,
            backend=backend,
        )
        last = (code, out, backend)
        if code == 0:
            return last
        attempts.append(f"{backend}(exit {code})")
    # all backends failed — annotate the output with what was tried
    code, out, backend = last
    return code, f"all backends failed: {', '.join(attempts)}\n{out}", backend


def warn_if_loop_check_missing_on_base(cfg: dict[str, Any]) -> str | None:
    """Fail-soft check: auto-tier Loop AC invokes loop_check.py from the TOOLKIT
    install (not the target repo). v2 is independent of any vendored/symlinked
    toolkit in the target repo — verify commands run it by absolute path via
    $ENGINEERING_LOOP_TOOLKIT. Warn only if the toolkit install itself lacks it.

    Returns a warning string when loop_check.py is absent from the toolkit, else None.
    """
    from engineering_work_loop_config import toolkit_root

    loop_check = toolkit_root() / "scripts" / "loop_check.py"
    if loop_check.is_file():
        return None
    msg = (
        f"loop_check.py not found in the toolkit install ({loop_check}). Auto-tier "
        f"Loop AC verify commands will fail. Set ENGINEERING_LOOP_TOOLKIT to the "
        f"toolkit repo root."
    )
    print(f"::warning::{msg}", file=sys.stderr)
    return msg


def fire(
    script_dir: Path,
    config_path: str,
    *,
    force_issue: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    ensure_dirs(cfg)
    warn_if_loop_check_missing_on_base(cfg)

    discovery = discover(cfg, force_issue=force_issue, dry_run=dry_run)
    candidates = discovery.get("candidates") or []
    skipped_count = discovery.get("skipped_count", 0)
    pool_size = discovery.get("pool_size", len(candidates) + skipped_count)

    if not candidates:
        report = build_report(
            outcome="no_work",
            detail="no actionable work after discovery",
            agent_output="no actionable work",
        )
        write_firing_report(cfg, report)
        return report

    if dry_run:
        items = [
            build_item_report(cand, 0, "", "dry_run") for cand in candidates
        ]
        report = build_firing_report(
            items=items,
            skipped_count=skipped_count,
            pool_size=pool_size,
            detail=f"{len(candidates)} candidate(s) selected",
            dry_run=True,
        )
        write_firing_report(cfg, report)
        return report

    item_reports: list[dict[str, Any]] = []
    for cand in candidates:
        owner = cand.get("owner", "")
        repo = cand.get("repo", "")
        number = int(cand["number"])
        issue_force = number if cand.get("kind") == "issue" else None
        try:
            # (v2) No deterministic compliance executor — every candidate goes to the
            # agent. Real code work only; there are no metadata-only auto-closeouts.
            code, out, backend_used = run_agent_with_fallback(
                script_dir,
                config_path,
                force_issue=issue_force,
                clone_path=cand.get("clone_path"),
                base_ref=cand.get("base_ref"),
            )
            outcome = "agent_complete" if code == 0 else "agent_error"
            out = f"[backend: {backend_used}]\n{out}"
        except Exception as exc:  # error isolation: one item must not abort the rest
            code, out, outcome = 1, f"exception running agent: {exc}", "agent_error"
        item_reports.append(build_item_report(cand, code, out, outcome))
        if cand.get("kind") == "issue":
            # Record per-issue cooldown so the next firing skips it (the gate is
            # otherwise inert — nothing else writes the state_log).
            append_state_log_entry(
                cfg, owner=owner, repo=repo, number=number, outcome=outcome
            )

    report = build_firing_report(
        items=item_reports,
        skipped_count=skipped_count,
        pool_size=pool_size,
        detail=f"processed {len(item_reports)} of {pool_size} discovered",
    )
    write_firing_report(cfg, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Engineering work loop cron")
    parser.add_argument("--config", default="")
    parser.add_argument("--force-issue", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config_path = args.config or str(resolve_config_path())

    proc = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        cfg = load_config(config_path)
        report = build_report(
            outcome="preflight_error",
            detail="gh not authenticated",
            agent_output=(proc.stdout or "") + (proc.stderr or ""),
        )
        write_firing_report(cfg, report)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        return 1

    script_dir = Path(__file__).resolve().parent
    os.environ.setdefault("ENGINEERING_LOOP_TOOLKIT", str(toolkit_root()))

    with firing_lock() as acquired:
        if not acquired:
            # Another firing of this loop is already running — never run two
            # concurrently (they collide on the shared worktree/branch). Exit clean.
            report = {"outcome": "busy", "detail": "another firing holds the loop lock"}
            with contextlib.suppress(Exception):
                write_firing_report(load_config(config_path), report)
            if args.json:
                print(json.dumps(report, indent=2, default=str))
            return 0
        report = fire(
            script_dir,
            config_path,
            force_issue=args.force_issue,
            dry_run=args.dry_run,
        )
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    outcome = report.get("outcome", "")
    if outcome in ("no_work", "dry_run", "busy"):
        return 0
    return 0 if outcome == "agent_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
