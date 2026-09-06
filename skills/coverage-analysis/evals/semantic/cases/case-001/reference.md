# 判定根拠
## Source of Truth
- RISK-001の失敗条件はexternal + privateの不正閲覧。
- TC-002はexternal + publicの許可確認であり、RISK-001の失敗条件を直接検証していない。
- matrix上のID接続だけではRISK-001をcoveredと判断できない。
- external + private → 閲覧不可を確認するCoverage Item/Test CaseがGap。
- 原因はTest Condition/Coverage Item段階で失敗条件が具体化されていないため、主な修正先はtest-condition-design。

## 許容される解釈
- 下流test-case-designにも追加作業が必要と指摘してよい。
