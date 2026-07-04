#!/usr/bin/env python3
"""Orchestration for PR comment fix loop cron firings."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from discover_pr_fix_candidates import discover, default_gh_run
from loop_firing_lock import firing_lock
from pr_fix_config import expand_path, load_config, report_apply_labels, report_push, report_submit
from pr_fix_publish import draft_report_path, meta_path
from pr_fix_rereview import parse_rereview_meta, requires_rereview
from pr_fix_status import enrich_report_from_artifacts, status_paths, write_firing_report

LOOP_NAME = "pr-comment-fix-loop"


def bootstrap_labels(cfg: dict[str, Any]) -> None:
    labels = cfg.get("labels") or {}
    specs = [
        (labels.get("complete", "pr-fix-cycle-complete"), "PR comment fix loop complete", "0E8A16"),
        (labels.get("in_progress", "pr-fix-cycle-in-progress"), "PR comment fix loop in progress", "FBCA04"),
        (labels.get("deferred", "pr-fix-deferred"), "PR comment fix loop deferred", "C5DEF5"),
        (labels.get("needs_human", "pr-fix-needs-human"), "PR comment fix loop needs human (max rounds reached)", "B60205"),
    ]
    repos = cfg.get("repos") or []
    for entry in repos:
        owner = entry.get("owner", "")
        repo = entry.get("repo", "")
        if not owner or not repo:
            continue
        full = f"{owner}/{repo}"
        for name, desc, color in specs:
            proc = subprocess.run(
                [
                    "gh",
                    "label",
                    "create",
                    name,
                    "--repo",
                    full,
                    "--description",
                    desc,
                    "--color",
                    color,
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 and "already exists" not in (proc.stderr or "").lower():
                pass


def apply_needs_human(cfg: dict[str, Any], full_repo: str, pr: int) -> None:
    """Mark a PR that exhausted max_rounds for human attention (best-effort).
    Idempotent — re-adding the label is a no-op for gh."""
    labels = cfg.get("labels") or {}
    needs = labels.get("needs_human", "pr-fix-needs-human")
    in_progress = labels.get("in_progress", "pr-fix-cycle-in-progress")
    subprocess.run(
        ["gh", "pr", "edit", str(pr), "--repo", full_repo,
         "--add-label", needs, "--remove-label", in_progress],
        capture_output=True, text=True,
    )


def ensure_dirs(cfg: dict[str, Any]) -> None:
    paths = status_paths(cfg)
    for key, p in paths.items():
        if key == "firing_dir":
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
    draft = Path(expand_path(str((cfg.get("report") or {}).get("draft_path"))))
    draft.mkdir(parents=True, exist_ok=True)


def run_post_agent_submit(
    script_dir: Path, config_path: str, pr: int, full_repo: str, cfg: dict[str, Any]
) -> tuple[int, str]:
    """Prepare publish artifacts (draft mode) or push + post comment (submit mode)."""
    repo_slug = full_repo.split("/", 1)[-1]
    draft_dir = str((cfg.get("report") or {}).get("draft_path"))
    if not draft_report_path(draft_dir, repo_slug, pr).exists():
        return 0, "no draft report"

    mode = "publish" if report_submit(cfg) else "prepare"
    proc = subprocess.run(
        [
            sys.executable,
            str(script_dir / "pr_fix_submit.py"),
            "--config",
            config_path,
            "--repo",
            full_repo,
            "--pr",
            str(pr),
            "--mode",
            mode,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def prepare_submit_if_needed(script_dir: Path, config_path: str, pr: int, repo: str) -> None:
    """Backward-compatible alias."""
    cfg = load_config(config_path)
    run_post_agent_submit(script_dir, config_path, pr, repo, cfg)


def run_agent(
    script_dir: Path,
    config_path: str,
    force_pr: int | None = None,
    backend: str | None = None,
    clone_path: str | None = None,
) -> tuple[int, str]:
    env = {**os.environ, "PR_FIX_CONFIG": config_path}
    if force_pr is not None:
        env["PR_FIX_FORCE_PR"] = str(force_pr)
    if backend:
        env["AGENT_BACKEND_OVERRIDE"] = backend
    if clone_path:
        env["PR_FIX_CLONE_PATH"] = clone_path
    proc = subprocess.run(
        [str(script_dir / "pr-comment-fix-loop.sh")],
        env=env,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_agent_with_fallback(
    script_dir: Path,
    config_path: str,
    force_pr: int | None = None,
    clone_path: str | None = None,
) -> tuple[int, str, str]:
    """Run the agent, falling through the backend chain on failure.

    Returns (exit_code, combined_output, backend_used). Stops at the first
    backend that exits 0; otherwise returns the last attempt's result.
    """
    from loop_agent_config import BACKEND_FALLBACK_CHAIN

    last: tuple[int, str, str] = (1, "no backend attempted", BACKEND_FALLBACK_CHAIN[0])
    attempts: list[str] = []
    for backend in BACKEND_FALLBACK_CHAIN:
        code, out = run_agent(
            script_dir, config_path, force_pr=force_pr, backend=backend, clone_path=clone_path
        )
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
    skip_agent: bool = False,
    force_pr: int | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    cfg["_config_path"] = config_path
    ensure_dirs(cfg)
    bootstrap_labels(cfg)

    discovery = discover(cfg, force_pr=force_pr)
    candidate = discovery.get("candidate")

    if candidate is None:
        report: dict[str, Any] = {"outcome": "no_work"}
        return write_firing_report(cfg, report)

    # Round ceiling: discovery can't apply labels, so it returns a sentinel; the
    # cron applies needs_human once and does NOT run the agent.
    if candidate.get("_skip") == "max_rounds_reached":
        full_repo = f"{candidate['owner']}/{candidate['repo']}"
        pr = int(candidate["number"])
        apply_needs_human(cfg, full_repo, pr)
        report = {"outcome": "max_rounds_reached", "repo": full_repo, "pr": pr}
        return write_firing_report(cfg, report)

    owner = candidate["owner"]
    repo = candidate["repo"]
    pr = int(candidate["number"])
    full_repo = f"{owner}/{repo}"

    if skip_agent:
        report = {"outcome": "skipped", "repo": full_repo, "pr": pr}
        report = enrich_report_from_artifacts(cfg, report, candidate)
        return write_firing_report(cfg, report, worktree=report.get("worktree"))

    exit_code, agent_out, backend_used = run_agent_with_fallback(
        script_dir, config_path, force_pr=force_pr, clone_path=candidate.get("clone_path")
    )
    if exit_code != 0:
        report = {
            "outcome": "error",
            "repo": full_repo,
            "pr": pr,
            "agent_exit_code": exit_code,
            "agent_backend": backend_used,
            "error": agent_out[-4000:] if agent_out else "agent failed",
        }
        return write_firing_report(cfg, report)

    pub_code, pub_out = run_post_agent_submit(script_dir, config_path, pr, full_repo, cfg)

    if report_submit(cfg):
        outcome = "published" if pub_code == 0 else "publish_failed"
    else:
        outcome = "draft_prepared" if pub_code == 0 else "draft_prepare_failed"

    report = {
        "outcome": outcome,
        "repo": full_repo,
        "pr": pr,
        "agent_exit_code": exit_code,
        "agent_backend": cfg.get("agent_backend", "cursor"),
        "agent_model": cfg.get("agent_model", ""),
        "agent_summary": agent_out[-4000:] if agent_out else "",
        "publish_exit_code": pub_code,
    }
    if pub_code != 0:
        report["publish_error"] = pub_out[-4000:] if pub_out else "publish failed"
    elif pub_out.strip():
        report["publish_summary"] = pub_out[-2000:]
    report = enrich_report_from_artifacts(cfg, report, candidate)
    if report.get("draft_path"):
        required, reason = requires_rereview(
            candidate.get("comment_inventory") or [],
            Path(report["draft_path"]).read_text(encoding="utf-8"),
            meta=parse_rereview_meta(Path(report["draft_path"]).read_text(encoding="utf-8")),
        )
        report["rereview_required"] = required
        report["rereview_reason"] = reason

    return write_firing_report(cfg, report, worktree=report.get("worktree"))


def main() -> None:
    parser = argparse.ArgumentParser(description="PR comment fix loop cron")
    parser.add_argument("--config", required=True)
    parser.add_argument("--force-pr", type=int, default=None)
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    script_dir = Path(__file__).resolve().parent

    with firing_lock(LOOP_NAME) as acquired:
        if not acquired:
            # Another firing of this loop is already running — never run two
            # concurrently (they'd collide on the same PR's worktree/branch).
            report = {"outcome": "busy", "detail": "another firing holds the loop lock"}
            with contextlib.suppress(Exception):
                write_firing_report(load_config(args.config), report)
        else:
            report = fire(
                script_dir,
                args.config,
                skip_agent=args.skip_agent,
                force_pr=args.force_pr,
            )
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(report.get("outcome", "unknown"))


if __name__ == "__main__":
    main()
