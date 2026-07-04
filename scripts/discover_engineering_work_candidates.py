#!/usr/bin/env python3
"""Discover assignee work items eligible for the engineering work loop."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from classify_work_item import classify_issue
from engineering_work_loop_config import expand_path, load_config

GhRunner = Callable[[list[str]], Any]


def has_loop_ac(body: str) -> bool:
    """True if the issue body already carries a `## Loop AC` section.

    (v2) In v1 a missing Loop AC could be auto-synthesized for compliance issues via
    synthesize_loop_ac. That path is removed — the loop implements real code work
    whose Loop AC is authored in the task's spec, not synthesized from drift. If an
    issue lacks Loop AC and the loop requires it, the issue is skipped, not patched.
    """
    return bool(re.search(r"(?mi)^##\s+Loop AC\b", body))

SKIP_LABELS = frozenset({"loop-deferred", "loop-blocked", "loop-closeout-complete", "self-heal-pending"})


def default_gh_run(args: list[str]) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return json.loads(proc.stdout or "null")


def read_state_log(path: str) -> dict[str, dict[str, Any]]:
    """Map owner/repo#issue -> latest entry with fired_at."""
    p = Path(expand_path(path))
    latest: dict[str, dict[str, Any]] = {}
    if not p.exists():
        return latest
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = entry.get("key") or ""
        if not key:
            owner = entry.get("owner", "")
            repo = entry.get("repo", "")
            issue = entry.get("issue")
            if owner and repo and issue is not None:
                key = f"{owner}/{repo}#{issue}"
        if key:
            latest[key] = entry
    return latest


def label_names(issue: dict[str, Any]) -> set[str]:
    return {lbl.get("name", "").lower() for lbl in issue.get("labels") or []}


def discovery_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    d = cfg.get("discovery") or {}
    if not isinstance(d, dict):
        d = {}
    # (v2) synthesize_missing_loop_ac / writeback_loop_ac removed — no synthesis path.
    return {
        "require_loop_ac_on_issue": bool(d.get("require_loop_ac_on_issue", False)),
    }


def _parse_project_block(p: Any) -> dict[str, Any]:
    """Normalize a {org, number, status_gates} project block (robust to YAML quirks)."""
    if not isinstance(p, dict):
        p = {}
    gates = p.get("status_gates") or []
    if not isinstance(gates, list):
        gates = [gates]
    raw_number = p.get("number")
    try:
        number = int(raw_number) if raw_number not in (None, "", {}) else None
    except (TypeError, ValueError):
        number = None
    return {
        "org": str(p.get("org") or "") or None,
        "number": number,
        "status_gates": [str(g) for g in gates if g],
    }


def project_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    """Top-level Project-board Status gating config (the default for all repos).

    `status_gates` is the allow-list of Project Status values that make an issue
    loop-eligible (e.g. ["Ready for Dev"]). When empty/unset, Status gating is
    OFF and the loop behaves exactly as before (backward compatible).
    """
    return _parse_project_block(cfg.get("project") or {})


def repo_project_cfg(entry: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Effective Status gate for ONE repo: its repos[].project overrides the
    top-level project. This keeps gating **per-repo** — a repo whose issues live
    on a specific Project (e.g. subsurface-agentic-ai → its board) is gated by
    that board, while repos with no project block stay ungated even if another
    repo declares one. Without this, a single top-level project would gate every
    repo's issues against one board and fail-closed every issue not on it.
    """
    if isinstance(entry, dict) and entry.get("project") is not None:
        return _parse_project_block(entry.get("project") or {})
    return project_cfg(cfg)


def fetch_project_status_map(
    org: str, number: int, gh_run: GhRunner
) -> dict[str, str]:
    """Return {issue_url: status_name} for every issue linked in the org Project.

    Mirrors the standard GitHub Projects GraphQL shape. Returns {} on any error so a
    transient Project API failure surfaces as an empty map; the caller's gate then
    fails CLOSED (an un-mapped issue is skipped), never silently auto-passing.
    """
    query = (
        "query($org:String!,$number:Int!,$cursor:String){"
        " organization(login:$org){ projectV2(number:$number){ items(first:100, after:$cursor){"
        " pageInfo{ hasNextPage endCursor }"
        " nodes{ content{ ... on Issue { url } }"
        " fieldValues(first:20){ nodes{ ... on ProjectV2ItemFieldSingleSelectValue {"
        " name field{ ... on ProjectV2SingleSelectField { name } } } } } } } } } }"
    )
    out: dict[str, str] = {}
    cursor: str | None = None
    while True:
        args = [
            "api", "graphql",
            "-f", f"query={query}",
            "-F", f"org={org}",
            "-F", f"number={number}",
        ]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        try:
            data = gh_run(args)
        except RuntimeError:
            return {}
        proj = (((data or {}).get("data") or {}).get("organization") or {}).get("projectV2") or {}
        items = proj.get("items") or {}
        for node in items.get("nodes") or []:
            content = node.get("content") or {}
            url = content.get("url")
            if not url:
                continue
            status = ""
            for fv in (node.get("fieldValues") or {}).get("nodes") or []:
                field = fv.get("field") or {}
                if field.get("name") == "Status" and fv.get("name"):
                    status = fv["name"]
                    break
            out[url] = status
        page = items.get("pageInfo") or {}
        if page.get("hasNextPage"):
            cursor = page.get("endCursor")
        else:
            break
    return out


def status_gate_skip_reason(
    issue: dict[str, Any],
    status_map: dict[str, str] | None,
    gates: list[str],
) -> str | None:
    """Skip reason if the issue's Project Status is not in the gate allow-list.

    No-op when gating is off (no gates). When on: an issue not on the board, or in
    a Status outside `gates`, is skipped ('project_status_gated'). Fails CLOSED —
    an issue must be explicitly in an allowed Status to be picked up.
    """
    if not gates:
        return None
    url = issue.get("url") or ""
    current = (status_map or {}).get(url, "")
    if current in gates:
        return None
    return "project_status_gated"


def initiatives_subpath_for_repo(cfg: dict[str, Any], owner: str, repo: str) -> str:
    for entry in cfg.get("repos") or []:
        if entry.get("owner") == owner and entry.get("repo") == repo:
            return str(entry.get("initiatives_path") or "initiatives/ai-native-development")
    return "initiatives/ai-native-development"


def _validated_clone_path(raw: str) -> str:
    """Expand and sanity-check a clone path. clone_path comes from the operator's
    own config/overlay (trusted), but reject obvious traversal patterns so a
    fat-fingered relative '..' entry can't point the worktree outside intent
    (addresses review C2)."""
    expanded = expand_path(str(raw))
    if ".." in Path(expanded).parts:
        raise ValueError(f"clone_path must be an absolute path without '..': {raw!r}")
    return expanded


def clone_path_for_repo(cfg: dict[str, Any], owner: str, repo: str) -> str:
    """Local git clone for a repo: entry clone_path, else git.primary_clone."""
    for entry in cfg.get("repos") or []:
        if entry.get("owner") == owner and entry.get("repo") == repo:
            cp = entry.get("clone_path")
            if cp:
                return _validated_clone_path(str(cp))
    primary = (cfg.get("git") or {}).get("primary_clone", ".")
    return _validated_clone_path(str(primary))


def base_ref_for_repo(cfg: dict[str, Any], owner: str, repo: str) -> str:
    """The branch a new spec/implement worktree branch forks from for this repo.

    Effective base ref: entry base_ref overrides the top-level git.base_ref, which
    overrides the hardcoded default origin/main. Keeps this per-repo (a single
    config spans repos with different integration branches — e.g. one repo builds
    off phase2, another off main — rather than one top-level value governing every
    repo's worktrees, which would silently fork the wrong branch for any repo that
    isn't the one the top-level value was written for)."""
    for entry in cfg.get("repos") or []:
        if entry.get("owner") == owner and entry.get("repo") == repo:
            br = entry.get("base_ref")
            if br:
                return str(br)
    top_level = (cfg.get("git") or {}).get("base_ref")
    if top_level:
        return str(top_level)
    return "origin/main"


def cap_candidates_per_repo(
    pool: list[dict[str, Any]], per_repo_cap: int
) -> list[dict[str, Any]]:
    """Keep at most per_repo_cap items per (owner, repo), preserving order."""
    if per_repo_cap <= 0:
        return list(pool)
    counts: dict[tuple[str, str], int] = {}
    out: list[dict[str, Any]] = []
    for c in pool:
        key = (c.get("owner", ""), c.get("repo", ""))
        if counts.get(key, 0) >= per_repo_cap:
            continue
        counts[key] = counts.get(key, 0) + 1
        out.append(c)
    return out


def parse_priority_value(body: str) -> int:
    m = re.search(r"\*\*Priority:\*\*\s*(P\d+)", body, re.I)
    if not m:
        return 2
    token = m.group(1).upper()
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(token, 2)


def parse_due_date(body: str) -> date | None:
    m = re.search(r"\*\*Due date:\*\*\s*(\d{4}-\d{2}-\d{2})", body)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def is_overdue(body: str) -> bool:
    due = parse_due_date(body)
    if due is None:
        return False
    return due < date.today()


def cooldown_active(
    key: str,
    state: dict[str, dict[str, Any]],
    cooldown_hours: float,
) -> bool:
    entry = state.get(key)
    if not entry:
        return False
    fired = entry.get("fired_at") or entry.get("last_fired")
    if not fired:
        return False
    try:
        ts = datetime.fromisoformat(str(fired).replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    return delta.total_seconds() < cooldown_hours * 3600


def open_pr_refs_issue(
    owner: str,
    repo: str,
    issue_number: int,
    gh_run: GhRunner,
) -> bool:
    prs = gh_run(
        [
            "pr",
            "list",
            "--repo",
            f"{owner}/{repo}",
            "--state",
            "open",
            "--json",
            "number,title,body",
            "--limit",
            "100",
        ]
    )
    if not isinstance(prs, list):
        return False
    patterns = [
        re.compile(rf"\b(?:fixes|closes|resolves)\s+#%d\b" % issue_number, re.I),
        re.compile(rf"\b#{issue_number}\b"),
    ]
    for pr in prs:
        text = f"{pr.get('title', '')}\n{pr.get('body', '')}"
        if any(p.search(text) for p in patterns):
            return True
    return False


def skip_reason(
    issue: dict[str, Any],
    classification: dict[str, Any],
    cfg: dict[str, Any],
    owner: str,
    repo: str,
    state: dict[str, dict[str, Any]],
    gh_run: GhRunner,
) -> str | None:
    labels = label_names(issue)
    if labels & SKIP_LABELS:
        return "deferred_label"

    # Defense-in-depth: `discover_issues()` already filters via `gh issue list
    # --assignee @me`, but that trusts whatever gh identity the process happens
    # to run under. Re-check explicitly against the configured github_user so a
    # stray/misconfigured gh auth context can never surface an issue that was
    # never actually assigned to the loop operator — spec-loop/implement-loop
    # must not act on unassigned work.
    github_user = str(cfg.get("github_user") or "").strip()
    if github_user:
        assignee_logins = {
            str(a.get("login") or "").strip()
            for a in (issue.get("assignees") or [])
            if isinstance(a, dict)
        }
        if github_user not in assignee_logins:
            return "not_assigned_to_operator"

    work_type = classification.get("work_item_type", "unknown")
    enabled = {str(x).lower() for x in (cfg.get("enabled_work_types") or [])}
    if work_type not in enabled:
        return "work_type_disabled"

    tier = classification.get("risk_tier", "human-only")
    if tier == "human-only":
        return "human_only"
    if tier == "assist" and not cfg.get("process_assist", False):
        return "assist_disabled"

    number = int(issue["number"])
    key = f"{owner}/{repo}#{number}"
    if cooldown_active(key, state, float(cfg.get("cooldown_hours", 24))):
        return "cooldown"

    if open_pr_refs_issue(owner, repo, number, gh_run):
        return "open_pr_refs_issue"

    disc = discovery_cfg(cfg)
    body = issue.get("body") or ""
    if disc["require_loop_ac_on_issue"] and not has_loop_ac(body):
        # (v2) No synthesis — an issue without Loop AC is skipped, not patched.
        return "missing_loop_ac"

    return None


def priority_score(
    issue: dict[str, Any],
    classification: dict[str, Any],
) -> tuple[int, int, int]:
    """Lower sorts first: band, priority P0=0, overdue first."""
    body = issue.get("body") or ""
    work_type = classification.get("work_item_type", "")
    tier = classification.get("risk_tier", "human-only")
    priority = parse_priority_value(body)
    overdue = 0 if is_overdue(body) else 1

    # (v2) No compliance band — the loop implements real code work only.
    if work_type == "dependabot":
        band = 1
    elif work_type == "chore" and tier == "auto":
        band = 3
    elif work_type == "task" and tier == "auto":
        band = 4
    elif work_type == "feature" and tier == "auto":
        band = 5
    else:
        band = 9
    return (band, priority, overdue)


def discover_issues(
    cfg: dict[str, Any],
    gh_run: GhRunner,
    *,
    force_issue: int | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    state = read_state_log(str(cfg.get("state_log", "")))
    candidates: list[dict[str, Any]] = []

    # Project-board Status gate is resolved PER REPO (repos[].project overrides
    # the top-level project). Status maps are fetched lazily and cached by
    # (org, number) so a board shared by several repos is fetched once.
    status_map_cache: dict[tuple[str, int], dict[str, str]] = {}

    def status_map_for(p: dict[str, Any]) -> dict[str, str]:
        if not (p["status_gates"] and p["org"] and p["number"] is not None):
            return {}
        key = (p["org"], int(p["number"]))
        if key not in status_map_cache:
            status_map_cache[key] = fetch_project_status_map(p["org"], int(p["number"]), gh_run)
        return status_map_cache[key]

    for entry in cfg.get("repos") or []:
        owner = entry.get("owner", "")
        repo = entry.get("repo", "")
        if not owner or not repo:
            continue
        full = f"{owner}/{repo}"
        proj = repo_project_cfg(entry, cfg)
        status_map = status_map_for(proj)
        issues = gh_run(
            [
                "issue",
                "list",
                "--repo",
                full,
                "--assignee",
                "@me",
                "--state",
                "open",
                "--json",
                "number,title,body,labels,url,assignees",
                "--limit",
                "100",
            ]
        )
        if not isinstance(issues, list):
            continue
        for issue in issues:
            number = int(issue["number"])
            if force_issue is not None and number != force_issue:
                continue
            labels = [lbl.get("name", "") for lbl in issue.get("labels") or []]
            classification = classify_issue(
                issue.get("title", ""),
                issue.get("body") or "",
                labels,
            )
            reason = skip_reason(issue, classification, cfg, owner, repo, state, gh_run)
            if reason:
                continue
            if status_gate_skip_reason(issue, status_map, proj["status_gates"]):
                continue
            # (v2) No synthesis: the body is whatever the issue carries. skip_reason
            # already skips issues that require Loop AC but lack it.
            body = issue.get("body") or ""
            item = {
                "kind": "issue",
                "owner": owner,
                "repo": repo,
                "number": number,
                "title": issue.get("title", ""),
                "body": body,
                "classification": classification,
                "clone_path": clone_path_for_repo(cfg, owner, repo),
                "base_ref": base_ref_for_repo(cfg, owner, repo),
                "priority": priority_score(issue, classification),
            }
            candidates.append(item)

    candidates.sort(key=lambda c: (c["priority"], c["number"]))
    return candidates


def discover_dependabot_prs(
    cfg: dict[str, Any],
    gh_run: GhRunner,
) -> list[dict[str, Any]]:
    if "dependabot" not in {str(x).lower() for x in (cfg.get("enabled_work_types") or [])}:
        return []
    results: list[dict[str, Any]] = []
    for entry in cfg.get("repos") or []:
        owner = entry.get("owner", "")
        repo = entry.get("repo", "")
        if not owner or not repo:
            continue
        prs = gh_run(
            [
                "pr",
                "list",
                "--repo",
                f"{owner}/{repo}",
                "--state",
                "open",
                "--app",
                "dependabot",
                "--json",
                "number,title,headRefName,body",
                "--limit",
                "50",
            ]
        )
        if not isinstance(prs, list):
            continue
        for pr in prs:
            classification = {
                "work_item_type": "dependabot",
                "risk_tier": "auto",
            }
            results.append(
                {
                    "kind": "dependabot_pr",
                    "owner": owner,
                    "repo": repo,
                    "number": int(pr["number"]),
                    "title": pr.get("title", ""),
                    "head_ref": pr.get("headRefName", ""),
                    "classification": classification,
                    "clone_path": clone_path_for_repo(cfg, owner, repo),
                    "priority": (1, 1, 1),
                }
            )
    return results


def discover(
    cfg: dict[str, Any],
    *,
    force_issue: int | None = None,
    dry_run: bool = False,
    gh_run: GhRunner | None = None,
) -> dict[str, Any]:
    runner = gh_run or default_gh_run
    issues = discover_issues(cfg, runner, force_issue=force_issue, dry_run=dry_run)
    dependabot = discover_dependabot_prs(cfg, runner) if force_issue is None else []
    pool = issues + dependabot
    pool.sort(key=lambda c: (c["priority"], c["number"]))

    per_repo_cap = int(cfg.get("max_items_per_repo", 5))
    selected = cap_candidates_per_repo(pool, per_repo_cap)

    # Legacy global ceiling: honored only when an overlay sets it.
    global_cap = cfg.get("max_items_per_firing")
    if global_cap is not None:
        try:
            selected = selected[: int(global_cap)]
        except (TypeError, ValueError):
            pass

    return {
        "candidate": selected[0] if selected else None,
        "candidates": selected,
        "pool_size": len(pool),
        "skipped_count": len(pool) - len(selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover engineering work loop candidates")
    parser.add_argument("--config", required=True)
    parser.add_argument("--force-issue", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="classify only; no issue writeback")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    result = discover(cfg, force_issue=args.force_issue, dry_run=args.dry_run)
    if args.json:
        json.dump(result, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        cand = result.get("candidate")
        if cand:
            print(f"{cand['owner']}/{cand['repo']}#{cand['number']} ({cand['kind']})")
        else:
            print("no candidate")


if __name__ == "__main__":
    main()
