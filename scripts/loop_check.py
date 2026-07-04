#!/usr/bin/env python3
"""Argv-only Loop AC verify helpers (no shell metacharacters).

These subcommands replace shell pipelines in Loop AC verify commands so they pass
the auto-tier allowlist in verify_loop_ac.py, which forbids shell metacharacters
(`; | < > $ && ||`). Each subcommand runs from the current working directory (the
worktree) and exits 0 on success, non-zero on failure — the contract
verify_loop_ac.py checks.

Subcommands (v2 — the markdown-status/M18/milestone drift and diff-size tripwire
helpers are removed; feature sizing is a generation-time reasoning judgment, not a
mechanical gate, and Loop AC verifies BEHAVIOR only):
  - issue-closed <number>     -> assert a referenced issue is CLOSED
  - cmd-succeeds "<argv>"     -> behavioral check (inner cmd must exit 0)
  - cmd-fails "<argv>"        -> behavioral check (inner cmd must exit non-0)

The cmd-succeeds / cmd-fails helpers run an inner command **without a shell**
(argv split via shlex, `shell=False`), so an auto-tier Loop AC can assert that a
build/test/lint command passes — or that a red fixture deliberately fails —
without using the forbidden shell metacharacters. They are the verification
primitive for code tasks (e.g. "pytest passes", "the lint flags a bad import"),
which `test -f` / `grep` cannot express.

Add a new check by: (1) adding a cmd_<name> function following the exit-0/non-zero
contract, (2) registering it in main()'s subparsers. It is auto-allowed since the
`python3 scripts/loop_check.py` prefix is on the auto-tier allowlist.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys


def _run_argv(inner: str, cwd: str) -> int:
    """Run an inner command WITHOUT a shell (argv split), return its exit code.

    shlex.split + shell=False keeps the auto-tier no-shell guarantee: the inner
    string is tokenised, never interpreted by a shell, so metacharacters cannot
    inject. Returns 127 if the command is empty or cannot be parsed/started.
    """
    try:
        argv = shlex.split(inner)
    except ValueError as exc:
        sys.stderr.write(f"cannot parse command: {exc}\n")
        return 127
    if not argv:
        sys.stderr.write("empty inner command\n")
        return 127
    try:
        proc = subprocess.run(argv, cwd=cwd)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"cannot run command: {exc}\n")
        return 127
    return proc.returncode


def cmd_cmd_succeeds(args: argparse.Namespace) -> int:
    """Exit 0 iff the inner command (run without a shell) exits 0."""
    return 0 if _run_argv(args.inner, args.cwd) == 0 else 1


def cmd_cmd_fails(args: argparse.Namespace) -> int:
    """Exit 0 iff the inner command (run without a shell) exits non-zero.

    For 'red fixture' AC: proving a linter/check correctly REJECTS bad input.
    """
    return 0 if _run_argv(args.inner, args.cwd) != 0 else 1


def cmd_issue_closed(args: argparse.Namespace) -> int:
    """Exit 0 if the GitHub issue is CLOSED."""
    proc = subprocess.run(
        ["gh", "issue", "view", str(args.number), "--json", "state", "-q", ".state"],
        capture_output=True,
        text=True,
        cwd=args.cwd,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return 2
    return 0 if proc.stdout.strip().upper() == "CLOSED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop AC verify helpers")
    parser.add_argument("--cwd", default=".", help="working directory (worktree)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ok = sub.add_parser("cmd-succeeds")
    p_ok.add_argument("inner", help="inner command (argv-split, run without a shell)")
    p_ok.set_defaults(func=cmd_cmd_succeeds)

    p_fail = sub.add_parser("cmd-fails")
    p_fail.add_argument("inner", help="inner command (argv-split, run without a shell)")
    p_fail.set_defaults(func=cmd_cmd_fails)

    p_issue = sub.add_parser("issue-closed")
    p_issue.add_argument("number", type=int)
    p_issue.set_defaults(func=cmd_issue_closed)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
