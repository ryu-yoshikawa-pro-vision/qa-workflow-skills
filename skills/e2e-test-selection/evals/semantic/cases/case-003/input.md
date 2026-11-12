新規候補はTI-003だけです。既存選定E2ESEL-004 revision 1の評価fixture readbackは次のとおりです。

```json
{
  "schema_version": "e2e-selection-v1",
  "selection_ref": "E2ESEL-004",
  "revision": 1,
  "change_reason": "初回のE2E自動化価値判断",
  "scope_refs": ["TI-001", "TI-002"],
  "automation_goal": "利用者の主要checkout経路を反復確認する技術非依存の価値選定",
  "population_complete": true,
  "source_refs": [
    { "ref": "E2E-01", "revision": "e2e-r3", "currentness": "current" },
    { "ref": "REQ-CHECKOUT", "revision": "req-r4", "currentness": "current" },
    { "ref": "TI-001", "revision": "ti1-r1", "currentness": "current" },
    { "ref": "TI-002", "revision": "ti2-r1", "currentness": "current" }
  ],
  "candidates": [
    {
      "candidate_id": "E2E-CAND-001",
      "candidate_key": "checkout-primary",
      "source_refs": ["REQ-CHECKOUT", "TI-001"],
      "decision": "selected",
      "rationale": "主要checkout完了経路をUIから反復確認する価値がある"
    },
    {
      "candidate_id": "E2E-CAND-002",
      "candidate_key": "checkout-shipping",
      "source_refs": ["REQ-CHECKOUT", "TI-002"],
      "decision": "deferred",
      "rationale": "現行source上は配送条件の反復確認価値が未評価"
    }
  ],
  "history": [],
  "retired_candidates": [],
  "blockers": [],
  "current_revision_digest": "sha256:4d5f0ed37a58d7e6d001dace61ed748d9fd18f0e382efe3a8d0d2b9b7794d464"
}
```

今回のsource revision更新はTI-002だけに関係し、TI-002はrevision `ti2-r2`でcurrentです。更新により、配送再試行の業務経路が追加されました。TI-001のsource・経路は変わっていません。新しいTI-003はcurrentな`REQ-ORDER-TRACKING` revision `req-track-r1`に基づく注文追跡経路で、selectionの候補母集団へ追加します。現時点の母集団はTI-001、TI-002、TI-003で完全です。

revision 1のdigestはこの評価fixtureのrecord整合性値です。共有保存先の真正性やreadbackを証明する値として扱わないでください。今回の変更理由は「TI-002のsource revision更新とTI-003の候補追加」です。
