"""Structured firing status reports for PR comment fix loop cron."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_registry import app_namespace
from pr_fix_config import expand_path
from pr_fix_publish import default_worktree_path, meta_path


def status_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    st = cfg.get("status") or {}
    return {
        "latest_json": Path(expand_path(st.get(
            "latest_json",
            f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-latest.json",
        ))),
        "latest_md": Path(expand_path(st.get(
            "latest_md",
            f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-latest.md",
        ))),
        "firing_log": Path(expand_path(st.get(
            "firing_log",
            f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-firings.log",
        ))),
        "firing_dir": Path(expand_path(st.get(
            "firing_dir",
            f"~/.local/share/{app_namespace()}/firings",
        ))),
    }


def branch_draft_dir(cfg: dict[str, Any]) -> str:
    return str((cfg.get("report") or {}).get("branch_draft_dir", ".sdlc/pr-fix-reports"))


def firing_json_name(pr_number: int, fired_at: str) -> str:
    safe_ts = fired_at.replace(":", "").replace("+", "")
    return f"{pr_number}-firing-{safe_ts}.json"


def firing_latest_name(pr_number: int) -> str:
    return f"{pr_number}-firing-latest.md"


def format_firing_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PR Comment Fix Loop — Firing Status",
        "",
        f"- **Fired at:** {report.get('fired_at', '')}",
        f"- **Outcome:** `{report.get('outcome', '')}`",
    ]
    if report.get("repo") and report.get("pr"):
        lines.append(f"- **PR:** {report['repo']}#{report['pr']}")
    if report.get("title"):
        lines.append(f"- **Title:** {report['title']}")
    if report.get("head_sha"):
        lines.append(f"- **Head SHA:** `{report['head_sha']}`")
    if report.get("fix_commits"):
        lines.append(f"- **Fix commits:** {', '.join(f'`{c}`' for c in report['fix_commits'])}")
    if "rereview_required" in report:
        rr = "yes" if report["rereview_required"] else "no"
        lines.append(f"- **Re-review required:** {rr}")
        if report.get("rereview_reason"):
            lines.append(f"- **Re-review reason:** {report['rereview_reason']}")
    if report.get("worktree"):
        lines.append(f"- **Worktree:** `{report['worktree']}`")
    if report.get("draft_path"):
        lines.append(f"- **Draft report:** `{report['draft_path']}`")
    if report.get("publish_script"):
        lines.append(f"- **Publish script:** `{report['publish_script']}`")
    if report.get("git_firing_json"):
        lines.append(f"- **Git evidence:** `{report['git_firing_json']}`")
    if report.get("agent_exit_code") is not None:
        lines.append(f"- **Agent exit code:** {report['agent_exit_code']}")
    if report.get("error"):
        lines.append(f"- **Error:** {report['error']}")
    lines.append("")
    if report.get("outcome") == "draft_prepared":
        pr = report.get("pr", "<pr>")
        lines.extend([
            "## Operator next steps",
            "",
            "```bash",
            f"scripts/pr-comment-fix-loop-submit.sh {pr}",
            f"PR_FIX_PUBLISH=1 scripts/pr-comment-fix-loop-publish.sh {pr}",
            "```",
            "",
        ])
    return "\n".join(lines)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _git_head(worktree: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _git_log_since_remote(worktree: Path, branch: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(worktree), "log", f"origin/{branch}..HEAD", "--oneline", "--format=%h"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        proc = subprocess.run(
            ["git", "-C", str(worktree), "log", "-5", "--oneline", "--format=%h"],
            capture_output=True,
            text=True,
            check=False,
        )
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def commit_firing_to_worktree(
    cfg: dict[str, Any],
    worktree: Path,
    pr_number: int,
    report: dict[str, Any],
    fired_at: str,
) -> dict[str, str]:
    """Write firing files on PR branch worktree and commit."""
    draft_rel = branch_draft_dir(cfg)
    out_dir = worktree / draft_rel
    out_dir.mkdir(parents=True, exist_ok=True)

    json_name = firing_json_name(pr_number, fired_at)
    md_name = firing_latest_name(pr_number)
    json_path = out_dir / json_name
    md_path = out_dir / md_name

    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(format_firing_markdown(report), encoding="utf-8")

    rel_json = f"{draft_rel}/{json_name}"
    rel_md = f"{draft_rel}/{md_name}"

    subprocess.run(
        ["git", "-C", str(worktree), "add", rel_json, rel_md],
        check=True,
    )
    diff = subprocess.run(
        ["git", "-C", str(worktree), "diff", "--cached", "--quiet"],
        check=False,
    )
    if diff.returncode == 1:
        subprocess.run(
            [
                "git",
                "-C",
                str(worktree),
                "commit",
                "-m",
                f"chore(sdlc): pr-fix firing {pr_number} {report.get('outcome', '')}",
            ],
            check=True,
        )

    return {"git_firing_json": rel_json, "git_firing_md": rel_md}


# Verbose prose kept out of the append-only firing history (it lives in
# latest.json / latest.md / the per-firing history file and the posted PR comment).
_FIRING_LOG_OMIT = ("agent_summary", "publish_summary")


def firing_log_record(report: dict[str, Any]) -> dict[str, Any]:
    """Compact JSONL record for the firing history — structured fields only,
    without the multi-KB agent_summary/publish_summary prose blobs."""
    return {k: v for k, v in report.items() if k not in _FIRING_LOG_OMIT}


def write_firing_report(
    cfg: dict[str, Any],
    report: dict[str, Any],
    *,
    worktree: str | Path | None = None,
) -> dict[str, Any]:
    """Dual-write local status + optional git commit on PR worktree."""
    if "fired_at" not in report:
        report["fired_at"] = datetime.now(timezone.utc).isoformat()

    paths = status_paths(cfg)
    for key, path in paths.items():
        if key == "firing_dir":
            path.mkdir(parents=True, exist_ok=True)
        else:
            _ensure_parent(path)

    fired_at = report["fired_at"]
    history_path = paths["firing_dir"] / f"pr-fix-{fired_at.replace(':', '').replace('+', '')}.json"
    history_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    paths["latest_json"].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    paths["latest_md"].write_text(format_firing_markdown(report), encoding="utf-8")

    with paths["firing_log"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(firing_log_record(report), separators=(",", ":")) + "\n")

    outcome = report.get("outcome", "")
    pr_number = report.get("pr")
    if outcome == "draft_prepared" and pr_number is not None:
        wt_path = Path(worktree) if worktree else None
        if wt_path is None:
            repo = str(report.get("repo", ""))
            repo_slug = repo.split("/", 1)[-1] if repo else ""
            git = cfg.get("git") or {}
            wt_path = Path(
                default_worktree_path(
                    str(git.get("worktree_root", f"~/.local/share/{app_namespace()}/worktrees")),
                    repo_slug,
                    int(pr_number),
                )
            )
        if wt_path.is_dir():
            git_paths = commit_firing_to_worktree(cfg, wt_path, int(pr_number), report, fired_at)
            report.update(git_paths)
            paths["latest_json"].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            paths["latest_md"].write_text(format_firing_markdown(report), encoding="utf-8")

    return report


def resolve_worktree_from_meta(cfg: dict[str, Any], repo_slug: str, pr_number: int) -> str | None:
    draft_dir = str((cfg.get("report") or {}).get("draft_path", f"~/.local/share/{app_namespace()}/pr-fix-reports"))
    mp = meta_path(draft_dir, repo_slug, pr_number)
    if mp.exists():
        meta = json.loads(mp.read_text(encoding="utf-8"))
        return meta.get("worktree")
    return None


def enrich_report_from_artifacts(
    cfg: dict[str, Any],
    report: dict[str, Any],
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fill report fields from discovery candidate and local artifacts."""
    if candidate:
        report.setdefault("repo", f"{candidate.get('owner')}/{candidate.get('repo')}")
        report.setdefault("pr", candidate.get("number"))
        report.setdefault("title", candidate.get("title"))
        report.setdefault("head_sha", candidate.get("head_sha"))

    pr = report.get("pr")
    repo = str(report.get("repo", ""))
    if not pr or not repo:
        return report

    repo_slug = repo.split("/", 1)[-1]
    draft_dir = Path(expand_path(str((cfg.get("report") or {}).get("draft_path"))))
    draft_path = draft_dir / f"{repo_slug}-{pr}-draft.md"
    meta_file = meta_path(str(draft_dir), repo_slug, int(pr))
    publish_script = draft_dir / f"{repo_slug}-{pr}-publish.sh"

    if draft_path.exists():
        report["draft_path"] = str(draft_path)
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        report.setdefault("worktree", meta.get("worktree"))
        report.setdefault("rereview_required", meta.get("rereview_required"))
        report.setdefault("rereview_reason", meta.get("rereview_reason"))
        report.setdefault("publish_script", meta.get("publish_script"))
    elif publish_script.exists():
        report["publish_script"] = str(publish_script)

    wt = report.get("worktree")
    if wt and candidate and candidate.get("head_branch"):
        commits = _git_log_since_remote(Path(wt), candidate["head_branch"])
        if commits:
            report["fix_commits"] = commits
        elif not report.get("head_sha"):
            report["head_sha"] = _git_head(Path(wt))

    return report
