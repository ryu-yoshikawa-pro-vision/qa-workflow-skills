# Test item candidate data contract

## Input sources

`feature_inventory` is B's `feature-inventory-v1` result. D derives the feature source ref as `{owner: feature-analysis, scope: project_ref, artifact_ref, revision: artifact_revision, content_hash: handoff.snapshot_sha256}`. Other source refs use A's published owner/scope/artifact/revision/content-hash tuple. Each candidate must cite current refs from the invocation.

The item helper accepts exact `materialize`, `validate`, `impact`, and `validate_readback` request shapes. `materialize` requires scope, logical artifact ref, feature inventory, current source refs, expected/current provider revisions, approval ref, permission requirement, previous artifact, candidates, and explicit retirements. Candidate rows carry request-local keys and explicit identity decisions. The complete field lists are enforced by the helper.

## Candidate artifact

Schema `test-item-candidates-v1` contains owner, scope, logical artifact ref, feature-inventory ref, feature population and boundary state, historical and active source refs, previous provider revision, item rows, retained ID history, append-only change events, and a canonical content fingerprint. Item rows contain stable item ID, name, description, kind, status, parent IDs, multiple feature refs, evidence refs, and currentness.

The content fingerprint is SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators, excluding only `content_fingerprint`. It is a candidate payload fingerprint, not a provider revision, approval, or proof of persistence.

An explicit merge records the new ID's links to its source IDs. Each merge source must also be explicitly retired in the same update with current evidence; otherwise the merge is rejected so the old and merged items cannot remain active together. Retired IDs remain in `id_history` and are never recycled.

## Storage handoff

`write_precondition.performed` is always false. The adapter must map the owner, scope, artifact ref, source revisions, expected revision, permission, approval ref, and resume owner into A's operation claim and selected provider. The provider must use native create-if-absent/CAS, save an immutable revision, and independently read back the same hash. The local `validate_readback` checks tuple/hash consistency only; it cannot authenticate a provider or prove CAS.

There is no legacy D artifact schema. Existing feature, Authority, TCN, CI, TC, and workflow artifacts remain owned by their existing Skills and are read by ref only.
