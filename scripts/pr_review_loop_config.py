"""Config loading for the PR review loop (stdlib only). Wraps pr_fix_config's
shared helpers, mirroring engineering_work_loop_config."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pr_fix_config import (
    _load_raw,
    deep_merge,
    deep_merge_missing,
    dump_overlay_yaml,
    expand_path,
)

OVERLAY_NAME = "pr-review-loop.yaml"


def toolkit_root() -> Path:
    env = os.environ.get("PR_REVIEW_LOOP_TOOLKIT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def toolkit_example_path(root: Path | None = None) -> Path:
    base = root or toolkit_root()
    return base / "skills/pr-review-loop/config.example.yaml"


def operator_overlay_path() -> Path:
    return Path.home() / ".config/ai-sdlc" / OVERLAY_NAME


def resolve_config_path() -> Path:
    overlay = operator_overlay_path()
    if overlay.is_file():
        return overlay
    example = toolkit_example_path()
    if example.is_file():
        return example
    return overlay


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path).expanduser() if path is not None else resolve_config_path()
    example = toolkit_example_path()
    overlay = operator_overlay_path()
    should_merge = p == overlay or p.name == OVERLAY_NAME
    if should_merge and example.is_file():
        base = _load_raw(example)
        overlay_data = _load_raw(p) if p.is_file() else {}
        cfg = deep_merge(base, overlay_data)
    elif p.is_file():
        cfg = _load_raw(p)
    elif example.is_file():
        cfg = _load_raw(example)
    else:
        raise FileNotFoundError(f"config not found: {p}")
    return _normalize_config(cfg)


def build_overlay_yaml(cfg: dict[str, Any]) -> str:
    return dump_overlay_yaml(cfg).replace(
        "pr-comment-fix-loop-setup.sh install --refresh-config",
        "pr-review-loop-setup.sh install --refresh-config",
    )


def _normalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg.setdefault("repos", [])
    if isinstance(cfg.get("repos"), dict):
        cfg["repos"] = [cfg["repos"]]
    elif not isinstance(cfg.get("repos"), list):
        cfg["repos"] = []
    cfg.setdefault("cadence_minutes", 15)
    cfg.setdefault("adjacent_reviewers", [])
    if not isinstance(cfg.get("adjacent_reviewers"), list):
        cfg["adjacent_reviewers"] = []
    cfg.setdefault("defer_to_ci", True)
    cfg.setdefault(
        "state_log", "~/.local/share/ai-sdlc/pr-review-loop.log"
    )
    labels = cfg.get("labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    labels.setdefault("complete", "pr-review-loop-complete")
    labels.setdefault("in_progress", "pr-review-loop-in-progress")
    cfg["labels"] = labels
    report = cfg.get("report") or {}
    if not isinstance(report, dict):
        report = {}
    report.setdefault("apply_labels", True)
    cfg["report"] = report
    git = cfg.get("git") or {}
    if isinstance(git, dict):
        git.setdefault("primary_clone", "~/projects/product-workspace")
        cfg["git"] = git
    status = cfg.get("status") or {}
    if isinstance(status, dict):
        cfg["status"] = {
            "latest_json": status.get(
                "latest_json", "~/.local/share/ai-sdlc/pr-review-loop-latest.json"
            ),
            "latest_md": status.get(
                "latest_md", "~/.local/share/ai-sdlc/pr-review-loop-latest.md"
            ),
            "firing_log": status.get(
                "firing_log", "~/.local/share/ai-sdlc/pr-review-loop-firings.log"
            ),
        }
    from loop_agent_config import normalize_agent_config

    normalize_agent_config(cfg)
    return cfg


__all__ = [
    "build_overlay_yaml",
    "deep_merge_missing",
    "expand_path",
    "load_config",
    "operator_overlay_path",
    "resolve_config_path",
    "toolkit_example_path",
    "toolkit_root",
]
