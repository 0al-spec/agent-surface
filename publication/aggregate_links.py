"""Deterministic Markdown-link transforms for the aggregate reading view."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit


LINK_POLICY = "source_relative_rebase_v1"
_INLINE_LINK = re.compile(
    r"(?P<prefix>!?\[[^\]\n]*\]\(\s*)"
    r"(?P<destination><[^>\n]+>|[^)\s\n]+)"
)
_REFERENCE_LINK = re.compile(
    r"^(?P<prefix>[ \t]{0,3}\[[^\]\n]+\]:[ \t]*)"
    r"(?P<destination><[^>\n]+>|[^ \t\n]+)"
)
_FENCE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})")
_BACKTICKS = re.compile(r"`+")


class AggregateLinkError(ValueError):
    """A Markdown link cannot be safely projected into the aggregate."""


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
) -> str:
    wrapped = destination.startswith("<") and destination.endswith(">")
    raw = destination[1:-1] if wrapped else destination
    try:
        parsed = urlsplit(raw)
    except ValueError as error:
        raise AggregateLinkError(
            f"invalid Markdown link in {source_path}: {raw!r}"
        ) from error
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path
        or parsed.path.startswith("/")
    ):
        return destination

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


def rebase_markdown_line(
    line: str,
    *,
    source_path: str,
    output_path: str,
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
            )
            + ending
        )
    return "".join(lines).encode("utf-8")


def relative_link_paths(content: bytes) -> list[str]:
    """Collect relative file targets from non-code Markdown links."""

    result: list[str] = []
    active_marker: str | None = None
    active_width = 0
    for raw_line in content.decode("utf-8").splitlines():
        fence = _FENCE.match(raw_line)
        marker = fence.group("marker") if fence is not None else None
        if active_marker is not None:
            if (
                marker is not None
                and marker[0] == active_marker
                and len(marker) >= active_width
                and not raw_line[fence.end() :].strip()
            ):
                active_marker = None
                active_width = 0
            continue
        if marker is not None:
            active_marker = marker[0]
            active_width = len(marker)
            continue

        code_spans = _code_spans(raw_line)
        matches = list(_INLINE_LINK.finditer(raw_line))
        reference = _REFERENCE_LINK.match(raw_line)
        if reference is not None:
            matches.append(reference)
        for match in matches:
            if _inside(match.start(), code_spans):
                continue
            destination = match.group("destination")
            if destination.startswith("<") and destination.endswith(">"):
                destination = destination[1:-1]
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
            result.append(parsed.path)
    return result
