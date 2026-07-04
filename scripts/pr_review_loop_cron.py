#!/usr/bin/env python3
"""Cron orchestration for the PR review loop.

Unlike the other two loops, a review firing posts a review (the agent calls
gh pr review) and does NOT edit code — so there is no worktree and no
publish/push step. fire(): discover -> run agent (backend fallback) -> report.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from discover_pr_review_candidates import discover, operator_review_at_head
from loop_firing_lock import firing_lock
from pr_review_loop_config import load_config, resolve_config_path, toolkit_root
from pr_review_loop_labels import apply_complete, apply_in_progress, bootstrap_labels
from pr_review_loop_setup import is_windows, resolve_bash
from pr_review_loop_status import (
    build_batch_report,
    build_report,
    status_paths,
    write_batch_report,
    write_firing_report,
)

LOOP_NAME = "pr-review-loop"


def ensure_dirs(cfg: dict[str, Any]) -> None:
    for p in status_paths(cfg).values():
        p.parent.mkdir(parents=True, exist_ok=True)


def run_agent_command(script_dir: Path) -> list[str]:
    script = str(script_dir / "pr-review-loop.sh")
    if is_windows():
        return [resolve_bash(), script]
    return [script]


def run_agent(
    script_dir: Path,
    config_path: str,
    *,
    force_pr: int | None = None,
    backend: str | None = None,
) -> tuple[int, str]:
    env = {**os.environ, "PR_REVIEW_LOOP_CONFIG": config_path}
    if force_pr is not None:
        env["PR_REVIEW_LOOP_FORCE_PR"] = str(force_pr)
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
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_agent_with_fallback(
    script_dir: Path,
    config_path: str,
    *,
    force_pr: int | None = None,
) -> tuple[int, str, str]:
    """Run the agent, falling through cursor->copilot->claude on failure.
    Returns (exit_code, combined_output, backend_used)."""
    from loop_agent_config import BACKEND_FALLBACK_CHAIN

    last: tuple[int, str, str] = (1, "no backend attempted", BACKEND_FALLBACK_CHAIN[0])
    attempts: list[str] = []
    for backend in BACKEND_FALLBACK_CHAIN:
        code, out = run_agent(script_dir, config_path, force_pr=force_pr, backend=backend)
        last = (code, out, backend)
        if code == 0:
            return last
        attempts.append(f"{backend}(exit {code})")
    code, out, backend = last
    return code, f"all backends failed: {', '.join(attempts)}\n{out}", backend


def fire(
    script_dir: Path,
    config_path: str,
    *,
    force_pr: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    ensure_dirs(cfg)
    bootstrap_labels(cfg)

    candidates = discover(cfg, force_pr=force_pr).get("candidates") or []
    if not candidates:
        report = build_report(outcome="no_work", detail="no review-requested PR eligible")
        return write_firing_report(cfg, report)

    if dry_run:
        refs = ", ".join(
            f"{c['owner']}/{c['repo']}#{c['number']}" for c in candidates
        )
        report = build_report(
            outcome="dry_run",
            detail=f"would review {len(candidates)}: {refs}",
        )
        return write_firing_report(cfg, report)

    # Review every eligible PR; isolate per-PR failures so one bad PR does not
    # abort the rest of the firing.
    results: list[dict[str, Any]] = []
    operator = str(cfg.get("github_user") or "")
    for candidate in candidates:
        full_repo = f"{candidate['owner']}/{candidate['repo']}"
        pr_num = int(candidate["number"])
        try:
            apply_in_progress(cfg, full_repo, pr_num)
            code, out, backend_used = run_agent_with_fallback(
                script_dir, config_path, force_pr=pr_num
            )
            if code == 0 and operator_review_at_head(
                candidate["owner"],
                candidate["repo"],
                pr_num,
                operator,
                candidate.get("head_sha") or "",
            ):
                apply_complete(cfg, full_repo, pr_num)
                outcome = "review_posted"
            elif code == 0:
                outcome = "review_not_verified"
                verify_note = (
                    "agent exited 0 but no operator review at HEAD on GitHub"
                )
                out = f"{verify_note}\n{out}".strip()
            else:
                outcome = "agent_error"
        except Exception as exc:  # error isolation — continue to the next PR
            code, out, backend_used, outcome = 1, f"exception: {exc}", "", "agent_error"
        results.append(
            build_report(
                outcome=outcome,
                candidate=candidate,
                agent_exit_code=code,
                agent_backend=backend_used,
                agent_output=out,
                detail="" if outcome == "review_posted" else (
                    "agent exited 0 but no operator review at HEAD on GitHub"
                    if outcome == "review_not_verified"
                    else ""
                ),
            )
        )

    return write_batch_report(cfg, build_batch_report(results=results))


def main() -> int:
    parser = argparse.ArgumentParser(description="PR review loop cron")
    parser.add_argument("--config", default="")
    parser.add_argument("--force-pr", type=int, default=None)
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
            outcome="preflight_error", detail="gh not authenticated",
            agent_output=(proc.stdout or "") + (proc.stderr or ""))
        write_firing_report(cfg, report)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        return 1

    script_dir = Path(__file__).resolve().parent
    os.environ.setdefault("PR_REVIEW_LOOP_TOOLKIT", str(toolkit_root()))

    with firing_lock(LOOP_NAME) as acquired:
        if not acquired:
            # Another firing of this loop is already running — never run two
            # concurrently (they'd post duplicate/conflicting reviews). Exit clean.
            report = {"outcome": "busy", "detail": "another firing holds the loop lock"}
            with contextlib.suppress(Exception):
                write_firing_report(load_config(config_path), report)
            if args.json:
                print(json.dumps(report, indent=2, default=str))
            return 0
        report = fire(script_dir, config_path, force_pr=args.force_pr, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    outcome = report.get("outcome", "")
    if outcome in ("no_work", "dry_run", "review_posted", "partial", "busy"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
