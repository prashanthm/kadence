#!/usr/bin/env python3
"""Detect which `initiatives/<slug>` directories are affected by a set of changed files.

Used by `templates/.github/workflows/index-regenerate.yml` to scope the INDEX.md drift
check to only the initiative(s) whose `epics/`, `features/`, or `adrs/` subtree actually
changed in a push/PR — not a full-repo regen on every push (epic AC-1 / feature AC-1).

Pure and dependency-free: takes a list of repo-relative path strings (typically
`git diff --name-only <base>...<head>` output) and returns the distinct, sorted
`initiatives/<slug>` prefixes touched under `epics/`, `features/`, or `adrs/`. No
filesystem or network access, so it is trivially unit-testable without a git checkout.

A changed path outside `initiatives/<slug>/{epics,features,adrs}/` — e.g.
`initiatives/<slug>/product-brief.md`, `initiatives/<slug>/INDEX.md` itself, or any file
outside `initiatives/` entirely — does not mark that initiative as affected. Only the
indexed content (epics, features, ADRs) should trigger a regeneration check.

Usage:
  git diff --name-only origin/main...HEAD | detect_affected_initiatives.py
  detect_affected_initiatives.py --changed-files-file changed.txt

Prints one affected `initiatives/<slug>` path per line, sorted. Empty output (exit 0) if
none match — no affected initiatives is a valid, non-error outcome.
"""
from __future__ import annotations

import argparse
import re
import sys

_AFFECTED_RE = re.compile(r"^(initiatives/[^/]+)/(?:epics|features|adrs)/")


def affected_initiatives(changed_files: list[str]) -> list[str]:
    """Distinct, sorted `initiatives/<slug>` prefixes touched under epics/, features/,
    or adrs/ in `changed_files`. Paths not matching that shape are ignored.
    """
    matched: set[str] = set()
    for path in changed_files:
        path = path.strip()
        if not path:
            continue
        m = _AFFECTED_RE.match(path)
        if m:
            matched.add(m.group(1))
    return sorted(matched)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect which initiatives/<slug> dirs are affected by changed files."
    )
    parser.add_argument(
        "--changed-files-file",
        help="path to a file with one changed-file path per line; reads stdin if omitted",
    )
    args = parser.parse_args(argv)

    if args.changed_files_file:
        with open(args.changed_files_file, encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    for initiative in affected_initiatives(lines):
        print(initiative)
    return 0


if __name__ == "__main__":
    sys.exit(main())
