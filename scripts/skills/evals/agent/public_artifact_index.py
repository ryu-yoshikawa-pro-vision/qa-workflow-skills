from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

_STATUSES = {"executed", "reused", "skipped", "blocked", "incomplete"}
_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def _load(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )


def _safe_markdown(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if path.suffix.lower() != ".md" or any(part.startswith(".") for part in path.parts):
        return None
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        current.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return current if current.is_file() else None


def validate(output_root: Path, contract_path: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if output_root.is_symlink() or not output_root.is_dir():
        return {"valid": False, "issues": [{"kind": "unsafe_output_root"}]}
    try:
        contract = _load(contract_path)
        index = _load(output_root / "artifact-index.json")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"valid": False, "issues": [{"kind": "missing_or_invalid_json"}]}

    if (
        not isinstance(contract, dict)
        or set(contract)
        != {
            "schema_version",
            "required_artifacts",
            "optional_artifacts",
            "max_artifact_file_bytes",
            "max_artifact_total_bytes",
        }
        or type(contract.get("schema_version")) is not int
        or contract.get("schema_version") != 1
    ):
        return {"valid": False, "issues": [{"kind": "invalid_public_contract"}]}
    if any(
        type(contract.get(field)) is not int or contract[field] <= 0
        for field in ("max_artifact_file_bytes", "max_artifact_total_bytes")
    ):
        return {"valid": False, "issues": [{"kind": "invalid_public_contract"}]}
    if not isinstance(index, dict) or set(index) != {
        "schema_version",
        "artifacts",
        "routing",
    }:
        return {"valid": False, "issues": [{"kind": "invalid_index_root"}]}
    if (
        type(index.get("schema_version")) is not int
        or index["schema_version"] != 1
        or not isinstance(index.get("artifacts"), list)
        or not isinstance(index.get("routing"), list)
    ):
        return {"valid": False, "issues": [{"kind": "invalid_index_schema"}]}

    required_rows = contract["required_artifacts"]
    optional_rows = contract["optional_artifacts"]
    if not isinstance(required_rows, list) or not isinstance(optional_rows, list):
        return {"valid": False, "issues": [{"kind": "invalid_public_contract"}]}
    required = {
        (row["skill"], row["kind"], row["scope"])
        for row in required_rows
        if isinstance(row, dict)
        and set(row) == {"skill", "kind", "scope"}
        and all(
            isinstance(row[key], str) and row[key] for key in ("skill", "kind", "scope")
        )
    }
    optional = {
        (row["skill"], row["kind"], row["scope"])
        for row in optional_rows
        if isinstance(row, dict)
        and set(row) == {"skill", "kind", "scope"}
        and all(
            isinstance(row[key], str) and row[key] for key in ("skill", "kind", "scope")
        )
    }
    if len(required) != len(required_rows) or len(optional) != len(optional_rows):
        return {"valid": False, "issues": [{"kind": "invalid_public_contract"}]}

    artifacts = index["artifacts"]
    routing = index["routing"]
    artifact_ids: set[str] = set()
    paths: set[str] = set()
    contracts: set[tuple[str, str, str]] = set()
    artifact_by_contract: dict[tuple[str, str, str], str] = {}
    artifact_total = 0
    for offset, row in enumerate(artifacts):
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "kind",
            "scope",
            "artifact_id",
            "path",
        }:
            issues.append({"kind": "invalid_artifact_row", "index": offset})
            continue
        if not all(
            isinstance(row.get(field), str) and row[field].strip() for field in row
        ):
            issues.append({"kind": "invalid_artifact_field", "index": offset})
            continue
        artifact_id = row["artifact_id"]
        relative = row["path"]
        identity = (row["skill"], row["kind"], row["scope"])
        if not _ARTIFACT_ID.fullmatch(artifact_id) or artifact_id in artifact_ids:
            issues.append({"kind": "invalid_or_duplicate_artifact_id", "index": offset})
            continue
        path = _safe_markdown(output_root, relative)
        if path is None:
            issues.append({"kind": "unsafe_or_missing_markdown", "path": relative})
            continue
        size = path.stat().st_size
        artifact_total += size
        if size > contract["max_artifact_file_bytes"]:
            issues.append({"kind": "artifact_too_large", "path": relative})
        if relative in paths:
            issues.append({"kind": "duplicate_artifact_path", "path": relative})
        if identity in contracts:
            issues.append({"kind": "duplicate_artifact_contract", "index": offset})
        artifact_ids.add(artifact_id)
        paths.add(relative)
        contracts.add(identity)
        artifact_by_contract[identity] = artifact_id
    if artifact_total > contract["max_artifact_total_bytes"]:
        issues.append({"kind": "artifacts_too_large_in_total"})
    for identity in sorted(required - contracts):
        issues.append({"kind": "required_artifact_missing", "contract": list(identity)})
    for identity in sorted(contracts - required - optional):
        issues.append(
            {"kind": "artifact_contract_not_published", "contract": list(identity)}
        )

    routes: dict[tuple[str, str], dict[str, Any]] = {}
    for offset, row in enumerate(routing):
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "scope",
            "status",
            "reason",
            "artifact_ids",
        }:
            issues.append({"kind": "invalid_routing_row", "index": offset})
            continue
        if (
            not isinstance(row.get("skill"), str)
            or not row["skill"].strip()
            or not isinstance(row.get("scope"), str)
            or not row["scope"].strip()
            or not isinstance(row.get("status"), str)
            or row["status"] not in _STATUSES
            or not isinstance(row.get("reason"), str)
            or not row["reason"].strip()
            or not isinstance(row.get("artifact_ids"), list)
            or any(not isinstance(item, str) for item in row["artifact_ids"])
            or len(set(row["artifact_ids"])) != len(row["artifact_ids"])
        ):
            issues.append({"kind": "invalid_routing_field", "index": offset})
            continue
        key = (row["skill"], row["scope"])
        if key in routes:
            issues.append({"kind": "duplicate_routing", "index": offset})
        if set(row["artifact_ids"]) - artifact_ids:
            issues.append({"kind": "unknown_artifact_reference", "index": offset})
        if row["status"] in {"executed", "reused"} and not row["artifact_ids"]:
            issues.append({"kind": "completed_route_without_artifact", "index": offset})
        routes[key] = row

    for skill, _kind, scope in required:
        if (skill, scope) not in routes:
            issues.append(
                {"kind": "required_routing_missing", "skill": skill, "scope": scope}
            )
    for identity, artifact_id in artifact_by_contract.items():
        route = routes.get((identity[0], identity[2]))
        if route is None or artifact_id not in route["artifact_ids"]:
            issues.append(
                {"kind": "artifact_not_linked_from_routing", "artifact_id": artifact_id}
            )

    unregistered = []
    for path in output_root.rglob("*.md"):
        relative = path.relative_to(output_root).as_posix()
        if relative.startswith(".runtime-evidence/"):
            continue
        if path.is_symlink() or relative not in paths:
            unregistered.append(relative)
    for relative in sorted(unregistered):
        issues.append({"kind": "unregistered_markdown", "path": relative})

    return {
        "valid": not issues,
        "issues": issues,
        "artifact_count": len(artifacts),
        "routing_count": len(routing),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the public artifact-index shape and file links."
    )
    parser.add_argument("--output-root", type=Path, default=Path(".qa-eval-output"))
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(".qa-eval-tools/artifact-index-contract.json"),
    )
    args = parser.parse_args(argv)
    result = validate(args.output_root, args.contract)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
