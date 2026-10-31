# Eval Input

正規形は`assets/output-template.md`を使います。下記はこのfixture用の合成discovery snapshot入力とmembership decisionです。`scripts/regression_runtime.py`の`build_discovery_snapshot`と`reconcile_membership`でsnapshotとmembership projectionを生成し、返された値を使ってbaselineを作成してください。scope identityとcoverage gapも入力値をそのまま使います。

このfixture用に割り当て済みの`baseline_ref`は`fixture:qa/regression/baseline/settings-auth-v1`です。この値を保持し、新しいIDを発行・推測しないでください。

```json
{
  "scope_identity": "regression-scope:settings-auth",
  "discovery_input": {
    "discovery_roots": ["fixture:qa/test-cases"],
    "listing_complete": true,
    "source_revisions": [
      {
        "source_ref": "fixture:qa/test-cases",
        "revision": "fixture-listing-r10"
      },
      {
        "source_ref": "fixture:qa/test-cases/TC-001.json",
        "revision": "fixture-tc-001-r3"
      },
      {
        "source_ref": "fixture:qa/test-cases/TC-002.json",
        "revision": "fixture-tc-002-r4"
      },
      {
        "source_ref": "fixture:qa/test-cases/TC-003.json",
        "revision": "fixture-tc-003-r2"
      }
    ],
    "cases": [
      {
        "tc_ref": "TC-001",
        "source_ref": "fixture:qa/test-cases/TC-001.json",
        "source_revision": "fixture-tc-001-r3",
        "lifecycle_status": "current",
        "content_fingerprint": "fixture-fingerprint-tc-001-r3"
      },
      {
        "tc_ref": "TC-002",
        "source_ref": "fixture:qa/test-cases/TC-002.json",
        "source_revision": "fixture-tc-002-r4",
        "lifecycle_status": "current",
        "content_fingerprint": "fixture-fingerprint-tc-002-r4"
      },
      {
        "tc_ref": "TC-003",
        "source_ref": "fixture:qa/test-cases/TC-003.json",
        "source_revision": "fixture-tc-003-r2",
        "lifecycle_status": "current",
        "content_fingerprint": "fixture-fingerprint-tc-003-r2"
      }
    ]
  },
  "membership_decisions": [
    {
      "tc_ref": "TC-001",
      "decision": "member",
      "reason": "認証設定の継続Regression対象",
      "source_refs": ["fixture:qa/test-cases/TC-001.json"],
      "source_revisions": [
        {
          "source_ref": "fixture:qa/test-cases/TC-001.json",
          "revision": "fixture-tc-001-r3"
        }
      ]
    },
    {
      "tc_ref": "TC-002",
      "decision": "member",
      "reason": "認証設定の継続Regression対象",
      "source_refs": ["fixture:qa/test-cases/TC-002.json"],
      "source_revisions": [
        {
          "source_ref": "fixture:qa/test-cases/TC-002.json",
          "revision": "fixture-tc-002-r4"
        }
      ]
    },
    {
      "tc_ref": "TC-003",
      "decision": "member",
      "reason": "認証設定の継続Regression対象",
      "source_refs": ["fixture:qa/test-cases/TC-003.json"],
      "source_revisions": [
        {
          "source_ref": "fixture:qa/test-cases/TC-003.json",
          "revision": "fixture-tc-003-r2"
        }
      ]
    }
  ],
  "coverage_gaps": []
}
```
