# 判定根拠
## Source of Truth
- TC-101 / TC-102とE2E path + title pathは、QA ID graphとは別の実装追跡参照として扱う。
- 実装参照から`resolved primary TestCase`または`result-1`と結果へ辿れることを確認する。
- 未実行の`order detail`は、実行済みと誤認せず未実行理由を保持する。

## 禁止される推測
- E2E path / title pathを既存QA IDの代替IDとして登録しない。
- 未実行の結果、locator、原因を推測しない。
