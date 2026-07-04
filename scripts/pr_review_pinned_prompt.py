#!/usr/bin/env python3
"""Append the non-interactive pinned-candidate section for cron PR review firings."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from discover_pr_review_candidates import discover
from force_pr_ref import parse_force_pr
from pr_review_loop_config import load_config


def resolve_candidate(cfg: dict[str, Any], force_pr: str | int) -> dict[str, Any]:
    raw = os.environ.get("PR_REVIEW_LOOP_CANDIDATE_JSON", "").strip()
    if raw:
        return json.loads(raw)
    ref = parse_force_pr(force_pr)
    if ref is None:
        raise SystemExit("error: PR_REVIEW_LOOP_FORCE_PR not set")
    cand = discover(cfg, force_pr=ref.number).get("candidate")
    if not cand:
        raise SystemExit(f"error: no eligible candidate for --force-pr {force_pr}")
    return cand


def render_pinned_section(cand: dict[str, Any]) -> str:
    owner = cand["owner"]
    repo = cand["repo"]
    num = cand["number"]
    head = cand.get("head_short") or (cand.get("head_sha") or "")[:7]
    title = cand.get("title", "")
    full_repo = f"{owner}/{repo}"

    lines = [
        "## Pinned candidate (automated cron firing — NON-INTERACTIVE)",
        "",
        "This section **overrides** the readiness-scan behavior above. Discovery already",
        "selected exactly one PR. You **must** complete a full review and **post it** with",
        "`gh pr review` before exiting. The cron verifies your review on GitHub at HEAD;",
        "exiting without posting counts as failure.",
        "",
        "**Do not:** scan other repos, list other eligible PRs, or ask the operator what to do.",
        "",
        f"- **Repo:** `{full_repo}`",
        f"- **PR:** #{num}",
        f"- **HEAD:** `{head}`",
        f"- **Title:** {title}",
        "",
        "**Required steps:**",
        "",
        "1. Gather context (no worktree unless `is_toolkit_pr`):",
        "```bash",
        f"gh pr diff {num} --repo {full_repo}",
        f"gh pr view {num} --repo {full_repo} --json "
        "title,body,files,commits,reviews,statusCheckRollup,headRefOid",
        "```",
        "2. Write the review per `pr-review.prompt.md` (findings-first, cite HEAD SHA).",
        "3. Post the review — **one of** `--approve`, `--request-changes`, or `--comment` "
        "is **required** (non-interactive `gh` rejects bare `gh pr review`):",
        "```bash",
        f"gh pr review {num} --repo {full_repo} --comment --body-file review.md",
        "# or: --approve / --request-changes",
        "```",
        "4. Confirm your review landed at HEAD before exiting.",
        "",
        "**Success criterion:** a review from the configured operator exists on GitHub "
        f"at HEAD `{head}`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    force_pr = os.environ["PR_REVIEW_LOOP_FORCE_PR"]
    config_path = os.environ["PR_REVIEW_LOOP_CONFIG"]
    cfg = load_config(config_path)
    cand = resolve_candidate(cfg, force_pr)
    sys.stdout.write(render_pinned_section(cand))


if __name__ == "__main__":
    main()
