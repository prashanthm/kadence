"""Published reusable workflow must match its template source."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/.github/workflows/index-regenerate.yml"
PUBLISHED = ROOT / ".github/workflows/index-regenerate.yml"


def test_index_regenerate_workflow_published_matches_template():
    assert TEMPLATE.is_file(), "template workflow missing"
    assert PUBLISHED.is_file(), "published workflow missing at .github/workflows/"
    assert TEMPLATE.read_text(encoding="utf-8") == PUBLISHED.read_text(encoding="utf-8")
