from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "test-requirement-design"
    / "scripts"
    / "requirement_structure.py"
)
RUNTIME_PATH = (
    REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "runtime_contract.py"
)
SPEC = importlib.util.spec_from_file_location("tr_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata(
    input_mode: str = "direct", upstream_entities: list[dict] | None = None
) -> dict:
    return {
        "envelope_version": "1",
        "skill": "test-requirement-design",
        "runtime_contract_version": "runtime-v2",
        "generator_contract_version": "requirement-structure-v2",
        "runtime_unit_key": "artifact:requirement_structure:all",
        "model_key": None,
        "model_type": None,
        "technique_slug": None,
        "selection_source": None,
        "selection_key": None,
        "scope_key": "all",
        "input_mode": input_mode,
        "upstream_entities": upstream_entities or [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


def run(
    value: dict, input_mode: str = "direct", upstream_entities: list[dict] | None = None
) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(
            {"metadata": metadata(input_mode, upstream_entities), "input": value},
            ensure_ascii=False,
        ).encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def draft(
    key: str,
    action: str,
    reuse_id: str | None,
    *,
    priority: str = "高",
    override: str | None = None,
    authority_refs: list[str] | None = None,
    risk_refs: list[str] | None = None,
) -> dict:
    return {
        "draft_key": key,
        "identity_action": action,
        "reuse_id": reuse_id,
        "text": f"Requirement {key}",
        "acceptance_refs": [],
        "scope_refs": [],
        "authority_refs": authority_refs or [],
        "risk_refs": risk_refs or [],
        "priority": priority,
        "priority_override_reason": override,
        "test_level": "system",
        "observation_method": "assertion",
    }


def base_input() -> dict:
    return {
        "authorities": [{"authority_id": "AUTH-001"}],
        "risks": [{"risk_id": "R-001", "mapped_priority": "高"}],
        "acceptance_criteria": [],
        "scope_ids": [],
        "test_requirements": [
            draft("keep", "reuse", "TR-001", priority="中", override="legacy scope"),
            draft("new", "new", None),
        ],
        "dispositions": [],
        "previous_tr_ids": [
            {"tr_id": "TR-001", "status": "active", "scope_refs": []},
            {"tr_id": "TR-002", "status": "deleted", "scope_refs": []},
        ],
        "update_scope_tr_ids": ["TR-001"],
        "inactive_tr_ids": [],
        "inactive_tr_history": [],
        "zero_scope_terminal": False,
    }


class RequirementStructureRuntimeTests(unittest.TestCase):
    def test_acceptance_closure_is_independent_from_authority_closure(self) -> None:
        value = {
            "authorities": [{"authority_id": "AUTH-001"}],
            "risks": [],
            "acceptance_criteria": [
                {"ac_id": "AC-001", "authority_refs": ["AUTH-001"]}
            ],
            "scope_ids": [],
            "test_requirements": [
                draft("ac-linked", "new", None, authority_refs=[], risk_refs=[])
                | {"acceptance_refs": ["AC-001"]}
            ],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
        }
        unresolved = run(value)
        self.assertEqual(unresolved["runtime_status"], "ok")
        self.assertTrue(
            any(
                issue["issue_type"] == "unclosed_reference"
                and issue["entity_ref"] == "AUTH-001"
                for issue in unresolved["payload"]["violations"]
            )
        )
        value["test_requirements"][0]["authority_refs"] = ["AUTH-001"]
        ready = run(value)
        self.assertEqual(ready["result_status"], "ready")
        entity = ready["payload"]["entities"][0]
        self.assertEqual(entity["content"]["acceptance_refs"], ["AC-001"])
        self.assertEqual(entity["content"]["scope_refs"], [])

    def test_artifact_ac_dependency_and_required_scope_are_exact(self) -> None:
        authority = runtime.make_machine_entity(
            "spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001"}
        )
        ac = runtime.make_machine_entity(
            "spec-analysis",
            "acceptance_criterion",
            "AC-001",
            {
                "ac_id": "AC-001",
                "authority_refs": ["AUTH-001"],
                "scope": {"scope_id": "SCOPE-001"},
            },
            upstream_entity_dependencies=[
                {
                    "skill": "spec-analysis",
                    "entity_type": "authority",
                    "entity_ref": "AUTH-001",
                    "content_fingerprint": authority["content_fingerprint"],
                }
            ],
        )
        value = {
            "authorities": [{"authority_id": "AUTH-001"}],
            "risks": [],
            "acceptance_criteria": [
                {"ac_id": "AC-001", "authority_refs": ["AUTH-001"]}
            ],
            "scope_ids": ["SCOPE-001"],
            "test_requirements": [
                draft(
                    "linked",
                    "new",
                    None,
                    authority_refs=["AUTH-001"],
                )
                | {"acceptance_refs": ["AC-001"], "scope_refs": ["SCOPE-001"]}
            ],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
        }
        upstream = [authority, ac]
        rows = [
            {
                "skill": entity["skill"],
                "entity_type": entity["entity_type"],
                "entity_ref": entity["entity_ref"],
                "content": entity["content"],
            }
            for entity in upstream
        ]
        result = run(value, input_mode="artifact", upstream_entities=rows)
        self.assertEqual(result["runtime_status"], "ok", result)
        tr_entity = next(
            row for row in result["payload"]["entities"] if row["entity_type"] == "tr"
        )
        self.assertEqual(
            {
                (row["skill"], row["entity_type"], row["entity_ref"])
                for row in tr_entity["upstream_entity_dependencies"]
            },
            {
                ("spec-analysis", "acceptance_criterion", "AC-001"),
                ("spec-analysis", "authority", "AUTH-001"),
            },
        )
        value["test_requirements"][0]["scope_refs"] = []
        self.assertEqual(
            run(value, input_mode="artifact", upstream_entities=rows)["runtime_status"],
            "invalid_input",
        )

    def test_inactive_history_reuse_and_zero_scope_terminal(self) -> None:
        first_input = {
            "authorities": [],
            "risks": [],
            "acceptance_criteria": [],
            "scope_ids": ["SCOPE-001"],
            "test_requirements": [
                draft("one", "new", None) | {"scope_refs": ["SCOPE-001"]}
            ],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
        }
        first = run(first_input)
        self.assertEqual(first["runtime_status"], "ok")
        tr_entity = next(
            row for row in first["payload"]["entities"] if row["entity_type"] == "tr"
        )

        blocked_input = {
            "authorities": [],
            "risks": [],
            "acceptance_criteria": [],
            "scope_ids": [],
            "test_requirements": [],
            "dispositions": [],
            "previous_tr_ids": first["payload"]["tr_id_state"],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": ["TR-001"],
            "inactive_tr_history": [tr_entity],
            "zero_scope_terminal": False,
        }
        blocked = run(blocked_input)
        self.assertEqual(blocked["runtime_status"], "ok", blocked)
        self.assertEqual(blocked["payload"]["tr_id_state"][0]["status"], "inactive")
        self.assertEqual(blocked["payload"]["entities"], [])

        active_input = {
            **first_input,
            "scope_ids": ["SCOPE-002"],
            "test_requirements": [
                draft("one-again", "reuse", "TR-001") | {"scope_refs": ["SCOPE-002"]}
            ],
            "previous_tr_ids": [
                {"tr_id": "TR-001", "status": "inactive", "scope_refs": ["SCOPE-002"]}
            ],
            "update_scope_tr_ids": ["TR-001"],
            "inactive_tr_ids": [],
            "inactive_tr_history": blocked["payload"]["inactive_tr_history"],
        }
        active = run(active_input)
        self.assertEqual(active["runtime_status"], "ok", active)
        self.assertEqual(
            active["payload"]["tr_id_state"][0]["scope_refs"], ["SCOPE-002"]
        )
        self.assertEqual(active["payload"]["inactive_tr_history"], [])

        terminal_input = {
            "authorities": [],
            "risks": [],
            "acceptance_criteria": [],
            "scope_ids": [],
            "test_requirements": [],
            "dispositions": [],
            "previous_tr_ids": active["payload"]["tr_id_state"],
            "update_scope_tr_ids": ["TR-001"],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": True,
        }
        terminal = run(terminal_input)
        self.assertEqual(terminal["runtime_status"], "ok", terminal)
        self.assertEqual(terminal["payload"]["tr_id_state"][0]["status"], "deleted")
        self.assertEqual(
            terminal["payload"]["tr_id_state"][0]["scope_refs"], ["SCOPE-002"]
        )
        self.assertEqual(terminal["payload"]["entities"], [])

    def test_reuse_new_and_scope_lifecycle_preserve_full_snapshot(self) -> None:
        value = base_input()
        value["test_requirements"][0]["authority_refs"] = ["AUTH-001"]
        value["test_requirements"][0]["risk_refs"] = ["R-001"]
        value["test_requirements"][1]["authority_refs"] = ["AUTH-001"]
        value["test_requirements"][1]["risk_refs"] = ["R-001"]
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(
            result["payload"]["tr_id_map"],
            [
                {"draft_key": "keep", "tr_id": "TR-001", "identity_action": "reuse"},
                {"draft_key": "new", "tr_id": "TR-003", "identity_action": "new"},
            ],
        )
        self.assertEqual(
            result["payload"]["tr_id_state"],
            [
                {"tr_id": "TR-001", "status": "active", "scope_refs": []},
                {"tr_id": "TR-002", "status": "deleted", "scope_refs": []},
                {"tr_id": "TR-003", "status": "active", "scope_refs": []},
            ],
        )
        tr = next(
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "tr" and row["entity_ref"] == "TR-001"
        )
        self.assertEqual(tr["content"]["text"], "Requirement keep")
        self.assertEqual(tr["content"]["priority"], "中")

    def test_linked_and_disposed_is_unresolved_and_reason_is_preserved(self) -> None:
        value = base_input()
        authority = runtime.make_machine_entity(
            "spec-analysis", "authority", "AUTH-001", {"authority_id": "AUTH-001"}
        )
        for row in value["test_requirements"]:
            row["authority_refs"] = ["AUTH-001"]
            row["risk_refs"] = ["R-001"]
        value["dispositions"] = [
            {
                "upstream_entity": {
                    "skill": "spec-analysis",
                    "entity_type": "authority",
                    "entity_ref": "AUTH-001",
                    "content_fingerprint": authority["content_fingerprint"],
                },
                "handling": "対象外",
                "reason": "not in scope",
                "authority_refs": [],
                "covered_by_entity": None,
            }
        ]
        result = run(
            value,
            upstream_entities=[
                {
                    "skill": authority["skill"],
                    "entity_type": authority["entity_type"],
                    "entity_ref": authority["entity_ref"],
                    "content": authority["content"],
                }
            ],
        )
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(
            any(
                issue["issue_type"] == "linked_and_disposed"
                for issue in result["issues"]
            )
        )
        disposition = next(
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "disposition"
        )
        self.assertEqual(
            disposition["upstream_entity_dependencies"],
            [
                {
                    "skill": "spec-analysis",
                    "entity_type": "authority",
                    "entity_ref": "AUTH-001",
                    "content_fingerprint": authority["content_fingerprint"],
                }
            ],
        )

    def test_legacy_seed_uses_active_previous_state_and_forbids_partial_scope(
        self,
    ) -> None:
        value = {
            "authorities": [],
            "risks": [],
            "acceptance_criteria": [],
            "scope_ids": [],
            "test_requirements": [draft("legacy", "reuse", "TR-004")],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
            "legacy_tr_ids": ["TR-004"],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["tr_id_map"][0]["tr_id"], "TR-004")
        bad = dict(value, update_scope_tr_ids=["TR-004"])
        self.assertEqual(run(bad)["runtime_status"], "invalid_input")

    def test_low_priority_without_override_reason_is_reported(self) -> None:
        value = base_input()
        value["test_requirements"][0]["priority_override_reason"] = ""
        value["test_requirements"][0]["risk_refs"] = ["R-001"]
        value["test_requirements"][1]["risk_refs"] = ["R-001"]
        result = run(value)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def test_tr_dependencies_use_full_typed_identity_and_current_fingerprints(
        self,
    ) -> None:
        value = {
            "authorities": [{"authority_id": "SHARED"}],
            "risks": [{"risk_id": "SHARED", "mapped_priority": "高"}],
            "acceptance_criteria": [],
            "scope_ids": [],
            "test_requirements": [
                draft(
                    "one", "new", None, authority_refs=["SHARED"], risk_refs=["SHARED"]
                )
            ],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
        }
        authority = runtime.make_machine_entity(
            "spec-analysis", "authority", "SHARED", {"authority_id": "SHARED"}
        )
        risk = runtime.make_machine_entity(
            "test-analysis",
            "product_risk",
            "SHARED",
            {"risk_id": "SHARED", "mapped_priority": "高"},
        )
        upstream = [
            {
                "skill": row["skill"],
                "entity_type": row["entity_type"],
                "entity_ref": row["entity_ref"],
                "content": row["content"],
            }
            for row in (authority, risk)
        ]
        result = run(value, "artifact", upstream)
        self.assertEqual(result["runtime_status"], "ok")
        tr = next(
            row for row in result["payload"]["entities"] if row["entity_type"] == "tr"
        )
        deps = {
            (row["skill"], row["entity_type"], row["entity_ref"]): row[
                "content_fingerprint"
            ]
            for row in tr["upstream_entity_dependencies"]
        }
        self.assertEqual(
            deps,
            {
                ("spec-analysis", "authority", "SHARED"): authority[
                    "content_fingerprint"
                ],
                ("test-analysis", "product_risk", "SHARED"): risk[
                    "content_fingerprint"
                ],
            },
        )

    def test_artifact_missing_known_reference_entity_is_invalid_but_unknown_reference_uses_existing_issue(
        self,
    ) -> None:
        value = {
            "authorities": [{"authority_id": "AUTH-001"}],
            "risks": [],
            "acceptance_criteria": [],
            "scope_ids": [],
            "test_requirements": [
                draft("one", "new", None, authority_refs=["AUTH-001"])
            ],
            "dispositions": [],
            "previous_tr_ids": [],
            "update_scope_tr_ids": [],
            "inactive_tr_ids": [],
            "inactive_tr_history": [],
            "zero_scope_terminal": False,
        }
        missing = run(value, "artifact", [])
        self.assertEqual(missing["runtime_status"], "invalid_input")

        value["authorities"] = []
        value["test_requirements"][0]["authority_refs"] = ["AUTH-404"]
        unknown = run(value, "artifact", [])
        self.assertEqual(unknown["runtime_status"], "ok")
        self.assertEqual(unknown["result_status"], "unresolved")
        self.assertEqual(
            [issue["issue_type"] for issue in unknown["issues"]], ["unknown_reference"]
        )


if __name__ == "__main__":
    unittest.main()
