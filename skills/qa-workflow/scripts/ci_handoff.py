"""Fail-closed, deterministic handoff integrity gate for a selected product CI.

The expected document must come from the product CI's trusted source enumeration
and artifact/approval provider, never from the candidate Agent output.
Passing this gate does not certify semantic QA quality or authenticated approvals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "qa-ci-handoff-v1"
DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("JSON input is missing or too large")
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"unsupported JSON number: {token}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields are invalid")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _path(value: Any) -> str:
    raw = _string(value, "path")
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or len(path.parts) == 0
        or any(part in {".", ".."} for part in raw.split("/"))
        or "\\" in raw
        or ":" in path.parts[0]
        or "\x00" in raw
    ):
        raise ValueError("unsafe relative artifact path")
    return raw


def _refs(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    results: dict[str, str] = {}
    for index, row in enumerate(value):
        record = _object(row, {"ref", "revision"}, f"{label}[{index}]")
        ref = _string(record["ref"], "source ref")
        revision = _string(record["revision"], "source revision")
        if ref in results:
            raise ValueError(f"duplicate source ref: {ref}")
        results[ref] = revision
    return results


def _source(value: Any) -> dict[str, str]:
    row = _object(value, {"repository", "base_sha", "head_sha", "build_ref"}, "source")
    result = {key: _string(item, f"source.{key}") for key, item in row.items()}
    if not GIT_SHA.fullmatch(result["base_sha"]) or not GIT_SHA.fullmatch(
        result["head_sha"]
    ):
        raise ValueError("source commit must be a full SHA")
    return result


def _artifacts(
    value: Any, *, expected: bool
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("artifacts must be a list")
    keys = {
        "owner",
        "scope",
        "artifact_ref",
        "revision",
        "sha256",
        "source_refs",
    }
    if not expected:
        keys = keys | {"path"}
    mapped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _object(raw, keys, f"artifact[{index}]")
        identity = tuple(
            _string(row[key], f"artifact.{key}")
            for key in ("owner", "scope", "artifact_ref")
        )
        if identity in mapped:
            raise ValueError(f"duplicate artifact identity: {identity}")
        _string(row["revision"], "artifact revision")
        if not isinstance(row["sha256"], str) or not DIGEST.fullmatch(row["sha256"]):
            raise ValueError("artifact sha256 must be a full sha256 digest")
        if not expected:
            _path(row["path"])
        _refs(row["source_refs"], "artifact source_refs")
        mapped[identity] = row
    return mapped


def _issues_add(issues: list[dict[str, str]], code: str, target: str) -> None:
    issues.append({"code": code, "target": target})


def _read_artifact(root: Path, relative: str) -> bytes:
    current = root
    for part in PurePosixPath(_path(relative)).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink artifact path is not allowed")
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise ValueError("artifact missing or outside trusted root")
    if current.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("artifact exceeds size limit")
    return current.read_bytes()


def verify(
    expected: dict[str, Any], manifest: dict[str, Any], artifacts_root: Path
) -> dict[str, Any]:
    """Compare untrusted handoff with a separately obtained, trusted CI snapshot."""
    _object(
        expected,
        {
            "schema_version",
            "source",
            "source_inventory",
            "changed_paths",
            "allowed_classifications",
            "artifacts",
            "required_approvals",
        },
        "expected",
    )
    _object(
        manifest,
        {
            "schema_version",
            "source",
            "source_inventory",
            "changes",
            "artifacts",
        },
        "manifest",
    )
    if expected["schema_version"] != SCHEMA or manifest["schema_version"] != SCHEMA:
        raise ValueError("unsupported handoff schema")
    required_source = _source(expected["source"])
    actual_source = _source(manifest["source"])
    required_inventory = _refs(expected["source_inventory"], "expected inventory")
    if not required_inventory:
        raise ValueError("trusted source inventory is empty")
    inventory = _object(
        manifest["source_inventory"], {"complete", "entries"}, "source_inventory"
    )
    if not isinstance(inventory["complete"], bool):
        raise ValueError("inventory completeness must be boolean")
    actual_inventory = _refs(inventory["entries"], "manifest inventory")
    changed_paths = expected["changed_paths"]
    if not isinstance(changed_paths, list):
        raise ValueError("changed_paths must be a list")
    paths = [_path(item) for item in changed_paths]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate expected changed path")
    allowed = expected["allowed_classifications"]
    if (
        not isinstance(allowed, list)
        or not allowed
        or any(not isinstance(value, str) or not value.strip() for value in allowed)
        or len(set(allowed)) != len(allowed)
    ):
        raise ValueError("trusted classification policy is missing or invalid")
    changes = manifest["changes"]
    if not isinstance(changes, list):
        raise ValueError("changes must be a list")
    actual_changes: dict[str, str] = {}
    for item in changes:
        record = _object(item, {"path", "classification"}, "change")
        path = _path(record["path"])
        classification = _string(record["classification"], "classification")
        if path in actual_changes:
            raise ValueError(f"duplicate change path: {path}")
        actual_changes[path] = classification
    expected_artifacts = _artifacts(expected["artifacts"], expected=True)
    actual_artifacts = _artifacts(manifest["artifacts"], expected=False)
    approvals = expected["required_approvals"]
    if (
        not isinstance(approvals, list)
        or any(not isinstance(value, str) or not value.strip() for value in approvals)
        or len(set(approvals)) != len(approvals)
    ):
        raise ValueError("invalid required approvals")

    issues: list[dict[str, str]] = []
    verified: list[dict[str, str]] = []
    if actual_source != required_source:
        _issues_add(issues, "source_revision_mismatch", "source")
    if not inventory["complete"] or actual_inventory != required_inventory:
        _issues_add(issues, "source_inventory_incomplete", "source_inventory")
    for path in sorted(set(paths) - set(actual_changes)):
        _issues_add(issues, "unclassified_change", path)
    for path in sorted(set(actual_changes) - set(paths)):
        _issues_add(issues, "unexpected_change", path)
    for path, classification in sorted(actual_changes.items()):
        if classification not in allowed:
            _issues_add(issues, "unclassified_change", path)

    for identity in sorted(set(expected_artifacts) - set(actual_artifacts)):
        _issues_add(issues, "missing_artifact", "/".join(identity))
    for identity in sorted(set(actual_artifacts) - set(expected_artifacts)):
        _issues_add(issues, "unexpected_artifact", "/".join(identity))
    for identity in sorted(set(expected_artifacts) & set(actual_artifacts)):
        required = expected_artifacts[identity]
        actual = actual_artifacts[identity]
        label = "/".join(identity)
        if any(
            required[field] != actual[field] for field in ("revision", "sha256")
        ) or _refs(required["source_refs"], label) != _refs(
            actual["source_refs"], label
        ):
            _issues_add(issues, "artifact_revision_mismatch", label)
            continue
        if any(
            required_inventory.get(ref) != revision
            for ref, revision in _refs(actual["source_refs"], label).items()
        ):
            _issues_add(issues, "stale_artifact_source", label)
            continue
        try:
            content = _read_artifact(artifacts_root, actual["path"])
        except (OSError, ValueError):
            _issues_add(issues, "artifact_readback_failed", label)
            continue
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        if digest != required["sha256"]:
            _issues_add(issues, "artifact_hash_mismatch", label)
            continue
        verified.append(
            {
                "owner": identity[0],
                "scope": identity[1],
                "artifact_ref": identity[2],
                "revision": required["revision"],
                "sha256": digest,
            }
        )
    if approvals:
        for approval in approvals:
            _issues_add(issues, "approval_provider_unconfigured", approval)
    if approvals:
        status = "blocked"
    elif issues:
        status = "fail"
    else:
        status = "pass"
    return {
        "schema_version": "qa-ci-handoff-verification-v1",
        "status": status,
        "issues": issues,
        "verified_artifacts": verified,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify(
            _read_json(args.expected), _read_json(args.manifest), args.artifacts_root
        )
    except (OSError, UnicodeError, ValueError) as exc:
        report = {
            "schema_version": "qa-ci-handoff-verification-v1",
            "status": "blocked",
            "issues": [{"code": "invalid_handoff_input", "target": str(exc)}],
            "verified_artifacts": [],
        }
        exit_code = 2
    else:
        exit_code = 0 if report["status"] == "pass" else 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
