"""Wiring tests for risk-based auto-land shadow mode (e04-f10-t03).

These cover the loop-facing guarantees: shadow mode logs a decision but performs
no GitHub writes, the disabled default is a no-op, and the docs (prompt + SKILL)
describe the gated step.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from assess_merge_readiness import (  # noqa: E402
    MERGE,
    BLOCK,
    MergePolicy,
    PrFacts,
    assess,
    decision_log_line,
    should_write_to_github,
)

ROOT = Path(__file__).resolve().parents[1]


def _green() -> PrFacts:
    return PrFacts(
        risk_tier="auto", loop_ac_passed=True, mergeable="MERGEABLE",
        ci_state="pass", review_approved=True, changes_requested=False,
        base_ref="main", changed_files=2, additions=50, deletions=5,
    )


def test_shadow_mode_logs_would_merge_and_writes_nothing():
    policy = MergePolicy(enabled=True, dry_run=True)
    verdict = assess(_green(), policy)
    assert verdict.action == MERGE
    line = decision_log_line("your-org/x", 7, verdict, policy)
    assert line.startswith("WOULD MERGE")
    # the loop must NOT touch GitHub in shadow mode
    assert should_write_to_github(verdict, policy) is False


def test_shadow_mode_logs_would_block_with_reason():
    policy = MergePolicy(enabled=True, dry_run=True)
    facts = PrFacts(**{**_green().__dict__, "ci_state": "fail"})
    verdict = assess(facts, policy)
    assert verdict.action == BLOCK
    line = decision_log_line("your-org/x", 7, verdict, policy)
    assert line.startswith("WOULD BLOCK")
    assert "ci_failed" in line
    assert should_write_to_github(verdict, policy) is False


def test_disabled_policy_is_noop_no_writes():
    policy = MergePolicy()  # enabled=False (default)
    verdict = assess(_green(), policy)
    assert verdict.action == BLOCK  # policy_disabled
    assert should_write_to_github(verdict, policy) is False


def test_live_merge_verdict_permits_writes():
    policy = MergePolicy(enabled=True, dry_run=False)
    verdict = assess(_green(), policy)
    assert verdict.action == MERGE
    assert should_write_to_github(verdict, policy) is True
    assert decision_log_line("your-org/x", 7, verdict, policy) == "MERGE your-org/x#7"


def test_live_block_verdict_forbids_merge_writes_but_allows_label():
    # A BLOCK in live mode still must not merge; should_write_to_github gates the
    # ready/merge path, the loop applies the label separately on BLOCK.
    policy = MergePolicy(enabled=True, dry_run=False)
    facts = PrFacts(**{**_green().__dict__, "mergeable": "CONFLICTING"})
    verdict = assess(facts, policy)
    assert verdict.action == BLOCK
    # writes are permitted in live mode, but the caller only merges on MERGE
    assert should_write_to_github(verdict, policy) is True
    assert verdict.action != MERGE


# --- docs wiring guarantees -------------------------------------------------


def test_prompt_documents_gated_merge_step():
    # The build prompt is now implement-loop.prompt.md (engineering-work-loop is the family).
    prompt = (ROOT / ".github/prompts/implement-loop.prompt.md").read_text()
    assert "merge_policy" in prompt
    assert "assess_merge_readiness.py" in prompt
    # default-off / never-merge guarantee still present
    assert "Never merge" in prompt or "never merge" in prompt


def test_skill_references_assess_merge_readiness():
    skill = (ROOT / "skills/engineering-work-loop/SKILL.md").read_text()
    assert "assess_merge_readiness" in skill
    assert "merge_policy" in skill


def test_config_example_default_off():
    cfg = (ROOT / "skills/engineering-work-loop/config.example.yaml").read_text()
    assert "merge_policy" in cfg
    assert "enabled: false" in cfg
