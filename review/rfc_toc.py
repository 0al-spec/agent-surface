#!/usr/bin/env python3
"""Generate and validate the compact top-level RFC table of contents."""

from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
START_MARKER = "<!-- BEGIN GENERATED RFC TOC -->"
END_MARKER = "<!-- END GENERATED RFC TOC -->"
SUMMARY = "Table of Contents"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "section"


def top_level_sections(markdown_source: str) -> list[tuple[str, str]]:
    """Return level-two headings with GitHub-compatible duplicate suffixes."""

    tokens = MarkdownIt("commonmark", {"html": False}).parse(markdown_source)
    occurrences: Counter[str] = Counter()
    sections: list[tuple[str, str]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content.strip()
        anchor = slugify(title)
        duplicate_index = occurrences[anchor]
        occurrences[anchor] += 1
        if duplicate_index:
            anchor = f"{anchor}-{duplicate_index}"
        if token.tag == "h2":
            sections.append((title, anchor))
    return sections


def dashboard_sections(markdown_source: str) -> list[tuple[str, str]]:
    """Return level-two headings with the dashboard's existing stable ids."""

    tokens = MarkdownIt("commonmark", {"html": False}).parse(markdown_source)
    occurrences: Counter[str] = Counter()
    sections: list[tuple[str, str]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content.strip()
        occurrences[title] += 1
        anchor = slugify(title)
        if occurrences[title] > 1:
            anchor = f"{anchor}-{occurrences[title]}"
        if token.tag == "h2":
            sections.append((title, anchor))
    return sections


def generated_block(markdown_source: str) -> str:
    links = "\n".join(
        f"- [{title}](#{anchor})" for title, anchor in top_level_sections(markdown_source)
    )
    return (
        f"{START_MARKER}\n"
        "<details>\n"
        f"<summary>{SUMMARY}</summary>\n\n"
        f"{links}\n\n"
        "</details>\n"
        f"{END_MARKER}"
    )


def replace_generated_block(markdown_source: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    if len(pattern.findall(markdown_source)) != 1:
        raise ValueError("RFC must contain exactly one generated TOC marker block")
    source_without_toc = pattern.sub(f"{START_MARKER}\n{END_MARKER}", markdown_source)
    return pattern.sub(generated_block(source_without_toc), markdown_source)


def dashboard_markdown(markdown_source: str) -> str:
    """Render the generated list in the dashboard without enabling raw HTML."""

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}\n"
        r"<details>\n"
        rf"<summary>{re.escape(SUMMARY)}</summary>\n\n"
        r"(?P<links>(?:- .+\n)+)\n"
        r"</details>\n"
        rf"{re.escape(END_MARKER)}"
    )
    match = pattern.search(markdown_source)
    if match is None:
        raise ValueError("RFC generated TOC block is malformed or stale")
    source_without_toc = pattern.sub("", markdown_source)
    links = "\n".join(
        f"- [{title}](#{anchor})"
        for title, anchor in dashboard_sections(source_without_toc)
    )
    replacement = f"## {SUMMARY}\n\n{links}"
    return pattern.sub(replacement, markdown_source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed RFC table of contents is stale",
    )
    args = parser.parse_args()
    source = RFC_PATH.read_text(encoding="utf-8")
    try:
        expected = replace_generated_block(source)
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        if source != expected:
            print("RFC table of contents is stale; run: make rfc-toc")
            return 1
        print(f"RFC table of contents is current: {RFC_PATH.relative_to(ROOT)}")
        return 0
    RFC_PATH.write_text(expected, encoding="utf-8")
    print(f"Updated {RFC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
