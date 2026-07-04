"""Tests for generate_initiative_index.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_initiative_index import (  # noqa: E402
    collect_adrs,
    collect_epics,
    collect_features,
    extract_first_sentence,
    generate_index,
    parse_adr,
    parse_epic,
    parse_feature,
    parse_product_brief_epic_phases,
    render_index,
)


# --- extract_first_sentence ---


def test_extract_first_sentence_basic():
    assert extract_first_sentence("Do the thing. Then do another thing.") == "Do the thing."


def test_extract_first_sentence_ignores_abbreviation_period():
    text = "Use the gateway, e.g. for cost routing. It also handles fallback."
    assert extract_first_sentence(text) == "Use the gateway, e.g. for cost routing."


def test_extract_first_sentence_strips_bold_and_collapses_whitespace():
    text = "**ADR-007: Core Agent Stack** — the decision record.\nMore text follows."
    assert extract_first_sentence(text) == "ADR-007: Core Agent Stack — the decision record."


def test_extract_first_sentence_no_period_returns_whole_text():
    assert extract_first_sentence("no terminal period here") == "no terminal period here"


# --- parse_epic ---


def test_parse_epic_reads_metadata_phase(tmp_path):
    epic = tmp_path / "saa-memory.md"
    epic.write_text(
        "# SAA-MEMORY — Layered Memory\n\n"
        "> Epic slug: `saa-memory`. Part of initiative [x](../initiative.md), Phase 2.\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| **Slug** | saa-memory |\n"
        "| **Phase** | Phase 2 |\n",
        encoding="utf-8",
    )
    result = parse_epic(epic)
    assert result == {
        "slug": "saa-memory",
        "epic_id": "",
        "phase": "Phase 2",
        "path": "saa-memory.md",
    }


def test_parse_epic_falls_back_to_header_line_when_no_metadata_table(tmp_path):
    epic = tmp_path / "saa-arch.md"
    epic.write_text(
        "# SAA-ARCH\n\n> Epic slug: `saa-arch`. Part of initiative [x](../initiative.md), Phase 1.\n",
        encoding="utf-8",
    )
    result = parse_epic(epic)
    assert result["phase"] == "Phase 1"


def test_parse_epic_unknown_phase_when_absent(tmp_path):
    epic = tmp_path / "bare.md"
    epic.write_text("# Bare epic\n\nNo phase info at all.\n", encoding="utf-8")
    result = parse_epic(epic)
    assert result["phase"] == "Unknown"


def test_parse_epic_reads_epic_id_old_convention(tmp_path):
    # Old epic-identity convention: a `**Epic ID**` Metadata row instead of `**Slug**`.
    # The filename stem stays the canonical slug; epic_id is captured separately so
    # features referencing the short ID (e.g. "e01") can still resolve.
    epic = tmp_path / "e01-core-standard-templates.md"
    epic.write_text(
        "# e01 — Core Standard, Templates & Samples\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| **Epic ID** | e01 |\n"
        "| **Phase** | Phase 1 |\n",
        encoding="utf-8",
    )
    result = parse_epic(epic)
    assert result == {
        "slug": "e01-core-standard-templates",
        "epic_id": "e01",
        "phase": "Phase 1",
        "path": "e01-core-standard-templates.md",
    }


def test_parse_epic_no_epic_id_row_defaults_empty(tmp_path):
    epic = tmp_path / "saa-arch.md"
    epic.write_text(
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n| **Slug** | saa-arch |\n",
        encoding="utf-8",
    )
    result = parse_epic(epic)
    assert result["epic_id"] == ""


# --- parse_product_brief_epic_phases ---


def test_parse_product_brief_epic_phases_old_id_convention_table(tmp_path):
    # Real-world shape (ai-native-development initiative): the Epic Index table keys
    # rows by positional ID with a Milestone/Phase column, e.g.:
    #   | ID | Epic | Description | Milestone | GitHub |
    #   | e01 | Core Standard... | ... | Phase 1 | [#55](...) |
    brief = tmp_path / "product-brief.md"
    brief.write_text(
        "## Epic Index\n\n"
        "| ID | Epic | Description | Milestone | GitHub |\n"
        "|----|------|------------|----------|--------|\n"
        "| e01 | Core Standard, Templates & Samples | Lifecycle standard | Phase 1 "
        "| [#55](https://github.com/x/y/issues/55) |\n"
        "| e06 | Engineering Metrics Scorecard | Weekly report | Phase 2 "
        "| [#60](https://github.com/x/y/issues/60) |\n"
        "| e10 | Release Gate Verification | Single gate | Phase 3 |\n",
        encoding="utf-8",
    )
    result = parse_product_brief_epic_phases(brief)
    assert result["e01"] == "Phase 1"
    assert result["e06"] == "Phase 2"
    assert result["e10"] == "Phase 3"


def test_parse_product_brief_epic_phases_v2_slug_convention_table(tmp_path):
    brief = tmp_path / "product-brief.md"
    brief.write_text(
        "## Epic Index\n\n"
        "| Slug | Epic | Description | Phase |\n"
        "|------|------|-------------|-------|\n"
        "| [`loop-enforcement`](epics/loop-enforcement.md) | Loop Enforcement "
        "| kadence doctor | v2 (first) |\n",
        encoding="utf-8",
    )
    result = parse_product_brief_epic_phases(brief)
    assert result["loop-enforcement"] == "v2 (first)"


def test_parse_product_brief_epic_phases_missing_file_returns_empty_dict(tmp_path):
    assert parse_product_brief_epic_phases(tmp_path / "does-not-exist.md") == {}


def test_parse_product_brief_epic_phases_no_epic_index_table_returns_empty_dict(tmp_path):
    brief = tmp_path / "product-brief.md"
    brief.write_text("# Product Brief\n\nNo epic index here.\n", encoding="utf-8")
    assert parse_product_brief_epic_phases(brief) == {}


# --- parse_feature ---


def test_parse_feature_extracts_what_and_parent(tmp_path):
    feature = tmp_path / "e03-f05-layered-memory.md"
    feature.write_text(
        "# Layered Memory\n\n"
        "> Part of epic: [saa-runtime](../epics/saa-runtime.md)\n\n"
        "## What\n\n"
        "Implement the three-tier memory model. More detail follows here.\n\n"
        "## Why\n\nBecause reasons.\n",
        encoding="utf-8",
    )
    result = parse_feature(feature)
    assert result["slug"] == "e03-f05-layered-memory"
    assert result["parent_epic"] == "saa-runtime"
    assert result["scope"] == "Implement the three-tier memory model."
    assert result["path"] == "e03-f05-layered-memory.md"


def test_parse_feature_unknown_parent_when_missing(tmp_path):
    feature = tmp_path / "orphan.md"
    feature.write_text("# Orphan\n\n## What\n\nDoes a thing.\n", encoding="utf-8")
    result = parse_feature(feature)
    assert result["parent_epic"] == "Unknown"


def test_parse_feature_resolves_prose_part_of_epic_against_known_slugs(tmp_path):
    # Real-world shape: adr-NNN-decision.md meta-features write "Part of epic:" as prose
    # (`SLUG — Title`), not a markdown link. The slug case in prose (SAA-MEMORY) commonly
    # differs from the epic file's actual slug (saa-memory); resolution must be
    # case-insensitive against known epic slugs parsed in the same run.
    feature = tmp_path / "adr-017-decision.md"
    feature.write_text(
        "# ADR-017 Decision Record\n\n"
        "> Part of epic: SAA-MEMORY — Layered Memory\n\n"
        "## What\n\nRecord the ADR-017 decision. More detail follows.\n",
        encoding="utf-8",
    )
    result = parse_feature(feature, known_epic_slugs={"saa-memory", "saa-runtime"})
    assert result["parent_epic"] == "saa-memory"


def test_parse_feature_resolves_short_epic_id_against_canonical_slug(tmp_path):
    # Real-world shape (ai-native-development initiative): the epic uses the old
    # `**Epic ID**` convention (filename `e01-core-standard-templates.md`, Epic ID
    # `e01`), and the feature's "Part of epic:" line references the short ID in prose,
    # e.g. "> Part of epic: e01 — Core Standard, Templates & Samples". Resolution must
    # map the short ID back to the epic's canonical (filename-stem) slug so the
    # Features table's Parent Epic column cross-references the same identifier the
    # Epics table lists that epic under.
    feature = tmp_path / "e01-f01-lifecycle-standard.md"
    feature.write_text(
        "# Lifecycle Standard\n\n"
        "> Part of epic: e01 — Core Standard, Templates & Samples  \n"
        "> **Feature ID:** e01-f01  \n\n"
        "## What\n\nThe locked SDLC specification. More detail follows.\n",
        encoding="utf-8",
    )
    known_epic_slugs = {
        "e01-core-standard-templates": "e01-core-standard-templates",
        "e01": "e01-core-standard-templates",
    }
    result = parse_feature(feature, known_epic_slugs=known_epic_slugs)
    assert result["parent_epic"] == "e01-core-standard-templates"


def test_parse_feature_accepts_legacy_set_shaped_known_epic_slugs(tmp_path):
    # Backward compatibility: callers passing a plain set() of slugs (the pre-fix
    # call shape) must still resolve correctly.
    feature = tmp_path / "adr-017-decision.md"
    feature.write_text(
        "# ADR-017 Decision Record\n\n"
        "> Part of epic: SAA-MEMORY — Layered Memory\n\n"
        "## What\n\nRecord the ADR-017 decision. More detail follows.\n",
        encoding="utf-8",
    )
    result = parse_feature(feature, known_epic_slugs={"saa-memory", "saa-runtime"})
    assert result["parent_epic"] == "saa-memory"


def test_parse_feature_resolves_multiline_blockquote_backtick_link(tmp_path):
    # Real-world shape (ai-native-development initiative, v2 features): the "Part of
    # epic:" label and its markdown link are split across two blockquote lines, and the
    # link text itself is backtick-wrapped, e.g. (from
    # features/initiative-index-generator.md):
    #   > Slug: `initiative-index-generator` · Part of epic:
    #   > [`planning-index-and-context-discovery`](../epics/planning-index-and-context-discovery.md) ·
    #   > GitHub Feature: ...
    # Both the blockquote-line-join normalization AND the backtick-tolerant link-text
    # capture are required together to resolve this: joining alone still leaves the
    # captured slug wrapped in backticks (`` `planning-index-and-context-discovery` ``),
    # which would not match the known epic slug.
    feature = tmp_path / "initiative-index-generator.md"
    feature.write_text(
        "# Initiative Index Generator\n\n"
        "> Slug: `initiative-index-generator` · Part of epic:\n"
        "> [`planning-index-and-context-discovery`]"
        "(../epics/planning-index-and-context-discovery.md) ·\n"
        "> GitHub Feature: [x](https://example.com/22)\n\n"
        "## What\n\nGenerate the initiative INDEX.md. More detail follows.\n",
        encoding="utf-8",
    )
    result = parse_feature(
        feature, known_epic_slugs={"planning-index-and-context-discovery"}
    )
    assert result["parent_epic"] == "planning-index-and-context-discovery"


def test_parse_feature_resolves_single_line_backtick_link_without_blockquote_split(tmp_path):
    # Isolates the backtick-tolerant capture fix from the blockquote-join fix: the link
    # is on a single line (no multi-line split), but the link text is still
    # backtick-wrapped. Must resolve on its own, without depending on normalization.
    feature = tmp_path / "loop-doctor-harness.md"
    feature.write_text(
        "# Loop Doctor Harness\n\n"
        "> Part of epic: [`loop-enforcement`](../epics/loop-enforcement.md)\n\n"
        "## What\n\nA doctor harness for the loop. More detail follows.\n",
        encoding="utf-8",
    )
    result = parse_feature(feature, known_epic_slugs={"loop-enforcement"})
    assert result["parent_epic"] == "loop-enforcement"


def test_parse_feature_prose_part_of_epic_unresolved_falls_back_to_unknown(tmp_path, capsys):
    # Prose is present but doesn't match any known epic slug: warn to stderr, don't
    # crash, and don't invent a wrong parent — final fallback stays "Unknown".
    feature = tmp_path / "adr-999-decision.md"
    feature.write_text(
        "# ADR-999 Decision Record\n\n"
        "> Part of epic: SAA-NONEXISTENT — Ghost Epic\n\n"
        "## What\n\nRecord a decision with no matching epic.\n",
        encoding="utf-8",
    )
    result = parse_feature(feature, known_epic_slugs={"saa-memory", "saa-runtime"})
    assert result["parent_epic"] == "Unknown"
    assert "SAA-NONEXISTENT" in capsys.readouterr().err


def test_parse_feature_missing_what_section_raises(tmp_path):
    feature = tmp_path / "malformed.md"
    feature.write_text(
        "# Malformed\n\n> Part of epic: [x](../epics/x.md)\n\n## Why\n\nNo What section.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed.md"):
        parse_feature(feature)


def test_parse_feature_empty_what_section_raises(tmp_path):
    feature = tmp_path / "empty_what.md"
    feature.write_text(
        "# Empty What\n\n## What\n\n## Why\n\nSomething.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="empty_what.md"):
        parse_feature(feature)


# --- parse_adr ---


def test_parse_adr_reads_number_title_status(tmp_path):
    adr = tmp_path / "adr-017-memory-architecture.md"
    adr.write_text(
        "# ADR-017: Memory Architecture\n\n"
        "GitHub Issue: https://example.com/332\n\n\n"
        "## Status\n\nAccepted\n\n## Context\n\nBlah.\n",
        encoding="utf-8",
    )
    result = parse_adr(adr)
    assert result == {
        "number": "017",
        "title": "Memory Architecture",
        "status": "Accepted",
        "path": "adr-017-memory-architecture.md",
    }


def test_parse_adr_missing_heading_raises(tmp_path):
    adr = tmp_path / "adr-999-bad.md"
    adr.write_text("No heading here.\n\n## Status\n\nAccepted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="adr-999-bad.md"):
        parse_adr(adr)


def test_parse_adr_missing_status_raises(tmp_path):
    adr = tmp_path / "adr-998-nostatus.md"
    adr.write_text("# ADR-998: No Status\n\n## Context\n\nBlah.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="adr-998-nostatus.md"):
        parse_adr(adr)


def test_parse_adr_empty_status_raises(tmp_path):
    adr = tmp_path / "adr-997-emptystatus.md"
    adr.write_text("# ADR-997: Empty Status\n\n## Status\n\n## Context\n\nBlah.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="adr-997-emptystatus.md"):
        parse_adr(adr)


# --- collect_* : empty / absent directories ---


def test_collect_features_empty_dir_returns_empty_list(tmp_path):
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    assert collect_features(features_dir) == []


def test_collect_features_absent_dir_returns_empty_list(tmp_path):
    assert collect_features(tmp_path / "does-not-exist") == []


def test_collect_adrs_empty_dir_returns_empty_list(tmp_path):
    adrs_dir = tmp_path / "adrs"
    adrs_dir.mkdir()
    assert collect_adrs(adrs_dir) == []


def test_collect_adrs_excludes_adr_list_file(tmp_path):
    adrs_dir = tmp_path / "adrs"
    adrs_dir.mkdir()
    (adrs_dir / "adr-list.md").write_text("# Catalog\n\nNot a real ADR.\n", encoding="utf-8")
    (adrs_dir / "adr-001-x.md").write_text(
        "# ADR-001: X\n\n## Status\n\nAccepted\n", encoding="utf-8"
    )
    result = collect_adrs(adrs_dir)
    assert len(result) == 1
    assert result[0]["number"] == "001"


def test_collect_epics_sorted_by_slug(tmp_path):
    epics_dir = tmp_path / "epics"
    epics_dir.mkdir()
    (epics_dir / "saa-runtime.md").write_text(
        "> Epic slug: `saa-runtime`. Phase 1.\n", encoding="utf-8"
    )
    (epics_dir / "saa-arch.md").write_text(
        "> Epic slug: `saa-arch`. Phase 1.\n", encoding="utf-8"
    )
    result = collect_epics(epics_dir)
    assert [e["slug"] for e in result] == ["saa-arch", "saa-runtime"]


def test_collect_epics_applies_product_brief_phase_fallback_by_epic_id(tmp_path):
    # Old-convention epic with no **Phase** row of its own resolves via the
    # product-brief's Epic Index, keyed by the epic's short Epic ID.
    epics_dir = tmp_path / "epics"
    epics_dir.mkdir()
    (epics_dir / "e01-core-standard-templates.md").write_text(
        "# e01 — Core Standard\n\n"
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n| **Epic ID** | e01 |\n",
        encoding="utf-8",
    )
    result = collect_epics(epics_dir, product_brief_phases={"e01": "Phase 1"})
    assert result[0]["phase"] == "Phase 1"


def test_collect_epics_applies_product_brief_phase_fallback_by_slug(tmp_path):
    epics_dir = tmp_path / "epics"
    epics_dir.mkdir()
    (epics_dir / "loop-enforcement.md").write_text(
        "# Loop Enforcement\n\n"
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        "| **Slug** | loop-enforcement |\n",
        encoding="utf-8",
    )
    result = collect_epics(
        epics_dir, product_brief_phases={"loop-enforcement": "v2 (first)"}
    )
    assert result[0]["phase"] == "v2 (first)"


def test_collect_epics_own_phase_row_wins_over_product_brief_fallback(tmp_path):
    # The epic doc's own **Phase** Metadata row is authoritative; the product-brief
    # fallback only fills in when the epic doc itself has no phase info at all.
    epics_dir = tmp_path / "epics"
    epics_dir.mkdir()
    (epics_dir / "saa-memory.md").write_text(
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        "| **Slug** | saa-memory |\n| **Phase** | Phase 2 |\n",
        encoding="utf-8",
    )
    result = collect_epics(epics_dir, product_brief_phases={"saa-memory": "Phase 9"})
    assert result[0]["phase"] == "Phase 2"


def test_collect_epics_stays_unknown_when_no_product_brief_data_available(tmp_path):
    # Genuine source-doc gap: the epic doc has no **Phase** row, and the product brief
    # (or its Epic Index) has no entry for this epic either. "Unknown" is the correct,
    # honest output here -- not a bug to paper over with an invented value.
    epics_dir = tmp_path / "epics"
    epics_dir.mkdir()
    (epics_dir / "mystery-epic.md").write_text(
        "# Mystery Epic\n\nNo phase info anywhere.\n", encoding="utf-8"
    )
    result = collect_epics(epics_dir, product_brief_phases={"some-other-epic": "Phase 1"})
    assert result[0]["phase"] == "Unknown"

    # Also true with no product_brief_phases supplied at all.
    result_no_fallback = collect_epics(epics_dir)
    assert result_no_fallback[0]["phase"] == "Unknown"


def test_collect_adrs_sorted_numerically_not_lexically(tmp_path):
    adrs_dir = tmp_path / "adrs"
    adrs_dir.mkdir()
    (adrs_dir / "adr-002-x.md").write_text("# ADR-002: X\n\n## Status\n\nAccepted\n", encoding="utf-8")
    (adrs_dir / "adr-010-y.md").write_text("# ADR-010: Y\n\n## Status\n\nAccepted\n", encoding="utf-8")
    result = collect_adrs(adrs_dir)
    assert [a["number"] for a in result] == ["002", "010"]


# --- render_index / generate_index : full tree + determinism ---


def _build_initiative(tmp_path: Path) -> Path:
    initiative = tmp_path / "initiatives" / "demo"
    (initiative / "epics").mkdir(parents=True)
    (initiative / "features").mkdir(parents=True)
    (initiative / "adrs").mkdir(parents=True)

    (initiative / "epics" / "demo-epic.md").write_text(
        "> Epic slug: `demo-epic`. Phase 1.\n\n"
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        "| **Phase** | Phase 1 |\n",
        encoding="utf-8",
    )
    (initiative / "features" / "demo-feature.md").write_text(
        "> Part of epic: [demo-epic](../epics/demo-epic.md)\n\n"
        "## What\n\nDoes the demo thing.\n",
        encoding="utf-8",
    )
    (initiative / "adrs" / "adr-001-demo.md").write_text(
        "# ADR-001: Demo Decision\n\n## Status\n\nAccepted\n",
        encoding="utf-8",
    )
    return initiative


def test_generate_index_full_tree_writes_expected_rows(tmp_path):
    initiative = _build_initiative(tmp_path)
    content = generate_index(initiative)

    assert "demo-epic" in content
    assert "Phase 1" in content
    assert "demo-feature" in content
    assert "Does the demo thing." in content
    assert "ADR-001" in content
    assert "Demo Decision" in content
    assert "Accepted" in content

    written = (initiative / "INDEX.md").read_text(encoding="utf-8")
    assert written == content


def test_generate_index_deterministic_across_runs(tmp_path):
    initiative = _build_initiative(tmp_path)
    first = generate_index(initiative)
    second = generate_index(initiative)
    assert first == second

    first_bytes = (initiative / "INDEX.md").read_bytes()
    generate_index(initiative)
    second_bytes = (initiative / "INDEX.md").read_bytes()
    assert first_bytes == second_bytes


def test_generate_index_missing_what_fails_loud(tmp_path):
    initiative = _build_initiative(tmp_path)
    (initiative / "features" / "broken.md").write_text(
        "> Part of epic: [demo-epic](../epics/demo-epic.md)\n\n## Why\n\nNo What here.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="broken.md"):
        generate_index(initiative)
    # No partial INDEX.md left behind from this failed run's write step.
    assert not (initiative / "INDEX.md").exists()


def test_generate_index_resolves_prose_part_of_epic_end_to_end(tmp_path):
    initiative = _build_initiative(tmp_path)
    (initiative / "features" / "adr-017-decision.md").write_text(
        "# ADR-017 Decision Record\n\n"
        "> Part of epic: DEMO-EPIC — Demo\n\n"
        "## What\n\nRecord the ADR-017 decision.\n",
        encoding="utf-8",
    )
    content = generate_index(initiative)
    assert "| adr-017-decision | demo-epic |" in content


def test_generate_index_resolves_epic_id_convention_end_to_end(tmp_path):
    # Old epic-identity convention: epic's Metadata table carries `**Epic ID**` (not
    # `**Slug**`), and a feature's "Part of epic:" line references that short ID in
    # prose. The Features table's Parent Epic column must resolve to the SAME
    # identifier (filename slug) the Epics table lists that epic under, so the two
    # tables in the generated INDEX.md cross-reference correctly.
    initiative = tmp_path / "initiatives" / "epic-id-demo"
    (initiative / "epics").mkdir(parents=True)
    (initiative / "features").mkdir(parents=True)

    (initiative / "epics" / "e01-core-standard-templates.md").write_text(
        "# e01 — Core Standard, Templates & Samples\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| **Epic ID** | e01 |\n"
        "| **Phase** | Phase 1 |\n",
        encoding="utf-8",
    )
    (initiative / "features" / "e01-f01-lifecycle-standard.md").write_text(
        "# Lifecycle Standard\n\n"
        "> Part of epic: e01 — Core Standard, Templates & Samples  \n"
        "> **Feature ID:** e01-f01  \n\n"
        "## What\n\nThe locked SDLC specification. More detail follows.\n",
        encoding="utf-8",
    )
    content = generate_index(initiative)

    assert "| e01-core-standard-templates | Phase 1 |" in content
    assert (
        "| e01-f01-lifecycle-standard | e01-core-standard-templates |" in content
    )
    assert "Unknown" not in content


def test_generate_index_ai_native_development_regression_fixture(tmp_path):
    # Regression fixture mirroring the real ai-native-development initiative shape:
    # a mix of old-convention epics (**Epic ID**) and new-convention epics (**Slug**),
    # with features referencing both by prose short-ID and by markdown-link slug.
    initiative = tmp_path / "initiatives" / "ai-native-development"
    (initiative / "epics").mkdir(parents=True)
    (initiative / "features").mkdir(parents=True)

    (initiative / "epics" / "e01-core-standard-templates.md").write_text(
        "# e01 — Core Standard, Templates & Samples\n\n"
        "> **Status:** Done\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| **Epic ID** | e01 |\n"
        "| **Status** | Done |\n",
        encoding="utf-8",
    )
    (initiative / "epics" / "loop-enforcement.md").write_text(
        "# Loop Enforcement\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| **Slug** | loop-enforcement |\n"
        "| **Phase** | v2 (lands first) |\n",
        encoding="utf-8",
    )
    (initiative / "features" / "e01-f01-lifecycle-standard.md").write_text(
        "# Lifecycle Standard\n\n"
        "> Part of epic: e01 — Core Standard, Templates & Samples  \n"
        "> **Feature ID:** e01-f01  \n\n"
        "## What\n\nThe locked SDLC specification in `standard/`. More detail follows.\n",
        encoding="utf-8",
    )
    (initiative / "features" / "loop-doctor-harness.md").write_text(
        "# Loop Doctor Harness\n\n"
        "> Slug: `loop-doctor-harness` · Part of epic: "
        "[`loop-enforcement`](../epics/loop-enforcement.md)\n\n"
        "## What\n\nA doctor harness for the loop. More detail follows.\n",
        encoding="utf-8",
    )
    # A genuinely orphaned feature (empty "Part of epic:" target) must still fall
    # back to Unknown rather than a forced/incorrect resolution.
    (initiative / "features" / "agents-md-bootstrap.md").write_text(
        "# AGENTS.md Bootstrap\n\n"
        "> Slug: `agents-md-bootstrap` · Part of epic:\n\n"
        "## What\n\nBootstrap the AGENTS.md files. More detail follows.\n",
        encoding="utf-8",
    )

    content = generate_index(initiative)

    assert "| e01-f01-lifecycle-standard | e01-core-standard-templates |" in content
    # loop-doctor-harness's "Part of epic:" link text is backtick-wrapped
    # (`` [`loop-enforcement`](...) ``) on a single line — resolves via the widened
    # _PART_OF_EPIC_RE (backticks stripped from the captured slug).
    assert "| loop-doctor-harness | loop-enforcement |" in content
    # agents-md-bootstrap's "Part of epic:" has no bracketed target at all (genuinely
    # orphaned) — must still fall back to Unknown rather than a forced/incorrect
    # resolution.
    assert "| agents-md-bootstrap | Unknown |" in content


def test_generate_index_reads_product_brief_phase_fallback_end_to_end(tmp_path):
    initiative = tmp_path / "initiatives" / "phase-fallback-demo"
    (initiative / "epics").mkdir(parents=True)

    (initiative / "epics" / "e01-core-standard-templates.md").write_text(
        "# e01 — Core Standard\n\n"
        "## Metadata\n\n| Field | Value |\n|-------|-------|\n| **Epic ID** | e01 |\n",
        encoding="utf-8",
    )
    (initiative / "product-brief.md").write_text(
        "## Epic Index\n\n"
        "| ID | Epic | Description | Milestone | GitHub |\n"
        "|----|------|------------|----------|--------|\n"
        "| e01 | Core Standard, Templates & Samples | Lifecycle standard | Phase 1 "
        "| [#55](https://github.com/x/y/issues/55) |\n",
        encoding="utf-8",
    )

    content = generate_index(initiative)
    assert "| e01-core-standard-templates | Phase 1 |" in content


def test_generate_index_empty_features_and_adrs_dirs_is_valid(tmp_path):
    initiative = tmp_path / "initiatives" / "sparse"
    (initiative / "epics").mkdir(parents=True)
    (initiative / "epics" / "e.md").write_text("> Epic slug: `e`. Phase 1.\n", encoding="utf-8")
    # features/ and adrs/ intentionally absent entirely.
    content = generate_index(initiative)
    assert "## Features" in content
    assert "## ADRs" in content


def test_generate_index_requires_epics_dir(tmp_path):
    initiative = tmp_path / "initiatives" / "no-epics"
    initiative.mkdir(parents=True)
    with pytest.raises(ValueError, match="epics"):
        generate_index(initiative)


def test_render_index_no_timestamps():
    content = render_index([], [], [])
    assert "generated" not in content.lower() or "Generated by" in content
    # No date-like tokens embedded (defensive: nothing resembling a timestamp).
    import re

    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", content)


# --- CLI end-to-end ---


def test_cli_writes_index_md(tmp_path):
    initiative = _build_initiative(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_initiative_index.py"
    result = subprocess.run(
        [sys.executable, str(script), "--initiative-path", str(initiative)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (initiative / "INDEX.md").exists()


def test_cli_exits_nonzero_on_malformed_doc(tmp_path):
    initiative = _build_initiative(tmp_path)
    (initiative / "adrs" / "adr-002-bad.md").write_text("no heading\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_initiative_index.py"
    result = subprocess.run(
        [sys.executable, str(script), "--initiative-path", str(initiative)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
