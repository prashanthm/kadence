"""Tests for detect_affected_initiatives.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from detect_affected_initiatives import affected_initiatives  # noqa: E402

_SCRIPT = str(Path(__file__).resolve().parents[1] / "scripts" / "detect_affected_initiatives.py")


# --- affected_initiatives ---


def test_affected_initiatives_matches_epics_path():
    result = affected_initiatives(["initiatives/foo/epics/bar.md"])
    assert result == ["initiatives/foo"]


def test_affected_initiatives_matches_features_path():
    result = affected_initiatives(["initiatives/foo/features/bar.md"])
    assert result == ["initiatives/foo"]


def test_affected_initiatives_matches_adrs_path():
    result = affected_initiatives(["initiatives/foo/adrs/adr-001-x.md"])
    assert result == ["initiatives/foo"]


def test_affected_initiatives_ignores_product_brief():
    result = affected_initiatives(["initiatives/foo/product-brief.md"])
    assert result == []


def test_affected_initiatives_ignores_index_md_itself():
    result = affected_initiatives(["initiatives/foo/INDEX.md"])
    assert result == []


def test_affected_initiatives_ignores_paths_outside_initiatives():
    result = affected_initiatives(["scripts/generate_initiative_index.py", "README.md"])
    assert result == []


def test_affected_initiatives_ignores_initiative_md():
    result = affected_initiatives(["initiatives/foo/initiative.md"])
    assert result == []


def test_affected_initiatives_multiple_initiatives_sorted():
    result = affected_initiatives(
        [
            "initiatives/zeta/epics/z.md",
            "initiatives/alpha/features/a.md",
            "initiatives/zeta/adrs/adr-002-y.md",
        ]
    )
    assert result == ["initiatives/alpha", "initiatives/zeta"]


def test_affected_initiatives_dedupes_within_one_initiative():
    result = affected_initiatives(
        [
            "initiatives/foo/epics/a.md",
            "initiatives/foo/epics/b.md",
            "initiatives/foo/features/c.md",
        ]
    )
    assert result == ["initiatives/foo"]


def test_affected_initiatives_empty_input():
    assert affected_initiatives([]) == []


def test_affected_initiatives_blank_lines_ignored():
    result = affected_initiatives(["", "   ", "initiatives/foo/epics/a.md", ""])
    assert result == ["initiatives/foo"]


def test_affected_initiatives_strips_whitespace():
    result = affected_initiatives(["  initiatives/foo/epics/a.md  "])
    assert result == ["initiatives/foo"]


def test_affected_initiatives_nested_slug_like_prefix_not_confused():
    # A slug containing hyphens/underscores is still one path segment.
    result = affected_initiatives(["initiatives/subsurface-agentic-ai/epics/e01.md"])
    assert result == ["initiatives/subsurface-agentic-ai"]


# --- CLI ---


def test_cli_reads_stdin():
    proc = subprocess.run(
        [sys.executable, _SCRIPT],
        input="initiatives/foo/epics/a.md\ninitiatives/bar/features/b.md\n",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == ["initiatives/bar", "initiatives/foo"]


def test_cli_reads_changed_files_file(tmp_path):
    changed = tmp_path / "changed.txt"
    changed.write_text("initiatives/foo/adrs/adr-001-x.md\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, _SCRIPT, "--changed-files-file", str(changed)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == ["initiatives/foo"]


def test_cli_empty_stdin_prints_nothing_and_exits_zero():
    proc = subprocess.run(
        [sys.executable, _SCRIPT],
        input="",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
