#!/usr/bin/env python3
"""Bootstrap one initiative's AGENTS.md and its row in the product-workspace root routing table.

Run as the required last step of `initiative-generation` for every *new* initiative. Given a
`product-workspace` repo root and an initiative slug (an already-written `initiatives/<slug>/initiative.md`
must exist), this script:

1. Creates `initiatives/<slug>/AGENTS.md`, seeded from that initiative's own `## Why` and `## What`
   sections (not blank scaffolding).
2. Appends exactly one new row to the root `AGENTS.md` routing table (`## Routing table`), pointing at
   `initiatives/<slug>/INDEX.md`, without disturbing any other row or line in the file.

Both steps are independently idempotent: re-running against an initiative that already has an `AGENTS.md`
and a routing-table row is a no-op for that step (no duplicate row, no destructive overwrite unless
`--force` is passed for the `AGENTS.md` file specifically). This keeps the routing table from silently
drifting stale as initiatives are added — the failure mode this feature exists to close.

No network calls — this reads/writes only the local markdown tree under the given
`--product-workspace-root`, so it is safe to run offline.

Usage:
  bootstrap_initiative_agents_md.py --product-workspace-root <path> --initiative-slug <slug> [--force]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_initiative_index import _section_body, extract_first_sentence  # noqa: E402

_ROUTING_TABLE_HEADER_RE = re.compile(
    r"^\|\s*Initiative\s*\|\s*Purpose\s*\|\s*INDEX\.md\s*\|\s*$\n"
    r"^\|[-\s|]+\|\s*$\n",
    re.M,
)
# A routing-table data row's first cell: `[`slug`](initiatives/slug/initiative.md)` or the
# no-charter variant `[`slug`](initiatives/slug/)` / `[`slug`](initiatives/slug/README.md)` —
# only the slug segment of the link target is used to detect an existing row for a given slug.
_ROW_SLUG_RE = re.compile(r"^\|\s*\[`([a-z0-9][a-z0-9-]*)`\]\(initiatives/([a-z0-9][a-z0-9-]*)/")


def _escape_table_cell(text: str) -> str:
    """Escape characters that would break a GFM markdown table cell."""
    return text.replace("|", "\\|")


def extract_purpose_sentence(initiative_md_text: str, slug: str) -> str:
    """First sentence of the `## Why` section body — the shared one-line purpose used both in the
    initiative's own `AGENTS.md` intro and the root routing-table row, so the two never drift
    from each other.

    Raises ValueError (naming `slug`) if `## Why` is missing or empty.
    """
    why = _section_body(initiative_md_text, "Why")
    if why is None or not why.strip():
        raise ValueError(
            f"malformed initiative.md (missing or empty '## Why' section) for initiative {slug!r}"
        )
    return extract_first_sentence(why)


def build_initiative_agents_md(initiative_md_text: str, slug: str) -> str:
    """Render `initiatives/<slug>/AGENTS.md` content, seeded from `initiative_md_text`.

    Raises ValueError (naming `slug`) if `## Why` or `## What` is missing or empty in the source
    charter — an initiative without those sections is malformed, and silently emitting a stub
    AGENTS.md would reintroduce the blank-scaffolding failure mode this feature guards against.
    """
    purpose = extract_purpose_sentence(initiative_md_text, slug)

    what = _section_body(initiative_md_text, "What")
    if what is None or not what.strip():
        raise ValueError(
            f"malformed initiative.md (missing or empty '## What' section) for initiative {slug!r}"
        )

    lines: list[str] = []
    lines.append("# AGENTS.md")
    lines.append("")
    lines.append(
        f"Guidance for AI agents (and humans) working in the `{slug}` initiative. {purpose}"
    )
    lines.append("")
    lines.append(
        "Read the repo-root [`AGENTS.md`](../../AGENTS.md) first — it documents repository-wide "
        "conventions, the initiative routing table, and the duplication-check discipline that "
        "applies before drafting any new epic, feature, or spec content in this initiative."
    )
    lines.append("")
    lines.append("## What this initiative delivers")
    lines.append("")
    lines.append(what.strip())
    lines.append("")
    lines.append("## Where things live")
    lines.append("")
    lines.append(f"```")
    lines.append(f"{slug}/")
    lines.append("├── initiative.md      # Charter: Status, Why, What")
    lines.append("├── product-brief.md   # Capability brief + Epic Index (release order)")
    lines.append("├── epics/<epic-slug>.md")
    lines.append("├── features/<feature-slug>.md")
    lines.append("├── adrs/               # Architecture Decision Records (where applicable)")
    lines.append("└── INDEX.md            # Generated — do not hand-edit")
    lines.append("```")
    lines.append("")
    lines.append(
        "Before drafting new epic, feature, or spec content under this initiative, read "
        f"[`INDEX.md`](INDEX.md) (once generated — see the repo-root `AGENTS.md` if it does not "
        "exist yet) to check whether the capability already exists under a sibling epic."
    )
    lines.append("")
    return "\n".join(lines)


def insert_routing_row(root_agents_md_text: str, slug: str, purpose: str) -> tuple[str, bool]:
    """Insert one routing-table row for `slug` into `root_agents_md_text`.

    Returns `(new_text, was_inserted)`. If a row for `slug` already exists (matched by the first
    cell's link target `initiatives/<slug>/...`), returns `(root_agents_md_text, False)` unchanged
    — no duplicate row. Otherwise appends the new row immediately after the last existing row,
    leaving every other line byte-identical, and returns `(new_text, True)`.

    Raises ValueError if the routing table header/separator cannot be found at all — this signals
    the root AGENTS.md is missing the bootstrap this feature depends on (`agents-md-bootstrap`).
    """
    header_match = _ROUTING_TABLE_HEADER_RE.search(root_agents_md_text)
    if not header_match:
        raise ValueError(
            "root AGENTS.md has no '| Initiative | Purpose | INDEX.md |' routing table — "
            "run agents-md-bootstrap first"
        )

    lines = root_agents_md_text.splitlines(keepends=True)
    # Locate the line index of the separator row (last line consumed by the header match).
    consumed_upto = header_match.end()
    offset = 0
    separator_line_idx = -1
    for idx, line in enumerate(lines):
        offset += len(line)
        if offset >= consumed_upto:
            separator_line_idx = idx
            break
    if separator_line_idx == -1:
        raise ValueError("failed to locate routing table separator row")

    # Walk forward through contiguous `|`-prefixed data rows.
    last_row_idx = separator_line_idx
    idx = separator_line_idx + 1
    while idx < len(lines) and lines[idx].lstrip().startswith("|"):
        row = lines[idx]
        row_match = _ROW_SLUG_RE.match(row.strip())
        if row_match and row_match.group(2) == slug:
            return root_agents_md_text, False
        last_row_idx = idx
        idx += 1

    escaped_purpose = _escape_table_cell(purpose)
    new_row = (
        f"| [`{slug}`](initiatives/{slug}/initiative.md) | {escaped_purpose} "
        f"| [`initiatives/{slug}/INDEX.md`](initiatives/{slug}/INDEX.md) |\n"
    )
    new_lines = lines[: last_row_idx + 1] + [new_row] + lines[last_row_idx + 1 :]
    return "".join(new_lines), True


def bootstrap_initiative_agents_md(
    product_workspace_root: Path, slug: str, force: bool = False
) -> dict[str, str]:
    """Orchestrate both steps for one initiative. Returns a status dict:

        {"agents_md": "created" | "skipped" | "overwritten",
         "routing_row": "appended" | "skipped"}
    """
    product_workspace_root = Path(product_workspace_root)
    initiative_dir = product_workspace_root / "initiatives" / slug
    initiative_md_path = initiative_dir / "initiative.md"
    if not initiative_md_path.is_file():
        raise ValueError(
            f"no initiative.md found for initiative {slug!r} at {initiative_md_path} "
            "(this script wires an existing charter; run initiative-generation's charter step first)"
        )
    initiative_md_text = initiative_md_path.read_text(encoding="utf-8")

    purpose = extract_purpose_sentence(initiative_md_text, slug)

    agents_md_path = initiative_dir / "AGENTS.md"
    if agents_md_path.exists() and not force:
        agents_md_status = "skipped"
    else:
        content = build_initiative_agents_md(initiative_md_text, slug)
        agents_md_status = "overwritten" if agents_md_path.exists() else "created"
        agents_md_path.write_text(content, encoding="utf-8")

    root_agents_md_path = product_workspace_root / "AGENTS.md"
    if not root_agents_md_path.is_file():
        raise ValueError(
            f"no root AGENTS.md found at {root_agents_md_path} — run agents-md-bootstrap first"
        )
    root_text = root_agents_md_path.read_text(encoding="utf-8")
    new_root_text, was_inserted = insert_routing_row(root_text, slug, purpose)
    if was_inserted:
        root_agents_md_path.write_text(new_root_text, encoding="utf-8")
        routing_row_status = "appended"
    else:
        routing_row_status = "skipped"

    return {"agents_md": agents_md_status, "routing_row": routing_row_status}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap an initiative's AGENTS.md and its row in the product-workspace root "
            "routing table"
        )
    )
    parser.add_argument(
        "--product-workspace-root",
        required=True,
        help="Path to the product-workspace repo root (absolute or relative to CWD)",
    )
    parser.add_argument(
        "--initiative-slug",
        required=True,
        help="Initiative directory name under initiatives/ (must already have an initiative.md)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing initiatives/<slug>/AGENTS.md with freshly-seeded content",
    )
    args = parser.parse_args()

    status = bootstrap_initiative_agents_md(
        Path(args.product_workspace_root), args.initiative_slug, force=args.force
    )
    print(f"AGENTS.md: {status['agents_md']}")
    print(f"routing table row: {status['routing_row']}")


if __name__ == "__main__":
    main()
