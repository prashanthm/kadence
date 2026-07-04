"""GitHub label helpers for the PR review loop (rollup / adoption telemetry)."""
from __future__ import annotations

import subprocess
from typing import Any


def label_cfg(cfg: dict[str, Any]) -> dict[str, str]:
    labels = cfg.get("labels") or {}
    return {
        "complete": str(labels.get("complete", "pr-review-loop-complete")),
        "in_progress": str(labels.get("in_progress", "pr-review-loop-in-progress")),
    }


def report_apply_labels(cfg: dict[str, Any]) -> bool:
    report = cfg.get("report") or {}
    if "apply_labels" in report:
        return bool(report["apply_labels"])
    return True


def bootstrap_labels(cfg: dict[str, Any]) -> None:
    """Ensure loop labels exist on every configured repo (idempotent)."""
    if not report_apply_labels(cfg):
        return
    labels = label_cfg(cfg)
    specs = [
        (labels["complete"], "PR review loop posted review at HEAD", "1D76DB"),
        (labels["in_progress"], "PR review loop in progress", "FBCA04"),
    ]
    for entry in cfg.get("repos") or []:
        owner = entry.get("owner", "")
        repo = entry.get("repo", "")
        if not owner or not repo:
            continue
        full = f"{owner}/{repo}"
        for name, desc, color in specs:
            proc = subprocess.run(
                [
                    "gh",
                    "label",
                    "create",
                    name,
                    "--repo",
                    full,
                    "--description",
                    desc,
                    "--color",
                    color,
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 and "already exists" not in (proc.stderr or "").lower():
                pass


def apply_in_progress(cfg: dict[str, Any], full_repo: str, pr: int) -> None:
    """Mark review firing started — best-effort."""
    if not report_apply_labels(cfg):
        return
    labels = label_cfg(cfg)
    subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            str(pr),
            "--repo",
            full_repo,
            "--add-label",
            labels["in_progress"],
            "--remove-label",
            labels["complete"],
        ],
        capture_output=True,
        text=True,
    )


def apply_complete(cfg: dict[str, Any], full_repo: str, pr: int) -> None:
    """Mark verified operator review at HEAD — best-effort."""
    if not report_apply_labels(cfg):
        return
    labels = label_cfg(cfg)
    subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            str(pr),
            "--repo",
            full_repo,
            "--add-label",
            labels["complete"],
            "--remove-label",
            labels["in_progress"],
        ],
        capture_output=True,
        text=True,
    )
