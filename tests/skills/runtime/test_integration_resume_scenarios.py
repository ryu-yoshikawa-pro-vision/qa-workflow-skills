"""統合シナリオ: owner verifier で完了した scope を含む保存済み v2 workflow の保存・再開。

各テストの先頭コメントに期待結果を先に書く。fixture は本ファイル内で組み立て、既存テストの
helper は import しない（owner の本番 CLI と qa-workflow の本番 CLI / 検査関数だけを呼ぶ）。

- workflow_runtime は CLI（subprocess）として呼び、保存再開は downstream_state.evaluate と
  _validate_frozen_pair（既存テストと同じ呼び方）で確認する。
- owner の保存本文・読戻し・承認証拠・要求集合は呼出し側の fixture であり、実 provider の
  読戻しではない。fixture の成功を実 provider の読戻し成功として扱わない。
- 承認の真正性は owner validator が確立しない（approval_authenticity は未確立の値）。本ファイルは
  承認の真正性を検証対象にしない。
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
QA_SCRIPTS = SKILLS / "qa-workflow" / "scripts"
sys.path.insert(0, str(QA_SCRIPTS))

import downstream_state as ds  # noqa: E402
import owner_verifiers  # noqa: E402
from runtime_contract import InvalidInput  # noqa: E402

WORKFLOW_SCRIPT = QA_SCRIPTS / "workflow_runtime.py"
ITEM_SCRIPT = SKILLS / "test-item-analysis" / "scripts" / "item_candidates.py"
CONDITION_SCRIPT = (
    SKILLS / "test-condition-analysis" / "scripts" / "condition_candidates.py"
)
REPORTING_SCRIPT = SKILLS / "test-reporting" / "scripts" / "reporting_runtime.py"
CHILD_ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}

# fixture 専用に別名で読み込む（共有モジュールの属性を書き換えない）。
_SPEC = importlib.util.spec_from_file_location(
    "integration_scenarios_fixture_runtime", QA_SCRIPTS / "runtime_contract.py"
)
assert _SPEC is not None and _SPEC.loader is not None
fixture_rc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fixture_rc
_SPEC.loader.exec_module(fixture_rc)
_ORIGINAL_MAKE_ENTITY = fixture_rc.make_machine_entity


def _make_v2_entity(skill, entity_type, entity_ref, content, **kwargs):
    if entity_type in {"tr", "tcn", "model", "ci", "tc"}:
        content = {**content}
        content.setdefault("scope_refs", [])
    return _ORIGINAL_MAKE_ENTITY(skill, entity_type, entity_ref, content, **kwargs)


fixture_rc.make_machine_entity = _make_v2_entity

REF = "00000000-0000-4000-8000-0000000000c1"
OTHER_REF = "00000000-0000-4000-8000-0000000000ff"
ROOT_ID = "qa-workflow::artifact:workflow_runtime:all"
TCD = "test-condition-design"
RA = "test-requirements-analysis"
TA = "test-architecture-design"
TM = "test-management"
TIA = "test-item-analysis"
TCA = "test-condition-analysis"
E2E = "e2e-test-selection"
TR = "test-reporting"
PACKET_OWNERS = (RA, TA, TM)
ALL_OWNERS = (TIA, TCA, E2E, TR, RA, TA, TM)
REF_KEYS = ("owner", "scope", "artifact_ref", "revision", "content_hash")
PACKET_EXAMPLES = {
    RA: ("packet-example.json", "sources"),
    TA: ("packet-example.json", "sources"),
    TM: ("plan-packet.example.json", "planned_sources"),
}
METADATA = {
    "envelope_version": "1",
    "skill": "qa-workflow",
    "runtime_contract_version": "runtime-v2",
    "generator_contract_version": "workflow-runtime-v2",
    "runtime_unit_key": "artifact:workflow_runtime:all",
    "model_key": None,
    "model_type": None,
    "technique_slug": None,
    "selection_source": None,
    "selection_key": None,
    "scope_key": "all",
    "input_mode": "artifact",
    "upstream_entities": [],
    "upstream_runtime_units": [],
    "static_data_versions": {},
    "authority_refs": [],
    "reference_refs": [],
}


# --- 共通 helper ------------------------------------------------------------


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_example(skill: str, name: str) -> dict:
    return json.loads((SKILLS / skill / "assets" / name).read_text(encoding="utf-8"))


def run_json(script: Path, request: Any, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(script), *args],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=CHILD_ENV,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.decode("utf-8", "replace"))
    return json.loads(completed.stdout)


class Store:
    """呼出し側の保存・読戻しを模した fixture（実 provider ではない）。"""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def save(
        self, ref: str, text: str, *, owner: str, scope: str, revision: str
    ) -> None:
        self.rows[ref] = {
            "text": text,
            "owner": owner,
            "scope": scope,
            "artifact_ref": ref,
            "revision": revision,
        }

    def readback(self, ref: str) -> dict:
        row = self.rows[ref]
        return {
            "owner": row["owner"],
            "scope": row["scope"],
            "artifact_ref": row["artifact_ref"],
            "revision": row["revision"],
            "content_hash": sha(row["text"]),
        }


def owner_scope(skill: str, target: str, evidence: dict) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": {"owner_verification": evidence},
        "current_structure_state": None,
    }


def required(skill: str, target: str | None = None) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "requirement": "required",
    }


# --- owner の保存成果物と証拠 ---------------------------------------------


def packet_owner(store: Store, skill: str) -> tuple[str, dict]:
    """RA / TA / TM: skills/<owner>/assets の example を保存本文として用いる。"""
    name, sources_key = PACKET_EXAMPLES[skill]
    packet = load_example(skill, name)
    text = canonical(packet)
    ref = packet["artifact_ref"]
    # TA の packet は revision を持たないため、保存時の revision ラベルを固定値にする。
    revision = "ta-r1" if skill == TA else str(packet["revision"])
    store.save(ref, text, owner=skill, scope=packet["scope"], revision=revision)
    evidence: dict[str, Any] = {
        "stored_content": text,
        "readback": store.readback(ref),
        "expected_revision": revision,
        "current_source_refs": [
            {key: row[key] for key in REF_KEYS} for row in packet[sources_key]
        ],
    }
    if skill == TA:
        evidence["approval_evidence"] = [
            {
                "approval_id": approval_id,
                "artifact_ref": packet["artifact_ref"],
                "scope": packet["scope"],
                "content_fingerprint": packet["content_fingerprint"],
                "revision": "ta-r1",
                "assignment_ids": [assignment_id],
                "approver": "QA責任者",
                "approver_role": "QA責任者",
                "evidence_ref": f"evidence:{approval_id}",
                "state": "承認済み",
            }
            for approval_id, assignment_id in (
                ("APR-001", "ARCH-002"),
                ("APR-002", "ARCH-003"),
            )
        ]
    return ref, evidence


def feature_analysis(snapshot: dict, status: str) -> dict:
    sources = sorted(snapshot["sources"], key=lambda row: row["id"])
    features = sorted(snapshot["features"], key=lambda row: row["id"])
    source_ids = {row["id"]: row for row in snapshot["sources"]}
    reasons: list[str] = []
    if not snapshot["expected_source_ids"]:
        reasons.append("source_boundary_unconfirmed")
    for source_id in snapshot["expected_source_ids"]:
        source = source_ids.get(source_id)
        if source is None:
            reasons.append(f"source_missing:{source_id}")
        elif source["status"] != "complete":
            reasons.append(f"source_incomplete:{source_id}")
    if snapshot["unknown_areas"]:
        reasons.append("unknown_areas_present")
    if not snapshot["changes"]:
        reasons.append("change_denominator_zero")
    if not snapshot["candidates"]:
        reasons.append("candidate_denominator_zero")
    reasons = sorted(set(reasons))
    if status == "complete" and reasons:
        raise AssertionError("fixture cannot report a complete analysis")
    handoff = {
        "snapshot_sha256": sha(canonical(snapshot)),
        "source_inventory": [
            {
                "id": row["id"],
                "ref": row["ref"],
                "status": row["status"],
                "revision": row.get("revision"),
                "unretrieved": row["unretrieved"],
            }
            for row in sources
        ],
        "artifact_ref": snapshot["artifact_ref"],
        "artifact_revision": snapshot["artifact_revision"],
        "source_revision": snapshot["source_revision"],
        "feature_ids": [row["id"] for row in features],
        "feature_refs": [
            {
                "id": row["id"],
                "kind": row["kind"],
                "status": row["status"],
                "parent_id": row["parent_id"],
                "source_ids": row["source_ids"],
                "implementation_refs": row["implementation_refs"],
                "spec_refs": row["spec_refs"],
                "qa_refs": row["qa_refs"],
            }
            for row in features
        ],
        "impacted_feature_ids": sorted(
            {
                feature_id
                for row in snapshot["changes"]
                if row["classification"] == "impact"
                for feature_id in row["feature_ids"]
            }
        ),
        "approval_required_change_ids": sorted(
            row["id"]
            for row in snapshot["changes"]
            if row["classification"] in {"no_impact", "out_of_scope"}
        ),
        "unknown_areas": snapshot["unknown_areas"],
        "unclassified_change_ids": sorted(
            row["id"]
            for row in snapshot["changes"]
            if row["classification"] not in {"impact", "no_impact", "out_of_scope"}
        ),
        "expected_source_ids": snapshot["expected_source_ids"],
    }
    metrics = {
        "change_classification": {
            "numerator_ids": sorted(
                row["id"]
                for row in snapshot["changes"]
                if row["classification"] in {"impact", "no_impact", "out_of_scope"}
            ),
            "denominator_ids": sorted(row["id"] for row in snapshot["changes"]),
            "rate": (
                sum(
                    row["classification"] in {"impact", "no_impact", "out_of_scope"}
                    for row in snapshot["changes"]
                )
                / len(snapshot["changes"])
                if snapshot["changes"]
                else None
            ),
        },
        "observed_candidate_mapping": {
            "numerator_ids": sorted(
                row["id"] for row in snapshot["candidates"] if row["status"] == "mapped"
            ),
            "denominator_ids": sorted(row["id"] for row in snapshot["candidates"]),
            "rate": (
                sum(row["status"] == "mapped" for row in snapshot["candidates"])
                / len(snapshot["candidates"])
                if snapshot["candidates"]
                else None
            ),
        },
        "source_boundary_complete": bool(snapshot["expected_source_ids"])
        and not snapshot["unknown_areas"]
        and all(
            any(
                source["id"] == source_id and source["status"] == "complete"
                for source in sources
            )
            for source_id in snapshot["expected_source_ids"]
        ),
        "unknown_areas": snapshot["unknown_areas"],
        "excluded_candidate_ids": sorted(
            row["id"] for row in snapshot["candidates"] if row["status"] == "excluded"
        ),
        "all_product_features_discovered": None,
    }
    return {
        "status": status,
        "reasons": reasons,
        "metrics": metrics,
        "handoff": handoff,
    }


def feature_inventory() -> dict:
    """feature-analysis の完了 inventory 相当の fixture（候補・材料の形だけを持つ）。"""
    snapshot = {
        "schema_version": "feature-inventory-v1",
        "project_ref": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "artifact_revision": "feature-r1",
        "previous_artifact_revision": None,
        "source_revision": "commit:abc123",
        "operation_id": "fixture:feature-1",
        "event": "initial",
        "expected_source_ids": ["SRC-001"],
        "sources": [
            {
                "id": "SRC-001",
                "kind": "code",
                "ref": "product/repo",
                "scope": "src",
                "status": "complete",
                "revision": "commit:abc123",
                "evidence_ref": "evidence/sources",
                "enumeration_complete": True,
                "unretrieved": [],
            }
        ],
        "features": [
            {
                "id": "FEAT-001",
                "identity": "fixture identity FEAT-001",
                "name": "Fixture FEAT-001",
                "kind": "api",
                "status": "implemented",
                "parent_id": None,
                "source_ids": ["SRC-001"],
                "implementation_refs": ["src/feature-1.py"],
                "spec_refs": [],
                "qa_refs": [],
            },
            {
                "id": "FEAT-002",
                "identity": "fixture identity FEAT-002",
                "name": "Fixture FEAT-002",
                "kind": "api",
                "status": "planned",
                "parent_id": None,
                "source_ids": ["SRC-001"],
                "implementation_refs": ["src/feature-2.py"],
                "spec_refs": [],
                "qa_refs": [],
            },
        ],
        "candidates": [
            {
                "id": "CAND-001",
                "source_ids": ["SRC-001"],
                "evidence_ref": "evidence/candidate",
                "status": "mapped",
                "feature_id": "FEAT-001",
            }
        ],
        "changes": [
            {
                "id": "DIF-001",
                "source_id": "SRC-001",
                "before_revision": "commit:old",
                "after_revision": "commit:abc123",
                "locator": "src/auth.py",
                "evidence_ref": "evidence/diff",
                "classification": "impact",
                "feature_ids": ["FEAT-001"],
                "reason": "Authorization behavior changed",
            }
        ],
        "history": [
            {
                "event_id": "feature-event-001",
                "kind": "added",
                "revision": "commit:abc123",
                "evidence_ref": "evidence/created",
                "from_ids": [],
                "to_ids": ["FEAT-001"],
            }
        ],
        "unknown_areas": [],
    }
    return {"snapshot": snapshot, "analysis": feature_analysis(snapshot, "complete")}


def feature_ref_for(inventory: dict) -> dict:
    return {
        "owner": "feature-analysis",
        "scope": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "revision": inventory["snapshot"]["artifact_revision"],
        "content_hash": inventory["analysis"]["handoff"]["snapshot_sha256"],
    }


def spec_ref() -> dict:
    return {
        "owner": "spec-analysis",
        "scope": "project:shop",
        "artifact_ref": "authority:shop",
        "revision": "spec-r1",
        "content_hash": "b" * 64,
    }


def materialize_request(kind: str) -> dict:
    inventory = feature_inventory()
    sources = [feature_ref_for(inventory), spec_ref()]
    common = {
        "operation": "materialize",
        "scope": "project:shop",
        "feature_inventory": inventory,
        "source_refs": sources,
        "expected_revision": None,
        "current_revision": None,
        "approval_ref": None,
        "required_permission": "owner_artifact_write",
        "previous_artifact": None,
        "retirements": [],
    }
    feature_evidence = [feature_ref_for(inventory)]
    if kind == TIA:
        candidate = {
            "candidate_key": "order-api",
            "identity_action": "new",
            "item_id": None,
            "related_item_ids": [],
            "reason": "fixture candidate identity review",
            "name": "order-api",
            "description": "candidate product test target",
            "kind": "api",
            "status": "implemented",
            "parent_item_refs": [],
            "feature_refs": ["FEAT-001"],
            "evidence_refs": feature_evidence,
        }
        return {
            **common,
            "artifact_ref": "item-candidates:shop",
            "candidates": [candidate],
        }
    candidate = {
        "candidate_key": "order-authz",
        "identity_action": "new",
        "condition_id": None,
        "related_condition_ids": [],
        "reason": "fixture candidate identity review",
        "name": "order-authz",
        "intent": "verify a source-backed authorization condition",
        "kind": "authorization",
        "applicable_item_kinds": ["api", "ui"],
        "feature_refs": ["FEAT-001"],
        "item_refs": [],
        "authority_refs": [{"source_ref": spec_ref(), "entity_ref": "AUTH-001"}],
        "evidence_refs": [feature_evidence[0], spec_ref()],
        "candidate_state": "candidate",
        "unknowns": [],
    }
    return {
        **common,
        "artifact_ref": "condition-candidates:shop",
        "candidates": [candidate],
    }


def candidate_owner(store: Store, kind: str) -> tuple[str, dict]:
    """TIA / TCA: 実 materialize の成果物を保存本文とする（候補の identity は fixture 入力）。"""
    request = materialize_request(kind)
    script = ITEM_SCRIPT if kind == TIA else CONDITION_SCRIPT
    result = run_json(script, request)
    if not result.get("valid"):
        raise AssertionError(result)
    artifact = result["candidate"]
    ref = artifact["artifact_ref"]
    text = canonical(artifact)
    store.save(
        ref, text, owner=kind, scope=artifact["scope"], revision=f"sha256:{sha(text)}"
    )
    readback = store.readback(ref)
    evidence = {
        "stored_content": text,
        "readback": readback,
        "expected_revision": readback["revision"],
        "current_source_refs": request["source_refs"],
    }
    return ref, evidence


def selection_packet() -> dict:
    return {
        "schema_version": "e2e-selection-v1",
        "selection_ref": "E2ESEL-001",
        "revision": 1,
        "change_reason": "初回のE2E自動化価値判断",
        "scope_refs": ["TI-001"],
        "automation_goal": "checkout経路の反復回帰確認",
        "population_complete": True,
        "source_refs": [
            {"ref": "SPEC-001", "revision": "s8", "currentness": "current"},
            {"ref": "TI-001", "revision": "i4", "currentness": "current"},
        ],
        "candidates": [
            {
                "candidate_id": "E2E-CAND-001",
                "candidate_key": "checkout-primary",
                "source_refs": ["SPEC-001", "TI-001"],
                "decision": "selected",
                "rationale": "主要業務経路で繰り返し確認する価値がある",
            },
            {
                "candidate_id": "E2E-CAND-002",
                "candidate_key": "non-payment",
                "source_refs": ["SPEC-001", "TI-001"],
                "decision": "not_selected",
                "rationale": "currentな既存E2Eで同じ経路を確認済み",
            },
        ],
        "history": [],
        "retired_candidates": [],
        "blockers": [],
    }


def selection_owner(store: Store) -> tuple[str, dict]:
    packet = selection_packet()
    text = canonical(packet)
    ref = packet["selection_ref"]
    readback = {"revision": "git:" + "a" * 40, "content_hash": sha(text)}
    store.save(ref, text, owner=E2E, scope="checkout", revision=readback["revision"])
    evidence = {
        "stored_content": text,
        "readback": readback,
        "current_source_revisions": {
            row["ref"]: row["revision"] for row in packet["source_refs"]
        },
    }
    return ref, evidence


def report_build_input() -> dict:
    def record(unit: str, ref: str) -> dict:
        return {
            "result_ref": f"res:{unit}:{ref}",
            "unit_ref": ref,
            "unit": unit,
            "state": "PASS",
            "build_ref": "build:41",
            "environment_ref": "env:stg",
            "result_finalized": True,
            "cleanup_status": "成功",
        }

    def retrieval(source_id: str, records: list[dict]) -> dict:
        return {
            "source_id": source_id,
            "status": "complete",
            "pagination_complete": True,
            "permission_ok": True,
            "source_revision": "rev1",
            "retrieved_at": "2026-11-10T00:00:00+00:00",
            "records": records,
        }

    def planned(source_id: str, kind: str, unit: str, refs: list[str]) -> dict:
        return {
            "source_id": source_id,
            "owner_skill": "owner",
            "kind": kind,
            "unit": unit,
            "expected_refs": refs,
        }

    return {
        "plan": {
            "plan_ref": "plan:qa-1",
            "plan_revision": "p3",
            "approval_state": "approved",
            "scope_ref": "scope:checkout",
            "build_ref": "build:41",
            "environment_ref": "env:stg",
            "planned_sources": [
                planned("e2e", "e2e", "logical_primary", ["T1", "T2"]),
                planned("api", "api", "test", ["A1", "A2", "A3"]),
            ],
            "exit_criteria": [
                {
                    "criterion_id": "EX-1",
                    "metric": "pass_rate",
                    "operator": ">=",
                    "threshold": 1.0,
                    "source_ids": ["e2e"],
                },
                {
                    "criterion_id": "EX-2",
                    "metric": "fail_count",
                    "operator": "<=",
                    "threshold": 0,
                    "source_ids": ["e2e"],
                },
            ],
        },
        "retrievals": [
            retrieval(
                "e2e",
                [record("logical_primary", "T1"), record("logical_primary", "T2")],
            ),
            retrieval(
                "api",
                [record("test", "A1"), record("test", "A2"), record("test", "A3")],
            ),
        ],
        "current_source_revisions": {"e2e": "rev1", "api": "rev1"},
        "current_plan_revision": "p3",
    }


def report_owner(store: Store) -> tuple[str, dict]:
    build_input = report_build_input()
    snapshot = run_json(REPORTING_SCRIPT, build_input, "build-snapshot")
    ref = snapshot["snapshot_ref"]
    store.save(
        ref,
        canonical(snapshot),
        owner=TR,
        scope="checkout",
        revision=f"sha256:{sha(canonical(snapshot))}",
    )
    evidence = {
        "build_input_content": canonical(build_input),
        "stored_snapshot_content": canonical(snapshot),
        "current": {
            "plan_revision": "p3",
            "source_revisions": {"e2e": "rev1", "api": "rev1"},
        },
    }
    return ref, evidence


class OwnerBundle:
    """1 回の保存空間で owner の保存成果物と証拠を組み立てる。"""

    def __init__(self) -> None:
        self.store = Store()
        self.items: dict[str, tuple[str, dict]] = {}

    def item(self, skill: str) -> tuple[str, dict]:
        if skill not in self.items:
            if skill in PACKET_OWNERS:
                self.items[skill] = packet_owner(self.store, skill)
            elif skill in (TIA, TCA):
                self.items[skill] = candidate_owner(self.store, skill)
            elif skill == E2E:
                self.items[skill] = selection_owner(self.store)
            elif skill == TR:
                self.items[skill] = report_owner(self.store)
            else:
                raise KeyError(skill)
        return self.items[skill]

    def scopes(self, skills: tuple[str, ...]) -> list[dict]:
        rows = []
        for skill in skills:
            ref, evidence = self.item(skill)
            rows.append(owner_scope(skill, ref, copy.deepcopy(evidence)))
        return rows

    def requested(self, skills: tuple[str, ...]) -> list[dict]:
        return [required(skill, self.item(skill)[0]) for skill in skills]


# --- runtime-v2 root（TCD）の完了 state（既存テストと同じ synthetic 形） ----


def _refresh_runtime_fingerprints(state: dict, unit_lists: list[list[dict]]) -> None:
    for row in state["runtime_results"]:
        result = row["result"]
        result["runtime_implementation_fingerprint"] = "sha256:" + "a" * 64
        result["generator_implementation_fingerprint"] = "sha256:" + "b" * 64
        result["generation_fingerprint"] = fixture_rc.generation_fingerprint(
            generator=result["generator"],
            input_fp=result["input_fingerprint"],
            model_fp=result["model_fingerprint"],
            runtime_contract_version=result["runtime_contract_version"],
            generator_contract_version=result["generator_contract_version"],
            runtime_impl_fp=result["runtime_implementation_fingerprint"],
            generator_impl_fp=result["generator_implementation_fingerprint"],
            upstream=result["upstream_entity_fingerprints"],
            static_data_versions=result["static_data_versions"],
        )
        fresh = fixture_rc.runtime_unit_row(result)
        for units in unit_lists:
            for index, unit in enumerate(units):
                if (
                    unit.get("skill") == fresh["skill"]
                    and unit.get("runtime_unit_key") == fresh["runtime_unit_key"]
                ):
                    units[index] = fresh


def _runtime_row(
    skill: str,
    unit: str,
    model_key: str | None = None,
    *,
    materialize=False,
    active_ci_ids=None,
    materialize_model_key=None,
) -> dict:
    row = {
        "skill": skill,
        "runtime_unit_key": unit,
        "model_key": model_key,
        "support_status": "supported",
        "result_status": "ready",
        "runtime_status": "ok",
        "runtime_required": True,
        "deterministic_generated": True,
        "generation_fingerprint": f"sha256:{unit.encode().hex()[:64].ljust(64, '0')}",
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "unsupported_items": [],
        "freshness_status": "current",
        "model_completion": [
            {
                "model_key": materialize_model_key or model_key,
                "required_target_refs": [
                    f"target:{materialize_model_key or model_key}"
                ],
                "closed_target_refs": [f"target:{materialize_model_key or model_key}"],
                "active_ci_ids": sorted(active_ci_ids or []),
                "semantic_item_keys": [],
                "materialize_complete": True,
            }
        ]
        if materialize
        else [],
        "target_mappings": [],
        "target_dispositions": [],
    }
    row["result_fingerprint"] = fixture_rc.sha256_digest(row)
    return row


def _structure_state(entities: list[dict]) -> tuple[dict, dict]:
    model_entities = [row for row in entities if row["entity_type"] == "model"]
    active_models = [
        {
            "model_key": row["entity_ref"],
            "model_type": row["content"]["model_type"],
            "technique_slug": row["content"].get("technique_slug"),
            "parent_tcn_id": row["content"]["parent_tcn_id"],
            "scope_refs": row["content"].get("scope_refs", []),
            "content_fingerprint": row["content_fingerprint"],
        }
        for row in model_entities
    ]
    result = {
        "envelope_version": "1",
        "skill": TCD,
        "runtime_contract_version": fixture_rc.RUNTIME_CONTRACT_VERSION,
        "generator_contract_version": "condition-structure-v2",
        "generator": "condition_structure",
        "runtime_unit_key": "artifact:condition_structure:all",
        "model_key": None,
        "input_fingerprint": fixture_rc.sha256_digest({"input": "condition_structure"}),
        "model_fingerprint": None,
        "generation_fingerprint": fixture_rc.sha256_digest(
            {"generation": "condition_structure"}
        ),
        "runtime_implementation_fingerprint": "sha256:" + "1" * 64,
        "generator_implementation_fingerprint": "sha256:" + "2" * 64,
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": {"active_model_metadata": active_models, "entities": entities},
        "issues": [],
    }
    row = fixture_rc.runtime_unit_row(result)
    state = {
        "runtime_results": [
            {"identity": f"{TCD}::artifact:condition_structure:all", "result": result}
        ],
        "carry_forward_entities": [],
        "previous_ci_id_state": [],
    }
    return state, row


def tcd_base() -> dict:
    """runtime-v2 root（TCD）だけを持つ完了済みの入力（参照ワークフローを REF に合わせる）。"""

    def ent(skill, entity_type, entity_ref, content, **kwargs):
        return fixture_rc.make_machine_entity(
            skill, entity_type, entity_ref, content, **kwargs
        )

    tcn = ent(TCD, "tcn", "TCN-001", {"tcn_id": "TCN-001"})
    model = ent(
        TCD,
        "model",
        "ep-001",
        {
            "model_key": "ep-001",
            "model_type": "ep",
            "technique_slug": "ep",
            "parent_tcn_id": "TCN-001",
        },
        model_key="ep-001",
    )
    ci_one = ent(
        TCD,
        "ci",
        "TCN-001-CI01",
        {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"},
        model_key="ep-001",
    )
    ci_two = ent(
        TCD,
        "ci",
        "TCN-001-CI02",
        {"ci_id": "TCN-001-CI02", "tcn_id": "TCN-001", "model_key": "ep-001"},
        model_key="ep-001",
    )
    authority = ent(
        "spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"}
    )
    condition_state, condition_row = _structure_state([tcn, model])
    units = [
        condition_row,
        _runtime_row(TCD, "model:ep-001", "ep-001"),
        _runtime_row(
            TCD,
            "artifact:materialize_coverage:TCN-001",
            materialize=True,
            active_ci_ids=["TCN-001-CI01", "TCN-001-CI02"],
            materialize_model_key="ep-001",
        ),
    ]
    normalized = {
        "tcn_id": "TCN-001",
        "test_conditions": [{"tcn_id": "TCN-001"}],
        "models": [{"model_key": "ep-001", "model_type": "ep"}],
        "ci_ids": ["TCN-001-CI01", "TCN-001-CI02"],
        "upstream_entities": [
            {
                "skill": "spec-analysis",
                "entity_type": "authority",
                "entity_ref": "SPEC-001",
            }
        ],
    }
    input_value = {
        "workflow_ref": REF,
        "requested_scopes": [
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "requirement": "required",
            }
        ],
        "workflow_scopes": [
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "input_mode": "artifact",
                "normalized_input": normalized,
                "current_structure_state": condition_state,
            }
        ],
        "runtime_units": units,
        "current_entities": [tcn, model, ci_one, ci_two, authority],
        "current_runtime_units": units,
        "unsupported_item_closures": [],
    }
    _refresh_runtime_fingerprints(
        input_value["workflow_scopes"][0]["current_structure_state"],
        [input_value["runtime_units"], input_value["current_runtime_units"]],
    )
    return {"metadata": copy.deepcopy(METADATA), "input": input_value}


# --- workflow_runtime（CLI）と保存・再開 -----------------------------------


def run_workflow(
    metadata: dict, scopes: list, requested: list, **extra: Any
) -> tuple[dict, dict]:
    value: dict[str, Any] = {
        "workflow_ref": REF,
        "workflow_scopes": scopes,
        "requested_scopes": requested,
        "runtime_units": [],
        "current_runtime_units": [],
        "current_entities": [],
        "unsupported_item_closures": [],
    }
    value.update(extra)
    completed = subprocess.run(
        [sys.executable, "-B", str(WORKFLOW_SCRIPT)],
        input=json.dumps({"metadata": copy.deepcopy(metadata), "input": value}).encode(
            "utf-8"
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=CHILD_ENV,
        check=False,
    )
    if completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8", "replace"))
    return value, json.loads(completed.stdout)


def run_owner_workflow(
    bundle: OwnerBundle, skills: tuple[str, ...]
) -> tuple[dict, dict]:
    return run_workflow(METADATA, bundle.scopes(skills), bundle.requested(skills))


def render(source: dict, envelope: dict, root: str = ROOT_ID) -> str:
    return (
        f"### Machine Runtime Input: {root}\n\n```json\n"
        f"{json.dumps(source, ensure_ascii=False)}\n```\n\n"
        f"### Machine Runtime Result: {root}\n\n```json\n"
        f"{json.dumps(envelope, ensure_ascii=False)}\n```\n"
    )


def save(metadata: dict, value: dict, result: dict) -> str:
    return render({"metadata": metadata, "input": value}, result)


def binding_request(markdown: str | None, *, ref: str = REF) -> dict:
    state: dict[str, Any] = {"last_completed_qa_workflow_artifact": None}
    if markdown is not None:
        state["last_completed_qa_workflow_artifact"] = {
            "artifact_ref": "artifact:qa-workflow-r1",
            "artifact_revision": "qa-workflow-r1",
            "artifact_sha256": sha(markdown),
        }
    return {
        "workflow_ref": ref,
        "workflow_state_record": {
            "workflow_ref": ref,
            "schema_version": "1",
            "state": state,
        },
        "current_scope_ids": [],
        "blocked_scope_ids": [],
        "previous_qa_workflow_artifact_markdown": markdown,
        "scope_removal_resolutions": [],
        "scope_removal_applied_states": [],
    }


def resume(markdown: str, ref: str = REF) -> dict:
    return ds.evaluate(binding_request(markdown, ref=ref))


def completed(result: dict) -> bool:
    return result.get("runtime_status") == "ok" and (
        result.get("payload", {}).get("can_complete") is True
    )


def verified_rows(result: dict) -> dict[str, dict]:
    return {
        row["skill"]: row["verified_artifact"]
        for row in result["payload"]["verified_owner_scopes"]
    }


def unverified(result: dict) -> dict[str, str]:
    return {
        row["skill"]: row["reason"] for row in result["payload"]["unverified_scopes"]
    }


def _refresh_identity(source: dict, envelope: dict, version: str) -> None:
    """版と入力を変えた後、保存済みのフィンガープリントを downstream_state と同じ式で再計算する。"""
    metadata = source["metadata"]
    metadata["generator_contract_version"] = version
    envelope["generator_contract_version"] = version
    input_fp = ds.input_fingerprint(
        "qa-workflow",
        metadata["runtime_unit_key"],
        metadata["input_mode"],
        source["input"],
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    model_fp = ds.model_fingerprint(metadata, input_fp)
    upstream = ds.upstream_entity_fingerprints(ds.validate_upstream_entities(metadata))
    envelope["input_fingerprint"] = input_fp
    envelope["model_fingerprint"] = model_fp
    envelope["upstream_entity_fingerprints"] = upstream
    envelope["generation_fingerprint"] = ds.generation_fingerprint(
        generator="workflow_runtime",
        input_fp=input_fp,
        model_fp=model_fp,
        runtime_contract_version="runtime-v2",
        generator_contract_version=version,
        runtime_impl_fp=envelope["runtime_implementation_fingerprint"],
        generator_impl_fp=envelope["generator_implementation_fingerprint"],
        upstream=upstream,
        static_data_versions=envelope["static_data_versions"],
    )


V2_ONLY_PAYLOAD_KEYS = (
    "scope_set_declared",
    "requested_scopes",
    "missing_requested_scopes",
    "excluded_scopes",
    "unrequested_scopes",
    "verified_owner_scopes",
)


class OwnerCompletionScenarios(unittest.TestCase):
    """正常系: 完了 → 保存 → 再開（R1〜R8）。"""

    def test_r1_ra_ta_tm_complete_save_and_resume(self) -> None:
        # 期待: RA・TA・TM が verified、can_complete=True。保存 markdown の再検証が通り、
        # downstream_state.evaluate が valid、inactive 系は空。
        bundle = OwnerBundle()
        value, result = run_owner_workflow(bundle, PACKET_OWNERS)
        self.assertTrue(completed(result), result)
        self.assertEqual(set(verified_rows(result)), set(PACKET_OWNERS))
        markdown = save(METADATA, value, result)
        _, payload = ds._validate_frozen_pair(markdown, REF)
        self.assertTrue(payload["can_complete"])
        evaluated = resume(markdown)
        self.assertTrue(evaluated["valid"], evaluated)
        for key in (
            "inactive_tr_ids",
            "inactive_tcn_ids",
            "inactive_model_keys",
            "inactive_ci_ids",
            "inactive_tc_ids",
        ):
            self.assertEqual(evaluated["payload"][key], [], key)

    def test_r2_each_remaining_owner_completes_saves_and_resumes(self) -> None:
        # 期待: TIA・TCA・E2E・TR をそれぞれ単独の workflow で完了 → 保存 → 再開できる。
        for skill in (TIA, TCA, E2E, TR):
            with self.subTest(skill=skill):
                bundle = OwnerBundle()
                value, result = run_owner_workflow(bundle, (skill,))
                self.assertTrue(completed(result), result)
                self.assertEqual(set(verified_rows(result)), {skill})
                markdown = save(METADATA, value, result)
                self.assertTrue(resume(markdown)["valid"])

    def test_r2_all_seven_owner_skills_complete_together(self) -> None:
        # 期待: 7 owner Skill（TIA・TCA・E2E・TR・RA・TA・TM）の混在が完了し、再開できる。
        bundle = OwnerBundle()
        value, result = run_owner_workflow(bundle, ALL_OWNERS)
        self.assertTrue(completed(result), result)
        self.assertEqual(set(verified_rows(result)), set(ALL_OWNERS))
        self.assertTrue(resume(save(METADATA, value, result))["valid"])

    def test_r3_runtime_v2_root_and_owner_scopes_mixed_resume(self) -> None:
        # 期待: TCD（runtime-v2 root・null でない state）と 7 owner の混在が完了・再開できる。
        # TCD の verified_owner_scopes には現れず、owner だけが記録される。
        base = tcd_base()
        bundle = OwnerBundle()
        scopes = [base["input"]["workflow_scopes"][0], *bundle.scopes(ALL_OWNERS)]
        requested = [
            base["input"]["requested_scopes"][0],
            *bundle.requested(ALL_OWNERS),
        ]
        value, result = run_workflow(
            base["metadata"],
            scopes,
            requested,
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        self.assertTrue(completed(result), result)
        self.assertEqual(set(verified_rows(result)), set(ALL_OWNERS))
        self.assertNotIn(TCD, verified_rows(result))
        self.assertTrue(resume(save(base["metadata"], value, result))["valid"])

    def test_r4_unchanged_inputs_reuse_the_same_records_and_results(self) -> None:
        # 期待: 入力が変わらなければ 2 回目の完了結果と再開結果は 1 回目と同一（不必要な変化なし）。
        bundle = OwnerBundle()
        value, first = run_owner_workflow(bundle, PACKET_OWNERS)
        _, second = run_workflow(
            METADATA, bundle.scopes(PACKET_OWNERS), bundle.requested(PACKET_OWNERS)
        )
        self.assertEqual(first["payload"], second["payload"])
        markdown = save(METADATA, value, first)
        self.assertEqual(resume(markdown), resume(markdown))

    def test_r5_only_the_changed_owner_scope_is_reverified(self) -> None:
        # 期待: TM の expected_revision を古い値にした回では TM だけが unverified。RA・TA は
        # verified のまま、verified_artifact は初回と同一。TM を現行 revision に戻すと TM だけが
        # 再び verified になり、RA・TA の記録は初回と変わらない。
        bundle = OwnerBundle()
        _, first = run_owner_workflow(bundle, PACKET_OWNERS)
        first_rows = verified_rows(first)
        stale_scopes = bundle.scopes(PACKET_OWNERS)
        stale_scopes[2]["normalized_input"]["owner_verification"][
            "expected_revision"
        ] = "tm-stale-rev"
        _, stale = run_workflow(METADATA, stale_scopes, bundle.requested(PACKET_OWNERS))
        self.assertFalse(completed(stale), stale)
        self.assertEqual(set(unverified(stale)), {TM})
        self.assertEqual(
            {k: v for k, v in verified_rows(stale).items()},
            {k: first_rows[k] for k in (RA, TA)},
        )
        current_scopes = bundle.scopes(PACKET_OWNERS)
        value, again = run_workflow(
            METADATA, current_scopes, bundle.requested(PACKET_OWNERS)
        )
        self.assertTrue(completed(again), again)
        self.assertEqual(verified_rows(again), first_rows)

    def test_r6_completed_workflow_resume_is_stable(self) -> None:
        # 期待: 完了済み workflow を 2 回再開しても結果は同一。保存入力を再実行しても verified は同一。
        base = tcd_base()
        bundle = OwnerBundle()
        scopes = [base["input"]["workflow_scopes"][0], *bundle.scopes(ALL_OWNERS)]
        requested = [
            base["input"]["requested_scopes"][0],
            *bundle.requested(ALL_OWNERS),
        ]
        value, result = run_workflow(
            base["metadata"],
            scopes,
            requested,
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        markdown = save(base["metadata"], value, result)
        self.assertEqual(resume(markdown), resume(markdown))
        _, rerun = run_workflow(
            base["metadata"],
            value["workflow_scopes"],
            value["requested_scopes"],
            runtime_units=value["runtime_units"],
            current_runtime_units=value["current_runtime_units"],
            current_entities=value["current_entities"],
        )
        self.assertEqual(verified_rows(rerun), verified_rows(result))

    def test_r7_v1_root_only_history_still_resumes(self) -> None:
        # 期待: v1 の履歴（root のみ、要求集合と検証記録を持たない）は従来どおり再開できる。
        base = tcd_base()
        value, result = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        source = {
            "metadata": copy.deepcopy(base["metadata"]),
            "input": copy.deepcopy(value),
        }
        envelope = copy.deepcopy(result)
        del source["input"]["requested_scopes"]
        for key in V2_ONLY_PAYLOAD_KEYS:
            envelope["payload"].pop(key, None)
        _refresh_identity(source, envelope, "workflow-runtime-v1")
        _, payload = ds._validate_frozen_pair(render(source, envelope), REF)
        self.assertTrue(payload["can_complete"])
        self.assertTrue(resume(render(source, envelope))["valid"])

    def test_r8_v2_requested_scopes_are_kept_in_the_saved_result(self) -> None:
        # 期待: v2 の要求集合は結果の requested_scopes に維持され、missing は空、保存 markdown の
        # 再開で同じ要求集合が読み戻される。
        bundle = OwnerBundle()
        requested = bundle.requested(PACKET_OWNERS)
        value, result = run_workflow(METADATA, bundle.scopes(PACKET_OWNERS), requested)
        self.assertTrue(completed(result), result)
        self.assertEqual(result["payload"]["requested_scopes"], requested)
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        markdown = save(METADATA, value, result)
        self.assertTrue(resume(markdown)["valid"])
        _, payload = ds._validate_frozen_pair(markdown, REF)
        self.assertEqual(payload["requested_scopes"], requested)


class OwnerResumeNegativeScenarios(unittest.TestCase):
    """異常系: 完了・再開してはいけない（X1〜X12）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = OwnerBundle()
        cls.value, cls.result = run_owner_workflow(cls.bundle, PACKET_OWNERS)
        assert completed(cls.result), cls.result
        cls.markdown = save(METADATA, cls.value, cls.result)

    def saved_tamper(self, mutate, *, refresh: bool = False) -> str:
        """保存結果を改ざんする。refresh=True は入力の fingerprint を同じ式で再計算し、
        fingerprint 不一致より後段の検査（本文 hash・記録・owner 照合）まで到達させる。"""
        source = {
            "metadata": copy.deepcopy(METADATA),
            "input": copy.deepcopy(self.value),
        }
        envelope = copy.deepcopy(self.result)
        mutate(source, envelope)
        if refresh:
            _refresh_identity(source, envelope, "workflow-runtime-v2")
        return render(source, envelope)

    def assert_resume_rejected(self, markdown: str, ref: str = REF) -> None:
        with self.assertRaises(InvalidInput):
            resume(markdown, ref)

    def test_x1_runtime_v2_root_with_null_state_is_rejected(self) -> None:
        # 期待: runtime-v2 root（TCD）の current_structure_state=null は完了せず、再開も拒否。
        base = tcd_base()
        scopes = copy.deepcopy(base["input"]["workflow_scopes"])
        scopes[0]["current_structure_state"] = None
        _, result = run_workflow(
            base["metadata"],
            scopes,
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        self.assertFalse(completed(result), result)

        # 有効な保存 markdown（TCD 完了）から root の state だけを null にした改ざん。
        tcd_value, tcd_result = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        tampered = {
            "metadata": copy.deepcopy(base["metadata"]),
            "input": copy.deepcopy(tcd_value),
        }
        tampered["input"]["workflow_scopes"][0]["current_structure_state"] = None
        envelope = copy.deepcopy(tcd_result)
        _refresh_identity(tampered, envelope, "workflow-runtime-v2")
        self.assert_resume_rejected(render(tampered, envelope))

    def test_x2_owner_scope_with_non_null_state_is_rejected(self) -> None:
        # 期待: owner（RA）に非null の current_structure_state を持つ入力は完了しない（偽造の入口）。
        base = tcd_base()
        scopes = self.bundle.scopes(PACKET_OWNERS)
        scopes[0]["current_structure_state"] = base["input"]["workflow_scopes"][0][
            "current_structure_state"
        ]
        try:
            _, result = run_workflow(
                METADATA, scopes, self.bundle.requested(PACKET_OWNERS)
            )
        except AssertionError:
            result = None
        self.assertFalse(result is not None and completed(result), result)

        def non_null(source, envelope):
            source["input"]["workflow_scopes"][0]["current_structure_state"] = base[
                "input"
            ]["workflow_scopes"][0]["current_structure_state"]

        self.assert_resume_rejected(self.saved_tamper(non_null, refresh=True))

    def test_x3_records_missing_duplicated_or_extra_are_rejected(self) -> None:
        # 期待: 検証記録の欠落・重複・余分（scope に対応しない記録）はいずれも再開を拒否。
        def missing(source, envelope):
            envelope["payload"]["verified_owner_scopes"] = envelope["payload"][
                "verified_owner_scopes"
            ][1:]

        def duplicated(source, envelope):
            rows = envelope["payload"]["verified_owner_scopes"]
            envelope["payload"]["verified_owner_scopes"] = [
                *rows,
                copy.deepcopy(rows[0]),
            ]

        def extra(source, envelope):
            rows = copy.deepcopy(envelope["payload"]["verified_owner_scopes"])
            extra_row = copy.deepcopy(rows[0])
            extra_row["skill"] = "test-item-analysis"
            extra_row["target"] = "item-candidates:unrelated"
            extra_row["verified_artifact"]["artifact_ref"] = "item-candidates:unrelated"
            envelope["payload"]["verified_owner_scopes"] = [*rows, extra_row]

        for name, mutate in (
            ("missing", missing),
            ("duplicated", duplicated),
            ("extra", extra),
        ):
            with self.subTest(case=name):
                self.assert_resume_rejected(self.saved_tamper(mutate))

    def test_x4_no_evidence_tampered_body_or_target_mismatch_are_rejected(self) -> None:
        # 期待: 証拠なし（owner_verification 欠落）は完了しない。保存本文の改ざんと target 不一致は再開拒否。
        scopes = self.bundle.scopes(PACKET_OWNERS)
        del scopes[0]["normalized_input"]["owner_verification"]
        _, no_evidence = run_workflow(
            METADATA, scopes, self.bundle.requested(PACKET_OWNERS)
        )
        self.assertFalse(completed(no_evidence), no_evidence)
        self.assertIn(RA, unverified(no_evidence))

        def altered_body(source, envelope):
            evidence = source["input"]["workflow_scopes"][0]["normalized_input"][
                "owner_verification"
            ]
            packet = json.loads(evidence["stored_content"])
            packet["scope"] = "altered-after-save"
            evidence["stored_content"] = canonical(packet)

        def target_mismatch(source, envelope):
            envelope["payload"]["verified_owner_scopes"][0]["verified_artifact"][
                "artifact_ref"
            ] = "other:ref"

        self.assert_resume_rejected(self.saved_tamper(altered_body, refresh=True))
        self.assert_resume_rejected(self.saved_tamper(target_mismatch, refresh=True))

    def test_x5_unregistered_skill_record_is_rejected(self) -> None:
        # 期待: owner verifier 未登録の Skill（defect-management）は完了せず、null 状態の記録も拒否。
        scopes = self.bundle.scopes(PACKET_OWNERS)
        scopes.append(owner_scope("defect-management", "defect:1", {"verified": True}))
        _, result = run_workflow(
            METADATA,
            scopes,
            self.bundle.requested(PACKET_OWNERS)
            + [required("defect-management", "defect:1")],
        )
        self.assertFalse(completed(result), result)
        self.assertIn("defect-management", unverified(result))

        def unregistered(source, envelope):
            source["input"]["workflow_scopes"].append(
                {
                    "skill": "defect-management",
                    "target": "defect:1",
                    "execution_range": "plan",
                    "input_mode": "artifact",
                    "normalized_input": {},
                    "current_structure_state": None,
                }
            )
            source["input"]["requested_scopes"].append(
                required("defect-management", "defect:1")
            )

        self.assert_resume_rejected(self.saved_tamper(unregistered))

    def test_x6_other_workflow_is_rejected(self) -> None:
        # 期待: 別 workflow_ref の状態に対して、この保存 markdown は再開できない。
        self.assert_resume_rejected(self.markdown, ref=OTHER_REF)

    def test_x7_fingerprint_and_hash_mismatch_are_rejected(self) -> None:
        # 期待: 保存結果の fingerprint 改ざん、検証記録の content_hash の不一致は再開拒否。
        def bad_fingerprint(source, envelope):
            envelope["input_fingerprint"] = "sha256:" + "0" * 64

        def bad_content_hash(source, envelope):
            envelope["payload"]["verified_owner_scopes"][0]["verified_artifact"][
                "content_hash"
            ] = "0" * 64

        for name, mutate in (
            ("fingerprint", bad_fingerprint),
            ("content_hash", bad_content_hash),
        ):
            with self.subTest(case=name):
                self.assert_resume_rejected(self.saved_tamper(mutate))

    def test_x8_omitted_required_owner_scope_blocks_completion(self) -> None:
        # 期待: 要求集合にある TM が workflow_scopes から省かれると完了しない（missing）。
        scopes = self.bundle.scopes((RA, TA))
        _, result = run_workflow(METADATA, scopes, self.bundle.requested(PACKET_OWNERS))
        self.assertFalse(completed(result), result)
        self.assertIn(
            TM, {row["skill"] for row in result["payload"]["missing_requested_scopes"]}
        )

    def test_x9_excluded_by_approval_is_not_confirmed(self) -> None:
        # 期待: 承認による除外（excluded_by_approval）は照合手段がなければ確定せず、scope は必須のまま。
        requested = self.bundle.requested((RA, TA))
        requested.append(
            {
                "skill": TM,
                "target": None,
                "execution_range": "plan",
                "requirement": "excluded_by_approval",
                "approval_ref": "APPROVAL-001",
            }
        )
        _, result = run_workflow(METADATA, self.bundle.scopes((RA, TA)), requested)
        self.assertFalse(completed(result), result)

    def test_x10_owner_failures_do_not_complete_and_failed_result_is_not_resumable(
        self,
    ) -> None:
        # 期待: 保存本文が owner validator を通らない・source が stale・source revision が unknown は
        # いずれも unverified。owner 不在は owner_verifier_unavailable。can_complete=False の保存は再開拒否。
        scopes = self.bundle.scopes((RA,))
        scopes[0]["normalized_input"]["owner_verification"]["current_source_refs"][0][
            "revision"
        ] = "changed-rev"
        _, stale = run_workflow(METADATA, scopes, self.bundle.requested((RA,)))
        self.assertFalse(completed(stale), stale)
        self.assertIn(RA, unverified(stale))

        scopes = self.bundle.scopes((RA,))
        scopes[0]["normalized_input"]["owner_verification"]["current_source_refs"] = []
        _, unknown = run_workflow(METADATA, scopes, self.bundle.requested((RA,)))
        self.assertFalse(completed(unknown), unknown)
        self.assertEqual(unverified(unknown).get(RA), "source_revision_unknown")

        scopes = self.bundle.scopes((TM,))
        scopes[0]["normalized_input"]["owner_verification"]["stored_content"] = "{}"
        _, invalid = run_workflow(METADATA, scopes, self.bundle.requested((TM,)))
        self.assertFalse(completed(invalid), invalid)

        with mock.patch.object(owner_verifiers, "SKILLS_ROOT", Path("/nonexistent")):
            outcome = owner_verifiers.verify(
                RA,
                owner_scope(
                    RA,
                    "x",
                    {
                        "stored_content": "{}",
                        "readback": {},
                        "expected_revision": "r",
                        "current_source_refs": [],
                    },
                ),
            )
        self.assertEqual(outcome["status"], "unverified")

        def not_complete(source, envelope):
            envelope["payload"]["can_complete"] = False

        self.assert_resume_rejected(self.saved_tamper(not_complete))

    def test_x11_stale_readback_after_revision_change_is_not_accepted_as_current(
        self,
    ) -> None:
        # 期待: 保存後に候補の内容が改版され、新しい本文と現行 readback（新 revision）が得られた場合、
        # 古い expected_revision との組合せは完了しない（readback revision 不一致）。
        # 一方、古い本文・古い読戻し・古い expected_revision の自己整合した組は受理される。これは
        # 呼出し側が現行 readback を取り直す既知の制約の範囲であり、runtime 単独では検出できない。
        bundle = OwnerBundle()
        ref, old = bundle.item(TIA)
        old_revision = old["expected_revision"]
        request = materialize_request(TIA)
        request["candidates"][0]["name"] = "order-api-revised"
        newer = run_json(ITEM_SCRIPT, request)
        self.assertTrue(newer.get("valid"), newer)
        newer_text = canonical(newer["candidate"])
        bundle.store.save(
            ref,
            newer_text,
            owner=TIA,
            scope=newer["candidate"]["scope"],
            revision=f"sha256:{sha(newer_text)}",
        )
        current = bundle.store.readback(ref)
        self.assertNotEqual(current["revision"], old_revision)
        mixed = {**old, "stored_content": newer_text, "readback": current}
        _, result = run_workflow(
            METADATA, [owner_scope(TIA, ref, mixed)], [required(TIA, ref)]
        )
        self.assertFalse(completed(result), result)
        self.assertIn(TIA, unverified(result))
        # 限界の記録: 古い本文・古い読戻し・古い expected_revision の組は自己整合しているため受理される。
        _, self_consistent = run_workflow(
            METADATA, [owner_scope(TIA, ref, old)], [required(TIA, ref)]
        )
        self.assertTrue(completed(self_consistent), self_consistent)
        self.assertEqual(old_revision, old["expected_revision"])

    def test_x12_failed_resume_does_not_break_the_baseline(self) -> None:
        # 期待: 改ざんした再開が拒否されても、正常な baseline の再開結果と保存 markdown は変わらない。
        baseline_before = resume(self.markdown)
        for mutate in (
            lambda s, e: e["payload"].update(verified_owner_scopes=[]),
            lambda s, e: e.update(input_fingerprint="sha256:" + "0" * 64),
        ):
            with self.assertRaises(InvalidInput):
                resume(self.saved_tamper(mutate))
        self.assertEqual(resume(self.markdown), baseline_before)
        self.assertTrue(baseline_before["valid"])


if __name__ == "__main__":
    unittest.main()
