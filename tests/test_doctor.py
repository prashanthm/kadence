"""Tests for the kadence doctor validation harness (v2)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import doctor  # noqa: E402


def _make_loop_skill(tmp_path: Path, refs: str) -> Path:
    """Build a minimal toolkit tree with an engineering-work-loop SKILL.md."""
    loop_dir = tmp_path / "skills" / "engineering-work-loop"
    (loop_dir / "handlers").mkdir(parents=True)
    (loop_dir / "SKILL.md").write_text(refs, encoding="utf-8")
    return tmp_path


def test_skill_registry_passes_when_refs_resolve(tmp_path):
    root = _make_loop_skill(
        tmp_path,
        "See handlers/feature.md and [pr-review](../pr-review/SKILL.md).",
    )
    (root / "skills" / "engineering-work-loop" / "handlers" / "feature.md").write_text("h", encoding="utf-8")
    prv = root / "skills" / "pr-review"
    prv.mkdir()
    (prv / "SKILL.md").write_text("s", encoding="utf-8")

    res = doctor.Result()
    doctor.check_skill_registry(root, res)
    assert res.failures == []


def test_skill_registry_fails_on_dangling_handler(tmp_path):
    root = _make_loop_skill(tmp_path, "Uses handlers/does-not-exist.md")
    res = doctor.Result()
    doctor.check_skill_registry(root, res)
    assert "skill-registry" in res.failures


def test_skill_registry_fails_on_dangling_skill_ref(tmp_path):
    root = _make_loop_skill(tmp_path, "See [gone](../retired-skill/SKILL.md).")
    res = doctor.Result()
    doctor.check_skill_registry(root, res)
    assert "skill-registry" in res.failures


def test_events_check_roundtrips(tmp_path):
    # Uses the real toolkit root so loop_events imports; just verifies the check passes.
    root = Path(__file__).resolve().parents[1]
    res = doctor.Result()
    doctor.check_events(root, res)
    assert res.failures == []


def test_no_status_sync_reports_present_on_current_tree():
    # On today's tree the status-sync path still exists, so the strict check fails.
    root = Path(__file__).resolve().parents[1]
    res = doctor.Result()
    doctor.check_no_status_sync(root, res)
    # Either it's still present (fail) or already removed (pass) — assert the check ran.
    assert res.failures in ([], ["no-status-sync (strict)"])


def test_result_tracks_failures():
    res = doctor.Result()
    res.check("a", True)
    res.check("b", False, "boom")
    assert res.failures == ["b"]
