"""Tests for pr_fix_submit.publish_now — regression for a missing import that made
every real publish crash with NameError: name 'report_push' is not defined (the
import was present for report_submit but report_push was never imported, even
though pr_fix_config defines both). This sat undetected because report_push is
only referenced inside a function body, so `import pr_fix_submit` alone succeeds;
the crash only fires when publish_now() actually runs, which is what this test
exercises directly."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pr_fix_submit as submit  # noqa: E402


def test_publish_now_does_not_crash_on_report_push_lookup(tmp_path, monkeypatch):
    draft = tmp_path / "draft.md"
    draft.write_text("DRAFT\n\nSome report body.\n", encoding="utf-8")

    worktree = tmp_path / "wt"
    worktree.mkdir()

    monkeypatch.setattr(
        submit, "subprocess",
        type("S", (), {"run": staticmethod(lambda *a, **k: None)}),
    )

    cfg = {
        "report": {"draft_path": str(tmp_path), "push": True},
        "git": {"worktree_root": str(tmp_path)},
    }

    # Must not raise NameError — this is the exact call path the crashed live
    # firing hit (pr_fix_cron.py -> publish_now -> report_push(cfg)).
    submit.publish_now(
        cfg,
        "your-org/subsurface-agentic-ai",
        136,
        draft,
        required=False,
        reason="approved_no_critical_high_fixes",
        reviewers=[],
        worktree_path=str(worktree),
    )


def test_report_push_is_importable_from_pr_fix_submit():
    # pr_fix_submit.publish_now calls report_push(cfg) directly (not via module
    # prefix) — it MUST be imported into this module's namespace, not just defined
    # in pr_fix_config.
    assert hasattr(submit, "report_push")
    assert submit.report_push({"report": {"push": True}}) is True
    assert submit.report_push({"report": {"push": False}}) is False
