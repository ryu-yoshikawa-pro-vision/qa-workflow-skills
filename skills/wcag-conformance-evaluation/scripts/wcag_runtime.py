"""WCAG-EM production runtime entry point over this Skill's fixed helpers."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from earl_report import EarlError, serialize_assertions
from runtime_contract import InvalidInput, reject_unknown, run_cli, static_data_fingerprint
from sampling import (SamplingError, compare_samples, evaluate_step_4_2_reuse, materialize_processes,
                      materialize_sample_lineage, random_target_count, reconcile_sampling_revision, sample_identity_registry,
                      validate_random_selection)
from wcag_criterion_plan import (CriterionPlanError, close_criterion, materialize_plan,
                                 materialize_sample_results)
from wcag_em_structure import (close_report, conformance_claim, evaluation_statement,
                               initialize_evaluation, materialize_additional_requirements,
                               materialize_conformance_requirement_results, materialize_variations,
                               close_conforming_alternate_version, render_machine_owned_report, statement_of_partial_conformance,
                               validate_sampling_skip, extend_accessibility_support_baseline, materialize_scope_coverage,
                               allocate_observation_handoff_ref,
                               EvaluationStructureError)


SKILL = "wcag-conformance-evaluation"
GENERATOR = "wcag_runtime"
GENERATOR_CONTRACT_VERSION = "wcag-em-runtime-v1"
SCRIPT_PATH = Path(__file__).resolve()
ASSETS = SCRIPT_DIR.parent / "assets"
OPERATIONS = {
    "initialize-evaluation", "materialize-additional-requirements", "materialize-variations",
    "allocate-observation-handoff-ref",
    "close-conforming-alternate-version", "materialize-conformance-requirement-results",
    "extend-accessibility-support-baseline",
    "materialize-scope-coverage", "materialize-complete-processes", "evaluate-step-4-2-reuse",
    "reconcile-sampling-revision",
    "materialize-sample-identities", "materialize-sample-lineage", "validate-sampling-skip", "random-target-count",
    "validate-random-selection", "compare-samples", "materialize-criterion-plan",
    "close-criterion", "materialize-sample-results", "close-report", "evaluation-statement",
    "conformance-claim", "statement-of-partial-conformance", "render-machine-owned-report", "serialize-earl",
}


def _static_versions() -> dict[str, str]:
    result = {f"wcag_requirements_{version.replace('.', '_')}":
             static_data_fingerprint(ASSETS / f"wcag-{version}-requirements.json")
             for version in ("2.0", "2.1", "2.2")}
    result["wcag_evaluation_procedures"] = static_data_fingerprint(ASSETS / "wcag-evaluation-procedure-catalog.json")
    result["wcag_semantic_contracts"] = static_data_fingerprint(ASSETS / "wcag-semantic-contracts.json")
    return result


def _dispatch(operation: str, args: dict[str, Any]) -> Any:
    if operation == "initialize-evaluation":
        return initialize_evaluation(args)
    if operation == "materialize-additional-requirements":
        return materialize_additional_requirements(args["drafts"])
    if operation == "allocate-observation-handoff-ref":
        return allocate_observation_handoff_ref(args.get("existing_handoffs"))
    if operation == "materialize-variations":
        return materialize_variations(args["samples"], args["drafts"])
    if operation == "close-conforming-alternate-version":
        return close_conforming_alternate_version(**args)
    if operation == "materialize-conformance-requirement-results":
        return materialize_conformance_requirement_results(**args)
    if operation == "extend-accessibility-support-baseline":
        return extend_accessibility_support_baseline(**args)
    if operation == "materialize-scope-coverage":
        return materialize_scope_coverage(args["drafts"])
    if operation == "materialize-complete-processes":
        return materialize_processes(**args)
    if operation == "evaluate-step-4-2-reuse":
        return evaluate_step_4_2_reuse(**args)
    if operation == "reconcile-sampling-revision":
        return reconcile_sampling_revision(**args)
    if operation == "materialize-sample-identities":
        return sample_identity_registry(args["drafts"])
    if operation == "materialize-sample-lineage":
        return materialize_sample_lineage(**args)
    if operation == "validate-sampling-skip":
        return validate_sampling_skip(**args)
    if operation == "random-target-count":
        return {"target_count": random_target_count(args["structured_count"])}
    if operation == "validate-random-selection":
        return validate_random_selection(**args)
    if operation == "compare-samples":
        return compare_samples(**args)
    if operation == "materialize-criterion-plan":
        return materialize_plan(**args)
    if operation == "close-criterion":
        return close_criterion(**args)
    if operation == "materialize-sample-results":
        current_refs = args.get("current_criterion_evaluation_refs")
        if (not isinstance(current_refs, list)
                or any(not isinstance(ref, str) or not ref.strip() for ref in current_refs)
                or len(current_refs) != len(set(current_refs))):
            raise InvalidInput("current criterion evaluation refs must be a unique JSON ref array")
        normalized = {**args, "current_criterion_evaluation_refs": set(current_refs)}
        try:
            return materialize_sample_results(**normalized)
        except CriterionPlanError as exc:
            raise InvalidInput(str(exc)) from exc
    if operation == "close-report":
        return close_report(**args)
    if operation == "evaluation-statement":
        return evaluation_statement(**args)
    if operation == "conformance-claim":
        return conformance_claim(**args)
    if operation == "statement-of-partial-conformance":
        return statement_of_partial_conformance(**args)
    if operation == "render-machine-owned-report":
        return render_machine_owned_report(args["data"])
    if operation == "serialize-earl":
        return {"earl_jsonld_utf8": serialize_assertions(**args).decode("utf-8")}
    raise InvalidInput("unsupported WCAG runtime operation")


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != "artifact:wcag_runtime:all" or metadata["scope_key"] != "all":
        raise InvalidInput("WCAG runtime metadata is invalid")
    reject_unknown(input_value, {"operation", "arguments"})
    operation = input_value.get("operation")
    arguments = input_value.get("arguments")
    if operation not in OPERATIONS or not isinstance(arguments, dict):
        raise InvalidInput("WCAG runtime operation and arguments are invalid")
    procedure_rows = arguments.get("result", {}).get("procedure_executions", []) if operation == "close-criterion" else []
    procedure_results = arguments.get("procedure_results", {}) if operation == "close-criterion" else {}
    machine_completed = any(row.get("procedure_kind") == "machine" and
        procedure_results.get(row.get("procedure_execution_ref"), {}).get("status") == "complete"
        for row in procedure_rows)
    inspection_dependencies = [row for row in metadata["upstream_runtime_units"]
        if row["skill"] == "usability-inspection" and row["runtime_unit_key"] == "artifact:inspection_runtime:formal-machine-probe"]
    if machine_completed and len(inspection_dependencies) != 1:
        raise InvalidInput("formal machine result requires exactly one current inspection runtime dependency")
    if "wcag_machine_probes" in _static_versions():
        raise InvalidInput("formal static data must not duplicate the inspection machine-probe hash")
    try:
        output = _dispatch(operation, arguments)
    except (CriterionPlanError, EarlError, EvaluationStructureError, SamplingError) as exc:
        raise InvalidInput(str(exc)) from exc
    if operation == "close-criterion":
        status = output.get("execution_status")
    elif operation == "validate-random-selection":
        status = output.get("selection_status")
    elif operation == "close-report":
        status = output.get("status")
    elif operation in {"initialize-evaluation", "materialize-criterion-plan", "materialize-conformance-requirement-results",
                       "extend-accessibility-support-baseline", "materialize-scope-coverage",
                       "materialize-complete-processes", "evaluate-step-4-2-reuse", "reconcile-sampling-revision"}:
        status = output.get("status")
    elif operation in {"evaluation-statement", "conformance-claim", "statement-of-partial-conformance"}:
        status = output.get("status")
    else:
        status = None
    if status in {"unsupported", "unresolved", "blocked", "in-progress", "selection-required", "selection-incomplete", "not-generated"}:
        result_status = "blocked" if status in {"blocked", "unsupported"} else "unresolved"
        support_status = "partial" if result_status == "unresolved" else "unsupported"
    else:
        result_status, support_status = "ready", "supported"
    issues = []
    if result_status != "ready":
        issues.append({"issue_type": "wcag_operation_not_closed", "blocking": True,
                       "operation": operation, "status": status or result_status})
    return {"runtime_status": "ok", "support_status": support_status, "result_status": result_status,
            "runtime_required": True, "deterministic_generated": True, "static_data_versions": _static_versions(),
            "payload": {"operation": operation, "result": output}, "issues": issues}


if __name__ == "__main__":
    raise SystemExit(run_cli(handler, skill=SKILL, generator=GENERATOR,
        generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH, aggregate=True))
