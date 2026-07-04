"""Shared config loading for PR comment fix loop scripts (stdlib only)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loop_registry import app_namespace


def expand_path(value: str) -> str:
    return str(Path(value).expanduser())


def min_reviewer_feedback(cfg: dict[str, Any]) -> int:
    if "min_reviewer_feedback" in cfg:
        return int(cfg["min_reviewer_feedback"])
    return int(cfg.get("min_automated_feedback", 2))


def exclude_reviewers(cfg: dict[str, Any]) -> set[str]:
    return set(cfg.get("exclude_reviewers") or [])


def toolkit_root() -> Path:
    env = __import__("os").environ.get("PR_FIX_TOOLKIT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def toolkit_example_path(root: Path | None = None) -> Path:
    base = root or toolkit_root()
    return base / "skills/pr-comment-fix-loop/config.example.yaml"


def operator_overlay_path() -> Path:
    return Path.home() / f".config/{app_namespace()}/pr-comment-fix-loop.yaml"


def resolve_config_path() -> Path:
    overlay = operator_overlay_path()
    if overlay.is_file():
        return overlay
    example = toolkit_example_path()
    if example.is_file():
        return example
    return overlay


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def deep_merge_missing(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Keep overlay values; add keys from base only when missing."""
    merged = dict(overlay)
    for key, value in base.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_missing(value, merged[key])
    return merged


def _load_raw(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw)
    else:
        data = _parse_yaml_subset(raw)
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path).expanduser() if path is not None else resolve_config_path()
    example = toolkit_example_path()
    overlay = operator_overlay_path()
    should_merge = (
        p == overlay
        or p.name == "pr-comment-fix-loop.yaml"
    )
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


def dump_overlay_yaml(cfg: dict[str, Any]) -> str:
    """Write minimal operator overlay (machine-specific keys only)."""
    lines = [
        "# Operator overlay — merged on top of toolkit config.example.yaml",
        "# Re-run: pr-comment-fix-loop-setup.sh install --refresh-config",
        f"github_user: {cfg.get('github_user', '')}",
        "git:",
        f"  primary_clone: {cfg.get('git', {}).get('primary_clone', '')}",
        f"agent_backend: {cfg.get('agent_backend', 'claude')}",
    ]
    model = str(cfg.get("agent_model") or "")
    if model:
        lines.append(f'agent_model: "{model}"')
    return "\n".join(lines) + "\n"


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    """Minimal YAML parser for config files (no PyYAML required)."""
    lines = [ln for ln in text.splitlines()]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        idx += 1
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        content = line.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                continue
            rest = content[2:].strip()
            if ":" in rest:
                key, _, val = rest.partition(":")
                item: dict[str, Any] = {key.strip(): _parse_scalar(val.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(_parse_scalar(rest))
            continue

        if ":" not in content:
            continue

        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            parent[key] = (
                [_parse_scalar(x.strip()) for x in inner.split(",") if x.strip()]
                if inner
                else []
            )
            continue

        if rest == "":
            if idx < len(lines):
                nxt = lines[idx]
                nxt_indent = len(nxt) - len(nxt.lstrip())
                if nxt_indent > indent and nxt.strip().startswith("- "):
                    child_list: list[Any] = []
                    parent[key] = child_list
                    stack.append((indent, child_list))
                    continue
            child_dict: dict[str, Any] = {}
            parent[key] = child_dict
            stack.append((indent, child_dict))
            continue

        if not isinstance(parent, dict):
            continue
        parent[key] = _parse_scalar(rest)

    return root


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _normalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    labels = cfg.get("labels") or {}
    if isinstance(labels, dict):
        cfg.setdefault("labels", {})
        cfg["labels"].setdefault("complete", "pr-fix-cycle-complete")
        cfg["labels"].setdefault("in_progress", "pr-fix-cycle-in-progress")
        cfg["labels"].setdefault("deferred", "pr-fix-deferred")
        cfg["labels"].setdefault("needs_human", "pr-fix-needs-human")
    cfg.setdefault("max_rounds", 3)
    cfg.setdefault("min_reviewer_feedback", cfg.get("min_automated_feedback", 2))
    cfg.setdefault("min_automated_feedback", cfg["min_reviewer_feedback"])
    cfg.setdefault("exclude_reviewers", [])
    if not isinstance(cfg.get("exclude_reviewers"), list):
        cfg["exclude_reviewers"] = []
    cfg.setdefault("max_files_changed", 15)
    cfg.setdefault("in_progress_stale_hours", 2)
    cfg.setdefault("max_items_per_firing", 1)
    cfg.setdefault("automated_actors", [])
    if not isinstance(cfg.get("automated_actors"), list):
        cfg["automated_actors"] = []
    cfg.setdefault("repos", [])
    if isinstance(cfg.get("repos"), dict):
        cfg["repos"] = [cfg["repos"]]
    elif not isinstance(cfg.get("repos"), list):
        cfg["repos"] = []
    cfg.setdefault(
        "state_log",
        f"~/.local/share/{app_namespace()}/pr-comment-fix-loop.log",
    )
    ctx = cfg.get("context") or {}
    if isinstance(ctx, dict):
        cfg["context"] = {
            "max_tokens": ctx.get("max_tokens", 12000),
            "include_local_reviews": ctx.get("include_local_reviews", True),
        }
    git = cfg.get("git") or {}
    if isinstance(git, dict):
        cfg["git"] = git
    report = cfg.get("report") or {}
    if isinstance(report, dict):
        submit = report.get("submit", True)
        cfg["report"] = {
            "submit": submit,
            "push": report.get("push", submit),
            "apply_labels": report.get("apply_labels", submit),
            "draft_path": report.get(
                "draft_path",
                f"~/.local/share/{app_namespace()}/pr-fix-reports",
            ),
            "branch_draft_dir": report.get(
                "branch_draft_dir", ".sdlc/pr-fix-reports"
            ),
        }
    status = cfg.get("status") or {}
    if isinstance(status, dict):
        cfg["status"] = {
            "latest_json": status.get(
                "latest_json",
                f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-latest.json",
            ),
            "latest_md": status.get(
                "latest_md",
                f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-latest.md",
            ),
            "firing_log": status.get(
                "firing_log",
                f"~/.local/share/{app_namespace()}/pr-comment-fix-loop-firings.log",
            ),
            "firing_dir": status.get(
                "firing_dir",
                f"~/.local/share/{app_namespace()}/firings",
            ),
        }
    from loop_agent_config import normalize_agent_config

    normalize_agent_config(cfg)
    return cfg


def report_submit(cfg: dict[str, Any]) -> bool:
    return bool((cfg.get("report") or {}).get("submit", True))


def report_push(cfg: dict[str, Any]) -> bool:
    report = cfg.get("report") or {}
    return bool(report.get("push", report_submit(cfg)))


def report_apply_labels(cfg: dict[str, Any]) -> bool:
    report = cfg.get("report") or {}
    return bool(report.get("apply_labels", report_submit(cfg)))
