#!/usr/bin/env python3
"""Prepare or execute PR comment fix loop submit/publish."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pr_fix_config import load_config, report_apply_labels, report_push, report_submit
from pr_fix_publish import draft_report_path, load_meta, meta_path, already_published, prepare_publish_artifacts
from pr_fix_rereview import parse_rereview_meta, requires_rereview


def _inventory_for_pr(cfg: dict, repo: str, pr_number: int, script_dir: Path) -> list[dict]:
    owner, repo_name = repo.split("/", 1)
    out = subprocess.run(
        [
            sys.executable,
            str(script_dir / "discover_pr_fix_candidates.py"),
            "--config",
            str(cfg.get("_config_path", "")),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    inventory: list[dict] = []
    if out.returncode == 0:
        candidate = json.loads(out.stdout).get("candidate") or {}
        if candidate.get("number") == pr_number:
            return candidate.get("comment_inventory") or []

    proc = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo_name}/pulls/{pr_number}/reviews", "--paginate"],
        capture_output=True,
        text=True,
        check=True,
    )
    reviews = json.loads(proc.stdout or "[]")
    if isinstance(reviews, dict):
        reviews = [reviews]
    github_user = cfg.get("github_user", "")
    for rev in reviews:
        login = (rev.get("user") or {}).get("login", "")
        if not login or login == github_user:
            continue
        inventory.append(
            {
                "id": rev.get("id"),
                "source": "review",
                "author": login,
                "body": (rev.get("body") or "")[:8000],
                "created_at": rev.get("submitted_at"),
                "state": rev.get("state"),
            }
        )
    return inventory


def resolve_rereview(
    cfg: dict, repo: str, pr_number: int, draft_text: str, script_dir: Path
) -> tuple[bool, str, list[str]]:
    meta = parse_rereview_meta(draft_text)
    inventory = _inventory_for_pr(cfg, repo, pr_number, script_dir)
    required, reason = requires_rereview(inventory, draft_text, meta=meta)
    reviewers: list[str] = []
    if required:
        if meta and meta.get("reviewers"):
            reviewers = [str(r) for r in meta["reviewers"]]
        else:
            seen: list[str] = []
            for item in sorted(
                inventory, key=lambda x: x.get("created_at") or "", reverse=True
            ):
                login = item.get("author", "")
                if login and login not in seen:
                    seen.append(login)
            reviewers = seen
    return required, reason, reviewers


def publish_now(
    cfg: dict,
    repo: str,
    pr_number: int,
    draft_path: Path,
    required: bool,
    reason: str,
    reviewers: list[str],
    worktree_path: str | None = None,
) -> None:
    from pr_fix_attribution import ensure_attribution_in_report
    from pr_fix_publish import default_worktree_path, ready_comment_path, strip_draft_header

    repo_slug = repo.split("/", 1)[-1]
    report = cfg.get("report") or {}
    draft_dir = str(report.get("draft_path", "~/.local/share/ai-sdlc/pr-fix-reports"))
    ready = ready_comment_path(draft_dir, repo_slug, pr_number)
    body = ensure_attribution_in_report(
        strip_draft_header(draft_path.read_text(encoding="utf-8")), cfg
    )
    ready.write_text(body, encoding="utf-8")

    if report_push(cfg):
        git = cfg.get("git") or {}
        wt = Path(
            worktree_path
            or default_worktree_path(
                str(git.get("worktree_root", "~/.local/share/ai-sdlc/worktrees")),
                repo_slug,
                pr_number,
            )
        )
        if not wt.is_dir():
            raise SystemExit(f"error: worktree not found: {wt}")
        subprocess.run(["git", "-C", str(wt), "push", "origin", "HEAD"], check=True)

    labels = cfg.get("labels") or {}
    complete = str(labels.get("complete", "pr-fix-cycle-complete"))
    in_progress = str(labels.get("in_progress", "pr-fix-cycle-in-progress"))

    subprocess.run(
        ["gh", "pr", "comment", str(pr_number), "--repo", repo, "--body-file", str(ready)],
        check=True,
    )
    if report_apply_labels(cfg):
        subprocess.run(
            [
                "gh",
                "pr",
                "edit",
                str(pr_number),
                "--repo",
                repo,
                "--add-label",
                complete,
                "--remove-label",
                in_progress,
            ],
            check=True,
        )
    if required and reviewers:
        args = ["gh", "pr", "edit", str(pr_number), "--repo", repo]
        for reviewer in reviewers:
            args.extend(["--add-reviewer", reviewer])
        subprocess.run(args, check=True)

    print(
        json.dumps(
            {
                "action": "published",
                "repo": repo,
                "pr": pr_number,
                "rereview_required": required,
                "rereview_reason": reason,
                "reviewers": reviewers,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument(
        "--mode",
        choices=("auto", "prepare", "publish"),
        default="auto",
        help="auto: prepare when report.submit=false, else publish",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    cfg["_config_path"] = args.config
    script_dir = Path(__file__).resolve().parent
    repo_slug = args.repo.split("/", 1)[-1]
    draft_path = draft_report_path(
        str((cfg.get("report") or {}).get("draft_path")),
        repo_slug,
        args.pr,
    )
    if not draft_path.exists():
        raise SystemExit(f"error: draft report not found: {draft_path}")

    draft_text = draft_path.read_text(encoding="utf-8")
    required, reason, reviewers = resolve_rereview(
        cfg, args.repo, args.pr, draft_text, script_dir
    )

    mode = args.mode
    if mode == "auto":
        mode = "publish" if report_submit(cfg) else "prepare"

    if mode == "prepare":
        meta = prepare_publish_artifacts(
            cfg=cfg,
            repo=args.repo,
            pr_number=args.pr,
            draft_text=draft_text,
            rereview_required=required,
            rereview_reason=reason,
            reviewers=reviewers,
        )
        print(json.dumps({"action": "prepared", **meta}))
        return

    if mode == "publish":
        draft_dir = str((cfg.get("report") or {}).get("draft_path"))
        mp = meta_path(draft_dir, repo_slug, args.pr)
        if mp.exists():
            meta = load_meta(draft_dir, repo_slug, args.pr)
            if already_published(meta):
                print(
                    json.dumps(
                        {
                            "action": "already_published",
                            "repo": args.repo,
                            "pr": args.pr,
                            "report_url": meta.get("report_url"),
                        }
                    )
                )
                return
            script_path = meta.get("publish_script")
            if script_path:
                script = Path(script_path)
                if script.is_file():
                    subprocess.run([str(script)], check=True)
                    print(json.dumps({"action": "published_via_script", "script": str(script)}))
                    return
            publish_now(
                cfg,
                args.repo,
                args.pr,
                draft_path,
                required,
                reason,
                reviewers,
                worktree_path=meta.get("worktree"),
            )
            return

        publish_now(cfg, args.repo, args.pr, draft_path, required, reason, reviewers)
        return

    raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
