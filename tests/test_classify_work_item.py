"""Tests for classify_work_item.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from classify_work_item import classify_issue  # noqa: E402

# (v2) compliance-gap classification removed — the loop classifies real code work
# only (feature/task/chore/dependabot/fix). See assessments/kadence-v2.


def test_unknown_defaults_human_only():
    result = classify_issue("random task", "no loop ac here")
    assert result["risk_tier"] == "human-only"


def test_task_with_loop_ac_is_auto():
    body = (
        "**Work item type:** task\n**Risk tier:** auto\n\n"
        "## Loop AC\n- [ ] AC-1: x\n  - verify: `test -f foo`\n"
    )
    result = classify_issue("Feature: e01-f01-t01 — skeleton", body)
    assert result["work_item_type"] == "task"
    assert result["risk_tier"] == "auto"
    assert result["thresholds"] == {"max_files": 8, "max_lines": 300}


def test_task_without_loop_ac_defaults_assist():
    result = classify_issue("e01-f01-t01", "**Work item type:** task\n")
    assert result["work_item_type"] == "task"
    assert result["risk_tier"] == "assist"


def test_task_by_label():
    result = classify_issue("anything", "no meta", labels=["task"])
    assert result["work_item_type"] == "task"


def test_feature_still_classifies():
    result = classify_issue("anything", "**Work item type:** feature\n")
    assert result["work_item_type"] == "feature"
    assert result["thresholds"] == {"max_files": 10, "max_lines": 500}
