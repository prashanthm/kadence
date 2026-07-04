"""Tests for assess_merge_readiness.py (e04-f10 risk-based loop merge)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from assess_merge_readiness import (  # noqa: E402
    BLOCK,
    MERGE,
    REASON_CHANGES_REQUESTED,
    REASON_CI_FAILED,
    REASON_CI_RUNNING,
    REASON_CONFLICTING,
    REASON_LOOP_AC_FAILED,
    REASON_MERGEABLE_UNKNOWN,
    REASON_NOT_REVIEWED,
    REASON_POLICY_DISABLED,
    REASON_TIER_NOT_AUTO,
    REASON_WRONG_BASE,
    MergePolicy,
    PrFacts,
    assess,
    ci_state_from_rollup,
    collect_pr_facts,
    review_body_has_critical_high,
)


def _green_facts(**over) -> PrFacts:
    """A fully-passing fact set; override one field to test each gate."""
    base = dict(
        risk_tier="auto",
        loop_ac_passed=True,
        mergeable="MERGEABLE",
        ci_state="pass",
        review_approved=True,
        changes_requested=False,
        base_ref="main",
        changed_files=2,
        additions=120,
        deletions=10,
    )
    base.update(over)
    return PrFacts(**base)


def _enabled_policy(**over) -> MergePolicy:
    base = dict(enabled=True, dry_run=False)
    base.update(over)
    return MergePolicy(**base)


def test_all_gates_pass_yields_merge():
    v = assess(_green_facts(), _enabled_policy())
    assert v.action == MERGE
    assert v.reason == ""


def test_policy_disabled_blocks_even_when_green():
    # Default policy (enabled=False) reproduces today's draft-only behavior.
    v = assess(_green_facts(), MergePolicy())
    assert v.action == BLOCK
    assert v.reason == REASON_POLICY_DISABLED


def test_assist_tier_never_merges():
    v = assess(_green_facts(risk_tier="assist"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_TIER_NOT_AUTO


def test_human_only_tier_never_merges():
    v = assess(_green_facts(risk_tier="human-only"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_TIER_NOT_AUTO


def test_loop_ac_failed_blocks():
    v = assess(_green_facts(loop_ac_passed=False), _enabled_policy())
    assert v == v  # dataclass sanity
    assert v.action == BLOCK
    assert v.reason == REASON_LOOP_AC_FAILED


def test_wrong_base_blocks():
    v = assess(_green_facts(base_ref="task/6-repo-bootstrap"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_WRONG_BASE


def test_large_diff_is_not_a_gate():
    # v2: diff size is never an auto-land criterion. A large but otherwise-green
    # PR merges — features are right-sized at generation, so there is no budget gate.
    v = assess(_green_facts(changed_files=99, additions=4000, deletions=0), _enabled_policy())
    assert v.action == MERGE
    assert v.reason == ""


def test_conflicting_blocks():
    v = assess(_green_facts(mergeable="CONFLICTING"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_CONFLICTING


def test_mergeable_unknown_blocks():
    v = assess(_green_facts(mergeable="UNKNOWN"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_MERGEABLE_UNKNOWN


def test_ci_failed_blocks():
    v = assess(_green_facts(ci_state="fail"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_CI_FAILED


def test_ci_running_blocks():
    v = assess(_green_facts(ci_state="running"), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_CI_RUNNING


def test_changes_requested_blocks():
    v = assess(
        _green_facts(review_approved=False, changes_requested=True), _enabled_policy()
    )
    assert v.action == BLOCK
    assert v.reason == REASON_CHANGES_REQUESTED


def test_not_reviewed_blocks():
    v = assess(_green_facts(review_approved=False), _enabled_policy())
    assert v.action == BLOCK
    assert v.reason == REASON_NOT_REVIEWED


def test_review_gate_can_be_relaxed():
    # When require_pr_review_approved is off, an un-reviewed-but-otherwise-green
    # auto PR may merge (lighter bar, opt-in only).
    v = assess(
        _green_facts(review_approved=False),
        _enabled_policy(require_pr_review_approved=False),
    )
    assert v.action == MERGE


def test_evidence_is_populated_on_block():
    v = assess(_green_facts(ci_state="fail"), _enabled_policy())
    assert v.evidence["ci_state"] == "fail"
    assert v.evidence["risk_tier"] == "auto"
    assert v.evidence["changed_lines"] == 130


# --- config mapping ---------------------------------------------------------


def test_policy_from_config_defaults_off():
    policy = MergePolicy.from_config({})
    assert policy.enabled is False
    assert policy.dry_run is True
    assert policy.auto_ready_tier == "auto"
    assert policy.require_pr_review_approved is True


def test_policy_from_config_tolerates_inline_comment_strings():
    # The minimal YAML parser can leave inline comments on the value; a stray
    # "true   # note" must NOT silently flip enabled on, and "false # x" must
    # stay off.
    cfg = {"pr": {"merge_policy": {"enabled": "false   # off by default",
                                   "dry_run": "true  # shadow",
                                   "method": "merge  # or squash"}}}
    policy = MergePolicy.from_config(cfg)
    assert policy.enabled is False
    assert policy.dry_run is True
    assert policy.method == "merge"


def test_policy_from_config_reads_block():
    cfg = {
        "pr": {
            "merge_policy": {
                "enabled": True,
                "dry_run": False,
                "require_pr_review_approved": False,
                "method": "squash",
            }
        },
    }
    policy = MergePolicy.from_config(cfg)
    assert policy.enabled is True
    assert policy.dry_run is False
    assert policy.require_pr_review_approved is False
    assert policy.method == "squash"


# --- CI rollup classification ----------------------------------------------


def test_ci_rollup_pass():
    assert ci_state_from_rollup([{"conclusion": "SUCCESS"}, {"conclusion": "SUCCESS"}]) == "pass"


def test_ci_rollup_fail():
    assert ci_state_from_rollup([{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]) == "fail"


def test_ci_rollup_running():
    assert ci_state_from_rollup([{"status": "IN_PROGRESS"}]) == "running"


def test_ci_rollup_none():
    assert ci_state_from_rollup([]) == "none"


# --- fact collection (injected gh runner) -----------------------------------


def test_collect_pr_facts_maps_gh_json():
    def fake_gh(args):
        return {
            "mergeable": "MERGEABLE",
            "reviewDecision": "APPROVED",
            "baseRefName": "main",
            "changedFiles": 3,
            "additions": 50,
            "deletions": 5,
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
        }

    facts = collect_pr_facts(
        "your-org", "subsurface-agentic-ai", 99,
        risk_tier="auto", loop_ac_passed=True, gh_run=fake_gh,
    )
    assert facts.mergeable == "MERGEABLE"
    assert facts.review_approved is True
    assert facts.changes_requested is False
    assert facts.ci_state == "pass"
    assert facts.base_ref == "main"
    # an end-to-end pass through assess() yields MERGE
    assert assess(facts, _enabled_policy()).action == MERGE


def test_collect_pr_facts_changes_requested():
    def fake_gh(args):
        return {
            "mergeable": "MERGEABLE",
            "reviewDecision": "CHANGES_REQUESTED",
            "baseRefName": "main",
            "changedFiles": 1,
            "additions": 2,
            "deletions": 0,
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
        }

    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True, gh_run=fake_gh
    )
    assert facts.changes_requested is True
    assert assess(facts, _enabled_policy()).reason == REASON_CHANGES_REQUESTED


# --- gate 5: pr-review-loop operator approval AT HEAD ------------------------


def _gh_with_reviews(reviews, *, head_oid="head-sha", decision="APPROVED"):
    """Return a fake gh runner yielding a green PR with the given reviews."""

    def fake_gh(args):
        return {
            "mergeable": "MERGEABLE",
            "reviewDecision": decision,
            "baseRefName": "main",
            "changedFiles": 2,
            "additions": 10,
            "deletions": 0,
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
            "reviews": reviews,
            "headRefOid": head_oid,
        }

    return fake_gh


def _review(login, state, oid, *, body="", submitted_at="2026-06-30T00:00:00Z"):
    return {
        "author": {"login": login},
        "state": state,
        "commit": {"oid": oid},
        "body": body,
        "submittedAt": submitted_at,
    }


def test_operator_approved_at_head_yields_merge():
    gh = _gh_with_reviews([_review("operator", "APPROVED", "head-sha")])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is True
    assert assess(facts, _enabled_policy()).action == MERGE


def test_operator_approved_at_stale_sha_blocks():
    # Approval exists but against an older commit → not reviewed at HEAD.
    gh = _gh_with_reviews([_review("operator", "APPROVED", "old-sha")])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is False
    assert assess(facts, _enabled_policy()).reason == REASON_NOT_REVIEWED


def test_unrelated_reviewer_approval_does_not_satisfy_gate():
    # Aggregate reviewDecision is APPROVED, but it came from someone other than
    # the pr-review-loop operator → gate 5 must not pass.
    gh = _gh_with_reviews([_review("teammate", "APPROVED", "head-sha")])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is False
    assert assess(facts, _enabled_policy()).reason == REASON_NOT_REVIEWED


def test_operator_latest_review_wins_over_older_approval():
    gh = _gh_with_reviews(
        [
            _review("operator", "APPROVED", "old-sha", submitted_at="2026-06-29T00:00:00Z"),
            _review(
                "operator", "CHANGES_REQUESTED", "head-sha",
                submitted_at="2026-06-30T00:00:00Z",
            ),
        ],
        decision="CHANGES_REQUESTED",
    )
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is False
    assert facts.changes_requested is True
    assert assess(facts, _enabled_policy()).reason == REASON_CHANGES_REQUESTED


def test_operator_approval_with_critical_high_body_blocks():
    body = "## Findings\n### Critical\n- a real problem\n"
    gh = _gh_with_reviews([_review("operator", "APPROVED", "head-sha", body=body)])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is False
    assert assess(facts, _enabled_policy()).reason == REASON_NOT_REVIEWED


def test_operator_approval_with_none_critical_high_passes():
    body = "## Findings\n### Critical\nNone.\n### High\n- none\n## Notes\nlgtm"
    gh = _gh_with_reviews([_review("operator", "APPROVED", "head-sha", body=body)])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True,
        operator="operator", gh_run=gh,
    )
    assert facts.review_approved is True
    assert assess(facts, _enabled_policy()).action == MERGE


def test_empty_operator_falls_back_to_aggregate_decision():
    # Backward-compatible: no operator configured → aggregate reviewDecision.
    gh = _gh_with_reviews([_review("teammate", "APPROVED", "head-sha")])
    facts = collect_pr_facts(
        "o", "r", 1, risk_tier="auto", loop_ac_passed=True, gh_run=gh,
    )
    assert facts.review_approved is True


# --- review body Critical/High parsing --------------------------------------


def test_review_body_has_critical_high_detects_findings():
    assert review_body_has_critical_high("### Critical\n- boom") is True
    assert review_body_has_critical_high("## High\n- gate gap") is True


def test_review_body_has_critical_high_ignores_none_sections():
    assert review_body_has_critical_high("### Critical\nNone.\n### High\n- none") is False


def test_review_body_has_critical_high_handles_empty_and_clean_bodies():
    assert review_body_has_critical_high("") is False
    assert review_body_has_critical_high(None) is False
    assert review_body_has_critical_high("## Summary\nLooks good, shipping it.") is False


def test_review_body_empty_section_followed_by_heading_is_clean():
    # "### Critical" with no content before the next heading → empty → clean.
    assert review_body_has_critical_high("### Critical\n### Medium\n- minor") is False


# --- CLI end-to-end against a fixture PR JSON --------------------------------

import assess_merge_readiness as amr  # noqa: E402


_FIXTURE_GREEN_PR = {
    "mergeable": "MERGEABLE",
    "reviewDecision": "APPROVED",
    "baseRefName": "main",
    "changedFiles": 2,
    "additions": 40,
    "deletions": 5,
    "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "SUCCESS"}],
    "reviews": [
        {
            "author": {"login": "operator"},
            "state": "APPROVED",
            "commit": {"oid": "deadbeef"},
            "body": "### Critical\nNone.\n### High\nNone.\nLGTM.",
            "submittedAt": "2026-06-30T01:00:00Z",
        }
    ],
    "headRefOid": "deadbeef",
}


def _run_cli(monkeypatch, capsys, fixture, argv, cfg):
    monkeypatch.setattr(amr, "default_gh_run", lambda args: fixture)
    # main() imports load_config lazily from engineering_work_loop_config; patch
    # that module's symbol so no real config file is read.
    import engineering_work_loop_config as ewlc

    monkeypatch.setattr(ewlc, "load_config", lambda path: cfg)
    monkeypatch.setattr(sys, "argv", argv)
    try:
        amr.main()
    except SystemExit as exc:
        code = exc.code
    else:  # pragma: no cover - main always exits
        code = None
    return code, json.loads(capsys.readouterr().out)


def test_cli_end_to_end_merge_verdict(monkeypatch, capsys):
    argv = [
        "assess_merge_readiness.py", "--repo", "o/r", "--pr", "7",
        "--risk-tier", "auto", "--loop-ac-passed",
        "--config", "ignored.yaml", "--json",
    ]
    cfg = {"github_user": "operator", "pr": {"merge_policy": {"enabled": True, "dry_run": False}}}
    code, out = _run_cli(monkeypatch, capsys, _FIXTURE_GREEN_PR, argv, cfg)
    assert code == 0
    assert out["action"] == MERGE
    assert out["dry_run"] is False
    assert out["policy"]["method"] == "merge"


def test_cli_end_to_end_block_unrelated_reviewer(monkeypatch, capsys):
    fixture = dict(_FIXTURE_GREEN_PR)
    fixture["reviews"] = [
        {
            "author": {"login": "someone-else"},
            "state": "APPROVED",
            "commit": {"oid": "deadbeef"},
            "body": "",
            "submittedAt": "2026-06-30T01:00:00Z",
        }
    ]
    argv = [
        "assess_merge_readiness.py", "--repo", "o/r", "--pr", "7",
        "--risk-tier", "auto", "--loop-ac-passed",
        "--config", "ignored.yaml", "--json",
    ]
    cfg = {"github_user": "operator", "pr": {"merge_policy": {"enabled": True, "dry_run": False}}}
    code, out = _run_cli(monkeypatch, capsys, fixture, argv, cfg)
    assert code == 10  # BLOCK exit code
    assert out["action"] == BLOCK
    assert out["reason"] == REASON_NOT_REVIEWED
