# 判定根拠
## Source of Truth
- role×visibilityは認可判定の主要因であり組合せ確認が必要。
- external+private拒否とpublic許可はセキュリティ境界として個別に明示確認する価値が高い。
- deviceはこのTRの認可意味には影響せず、全組合せへ混ぜると冗長になり得る。
- Pairwiseを使う場合でも、高リスク境界をPairwiseだけに任せず明示Coverage Itemを持つ判断が適切。

## 禁止される推測
- Pairwiseの数学的pair数自体を意味評価しない。
