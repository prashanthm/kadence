#!/usr/bin/env python3
"""Classify GitHub issue/PR for engineering work loop risk tier."""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


def parse_loop_ac_meta(body: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    m = re.search(r"\*\*Work item type:\*\*\s*(\S+)", body)
    if m:
        meta["work_item_type"] = m.group(1).strip().lower()
    m = re.search(r"\*\*Risk tier:\*\*\s*(\S+)", body)
    if m:
        meta["risk_tier"] = m.group(1).strip().lower()
    return meta


# (v2) The compliance-gap classification path is removed. There is no M18 status
# drift / epic_milestone / orphan_pr work type in v2 — the loop implements real code
# work only (feature/task/chore/dependabot/fix). See assessments/kadence-v2.


def classify_issue(title: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
    labels = [x.lower() for x in (labels or [])]
    meta = parse_loop_ac_meta(body)
    work_type = meta.get("work_item_type", "")

    if work_type == "dependabot" or "dependabot" in labels:
        return {
            "work_item_type": "dependabot",
            "risk_tier": meta.get("risk_tier", "assist"),
            "reasons": [],
            "thresholds": {"max_files": 20, "max_lines": 500},
        }

    if work_type == "chore" or "chore" in labels:
        tier = meta.get("risk_tier", "assist")
        if "## loop ac" in body.lower() and "verify:" in body.lower():
            tier = meta.get("risk_tier", "auto")
        return {
            "work_item_type": "chore",
            "risk_tier": tier,
            "reasons": [],
            "thresholds": {"max_files": 3, "max_lines": 50},
        }

    if work_type == "task" or "task" in labels:
        # Task = a legacy-compatible loop-implementable unit. Auto tier when it
        # carries a verifiable Loop AC section. (In v2 the Feature is the build
        # unit — right-sized at generation, one feature -> one spec -> one PR;
        # Loop AC verifies behavior, not diff size, so there is no size tripwire.)
        # The thresholds below are risk-classification heuristics only.
        tier = meta.get("risk_tier", "assist")
        if "## loop ac" in body.lower() and "verify:" in body.lower():
            tier = meta.get("risk_tier", "auto")
        return {
            "work_item_type": "task",
            "risk_tier": tier,
            "reasons": [],
            "thresholds": {"max_files": 8, "max_lines": 300},
        }

    if work_type == "feature" or "feature" in labels:
        return {
            "work_item_type": "feature",
            "risk_tier": meta.get("risk_tier", "assist"),
            "reasons": [],
            "thresholds": {"max_files": 10, "max_lines": 500},
        }

    if work_type == "fix" or "bug" in labels:
        return {
            "work_item_type": "fix",
            "risk_tier": meta.get("risk_tier", "assist"),
            "reasons": [],
            "thresholds": {"max_files": 5, "max_lines": 200},
        }

    return {
        "work_item_type": work_type or "unknown",
        "risk_tier": "human-only",
        "reasons": ["unclassified work item"],
        "thresholds": {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify work item for engineering loop")
    parser.add_argument("--title", default="")
    parser.add_argument("--body-file", type=argparse.FileType("r"), default=None)
    parser.add_argument("--body", default="")
    parser.add_argument("--labels", default="", help="comma-separated")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    body = args.body
    if args.body_file:
        body = args.body_file.read()
    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    result = classify_issue(args.title, body, labels)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"type={result['work_item_type']} tier={result['risk_tier']}")


if __name__ == "__main__":
    main()
