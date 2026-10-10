from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPO_ROOT / "skills" / "usability-evaluation"
SCRIPT_ROOT = SKILL_ROOT / "scripts"
FIXTURE = SKILL_ROOT / "evals" / "deterministic" / "fixtures" / "reference-catalog-dialog.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog = load_module("usability_evaluation_reference_catalog", SCRIPT_ROOT / "reference_catalog.py")
validator = load_module("usability_evaluation_reference_validator", SCRIPT_ROOT / "validate-reference-catalog.py")


def source_row(key: str, url: str) -> dict:
    return {
        "key": key,
        "canonical_url": url,
        "name": key,
        "publisher": "Example owner",
        "category": "reference",
        "source_position": "informative",
        "scope": "Web",
        "source_status": "current",
        "access_state": "public",
        "checked_at": "2026-09-28",
        "adoption_status": "adopted",
        "license_terms": "Attribution; summarize",
        "coverage_axes": ["ui-pattern"],
        "note": "Fixture",
    }


class ReferenceCatalogTests(unittest.TestCase):
    def load_fixture(self, *, retain_existing_reference_ids: bool = False) -> dict:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if not retain_existing_reference_ids:
            for group in fixture["references"]:
                for entry in group["entries"]:
                    entry.pop("existing_reference_id", None)
        return fixture

    def test_url_normalization_preserves_identity_and_rejects_fragment(self) -> None:
        self.assertEqual(
            catalog.normalize_url("HTTPS://Example.COM:443/a?x=1"),
            "https://example.com/a?x=1",
        )
        with self.assertRaisesRegex(catalog.CatalogError, "fragment_must_be_a_source_item_locator"):
            catalog.normalize_url("https://example.com/a#section")

    def test_initial_source_ids_are_canonical_url_ordered_and_input_order_independent(self) -> None:
        fixture = self.load_fixture()
        fixture["sources"] = [source_row("z", "https://example.com/z"), source_row("a", "https://example.com/a")]
        fixture.update({"candidates": [], "discovery_runs": [], "coverage": [], "source_items": [], "references": []})
        first = catalog.materialize(fixture, Path(tempfile.mkdtemp()))
        fixture["sources"].reverse()
        second = catalog.materialize(fixture, Path(tempfile.mkdtemp()))
        self.assertEqual(first["allocated"]["source_ids"], second["allocated"]["source_ids"])
        self.assertEqual(first["allocated"]["source_ids"], {"a": "SRC-001", "z": "SRC-002"})

    def test_duplicate_canonical_source_url_is_rejected(self) -> None:
        fixture = self.load_fixture()
        fixture["sources"] = [source_row("one", "https://example.com/"), source_row("two", "https://EXAMPLE.com:443")]
        with self.assertRaisesRegex(catalog.CatalogError, "duplicate_source_url"):
            catalog.materialize(fixture, Path(tempfile.mkdtemp()))

    def test_duplicate_source_item_identity_is_rejected(self) -> None:
        fixture = self.load_fixture()
        fixture["source_items"].append({**fixture["source_items"][0], "key": "duplicate-item"})
        with self.assertRaisesRegex(catalog.CatalogError, "duplicate_source_item_identity"):
            catalog.materialize(fixture, Path(tempfile.mkdtemp()))

    def test_included_item_requires_dimension_closure(self) -> None:
        fixture = self.load_fixture()
        fixture["source_items"][0]["captured_dimensions"] = ["purpose"]
        with self.assertRaisesRegex(catalog.CatalogError, "dimension_coverage_mismatch"):
            catalog.materialize(fixture, Path(tempfile.mkdtemp()))

    def test_dialog_vertical_slice_materializes_and_independent_validator_accepts_it(self) -> None:
        fixture = self.load_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = catalog.materialize(fixture, root)
            for relative, contents in result["files"].items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
            # Group count and materialized entry count are different: derive
            # the expected cardinality from the nested entries in the fixture.
            self.assertEqual(
                result["summary"]["reference_entry_count"],
                sum(len(group["entries"]) for group in fixture["references"]),
            )
            self.assertEqual(validator.validate(root, allow_incomplete=True), [])
            self.assertEqual(validator.validate(root), [])

    def test_reference_entry_moves_keep_package_local_ids(self) -> None:
        fixture = self.load_fixture(retain_existing_reference_ids=True)
        existing_references = SKILL_ROOT / "references"
        result = catalog.materialize(fixture, existing_references)
        expected_stable_ids = {
            "dialog-accessibility": "REF-0002",
            "dialog-semantics": "REF-0004",
            "dialog-user-control": "REF-0003",
            "modal-dialog": "REF-0001",
        }
        for key, ref in expected_stable_ids.items():
            self.assertEqual(result["allocated"]["reference_entry_ids"][key], ref)
        self.assertIn("accessibility/dialog-semantics.md", result["files"])
        self.assertIn("heuristics/user-control-and-freedom.md", result["files"])

    def test_independent_validator_rejects_column_drift_and_broken_cross_reference(self) -> None:
        fixture = self.load_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = catalog.materialize(fixture, root)
            for relative, contents in result["files"].items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
            catalog_path = root / "source-catalog.md"
            original = catalog_path.read_text(encoding="utf-8")
            catalog_path.write_text(original.replace("| Source ID | Name |", "| Wrong ID | Name |", 1), encoding="utf-8")
            self.assertTrue(any("columns_mismatch" in issue for issue in validator.validate(root, allow_incomplete=True)))
            catalog_path.write_text(original, encoding="utf-8")
            coverage_path = root / "source-coverage.md"
            coverage_text = coverage_path.read_text(encoding="utf-8")
            modal_ref = result["allocated"]["reference_entry_ids"]["modal-dialog"]
            coverage_path.write_text(
                coverage_text.replace(f"{modal_ref}:patterns/", "REF-9999:patterns/", 1),
                encoding="utf-8",
            )
            self.assertTrue(any("item_destination_unresolved" in issue for issue in validator.validate(root, allow_incomplete=True)))


if __name__ == "__main__":
    unittest.main()
