# Candidate output

```json
{
  "action": "create",
  "entry": {
    "schema_version": "1",
    "entry_ref": "KN-975f88a44ac089a7d6a85b5190643f94a9873d004b69d2d947828323d0736dd5",
    "identity": {
      "kind": "test_environment",
      "scope_refs": [
        "project:checkout"
      ],
      "subject": "staging-job-delay"
    },
    "kind": "test_environment",
    "content": "stagingのexternal jobは完了状態の反映が遅れることがある。authoritative completion stateを確認してから結果を判断する。",
    "scope_refs": [
      "project:checkout"
    ],
    "applicability": {
      "environment": [
        "staging"
      ],
      "version": "job-config-v3"
    },
    "provenance": [
      {
        "ref": "activity:ACT-020",
        "revision": "rev:act20"
      }
    ],
    "currentness_dependencies": [
      {
        "ref": "config:job-status",
        "revision": "rev:cfg3"
      }
    ],
    "last_verified": {
      "at": "2026-09-27",
      "condition": "job-config-v3 / staging"
    },
    "state": "有効",
    "replacement_ref": null,
    "related_qa_refs": [
      "test-case:TC-025"
    ]
  },
  "currentness_status": "current",
  "storage": {
    "atomic_create_if_absent": true,
    "complete_root_snapshot": true,
    "returned_entry_revision": "sha256:known-provider-token"
  }
}
```
