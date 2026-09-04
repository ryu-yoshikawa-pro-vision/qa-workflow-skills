# Coverageレビュー Probes

このreferenceはCoverage Analysisまたは残存リスクを反証レビューする場合だけ読みます。

Coverage Criteria / Itemの設計は`test-condition-design`、Coverage / Gap判定は`coverage-analysis`をSingle Source of Truthとします。

## Coverage Analysis

主に次を疑います。

- Current Effective Authority / Product RiskからTest Caseまでの各層が下流接続または妥当なDispositionへ閉じているか
- Product Riskが下流へ接続されず消えていないか
- 件数比較やIDリンクだけを意味上のCoverageとして扱っていないか
- 入力されたCoverage Criteriaに対する充足を実Evidenceで確認しているか
- 下流成果物不存在をBlockedと誤判定せずCoverage Gapとして扱っているか
- 不十分なTest CaseをCoverage済みと誤認していないか
- `要再検証`の成果物を最新のCoverage Evidenceとして数えていないか
- Gapや不正Dispositionの修正先が最も早い責任Skillになっているか
- Coverage Analysis自身が上流成果物を再設計していないか

## 残存リスク

主に次を疑います。

- 対象内の未カバー内容が明示されているか
- 理由と関連Product Riskが追跡できるか
- 高Product Riskの未カバーが無処置で見逃されていないか
- 重大な未カバーを受容済みとする場合、必要な明示承認 / 承認参照があるか
- `対象外`や`Blocked`を便宜的に使って残存リスクを隠していないか

重大度や残存リスク受容の処置条件は`adversarial-review`基本ガイダンスを正本とします。
