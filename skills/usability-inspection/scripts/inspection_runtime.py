"""Usability inspection runtime entry point for fixed artifact/probe contracts."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import criterion_checks
import inspection_structure
import measurement
import observation_contract
from runtime_contract import InvalidInput, reject_unknown, run_cli, static_data_fingerprint


SKILL = "usability-inspection"
GENERATOR = "inspection_runtime"
GENERATOR_CONTRACT_VERSION = "usability-inspection-runtime-v2"
SCRIPT_PATH = Path(__file__).resolve()
ASSETS = PACKAGE / "assets"
FORMAL_OPERATIONS = {"validate-wcag-machine-probe-request", "normalize-wcag-machine-probe-result"}
OPERATIONS = {
    "scope-skeleton", "materialize-refs", "close-scope", "finding-requirement",
    "validate-formal-handoff", "validate-predicate", "validate-resolver", "materialize-targets",
    "normalize-target-resolution", "plan-probes", "normalize-observation-probe-result",
    "validate-wcag-machine-probe-request", "normalize-wcag-machine-probe-result",
    "materialize-additional-request", "close-additional-request", "run-supported-rule",
    "requirement-result", "viewport-overflow", "target-geometry", "contrast-ratio",
    "interaction-elapsed-ms", "threshold-result",
}


def _static_versions(*, formal: bool) -> dict[str, str]:
    result = {
        "browser_observation_catalog": static_data_fingerprint(ASSETS / "browser-observation-catalog.json"),
        "test_rule_catalog": static_data_fingerprint(ASSETS / "test-rule-catalog.json"),
    }
    if formal:
        result["wcag_machine_probes"] = static_data_fingerprint(ASSETS / "wcag-machine-probe-catalog.json")
    return result


def _dispatch(operation: str, args: dict[str, Any]) -> Any:
    if operation == "scope-skeleton": return inspection_structure.scope_skeleton(**args)
    if operation == "materialize-refs": return inspection_structure.materialize_refs(**args)
    if operation == "close-scope": return inspection_structure.close_scope(**args)
    if operation == "finding-requirement": return {"required": inspection_structure.finding_requirement(**args)}
    if operation == "validate-formal-handoff": return inspection_structure.validate_formal_handoff(args["request"])
    if operation == "validate-predicate": return observation_contract.validate_predicate(args["predicate"])
    if operation == "validate-resolver":
        observation_contract.validate_resolver(args["resolver_kind"], args["resolver_payload"])
        return {"valid": True}
    if operation == "materialize-targets": return observation_contract.materialize_targets(**args)
    if operation == "normalize-target-resolution": return observation_contract.normalize_target_resolution(**args)
    if operation == "plan-probes": return observation_contract.plan_probes(**args)
    if operation == "normalize-observation-probe-result":
        if set(args) != {"probe", "result", "current_document_identity"}:
            raise InvalidInput("general observation result arguments do not match the fixed schema")
        return observation_contract.normalize_probe_result(
            probe=args["probe"], result=args["result"],
            current_document_identity=args["current_document_identity"], formal=False)
    if operation == "validate-wcag-machine-probe-request":
        if set(args) != {"request"}:
            raise InvalidInput("formal request arguments do not match the fixed schema")
        return observation_contract.validate_formal_probe_request(args["request"])
    if operation == "normalize-wcag-machine-probe-result":
        if set(args) != {"request", "result", "current_document_identity"}:
            raise InvalidInput("formal result arguments do not match the fixed schema")
        observation_contract.validate_formal_probe_request(args["request"])
        return observation_contract.normalize_probe_result(
            probe={}, result=args["result"], current_document_identity=args["current_document_identity"],
            formal=True, formal_request=args["request"])
    if operation == "materialize-additional-request": return observation_contract.materialize_additional(**args)
    if operation == "close-additional-request": return observation_contract.close_additional_request(**args)
    if operation == "run-supported-rule": return criterion_checks.run_supported_rule(**args)
    if operation == "requirement-result": return {"result": criterion_checks.requirement_result(**args)}
    if operation == "viewport-overflow": return measurement.viewport_overflow(args["metrics"])
    if operation == "target-geometry": return measurement.target_geometry(args["box"])
    if operation == "contrast-ratio": return {"contrast_ratio": str(measurement.contrast_ratio(args["luminance_a"], args["luminance_b"]))}
    if operation == "interaction-elapsed-ms":
        return {"result": measurement.interaction_elapsed_ms(**args)}
    if operation == "threshold-result": return {"result": measurement.threshold_result(**args)}
    raise InvalidInput("unsupported inspection runtime operation")


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_key"] is not None or metadata["scope_key"] not in {"all", "scoped"}:
        raise InvalidInput("inspection runtime metadata is invalid")
    reject_unknown(input_value, {"operation", "arguments"})
    operation, arguments = input_value.get("operation"), input_value.get("arguments")
    if operation not in OPERATIONS or not isinstance(arguments, dict):
        raise InvalidInput("inspection runtime operation and arguments are invalid")
    formal = operation in FORMAL_OPERATIONS
    expected_unit = "artifact:inspection_runtime:formal-machine-probe" if formal else f"artifact:inspection_runtime:{metadata['scope_key']}"
    if metadata["runtime_unit_key"] != expected_unit:
        raise InvalidInput("inspection runtime unit does not match its fixed operation scope")
    try:
        output = _dispatch(operation, arguments)
    except InvalidInput:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInput(f"inspection operation contract rejected input: {exc}") from exc
    state = output.get("status") if isinstance(output, dict) else None
    completeness = output.get("value", {}).get("observation_completeness") if isinstance(output, dict) and isinstance(output.get("value"), dict) else None
    partial_observation = (isinstance(completeness, dict) and completeness.get("state") == "partial"
                           and completeness.get("reason") in observation_contract.PARTIAL_FORMAL_OBSERVATION_REASONS)
    if operation == "normalize-target-resolution" and state != "unique":
        result_status, support_status = "unresolved", "partial"
    elif (operation == "normalize-wcag-machine-probe-result"
          and state in {"unsupported", "unavailable", "incomplete"}
          and output.get("limitation_code") in observation_contract.LIMITATION_CODES):
        # A catalogued machine limitation is a completed observation. The formal
        # procedure owner decides whether its conditional manual fallback closes.
        result_status, support_status = "ready", "supported"
    elif (operation == "normalize-wcag-machine-probe-result" and state == "incomplete"
          and partial_observation):
        # A current, typed partial observation is evidence for semantic closure,
        # not a machine failure or a WCAG failure. The formal owner must preserve
        # its limitation and close the criterion as undetermined or re-observe.
        result_status, support_status = "ready", "partial"
    elif operation == "normalize-wcag-machine-probe-result" and state in {
        "blocked", "unsupported", "unavailable", "incomplete"
    }:
        result_status, support_status = "blocked", "unsupported"
    elif state in {"blocked", "unsupported"}:
        result_status, support_status = "blocked", "unsupported"
    elif state in {"requested", "in-progress", "stale", "ambiguous", "missing", "no-progress"}:
        result_status, support_status = "unresolved", "partial"
    else:
        result_status, support_status = "ready", "supported"
    partial_result = (operation == "normalize-wcag-machine-probe-result" and state == "incomplete"
                      and result_status == "ready" and support_status == "partial" and partial_observation)
    issues = ([{"issue_type": "wcag_machine_observation_incomplete", "blocking": False,
                "operation": operation, "status": state,
                "reason": completeness["reason"]}]
              if partial_result else [] if result_status == "ready" else [{"issue_type": "inspection_operation_not_closed", "blocking": True,
        "operation": operation, "status": state or result_status}])
    return {"runtime_status": "ok", "support_status": support_status, "result_status": result_status,
            "runtime_required": True, "deterministic_generated": True, "static_data_versions": _static_versions(formal=formal),
            "payload": {"operation": operation, "result": output}, "issues": issues}


if __name__ == "__main__":
    raise SystemExit(run_cli(handler, skill=SKILL, generator=GENERATOR,
        generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH, aggregate=True))
