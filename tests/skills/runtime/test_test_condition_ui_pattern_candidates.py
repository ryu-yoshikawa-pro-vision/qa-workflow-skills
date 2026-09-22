from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "ui_pattern_candidates.py"


def metadata(static_data_versions=None) -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "ui-pattern-candidates-v1",
        "runtime_unit_key": "model:ui-001", "model_key": "ui-001", "model_type": "ui", "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": static_data_versions or {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, static_data_versions=None) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(static_data_versions), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class UiPatternCandidatesRuntimeTests(unittest.TestCase):
    def test_alias_resolution_uses_catalog_and_emits_catalog_hash(self) -> None:
        result = run({"pattern": "input-text", "attributes": {"type": "text", "required": True}})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["static_data_versions"]["ui_pattern_catalog"].startswith("sha256:"))
        self.assertEqual(result["payload"]["pattern"]["pattern_key"], "text-input")
        self.assertTrue(all(row["target_key"].startswith("ui:text-input:") for row in result["payload"]["targets"]))
        self.assertTrue(all(row["candidate"]["requires_product_authority"] for row in result["payload"]["targets"]))

    def test_unknown_pattern_is_explicit_unsupported_and_bad_attribute_is_invalid(self) -> None:
        unknown = run({"pattern": "not-in-catalog", "attributes": {}})
        self.assertEqual(unknown["runtime_status"], "unsupported")
        self.assertEqual(unknown["payload"]["unsupported_items"][0]["reason_code"], "unknown_pattern")
        bad = run({"pattern": "button", "attributes": {"unknown": True}})
        self.assertEqual(bad["runtime_status"], "invalid_input")

    def test_caller_cannot_pin_stale_catalog_version(self) -> None:
        result = run({"pattern": "button", "attributes": {}}, {"ui_pattern_catalog": "sha256:" + "0" * 64})
        self.assertEqual(result["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
