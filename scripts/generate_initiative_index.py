#!/usr/bin/env python3
"""Generate the deterministic INDEX.md for one initiative directory.

Walks `initiatives/<slug>/{epics,features,adrs}/` and writes `INDEX.md` into that same
directory: one row per epic (slug, phase, doc path), one flat row per feature (slug,
parent epic, one-line scope pulled from the feature doc's `## What` section, doc path),
and one row per ADR (number, title, doc path, status read from the ADR file's own
`## Status` field — never from the GitHub board).

Deterministic: rows are sorted by a stable key (slug / ADR number) and no timestamps are
embedded, so running the generator twice on unchanged source produces a byte-identical
file. No network calls — this reads only the local markdown tree, so it is safe to run
offline and in CI without a token.

Malformed docs fail loud: a feature doc missing `## What` (or with an empty one), or an
ADR doc missing its `# ADR-NNN: Title` heading or `## Status` section, raises ValueError
naming the offending file rather than silently skipping it or emitting an empty row.

Usage:
  generate_initiative_index.py --initiative-path <path-to-initiatives/slug>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_EPIC_SLUG_PHASE_RE = re.compile(r"Epic slug:\s*`[^`]+`.*?Phase\s+(\S+)", re.I)
_METADATA_ROW_RE = re.compile(r"^\|\s*\*\*Phase\*\*\s*\|\s*(.+?)\s*\|\s*$", re.I | re.M)
# Old epic-identity convention: a `**Epic ID**` Metadata row (e.g. `| **Epic ID** | e01 |`)
# instead of a `**Slug**` row. The epic's filename is positionally prefixed with this ID
# (`e01-core-standard-templates.md`) but the ID itself — not the filename stem — is what
# feature docs reference in their `Part of epic:` line.
_EPIC_ID_ROW_RE = re.compile(r"^\|\s*\*\*Epic ID\*\*\s*\|\s*(.+?)\s*\|\s*$", re.I | re.M)
# Link text is normally a bare slug (`[slug](url)`), but some docs wrap it in backticks
# to match the inline-code styling used elsewhere in the same line (`` [`slug`](url) ``).
# The optional backtick pair is stripped from the captured group in the caller.
_PART_OF_EPIC_RE = re.compile(r"Part of epic:\s*\[`?([^\]`]+)`?\]")
# Fallback for meta-features (e.g. adr-NNN-decision.md) whose "Part of epic:" line is
# prose, not a markdown link, e.g. "> Part of epic: SAA-MEMORY — Layered Memory". Capture
# the leading token (letters/digits/hyphens/underscores) as a candidate slug to resolve
# against known epic slugs case-insensitively.
_PART_OF_EPIC_PROSE_RE = re.compile(r"Part of epic:\s*([A-Za-z0-9_-]+)")
_ADR_HEADING_RE = re.compile(r"^#\s*ADR-(\d+):\s*(.+?)\s*$", re.M)
_ADR_FILENAME_RE = re.compile(r"^adr-(\d+)-.*\.md$", re.I)
_SECTION_RE_TMPL = r"^##\s+{name}\s*$(.*?)(?=^##\s+|\Z)"
# Consecutive blockquote lines (each starting with `>`, optionally indented) are how
# markdown renders a single continuous paragraph — a link or phrase can be split mid-
# sentence across two or more such lines purely for source line-wrapping. Match a run of
# 2+ such lines so they can be joined into one logical line before the "Part of epic:"
# regexes run, the same way a markdown renderer would flow them together.
_BLOCKQUOTE_RUN_RE = re.compile(r"(?:^[ \t]*>.*\n?){2,}", re.M)
# product-brief.md "Epic Index" table row, old (positional-ID) convention:
# `| e01 | Epic Name | Description | Phase 1 | [#55](...) |` — captures ID and the
# Milestone/Phase column (4th pipe-delimited cell).
_BRIEF_EPIC_ROW_ID_RE = re.compile(
    r"^\|\s*(e\d+)\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|", re.M
)
# product-brief.md "Epic Index" table row, v2 (slug) convention:
# `| [`slug`](epics/slug.md) | Epic Name | Description | Phase |` — captures the slug
# (bare or backtick-wrapped, linked or not) and the trailing Phase column.
_BRIEF_EPIC_ROW_SLUG_RE = re.compile(
    r"^\|\s*\[?`?([a-z][a-z0-9-]*)`?\]?(?:\([^)]*\))?\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|",
    re.M,
)


def _join_blockquote_runs(text: str) -> str:
    """Join each run of 2+ consecutive `>`-prefixed lines into one logical line.

    Markdown renders consecutive blockquote lines as a single continuous paragraph, so a
    phrase (e.g. a `Part of epic:` label and its markdown link) can be split across two
    source lines purely for wrapping, e.g.:

        > Slug: `x` · Part of epic:
        > [`some-epic`](../epics/some-epic.md) ·
        > GitHub Feature: ...

    This collapses each such run to a single `>`-prefixed line with the leading `>` (and
    any indentation) stripped from every line and inter-line whitespace collapsed to a
    single space, so downstream regexes that assume single-line phrases (e.g.
    `_PART_OF_EPIC_RE`) match regardless of where the source happened to wrap. Runs of a
    single blockquote line, and non-blockquote text, are left untouched.
    """

    def _join(match: re.Match[str]) -> str:
        run = match.group(0)
        lines = [ln.split(">", 1)[1].strip() for ln in run.splitlines()]
        return "> " + " ".join(line for line in lines if line) + "\n"

    return _BLOCKQUOTE_RUN_RE.sub(_join, text)


def _section_body(text: str, heading: str) -> str | None:
    """Return the body text between `## <heading>` and the next `##` heading (or EOF).

    None if the heading is not present at all.
    """
    pattern = re.compile(_SECTION_RE_TMPL.format(name=re.escape(heading)), re.M | re.S)
    m = pattern.search(text)
    if not m:
        return None
    return m.group(1).strip()


# Sentence-ending period: not preceded by a decimal digit (e.g. "v1.0") and not the
# second period of a short lowercase abbreviation like "e.g." / "i.e." (single letter,
# dot, single letter, immediately before the terminal period).
_SENTENCE_END_RE = re.compile(r"(?<!\d)(?<![a-z]\.[a-z])\.(?=\s|$)")


def extract_first_sentence(text: str) -> str:
    """First sentence of `text`: up to and including the first sentence-ending `.`
    followed by whitespace/EOF (so `e.g.` / `i.e.` / `v1.0` mid-sentence don't
    terminate early), with markdown bold markers stripped and whitespace/newlines
    collapsed to single spaces.
    """
    collapsed = re.sub(r"\s+", " ", text).strip()
    collapsed = collapsed.replace("**", "")
    m = _SENTENCE_END_RE.search(collapsed)
    if m:
        return collapsed[: m.end()].strip()
    return collapsed.strip()


def parse_epic(path: Path) -> dict[str, str]:
    """slug (filename stem, cross-checked against Metadata `Slug` when present), epic_id
    (Metadata `**Epic ID**` row when present, else ""), phase (Metadata `Phase` row, else
    `Phase N` in the header line, else "Unknown"), doc path.

    `epic_id` supports the old epic-identity convention, where an epic's Metadata table
    carries `| **Epic ID** | e01 |` instead of a `**Slug**` row. The epic's filename stem
    (e.g. `e01-core-standard-templates`) stays the canonical identifier shown in the
    generated Epics table; `epic_id` is additionally used to resolve feature docs whose
    `Part of epic:` line references the short ID (`e01`) rather than the full slug.
    """
    text = path.read_text(encoding="utf-8")
    slug = path.stem

    phase = "Unknown"
    m = _METADATA_ROW_RE.search(text)
    if m:
        phase = m.group(1).strip()
    else:
        m2 = _EPIC_SLUG_PHASE_RE.search(text)
        if m2:
            phase = f"Phase {m2.group(1).rstrip('.')}"

    epic_id = ""
    m_id = _EPIC_ID_ROW_RE.search(text)
    if m_id:
        epic_id = m_id.group(1).strip()

    return {"slug": slug, "epic_id": epic_id, "phase": phase, "path": path.name}


def parse_product_brief_epic_phases(product_brief_path: Path) -> dict[str, str]:
    """Map epic ID/slug -> Phase, read from `product-brief.md`'s "Epic Index" table(s).

    The Epic Index is the initiative's own durable release-order record (see its
    "Release order is this Epic Index" note), so it is a reliable cross-reference for an
    epic's phase even when the epic's own doc omits a `**Phase**` Metadata row. Both
    table conventions used across initiatives are recognized: the old positional-ID
    table (`| e01 | ... | Phase 1 | ... |`) and the v2 slug table
    (`| [`slug`](epics/slug.md) | ... | Phase |`). Returns an empty dict (not an error)
    if `product-brief.md` doesn't exist or has no Epic Index table — callers treat that
    as "no fallback data available", not a fatal condition.
    """
    if not product_brief_path.is_file():
        return {}
    text = product_brief_path.read_text(encoding="utf-8")

    phases: dict[str, str] = {}
    for m in _BRIEF_EPIC_ROW_ID_RE.finditer(text):
        phases[m.group(1).strip().lower()] = m.group(2).strip()
    for m in _BRIEF_EPIC_ROW_SLUG_RE.finditer(text):
        phases[m.group(1).strip().lower()] = m.group(2).strip()
    return phases


def parse_feature(path: Path, known_epic_slugs: dict[str, str] | set[str] | None = None) -> dict[str, str]:
    """slug (filename stem), parent epic (`> Part of epic: [slug](...)` line; else, for
    meta-features whose line is prose like `Part of epic: SAA-MEMORY — Layered Memory`,
    the leading token resolved case-insensitively against `known_epic_slugs`; else
    "Unknown"), one-line scope (first sentence of the `## What` section body — raises
    ValueError if that section is missing or empty), doc path.

    `known_epic_slugs` may be a plain set of epic slugs (legacy call shape, still
    supported), or a dict mapping every known lookup key (an epic's filename slug *and*,
    for old-convention epics, its short `**Epic ID**` — e.g. both `e01-core-standard-
    templates` and `e01`) to that epic's canonical slug, so a feature referencing the
    short ID resolves to the same identifier the Epics table lists it under.

    A `Part of epic:` line that is present but resolves to neither a markdown link nor a
    known epic slug/ID is not fatal (one unparseable/unresolvable parent shouldn't block
    indexing the rest of the initiative) — it warns to stderr and falls back to "Unknown".

    The "Part of epic:" label and its link/prose target are sometimes split across
    consecutive blockquote (`>`) lines purely for source wrapping (markdown renders them
    as one continuous line regardless). `_join_blockquote_runs` normalizes those runs
    before either regex runs, so a link split mid-phrase resolves the same as if it were
    on one line.
    """
    text = path.read_text(encoding="utf-8")
    slug = path.stem
    known_epic_slugs = known_epic_slugs or {}
    if isinstance(known_epic_slugs, set):
        known_epic_slugs = {s: s for s in known_epic_slugs}

    normalized = _join_blockquote_runs(text)

    parent = "Unknown"
    m = _PART_OF_EPIC_RE.search(normalized)
    if m:
        parent = m.group(1).strip()
    else:
        m_prose = _PART_OF_EPIC_PROSE_RE.search(normalized)
        if m_prose:
            candidate = m_prose.group(1).strip()
            lookup = {k.lower(): v for k, v in known_epic_slugs.items()}
            resolved = lookup.get(candidate.lower())
            if resolved:
                parent = resolved
            else:
                print(
                    f"warning: unresolved 'Part of epic:' value {candidate!r} in {path} "
                    "(no matching epic slug); defaulting parent to Unknown",
                    file=sys.stderr,
                )

    what = _section_body(text, "What")
    if what is None or not what.strip():
        raise ValueError(
            f"malformed feature doc (missing or empty '## What' section): {path}"
        )
    scope = extract_first_sentence(what)
    if not scope:
        raise ValueError(
            f"malformed feature doc (missing or empty '## What' section): {path}"
        )

    return {"slug": slug, "parent_epic": parent, "scope": scope, "path": path.name}


def parse_adr(path: Path) -> dict[str, str]:
    """number + title (from `# ADR-NNN: Title` heading — raises ValueError if missing),
    status (first non-blank line after `## Status` — raises ValueError if that section
    is missing), doc path.
    """
    text = path.read_text(encoding="utf-8")

    heading_match = _ADR_HEADING_RE.search(text)
    if not heading_match:
        raise ValueError(f"malformed ADR doc (missing '# ADR-NNN: Title' heading): {path}")
    number = heading_match.group(1)
    title = heading_match.group(2)

    status_body = _section_body(text, "Status")
    if status_body is None or not status_body.strip():
        raise ValueError(f"malformed ADR doc (missing or empty '## Status' section): {path}")
    status = status_body.splitlines()[0].strip()
    if not status:
        raise ValueError(f"malformed ADR doc (missing or empty '## Status' section): {path}")

    return {"number": number, "title": title, "status": status, "path": path.name}


def collect_epics(
    epics_dir: Path, product_brief_phases: dict[str, str] | None = None
) -> list[dict[str, str]]:
    """Parse every epic doc in `epics_dir`, sorted by slug.

    `product_brief_phases` (epic ID/slug, lowercased -> Phase, as returned by
    `parse_product_brief_epic_phases`) is an optional fallback: when an epic doc has no
    `**Phase**` Metadata row of its own (`parse_epic` returns "Unknown"), look it up by
    the epic's canonical slug and, for old-convention epics, its short Epic ID. If
    neither key is present in `product_brief_phases` (or no product brief was supplied),
    "Unknown" is left as-is — a genuine data-completeness gap in the source docs, not a
    parsing bug, so it is never silently invented.
    """
    if not epics_dir.is_dir():
        return []
    epics = [parse_epic(p) for p in sorted(epics_dir.glob("*.md"))]
    if product_brief_phases:
        for e in epics:
            if e["phase"] != "Unknown":
                continue
            fallback = product_brief_phases.get(e["slug"].lower())
            if fallback is None and e.get("epic_id"):
                fallback = product_brief_phases.get(e["epic_id"].lower())
            if fallback:
                e["phase"] = fallback
    return sorted(epics, key=lambda e: e["slug"])


def collect_features(
    features_dir: Path, known_epic_slugs: dict[str, str] | set[str] | None = None
) -> list[dict[str, str]]:
    if not features_dir.is_dir():
        return []
    features = [
        parse_feature(p, known_epic_slugs) for p in sorted(features_dir.glob("*.md"))
    ]
    return sorted(features, key=lambda f: f["slug"])


def collect_adrs(adrs_dir: Path) -> list[dict[str, str]]:
    if not adrs_dir.is_dir():
        return []
    adrs = []
    for p in sorted(adrs_dir.glob("*.md")):
        if not _ADR_FILENAME_RE.match(p.name):
            continue  # excludes adr-list.md and any other non-numbered file
        adrs.append(parse_adr(p))
    return sorted(adrs, key=lambda a: int(a["number"]))


def render_index(
    epics: list[dict[str, str]],
    features: list[dict[str, str]],
    adrs: list[dict[str, str]],
) -> str:
    lines: list[str] = []
    lines.append("# Initiative Index")
    lines.append("")
    lines.append(
        "> Generated by `scripts/generate_initiative_index.py`. Do not hand-edit — "
        "regenerate instead."
    )
    lines.append("")

    lines.append("## Epics")
    lines.append("")
    lines.append("| Slug | Phase | Doc |")
    lines.append("|------|-------|-----|")
    for e in epics:
        lines.append(f"| {e['slug']} | {e['phase']} | epics/{e['path']} |")
    lines.append("")

    lines.append("## Features")
    lines.append("")
    lines.append("| Slug | Parent Epic | Scope | Doc |")
    lines.append("|------|--------------|-------|-----|")
    for f in features:
        lines.append(
            f"| {f['slug']} | {f['parent_epic']} | {f['scope']} | features/{f['path']} |"
        )
    lines.append("")

    lines.append("## ADRs")
    lines.append("")
    lines.append("| Number | Title | Status | Doc |")
    lines.append("|--------|-------|--------|-----|")
    for a in adrs:
        lines.append(f"| ADR-{a['number']} | {a['title']} | {a['status']} | adrs/{a['path']} |")
    lines.append("")

    return "\n".join(lines)


def generate_index(initiative_path: Path) -> str:
    """Build INDEX.md content for `initiative_path` and write it there. Returns the
    written content.
    """
    initiative_path = Path(initiative_path)
    if not (initiative_path / "epics").is_dir():
        raise ValueError(
            f"not a valid initiative directory (no 'epics/' subdirectory): {initiative_path}"
        )

    product_brief_phases = parse_product_brief_epic_phases(
        initiative_path / "product-brief.md"
    )
    epics = collect_epics(initiative_path / "epics", product_brief_phases)
    # Every epic resolves to its own filename slug (the canonical identifier used in the
    # Epics table); old-convention epics additionally resolve via their short Epic ID, so
    # a feature's `Part of epic: e01` matches the same row `e01-core-standard-templates`
    # that the Epics table lists.
    known_epic_slugs: dict[str, str] = {}
    for e in epics:
        known_epic_slugs[e["slug"]] = e["slug"]
        if e.get("epic_id"):
            known_epic_slugs[e["epic_id"]] = e["slug"]
    features = collect_features(initiative_path / "features", known_epic_slugs)
    adrs = collect_adrs(initiative_path / "adrs")

    content = render_index(epics, features, adrs)
    (initiative_path / "INDEX.md").write_text(content, encoding="utf-8")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic INDEX.md for one initiative directory"
    )
    parser.add_argument(
        "--initiative-path",
        required=True,
        help="Path to initiatives/<slug>/ (absolute or relative to CWD)",
    )
    args = parser.parse_args()
    generate_index(Path(args.initiative_path))


if __name__ == "__main__":
    main()
