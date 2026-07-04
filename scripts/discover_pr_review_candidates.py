#!/usr/bin/env python3
"""Discover PRs where the operator's review is requested, eligible for the
reviewer-side PR review loop.

Implements the decision matrix from .github/prompts/pr-review-loop.prompt.md:
skip draft / self-PR / already-reviewed-this-HEAD / approved-at-HEAD /
CHANGES_REQUESTED-without-re-request / not-requested (incl. stale review at
older HEAD) / ci-pending (when defer_to_ci) / adjacent-reviewer-at-HEAD
(when adjacent_reviewers configured). Idempotent on owner/repo#pr@headRefOid.

A reviewer posts a review (gh pr review); it does NOT edit code, so there is no
worktree / clone_path in the common path. `is_toolkit_pr` flags PRs that modify
kadence/ so the agent can optionally materialize a read-only worktree.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pr_review_loop_config import expand_path, load_config

GhRunner = Callable[[list[str]], Any]

GITHUB_FILES_CAP = 100

PR_VIEW_FIELDS = (
    "number,title,isDraft,author,headRefName,headRefOid,"
    "reviewRequests,reviews,reviewDecision,files,labels,statusCheckRollup"
)


def default_gh_run(args: list[str]) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return json.loads(proc.stdout or "null")


def read_state_log(path: str) -> dict[str, dict[str, Any]]:
    """Map 'owner/repo#pr@sha' -> latest reviewed entry (idempotency per HEAD)."""
    reviewed: dict[str, dict[str, Any]] = {}
    if not path:
        return reviewed
    p = Path(expand_path(path))
    if not p.exists():
        return reviewed
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("outcome") != "review_posted":
            continue
        sha = entry.get("head_sha") or ""
        key = f"{entry.get('owner')}/{entry.get('repo')}#{entry.get('pr')}@{sha}"
        reviewed[key] = entry
    return reviewed


def label_names(pr: dict[str, Any]) -> set[str]:
    return {lbl.get("name", "") for lbl in pr.get("labels") or []}


def review_request_logins(pr: dict[str, Any]) -> set[str]:
    """Logins (users) + slugs (teams) currently in reviewRequests."""
    out: set[str] = set()
    for rr in pr.get("reviewRequests") or []:
        login = rr.get("login") or rr.get("slug") or rr.get("name")
        if login:
            out.add(login)
    return out


def latest_review_by(pr: dict[str, Any], login: str) -> dict[str, Any] | None:
    """Most recent review submitted by `login` (sorted by submittedAt)."""
    matching = [
        rv
        for rv in pr.get("reviews") or []
        if (rv.get("author") or {}).get("login") == login
    ]
    if not matching:
        return None
    return max(matching, key=lambda r: r.get("submittedAt") or "")


def reviewed_at_head(review: dict[str, Any] | None, head_oid: str) -> bool:
    if not review:
        return False
    return (review.get("commit") or {}).get("oid", "") == head_oid


def operator_review_at_head(
    owner: str,
    repo: str,
    pr_number: int,
    operator: str,
    head_sha: str,
    gh_run: GhRunner | None = None,
) -> bool:
    """True when `operator` submitted a review on GitHub at `head_sha`."""
    if not operator or not head_sha:
        return False
    gh_run = gh_run or default_gh_run
    pr = gh_run(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "reviews,headRefOid",
        ]
    )
    if (pr.get("headRefOid") or "") != head_sha:
        return False
    return reviewed_at_head(latest_review_by(pr, operator), head_sha)


def ci_pending(pr: dict[str, Any]) -> bool:
    """True when any status check is still running or queued."""
    for check in pr.get("statusCheckRollup") or []:
        status = (check.get("status") or "").upper()
        if status in ("IN_PROGRESS", "QUEUED", "PENDING", "WAITING"):
            return True
    return False


def adjacent_review_at_head(
    pr: dict[str, Any], operator: str, head_oid: str, adjacent: set[str]
) -> bool:
    """A configured adjacent reviewer already reviewed this HEAD."""
    if not adjacent:
        return False
    author = (pr.get("author") or {}).get("login", "")
    for rv in pr.get("reviews") or []:
        rv_login = (rv.get("author") or {}).get("login", "")
        if rv_login in ("", operator, author):
            continue
        if rv_login not in adjacent:
            continue
        if (rv.get("commit") or {}).get("oid", "") == head_oid:
            return True
    return False


def is_toolkit_pr(pr: dict[str, Any]) -> bool:
    # Legacy check: a PR (in some OTHER repo) that modified a vendored
    # kadence/ subdirectory. Kept for any repo that still vendors the
    # toolkit that way; standalone-repo detection is repo-identity, below.
    for f in pr.get("files") or []:
        if str(f.get("path", "")).startswith("kadence/"):
            return True
    return False


def is_toolkit_pr_paginated(
    pr: dict[str, Any], owner: str, repo: str, gh_run: GhRunner
) -> bool:
    """Paginated files walk when gh pr view truncates at GITHUB_FILES_CAP."""
    page = 1
    while True:
        batch = gh_run(
            [
                "api",
                f"repos/{owner}/{repo}/pulls/{pr['number']}/files",
                "-f",
                "per_page=100",
                "-f",
                f"page={page}",
            ]
        )
        if not batch:
            break
        for f in batch:
            if str(f.get("filename", "")).startswith("kadence/"):
                return True
        if len(batch) < GITHUB_FILES_CAP:
            break
        page += 1
    return False


def resolve_is_toolkit_pr(
    pr: dict[str, Any], owner: str, repo: str, gh_run: GhRunner | None
) -> bool:
    # Standalone repo: a PR IN kadence itself always needs the
    # read-only worktree exception (its own conventions/prompts are under
    # review) — no file path carries a vendored-subdirectory prefix anymore.
    if repo == "kadence":
        return True
    if is_toolkit_pr(pr):
        return True
    if gh_run and len(pr.get("files") or []) >= GITHUB_FILES_CAP:
        return is_toolkit_pr_paginated(pr, owner, repo, gh_run)
    return False


def skip_reason(
    pr: dict[str, Any],
    cfg: dict[str, Any],
    reviewed_state: dict[str, dict[str, Any]],
    owner: str,
    repo: str,
) -> str | None:
    operator = cfg.get("github_user", "")
    head_oid = pr.get("headRefOid") or ""
    author = (pr.get("author") or {}).get("login", "")
    requested = review_request_logins(pr)
    adjacent = {str(x) for x in (cfg.get("adjacent_reviewers") or [])}

    if pr.get("isDraft"):
        return "draft"
    if author == operator:
        return "self_pr"
    # idempotency: already reviewed this exact HEAD
    key = f"{owner}/{repo}#{pr['number']}@{head_oid}"
    if key in reviewed_state:
        return "already_reviewed_head"

    op_latest = latest_review_by(pr, operator)
    if op_latest:
        state = op_latest.get("state", "")
        if state == "APPROVED" and reviewed_at_head(op_latest, head_oid):
            return "approved_at_head"
        if state == "CHANGES_REQUESTED" and operator not in requested:
            # author hasn't re-requested -> wait, regardless of new commits
            return "changes_requested_no_rerequest"

    # Operator must be in reviewRequests unless they already reviewed this HEAD.
    # Stale reviews at older SHAs do not qualify — re-request is required (closes
    # the --force-pr hole where APPROVED-at-old-HEAD without re-request slips through).
    if operator not in requested and not reviewed_at_head(op_latest, head_oid):
        return "not_requested"

    if cfg.get("defer_to_ci", True) and ci_pending(pr):
        return "ci_pending"

    # Skip when a configured adjacent reviewer reviewed at HEAD, unless the
    # operator is explicitly re-requested (author wants their review anyway).
    if adjacent_review_at_head(pr, operator, head_oid, adjacent) and operator not in requested:
        return "adjacent_reviewed_at_head"

    return None


def evaluate_pr(
    pr: dict[str, Any],
    owner: str,
    repo: str,
    cfg: dict[str, Any],
    reviewed_state: dict[str, dict[str, Any]],
    gh_run: GhRunner | None = None,
) -> dict[str, Any] | None:
    if skip_reason(pr, cfg, reviewed_state, owner, repo) is not None:
        return None
    head_oid = pr.get("headRefOid") or ""
    return {
        "owner": owner,
        "repo": repo,
        "number": pr["number"],
        "title": pr.get("title", ""),
        "head_sha": head_oid,
        "head_short": head_oid[:7],
        "head_branch": pr.get("headRefName", ""),
        "review_decision": pr.get("reviewDecision", ""),
        "is_toolkit_pr": resolve_is_toolkit_pr(pr, owner, repo, gh_run),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def find_candidates(
    cfg: dict[str, Any],
    gh_run: GhRunner | None = None,
    force_pr: int | None = None,
) -> list[dict[str, Any]]:
    """Every eligible PR across all configured repos, in (repo, PR) order.

    Unlike a first-match scan, this accumulates all eligible candidates so a
    single firing can review them all. Per-HEAD idempotency still filters out
    already-reviewed HEADs via `evaluate_pr`/`reviewed_state`.
    """
    gh_run = gh_run or default_gh_run
    reviewed_state = read_state_log(cfg.get("state_log", ""))
    operator = cfg.get("github_user", "")

    candidates: list[dict[str, Any]] = []
    for repo_entry in cfg.get("repos") or []:
        owner = repo_entry.get("owner", "")
        repo = repo_entry.get("repo", "")
        if not owner or not repo:
            continue

        if force_pr is not None:
            try:
                pr = gh_run(
                    ["pr", "view", str(force_pr), "--repo", f"{owner}/{repo}",
                     "--json", PR_VIEW_FIELDS]
                )
            except RuntimeError:
                continue
            cand = evaluate_pr(pr, owner, repo, cfg, reviewed_state, gh_run)
            if cand:
                candidates.append(cand)
            return candidates

        # search: PRs where the operator's review is requested
        prs = gh_run(
            ["pr", "list", "--repo", f"{owner}/{repo}", "--state", "open",
             "--search", f"review-requested:{operator}",
             "--json", PR_VIEW_FIELDS, "--limit", "50"]
        )
        if isinstance(prs, dict):
            prs = [prs]
        for pr in prs or []:
            cand = evaluate_pr(pr, owner, repo, cfg, reviewed_state, gh_run)
            if cand:
                candidates.append(cand)
    return candidates


def find_candidate(
    cfg: dict[str, Any],
    gh_run: GhRunner | None = None,
    force_pr: int | None = None,
) -> dict[str, Any] | None:
    """First eligible candidate (back-compat for single-PR callers)."""
    found = find_candidates(cfg, gh_run, force_pr=force_pr)
    return found[0] if found else None


def discover(
    cfg: dict[str, Any],
    gh_run: GhRunner | None = None,
    force_pr: int | None = None,
) -> dict[str, Any]:
    """Return all eligible candidates plus the first one for back-compat.

    `candidates` is the full list the cron consumes for batch review;
    `candidate` is the first (or None) for any single-PR reader.
    """
    found = find_candidates(cfg, gh_run, force_pr=force_pr)
    return {"candidates": found, "candidate": found[0] if found else None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover PR review loop candidates")
    parser.add_argument("--config", required=True)
    parser.add_argument("--force-pr", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    result = discover(cfg, force_pr=args.force_pr)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        cands = result.get("candidates") or []
        if not cands:
            print("no candidates")
        else:
            print(f"{len(cands)} candidate(s):")
            for c in cands:
                print(f"  {c['owner']}/{c['repo']}#{c['number']} @{c['head_short']}")


if __name__ == "__main__":
    main()
