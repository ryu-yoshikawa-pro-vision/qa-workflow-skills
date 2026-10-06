from __future__ import annotations
import hashlib, json, math, re
from pathlib import Path
from urllib.parse import urlsplit
from scripts.skills.evals.deterministic.result import EvalResult

BASE=Path(__file__).resolve().parents[2]/'assets'
INSPECTION_ASSETS=Path(__file__).resolve().parents[3]/'usability-inspection'/'assets'
EXPECTED_COUNTS={'2.0':61,'2.1':78,'2.2':86}
STATIC_ROLES={'population-completeness','current-browser-observation','visual-evidence','process-context',
              'presentation-variation','accessibility-support-baseline','technology-context','authority-context'}
ALL_ROLES=STATIC_ROLES|{'machine-procedure-result','manual-procedure-result','assistive-technology-result','external-evidence-result'}
OBSERVATION_FIELDS={'viewport.metrics','element.geometry','element.state','document.location','element.rendered-text',
 'element.control-value','element.selected-values','accessibility.semantics','focus.state','computed-style.properties',
 'responsive.conditions','responsive.boundaries','navigation.timing','paint.timing','interaction.timing','screenshot.image'}
DECISION_KINDS={'applicability','exception','purpose','meaning','equivalence','relationship','sequence',
                'instruction-feedback','accessibility-support','other-normative-semantic'}
SHORTCUT_GUARDS={
 'A single ACT Rule PASS does not establish the complete Success Criterion.',
 'A single target with zero matches does not establish an empty applicable population.',
 'A partial machine-procedure PASS does not close semantic requirements.',
 'Visual meaning is not observed without the required visual evidence.',
 'Missing manual, assistive-technology, or external evidence must not be inferred.',
 'Apply a normative exception only when its evidence is present and its conditions hold.',
 'Do not transfer a neighboring Success Criterion result to this criterion.',
 'Do not use normative wording from a different WCAG version.',
}
SCOPE_KEYS=("third-party-content","language-versions","responsive-device-variations",
            "separately-hosted-product-areas","authenticated-restricted-views")


def validate_scope_coverage(result: dict) -> list[str]:
    """Independent Step 1.1 validator; does not import the production helper."""
    errors=[]
    if not isinstance(result,dict) or set(result)!={"status","scope_coverage","missing_scope_keys","unresolved_scope_refs"}:
        return ["scope_coverage_output_schema"]
    rows=result.get("scope_coverage")
    if not isinstance(rows,list) or len(rows)!=len(SCOPE_KEYS):
        return ["scope_coverage_row_count"]
    seen=[]; unresolved=[]
    for index,row in enumerate(rows,1):
        if not isinstance(row,dict) or set(row)!={"scope_ref","scope_key","decision","reason","evidence_refs"}:
            errors.append(f"scope_coverage_schema:{index}"); continue
        key=SCOPE_KEYS[index-1]
        if row.get("scope_ref")!=f"SCOPE-{index:03d}" or row.get("scope_key")!=key:
            errors.append(f"scope_coverage_identity:{index}")
        if row.get("decision") not in {"in-scope","out-of-product","unresolved"}:
            errors.append(f"scope_coverage_decision:{index}")
        refs=row.get("evidence_refs")
        if not isinstance(refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in refs) or len(refs)!=len(set(refs)):
            errors.append(f"scope_coverage_evidence:{index}")
        elif row.get("decision")!="unresolved" and not refs:
            errors.append(f"scope_coverage_closed_without_evidence:{index}")
        if row.get("decision")=="out-of-product" and (not isinstance(row.get("reason"),str) or not row["reason"].strip()):
            errors.append(f"scope_coverage_boundary_reason:{index}")
        if row.get("decision")=="unresolved": unresolved.append(row.get("scope_ref"))
        seen.append(row.get("scope_key"))
    expected_unresolved=sorted(unresolved)
    expected_status="ready" if not unresolved else "unresolved"
    if seen!=list(SCOPE_KEYS): errors.append("scope_coverage_exact_key_set")
    missing=result.get("missing_scope_keys")
    if (not isinstance(missing,list) or missing!=sorted(set(missing))
            or not set(missing)<=set(SCOPE_KEYS)
            or not set(missing)<=set(row.get("scope_key") for row in rows
                if isinstance(row,dict) and row.get("decision")=="unresolved")):
        errors.append("scope_coverage_missing_keys")
    if result.get("unresolved_scope_refs")!=expected_unresolved: errors.append("scope_coverage_unresolved_refs")
    if result.get("status")!=expected_status: errors.append("scope_coverage_status")
    return errors


def validate_baseline_extension(arguments: dict, result: dict) -> list[str]:
    """Independently check revision, formal/diagnostic separation and stale dependencies."""
    errors=[]
    formal=arguments.get("formal_evidence_environment_refs",[])
    diagnostic=arguments.get("diagnostic_only_environment_refs",[])
    current=arguments.get("environment_refs",[])
    if set(formal)&set(diagnostic): return ["baseline_environment_role_overlap"]
    added=sorted(set(formal)-set(current))
    if result.get("status")=="extended":
        expected_revision=arguments.get("revision",0)+1
        expected_env=sorted(set(current)|set(added))
        if result.get("revision")!=expected_revision: errors.append("baseline_revision_increment")
        if result.get("previous_baseline_ref")!=arguments.get("baseline_ref"): errors.append("baseline_previous_ref")
        if result.get("environment_refs")!=expected_env: errors.append("baseline_formal_environment_set")
        if set(result.get("environment_refs",[]))&set(diagnostic): errors.append("baseline_diagnostic_environment_promoted")
        rows=arguments.get("sample_results",[]); stale=[]
        for row in rows:
            if set(row.get("environment_refs",[]))&set(added) and row.get("baseline_revision")!=expected_revision:
                stale.append(row.get("sample_result_ref"))
        if result.get("stale_sample_result_refs")!=sorted(stale): errors.append("baseline_related_result_freshness")
    elif result.get("status")=="unchanged":
        if added: errors.append("baseline_extension_missing")
        if result.get("revision")!=arguments.get("revision"): errors.append("baseline_unchanged_revision")
        if set(result.get("environment_refs",[]))&set(diagnostic): errors.append("baseline_diagnostic_environment_promoted")
    elif result.get("status")=="blocked":
        if added and arguments.get("extension_reason") and arguments["extension_reason"].strip():
            errors.append("baseline_extension_blocked_with_reason")
        if result.get("revision")!=arguments.get("revision"): errors.append("baseline_blocked_revision_changed")
    else:
        errors.append("baseline_extension_status")
    return errors


def validate_process_materialization(arguments: dict, result: dict) -> list[str]:
    errors=[]
    samples=arguments.get("samples",[]); selected=set(arguments.get("selected_sample_refs",[]))
    sample_refs={row.get("sample_ref") for row in samples if isinstance(row,dict)}
    ordered=sorted(arguments.get("process_drafts",[]),key=lambda row:row.get("process_key",""))
    expected_rows=[]; memberships={ref:[] for ref in sample_refs}; added=[]
    for index,draft in enumerate(ordered,1):
        process_ref=f"PROCESS-{index:03d}"
        paths=[draft.get("default_sequence_refs",[])]+draft.get("critical_branch_sequences",[])
        flattened=[]; seen=set()
        for path in paths:
            for ref in path:
                if ref not in seen:
                    flattened.append(ref); seen.add(ref)
                if process_ref not in memberships.setdefault(ref,[]): memberships[ref].append(process_ref)
        expected_rows.append({"process_ref":process_ref,"process_key":draft.get("process_key"),
            "starting_point_ref":draft.get("starting_point_ref"),"start_condition":draft.get("start_condition"),
            "default_sequence_refs":draft.get("default_sequence_refs"),
            "critical_branch_sequences":draft.get("critical_branch_sequences"),"sample_refs":flattened,
            "completion_condition":draft.get("completion_condition"),
            "evidence_refs":sorted(draft.get("evidence_refs",[]))})
        for ref in flattened:
            if ref not in selected and ref not in added: added.append(ref)
    expected={"status":"ready","processes":expected_rows,
        "process_sample_memberships":{ref:sorted(values) for ref,values in memberships.items() if values},
        "process_added_sample_refs":added,"process_added_sample_kinds":{ref:"process-added" for ref in added},
        "selected_sample_refs":sorted(selected|set(added))}
    if result!=expected: errors.append("complete_process_materialization_mismatch")
    return errors


def validate_step_4_2_reuse(arguments: dict, result: dict) -> list[str]:
    errors=[]
    items=arguments.get("evaluation_items",[]); prior=arguments.get("existing_results",[])
    by_item={row.get("item_ref"):row for row in prior if isinstance(row,dict)}
    reusable=[]; reevaluate=[]; reasons={}
    for item in items:
        ref=item.get("item_ref"); old=by_item.get(ref); reason=None
        if item.get("item_kind")!="unchanged-content": reason="process-interaction-or-changed-content"
        elif not item.get("identity_fingerprint") or not item.get("evidence_fingerprint"): reason="current-identity-or-evidence-unknown"
        elif old is None: reason="no-prior-result"
        elif old.get("freshness_status")!="current": reason="prior-result-not-current"
        elif old.get("identity_fingerprint")!=item.get("identity_fingerprint"): reason="content-identity-changed"
        elif old.get("evidence_fingerprint")!=item.get("evidence_fingerprint"): reason="evidence-changed"
        if reason is None: reusable.append(old.get("result_ref"))
        else: reevaluate.append(ref); reasons[ref]=reason
    if not isinstance(result,dict) or set(result)!={"status","reusable_result_refs","reevaluate_item_refs","reevaluation_reasons"}:
        return ["step_4_2_output_schema"]
    if result.get("status")!="ready": errors.append("step_4_2_status")
    if result.get("reusable_result_refs")!=sorted(reusable): errors.append("step_4_2_reuse_set")
    if result.get("reevaluate_item_refs")!=sorted(reevaluate): errors.append("step_4_2_reevaluate_set")
    if result.get("reevaluation_reasons")!=reasons: errors.append("step_4_2_reasons")
    return errors


def validate_step_4_3_reconciliation(arguments: dict, result: dict) -> list[str]:
    errors=[]
    candidates=arguments.get("candidates",[]); provenance=arguments.get("provenance",{})
    identities=sorted(row.get("sample_identity") for row in candidates)
    payload=json.dumps({"candidate_identities":identities,"provenance":provenance},
        ensure_ascii=False,sort_keys=True,separators=(",",":" )).encode("utf-8")
    population="sha256:"+hashlib.sha256(payload).hexdigest()
    previous=arguments.get("previous_iteration",{})
    same=previous.get("candidate_population_fingerprint")==population
    current_structured=set(arguments.get("current_structured_sample_refs",[]))
    candidates_by_ref={row.get("sample_ref") for row in candidates}
    prior_rows=previous.get("random_samples",[])
    prior_refs={row.get("sample_ref") for row in prior_rows}
    if same:
        current_prior={row.get("sample_ref") for row in prior_rows if row.get("freshness_status")=="current"}
        retained=sorted(prior_refs & current_prior & candidates_by_ref-current_structured)
    else: retained=[]
    discarded=sorted(prior_refs-set(retained))
    target=math.ceil(len(current_structured)*0.10)
    needed=max(0,target-len(retained))
    if not isinstance(result,dict): return ["step_4_3_output_schema"]
    expected_fields={"status","structured_revision","structured_sample_refs","candidate_population_fingerprint",
        "population_unchanged","retained_random_sample_refs","discarded_random_sample_refs",
        "random_selection_required_count","random_target_count","random_sample_refs",
        "selection_closure","selection_method"}
    if needed>0 and arguments.get("new_random_selection_refs") is None:
        expected_fields=expected_fields
    if set(result)!=expected_fields: errors.append("step_4_3_output_schema")
    if result.get("candidate_population_fingerprint")!=population: errors.append("step_4_3_population_fingerprint")
    if result.get("population_unchanged") is not same: errors.append("step_4_3_population_comparison")
    if result.get("retained_random_sample_refs")!=retained: errors.append("step_4_3_retained_random_set")
    if result.get("discarded_random_sample_refs")!=discarded: errors.append("step_4_3_discarded_random_set")
    if result.get("random_selection_required_count")!=needed or result.get("random_target_count")!=target:
        errors.append("step_4_3_random_target")
    selected=result.get("random_sample_refs",[])
    if (not isinstance(selected,list) or len(selected)!=len(set(selected))
            or set(selected)&current_structured or not set(selected)<=candidates_by_ref):
        errors.append("step_4_3_random_overlap_or_scope")
    if needed>0 and arguments.get("new_random_selection_refs") is None:
        if result.get("status")!="selection-required" or selected!=retained:
            errors.append("step_4_3_selection_required")
    else:
        selected_input=arguments.get("new_random_selection_refs") or []
        expected_random=sorted(retained+selected_input)
        if selected!=expected_random: errors.append("step_4_3_selected_random_set")
        if len(selected)==target:
            expected_status="target-met"
        elif arguments.get("complete_inventory") and arguments.get("exhaustion_evidence_refs"):
            expected_status="exhausted-no-new-view"
        else: expected_status="blocked"
        if result.get("status")!=expected_status: errors.append("step_4_3_selection_status")
    return errors


def validate_sample_lineage(arguments: dict, result: dict) -> list[str]:
    """Independently reconstruct rerun identity closure without production imports."""
    required={"previous_sample_refs","previous_identity_rows","current_identity_registry",
              "current_structured_sample_refs"}
    if (not isinstance(arguments,dict) or not required<=set(arguments)
            or not isinstance(result,dict)):
        return ["sample_lineage_input_schema"]
    previous_refs=arguments["previous_sample_refs"]
    current_refs=arguments["current_structured_sample_refs"]
    evidence_refs=arguments.get("current_evidence_refs",[])
    def valid_refs(values: object, *, allow_empty: bool=True) -> bool:
        return (isinstance(values,list) and (allow_empty or bool(values))
                and all(isinstance(value,str) and value.strip() for value in values)
                and len(values)==len(set(values)))
    def valid_document_identity(value: object) -> bool:
        if not isinstance(value,str) or not value.strip(): return False
        try: parsed=urlsplit(value)
        except ValueError: return False
        return (parsed.scheme in {"http","https"} and bool(parsed.netloc)
                and parsed.username is None and parsed.password is None)
    if (not valid_refs(previous_refs) or not valid_refs(current_refs)
            or not valid_refs(evidence_refs)):
        return ["sample_lineage_ref_inputs"]
    registry=arguments["current_identity_registry"]
    if (not isinstance(registry,dict) or set(registry)!={"samples","draft_to_sample_ref"}
            or not isinstance(registry["samples"],list) or not isinstance(registry["draft_to_sample_ref"],dict)
            or not isinstance(arguments["previous_identity_rows"],list)):
        return ["sample_lineage_identity_input_schema"]
    current_registry_refs=[row.get("sample_ref") if isinstance(row,dict) else None for row in registry["samples"]]
    if (any(not isinstance(ref,str) or not ref.strip() for ref in current_registry_refs)
            or len(current_registry_refs)!=len(set(current_registry_refs))):
        return ["sample_lineage_identity_input_schema"]
    fields={"sample_ref","target_ref","state_key","source_locators","target_identity",
            "identity_fingerprint","source_evidence_refs"}
    def index(rows: list[dict], selected: set[str]) -> tuple[dict[str,dict],dict[str,str]] | None:
        by_ref={}; by_identity={}
        for row in rows:
            if not isinstance(row,dict) or set(row)!=fields:
                return None
            ref=row["sample_ref"]; target=row["target_ref"]; state=row["state_key"]
            locators=row["source_locators"]; sources=row["source_evidence_refs"]
            if (not isinstance(ref,str) or not ref.strip() or ref not in selected or ref in by_ref
                    or not isinstance(target,str) or not target.strip()
                    or not isinstance(state,str) or not state.strip()
                    or not valid_document_identity(row["target_identity"])
                    or not valid_refs(locators,allow_empty=False) or not valid_refs(sources)):
                return None
            identity_data=json.dumps({"target_ref":target,"state_key":state},ensure_ascii=False,
                sort_keys=True,separators=(",",":")).encode("utf-8")
            identity="sha256:"+hashlib.sha256(identity_data).hexdigest()
            if row["identity_fingerprint"]!=identity or identity in by_identity:
                return None
            by_ref[ref]=row; by_identity[identity]=ref
        return by_ref,by_identity
    previous_index=index(arguments["previous_identity_rows"],set(previous_refs))
    current_index=index(registry["samples"],set(current_registry_refs))
    if previous_index is None or current_index is None:
        return ["sample_lineage_identity_rows"]
    current_by_ref,current_by_identity=current_index
    mapping=registry["draft_to_sample_ref"]
    if (any(not isinstance(key,str) or not key or not isinstance(ref,str) or ref not in current_by_ref
            for key,ref in mapping.items()) or set(mapping.values())!=set(current_by_ref)
            or not set(current_refs)<=set(current_by_ref)):
        return ["sample_lineage_current_registry"]
    decisions=arguments.get("replacement_decisions",[])
    if not isinstance(decisions,list): return ["sample_lineage_replacement_inputs"]
    decision_by_previous={}
    for decision in decisions:
        if (not isinstance(decision,dict)
                or set(decision)!={"previous_sample_ref","current_sample_ref","reason","evidence_refs"}):
            return ["sample_lineage_replacement_inputs"]
        previous_ref=decision["previous_sample_ref"]; current_ref=decision["current_sample_ref"]
        refs=decision["evidence_refs"]
        if (not isinstance(previous_ref,str) or previous_ref not in previous_refs
                or previous_ref not in previous_index[0] or previous_ref in decision_by_previous
                or not isinstance(current_ref,str) or current_ref not in current_refs
                or not isinstance(decision["reason"],str) or not decision["reason"].strip()
                or not valid_refs(refs,allow_empty=False) or not set(refs)<=set(evidence_refs)
                or previous_index[0][previous_ref]["identity_fingerprint"]==current_by_ref[current_ref]["identity_fingerprint"]):
            return ["sample_lineage_replacement_inputs"]
        decision_by_previous[previous_ref]=decision
    retained=[]; replaced=[]; unavailable=[]; mapped=set()
    for previous_ref in previous_refs:
        old=previous_index[0].get(previous_ref)
        if old is None:
            unavailable.append({"previous_sample_ref":previous_ref,"reason":"previous-identity-not-supplied"})
            continue
        current_ref=current_by_identity.get(old["identity_fingerprint"])
        decision=decision_by_previous.get(previous_ref)
        if current_ref in current_refs:
            if decision is not None or current_ref in mapped:
                return ["sample_lineage_identity_mapping"]
            retained.append({"previous_sample_ref":previous_ref,"current_sample_ref":current_ref})
            mapped.add(current_ref)
        elif decision is not None:
            current_ref=decision["current_sample_ref"]
            if current_ref in mapped: return ["sample_lineage_identity_mapping"]
            replaced.append({"previous_sample_ref":previous_ref,"current_sample_ref":current_ref,
                "reason":decision["reason"],"evidence_refs":sorted(decision["evidence_refs"])})
            mapped.add(current_ref)
        else:
            reason=("identity-not-selected-as-current-structured-sample" if current_ref is not None
                    else "identity-not-present-in-current-identity-registry")
            unavailable.append({"previous_sample_ref":previous_ref,"reason":reason})
    expected={"status":"ready","previous_sample_refs":sorted(previous_refs),
        "current_structured_sample_refs":sorted(current_refs),
        "retained":sorted(retained,key=lambda row:row["previous_sample_ref"]),
        "replaced":sorted(replaced,key=lambda row:row["previous_sample_ref"]),
        "added":sorted(set(current_refs)-mapped),
        "unavailable":sorted(unavailable,key=lambda row:row["previous_sample_ref"])}
    return [] if result==expected else ["sample_lineage_contract_mismatch"]


def validate_static_assets() -> list[str]:
    errors=[]
    criteria_by_version={}
    for version,count in EXPECTED_COUNTS.items():
        try: data=json.loads((BASE/f'wcag-{version}-requirements.json').read_text(encoding='utf-8'))
        except Exception as exc: errors.append(f'catalog_load:{version}:{exc}'); continue
        rows=data.get('success_criteria',[]); refs=[r.get('criterion_ref') for r in rows]
        if len(rows)!=count or len(refs)!=len(set(refs)): errors.append(f'criteria_count_or_duplicates:{version}')
        if version=='2.2' and '4.1.1' in refs: errors.append('wcag_2_2_contains_4_1_1')
        if set(r.get('requirement_key') for r in data.get('conformance_requirements',[]))!={'conformance-level','full-pages','complete-processes','accessibility-supported-ways','non-interference'}:
            errors.append(f'conformance_requirement_set:{version}')
        if any(f's-wcag-{row.get("criterion_ref")}' not in row.get('procedure_keys',[]) for row in rows):
            errors.append(f'semantic_procedure_missing:{version}')
        criteria_by_version[version]=set(refs)
    try:
        procs=json.loads((BASE/'wcag-evaluation-procedure-catalog.json').read_text(encoding='utf-8'))['procedures']
        keys=[row.get('procedure_key') for row in procs]
        if len(keys)!=len(set(keys)): errors.append('duplicate_procedure_key')
        proc_keys=set(keys)
    except Exception as exc: errors.append(f'procedure_catalog_load:{exc}'); proc_keys=set()
    for version in EXPECTED_COUNTS:
        try: data=json.loads((BASE/f'wcag-{version}-requirements.json').read_text(encoding='utf-8'))
        except Exception: continue
        for row in data.get('success_criteria',[]):
            for key in row.get('procedure_keys',[]):
                if key not in proc_keys: errors.append(f'procedure_missing:{version}:{row.get("criterion_ref")}:{key}')
    try:
        procedure_rows=json.loads((BASE/'wcag-evaluation-procedure-catalog.json').read_text(encoding='utf-8'))['procedures']
        procedures={row['procedure_key']:row for row in procedure_rows}
        if len(procedures)!=len(procedure_rows): errors.append('procedure_catalog_duplicate')
        common={'procedure_key','procedure_kind','applicability_mode','applicable_criterion_refs','required_capabilities',
                'required_input_refs','result_contract','completion_evidence','limitation_behavior'}
        allowed_kinds={'machine','semantic','manual','assistive-technology','external-evidence'}
        for key,row in procedures.items():
            kind=row.get('procedure_kind'); mode=row.get('applicability_mode')
            expected_schema=common|({'machine_probe_keys','dispatch_key'} if kind=='machine' else
                {'semantic_decision_key'} if kind=='semantic' else
                {'required_evidence_kind','activation_source_procedure_key','activation_limitation_codes'} if mode=='machine-limitation' else
                {'required_evidence_kind','applicability_decision_key'} if kind=='assistive-technology' else
                {'required_evidence_kind','external_evidence_allowed'} if kind=='external-evidence' else
                {'required_evidence_kind'})
            if kind not in allowed_kinds or set(row)!=expected_schema:
                errors.append(f'procedure_schema:{key}')
                continue
            if mode not in {'always','semantic','machine-limitation','external-evidence-available'}:
                errors.append(f'procedure_applicability_mode:{key}')
            for field in ('applicable_criterion_refs','required_capabilities','required_input_refs','completion_evidence'):
                values=row.get(field)
                if not isinstance(values,list) or len(values)!=len(set(values)) or any(not isinstance(value,str) or not value for value in values):
                    errors.append(f'procedure_{field}:{key}')
            contract=row.get('result_contract')
            if not isinstance(contract,dict) or not isinstance(contract.get('contract_kind'),str) or not isinstance(contract.get('required_fields'),list) or not contract['required_fields']:
                errors.append(f'procedure_result_contract:{key}')
            if not isinstance(row.get('limitation_behavior'),str) or not row['limitation_behavior'].strip():
                errors.append(f'procedure_limitation_behavior:{key}')
            if kind=='machine':
                probes=row.get('machine_probe_keys')
                if not isinstance(probes,list) or len(probes)!=len(set(probes)) or not row.get('dispatch_key'):
                    errors.append(f'machine_dispatch_contract:{key}')
                if isinstance(contract,dict) and contract.get('contract_kind')=='typed-machine-probe-results' and set(probes or [])!=set(contract.get('required_machine_probe_keys',[])):
                    errors.append(f'machine_result_probe_contract:{key}')
            if kind=='semantic' and row.get('semantic_decision_key')!=key:
                errors.append(f'semantic_decision_key:{key}')
            if mode=='machine-limitation' and (not row.get('activation_source_procedure_key') or not row.get('activation_limitation_codes')):
                errors.append(f'machine_fallback_source:{key}')
            if kind=='external-evidence' and row.get('external_evidence_allowed') is not True:
                errors.append(f'external_evidence_not_allowed:{key}')
        for version in EXPECTED_COUNTS:
            req=json.loads((BASE/f'wcag-{version}-requirements.json').read_text(encoding='utf-8'))
            for criterion in req.get('success_criteria',[]):
                ref=criterion.get('criterion_ref')
                expected=sorted(key for key,row in procedures.items() if ref in row.get('applicable_criterion_refs',[]))
                if criterion.get('procedure_keys')!=expected:
                    errors.append(f'procedure_assignment_mismatch:{version}:{ref}')
                external=any(procedures.get(key,{}).get('procedure_kind')=='external-evidence' for key in expected)
                if criterion.get('external_evidence_allowed') is not external:
                    errors.append(f'external_evidence_allowance_mismatch:{version}:{ref}')
        try:
            probe_rows=json.loads((INSPECTION_ASSETS/'wcag-machine-probe-catalog.json').read_text(encoding='utf-8')).get('probes',[])
            formal_probe_keys=[probe for row in procedure_rows if row.get('procedure_kind')=='machine' for probe in row.get('machine_probe_keys',[])]
            inspection_probe_keys=[row.get('machine_probe_key') for row in probe_rows]
            if set(formal_probe_keys)!=set(inspection_probe_keys) or len(inspection_probe_keys)!=len(set(inspection_probe_keys)):
                errors.append('cross_package_machine_probe_set_mismatch')
        except Exception as exc:
            errors.append(f'inspection_machine_probe_catalog_load:{exc}')
        semantic_asset=json.loads((BASE/'wcag-semantic-contracts.json').read_text(encoding='utf-8'))
        semantics=semantic_asset.get('contracts')
        if semantic_asset.get('schema_version')!='1' or semantic_asset.get('source_plan')!='_05k_wcag-semantic-procedure-contract.md' or not isinstance(semantics,list):
            errors.append('semantic_contract_asset_envelope')
            semantics=[]
        versions={}
        for row in semantics:
            version=row.get('target_wcag_version')
            versions.setdefault(version,[]).append(row)
        for version in EXPECTED_COUNTS:
            req=json.loads((BASE/f'wcag-{version}-requirements.json').read_text(encoding='utf-8'))
            expected={row['criterion_ref']:row for row in req['success_criteria']}
            actual={row.get('criterion_ref'):row for row in versions.get(version,[])}
            if set(actual)!=set(expected) or len(actual)!=len(versions.get(version,[])):
                errors.append(f'semantic_contract_criterion_set:{version}')
            for criterion,contract in actual.items():
                prefix=f'{version}:{criterion}'
                if contract.get('semantic_contract_key')!=f's-wcag-{criterion}@{version}':
                    errors.append(f'semantic_contract_key:{prefix}')
                if contract.get('level')!=expected.get(criterion,{}).get('level'):
                    errors.append(f'semantic_contract_level:{prefix}')
                required_contract={'semantic_contract_key','criterion_ref','target_wcag_version','level','normative_source_item_refs',
                  'normative_clause_refs','definition_refs','exception_refs','semantic_evaluation_points','required_evidence_roles',
                  'allowed_additional_observation_fields','forbidden_shortcuts','missing_evidence_behavior','procedure_applicability_contracts'}
                if set(contract)!=required_contract:
                    errors.append(f'semantic_contract_schema:{prefix}')
                source_refs=contract.get('normative_source_item_refs',[])
                expected_source=f'SRC-WCAG-{version}:{criterion}'
                if source_refs!=[expected_source]: errors.append(f'normative_source_item_ref:{prefix}')
                clauses=contract.get('normative_clause_refs',[])
                clause_refs=[item.get('clause_ref') for item in clauses if isinstance(item,dict)]
                if not clauses or len(clause_refs)!=len(set(clause_refs)):
                    errors.append(f'normative_clause_ref_set:{prefix}')
                for item in clauses:
                    if set(item)!={'clause_ref','locator_type','locator'} or item.get('locator_type') not in {'fragment','section-id','heading','page'} or not item.get('locator'):
                        errors.append(f'normative_clause_locator:{prefix}')
                if any(not isinstance(ref,str) or not ref.startswith('https://www.w3.org/TR/WCAG'+version.replace('.','')+'/#') for ref in contract.get('definition_refs',[])):
                    errors.append(f'definition_ref_unresolved:{prefix}')
                if not set(contract.get('exception_refs',[]))<=set(clause_refs):
                    errors.append(f'exception_ref_unresolved:{prefix}')
                points=contract.get('semantic_evaluation_points',[])
                point_keys=[point.get('point_key') for point in points if isinstance(point,dict)]
                if not points or len(point_keys)!=len(set(point_keys)):
                    errors.append(f'semantic_point_set:{prefix}')
                covered_clauses=set()
                for point in points:
                    if set(point)!={'point_key','source_clause_refs','decision_kind','required_evidence_roles','completion_required'}:
                        errors.append(f'semantic_point_schema:{prefix}')
                        continue
                    covered_clauses.update(point.get('source_clause_refs',[]))
                    if point.get('decision_kind') not in DECISION_KINDS or point.get('completion_required') is not True:
                        errors.append(f'semantic_point_enum:{prefix}')
                    if not set(point.get('source_clause_refs',[]))<=set(clause_refs):
                        errors.append(f'semantic_point_source_unresolved:{prefix}')
                    if not set(point.get('required_evidence_roles',[]))<=STATIC_ROLES:
                        errors.append(f'semantic_point_procedure_role_forbidden:{prefix}')
                if covered_clauses!=set(clause_refs): errors.append(f'semantic_clause_coverage:{prefix}')
                if not set(contract.get('required_evidence_roles',[]))<=STATIC_ROLES:
                    errors.append(f'static_procedure_role_forbidden:{prefix}')
                if not set(contract.get('allowed_additional_observation_fields',[]))<=OBSERVATION_FIELDS:
                    errors.append(f'additional_observation_field_invalid:{prefix}')
                if not SHORTCUT_GUARDS<=set(contract.get('forbidden_shortcuts',[])):
                    errors.append(f'common_forbidden_shortcut_missing:{prefix}')
                if contract.get('missing_evidence_behavior')!='undetermined':
                    errors.append(f'missing_evidence_behavior:{prefix}')
                applicability=contract.get('procedure_applicability_contracts',[])
                expected_at={key:value for key,value in procedures.items()
                             if value.get('procedure_kind')=='assistive-technology' and key in expected.get(criterion,{}).get('procedure_keys',[])}
                by_proc={item.get('procedure_key'):item for item in applicability if isinstance(item,dict)}
                if set(by_proc)!=set(expected_at) or len(by_proc)!=len(applicability):
                    errors.append(f'at_applicability_coverage:{prefix}')
                for key,item in by_proc.items():
                    if item.get('decision_key')!=expected_at.get(key,{}).get('applicability_decision_key'):
                        errors.append(f'at_decision_key:{prefix}:{key}')
                    if set(item.get('source_clause_refs',[]))-set(clause_refs): errors.append(f'at_source_clause:{prefix}:{key}')
                    if not set(item.get('required_evidence_roles',[]))<=ALL_ROLES:
                        errors.append(f'at_evidence_role:{prefix}:{key}')
                    if {'assistive-technology-result','manual-procedure-result','external-evidence-result'}&set(item.get('required_evidence_roles',[])):
                        errors.append(f'at_circular_result_dependency:{prefix}:{key}')
                    if not set(item.get('allowed_additional_observation_fields',[]))<=OBSERVATION_FIELDS:
                        errors.append(f'at_additional_observation_field:{prefix}:{key}')
                    if item.get('missing_evidence_behavior')!='unknown': errors.append(f'at_missing_evidence_behavior:{prefix}:{key}')
        if set(actual.get('criterion_ref') for actual in versions.get('2.2',[])) and any(row.get('criterion_ref')=='4.1.1' for row in versions.get('2.2',[])):
            errors.append('wcag_2_2_semantic_contract_contains_4_1_1')
    except Exception as exc: errors.append(f'semantic_contracts_load:{exc}')
    return errors


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result=EvalResult('wcag-conformance-evaluation',eval_id)
    errors=validate_static_assets()
    result.add('WCAG-D001',not errors,'versioned requirement/procedure/semantic catalogs are structurally complete',evidence=errors or None)
    headings=set(re.findall(r'^##\s+(.+?)\s*$',text,re.M))
    baseline_sections={
        'Evaluation Input', 'WCAG-EM Step 1', 'WCAG-EM Step 2',
        'WCAG-EM Step 3', 'WCAG-EM Step 4', 'WCAG-EM Step 5',
        'Criterion Evaluation Plan', 'Sample Evaluation Results', 'Report Closure',
    }
    missing=sorted((baseline_sections | set(expected.get('required_sections',[])))-headings)
    result.add('WCAG-D002',not missing,'fixture-required report sections exist',evidence=missing or None)
    absent=[token for token in expected.get('required_tokens',[]) if token not in text]
    result.add('WCAG-D003',not absent,'fixture-required outcome/limitations are preserved',evidence=absent or None)
    forbidden=[token for token in expected.get('forbidden_tokens',[]) if token.casefold() in text.casefold()]
    result.add('WCAG-D004',not forbidden,'aggregated score and prohibited claims are absent',evidence=forbidden or None)
    return result
