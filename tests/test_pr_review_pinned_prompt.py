"""Tests for pr_review_pinned_prompt.resolve_candidate."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pr_review_pinned_prompt import resolve_candidate  # noqa: E402


def test_resolve_candidate_passes_pr_number_to_discover(monkeypatch):
    captured: dict[str, object] = {}

    def fake_discover(cfg, gh_run=None, force_pr=None):
        captured["force_pr"] = force_pr
        return {
            "candidate": {
                "owner": "your-org",
                "repo": "edi-mcp-server",
                "number": 187,
                "head_short": "cf34cbb",
                "title": "example",
            }
        }

    monkeypatch.setattr("pr_review_pinned_prompt.discover", fake_discover)

    cand = resolve_candidate({}, "187")

    assert cand["number"] == 187
    assert captured["force_pr"] == 187
