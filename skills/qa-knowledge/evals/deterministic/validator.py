from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if len(matches) != 1:
        return None, ["exactly_one_json_knowledge_record_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    return (value, []) if isinstance(value, dict) else (None, ["knowledge_record_must_be_object"])


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("qa-knowledge", eval_id)
    doc, errors = _document(text)
    result.add("KN-D001", doc is not None, "knowledge decision / entry artifactが整形式で存在すること", evidence=errors or None)
    if doc is None:
        return result
    action = doc.get("action")
    entry = doc.get("entry")
    routed = action == "route_to_owner"
    result.add("KN-D002", routed or action in {"create", "update", "revalidation", "replacement", "lookup", "history", "blocked"}, "処理がowner routingまたはqa-knowledgeの正規lifecycleであること")
    if isinstance(entry, dict):
        identity = entry.get("identity")
        expected_ref = "KN-" + hashlib.sha256(_canonical(identity)).hexdigest() if isinstance(identity, dict) and identity else None
        result.add("KN-D003", expected_ref is not None and entry.get("entry_ref") == expected_ref, "entry_refがstructured semantic identityから決定論的に解決されること")
        required = ("kind", "content", "scope_refs", "applicability", "provenance", "currentness_dependencies", "state", "related_qa_refs")
        missing = [field for field in required if field not in entry]
        result.add("KN-D004", not missing and entry.get("kind") in {"test_subject_or_mechanism", "test_focus", "test_environment"} and entry.get("state") in {"有効", "要再検証", "置換済み"}, "entry schema、kind、stateが揃うこと", evidence=missing)
        provenance_ok = all(isinstance(item, dict) and item.get("ref") and item.get("revision") for item in entry.get("provenance", []))
        dependency_ok = all(isinstance(item, dict) and item.get("ref") and item.get("revision") for item in entry.get("currentness_dependencies", []))
        result.add("KN-D005", provenance_ok and dependency_ok, "provenanceとcurrentness dependencyを別ref / revisionとして保持すること")
        currentness = doc.get("currentness_status")
        result.add("KN-D006", entry.get("state") != "有効" or currentness == "current", "有効entryはcurrentness確認済みであること")
        storage = doc.get("storage", {})
        if action == "create":
            storage_ok = storage.get("atomic_create_if_absent") is True and storage.get("complete_root_snapshot") is True
        elif action in {"update", "revalidation"}:
            storage_ok = storage.get("native_atomic_conditional_write") is True and bool(storage.get("expected_entry_revision"))
        elif action == "replacement":
            storage_ok = storage.get("native_atomic_multi_entry_update") is True
        else:
            storage_ok = True
        result.add("KN-D007", storage_ok or action == "blocked", "保存成功には該当するnative atomic conditionを要求し、なければblockすること")
        if action == "update":
            result.add("KN-D008", storage.get("auto_merge") is False, "same-entry CAS conflictをsemantic auto-mergeしないこと")
    else:
        result.add("KN-D003", routed or action in {"lookup", "history", "blocked"}, "entryを作らないrouting / lookup outcomeを許可すること")
    result.add("KN-D009", not expected.get("must_route", False) or routed, "既存QA正本候補をownerへ戻すこと")
    result.add("KN-D010", not expected.get("must_block_storage", False) or action == "blocked", "CAS / completeness不足の保存をfail-closedにすること")
    result.add("KN-D011", not re.search(r"(?i)(?:password|access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}", text), "secret実値をentry / outputへ含めないこと")
    return result
