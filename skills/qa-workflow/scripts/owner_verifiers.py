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

Registered owners (7): test-item-analysis, test-condition-analysis,
e2e-test-selection, test-reporting, test-requirements-analysis,
test-architecture-design and test-management. For the three stored-artifact
Skills (requirements, architecture, management) the owner script must pass
``validate``, ``validate_readback`` (provider readback = canonical stored text),
``impact`` (``current``) and ``completion_check`` (``complete``). A current
source alone never completes a scope: the owner's ``completion_check`` must also
report complete.

Approval boundary: an approval is complete only when the owner's
``completion_check`` accepts it against the saved revision. The owner validators
report ``approval_authenticity: "not_established_by_this_validator"``; this module
records the same value in every verified record and never establishes who
approved. Approval evidence (architecture) and the source revisions are caller
supplied; they are not re-read from the approval authority or the source provider
here. The provider readback is likewise caller supplied and not authenticated.
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
        # owner側はexpected_revisionがNoneのときrevision比較を省略するため、
        # 検証入口で空・非文字列・nullを必ず拒否し、revision検査の迂回を塞ぐ。
        expected_revision = evidence["expected_revision"]
        if not isinstance(expected_revision, str) or not expected_revision.strip():
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
                "expected_revision": expected_revision,
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
            "artifact_revision": expected_revision,
            "content_hash": readback["storage_content_sha256"],
            "candidate_fingerprint": readback["candidate_fingerprint"],
        }

    return verify


def _verify_selection(scope: dict[str, Any]) -> dict[str, Any]:
    """e2e-test-selection: the owner validator, a stored-content hash match and the
    source currentness check (``impact``) against the current revisions.

    Evidence: ``stored_content`` (the exact stored text), the provider ``readback``
    (``revision`` and ``content_hash`` = SHA-256 of those bytes) and
    ``current_source_revisions`` (``ref -> revision``, supplied by the caller).
    The saved ``currentness`` self-declaration is never trusted: a saved source
    whose supplied revision differs or is absent (unknown) leaves the scope
    unverified. Only the saved source refs are compared, so a change to an
    unrelated source does not invalidate the selection.

    Limits: the current revisions are caller-supplied evidence, not read again
    from the source provider here, and the readback ``revision`` is not compared
    with anything. A fixture success is not a verified provider readback.
    """
    evidence = _evidence(scope)
    if set(evidence) != {"stored_content", "readback", "current_source_revisions"}:
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
    source = _run_owner(
        "e2e-test-selection/scripts/selection_contract.py",
        {
            "operation": "impact",
            "input": selection,
            "current_source_revisions": evidence["current_source_revisions"],
        },
    )
    if source.get("runtime_status") != "ok":
        raise VerificationFailed("owner_verification_schema_invalid")
    if source.get("result_status") == "unknown":
        raise VerificationFailed("source_revision_unknown")
    if source.get("result_status") != "current":
        raise VerificationFailed("source_not_current")
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


APPROVAL_AUTHENTICITY = "not_established_by_this_validator"
REVISION_MISMATCH_CODES = frozenset(
    {"readback_revision_mismatch", "expected_revision_mismatch"}
)
APPROVAL_CODE_PREFIXES = ("approval", "status_approval", "upstream_not_approved")
STORED_OWNER_KEYS = frozenset(
    {"stored_content", "readback", "expected_revision", "current_source_refs"}
)
RA_SCRIPT = "test-requirements-analysis/scripts/qa_requirement_runtime.py"
TA_SCRIPT = "test-architecture-design/scripts/architecture_runtime.py"
TM_SCRIPT = "test-management/scripts/management_runtime.py"


def _canonical_stored_json(value: Any, name: str) -> tuple[Any, str]:
    """Like ``_stored_json``, but the stored text must already be canonical JSON.

    The owner validators hash canonical JSON bytes (sorted keys, compact separators,
    UTF-8). A text in any other form can never match that hash, so it is refused
    with its own reason rather than reported as a generic readback mismatch.
    """
    parsed, digest = _stored_json(value, name)
    try:
        canonical = json.dumps(
            parsed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise VerificationFailed(f"{name}_not_canonical") from exc
    if canonical != value:
        raise VerificationFailed(f"{name}_not_canonical")
    return parsed, digest


def _expected_revision(evidence: dict[str, Any]) -> str:
    # owner側はexpected_revisionがNone/空のとき比較を省略・拒否の挙動が分かれるため、
    # 検証入口で非空の文字列だけを受け付ける（_verify_candidatesと同じ検査）。
    value = evidence["expected_revision"]
    if not isinstance(value, str) or not value.strip():
        raise VerificationFailed("owner_verification_schema_invalid")
    return value


def _issue_codes(result: dict[str, Any]) -> set[str]:
    issues = result.get("issues")
    if not isinstance(issues, list):
        return set()
    return {
        issue["code"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    }


def _stored_owner_artifact(
    evidence: dict[str, Any],
    target: str,
    script: str,
    keys: frozenset[str],
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    """Shared gate for a stored artifact validated by its owner script.

    Returns ``(artifact, stored sha256, expected revision, owner readback result)``.
    """
    if set(evidence) != keys:
        raise VerificationFailed("owner_verification_schema_invalid")
    expected_revision = _expected_revision(evidence)
    artifact, digest = _canonical_stored_json(
        evidence["stored_content"], "stored_content"
    )
    readback_claim = evidence["readback"]
    if not isinstance(readback_claim, dict) or (
        readback_claim.get("content_hash") != digest
    ):
        raise VerificationFailed("stored_artifact_readback_not_verified")
    if not isinstance(artifact, dict) or artifact.get("artifact_ref") != target:
        raise VerificationFailed("artifact_ref_differs_from_scope_target")
    structure = _run_owner(script, {"operation": "validate", "artifact": artifact})
    if structure.get("valid") is not True:
        raise VerificationFailed("owner_verification_schema_invalid")
    readback = _run_owner(
        script,
        {
            "operation": "validate_readback",
            "candidate_artifact": artifact,
            "readback": readback_claim,
            "expected_revision": expected_revision,
        },
    )
    if readback.get("valid") is not True or readback.get("status") != (
        "readback_matches"
    ):
        if _issue_codes(readback) & REVISION_MISMATCH_CODES:
            raise VerificationFailed("artifact_revision_mismatch")
        raise VerificationFailed("stored_artifact_readback_not_verified")
    return artifact, digest, expected_revision, readback


def _current_source_refs(evidence: dict[str, Any]) -> list[Any]:
    refs = evidence["current_source_refs"]
    if not isinstance(refs, list):
        raise VerificationFailed("owner_verification_schema_invalid")
    if not refs:
        # 取得不能（空）: current revisionが1件も与えられていないため unknown。
        raise VerificationFailed("source_revision_unknown")
    return refs


def _require_current(result: dict[str, Any]) -> None:
    """Owner ``impact`` must report ``current``; ``unknown`` is reported separately."""
    unknown = result.get("unknown_source_refs") or result.get("unknown_source_ids")
    if result.get("status") == "unknown" or unknown:
        raise VerificationFailed("source_revision_unknown")
    if result.get("valid") is not True:
        raise VerificationFailed("owner_verification_schema_invalid")
    if result.get("status") != "current":
        raise VerificationFailed("source_not_current")


def _require_complete(result: dict[str, Any]) -> None:
    """Owner ``completion_check`` must report ``complete``, independently of impact."""
    if result.get("complete") is True and result.get("status") == "complete":
        return
    codes = _issue_codes(result)
    # test-management reports its unresolved holds (including approval) under "open".
    open_holds = result.get("open")
    if isinstance(open_holds, dict):
        codes |= {code for code in open_holds if isinstance(code, str)}
    if any(code.startswith(APPROVAL_CODE_PREFIXES) for code in codes):
        raise VerificationFailed("approval_not_satisfied")
    raise VerificationFailed("completion_not_met")


def _stored_identity(
    artifact: dict[str, Any], digest: str, revision: str, **extra: Any
) -> dict[str, Any]:
    return {
        "artifact_ref": artifact["artifact_ref"],
        "artifact_revision": revision,
        "content_hash": digest,
        "approval_authenticity": APPROVAL_AUTHENTICITY,
        **extra,
    }


def _verify_requirements(scope: dict[str, Any]) -> dict[str, Any]:
    """test-requirements-analysis: stored QA requirement packet (qa_requirement_runtime.py).

    Evidence: ``stored_content``, ``readback``, ``expected_revision`` and
    ``current_source_refs``. The sources must be current (``impact``) and the packet
    must be complete (``completion_check``, which also covers open QA requirements,
    open items and the approval state of the packet itself).
    """
    evidence = _evidence(scope)
    artifact, digest, revision, _ = _stored_owner_artifact(
        evidence, scope["target"], RA_SCRIPT, STORED_OWNER_KEYS
    )
    refs = _current_source_refs(evidence)
    _require_current(
        _run_owner(
            RA_SCRIPT,
            {"operation": "impact", "artifact": artifact, "current_source_refs": refs},
        )
    )
    _require_complete(
        _run_owner(
            RA_SCRIPT,
            {
                "operation": "completion_check",
                "artifact": artifact,
                "current_source_refs": refs,
            },
        )
    )
    return _stored_identity(artifact, digest, revision)


def _verify_architecture(scope: dict[str, Any]) -> dict[str, Any]:
    """test-architecture-design: stored assignment packet (architecture_runtime.py).

    Evidence adds ``approval_evidence`` (supplied outside the packet). Approvals are
    accepted only when bound to the saved revision (``expected_revision``) and the
    packet's ``content_fingerprint``; the owner's ``completion_check`` decides this.
    """
    evidence = _evidence(scope)
    keys = STORED_OWNER_KEYS | {"approval_evidence"}
    artifact, digest, revision, readback = _stored_owner_artifact(
        evidence, scope["target"], TA_SCRIPT, keys
    )
    refs = _current_source_refs(evidence)
    _require_current(
        _run_owner(
            TA_SCRIPT,
            {"operation": "impact", "artifact": artifact, "current_source_refs": refs},
        )
    )
    approvals = evidence["approval_evidence"]
    if not isinstance(approvals, list):
        raise VerificationFailed("owner_verification_schema_invalid")
    _require_complete(
        _run_owner(
            TA_SCRIPT,
            {
                "operation": "completion_check",
                "artifact": artifact,
                "expected_revision": revision,
                "approval_evidence": approvals,
            },
        )
    )
    return _stored_identity(
        artifact,
        digest,
        revision,
        candidate_fingerprint=readback.get("candidate_fingerprint"),
    )


def _verify_management(scope: dict[str, Any]) -> dict[str, Any]:
    """test-management: stored plan packet (management_runtime.py).

    Evidence: ``stored_content``, ``readback``, ``expected_revision`` and
    ``current_source_refs`` (source identity with revision and hash; source ids are
    not accepted). The stored monitoring snapshot must match a recount, the sources
    must be current, and the plan must be complete (acquisition, execution, criteria,
    risks, approval state).
    """
    evidence = _evidence(scope)
    artifact, digest, revision, _ = _stored_owner_artifact(
        evidence, scope["target"], TM_SCRIPT, STORED_OWNER_KEYS
    )
    refs = _current_source_refs(evidence)
    snapshot = _run_owner(
        TM_SCRIPT, {"operation": "build_snapshot", "artifact": artifact}
    )
    if snapshot.get("matches_stored") is False:
        raise VerificationFailed("monitoring_snapshot_mismatch")
    _require_current(
        _run_owner(
            TM_SCRIPT,
            {"operation": "impact", "artifact": artifact, "current_source_refs": refs},
        )
    )
    _require_complete(
        _run_owner(TM_SCRIPT, {"operation": "completion_check", "artifact": artifact})
    )
    return _stored_identity(artifact, digest, revision)


VERIFIERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "test-item-analysis": _verify_candidates(
        "test-item-analysis/scripts/item_candidates.py"
    ),
    "test-condition-analysis": _verify_candidates(
        "test-condition-analysis/scripts/condition_candidates.py"
    ),
    "e2e-test-selection": _verify_selection,
    "test-reporting": _verify_report,
    "test-requirements-analysis": _verify_requirements,
    "test-architecture-design": _verify_architecture,
    "test-management": _verify_management,
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
