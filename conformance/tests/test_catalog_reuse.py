from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from conformance.check import (
    Catalog,
    ConformanceError,
    _catalog_memory_digest,
    _resolve_catalog,
    validate_catalog,
)


ROOT = Path(__file__).resolve().parents[2]


def _catalog(root: Path) -> Catalog:
    catalog = Catalog(
        root=root.resolve(),
        snapshot_catalog_sha256="catalog-snapshot",
        snapshot_specification_sha256="specification-snapshot",
        snapshot_memory_sha256="",
        suite={},
        vector_catalog={},
        fixture_catalog={},
        schema_case_catalog={},
        bundle_registry={},
        requirements={},
        vectors={},
        profiles={},
        features={},
        fixtures={},
        mutations={},
        bundles={},
    )
    return replace(
        catalog,
        snapshot_memory_sha256=_catalog_memory_digest(catalog),
    )


class CatalogReuseTests(unittest.TestCase):
    def test_default_path_performs_fresh_validation(self) -> None:
        root = Path("/tmp/asp-catalog-root")
        catalog = _catalog(root)

        with patch(
            "conformance.check.validate_catalog", return_value=catalog
        ) as validate:
            resolved_root, resolved_catalog = _resolve_catalog(root, None)

        validate.assert_called_once_with(root.resolve())
        self.assertEqual(resolved_root, root.resolve())
        self.assertIs(resolved_catalog, catalog)

    def test_explicit_catalog_skips_revalidation(self) -> None:
        root = Path("/tmp/asp-catalog-root")
        catalog = _catalog(root)

        with (
            patch("conformance.check.validate_catalog") as validate,
            patch(
                "conformance.check.catalog_digest",
                return_value=catalog.snapshot_catalog_sha256,
            ),
            patch(
                "conformance.check.specification_digest",
                return_value=catalog.snapshot_specification_sha256,
            ),
        ):
            resolved_root, resolved_catalog = _resolve_catalog(root, catalog)

        validate.assert_not_called()
        self.assertEqual(resolved_root, root.resolve())
        self.assertIs(resolved_catalog, catalog)

    def test_explicit_catalog_fingerprint_preserves_finite_float_type(self) -> None:
        root = Path("/tmp/asp-catalog-root")
        catalog = _catalog(root)
        catalog.schema_case_catalog["example"] = 1.5
        catalog = replace(
            catalog,
            snapshot_memory_sha256=_catalog_memory_digest(catalog),
        )

        with (
            patch(
                "conformance.check.catalog_digest",
                return_value=catalog.snapshot_catalog_sha256,
            ),
            patch(
                "conformance.check.specification_digest",
                return_value=catalog.snapshot_specification_sha256,
            ),
        ):
            _, resolved_catalog = _resolve_catalog(root, catalog)

        self.assertIs(resolved_catalog, catalog)

    def test_explicit_catalog_is_bound_to_one_root(self) -> None:
        catalog = _catalog(Path("/tmp/asp-catalog-root"))

        with self.assertRaisesRegex(ConformanceError, "root does not match"):
            _resolve_catalog(Path("/tmp/different-root"), catalog)


class CatalogSnapshotIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        shutil.copytree(
            ROOT / "conformance" / "v1",
            cls.root / "conformance" / "v1",
        )
        shutil.copytree(ROOT / "drafts", cls.root / "drafts")
        cls.catalog = validate_catalog(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_same_root_catalog_file_change_rejects_reuse(self) -> None:
        path = self.root / "conformance" / "v1" / "vectors.json"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        try:
            with self.assertRaisesRegex(
                ConformanceError, "catalog source files changed"
            ):
                _resolve_catalog(self.root, self.catalog)
        finally:
            path.write_bytes(original)

    def test_same_root_specification_change_rejects_reuse(self) -> None:
        path = self.root / "drafts" / "agent-surface.md"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        try:
            with self.assertRaisesRegex(
                ConformanceError, "specification source changed"
            ):
                _resolve_catalog(self.root, self.catalog)
        finally:
            path.write_bytes(original)

    def test_in_memory_catalog_change_rejects_reuse(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog.vectors.pop(next(iter(catalog.vectors)))

        with self.assertRaisesRegex(ConformanceError, "mutated in memory"):
            _resolve_catalog(self.root, catalog)

    def test_in_memory_integer_to_float_change_rejects_reuse(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog.suite["schema_version"] = float(catalog.suite["schema_version"])

        with self.assertRaisesRegex(ConformanceError, "mutated in memory"):
            _resolve_catalog(self.root, catalog)

    def test_missing_snapshot_source_uses_conformance_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ConformanceError, "source files"):
                validate_catalog(Path(directory))


if __name__ == "__main__":
    unittest.main()
