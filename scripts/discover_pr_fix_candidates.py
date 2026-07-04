#!/usr/bin/env python3
"""Discover operator-authored PRs eligible for the PR comment fix loop."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pr_fix_config import exclude_reviewers, expand_path, load_config, min_reviewer_feedback
from pr_fix_rereview import all_reviews_approved, latest_review_states

GhRunner = Callable[[list[str]], Any]


def default_gh_run(args: list[str]) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return json.loads(proc.stdout or "null")


def read_state_log(path: str) -> dict[str, dict[str, Any]]:
    """Map 'owner/repo#pr' -> latest complete entry."""
    p = Path(expand_path(path))
    complete: dict[str, dict[str, Any]] = {}
    if not p.exists():
        return complete
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("status") == "complete":
            key = f"{entry.get('owner')}/{entry.get('repo')}#{entry.get('pr')}"
            complete[key] = entry
    return complete


def label_names(pr: dict[str, Any]) -> set[str]:
    return {lbl.get("name", "") for lbl in pr.get("labels") or []}


# --- Round-aware re-engagement ---------------------------------------------
# The loop completes a fix cycle (status:complete + pr-fix-cycle-complete label),
# but a PR can come back for round 2/3 with new CHANGES_REQUESTED. These helpers
# detect a *genuinely new round* (head advanced + fresh non-operator pressure)
# and enforce a hard ceiling (max_rounds) so the loop never re-fires forever.


def completed_head(entry: dict[str, Any]) -> str | None:
    """The PR head the last completed cycle ended at (fallback across schema
    variants the agent has written over time)."""
    for k in ("head_after_fix", "head_after_push", "head_at_fix"):
        v = entry.get(k)
        if v:
            return str(v)
    return None


def completed_rounds(entry: dict[str, Any]) -> int:
    """How many cycles have completed on this PR (legacy entries lacking the
    field count as round 1)."""
    try:
        return int(entry.get("rounds", 1))
    except (TypeError, ValueError):
        return 1


def head_advanced(pr: dict[str, Any], entry: dict[str, Any]) -> bool:
    """True when the PR's current head differs from the completed head. The
    stored head may be a 7-char short SHA; headRefOid is full — prefix-compare.
    Missing data is conservative (NOT advanced) so we never re-fire on ambiguity."""
    ch = completed_head(entry)
    head = pr.get("headRefOid") or ""
    if not ch or not head:
        return False
    n = min(len(head), len(ch))
    return head[:n].lower() != ch[:n].lower()


def fresh_feedback_count(inventory: list[dict[str, Any]], completed_at: str | None) -> int:
    """Number of reviewer-feedback items created after the last completion.
    ISO8601 UTC strings sort lexically. No completed_at -> can't time-bound, so
    return 0 (the round signal then relies on head-advanced + CHANGES_REQUESTED)."""
    if not completed_at:
        return 0
    n = 0
    for item in inventory or []:
        ts = item.get("created_at")
        if ts and str(ts) > str(completed_at):
            n += 1
    return n


def is_new_round(
    pr: dict[str, Any],
    entry: dict[str, Any],
    inventory: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> bool:
    """A genuinely new review round: head advanced past the completed head, the
    PR is not all-approved (approved = done), and there is fresh non-operator
    pressure — a latest CHANGES_REQUESTED review, or >= min_reviewer_feedback
    new items since completion."""
    if not head_advanced(pr, entry):
        return False
    if all_reviews_approved(inventory):
        return False
    states = latest_review_states(inventory)
    if any(s == "CHANGES_REQUESTED" for s in states.values()):
        return True
    threshold = min_reviewer_feedback(cfg)
    return fresh_feedback_count(inventory, entry.get("completed_at")) >= threshold


def complete_gate(
    pr: dict[str, Any],
    cfg: dict[str, Any],
    entry: dict[str, Any] | None,
    labels: set[str],
    inventory: list[dict[str, Any]],
) -> str | None:
    """Round-aware replacement for the old absolute complete gates.

    Returns a skip reason string, "max_rounds_reached" (ceiling hit), or None
    (eligible — either never completed, or a new round under the cap)."""
    if str(pr.get("state", "")).upper() in {"MERGED", "CLOSED"}:
        return "state_log_complete"

    complete_lbl = (cfg.get("labels") or {}).get("complete", "pr-fix-cycle-complete")
    has_label = complete_lbl in labels
    has_state = entry is not None
    if not has_label and not has_state:
        return None  # never completed -> normal eligibility path

    if not is_new_round(pr, entry or {}, inventory, cfg):
        return "state_log_complete" if has_state else "complete_label"

    try:
        max_rounds = int(cfg.get("max_rounds", 3))
    except (TypeError, ValueError):
        max_rounds = 3
    if completed_rounds(entry or {}) >= max_rounds:
        return "max_rounds_reached"
    return None  # eligible to re-engage the next round


def _validated_clone_path(raw: str) -> str:
    """Expand and sanity-check a clone path. clone_path is operator-trusted
    config, but reject '..' traversal so a fat-fingered relative entry can't
    point the worktree outside intent. Mirrors the engineering-work-loop."""
    expanded = expand_path(str(raw))
    if ".." in Path(expanded).parts:
        raise ValueError(f"clone_path must be an absolute path without '..': {raw!r}")
    return expanded


def clone_path_for_repo(cfg: dict[str, Any], owner: str, repo: str) -> str:
    """Local git clone for a repo: entry clone_path, else git.primary_clone."""
    for entry in cfg.get("repos") or []:
        if entry.get("owner") == owner and entry.get("repo") == repo:
            cp = entry.get("clone_path")
            if cp:
                return _validated_clone_path(str(cp))
    primary = (cfg.get("git") or {}).get("primary_clone", ".")
    return _validated_clone_path(str(primary))


def in_progress_label_age_hours(
    owner: str,
    repo: str,
    pr_number: int,
    in_progress_lbl: str,
    gh_run: GhRunner,
) -> float | None:
    """Hours since in-progress label was applied, or None if not found."""
    events = gh_run(
        ["api", f"repos/{owner}/{repo}/issues/{pr_number}/events", "--paginate"]
    )
    if isinstance(events, dict):
        events = [events]
    latest: datetime | None = None
    for ev in events or []:
        if ev.get("event") != "labeled":
            continue
        label = (ev.get("label") or {}).get("name", "")
        if label != in_progress_lbl:
            continue
        created = ev.get("created_at")
        if not created:
            continue
        ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if latest is None or ts > latest:
            latest = ts
    if latest is None:
        return None
    delta = datetime.now(timezone.utc) - latest
    return delta.total_seconds() / 3600.0


def skip_reason(
    pr: dict[str, Any],
    cfg: dict[str, Any],
    state_complete: dict[str, dict[str, Any]],
    owner: str,
    repo: str,
    gh_run: GhRunner | None = None,
) -> str | None:
    labels = label_names(pr)
    label_cfg = cfg.get("labels") or {}
    in_progress_lbl = label_cfg.get("in_progress", "pr-fix-cycle-in-progress")
    deferred_lbl = label_cfg.get("deferred", "pr-fix-deferred")
    needs_human_lbl = label_cfg.get("needs_human", "pr-fix-needs-human")

    if pr.get("isDraft") and VALID_E2E_LABEL not in labels:
        return "draft"
    # The complete-label / state-log-complete gates are now round-aware and live
    # in complete_gate() (called from evaluate_pr after the review inventory is
    # collected). A PR that exhausted max_rounds carries needs_human — skip it
    # cheaply here before any gh-api inventory calls.
    if needs_human_lbl in labels:
        return "needs_human"
    if deferred_lbl in labels or "loop-blocked" in labels:
        return "deferred"
    if in_progress_lbl in labels:
        stale_hours = float(cfg.get("in_progress_stale_hours", 2))
        if gh_run is not None:
            age = in_progress_label_age_hours(
                owner, repo, int(pr["number"]), in_progress_lbl, gh_run
            )
            if age is None or age < stale_hours:
                return "in_progress"
        else:
            return "in_progress"
    changed = pr.get("changedFiles") or 0
    if changed > cfg.get("max_files_changed", 15):
        return "too_many_files"
    author = (pr.get("author") or {}).get("login", "")
    if author != cfg.get("github_user"):
        return "not_author"
    return None


def _feedback_threshold_not_met(cfg: dict[str, Any], count: int) -> bool:
    return count < min_reviewer_feedback(cfg)


def collect_reviewer_feedback(
    owner: str,
    repo: str,
    pr_number: int,
    github_user: str,
    gh_run: GhRunner,
    excluded: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Collect reviews/comments from all non-operator reviewers."""
    inventory: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    excluded = excluded or set()

    def add(source: str, item: dict[str, Any]) -> None:
        login = (item.get("user") or {}).get("login", "")
        if not login or login == github_user or login in excluded:
            return
        item_id = item.get("id")
        if item_id is None:
            return
        key = (source, int(item_id))
        if key in seen:
            return
        seen.add(key)
        entry: dict[str, Any] = {
            "id": item_id,
            "source": source,
            "author": login,
            "body": (item.get("body") or "")[:8000],
            "created_at": item.get("submitted_at") or item.get("created_at"),
        }
        if source == "review":
            entry["state"] = item.get("state")
        inventory.append(entry)

    reviews = gh_run(
        ["api", f"repos/{owner}/{repo}/pulls/{pr_number}/reviews", "--paginate"]
    )
    if isinstance(reviews, dict):
        reviews = [reviews]
    for rev in reviews or []:
        add("review", rev)

    issue_comments = gh_run(
        ["api", f"repos/{owner}/{repo}/issues/{pr_number}/comments", "--paginate"]
    )
    if isinstance(issue_comments, dict):
        issue_comments = [issue_comments]
    for c in issue_comments or []:
        add("issue_comment", c)

    inline_comments = gh_run(
        ["api", f"repos/{owner}/{repo}/pulls/{pr_number}/comments", "--paginate"]
    )
    if isinstance(inline_comments, dict):
        inline_comments = [inline_comments]
    for c in inline_comments or []:
        add("review_comment", c)

    return inventory


def reviewers_from_inventory(
    inventory: list[dict[str, Any]],
    github_user: str,
    owner: str,
    repo: str,
    pr_number: int,
    gh_run: GhRunner,
) -> list[str]:
    """Unique reviewer logins from inventory, newest feedback first."""
    requested: list[str] = []
    for item in sorted(
        inventory,
        key=lambda x: x.get("created_at") or "",
        reverse=True,
    ):
        login = item.get("author", "")
        if login and login != github_user and login not in requested:
            requested.append(login)
    if requested:
        return requested
    detail = gh_run(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "reviewRequests",
        ]
    )
    for req in detail.get("reviewRequests") or []:
        login = (req.get("login") or req.get("name") or "").strip()
        if login and login != github_user and login not in requested:
            requested.append(login)
    return requested


# Backward-compatible alias
collect_automated_feedback = collect_reviewer_feedback


def reviewers_to_rerequest(
    inventory: list[dict[str, Any]],
    github_user: str,
    owner: str,
    repo: str,
    pr_number: int,
    gh_run: GhRunner,
) -> list[str]:
    return reviewers_from_inventory(
        inventory, github_user, owner, repo, pr_number, gh_run
    )


VALID_E2E_LABEL = "e2e-synthetic-reviews"


def e2e_synthetic_inventory() -> list[dict[str, Any]]:
    """Fixture reviewer feedback for E2E dummy PRs (non-operator authors)."""
    return [
        {
            "id": 900001,
            "source": "review",
            "author": "e2e-reviewer-a",
            "body": "**Low** L1: Fix typo `tset` → `test` in e2e doc.",
            "created_at": "2026-06-23T12:00:00Z",
            "state": "APPROVED",
        },
        {
            "id": 900002,
            "source": "review",
            "author": "e2e-reviewer-b",
            "body": "**Low** L2: Add one-line pointer to loop README in e2e doc.",
            "created_at": "2026-06-23T12:01:00Z",
            "state": "APPROVED",
        },
    ]


def uses_e2e_synthetic_reviews(pr: dict[str, Any]) -> bool:
    return VALID_E2E_LABEL in label_names(pr)


def evaluate_pr(
    pr: dict[str, Any],
    owner: str,
    repo: str,
    cfg: dict[str, Any],
    state_complete: dict[str, dict[str, Any]],
    gh_run: GhRunner,
) -> dict[str, Any] | None:
    reason = skip_reason(pr, cfg, state_complete, owner, repo, gh_run)
    if reason:
        return None

    github_user = cfg.get("github_user", "")
    if uses_e2e_synthetic_reviews(pr):
        inventory = e2e_synthetic_inventory()
    else:
        inventory = collect_reviewer_feedback(
            owner,
            repo,
            int(pr["number"]),
            github_user,
            gh_run,
            exclude_reviewers(cfg),
        )

    # Round-aware complete gate (needs the inventory collected above).
    state_entry = state_complete.get(f"{owner}/{repo}#{pr['number']}")
    gate = complete_gate(pr, cfg, state_entry, label_names(pr), inventory)
    if gate == "max_rounds_reached":
        # Sentinel: discovery can't apply labels; the cron applies needs_human.
        return {
            "_skip": "max_rounds_reached",
            "owner": owner,
            "repo": repo,
            "number": pr["number"],
            "head_branch": pr.get("headRefName", ""),
        }
    if gate is not None:
        return None

    if _feedback_threshold_not_met(cfg, len(inventory)):
        return None

    head_sha = pr.get("headRefOid") or ""
    count = len(inventory)
    review_states = latest_review_states(inventory)
    this_round = (completed_rounds(state_entry) + 1) if state_entry else 1
    return {
        "owner": owner,
        "repo": repo,
        "number": pr["number"],
        "title": pr.get("title", ""),
        "clone_path": clone_path_for_repo(cfg, owner, repo),
        "head_sha": head_sha[:7] if head_sha else "",
        "head_branch": pr.get("headRefName", ""),
        "round": this_round,
        "completed_rounds": completed_rounds(state_entry) if state_entry else 0,
        "reviewer_feedback_count": count,
        "automated_count": count,
        "comment_inventory": inventory,
        "review_states": review_states,
        "all_reviews_approved": all_reviews_approved(inventory),
        "reviewers_to_rerequest": reviewers_to_rerequest(
            inventory, github_user, owner, repo, int(pr["number"]), gh_run
        ),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def find_candidate(
    cfg: dict[str, Any],
    gh_run: GhRunner | None = None,
    force_pr: int | None = None,
) -> dict[str, Any] | None:
    gh_run = gh_run or default_gh_run
    state_path = expand_path(cfg.get("state_log", ""))
    state_complete = read_state_log(state_path)
    github_user = cfg.get("github_user", "")

    for repo_entry in cfg.get("repos") or []:
        owner = repo_entry.get("owner", "")
        repo = repo_entry.get("repo", "")
        if not owner or not repo:
            continue

        if force_pr is not None:
            pr = gh_run(
                [
                    "pr",
                    "view",
                    str(force_pr),
                    "--repo",
                    f"{owner}/{repo}",
                    "--json",
                    "number,title,headRefName,headRefOid,isDraft,labels,changedFiles,author,state",
                ]
            )
            return evaluate_pr(pr, owner, repo, cfg, state_complete, gh_run)

        prs = gh_run(
            [
                "pr",
                "list",
                "--repo",
                f"{owner}/{repo}",
                "--author",
                github_user,
                "--state",
                "open",
                "--json",
                "number,title,headRefName,headRefOid,isDraft,labels,changedFiles,author,state",
                "--limit",
                "50",
            ]
        )
        if isinstance(prs, dict):
            prs = [prs]
        for pr in prs or []:
            candidate = evaluate_pr(pr, owner, repo, cfg, state_complete, gh_run)
            if candidate:
                return candidate
    return None


def discover(
    cfg: dict[str, Any],
    gh_run: GhRunner | None = None,
    force_pr: int | None = None,
) -> dict[str, Any]:
    candidate = find_candidate(cfg, gh_run, force_pr=force_pr)
    return {"candidate": candidate}


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover PR fix loop candidates")
    parser.add_argument("--config", required=True, help="Path to pr-comment-fix-loop config")
    parser.add_argument("--force-pr", type=int, default=None, help="E2E: pin discovery to PR number")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    result = discover(cfg, force_pr=args.force_pr)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        c = result.get("candidate")
        if c:
            print(f"candidate: {c['owner']}/{c['repo']}#{c['number']}")
        else:
            print("no actionable work")


if __name__ == "__main__":
    main()
