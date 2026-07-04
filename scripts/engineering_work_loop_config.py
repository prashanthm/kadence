"""Shared config loading for engineering work loop scripts (stdlib only)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pr_fix_config import (
    _load_raw,
    deep_merge,
    deep_merge_missing,
    dump_overlay_yaml,
    expand_path,
)


def toolkit_root() -> Path:
    env = __import__("os").environ.get("ENGINEERING_LOOP_TOOLKIT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def toolkit_example_path(root: Path | None = None) -> Path:
    base = root or toolkit_root()
    return base / "skills/engineering-work-loop/config.example.yaml"


def loop_stem() -> str:
    """The active loop's name — the stem for config/label/state paths.

    A "loop" in the engineering-work-loop family (implement-loop, spec-loop,
    pr-review-loop, pr-comment-fix-loop) drives its own config/state stem. Resolved
    from ENGINEERING_LOOP_NAME via the registry; the legacy family name and empty
    default to implement-loop, so existing single-loop installs keep working.
    """
    from loop_registry import resolve_loop_name

    return resolve_loop_name()


def operator_overlay_path() -> Path:
    # Loop- and instance-aware: <loop-stem>[-<inst>].yaml, e.g. spec-loop-v2.yaml.
    # ENGINEERING_LOOP_NAME picks the loop; ENGINEERING_LOOP_INSTANCE suffixes for
    # side-by-side installs. Both empty = implement-loop (the former default).
    inst = __import__("os").environ.get("ENGINEERING_LOOP_INSTANCE", "").strip()
    stem = loop_stem()
    name = f"{stem}-{inst}.yaml" if inst else f"{stem}.yaml"
    return Path.home() / ".config/ai-sdlc" / name


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
    # Merge the example defaults under an operator overlay (the resolved overlay path,
    # or any loop-family overlay filename <loop>[-<inst>].yaml).
    from loop_registry import LOOPS

    _is_family_overlay = p.name == "engineering-work-loop.yaml" or any(
        p.name == f"{n}.yaml" or p.name.startswith(f"{n}-") for n in LOOPS
    )
    should_merge = p == overlay or _is_family_overlay
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
        "engineering-work-loop-setup.sh install --refresh-config",
    )


def _normalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg.setdefault("repos", [])
    if isinstance(cfg.get("repos"), dict):
        cfg["repos"] = [cfg["repos"]]
    elif not isinstance(cfg.get("repos"), list):
        cfg["repos"] = []
    for entry in cfg["repos"]:
        if isinstance(entry, dict) and entry.get("clone_path"):
            entry["clone_path"] = expand_path(str(entry["clone_path"]))
    cfg.setdefault("enabled_work_types", [])
    if not isinstance(cfg.get("enabled_work_types"), list):
        cfg["enabled_work_types"] = []
    cfg.setdefault("cadence_minutes", 30)
    cfg.setdefault("cooldown_hours", 24)
    # Per-repo cap (default 5). max_items_per_firing is NOT defaulted here: when
    # absent, the loop is multi-item; when present (legacy overlays), it acts as a
    # global hard ceiling across all repos. Both are clamped to [1, 100] to reject
    # negative / zero / runaway values (addresses review H7).
    def _clamp_cap(value: Any, default: int) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(100, n))

    cfg["max_items_per_repo"] = _clamp_cap(cfg.get("max_items_per_repo", 5), 5)
    if cfg.get("max_items_per_firing") is not None:
        cfg["max_items_per_firing"] = _clamp_cap(cfg["max_items_per_firing"], 1)
    cfg.setdefault("process_assist", False)
    comp = cfg.setdefault("compliance", {})
    if not isinstance(comp, dict):
        comp = {}
        cfg["compliance"] = comp
    comp.setdefault("auto_execute", True)
    if not isinstance(comp.get("allowed_categories"), list):
        comp["allowed_categories"] = comp.get("allowed_categories") or []
    discovery = cfg.get("discovery") or {}
    if isinstance(discovery, dict):
        cfg["discovery"] = {
            "require_loop_ac_on_issue": bool(
                discovery.get("require_loop_ac_on_issue", False)
            ),
            "synthesize_missing_loop_ac": bool(
                discovery.get("synthesize_missing_loop_ac", True)
            ),
            "writeback_loop_ac": bool(discovery.get("writeback_loop_ac", True)),
        }
    else:
        cfg["discovery"] = {
            "require_loop_ac_on_issue": False,
            "synthesize_missing_loop_ac": True,
            "writeback_loop_ac": True,
        }
    _stem = loop_stem()
    cfg.setdefault(
        "state_log",
        f"~/.local/share/ai-sdlc/{_stem}.log",
    )
    git = cfg.get("git") or {}
    if isinstance(git, dict):
        git.setdefault("worktree_root", "~/.local/share/ai-sdlc/worktrees")
        git.setdefault("fetch_only_in_primary", True)
        git.setdefault("release_after_pr", True)
        git.setdefault("keep_worktree_on_failure", True)
        cfg["git"] = git
    pr = cfg.get("pr") or {}
    if isinstance(pr, dict):
        pr.setdefault("open_as_draft", True)
        # Risk-based auto-land policy (e04-f10). Default-off reproduces today's
        # draft-only, human-merge behavior; only present so callers can read a
        # complete block without missing-key handling.
        mp = pr.get("merge_policy") or {}
        if isinstance(mp, dict):
            mp.setdefault("enabled", False)
            mp.setdefault("auto_ready_tier", "auto")
            mp.setdefault("require_pr_review_approved", True)
            mp.setdefault("require_ci_green", True)
            mp.setdefault("require_mergeable", True)
            mp.setdefault("method", "merge")
            mp.setdefault("delete_branch", True)
            mp.setdefault("dry_run", True)
            pr["merge_policy"] = mp
        cfg["pr"] = pr
    status = cfg.get("status") or {}
    if isinstance(status, dict):
        cfg["status"] = {
            "latest_json": status.get(
                "latest_json",
                f"~/.local/share/ai-sdlc/{_stem}-latest.json",
            ),
            "latest_md": status.get(
                "latest_md",
                f"~/.local/share/ai-sdlc/{_stem}-latest.md",
            ),
            "firing_log": status.get(
                "firing_log",
                f"~/.local/share/ai-sdlc/{_stem}-firings.log",
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
