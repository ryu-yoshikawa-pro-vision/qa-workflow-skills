"""Materialize the exact sample × variation × criterion × finite-procedure plan."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
from runtime_contract import static_data_fingerprint
from wcag_requirements import ASSETS, load_catalog, resolve_target


class CriterionPlanError(ValueError):
    pass


def load_procedure_catalog(assets_dir: Path = ASSETS) -> dict[str, Any]:
    path=assets_dir/'wcag-evaluation-procedure-catalog.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    rows=data.get('procedures')
    if not isinstance(rows,list): raise CriterionPlanError('procedure catalog schema invalid')
    keys=[row.get('procedure_key') for row in rows]
    if len(keys)!=len(set(keys)) or any(not isinstance(key,str) for key in keys): raise CriterionPlanError('procedure keys must be unique')
    common={'procedure_key','procedure_kind','applicability_mode','applicable_criterion_refs','required_capabilities',
            'required_input_refs','result_contract','completion_evidence','limitation_behavior'}
    for row in rows:
        if row.get('procedure_kind') not in {'machine','semantic','manual','assistive-technology','external-evidence'}:
            raise CriterionPlanError(f"unknown finite procedure kind: {row.get('procedure_key')}")
        kind=row['procedure_kind']; mode=row.get('applicability_mode')
        expected=common|({'machine_probe_keys','dispatch_key'} if kind=='machine' else
            {'semantic_decision_key'} if kind=='semantic' else
            {'required_evidence_kind','activation_source_procedure_key','activation_limitation_codes'} if mode=='machine-limitation' else
            {'required_evidence_kind','applicability_decision_key'} if kind=='assistive-technology' else
            {'required_evidence_kind','external_evidence_allowed'} if kind=='external-evidence' else
            {'required_evidence_kind'})
        if set(row)!=expected:
            raise CriterionPlanError(f"procedure catalog schema mismatch: {row.get('procedure_key')}")
        for field in ('applicable_criterion_refs','required_capabilities','required_input_refs','completion_evidence'):
            value=row.get(field)
            if not isinstance(value,list) or not value or any(not isinstance(item,str) or not item for item in value) or len(value)!=len(set(value)):
                if field=='applicable_criterion_refs' and isinstance(value,list) and not value:
                    continue
                raise CriterionPlanError(f"procedure catalog {field} is invalid: {row.get('procedure_key')}")
        contract=row.get('result_contract')
        if not isinstance(contract,dict) or not isinstance(contract.get('contract_kind'),str) or not contract.get('required_fields'):
            raise CriterionPlanError(f"procedure result contract is incomplete: {row.get('procedure_key')}")
        if not isinstance(row.get('limitation_behavior'),str) or not row['limitation_behavior'].strip():
            raise CriterionPlanError(f"procedure limitation behavior is missing: {row.get('procedure_key')}")
        if kind=='machine':
            probes=row.get('machine_probe_keys')
            if not isinstance(probes,list) or len(probes)!=len(set(probes)) or any(not isinstance(key,str) or not key for key in probes):
                raise CriterionPlanError(f"machine mapping missing or duplicated: {row['procedure_key']}")
            if not isinstance(row.get('dispatch_key'),str) or not row['dispatch_key']:
                raise CriterionPlanError(f"machine dispatch missing: {row['procedure_key']}")
            if set(probes)!=set(contract.get('required_machine_probe_keys',probes)):
                raise CriterionPlanError(f"machine result contract probe mapping mismatch: {row['procedure_key']}")
        elif kind=='semantic' and row['semantic_decision_key']!=row['procedure_key']:
            raise CriterionPlanError(f"semantic decision key mismatch: {row['procedure_key']}")
        elif mode=='machine-limitation':
            codes=row.get('activation_limitation_codes')
            if not isinstance(codes,list) or not codes or len(codes)!=len(set(codes)):
                raise CriterionPlanError(f"machine fallback limitation codes missing: {row['procedure_key']}")
        elif kind=='assistive-technology' and not row.get('applicability_decision_key'):
            raise CriterionPlanError(f"AT applicability decision key missing: {row['procedure_key']}")
        elif kind=='external-evidence' and row.get('external_evidence_allowed') is not True:
            raise CriterionPlanError(f"external evidence procedure must be explicitly allowed: {row['procedure_key']}")
    return data


def materialize_plan(*, wcag_version: str | None, level: str | None,
                     samples: list[dict[str, Any]], variations: list[dict[str, Any]],
                     process_memberships: dict[str,str] | None = None,
                     assets_dir: Path = ASSETS) -> dict[str, Any]:
    target=resolve_target(wcag_version,level,assets_dir=assets_dir)
    if target['status']!='supported':
        return {'status':target['status'],'reason':target['reason'],'criteria':[],'requests':[]}
    if not samples: raise CriterionPlanError('at least one canonical sample is required')
    if not variations: raise CriterionPlanError('selected samples require a closed presentation-variation inventory')
    if any(not isinstance(row.get('sample_ref'), str) or not row['sample_ref'].strip() for row in samples):
        raise CriterionPlanError('sample refs are required')
    if any(not isinstance(row.get('variation_ref'), str) or not row['variation_ref'].strip() for row in variations):
        raise CriterionPlanError('variation refs are required')
    fingerprint_re = re.compile(r'^sha256:[0-9a-f]{64}$')
    if any(not isinstance(row.get('identity_fingerprint'), str) or not fingerprint_re.fullmatch(row['identity_fingerprint']) for row in samples):
        raise CriterionPlanError('each canonical sample requires a SHA-256 identity fingerprint')
    if any(not isinstance(row.get('identity_fingerprint'), str) or not fingerprint_re.fullmatch(row['identity_fingerprint']) for row in variations):
        raise CriterionPlanError('each presentation variation requires a SHA-256 identity fingerprint')
    if len({row['sample_ref'] for row in samples})!=len(samples): raise CriterionPlanError('duplicate sample refs')
    if len({row['variation_ref'] for row in variations})!=len(variations): raise CriterionPlanError('duplicate variation refs')
    sample_refs={row['sample_ref'] for row in samples}
    if any(row['sample_ref'] not in sample_refs for row in variations):
        raise CriterionPlanError('presentation variation refers to an unknown sample')
    variation_pairs=[(row['sample_ref'],row['variation_ref']) for row in variations]
    if len(variation_pairs)!=len(set(variation_pairs)):
        raise CriterionPlanError('duplicate sample presentation variation')
    variations_by_sample={sample_ref:[row for row in variations if row['sample_ref']==sample_ref] for sample_ref in sample_refs}
    if any(not rows for rows in variations_by_sample.values()):
        raise CriterionPlanError('each selected sample requires at least one presentation variation')
    catalog=load_catalog(wcag_version,assets_dir=assets_dir)
    procedures=load_procedure_catalog(assets_dir)
    proc_by_key={row['procedure_key']:row for row in procedures['procedures']}
    required_criteria=set(target['required_success_criteria'])
    criterion_rows=[row for row in catalog['success_criteria'] if row['criterion_ref'] in required_criteria]
    if {row['criterion_ref'] for row in criterion_rows}!=required_criteria:
        raise CriterionPlanError('versioned requirement catalog does not close the requested target criteria')
    for criterion in criterion_rows:
        expected_keys=sorted(key for key,spec in proc_by_key.items() if criterion['criterion_ref'] in spec['applicable_criterion_refs'])
        if criterion['procedure_keys']!=expected_keys:
            raise CriterionPlanError(f"criterion procedure set does not match finite inventory: {criterion['criterion_ref']}")
        external_keys=[key for key in expected_keys if proc_by_key[key]['procedure_kind']=='external-evidence']
        if criterion['external_evidence_allowed'] != bool(external_keys):
            raise CriterionPlanError(f"external evidence assignment and criterion allowance disagree: {criterion['criterion_ref']}")
    rows=[]; requests=[]; execution_sequence=0
    for sample in samples:
        for variation in variations_by_sample[sample['sample_ref']]:
            for criterion in criterion_rows:
                row_index=len(rows)+1
                evaluation_ref=f'CRIT-EVAL-{row_index:06d}'
                execution_refs=[]
                for key in criterion['procedure_keys']:
                    procedure=proc_by_key.get(key)
                    if procedure is None: raise CriterionPlanError(f'procedure key absent from finite catalog: {key}')
                    execution_sequence+=1
                    execution_ref=f'PROC-EXEC-{execution_sequence:06d}'
                    request_ref=None
                    if procedure['procedure_kind']=='machine':
                        for probe_key in procedure['machine_probe_keys']:
                            req={'request_kind':'wcag-machine-probe','observation_request_ref':f'WCAG-OBS-{len(requests)+1:06d}',
                                 'criterion_evaluation_ref':evaluation_ref,'procedure_execution_ref':execution_ref,
                                 'machine_probe_key':probe_key,'sample_ref':sample['sample_ref'],'variation_ref':variation['variation_ref'],
                                 'process_ref':(process_memberships or {}).get(sample['sample_ref']),
                                 'requirement_ref':criterion['criterion_ref'],
                                 'currentness_dependency':{'sample_identity_fingerprint':sample.get('identity_fingerprint'),
                                                           'variation_identity_fingerprint':variation.get('identity_fingerprint')},
                                 'target_identity':sample.get('target_identity',sample['sample_ref']),
                                 'required_browser_capability':probe_key}
                            request_ref=req['observation_request_ref']
                            signature=json.dumps(req,ensure_ascii=False,sort_keys=True,separators=(',',':'))
                            import hashlib
                            req['request_signature']='sha256:'+hashlib.sha256(signature.encode('utf-8')).hexdigest()
                            requests.append(req)
                    execution_refs.append({'procedure_execution_ref':execution_ref,'procedure_key':key,
                                           'procedure_kind':procedure['procedure_kind'],'applicability_mode':procedure['applicability_mode'],
                                           'status':'pending','result':None,'observation_request_refs':[request_ref] if request_ref else [],
                                           'evidence_refs':[]})
                rows.append({'criterion_evaluation_ref':evaluation_ref,'sample_ref':sample['sample_ref'],
                             'variation_ref':variation['variation_ref'],'process_ref':(process_memberships or {}).get(sample['sample_ref']),
                             'criterion_ref':criterion['criterion_ref'],'level':criterion['level'],'procedure_executions':execution_refs,
                             'applicable_population':'unknown','execution_status':'pending','result':None,
                             'observation_refs':[],'measurement_refs':[],'act_rule_result_refs':[],'semantic_refs':[],
                             'manual_refs':[],'assistive_technology_refs':[],'external_evidence_refs':[],'limitation':None})
    return {'status':'ready','wcag_version':wcag_version,'level':level,'catalog_fingerprint':target['catalog_fingerprint'],
            'procedure_catalog_fingerprint':static_data_fingerprint(assets_dir/'wcag-evaluation-procedure-catalog.json'),
            'expected_row_count':sum(len(variations_by_sample[sample['sample_ref']]) for sample in samples)*len(target['required_success_criteria']),
            'criteria':rows,'requests':requests}


def resolve_external_evidence_candidates(candidates: list[dict[str, Any]], *, allowed_source_ids: set[str],
                                         current_source_revisions: dict[str, str],
                                         environment_fingerprint: str, scope_fingerprint: str) -> dict[str, Any]:
    """Close optional evidence applicability from exact current source/scope identity."""
    if not isinstance(candidates,list) or not isinstance(allowed_source_ids,set) or not isinstance(current_source_revisions,dict):
        raise CriterionPlanError('external evidence inventory contract is invalid')
    if not re.fullmatch(r'^sha256:[0-9a-f]{64}$',str(environment_fingerprint)) or not re.fullmatch(r'^sha256:[0-9a-f]{64}$',str(scope_fingerprint)):
        raise CriterionPlanError('current external-evidence environment and scope fingerprints are required')
    allowed_fields={'evidence_ref','source_id','source_revision','environment_fingerprint','scope_fingerprint','freshness_status','evidence_kind'}
    seen=set(); current=[]; rejected=[]
    for index,candidate in enumerate(candidates):
        if not isinstance(candidate,dict) or set(candidate)!=allowed_fields:
            raise CriterionPlanError(f'external evidence candidate schema mismatch at {index}')
        if any(not isinstance(candidate[key],str) or not candidate[key].strip() for key in allowed_fields):
            raise CriterionPlanError(f'external evidence candidate values are required at {index}')
        ref=candidate['evidence_ref']
        if ref in seen: raise CriterionPlanError('duplicate external evidence candidate ref')
        seen.add(ref)
        if candidate['source_id'] not in allowed_source_ids:
            raise CriterionPlanError(f'external evidence source is outside the approved registry: {candidate["source_id"]}')
        reasons=[]
        if candidate['evidence_kind']!='external-evidence': reasons.append('evidence-kind-mismatch')
        if candidate['freshness_status']!='current': reasons.append('stale-evidence')
        if current_source_revisions.get(candidate['source_id'])!=candidate['source_revision']: reasons.append('source-revision-mismatch')
        if candidate['environment_fingerprint']!=environment_fingerprint: reasons.append('environment-mismatch')
        if candidate['scope_fingerprint']!=scope_fingerprint: reasons.append('scope-mismatch')
        if reasons: rejected.append({'evidence_ref':ref,'reasons':sorted(reasons)})
        else: current.append(ref)
    return {'applicability':'applicable' if current else 'not-applicable',
            'basis_refs':sorted(current) if current else ['external-evidence-inventory:checked'],
            'current_evidence_refs':sorted(current),'candidate_refs':sorted(seen),
            'rejected_candidates':sorted(rejected,key=lambda row:row['evidence_ref'])}


def close_criterion(result: dict[str, Any], *, procedure_results: dict[str, dict[str, Any]], applicable_population: str,
                    semantic_result: str, reason: str, evidence_refs: list[str],
                    population_evidence_refs: list[str] | None = None,
                    violation_evidence_refs: list[str] | None = None,
                    external_evidence_candidates: list[dict[str, Any]] | None = None,
                    allowed_external_source_ids: set[str] | None = None,
                    current_external_source_revisions: dict[str, str] | None = None,
                    current_environment_fingerprint: str | None = None,
                    current_scope_fingerprint: str | None = None) -> dict[str, Any]:
    if applicable_population not in {'present','none','unknown'}:
        raise CriterionPlanError('invalid applicable_population')
    if semantic_result not in {'satisfied','not-satisfied','undetermined'}:
        raise CriterionPlanError('invalid semantic result')
    if not isinstance(reason,str) or not reason.strip():
        raise CriterionPlanError('every semantic criterion decision requires a judgment reason')
    if not isinstance(evidence_refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in evidence_refs):
        raise CriterionPlanError('criterion evidence refs must be non-empty strings')
    if len(evidence_refs)!=len(set(evidence_refs)):
        raise CriterionPlanError('criterion evidence refs must be unique')
    population_evidence_refs=population_evidence_refs or []
    violation_evidence_refs=violation_evidence_refs or []
    if any(not isinstance(ref,str) or not ref.strip() for ref in population_evidence_refs+violation_evidence_refs):
        raise CriterionPlanError('population and violation evidence refs must be non-empty strings')
    procedures=load_procedure_catalog()['procedures']
    procedure_by_key={row['procedure_key']:row for row in procedures}
    execution_by_key={row['procedure_key']:row for row in result['procedure_executions']}
    expected_execution_refs={row['procedure_execution_ref'] for row in result['procedure_executions']}
    if set(procedure_results)-expected_execution_refs:
        raise CriterionPlanError('procedure result contains a non-current execution reference')
    normalized=[]; unresolved=[]; blocked=[]; current_evidence=set(evidence_refs)
    external_evidence_candidates=external_evidence_candidates or []
    for execution in result['procedure_executions']:
        execution_ref=execution['procedure_execution_ref']
        spec=procedure_by_key.get(execution['procedure_key'])
        if spec is None: raise CriterionPlanError(f"unregistered procedure: {execution['procedure_key']}")
        value=procedure_results.get(execution_ref)
        if value is None:
            unresolved.append(execution_ref); normalized.append({**execution,'applicability':'unknown','status':'pending'})
            continue
        allowed={'status','applicability','applicability_basis_refs','applicability_dependency_refs','result','evidence_refs','reason','limitation_code','activation_source_procedure_ref','blocker'}
        if set(value)-allowed: raise CriterionPlanError(f"unknown procedure result fields: {execution_ref}")
        status=value.get('status')
        if status not in {'pending','in-progress','complete','blocked'}: raise CriterionPlanError(f"invalid procedure execution status: {execution_ref}")
        basis=value.get('applicability_basis_refs',[])
        proc_evidence=value.get('evidence_refs',[])
        applicability_dependencies=value.get('applicability_dependency_refs',[])
        if not isinstance(basis,list) or any(not isinstance(ref,str) or not ref.strip() for ref in basis) or len(basis)!=len(set(basis)):
            raise CriterionPlanError(f"invalid applicability basis refs: {execution_ref}")
        if not isinstance(proc_evidence,list) or any(not isinstance(ref,str) or not ref.strip() for ref in proc_evidence) or len(proc_evidence)!=len(set(proc_evidence)):
            raise CriterionPlanError(f"invalid procedure evidence refs: {execution_ref}")
        if not isinstance(applicability_dependencies,list) or any(not isinstance(ref,str) or not ref.strip() for ref in applicability_dependencies):
            raise CriterionPlanError(f"invalid applicability dependency refs: {execution_ref}")
        mode=spec['applicability_mode']; applicability=value.get('applicability')
        if mode=='always':
            if applicability not in (None,'applicable'):
                raise CriterionPlanError(f"always-applicable procedure cannot be skipped: {execution_ref}")
            applicability='applicable'
            if not basis: basis=['catalog:always-applicable']
        elif mode=='machine-limitation':
            source=execution_by_key.get(spec['activation_source_procedure_key'])
            if source is None: raise CriterionPlanError(f"machine fallback source missing: {execution_ref}")
            source_value=procedure_results.get(source['procedure_execution_ref'])
            if source_value is None or source_value.get('status')!='complete':
                applicability='unknown'
            else:
                limitation=source_value.get('limitation_code')
                applicability='applicable' if limitation in spec['activation_limitation_codes'] else 'not-applicable'
                basis=[source['procedure_execution_ref']]
            if value.get('activation_source_procedure_ref') not in (None, source['procedure_execution_ref']):
                raise CriterionPlanError(f"manual fallback activation source mismatch: {execution_ref}")
        elif mode=='external-evidence-available':
            if spec.get('external_evidence_allowed') is not True:
                raise CriterionPlanError(f"external evidence procedure is not allowed for this requirement: {execution_ref}")
            if (current_environment_fingerprint is None or current_scope_fingerprint is None or
                    current_external_source_revisions is None or allowed_external_source_ids is None):
                if external_evidence_candidates:
                    raise CriterionPlanError('current external evidence baseline is required when candidates exist')
                decision={'applicability':'not-applicable','basis_refs':['external-evidence-inventory:empty'],
                          'current_evidence_refs':[],'candidate_refs':[],'rejected_candidates':[]}
            else:
                decision=resolve_external_evidence_candidates(external_evidence_candidates,
                    allowed_source_ids=allowed_external_source_ids,
                    current_source_revisions=current_external_source_revisions,
                    environment_fingerprint=current_environment_fingerprint,
                    scope_fingerprint=current_scope_fingerprint)
            applicability=decision['applicability']; basis=decision['basis_refs']
            if applicability=='applicable':
                if status!='complete' or set(proc_evidence)!=set(decision['current_evidence_refs']) or value.get('result') is None:
                    raise CriterionPlanError(f"current external evidence must be the exact procedure input: {execution_ref}")
            elif status!='complete' or value.get('result') is not None:
                raise CriterionPlanError(f"no current external evidence must close as not-applicable: {execution_ref}")
        elif mode=='semantic':
            if applicability not in {'applicable','not-applicable','unknown'} or not basis:
                raise CriterionPlanError(f"semantic applicability needs a decision and basis: {execution_ref}")
            if spec['procedure_kind']=='assistive-technology':
                circular_refs=set(proc_evidence)
                circular_refs.update(ref for row in result['procedure_executions']
                    if row['procedure_key'].startswith('s-wcag-')
                    for ref in procedure_results.get(row['procedure_execution_ref'],{}).get('evidence_refs',[]))
                if circular_refs & set(applicability_dependencies):
                    raise CriterionPlanError(f"AT applicability depends on AT/final semantic result: {execution_ref}")
        if applicability not in {'applicable','not-applicable','unknown'}:
            raise CriterionPlanError(f"procedure applicability missing: {execution_ref}")
        if applicability=='not-applicable':
            if status!='complete' or value.get('result') is not None or not basis:
                raise CriterionPlanError(f"not-applicable procedure must be complete with null result and basis: {execution_ref}")
        elif applicability=='unknown':
            if status=='complete': raise CriterionPlanError(f"unknown applicability cannot complete: {execution_ref}")
            if status=='blocked':
                if not isinstance(value.get('blocker'),str) or not value['blocker'].strip():
                    raise CriterionPlanError(f"blocked procedure requires blocker: {execution_ref}")
                blocked.append(execution_ref)
            else:
                unresolved.append(execution_ref)
        elif status=='blocked':
            blocked.append(execution_ref)
            if not isinstance(value.get('blocker'),str) or not value['blocker'].strip():
                raise CriterionPlanError(f"blocked procedure requires blocker: {execution_ref}")
        elif status!='complete':
            unresolved.append(execution_ref)
        elif value.get('result') is None or not proc_evidence:
            raise CriterionPlanError(f"applicable completed procedure needs a result and evidence: {execution_ref}")
        if status=='complete' and mode=='machine-limitation' and applicability=='applicable' and not value.get('result'):
            raise CriterionPlanError(f"manual fallback completion requires evidence result: {execution_ref}")
        current_evidence.update(proc_evidence)
        normalized.append({**execution,'applicability':applicability,'applicability_basis_refs':sorted(set(basis)),
                           'status':status,'result':value.get('result'),'evidence_refs':sorted(set(proc_evidence)),
                           'reason':value.get('reason'),'limitation_code':value.get('limitation_code'),
                           'activation_source_procedure_ref':value.get('activation_source_procedure_ref'),
                           'blocker':value.get('blocker'),
                           'applicability_dependency_refs':sorted(set(applicability_dependencies)),
                           'rejected_external_evidence':decision['rejected_candidates'] if mode=='external-evidence-available' else []})
    semantic_rows=[row for row in normalized if row['procedure_key'].startswith('s-wcag-')]
    if len(semantic_rows)!=1:
        raise CriterionPlanError('criterion plan requires exactly one criterion-specific semantic procedure')
    semantic_row=semantic_rows[0]
    at_rows=[row for row in normalized if row['procedure_kind']=='assistive-technology']
    if any(row['applicability']=='unknown' for row in at_rows) and semantic_row['status']=='complete':
        raise CriterionPlanError('final semantic procedure cannot run before AT applicability is closed')
    semantic_value=procedure_results.get(semantic_row['procedure_execution_ref'],{})
    required_semantic_inputs=set()
    for row in normalized:
        if row is semantic_row:
            continue
        if row['applicability']=='applicable': required_semantic_inputs.update(row['evidence_refs'])
        elif row['applicability']=='not-applicable': required_semantic_inputs.update(row['applicability_basis_refs'])
    if semantic_row['status']=='complete' and not required_semantic_inputs<=set(semantic_value.get('evidence_refs',[])):
        raise CriterionPlanError('final semantic result omits current applicable procedure evidence or not-applicable basis')
    if blocked:
        return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
                'execution_status':'blocked','result':None,'limitation':'required_procedure_blocked',
                'blocker_refs':sorted(blocked)}
    if unresolved:
        return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
                'execution_status':'in-progress','result':None,'limitation':'required_procedure_unclosed',
                'open_procedure_execution_refs':sorted(set(unresolved))}
    if applicable_population=='none':
        if not population_evidence_refs or semantic_result!='satisfied':
            return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
                    'execution_status':'complete','result':'undetermined','limitation':'population_none_not_proven_complete',
                    'judgment_reason':reason,'evidence_refs':sorted(current_evidence)}
        current_evidence.update(population_evidence_refs)
    if applicable_population=='unknown' or not current_evidence:
        return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
                'execution_status':'complete','result':'undetermined','limitation':'population_or_evidence_unresolved',
                'judgment_reason':reason,'evidence_refs':sorted(current_evidence)}
    if semantic_result=='not-satisfied' and not violation_evidence_refs:
        return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
                'execution_status':'complete','result':'undetermined','limitation':'violation_evidence_missing',
                'judgment_reason':reason,'evidence_refs':sorted(current_evidence)}
    current_evidence.update(violation_evidence_refs)
    return {**result,'procedure_executions':normalized,'applicable_population':applicable_population,
            'execution_status':'complete','result':semantic_result,'judgment_reason':reason,
            'evidence_refs':sorted(current_evidence),'violation_evidence_refs':sorted(set(violation_evidence_refs))}


def materialize_sample_results(criterion_rows: list[dict[str, Any]], *, current_criterion_evaluation_refs: set[str],
                               sample_kinds: dict[str,str]) -> list[dict[str, Any]]:
    if not isinstance(current_criterion_evaluation_refs,set) or any(not isinstance(ref,str) for ref in current_criterion_evaluation_refs):
        raise CriterionPlanError('current criterion evaluation refs must be an explicit ref set')
    rows_by_ref={}
    for row in criterion_rows:
        ref=row.get('criterion_evaluation_ref')
        if not isinstance(ref,str) or not ref or ref in rows_by_ref: raise CriterionPlanError('criterion evaluation refs must be unique and explicit')
        rows_by_ref[ref]=row
    if not current_criterion_evaluation_refs<=set(rows_by_ref): raise CriterionPlanError('current criterion evaluation ref is missing')
    sample_refs={rows_by_ref[ref].get('sample_ref') for ref in current_criterion_evaluation_refs}
    if not isinstance(sample_kinds,dict) or set(sample_kinds)!=sample_refs or any(
        not isinstance(kind,str) or not kind.strip() for kind in sample_kinds.values()):
        raise CriterionPlanError('current sample refs require an explicit sample kind mapping')
    results=[]
    current_rows=sorted((rows_by_ref[ref] for ref in current_criterion_evaluation_refs),
                        key=lambda row:(row['sample_ref'],row['variation_ref'],row['criterion_ref'],row['criterion_evaluation_ref']))
    for row in current_rows:
        if row.get('execution_status')!='complete' or row.get('result') not in {'satisfied','not-satisfied','undetermined'}:
            continue
        results.append({'sample_result_ref':f'WCAG-RES-{len(results)+1:03d}','sample_ref':row['sample_ref'],
                        'variation_ref':row['variation_ref'],'sample_kind':sample_kinds[row['sample_ref']],
                        'process_ref':row.get('process_ref'),'requirement_ref':row['criterion_ref'],
                        'criterion_evaluation_ref':row['criterion_evaluation_ref'],'result':row['result'],
                        'observation_refs':row.get('observation_refs',[]),'test_rule_result_refs':row.get('act_rule_result_refs',[]),
                        'evidence_refs':row.get('evidence_refs',[]),'unmet_example_refs':row.get('violation_evidence_refs',[]),
                        'freshness_status':'current','limitation':row.get('limitation')})
    return results
