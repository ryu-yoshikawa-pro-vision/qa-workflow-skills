# Exploratory Session output

正規SessionはMarkdown内にJSON code blockをちょうど1つ置きます。`assets/session-template.json`を基礎に、mode、Charter、Observation / Finding、evidence、follow-up、cleanupを記録します。`side_effect_operations: []`は許可した副作用操作がないことを明示します。Observationは実測事実、Findingはfollow-up対象として分け、cleanup未確認を安全完了にしません。

```json
{
  "schema_version": "1",
  "session_ref": "",
  "mode": "exploration | investigation",
  "charter": {},
  "state": "未開始 | 実行中 | 部分完了（ブロック中あり） | ブロック中 | 完了",
  "observations": [],
  "findings": [],
  "evidence_refs": [],
  "unresolved": [],
  "follow_up_refs": [],
  "cleanup": {"required": false, "status": "対象なし", "evidence_refs": []},
  "residual_side_effect": []
}
```
