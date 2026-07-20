from __future__ import annotations

import sys
import unittest
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REVIEW_DIR))

from build_review import RFC_PATH, render_rfc
from rfc_toc import (
    END_MARKER,
    START_MARKER,
    dashboard_markdown,
    replace_generated_block,
    top_level_sections,
)


class RfcTableOfContentsTests(unittest.TestCase):
    def test_committed_toc_is_current_and_covers_every_level_two_heading(self) -> None:
        source = RFC_PATH.read_text(encoding="utf-8")
        self.assertEqual(replace_generated_block(source), source)
        sections = top_level_sections(source)
        block = source.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0]
        for title, anchor in sections:
            self.assertIn(f"- [{title}](#{anchor})", block)

    def test_dashboard_projection_uses_safe_markdown_instead_of_raw_html(self) -> None:
        source = RFC_PATH.read_text(encoding="utf-8")
        projected = dashboard_markdown(source)
        self.assertIn("## Table of Contents", projected)
        self.assertIn(
            "- [Agent Surface Manifest](#agent-surface-manifest-2)",
            projected,
        )
        self.assertNotIn("<details>", projected)
        self.assertNotIn(START_MARKER, projected)
        self.assertNotIn(END_MARKER, projected)

    def test_canonical_toc_uses_github_duplicate_suffixes(self) -> None:
        source = RFC_PATH.read_text(encoding="utf-8")
        block = source.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0]
        self.assertIn(
            "- [Agent Surface Manifest](#agent-surface-manifest-1)",
            block,
        )

    def test_dashboard_renderer_preserves_existing_review_anchor_ids(self) -> None:
        _, heading_ids = render_rfc()
        self.assertEqual(heading_ids["Abstract"], "abstract")
        self.assertEqual(heading_ids["Surface Hash"], "surface-hash")


if __name__ == "__main__":
    unittest.main()
