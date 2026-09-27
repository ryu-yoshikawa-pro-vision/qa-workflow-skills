# QA引継ぎ

## 現在の事象

- manual TC-401の結果は `FAIL`。観測証拠では期待結果の仕様authorityが不明です。
- TC-401はcurrentかつ有効です。原因や結果の再判定はせず、提示されたFAILと証拠を維持します。証拠の詳細・参照先は入力にないため、リンクは未解決です。
- **FAIL / FindingだけではDefectへ自動登録しない**でください。

## 原因調査のルート

1. `question-analysis`で、観測証拠に照らして期待結果の不足条件を確認します。
2. 既存仕様の解釈やauthorityの確定が必要なら、`spec-analysis`へ引き継ぎます。

## 修正後の確認

修正後は、同じcurrent TC-401を`test-execution`で再実行して修正確認します。専用のfix-confirmation Skillや独自状態は作りません。修正確認の実行結果は未提示です。

## 別Runの周辺Regression

周辺Regressionは修正確認とは別目的のRunとして`regression-testing`で選定します。現時点では、current TC一覧、完全なdiscovery、baseline、関連RiskとTCのtraceabilityが入力にないため、対象TC・Run scope・残る未検証影響は未解決です。対象を推測して選定・実行済みとは扱いません。選定後、実行前に各TCのrequired routeを確定します。
