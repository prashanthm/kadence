"""Tests for loop_events append-only JSONL event log (v2 instrumentation)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json  # noqa: E402

from loop_events import (  # noqa: E402
    append_event,
    events_path,
    read_events,
    summarize,
)


def test_append_writes_one_jsonl_line_per_event(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "run1", "discover", events_dir=d)
    append_event("o/r", "run1", "publish", outcome="pr", issue=42, events_dir=d)
    path = events_path("o/r", d)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    # each line is valid JSON with the required fields
    for line in lines:
        ev = json.loads(line)
        assert ev["repo"] == "o/r"
        assert ev["run_id"] == "run1"
        assert "ts" in ev and "action" in ev


def test_append_is_append_only(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "run1", "discover", events_dir=d)
    first = events_path("o/r", d).read_text(encoding="utf-8")
    append_event("o/r", "run1", "classify", events_dir=d)
    second = events_path("o/r", d).read_text(encoding="utf-8")
    # earlier content is preserved verbatim (append-only, never rewritten)
    assert second.startswith(first)


def test_unset_fields_are_omitted(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "run1", "discover", events_dir=d)
    ev = read_events("o/r", d)[0]
    # optional fields not passed must not appear
    assert "issue" not in ev
    assert "exit_code" not in ev
    assert "skill_used" not in ev


def test_repo_slug_is_filename_safe(tmp_path):
    d = str(tmp_path)
    append_event("prashanthm/product-workspace", "run1", "discover", events_dir=d)
    path = events_path("prashanthm/product-workspace", d)
    assert path.name == "prashanthm__product-workspace.jsonl"
    assert path.exists()


def test_read_events_filters_by_run_id(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "runA", "discover", events_dir=d)
    append_event("o/r", "runB", "discover", events_dir=d)
    assert len(read_events("o/r", d)) == 2
    assert len(read_events("o/r", d, run_id="runA")) == 1


def test_read_events_skips_malformed_lines(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "run1", "discover", events_dir=d)
    with events_path("o/r", d).open("a", encoding="utf-8") as fh:
        fh.write("not json\n")
    # malformed line skipped, good line still read
    assert len(read_events("o/r", d)) == 1


def test_summary_counts_only_pr_as_delivered(tmp_path):
    # The anti-reward-hack accounting: metadata-only does NOT count as delivered.
    d = str(tmp_path)
    append_event("o/r", "r1", "publish", outcome="pr", events_dir=d)
    append_event("o/r", "r2", "publish", outcome="metadata", events_dir=d)
    append_event("o/r", "r3", "block", outcome="blocked", events_dir=d)
    s = summarize(read_events("o/r", d))
    assert s["delivered_prs"] == 1
    assert s["metadata_only"] == 1
    assert s["blocked"] == 1


def test_summary_counts_verify_pass_fail(tmp_path):
    d = str(tmp_path)
    append_event("o/r", "r1", "verify", ac_id="AC-1", exit_code=0, events_dir=d)
    append_event("o/r", "r1", "verify", ac_id="AC-2", exit_code=1, events_dir=d)
    s = summarize(read_events("o/r", d))
    assert s["verify_pass"] == 1
    assert s["verify_fail"] == 1
    assert s["issues_touched"] == 0  # no issue numbers were set


def test_summary_empty_when_no_events(tmp_path):
    s = summarize(read_events("o/r", str(tmp_path)))
    assert s["events"] == 0
    assert s["delivered_prs"] == 0
