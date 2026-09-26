from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "test_data_requirements.py"
DIGEST = "sha256:" + "1" * 64
RUNTIME_PATH = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("tdr_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def model_entity(model_key: str = "ep-001", model_type: str = "ep") -> dict:
    technique = "ep" if model_type == "ep" else None
    content = {
        "model_key": model_key, "model_type": model_type, "technique_slug": technique,
        "parent_tcn_id": "TCN-001", "selection_source": "analysis" if technique else None,
        "selection_key": "SEL-001" if technique else None, "derived_from_model_key": None, "status": "active",
    }
    return runtime.make_machine_entity("test-condition-design", "model", model_key, content, model_key=model_key)


def metadata(*, models: list[dict] | None = None, runtimes: list[dict] | None = None, authorities: list[dict] | None = None, input_mode: str = "artifact") -> dict:
    models = models if models is not None else [model_entity()]
    authorities = authorities or []
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
        "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": input_mode,
        "upstream_entities": [
            {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
            for row in [*models, *authorities]
        ],
        "upstream_runtime_units": runtimes if runtimes is not None else [
            {"skill": "test-condition-design", "runtime_unit_key": f"model:{row['entity_ref']}", "generation_fingerprint": DIGEST}
            for row in models if row["content"]["model_type"] in {"ep", "bva", "domain", "decision", "comb", "classification", "state", "flow", "crud", "cause-effect", "syntax", "schema", "ui", "random", "metamorphic"}
        ],
        "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, *, models: list[dict] | None = None, runtimes: list[dict] | None = None, authorities: list[dict] | None = None, input_mode: str = "artifact") -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(models=models, runtimes=runtimes, authorities=authorities, input_mode=input_mode), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
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

    def test_model_wide_requirement_resolves_current_coverage_or_adapter_model(self) -> None:
        row = requirement("model-wide", "eq", value={"type": "string", "value": "admin"})
        value = {"current_source_targets": [], "requirements": [row]}
        current = run(value)
        self.assertEqual(current["runtime_status"], "ok")
        entity = current["payload"]["entities"][0]
        dep = entity["upstream_entity_dependencies"]
        self.assertEqual([(item["entity_type"], item["entity_ref"]) for item in dep], [("model", "ep-001")])
        self.assertIn({"skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": DIGEST}, entity["runtime_dependencies"])
        tdr_runtime = runtime.runtime_unit_row(current)
        scoped_dependency = {
            "skill": "test-condition-design",
            "runtime_unit_key": runtime.machine_entity_runtime_unit_key("artifact:test_data_requirements:all", entity),
            "generation_fingerprint": runtime.machine_entity_runtime_generation(entity, tdr_runtime),
        }
        self.assertIn(scoped_dependency, entity["runtime_dependencies"])

        adapter = model_entity("schema-001", "schema")
        adapter_result = run(
            {"current_source_targets": [], "requirements": [{**row, "source_model_key": "schema-001"}]},
            models=[adapter],
            runtimes=[{"skill": "test-condition-design", "runtime_unit_key": "model:schema-001", "generation_fingerprint": DIGEST}],
        )
        self.assertEqual(adapter_result["runtime_status"], "ok")
        self.assertEqual(adapter_result["payload"]["normalized_requirements"][0]["applicable_target_refs"], [])

        unknown = run({"current_source_targets": [], "requirements": [{**row, "source_model_key": "ep-404"}]})
        self.assertEqual(unknown["runtime_status"], "invalid_input")

        mismatched = model_entity()
        mismatched = runtime.make_machine_entity(
            "test-condition-design", "model", "ep-001", {**mismatched["content"], "model_key": "ep-002"}, model_key="ep-001",
        )
        rejected = run(value, models=[mismatched])
        self.assertEqual(rejected["runtime_status"], "invalid_input")

    def test_source_model_entity_and_runtime_changes_propagate_freshness(self) -> None:
        source = model_entity()
        value = {"current_source_targets": [], "requirements": [requirement("model-wide", "eq", value={"type": "string", "value": "admin"})]}
        old_result = run(value, models=[source])
        self.assertEqual(old_result["runtime_status"], "ok")
        old_requirement = old_result["payload"]["entities"][0]
        unrelated = runtime.make_machine_entity("test-condition-design", "model", "bva-002", {"model_key": "bva-002", "model_type": "bva", "technique_slug": "bva"}, model_key="bva-002")
        changed = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {**source["content"], "selection_key": "SEL-002"}, model_key="ep-001")
        unrelated_changed = runtime.make_machine_entity("test-condition-design", "model", "bva-002", {**unrelated["content"], "selection_key": "SEL-UNRELATED"}, model_key="bva-002")

        rows = [source, unrelated, {**old_requirement, "runtime_dependencies": []}]
        states = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, {}) if row["entity_type"] == "test_data_requirement"}
        self.assertEqual(states["data:model-wide"], "current")

        rows = [changed, unrelated, {**old_requirement, "runtime_dependencies": []}]
        states = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, {}) if row["entity_type"] == "test_data_requirement"}
        self.assertEqual(states["data:model-wide"], "stale")

        current_runtime = {("test-condition-design", "artifact:test_data_requirements:all"): {"generation_fingerprint": old_result["generation_fingerprint"]}, ("test-condition-design", "model:ep-001"): {"generation_fingerprint": "sha256:" + "f" * 64}}
        rows = [source, {**old_requirement, "runtime_dependencies": [dep for dep in old_requirement["runtime_dependencies"] if dep["runtime_unit_key"] == "model:ep-001"]}]
        states = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, current_runtime) if row["entity_type"] == "test_data_requirement"}
        self.assertEqual(states["data:model-wide"], "stale")

        second_model = model_entity("bva-002", "bva")
        expanded = run(
            {"current_source_targets": [], "requirements": [
                requirement("model-wide", "eq", value={"type": "string", "value": "admin"}),
                {**requirement("unrelated", "eq", value={"type": "string", "value": "other"}), "source_model_key": "bva-002"},
            ]},
            models=[source, second_model],
        )
        self.assertNotEqual(expanded["generation_fingerprint"], old_result["generation_fingerprint"])
        current_runtime = {
            ("test-condition-design", "artifact:test_data_requirements:all"): runtime.runtime_unit_row(expanded),
            ("test-condition-design", "model:ep-001"): {"generation_fingerprint": DIGEST},
        }
        rows = [source, second_model, old_requirement]
        states = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, current_runtime) if row["entity_type"] == "test_data_requirement"}
        self.assertEqual(states["data:model-wide"], "current")

        rows = [source, unrelated_changed, {**old_requirement, "runtime_dependencies": []}]
        states = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, {}) if row["entity_type"] == "test_data_requirement"}
        self.assertEqual(states["data:model-wide"], "current")


if __name__ == "__main__":
    unittest.main()
