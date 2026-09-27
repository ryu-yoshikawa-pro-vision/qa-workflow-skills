# Candidate output

```json
{
  "schema_version": "1",
  "session_ref": "SES-002",
  "mode": "investigation",
  "charter": {
    "purpose": "認証状態が切れる条件を実対象で仮説検証する",
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
    "focus_refs": [],
    "timebox_or_exit_condition": "30分または管理者以外の注文詳細表示経路を確認",
    "allowed_origins": [
      "https://staging.example.test"
    ],
    "allowed_operations": [
      "navigate",
      "open_order_detail",
      "invalidate_session"
    ],
    "side_effect_scope": "session-only",
    "side_effect_action_definition": "セッションを無効化する操作",
    "side_effect_maximum": 1,
    "cleanup_plan": "認証sessionを破棄する",
    "evidence_policy": "画面上の事実とevidence refだけを保存",
    "block_conditions": [
      "session stateを安全に確認できない"
    ],
    "symptom": "有効な操作の途中でログインへ戻る理由を確認する",
    "side_effect_operations": [
      "invalidate_session"
    ]
  },
  "state": "ブロック中",
  "observations": [],
  "findings": [],
  "evidence_refs": [],
  "unresolved": [
    "許可されたtest user / session状態を取得できず、仮説検証を開始していない"
  ],
  "follow_up_refs": [],
  "cleanup": {
    "required": true,
    "status": "未確認",
    "evidence_refs": []
  },
  "residual_side_effect": [],
  "started_at": null,
  "completed_at": null
}
```
