# Test condition candidate data contract

## B input and sources

The `feature_inventory` request value is the exact B snapshot paired with the separate `feature_registry.analyze()` result:

```json
{
  "snapshot": { "schema_version": "feature-inventory-v1" },
  "analysis": {
    "status": "complete",
    "reasons": [],
    "metrics": {},
    "handoff": {}
  }
}
```

D checks B's published analysis/handoff field sets, snapshot SHA-256, project/artifact identity and revisions, source inventory, feature projection and IDs, boundary state, and metric consistency. It does not call B's persistence path or duplicate B's full validator. `incomplete` input is preserved as incomplete and cannot establish a complete population; `stale`, `blocked`, `idempotent`, mismatched, and malformed input is rejected. `project_ref` must equal D's scope.

D derives the feature source ref as `{owner: "feature-analysis", scope: project_ref, artifact_ref, revision: artifact_revision, content_hash: handoff.snapshot_sha256}`. The artifact also carries the separate B `source_revision`, source inventory, expected source IDs, feature IDs, and unknown areas in `feature_inventory_context`. The B stored revision, source revision, and snapshot hash remain distinct values.

Authority refs are `{source_ref, entity_ref}` with a source ref owned by `spec-analysis`. Every source ref is `{owner, scope, artifact_ref, revision, content_hash}`. A current source set may contain only one revision/hash for each logical source `(owner, scope, artifact_ref)`; historical source sets may retain older revisions. Currentness compares logical identity and exact revision/hash, independent of input order. Revision matching does not prove CAS or provider readback.

The helper accepts exact `materialize`, `validate`, `impact`, `validate_readback`, and `crosscheck` request shapes. Candidate rows use request-local keys and explicit identity actions. Unknown fields are rejected.

## JSON input boundary

The standalone CLI accepts strict UTF-8 JSON up to 16 MiB. Duplicate object keys, malformed JSON, non-finite constants such as NaN or Infinity, and inputs beyond the byte limit return a blocked result. Canonical serialization also rejects non-finite values; item and condition packages carry byte-identical parsing helpers.

## Candidate artifact and compatibility

Schema `test-condition-candidates-v1` contains owner, scope, logical artifact ref, feature inventory ref and context, feature population and boundary state, historical/current source refs, previous provider revision, condition candidates, append-only ID history, change events, and a canonical content fingerprint. A candidate has a stable `COND-*`, name, intent, kind, applicable item kinds, feature refs, optional item refs, Authority refs, evidence refs, candidate state (`candidate`, `unconfirmed`, `blocked`), currentness, and unknowns.

The fingerprint is SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators, excluding only `content_fingerprint`. It identifies the candidate payload, not the provider's artifact revision.

Older v1 item and condition artifacts without `feature_inventory_context` remain readable when their semantic fields, history, refs, and fingerprints validate. A crosscheck using such artifacts is `incomplete`; it does not infer a complete source population. The next materialization adds current B context and retains existing IDs and historical event IDs. Legacy event IDs are checked against their legacy event-body fingerprint. New appended IDs bind the event body, sequence, and previous event ID, preserving deterministic replay and uniqueness when different updates share the same reason and evidence.

An explicit merge records the new condition ID's links to source IDs. Every merge source must also be explicitly retired in the same update with current evidence; otherwise the merge is rejected. Retired IDs remain in `id_history` and are never reused.

## Materialization result

`valid` means that the request and candidate artifact satisfy D's structural contract. It does not mean analysis completion, E approval, persistence, or readback. `status: no_change` means only that candidate content is unchanged. The result separately returns `analysis_status` (`complete` or `incomplete`), current issues, stale/unknown/unconfirmed/blocked condition IDs, `unknown_feature_ids`, and recheck condition IDs. Unconfirmed and blocked conditions remain incomplete when the same request is replayed. A feature whose B status is `unknown` is not a confirmed active feature: it is returned in `unknown_feature_ids` with a non-blocking `unknown_feature_status` issue and keeps `analysis_status: incomplete` (never `candidate_ready_unpersisted`), including on a `no_change` replay. This is the same rule `test-item-analysis` applies; retired and confirmed features do not trigger it, and it does not alter the candidate artifact, B input contract, or history.

For `no_change`, `candidate` is the prior validated artifact unchanged: stable IDs, history, and fingerprint are preserved and no event is appended. `write_precondition.performed` and `provider_selected` are false; no provider write, CAS, or readback is requested by this result. Diagnostics are recomputed from the current input and candidate projection, retaining incomplete B analysis, source/currentness uncertainty, and condition blockers. Candidate condition and explicit pair information remains advisory; formal applicability and execution stay with their owners.

## Crosscheck and D-to-E boundary

`item-condition-candidate-crosscheck-v1` validates the item artifact using the same byte-identical read-only contract helper embedded in the isolated item and condition packages. It checks semantic fields and references, not just the candidate fingerprint. Scope, B feature ref/population/context, and active source revisions must agree across both artifacts.

Only explicitly supplied candidate pairs are checked; no item × condition Cartesian product is generated. Duplicate pairs and malformed IDs are rejected. A well-formed but missing item ID, a retired item, or an unconfirmed/stale item is reported as unresolved with reason and recheck IDs; D never creates an item or changes the condition ID. A well-formed pair whose registered condition is still a `candidate` but whose currentness is `stale` or `unknown` is reported the same way in `unresolved_condition_references` (reason `condition_stale` or `condition_currentness_unknown`, the original pair status and rationale retained, no `candidate_pairs` row), and both the condition and the item are added to `recheck_condition_ids` / `recheck_item_ids`; the condition stays in `stale_condition_ids` / `unknown_condition_ids`, the crosscheck stays incomplete, and no formal decision is made. A `proposed` pair that references an `unconfirmed` or `blocked` condition is still rejected (`candidate_pair_unconfirmed`), even if that condition's evidence is also stale or unknown, so an uncertain condition cannot be promoted by the caller. This check runs before unresolved references are reported, so it applies whatever the item's state (current, stale, unknown, retired, or not found); an unregistered condition has no state to check and is reported as an unresolved condition reference instead. `unconfirmed`/`blocked` pair statuses remain valid advisory pairs. Pair evidence must resolve to supplied source history. A proposed pair with a machine-detectable item-kind conflict, disjoint nonempty feature refs, or stale/unknown pair evidence is downgraded to `unconfirmed` and returned with issue codes. Formal applicability remains E-owned.

Retired item/condition IDs are reported separately from active candidates without a pair proposal. Stale or unknown item/condition currentness, incomplete B population, unknown feature status, unconfirmed/blocked conditions, unresolved refs, pair conflicts, and a zero feature denominator prevent `candidate_crosscheck_complete`. Candidate counts, formal E applicability/design counts, and execution counts remain separate; counts outside D ownership are `null` with `not_provided_to_D`. Missing candidate pairs are reported as candidate gaps and do not become formal E disposition decisions.

D exposes owner/scope/logical artifact refs, stable item/condition IDs, candidate fingerprints, current source refs/revisions, known gaps, and unknowns for E to consume. PR #27 (draft, unmerged; checked at `bda79aa`) implements the E `formal-design-v1` validator, which uses `TI-*` item refs, `COND-*` condition refs, `{ref, revision, currentness}` source refs, boolean completeness flags, and an explicit decision for every item × condition pair. No D-to-E adapter exists in D, E, or shared code, and D's `ITEM-*` IDs and `{owner, scope, artifact_ref, revision, content_hash}` refs do not map to those shapes automatically; this document does not fix or implement that mapping or change the E schema. A D `proposed` pair is never an E `adopted` decision, and D's local `candidate_crosscheck_complete` or identification rate is not E's formal completeness or coverage. E owns item-condition adoption/rejection, formal Disposition, TCN/CI, and expected results. Real D artifacts and the E owner validator must be cross-connected in PR #22.

## Storage handoff

`write_precondition.performed` and `provider_selected` are false. The nested A operation-claim details use `owner_skill`, `scope_ref`, `operation_type`, `target_ref`, `source_revisions`, `artifact_revisions`, `expected_revision`, `approval_ref`, `permission_scope`, and `resume_owner`, matching A's current validator. D does not claim authenticated approval, persistence, CAS, or readback.

The A-owned adapter must select an authorized provider, use native CAS/create-if-absent, preserve immutable history, and independently read back the saved hash. Three different values must not be conflated: the candidate `content_fingerprint`, the **storage content hash**, and the provider revision. The storage content hash (`write_precondition.storage_content_sha256`, encoding `storage_content_encoding: canonical-json-utf8`) is the SHA-256 of the canonical UTF-8 JSON bytes of the **complete** candidate artifact including `content_fingerprint`; a provider that stores exactly those bytes reports this value as `content_hash`, consistent with A's existing storage, where `artifact_sha256` is the SHA-256 of the stored bytes. The provider revision (for A's local baseline `sha256:` plus that digest, for other providers an opaque value) is provider-owned and is never derived from the fingerprint. `validate_readback` accepts `{operation, candidate_artifact, readback}` and an optional `expected_revision`. It requires `readback.content_hash` to equal the storage content hash (`readback_hash_mismatch` otherwise, including when the candidate fingerprint is supplied instead) and, only when `expected_revision` is given, `readback.revision` to equal it (`readback_revision_mismatch`). It returns the candidate fingerprint and storage content hash separately. It checks consistency only and does not authenticate a provider or prove CAS, approval, persistence, or readback; a provider that stores different bytes (for example a different serialization) must be bridged by the A-owned adapter, which is outside D. A candidate fingerprint must never be presented as the saved provider revision.
