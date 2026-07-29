"""Deterministic Markdown-link transforms for the aggregate reading view."""

from __future__ import annotations

import posixpath
import re
import unicodedata
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token


LINK_POLICY = "source_relative_rebase_v1"
_INLINE_LINK = re.compile(
    r"(?P<prefix>!?\[[^\]\n]*\]\(\s*)"
    r"(?P<destination><[^>\n]+>|[^)\s\n]+)"
)
_REFERENCE_LINK = re.compile(
    r"^(?P<prefix>[ \t]{0,3}\[(?!\^)[^\]\n]+\]:[ \t]*)"
    r"(?P<destination><[^>\n]+>|[^ \t\n]+)"
)
_FENCE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})")
_BACKTICKS = re.compile(r"`+")
_ANCHOR_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_GITHUB_PUNCTUATION = re.compile(
    r"[\u2000-\u206f\u2e00-\u2e7f\\'!\"#$%&()*+,./:;<=>?@\[\]^`{|}~]"
)


class AggregateLinkError(ValueError):
    """A Markdown link cannot be safely projected into the aggregate."""


class _RenderedAnchorParser(HTMLParser):
    """Collect real anchor start tags while HTML comments remain inert."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchor_ids: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return
        ids = [value for name, value in attrs if name.lower() == "id"]
        if (
            len(ids) == 1
            and ids[0] is not None
            and _ANCHOR_ID.fullmatch(ids[0]) is not None
        ):
            self.anchor_ids.append(ids[0])


def _code_spans(line: str) -> list[tuple[int, int]]:
    """Return conservative same-line code-span ranges."""

    delimiters = list(_BACKTICKS.finditer(line))
    ranges: list[tuple[int, int]] = []
    index = 0
    while index + 1 < len(delimiters):
        opening = delimiters[index]
        closing_index = index + 1
        while (
            closing_index < len(delimiters)
            and len(delimiters[closing_index].group())
            != len(opening.group())
        ):
            closing_index += 1
        if closing_index == len(delimiters):
            break
        ranges.append((opening.start(), delimiters[closing_index].end()))
        index = closing_index + 1
    return ranges


def _inside(position: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def _relative_destination(
    destination: str,
    *,
    source_path: str,
    output_path: str,
    fragment_targets: Mapping[str, str] | None = None,
) -> str:
    wrapped = destination.startswith("<") and destination.endswith(">")
    raw = destination[1:-1] if wrapped else destination
    try:
        parsed = urlsplit(raw)
    except ValueError as error:
        raise AggregateLinkError(
            f"invalid Markdown link in {source_path}: {raw!r}"
        ) from error
    if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
        return destination
    if not parsed.path:
        if not parsed.fragment or fragment_targets is None:
            return destination
        local_fragment = unquote(parsed.fragment)
        aggregate_fragment = fragment_targets.get(local_fragment)
        if aggregate_fragment is None:
            raise AggregateLinkError(
                f"fragment-only Markdown link has no canonical source anchor "
                f"in {source_path}: {raw!r}"
            )
        result = urlunsplit(
            ("", "", "", parsed.query, aggregate_fragment)
        )
        return f"<{result}>" if wrapped else result

    source_parent = PurePosixPath(source_path).parent.as_posix()
    target = posixpath.normpath(posixpath.join(source_parent, parsed.path))
    if target == ".." or target.startswith("../"):
        raise AggregateLinkError(
            f"relative Markdown link escapes the repository in {source_path}: "
            f"{raw!r}"
        )
    rebased = posixpath.relpath(
        target,
        PurePosixPath(output_path).parent.as_posix(),
    )
    result = urlunsplit(("", "", rebased, parsed.query, parsed.fragment))
    return f"<{result}>" if wrapped else result


def _walk_tokens(tokens: Sequence[Token]) -> list[Token]:
    result: list[Token] = []
    for token in tokens:
        result.append(token)
        if token.children:
            result.extend(_walk_tokens(token.children))
    return result


def markdown_link_destinations(content: bytes) -> list[str]:
    """Return every rendered CommonMark link and image destination in order."""

    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AggregateLinkError("Markdown content is not UTF-8") from error
    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    destinations: list[str] = []
    for token in _walk_tokens(tokens):
        attribute = (
            "href"
            if token.type == "link_open"
            else "src"
            if token.type == "image"
            else None
        )
        if attribute is None:
            continue
        destination = token.attrGet(attribute)
        if destination is None:
            raise AggregateLinkError(
                f"CommonMark {token.type} token lacks {attribute}"
            )
        destinations.append(destination)
    return destinations


def expected_aggregate_destinations(
    source_contents: Mapping[str, bytes],
    *,
    source_order: Sequence[str],
    output_path: str,
) -> list[str]:
    """Return the exact ordered destinations expected after link rebasing."""

    result: list[str] = []
    fragment_targets = aggregate_fragment_targets(
        source_contents,
        source_order=source_order,
    )
    for source_path in source_order:
        content = source_contents.get(source_path)
        if content is None:
            raise AggregateLinkError(
                f"aggregate link source is unavailable: {source_path!r}"
            )
        for destination in markdown_link_destinations(content):
            result.append(
                _relative_destination(
                    destination,
                    source_path=source_path,
                    output_path=output_path,
                    fragment_targets=fragment_targets[source_path],
                )
            )
    return result


def validate_aggregate_destinations(
    content: bytes,
    source_contents: Mapping[str, bytes],
    *,
    source_order: Sequence[str],
    output_path: str,
) -> None:
    """Prove that every rendered destination preserves source semantics."""

    expected = expected_aggregate_destinations(
        source_contents,
        source_order=source_order,
        output_path=output_path,
    )
    actual = markdown_link_destinations(content)
    if actual != expected:
        raise AggregateLinkError(
            "post-transform CommonMark destinations do not exactly match "
            "source-relative expectations"
        )


def _inline_text(token: Token) -> str:
    if not token.children:
        return token.content
    parts: list[str] = []
    for child in token.children:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
        elif child.type == "image":
            parts.append(child.content)
    return "".join(parts)


def _github_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return _GITHUB_PUNCTUATION.sub("", normalized).replace(" ", "-")


def _html_anchor_ids(token: Token) -> list[str]:
    if token.type not in {"html_block", "html_inline"}:
        return []
    parser = _RenderedAnchorParser()
    parser.feed(token.content)
    parser.close()
    return parser.anchor_ids


def markdown_explicit_anchor_ids(content: bytes) -> list[str]:
    """Return anchors rendered from raw HTML, excluding every code context."""

    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AggregateLinkError("Markdown content is not UTF-8") from error
    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    return [
        anchor
        for token in _walk_tokens(tokens)
        for anchor in _html_anchor_ids(token)
    ]


def markdown_heading_anchor_ids(content: bytes) -> list[str]:
    """Return generated GitHub-compatible heading anchors in source order."""

    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AggregateLinkError("Markdown content is not UTF-8") from error
    anchors: list[str] = []
    used: set[str] = set()
    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or index + 1 >= len(tokens):
            continue
        base = _github_slug(_inline_text(tokens[index + 1]))
        candidate = base
        suffix = 0
        while candidate in used:
            suffix += 1
            candidate = f"{base}-{suffix}"
        used.add(candidate)
        anchors.append(candidate)
    return anchors


def markdown_canonical_heading_anchor_ids(content: bytes) -> list[str]:
    """Return stable explicit anchors or generated anchors for each heading."""

    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AggregateLinkError("Markdown content is not UTF-8") from error
    generated = iter(markdown_heading_anchor_ids(content))
    canonical: list[str] = []
    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        anchor = next(generated)
        previous = next(
            (
                candidate
                for candidate in reversed(tokens[:index])
                if candidate.map is not None
            ),
            None,
        )
        if (
            previous is not None
            and token.map is not None
            and previous.map[1] == token.map[0]
        ):
            explicit = [
                anchor_id
                for candidate in _walk_tokens([previous])
                for anchor_id in _html_anchor_ids(candidate)
            ]
            if explicit:
                anchor = explicit[-1]
        canonical.append(anchor)
    return canonical


def markdown_anchor_ids(content: bytes) -> set[str]:
    """Return explicit and GitHub-compatible generated heading anchors."""

    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AggregateLinkError("Markdown content is not UTF-8") from error
    anchors = set(markdown_explicit_anchor_ids(content))
    anchors.update(markdown_heading_anchor_ids(content))
    return anchors


def aggregate_fragment_targets(
    source_contents: Mapping[str, bytes],
    *,
    source_order: Sequence[str],
) -> dict[str, dict[str, str]]:
    """Map each source-local anchor to its exact aggregate anchor."""

    targets: dict[str, dict[str, str]] = {}
    aggregate_used: set[str] = set()
    explicit_owners: dict[str, str] = {}
    for source_path in source_order:
        content = source_contents.get(source_path)
        if content is None:
            raise AggregateLinkError(
                f"aggregate link source is unavailable: {source_path!r}"
            )
        local_targets: dict[str, str] = {}
        source = content.decode("utf-8")
        for anchor in markdown_explicit_anchor_ids(content):
            owner = explicit_owners.get(anchor)
            if owner is not None:
                raise AggregateLinkError(
                    f"duplicate explicit aggregate anchor {anchor!r}: "
                    f"{owner!r} and {source_path!r}"
                )
            explicit_owners[anchor] = source_path
            local_targets[anchor] = anchor

        local_heading_anchors = markdown_heading_anchor_ids(content)
        tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
        heading_titles = [
            _inline_text(tokens[index + 1])
            for index, token in enumerate(tokens)
            if token.type == "heading_open" and index + 1 < len(tokens)
        ]
        if len(local_heading_anchors) != len(heading_titles):
            raise AggregateLinkError(
                f"heading anchor derivation drifted for {source_path!r}"
            )
        for local_anchor, title in zip(
            local_heading_anchors,
            heading_titles,
            strict=True,
        ):
            base = _github_slug(title)
            aggregate_anchor = base
            suffix = 0
            while aggregate_anchor in aggregate_used:
                suffix += 1
                aggregate_anchor = f"{base}-{suffix}"
            aggregate_used.add(aggregate_anchor)
            local_targets[local_anchor] = aggregate_anchor
        targets[source_path] = local_targets
    return targets


def rebase_markdown_line(
    line: str,
    *,
    source_path: str,
    output_path: str,
    fragment_targets: Mapping[str, str] | None = None,
) -> str:
    """Rebase non-code inline and reference links from source to output."""

    code_spans = _code_spans(line)

    def replace(match: re.Match[str]) -> str:
        if _inside(match.start(), code_spans):
            return match.group(0)
        return match.group("prefix") + _relative_destination(
            match.group("destination"),
            source_path=source_path,
            output_path=output_path,
            fragment_targets=fragment_targets,
        )

    rewritten = _INLINE_LINK.sub(replace, line)
    reference = _REFERENCE_LINK.match(rewritten)
    if reference is not None and not _inside(reference.start(), code_spans):
        rewritten = (
            reference.group("prefix")
            + _relative_destination(
                reference.group("destination"),
                source_path=source_path,
                output_path=output_path,
                fragment_targets=fragment_targets,
            )
            + rewritten[reference.end() :]
        )
    return rewritten


def fenced_source_lines(content: bytes) -> set[int]:
    """Return one-based source lines that belong to fenced code blocks."""

    fenced: set[int] = set()
    active_marker: str | None = None
    active_width = 0
    for line_number, raw_line in enumerate(content.splitlines(), 1):
        line = raw_line.decode("utf-8")
        match = _FENCE.match(line)
        marker = match.group("marker") if match is not None else None
        if active_marker is None:
            if marker is not None:
                active_marker = marker[0]
                active_width = len(marker)
                fenced.add(line_number)
            continue
        fenced.add(line_number)
        if (
            marker is not None
            and marker[0] == active_marker
            and len(marker) >= active_width
            and not line[match.end() :].strip()
        ):
            active_marker = None
            active_width = 0
    return fenced


def expected_mapped_source_lines(
    source_contents: Mapping[str, bytes],
    *,
    source_order: Sequence[str],
    output_path: str,
) -> dict[str, list[str]]:
    """Return each source line after the aggregate's deterministic rewrites."""

    fragment_targets = aggregate_fragment_targets(
        source_contents,
        source_order=source_order,
    )
    expected: dict[str, list[str]] = {}
    for source_index, source_path in enumerate(source_order):
        content = source_contents.get(source_path)
        if content is None:
            raise AggregateLinkError(
                f"aggregate link source is unavailable: {source_path!r}"
            )
        try:
            source = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AggregateLinkError(
                f"Markdown source is not UTF-8: {source_path!r}"
            ) from error
        lines = source.splitlines()
        fenced = fenced_source_lines(content)
        demoted_headings: set[int] = set()
        if source_index:
            tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
            for token in tokens:
                if token.type != "heading_open":
                    continue
                if (
                    token.map is None
                    or token.map[1] - token.map[0] != 1
                    or not token.markup
                    or set(token.markup) != {"#"}
                    or token.tag == "h6"
                ):
                    raise AggregateLinkError(
                        "aggregate heading demotion supports only one-line "
                        f"ATX headings below level six in {source_path!r}"
                    )
                demoted_headings.add(token.map[0] + 1)

        transformed: list[str] = []
        for line_number, line in enumerate(lines, 1):
            if line_number in demoted_headings:
                line = "#" + line
            if line_number not in fenced:
                line = rebase_markdown_line(
                    line,
                    source_path=source_path,
                    output_path=output_path,
                    fragment_targets=fragment_targets[source_path],
                )
            transformed.append(line)
        expected[source_path] = transformed
    return expected


def rebase_aggregate_links(
    content: bytes,
    source_map: Mapping[str, Any],
    source_contents: Mapping[str, bytes],
    *,
    output_path: str,
) -> bytes:
    """Apply provenance-aware link rebasing without changing line coverage."""

    lines = content.decode("utf-8").splitlines(keepends=True)
    fenced = {
        path: fenced_source_lines(source)
        for path, source in source_contents.items()
    }
    fragment_targets = aggregate_fragment_targets(
        source_contents,
        source_order=list(source_contents),
    )
    mappings = source_map.get("mappings")
    if not isinstance(mappings, list) or len(mappings) != len(lines):
        raise AggregateLinkError(
            "raw source map must contain exactly one mapping per output line"
        )

    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, Mapping) or mapping.get("kind") != "markdown":
            continue
        source = mapping.get("source")
        if not isinstance(source, Mapping):
            raise AggregateLinkError("markdown source-map entry lacks provenance")
        source_path = source.get("path")
        source_line = source.get("startLine")
        if (
            not isinstance(source_path, str)
            or not isinstance(source_line, int)
            or source_path not in source_contents
        ):
            raise AggregateLinkError("markdown source-map provenance is invalid")
        if source_line in fenced[source_path]:
            continue
        line = lines[index]
        ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if ending else line
        lines[index] = (
            rebase_markdown_line(
                body,
                source_path=source_path,
                output_path=output_path,
                fragment_targets=fragment_targets[source_path],
            )
            + ending
        )
    return "".join(lines).encode("utf-8")


def relative_link_paths(content: bytes) -> list[str]:
    """Collect relative file targets from rendered CommonMark links."""

    result: list[str] = []
    for destination in markdown_link_destinations(content):
        try:
            parsed = urlsplit(destination)
        except ValueError as error:
            raise AggregateLinkError(
                f"invalid aggregate Markdown link: {destination!r}"
            ) from error
        if (
            parsed.scheme
            or parsed.netloc
            or not parsed.path
            or parsed.path.startswith("/")
        ):
            continue
        result.append(unquote(parsed.path))
    return result
