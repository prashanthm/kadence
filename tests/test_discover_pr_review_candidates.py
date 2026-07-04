"""Tests for discover_pr_review_candidates.resolve_is_toolkit_pr — regression for
PR #13 review finding H2: is_toolkit_pr only matched a vendored `kadence/`
file-path prefix, a v1 subdirectory-install artifact. In the standalone v2 repo, no
file in a PR against kadence itself carries that prefix, so the read-only
worktree exception (materialize the PR HEAD to review its own conventions/prompts)
could never fire for a PR IN the toolkit repo — exactly the case that matters most."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from discover_pr_review_candidates import (  # noqa: E402
    is_toolkit_pr,
    resolve_is_toolkit_pr,
)


def test_pr_in_the_toolkit_repo_itself_is_always_toolkit_pr():
    # No vendored-prefix file path needed — repo identity alone is sufficient.
    pr = {"files": [{"path": "README.md"}, {"path": "scripts/doctor.py"}]}
    assert resolve_is_toolkit_pr(pr, "your-org", "kadence", None) is True


def test_pr_in_another_repo_without_vendored_path_is_not_toolkit_pr():
    pr = {"files": [{"path": "src/saa/orchestration/mining.py"}]}
    assert resolve_is_toolkit_pr(pr, "your-org", "subsurface-agentic-ai", None) is False


def test_legacy_vendored_subdirectory_path_still_matches():
    # Some repo may still vendor the toolkit as a subdirectory — the old check is
    # kept as a fallback for that case.
    pr = {"files": [{"path": "kadence/scripts/doctor.py"}]}
    assert is_toolkit_pr(pr) is True
    assert resolve_is_toolkit_pr(pr, "your-org", "product-workspace", None) is True
