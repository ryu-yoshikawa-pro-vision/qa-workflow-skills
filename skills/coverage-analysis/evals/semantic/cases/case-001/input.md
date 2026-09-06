# Eval Input
## Product Risk
RISK-001: externalユーザーがprivate会話を閲覧できると機密情報が露出する。

## Test Requirement
TR-001: roleとvisibilityに応じた閲覧可否を保証する。

## Test Conditions / Cases
- TCN-001: ownerがprivate会話を閲覧できる。
  - TC-001: owner + private → 閲覧可能を確認。
- TCN-002: externalの公開会話閲覧。
  - TC-002: external + public → 閲覧可能を確認。
- Coverage matrix上はRISK-001 → TR-001 → TCN-002 → TC-002が接続済みと記載されている。

## 目的
ID接続だけでなく意味的CoverageとGapを分析する。
