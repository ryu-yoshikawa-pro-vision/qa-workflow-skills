# Context Signal Audit 出力形式

source、requested range、actual inspected range、scan completenessを短く示し、完了/readbackを未確認のときはその状態を明示してください。正規保存用のcanonical `context-signal-batch`を、次のJSONコードブロックに一つだけ出力します。schema・identity・値の規則は`references/data-contract.md`に従います。

```json
<canonical context-signal-batch artifact>
```
