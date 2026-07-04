"""Tests for bootstrap_initiative_agents_md.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bootstrap_initiative_agents_md import (  # noqa: E402
    bootstrap_initiative_agents_md,
    build_initiative_agents_md,
    extract_purpose_sentence,
    insert_routing_row,
)

ROOT_AGENTS_MD_TEMPLATE = """# AGENTS.md

Guidance for AI agents.

## Routing table

| Initiative | Purpose | INDEX.md |
|---|---|---|
| [`ai-native-development`](initiatives/ai-native-development/initiative.md) | Build a reusable AI-SDLC toolkit. | [`initiatives/ai-native-development/INDEX.md`](initiatives/ai-native-development/INDEX.md) |
| [`subsurface-agentic-ai`](initiatives/subsurface-agentic-ai/initiative.md) | Source-agnostic agentic AI over subsurface data. | [`initiatives/subsurface-agentic-ai/INDEX.md`](initiatives/subsurface-agentic-ai/INDEX.md) |

## Conventions

Some other prose that must not be touched.
"""

WELL_FORMED_INITIATIVE_MD = """# Zzz Test Lifecycle Verification

## Status

Proposed

## Why

This initiative validates the lifecycle wiring end to end. It exists only as scratch verification.

## What

Deliver a throwaway capability used solely to prove the bootstrap script works correctly. It is deleted
after verification.

## Success Criteria

- [ ] Verification complete.
"""


# --- extract_purpose_sentence ---


def test_extract_purpose_sentence_returns_first_sentence_of_why():
    result = extract_purpose_sentence(WELL_FORMED_INITIATIVE_MD, "zzz-test-lifecycle-verification")
    assert result == "This initiative validates the lifecycle wiring end to end."


def test_extract_purpose_sentence_missing_why_raises():
    text = "# Title\n\n## What\n\nSomething.\n"
    with pytest.raises(ValueError, match="missing or empty '## Why'"):
        extract_purpose_sentence(text, "some-slug")


def test_extract_purpose_sentence_empty_why_raises():
    text = "# Title\n\n## Why\n\n## What\n\nSomething.\n"
    with pytest.raises(ValueError, match="missing or empty '## Why'"):
        extract_purpose_sentence(text, "some-slug")


# --- build_initiative_agents_md ---


def test_build_initiative_agents_md_missing_why_raises():
    text = "# Title\n\n## What\n\nSomething.\n"
    with pytest.raises(ValueError, match="missing or empty '## Why'"):
        build_initiative_agents_md(text, "some-slug")


def test_build_initiative_agents_md_missing_what_raises():
    text = "# Title\n\n## Why\n\nBecause reasons.\n"
    with pytest.raises(ValueError, match="missing or empty '## What'"):
        build_initiative_agents_md(text, "some-slug")


def test_build_initiative_agents_md_seeded_content():
    content = build_initiative_agents_md(
        WELL_FORMED_INITIATIVE_MD, "zzz-test-lifecycle-verification"
    )
    assert "zzz-test-lifecycle-verification" in content
    assert "## What this initiative delivers" in content
    assert "Deliver a throwaway capability used solely to prove the bootstrap script works" in content
    assert "It is deleted\nafter verification." in content
    assert "## Where things live" in content
    # No leftover template scaffolding markers.
    assert "<!-- AGENT" not in content
    assert "<!-- REPLACE" not in content


def test_build_initiative_agents_md_purpose_sentence_matches_extract_purpose_sentence():
    content = build_initiative_agents_md(
        WELL_FORMED_INITIATIVE_MD, "zzz-test-lifecycle-verification"
    )
    purpose = extract_purpose_sentence(
        WELL_FORMED_INITIATIVE_MD, "zzz-test-lifecycle-verification"
    )
    assert purpose in content


# --- insert_routing_row ---


def test_insert_routing_row_appends_new_row_last():
    new_text, inserted = insert_routing_row(
        ROOT_AGENTS_MD_TEMPLATE, "zzz-test-lifecycle-verification", "A throwaway test initiative."
    )
    assert inserted is True
    old_rows = [
        line
        for line in ROOT_AGENTS_MD_TEMPLATE.splitlines()
        if line.startswith("| [`")
    ]
    new_rows = [line for line in new_text.splitlines() if line.startswith("| [`")]
    assert len(new_rows) == len(old_rows) + 1
    assert new_rows[:-1] == old_rows
    assert "zzz-test-lifecycle-verification" in new_rows[-1]
    assert "[`initiatives/zzz-test-lifecycle-verification/INDEX.md`]" in new_rows[-1]
    # Every other line (prose before/after the table) is untouched.
    assert "Some other prose that must not be touched." in new_text
    assert new_text.startswith("# AGENTS.md")


def test_insert_routing_row_existing_row_is_noop():
    new_text, inserted = insert_routing_row(
        ROOT_AGENTS_MD_TEMPLATE, "subsurface-agentic-ai", "Different purpose text."
    )
    assert inserted is False
    assert new_text == ROOT_AGENTS_MD_TEMPLATE


def test_insert_routing_row_missing_table_raises():
    text = "# AGENTS.md\n\nNo routing table here.\n"
    with pytest.raises(ValueError, match="routing table"):
        insert_routing_row(text, "some-slug", "Purpose.")


def test_insert_routing_row_escapes_pipe_in_purpose():
    new_text, inserted = insert_routing_row(
        ROOT_AGENTS_MD_TEMPLATE, "pipe-test-initiative", "Option A | Option B"
    )
    assert inserted is True
    pipe_row = next(
        line for line in new_text.splitlines() if "pipe-test-initiative" in line
    )
    assert "Option A \\| Option B" in pipe_row
    assert "Option A | Option B" not in pipe_row


# --- bootstrap_initiative_agents_md orchestration ---


def _make_workspace(tmp_path: Path, slug: str = "zzz-test-lifecycle-verification") -> Path:
    root = tmp_path / "product-workspace"
    root.mkdir()
    (root / "AGENTS.md").write_text(ROOT_AGENTS_MD_TEMPLATE, encoding="utf-8")
    initiative_dir = root / "initiatives" / slug
    initiative_dir.mkdir(parents=True)
    (initiative_dir / "initiative.md").write_text(WELL_FORMED_INITIATIVE_MD, encoding="utf-8")
    return root


def test_bootstrap_first_run_creates(tmp_path):
    root = _make_workspace(tmp_path)
    status = bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification")
    assert status == {"agents_md": "created", "routing_row": "appended"}
    agents_md_path = root / "initiatives" / "zzz-test-lifecycle-verification" / "AGENTS.md"
    assert agents_md_path.is_file()
    assert "zzz-test-lifecycle-verification" in (root / "AGENTS.md").read_text(encoding="utf-8")


def test_bootstrap_second_run_is_idempotent(tmp_path):
    root = _make_workspace(tmp_path)
    bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification")

    agents_md_path = root / "initiatives" / "zzz-test-lifecycle-verification" / "AGENTS.md"
    root_agents_md_path = root / "AGENTS.md"
    agents_md_before = agents_md_path.read_text(encoding="utf-8")
    root_before = root_agents_md_path.read_text(encoding="utf-8")

    status = bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification")

    assert status == {"agents_md": "skipped", "routing_row": "skipped"}
    assert agents_md_path.read_text(encoding="utf-8") == agents_md_before
    assert root_agents_md_path.read_text(encoding="utf-8") == root_before
    # No duplicate row: exactly one occurrence of the slug's link target in the table.
    assert root_before.count("[`initiatives/zzz-test-lifecycle-verification/INDEX.md`]") == 1


def test_bootstrap_force_overwrites_agents_md_but_routing_row_stays_skipped(tmp_path):
    root = _make_workspace(tmp_path)
    bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification")

    agents_md_path = root / "initiatives" / "zzz-test-lifecycle-verification" / "AGENTS.md"
    agents_md_path.write_text("# stale content\n", encoding="utf-8")

    status = bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification", force=True)

    assert status == {"agents_md": "overwritten", "routing_row": "skipped"}
    assert "stale content" not in agents_md_path.read_text(encoding="utf-8")
    assert "## What this initiative delivers" in agents_md_path.read_text(encoding="utf-8")


def test_bootstrap_cli_end_to_end(tmp_path):
    root = _make_workspace(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_initiative_agents_md.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--product-workspace-root",
            str(root),
            "--initiative-slug",
            "zzz-test-lifecycle-verification",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "AGENTS.md: created" in result.stdout
    assert "routing table row: appended" in result.stdout
    assert (root / "initiatives" / "zzz-test-lifecycle-verification" / "AGENTS.md").is_file()


def test_bootstrap_missing_input_raises(tmp_path):
    root = _make_workspace(tmp_path)

    with pytest.raises(ValueError, match="no initiative.md found"):
        bootstrap_initiative_agents_md(root, "does-not-exist")

    (root / "AGENTS.md").unlink()
    with pytest.raises(ValueError, match="no root AGENTS.md found"):
        bootstrap_initiative_agents_md(root, "zzz-test-lifecycle-verification")
