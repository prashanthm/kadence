"""AI Attribution block for PR comment fix loop published comments."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loop_agent_config import agent_tool_name, normalize_agent_config

ATTRIBUTION_HEADING = "## AI Attribution"
PR_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "pull-request.md"


def extract_attribution_from_template() -> str:
    if not PR_TEMPLATE.exists():
        return _default_attribution_markdown()
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    match = re.search(
        r"(## AI Attribution\s*\n(?:.*\n)*?\|[^\n]+\|\s*\n\|[-| ]+\|\s*\n(?:\|[^\n]+\|\s*\n)+)",
        text,
    )
    if match:
        return match.group(1).rstrip() + "\n"
    return _default_attribution_markdown()


def _default_attribution_markdown() -> str:
    return """## AI Attribution

| Role | Model | Tool |
|------|-------|------|
| Author | — | — |
| Spec | — | — |
| Reviewer | — | — |
"""


def _dash(value: str) -> str:
    v = (value or "").strip()
    return v if v else "—"


def fill_attribution(
    cfg: dict[str, Any],
    *,
    author_model: str | None = None,
    author_tool: str | None = None,
    spec_model: str = "—",
    spec_tool: str = "—",
    reviewer_model: str = "—",
    reviewer_tool: str = "—",
) -> str:
    cfg = normalize_agent_config(dict(cfg))
    model = _dash(author_model if author_model is not None else str(cfg.get("agent_model", "")))
    tool = _dash(author_tool if author_tool is not None else agent_tool_name(cfg))
    return (
        f"{ATTRIBUTION_HEADING}\n\n"
        "| Role | Model | Tool |\n"
        "|------|-------|------|\n"
        f"| Author | {model} | {tool} |\n"
        f"| Spec | {spec_model} | {spec_tool} |\n"
        f"| Reviewer | {reviewer_model} | {reviewer_tool} |\n"
    )


def has_filled_author_attribution(text: str) -> bool:
    if ATTRIBUTION_HEADING not in text:
        return False
    section = text.split(ATTRIBUTION_HEADING, 1)[1]
    for line in section.splitlines():
        if not line.startswith("| Author |"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            return False
        tool = cells[2]
        if tool and tool != "—" and not tool.startswith("<!--"):
            return True
    return False


def ensure_attribution_in_report(report_text: str, cfg: dict[str, Any]) -> str:
    """Append or keep AI Attribution in fix report / ready comment body."""
    if has_filled_author_attribution(report_text):
        return report_text
    block = fill_attribution(cfg)
    if ATTRIBUTION_HEADING in report_text:
        # Replace empty attribution section
        return re.sub(
            r"## AI Attribution\s*\n(?:.*\n)*?(?=\n## |\Z)",
            block.rstrip() + "\n\n",
            report_text,
            count=1,
        )
    return report_text.rstrip() + "\n\n" + block
