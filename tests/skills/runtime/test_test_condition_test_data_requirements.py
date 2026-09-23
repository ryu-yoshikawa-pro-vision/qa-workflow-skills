from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "test_data_requirements.py"
DIGEST = "sha256:" + "1" * 64


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
        "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def target(ref: str, model: str = "ep-001", *, content: str = DIGEST, generation: str = DIGEST) -> dict:
    return {"source_model_key": model, "target_ref": ref, "target_content_fingerprint": content, "generation_fingerprint": generation}


def requirement(key: str, operator: str, *, versions: list[dict] | None = None, **fields: object) -> dict:
    return {"requirement_key": key, "environment_key": None, "dimension_key": "role", "operator": operator, "authority_refs": [], "source_model_key": "ep-001", "source_target_versions": versions or [], **fields}


class TestDataRequirementRuntimeTests(unittest.TestCase):
    def test_model_wide_and_target_specific_requirements_keep_original_identity(self) -> None:
        targets = [target("sha256:" + "2" * 64), target("sha256:" + "3" * 64)]
        value = {"current_source_targets": targets, "requirements": [
            requirement("role-any", "enum", values=[{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}]),
            requirement("role-one", "eq", versions=[{key: targets[0][key] for key in ("target_ref", "target_content_fingerprint", "generation_fingerprint")}], value={"type": "string", "value": "admin"}),
        ]}
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        rows = {row["requirement_key"]: row for row in result["payload"]["normalized_requirements"]}
        self.assertEqual(rows["role-any"]["data_ref"], "data:role-any")
        self.assertEqual(rows["role-any"]["applicable_target_refs"], sorted(row["target_ref"] for row in targets))
        self.assertEqual(rows["role-one"]["applicable_target_refs"], [targets[0]["target_ref"]])
        self.assertEqual({row["entity_ref"] for row in result["payload"]["entities"]}, {"data:role-any", "data:role-one"})

    def test_empty_intersection_is_target_scoped(self) -> None:
        target_row = target("sha256:" + "2" * 64)
        result = run({"current_source_targets": [target_row], "requirements": [
            requirement("r1", "eq", value={"type": "string", "value": "admin"}),
            requirement("r2", "eq", value={"type": "string", "value": "user"}),
        ]})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertEqual(result["payload"]["conflicts"][0]["target_ref"], target_row["target_ref"])

    def test_target_specific_cross_model_reference_is_rejected(self) -> None:
        first = target("sha256:" + "2" * 64, "ep-001")
        second = target("sha256:" + "3" * 64, "bva-001")
        value = {"current_source_targets": [first, second], "requirements": [requirement("bad", "eq", versions=[{key: second[key] for key in ("target_ref", "target_content_fingerprint", "generation_fingerprint")}], value={"type": "string", "value": "x"})]}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")

    def test_target_version_must_match_current_content_and_generation(self) -> None:
        current = target("sha256:" + "2" * 64, content="sha256:" + "4" * 64, generation="sha256:" + "5" * 64)
        exact = {key: current[key] for key in ("target_ref", "target_content_fingerprint", "generation_fingerprint")}
        row = requirement("scoped", "eq", versions=[exact], value={"type": "string", "value": "admin"})
        passed = run({"current_source_targets": [current], "requirements": [row]})
        self.assertEqual(passed["runtime_status"], "ok")
        self.assertEqual(passed["payload"]["normalized_requirements"][0]["applicable_target_refs"], [current["target_ref"]])

        stale_content = {**exact, "target_content_fingerprint": DIGEST}
        stale_generation = {**exact, "generation_fingerprint": DIGEST}
        mismatched_model = {**row, "source_model_key": "bva-001"}
        unknown_target = {**exact, "target_ref": "sha256:" + "6" * 64}
        for label, versions, requirement_row in (
            ("stale content", [stale_content], row),
            ("stale generation", [stale_generation], row),
            ("source model mismatch", [exact], mismatched_model),
            ("unknown target", [unknown_target], row),
        ):
            with self.subTest(label=label):
                candidate = {**requirement_row, "source_target_versions": versions}
                result = run({"current_source_targets": [current], "requirements": [candidate]})
                self.assertEqual(result["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
