#!/usr/bin/env python3
"""Set a GitHub Project (v2) Status for one issue/PR — mechanical moves only.

The reproducible, version-controlled replacement for GitHub Projects' UI-only
built-in workflows (which have no GraphQL API to enable). Driven by the
event-driven Action templates under `templates/.github/workflows/`, it sets a
content item's Status to one of the **mechanical** values and **refuses to
overwrite a human-gate status** — so it can never bypass an approval gate.

Mechanical (allowed): Backlog, In review, Done. (Plus In Progress if a project
chooses, but the shipped Actions use only the three above.)

Human gates (NEVER set, NEVER overwritten): Ready for Spec, Approved,
Ready for Dev. If an item is already in one of these, this script leaves it
alone — the board move is the gate, owned by a human.

Exception — a merge is authoritative: `--allow-gate-override` lets the terminal
`Done` status (and only `Done`) finalize a card even from a human gate. Used by
the PR-merged path: once work is merged, the "is this approved to work on" gate
is moot, so the card must reach Done. All other directions still respect gates.

Usage:
  set_project_status.py --org <org> --project <N> --content-url <issue/pr url> --status "<Status>"
    [--only-if-current "<a>,<b>"]    # set only when current Status is one of these (optional)
    [--allow-gate-override]          # let Done finalize a card even from a human gate (merge path)

Exit 0 on success or intentional no-op (gate-protected / not on board); non-zero
only on an unexpected API error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# Statuses a human owns — automation must never set or overwrite these.
GATE_STATUSES = frozenset({"Ready for Spec", "Approved", "Ready for Dev"})
# Statuses the mechanical automation is allowed to set.
MECHANICAL_STATUSES = frozenset({"Backlog", "In Progress", "In review", "Done"})


def gh_graphql(query: str, **variables) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        # -F coerces ints/bools; -f forces string
        flag = "-F" if isinstance(v, (int, bool)) else "-f"
        args += [flag, f"{k}={v}"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh graphql failed")
    return json.loads(proc.stdout or "{}")


def resolve_project(org: str, number: int) -> tuple[str, str, dict[str, str]]:
    """Return (project_id, status_field_id, {option_name: option_id})."""
    q = (
        "query($org:String!,$num:Int!){ organization(login:$org){ projectV2(number:$num){"
        " id field(name:\"Status\"){ ... on ProjectV2SingleSelectField { id options{ id name } } } } } }"
    )
    d = gh_graphql(q, org=org, num=number)
    p = (((d.get("data") or {}).get("organization") or {}).get("projectV2") or {})
    field = p.get("field") or {}
    options = {o["name"]: o["id"] for o in field.get("options") or []}
    return p.get("id"), field.get("id"), options


def find_item(project_id: str, content_url: str) -> tuple[str | None, str | None]:
    """Return (item_id, current_status_name) for the content URL, or (None, None)."""
    q = (
        "query($id:ID!,$cursor:String){ node(id:$id){ ... on ProjectV2 { items(first:100, after:$cursor){"
        " pageInfo{ hasNextPage endCursor }"
        " nodes{ id content{ ... on Issue { url } ... on PullRequest { url } }"
        " fieldValueByName(name:\"Status\"){ ... on ProjectV2ItemFieldSingleSelectValue { name } } } } } } }"
    )
    cursor = None
    while True:
        d = gh_graphql(q, id=project_id, **({"cursor": cursor} if cursor else {}))
        items = (((d.get("data") or {}).get("node") or {}).get("items") or {})
        for node in items.get("nodes") or []:
            if (node.get("content") or {}).get("url") == content_url:
                cur = (node.get("fieldValueByName") or {}).get("name")
                return node["id"], cur
        page = items.get("pageInfo") or {}
        if page.get("hasNextPage"):
            cursor = page.get("endCursor")
        else:
            return None, None


def set_status(project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    q = (
        "mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue(input:{"
        " projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){ projectV2Item{ id } } }"
    )
    gh_graphql(q, p=project_id, i=item_id, f=field_id, o=option_id)


def main() -> int:
    ap = argparse.ArgumentParser(description="Set a Project Status (mechanical moves only)")
    ap.add_argument("--org", required=True)
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--content-url", required=True, help="issue or PR html_url")
    ap.add_argument("--status", required=True, help="target Status (mechanical only)")
    ap.add_argument("--only-if-current", default="", help="comma-list; set only if current in it")
    ap.add_argument(
        "--allow-gate-override",
        action="store_true",
        help="let the terminal 'Done' status finalize a card even from a human gate (PR-merged path)",
    )
    ap.add_argument(
        "--spec-merge-promote",
        action="store_true",
        help=(
            "permit exactly the 'Ready for Spec' -> 'Ready for Dev' promotion, and only from a merged "
            "spec PR. Merging the spec IS the human plan-approval, so this one gate-to-gate move is "
            "authorized. No other gate transition is allowed by this flag."
        ),
    )
    ap.add_argument(
        "--allow-dev-review",
        action="store_true",
        help=(
            "permit exactly 'Ready for Dev' -> 'In review' — a code PR became ready for its feature, so "
            "work has started. This is a FORWARD move off the gate (not overwriting an unstarted gate); "
            "no other transition is affected."
        ),
    )
    args = ap.parse_args()

    target = args.status
    # Narrow exception: the spec-merge promotion is a gate-to-gate move (Ready for Spec ->
    # Ready for Dev) authorized by a human merging the spec PR. It bypasses the
    # "mechanical only" refusal below but is still constrained to that single transition
    # in the gate-handling block.
    spec_promote = args.spec_merge_promote and target == "Ready for Dev"
    if target not in MECHANICAL_STATUSES and not spec_promote:
        sys.stderr.write(
            f"refusing: '{target}' is not a mechanical status "
            f"(allowed: {sorted(MECHANICAL_STATUSES)}). Human gates are never set by automation.\n"
        )
        return 2

    try:
        project_id, field_id, options = resolve_project(args.org, args.project)
        if not project_id or not field_id:
            sys.stderr.write("could not resolve project / Status field\n")
            return 2
        if target not in options:
            sys.stderr.write(f"Status option '{target}' not on the board (run setup-project-board.sh)\n")
            return 2
        item_id, current = find_item(project_id, args.content_url)
        if not item_id:
            print(f"no-op: {args.content_url} is not on project {args.project}")
            return 0
        # Never overwrite a human gate — except two human-authorized transitions:
        #  (a) a merge finalizing a card to Done (the "approved to work on" gate is moot);
        #  (b) a merged SPEC PR promoting Ready for Spec -> Ready for Dev (merging the
        #      spec IS the plan approval). Both are triggered by a human merge, not by the
        #      loop deciding on its own.
        if current in GATE_STATUSES:
            if args.allow_gate_override and target == "Done":
                print(f"override: merge finalizes '{current}' -> Done")
            elif args.allow_dev_review and current == "Ready for Dev" and target == "In review":
                print("dev-review: 'Ready for Dev' -> 'In review' (a code PR became ready)")
            elif spec_promote and current == "Ready for Spec":
                print("spec-merge: 'Ready for Spec' -> 'Ready for Dev' (plan approved by merge)")
            else:
                print(f"no-op: '{current}' is a human gate — automation leaves it untouched")
                return 0
        # Optional conditional set.
        gate = [s.strip() for s in args.only_if_current.split(",") if s.strip()]
        if gate and current not in gate:
            print(f"no-op: current '{current}' not in {gate}")
            return 0
        if current == target:
            print(f"no-op: already '{target}'")
            return 0
        set_status(project_id, item_id, field_id, options[target])
        print(f"set {args.content_url} -> {target} (was {current!r})")
        return 0
    except RuntimeError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
