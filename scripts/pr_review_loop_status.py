"""Firing status reports for the PR review loop cron (lean JSONL history)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pr_review_loop_config import expand_path


def status_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    st = cfg.get("status") or {}
    return {
        "latest_json": Path(expand_path(st.get(
            "latest_json", "~/.local/share/ai-sdlc/pr-review-loop-latest.json"))),
        "latest_md": Path(expand_path(st.get(
            "latest_md", "~/.local/share/ai-sdlc/pr-review-loop-latest.md"))),
        "firing_log": Path(expand_path(st.get(
            "firing_log", "~/.local/share/ai-sdlc/pr-review-loop-firings.log"))),
    }


def state_log_path(cfg: dict[str, Any]) -> Path:
    return Path(expand_path(cfg.get("state_log", "~/.local/share/ai-sdlc/pr-review-loop.log")))


def append_state_log(cfg: dict[str, Any], record: dict[str, Any]) -> None:
    """Append one idempotency record to state_log.

    `discover_pr_review_candidates.read_state_log` reads this file and keys
    `review_posted` rows by `owner/repo#pr@head_sha` to skip already-reviewed
    HEADs. Nothing else writes it, so without this call the per-HEAD guard is
    inert. One row per reviewed PR.
    """
    p = state_log_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(firing_log_record(record), separators=(",", ":")) + "\n")


def build_report(
    *,
    outcome: str,
    candidate: dict[str, Any] | None = None,
    agent_exit_code: int | None = None,
    agent_backend: str = "",
    detail: str = "",
    agent_output: str = "",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "detail": detail,
        "agent_exit_code": agent_exit_code,
        "agent_backend": agent_backend,
        "agent_output": (agent_output or "")[-8000:],
    }
    if candidate:
        report["owner"] = candidate.get("owner")
        report["repo"] = candidate.get("repo")
        report["pr"] = candidate.get("number")
        report["head_sha"] = candidate.get("head_sha")
        report["title"] = candidate.get("title")
        report["is_toolkit_pr"] = candidate.get("is_toolkit_pr", False)
    return report


def firing_log_record(report: dict[str, Any]) -> dict[str, Any]:
    """Compact JSONL record — structured fields only, no multi-KB agent_output."""
    keep = (
        "fired_at", "outcome", "owner", "repo", "pr", "head_sha", "title",
        "agent_exit_code", "agent_backend", "is_toolkit_pr", "detail",
    )
    return {k: report[k] for k in keep if k in report}


def format_firing_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PR Review Loop — Firing Status",
        "",
        f"- **Fired at:** {report.get('fired_at', '')}",
        f"- **Outcome:** `{report.get('outcome', '')}`",
    ]
    if report.get("owner") and report.get("repo") and report.get("pr"):
        head = (report.get("head_sha") or "")[:7]
        lines.append(f"- **PR:** {report['owner']}/{report['repo']}#{report['pr']} @{head}")
    if report.get("title"):
        lines.append(f"- **Title:** {report['title']}")
    if report.get("agent_backend"):
        lines.append(f"- **Backend:** {report['agent_backend']}")
    if report.get("agent_exit_code") is not None:
        lines.append(f"- **Agent exit code:** {report['agent_exit_code']}")
    if report.get("detail"):
        lines.append(f"- **Detail:** {report['detail']}")
    if report.get("agent_output"):
        lines.extend(["", "## Agent output", "", "```", report["agent_output"].strip(), "```"])
    return "\n".join(lines) + "\n"


def write_firing_report(cfg: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    paths = status_paths(cfg)
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    paths["latest_json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["latest_md"].write_text(format_firing_markdown(report), encoding="utf-8")
    with paths["firing_log"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(firing_log_record(report), separators=(",", ":")) + "\n")
    return report


def build_batch_report(
    *,
    results: list[dict[str, Any]],
    detail: str = "",
) -> dict[str, Any]:
    """Aggregate per-PR review reports into one firing report.

    Each item in `results` is a per-PR report from `build_report`. The firing's
    `outcome` summarizes: `no_work` (empty), `review_posted` (all ok), or
    `partial` (some agent_error). `reviewed`/`errors` count the split.
    """
    reviewed = sum(1 for r in results if r.get("outcome") == "review_posted")
    errors = sum(
        1
        for r in results
        if r.get("outcome") in ("agent_error", "review_not_verified")
    )
    if not results:
        outcome = "no_work"
    elif errors == 0:
        outcome = "review_posted"
    elif reviewed == 0:
        outcome = "agent_error"
    else:
        outcome = "partial"
    return {
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "detail": detail or f"{reviewed} reviewed, {errors} error",
        "reviewed": reviewed,
        "errors": errors,
        "results": results,
    }


def format_batch_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PR Review Loop — Firing Status",
        "",
        f"- **Fired at:** {report.get('fired_at', '')}",
        f"- **Outcome:** `{report.get('outcome', '')}`",
        f"- **Reviewed:** {report.get('reviewed', 0)}  **Errors:** {report.get('errors', 0)}",
        "",
        "## PRs this firing",
        "",
    ]
    for r in report.get("results") or []:
        head = (r.get("head_sha") or "")[:7]
        ref = f"{r.get('owner')}/{r.get('repo')}#{r.get('pr')} @{head}"
        lines.append(
            f"- `{r.get('outcome', '')}` — {ref} "
            f"(exit {r.get('agent_exit_code')}, {r.get('agent_backend') or '—'}) "
            f"{r.get('title') or ''}".rstrip()
        )
    if not report.get("results"):
        lines.append("- (none eligible)")
    return "\n".join(lines) + "\n"


def write_batch_report(cfg: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Write the combined latest.* + one firings.log row per PR, and append a
    state_log record for each posted review so per-HEAD idempotency works."""
    paths = status_paths(cfg)
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    paths["latest_json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["latest_md"].write_text(format_batch_markdown(report), encoding="utf-8")
    results = report.get("results") or []
    with paths["firing_log"].open("a", encoding="utf-8") as fh:
        if results:
            for r in results:
                fh.write(json.dumps(firing_log_record(r), separators=(",", ":")) + "\n")
        else:
            fh.write(json.dumps(firing_log_record(report), separators=(",", ":")) + "\n")
    for r in results:
        if r.get("outcome") == "review_posted":
            append_state_log(cfg, r)
    return report
