"""Owner verifier registry for qa-workflow completion (Plan 04 section 1).

A Skill without runtime-v2 roots can complete a workflow scope only when its
*owner's own production CLI* verifies the stored artifact. This module registers
those verification entry points. It never judges process semantics itself.
The evidence (the stored text and its readback) is supplied by the caller; this
module does not read the storage provider again to confirm it. Each registered
verifier checks that the supplied text's hash matches the readback, runs the
owner's script as a subprocess (JSON on stdin, JSON on stdout) to validate the
readback and the identity the scope claims, and checks source currentness where
the registration defines it. A self-declared "verified" value is not enough: the
owner's validator must pass. Producing the readback from the store is the
caller's responsibility (store side). A missing script, a failing command,
unparsable output or any mismatch leaves the scope unverified.

Registered owners are only those with a deterministic production entry point that
can verify a stored artifact or recompute it from its inputs. Owners without one
(for example Markdown-only Skills) stay unregistered and block completion.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SKILLS_ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
NOT_REGISTERED = "owner_verifier_not_registered"


class VerificationFailed(Exception):
    """The owner could not verify the scope; ``reason`` is a stable code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _stored_json(value: Any, name: str) -> tuple[Any, str]:
    """Parse a stored text and return ``(value, sha256 of its exact UTF-8 bytes)``.

    The runtime canonicalizes (and reorders) every structured input before a
    handler sees it, which would change the bytes a provider hashed. Evidence that
    is hashed by the provider is therefore carried as the exact stored text.
    """
    if not isinstance(value, str) or not value.strip():
        raise VerificationFailed(f"{name}_must_be_the_stored_text")
    try:
        parsed = json.loads(value)
    except ValueError as exc:
        raise VerificationFailed(f"{name}_is_not_json") from exc
    return parsed, hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact(value: Any) -> Any:
    normalized = getattr(value, "normalized", None)
    if callable(normalized):
        return normalized()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _run_owner(
    relative_script: str, request: Any, args: tuple[str, ...] = ()
) -> dict[str, Any]:
    script = SKILLS_ROOT / relative_script
    if not script.is_file():
        raise VerificationFailed("owner_verifier_unavailable")
    try:
        completed = subprocess.run(
            [sys.executable, str(script), *args],
            input=json.dumps(request, ensure_ascii=False, default=_exact).encode(
                "utf-8"
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationFailed("owner_verifier_unavailable") from exc
    if completed.returncode != 0 or len(completed.stdout) > MAX_OUTPUT_BYTES:
        raise VerificationFailed("owner_verifier_failed")
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise VerificationFailed("owner_verifier_output_invalid") from exc
    if not isinstance(result, dict):
        raise VerificationFailed("owner_verifier_output_invalid")
    return result


def _evidence(scope: dict[str, Any]) -> dict[str, Any]:
    value = scope["normalized_input"].get("owner_verification")
    if not isinstance(value, dict):
        raise VerificationFailed("owner_verification_missing")
    if not isinstance(scope.get("target"), str) or not scope["target"].strip():
        raise VerificationFailed("scope_target_required")
    return value


def _verify_candidates(script: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """test-item-analysis / test-condition-analysis candidate artifacts.

    Evidence: ``stored_content`` (the exact stored text), the provider ``readback``,
    the expected saved ``expected_revision`` and ``current_source_refs``. The
    provider hash must match the stored bytes, the owner validator must accept
    them, and the sources must be current.
    """

    def verify(scope: dict[str, Any]) -> dict[str, Any]:
        evidence = _evidence(scope)
        if set(evidence) != {
            "stored_content",
            "readback",
            "expected_revision",
            "current_source_refs",
        }:
            raise VerificationFailed("owner_verification_schema_invalid")
        artifact, stored_sha = _stored_json(
            evidence["stored_content"], "stored_content"
        )
        readback_claim = evidence["readback"]
        if not isinstance(readback_claim, dict) or (
            readback_claim.get("content_hash") != stored_sha
        ):
            raise VerificationFailed("stored_artifact_readback_not_verified")
        if (
            not isinstance(artifact, dict)
            or artifact.get("artifact_ref") != (scope["target"])
        ):
            raise VerificationFailed("artifact_ref_differs_from_scope_target")
        readback = _run_owner(
            script,
            {
                "operation": "validate_readback",
                "candidate_artifact": artifact,
                "readback": evidence["readback"],
                "expected_revision": evidence["expected_revision"],
            },
        )
        if readback.get("valid") is not True or readback.get("status") != (
            "readback_matches"
        ):
            raise VerificationFailed("stored_artifact_readback_not_verified")
        impact = _run_owner(
            script,
            {
                "operation": "impact",
                "artifact": artifact,
                "current_source_refs": evidence["current_source_refs"],
            },
        )
        if impact.get("valid") is not True or impact.get("status") != "current":
            raise VerificationFailed("source_not_current")
        return {
            "artifact_ref": artifact["artifact_ref"],
            "artifact_revision": evidence["expected_revision"],
            "content_hash": readback["storage_content_sha256"],
            "candidate_fingerprint": readback["candidate_fingerprint"],
        }

    return verify


def _verify_selection(scope: dict[str, Any]) -> dict[str, Any]:
    """e2e-test-selection: the owner validator plus a stored-content hash match.

    Evidence: ``stored_content`` (the exact stored text) and the provider
    ``readback`` (``revision`` and ``content_hash`` = SHA-256 of those bytes).
    """
    evidence = _evidence(scope)
    if set(evidence) != {"stored_content", "readback"}:
        raise VerificationFailed("owner_verification_schema_invalid")
    selection, digest = _stored_json(evidence["stored_content"], "stored_content")
    readback = evidence["readback"]
    if (
        not isinstance(selection, dict)
        or not isinstance(readback, dict)
        or set(readback) != {"revision", "content_hash"}
    ):
        raise VerificationFailed("owner_verification_schema_invalid")
    if selection.get("selection_ref") != scope["target"]:
        raise VerificationFailed("artifact_ref_differs_from_scope_target")
    if readback["content_hash"] != digest:
        raise VerificationFailed("stored_artifact_readback_not_verified")
    envelope = _run_owner(
        "e2e-test-selection/scripts/selection_contract.py", {"input": selection}
    )
    if envelope.get("runtime_status") != "ok" or envelope.get("result_status") != (
        "ready"
    ):
        raise VerificationFailed("selection_not_ready")
    if readback["content_hash"] != digest:
        raise VerificationFailed("stored_artifact_readback_not_verified")
    return {
        "artifact_ref": selection["selection_ref"],
        "artifact_revision": readback["revision"],
        "content_hash": digest,
    }


def _verify_report(scope: dict[str, Any]) -> dict[str, Any]:
    """test-reporting: recompute the snapshot from its inputs and compare.

    Evidence: ``build_input_content`` and ``stored_snapshot_content`` (exact texts)
    and ``current`` (plan and source revisions now). The stored snapshot must
    equal the recomputed one, be complete and be current.
    """
    evidence = _evidence(scope)
    if set(evidence) != {"build_input_content", "stored_snapshot_content", "current"}:
        raise VerificationFailed("owner_verification_schema_invalid")
    build_input, _ = _stored_json(evidence["build_input_content"], "build_input")
    stored, stored_sha = _stored_json(
        evidence["stored_snapshot_content"], "stored_snapshot"
    )
    if not isinstance(stored, dict) or stored.get("snapshot_ref") != scope["target"]:
        raise VerificationFailed("artifact_ref_differs_from_scope_target")
    script = "test-reporting/scripts/reporting_runtime.py"
    recomputed = _run_owner(script, build_input, ("build-snapshot",))
    if recomputed != stored:
        raise VerificationFailed("stored_snapshot_differs_from_recomputed")
    if (recomputed.get("overall") or {}).get("complete") is not True:
        raise VerificationFailed("snapshot_not_complete")
    currentness = _run_owner(
        script,
        {"snapshot": stored, "current": evidence["current"]},
        ("check-currentness",),
    )
    if currentness.get("status") != "current":
        raise VerificationFailed("snapshot_not_current")
    return {
        "artifact_ref": stored["snapshot_ref"],
        "artifact_revision": stored.get("plan_revision"),
        "content_hash": stored_sha,
    }


VERIFIERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "test-item-analysis": _verify_candidates(
        "test-item-analysis/scripts/item_candidates.py"
    ),
    "test-condition-analysis": _verify_candidates(
        "test-condition-analysis/scripts/condition_candidates.py"
    ),
    "e2e-test-selection": _verify_selection,
    "test-reporting": _verify_report,
}


def verify(skill: str, scope: dict[str, Any]) -> dict[str, Any]:
    """Return ``{"status": "verified", "record": ...}`` or ``{"status": "unverified",
    "reason": ...}``. Never raises for an owner failure."""
    verifier = VERIFIERS.get(skill)
    if verifier is None:
        return {"status": "unverified", "reason": NOT_REGISTERED}
    try:
        identity = verifier(scope)
    except VerificationFailed as exc:
        return {"status": "unverified", "reason": exc.reason}
    except (KeyError, TypeError, ValueError):
        return {"status": "unverified", "reason": "owner_verification_schema_invalid"}
    return {
        "status": "verified",
        "record": {
            "skill": skill,
            "target": scope["target"],
            "execution_range": scope["execution_range"],
            "verified_artifact": identity,
        },
    }
