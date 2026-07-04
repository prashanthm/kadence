#!/usr/bin/env python3
"""Append-only structured event log for the engineering work loop (v2).

Every loop action emits one JSONL line to ``~/.local/share/<namespace>/events/<repo>.jsonl``.
This makes loop behaviour observable without mining transcripts and is the substrate
for the anti-reward-hack checks (independent verify, diff-vs-claim): outcomes are
recorded here, not inferred from an agent's self-report.

Design constraints (match the rest of scripts/): stdlib only, no PyYAML, append-only
(never rewrite a line), safe to call from any loop stage.

CLI:
  loop_events.py append --repo <owner/repo> --run-id <id> --action <a> [--issue N]
      [--work-type T] [--risk-tier R] [--skill S] [--ac-id AC-1] [--verify-cmd C]
      [--exit-code N] [--outcome O] [--note TEXT] [--events-dir DIR]
  loop_events.py summary --repo <owner/repo> [--run-id <id>] [--events-dir DIR]

``summary`` aggregates by outcome (pr / metadata / blocked / rejected / none) so the
weekly report can read real telemetry instead of computing markdown-status drift.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_registry import app_namespace

# Canonical vocabulary. Kept small and explicit so the summary and downstream
# report never have to guess. Unknown values are allowed (recorded verbatim) but
# these are the ones the loop should emit.
ACTIONS = (
    "discover",
    "classify",
    "worktree_acquire",
    "skill_invoked",
    "implement",
    "verify",          # one per AC item, carries ac_id + verify_cmd + exit_code
    "publish",         # carries outcome: pr | metadata | none
    "block",           # carries outcome: blocked | rejected
    "worktree_release",
)
OUTCOMES = ("pr", "metadata", "none", "blocked", "rejected")

DEFAULT_EVENTS_DIR = f"~/.local/share/{app_namespace()}/events"


def expand_path(p: str) -> str:
    """Expand ~ and env vars (mirrors engineering_work_loop_config.expand_path)."""
    return os.path.expandvars(os.path.expanduser(p))


def _repo_slug(repo: str) -> str:
    """owner/repo -> owner__repo, safe as a filename."""
    return repo.replace("/", "__").replace("..", "_")


def events_path(repo: str, events_dir: str | None = None) -> Path:
    base = Path(expand_path(events_dir or DEFAULT_EVENTS_DIR))
    return base / f"{_repo_slug(repo)}.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_event(
    repo: str,
    run_id: str,
    action: str,
    *,
    issue: int | None = None,
    work_type: str | None = None,
    risk_tier: str | None = None,
    skill_used: str | None = None,
    ac_id: str | None = None,
    verify_cmd: str | None = None,
    exit_code: int | None = None,
    outcome: str | None = None,
    note: str | None = None,
    events_dir: str | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    """Append one event as a single JSONL line. Returns the event dict.

    Append-only: opens with mode 'a' and writes exactly one line. Never rewrites
    existing content, so concurrent loop stages cannot corrupt earlier events.
    """
    event: dict[str, Any] = {
        "ts": ts or _utc_now_iso(),
        "run_id": run_id,
        "repo": repo,
        "action": action,
    }
    # Only include set fields — keeps lines compact and the schema self-describing.
    for key, val in (
        ("issue", issue),
        ("work_type", work_type),
        ("risk_tier", risk_tier),
        ("skill_used", skill_used),
        ("ac_id", ac_id),
        ("verify_cmd", verify_cmd),
        ("exit_code", exit_code),
        ("outcome", outcome),
        ("note", note),
    ):
        if val is not None:
            event[key] = val

    path = events_path(repo, events_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return event


def read_events(
    repo: str, events_dir: str | None = None, run_id: str | None = None
) -> list[dict[str, Any]]:
    path = events_path(repo, events_dir)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                # A malformed line should not sink the whole summary; skip it.
                continue
            if run_id is not None and ev.get("run_id") != run_id:
                continue
            out.append(ev)
    return out


def summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll events up into counts the weekly report consumes.

    Crucially, 'delivered work' = publish events with outcome 'pr' ONLY. A
    'metadata' outcome (the old evidence-free closeout) is counted separately and
    does NOT count as delivered — this is the anti-reward-hack accounting.
    """
    by_outcome: dict[str, int] = {}
    by_action: dict[str, int] = {}
    verify_pass = 0
    verify_fail = 0
    runs: set[str] = set()
    issues: set[int] = set()

    for ev in events:
        action = ev.get("action", "unknown")
        by_action[action] = by_action.get(action, 0) + 1
        if ev.get("run_id"):
            runs.add(ev["run_id"])
        if isinstance(ev.get("issue"), int):
            issues.add(ev["issue"])
        outcome = ev.get("outcome")
        if outcome:
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        if action == "verify" and isinstance(ev.get("exit_code"), int):
            if ev["exit_code"] == 0:
                verify_pass += 1
            else:
                verify_fail += 1

    delivered = by_outcome.get("pr", 0)
    return {
        "events": len(events),
        "runs": len(runs),
        "issues_touched": len(issues),
        "delivered_prs": delivered,
        "metadata_only": by_outcome.get("metadata", 0),
        "blocked": by_outcome.get("blocked", 0),
        "rejected": by_outcome.get("rejected", 0),
        "verify_pass": verify_pass,
        "verify_fail": verify_fail,
        "by_outcome": by_outcome,
        "by_action": by_action,
    }


def _cmd_append(args: argparse.Namespace) -> int:
    ev = append_event(
        args.repo,
        args.run_id,
        args.action,
        issue=args.issue,
        work_type=args.work_type,
        risk_tier=args.risk_tier,
        skill_used=args.skill,
        ac_id=args.ac_id,
        verify_cmd=args.verify_cmd,
        exit_code=args.exit_code,
        outcome=args.outcome,
        note=args.note,
        events_dir=args.events_dir,
    )
    print(json.dumps(ev, sort_keys=True))
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    events = read_events(args.repo, args.events_dir, run_id=args.run_id)
    print(json.dumps(summarize(events), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Engineering work loop event log (append-only JSONL).")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="Append one event.")
    a.add_argument("--repo", required=True, help="owner/repo")
    a.add_argument("--run-id", required=True)
    a.add_argument("--action", required=True, help=f"one of {', '.join(ACTIONS)} (others allowed)")
    a.add_argument("--issue", type=int)
    a.add_argument("--work-type")
    a.add_argument("--risk-tier")
    a.add_argument("--skill")
    a.add_argument("--ac-id")
    a.add_argument("--verify-cmd")
    a.add_argument("--exit-code", type=int)
    a.add_argument("--outcome", help=f"one of {', '.join(OUTCOMES)} (others allowed)")
    a.add_argument("--note")
    a.add_argument("--events-dir")
    a.set_defaults(func=_cmd_append)

    s = sub.add_parser("summary", help="Aggregate events by outcome/action.")
    s.add_argument("--repo", required=True, help="owner/repo")
    s.add_argument("--run-id", help="Limit to a single run.")
    s.add_argument("--events-dir")
    s.set_defaults(func=_cmd_summary)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
