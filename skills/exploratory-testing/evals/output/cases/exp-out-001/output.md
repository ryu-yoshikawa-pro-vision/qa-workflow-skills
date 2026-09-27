# Candidate output

```json
{
  "schema_version": "1",
  "session_ref": "SES-001",
  "mode": "exploration",
  "charter": {
    "purpose": "注文履歴から取消済み注文の表示と権限境界を探索する",
    "in_scope": [
      "注文履歴の閲覧"
    ],
    "out_of_scope": [
      "注文確定",
      "決済"
    ],
    "source_refs": [
      "change:CHG-014"
    ],
    "focus_refs": [
      "risk:RISK-014"
    ],
    "timebox_or_exit_condition": "30分または管理者以外の注文詳細表示経路を確認",
    "allowed_origins": [
      "https://staging.example.test"
    ],
    "allowed_operations": [
      "navigate",
      "open_order_detail"
    ],
    "side_effect_scope": "read-only",
    "side_effect_action_definition": "注文・顧客状態を書き換える操作",
    "side_effect_maximum": 0,
    "cleanup_plan": "read-only。作成データなし",
    "evidence_policy": "画面上の事実とevidence refだけを保存",
    "block_conditions": [
      "許可origin外",
      "権限境界を変更する操作"
    ],
    "side_effect_operations": []
  },
  "state": "完了",
  "observations": [
    {
      "observation_ref": "OBS-001",
      "action_or_observation": "閲覧者roleで注文詳細を開く",
      "observed_fact": "取消済みの注文詳細が表示された",
      "evidence_refs": [
        "ev:screen-1"
      ]
    }
  ],
  "findings": [],
  "evidence_refs": [
    "ev:screen-1"
  ],
  "unresolved": [],
  "follow_up_refs": [],
  "cleanup": {
    "required": false,
    "status": "対象なし",
    "evidence_refs": []
  },
  "residual_side_effect": [],
  "started_at": "2026-09-27T00:00:00Z",
  "completed_at": "2026-09-27T00:30:00Z"
}
```
