#!/usr/bin/env python3
"""Publish gate for the Work Fix Report (v2 force-skill-use + diff-vs-claim).

Runs before `gh pr create` / on the PR body. Rejects a report that:
  1. omits the required **Skill used** field, or names a skill that does not exist
     under skills/ — forcing the agent to actually route through a skill, not
     freelance;
  2. claims changed files in its Diff summary that are NOT present in the branch's
     `git diff` — the agent cannot claim work it did not do; and
  3. contains a local filesystem path (PII) — an absolute ``/Users/<name>/...``,
     ``/home/<name>/...``, a Windows ``C:\\Users\\<name>\\...`` path, a ``~`` home
     path, or a worktree/clone path. The report is published to a public PR; the
     operator's username and private paths must never leak; and
  4. contains a **relative markdown link** (``](../epics/x.md)``, ``](adrs/x.md)``).
     An issue/PR body is not a repo file, so a relative link 404s — worse when doc
     text is copied verbatim across repos. Cross-repo references must be ABSOLUTE:
     ``owner/repo#N`` issue refs or full ``https://`` permalinks.

This gate makes each of these impossible to publish, not just discouraged.

Principle: the agent proposes; the deterministic gate disposes. Exit 0 = publishable,
non-zero = blocked (with a reason on stderr).

CLI:
  report_gate.py --report-file PATH --skills-dir DIR [--cwd REPO] [--base REF]
  report_gate.py --report-file PATH --skills-dir DIR --skip-diff   # skill check only
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_skill_used(report: str) -> str | None:
    """Extract the required `Skill used` field value from the report table."""
    m = re.search(r"\|\s*\*\*?Skill used\*\*?[^|]*\|\s*`?([^`|]+?)`?\s*\|", report, re.I)
    if not m:
        return None
    val = m.group(1).strip()
    # Reject an unfilled placeholder (e.g. "<skill slug ...>").
    if not val or val.startswith("<") or val.lower() in {"—", "-", "n/a", "none"}:
        return None
    return val


def parse_claimed_files(report: str) -> list[str]:
    """Extract file paths from the Diff summary table (first column, backticked)."""
    files: list[str] = []
    section = re.search(r"##\s*Diff summary\s*(.*?)(?:\n##\s|\Z)", report, re.S | re.I)
    if not section:
        return files
    for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|", section.group(1), re.M):
        path = m.group(1).strip()
        if path and "/" in path or path.endswith((".py", ".md", ".yml", ".yaml", ".sh", ".txt", ".json")):
            files.append(path)
    return files


def skill_exists(skill: str, skills_dir: Path) -> bool:
    """A skill exists if skills/<slug>/SKILL.md is present."""
    return (skills_dir / skill / "SKILL.md").exists()


# Local-path / PII patterns that must never appear in a published report.
_PII_PATTERNS = (
    re.compile(r"/Users/[^\s/`'\"]+"),          # macOS home: /Users/<name>
    re.compile(r"/home/[^\s/`'\"]+"),           # Linux home: /home/<name>
    re.compile(r"[A-Za-z]:\\Users\\[^\s\\`'\"]+"),  # Windows: C:\Users\<name>
    re.compile(r"~/\.local/share/ai-sdlc\b"),   # a worktree/state path
    re.compile(r"\.local/share/ai-sdlc/worktrees\b"),
)


def find_pii_paths(report: str) -> list[str]:
    """Return distinct local-filesystem path snippets found in the report (PII)."""
    hits: list[str] = []
    seen: set[str] = set()
    for pat in _PII_PATTERNS:
        for m in pat.finditer(report):
            frag = m.group(0)
            if frag not in seen:
                seen.add(frag)
                hits.append(frag)
    return hits


# Relative markdown links resolve against the *rendering file's* path in its repo.
# An issue/PR body is not a repo file, so a relative link (`](../epics/x.md)`,
# `](adrs/x.md)`, `](./x.md)`) 404s — worse when the body is a doc copied verbatim
# across repos (the exact defect that broke feature issues). Cross-repo references
# must be ABSOLUTE: `owner/repo#N` issue refs or full https:// permalinks.
_REL_LINK = re.compile(
    r"\]\(\s*("
    r"\.\.?/[^)\s]+"          # ../foo  or ./foo
    r"|(?:epics|adrs|features|research|tasks|specs)/[^)\s]+\.md"  # bare doc-dir/…md
    r")\s*\)"
)


def find_relative_links(report: str) -> list[str]:
    """Return distinct relative markdown link targets in the report (cross-repo rot)."""
    hits: list[str] = []
    seen: set[str] = set()
    for m in _REL_LINK.finditer(report):
        frag = m.group(1)
        if frag not in seen:
            seen.add(frag)
            hits.append(frag)
    return hits


def git_changed_files(cwd: str, base: str) -> set[str]:
    proc = subprocess.run(
        ["git", "-C", cwd, "diff", "--name-only", base],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        # Fall back to unstaged+staged diff if the base ref is unknown.
        proc = subprocess.run(
            ["git", "-C", cwd, "diff", "--name-only", "HEAD"],
            capture_output=True, text=True,
        )
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def gate(
    report: str,
    skills_dir: Path,
    *,
    cwd: str | None = None,
    base: str = "origin/main",
    check_diff: bool = True,
) -> list[str]:
    """Return a list of rejection reasons (empty = publishable)."""
    reasons: list[str] = []

    skill = parse_skill_used(report)
    if not skill:
        reasons.append("missing required 'Skill used' field")
    elif not skill_exists(skill, skills_dir):
        reasons.append(f"'Skill used' names a non-existent skill: {skill}")

    # PII guard — no local filesystem paths may reach a public PR.
    pii = find_pii_paths(report)
    if pii:
        reasons.append(
            "local filesystem path(s) present (PII — strip the absolute prefix, keep "
            "the command repo-relative): " + ", ".join(pii)
        )

    # Cross-repo link guard — an issue/PR body must reference other docs/issues by
    # ABSOLUTE ref (owner/repo#N or a full https:// permalink), never a relative
    # markdown link (which 404s because a body is not a repo file).
    rel = find_relative_links(report)
    if rel:
        reasons.append(
            "relative markdown link(s) in a body that renders across repos (use "
            "owner/repo#N or a full permalink): " + ", ".join(rel)
        )

    if check_diff and cwd:
        claimed = parse_claimed_files(report)
        if claimed:
            changed = git_changed_files(cwd, base)
            missing = [f for f in claimed if f not in changed]
            if missing:
                reasons.append(
                    "claimed files not present in git diff: " + ", ".join(missing)
                )
    return reasons


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Work Fix Report publish gate.")
    p.add_argument("--report-file", required=True, type=argparse.FileType("r"))
    p.add_argument("--skills-dir", required=True, help="path to skills/")
    p.add_argument("--cwd", help="repo/worktree root for the git diff check")
    p.add_argument("--base", default="origin/main", help="base ref for diff-vs-claim")
    p.add_argument("--skip-diff", action="store_true", help="skill check only")
    args = p.parse_args(argv)

    report = args.report_file.read()
    reasons = gate(
        report,
        Path(args.skills_dir),
        cwd=args.cwd,
        base=args.base,
        check_diff=not args.skip_diff,
    )
    if reasons:
        for r in reasons:
            print(f"BLOCK: {r}", file=sys.stderr)
        return 1
    print("report gate: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
