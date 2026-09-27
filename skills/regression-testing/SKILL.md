---
name: regression-testing
description: 既存のcurrent QA成果物を継続Regressionへ接続し、baseline、membership、今回のRun選定、Activity、履歴を管理する。Product Risk分析、TC設計、テスト実行そのものには使用しない。
---

# Regression Testing

既存のcurrent logical TCからRegression Suiteを構成し、Run scopeと実行後Activityを管理します。要求がbaseline / membership / Run計画 / 履歴だけなら単独で開始できます。manual / E2E実行を含む場合は`qa-workflow`が本Skillと既存execution Skillを接続します。

## 実行契約

1. 先に`references/guidance.md`を読み、current QA source、discovery completeness、membership、Run、Activityの契約に従います。
2. PR #11のMachine Entity identity / fingerprint / dependency / lifecycle / freshnessと、PR #12 / E2Eのexecution start / resultを正本として使います。独自ID、freshness、execution taxonomyを作りません。
3. current TCの完全な一覧はauthoritative rootの完全列挙結果とownerが解決したcurrent TC inputsから作ります。入力欠落、truncated listing、lifecycle unresolvedは`complete=false`として区別します。決定論的production helperの失敗をLLMで代替しません。
4. Membershipの意味判断、Run scope、残存Riskとの関係は本Skillで行います。既存Riskごとに関係するTCの選択・除外・未実行と、そのRunで残る未検証影響を明記します。除外をRiskの検証済み根拠にせず、TCとRiskのtraceabilityが不足する場合は推測せず未解決にします。Product Riskを新規採点せず、変更影響候補は`test-analysis`へ戻します。
5. full Runはcompleteかつcurrentなbaselineでだけ宣言します。selected RunはSuite全体の完了に数えません。candidate queryが不完全ならscopeを候補だけで狭めません。
6. scope selection、required routeの確定、execution startを別段階として記録します。selection-only要求はroute未解決でもscope判断を完了でき、execution readinessだけを未解決として残します。実行を要求された場合はselected TCごとのrequired routeを開始前に固定します。actual startはsource execution contractで確認し、全routeの開始後だけlogical TCをexecutedとして数えます。source resultは再判定せずActivityへ投影します。
7. Activity / Suiteの保存にatomic conditional writeが必要な場合、保存先が提供するnative conditionを確認します。read-compare-unconditional-writeをCASと呼びません。条件付き保存ができない操作は`blocked`にします。
8. TCなしE2Eはuserまたはproject policyの明示時だけ補助testwareとして含め、TC count / TC coverageと分離します。
9. FAIL / Findingのfeedbackでは、source結果とevidenceを保ち、原因判断をowner Skillへ戻します。ユーザー向けfeedbackに「FAIL / FindingだけではDefectへ自動登録しない」と明記し、修正確認と、要求された場合の別目的Regressionを分けます。

## 正規対象

- `baseline / membership`
- `Run計画`
- `Run結果更新`
- `履歴参照`

## リソース

- 手順・責務境界・停止条件: `references/guidance.md`
- baselineとActivityのmachine input: `references/data-contract.md`
- 正規出力形: `assets/output-template.md`
- production helper: `scripts/regression_runtime.py`
- deterministic contract: `evals/deterministic/validator.py`
