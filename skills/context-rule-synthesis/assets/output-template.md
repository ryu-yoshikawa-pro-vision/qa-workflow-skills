# Context Rule Synthesis 出力形式

依頼された分析範囲、scan completeness、候補/質問/handoffの状態、runの完了/readback状態を短く示してください。要求された操作に対応するcanonical `context-rule-candidate`または`context-synthesis-run`を、次のJSONコードブロックに一つだけ出力します。schema・identity・値の規則は`references/data-contract.md`に従います。候補の予定本文はrunの`planned_payload`へ含めます。

```json
<canonical context-rule-candidate or context-synthesis-run artifact>
```
