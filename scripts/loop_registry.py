#!/usr/bin/env python3
"""The loop registry — the shared engine's descriptor for each named loop.

`kloop` is the **family** of four peer loops (legacy name: `engineering-work-loop`,
still accepted), all thin descriptors over one shared engine (discovery, worktree,
verify, report gate, config, cron/launchd/Task-Scheduler install). A "loop" is fully
described by:

  name           the loop's identity — drives the cron label, config file, and
                 state paths (com.<namespace>[.<inst>].<name>, <name>[-<inst>].yaml, ...)
  prompt         the agent prompt file under .github/prompts/ (what the loop does)
  skill          the skill the prompt routes through (validated by report_gate)
  status_gate    the default Project Status this loop picks up (may be overridden
                 per-repo in config; None = ungated)
  summary        one-line human description

Selecting a loop is `--loop <name>` on the setup/cron entrypoints, or the
ENGINEERING_LOOP_NAME env var (the cron injects it into the plist / Task). The
default is `implement-loop` (the former engineering-work-loop build behavior), so
existing single-loop installs keep working.

This module is stdlib-only and importable by every engine script.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def app_namespace() -> str:
    """The toolkit's filesystem/label namespace. Env override KADENCE_NAMESPACE,
    else 'kadence'. Every ~/.config, ~/.local/share, launchd-label, and
    Windows-task-name construction routes through this so the brand lives in one
    place. A legacy operator can keep the old layout with KADENCE_NAMESPACE=ai-sdlc."""
    return os.environ.get("KADENCE_NAMESPACE", "").strip() or "kadence"


@dataclass(frozen=True)
class LoopDescriptor:
    name: str
    prompt: str | None  # None for self-hosted loops (pr-review/pr-comment-fix)
    skill: str
    status_gate: str | None
    summary: str


# The four peer loops under the engineering-work-loop family.
#
# spec-loop and implement-loop are ENGINE-DRIVEN: they run over the shared engine
# (engineering-work-loop.sh + engineering_work_loop_setup.py), selected by
# ENGINEERING_LOOP_NAME, differing only by prompt + skill + status gate.
#
# pr-review-loop and pr-comment-fix-loop are SELF-HOSTED: they predate the shared
# engine and keep their own runners/setup (pr_review_loop_*.py, pr_fix_*.py). Their
# descriptors here exist for family naming/label consistency and documentation; the
# engine does not run them (prompt=None, engine_driven=False).
LOOPS: dict[str, LoopDescriptor] = {
    "implement-loop": LoopDescriptor(
        name="implement-loop",
        prompt="implement-loop.prompt.md",
        skill="implement",
        status_gate="Ready for Dev",
        summary="Build: picks up Ready-for-Dev issues, writes code to the spec, opens a code PR (Closes #).",
    ),
    "spec-loop": LoopDescriptor(
        name="spec-loop",
        prompt="spec-loop.prompt.md",
        skill="spec-author",
        status_gate="Ready for Spec",
        summary="Spec: picks up Ready-for-Spec issues, authors specs/<slug>/ only, opens a spec-only PR (Refs #).",
    ),
    "pr-review-loop": LoopDescriptor(
        name="pr-review-loop",
        prompt=None,
        skill="pr-review",
        status_gate=None,
        summary="Review (self-hosted runner): reviews open PRs on their diff, posts a structured review.",
    ),
    "pr-comment-fix-loop": LoopDescriptor(
        name="pr-comment-fix-loop",
        prompt=None,
        skill="pr-comment-fix-loop",
        status_gate=None,
        summary="Fix (self-hosted runner): addresses reviewer comments on a PR and re-requests review.",
    ),
}

# The family umbrella name (not a concrete loop) + the default concrete loop for
# bare invocations (backward compatibility with the former single loop). 'kloop' is
# the current brand for the four-loop family; 'engineering-work-loop' is the legacy
# family name kept as an alias so old installs/labels/env values keep resolving. The
# concrete cron scripts and ENGINEERING_LOOP_* env vars still carry the legacy stem
# (they are load-bearing in the installed plists); only the family *name* is rebranded.
FAMILY_NAME = "kloop"
LEGACY_FAMILY_NAME = "engineering-work-loop"
DEFAULT_LOOP = "implement-loop"

# The loops the shared engine (engineering-work-loop.sh / setup) actually runs.
ENGINE_DRIVEN = ("implement-loop", "spec-loop")


def is_engine_driven(name: str) -> bool:
    return resolve_loop_name(name) in ENGINE_DRIVEN


def resolve_loop_name(explicit: str | None = None) -> str:
    """Resolve the active loop: explicit arg > ENGINEERING_LOOP_NAME env > default.

    The family name — 'kloop' or the legacy 'engineering-work-loop' — resolves to the
    default concrete loop (implement-loop) so both the current brand and old
    installs/labels keep working.
    """
    name = (explicit or os.environ.get("ENGINEERING_LOOP_NAME", "") or "").strip()
    if not name:
        return DEFAULT_LOOP
    if name in (FAMILY_NAME, LEGACY_FAMILY_NAME):
        return DEFAULT_LOOP
    return name


def get_loop(name: str | None = None) -> LoopDescriptor:
    resolved = resolve_loop_name(name)
    try:
        return LOOPS[resolved]
    except KeyError:
        raise SystemExit(
            f"unknown loop '{resolved}'. Known loops: {', '.join(sorted(LOOPS))}"
        )


__all__ = [
    "app_namespace",
    "LoopDescriptor",
    "LOOPS",
    "FAMILY_NAME",
    "LEGACY_FAMILY_NAME",
    "DEFAULT_LOOP",
    "ENGINE_DRIVEN",
    "resolve_loop_name",
    "get_loop",
    "is_engine_driven",
]
