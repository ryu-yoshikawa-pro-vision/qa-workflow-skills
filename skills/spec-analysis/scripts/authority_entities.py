"""Build canonical Authority Machine Entities for spec-analysis.

This helper is intentionally not a runtime unit.  It is the only production
path used to turn normalized Authority rows into machine evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_contract import (
    ENTITY_SCHEMA_VERSION,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_STDOUT_BYTES,
    InvalidInput,
    LimitExceeded,
    RuntimeErrorBase,
    canonical_json_bytes,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    extract_machine_blocks,
    implementation_fingerprint,
    make_machine_entity,
    reject_unknown,
    sha256_digest,
    strict_loads,
)

SCRIPT_PATH = Path(__file__).resolve()
_V1_ENTITY_FIELDS = {
    "schema_version",
    "skill",
    "entity_type",
    "entity_ref",
    "model_key",
    "content",
    "content_fingerprint",
    "upstream_entity_dependencies",
    "runtime_dependencies",
}


def _authorities_from_v1_artifact(markdown: object) -> list[dict]:
    if not isinstance(markdown, str):
        raise InvalidInput("source_artifact_markdown must be a string")
    blocks = extract_machine_blocks(markdown, "Machine Entities", allow_duplicates=True)
    selected = [
        (identity, body) for identity, body in blocks if identity == "spec-analysis"
    ]
    if len(selected) != 1:
        raise InvalidInput(
            "exactly one v1 spec-analysis Machine Entities block is required"
        )
    _identity, wrapper = selected[0]
    if (
        set(wrapper) != {"schema_version", "skill", "entities"}
        or wrapper.get("schema_version") != "entity-state-v1"
        or wrapper.get("skill") != "spec-analysis"
        or not isinstance(wrapper.get("entities"), list)
    ):
        raise InvalidInput("v1 Machine Entities wrapper is invalid")
    authorities = []
    seen: set[str] = set()
    for index, entity in enumerate(wrapper["entities"]):
        if (
            not isinstance(entity, dict)
            or set(entity) != _V1_ENTITY_FIELDS
            or entity.get("schema_version") != "entity-state-v1"
            or entity.get("skill") != "spec-analysis"
            or entity.get("entity_type") != "authority"
            or entity.get("model_key") is not None
            or not isinstance(entity.get("content"), dict)
            or entity.get("upstream_entity_dependencies") != []
            or entity.get("runtime_dependencies") != []
            or entity.get("content_fingerprint") != sha256_digest(entity.get("content"))
        ):
            raise InvalidInput(f"v1 Authority Entity[{index}] is invalid")
        content = entity["content"]
        if set(content) != {
            "authority_id",
            "authority_type",
            "active_content",
            "scope",
            "source_refs",
            "relations",
            "related_authority_refs",
        } or content.get("authority_id") != entity.get("entity_ref"):
            raise InvalidInput(f"v1 Authority Entity[{index}] content is invalid")
        authority_id = content["authority_id"]
        if not isinstance(authority_id, str) or authority_id in seen:
            raise InvalidInput("v1 Authority identity is duplicated or invalid")
        seen.add(authority_id)
        authorities.append(content)
    return authorities


def build(authorities: object) -> dict:
    rows = ensure_list(authorities, "authorities")
    entities = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"authorities[{index}]はobjectである必要があります")
        reject_unknown(
            row,
            {
                "authority_id",
                "authority_type",
                "active_content",
                "scope",
                "source_refs",
                "relations",
                "related_authority_refs",
            },
        )
        authority_id = ensure_nonempty_string(
            row["authority_id"], f"authorities[{index}].authority_id"
        )
        if authority_id in seen:
            raise InvalidInput(f"authority_idが重複しています: {authority_id}")
        seen.add(authority_id)
        if not isinstance(row["authority_type"], str) or not row["authority_type"]:
            raise InvalidInput(f"authorities[{index}].authority_typeが不正です")
        if not isinstance(row["active_content"], dict):
            raise InvalidInput(
                f"authorities[{index}].active_contentはobjectである必要があります"
            )
        if not isinstance(row["scope"], (str, dict, type(None))):
            raise InvalidInput(f"authorities[{index}].scopeが不正です")
        for field in ("source_refs", "relations", "related_authority_refs"):
            if not isinstance(row[field], list) or not all(
                isinstance(value, str) for value in row[field]
            ):
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
        entities.append(
            make_machine_entity("spec-analysis", "authority", authority_id, content)
        )
    entities.sort(key=lambda entity: entity["entity_ref"])
    return {
        "schema_version": ENTITY_SCHEMA_VERSION,
        "skill": "spec-analysis",
        "entities": entities,
        "expected_entity_identities": [
            {
                "skill": "spec-analysis",
                "entity_type": "authority",
                "entity_ref": entity["entity_ref"],
            }
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
        if set(request) == {"authorities"}:
            result = build(request["authorities"])
        elif set(request) == {"source_artifact_markdown"}:
            result = build(
                _authorities_from_v1_artifact(request["source_artifact_markdown"])
            )
        else:
            reject_unknown(request, {"authorities"}, {"source_artifact_markdown"})
            raise InvalidInput("request must use one exclusive authority input")
        encoded = canonical_json_bytes(result) + b"\n"
        if len(encoded) > MAX_STDOUT_BYTES:
            raise LimitExceeded("stdout JSONのbyte上限を超えました")
        sys.stdout.buffer.write(encoded)
        return 0
    except RuntimeErrorBase as exc:
        error = {
            "valid": False,
            "status": "blocked",
            "issues": [
                {"issue_type": exc.issue_type, "blocking": True, "message": exc.message}
            ],
            "entities": [],
            "expected_entity_identities": [],
        }
        encoded = canonical_json_bytes(error) + b"\n"
        if len(encoded) <= MAX_STDOUT_BYTES:
            sys.stdout.buffer.write(encoded)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
