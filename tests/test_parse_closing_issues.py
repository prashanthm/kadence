"""Tests for parse_closing_issues.py — Closes-keyword parsing that ignores code."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from parse_closing_issues import parse_closing_issue_numbers as parse  # noqa: E402


def test_plain_closes_matches():
    assert parse("Closes #122") == ["122"]


def test_all_keyword_forms():
    body = "closes #1\nFixes #2\nresolved #3\nCLOSE #4\nCloses: #5"
    assert parse(body) == ["1", "2", "3", "4", "5"]


def test_ignores_inline_code_span():
    # A body that only DESCRIBES the mechanism must NOT close the issue — this is
    # the PR #131 false-positive that set #122 to Done.
    body = "GitHub only registers `Closes #122` for default-branch PRs."
    assert parse(body) == []


def test_ignores_fenced_code_block():
    body = "See the workflow:\n```\nCloses #99 is inert\n```\nnothing to close."
    assert parse(body) == []


def test_real_closing_survives_alongside_code_mention():
    body = (
        "This PR builds the feature.\n"
        "Note: `Closes #99` in a doc is inert.\n"
        "\n"
        "Closes #122\n"
    )
    assert parse(body) == ["122"]


def test_refs_does_not_match():
    assert parse("Refs #5 and see #6") == []


def test_dedup_and_multiple():
    assert parse("Closes #7, fixes #7, resolves #8") == ["7", "8"]


def test_empty_and_none():
    assert parse("") == []
    assert parse(None) == []  # type: ignore[arg-type]
