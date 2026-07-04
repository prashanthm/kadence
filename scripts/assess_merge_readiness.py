#!/usr/bin/env python3
"""Risk-based merge-readiness gate for the engineering work loop (e04-f10).

Decides whether the loop may promote a draft PR to ready and merge it, or must
leave it draft for the operator. The decision is a pure function of collected
facts plus the operator's ``pr.merge_policy`` config — it performs no GitHub
writes itself (the caller does, honoring ``dry_run``).

Auto-land requires ALL gates to hold (see e04-f10 design appendix A):
  1. risk tier == ``auto``
  2. Loop AC fully verified (verify_loop_ac exit 0)
  3. PR mergeable
  4. CI all-green
  5. independent pr-review-loop approval at HEAD (no Critical/High)
  6. base == the integration branch

There is no diff-size budget gate: in v2 each feature is a single coherent,
PR-sized increment (right-sized at generation time), so PR size is not an
auto-land criterion. Size is never a gate — Loop AC verifies behavior only.

Any failed gate yields a ``BLOCK`` verdict with a specific machine-readable
reason; the loop leaves the PR draft and applies ``loop-merge-blocked:<reason>``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

GhRunner = Callable[[list[str]], Any]

MERGE = "MERGE"
BLOCK = "BLOCK"

# Ordered: the first failing gate is reported, so the reason is the most
# fundamental blocker rather than an arbitrary one.
REASON_TIER_NOT_AUTO = "tier_not_auto"
REASON_LOOP_AC_FAILED = "loop_ac_failed"
REASON_WRONG_BASE = "wrong_base"
REASON_CONFLICTING = "conflicting"
REASON_MERGEABLE_UNKNOWN = "mergeable_unknown"
REASON_CI_FAILED = "ci_failed"
REASON_CI_RUNNING = "ci_running"
REASON_NOT_REVIEWED = "not_reviewed"
REASON_CHANGES_REQUESTED = "changes_requested"
REASON_POLICY_DISABLED = "policy_disabled"


def _as_bool(value: Any, default: bool) -> bool:
    """Coerce a config scalar to bool. The toolkit's minimal YAML parser does
    not strip inline ``#`` comments, so a value can arrive as a string like
    ``"true   # note"``; treat any non-empty, non-false-ish string as the
    boolean it was meant to be rather than relying on Python truthiness."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        head = value.strip().split("#", 1)[0].strip().lower()
        if head in ("true", "yes", "1", "on"):
            return True
        if head in ("false", "no", "0", "off", ""):
            return False
        return default
    return bool(value)


@dataclass(frozen=True)
class MergePolicy:
    """Operator ``pr.merge_policy`` config (see engineering-work-loop config)."""

    enabled: bool = False
    auto_ready_tier: str = "auto"
    require_pr_review_approved: bool = True
    require_ci_green: bool = True
    require_mergeable: bool = True
    method: str = "merge"
    delete_branch: bool = True
    dry_run: bool = True
    integration_branch: str = "main"

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> MergePolicy:
        pr = (cfg or {}).get("pr") or {}
        mp = pr.get("merge_policy") or {}
        defaults = cls()
        return cls(
            enabled=_as_bool(mp.get("enabled"), defaults.enabled),
            auto_ready_tier=str(mp.get("auto_ready_tier", defaults.auto_ready_tier)).split("#")[0].strip(),
            require_pr_review_approved=_as_bool(
                mp.get("require_pr_review_approved"), defaults.require_pr_review_approved
            ),
            require_ci_green=_as_bool(mp.get("require_ci_green"), defaults.require_ci_green),
            require_mergeable=_as_bool(mp.get("require_mergeable"), defaults.require_mergeable),
            method=str(mp.get("method", defaults.method)).split("#")[0].strip(),
            delete_branch=_as_bool(mp.get("delete_branch"), defaults.delete_branch),
            dry_run=_as_bool(mp.get("dry_run"), defaults.dry_run),
            integration_branch=str(
                mp.get("integration_branch")
                or (cfg or {}).get("integration_branch")
                or defaults.integration_branch
            ).split("#")[0].strip(),
        )


@dataclass(frozen=True)
class PrFacts:
    """Everything ``assess`` needs about a PR — collectable without merging."""

    risk_tier: str = "human-only"
    loop_ac_passed: bool = False
    mergeable: str = "UNKNOWN"          # MERGEABLE | CONFLICTING | UNKNOWN
    ci_state: str = "fail"              # pass | fail | running | none
    review_approved: bool = False
    changes_requested: bool = False
    base_ref: str = ""
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0


@dataclass(frozen=True)
class Verdict:
    action: str                         # MERGE | BLOCK
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "reason": self.reason, "evidence": self.evidence}


def assess(facts: PrFacts, policy: MergePolicy) -> Verdict:
    """Pure decision: MERGE only when every required gate holds."""
    evidence = {
        "risk_tier": facts.risk_tier,
        "loop_ac_passed": facts.loop_ac_passed,
        "mergeable": facts.mergeable,
        "ci_state": facts.ci_state,
        "review_approved": facts.review_approved,
        "base_ref": facts.base_ref,
        "changed_files": facts.changed_files,
        "changed_lines": facts.additions + facts.deletions,
    }

    # Gate 0: policy must opt in. Default-off reproduces today's behavior.
    if not policy.enabled:
        return Verdict(BLOCK, REASON_POLICY_DISABLED, evidence)

    # Gate 1: only the configured auto tier is ever eligible.
    if facts.risk_tier != policy.auto_ready_tier:
        return Verdict(BLOCK, REASON_TIER_NOT_AUTO, evidence)

    # Gate 2: deterministic Loop AC must have fully passed.
    if not facts.loop_ac_passed:
        return Verdict(BLOCK, REASON_LOOP_AC_FAILED, evidence)

    # Gate 6: never land onto a stacked/unexpected base.
    if policy.integration_branch and facts.base_ref != policy.integration_branch:
        return Verdict(BLOCK, REASON_WRONG_BASE, evidence)

    # Gate 3: mergeable (no conflicts).
    if policy.require_mergeable:
        if facts.mergeable == "CONFLICTING":
            return Verdict(BLOCK, REASON_CONFLICTING, evidence)
        if facts.mergeable != "MERGEABLE":
            return Verdict(BLOCK, REASON_MERGEABLE_UNKNOWN, evidence)

    # Gate 4: CI all-green. ``none`` (empty rollup — no checks reported) is
    # treated like ``running``: not demonstrably green, so it blocks merge.
    if policy.require_ci_green:
        if facts.ci_state in ("running", "pending", "none"):
            return Verdict(BLOCK, REASON_CI_RUNNING, evidence)
        if facts.ci_state != "pass":
            return Verdict(BLOCK, REASON_CI_FAILED, evidence)

    # Gate 5: independent pr-review-loop approval at HEAD.
    if policy.require_pr_review_approved:
        if facts.changes_requested:
            return Verdict(BLOCK, REASON_CHANGES_REQUESTED, evidence)
        if not facts.review_approved:
            return Verdict(BLOCK, REASON_NOT_REVIEWED, evidence)

    return Verdict(MERGE, "", evidence)


# --- Fact collection (thin gh wrapper; injectable for tests) ----------------


def default_gh_run(args: list[str]) -> Any:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return json.loads(proc.stdout or "null")


def ci_state_from_rollup(rollup: list[dict[str, Any]] | None) -> str:
    """Classify a PR's status-check rollup as pass | fail | running | none.

    An empty rollup yields ``none`` — treated by gate 4 as a non-green state
    that blocks merge (``ci_running``). This is deliberately conservative: a PR
    with no checks reported has not demonstrably passed CI, so the loop must not
    auto-land it."""
    states = [
        (c.get("conclusion") or c.get("state") or "") for c in (rollup or [])
    ]
    if not states:
        return "none"
    bad = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}
    pend = {"IN_PROGRESS", "PENDING", "QUEUED", "WAITING", "", None}
    if any(s in bad for s in states):
        return "fail"
    if any(s in pend for s in states):
        return "running"
    return "pass"


def latest_review_by(reviews: list[dict[str, Any]] | None, login: str) -> dict[str, Any] | None:
    """Most recent review submitted by ``login`` (sorted by ``submittedAt``).

    Mirrors ``discover_pr_review_candidates.latest_review_by`` so gate 5 keys off
    the same notion of "the operator's current review" the review loop uses."""
    matching = [
        rv
        for rv in (reviews or [])
        if (rv.get("author") or {}).get("login") == login
    ]
    if not matching:
        return None
    return max(matching, key=lambda r: r.get("submittedAt") or "")


def review_at_head(review: dict[str, Any] | None, head_oid: str) -> bool:
    """True when ``review`` was submitted against the PR's current HEAD commit."""
    if not review or not head_oid:
        return False
    return (review.get("commit") or {}).get("oid", "") == head_oid


# A review body carrying findings under a Critical/High heading must block, even
# when the verdict is APPROVED — an approval with open Critical/High findings is
# a mistake the gate should not honor (e04-f10 appendix A gate 5: "no
# Critical/High"). Matches markdown headings like "### Critical" / "## High".
_CRITICAL_HIGH_HEADING = re.compile(r"(?im)^\s{0,3}#{1,6}\s*(critical|high)\b")
# A "none under this heading" marker that neutralizes the heading above.
_NONE_MARKER = re.compile(r"(?im)^\s*-?\s*none\b\.?\s*$")


def review_body_has_critical_high(body: str | None) -> bool:
    """True when a review body lists Critical or High findings.

    Scans the markdown for a ``Critical``/``High`` heading whose section is not
    immediately marked ``None``. Conservative: an ambiguous/free-form body that
    names a Critical/High section without an explicit ``None`` blocks merge."""
    if not body:
        return False
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        if not _CRITICAL_HIGH_HEADING.match(line):
            continue
        # Look at the lines immediately following the heading until the next
        # heading; if the first non-blank content is "None", the section is empty.
        for follow in lines[idx + 1:]:
            if not follow.strip():
                continue
            if follow.lstrip().startswith("#"):
                break  # next heading — section had no content, treat as empty
            if _NONE_MARKER.match(follow):
                break  # explicitly "None" → not a finding
            return True  # real content under a Critical/High heading
    return False


def collect_pr_facts(
    owner: str,
    repo: str,
    pr_number: int,
    *,
    risk_tier: str,
    loop_ac_passed: bool,
    operator: str = "",
    gh_run: GhRunner | None = None,
) -> PrFacts:
    """Collect mergeability / CI / review facts for a PR via ``gh``.

    ``risk_tier`` and ``loop_ac_passed`` come from the loop's prior
    classification + Loop AC verification (not re-derived here).

    Gate 5 (review) is resolved against the *pr-review-loop operator* at HEAD,
    not GitHub's aggregate ``reviewDecision``: ``review_approved`` is true only
    when ``operator``'s most recent review is ``APPROVED``, was submitted against
    the current HEAD commit, and carries no Critical/High findings in its body.
    This enforces the independent dual-gate invariant the feature depends on —
    an unrelated team reviewer's approval, or a stale approval at an older SHA,
    no longer satisfies the gate. When ``operator`` is empty the gate falls back
    to the aggregate ``reviewDecision`` (legacy behavior)."""
    gh_run = gh_run or default_gh_run
    data = gh_run(
        [
            "pr", "view", str(pr_number), "--repo", f"{owner}/{repo}",
            "--json",
            "mergeable,reviewDecision,baseRefName,changedFiles,additions,deletions,"
            "statusCheckRollup,reviews,headRefOid",
        ]
    )
    decision = (data.get("reviewDecision") or "").upper()
    # Aggregate CHANGES_REQUESTED is always a fast-path block (any reviewer).
    changes_requested = decision == "CHANGES_REQUESTED"
    head_oid = str(data.get("headRefOid") or "")

    if operator:
        op_review = latest_review_by(data.get("reviews"), operator)
        op_state = (op_review or {}).get("state", "").upper()
        # The operator may have requested changes at HEAD even if the aggregate
        # decision is something else; honor that as a block too.
        if op_state == "CHANGES_REQUESTED" and review_at_head(op_review, head_oid):
            changes_requested = True
        review_approved = (
            op_state == "APPROVED"
            and review_at_head(op_review, head_oid)
            and not review_body_has_critical_high((op_review or {}).get("body"))
        )
    else:
        review_approved = decision == "APPROVED"

    return PrFacts(
        risk_tier=risk_tier,
        loop_ac_passed=loop_ac_passed,
        mergeable=str(data.get("mergeable") or "UNKNOWN"),
        ci_state=ci_state_from_rollup(data.get("statusCheckRollup")),
        review_approved=review_approved,
        changes_requested=changes_requested,
        base_ref=str(data.get("baseRefName") or ""),
        changed_files=int(data.get("changedFiles") or 0),
        additions=int(data.get("additions") or 0),
        deletions=int(data.get("deletions") or 0),
    )


def decision_log_line(repo: str, pr_number: int, verdict: Verdict, policy: MergePolicy) -> str:
    """One-line audit record for the operator state log.

    In ``dry_run`` (shadow) mode the action is prefixed ``WOULD ``; the caller
    must perform no GitHub writes in that mode."""
    prefix = "WOULD " if policy.dry_run else ""
    if verdict.action == MERGE:
        return f"{prefix}MERGE {repo}#{pr_number}"
    return f"{prefix}BLOCK {repo}#{pr_number} — {verdict.reason}"


def should_write_to_github(verdict: Verdict, policy: MergePolicy) -> bool:
    """True only when the loop may perform GitHub writes (ready/merge/label).

    Shadow mode (``dry_run``) and a disabled policy both forbid writes. A
    ``BLOCK`` verdict only ever applies a label, never merges — callers gate the
    merge on ``verdict.action == MERGE`` separately."""
    if not policy.enabled or policy.dry_run:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess PR merge-readiness (e04-f10)")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--risk-tier", default="human-only")
    parser.add_argument(
        "--loop-ac-passed",
        action="store_true",
        help="set when verify_loop_ac.py exited 0 for this item",
    )
    parser.add_argument("--config", help="engineering-work-loop config path")
    parser.add_argument(
        "--review-operator",
        default="",
        help="pr-review-loop reviewer login for gate 5 (defaults to config github_user)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.config:
        from engineering_work_loop_config import load_config

        cfg = load_config(args.config)
    else:
        cfg = {}
    policy = MergePolicy.from_config(cfg)
    # Gate 5 keys off the pr-review-loop operator (the configured reviewer whose
    # independent approval at HEAD the dual-gate model requires). It is the same
    # ``github_user`` the review loop authenticates as; allow an explicit
    # override via --review-operator for setups where they differ.
    operator = args.review_operator or str((cfg or {}).get("github_user") or "")

    owner, _, repo = args.repo.partition("/")
    facts = collect_pr_facts(
        owner, repo, args.pr,
        risk_tier=args.risk_tier,
        loop_ac_passed=args.loop_ac_passed,
        operator=operator,
    )
    verdict = assess(facts, policy)

    if args.json:
        json.dump(
            {
                **verdict.to_dict(),
                "dry_run": policy.dry_run,
                "policy": {"method": policy.method, "delete_branch": policy.delete_branch},
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        prefix = "WOULD " if policy.dry_run else ""
        if verdict.action == MERGE:
            print(f"{prefix}MERGE {args.repo}#{args.pr}")
        else:
            print(f"{prefix}BLOCK {args.repo}#{args.pr} — {verdict.reason}")
    # exit 0 = MERGE verdict, 10 = BLOCK (so callers can branch on it)
    sys.exit(0 if verdict.action == MERGE else 10)


if __name__ == "__main__":
    main()
