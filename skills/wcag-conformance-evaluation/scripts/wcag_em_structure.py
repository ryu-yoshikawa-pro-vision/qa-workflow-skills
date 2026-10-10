"""WCAG-EM 2 report and workflow structures; machine-owned IDs and closures."""
from __future__ import annotations
from datetime import date
import json
import re
from typing import Any
from wcag_requirements import load_catalog, resolve_target
from sampling import fingerprint, random_target_count, sample_identity_registry, validate_random_selection, compare_samples
from wcag_criterion_plan import CriterionPlanError, validate_materialized_plan

SCOPE_ROWS=("third-party-content","language-versions","responsive-device-variations","separately-hosted-product-areas","authenticated-restricted-views")
REPORT_STEPS=("1.1","1.2","1.3","1.4","2.1","2.2","2.3","2.4","2.5",
              "3.1","3.2","3.3","4.1","4.2","4.3")
ADDITIONAL_REQUIREMENT_STEPS=set(REPORT_STEPS)|{"5.1","5.2","5.3","5.4","5.5"}
ACCESSIBLE_OUTPUT_CHECKS=("heading_hierarchy","table_headers","image_text_descriptions",
                          "color_independent_state","descriptive_link_text")
PARTIAL_REASONS={"third-party-content","lack-of-accessibility-support-for-languages"}
_HANDOFF_REF = re.compile(r"^HANDOFF-(\d{3,})$")
_DOCUMENT_IDENTITY = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")


class EvaluationStructureError(ValueError):
    pass


def initialize_evaluation(inputs: dict[str, Any]) -> dict[str, Any]:
    required={"artifact_ref","artifact_revision","evaluator","evaluation_date","live_web_target","commissioner","wcag_version","level","product_scope","product_enclosure",
              "accessibility_support_baseline","browser_user_agent_baseline","role_permission_environment",
              "side_effect_scope","cleanup_scope","evaluation_period"}
    missing=sorted(key for key in required if inputs.get(key) in (None,"",[],{}))
    if missing:
        resolved=resolve_target(inputs.get('wcag_version'),inputs.get('level'))
        return {'status':resolved['status'] if resolved['status']!='supported' else 'unresolved',
                'blockers':[{'reason':'required_input_missing','fields':missing}], 'evaluation_ref':None}
    target=resolve_target(inputs['wcag_version'],inputs['level'])
    if target['status']!='supported': return {'status':target['status'],'blockers':[target], 'evaluation_ref':None}
    try:
        date.fromisoformat(inputs['evaluation_date'])
    except (TypeError, ValueError):
        return {'status':'unresolved','blockers':[{'reason':'invalid_evaluation_date','field':'evaluation_date'}],
                'evaluation_ref':inputs['artifact_ref'],'revision':inputs['artifact_revision']}
    return {'status':'ready','evaluation_ref':inputs['artifact_ref'],'revision':inputs['artifact_revision'],'target':target,
            'input_fingerprint':fingerprint(inputs),'scope_coverage':[{'scope_ref':f'SCOPE-{i:03d}','scope_key':key,
              'decision':'unresolved','reason':None,'evidence_refs':[]} for i,key in enumerate(SCOPE_ROWS,1)],
            'accessibility_support_baseline':{'revision':1,'entries':inputs['accessibility_support_baseline']},
            'additional_requirements':[],'handoffs':[],'sampling':{'procedure_status':'unresolved','selected_sample_refs':[]},
            'complete_processes':[],'criterion_plan':[],'sample_results':[],'report_status':'not-started'}


def allocate_observation_handoff_ref(existing_handoffs: list[dict[str, Any]]) -> dict[str, Any]:
    """Allocate the next monotonic, artifact-local WCAG observation handoff ref."""
    if not isinstance(existing_handoffs, list):
        raise EvaluationStructureError('handoffs must be an array')
    seen: set[str] = set()
    highest = 0
    for row in existing_handoffs:
        if not isinstance(row, dict):
            raise EvaluationStructureError('handoff row must be an object')
        handoff_ref = row.get('handoff_ref')
        match = _HANDOFF_REF.fullmatch(handoff_ref) if isinstance(handoff_ref, str) else None
        if match is None:
            raise EvaluationStructureError('handoff ref is invalid')
        if handoff_ref in seen:
            raise EvaluationStructureError('handoff ref is duplicate')
        seen.add(handoff_ref)
        highest = max(highest, int(match.group(1)))
    return {'handoff_ref': f'HANDOFF-{highest + 1:03d}', 'existing_handoff_count': len(seen)}


def materialize_scope_coverage(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    """Close every fixed WCAG-EM Step 1.1 product-boundary question."""
    if not isinstance(drafts,list):
        raise EvaluationStructureError('scope coverage drafts must be an array')
    by_key={}
    required={'scope_key','decision','reason','evidence_refs'}
    for draft in drafts:
        if not isinstance(draft,dict) or set(draft)!=required:
            raise EvaluationStructureError('scope coverage draft schema mismatch')
        key=draft['scope_key']
        if key not in SCOPE_ROWS or key in by_key:
            raise EvaluationStructureError('scope coverage key is unknown or duplicate')
        decision=draft['decision']
        if decision not in {'in-scope','out-of-product','unresolved'}:
            raise EvaluationStructureError('scope coverage decision is invalid')
        reason=draft['reason']
        if reason is not None and (not isinstance(reason,str) or not reason.strip()):
            raise EvaluationStructureError('scope coverage reason must be a non-empty string or null')
        evidence=draft['evidence_refs']
        if not isinstance(evidence,list) or any(not isinstance(ref,str) or not ref.strip() for ref in evidence) or len(evidence)!=len(set(evidence)):
            raise EvaluationStructureError('scope coverage evidence refs must be unique non-empty refs')
        if decision=='unresolved':
            by_key[key]={'decision':decision,'reason':reason,'evidence_refs':sorted(evidence)}
            continue
        if not evidence:
            raise EvaluationStructureError('closed scope coverage requires evidence refs')
        if decision=='out-of-product' and reason is None:
            raise EvaluationStructureError('out-of-product scope coverage requires a boundary reason')
        by_key[key]={'decision':decision,'reason':reason,'evidence_refs':sorted(evidence)}
    missing=sorted(set(SCOPE_ROWS)-set(by_key))
    rows=[]
    for index,key in enumerate(SCOPE_ROWS,1):
        value=by_key.get(key,{'decision':'unresolved','reason':None,'evidence_refs':[]})
        rows.append({'scope_ref':f'SCOPE-{index:03d}','scope_key':key,**value})
    unresolved=[row['scope_ref'] for row in rows if row['decision']=='unresolved']
    return {'status':'ready' if not unresolved else 'unresolved','scope_coverage':rows,
            'missing_scope_keys':missing,'unresolved_scope_refs':unresolved}


def materialize_additional_requirements(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=[]
    for i,draft in enumerate(drafts,1):
        fields={'draft_key','requester','request_text','purpose_in_scope','out_of_scope_reason','affected_steps',
                'semantic_completion_condition','required_evidence_refs','closure_evidence_refs','output_refs'}
        if set(draft)!=fields: raise EvaluationStructureError('additional requirement draft schema mismatch')
        if draft['purpose_in_scope'] not in {True,False,None}: raise EvaluationStructureError('purpose_in_scope must be a semantic decision')
        for field in ('draft_key','requester','request_text','semantic_completion_condition'):
            if not isinstance(draft[field],str) or not draft[field].strip():
                raise EvaluationStructureError(f'additional requirement {field} is required')
        affected=draft['affected_steps']
        if not isinstance(affected,list) or not affected or len(affected)!=len(set(affected)) or any(step not in ADDITIONAL_REQUIREMENT_STEPS for step in affected):
            raise EvaluationStructureError('additional requirement affected steps must be unique WCAG-EM step keys')
        required_evidence=draft['required_evidence_refs']
        closure_evidence=draft['closure_evidence_refs']
        output_refs=draft['output_refs']
        for label,refs in (('required_evidence_refs',required_evidence),('closure_evidence_refs',closure_evidence),('output_refs',output_refs)):
            if not isinstance(refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in refs) or len(refs)!=len(set(refs)):
                raise EvaluationStructureError(f'additional requirement {label} must be unique non-empty refs')
        if draft['purpose_in_scope'] is False:
            reason=draft['out_of_scope_reason']
            status='out-of-scope' if isinstance(reason,str) and reason.strip() else 'blocked'
            blocker=None if status=='out-of-scope' else 'explicit_out_of_scope_reason_required'
        elif draft['purpose_in_scope'] is None:
            status='blocked'; reason=None; blocker='purpose_scope_decision_unresolved'
        else:
            reason=None
            closed=set(required_evidence)<=set(closure_evidence) and bool(output_refs)
            status='applied' if closed else 'blocked'
            blocker=None if closed else 'in_scope_requirement_closure_incomplete'
        rows.append({'additional_requirement_ref':f'ADDREQ-{i:03d}','draft_key':draft['draft_key'],'requester':draft['requester'],
          'request_text':draft['request_text'],'affected_steps':draft['affected_steps'],
          'semantic_completion_condition':draft['semantic_completion_condition'],'status':status,
          'required_evidence_refs':sorted(required_evidence),'closure_evidence_refs':sorted(closure_evidence),
          'output_refs':sorted(output_refs),'reason':reason,'blocker':blocker})
    return rows


def materialize_variations(samples: list[dict[str, Any]], drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=[]; seen=set(); sample_refs={row.get('sample_ref') for row in samples}
    if not sample_refs or None in sample_refs or len(sample_refs)!=len(samples):
        raise EvaluationStructureError('sample inventory requires unique sample refs')
    seen_samples=set()
    for draft in drafts:
        expected={'sample_ref','draft_key','source_kind','source_ref','state_identity','variation_description',
                  'presentation_condition','environment_ref','viewport_condition_refs','responsive_condition_refs',
                  'required','completeness','evidence_refs'}
        if set(draft)!=expected:
            raise EvaluationStructureError('variation draft schema mismatch')
        if draft['sample_ref'] not in sample_refs:
            raise EvaluationStructureError('variation refers to unknown sample')
        if draft['source_kind'] not in {'project-authority','current-observation','responsive-inventory','user-agent-device-condition'}:
            raise EvaluationStructureError('variation source kind is outside the fixed inventory')
        if type(draft['required']) is not bool or draft['required'] is not True:
            raise EvaluationStructureError('variation candidates must be semantically confirmed as required')
        if draft['completeness'] not in {'complete','incomplete','unknown','unreachable'}:
            raise EvaluationStructureError('variation completeness status is invalid')
        for field in ('draft_key','source_ref','state_identity','variation_description','presentation_condition'):
            if not isinstance(draft[field],str) or not draft[field].strip():
                raise EvaluationStructureError(f'variation {field} is required')
        for field in ('viewport_condition_refs','responsive_condition_refs','evidence_refs'):
            values=draft[field]
            if not isinstance(values,list) or any(not isinstance(ref,str) or not ref.strip() for ref in values) or len(values)!=len(set(values)):
                raise EvaluationStructureError(f'variation {field} must be unique non-empty refs')
        if not _nonempty_refs(draft['evidence_refs']):
            raise EvaluationStructureError('required variation evidence refs cannot be empty')
        if draft['environment_ref'] is not None and (not isinstance(draft['environment_ref'],str) or not draft['environment_ref'].strip()):
            raise EvaluationStructureError('variation environment ref must be a non-empty string or null')
        identity=fingerprint({k:draft[k] for k in ('sample_ref','source_kind','source_ref','state_identity','presentation_condition')})
        if identity in seen:
            raise EvaluationStructureError('duplicate presentation variation identity')
        seen.add(identity)
        seen_samples.add(draft['sample_ref'])
        coverage='required' if draft['completeness']=='complete' else ('blocked' if draft['completeness']=='unreachable' else 'undetermined')
        rows.append({'variation_ref':f'VAR-{len(rows)+1:03d}','sample_ref':draft['sample_ref'],
                     'source_kind':draft['source_kind'],'source_ref':draft['source_ref'],
                     'variation_description':draft['variation_description'],
                     'presentation_condition':draft['presentation_condition'],'environment_ref':draft['environment_ref'],
                     'viewport_condition_refs':sorted(draft['viewport_condition_refs']),
                     'responsive_condition_refs':sorted(draft['responsive_condition_refs']),
                     'identity_fingerprint':identity,'required':True,'completeness':draft['completeness'],
                     'coverage_status':coverage,'evidence_refs':sorted(draft['evidence_refs'])})
    if seen_samples!=sample_refs:
        raise EvaluationStructureError(f'variation inventory missing selected samples: {sorted(sample_refs-seen_samples)}')
    return rows


def validate_sampling_skip(*, complete_inventory: bool, inventory_refs: list[str], all_in_scope_selected: list[str],
                           rationale: str) -> dict[str, Any]:
    if not complete_inventory or not inventory_refs or set(inventory_refs)!=set(all_in_scope_selected) or not rationale.strip():
        raise EvaluationStructureError('sampling may be skipped only for complete, fully selected inventory with rationale')
    return {'procedure_status':'skipped','rationale':rationale,'inventory_refs':sorted(set(inventory_refs)),
            'selected_sample_refs':sorted(set(all_in_scope_selected)),
            'structured_sample_status':'not-applicable','random_sample_status':'not-applicable',
            'comparison_status':'not-applicable','complete_processes_required':True,'step_4_2_required':True}


def extend_accessibility_support_baseline(*, baseline_ref: str, revision: int,
        environment_refs: list[str], formal_evidence_environment_refs: list[str],
        diagnostic_only_environment_refs: list[str], extension_reason: str | None,
        sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extend the current baseline only for environments used as formal evidence."""
    if not isinstance(baseline_ref,str) or not baseline_ref.strip():
        raise EvaluationStructureError('accessibility baseline identity is required')
    if isinstance(revision,bool) or not isinstance(revision,int) or revision < 1:
        raise EvaluationStructureError('accessibility baseline revision must be a positive integer')
    inventories=(('environment_refs',environment_refs),
        ('formal_evidence_environment_refs',formal_evidence_environment_refs),
        ('diagnostic_only_environment_refs',diagnostic_only_environment_refs))
    for label,refs in inventories:
        if not isinstance(refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in refs) or len(refs)!=len(set(refs)):
            raise EvaluationStructureError(f'{label} must be unique non-empty environment refs')
    if set(formal_evidence_environment_refs)&set(diagnostic_only_environment_refs):
        raise EvaluationStructureError('an environment cannot be both formal evidence and diagnostic-only')
    if not isinstance(sample_results,list):
        raise EvaluationStructureError('baseline freshness input must be a sample result array')
    sample_result_refs=set(); normalized_results=[]
    for row in sample_results:
        if not isinstance(row,dict) or set(row)!={'sample_result_ref','baseline_revision','environment_refs','freshness_status'}:
            raise EvaluationStructureError('baseline freshness sample result schema mismatch')
        result_ref=row['sample_result_ref']; result_revision=row['baseline_revision']; result_environments=row['environment_refs']
        if not isinstance(result_ref,str) or not result_ref.strip() or result_ref in sample_result_refs:
            raise EvaluationStructureError('baseline freshness sample result ref is missing or duplicate')
        if isinstance(result_revision,bool) or not isinstance(result_revision,int) or result_revision<1:
            raise EvaluationStructureError('sample result baseline revision must be positive')
        if row['freshness_status'] not in {'current','stale','unknown'}:
            raise EvaluationStructureError('sample result freshness status is invalid')
        if not isinstance(result_environments,list) or any(not isinstance(ref,str) or not ref.strip() for ref in result_environments) or len(result_environments)!=len(set(result_environments)):
            raise EvaluationStructureError('sample result environment refs must be unique non-empty refs')
        sample_result_refs.add(result_ref)
        normalized_results.append(row)
    added=sorted(set(formal_evidence_environment_refs)-set(environment_refs))
    if not added:
        freshness=[{'sample_result_ref':row['sample_result_ref'],'freshness_status':row['freshness_status'],
                    'reason':None} for row in normalized_results]
        return {'status':'unchanged','baseline_ref':baseline_ref,'revision':revision,
            'previous_baseline_ref':None,'environment_refs':sorted(set(environment_refs)),
            'formal_evidence_environment_refs':sorted(set(formal_evidence_environment_refs)),
            'diagnostic_only_environment_refs':sorted(set(diagnostic_only_environment_refs)),
            'added_environment_refs':[],'extension_reason':None,'sample_result_freshness':freshness,
            'stale_sample_result_refs':[]}
    if not isinstance(extension_reason,str) or not extension_reason.strip():
        return {'status':'blocked','baseline_ref':baseline_ref,'revision':revision,
            'added_environment_refs':added,'blocker':'formal_baseline_extension_reason_required'}
    next_revision=revision+1
    freshness=[]; stale=[]
    for row in normalized_results:
        affected=bool(set(row['environment_refs'])&set(added))
        status=row['freshness_status']; reason=None
        if affected and row['baseline_revision']!=next_revision:
            status='stale'; reason='accessibility_support_baseline_revision_changed'
            stale.append(row['sample_result_ref'])
        freshness.append({'sample_result_ref':row['sample_result_ref'],'freshness_status':status,'reason':reason})
    return {'status':'extended','baseline_ref':baseline_ref,'revision':revision+1,
        'previous_baseline_ref':baseline_ref,'environment_refs':sorted(set(environment_refs)|set(added)),
        'formal_evidence_environment_refs':sorted(set(formal_evidence_environment_refs)),
        'diagnostic_only_environment_refs':sorted(set(diagnostic_only_environment_refs)),
        'added_environment_refs':added,'extension_reason':extension_reason.strip(),
        'sample_result_freshness':freshness,'stale_sample_result_refs':sorted(stale)}


def close_conforming_alternate_version(*, version: str, level: str, primary_sample_ref: str,
                                       alternate_version_ref: str, condition_results: list[dict[str,Any]],
                                       criterion_results: list[dict[str,Any]]) -> dict[str,Any]:
    target=resolve_target(version,level)
    if target['status']!='supported':
        return {'status':'blocked','reason':'unsupported_target','target_status':target['status']}
    contract=load_catalog(version)['conforming_alternate_version_contract']
    if not all(isinstance(value,str) and value.strip() for value in (primary_sample_ref,alternate_version_ref)):
        raise EvaluationStructureError('alternate version and primary sample refs are required')
    if primary_sample_ref==alternate_version_ref:
        raise EvaluationStructureError('alternate version cannot be counted as a separate sample')
    expected=set(contract['required_condition_keys'])
    if not isinstance(condition_results,list): raise EvaluationStructureError('alternate version conditions must be an array')
    by_key={}
    for row in condition_results:
        if not isinstance(row,dict) or set(row)!={'condition_key','result','freshness_status','evidence_refs'}:
            raise EvaluationStructureError('alternate version condition schema mismatch')
        key=row['condition_key']
        if key not in expected or key in by_key: raise EvaluationStructureError('alternate version condition key is unknown or duplicate')
        if row['result'] not in {'satisfied','not-satisfied','undetermined'} or row['freshness_status'] not in {'current','stale','unknown'}:
            raise EvaluationStructureError('alternate version condition result/freshness is invalid')
        if not _nonempty_refs(row['evidence_refs']):
            raise EvaluationStructureError('alternate version condition evidence refs invalid')
        by_key[key]=row
    missing=sorted(expected-set(by_key))
    required_criteria=set(target['required_success_criteria'])
    criteria={}
    if not isinstance(criterion_results,list): raise EvaluationStructureError('alternate version criterion results must be an array')
    for row in criterion_results:
        if not isinstance(row,dict) or set(row)!={'criterion_ref','result_ref','result','freshness_status','evidence_refs'}:
            raise EvaluationStructureError('alternate version criterion result schema mismatch')
        ref=row['criterion_ref']
        if ref not in required_criteria or ref in criteria: raise EvaluationStructureError('alternate version criterion ref is unknown or duplicate')
        if row['result'] not in {'satisfied','not-satisfied','undetermined'} or row['freshness_status'] not in {'current','stale','unknown'}:
            raise EvaluationStructureError('alternate version criterion result/freshness invalid')
        if not isinstance(row['result_ref'],str) or not row['result_ref'].strip() or not _nonempty_refs(row['evidence_refs']):
            raise EvaluationStructureError('alternate version criterion evidence identity invalid')
        criteria[ref]=row
    missing_criteria=sorted(required_criteria-set(criteria))
    rows=list(by_key.values())+list(criteria.values())
    if any(row['result']=='not-satisfied' and row['freshness_status']=='current' for row in rows): status='not-satisfied'
    elif missing or missing_criteria or any(row['result']!='satisfied' or row['freshness_status']!='current' for row in rows): status='undetermined'
    else: status='satisfied'
    return {'status':status,'primary_sample_ref':primary_sample_ref,'alternate_version_ref':alternate_version_ref,
            'target_version':version,'target_level':level,'condition_results':[by_key[key] for key in sorted(by_key)],
            'criterion_results':[criteria[key] for key in sorted(criteria)],
            'criterion_result_refs':[criteria[key]['result_ref'] for key in sorted(criteria)],
            'evidence_refs':sorted({ref for row in rows for ref in row.get('evidence_refs',[])}),
            'missing_condition_keys':missing,'missing_success_criteria':missing_criteria}


def materialize_conformance_requirement_results(*, version: str, level: str, samples: list[dict[str,Any]],
        variations: list[dict[str,Any]], sample_results: list[dict[str,Any]], complete_processes: list[dict[str,Any]],
        process_inventory_complete: bool, process_inventory_evidence_refs: list[str],
        accessibility_support_baseline: dict[str,Any], alternate_version_results: list[dict[str,Any]] | None = None,
        evaluation_ref: str | None = None, evaluation_revision: str | None = None) -> dict[str,Any]:
    if ((evaluation_ref is None) != (evaluation_revision is None)
            or any(value is not None and (not isinstance(value,str) or not value.strip())
                   for value in (evaluation_ref,evaluation_revision))):
        raise EvaluationStructureError('evaluation ref and revision must be provided together')
    target=resolve_target(version,level)
    if target['status']!='supported': return {'status':target['status'],'results':[],'reason':target['reason']}
    catalog=load_catalog(version)
    sample_refs=[row.get('sample_ref') for row in samples]
    if not sample_refs or any(not isinstance(ref,str) or not ref.strip() for ref in sample_refs) or len(sample_refs)!=len(set(sample_refs)):
        raise EvaluationStructureError('conformance closure requires unique sample refs')
    sample_kinds={}
    for row in samples:
        if not isinstance(row,dict) or row.get('sample_kind') not in {'structured','random','process-added'}:
            raise EvaluationStructureError('each selected sample requires a canonical sample kind')
        sample_kinds[row['sample_ref']]=row['sample_kind']
    sample_ref_set=set(sample_refs)
    required_sc=set(target['required_success_criteria'])
    variation_by_sample={ref:[] for ref in sample_refs}
    all_variation_refs=set()
    for row in variations:
        if row.get('sample_ref') not in sample_ref_set or not isinstance(row.get('variation_ref'),str) or not row['variation_ref'].strip():
            raise EvaluationStructureError('conformance variation inventory identity invalid')
        if row.get('required') is not True:
            raise EvaluationStructureError('non-required variation must not enter formal coverage')
        if row['variation_ref'] in all_variation_refs:
            raise EvaluationStructureError('presentation variation refs must be globally unique')
        all_variation_refs.add(row['variation_ref'])
        if row.get('completeness') not in {'complete','incomplete','unknown','unreachable'} or row.get('coverage_status') not in {'required','evaluated','undetermined','blocked'}:
            raise EvaluationStructureError('presentation variation completeness or coverage status is invalid')
        if not isinstance(row.get('identity_fingerprint'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',row['identity_fingerprint']):
            raise EvaluationStructureError('presentation variation requires a current identity fingerprint')
        if not _nonempty_refs(row.get('evidence_refs')):
            raise EvaluationStructureError('presentation variation requires source evidence refs')
        variation_by_sample[row['sample_ref']].append(row)
    if any(not rows for rows in variation_by_sample.values()):
        raise EvaluationStructureError('each sample requires a presentation variation inventory')
    sample_result_index={}; duplicate_result_keys=set(); result_refs=set(); criterion_refs=set()
    result_fields={'sample_result_ref','evaluation_ref','evaluation_revision','sample_ref','variation_ref','sample_kind','process_ref','requirement_ref',
        'criterion_evaluation_ref','result','observation_refs','test_rule_result_refs','evidence_refs',
        'unmet_example_refs','freshness_status','limitation'}
    for row in sample_results:
        if not isinstance(row,dict) or set(row)!=result_fields:
            raise EvaluationStructureError('sample evaluation result schema mismatch')
        if (not isinstance(row.get('evaluation_ref'),str) or not row['evaluation_ref'].strip()
                or not isinstance(row.get('evaluation_revision'),str) or not row['evaluation_revision'].strip()
                or (evaluation_ref is not None and row['evaluation_ref']!=evaluation_ref)
                or (evaluation_revision is not None and row['evaluation_revision']!=evaluation_revision)):
            raise EvaluationStructureError('sample evaluation result does not belong to the current evaluation revision')
        key=(row.get('sample_ref'),row.get('variation_ref'),row.get('requirement_ref'))
        if key in sample_result_index: duplicate_result_keys.add(key)
        for field,seen in (('sample_result_ref',result_refs),('criterion_evaluation_ref',criterion_refs)):
            value=row.get(field)
            if not isinstance(value,str) or not value.strip() or value in seen:
                raise EvaluationStructureError(f'current sample result has a missing or duplicate {field}')
            seen.add(value)
        if row.get('sample_kind')!=sample_kinds.get(row.get('sample_ref')):
            raise EvaluationStructureError('sample result kind does not match its canonical sample')
        if row.get('result') not in {'satisfied','not-satisfied','undetermined'} or row.get('freshness_status') not in {'current','stale','unknown'}:
            raise EvaluationStructureError('sample result enum or freshness status is invalid')
        for field in ('observation_refs','test_rule_result_refs','evidence_refs','unmet_example_refs'):
            if not isinstance(row.get(field),list) or any(not isinstance(ref,str) or not ref.strip() for ref in row[field]) or len(row[field])!=len(set(row[field])):
                raise EvaluationStructureError(f'sample result {field} must be unique non-empty refs')
        if row.get('process_ref') is not None and (not isinstance(row['process_ref'],str) or not row['process_ref'].strip()):
            raise EvaluationStructureError('sample result process ref must be a non-empty ref or null')
        if row.get('limitation') is not None and (not isinstance(row['limitation'],str) or not row['limitation'].strip()):
            raise EvaluationStructureError('sample result limitation must be a non-empty string or null')
        if row['result']=='not-satisfied' and not row['unmet_example_refs']:
            raise EvaluationStructureError('not-satisfied sample result requires an unmet example ref')
        if row['result'] in {'satisfied','not-satisfied'} and row['freshness_status']=='current' and not row['evidence_refs']:
            raise EvaluationStructureError('current conclusive sample result requires evidence refs')
        sample_result_index[key]=row
    if duplicate_result_keys: raise EvaluationStructureError('duplicate current sample Success Criterion result')
    evaluation_identities={(row['evaluation_ref'],row['evaluation_revision']) for row in sample_results}
    if len(evaluation_identities)>1: raise EvaluationStructureError('sample results mix evaluation revisions')
    if evaluation_identities:
        result_evaluation_ref,result_evaluation_revision=next(iter(evaluation_identities))
    else:
        result_evaluation_ref,result_evaluation_revision=evaluation_ref,evaluation_revision
    required_result_keys={(sample_ref,variation['variation_ref'],criterion_ref)
        for sample_ref,variation_rows in variation_by_sample.items() for variation in variation_rows
        for criterion_ref in required_sc}
    unexpected=set(sample_result_index)-required_result_keys
    # Not every sample result set must be complete to emit undetermined, but unrelated results are never consumed.
    if unexpected: raise EvaluationStructureError('sample result is outside current sample/variation/target criterion set')
    alternate_by_sample={}; alternate_refs=set()
    alternate_fields={'status','primary_sample_ref','alternate_version_ref','target_version','target_level',
        'condition_results','criterion_results','criterion_result_refs','evidence_refs','missing_condition_keys','missing_success_criteria'}
    for row in alternate_version_results or []:
        if not isinstance(row,dict) or set(row)!=alternate_fields or row.get('primary_sample_ref') not in sample_ref_set:
            raise EvaluationStructureError('alternate-version closure is not linked to a current primary sample')
        if (row.get('target_version')!=version or row.get('target_level')!=level
                or not isinstance(row.get('alternate_version_ref'),str) or not row['alternate_version_ref'].strip()
                or row['alternate_version_ref'] in sample_ref_set or row['alternate_version_ref'] in alternate_refs):
            raise EvaluationStructureError('alternate version target or identity is invalid')
        alternate_refs.add(row['alternate_version_ref'])
        recomputed=close_conforming_alternate_version(version=version,level=level,
            primary_sample_ref=row['primary_sample_ref'],alternate_version_ref=row['alternate_version_ref'],
            condition_results=row['condition_results'],criterion_results=row['criterion_results'])
        for field in ('status','criterion_result_refs','evidence_refs','missing_condition_keys','missing_success_criteria'):
            if row.get(field)!=recomputed.get(field):
                raise EvaluationStructureError(f'alternate version materialized {field} does not match current evidence')
        alternate_by_sample.setdefault(row['primary_sample_ref'],[]).append(recomputed)
    sample_level={}; all_evidence=set(); all_criterion_refs=set(); missing_keys=[]; stale_keys=[]
    for sample_ref,variation_rows in variation_by_sample.items():
        values=[]; unknown_variations=[]; sample_missing=[]
        for variation in variation_rows:
            if variation.get('completeness')!='complete' or variation.get('coverage_status') in {'undetermined','blocked'}:
                unknown_variations.append(variation['variation_ref'])
            for criterion_ref in sorted(required_sc):
                key=(sample_ref,variation['variation_ref'],criterion_ref); result=sample_result_index.get(key)
                if result is None:
                    missing_keys.append(key); sample_missing.append(key); values.append('undetermined'); continue
                if result.get('freshness_status')!='current':
                    stale_keys.append(key)
                    values.append('undetermined'); continue
                if result.get('result') not in {'satisfied','not-satisfied','undetermined'}:
                    raise EvaluationStructureError('sample criterion result enum is invalid')
                values.append(result['result'])
                all_evidence.update(result.get('evidence_refs',[])); all_criterion_refs.add(result.get('criterion_evaluation_ref'))
        valid_alternates=[row for row in alternate_by_sample.get(sample_ref,[]) if row['status']=='satisfied']
        if valid_alternates: sample_level[sample_ref]='satisfied'
        elif any(value=='not-satisfied' for value in values): sample_level[sample_ref]='not-satisfied'
        elif unknown_variations: sample_level[sample_ref]='undetermined'
        elif sample_missing or any(value=='undetermined' for value in values):
            sample_level[sample_ref]='undetermined'
        else: sample_level[sample_ref]='satisfied'
    if not isinstance(process_inventory_complete,bool): raise EvaluationStructureError('process inventory completeness must be boolean')
    if not isinstance(process_inventory_evidence_refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in process_inventory_evidence_refs):
        raise EvaluationStructureError('process inventory evidence refs invalid')
    process_ids=[]; process_statuses=[]
    for process in complete_processes:
        if not isinstance(process,dict) or not isinstance(process.get('process_ref'),str) or not process['process_ref'].strip():
            raise EvaluationStructureError('complete process identity missing')
        refs=process.get('sample_refs')
        if not isinstance(refs,list) or not refs or any(ref not in sample_ref_set for ref in refs):
            raise EvaluationStructureError('complete process sample sequence is invalid')
        if len(refs)!=len(set(refs)): raise EvaluationStructureError('complete process sequence repeats sample identity')
        process_ids.append(process['process_ref'])
        statuses=[sample_level.get(ref,'undetermined') for ref in refs]
        process_statuses.append('not-satisfied' if 'not-satisfied' in statuses else 'undetermined' if 'undetermined' in statuses else 'satisfied')
    if len(process_ids)!=len(set(process_ids)): raise EvaluationStructureError('duplicate complete process ref')
    if any(row.get('process_ref') is not None and row['process_ref'] not in process_ids for row in sample_results):
        raise EvaluationStructureError('sample result refers to an unknown complete process')
    if complete_processes and (not process_inventory_complete or not _nonempty_refs(process_inventory_evidence_refs)):
        process_statuses=['undetermined' for _ in process_statuses]
    baseline=accessibility_support_baseline
    baseline_valid=(isinstance(baseline,dict) and set(baseline)=={'baseline_ref','status','required_usage_refs','supported_usage_refs','evidence_refs'}
        and isinstance(baseline.get('baseline_ref'),str) and baseline['baseline_ref'].strip()
        and baseline.get('status') in {'complete','incomplete','blocked'}
        and _nonempty_refs(baseline.get('required_usage_refs')) and isinstance(baseline.get('supported_usage_refs'),list)
        and all(isinstance(ref,str) and ref.strip() for ref in baseline.get('supported_usage_refs',[]))
        and len(baseline.get('supported_usage_refs',[]))==len(set(baseline.get('supported_usage_refs',[])))
        and set(baseline.get('supported_usage_refs',[]))<=set(baseline.get('required_usage_refs',[]))
        and isinstance(baseline.get('evidence_refs'),list)
        and all(isinstance(ref,str) and ref.strip() for ref in baseline.get('evidence_refs',[]))
        and len(baseline.get('evidence_refs',[]))==len(set(baseline.get('evidence_refs',[]))))
    baseline_result='undetermined'; baseline_evidence=[]
    if baseline_valid:
        baseline_evidence=baseline['evidence_refs']
        if baseline['status']=='complete' and _nonempty_refs(baseline_evidence):
            baseline_result='not-satisfied' if set(baseline['required_usage_refs'])-set(baseline['supported_usage_refs']) else 'satisfied'
        elif baseline['status']=='blocked': baseline_result='undetermined'
    non_interference={row['requirement_key']:set(row.get('metadata',{}).get('success_criterion_refs',[]))
                      for row in catalog['conformance_requirements'] if row['requirement_key']=='non-interference'}['non-interference']
    ni_values=[]; ni_evidence=set()
    for sample_ref,variation_rows in variation_by_sample.items():
        for variation in variation_rows:
            for criterion_ref in non_interference:
                row=sample_result_index.get((sample_ref,variation['variation_ref'],criterion_ref))
                if row is None or row.get('freshness_status')!='current': ni_values.append('undetermined')
                else:
                    ni_values.append(row['result']); ni_evidence.update(row.get('evidence_refs',[]))
    def aggregate(values: list[str], *, unknown_if_empty: bool = True) -> str:
        if any(value=='not-satisfied' for value in values): return 'not-satisfied'
        if not values and not unknown_if_empty: return 'satisfied'
        return 'undetermined' if not values or any(value=='undetermined' for value in values) else 'satisfied'
    conformance_level=aggregate(list(sample_level.values()))
    full_pages='undetermined' if any(row.get('completeness')!='complete' or row.get('coverage_status') in {'undetermined','blocked'} for rows in variation_by_sample.values() for row in rows) else conformance_level
    if complete_processes:
        complete_process_result=aggregate(process_statuses)
    elif process_inventory_complete and _nonempty_refs(process_inventory_evidence_refs):
        complete_process_result='satisfied'
    else: complete_process_result='undetermined'
    accessibility_result=baseline_result
    non_interference_result=aggregate(ni_values)
    values={'conformance-level':conformance_level,'full-pages':full_pages,
            'complete-processes':complete_process_result,'accessibility-supported-ways':accessibility_result,
            'non-interference':non_interference_result}
    result_rows=[]
    for index,requirement in enumerate(catalog['conformance_requirements'],1):
        key=requirement['requirement_key']; evidence=set(all_evidence)
        if key=='accessibility-supported-ways': evidence.update(baseline_evidence)
        if key=='complete-processes': evidence.update(process_inventory_evidence_refs)
        if key=='non-interference': evidence.update(ni_evidence)
        result_rows.append({'conformance_result_ref':f'WCAG-REQ-RES-{index:03d}','requirement_ref':key,
            'canonical_uri':requirement['canonical_uri'],'result':values[key],
            'sample_refs':sorted(sample_refs),'variation_refs':sorted({row['variation_ref'] for rows in variation_by_sample.values() for row in rows}),
            'process_refs':sorted(process_ids),'criterion_evaluation_refs':sorted(ref for ref in all_criterion_refs if isinstance(ref,str)),
            'alternate_version_refs':sorted(row['alternate_version_ref'] for rows in alternate_by_sample.values() for row in rows if row['status']=='satisfied'),
            'success_criterion_refs':sorted(non_interference) if key=='non-interference' else sorted(required_sc) if key=='conformance-level' else [],
            'evidence_refs':sorted(evidence),'limitation':None if values[key]=='satisfied' else 'required current conformance evidence is incomplete or not satisfied'})
    return {'status':'ready' if all(row['result'] in {'satisfied','not-satisfied'} for row in result_rows) else 'unresolved',
            'target_version':version,'target_level':level,'evaluation_ref':result_evaluation_ref,
            'evaluation_revision':result_evaluation_revision,'criterion_evaluation_refs':sorted(criterion_refs),
            'sample_results_count':len(sample_results),
            'expected_sample_criterion_rows':len(required_result_keys),'missing_sample_criterion_rows':[
                {'sample_ref':s,'variation_ref':v,'criterion_ref':c} for s,v,c in sorted(missing_keys)],
            'stale_sample_criterion_rows':[{'sample_ref':s,'variation_ref':v,'criterion_ref':c}
                for s,v,c in sorted(stale_keys)],
            'sample_conformance_results':[{'sample_ref':ref,'result':sample_level[ref]} for ref in sorted(sample_level)],
            'results':result_rows}


def evaluation_statement(*, version: str, status: str, all_methodology_complete: bool, all_samples_conform: bool,
                         owner_commitment_ref: str | None, product_scope: str, technologies: list[str], baseline_ref: str,
                         issued_date: str | None = None, level: str | None = None, scope_ref: str | None = None,
                         nonconforming_areas: list[dict[str, Any]] | None = None,
                         report_closure: dict[str, Any] | None = None,
                         formal_conformance_results: dict[str, Any] | None = None) -> dict[str, Any]:
    if version!='2.2': return {'status':'not-generated','reason':'wcag-em-2-step-5.3-is-wcag-2.2-only'}
    catalog=load_catalog(version)
    contract=catalog['evaluation_statement_contract']
    if status not in set(contract['types']) or type(all_methodology_complete) is not bool or type(all_samples_conform) is not bool:
        return {'status':'blocked','reason':'statement-input-enum-or-boolean-invalid'}
    required={'issued_date':issued_date,'wcag_title':contract.get('wcag_title','Web Content Accessibility Guidelines (WCAG) 2.2'),
              'wcag_uri':contract.get('wcag_uri','https://www.w3.org/TR/WCAG22/'),'conformance_level':level,
              'product_scope':product_scope,'technologies_relied_upon':technologies,
              'accessibility_support_baseline_ref':baseline_ref,'owner_commitment_ref':owner_commitment_ref,
              'scope_ref':scope_ref}
    missing=[key for key,value in required.items() if value in (None,'',[],{})]
    try: date.fromisoformat(issued_date or '')
    except (TypeError,ValueError): missing.append('issued_date')
    target=resolve_target(version,level)
    if target['status']!='supported': missing.append('conformance_level')
    if not isinstance(technologies,list) or any(not isinstance(value,str) or not value.strip() for value in technologies):
        missing.append('technologies_relied_upon')
    if missing: return {'status':'blocked','reason':'statement-required-fields-missing-or-invalid','missing_fields':sorted(set(missing))}
    if required['wcag_title']!='Web Content Accessibility Guidelines (WCAG) 2.2' or required['wcag_uri']!='https://www.w3.org/TR/WCAG22/':
        return {'status':'blocked','reason':'statement-version-metadata-mismatch'}
    if not all_methodology_complete or not owner_commitment_ref:
        return {'status':'blocked','reason':'methodology-or-owner-commitment-incomplete'}
    if not _statement_evaluation_evidence_is_current(report_closure,formal_conformance_results,
                                                      version=version,level=level):
        return {'status':'blocked','reason':'current-report-and-conformance-results-required'}
    common={'issued_date':issued_date,'wcag_title':required['wcag_title'],'wcag_uri':required['wcag_uri'],
            'conformance_level':level,'product_scope':product_scope,'scope_ref':scope_ref,
            'technologies_relied_upon':sorted(set(technologies)),
            'accessibility_support_baseline_ref':baseline_ref,'owner_commitment_ref':owner_commitment_ref}
    sample_results=formal_conformance_results['sample_conformance_results']
    requirement_results=formal_conformance_results['results']
    all_current_samples_conform=all(row['result']=='satisfied' for row in sample_results)
    all_current_requirements_conform=all(row['result']=='satisfied' for row in requirement_results)
    if status=='full' and all_samples_conform and all_current_samples_conform and all_current_requirements_conform:
        return {'status':'generated','statement_type':'full',**common}
    if status=='full':
        return {'status':'blocked','reason':'full-statement-requires-current-conformance-for-every-sample'}
    if status=='partial' and nonconforming_areas is not None:
        if all_samples_conform or all_current_samples_conform or all_current_requirements_conform:
            return {'status':'blocked','reason':'partial-statement-requires-current-nonconforming-results'}
        if not isinstance(nonconforming_areas,list) or not nonconforming_areas:
            return {'status':'blocked','reason':'partial-statement-requires-nonconforming-areas'}
        normalized=[]; seen=set()
        for row in nonconforming_areas:
            common_fields={'area_ref','description','reason','evidence_refs','rest_conforms'}
            if not isinstance(row,dict) or not common_fields<=set(row):
                return {'status':'blocked','reason':'partial-area-schema-invalid'}
            if row['reason'] not in contract['partial_reasons'] or type(row['rest_conforms']) is not bool or not row['rest_conforms']:
                return {'status':'blocked','reason':'partial-area-reason-or-rest-conformance-invalid'}
            if not all(isinstance(row.get(key),str) and row[key].strip() for key in ('area_ref','description')):
                return {'status':'blocked','reason':'partial-area-identity-missing'}
            if row['area_ref'] in seen:
                return {'status':'blocked','reason':'duplicate-partial-area'}
            seen.add(row['area_ref'])
            refs=row['evidence_refs']
            if not isinstance(refs,list) or not refs or any(not isinstance(ref,str) or not ref.strip() for ref in refs) or len(refs)!=len(set(refs)):
                return {'status':'blocked','reason':'partial-area-evidence-required'}
            if row['reason']=='third-party-content':
                if row.get('outside_author_control') is not True or row.get('user_identifiable') is not True:
                    return {'status':'blocked','reason':'third-party-partial-statement-identification-guard'}
                normalized.append({key:row[key] for key in ('area_ref','description','reason','evidence_refs','rest_conforms','outside_author_control','user_identifiable')})
            else:
                languages=row.get('language_refs'); support_refs=row.get('support_gap_refs')
                if not isinstance(languages,list) or not languages or any(not isinstance(x,str) or not x.strip() for x in languages):
                    return {'status':'blocked','reason':'language-partial-statement-requires-language-refs'}
                if not isinstance(support_refs,list) or not support_refs or any(not isinstance(x,str) or not x.strip() for x in support_refs):
                    return {'status':'blocked','reason':'language-partial-statement-requires-support-gap-evidence'}
                normalized.append({key:row[key] for key in ('area_ref','description','reason','evidence_refs','rest_conforms')} |
                                  {'language_refs':sorted(set(languages)),'support_gap_refs':sorted(set(support_refs))})
        return {'status':'generated','statement_type':'partial',**common,'nonconforming_areas':normalized}
    return {'status':'blocked','reason':'statement-conditions-not-met'}


def _statement_evaluation_evidence_is_current(report_closure: Any, formal_results: Any, *,
                                               version: str, level: str | None) -> bool:
    if (not isinstance(report_closure,dict) or report_closure.get('status')!='complete'
            or not isinstance(formal_results,dict) or formal_results.get('status')!='ready'):
        return False
    evaluation_ref=report_closure.get('evaluation_ref')
    revision=report_closure.get('evaluation_revision')
    if (not isinstance(evaluation_ref,str) or not evaluation_ref.strip()
            or not isinstance(revision,str) or not revision.strip()
            or formal_results.get('evaluation_ref')!=evaluation_ref
            or formal_results.get('evaluation_revision')!=revision
            or report_closure.get('wcag_version')!=version or report_closure.get('level')!=level
            or formal_results.get('target_version')!=version or formal_results.get('target_level')!=level):
        return False
    plan_refs=report_closure.get('criterion_evaluation_refs')
    result_refs=formal_results.get('criterion_evaluation_refs')
    if (not isinstance(plan_refs,list) or not plan_refs
            or any(not isinstance(ref,str) or not ref.strip() for ref in plan_refs)
            or len(plan_refs)!=len(set(plan_refs)) or result_refs!=plan_refs):
        return False
    expected_count=formal_results.get('expected_sample_criterion_rows')
    if (isinstance(expected_count,bool) or not isinstance(expected_count,int)
            or expected_count!=len(plan_refs) or formal_results.get('sample_results_count')!=expected_count
            or formal_results.get('missing_sample_criterion_rows')
            or formal_results.get('stale_sample_criterion_rows')):
        return False
    samples=formal_results.get('sample_conformance_results')
    requirements=formal_results.get('results')
    if (not isinstance(samples,list) or not samples or not isinstance(requirements,list) or not requirements
            or any(not isinstance(row,dict) or row.get('result') not in {'satisfied','not-satisfied'} for row in samples)
            or any(not isinstance(row,dict) or row.get('result') not in {'satisfied','not-satisfied'} for row in requirements)
            or len({row.get('sample_ref') for row in samples})!=len(samples)):
        return False
    requirement_refs=[row.get('requirement_ref') for row in requirements]
    if any(not isinstance(ref,str) or not ref.strip() for ref in requirement_refs):
        return False
    required_requirement_refs={row['requirement_key']
        for row in load_catalog(version)['conformance_requirements']}
    return (len(requirement_refs)==len(set(requirement_refs))
            and set(requirement_refs)==required_requirement_refs)


def conformance_claim(*, version: str, full_scope_evidence: bool, required_fields: dict[str, Any],
                      third_party_content: dict[str, Any] | None = None,
                      scope_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog=load_catalog(version)
    contract=catalog['claim_contract']
    if not isinstance(required_fields,dict):
        return {'status':'not-generated','reason':'claim-fields-invalid','missing_fields':contract['required_fields']}
    allowed=set(contract['required_fields'])|set(contract['optional_fields'])
    unknown=sorted(set(required_fields)-allowed)
    missing=sorted(k for k in contract['required_fields'] if required_fields.get(k) in (None,'',[],{}))
    if unknown: return {'status':'not-generated','reason':'claim-field-outside-version-contract','unknown_fields':unknown}
    try: date.fromisoformat(required_fields.get('claim_date',''))
    except (TypeError,ValueError): missing.append('claim_date')
    for key in ('guideline_title','guideline_version','guideline_uri'):
        if required_fields.get(key)!=contract.get(key): missing.append(key)
    if required_fields.get('conformance_level') not in {'A','AA','AAA'}: missing.append('conformance_level')
    technologies=required_fields.get('technologies_relied_upon')
    if not isinstance(technologies,list) or not technologies or any(not isinstance(x,str) or not x.strip() for x in technologies):
        missing.append('technologies_relied_upon')
    scope=required_fields.get('page_scope')
    if not isinstance(scope,dict) or set(scope)!={'description','uris','scope_expression','includes_subdomains'}:
        missing.append('page_scope')
    else:
        uris=scope.get('uris'); expression=scope.get('scope_expression')
        if not isinstance(scope.get('description'),str) or not scope['description'].strip() or type(scope.get('includes_subdomains')) is not bool:
            missing.append('page_scope')
        if not isinstance(uris,list) or any(not isinstance(uri,str) or not uri.startswith(('https://','http://')) for uri in uris) or len(uris)!=len(set(uris)):
            missing.append('page_scope.uris')
        if bool(uris)==bool(isinstance(expression,str) and expression.strip()):
            missing.append('page_scope.requires_uri_list_or_scope_expression')
    if type(full_scope_evidence) is not bool or full_scope_evidence is not True or not _validate_claim_scope_evidence(
        scope_evidence, scope, contract, required_fields.get('conformance_level')):
        missing.append('full_scope_evidence')
    if missing:
        return {'status':'not-generated','reason':'claim-requires-complete-full-scope-evidence-and-version-fields','missing_fields':sorted(set(missing))}
    if third_party_content:
        if (not isinstance(third_party_content,dict) or third_party_content.get('all_affected_pages_identified') is not True
            or third_party_content.get('monitoring_possible') is not True
            or third_party_content.get('repair_window_business_days')!=contract['third_party_repair_window_business_days']
            or not _nonempty_refs(third_party_content.get('affected_page_refs'))
            or not _nonempty_refs(third_party_content.get('repair_evidence_refs'))):
            return {'status':'blocked','reason':'third-party-monitoring-repair-guard'}
    normalized_fields=dict(required_fields)
    normalized_fields['technologies_relied_upon']=sorted(set(technologies))
    return {'status':'generated','guideline_title':contract['guideline_title'],'guideline_version':version,
            'guideline_uri':contract['guideline_uri'],'fields':normalized_fields,'scope_evidence':scope_evidence,
            'third_party_content':third_party_content}


def _nonempty_refs(value: Any) -> bool:
    return isinstance(value,list) and bool(value) and all(isinstance(ref,str) and ref.strip() for ref in value) and len(value)==len(set(value))


def _validate_claim_scope_evidence(scope_evidence: Any, page_scope: Any, contract: dict[str, Any], level: str) -> bool:
    if not isinstance(scope_evidence,dict): return False
    required={'coverage_method','scope_ref','scope_population_complete','covered_page_uris','claim_level','success_criterion_results',
              'conformance_requirement_results','complete_process_evidence_refs','evidence_refs'}
    if set(scope_evidence)!=required or scope_evidence.get('coverage_method') not in {'all-pages-evaluated','assurance-process'}:
        return False
    if not isinstance(scope_evidence.get('scope_ref'),str) or not scope_evidence['scope_ref'].strip() or scope_evidence.get('scope_population_complete') is not True:
        return False
    if not _nonempty_refs(scope_evidence.get('evidence_refs')): return False
    covered=scope_evidence.get('covered_page_uris')
    if not isinstance(covered,list) or any(not isinstance(uri,str) or not uri.startswith(('https://','http://')) for uri in covered) or len(covered)!=len(set(covered)):
        return False
    if scope_evidence['coverage_method']=='all-pages-evaluated':
        if not isinstance(page_scope,dict) or not covered: return False
        if page_scope.get('uris') and set(covered)!=set(page_scope['uris']): return False
        # A free-form expression cannot be enumerated here. Without an exact
        # URI inventory, all-pages-evaluated would assert unverified coverage.
        if not page_scope.get('uris'): return False
    else:
        if not _nonempty_refs(scope_evidence.get('complete_process_evidence_refs')) or not isinstance(page_scope,dict): return False
        if page_scope.get('uris') and set(covered)!=set(page_scope['uris']): return False
        if not page_scope.get('uris') and not (isinstance(page_scope.get('scope_expression'),str) and page_scope['scope_expression'].strip()): return False
        if not set(scope_evidence['complete_process_evidence_refs'])<=set(scope_evidence['evidence_refs']): return False
    sc_rows=scope_evidence.get('success_criterion_results')
    if not isinstance(sc_rows,list) or not sc_rows: return False
    expected={row['criterion_ref'] for row in load_catalog(contract['guideline_version'])['success_criteria']
              if row['level'] in ({'A'} if scope_evidence.get('claim_level')=='A' else {'A','AA'} if scope_evidence.get('claim_level')=='AA' else {'A','AA','AAA'})}
    # Every claimed page must have a current result for every criterion at the exact target level.
    if scope_evidence.get('claim_level')!=level or level not in {'A','AA','AAA'}: return False
    expected_page_criteria={(uri,criterion) for uri in covered for criterion in expected}
    sc_pairs=[]; sc_result_refs=[]
    for row in sc_rows:
        if not isinstance(row,dict) or set(row)!={'criterion_ref','page_uri','result_ref','result','freshness_status','evidence_refs'}:
            return False
        pair=(row.get('page_uri'),row.get('criterion_ref'))
        if (pair not in expected_page_criteria or row.get('result')!='satisfied'
                or row.get('freshness_status')!='current' or not isinstance(row.get('result_ref'),str)
                or not row['result_ref'].strip() or not _nonempty_refs(row.get('evidence_refs'))):
            return False
        sc_pairs.append(pair); sc_result_refs.append(row['result_ref'])
    if set(sc_pairs)!=expected_page_criteria or len(sc_pairs)!=len(set(sc_pairs)) or len(sc_result_refs)!=len(set(sc_result_refs)):
        return False
    req_rows=scope_evidence.get('conformance_requirement_results')
    requirement_keys={row['requirement_key'] for row in load_catalog(contract['guideline_version'])['conformance_requirements']}
    expected_page_requirements={(uri,key) for uri in covered for key in requirement_keys}
    req_pairs=[]; req_result_refs=[]
    if not isinstance(req_rows,list) or not req_rows: return False
    for row in req_rows:
        if not isinstance(row,dict) or set(row)!={'requirement_key','page_uri','result_ref','result','freshness_status','evidence_refs'}:
            return False
        pair=(row.get('page_uri'),row.get('requirement_key'))
        if (pair not in expected_page_requirements or row.get('result')!='satisfied'
                or row.get('freshness_status')!='current' or not isinstance(row.get('result_ref'),str)
                or not row['result_ref'].strip() or not _nonempty_refs(row.get('evidence_refs'))):
            return False
        req_pairs.append(pair); req_result_refs.append(row['result_ref'])
    if set(req_pairs)!=expected_page_requirements or len(req_pairs)!=len(set(req_pairs)) or len(req_result_refs)!=len(set(req_result_refs)):
        return False
    return True


def statement_of_partial_conformance(*, version: str, level: str, statement_type: str,
                                     parts_or_languages: list[dict[str, Any]]) -> dict[str, Any]:
    target=resolve_target(version,level)
    if target['status']!='supported': return {'status':'blocked','reason':'unsupported_target'}
    contract=load_catalog(version)['statement_of_partial_conformance_contract']
    if statement_type not in contract['types'] or not isinstance(parts_or_languages,list) or not parts_or_languages:
        return {'status':'blocked','reason':'partial_statement_type_or_scope_invalid'}
    normalized=[]; scopes=[]; evidence=[]
    for row in parts_or_languages:
        if not isinstance(row,dict) or not _nonempty_refs(row.get('supporting_evidence_refs')):
            return {'status':'blocked','reason':'partial_statement_evidence_missing'}
        refs=sorted(set(row['supporting_evidence_refs'])); evidence.extend(refs)
        if statement_type=='third-party-content':
            required={'part_ref','description','outside_author_control','user_identifiable','would_conform_if_removed','supporting_evidence_refs'}
            if set(row)!=required or any(row[key] is not True for key in ('outside_author_control','user_identifiable','would_conform_if_removed')):
                return {'status':'blocked','reason':'third_party_partial_statement_guard'}
            if not all(isinstance(row[key],str) and row[key].strip() for key in ('part_ref','description')):
                return {'status':'blocked','reason':'third_party_partial_statement_identity_missing'}
            scopes.append(row['description']); normalized.append({**row,'supporting_evidence_refs':refs})
        else:
            required={'language_ref','language_name','accessibility_support_missing','would_conform_if_supported','supporting_evidence_refs'}
            if set(row)!=required or row.get('accessibility_support_missing') is not True or row.get('would_conform_if_supported') is not True:
                return {'status':'blocked','reason':'language_partial_statement_guard'}
            if not all(isinstance(row[key],str) and row[key].strip() for key in ('language_ref','language_name')):
                return {'status':'blocked','reason':'language_partial_statement_identity_missing'}
            scopes.append(row['language_name']); normalized.append({**row,'supporting_evidence_refs':refs})
    if len({row.get('part_ref',row.get('language_ref')) for row in normalized})!=len(normalized):
        return {'status':'blocked','reason':'duplicate_partial_statement_scope'}
    if statement_type=='third-party-content':
        details='; '.join(scopes)
        canonical=f'This page does not conform, but would conform to WCAG {version} at level {level} if the following parts from uncontrolled sources were removed: {details}.'
    else:
        details=', '.join(scopes)
        canonical=f'This page does not conform, but would conform to WCAG {version} at level {level} if accessibility support existed for the following language(s): {details}.'
    return {'status':'generated','statement_type':statement_type,'target_version':version,'level':level,
            'canonical_uri':contract['canonical_uri'],'scope_rows':normalized,'canonical_statement':canonical,
            'supporting_evidence_refs':sorted(set(evidence))}


def close_report(*, required_steps: list[str], step_outcomes: dict[str, str], sample_results: list[dict[str, Any]],
                 example_coverage: dict[str, list[str]], required_criterion_evaluation_refs: list[str] | None = None,
                 canonical_criterion_plan: dict[str, Any] | None = None,
                 all_occurrence_requirements: dict[str, list[str]] | None = None,
                 accessible_output_closure: dict[str, bool] | None = None) -> dict[str, Any]:
    if (not isinstance(required_steps, list) or not required_steps
            or any(not isinstance(step, str) for step in required_steps)
            or len(required_steps) != len(set(required_steps))
            or set(required_steps)-set(REPORT_STEPS) or not isinstance(step_outcomes, dict)
            or set(step_outcomes)-set(REPORT_STEPS)):
        raise EvaluationStructureError('report step key outside fixed WCAG-EM step inventory')
    if not isinstance(sample_results, list):
        raise EvaluationStructureError('sample results must be a list')
    if required_criterion_evaluation_refs is not None and (
            not isinstance(required_criterion_evaluation_refs, list)
            or any(not isinstance(ref, str) or not ref.strip() for ref in required_criterion_evaluation_refs)
            or len(required_criterion_evaluation_refs) != len(set(required_criterion_evaluation_refs))):
        raise EvaluationStructureError('required criterion evaluation refs must be unique non-empty refs')

    missing_steps=sorted(set(REPORT_STEPS)-set(step_outcomes))
    open_steps=sorted(step for step,status in step_outcomes.items() if status not in {'complete','not-applicable'})
    incomplete_required_steps=sorted(step for step in required_steps if step_outcomes.get(step) != 'complete')
    canonical_plan_error=None
    canonical_plan_refs=[]
    canonical_rows_by_ref={}
    canonical_samples_by_ref={}
    evaluation_ref=None
    evaluation_revision=None
    if canonical_criterion_plan is not None:
        try:
            canonical_plan_refs=validate_materialized_plan(canonical_criterion_plan)
            if (not isinstance(canonical_criterion_plan.get('evaluation_ref'),str)
                    or not canonical_criterion_plan['evaluation_ref'].strip()
                    or not isinstance(canonical_criterion_plan.get('evaluation_revision'),str)
                    or not canonical_criterion_plan['evaluation_revision'].strip()):
                raise CriterionPlanError('current criterion plan requires evaluation identity and revision')
            evaluation_ref=canonical_criterion_plan['evaluation_ref']
            evaluation_revision=canonical_criterion_plan['evaluation_revision']
            canonical_rows_by_ref={row['criterion_evaluation_ref']:row for row in canonical_criterion_plan['criteria']}
            canonical_samples_by_ref={row['sample_ref']:row for row in canonical_criterion_plan['plan_basis']['samples']}
        except (CriterionPlanError, KeyError, TypeError) as exc:
            canonical_plan_error=str(exc) or 'canonical criterion plan is invalid'
            canonical_plan_refs=[]
            canonical_rows_by_ref={}
            canonical_samples_by_ref={}
    sample_result_refs=[]
    sample_result_identity_refs=[]
    invalid_sample_results=[]
    incomplete_sample_results=[]
    unsatisfied=set()
    for index,row in enumerate(sample_results):
        if (not isinstance(row, dict) or not isinstance(row.get('criterion_evaluation_ref'), str)
                or not row.get('criterion_evaluation_ref','').strip()
                or not isinstance(row.get('requirement_ref'), str) or not row.get('requirement_ref','').strip()
                or row.get('result') not in {'satisfied','not-satisfied','undetermined'}
                or row.get('freshness_status') not in {'current','stale','unknown'}):
            invalid_sample_results.append(str(index))
            continue
        sample_result_refs.append(row['criterion_evaluation_ref'])
        sample_result_identity_refs.append(row.get('sample_result_ref'))
        if row['result'] == 'not-satisfied': unsatisfied.add(row['requirement_ref'])
        if row['result'] == 'undetermined' or row['freshness_status'] != 'current':
            incomplete_sample_results.append(row['criterion_evaluation_ref'])
        if canonical_criterion_plan is not None:
            canonical_row=canonical_rows_by_ref.get(row['criterion_evaluation_ref'])
            canonical_sample=canonical_samples_by_ref.get(row.get('sample_ref'))
            if (canonical_row is None or row.get('evaluation_ref')!=evaluation_ref
                    or row.get('evaluation_revision')!=evaluation_revision
                    or row.get('sample_ref')!=canonical_row.get('sample_ref')
                    or row.get('variation_ref')!=canonical_row.get('variation_ref')
                    or row.get('requirement_ref')!=canonical_row.get('criterion_ref')
                    or (canonical_sample is not None and canonical_sample.get('sample_kind') is not None
                        and row.get('sample_kind')!=canonical_sample.get('sample_kind'))
                    or row.get('process_ref')!=canonical_row.get('process_ref')):
                invalid_sample_results.append(f'non_current_plan_identity:{row["criterion_evaluation_ref"]}')
    if any(not isinstance(ref,str) or not ref.strip() for ref in sample_result_identity_refs):
        invalid_sample_results.append('sample_result_ref_missing')
    if len(sample_result_identity_refs)!=len(set(sample_result_identity_refs)):
        invalid_sample_results.append('duplicate_sample_result_ref')
    if len(sample_result_refs) != len(set(sample_result_refs)):
        invalid_sample_results.append('duplicate_criterion_evaluation_ref')

    missing_sample_result_refs=[]
    unexpected_sample_result_refs=[]
    sample_selection_completed = any(step_outcomes.get(step)=='complete' for step in ('3.1','3.2','3.3'))
    criterion_evaluation_required = (
        '4.1' in required_steps or '4.2' in required_steps
        or step_outcomes.get('4.1') == 'complete' or step_outcomes.get('4.2') == 'complete'
        or sample_selection_completed or bool(sample_results) or canonical_criterion_plan is not None
    )
    sample_result_scope_missing = criterion_evaluation_required and (canonical_criterion_plan is None or canonical_plan_error is not None)
    expected_refs=canonical_plan_refs if canonical_criterion_plan is not None and canonical_plan_error is None else []
    declared_scope_mismatch=(required_criterion_evaluation_refs is not None
                             and set(required_criterion_evaluation_refs)!=set(expected_refs))
    missing_sample_result_refs=sorted(set(expected_refs)-set(sample_result_refs))
    unexpected_sample_result_refs=sorted(set(sample_result_refs)-set(expected_refs))
    unsatisfied=sorted(unsatisfied)
    missing_examples=sorted(req for req in unsatisfied if not _nonempty_refs(example_coverage.get(req)))
    missing_occurrences=[]
    for req, expected in (all_occurrence_requirements or {}).items():
        actual=set(example_coverage.get(req,[]))
        if not set(expected)<=actual: missing_occurrences.append(req)
    accessible_missing=[]
    if not isinstance(accessible_output_closure,dict) or set(accessible_output_closure)!=set(ACCESSIBLE_OUTPUT_CHECKS):
        accessible_missing=list(ACCESSIBLE_OUTPUT_CHECKS)
    else:
        accessible_missing=sorted(key for key,value in accessible_output_closure.items() if value is not True)
    complete=(not missing_steps and not open_steps and not incomplete_required_steps and not invalid_sample_results
              and not incomplete_sample_results and not missing_sample_result_refs and not unexpected_sample_result_refs
              and not sample_result_scope_missing and not declared_scope_mismatch and not missing_examples and not missing_occurrences
              and not accessible_missing)
    return {'status':'complete' if complete else 'blocked','missing_step_outcomes':missing_steps,
            'open_steps':open_steps,'incomplete_required_steps':incomplete_required_steps,
            'invalid_sample_results':sorted(set(invalid_sample_results)),
            'incomplete_sample_results':sorted(incomplete_sample_results),
            'sample_result_scope_missing':sample_result_scope_missing,
            'canonical_criterion_plan_error':canonical_plan_error,
            'declared_criterion_scope_mismatch':declared_scope_mismatch,
            'evaluation_ref':evaluation_ref,'evaluation_revision':evaluation_revision,
            'wcag_version':canonical_criterion_plan.get('wcag_version') if canonical_plan_error is None and canonical_criterion_plan else None,
            'level':canonical_criterion_plan.get('level') if canonical_plan_error is None and canonical_criterion_plan else None,
            'criterion_evaluation_refs':sorted(expected_refs),
            'missing_sample_result_refs':missing_sample_result_refs,
            'unexpected_sample_result_refs':unexpected_sample_result_refs,
            'not_satisfied_requirements_without_example':missing_examples,
            'all_occurrence_gaps':sorted(missing_occurrences),'accessible_output_missing_checks':accessible_missing,
            'accessible_output_closure':accessible_output_closure if not accessible_missing else None,'aggregated_score':None}


def validate_accessible_markdown(markdown: str) -> dict[str, Any]:
    if not isinstance(markdown,str) or not markdown.strip():
        raise EvaluationStructureError('report_markdown_required')
    lines=markdown.splitlines(); headings=[]; table_headers=[]; table_errors=[]
    for index,line in enumerate(lines):
        heading=re.match(r'^(#{1,6})\s+(.+?)\s*#*$',line)
        if heading:
            headings.append((len(heading.group(1)),heading.group(2)))
        if line.startswith('|'):
            cells=_split_markdown_row(line)
            if index+1>=len(lines) or not re.fullmatch(r'\|(?:\s*:?-{3,}:?\s*\|)+',lines[index+1].strip()):
                table_errors.append(f'table_header_rule_missing_line_{index+1}')
            else:
                separator=_split_markdown_row(lines[index+1])
                if len(separator)!=len(cells): table_errors.append(f'table_header_separator_mismatch_line_{index+1}')
                else: table_headers.append(cells)
            break
    # Validate every table block and consistent column count.
    i=0
    while i<len(lines):
        if not lines[i].startswith('|'):
            i+=1; continue
        try: header=_split_markdown_row(lines[i])
        except EvaluationStructureError:
            table_errors.append(f'malformed_table_header_line_{i+1}'); i+=1; continue
        if i+1>=len(lines) or not re.fullmatch(r'\|(?:\s*:?-{3,}:?\s*\|)+',lines[i+1].strip()):
            table_errors.append(f'table_header_rule_missing_line_{i+1}')
            i+=1; continue
        separator=_split_markdown_row(lines[i+1])
        if len(header)!=len(separator): table_errors.append(f'table_header_separator_mismatch_line_{i+1}')
        i+=2
        while i<len(lines) and lines[i].startswith('|'):
            try:
                if len(_split_markdown_row(lines[i]))!=len(header): table_errors.append(f'table_column_count_mismatch_line_{i+1}')
            except EvaluationStructureError:
                table_errors.append(f'malformed_table_row_line_{i+1}')
            i+=1
    heading_ok=bool(headings) and headings[0][0]==1 and all(
        level<=headings[index-1][0]+1 for index,(level,_) in enumerate(headings[1:],start=1))
    image_alt_ok=all(bool(alt.strip()) for alt in re.findall(r'!\[([^\]]*)\]\([^)]*\)',markdown))
    status_symbols=set('✅❌⚠️🟢🔴🟡')
    color_independent=not any(symbol in markdown for symbol in status_symbols)
    link_labels=re.findall(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)',markdown)
    vague={'here','click here','more','link','こちら','ここ','詳細はこちら'}
    descriptive_links=all(label.strip() and label.strip().lower() not in vague and label.strip()!=url.strip()
                          for label,url in link_labels)
    result={'heading_hierarchy':heading_ok,'table_headers':not table_errors and bool(table_headers),
            'image_text_descriptions':image_alt_ok,'color_independent_state':color_independent,
            'descriptive_link_text':descriptive_links}
    return {'checks':result,'errors':table_errors,'status':'complete' if all(result.values()) else 'blocked'}


def _split_markdown_row(line: str) -> list[str]:
    if not line.startswith('|') or not line.endswith('|'):
        raise EvaluationStructureError('malformed_markdown_table_row')
    return [cell.strip() for cell in re.split(r'(?<!\\)\|',line[1:-1])]


def _report_cell(value: Any) -> str:
    if value is None or value=='': return '-'
    if isinstance(value,(dict,list)):
        value=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return str(value).replace('\\','\\\\').replace('|','\\|').replace('\r\n',' ').replace('\r',' ').replace('\n',' ').strip() or '-'


def _report_table(columns: list[str], rows: list[dict[str,Any]]) -> str:
    header='| '+' | '.join(columns)+' |'
    separator='| '+' | '.join('---' for _ in columns)+' |'
    output=[header,separator]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=set(columns):
            raise EvaluationStructureError('report row does not match fixed columns')
        output.append('| '+' | '.join(_report_cell(row[column]) for column in columns)+' |')
    return '\n'.join(output)


def _field_table(fields: dict[str,Any]) -> str:
    if not isinstance(fields,dict) or not fields:
        raise EvaluationStructureError('report field section must be a non-empty object')
    return _report_table(['Field','Value'],[{'Field':key,'Value':fields[key]} for key in sorted(fields)])


def _random_sample_report_rows(rows: list[dict[str,Any]]) -> list[dict[str,Any]]:
    columns={'Target count','Actual count','Selection method','Selected sample refs','Status','Exhaustion / blocker'}
    if not isinstance(rows,list):
        raise EvaluationStructureError('random sample report rows must be a list')
    output=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=columns:
            raise EvaluationStructureError('random sample report row does not match fixed fields')
        refs=row['Selected sample refs']
        if (not isinstance(refs,list) or any(not isinstance(ref,str) or not ref.strip() for ref in refs)
                or len(refs)!=len(set(refs))):
            raise EvaluationStructureError('random sample selected refs must be unique non-empty strings')
        output.append({**row,'Selected sample refs':', '.join(refs) if refs else 'None selected'})
    return output


def render_machine_owned_report(data: dict[str,Any]) -> dict[str,Any]:
    required={'evaluation_input','scope_rows','exploration_rows','sampling_procedure','structured_samples','random_sample',
        'complete_processes','criterion_plan','sample_results','comparisons','evaluation_outcomes','handoffs','limitations',
        'report_closure'}
    optional={'evaluation_specifics','evaluation_statement','conformance_claim','partial_statement','earl_artifact',
        'sample_lineage'}
    if not isinstance(data,dict) or required-set(data) or set(data)-required-optional:
        raise EvaluationStructureError('report materialization schema mismatch')
    header_fields={'evaluation_ref','revision','evaluator','commissioner','issued_date','evaluation_period','wcag_title',
        'wcag_version','wcag_uri','conformance_level','product_scope','project_authority_refs','release_gate','previous_evaluation_ref'}
    if not isinstance(data['evaluation_input'],dict) or set(data['evaluation_input'])!=header_fields:
        raise EvaluationStructureError('report evaluation header does not match fixed fields')
    structured_sample_fields={'Sample ref','State','Document identity','Type / technology coverage',
        'Process membership','Rationale'}
    structured_samples=data['structured_samples']
    if not isinstance(structured_samples,list):
        raise EvaluationStructureError('structured sample report rows must be an array')
    for row in structured_samples:
        if (not isinstance(row,dict) or set(row)!=structured_sample_fields
                or not isinstance(row.get('Sample ref'),str) or not row['Sample ref'].strip()
                or not isinstance(row.get('State'),str) or not row['State'].strip()
                or not isinstance(row.get('Document identity'),str)
                or not _DOCUMENT_IDENTITY.fullmatch(row['Document identity'])
                or any(not isinstance(row.get(field),str) for field in
                    ('Type / technology coverage','Process membership','Rationale'))):
            raise EvaluationStructureError('structured sample rows require state and opaque document identity; raw locators are not accepted')
    if not isinstance(data['report_closure'],dict) or data['report_closure'].get('status') not in {'complete','blocked'}:
        raise EvaluationStructureError('report closure status is invalid')
    lineage=data.get('sample_lineage')
    lineage_rows=[]
    if lineage is not None:
        lineage_fields={'status','previous_sample_refs','current_structured_sample_refs','retained','replaced','added','unavailable'}
        if not isinstance(lineage,dict) or set(lineage)!=lineage_fields or lineage.get('status')!='ready':
            raise EvaluationStructureError('rerun sample lineage result is invalid')
        for field in ('previous_sample_refs','current_structured_sample_refs','added'):
            values=lineage.get(field)
            if (not isinstance(values,list) or any(not isinstance(value,str) or not value.strip() for value in values)
                    or len(values)!=len(set(values))):
                raise EvaluationStructureError('rerun sample lineage refs are invalid')
        row_contracts={
            'retained':({'previous_sample_ref','current_sample_ref'},'retained'),
            'replaced':({'previous_sample_ref','current_sample_ref','reason','evidence_refs'},'replaced'),
            'unavailable':({'previous_sample_ref','reason'},'unavailable')}
        for field,(expected,status) in row_contracts.items():
            values=lineage.get(field)
            if not isinstance(values,list): raise EvaluationStructureError('rerun sample lineage rows are invalid')
            for row in values:
                if not isinstance(row,dict) or set(row)!=expected:
                    raise EvaluationStructureError('rerun sample lineage row schema mismatch')
                if (not isinstance(row.get('previous_sample_ref'),str) or not row['previous_sample_ref'].strip()
                        or (field!='unavailable' and (not isinstance(row.get('current_sample_ref'),str)
                            or not row['current_sample_ref'].strip()))):
                    raise EvaluationStructureError('rerun sample lineage row refs are invalid')
                if field=='replaced' and (not isinstance(row.get('reason'),str) or not row['reason'].strip()
                        or not isinstance(row.get('evidence_refs'),list) or not row['evidence_refs']):
                    raise EvaluationStructureError('rerun sample replacement decision lacks provenance')
                if field=='unavailable' and (not isinstance(row.get('reason'),str) or not row['reason'].strip()):
                    raise EvaluationStructureError('unavailable rerun sample lacks a reason')
                lineage_rows.append({'Previous sample ref':row['previous_sample_ref'],
                    'Lineage status':status,
                    'Current sample ref':row.get('current_sample_ref'),
                    'Reason / evidence':(row.get('reason','') + ('; evidence: '+', '.join(row['evidence_refs'])
                        if field=='replaced' else ''))})
        for sample_ref in lineage['added']:
            lineage_rows.append({'Previous sample ref':'','Lineage status':'added',
                'Current sample ref':sample_ref,'Reason / evidence':''})
    lines=['# WCAG-EM 2.0 Evaluation Report','', '## Evaluation Input','',_field_table(data['evaluation_input']),
        '', '## Step 1: Define evaluation scope','',_report_table(['Scope ref','Area','In scope / outside product / unresolved','Reason','Evidence refs'],data['scope_rows']),
        '', '## Step 2: Explore the target Web product','',_report_table(['Exploration ref','Views / functionality / technology / sample type','Outcome','Evidence / provenance'],data['exploration_rows']),
        '', '## Step 3: Select representative samples','', '### Sampling procedure','',
        _report_table(['Procedure','Status','Rationale / complete inventory','Candidate provenance / fingerprint'],data['sampling_procedure'])]
    if lineage is not None:
        lines.extend(['','### Rerun Sample Lineage','',_report_table(
            ['Previous sample ref','Lineage status','Current sample ref','Reason / evidence'],lineage_rows)])
    lines.extend([
        '', '### Structured Sample','',_report_table(['Sample ref','State','Document identity','Type / technology coverage','Process membership','Rationale'],structured_samples),
        '', '### Random Sample','',_report_table(
            ['Target count','Actual count','Selection method','Selected sample refs','Status','Exhaustion / blocker'],
            _random_sample_report_rows(data['random_sample'])),
        '', '### Complete Processes','',_report_table(['Process ref','Ordered sample/action sequence','Completion condition','Evidence refs'],data['complete_processes']),
        '', '## Step 4: Audit the selected sample','', '### Criterion Evaluation Plan','',
        _report_table(['Evaluation ref','Sample / variation / process','Criterion','Procedure closure','Population','Execution status','Result','Evidence / limitation'],data['criterion_plan']),
        '', '### Sample Evaluation Results','',_report_table(['Result ref','Sample / variation','Requirement','Criterion evaluation ref','Result','Example refs','Evidence / limitation'],data['sample_results']),
        '', '### Structured / Random Comparison','',_report_table(['Iteration','New content type','New finding group','Action','Added sample refs'],data['comparisons']),
        '', '## Step 5: Report the evaluation findings','', '### Evaluation Outcome','',
        _report_table(['Requirement / criterion','Outcome','Example refs','Scope / limitation'],data['evaluation_outcomes'])])
    if data.get('evaluation_specifics'):
        lines.extend(['','### Evaluation Specifics (when requested)','',_report_table(
            ['Scope','Archive / evidence ref','Path / settings / actions','Tool / version / method','Confidentiality limitation'],data['evaluation_specifics'])])
    for key,title in (('evaluation_statement','Evaluation Statement (Step 5.3 status)'),
                      ('conformance_claim','WCAG Conformance Claim (when eligible)'),
                      ('partial_statement','Statement of Partial Conformance (when eligible)')):
        if data.get(key) is not None: lines.extend(['','### '+title,'',_field_table(data[key])])
    if data.get('earl_artifact') is not None:
        lines.extend(['','### EARL JSON-LD (when requested)','',_field_table(data['earl_artifact'])])
    lines.extend(['','## Handoffs, freshness, cleanup, and unresolved blockers','',
        _report_table(['Handoff / operation','Origin revision','Expected / returned evidence','CAS / reservation / cleanup','Resume status'],data['handoffs']),
        '', '## Accessible output closure','',
        _report_table(['Check','Result','Evidence / correction'],[
            {'Check':'Heading hierarchy','Result':'PASS','Evidence / correction':'Fixed report heading hierarchy'},
            {'Check':'Table headers','Result':'PASS','Evidence / correction':'Fixed table header and row schema'},
            {'Check':'Evidence image descriptions','Result':'PASS','Evidence / correction':'Every rendered image has non-empty alternative text'},
            {'Check':'Color-independent state','Result':'PASS','Evidence / correction':'State uses text labels'},
            {'Check':'Descriptive links','Result':'PASS','Evidence / correction':'Links use descriptive labels'}]),
        '', '## Limitations','',_report_table(['Limitation','Status / scope','Evidence / next action'],data['limitations']),
        '', '## Machine Runtime / Summary','',_field_table({
            'criterion evaluation rows':len(data['criterion_plan']),'sample result rows':len(data['sample_results']),
            'not-satisfied outcomes':sum(row.get('Outcome')=='not-satisfied' for row in data['evaluation_outcomes']),
            'blocked handoffs':sum(row.get('Resume status')=='blocked' for row in data['handoffs']),
            'report closure':data['report_closure']['status'],'aggregated score':'not generated'}),
        '', 'No aggregated conformance score is generated. Repository fixtures test methodology implementation and do not establish conformance of an external product.',''])
    markdown='\n'.join(lines)
    accessible=validate_accessible_markdown(markdown)
    if accessible['status']!='complete':
        return {'status':'blocked','reason':'accessible_output_contract_failed','machine_owned_markdown':None,
                'accessible_output_closure':accessible}
    return {'status':'generated','machine_owned_markdown':markdown,
            'accessible_output_closure':accessible['checks'],
            'summary':{'criterion_evaluation_rows':len(data['criterion_plan']),'sample_result_rows':len(data['sample_results']),
                       'not_satisfied_outcomes':sum(row.get('Outcome')=='not-satisfied' for row in data['evaluation_outcomes']),
                       'blocked_handoffs':sum(row.get('Resume status')=='blocked' for row in data['handoffs']),
                       'aggregated_score':None}}
