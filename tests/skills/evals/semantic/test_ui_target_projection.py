from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "skills" / "evals" / "ui_target_projection.py"
SPEC = importlib.util.spec_from_file_location("ui_target_projection", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
projection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projection)


class UiTargetProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "package"
        self.root.mkdir()
        self.files = {
            "README.md": "# UI package\n\n| Package Version | v01 |\n",
            "00_scope_and_context.md": "# Scope\n\nCurrent payload content\n",
            "01_ui_structure_and_navigation.md": "# UI\n",
            "02_behavior_and_business_rules.md": "# Behavior\n",
            "06_spec_inconsistencies_and_pending.md": "# Pending\n",
            "07_current_unknowns.md": "# UNKNOWN\n",
            "09_authority_and_traceability.md": "# Authority\n",
            "CHANGELOG.md": (
                "# CHANGELOG\n\n## v01\n\n### 変更概要\n\nCurrent summary\n\n"
                "### Stable ID changes\n\nold summary detail\n\n## v00\n\n"
                "### 変更概要\n\nHistorical summary\n"
            ),
        }
        for relative, content in self.files.items():
            (self.root / relative).write_text(content, encoding="utf-8", newline="")
        rows = "\n".join(
            f"| {index} | {relative} | {'a' * 64} |"
            for index, relative in enumerate(self.files, 1)
        )
        manifest = (
            "# Package Manifest\n\nPackage Schema Version: ui-target-v1\n"
            "Package Version: v01\n\n### Package manifest\n\n"
            "| 順序 | ファイル | SHA-256 |\n| --- | --- | --- |\n"
            f"{rows}\n\n### Last materialize receipt\n\n```json\n{{}}\n```\n"
        )
        (self.root / "MANIFEST.md").write_text(manifest, encoding="utf-8", newline="")

    def test_semantic_projection_omits_history_and_manifest_but_keeps_current_summary(
        self,
    ) -> None:
        result = projection.project(self.root, "semantic")
        self.assertIn("<!-- FILE: 00_scope_and_context.md -->", result)
        self.assertIn(
            "<!-- CONTROL: CHANGELOG.current_change_summary -->\nCurrent summary",
            result,
        )
        self.assertNotIn("<!-- FILE: CHANGELOG.md -->", result)
        self.assertNotIn("<!-- FILE: MANIFEST.md -->", result)
        self.assertNotIn("Historical summary", result)
        self.assertNotIn("old summary detail", result)

    def test_deterministic_projection_uses_manifest_order_and_keeps_manifest_last(
        self,
    ) -> None:
        result = projection.project(self.root, "deterministic")
        markers = [
            line for line in result.splitlines() if line.startswith("<!-- FILE:")
        ]
        self.assertEqual(
            markers,
            [
                *(f"<!-- FILE: {path} -->" for path in self.files),
                "<!-- FILE: MANIFEST.md -->",
            ],
        )
        self.assertTrue(result.endswith("```\n"))

    def test_projection_rejects_file_set_mismatch(self) -> None:
        (self.root / "unlisted.md").write_text("extra\n", encoding="utf-8")
        with self.assertRaises(projection.ProjectionError):
            projection.project(self.root, "deterministic")

    def test_projection_rejects_duplicate_manifest_paths(self) -> None:
        manifest_path = self.root / "MANIFEST.md"
        manifest = manifest_path.read_text(encoding="utf-8")
        manifest = manifest.replace(
            "| 8 | CHANGELOG.md |", "| 8 | 07_current_unknowns.md |"
        )
        manifest_path.write_text(manifest, encoding="utf-8", newline="")
        with self.assertRaises(projection.ProjectionError):
            projection.project(self.root, "semantic")


if __name__ == "__main__":
    unittest.main()
