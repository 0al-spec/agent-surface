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
    dashboard_sections,
    replace_generated_block,
    top_level_sections,
)


class RfcTableOfContentsTests(unittest.TestCase):
    def test_modular_toc_projection_covers_every_level_two_heading(self) -> None:
        source = RFC_PATH.read_text(encoding="utf-8")
        projected = dashboard_markdown(source)
        for title, anchor in dashboard_sections(source):
            self.assertIn(f"- [{title}](#{anchor})", projected)

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

    def test_modular_aggregate_has_no_post_assembly_toc_mutation(self) -> None:
        source = RFC_PATH.read_text(encoding="utf-8")
        self.assertNotIn(START_MARKER, source)
        self.assertNotIn(END_MARKER, source)

    def test_dashboard_renderer_preserves_existing_review_anchor_ids(self) -> None:
        rendered, heading_ids = render_rfc()
        self.assertEqual(heading_ids["Abstract"], "abstract")
        self.assertEqual(heading_ids["Surface Hash"], "surface-hash")
        self.assertIn('id="agent-surface-manifest-2"', rendered)
        self.assertIn('href="#agent-surface-manifest-2"', rendered)
        self.assertNotIn('href="#agent-surface-manifest-1"', rendered)
        self.assertIn('id="agent-grant-2"', rendered)
        self.assertIn('href="#agent-grant-2"', rendered)
        self.assertNotIn('href="#agent-grant-1"', rendered)


if __name__ == "__main__":
    unittest.main()
