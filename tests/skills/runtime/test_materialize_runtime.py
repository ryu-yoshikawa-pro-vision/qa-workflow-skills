from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tests.skills.runtime.test_ep_vertical_integration import runtime


REPO_ROOT = Path(__file__).resolve().parents[3]
EP_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"
MATERIALIZE_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "materialize_coverage.py"
TDR_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "test_data_requirements.py"
sys.path.insert(0, str(MATERIALIZE_SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("runtime_test_materialize_module", MATERIALIZE_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
materialize_runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = materialize_runtime
SPEC.loader.exec_module(materialize_runtime)


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def current_model_content(model_key: str = "ep-001") -> dict:
    return {
        "derived_from_model_key": None, "model_key": model_key, "model_type": "ep", "parent_tcn_id": "TCN-001",
        "selection_key": f"SEL-{model_key[-3:]}", "selection_source": "analysis", "status": "active", "technique_slug": "ep",
    }


def ep_metadata(model_key: str = "ep-001") -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "equivalence-partitions-v1", "runtime_unit_key": f"model:{model_key}", "model_key": model_key,
        "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": f"SEL-{model_key[-3:]}",
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
        "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def materialize_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "materialize-coverage-v1", "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None,
        "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None, "scope_key": "TCN-001",
        "input_mode": "artifact", "upstream_entities": [
            {"skill": "test-condition-design", "entity_type": "tcn", "entity_ref": "TCN-001", "content": {"tcn_id": "TCN-001"}},
            {"skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001", "content": current_model_content()},
        ], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run_script(script: Path, request: dict) -> dict:
    result = subprocess.run([sys.executable, str(script)], input=json.dumps(request).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def ep_result(model_key: str = "ep-001") -> dict:
    return run_script(
        EP_SCRIPT,
        {
            "metadata": ep_metadata(model_key),
            "input": {
                "sets": [{"set_key": "role", "label": "Role", "partitions": [
                    {"partition_key": "admin", "label": "Admin", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "admin"}]}, "representative": None, "authority_refs": []},
                    {"partition_key": "user", "label": "User", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "user"}]}, "representative": None, "authority_refs": []},
                ]}],
            },
        },
    )


def materialize_request(ep: dict, *, previous: dict | None = None) -> dict:
    model_result = {
        "skill": "test-condition-design", "model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": "model:ep-001",
        "input_fingerprint": ep["input_fingerprint"], "model_fingerprint": ep["model_fingerprint"], "generator_contract_version": ep["generator_contract_version"],
        "generation_fingerprint": ep["generation_fingerprint"], "support_status": ep["support_status"], "runtime_status": ep["runtime_status"],
        "result_status": ep["result_status"], "deterministic_generated": ep["deterministic_generated"], "targets": ep["payload"]["targets"],
        "unsupported_items": [], "coverage_summary": ep["payload"]["coverage_summary"], "freshness_status": "current",
    }
    previous = previous or {}
    annotations = [{
        "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"],
        "generation_fingerprint": ep["generation_fingerprint"], "priority": "中", "priority_override_reason": None,
        "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": [],
    } for target in ep["payload"]["targets"]]
    return {
        "metadata": materialize_metadata(),
        "input": {
            "tcn_id": "TCN-001",
            "active_model_metadata": [{"model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "parent_tcn_id": "TCN-001", "content_fingerprint": digest(current_model_content())}],
            "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": [],
            "target_annotations": annotations, "target_dispositions": [], "previous_semantic_ci_map": [],
            "previous_target_id_map": previous.get("target_mapping_state", []), "previous_ci_ids": previous.get("ci_id_state", []),
            "previous_expected_result_roots": [], "merge_groups": [],
        },
    }


def test_data_output(
    ep: dict,
    requirements: list[dict],
    *,
    model_entities: list[dict] | None = None,
    source_targets: list[dict] | None = None,
    source_runtime_units: list[dict] | None = None,
    authority_entities: list[dict] | None = None,
) -> dict:
    model_entities = model_entities or [{
        "skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001",
        "content": {"model_key": "ep-001", "model_type": "ep", "technique_slug": "ep"},
    }]
    authority_entities = authority_entities or []
    source_targets = source_targets or [{
        "source_model_key": "ep-001", "target_ref": target["target_ref"],
        "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"],
    } for target in ep["payload"]["targets"]]
    source_runtime_units = source_runtime_units or [{
        "skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": ep["generation_fingerprint"],
    }]
    metadata = {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
        "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "artifact",
        "upstream_entities": [
            {key: entity[key] for key in ("skill", "entity_type", "entity_ref", "content")}
            for entity in [*model_entities, *authority_entities]
        ],
        "upstream_runtime_units": source_runtime_units,
        "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }
    return run_script(TDR_SCRIPT, {"metadata": metadata, "input": {"current_source_targets": source_targets, "requirements": requirements}})


def model_result_for(ep: dict, model_key: str) -> dict:
    return {
        "skill": "test-condition-design", "model_key": model_key, "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": f"model:{model_key}",
        "input_fingerprint": ep["input_fingerprint"], "model_fingerprint": ep["model_fingerprint"], "generator_contract_version": ep["generator_contract_version"],
        "generation_fingerprint": ep["generation_fingerprint"], "support_status": ep["support_status"], "runtime_status": ep["runtime_status"],
        "result_status": ep["result_status"], "deterministic_generated": ep["deterministic_generated"], "targets": ep["payload"]["targets"],
        "unsupported_items": [], "coverage_summary": ep["payload"]["coverage_summary"], "freshness_status": "current",
    }


class MaterializeRuntimeTests(unittest.TestCase):
    def test_targets_materialize_to_stable_ci_and_machine_entity(self) -> None:
        ep = ep_result()
        result = run_script(MATERIALIZE_SCRIPT, materialize_request(ep))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        mapping = {row["target_key"]: row["ci_id"] for row in result["payload"]["target_id_map"]}
        self.assertEqual(mapping, {"ep:role:admin": "TCN-001-CI01", "ep:role:user": "TCN-001-CI02"})
        self.assertTrue(result["payload"]["model_completion"][0]["materialize_complete"])
        self.assertEqual(len(result["payload"]["entities"]), 2)
        self.assertEqual(result["payload"]["entities"][0]["content"]["source_kind"], "runtime_target")
        self.assertIsNotNone(result["payload"]["entities"][0]["content"]["execution"])

    def test_previous_full_state_preserves_ci_ids(self) -> None:
        ep = ep_result()
        first = run_script(MATERIALIZE_SCRIPT, materialize_request(ep))
        second = run_script(MATERIALIZE_SCRIPT, materialize_request(ep, previous=first["payload"]))
        self.assertEqual(first["payload"]["target_id_map"], second["payload"]["target_id_map"])
        self.assertEqual(first["payload"]["ci_id_state"], second["payload"]["ci_id_state"])

    def test_previous_mapping_target_ref_is_recomputed(self) -> None:
        ep = ep_result()
        request = materialize_request(ep)
        request["input"]["previous_target_id_map"] = [{
            "target_ref": "sha256:" + "0" * 64, "model_key": "ep-001", "target_key": "ep:role:admin",
            "target_content_fingerprint": ep["payload"]["targets"][0]["target_content_fingerprint"], "ci_id": "TCN-001-CI01", "mapping_status": "active",
        }]
        result = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def test_semantic_item_materializes_as_separate_ci_and_round_trips(self) -> None:
        ep = ep_result()
        request = materialize_request(ep)
        source = ep["payload"]["targets"][0]
        request["input"]["semantic_coverage_items"] = [{
            "draft_key": "semantic-error-path",
            "model_key": "ep-001",
            "identity_action": "new",
            "reuse_semantic_item_key": None,
            "reuse_ci_id": None,
            "source_target_versions": [{"target_ref": source["target_ref"], "target_content_fingerprint": source["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"]}],
            "item_text": "仕様根拠で確認が必要な追加観点",
            "authority_refs": [], "reference_refs": [], "priority": "中", "priority_override_reason": None,
            "expected_result_root": "root-semantic-error-path", "test_data_requirement_refs": [],
        }]
        result = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(result["runtime_status"], "ok")
        semantic = [row for row in result["payload"]["entities"] if row["content"]["source_kind"] == "semantic_item"]
        self.assertEqual(len(semantic), 1)
        self.assertEqual(semantic[0]["entity_ref"], "TCN-001-CI03")
        self.assertEqual(result["payload"]["semantic_ci_mapping_state"][0]["semantic_item_key"], "semantic:TCN-001-CI03")

    def test_materialize_consumes_current_tdr_entity_without_resolving_its_authority(self) -> None:
        ep = ep_result()
        model = materialize_runtime.make_machine_entity(
            "test-condition-design", "model", "ep-001", current_model_content(), model_key="ep-001",
        )
        authority = materialize_runtime.make_machine_entity(
            "spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001", "text": "current authority"},
        )
        tdr = test_data_output(
            ep,
            [{
                "requirement_key": "role", "environment_key": None, "dimension_key": "role", "operator": "eq",
                "authority_refs": ["SPEC-001"], "source_model_key": "ep-001", "source_target_versions": [],
                "value": {"type": "string", "value": "admin"},
            }],
            model_entities=[model],
            authority_entities=[authority],
        )
        self.assertEqual(tdr["runtime_status"], "ok", tdr)
        tdr_entity = tdr["payload"]["entities"][0]
        self.assertIn(
            ("spec-analysis", "authority", "SPEC-001"),
            {(row["skill"], row["entity_type"], row["entity_ref"]) for row in tdr_entity["upstream_entity_dependencies"]},
        )

        request = materialize_request(ep)
        request["input"]["test_data_requirements"] = tdr["payload"]["normalized_requirements"]
        request["input"]["target_annotations"] = [
            {**row, "test_data_requirement_refs": ["data:role"]}
            for row in request["input"]["target_annotations"]
        ]
        request["metadata"]["upstream_entities"].append({
            "skill": tdr_entity["skill"], "entity_type": tdr_entity["entity_type"],
            "entity_ref": tdr_entity["entity_ref"], "content": tdr_entity["content"],
        })
        request["metadata"]["upstream_runtime_units"] = [{
            "skill": "test-condition-design", "runtime_unit_key": "artifact:test_data_requirements:all",
            "generation_fingerprint": tdr["generation_fingerprint"],
        }]

        result = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(result["runtime_status"], "ok", result)
        ci = next(row for row in result["payload"]["entities"] if row["entity_type"] == "ci")
        self.assertEqual(
            {(row["skill"], row["entity_type"], row["entity_ref"]): row["content_fingerprint"] for row in ci["upstream_entity_dependencies"]},
            {
                ("test-condition-design", "tcn", "TCN-001"): digest({"tcn_id": "TCN-001"}),
                ("test-condition-design", "model", "ep-001"): digest(current_model_content()),
                ("test-condition-design", "test_data_requirement", "data:role"): tdr_entity["content_fingerprint"],
            },
        )
        self.assertNotIn("spec-analysis", {row["skill"] for row in ci["upstream_entity_dependencies"]})

        missing = json.loads(json.dumps(request))
        missing["metadata"]["upstream_entities"] = [
            row for row in missing["metadata"]["upstream_entities"] if row["entity_type"] != "test_data_requirement"
        ]
        self.assertEqual(run_script(MATERIALIZE_SCRIPT, missing)["runtime_status"], "invalid_input")

        mismatched = json.loads(json.dumps(request))
        stored = next(row for row in mismatched["metadata"]["upstream_entities"] if row["entity_type"] == "test_data_requirement")
        stored["content"] = {**stored["content"], "value": {"type": "string", "value": "member"}}
        self.assertEqual(run_script(MATERIALIZE_SCRIPT, mismatched)["runtime_status"], "invalid_input")

        stale_fingerprint = json.loads(json.dumps(request))
        stale_fingerprint["input"]["test_data_requirements"][0]["content_fingerprint"] = "sha256:" + "0" * 64
        self.assertEqual(run_script(MATERIALIZE_SCRIPT, stale_fingerprint)["runtime_status"], "invalid_input")

    def test_ci_dependencies_are_limited_to_owner_model_and_referenced_tdr(self) -> None:
        ep_a = ep_result("ep-001")
        ep_b = ep_result("ep-002")
        model_a = materialize_runtime.make_machine_entity(
            "test-condition-design", "model", "ep-001", current_model_content("ep-001"), model_key="ep-001",
        )
        model_b = materialize_runtime.make_machine_entity(
            "test-condition-design", "model", "ep-002", current_model_content("ep-002"), model_key="ep-002",
        )
        tcn = materialize_runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        authority = materialize_runtime.make_machine_entity(
            "spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001", "text": "current authority"},
        )
        source_targets = [
            {
                "source_model_key": model_key, "target_ref": target["target_ref"],
                "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": source["generation_fingerprint"],
            }
            for model_key, source in (("ep-001", ep_a), ("ep-002", ep_b))
            for target in source["payload"]["targets"]
        ]
        tdr = test_data_output(
            ep_a,
            [
                {
                    "requirement_key": "role-a", "environment_key": None, "dimension_key": "role", "operator": "eq",
                    "authority_refs": ["SPEC-001"], "source_model_key": "ep-001", "source_target_versions": [],
                    "value": {"type": "string", "value": "admin"},
                },
                {
                    "requirement_key": "role-b", "environment_key": None, "dimension_key": "role", "operator": "eq",
                    "authority_refs": [], "source_model_key": "ep-002", "source_target_versions": [],
                    "value": {"type": "string", "value": "user"},
                },
            ],
            model_entities=[model_a, model_b],
            source_targets=source_targets,
            source_runtime_units=[
                {"skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": ep_a["generation_fingerprint"]},
                {"skill": "test-condition-design", "runtime_unit_key": "model:ep-002", "generation_fingerprint": ep_b["generation_fingerprint"]},
            ],
            authority_entities=[authority],
        )
        self.assertEqual(tdr["runtime_status"], "ok", tdr)
        tdr_entities = tdr["payload"]["entities"]
        tdr_by_ref = {row["entity_ref"]: row for row in tdr_entities}

        request = materialize_request(ep_a)
        request["metadata"]["upstream_entities"] = [
            {key: entity[key] for key in ("skill", "entity_type", "entity_ref", "content")}
            for entity in [tcn, model_a, model_b, *tdr_entities]
        ]
        request["metadata"]["upstream_runtime_units"] = [
            {"skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": ep_a["generation_fingerprint"]},
            {"skill": "test-condition-design", "runtime_unit_key": "model:ep-002", "generation_fingerprint": ep_b["generation_fingerprint"]},
            {"skill": "test-condition-design", "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": tdr["generation_fingerprint"]},
        ]
        request["input"]["active_model_metadata"] = [
            {"model_key": key, "model_type": "ep", "technique_slug": "ep", "parent_tcn_id": "TCN-001", "content_fingerprint": entity["content_fingerprint"]}
            for key, entity in (("ep-001", model_a), ("ep-002", model_b))
        ]
        request["input"]["models"] = [model_result_for(ep_a, "ep-001"), model_result_for(ep_b, "ep-002")]
        request["input"]["test_data_requirements"] = tdr["payload"]["normalized_requirements"]
        request["input"]["target_annotations"] = [
            {
                "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"],
                "generation_fingerprint": result["generation_fingerprint"], "priority": "中", "priority_override_reason": None,
                "expected_result_root": f"root-{target['target_key'].replace(':', '-')}",
                "test_data_requirement_refs": ["data:role-a"] if model_key == "ep-001" else [],
            }
            for model_key, result in (("ep-001", ep_a), ("ep-002", ep_b))
            for target in result["payload"]["targets"]
        ]
        semantic_target = ep_b["payload"]["targets"][0]
        request["input"]["semantic_coverage_items"] = [{
            "draft_key": "semantic-b", "model_key": "ep-002", "identity_action": "new", "reuse_semantic_item_key": None,
            "reuse_ci_id": None, "source_target_versions": [{
                "target_ref": semantic_target["target_ref"], "target_content_fingerprint": semantic_target["target_content_fingerprint"],
                "generation_fingerprint": ep_b["generation_fingerprint"],
            }],
            "item_text": "additional semantic coverage", "authority_refs": [], "reference_refs": [], "priority": "中",
            "priority_override_reason": None, "expected_result_root": "root-semantic-b", "test_data_requirement_refs": [],
        }]

        materialized = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(materialized["runtime_status"], "ok", materialized)
        ci_entities = materialized["payload"]["entities"]
        ci_a = next(row for row in ci_entities if row["entity_type"] == "ci" and row["content"]["source_kind"] == "runtime_target" and row["content"]["model_key"] == "ep-001")
        ci_b = next(row for row in ci_entities if row["entity_type"] == "ci" and row["content"]["source_kind"] == "runtime_target" and row["content"]["model_key"] == "ep-002")
        semantic_ci = next(row for row in ci_entities if row["entity_type"] == "ci" and row["content"]["source_kind"] == "semantic_item")
        identities = lambda entity: {(row["skill"], row["entity_type"], row["entity_ref"]) for row in entity["upstream_entity_dependencies"]}
        self.assertEqual(identities(ci_a), {
            ("test-condition-design", "tcn", "TCN-001"), ("test-condition-design", "model", "ep-001"),
            ("test-condition-design", "test_data_requirement", "data:role-a"),
        })
        self.assertEqual(identities(ci_b), {("test-condition-design", "tcn", "TCN-001"), ("test-condition-design", "model", "ep-002")})
        self.assertEqual(identities(semantic_ci), {("test-condition-design", "tcn", "TCN-001"), ("test-condition-design", "model", "ep-002")})

        current_authorities = [authority]
        unrelated_authority = materialize_runtime.make_machine_entity(
            "spec-analysis", "authority", "SPEC-OTHER", {"authority_id": "SPEC-OTHER", "text": "unrelated authority"},
        )
        machine_rows = [tcn, model_a, model_b, *tdr_entities, *ci_entities, *current_authorities, unrelated_authority]
        def freshness_states(rows: list[dict]) -> dict[tuple[str, str], str]:
            current = [{**row, "runtime_dependencies": []} for row in rows]
            return {
                (row["entity_type"], row["entity_ref"]): row["freshness_status"]
                for row in runtime.evaluate_entity_freshness(current, {})
            }

        def replace_identity(rows: list[dict], replacement: dict) -> list[dict]:
            identity = (replacement["skill"], replacement["entity_type"], replacement["entity_ref"])
            return [row for row in rows if (row["skill"], row["entity_type"], row["entity_ref"]) != identity] + [replacement]

        changed_model_a = materialize_runtime.make_machine_entity("test-condition-design", "model", "ep-001", {**current_model_content("ep-001"), "revision": 2}, model_key="ep-001")
        states = freshness_states(replace_identity(machine_rows, changed_model_a))
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "stale")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "current")

        changed_unrelated_authority = materialize_runtime.make_machine_entity(
            "spec-analysis", "authority", "SPEC-OTHER", {"authority_id": "SPEC-OTHER", "text": "changed unrelated authority"},
        )
        states = freshness_states(replace_identity(machine_rows, changed_unrelated_authority))
        self.assertEqual(states[("test_data_requirement", "data:role-a")], "current")
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "current")

        changed_model_b = materialize_runtime.make_machine_entity("test-condition-design", "model", "ep-002", {**current_model_content("ep-002"), "revision": 2}, model_key="ep-002")
        states = freshness_states(replace_identity(machine_rows, changed_model_b))
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "current")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "stale")
        self.assertEqual(states[("ci", semantic_ci["entity_ref"])], "stale")

        changed_tdr_a = materialize_runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:role-a", {**tdr_by_ref["data:role-a"]["content"], "revision": 2})
        states = freshness_states(replace_identity(machine_rows, changed_tdr_a))
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "stale")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "current")

        changed_tdr_b = materialize_runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:role-b", {**tdr_by_ref["data:role-b"]["content"], "revision": 2})
        states = freshness_states(replace_identity(machine_rows, changed_tdr_b))
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "current")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "current")

        changed_authority = materialize_runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001", "text": "changed authority"})
        states = freshness_states(replace_identity(machine_rows, changed_authority))
        self.assertEqual(states[("test_data_requirement", "data:role-a")], "stale")
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "stale")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "current")

        changed_tcn = materialize_runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001", "revision": 2})
        states = freshness_states(replace_identity(machine_rows, changed_tcn))
        self.assertEqual(states[("ci", ci_a["entity_ref"])], "stale")
        self.assertEqual(states[("ci", ci_b["entity_ref"])], "stale")
        self.assertEqual(states[("ci", semantic_ci["entity_ref"])], "stale")

    def test_consumer_rederives_applicability_and_rejects_tampered_saved_refs(self) -> None:
        ep = ep_result()
        targets = ep["payload"]["targets"]
        versions = [{key: targets[0][key] for key in ("target_ref", "target_content_fingerprint")} | {"generation_fingerprint": ep["generation_fingerprint"]}]
        requirements = [
            {"requirement_key": "role-any", "environment_key": None, "dimension_key": "role", "operator": "enum", "authority_refs": [], "source_model_key": "ep-001", "source_target_versions": [], "values": [{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}]},
            {"requirement_key": "role-one", "environment_key": None, "dimension_key": "role", "operator": "eq", "authority_refs": [], "source_model_key": "ep-001", "source_target_versions": versions, "value": {"type": "string", "value": "admin"}},
        ]
        produced = test_data_output(ep, requirements)
        self.assertEqual(produced["runtime_status"], "ok")
        target_map = {target["target_ref"]: {
            "model_key": "ep-001", "target_key": target["target_key"], "target_content_fingerprint": target["target_content_fingerprint"],
            "generation_fingerprint": ep["generation_fingerprint"], "execution_fingerprint": target["execution_fingerprint"], "materializable": target["materializable"],
        } for target in targets}
        current_models = {"ep-001": {"model_type": "ep", "technique_slug": "ep"}}
        normalized = materialize_runtime._validate_test_data_requirements(produced["payload"]["normalized_requirements"], target_map, current_models)
        rows = {row["requirement_key"]: row for row in normalized.values()}
        self.assertEqual(rows["role-any"]["applicable_target_refs"], sorted(target["target_ref"] for target in targets))
        self.assertEqual(rows["role-one"]["applicable_target_refs"], [targets[0]["target_ref"]])

        tampered = [dict(row) for row in produced["payload"]["normalized_requirements"]]
        tampered[0]["applicable_target_refs"] = []
        with self.assertRaises(materialize_runtime.InvalidInput):
            materialize_runtime._validate_test_data_requirements(tampered, target_map, current_models)

    def test_merge_union_detects_conflict_that_target_scoped_inputs_allow(self) -> None:
        ep = ep_result()
        source_targets = ep["payload"]["targets"]
        requirements = []
        for index, value in enumerate(("admin", "user")):
            target = source_targets[index]
            requirements.append({
                "requirement_key": f"role-{index}", "environment_key": None, "dimension_key": "role", "operator": "eq", "authority_refs": [],
                "source_model_key": "ep-001", "source_target_versions": [{"target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"]}],
                "value": {"type": "string", "value": value},
            })
        produced = test_data_output(ep, requirements)
        self.assertEqual(produced["runtime_status"], "ok")
        self.assertEqual(produced["result_status"], "ready")

        common_execution = digest({"execution": "same merge witness"})
        targets = {target["target_ref"]: {
            "model_key": "ep-001", "target_key": target["target_key"], "target_content_fingerprint": target["target_content_fingerprint"],
            "generation_fingerprint": ep["generation_fingerprint"], "execution_fingerprint": common_execution, "materializable": True,
        } for target in source_targets}
        current_models = {"ep-001": {"model_type": "ep", "technique_slug": "ep"}}
        data_rows = materialize_runtime._validate_test_data_requirements(produced["payload"]["normalized_requirements"], targets, current_models)
        data_refs = {row["requirement_key"]: row["data_ref"] for row in data_rows.values()}
        annotations = {
            source_targets[0]["target_ref"]: {"expected_result_root": "shared-root", "test_data_requirement_refs": [data_refs["role-0"]]},
            source_targets[1]["target_ref"]: {"expected_result_root": "shared-root", "test_data_requirement_refs": [data_refs["role-1"]]},
        }
        merge = [{
            "merge_group_key": "merge-role", "model_key": "ep-001", "target_refs": [row["target_ref"] for row in source_targets],
            "target_versions": [{"target_ref": target["target_ref"], "target_content_fingerprint": targets[target["target_ref"]]["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"], "execution_fingerprint": common_execution} for target in source_targets],
        }]
        with self.assertRaises(materialize_runtime.InvalidInput):
            materialize_runtime._validate_merge_groups(merge, targets, annotations, {}, data_rows, "TCN-001")


if __name__ == "__main__":
    unittest.main()
