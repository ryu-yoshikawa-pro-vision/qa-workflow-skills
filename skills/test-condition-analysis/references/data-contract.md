# Test condition candidate data contract

## Inputs and outputs

The upstream feature input is B's `feature-inventory-v1`. D preserves its `project_ref`, `artifact_ref`, `artifact_revision`, `source_revision`, and `handoff.snapshot_sha256`. Authority refs are `{source_ref, entity_ref}` with a source ref owned by `spec-analysis`. A source ref is `{owner, scope, artifact_ref, revision, content_hash}`. D validates shape and links but does not re-run upstream owner validators or authenticate provider readback.

The helper accepts exact `materialize`, `validate`, `impact`, `validate_readback`, and `crosscheck` operations. Candidate rows provide request-local keys, an explicit identity action, intent, kind, applicable item kinds, feature/item refs, evidence/Authority refs, candidate state, unknowns, and reason. Unknown fields are rejected.

## Candidate artifact

Schema `test-condition-candidates-v1` contains owner, scope, logical artifact ref, exact feature inventory source ref and population, source-boundary state, historical/current source refs, previous provider revision, condition candidates, append-only ID history, change events, and a canonical content fingerprint. A candidate has `COND-*`, name, intent, kind, applicable item kinds, feature refs, optional item refs, Authority refs, evidence refs, candidate state (`candidate`, `unconfirmed`, `blocked`), currentness, and unknowns.

The fingerprint is SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators, excluding only `content_fingerprint`. It is not the provider's artifact revision.

An explicit merge records the new condition ID's links to its source IDs. Every merge source must also be explicitly retired in the same update with current evidence; otherwise the merge is rejected so old and merged meanings cannot remain active together. Retired IDs remain in `id_history` and are never recycled.

## Crosscheck and storage handoff

`item-condition-candidate-crosscheck-v1` returns explicit proposed pairs and gaps. It never creates all combinations and never carries an E-owned formal decision. Candidate counts are numeric; out-of-owner applicability, formal design, and execution counts are `null` with `not_provided_to_D` state.

`write_precondition.performed` is always false. The A adapter must create an operation claim from owner, scope, operation kind, target ref, source revisions, expected revision, approval ref, required permission, and resume owner; then use provider-native CAS/create-if-absent and independently read back the same content hash. The local `validate_readback` only compares the supplied tuple and hash. No real provider or authenticated approval is connected in this D branch.
