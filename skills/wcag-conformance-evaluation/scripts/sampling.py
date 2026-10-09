"""Deterministic sample identity, overlap, population fingerprint, and retry helpers."""
from __future__ import annotations
import hashlib, json, math
import random
import re
from typing import Any


class SamplingError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


DOCUMENT_IDENTITY_PATTERN = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")


def is_current_document_identity(value: Any) -> bool:
    """Accept only an opaque browser-issued current-document identity token."""
    return isinstance(value, str) and DOCUMENT_IDENTITY_PATTERN.fullmatch(value) is not None


def sample_identity_registry(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    by_key={}; grouped={}
    for draft in drafts:
        required={"draft_key","target_ref","state_key","target_identity","source_evidence_refs"}
        if set(draft)!=required: raise SamplingError("sample draft schema mismatch")
        key=draft["draft_key"]
        if not isinstance(key,str) or not key or key in by_key: raise SamplingError("sample draft keys must be unique")
        if any(not isinstance(draft[field],str) or not draft[field].strip() for field in ("target_ref","state_key")):
            raise SamplingError("sample target and canonical state are required")
        if not is_current_document_identity(draft["target_identity"]):
            raise SamplingError("sample draft requires an opaque current-document identity token")
        evidence=draft["source_evidence_refs"]
        if not isinstance(evidence,list) or any(not isinstance(ref,str) or not ref.strip() for ref in evidence):
            raise SamplingError("sample source evidence refs must be non-empty strings")
        # The opaque browser identity distinguishes exact routes without
        # persisting their URL or the supplied navigation locator.
        identity=fingerprint({"target_ref":draft["target_ref"],"state_key":draft["state_key"],
                              "document_identity":draft["target_identity"]})
        group=grouped.setdefault(identity,{"target_ref":draft["target_ref"],"state_key":draft["state_key"],
            "target_identities":set(),"source_evidence_refs":set(),"draft_keys":[]})
        group["target_identities"].add(draft["target_identity"])
        group["source_evidence_refs"].update(evidence)
        group["draft_keys"].append(key)
        by_key[key]=identity
    rows=[]; identity_to_ref={}
    for identity,group in sorted(grouped.items()):
        ref=f"SAMPLE-{len(rows)+1:03d}"
        identity_to_ref[identity]=ref
        rows.append({"sample_ref":ref,"target_ref":group["target_ref"],"state_key":group["state_key"],
            "source_locators":sorted(group["target_identities"]),
            "target_identity":sorted(group["target_identities"])[0],"identity_fingerprint":identity,
            "source_evidence_refs":sorted(group["source_evidence_refs"])})
    by_key={key:identity_to_ref[identity] for key,identity in by_key.items()}
    return {"samples":rows,"draft_to_sample_ref":by_key}


def materialize_sample_lineage(*, previous_sample_refs: list[str],
        previous_identity_rows: list[dict[str, Any]], current_identity_registry: dict[str, Any],
        current_structured_sample_refs: list[str],
        replacement_decisions: list[dict[str, Any]] | None = None,
        current_evidence_refs: list[str] | None = None) -> dict[str, Any]:
    """Resolve structured sample refs across a WCAG evaluation revision.

    Identity equality includes the browser-issued opaque document identity and
    canonical target/state identity. A changed identity is replaced only when an explicit, evidence-backed semantic
    decision maps it to a current structured sample; otherwise it remains
    unavailable. Current refs with no prior mapping are materialized as added.
    """
    for label, refs in (("previous", previous_sample_refs),
                        ("current structured", current_structured_sample_refs)):
        if (not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
                or len(refs) != len(set(refs))):
            raise SamplingError(f"{label} sample refs must be unique non-empty refs")
    if not isinstance(previous_identity_rows, list):
        raise SamplingError("previous sample identity rows must be an array")
    evidence_refs = [] if current_evidence_refs is None else current_evidence_refs
    if (not isinstance(evidence_refs, list)
            or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs)
            or len(evidence_refs) != len(set(evidence_refs))):
        raise SamplingError("current evidence refs must be unique non-empty refs")
    if (not isinstance(current_identity_registry, dict)
            or set(current_identity_registry) != {"samples", "draft_to_sample_ref"}
            or not isinstance(current_identity_registry["samples"], list)
            or not isinstance(current_identity_registry["draft_to_sample_ref"], dict)):
        raise SamplingError("current sample identity registry schema mismatch")

    identity_fields = {"sample_ref", "target_ref", "state_key", "source_locators", "target_identity",
                       "identity_fingerprint", "source_evidence_refs"}

    def index_identity_rows(rows: list[dict[str, Any]], label: str) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        by_ref: dict[str, dict[str, Any]] = {}
        by_identity: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != identity_fields:
                raise SamplingError(f"{label} sample identity row schema mismatch")
            ref = row["sample_ref"]
            target = row["target_ref"]
            state = row["state_key"]
            if (not isinstance(ref, str) or not ref.strip() or ref in by_ref
                    or not isinstance(target, str) or not target.strip()
                    or not isinstance(state, str) or not state.strip()
                    or not is_current_document_identity(row.get("target_identity"))):
                raise SamplingError(f"{label} sample identity refs and target/state must be unique and non-empty")
            locators = row["source_locators"]
            evidence = row["source_evidence_refs"]
            if (not isinstance(locators, list) or not locators
                    or any(not is_current_document_identity(value) for value in locators)
                    or row["target_identity"] not in locators
                    or len(locators) != len(set(locators))
                    or not isinstance(evidence, list)
                    or any(not isinstance(value, str) or not value.strip() for value in evidence)
                    or len(evidence) != len(set(evidence))):
                raise SamplingError(f"{label} sample identity provenance is invalid")
            expected_identity = fingerprint({"target_ref": target, "state_key": state,
                                             "document_identity": row["target_identity"]})
            if row["identity_fingerprint"] != expected_identity or expected_identity in by_identity:
                raise SamplingError(f"{label} sample identity fingerprint is invalid or duplicated")
            by_ref[ref] = row
            by_identity[expected_identity] = ref
        return by_ref, by_identity

    previous_by_ref, _ = index_identity_rows(previous_identity_rows, "previous")
    if not set(previous_by_ref) <= set(previous_sample_refs):
        raise SamplingError("previous identity rows include an unselected sample ref")
    current_by_ref, current_by_identity = index_identity_rows(
        current_identity_registry["samples"], "current")
    if not set(current_structured_sample_refs) <= set(current_by_ref):
        raise SamplingError("current structured sample refs are not in the current identity registry")
    for draft_key, sample_ref in current_identity_registry["draft_to_sample_ref"].items():
        if (not isinstance(draft_key, str) or not draft_key
                or not isinstance(sample_ref, str) or sample_ref not in current_by_ref):
            raise SamplingError("current identity draft mapping is invalid")
    if set(current_identity_registry["draft_to_sample_ref"].values()) != set(current_by_ref):
        raise SamplingError("current identity draft mapping does not cover every registered sample")

    decisions = [] if replacement_decisions is None else replacement_decisions
    if not isinstance(decisions, list):
        raise SamplingError("sample replacement decisions must be an array")
    decision_by_previous: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        if (not isinstance(decision, dict)
                or set(decision) != {"previous_sample_ref", "current_sample_ref", "reason", "evidence_refs"}):
            raise SamplingError("sample replacement decision schema mismatch")
        previous_ref = decision["previous_sample_ref"]
        current_ref = decision["current_sample_ref"]
        reason = decision["reason"]
        evidence = decision["evidence_refs"]
        if (previous_ref not in previous_sample_refs or previous_ref in decision_by_previous
                or previous_ref not in previous_by_ref):
            raise SamplingError("sample replacement decision has an unknown or unresolved previous identity")
        if (current_ref not in current_structured_sample_refs
                or not isinstance(reason, str) or not reason.strip()
                or not isinstance(evidence, list) or not evidence
                or any(not isinstance(value, str) or not value.strip() for value in evidence)
                or len(evidence) != len(set(evidence))
                or not set(evidence) <= set(evidence_refs)):
            raise SamplingError("sample replacement decision needs a current ref, reason, and unique evidence refs")
        if previous_by_ref[previous_ref]["identity_fingerprint"] == current_by_ref[current_ref]["identity_fingerprint"]:
            raise SamplingError("an unchanged canonical sample identity must be retained")
        decision_by_previous[previous_ref] = decision

    retained: list[dict[str, str]] = []
    replaced: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    mapped_current: set[str] = set()
    for previous_ref in previous_sample_refs:
        previous_row = previous_by_ref.get(previous_ref)
        if previous_row is None:
            unavailable.append({"previous_sample_ref": previous_ref,
                                "reason": "previous-identity-not-supplied"})
            continue
        identity = previous_row["identity_fingerprint"]
        exact_current_ref = current_by_identity.get(identity)
        decision = decision_by_previous.get(previous_ref)
        if exact_current_ref in current_structured_sample_refs:
            if decision is not None:
                raise SamplingError("an unchanged canonical sample identity cannot be replaced")
            if exact_current_ref in mapped_current:
                raise SamplingError("current structured sample identity is mapped more than once")
            retained.append({"previous_sample_ref": previous_ref,
                             "current_sample_ref": exact_current_ref})
            mapped_current.add(exact_current_ref)
        elif decision is not None:
            current_ref = decision["current_sample_ref"]
            if current_ref in mapped_current:
                raise SamplingError("current structured sample identity is mapped more than once")
            replaced.append({"previous_sample_ref": previous_ref,
                             "current_sample_ref": current_ref,
                             "reason": decision["reason"],
                             "evidence_refs": sorted(decision["evidence_refs"])})
            mapped_current.add(current_ref)
        else:
            reason = ("identity-not-selected-as-current-structured-sample" if exact_current_ref is not None
                      else "identity-not-present-in-current-identity-registry")
            unavailable.append({"previous_sample_ref": previous_ref, "reason": reason})

    return {
        "status": "ready",
        "previous_sample_refs": sorted(previous_sample_refs),
        "current_structured_sample_refs": sorted(current_structured_sample_refs),
        "retained": sorted(retained, key=lambda row: row["previous_sample_ref"]),
        "replaced": sorted(replaced, key=lambda row: row["previous_sample_ref"]),
        "added": sorted(set(current_structured_sample_refs) - mapped_current),
        "unavailable": sorted(unavailable, key=lambda row: row["previous_sample_ref"]),
    }


def random_target_count(structured_count: int) -> int:
    if isinstance(structured_count,bool) or not isinstance(structured_count,int) or structured_count < 0:
        raise SamplingError("structured sample count must be a non-negative integer")
    return math.ceil(structured_count * 0.1)


def candidate_population_fingerprint(candidates: list[dict[str, Any]], provenance: dict[str, Any]) -> str:
    if not isinstance(candidates,list) or not isinstance(provenance,dict):
        raise SamplingError("candidate inventory and provenance are required")
    identities=[row.get("sample_identity") for row in candidates]
    if any(not isinstance(x,str) or not x for x in identities) or len(identities)!=len(set(identities)):
        raise SamplingError("candidate sample identities must be unique and explicit")
    return fingerprint({"candidate_identities":sorted(identities),"provenance":provenance})


def validate_random_selection(*, structured_refs: list[str], selected_refs: list[str], target_count: int,
                              complete_inventory: bool, selection_method: str, exhaustion_evidence_refs: list[str] | None = None,
                              blocked_reason: str | None = None) -> dict[str, Any]:
    if (not isinstance(structured_refs,list) or not isinstance(selected_refs,list)
            or any(not isinstance(ref,str) or not ref.strip() for ref in structured_refs+selected_refs)):
        raise SamplingError("structured/random selections must be arrays of non-empty refs")
    if isinstance(target_count,bool) or not isinstance(target_count,int) or target_count < 0:
        raise SamplingError("random target count must be a non-negative integer")
    expected_target_count=random_target_count(len(structured_refs))
    if target_count!=expected_target_count:
        raise SamplingError("random target count differs from the WCAG-EM structured-sample target")
    if not isinstance(complete_inventory,bool):
        raise SamplingError("complete inventory must be boolean")
    if len(structured_refs)!=len(set(structured_refs)) or len(selected_refs)!=len(set(selected_refs)):
        raise SamplingError("duplicate sample selection")
    overlap=sorted(set(structured_refs)&set(selected_refs))
    if overlap: raise SamplingError(f"structured/random overlap: {overlap}")
    if target_count < 0 or len(selected_refs)>target_count: raise SamplingError("invalid random target/selection")
    if not isinstance(selection_method,str) or not selection_method.strip(): raise SamplingError("selection method/provenance required")
    if exhaustion_evidence_refs is not None and (not isinstance(exhaustion_evidence_refs,list)
            or any(not isinstance(ref,str) or not ref.strip() for ref in exhaustion_evidence_refs)
            or len(exhaustion_evidence_refs)!=len(set(exhaustion_evidence_refs))):
        raise SamplingError("exhaustion evidence refs must be unique non-empty refs")
    if blocked_reason is not None and (not isinstance(blocked_reason,str) or not blocked_reason.strip()):
        raise SamplingError("blocked reason must be a non-empty string")
    if len(selected_refs)==target_count:
        return {"selection_status":"target-met","actual_count":len(selected_refs),"target_count":target_count,"overlap":[]}
    if complete_inventory and exhaustion_evidence_refs:
        return {"selection_status":"exhausted-no-new-view","actual_count":len(selected_refs),"target_count":target_count,"overlap":[],"exhaustion_evidence_refs":sorted(set(exhaustion_evidence_refs))}
    if not blocked_reason:
        raise SamplingError("incomplete candidate acquisition requires blocked reason")
    return {"selection_status":"blocked","actual_count":len(selected_refs),"target_count":target_count,"overlap":[],"blocked_reason":blocked_reason}


def compare_samples(structured_content_types: list[str], random_content_types: list[str],
                    structured_finding_groups: list[str], random_finding_groups: list[str]) -> dict[str, Any]:
    if any(len(values)!=len(set(values)) for values in (structured_content_types,random_content_types,structured_finding_groups,random_finding_groups)):
        raise SamplingError("comparison grouping keys must be unique sets")
    new_types=sorted(set(random_content_types)-set(structured_content_types))
    new_findings=sorted(set(random_finding_groups)-set(structured_finding_groups))
    return {"new_content_type_keys":new_types,"new_finding_group_keys":new_findings,
            "new_content_type_detected":bool(new_types),"new_finding_detected":bool(new_findings),
            "action":"return-to-step-2-3" if new_types or new_findings else "closed"}


def select_random_candidates(*, candidates: list[dict[str, Any]], structured_refs: list[str],
                              target_count: int, excluded_refs: list[str] | None = None) -> dict[str, Any]:
    """Select a non-deterministic finite-inventory random sample without a fixed seed."""
    if not isinstance(candidates,list) or not isinstance(structured_refs,list):
        raise SamplingError("finite random selection requires candidate and structured arrays")
    candidate_refs=[]
    for row in candidates:
        if not isinstance(row,dict) or set(row)!={"sample_ref","sample_identity"}:
            raise SamplingError("random candidate schema mismatch")
        if (not isinstance(row["sample_ref"],str) or not row["sample_ref"].strip()
                or not isinstance(row["sample_identity"],str) or not row["sample_identity"].strip()):
            raise SamplingError("random candidate identity is required")
        candidate_refs.append(row["sample_ref"])
    if len(candidate_refs)!=len(set(candidate_refs)):
        raise SamplingError("finite candidate refs must be unique")
    if len({row["sample_identity"] for row in candidates})!=len(candidates):
        raise SamplingError("finite candidate identities must be unique")
    if any(not isinstance(ref,str) or not ref.strip() for ref in structured_refs):
        raise SamplingError("structured refs must be non-empty")
    if len(structured_refs)!=len(set(structured_refs)):
        raise SamplingError("structured refs must be unique")
    if isinstance(target_count,bool) or not isinstance(target_count,int) or target_count<0:
        raise SamplingError("random target count must be a non-negative integer")
    expected_target_count=random_target_count(len(structured_refs))
    if target_count!=expected_target_count:
        raise SamplingError("random target count differs from the WCAG-EM structured-sample target")
    excluded_refs=excluded_refs or []
    if not isinstance(excluded_refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in excluded_refs):
        raise SamplingError("excluded refs must be non-empty refs")
    if len(excluded_refs)!=len(set(excluded_refs)):
        raise SamplingError("excluded refs must be unique")
    forbidden=set(structured_refs)|set(excluded_refs)
    eligible=sorted(set(candidate_refs)-forbidden)
    count=min(target_count,len(eligible))
    selected=sorted(random.SystemRandom().sample(eligible,count)) if count else []
    return {"selected_sample_refs":selected,"target_count":target_count,
            "eligible_candidate_count":len(eligible),"selection_status":"target-met" if count==target_count else "selection-incomplete",
            "selection_method":"system-random finite inventory selection","fixed_seed_used":False}


def materialize_processes(*, samples: list[dict[str, Any]], selected_sample_refs: list[str],
                          process_drafts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(samples,list) or not isinstance(selected_sample_refs,list) or not isinstance(process_drafts,list):
        raise SamplingError("process materialization inputs must be arrays")
    sample_refs=[]
    for row in samples:
        if not isinstance(row,dict) or not isinstance(row.get("sample_ref"),str) or not row["sample_ref"].strip():
            raise SamplingError("process sample inventory requires sample refs")
        sample_refs.append(row["sample_ref"])
    if len(sample_refs)!=len(set(sample_refs)):
        raise SamplingError("process sample inventory refs must be unique")
    if (any(not isinstance(ref,str) or not ref.strip() for ref in selected_sample_refs)
            or len(selected_sample_refs)!=len(set(selected_sample_refs))
            or not set(selected_sample_refs)<=set(sample_refs)):
        raise SamplingError("selected process sample refs must be unique current inventory refs")
    expected={"process_key","starting_point_ref","start_condition","default_sequence_refs",
        "critical_branch_sequences","completion_condition","evidence_refs"}
    keys=set(); normalized=[]
    for draft in process_drafts:
        if not isinstance(draft,dict) or set(draft)!=expected:
            raise SamplingError("complete process draft schema mismatch")
        key=draft["process_key"]
        if not isinstance(key,str) or not key.strip() or key in keys:
            raise SamplingError("complete process keys must be unique non-empty values")
        keys.add(key)
        for field in ("start_condition","completion_condition"):
            if not isinstance(draft[field],str) or not draft[field].strip():
                raise SamplingError(f"complete process {field} must be a non-empty semantic condition")
        default=draft["default_sequence_refs"]
        branches=draft["critical_branch_sequences"]
        evidence=draft["evidence_refs"]
        if (not isinstance(default,list) or not default or default[0]!=draft["starting_point_ref"]
                or any(not isinstance(ref,str) or not ref.strip() for ref in default)):
            raise SamplingError("complete process default sequence must begin at its starting point")
        if not isinstance(branches,list) or any(not isinstance(path,list) or not path
                or any(not isinstance(ref,str) or not ref.strip() for ref in path) for path in branches):
            raise SamplingError("complete process critical branch sequences are invalid")
        if not isinstance(evidence,list) or not evidence or any(not isinstance(ref,str) or not ref.strip() for ref in evidence) or len(evidence)!=len(set(evidence)):
            raise SamplingError("complete process requires unique evidence refs")
        all_refs=set(default)
        for path in branches: all_refs.update(path)
        if not all_refs<=set(sample_refs):
            raise SamplingError("complete process refers to an unknown sample")
        normalized.append(draft)
    normalized.sort(key=lambda row:row["process_key"])
    selected=set(selected_sample_refs); added=[]; rows=[]; memberships={ref:[] for ref in sample_refs}
    for index,draft in enumerate(normalized,1):
        paths=[draft["default_sequence_refs"]]+draft["critical_branch_sequences"]
        ordered=[]; seen=set()
        for path in paths:
            for ref in path:
                if ref not in seen:
                    ordered.append(ref); seen.add(ref)
                process_ref=f"PROCESS-{index:03d}"
                if process_ref not in memberships[ref]: memberships[ref].append(process_ref)
        rows.append({"process_ref":f"PROCESS-{index:03d}","process_key":draft["process_key"],
            "starting_point_ref":draft["starting_point_ref"],"start_condition":draft["start_condition"],
            "default_sequence_refs":draft["default_sequence_refs"],
            "critical_branch_sequences":draft["critical_branch_sequences"],"sample_refs":ordered,
            "completion_condition":draft["completion_condition"],
            "evidence_refs":sorted(draft["evidence_refs"])})
        for ref in ordered:
            if ref not in selected and ref not in added: added.append(ref)
    return {"status":"ready","processes":rows,"process_sample_memberships":{ref:sorted(values) for ref,values in memberships.items() if values},
            "process_added_sample_refs":added,"process_added_sample_kinds":{ref:"process-added" for ref in added},
            "selected_sample_refs":sorted(selected|set(added))}


def evaluate_step_4_2_reuse(*, evaluation_items: list[dict[str, Any]],
                            existing_results: list[dict[str, Any]]) -> dict[str, Any]:
    item_fields={"item_ref","item_kind","identity_fingerprint","evidence_fingerprint"}
    result_fields={"item_ref","result_ref","identity_fingerprint","evidence_fingerprint","freshness_status"}
    digest=re.compile(r"^sha256:[0-9a-f]{64}$")
    items={}; results={}
    for row in evaluation_items:
        if not isinstance(row,dict) or set(row)!=item_fields or not isinstance(row.get("item_ref"),str) or not row["item_ref"].strip():
            raise SamplingError("Step 4.2 evaluation item schema mismatch")
        if row["item_ref"] in items or row["item_kind"] not in {"unchanged-content","changed-content","unknown-content","interaction","input","notification","feedback"}:
            raise SamplingError("Step 4.2 item identity or kind is invalid")
        for field in ("identity_fingerprint","evidence_fingerprint"):
            value=row[field]
            if value is not None and (not isinstance(value,str) or not digest.fullmatch(value)):
                raise SamplingError(f"Step 4.2 {field} must be a SHA-256 fingerprint or null")
        items[row["item_ref"]]=row
    for row in existing_results:
        if not isinstance(row,dict) or set(row)!=result_fields or not isinstance(row.get("item_ref"),str) or not row["item_ref"].strip():
            raise SamplingError("Step 4.2 existing result schema mismatch")
        if row["item_ref"] in results or not isinstance(row.get("result_ref"),str) or not row["result_ref"].strip():
            raise SamplingError("Step 4.2 result identity is missing or duplicated")
        if row["freshness_status"] not in {"current","stale","unknown"}:
            raise SamplingError("Step 4.2 result freshness is invalid")
        for field in ("identity_fingerprint","evidence_fingerprint"):
            value=row[field]
            if value is not None and (not isinstance(value,str) or not digest.fullmatch(value)):
                raise SamplingError(f"Step 4.2 prior {field} must be a SHA-256 fingerprint or null")
        results[row["item_ref"]]=row
    if set(results)-set(items):
        raise SamplingError("Step 4.2 prior results contain items outside the current process")
    reused=[]; reevaluate=[]; reasons={}
    for item_ref,item in items.items():
        prior=results.get(item_ref)
        reason=None
        if item["item_kind"]!="unchanged-content": reason="process-interaction-or-changed-content"
        elif item["identity_fingerprint"] is None or item["evidence_fingerprint"] is None: reason="current-identity-or-evidence-unknown"
        elif prior is None: reason="no-prior-result"
        elif prior["freshness_status"]!="current": reason="prior-result-not-current"
        elif prior["identity_fingerprint"]!=item["identity_fingerprint"]: reason="content-identity-changed"
        elif prior["evidence_fingerprint"]!=item["evidence_fingerprint"]: reason="evidence-changed"
        if reason is None: reused.append(prior["result_ref"])
        else: reevaluate.append(item_ref); reasons[item_ref]=reason
    return {"status":"ready","reusable_result_refs":sorted(reused),"reevaluate_item_refs":sorted(reevaluate),
            "reevaluation_reasons":reasons}


def reconcile_sampling_revision(*, previous_iteration: dict[str, Any],
        current_structured_revision: int, current_structured_sample_refs: list[str],
        candidates: list[dict[str, Any]], provenance: dict[str, Any],
        new_random_selection_refs: list[str] | None = None, selection_method: str | None = None,
        complete_inventory: bool = False, exhaustion_evidence_refs: list[str] | None = None,
        blocked_reason: str | None = None) -> dict[str, Any]:
    previous_fields={"structured_revision","structured_sample_refs","random_samples","candidate_population_fingerprint","selection_method"}
    if not isinstance(previous_iteration,dict) or set(previous_iteration)!=previous_fields:
        raise SamplingError("previous sampling iteration schema mismatch")
    old_revision=previous_iteration["structured_revision"]
    if isinstance(old_revision,bool) or not isinstance(old_revision,int) or old_revision<1:
        raise SamplingError("previous structured revision must be positive")
    if isinstance(current_structured_revision,bool) or not isinstance(current_structured_revision,int) or current_structured_revision<=old_revision:
        raise SamplingError("Step 4.3 requires a newer structured sample revision")
    for label,refs in (("previous structured",previous_iteration["structured_sample_refs"]),
            ("current structured",current_structured_sample_refs)):
        if not isinstance(refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in refs) or len(refs)!=len(set(refs)):
            raise SamplingError(f"{label} sample refs must be unique non-empty refs")
    if not current_structured_sample_refs:
        raise SamplingError("Step 4.3 current structured sample set cannot be empty")
    current_population=candidate_population_fingerprint(candidates,provenance)
    old_population=previous_iteration["candidate_population_fingerprint"]
    if not isinstance(old_population,str) or not re.fullmatch(r"sha256:[0-9a-f]{64}",old_population):
        raise SamplingError("previous candidate population fingerprint is invalid")
    candidate_refs={row["sample_ref"] for row in candidates}
    previous_samples=previous_iteration["random_samples"]
    if not isinstance(previous_samples,list):
        raise SamplingError("previous random samples must be an array")
    previous_random=[]
    for row in previous_samples:
        if not isinstance(row,dict) or set(row)!={"sample_ref","freshness_status"}:
            raise SamplingError("previous random sample schema mismatch")
        if not isinstance(row["sample_ref"],str) or not row["sample_ref"].strip() or row["freshness_status"] not in {"current","stale","unknown"}:
            raise SamplingError("previous random sample identity or freshness is invalid")
        previous_random.append(row["sample_ref"])
    if len(previous_random)!=len(set(previous_random)):
        raise SamplingError("previous random sample refs must be unique")
    prior_method=previous_iteration["selection_method"]
    if not isinstance(prior_method,str) or not prior_method.strip():
        raise SamplingError("previous random selection method provenance is required")
    population_same=old_population==current_population
    prior_random=set(previous_random)
    structured=set(current_structured_sample_refs)
    if population_same:
        current_prior={row["sample_ref"] for row in previous_samples if row["freshness_status"]=="current"}
        retained=sorted(prior_random & current_prior & candidate_refs - structured)
        discarded=sorted(prior_random-set(retained))
    else:
        retained=[]
        discarded=sorted(prior_random)
    target=random_target_count(len(current_structured_sample_refs))
    needed=max(0,target-len(retained))
    if new_random_selection_refs is None:
        if selection_method is not None:
            raise SamplingError("selection method must accompany actual new random refs")
        if not needed:
            checked=validate_random_selection(structured_refs=current_structured_sample_refs,
                selected_refs=retained,target_count=target,complete_inventory=complete_inventory,
                selection_method=prior_method,exhaustion_evidence_refs=exhaustion_evidence_refs,
                blocked_reason=blocked_reason)
            status=checked["selection_status"]
        else:
            checked=None
            status="selection-required"
        return {"status":status,"structured_revision":current_structured_revision,
            "structured_sample_refs":sorted(structured),"candidate_population_fingerprint":current_population,
            "population_unchanged":population_same,"retained_random_sample_refs":retained,
            "discarded_random_sample_refs":discarded,"random_selection_required_count":needed,
            "random_target_count":target,"random_sample_refs":retained,"selection_closure":checked,
            "selection_method":prior_method if not needed else None}
    if not isinstance(new_random_selection_refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in new_random_selection_refs):
        raise SamplingError("new random selection refs must be non-empty refs")
    if selection_method is None or not isinstance(selection_method,str) or not selection_method.strip():
        raise SamplingError("actual random selection requires method provenance")
    eligible_new=candidate_refs-structured-set(retained)
    if len(new_random_selection_refs)!=len(set(new_random_selection_refs)) or not set(new_random_selection_refs)<=eligible_new:
        raise SamplingError("new random selection is duplicate, overlapping, or outside current candidate population")
    final_random=retained+new_random_selection_refs
    checked=validate_random_selection(structured_refs=current_structured_sample_refs,
        selected_refs=final_random,target_count=target,complete_inventory=complete_inventory,
        selection_method=selection_method,exhaustion_evidence_refs=exhaustion_evidence_refs,
        blocked_reason=blocked_reason)
    if len(new_random_selection_refs)>needed:
        raise SamplingError("new random selection exceeds the current target")
    return {"status":checked["selection_status"],"structured_revision":current_structured_revision,
        "structured_sample_refs":sorted(structured),"candidate_population_fingerprint":current_population,
        "population_unchanged":population_same,"retained_random_sample_refs":retained,
        "discarded_random_sample_refs":discarded,"random_selection_required_count":needed,
        "random_target_count":target,"random_sample_refs":sorted(final_random),
        "selection_method":selection_method,"selection_closure":checked}
