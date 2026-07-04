#!/usr/bin/env python3
"""Parse GitHub closing-keyword issue references from a PR body.

Used by project-status-on-pr.yml on integration branches (phase2, release
branches), where GitHub does NOT populate closingIssuesReferences (that only
works for default-branch PRs) — so the workflow must parse `Closes #N` itself.

CRITICAL: ignore closing keywords inside inline code spans (`...`) and fenced
code blocks (```...```). A PR that only *describes* the mechanism (e.g. a doc PR
whose body says "`Closes #122` was inert") must NOT close that issue. GitHub's
own parser likewise does not honor closing keywords inside code spans. Skipping
this is exactly how PR #131's body-mention of `Closes #122` falsely set #122 to
Done.

Reads the body from --body-file or stdin; prints one issue number per line.

  parse_closing_issues.py --body-file body.md
  gh pr view N --json body -q .body | parse_closing_issues.py
"""
from __future__ import annotations

import argparse
import re
import sys

# GitHub's supported closing keywords: close/closes/closed, fix/fixes/fixed,
# resolve/resolves/resolved. Matched at a word boundary, keyword [: ] #<number>.
_CLOSING = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#(\d+)",
    re.IGNORECASE,
)
_FENCED = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`]*`")


def strip_code(body: str) -> str:
    """Remove fenced code blocks then inline code spans, so closing keywords
    inside code are not honored (matches GitHub's own behavior)."""
    body = _FENCED.sub("", body)
    body = _INLINE.sub("", body)
    return body


def parse_closing_issue_numbers(body: str) -> list[str]:
    """Distinct issue numbers referenced by a real (non-code) closing keyword."""
    cleaned = strip_code(body or "")
    seen: dict[str, None] = {}
    for m in _CLOSING.finditer(cleaned):
        seen.setdefault(m.group(1), None)
    return list(seen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse Closes #N from a PR body (ignoring code spans).")
    ap.add_argument("--body-file", help="path to the PR body; omit to read stdin")
    args = ap.parse_args(argv)
    body = open(args.body_file, encoding="utf-8").read() if args.body_file else sys.stdin.read()
    for num in parse_closing_issue_numbers(body):
        print(num)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
