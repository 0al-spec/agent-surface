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


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = Path(__file__).resolve().parent
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
DATA_PATH = REVIEW_DIR / "review-data.json"
TEMPLATE_PATH = REVIEW_DIR / "review-template.html"
STYLESHEET_PATH = REVIEW_DIR / "standalone.css"
OUTPUT_PATH = REVIEW_DIR / "agent-surface-rfc-review.html"
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_SIDES = {"left", "right"}
VALID_STATUSES = {"present", "partial", "missing"}


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
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    reviews = payload.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("review-data.json must contain a non-empty reviews array")

    ids = [review.get("id") for review in reviews]
    if not all(isinstance(review_id, int) for review_id in ids):
        raise ValueError("Every review id must be an integer")
    if sorted(ids) != list(range(1, len(reviews) + 1)):
        raise ValueError("Review ids must be unique and sequential, starting at 1")

    missing_headings: list[str] = []
    normalized_reviews: list[dict[str, object]] = []
    required_fields = {"id", "title", "description", "category", "side", "status", "rationale", "priority", "anchors"}
    for review in sorted(reviews, key=lambda item: item["id"]):
        absent = required_fields - set(review)
        if absent:
            raise ValueError(f"Review #{review.get('id', '?')} is missing fields: {', '.join(sorted(absent))}")
        if review["side"] not in VALID_SIDES:
            raise ValueError(f"Review #{review['id']} has invalid side: {review['side']}")
        if review["status"] not in VALID_STATUSES:
            raise ValueError(f"Review #{review['id']} has invalid status: {review['status']}")
        if review["priority"] not in VALID_PRIORITIES:
            raise ValueError(f"Review #{review['id']} has invalid priority: {review['priority']}")
        if not all(isinstance(review[field], str) and review[field].strip() for field in required_fields - {"id", "anchors"}):
            raise ValueError(f"Review #{review['id']} has an empty text field")
        anchors = review["anchors"]
        if not isinstance(anchors, list) or not anchors:
            raise ValueError(f"Review #{review['id']} must have anchors")
        anchor_headings = []
        for anchor in anchors:
            heading = anchor if isinstance(anchor, str) else anchor.get("heading") if isinstance(anchor, dict) else None
            if not isinstance(heading, str) or not heading.strip():
                raise ValueError(f"Review #{review['id']} has an invalid anchor")
            anchor_headings.append(heading)
        if len(anchor_headings) != len(set(anchor_headings)):
            raise ValueError(f"Review #{review['id']} must have unique anchors")

        resolved_anchors = []
        for heading in anchor_headings:
            anchor_id = heading_ids.get(heading)
            if anchor_id is None:
                missing_headings.append(f"#{review['id']}: {heading}")
                continue
            resolved_anchors.append({"heading": heading, "anchorId": anchor_id})
        normalized_reviews.append({**review, "anchors": resolved_anchors})

    if missing_headings:
        raise ValueError("Unresolved RFC headings:\n" + "\n".join(missing_headings))
    return normalized_reviews


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
    parser.add_argument("--check", action="store_true", help="fail when the committed dashboard is stale")
    args = parser.parse_args()
    document = build_document()
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
