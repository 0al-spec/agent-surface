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
from urllib.parse import unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.aggregate_links import (
    markdown_canonical_heading_anchor_ids,
    markdown_heading_anchor_ids,
)
from rfc_toc import dashboard_markdown
from review_data import (
    MATURITY_ORDER,
    load_review_payload,
    normalize_reviews,
    validate_review_payload,
)


REVIEW_DIR = Path(__file__).resolve().parent
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
DATA_PATH = REVIEW_DIR / "review-data.json"
TEMPLATE_PATH = REVIEW_DIR / "review-template.html"
STYLESHEET_PATH = REVIEW_DIR / "standalone.css"
STATE_PATH = REVIEW_DIR / "dashboard-state.js"
UI_PATH = REVIEW_DIR / "dashboard-ui.js"
OUTPUT_PATH = REVIEW_DIR / "agent-surface-rfc-review.html"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "section"


def render_rfc() -> tuple[str, dict[str, str]]:
    markdown = MarkdownIt("commonmark", {"html": False, "linkify": True})
    source = dashboard_markdown(RFC_PATH.read_text(encoding="utf-8"))
    tokens = markdown.parse(source)
    generated_anchors = markdown_heading_anchor_ids(source.encode("utf-8"))
    canonical_anchors = markdown_canonical_heading_anchor_ids(
        source.encode("utf-8")
    )
    heading_tokens = [
        (index, token)
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
    ]
    if not (
        len(heading_tokens)
        == len(generated_anchors)
        == len(canonical_anchors)
    ):
        raise ValueError("dashboard and aggregate heading parsers disagree")

    occurrences: Counter[str] = Counter()
    headings: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    aggregate_to_dashboard: dict[str, str] = {}

    for (index, token), generated_anchor, canonical_anchor in zip(
        heading_tokens,
        generated_anchors,
        canonical_anchors,
        strict=True,
    ):
        title = tokens[index + 1].content.strip()
        level = int(token.tag[1:])
        occurrences[title] += 1
        anchor_id = slugify(title)
        if occurrences[title] > 1:
            anchor_id = f"{anchor_id}-{occurrences[title]}"
        token.attrSet("id", anchor_id)
        token.attrSet("data-asp-heading", title)
        headings[title].append((level, anchor_id))
        aggregate_to_dashboard[generated_anchor] = anchor_id
        aggregate_to_dashboard[canonical_anchor] = anchor_id

    for token in tokens:
        for child in token.children or ():
            if child.type != "link_open":
                continue
            destination = child.attrGet("href")
            if destination is None:
                continue
            parsed = urlsplit(destination)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.path
                or not parsed.fragment
            ):
                continue
            dashboard_anchor = aggregate_to_dashboard.get(
                unquote(parsed.fragment)
            )
            if dashboard_anchor is None:
                continue
            child.attrSet(
                "href",
                urlunsplit(("", "", "", parsed.query, dashboard_anchor)),
            )

    heading_ids = {
        title: sorted(candidates, key=lambda candidate: candidate[0])[0][1]
        for title, candidates in headings.items()
    }
    return markdown.renderer.render(tokens, markdown.options, {}), heading_ids


def load_dashboard_data(heading_ids: dict[str, str]) -> dict[str, object]:
    payload = load_review_payload(DATA_PATH)
    validate_review_payload(payload, heading_ids, required_planning_mode="required")
    return {
        "schema_version": payload["schema_version"],
        "maturity_order": list(MATURITY_ORDER),
        "profiles": payload["profiles"],
        "releases": payload["releases"],
        "reviews": normalize_reviews(payload, heading_ids),
    }


def serialize_inline_json(value: object) -> str:
    """Serialize JSON without allowing tracked text to terminate the inline script."""

    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    for character, escape in (
        ("&", "\\u0026"),
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        serialized = serialized.replace(character, escape)
    return serialized


def replace_placeholders(template: str, replacements: dict[str, str]) -> str:
    """Replace every required build marker exactly once."""

    for placeholder in replacements:
        count = template.count(placeholder)
        if count != 1:
            raise ValueError(
                f"review template must contain exactly one {placeholder}; found {count}"
            )
    pattern = re.compile("|".join(re.escape(placeholder) for placeholder in replacements))
    return pattern.sub(lambda match: replacements[match.group(0)], template)


def build_document() -> str:
    rfc_html, heading_ids = render_rfc()
    dashboard_data = load_dashboard_data(heading_ids)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    state_source = STATE_PATH.read_text(encoding="utf-8")
    ui_source = UI_PATH.read_text(encoding="utf-8")
    fragment = replace_placeholders(
        template,
        {
            "<!--__RFC_HTML__-->": rfc_html,
            "/*__DASHBOARD_STATE__*/": state_source,
            "/*__DASHBOARD_UI__*/": ui_source,
            "/*__DASHBOARD_DATA__*/": serialize_inline_json(dashboard_data),
        },
    )
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
            load_dashboard_data(heading_ids)
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
