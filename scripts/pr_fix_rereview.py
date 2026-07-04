"""Decide whether to re-request reviewers after a PR fix cycle."""
from __future__ import annotations

import json
import re
from typing import Any

HIGH_SEVERITIES = frozenset({"critical", "high"})


def latest_review_states(inventory: list[dict[str, Any]]) -> dict[str, str]:
    """Latest review state per non-review-comment author."""
    states: dict[str, str] = {}
    reviews = [
        item
        for item in inventory
        if item.get("source") == "review" and item.get("author")
    ]
    for item in sorted(reviews, key=lambda x: x.get("created_at") or ""):
        state = item.get("state") or ""
        if state:
            states[item["author"]] = state
    return states


def all_reviews_approved(inventory: list[dict[str, Any]]) -> bool:
    states = latest_review_states(inventory)
    if not states:
        return False
    return all(state == "APPROVED" for state in states.values())


def _severity_from_text(text: str) -> str:
    t = text.strip()
    if re.search(r"\bCritical\b|\bC\d+\b", t, re.I):
        return "critical"
    if re.search(r"\bHigh\b|\bH\d+\b", t, re.I):
        return "high"
    if re.search(r"\bMedium\b|\bM\d+\b", t, re.I):
        return "medium"
    if re.search(r"\bLow\b|\bL\d+\b", t, re.I):
        return "low"
    if re.search(r"\bInfo\b", t, re.I):
        return "info"
    return "unknown"


def fixed_severities_from_report(report_text: str) -> list[str]:
    """Parse disposition table rows marked Fixed and infer severities."""
    severities: list[str] = []
    in_disposition = False
    for line in report_text.splitlines():
        if line.strip().lower().startswith("## disposition"):
            in_disposition = True
            continue
        if in_disposition and line.startswith("## "):
            break
        if not in_disposition or not line.startswith("|"):
            continue
        if line.strip().startswith("|--"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 3:
            continue
        finding, disposition = cols[1], cols[2].lower()
        if "fixed" not in disposition:
            continue
        severities.append(_severity_from_text(finding))
    return severities


def parse_rereview_meta(report_text: str) -> dict[str, Any] | None:
    """Read optional ```json pr-fix-rereview ... ``` block from report."""
    match = re.search(
        r"```json\s+pr-fix-rereview\s*\n(.*?)\n```",
        report_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def requires_rereview(
    inventory: list[dict[str, Any]],
    report_text: str,
    *,
    meta: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """
    Re-request reviewers when changes were requested or critical/high fixes landed.
    Skip when all latest reviews are APPROVED and only low/medium/info fixes (or none).
    """
    meta = meta if meta is not None else parse_rereview_meta(report_text)
    if meta and "required" in meta:
        required = bool(meta["required"])
        reason = str(meta.get("reason") or ("rereview_required" if required else "rereview_skipped"))
        return required, reason

    approved = all_reviews_approved(inventory)
    fixed = fixed_severities_from_report(report_text)
    if not approved:
        return True, "not_all_reviews_approved"
    if any(s in HIGH_SEVERITIES for s in fixed):
        return True, "critical_or_high_fixed"
    return False, "approved_no_critical_high_fixes"
