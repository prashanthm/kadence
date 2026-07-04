"""Tests for report_gate.py — force-skill-use + diff-vs-claim (v2)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from report_gate import gate, parse_claimed_files, parse_skill_used  # noqa: E402


def _skills_dir(tmp_path, *skills):
    d = tmp_path / "skills"
    for s in skills:
        (d / s).mkdir(parents=True)
        (d / s / "SKILL.md").write_text("x", encoding="utf-8")
    return d


REPORT_TMPL = """# Work Fix Report

## Work item

| Field | Value |
|-------|-------|
| Work item type | `feature` |
| **Skill used** (required) | `{skill}` |
| Source issue | `o/r#1` — t |

## Diff summary

| File | Change |
|------|--------|
{files}
"""


def _report(skill="implement", files=("scripts/foo.py",)):
    rows = "\n".join(f"| `{f}` | edit |" for f in files)
    return REPORT_TMPL.format(skill=skill, files=rows)


def test_parse_skill_used():
    assert parse_skill_used(_report(skill="implement")) == "implement"


def test_parse_skill_used_rejects_placeholder():
    assert parse_skill_used(_report(skill="<skill slug>")) is None


def test_gate_blocks_missing_skill_field(tmp_path):
    report = "# Work Fix Report\n\n| Field | Value |\n|--|--|\n| Work item type | `fix` |\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("Skill used" in r for r in reasons)


def test_gate_blocks_nonexistent_skill(tmp_path):
    reasons = gate(_report(skill="made-up-skill"), _skills_dir(tmp_path, "implement"),
                   check_diff=False)
    assert any("non-existent skill" in r for r in reasons)


def test_gate_passes_valid_skill_no_diff(tmp_path):
    reasons = gate(_report(skill="implement"), _skills_dir(tmp_path, "implement"),
                   check_diff=False)
    assert reasons == []


# --- PII guard: no local filesystem paths may reach a public PR ---

def test_gate_blocks_macos_home_path(tmp_path):
    report = _report() + "\n| Clone path | `/Users/alice/projects/repo` |\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("PII" in r for r in reasons)


def test_gate_blocks_linux_home_path(tmp_path):
    report = _report() + "\nworktree at /home/bob/.local/share/ai-sdlc/worktrees/x\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("PII" in r for r in reasons)


def test_gate_blocks_windows_user_path(tmp_path):
    win_path = "C:" + "\\" + "Users" + "\\" + "carol" + "\\" + "repo"
    report = _report() + "| Clone | `" + win_path + "` |\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("PII" in r for r in reasons)


def test_gate_blocks_worktree_tilde_path(tmp_path):
    # Active namespace (kadence) worktree path must be scrubbed.
    report = _report() + "\nworktree: ~/.local/share/kadence/worktrees/repo/1\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("PII" in r for r in reasons)


def test_gate_blocks_legacy_ai_sdlc_tilde_path(tmp_path):
    # Legacy 'ai-sdlc' state path stays blocked too (defense-in-depth: reports
    # authored on the old layout, or with KADENCE_NAMESPACE=ai-sdlc, must not leak).
    report = _report() + "\nworktree: ~/.local/share/ai-sdlc/worktrees/repo/1\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("PII" in r for r in reasons)


def test_gate_allows_repo_relative_paths(tmp_path):
    # repo-relative verify commands + files (in the diff/AC tables, NOT as markdown
    # links) must NOT trip the PII or relative-link guards.
    report = _report(files=("scripts/loop_check.py", "specs/x/spec.md"))
    report += "\n| AC-1 | ok | `python3 scripts/loop_check.py issue-closed 1` | 0 |\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert reasons == []


# --- cross-repo relative-link guard: an issue/PR body must use absolute refs ---

def test_gate_blocks_relative_dotdot_link(tmp_path):
    report = _report() + "\n> Part of epic: [saa-agents](../epics/saa-agents.md)\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("relative markdown link" in r for r in reasons)


def test_gate_blocks_bare_docdir_link(tmp_path):
    report = _report() + "\nSee [ADR-014](adrs/adr-014-routing.md) for the decision.\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert any("relative markdown link" in r for r in reasons)


def test_gate_allows_absolute_issue_ref_and_permalink(tmp_path):
    # owner/repo#N refs and full permalinks are the correct cross-repo form.
    report = _report()
    report += "\nEpic: prashanthm/product-workspace#348\n"
    report += "Doc: [saa-agents](https://github.com/prashanthm/product-workspace/blob/abc123/initiatives/x/epics/saa-agents.md)\n"
    reasons = gate(report, _skills_dir(tmp_path, "implement"), check_diff=False)
    assert reasons == []


def test_parse_claimed_files():
    r = _report(files=("scripts/a.py", "docs/b.md"))
    assert parse_claimed_files(r) == ["scripts/a.py", "docs/b.md"]


def _git_repo(tmp_path):
    import subprocess as sp
    sp.run(["git", "init", "-q", str(tmp_path)], check=True)
    sp.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    sp.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "base.txt").write_text("x")
    sp.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    sp.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "base"], check=True)
    return tmp_path


def test_gate_blocks_claimed_file_not_in_diff(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    skills = _skills_dir(tmp_path, "implement")
    # Claim a file that was never changed.
    report = _report(skill="implement", files=("scripts/never-touched.py",))
    reasons = gate(report, skills, cwd=str(repo), base="HEAD", check_diff=True)
    assert any("not present in git diff" in r for r in reasons)


def test_gate_passes_when_claimed_file_is_in_diff(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    skills = _skills_dir(tmp_path, "implement")
    # Actually change the claimed file.
    (repo / "scripts").mkdir()
    (repo / "scripts" / "real.py").write_text("print('hi')\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    report = _report(skill="implement", files=("scripts/real.py",))
    reasons = gate(report, skills, cwd=str(repo), base="HEAD", check_diff=True)
    assert reasons == []
