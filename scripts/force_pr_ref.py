#!/usr/bin/env python3
"""Parse --force-pr values: number, GitHub URL, or owner/repo#N."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

_GH_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)
_OWNER_REPO_PULL = re.compile(
    r"^(?P<owner>[^/]+)/(?P<repo>[^/#]+)/pull/(?P<number>\d+)$",
    re.IGNORECASE,
)
_OWNER_REPO_HASH = re.compile(
    r"^(?P<owner>[^/]+)/(?P<repo>[^/#]+)#(?P<number>\d+)$",
    re.IGNORECASE,
)
_NUMBER_ONLY = re.compile(r"^\d+$")


@dataclass(frozen=True)
class ForcePrRef:
    number: int
    owner: str | None = None
    repo: str | None = None

    @property
    def pinned(self) -> bool:
        return bool(self.owner and self.repo)


def parse_force_pr(value: str | int | None) -> ForcePrRef | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    m = _GH_URL.search(raw) or _OWNER_REPO_PULL.match(raw) or _OWNER_REPO_HASH.match(raw)
    if m:
        number = int(m.group("number"))
        if number < 1:
            raise ValueError(f"invalid --force-pr {raw!r}; PR number must be >= 1")
        return ForcePrRef(
            number=number,
            owner=m.group("owner"),
            repo=m.group("repo"),
        )
    if _NUMBER_ONLY.match(raw):
        number = int(raw)
        if number < 1:
            raise ValueError(f"invalid --force-pr {raw!r}; PR number must be >= 1")
        return ForcePrRef(number=number)
    raise ValueError(
        f"invalid --force-pr {raw!r}; use N, owner/repo#N, or "
        "https://github.com/owner/repo/pull/N"
    )


def add_force_pr_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--force-pr",
        default=None,
        help=(
            "Pin one PR: number (13), owner/repo#13, or full URL "
            "(https://github.com/owner/repo/pull/13)"
        ),
    )
    parser.add_argument(
        "--force-repo",
        default=None,
        help="Deprecated: use owner/repo in --force-pr instead (repo short name only)",
    )


def resolve_force_pr_args(
    force_pr: str | int | None,
    force_repo: str | None = None,
) -> ForcePrRef | None:
    ref = parse_force_pr(force_pr)
    if ref is None:
        return None
    if force_repo and not ref.pinned:
        return ForcePrRef(number=ref.number, owner=None, repo=force_repo)
    if force_repo and ref.pinned and ref.repo != force_repo:
        raise ValueError(
            f"--force-repo {force_repo!r} conflicts with --force-pr repo {ref.repo!r}"
        )
    return ref
