"""Structured firing status reports for engineering work loop cron."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engineering_work_loop_config import expand_path


def status_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    st = cfg.get("status") or {}
    return {
        "latest_json": Path(
            expand_path(
                st.get(
                    "latest_json",
                    "~/.local/share/ai-sdlc/engineering-work-loop-latest.json",
                )
            )
        ),
        "latest_md": Path(
            expand_path(
                st.get(
                    "latest_md",
                    "~/.local/share/ai-sdlc/engineering-work-loop-latest.md",
                )
            )
        ),
        "firing_log": Path(
            expand_path(
                st.get(
                    "firing_log",
                    "~/.local/share/ai-sdlc/engineering-work-loop-firings.log",
                )
            )
        ),
    }


def _candidate_ref(cand: dict[str, Any]) -> str:
    return f"{cand.get('owner', '')}/{cand.get('repo', '')}#{cand.get('number', '')} ({cand.get('kind', '')})"


def format_firing_markdown(report: dict[str, Any]) -> str:
    # Multi-item aggregate firing (new shape with an `items` list).
    if isinstance(report.get("items"), list):
        return _format_multi_item_markdown(report)

    # Legacy single-item / preflight / no_work / dry_run shape.
    lines = [
        "# Engineering Work Loop — Firing Status",
        "",
        f"- **Fired at:** {report.get('fired_at', '')}",
        f"- **Outcome:** `{report.get('outcome', '')}`",
    ]
    cand = report.get("candidate") or {}
    if cand.get("owner") and cand.get("repo") and cand.get("number"):
        lines.append(
            f"- **Candidate:** {cand['owner']}/{cand['repo']}#{cand['number']} ({cand.get('kind', '')})"
        )
    if cand.get("synthesized_loop_ac"):
        lines.append("- **Loop AC:** synthesized and written back to issue")
    if report.get("agent_exit_code") is not None:
        lines.append(f"- **Agent exit code:** {report['agent_exit_code']}")
    if report.get("detail"):
        lines.append(f"- **Detail:** {report['detail']}")
    if report.get("agent_output"):
        lines.extend(["", "## Agent output", "", "```", report["agent_output"].strip(), "```"])
    return "\n".join(lines) + "\n"


def _format_multi_item_markdown(report: dict[str, Any]) -> str:
    items = report.get("items") or []
    processed = report.get("processed_count", len(items))
    skipped = report.get("skipped_count", 0)
    pool = report.get("pool_size", processed + skipped)
    lines = [
        "# Engineering Work Loop — Firing Status",
        "",
        f"- **Fired at:** {report.get('fired_at', '')}",
        f"- **Outcome:** `{report.get('outcome', '')}`",
        f"- **Processed:** {processed}, skipped {skipped} of {pool} discovered",
    ]
    if report.get("detail"):
        lines.append(f"- **Detail:** {report['detail']}")
    for item in items:
        cand = item.get("candidate") or {}
        lines.extend(
            [
                "",
                f"## {_candidate_ref(cand)}",
                f"- **Outcome:** `{item.get('outcome', '')}`",
            ]
        )
        if item.get("agent_exit_code") is not None:
            lines.append(f"- **Exit code:** {item['agent_exit_code']}")
        if item.get("executor"):
            lines.append(f"- **Executor:** {item['executor']}")
        if cand.get("synthesized_loop_ac"):
            lines.append("- **Loop AC:** synthesized and written back to issue")
        if item.get("agent_output"):
            lines.extend(["", "```", item["agent_output"].strip(), "```"])
    return "\n".join(lines) + "\n"


def firing_log_record(report: dict[str, Any]) -> dict[str, Any]:
    """Compact JSONL record for the append-only firing history.

    Carries the structured outcome plus a lean per-item array (no multi-KB
    agent_output prose — that lives in latest.json / latest.md). Shape matches
    the pr-comment-fix-loop firing log so a single jq/dashboard query spans both.
    """
    rec: dict[str, Any] = {
        "fired_at": report.get("fired_at", ""),
        "outcome": report.get("outcome", ""),
    }
    if report.get("detail"):
        rec["detail"] = report["detail"]
    if report.get("items") is not None:
        rec["processed_count"] = report.get("processed_count", 0)
        rec["skipped_count"] = report.get("skipped_count", 0)
        rec["pool_size"] = report.get("pool_size", 0)
        rec["items"] = [
            {
                "repo": f"{(it.get('candidate') or {}).get('owner', '')}/"
                f"{(it.get('candidate') or {}).get('repo', '')}",
                "number": (it.get("candidate") or {}).get("number"),
                "kind": (it.get("candidate") or {}).get("kind"),
                "outcome": it.get("outcome"),
                "exit": it.get("agent_exit_code"),
            }
            for it in report["items"]
        ]
    else:
        # legacy single-report shape (preflight / no_work / dry_run)
        cand = report.get("candidate") or {}
        if cand:
            rec["repo"] = f"{cand.get('owner', '')}/{cand.get('repo', '')}"
            rec["number"] = cand.get("number")
        if report.get("agent_exit_code") is not None:
            rec["agent_exit_code"] = report["agent_exit_code"]
    return rec


def write_firing_report(cfg: dict[str, Any], report: dict[str, Any]) -> None:
    paths = status_paths(cfg)
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    paths["latest_json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["latest_md"].write_text(format_firing_markdown(report), encoding="utf-8")
    with paths["firing_log"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(firing_log_record(report), separators=(",", ":")) + "\n")


def build_report(
    *,
    outcome: str,
    agent_exit_code: int | None = None,
    detail: str = "",
    agent_output: str = "",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "agent_exit_code": agent_exit_code,
        "detail": detail,
        "agent_output": agent_output[-8000:],
    }
    if candidate:
        report["candidate"] = _candidate_summary(candidate)
    return report


def _candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": candidate.get("kind"),
        "owner": candidate.get("owner"),
        "repo": candidate.get("repo"),
        "number": candidate.get("number"),
        "title": candidate.get("title"),
        "classification": candidate.get("classification"),
        "clone_path": candidate.get("clone_path"),
        "synthesized_loop_ac": candidate.get("synthesized_loop_ac", False),
    }


def build_item_report(
    candidate: dict[str, Any],
    agent_exit_code: int,
    agent_output: str,
    outcome: str,
    *,
    executor: str | None = None,
) -> dict[str, Any]:
    """Per-item record within a multi-item firing."""
    report: dict[str, Any] = {
        "candidate": _candidate_summary(candidate),
        "outcome": outcome,
        "agent_exit_code": agent_exit_code,
        "agent_output": (agent_output or "")[-8000:],
    }
    if executor:
        report["executor"] = executor
    return report


def build_firing_report(
    *,
    items: list[dict[str, Any]],
    skipped_count: int = 0,
    pool_size: int | None = None,
    detail: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Aggregate firing report over N processed items."""
    if not items:
        outcome = "no_work"
    elif dry_run:
        outcome = "dry_run"
    elif any(it.get("outcome") == "agent_error" for it in items):
        outcome = "agent_error"
    elif any(it.get("outcome") == "auto_error" for it in items):
        outcome = "agent_error"
    else:
        outcome = "agent_complete"
    processed = len(items)
    if pool_size is None:
        pool_size = processed + skipped_count
    return {
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "detail": detail,
        "processed_count": processed,
        "skipped_count": skipped_count,
        "pool_size": pool_size,
        "items": items,
    }


def append_state_log_entry(
    cfg: dict[str, Any],
    *,
    owner: str,
    repo: str,
    number: int,
    outcome: str,
) -> None:
    """Append a per-issue cooldown record to state_log so the next firing's
    cooldown_active() sees it. The key matches discovery's
    f'{owner}/{repo}#{number}'; read_state_log keeps the last entry per key.

    Without this, the cooldown gate is inert and every assigned issue is
    re-pickable on every firing.
    """
    path = expand_path(
        str(cfg.get("state_log", "~/.local/share/ai-sdlc/engineering-work-loop.log"))
    )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "key": f"{owner}/{repo}#{number}",
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
    }
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
