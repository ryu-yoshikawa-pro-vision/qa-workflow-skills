from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
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
            }
        )
        self.assertFalse(invalid["valid"])
        self.assertIn("test-condition-design::model:ep-001", invalid["incomplete_pairs"])

    def test_evidence_operation_is_fixed(self) -> None:
        with self.assertRaises(runtime.InvalidInput):
            runtime.verify_runtime_evidence({
                "operation": "other",
                "skill": "test-condition-design",
                "normalized_skill_input": {},
                "artifact_markdown": "",
                "previous_artifact_markdown": None,
            })


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
