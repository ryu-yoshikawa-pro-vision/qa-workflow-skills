# 判定根拠
## Source of Truth
- E2Eコードの対象・期待挙動がAuthorityの注文履歴 / 詳細表示と意味的に整合するかを確認する。
- TCがないこと自体を理由にTC IDを創作したり、E2Eコードだけを仕様根拠にして正当化したりしない。
- 「トーストがない」「API statusがない」等はAuthority根拠がなくFalse Positive。
- 欠陥が提示情報から確認できない場合、無理にFindingを作らない。

## 許容される解釈
- 実装参照のpath + title pathが追跡可能であることを確認してよいが、QA ID graphへ混ぜない。
