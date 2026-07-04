"""Prepare human-gated publish artifacts for PR comment fix loop."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loop_registry import app_namespace
from pr_fix_attribution import ensure_attribution_in_report
from pr_fix_config import report_apply_labels, report_push, report_submit


def draft_report_path(draft_dir: str, repo_slug: str, pr_number: int) -> Path:
    return Path(draft_dir).expanduser() / f"{repo_slug}-{pr_number}-draft.md"


def publish_script_path(draft_dir: str, repo_slug: str, pr_number: int) -> Path:
    return Path(draft_dir).expanduser() / f"{repo_slug}-{pr_number}-publish.sh"


def ready_comment_path(draft_dir: str, repo_slug: str, pr_number: int) -> Path:
    return Path(draft_dir).expanduser() / f"{repo_slug}-{pr_number}-ready.md"


def meta_path(draft_dir: str, repo_slug: str, pr_number: int) -> Path:
    return Path(draft_dir).expanduser() / f"{repo_slug}-{pr_number}-meta.json"


def strip_draft_header(text: str) -> str:
    lines = text.splitlines()
    while lines and (
        not lines[0].strip()
        or lines[0].strip().startswith("> **DRAFT**")
        or lines[0].strip() == "---"
    ):
        lines.pop(0)
    return "\n".join(lines).lstrip() + "\n"


def default_worktree_path(worktree_root: str, repo_slug: str, pr_number: int) -> str:
    return str(
        Path(worktree_root).expanduser() / repo_slug / f"prfix-{pr_number}"
    )


def build_publish_script(
    *,
    repo: str,
    pr_number: int,
    ready_comment: Path,
    complete_label: str,
    in_progress_label: str,
    worktree_path: str,
    include_push: bool,
    include_labels: bool,
    include_comment: bool,
    rereview_required: bool,
    reviewers: list[str],
) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "# Human gate — review this script before running.",
        "# Pushes the PR branch worktree (fixes, draft report, firing evidence).",
        "set -euo pipefail",
        "",
        f'REPO="{repo}"',
        f"PR_NUM={pr_number}",
        f'WT="{worktree_path}"',
        "",
    ]
    if include_push:
        lines.extend(
            [
                'if [[ ! -d "$WT" ]]; then',
                '  echo "error: worktree not found: $WT" >&2',
                "  exit 1",
                "fi",
                'cd "$WT"',
                "git push origin HEAD",
                "",
            ]
        )
    if include_comment:
        lines.append(f'gh pr comment "$PR_NUM" --repo "$REPO" --body-file "{ready_comment}"')
    if include_labels:
        lines.append(
            f'gh pr edit "$PR_NUM" --repo "$REPO" '
            f'--add-label "{complete_label}" --remove-label "{in_progress_label}"'
        )
    if rereview_required and reviewers:
        args = " ".join(f'--add-reviewer "{r}"' for r in reviewers)
        lines.append(f'gh pr edit "$PR_NUM" --repo "$REPO" {args}')
    lines.extend(["", 'echo "published $REPO#$PR_NUM"', ""])
    return "\n".join(lines)


def prepare_publish_artifacts(
    *,
    cfg: dict[str, Any],
    repo: str,
    pr_number: int,
    draft_text: str,
    rereview_required: bool,
    rereview_reason: str,
    reviewers: list[str],
    worktree_path: str | None = None,
) -> dict[str, Any]:
    report = cfg.get("report") or {}
    draft_dir = str(report.get("draft_path", f"~/.local/share/{app_namespace()}/pr-fix-reports"))
    repo_slug = repo.split("/", 1)[-1]
    labels = cfg.get("labels") or {}
    git = cfg.get("git") or {}
    wt = worktree_path or default_worktree_path(
        str(git.get("worktree_root", f"~/.local/share/{app_namespace()}/worktrees")),
        repo_slug,
        pr_number,
    )

    draft_path = draft_report_path(draft_dir, repo_slug, pr_number)
    ready_path = ready_comment_path(draft_dir, repo_slug, pr_number)
    script_path = publish_script_path(draft_dir, repo_slug, pr_number)
    meta_file = meta_path(draft_dir, repo_slug, pr_number)

    body = ensure_attribution_in_report(strip_draft_header(draft_text), cfg)
    ready_path.write_text(body, encoding="utf-8")
    script = build_publish_script(
        repo=repo,
        pr_number=pr_number,
        ready_comment=ready_path,
        complete_label=str(labels.get("complete", "pr-fix-cycle-complete")),
        in_progress_label=str(labels.get("in_progress", "pr-fix-cycle-in-progress")),
        worktree_path=wt,
        include_push=not report_push(cfg),
        include_labels=not report_apply_labels(cfg),
        include_comment=not report_submit(cfg),
        rereview_required=rereview_required,
        reviewers=reviewers,
    )
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)

    meta: dict[str, Any] = {
        "repo": repo,
        "pr": pr_number,
        "worktree": wt,
        "draft": str(draft_path),
        "ready_comment": str(ready_path),
        "publish_script": str(script_path),
        "rereview_required": rereview_required,
        "rereview_reason": rereview_reason,
        "reviewers": reviewers,
        "push_pending": not report_push(cfg),
        "comment_pending": not report_submit(cfg),
        "labels_pending": not report_apply_labels(cfg),
        "agent_backend": cfg.get("agent_backend", "claude"),
        "agent_model": cfg.get("agent_model", ""),
    }
    meta_file.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_meta(draft_dir: str, repo_slug: str, pr_number: int) -> dict[str, Any]:
    path = meta_path(draft_dir, repo_slug, pr_number)
    if not path.exists():
        raise FileNotFoundError(f"missing publish meta: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def already_published(meta: dict[str, Any]) -> bool:
    """True when the agent already posted the fix report (submit-mode inline publish)."""
    return bool(meta.get("report_url"))
