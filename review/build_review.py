#!/usr/bin/env python3
"""Build the standalone Agent Surface RFC review dashboard."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from markdown_it import MarkdownIt

from review_data import load_review_payload, normalize_reviews, validate_review_payload


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = Path(__file__).resolve().parent
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
DATA_PATH = REVIEW_DIR / "review-data.json"
TEMPLATE_PATH = REVIEW_DIR / "review-template.html"
STYLESHEET_PATH = REVIEW_DIR / "standalone.css"
OUTPUT_PATH = REVIEW_DIR / "agent-surface-rfc-review.html"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "section"


def render_rfc() -> tuple[str, dict[str, str]]:
    markdown = MarkdownIt("commonmark", {"html": False, "linkify": True})
    tokens = markdown.parse(RFC_PATH.read_text(encoding="utf-8"))
    occurrences: Counter[str] = Counter()
    headings: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)

    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content.strip()
        level = int(token.tag[1:])
        occurrences[title] += 1
        anchor_id = slugify(title)
        if occurrences[title] > 1:
            anchor_id = f"{anchor_id}-{occurrences[title]}"
        token.attrSet("id", anchor_id)
        token.attrSet("data-asp-heading", title)
        headings[title].append((level, anchor_id))

    heading_ids = {
        title: sorted(candidates, key=lambda candidate: candidate[0])[0][1]
        for title, candidates in headings.items()
    }
    return markdown.renderer.render(tokens, markdown.options, {}), heading_ids


def load_reviews(heading_ids: dict[str, str]) -> list[dict[str, object]]:
    payload = load_review_payload(DATA_PATH)
    validate_review_payload(payload, heading_ids)
    return normalize_reviews(payload, heading_ids)


def build_document() -> str:
    rfc_html, heading_ids = render_rfc()
    reviews = load_reviews(heading_ids)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    fragment = template.replace("<!--__RFC_HTML__-->", rfc_html).replace(
        "/*__REVIEW_DATA__*/", json.dumps(reviews, ensure_ascii=False, separators=(",", ":"))
    )
    if "<!--__RFC_HTML__-->" in fragment or "/*__REVIEW_DATA__*/" in fragment:
        raise ValueError("review template placeholders were not fully replaced")
    stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<meta name=\"referrer\" content=\"no-referrer\">
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'\">
<title>Agent Surface Protocol — Interactive RFC Review</title>
<style>{stylesheet}</style>
</head>
<body>
<main id=\"widget\">
{fragment}
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail when the committed dashboard is stale")
    mode.add_argument(
        "--check-data",
        action="store_true",
        help="validate review metadata without writing the dashboard",
    )
    args = parser.parse_args()
    try:
        if args.check_data:
            _, heading_ids = render_rfc()
            load_reviews(heading_ids)
            print(f"Review data is valid: {DATA_PATH.relative_to(ROOT)}")
            return 0
        document = build_document()
    except (json.JSONDecodeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != document:
            print("Dashboard is stale; run: make review-build", file=sys.stderr)
            return 1
        print(f"Dashboard is current: {OUTPUT_PATH.relative_to(ROOT)}")
        return 0
    OUTPUT_PATH.write_text(document, encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
