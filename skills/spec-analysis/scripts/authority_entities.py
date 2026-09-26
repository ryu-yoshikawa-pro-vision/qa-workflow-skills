"""Build canonical Authority Machine Entities for spec-analysis.

This helper is intentionally not a runtime unit.  It is the only production
path used to turn normalized Authority rows into machine evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

from runtime_contract import (
    ENTITY_SCHEMA_VERSION,
    InvalidInput,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_STDOUT_BYTES,
    LimitExceeded,
    RuntimeErrorBase,
    canonical_json_bytes,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    implementation_fingerprint,
    make_machine_entity,
    reject_unknown,
    strict_loads,
)


SCRIPT_PATH = Path(__file__).resolve()


def build(authorities: object) -> dict:
    rows = ensure_list(authorities, "authorities")
    entities = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"authorities[{index}]はobjectである必要があります")
        reject_unknown(
            row,
            {"authority_id", "authority_type", "active_content", "scope", "source_refs", "relations", "related_authority_refs"},
        )
        authority_id = ensure_nonempty_string(row["authority_id"], f"authorities[{index}].authority_id")
        if authority_id in seen:
            raise InvalidInput(f"authority_idが重複しています: {authority_id}")
        seen.add(authority_id)
        if not isinstance(row["authority_type"], str) or not row["authority_type"]:
            raise InvalidInput(f"authorities[{index}].authority_typeが不正です")
        if not isinstance(row["active_content"], dict):
            raise InvalidInput(f"authorities[{index}].active_contentはobjectである必要があります")
        if not isinstance(row["scope"], (str, dict, type(None))):
            raise InvalidInput(f"authorities[{index}].scopeが不正です")
        for field in ("source_refs", "relations", "related_authority_refs"):
            if not isinstance(row[field], list) or not all(isinstance(value, str) for value in row[field]):
                raise InvalidInput(f"authorities[{index}].{field}が不正です")
        content = canonicalize(
            {
                "authority_id": authority_id,
                "authority_type": row["authority_type"],
                "active_content": row["active_content"],
                "scope": row["scope"],
                "source_refs": row["source_refs"],
                "relations": row["relations"],
                "related_authority_refs": row["related_authority_refs"],
            }
        )
        entities.append(make_machine_entity("spec-analysis", "authority", authority_id, content))
    entities.sort(key=lambda entity: entity["entity_ref"])
    return {
        "schema_version": ENTITY_SCHEMA_VERSION,
        "skill": "spec-analysis",
        "entities": entities,
        "expected_entity_identities": [
            {"skill": "spec-analysis", "entity_type": "authority", "entity_ref": entity["entity_ref"]}
            for entity in entities
        ],
        "implementation_fingerprint": implementation_fingerprint(SCRIPT_PATH),
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
            raise LimitExceeded("集約stdinのbyte上限を超えました")
        request = strict_loads(raw, aggregate=True)
        if not isinstance(request, dict):
            raise InvalidInput("top-level JSONはobjectである必要があります")
        reject_unknown(request, {"authorities"})
        result = build(request["authorities"])
        encoded = canonical_json_bytes(result) + b"\n"
        if len(encoded) > MAX_STDOUT_BYTES:
            raise LimitExceeded("stdout JSONのbyte上限を超えました")
        sys.stdout.buffer.write(encoded)
        return 0
    except RuntimeErrorBase as exc:
        error = {"valid": False, "status": "blocked", "issues": [{"issue_type": exc.issue_type, "blocking": True, "message": exc.message}], "entities": [], "expected_entity_identities": []}
        encoded = canonical_json_bytes(error) + b"\n"
        if len(encoded) <= MAX_STDOUT_BYTES:
            sys.stdout.buffer.write(encoded)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
