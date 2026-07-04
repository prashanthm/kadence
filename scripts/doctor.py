#!/usr/bin/env python3
"""``ai-sdlc doctor`` — prove the loop, tests, and skill registry still run (v2).

A single smoke command run in CI and after any skill/loop change. Exits non-zero on
the first regression so a change that breaks the loop or the skill wiring fails the PR.

Checks (each prints PASS/FAIL and contributes to the exit code):
  1. tests            — pytest over tests/ is green
  2. engine-imports   — the ported loop-engine modules import cleanly
  3. skill-registry   — every handler/skill the loop references resolves to a file;
                        no dangling reference to a retired/renamed skill
  4. events           — loop_events append+summary roundtrips (instrumentation alive)

v2 cut-assertions (no M18 section in the report; issue-sync absent) are added as those
cuts land — see --strict. They are OFF by default so doctor is green on today's tree.

Usage:
  doctor.py [--skip-tests] [--strict] [--root <toolkit-root>]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Loop-engine modules that must import cleanly (the ~1,668-LoC moat we port to v2).
ENGINE_MODULES = (
    "loop_check",
    "verify_loop_ac",
    "classify_work_item",
    "discover_engineering_work_candidates",
    "engineering_work_loop_config",
    "loop_events",
    "loop_firing_lock",
    # self-hosted loops (pr-review-loop, pr-comment-fix-loop) — no shared engine, so
    # their own entry points must be checked explicitly (a missing-import bug in
    # pr_fix_submit.report_push sat undetected here until a live firing hit it).
    "discover_pr_review_candidates",
    "pr_review_loop_cron",
    "discover_pr_fix_candidates",
    "pr_fix_cron",
    "pr_fix_submit",
)


def _toolkit_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    # scripts/doctor.py -> toolkit root is the parent of scripts/
    return Path(__file__).resolve().parents[1]


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
        if not ok:
            self.failures.append(name)


def check_tests(root: Path, res: Result) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    detail = tail[-1] if tail else f"exit {proc.returncode}"
    res.check("tests", ok, detail)


def check_engine_imports(root: Path, res: Result) -> None:
    # Only check modules actually present. During the skeleton stage the engine
    # is not yet ported; a missing module is a not-yet-here, not a regression.
    scripts_dir = root / "scripts"
    present = [m for m in ENGINE_MODULES if (scripts_dir / f"{m}.py").exists()]
    if not present:
        res.check("engine-imports", True, "no engine modules yet (skeleton) — skipped")
        return
    code = (
        "import sys; sys.path.insert(0, %r)\n" % str(scripts_dir)
        + "".join(f"import {m}\n" for m in present)
        + "print('ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    ok = proc.returncode == 0
    detail = (
        f"{len(present)}/{len(ENGINE_MODULES)} present module(s) import"
        if ok
        else (proc.stderr.strip().splitlines() or ["import error"])[-1]
    )
    res.check("engine-imports", ok, detail)


def check_skill_registry(root: Path, res: Result) -> None:
    """Every handler/skill the loop references must resolve to an existing file.

    Catches the classic 'merged/renamed a skill, forgot a caller' regression that
    would otherwise only surface at loop runtime.
    """
    loop_skill = root / "skills" / "engineering-work-loop" / "SKILL.md"
    missing: list[str] = []
    if not loop_skill.exists():
        # Not yet ported (skeleton stage). Once the loop skill lands, this check
        # enforces that every handler/skill it names resolves.
        res.check("skill-registry", True, "no loop skill yet (skeleton) — skipped")
        return
    text = loop_skill.read_text(encoding="utf-8")

    # handler refs: handlers/<name>.md relative to the loop skill dir
    for ref in sorted(set(re.findall(r"handlers/[a-z0-9-]+\.md", text))):
        if not (loop_skill.parent / ref).exists():
            missing.append(ref)

    # skill refs: ../<skill>/SKILL.md relative to the loop skill dir
    for ref in sorted(set(re.findall(r"\.\./[a-z0-9-]+/SKILL\.md", text))):
        if not (loop_skill.parent / ref).resolve().exists():
            missing.append(ref)

    res.check(
        "skill-registry",
        not missing,
        "all references resolve" if not missing else f"dangling: {', '.join(missing)}",
    )


def check_events(root: Path, res: Result) -> None:
    scripts = str(root / "scripts")
    with tempfile.TemporaryDirectory() as d:
        code = (
            "import sys; sys.path.insert(0, %r)\n" % scripts
            + "from loop_events import append_event, read_events, summarize\n"
            + "append_event('o/r','run','publish',outcome='pr',events_dir=%r)\n" % d
            + "s=summarize(read_events('o/r',%r))\n" % d
            + "assert s['delivered_prs']==1, s\n"
            + "print('ok')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
    ok = proc.returncode == 0
    res.check("events", ok, "append+summary roundtrip" if ok else proc.stderr.strip()[-120:])


def check_no_status_sync(root: Path, res: Result) -> None:
    """v2 strict: the markdown status-sync path must be gone.

    OFF by default (--strict) because the cut lands in a later v2 feature.
    """
    sync = root.parent / ".github" / "scripts" / "sync_status.py"
    issue_sync = root / "skills" / "issue-sync"
    absent = not sync.exists() and not issue_sync.exists()
    res.check(
        "no-status-sync (strict)",
        absent,
        "sync_status.py + issue-sync removed"
        if absent
        else "status-sync still present (expected until the cut lands)",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ai-sdlc doctor — loop/tests/registry smoke.")
    p.add_argument("--root", help="Toolkit root (default: parent of scripts/).")
    p.add_argument("--skip-tests", action="store_true", help="Skip the pytest run (fast checks only).")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Also assert v2 cuts have landed (no status-sync). Off by default.",
    )
    args = p.parse_args(argv)

    root = _toolkit_root(args.root)
    res = Result()

    if not args.skip_tests:
        check_tests(root, res)
    check_engine_imports(root, res)
    check_skill_registry(root, res)
    check_events(root, res)
    if args.strict:
        check_no_status_sync(root, res)

    print()
    if res.failures:
        print(f"doctor: FAIL ({len(res.failures)} check(s): {', '.join(res.failures)})")
        return 1
    print("doctor: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
