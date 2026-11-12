# Test item candidate data contract

## B input

The `feature_inventory` request value is the B-owned snapshot paired with the separate result of `feature_registry.analyze()`:

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

`snapshot` is the exact object analyzed by B. D requires its `project_ref`, `artifact_ref`, `artifact_revision`, `source_revision`, `expected_source_ids`, `sources`, `features`, `candidates`, `changes`, and `unknown_areas`. B's `analysis` result and handoff field sets are checked against the published contract; the snapshot SHA-256, identity/revision tuple, source inventory, feature projection, IDs, boundary state, and derived metrics must agree. D does not invoke B's persistence path or duplicate B's full validator.

The only current analysis statuses accepted by D are `complete` and `incomplete`. An incomplete analysis can be used for local candidate work, but D stores `analysis_status: incomplete`, preserves partial sources and `unknown_areas`, and does not treat the population as complete. `stale`, `blocked`, and `idempotent` results have no current handoff and are rejected. `project_ref` must equal D's scope.

## JSON input boundary

The standalone CLI accepts strict UTF-8 JSON up to 16 MiB. Duplicate object keys, malformed JSON, non-finite constants such as NaN or Infinity, and inputs beyond the byte limit return a blocked result. Canonical serialization also rejects non-finite values; item and condition packages carry byte-identical parsing helpers.

D derives the feature source ref as `{owner: "feature-analysis", scope: project_ref, artifact_ref, revision: artifact_revision, content_hash: handoff.snapshot_sha256}`. It separately preserves B's `source_revision`, source inventory, expected source IDs, feature IDs, and unknown areas in `feature_inventory_context`. This ref's stored artifact revision and snapshot hash are not the source revision and are not D's candidate fingerprint.

Other source refs use A's `{owner, scope, artifact_ref, revision, content_hash}` tuple. Within a current invocation, each logical source `(owner, scope, artifact_ref)` may have one revision/hash only; duplicate exact refs and competing current revisions are rejected. Historical `source_refs` may retain older revisions. Currentness is derived from logical source identity and the exact revision/hash, independent of input order. A source revision comparison is not proof that a provider-side CAS ran.

## Candidate artifact

Schema `test-item-candidates-v1` contains owner, scope, logical artifact ref, feature inventory ref and context, feature population and boundary state, historical and active source refs, previous provider revision, item rows, retained ID history, append-only change events, and a canonical content fingerprint. Item rows contain stable item ID, name, description, kind, status, parent IDs, multiple feature refs, evidence refs, and derived currentness.

The content fingerprint is SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators, excluding only `content_fingerprint`. It identifies this candidate payload; it is not the saved provider revision, an approval, or proof of persistence. Stable IDs are never allocated from names or reused after retirement.

Older v1 artifacts without `feature_inventory_context` remain readable if their semantic fields, history, refs, and fingerprint validate. They cannot establish a complete B population in crosscheck. A later materialization attaches the current B context while preserving existing IDs and history; it does not rewrite historical events. Legacy event IDs are checked against their legacy event-body fingerprint. New appended event IDs bind the event body, sequence, and previous event ID, so repeated updates with the same reason/evidence remain unique and deterministic.

An explicit merge records the new ID's links to its source IDs. Each merge source must also be explicitly retired in the same update with current evidence; otherwise the merge is rejected so the old and merged items cannot remain active together. Retired IDs remain in `id_history` and are never recycled.

## Materialization result

`valid` means that the request and candidate artifact satisfy D's structural contract. It does not mean the analysis is complete, the candidate is approved, or an artifact was saved. `status: no_change` means only that the candidate content is unchanged. The result separately returns `analysis_status` (`complete` or `incomplete`), current issues, stale/unknown/recheck item IDs, unrepresented feature IDs, and the item identification metric. `item_candidate_coverage` is `{status, basis, numerator, denominator, rate, zero_denominator}` over confirmed active features only: features that are neither `retired` nor `unknown`. Only when `status` is `measured` are `numerator` (confirmed active features represented by non-retired items), `denominator` and `rate` set. In every `not_measurable_*` state (`zero_denominator`, `incomplete_population`, `unknown_feature_status`, `stale_or_unknown_items`, checked in that order) numerator, denominator and rate are all null, so an unconfirmed population is never reported as measured or 100%. `test-condition-analysis` crosscheck uses the same shared rule and returns an identical metric. It is a candidate identification metric only and does not change Authority, TCN/CI, Disposition, or formal coverage. A known active feature without an item candidate keeps `analysis_status: incomplete` and an `unrepresented_feature_candidates` issue, even when no candidate content changed. A feature whose B status is `unknown` is not confirmed active: it is returned in `unknown_feature_ids` with a non-blocking `unknown_feature_status` issue, keeps `analysis_status: incomplete`, and makes the identification metric `not_measurable_unknown_feature_status` (null rate and denominator). Retired items are excluded from `stale_item_ids`, `unknown_item_ids`, `recheck_item_ids`, and the `source_stale` and `source_unknown` issues, and a source change appends no `source_changed` event to them; their stored `currentness` remains derived from their evidence so existing artifacts keep validating. `impact` likewise reports retired items in `retired_item_ids`, not in `impacted_item_ids`, `source_unknown_item_ids`, or `unaffected_item_ids`.

For `no_change`, `candidate` is the prior validated artifact unchanged: stable IDs, history, and fingerprint are preserved and no event is appended. `write_precondition.performed` and `provider_selected` are false; no provider write, CAS, or readback is requested by this result. Diagnostics and metrics are recomputed from the current input and candidate projection so a repeated request cannot hide an incomplete B analysis, source/currentness uncertainty, or candidate gap. Candidate identification metrics remain separate from formal coverage and execution.

## Storage handoff

`write_precondition.performed` and `provider_selected` are false. `operation_claim_details` is formatted for A's published claim validator: `owner_skill`, `scope_ref`, `operation_type`, `target_ref`, `source_revisions`, `artifact_revisions`, `expected_revision`, `approval_ref`, `permission_scope`, and `resume_owner`. The current helper validates claim field bounds and carries at most 256 source revisions. It does not claim that permission or approval was authenticated.

The A-owned adapter must select an authorized provider, enforce native create-if-absent/CAS on the expected provider revision, persist immutable history, and independently read back the exact saved hash before reporting success. Three different values must not be conflated: the candidate `content_fingerprint`, the **storage content hash**, and the provider revision. The storage content hash (`write_precondition.storage_content_sha256`, encoding `storage_content_encoding: canonical-json-utf8`) is the SHA-256 of the canonical UTF-8 JSON bytes of the **complete** candidate artifact including `content_fingerprint`; a provider that stores exactly those bytes reports this value as `content_hash`, consistent with A's existing storage, where `artifact_sha256` is the SHA-256 of the stored bytes. The provider revision (for A's local baseline `sha256:` plus that digest, for other providers an opaque value) is provider-owned and is never derived from the fingerprint. `validate_readback` accepts `{operation, candidate_artifact, readback}` and an optional `expected_revision`. It requires `readback.content_hash` to equal the storage content hash (`readback_hash_mismatch` otherwise, including when the candidate fingerprint is supplied instead) and, only when `expected_revision` is given, `readback.revision` to equal it (`readback_revision_mismatch`). It returns the candidate fingerprint and storage content hash separately. It checks consistency only and does not authenticate a provider or prove CAS, approval, persistence, or readback; a provider that stores different bytes (for example a different serialization) must be bridged by the A-owned adapter, which is outside D.

Existing feature, Authority, TR, TCN, CI, TC, and workflow artifacts remain owned by their existing Skills and are read by ref only.
