"""Resolve dashboard RFC headings to exact modular document locations."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "publication" / "document-set.json"


class RfcEvidenceTarget(TypedDict):
    document_id: str
    document_version: str
    anchor_id: str


def slugify(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "section"


@lru_cache(maxsize=1)
def canonical_rfc_evidence_targets() -> dict[str, RfcEvidenceTarget]:
    """Map selected dashboard anchor ids to exact canonical documents."""

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    documents = sorted(
        catalog["documents"],
        key=lambda item: item["publication_order"],
    )
    global_occurrences: Counter[str] = Counter()
    candidates: dict[
        str,
        list[tuple[int, int, str, RfcEvidenceTarget]],
    ] = {}
    order = 0
    markdown = MarkdownIt("commonmark", {"html": False})

    for document in documents:
        local_occurrences: Counter[str] = Counter()
        source = ROOT / document["source_path"]
        tokens = markdown.parse(source.read_text(encoding="utf-8"))
        heading_shift = 0 if document["publication_order"] == 0 else 1
        for index, token in enumerate(tokens):
            if token.type != "heading_open":
                continue
            title = tokens[index + 1].content.strip()
            global_occurrences[title] += 1
            local_occurrences[title] += 1
            aggregate_anchor = slugify(title)
            if global_occurrences[title] > 1:
                aggregate_anchor = (
                    f"{aggregate_anchor}-{global_occurrences[title]}"
                )
            local_anchor = slugify(title)
            if local_occurrences[title] > 1:
                local_anchor = f"{local_anchor}-{local_occurrences[title]}"
            effective_level = min(6, int(token.tag[1:]) + heading_shift)
            candidates.setdefault(title, []).append(
                (
                    effective_level,
                    order,
                    aggregate_anchor,
                    {
                        "document_id": document["document_id"],
                        "document_version": document["version"],
                        "anchor_id": local_anchor,
                    },
                )
            )
            order += 1

    targets: dict[str, RfcEvidenceTarget] = {}
    for title_candidates in candidates.values():
        _, _, aggregate_anchor, target = min(
            title_candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
        if aggregate_anchor in targets:
            raise ValueError(
                f"duplicate selected dashboard anchor: {aggregate_anchor!r}"
            )
        targets[aggregate_anchor] = target
    return targets
