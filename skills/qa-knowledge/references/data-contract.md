# QA Knowledge data contract

```json
{
  "schema_version": "1",
  "entry_ref": "KN-<sha256(identity-json)>",
  "identity": {
    "kind": "test_environment",
    "scope_refs": ["project:checkout"],
    "subject": "staging-job-delay"
  },
  "kind": "test_environment",
  "content": "Staging job status may lag for several minutes; query authoritative completion state before deciding the test result.",
  "scope_refs": ["project:checkout"],
  "applicability": {
    "environment": ["staging"],
    "version": "all versions of this configuration"
  },
  "provenance": [{ "ref": "activity:ACT-1", "revision": "opaque-token" }],
  "currentness_dependencies": [
    { "ref": "config:job-status", "revision": "opaque-token" }
  ],
  "last_verified": { "at": "", "condition": "" },
  "state": "有効",
  "replacement_ref": null,
  "related_qa_refs": []
}
```

Kinds are `test_subject_or_mechanism`, `test_focus`, `test_environment`. States are `有効`, `要再検証`, `置換済み`. Provenance and dependency refs each require a string `ref` and a string `revision` read from their owning source. A JSON array or object where a string is required (`identity.kind`, `kind`, `state`, `scope_refs`, dependency `ref` / `revision`) is a validation issue (`blocked` / `incomplete`), never an exception. Each entry is stored as `<entry-ref>.md` with one JSON fenced block; `entry_revision` is storage metadata kept in the calling workflow / Activity, not written into the entry body. A local-file digest can identify the exact file bytes for a current read, but is never treated as an atomic update condition; if an older version cannot be fetched, historical use is blocked.

## Identity and applicability invariants

`identity.kind` must be a valid kind and equal the top-level `kind`. `identity.scope_refs` must be a non-empty list equal to the top-level `scope_refs`, including order. `entry_ref` matching the identity hash is necessary but not sufficient. Create, read, update, replacement, revalidation and lookup all apply the same check (`identity_issues()`). `plan_update()` and `plan_replacement()` require the current and new entries, so the check cannot be skipped by omitting them; an inconsistent entry is rejected and returned to its owner, never repaired from the top-level values, re-numbered, or reused for another scope.

## Stored revision hand-off

`read_entry()` returns `entry` and `entry_revision` separately. Pass the pair to `lookup()` as a copy of the entry with the revision attached (`lookup_input()`); do not write `entry_revision` into the stored body (`create_entry()` rejects it) and do not use any revision other than the one actually read. `read_root_entries()` / `lookup_root()` read every entry again on each call, so a different Agent session does not reuse an earlier search result.

## Storage write and readback

`create_entry()` returns a revision only after reading the stored bytes back and finding the same entry. `update_entry()` writes only through a caller-supplied storage-native `conditional_write(path, content, expected_revision)` (compare-and-set owned by the provider); without one it is `blocked`, and the helper never does its own compare-then-write. A provider conflict, an unconfirmed write, or a readback that differs is never reported as success, and conflicts are never auto-merged. The returned `entry_revision` is a local content digest, not a CAS condition, and an earlier revision cannot be read back (`historical_revision_available=false`).

## Hand-off to the shared runtime

`improvement_reference()` returns a reference-only record with the fields the common runtime expects: `owner_skill`, `artifact_ref`, `content_hash` / `entry_revision`, `source_refs`, `currentness_dependencies`, `validation` (inline result; `result_ref` is `null` until the caller stores it), `state` (`current` / `stale` / `blocked`), `unresolved`, `resume` and `required_approval`. Without a dependency snapshot the state is `blocked`. Approval is never recorded here; the improvement owner decides.

## Lookup scope

`lookup()` first checks that the root listing is complete and that each entry's identity and scope can be decided. Entries that certainly do not apply (other scope, kind, environment or version) are not checked for content or dependencies; an unfetchable dependency of such an entry is reported only in `out_of_scope_diagnostics`. An applicable entry with unresolved, invalid or stale dependencies is never returned as current. Broken identity, unresolved scope, duplicate or missing refs, unreadable files and truncated root listings make the result `incomplete`. `plan_revalidation()` selects only entries whose own dependencies changed or are unresolved; scope-limited requests and unchanged entries are left alone, and a repository HEAD change alone selects nothing. Each target carries the stored `entry_revision` that was read as its expected revision. A non-object entry, broken identity, a dependencies field that is not a list, or a target without a stored revision is reported in `rejected` and makes the plan `incomplete`; it is never dropped silently. Stale, unresolved-dependency and invalid-identity entries are reported separately.

## Identity input

Callers pass an explicit structured identity object. The helper sorts JSON object keys only; it does not infer semantic equivalence, reorder caller arrays, or use an LLM to choose identity.
