from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("test_condition_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


class StrictJsonTests(unittest.TestCase):
    def test_rejects_duplicate_keys_and_non_finite_values(self) -> None:
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(runtime.InvalidInput):
                    runtime.strict_loads(raw)

    def test_rejects_invalid_utf8_and_unpaired_surrogate(self) -> None:
        with self.assertRaises(runtime.InvalidInput):
            runtime.strict_loads(b"{\"a\":\xff}")
        with self.assertRaises(runtime.InvalidInput):
            runtime.strict_loads(b'{"a":"\\ud800"}')

    def test_rejects_depth_and_string_limits_before_normalization(self) -> None:
        too_deep = (b"[" * (runtime.MAX_DEPTH + 1)) + b"0" + (b"]" * (runtime.MAX_DEPTH + 1))
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(too_deep)
        too_long = json.dumps({"a": "x" * (runtime.MAX_STRING_BYTES + 1)}, ensure_ascii=False).encode()
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(too_long)

    def test_exact_numbers_remain_distinct_from_strings_and_float(self) -> None:
        value = runtime.strict_loads(b'{"integer":1,"decimal":1.0,"exponent":1e3,"text":"1"}')
        self.assertEqual(value["integer"], 1)
        self.assertEqual(value["decimal"], 1)
        self.assertEqual(value["exponent"], 1000)
        self.assertNotEqual(runtime.canonical_json_text(value["integer"]), runtime.canonical_json_text(value["text"]))
        self.assertNotEqual(runtime.canonical_json_text(value["decimal"]), runtime.canonical_json_text("1.0"))
        self.assertNotEqual(runtime.canonical_json_text(value["exponent"]), runtime.canonical_json_text("1e3"))

    def test_rejects_expanded_numeric_limit(self) -> None:
        raw = ('{"n":1e' + str(runtime.MAX_NUMERIC_CHARS + 1) + '}').encode()
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(raw)


class MachineBlockExtractionTests(unittest.TestCase):
    def test_extract_machine_blocks_preserves_identity_for_crlf_markdown(self) -> None:
        markdown = runtime.render_machine_entities(
            "test-condition-design",
            [runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})],
        ).replace("\n", "\r\n")

        blocks = runtime.extract_machine_blocks(markdown, "Machine Entities")

        self.assertEqual([identity for identity, _body in blocks], ["test-condition-design"])


class CanonicalAndFingerprintTests(unittest.TestCase):
    def test_canonicalizes_set_like_arrays_and_record_arrays(self) -> None:
        left = {
            "authority_refs": ["SPEC-002", "SPEC-001"],
            "upstream_entities": [
                {"skill": "z", "entity_type": "model", "entity_ref": "B"},
                {"skill": "a", "entity_type": "model", "entity_ref": "A"},
            ],
        }
        right = {
            "upstream_entities": [
                {"entity_ref": "A", "entity_type": "model", "skill": "a"},
                {"entity_ref": "B", "entity_type": "model", "skill": "z"},
            ],
            "authority_refs": ["SPEC-001", "SPEC-002"],
        }
        self.assertEqual(runtime.canonical_json_text(runtime.canonicalize(left)), runtime.canonical_json_text(runtime.canonicalize(right)))
        self.assertEqual(runtime.sha256_digest(left), runtime.sha256_digest(right))

    def test_authority_and_risk_refs_are_sorted_without_hiding_duplicates(self) -> None:
        normalized = runtime.canonicalize({"authority_refs": ["SPEC-002", "SPEC-001", "SPEC-001"], "risk_refs": ["R-002", "R-001", "R-001"]})
        self.assertEqual(normalized["authority_refs"], ["SPEC-001", "SPEC-001", "SPEC-002"])
        self.assertEqual(normalized["risk_refs"], ["R-001", "R-001", "R-002"])

    def test_lf_normalized_implementation_fingerprint(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.py"
            path.write_bytes(b"a\r\nb\r")
            first = runtime.implementation_fingerprint(path)
            path.write_bytes(b"a\nb\n")
            self.assertEqual(first, runtime.implementation_fingerprint(path))

    def test_exact_decimal_operations_are_not_binary_float_operations(self) -> None:
        self.assertEqual(runtime.exact_add("0.1", "0.2"), "0.3")
        self.assertEqual(runtime.exact_multiply("1.25", "0.8"), "1")
        self.assertEqual(runtime.exact_compare("1.00", "1"), 0)

    def test_constraint_intersection_contract_covers_typed_ranges_and_versions(self) -> None:
        tv = lambda kind, value: {"type": kind, "value": value}
        eq = {"operator": "eq", "value": tv("integer", 5)}
        enum = {"operator": "enum", "values": [tv("integer", 3), tv("integer", 5)]}
        range_row = {"operator": "range", "minimum": tv("integer", 1), "maximum": tv("integer", 5), "minimum_inclusive": True, "maximum_inclusive": True}
        self.assertTrue(runtime.constraint_intersection_compatible([eq, range_row]))
        self.assertTrue(runtime.constraint_intersection_compatible([enum, range_row]))

        left = {"operator": "range", "minimum": tv("integer", 1), "maximum": tv("integer", 5), "minimum_inclusive": True, "maximum_inclusive": True}
        exclusive = {"operator": "range", "minimum": tv("integer", 5), "maximum": tv("integer", 8), "minimum_inclusive": False, "maximum_inclusive": True}
        inclusive = {**exclusive, "minimum_inclusive": True}
        self.assertFalse(runtime.constraint_intersection_compatible([left, exclusive]))
        self.assertTrue(runtime.constraint_intersection_compatible([left, inclusive]))
        point_open = {**left, "minimum": tv("integer", 5), "minimum_inclusive": False}
        self.assertFalse(runtime.constraint_intersection_compatible([point_open]))
        point_closed = {**point_open, "minimum_inclusive": True}
        self.assertTrue(runtime.constraint_intersection_compatible([point_closed]))

        version_a = {"operator": "version_range", "minimum": "1.0", "maximum": "2.0", "minimum_inclusive": True, "maximum_inclusive": True}
        version_b = {"operator": "version_range", "minimum": "2.1", "maximum": "3.0", "minimum_inclusive": True, "maximum_inclusive": True}
        version_touch_open = {**version_a, "minimum": "2.0", "maximum": "3.0", "minimum_inclusive": False}
        version_touch_closed = {**version_touch_open, "minimum_inclusive": True, "maximum": "2.0"}
        self.assertFalse(runtime.constraint_intersection_compatible([version_a, version_b]))
        self.assertFalse(runtime.constraint_intersection_compatible([version_a, version_touch_open]))
        self.assertTrue(runtime.constraint_intersection_compatible([version_a, version_touch_closed]))

    def test_fixed_offset_datetime_range_uses_absolute_instants_and_keeps_offsets(self) -> None:
        first = {"operator": "range", "minimum": {"type": "fixed_offset_datetime", "value": "2026-09-23T10:00:00+09:00"}, "maximum": {"type": "fixed_offset_datetime", "value": "2026-09-23T10:00:00+09:00"}, "minimum_inclusive": True, "maximum_inclusive": True}
        second = {"operator": "range", "minimum": {"type": "fixed_offset_datetime", "value": "2026-09-23T01:00:00+00:00"}, "maximum": {"type": "fixed_offset_datetime", "value": "2026-09-23T01:00:00+00:00"}, "minimum_inclusive": True, "maximum_inclusive": True}
        self.assertTrue(runtime.constraint_intersection_compatible([first, second]))
        self.assertEqual(runtime.typed_value(first["minimum"])["value"], "2026-09-23T10:00:00+09:00")

    def test_unsupported_intersection_is_not_assumed_compatible(self) -> None:
        boolean = {"operator": "boolean", "value": True}
        enum = {"operator": "enum", "values": [{"type": "boolean", "value": True}]}
        with self.assertRaises(runtime.UnsupportedInput):
            runtime.constraint_intersection_compatible([boolean, enum])

    def test_target_postprocessing_is_stable_and_requires_execution(self) -> None:
        rows = runtime.post_process_targets(
            "ep-001",
            [
                {"target_key": "R1", "materializable": True, "execution": {"value": "low"}},
                {"target_key": "R2", "materializable": False, "execution": None},
            ],
        )
        self.assertEqual(rows[0]["target_ref"], runtime.target_ref("ep-001", "R1"))
        self.assertEqual(rows[0]["execution_fingerprint"], runtime.sha256_digest({"value": "low"}))
        self.assertIsNone(rows[1]["execution_fingerprint"])
        with self.assertRaises(runtime.InvalidInput):
            runtime.post_process_targets("ep-001", [{"target_key": "R1", "materializable": True, "execution": None}])


class EntityAndEvidenceTests(unittest.TestCase):
    def _entity(self, ref: str = "TCN-001") -> dict:
        return runtime.make_machine_entity(
            "test-condition-design",
            "tcn",
            ref,
            {"tcn_id": ref, "technique_slugs": ["equivalence-partitioning"]},
        )

    def _artifact(self, *, include_model: bool = True) -> str:
        normalized = {
            "tcn_id": "TCN-001",
            "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": ([{"model_key": "ep-001", "model_type": "ep"}] if include_model else []),
        }
        units = [
            ("artifact:condition_structure:all", None),
            ("model:ep-001", "ep-001"),
            ("artifact:materialize_coverage:TCN-001", None),
        ]
        blocks = []
        for unit, model_key in units:
            generator = {
                "artifact:condition_structure:all": "condition_structure",
                "model:ep-001": "equivalence_partitions",
                "artifact:materialize_coverage:TCN-001": "materialize_coverage",
            }[unit]
            generator_contract_version = {
                "condition_structure": "condition-structure-v1",
                "equivalence_partitions": "equivalence-partitions-v1",
                "materialize_coverage": "materialize-coverage-v1",
            }[generator]
            model_type = "ep" if model_key else None
            metadata = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
                "generator_contract_version": generator_contract_version, "runtime_unit_key": unit, "model_key": model_key, "model_type": model_type,
                "technique_slug": "ep" if model_key else None, "selection_source": "analysis" if model_key else None,
                "selection_key": "SEL-001" if model_key else None, "scope_key": "TCN-001" if not model_key and "materialize" in unit else "all" if not model_key else None,
                "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {},
                "authority_refs": [], "reference_refs": [],
            }
            input_value = {"runtime_unit_key": unit}
            input_fp = runtime.input_fingerprint("test-condition-design", unit, "direct", input_value, [], [], metadata["selection_source"])
            model_fp = runtime.model_fingerprint(metadata, input_fp)
            runtime_fp = runtime.implementation_fingerprint(RUNTIME_PATH)
            generator_path = RUNTIME_PATH.parent / f"{generator}.py"
            generator_fp = runtime.implementation_fingerprint(generator_path)
            generation_fp = runtime.generation_fingerprint(
                generator=generator, input_fp=input_fp, model_fp=model_fp, runtime_contract_version="runtime-v1",
                generator_contract_version=generator_contract_version, runtime_impl_fp=runtime_fp, generator_impl_fp=generator_fp,
                upstream=[], static_data_versions={},
            )
            result = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
                "generator_contract_version": generator_contract_version, "generator": generator, "runtime_unit_key": unit, "model_key": model_key,
                "input_fingerprint": input_fp, "model_fingerprint": model_fp, "generation_fingerprint": generation_fp,
                "runtime_implementation_fingerprint": runtime_fp, "generator_implementation_fingerprint": generator_fp,
                "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "support_status": "supported",
                "static_data_versions": {}, "runtime_status": "ok", "result_status": "ready", "runtime_required": True,
                "deterministic_generated": True, "fallback_reason": None, "payload": {}, "issues": [],
            }
            blocks.append(runtime.render_runtime_input("test-condition-design", metadata, input_value))
            blocks.append(runtime.render_runtime_result("test-condition-design", result))
        blocks.append(
            runtime.render_machine_entities(
                "test-condition-design",
                [
                    self._entity(),
                    runtime.make_machine_entity(
                        "test-condition-design",
                        "model",
                        "ep-001",
                        {"model_key": "ep-001", "model_type": "ep"},
                        model_key="ep-001",
                    ),
                ],
            )
        )
        return normalized, "\n".join(blocks)

    def test_machine_entity_fingerprint_and_duplicate_identity(self) -> None:
        entity = self._entity()
        self.assertEqual(entity["content_fingerprint"], runtime.sha256_digest(entity["content"]))
        with self.assertRaises(runtime.InvalidInput):
            runtime.validate_entity_collection([entity, entity], expected_skill="test-condition-design")
        invalid = dict(entity)
        invalid["entity_ref"] = ""
        with self.assertRaises(runtime.InvalidInput):
            runtime.validate_machine_entity(invalid)

    def test_shared_dependency_resolver_uses_full_identity_and_current_content(self) -> None:
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SHARED", {"authority_id": "SHARED"})
        risk = runtime.make_machine_entity("test-analysis", "product_risk", "SHARED", {"risk_id": "SHARED"})
        current = [authority, risk]
        dependencies = runtime.resolve_entity_dependencies(
            [("spec-analysis", "authority", "SHARED"), ("test-analysis", "product_risk", "SHARED")],
            current,
        )
        self.assertEqual(
            {(row["skill"], row["entity_type"], row["entity_ref"]): row["content_fingerprint"] for row in dependencies},
            {
                ("spec-analysis", "authority", "SHARED"): authority["content_fingerprint"],
                ("test-analysis", "product_risk", "SHARED"): risk["content_fingerprint"],
            },
        )
        with self.assertRaises(runtime.InvalidInput):
            runtime.resolve_entity_dependencies([("spec-analysis", "product_risk", "SHARED")], current)
        with self.assertRaises(runtime.InvalidInput):
            runtime.resolve_entity_dependencies([("spec-analysis", "authority", "SHARED")], [risk])

    def _scoped_entity(self, *, content: dict | None = None, context: dict | None = None) -> tuple[dict, dict]:
        current_context = context or {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "condition-structure-v1",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
            "generator_implementation_fingerprint": runtime.implementation_fingerprint(REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "condition_structure.py"),
            "static_data_versions": {},
        }
        entity = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", content or {"tcn_id": "TCN-001", "conditions": ["A"]},
            runtime_dependencies=[runtime.machine_entity_runtime_dependency("test-condition-design", "artifact:condition_structure:all")],
        )
        aggregate_generation = "sha256:" + "1" * 64
        entity = runtime.bind_current_entity_runtime_dependencies(
            {"entities": [entity]}, aggregate_generation, runtime_context=current_context,
        )["entities"][0]
        current_runtime = {
            "skill": "test-condition-design", "runtime_unit_key": "artifact:condition_structure:all",
            "generation_fingerprint": "sha256:" + "2" * 64, "freshness_status": "current",
            **current_context,
        }
        return entity, current_runtime

    def test_entity_scoped_runtime_dependency_is_fresh_across_unrelated_scope_generation(self) -> None:
        entity, current_runtime = self._scoped_entity()
        dependency = entity["runtime_dependencies"][0]
        self.assertRegex(dependency["runtime_unit_key"], r"^artifact:condition_structure:all#entity:sha256:[0-9a-f]{64}$")
        self.assertEqual(
            dependency["runtime_unit_key"],
            runtime.machine_entity_runtime_unit_key("artifact:condition_structure:all", entity),
        )
        current = runtime.evaluate_entity_freshness(
            [entity], {("test-condition-design", "artifact:condition_structure:all"): current_runtime},
        )
        self.assertEqual(current[0]["freshness_status"], "current", current)

        changed_content = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001", "conditions": ["changed"]},
            runtime_dependencies=entity["runtime_dependencies"],
        )
        stale_content = runtime.evaluate_entity_freshness(
            [changed_content], {("test-condition-design", "artifact:condition_structure:all"): current_runtime},
        )
        self.assertEqual(stale_content[0]["freshness_status"], "stale")
        self.assertTrue(any(row["reason_code"] == "runtime_generation_mismatch" for row in stale_content[0]["stale_reasons"]))

    def test_entity_scoped_runtime_dependency_tracks_producer_metadata_and_key(self) -> None:
        entity, current_runtime = self._scoped_entity()
        runtime_key = ("test-condition-design", "artifact:condition_structure:all")
        for field, changed_value in (
            ("runtime_contract_version", "runtime-v2"),
            ("generator_contract_version", "condition-structure-v2"),
            ("runtime_implementation_fingerprint", "sha256:" + "3" * 64),
            ("generator_implementation_fingerprint", "sha256:" + "4" * 64),
            ("static_data_versions", {"schema_catalog": "v2"}),
        ):
            with self.subTest(field=field):
                changed_runtime = {**current_runtime, field: changed_value}
                stale = runtime.evaluate_entity_freshness([entity], {runtime_key: changed_runtime})
                self.assertEqual(stale[0]["freshness_status"], "stale")

        tampered = {**entity, "runtime_dependencies": [dict(entity["runtime_dependencies"][0])]}
        tampered["runtime_dependencies"][0]["runtime_unit_key"] = "artifact:condition_structure:all#entity:sha256:" + "f" * 64
        stale_key = runtime.evaluate_entity_freshness([tampered], {runtime_key: current_runtime})
        self.assertEqual(stale_key[0]["freshness_status"], "stale")
        self.assertTrue(any(row["reason_code"] == "runtime_generation_mismatch" for row in stale_key[0]["stale_reasons"]))

        expected = runtime._default_expected_runtime_units("test-condition-design", {"test_conditions": [], "models": []}, "")
        self.assertFalse(any("#entity:" in row["runtime_unit_key"] for row in expected))
        envelope = {
            "skill": "test-condition-design", "runtime_unit_key": "artifact:condition_structure:all", "model_key": None,
            "support_status": "supported", "result_status": "ready", "runtime_status": "ok", "runtime_required": True,
            "deterministic_generated": True, "generation_fingerprint": "sha256:" + "5" * 64,
            "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "unsupported_items": [], "payload": {},
            **{field: current_runtime[field] for field in (
                "runtime_contract_version", "generator_contract_version", "runtime_implementation_fingerprint",
                "generator_implementation_fingerprint", "static_data_versions",
            )},
        }
        runtime_projection = runtime.runtime_unit_row(envelope)
        self.assertTrue({
            "runtime_contract_version", "generator_contract_version", "runtime_implementation_fingerprint",
            "generator_implementation_fingerprint", "static_data_versions",
        }.issubset(runtime_projection))

    def test_common_disposition_currentness_covered_rules_and_dependencies(self) -> None:
        upstream = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001"})
        covered = runtime.make_machine_entity("test-analysis", "product_risk", "R-001", {"risk_id": "R-001"})
        authority = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-002", {"authority_id": "AUTH-002"})
        current = [upstream, covered, authority]
        row = {
            "upstream_entity": {key: upstream[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
            "handling": "重複", "reason": "already covered", "authority_refs": ["AUTH-001", "AUTH-002"],
            "covered_by_entity": {key: covered[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
        }
        normalized, dependencies = runtime.normalize_machine_entity_disposition(
            row, current, allowed_handlings={"対象外", "重複"}, allowed_upstream_entity_types={"authority"}, input_mode="artifact",
        )
        self.assertEqual(normalized["authority_refs"], ["AUTH-001", "AUTH-002"])
        self.assertEqual(
            {(item["skill"], item["entity_type"], item["entity_ref"]) for item in dependencies},
            {("spec-analysis", "authority", "AUTH-001"), ("spec-analysis", "authority", "AUTH-002"), ("test-analysis", "product_risk", "R-001")},
        )
        regular = {**row, "handling": "対象外", "covered_by_entity": None}
        runtime.normalize_machine_entity_disposition(
            regular, current, allowed_handlings={"対象外", "重複"}, allowed_upstream_entity_types={"authority"}, input_mode="artifact",
        )

        disposition = runtime.make_machine_entity("test-requirement-design", "disposition", "authority:AUTH-001", normalized, upstream_entity_dependencies=dependencies)
        changed_upstream = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001", "text": "changed"})
        changed_covered = runtime.make_machine_entity("test-analysis", "product_risk", "R-001", {"risk_id": "R-001", "text": "changed"})
        unrelated = runtime.make_machine_entity("test-analysis", "product_risk", "R-002", {"risk_id": "R-002", "text": "unrelated"})
        for replacement, expected in ((changed_upstream, "stale"), (changed_covered, "stale"), (unrelated, "current")):
            current_rows = [entity for entity in current if (entity["skill"], entity["entity_type"], entity["entity_ref"]) != (replacement["skill"], replacement["entity_type"], replacement["entity_ref"])]
            current_rows.append(replacement)
            current_rows.append(disposition)
            freshness = runtime.evaluate_entity_freshness(current_rows, {})
            status = next(item["freshness_status"] for item in freshness if item["entity_type"] == "disposition")
            self.assertEqual(status, expected)

        for invalid in (
            {**row, "upstream_entity": {**row["upstream_entity"], "content_fingerprint": "sha256:" + "f" * 64}},
            {**row, "upstream_entity": {"skill": "spec-analysis", "entity_type": "authority", "entity_ref": "AUTH-404", "content_fingerprint": "sha256:" + "f" * 64}},
            {**row, "covered_by_entity": None},
            {**row, "covered_by_entity": {**row["covered_by_entity"], "content_fingerprint": "sha256:" + "f" * 64}},
            {**row, "covered_by_entity": row["upstream_entity"]},
            {**row, "handling": "対象外"},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(runtime.InvalidInput):
                    runtime.normalize_machine_entity_disposition(
                        invalid, current, allowed_handlings={"対象外", "重複"}, allowed_upstream_entity_types={"authority"}, input_mode="artifact",
                    )

    def test_same_invocation_entity_dependency_accepts_current_runtime_placeholder(self) -> None:
        parent = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"},
            runtime_dependencies=[{"skill": "test-condition-design", "runtime_unit_key": "artifact:condition_structure:all", "generation_fingerprint": "__CURRENT__"}],
        )
        dependencies = runtime.resolve_entity_dependencies([("test-condition-design", "tcn", "TCN-001")], [parent])
        self.assertEqual(dependencies[0]["content_fingerprint"], parent["content_fingerprint"])

    def test_evidence_builder_is_independent_of_actual_unit_set(self) -> None:
        normalized, artifact = self._artifact()
        valid = runtime.verify_runtime_evidence(
            {
                "operation": "verify_runtime_evidence",
                "skill": "test-condition-design",
                "normalized_skill_input": normalized,
                "artifact_markdown": artifact,
                "previous_artifact_markdown": None,
                "partial_rerun": False,
            }
        )
        self.assertTrue(valid["valid"], valid)
        _, incomplete = self._artifact()
        incomplete = re.sub(r"### Machine Runtime Result: test-condition-design::model:ep-001\r?\n\r?\n```json\r?\n.*?\r?\n```\r?\n", "", incomplete, count=1, flags=re.DOTALL)
        invalid = runtime.verify_runtime_evidence(
            {
                "operation": "verify_runtime_evidence",
                "skill": "test-condition-design",
                "normalized_skill_input": normalized,
                "artifact_markdown": incomplete,
                "previous_artifact_markdown": None,
                "partial_rerun": False,
            }
        )
        self.assertFalse(invalid["valid"])
        self.assertIn("test-condition-design::model:ep-001", invalid["incomplete_pairs"])

    def test_current_structure_state_matches_materialize_result_projection(self) -> None:
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": [], "test_data_requirements": [],
            "previous_tcn_ids": [], "previous_model_keys": [], "previous_ci_ids": [],
            "update_scope_tcn_ids": [], "update_scope_model_keys": [],
        }
        payload = {
            "entities": [], "model_completion": [{
                "model_key": "ep-001", "required_target_refs": [], "closed_target_refs": [], "active_ci_ids": [],
                "semantic_item_keys": [], "materialize_complete": True,
            }],
            "target_id_map": [], "disposed_target_refs": [],
        }
        result = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "materialize-coverage-v1", "generator": "materialize_coverage",
            "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None,
            "input_fingerprint": "sha256:" + "1" * 64, "model_fingerprint": None, "generation_fingerprint": "sha256:" + "2" * 64,
            "runtime_implementation_fingerprint": "sha256:" + "3" * 64, "generator_implementation_fingerprint": "sha256:" + "4" * 64,
            "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "support_status": "supported", "static_data_versions": {},
            "runtime_status": "ok", "result_status": "ready", "runtime_required": True, "deterministic_generated": True,
            "fallback_reason": None, "payload": payload, "issues": [],
        }
        state = {
            "runtime_results": [{"identity": "test-condition-design::artifact:materialize_coverage:TCN-001", "result": result}],
            "carry_forward_entities": [], "previous_ci_id_state": [],
        }
        current_row = runtime._runtime_unit_result_row(result)
        self.assertEqual(current_row["model_completion"], payload["model_completion"])
        runtime.validate_current_structure_state(
            "test-condition-design", normalized, state,
            current_entities=[], current_runtime_units=[current_row],
        )

        tampered = json.loads(json.dumps(state))
        tampered["runtime_results"][0]["result"]["payload"]["model_completion"][0]["materialize_complete"] = False
        with self.assertRaises(runtime.InvalidInput):
            runtime.validate_current_structure_state(
                "test-condition-design", normalized, tampered,
                current_entities=[], current_runtime_units=[current_row],
            )

    def _tr_entity(self, ref: str, runtime_context: dict[str, object], generation_fp: str) -> dict:
        entity = runtime.make_machine_entity(
            "test-requirement-design", "tr", ref, {"tr_id": ref, "text": f"Requirement {ref}"},
            runtime_dependencies=[runtime.machine_entity_runtime_dependency("test-requirement-design", "artifact:requirement_structure:all")],
        )
        return runtime.bind_current_entity_runtime_dependencies(
            {"entities": [entity]}, generation_fp, runtime_context=runtime_context,
        )["entities"][0]

    def _tr_artifact(self, normalized: dict, entities: list[dict], state: list[dict], *, generator_fp: str | None = None, result_entities: list[dict] | None = None) -> str:
        skill = "test-requirement-design"
        unit = "artifact:requirement_structure:all"
        generator = "requirement_structure"
        generator_contract_version = "requirement-structure-v1"
        generator_path = REPO_ROOT / "skills" / skill / "scripts" / "requirement_structure.py"
        generator_impl_fp = generator_fp or runtime.implementation_fingerprint(generator_path)
        metadata = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": generator_contract_version, "runtime_unit_key": unit, "model_key": None,
            "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        input_fp = runtime.input_fingerprint(skill, unit, "direct", normalized, [], [], None)
        model_fp = runtime.model_fingerprint(metadata, input_fp)
        runtime_impl_fp = runtime.implementation_fingerprint(RUNTIME_PATH)
        generation_fp = runtime.generation_fingerprint(
            generator=generator, input_fp=input_fp, model_fp=model_fp,
            runtime_contract_version=runtime.RUNTIME_CONTRACT_VERSION,
            generator_contract_version=generator_contract_version,
            runtime_impl_fp=runtime_impl_fp, generator_impl_fp=generator_impl_fp,
            upstream=[], static_data_versions={},
        )
        context = {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": generator_contract_version,
            "runtime_implementation_fingerprint": runtime_impl_fp,
            "generator_implementation_fingerprint": generator_impl_fp,
            "static_data_versions": {},
        }
        envelope = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": generator_contract_version, "generator": generator, "runtime_unit_key": unit,
            "model_key": None, "input_fingerprint": input_fp, "model_fingerprint": model_fp,
            "generation_fingerprint": generation_fp, "runtime_implementation_fingerprint": runtime_impl_fp,
            "generator_implementation_fingerprint": generator_impl_fp, "upstream_entity_fingerprints": [],
            "upstream_runtime_units": [], "support_status": "supported", "static_data_versions": {},
            "runtime_status": "ok", "result_status": "ready", "runtime_required": True,
            "deterministic_generated": True, "fallback_reason": None,
            "payload": {"tr_id_state": state, "entities": entities if result_entities is None else result_entities}, "issues": [],
        }
        return "\n".join((
            runtime.render_runtime_input(skill, metadata, normalized),
            runtime.render_runtime_result(skill, envelope),
            runtime.render_machine_entities(skill, entities),
        ))

    def _structure_artifact(
        self,
        skill: str,
        normalized: dict,
        entities: list[dict],
        state_payload: dict,
        *,
        result_entities: list[dict] | None = None,
        extra_blocks: list[str] | None = None,
    ) -> str:
        generator, unit, version = {
            "test-condition-design": ("condition_structure", "artifact:condition_structure:all", "condition-structure-v1"),
            "test-case-design": ("case_structure", "artifact:case_structure:all", "case-structure-v1"),
        }[skill]
        runtime_path = REPO_ROOT / "skills" / skill / "scripts" / "runtime_contract.py"
        generator_path = runtime_path.parent / f"{generator}.py"
        metadata = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": version, "runtime_unit_key": unit, "model_key": None,
            "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        input_value = {"normalized": normalized}
        input_fp = runtime.input_fingerprint(skill, unit, "direct", input_value, [], [], None)
        model_fp = runtime.model_fingerprint(metadata, input_fp)
        runtime_fp = runtime.implementation_fingerprint(runtime_path)
        generator_fp = runtime.implementation_fingerprint(generator_path)
        generation_fp = runtime.generation_fingerprint(
            generator=generator, input_fp=input_fp, model_fp=model_fp,
            runtime_contract_version=runtime.RUNTIME_CONTRACT_VERSION, generator_contract_version=version,
            runtime_impl_fp=runtime_fp, generator_impl_fp=generator_fp, upstream=[], static_data_versions={},
        )
        payload = {**state_payload, "entities": entities if result_entities is None else result_entities}
        result = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": version, "generator": generator, "runtime_unit_key": unit, "model_key": None,
            "input_fingerprint": input_fp, "model_fingerprint": model_fp, "generation_fingerprint": generation_fp,
            "runtime_implementation_fingerprint": runtime_fp, "generator_implementation_fingerprint": generator_fp,
            "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "support_status": "supported",
            "static_data_versions": {}, "runtime_status": "ok", "result_status": "ready", "runtime_required": True,
            "deterministic_generated": True, "fallback_reason": None, "payload": payload, "issues": [],
        }
        blocks = [
            runtime.render_runtime_input(skill, metadata, input_value),
            runtime.render_runtime_result(skill, result),
            runtime.render_machine_entities(skill, entities),
        ]
        blocks.extend(extra_blocks or [])
        return "\n".join(blocks)

    def _artifact_runtime_pair(self, generator: str, unit: str, version: str, payload: dict) -> str:
        skill = "test-condition-design"
        generator_path = REPO_ROOT / "skills" / skill / "scripts" / f"{generator}.py"
        runtime_impl_fp = runtime.implementation_fingerprint(RUNTIME_PATH)
        generator_impl_fp = runtime.implementation_fingerprint(generator_path)
        scope_key = unit.split(":", 2)[-1]
        metadata = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": version, "runtime_unit_key": unit, "model_key": None,
            "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": scope_key, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        input_value = {"runtime_unit_key": unit}
        input_fp = runtime.input_fingerprint(skill, unit, "direct", input_value, [], [], None)
        model_fp = runtime.model_fingerprint(metadata, input_fp)
        generation_fp = runtime.generation_fingerprint(
            generator=generator, input_fp=input_fp, model_fp=model_fp,
            runtime_contract_version=runtime.RUNTIME_CONTRACT_VERSION,
            generator_contract_version=version, runtime_impl_fp=runtime_impl_fp,
            generator_impl_fp=generator_impl_fp, upstream=[], static_data_versions={},
        )
        result = {
            "envelope_version": "1", "skill": skill, "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": version, "generator": generator, "runtime_unit_key": unit,
            "model_key": None, "input_fingerprint": input_fp, "model_fingerprint": model_fp,
            "generation_fingerprint": generation_fp, "runtime_implementation_fingerprint": runtime_impl_fp,
            "generator_implementation_fingerprint": generator_impl_fp, "upstream_entity_fingerprints": [],
            "upstream_runtime_units": [], "support_status": "supported", "static_data_versions": {},
            "runtime_status": "ok", "result_status": "ready", "runtime_required": True,
            "deterministic_generated": True, "fallback_reason": None, "payload": payload, "issues": [],
        }
        return "\n".join((
            runtime.render_runtime_input(skill, metadata, input_value),
            runtime.render_runtime_result(skill, result),
        ))

    def test_partial_rerun_carries_scope_out_tcn_model_ci_tdr_and_dispositions(self) -> None:
        tcn_one = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        tcn_two = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        model_one = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001")
        model_two = runtime.make_machine_entity("test-condition-design", "model", "ep-002", {"model_key": "ep-002", "model_type": "ep"}, model_key="ep-002")
        ci_one = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        ci_two = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
        tdr_one = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-001", {"data_ref": "data:REQ-001", "requirement_key": "REQ-001", "source_model_key": "ep-001"}, model_key="ep-001")
        tdr_two = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-002", {"data_ref": "data:REQ-002", "requirement_key": "REQ-002", "source_model_key": "ep-002"}, model_key="ep-002")

        tr_two = runtime.make_machine_entity("test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002"})
        tr_two_dependency = runtime.machine_entity_dependency(tr_two)
        tr_disposition = runtime.make_machine_entity(
            "test-condition-design", "disposition", "tr:TR-002",
            {"upstream_entity": tr_two_dependency, "handling": "対象外", "reason": "scope ownership", "authority_refs": [], "covered_by_entity": None},
            upstream_entity_dependencies=[tr_two_dependency],
        )
        previous_entities = [tcn_one, tcn_two, model_one, model_two, ci_one, ci_two, tdr_one, tdr_two, tr_disposition]
        previous_state = {
            "tcn_id_state": [{"tcn_id": ref, "status": "active"} for ref in ("TCN-001", "TCN-002")],
            "model_key_state": [{"model_key": ref, "model_type": "ep", "status": "active"} for ref in ("ep-001", "ep-002")],
        }
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [], "models": [], "test_data_requirements": [], "ci_ids": [],
            "previous_tcn_ids": previous_state["tcn_id_state"], "previous_model_keys": previous_state["model_key_state"],
            "previous_ci_ids": [{"ci_id": "TCN-001-CI01", "status": "active"}], "update_scope_tcn_ids": ["TCN-001"],
            "update_scope_model_keys": ["ep-001"], "upstream_entities": [{"skill": "test-requirement-design", "entity_type": "tr", "entity_ref": "TR-002"}],
        }
        root_entities = [
            *[row for row in previous_entities if row["entity_type"] in {"tcn", "model"}],
            tr_disposition,
        ]
        previous_root = self._structure_artifact(
            "test-condition-design", normalized, previous_entities, previous_state,
            result_entities=root_entities,
            extra_blocks=[
                self._artifact_runtime_pair("materialize_coverage", "artifact:materialize_coverage:TCN-001", "materialize-coverage-v1", {"ci_id_state": [{"ci_id": "TCN-001-CI01", "status": "active"}], "entities": [ci_one]}),
                self._artifact_runtime_pair("materialize_coverage", "artifact:materialize_coverage:TCN-002", "materialize-coverage-v1", {"ci_id_state": [{"ci_id": "TCN-002-CI01", "status": "active"}], "entities": [ci_two]}),
                self._artifact_runtime_pair("test_data_requirements", "artifact:test_data_requirements:all", "test-data-requirements-v1", {"entities": [tdr_one, tdr_two]}),
                runtime.render_machine_entities("test-requirement-design", [tr_two]),
            ],
        )
        # Keep the previous artifact's runtime result shape production-like:
        # one condition_structure full snapshot and TCN-scoped materialize states.
        previous = previous_root
        current_state = {
            "tcn_id_state": [{"tcn_id": "TCN-001", "status": "deleted"}, {"tcn_id": "TCN-002", "status": "active"}],
            "model_key_state": [{"model_key": "ep-001", "model_type": "ep", "status": "deleted"}, {"model_key": "ep-002", "model_type": "ep", "status": "active"}],
        }
        carry = [tcn_two, model_two, ci_two, tdr_two, tr_disposition]
        candidate = self._structure_artifact(
            "test-condition-design", normalized, carry, current_state, result_entities=[],
            extra_blocks=[runtime.render_machine_entities("test-requirement-design", [tr_two])],
        )
        checked = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-condition-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertTrue(checked["valid"], checked)
        self.assertIsNotNone(checked["current_structure_state"])
        self.assertEqual(
            checked["current_structure_state"]["previous_ci_id_state"],
            [
                {"ci_id": "TCN-001-CI01", "status": "active"},
                {"ci_id": "TCN-002-CI01", "status": "active"},
            ],
        )
        expected = {(row["entity_type"], row["entity_ref"]) for row in checked["expected_entities"]}
        self.assertEqual(expected, {(row["entity_type"], row["entity_ref"]) for row in [*carry, tr_two]})
        self.assertEqual(
            {runtime.entity_identity(row["skill"], row["entity_type"], row["entity_ref"]) for row in checked["current_structure_state"]["carry_forward_entities"]},
            {runtime.entity_identity(row["skill"], row["entity_type"], row["entity_ref"]) for row in carry},
        )

        # Feed the standalone verifier's fixed projection unchanged into both
        # production aggregators. Neither consumer reconstructs the scope-out
        # rows from current_entities.
        from tests.skills.runtime.test_traceability_runtime import metadata as traceability_metadata, run as run_traceability
        from tests.skills.runtime.test_workflow_runtime import metadata as workflow_metadata, run as run_workflow

        current_runtime_results = checked["current_structure_state"]["runtime_results"]
        current_runtime_rows = [runtime.runtime_unit_row(row["result"]) for row in current_runtime_results]
        workflow_request = {
            "metadata": workflow_metadata(),
            "input": {
                "workflow_scopes": [{
                    "skill": "test-condition-design", "target": "TCN-001", "execution_range": None,
                    "input_mode": "artifact", "normalized_input": normalized,
                    "current_structure_state": checked["current_structure_state"],
                }],
                "runtime_units": current_runtime_rows,
                "current_runtime_units": current_runtime_rows,
                "current_entities": [*carry, tr_two],
                "unsupported_item_closures": [],
            },
        }
        workflow_result = run_workflow(workflow_request)
        self.assertEqual(workflow_result["result_status"], "ready", workflow_result)
        self.assertEqual(workflow_result["payload"]["missing_entities"], [])
        self.assertEqual(workflow_result["payload"]["extra_entities"], [])
        self.assertEqual(workflow_result["payload"]["expected_entities"], checked["expected_entities"])

        traceability_request = {
            "metadata": traceability_metadata(),
            "input": {
                "analysis_scopes": [{
                    "skill": "test-condition-design", "target": "TCN-001", "execution_range": None,
                    "input_mode": "artifact", "normalized_input": normalized,
                    "current_structure_state": checked["current_structure_state"],
                }],
                "nodes": [], "edges": [], "dispositions": [],
                "runtime_units": current_runtime_rows,
                "current_entities": [*carry, tr_two],
                "current_runtime_units": current_runtime_rows,
                "unsupported_item_closures": [],
            },
        }
        traceability_result = run_traceability(traceability_request)
        self.assertEqual(traceability_result["result_status"], "ready", traceability_result)
        self.assertEqual(traceability_result["payload"]["missing_entities"], [])
        self.assertEqual(traceability_result["payload"]["extra_entities"], [])
        self.assertEqual(traceability_result["payload"]["expected_entities"], checked["expected_entities"])

        tampered_state = json.loads(json.dumps(checked["current_structure_state"]))
        self.assertTrue(tampered_state["runtime_results"])
        tampered_state["runtime_results"][0]["result"]["payload"]["tampered_projection"] = True
        tampered_workflow = json.loads(json.dumps(workflow_request))
        tampered_workflow["input"]["workflow_scopes"][0]["current_structure_state"] = tampered_state
        workflow_rejected = run_workflow(tampered_workflow)
        self.assertEqual(workflow_rejected["runtime_status"], "invalid_input")
        tampered_traceability = json.loads(json.dumps(traceability_request))
        tampered_traceability["input"]["analysis_scopes"][0]["current_structure_state"] = tampered_state
        traceability_rejected = run_traceability(tampered_traceability)
        self.assertEqual(traceability_rejected["runtime_status"], "invalid_input")

        input_blocks = dict(runtime.extract_machine_blocks(previous, "Machine Runtime Input", allow_duplicates=True))
        result_blocks = dict(runtime.extract_machine_blocks(previous, "Machine Runtime Result", allow_duplicates=True))
        reversed_blocks = []
        for identity in reversed(sorted(result_blocks)):
            reversed_blocks.append(runtime.render_runtime_input("test-condition-design", input_blocks[identity]["metadata"], input_blocks[identity]["input"]))
            reversed_blocks.append(runtime.render_runtime_result("test-condition-design", result_blocks[identity]))
        reversed_blocks.append(runtime.render_machine_entities("test-condition-design", [row for row in previous_entities if row["skill"] == "test-condition-design"]))
        reversed_blocks.append(runtime.render_machine_entities("test-requirement-design", [tr_two]))
        reordered = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-condition-design",
            "normalized_skill_input": normalized,
            "artifact_markdown": candidate,
            "previous_artifact_markdown": "\n".join(reversed_blocks),
            "partial_rerun": True,
        })
        self.assertTrue(reordered["valid"], reordered)
        self.assertEqual(reordered["expected_entities"], checked["expected_entities"])

        wrong_prefix_previous = self._structure_artifact(
            "test-condition-design", normalized, previous_entities, previous_state,
            result_entities=root_entities,
            extra_blocks=[
                self._artifact_runtime_pair("materialize_coverage", "artifact:materialize_coverage:TCN-001", "materialize-coverage-v1", {"ci_id_state": [{"ci_id": "TCN-002-CI01", "status": "active"}], "entities": [ci_two]}),
                self._artifact_runtime_pair("materialize_coverage", "artifact:materialize_coverage:TCN-002", "materialize-coverage-v1", {"ci_id_state": [{"ci_id": "TCN-002-CI01", "status": "active"}], "entities": [ci_two]}),
                self._artifact_runtime_pair("test_data_requirements", "artifact:test_data_requirements:all", "test-data-requirements-v1", {"entities": [tdr_one, tdr_two]}),
                runtime.render_machine_entities("test-requirement-design", [tr_two]),
            ],
        )
        bad_prefix = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-condition-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": wrong_prefix_previous,
            "partial_rerun": True,
        })
        self.assertFalse(bad_prefix["valid"])
        self.assertIn("invalid_previous_artifact", [issue["issue_type"] for issue in bad_prefix["issues"]])

        for label, previous_ci_ids in (
            ("other-tcn", [{"ci_id": "TCN-001-CI01", "status": "active"}, {"ci_id": "TCN-002-CI01", "status": "active"}]),
            ("status-mismatch", [{"ci_id": "TCN-001-CI01", "status": "deleted"}]),
        ):
            with self.subTest(label=label):
                invalid_normalized = {**normalized, "previous_ci_ids": previous_ci_ids}
                invalid = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": "test-condition-design",
                    "normalized_skill_input": invalid_normalized, "artifact_markdown": candidate,
                    "previous_artifact_markdown": previous,
                    "partial_rerun": True,
                })
                self.assertFalse(invalid["valid"])
                self.assertIn("invalid_previous_artifact", [issue["issue_type"] for issue in invalid["issues"]])

    def test_partial_rerun_requires_previous_artifact_when_scope_out_entities_are_active(self) -> None:
        tr_state = [{"tr_id": "TR-001", "status": "active"}, {"tr_id": "TR-002", "status": "active"}]
        normalized = {"authorities": [], "risks": [], "test_requirements": [], "dispositions": [], "previous_tr_ids": tr_state, "update_scope_tr_ids": ["TR-001"]}
        candidate = self._tr_artifact(
            normalized, [], [{"tr_id": "TR-001", "status": "deleted"}, {"tr_id": "TR-002", "status": "active"}], result_entities=[],
        )
        missing_previous = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": None,
            "partial_rerun": True,
        })
        self.assertFalse(missing_previous["valid"])
        self.assertIsNone(missing_previous["current_structure_state"])
        self.assertIn("invalid_previous_artifact", [issue["issue_type"] for issue in missing_previous["issues"]])
        self.assertIn(["test-requirement-design", "tr", "TR-002"], missing_previous["missing_entities"])

        scoped_only_state = [{"tr_id": "TR-001", "status": "active"}]
        scoped_only = {"authorities": [], "risks": [], "test_requirements": [], "dispositions": [], "previous_tr_ids": scoped_only_state, "update_scope_tr_ids": ["TR-001"]}
        current_tr = runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "Current"})
        scoped_candidate = self._tr_artifact(scoped_only, [current_tr], scoped_only_state, result_entities=[current_tr])
        no_carry_needed = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": scoped_only, "artifact_markdown": scoped_candidate,
            "previous_artifact_markdown": None,
            "partial_rerun": False,
        })
        self.assertTrue(no_carry_needed["valid"], no_carry_needed)

        deleted_scoped = {"authorities": [], "risks": [], "test_requirements": [], "dispositions": [], "previous_tr_ids": scoped_only_state, "update_scope_tr_ids": ["TR-001"]}
        deleted_candidate = self._tr_artifact(deleted_scoped, [], [{"tr_id": "TR-001", "status": "deleted"}], result_entities=[])
        deleted_without_previous = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": deleted_scoped, "artifact_markdown": deleted_candidate,
            "previous_artifact_markdown": None,
            "partial_rerun": False,
        })
        self.assertTrue(deleted_without_previous["valid"], deleted_without_previous)

        condition_normalized = {
            "tcn_id": "TCN-001", "test_conditions": [], "models": [], "ci_ids": [],
            "previous_tcn_ids": [{"tcn_id": "TCN-001", "status": "active"}, {"tcn_id": "TCN-002", "status": "active"}],
            "previous_model_keys": [{"model_key": "ep-001", "model_type": "ep", "status": "active"}, {"model_key": "ep-002", "model_type": "ep", "status": "active"}],
            "previous_ci_ids": [], "update_scope_tcn_ids": ["TCN-001"], "update_scope_model_keys": ["ep-001"],
        }
        condition_candidate = self._structure_artifact(
            "test-condition-design", condition_normalized, [],
            {"tcn_id_state": [{"tcn_id": "TCN-001", "status": "deleted"}, {"tcn_id": "TCN-002", "status": "active"}],
             "model_key_state": [{"model_key": "ep-001", "model_type": "ep", "status": "deleted"}, {"model_key": "ep-002", "model_type": "ep", "status": "active"}]},
            result_entities=[],
        )
        condition_missing = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-condition-design",
            "normalized_skill_input": condition_normalized, "artifact_markdown": condition_candidate,
            "previous_artifact_markdown": None,
            "partial_rerun": True,
        })
        self.assertFalse(condition_missing["valid"])
        self.assertIn("invalid_previous_artifact", [issue["issue_type"] for issue in condition_missing["issues"]])
        self.assertIn(["test-condition-design", "model", "ep-002"], condition_missing["missing_entities"])

        tc_state = [{"tc_id": "TC-001", "status": "active"}, {"tc_id": "TC-002", "status": "active"}]
        tc_normalized = {"test_cases": [], "previous_tc_ids": tc_state, "update_scope_tc_ids": ["TC-001"]}
        tc_candidate = self._structure_artifact(
            "test-case-design", tc_normalized, [],
            {"tc_id_state": [{"tc_id": "TC-001", "status": "deleted"}, {"tc_id": "TC-002", "status": "active"}]},
            result_entities=[],
        )
        tc_missing = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-case-design",
            "normalized_skill_input": tc_normalized, "artifact_markdown": tc_candidate,
            "previous_artifact_markdown": None,
            "partial_rerun": True,
        })
        self.assertFalse(tc_missing["valid"])
        self.assertIn("invalid_previous_artifact", [issue["issue_type"] for issue in tc_missing["issues"]])
        self.assertIn(["test-case-design", "tc", "TC-002"], tc_missing["missing_entities"])

    def test_skill_specific_previous_artifact_contracts(self) -> None:
        for skill in ("test-analysis", "coverage-analysis", "qa-workflow"):
            with self.subTest(skill=skill):
                result = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": skill,
                    "normalized_skill_input": {}, "artifact_markdown": "",
                    "previous_artifact_markdown": "previous artifact",
                    "partial_rerun": False,
                })
                self.assertFalse(result["valid"])
                self.assertIsNone(result["current_structure_state"])
                self.assertIn("invalid_previous_artifact", [row["issue_type"] for row in result["issues"]])

        previous_state = [{"tr_id": "TR-001", "status": "active"}]
        normalized = {"authorities": [], "risks": [], "test_requirements": [], "dispositions": [], "previous_tr_ids": previous_state, "update_scope_tr_ids": ["TR-001"]}
        old_tr = runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "Old"})
        previous = self._tr_artifact(normalized, [old_tr], previous_state)
        current_tr = runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "Updated"})
        current = self._tr_artifact(normalized, [current_tr], previous_state)
        no_carry_needed = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": current,
            "previous_artifact_markdown": previous,
            "partial_rerun": False,
        })
        self.assertFalse(no_carry_needed["valid"])
        self.assertIsNone(no_carry_needed["current_structure_state"])
        self.assertIn("full build requires previous_artifact_markdown=null", " ".join(row.get("message", "") for row in no_carry_needed["issues"]))

    def test_disposition_only_partial_reruns_require_previous_for_each_carry_skill(self) -> None:
        cases = (
            (
                "test-requirement-design",
                {"authorities": [], "risks": [], "test_requirements": [], "dispositions": [], "previous_tr_ids": [], "update_scope_tr_ids": []},
                "spec-analysis", "authority", "AUTH-OUT", {"authority_id": "AUTH-OUT"},
                {"tr_id_state": []},
            ),
            (
                "test-condition-design",
                {"tcn_id": "TCN-001", "test_requirements": [], "test_conditions": [], "models": [], "ci_ids": [], "test_data_requirements": [], "dispositions": [], "previous_tcn_ids": [], "previous_model_keys": [], "previous_ci_ids": [], "update_scope_tcn_ids": [], "update_scope_model_keys": []},
                "test-requirement-design", "tr", "TR-OUT", {"tr_id": "TR-OUT", "text": "Out of current scope"},
                {"tcn_id_state": [], "model_key_state": []},
            ),
            (
                "test-case-design",
                {"test_cases": [], "test_conditions": [], "coverage_items": [], "environment_requirements": [], "test_data_requirements": [], "previous_tc_ids": [], "update_scope_tc_ids": []},
                "test-analysis", "environment_requirement", "ENV-OUT", {"requirement_key": "ENV-OUT"},
                {"tc_id_state": []},
            ),
        )

        for skill, normalized, owner_skill, owner_type, owner_ref, owner_content, state in cases:
            with self.subTest(skill=skill):
                owner = runtime.make_machine_entity(owner_skill, owner_type, owner_ref, owner_content)
                dependency = runtime.machine_entity_dependency(owner)
                disposition = runtime.make_machine_entity(
                    skill, "disposition", f"{owner_type}:{owner_ref}",
                    {"upstream_entity": dependency, "handling": "対象外", "reason": "outside current scope", "authority_refs": [], "covered_by_entity": None},
                    upstream_entity_dependencies=[dependency],
                )
                owner_block = runtime.render_machine_entities(owner_skill, [owner])

                def artifact(rows: list[dict]) -> str:
                    if skill == "test-requirement-design":
                        own = self._tr_artifact(normalized, rows, state["tr_id_state"], result_entities=[])
                    else:
                        own = self._structure_artifact(skill, normalized, rows, state, result_entities=[])
                    return "\n".join((own, owner_block))

                previous = artifact([disposition])
                candidate = artifact([disposition])
                omitted_previous = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": skill,
                    "normalized_skill_input": normalized, "artifact_markdown": candidate,
                    "previous_artifact_markdown": None, "partial_rerun": True,
                })
                self.assertFalse(omitted_previous["valid"], omitted_previous)
                self.assertIn("invalid_previous_artifact", [row["issue_type"] for row in omitted_previous["issues"]])

                accepted = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": skill,
                    "normalized_skill_input": normalized, "artifact_markdown": candidate,
                    "previous_artifact_markdown": previous, "partial_rerun": True,
                })
                self.assertTrue(accepted["valid"], accepted)
                self.assertEqual(accepted["expected_entities"], [{"skill": skill, "entity_type": "disposition", "entity_ref": f"{owner_type}:{owner_ref}"}])

                omitted_disposition = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": skill,
                    "normalized_skill_input": normalized, "artifact_markdown": artifact([]),
                    "previous_artifact_markdown": previous, "partial_rerun": True,
                })
                self.assertFalse(omitted_disposition["valid"], omitted_disposition)
                self.assertIn((skill, "disposition", f"{owner_type}:{owner_ref}"), [tuple(row) for row in omitted_disposition["missing_entities"]])

                full_build = runtime.verify_runtime_evidence({
                    "operation": "verify_runtime_evidence", "skill": skill,
                    "normalized_skill_input": normalized, "artifact_markdown": artifact([]),
                    "previous_artifact_markdown": None, "partial_rerun": False,
                })
                self.assertTrue(full_build["valid"], full_build)

    def test_cli_verify_error_has_fixed_null_current_structure_state(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RUNTIME_PATH)], input=b'{"operation":"verify_runtime_evidence"}',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        response = json.loads(completed.stdout)
        self.assertFalse(response["valid"])
        self.assertIsNone(response["current_structure_state"])

    def test_producer_valid_disposition_scope_replaces_current_and_carries_only_out_of_scope(self) -> None:
        def disposition(producer_skill: str, owner: dict, row_reason: str) -> dict:
            dependency = runtime.machine_entity_dependency(owner)
            entity_type = owner["entity_type"]
            ref = owner["entity_ref"]
            return runtime.make_machine_entity(
                producer_skill, "disposition", f"{entity_type}:{ref}",
                {"upstream_entity": dependency, "handling": "対象外", "reason": row_reason, "authority_refs": [], "covered_by_entity": None},
                upstream_entity_dependencies=[dependency],
            )

        cases = []
        authority_current = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001"})
        authority_out = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-002", {"authority_id": "AUTH-002"})
        risk_current = runtime.make_machine_entity("test-analysis", "product_risk", "R-001", {"risk_id": "R-001"})
        risk_out = runtime.make_machine_entity("test-analysis", "product_risk", "R-002", {"risk_id": "R-002"})
        cases.append((
            "test-requirement-design",
            {"authorities": [{"authority_id": "AUTH-001"}], "risks": [{"risk_id": "R-001"}], "test_requirements": [], "test_cases": []},
            [authority_current, authority_out, risk_current, risk_out],
            [disposition("test-requirement-design", authority_current, "old authority"), disposition("test-requirement-design", risk_current, "old risk")],
            [disposition("test-requirement-design", authority_out, "out authority"), disposition("test-requirement-design", risk_out, "out risk")],
        ))

        tr_current = runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001"})
        tr_out = runtime.make_machine_entity("test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002"})
        cases.append((
            "test-condition-design",
            {"test_requirements": [{"tr_id": "TR-001"}], "test_conditions": [], "models": [], "test_data_requirements": []},
            [tr_current, tr_out],
            [disposition("test-condition-design", tr_current, "old TR")],
            [disposition("test-condition-design", tr_out, "out TR")],
        ))

        tcn_current = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        tcn_out = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        ci_current = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        ci_out = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
        env_current = runtime.make_machine_entity("test-analysis", "environment_requirement", "ENV-001", {"requirement_key": "ENV-001"})
        env_out = runtime.make_machine_entity("test-analysis", "environment_requirement", "ENV-002", {"requirement_key": "ENV-002"})
        tdr_current = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-001", {"data_ref": "data:REQ-001", "requirement_key": "REQ-001", "source_model_key": "ep-001"}, model_key="ep-001")
        tdr_out = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-002", {"data_ref": "data:REQ-002", "requirement_key": "REQ-002", "source_model_key": "ep-002"}, model_key="ep-002")
        case_owners = [tcn_current, tcn_out, ci_current, ci_out, env_current, env_out, tdr_current, tdr_out]
        cases.append((
            "test-case-design",
            {"test_conditions": [{"tcn_id": "TCN-001"}], "coverage_items": [{"ci_id": "TCN-001-CI01"}], "environment_requirements": [{"requirement_key": "ENV-001"}], "test_data_requirements": [{"data_ref": "data:REQ-001"}], "test_cases": []},
            case_owners,
            [disposition("test-case-design", owner, "old current") for owner in (tcn_current, ci_current, env_current, tdr_current)],
            [disposition("test-case-design", owner, "scope-out") for owner in (tcn_out, ci_out, env_out, tdr_out)],
        ))

        for skill, normalized, owners, current_dispositions, out_dispositions in cases:
            with self.subTest(skill=skill):
                previous = [*owners, *current_dispositions, *out_dispositions]
                carried = runtime._carry_forward_machine_entities(skill, normalized, previous, {})
                carried_ids = {row["entity_ref"] for row in carried if row["entity_type"] == "disposition"}
                expected_out_ids = {row["entity_ref"] for row in out_dispositions}
                self.assertEqual(carried_ids, expected_out_ids)

                changed_current = []
                for old in current_dispositions:
                    owner = next(row for row in owners if runtime.entity_identity(row["skill"], row["entity_type"], row["entity_ref"]) == runtime.entity_identity(old["content"]["upstream_entity"]["skill"], old["content"]["upstream_entity"]["entity_type"], old["content"]["upstream_entity"]["entity_ref"]))
                    changed_current.append(disposition(skill, owner, "current replacement"))
                fixed_state = {"runtime_results": [], "carry_forward_entities": out_dispositions, "previous_ci_id_state": []}
                current_expected = runtime._expected_entities(skill, normalized, [], current_result_entities=changed_current, previous_states={}, current_structure_state=fixed_state)
                current_expected_ids = {row["entity_ref"] for row in current_expected if row["entity_type"] == "disposition"}
                self.assertEqual(current_expected_ids, {row["entity_ref"] for row in current_dispositions} | expected_out_ids)
                deleted_expected = runtime._expected_entities(skill, normalized, [], current_result_entities=[], previous_states={}, current_structure_state=fixed_state)
                deleted_ids = {row["entity_ref"] for row in deleted_expected if row["entity_type"] == "disposition"}
                self.assertFalse({row["entity_ref"] for row in current_dispositions} & deleted_ids)


    def test_partial_rerun_carries_scope_out_tc_and_does_not_resurrect_deleted_tc(self) -> None:
        tc_one = runtime.make_machine_entity("test-case-design", "tc", "TC-001", {"tc_id": "TC-001"})
        tc_two = runtime.make_machine_entity("test-case-design", "tc", "TC-002", {"tc_id": "TC-002"})
        previous_state = [{"tc_id": "TC-001", "status": "active"}, {"tc_id": "TC-002", "status": "active"}]
        normalized = {"test_cases": [], "previous_tc_ids": previous_state, "update_scope_tc_ids": ["TC-001"]}
        previous = self._structure_artifact(
            "test-case-design", normalized, [tc_one, tc_two], {"tc_id_state": previous_state},
        )
        current_state = [{"tc_id": "TC-001", "status": "deleted"}, {"tc_id": "TC-002", "status": "active"}]
        candidate = self._structure_artifact(
            "test-case-design", normalized, [tc_two], {"tc_id_state": current_state}, result_entities=[],
        )
        request = {
            "operation": "verify_runtime_evidence", "skill": "test-case-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        }
        checked = runtime.verify_runtime_evidence(request)
        self.assertTrue(checked["valid"], checked)
        self.assertEqual(
            {(row["entity_type"], row["entity_ref"]) for row in checked["expected_entities"]},
            {("tc", "TC-002")},
        )
        deleted_left = runtime.verify_runtime_evidence({**request, "artifact_markdown": self._structure_artifact(
            "test-case-design", normalized, [tc_one, tc_two], {"tc_id_state": current_state}, result_entities=[],
        )})
        self.assertFalse(deleted_left["valid"])
        self.assertIn(("test-case-design", "tc", "TC-001"), [tuple(row) for row in deleted_left["extra_entities"]])

    def test_partial_rerun_carries_only_active_entities_outside_tr_scope(self) -> None:
        previous_state = [
            {"tr_id": "TR-001", "status": "active"},
            {"tr_id": "TR-002", "status": "active"},
            {"tr_id": "TR-003", "status": "deleted"},
        ]
        normalized = {
            "authorities": [], "risks": [], "test_requirements": [], "dispositions": [],
            "previous_tr_ids": previous_state, "update_scope_tr_ids": ["TR-001"],
        }
        prior_entities = [
            self._tr_entity("TR-001", {
                "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
                "generator_contract_version": "requirement-structure-v1",
                "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
                "generator_implementation_fingerprint": runtime.implementation_fingerprint(REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "requirement_structure.py"),
                "static_data_versions": {},
            }, "sha256:" + "1" * 64),
            self._tr_entity("TR-002", {
                "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
                "generator_contract_version": "requirement-structure-v1",
                "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
                "generator_implementation_fingerprint": runtime.implementation_fingerprint(REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "requirement_structure.py"),
                "static_data_versions": {},
            }, "sha256:" + "1" * 64),
        ]
        previous = self._tr_artifact(normalized, prior_entities, previous_state)
        current_state = [
            {"tr_id": "TR-001", "status": "deleted"},
            {"tr_id": "TR-002", "status": "active"},
            {"tr_id": "TR-003", "status": "deleted"},
        ]
        candidate = self._tr_artifact(normalized, [prior_entities[1]], current_state, result_entities=[])
        checked = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertTrue(checked["valid"], checked)
        cli = subprocess.run(
            [sys.executable, str(REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "runtime_contract.py")],
            input=json.dumps({
                "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
                "normalized_skill_input": normalized, "artifact_markdown": candidate,
                "previous_artifact_markdown": previous,
                "partial_rerun": True,
            }, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(cli.returncode, 0, cli.stderr.decode("utf-8", errors="replace"))
        self.assertFalse(cli.stderr)
        self.assertTrue(json.loads(cli.stdout)["valid"], cli.stdout.decode("utf-8", errors="replace"))
        self.assertEqual(
            {(row["entity_type"], row["entity_ref"]) for row in checked["expected_entities"]},
            {("tr", "TR-002")},
        )

        missing = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": self._tr_artifact(normalized, [], current_state, result_entities=[]),
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(missing["valid"])
        self.assertIn(("test-requirement-design", "tr", "TR-002"), [tuple(row) for row in missing["missing_entities"]])

        deleted_left = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": self._tr_artifact(normalized, prior_entities, current_state, result_entities=[]),
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(deleted_left["valid"])
        self.assertIn(("test-requirement-design", "tr", "TR-001"), [tuple(row) for row in deleted_left["extra_entities"]])

        unknown_entity = runtime.make_machine_entity(
            "test-requirement-design", "tr", "TR-404", {"tr_id": "TR-404", "text": "Unexpected"},
        )
        unknown = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized,
            "artifact_markdown": self._tr_artifact(normalized, [prior_entities[1], unknown_entity], current_state, result_entities=[]),
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(unknown["valid"])
        self.assertIn(["test-requirement-design", "tr", "TR-404"], unknown["extra_entities"])

        duplicate = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized,
            "artifact_markdown": self._tr_artifact(normalized, [prior_entities[1], prior_entities[1]], current_state, result_entities=[]),
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(duplicate["valid"])
        self.assertIn(["test-requirement-design", "tr", "TR-002"], duplicate["duplicate_entities"])

        fingerprint = prior_entities[1]["content_fingerprint"]
        tampered_previous = previous.rsplit(fingerprint, 1)[0] + "sha256:" + "f" * 64 + previous.rsplit(fingerprint, 1)[1]
        invalid_previous = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": tampered_previous,
            "partial_rerun": True,
        })
        self.assertFalse(invalid_previous["valid"])
        self.assertTrue(any(issue["issue_type"] == "invalid_previous_artifact" for issue in invalid_previous["issues"]))

    def test_partial_carry_forward_with_changed_producer_implementation_is_stale(self) -> None:
        state = [{"tr_id": "TR-001", "status": "active"}]
        normalized = {
            "authorities": [], "risks": [], "test_requirements": [], "dispositions": [],
            "previous_tr_ids": state, "update_scope_tr_ids": [],
        }
        old_generator_fp = "sha256:" + "2" * 64
        old_context = {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "requirement-structure-v1",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
            "generator_implementation_fingerprint": old_generator_fp,
            "static_data_versions": {},
        }
        previous_entity = self._tr_entity("TR-001", old_context, "sha256:" + "3" * 64)
        previous = self._tr_artifact(normalized, [previous_entity], state, generator_fp=old_generator_fp)
        current = self._tr_artifact(normalized, [previous_entity], state)
        checked = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": current,
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(checked["valid"])
        self.assertTrue(any(issue["issue_type"] == "stale_carry_forward_entity" for issue in checked["issues"]))

    def test_partial_carry_forward_with_changed_upstream_fingerprint_is_stale(self) -> None:
        state = [{"tr_id": "TR-001", "status": "active"}]
        normalized = {
            "authorities": [], "risks": [], "test_requirements": [], "dispositions": [],
            "previous_tr_ids": state, "update_scope_tr_ids": [],
        }
        old_authority = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001", "text": "old"})
        current_authority = runtime.make_machine_entity("spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001", "text": "current"})
        tr = runtime.make_machine_entity(
            "test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "Requirement TR-001"},
            upstream_entity_dependencies=[runtime.machine_entity_dependency(old_authority)],
            runtime_dependencies=[runtime.machine_entity_runtime_dependency("test-requirement-design", "artifact:requirement_structure:all")],
        )
        runtime_context = {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "requirement-structure-v1",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
            "generator_implementation_fingerprint": runtime.implementation_fingerprint(REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "requirement_structure.py"),
            "static_data_versions": {},
        }
        tr = runtime.bind_current_entity_runtime_dependencies({"entities": [tr]}, "sha256:" + "1" * 64, runtime_context=runtime_context)["entities"][0]
        previous = self._tr_artifact(normalized, [tr], state) + "\n" + runtime.render_machine_entities("spec-analysis", [old_authority])
        candidate = self._tr_artifact(normalized, [tr], state) + "\n" + runtime.render_machine_entities("spec-analysis", [current_authority])
        checked = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-requirement-design",
            "normalized_skill_input": normalized, "artifact_markdown": candidate,
            "previous_artifact_markdown": previous,
            "partial_rerun": True,
        })
        self.assertFalse(checked["valid"])
        stale = next(issue for issue in checked["issues"] if issue["issue_type"] == "stale_carry_forward_entity")
        self.assertIn("upstream_entity_fingerprint_mismatch", [row["reason_code"] for row in stale["stale_reasons"]])

    def test_evidence_operation_is_fixed(self) -> None:
        with self.assertRaises(runtime.InvalidInput):
            runtime.verify_runtime_evidence({
                "operation": "other",
                "skill": "test-condition-design",
                "normalized_skill_input": {},
                "artifact_markdown": "",
                "previous_artifact_markdown": None,
            })

    def test_evidence_operation_requires_partial_rerun_boolean(self) -> None:
        base = {
            "operation": "verify_runtime_evidence", "skill": "test-condition-design",
            "normalized_skill_input": {}, "artifact_markdown": "", "previous_artifact_markdown": None,
        }
        for request in (base, {**base, "partial_rerun": "false"}, {**base, "partial_rerun": 0}):
            with self.subTest(request=request):
                with self.assertRaises(runtime.InvalidInput):
                    runtime.verify_runtime_evidence(request)


class TargetDispositionClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content_a = "sha256:" + "1" * 64
        self.content_b = "sha256:" + "2" * 64
        self.content_c = "sha256:" + "3" * 64
        self.generation_a = "sha256:" + "4" * 64
        self.generation_b = "sha256:" + "5" * 64
        self.generation_c = "sha256:" + "6" * 64
        self.execution_a = "sha256:" + "7" * 64
        self.execution_b = "sha256:" + "8" * 64
        self.execution_c = "sha256:" + "9" * 64
        self.ref_a = runtime.target_ref("ep-001", "target-a")
        self.ref_b = runtime.target_ref("ep-001", "target-b")
        self.ref_c = runtime.target_ref("ep-001", "target-c")

    def _version(self, ref: str, content: str, generation: str, execution: str | None) -> dict:
        return {"target_ref": ref, "target_content_fingerprint": content, "generation_fingerprint": generation, "execution_fingerprint": execution}

    def _disposition(self, ref: str, content: str, generation: str, handling: str, covered: dict | None = None) -> dict:
        return {"target_ref": ref, "target_content_fingerprint": content, "generation_fingerprint": generation, "handling": handling, "covered_by_target_version": covered}

    def _mapping(self, ref: str, target_key: str, content: str, generation: str, execution: str, ci_id: str = "TCN-001-CI01") -> tuple[dict, dict]:
        mapping = {"target_ref": ref, "target_content_fingerprint": content, "generation_fingerprint": generation, "execution_fingerprint": execution, "model_key": "ep-001", "target_key": target_key, "ci_id": ci_id}
        ci = runtime.make_machine_entity("test-condition-design", "ci", ci_id, {
            "ci_id": ci_id, "model_key": "ep-001", "source_kind": "runtime_target", "status": "active",
            "covered_targets": [{"target_ref": ref, "target_content_fingerprint": content, "execution_fingerprint": execution}],
        }, model_key="ep-001")
        return mapping, ci

    def _evaluate(self, dispositions: list[dict], mappings: list[dict] | None = None, entities: list[dict] | None = None) -> list[dict]:
        return runtime.evaluate_target_disposition_closure([{"target_mappings": mappings or [], "target_dispositions": dispositions}], entities or [])

    def test_duplicate_chain_closes_only_at_current_mapping(self) -> None:
        direct_mapping, direct_ci = self._mapping(self.ref_b, "target-b", self.content_b, self.generation_b, self.execution_b)
        duplicate_a = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", self._version(self.ref_b, self.content_b, self.generation_b, self.execution_b))
        duplicate_b = self._disposition(self.ref_b, self.content_b, self.generation_b, "重複", self._version(self.ref_c, self.content_c, self.generation_c, self.execution_c))
        self.assertEqual(self._evaluate([duplicate_a], [direct_mapping], [direct_ci]), [])
        chain_mapping, chain_ci = self._mapping(self.ref_c, "target-c", self.content_c, self.generation_c, self.execution_c)
        self.assertEqual(self._evaluate([duplicate_a, duplicate_b], [chain_mapping], [chain_ci]), [])

    def test_duplicate_can_close_at_current_semantic_ci_version(self) -> None:
        semantic = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI02", {
            "ci_id": "TCN-001-CI02", "model_key": "ep-001", "source_kind": "semantic_item", "status": "active",
            "semantic_source_targets": [{"target_ref": self.ref_b, "target_content_fingerprint": self.content_b, "generation_fingerprint": self.generation_b}],
        }, model_key="ep-001")
        duplicate = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", self._version(self.ref_b, self.content_b, self.generation_b, None))
        self.assertEqual(self._evaluate([duplicate], entities=[semantic]), [])

    def test_noncoverage_dispositions_cannot_terminate_another_duplicate(self) -> None:
        for handling in ("対象外", "残存リスク"):
            with self.subTest(handling=handling):
                duplicate = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", self._version(self.ref_b, self.content_b, self.generation_b, self.execution_b))
                other = self._disposition(self.ref_b, self.content_b, self.generation_b, handling)
                issues = self._evaluate([duplicate, other])
                self.assertTrue(any(issue["issue_type"] == "target_disposition_non_coverage_terminal" for issue in issues))

    def test_duplicate_rejects_stale_versions_execution_mismatch_cycle_and_missing_target(self) -> None:
        mapping, ci = self._mapping(self.ref_b, "target-b", self.content_b, self.generation_b, self.execution_b)
        cases = [
            ("stale content", self._version(self.ref_b, self.content_c, self.generation_b, self.execution_b), [mapping], [ci], "target_disposition_stale_covered_version"),
            ("stale generation", self._version(self.ref_b, self.content_b, self.generation_c, self.execution_b), [mapping], [ci], "target_disposition_stale_covered_version"),
            ("execution mismatch", self._version(self.ref_b, self.content_b, self.generation_b, self.execution_c), [mapping], [ci], "target_disposition_stale_execution"),
            ("missing", self._version(self.ref_b, self.content_b, self.generation_b, self.execution_b), [], [], "target_disposition_missing"),
        ]
        for label, covered, mappings, entities, expected in cases:
            with self.subTest(label=label):
                duplicate = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", covered)
                issues = self._evaluate([duplicate], mappings, entities)
                self.assertTrue(any(issue["issue_type"] == expected for issue in issues))

        cycle_a = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", self._version(self.ref_b, self.content_b, self.generation_b, self.execution_b))
        cycle_b = self._disposition(self.ref_b, self.content_b, self.generation_b, "重複", self._version(self.ref_a, self.content_a, self.generation_a, self.execution_a))
        self.assertTrue(any(issue["issue_type"] == "target_disposition_cycle" for issue in self._evaluate([cycle_a, cycle_b])))

    def test_duplicate_self_reference_is_invalid(self) -> None:
        duplicate = self._disposition(self.ref_a, self.content_a, self.generation_a, "重複", self._version(self.ref_a, self.content_a, self.generation_a, self.execution_a))
        with self.assertRaises(runtime.InvalidInput):
            self._evaluate([duplicate])


class DependencyAndAdapterValidationTests(unittest.TestCase):
    def _runtime_row(self, unit: str, generation: str, dependencies: list[dict] | None = None) -> dict:
        return {
            "skill": "test-condition-design",
            "runtime_unit_key": unit,
            "model_key": None,
            "support_status": "supported",
            "result_status": "ready",
            "runtime_status": "ok",
            "runtime_required": True,
            "deterministic_generated": True,
            "generation_fingerprint": generation,
            "upstream_entity_fingerprints": [],
            "upstream_runtime_units": dependencies or [],
            "unsupported_items": [],
            "freshness_status": "current",
            "model_completion": [],
            "target_mappings": [],
            "target_dispositions": [],
        }

    def test_runtime_dependency_graph_rejects_duplicate_and_cycle(self) -> None:
        digest = "sha256:" + "1" * 64
        duplicate = [{
            "skill": "test-condition-design",
            "runtime_unit_key": "model:a",
            "upstream_runtime_units": [
                {"skill": "test-condition-design", "runtime_unit_key": "model:b", "generation_fingerprint": digest},
                {"skill": "test-condition-design", "runtime_unit_key": "model:b", "generation_fingerprint": digest},
            ],
        }, {"skill": "test-condition-design", "runtime_unit_key": "model:b", "upstream_runtime_units": []}]
        with self.assertRaises(runtime.InvalidInput):
            runtime.validate_runtime_dependency_graph(duplicate)

        cycle = [{
            "skill": "test-condition-design", "runtime_unit_key": "model:a",
            "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:b", "generation_fingerprint": digest}],
        }, {
            "skill": "test-condition-design", "runtime_unit_key": "model:b",
            "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:a", "generation_fingerprint": digest}],
        }]
        with self.assertRaises(runtime.InvalidInput):
            runtime.validate_runtime_dependency_graph(cycle)

    def test_common_runtime_validation_rejects_ready_with_blocking_issue(self) -> None:
        metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
            "generator_contract_version": "test-generator-v1", "runtime_unit_key": "artifact:test_generator:all", "model_key": None,
            "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None, "scope_key": "all",
            "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {},
            "authority_refs": [], "reference_refs": [],
        }
        digest = "sha256:" + "0" * 64
        result = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
            "generator_contract_version": "test-generator-v1", "generator": "test_generator", "runtime_unit_key": "artifact:test_generator:all", "model_key": None,
            "input_fingerprint": digest, "model_fingerprint": digest, "generation_fingerprint": digest,
            "runtime_implementation_fingerprint": digest, "generator_implementation_fingerprint": digest,
            "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "support_status": "supported", "static_data_versions": {},
            "runtime_status": "ok", "result_status": "ready", "runtime_required": True, "deterministic_generated": True,
            "fallback_reason": None, "payload": {}, "issues": [{"issue_type": "blocking", "blocking": True}],
        }
        issues = runtime._validate_runtime_pair(
            "test-condition-design", "test-condition-design::artifact:test_generator:all",
            {"metadata": metadata, "input": {}}, result,
        )
        self.assertTrue(any(issue["issue_type"] == "ready_runtime_has_blocking_issue" for issue in issues))

    def test_unsupported_fallback_uses_model_union_from_all_scope_inputs(self) -> None:
        generation = "sha256:" + "a" * 64
        ci = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {
            "ci_id": "TCN-002-CI01", "model_key": "ep-002", "source_kind": "runtime_target", "status": "active",
        }, model_key="ep-002")
        unsupported = [{
            "item_key": "unsupported:item-1", "item_type": "constraint", "source_key": "rule-1", "reason_code": "outside_supported_subset",
            "affected_technique_slug": "ep", "authority_refs": [],
        }]
        runtime_row = {
            "skill": "test-condition-design", "runtime_unit_key": "model:adapter-001", "model_key": "adapter-001",
            "generation_fingerprint": generation, "support_status": "partial", "unsupported_items": unsupported,
        }
        closure = {
            "skill": "test-condition-design", "runtime_unit_key": "model:adapter-001", "generation_fingerprint": generation,
            "item_key": "unsupported:item-1", "reason_code": "outside_supported_subset", "handling": "llm_fallback", "reason": "direct EP child covers the item",
            "authority_refs": [], "covered_by_entity": {"skill": ci["skill"], "entity_type": ci["entity_type"], "entity_ref": ci["entity_ref"], "content_fingerprint": ci["content_fingerprint"]},
        }
        normalized = [
            {"models": [{"model_key": "adapter-001", "model_type": "cause-effect", "technique_slug": None}]},
            {"models": [{"model_key": "ep-002", "model_type": "ep", "technique_slug": "ep", "derived_from_model_key": "adapter-001"}]},
        ]
        rows, issues = runtime.validate_unsupported_item_closures([closure], [runtime_row], [ci], normalized=normalized)
        self.assertEqual(rows, [closure])
        self.assertEqual(issues, [])

    def test_stale_propagates_only_to_dependent_runtime_units(self) -> None:
        old = "sha256:" + "1" * 64
        new = "sha256:" + "2" * 64
        dependency = {"skill": "test-condition-design", "runtime_unit_key": "artifact:root:all", "generation_fingerprint": old}
        old_rows = [
            self._runtime_row("artifact:root:all", old),
            self._runtime_row("model:dependent", old, [dependency]),
            self._runtime_row("model:independent", old),
        ]
        current_rows = [
            self._runtime_row("artifact:root:all", new),
            self._runtime_row("model:dependent", old, [dependency]),
            self._runtime_row("model:independent", old),
        ]
        fresh, _issues = runtime.evaluate_runtime_unit_freshness(old_rows, current_rows, [])
        status = {row["runtime_unit_key"]: row["freshness_status"] for row in fresh}
        self.assertEqual(status, {"artifact:root:all": "stale", "model:dependent": "stale", "model:independent": "current"})

    def test_adapter_child_requires_unique_input_and_parent_generation_dependency(self) -> None:
        normalized = {"models": [
            {"model_key": "cause-effect-001", "model_type": "cause-effect"},
            {"model_key": "decision-001", "model_type": "decision", "derived_from_model_key": "cause-effect-001"},
        ]}
        generation = "sha256:" + "3" * 64
        child = {"child_model_key": "decision-001", "parent_model_key": "cause-effect-001", "model_type": "decision"}
        parent_identity = "test-condition-design::model:cause-effect-001"
        child_identity = "test-condition-design::model:decision-001"
        parent = {"result_status": "ready", "generation_fingerprint": generation, "payload": {"derived_child_inputs": [child]}}
        input_blocks = {child_identity: {"metadata": {"upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:cause-effect-001", "generation_fingerprint": generation}]}}}
        expected = [{"skill": "test-condition-design", "runtime_unit_key": "model:cause-effect-001", "model_key": "cause-effect-001"}]
        issues: list[dict] = []
        actual_expected = runtime._verified_child_units("test-condition-design", normalized, {parent_identity: parent}, expected, input_blocks=input_blocks, issues=issues)
        self.assertIn(("test-condition-design", "model:decision-001"), {(row["skill"], row["runtime_unit_key"]) for row in actual_expected})
        self.assertEqual(issues, [])

        duplicate_issues: list[dict] = []
        runtime._verified_child_units(
            "test-condition-design", normalized,
            {parent_identity: {**parent, "payload": {"derived_child_inputs": [child, child]}}},
            [{"skill": "test-condition-design", "runtime_unit_key": "model:cause-effect-001", "model_key": "cause-effect-001"}],
            input_blocks=input_blocks,
            issues=duplicate_issues,
        )
        self.assertTrue(any(issue["issue_type"] == "duplicate_derived_child_input" for issue in duplicate_issues))

        missing_dependency_issues: list[dict] = []
        runtime._verified_child_units(
            "test-condition-design", normalized, {parent_identity: parent},
            [{"skill": "test-condition-design", "runtime_unit_key": "model:cause-effect-001", "model_key": "cause-effect-001"}],
            input_blocks={child_identity: {"metadata": {"upstream_runtime_units": []}}},
            issues=missing_dependency_issues,
        )
        self.assertTrue(any(issue["issue_type"] == "missing_derived_child_runtime_dependency" for issue in missing_dependency_issues))

    def test_whole_model_unsupported_requires_whole_closure(self) -> None:
        generation = "sha256:" + "4" * 64
        item = runtime.make_unsupported_item(
            generator="flow_paths",
            item_type="concurrent-flow-target",
            source_key="flow-target",
            reason_code="concurrent_flow_requires_semantic_execution",
        )
        row = self._runtime_row("model:flow-001", generation)
        row.update({"model_key": "flow-001", "support_status": "unsupported", "unsupported_items": [item]})
        closure = {
            "skill": "test-condition-design", "runtime_unit_key": "model:flow-001", "generation_fingerprint": generation,
            "item_key": None, "reason_code": None, "handling": "対象外", "reason": "fork-joinをsemantic executionへ移譲",
            "authority_refs": [], "covered_by_entity": None,
        }
        _rows, issues = runtime.validate_unsupported_item_closures([closure], [row], [])
        self.assertEqual(issues, [])
        item_closure = {**closure, "item_key": item["item_key"], "reason_code": item["reason_code"]}
        _rows, item_issues = runtime.validate_unsupported_item_closures([item_closure], [row], [])
        self.assertTrue(any(issue["issue_type"] == "whole_model_unsupported_closure_missing" for issue in item_issues))


if __name__ == "__main__":
    unittest.main()
