# QA Knowledge data contract

```json
{
  "schema_version":"1",
  "entry_ref":"KN-<sha256(identity-json)>",
  "identity":{"kind":"test_environment","scope_refs":["project:checkout"],"subject":"staging-job-delay"},
  "kind":"test_environment",
  "content":"Staging job status may lag for several minutes; query authoritative completion state before deciding the test result.",
  "scope_refs":["project:checkout"],
  "applicability":{"environment":["staging"],"version":"all versions of this configuration"},
  "provenance":[{"ref":"activity:ACT-1","revision":"opaque-token"}],
  "currentness_dependencies":[{"ref":"config:job-status","revision":"opaque-token"}],
  "last_verified":{"at":"","condition":""},
  "state":"有効",
  "replacement_ref":null,
  "related_qa_refs":[]
}
```

Kinds are `test_subject_or_mechanism`, `test_focus`, `test_environment`. States are `有効`, `要再検証`, `置換済み`. Provenance and dependency refs each require the revision read from their owning source. Each entry is stored as `<entry-ref>.md` with one JSON fenced block; `entry_revision` is storage metadata kept in the calling workflow / Activity, not written into the entry body. A local-file digest can identify the exact file bytes for a current read, but is never treated as an atomic update condition; if an older version cannot be fetched, historical use is blocked.

Callers pass an explicit structured identity object. The helper sorts JSON object keys only; it does not infer semantic equivalence, reorder caller arrays, or use an LLM to choose identity.
