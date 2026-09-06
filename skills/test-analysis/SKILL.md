---
name: test-analysis
description: 新規機能・変更機能・指定対象機能について、変更影響、Product Risk、テスト重点、テストレベル、観測方法、適用テスト技法を決めるSkill。何をなぜどの深さでテストするかを整理し、Test Requirement設計の入力を作るときに使用する。
---

# テスト分析

## 実行契約

1. 実行前に `references/guidance.md` を読み、Product Risk評価、テスト可能性、技法選択、停止条件、品質ゲートに従います。
2. 本Skillで扱うリスクはProduct Riskに限定し、Project Riskをリスク評価へ混ぜません。
3. テストレベルがユーザー、案件コンテキスト、既存有効成果物で指定されず、依頼が別レベルを明確に要求しない場合はシステムテストを既定とします。
4. リスクレベルはラベルで終わらせず、詳細ガイダンスに定義された高・中・低の設計深度へ接続します。
5. 技法は問題構造に合う場合だけ選び、具体的Coverage Criteria / Coverage Itemは `test-condition-design`（テスト観点・条件設計）に委ねます。
6. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
7. 他Skillを参照するときはCanonical Skill名を使用します。
8. 最終出力前に、本Skill自身のInput / Output Contract・停止条件・品質ゲートを対象成果物へ適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。最終確認で問題が残る場合は2回目の自動修正を行わず、Product Riskや未解決Oracleを再解釈・創作せず既存の停止条件・Blocked・routingに従います。

## インターフェース

- **Input**: 対象挙動と要求範囲を理解できるCurrent Effective Authorityまたは同等の仕様情報。変更情報、既存テスト / 不具合、案件コンテキスト等は利用可能な場合に補助入力とします。
- **Function**: 対象のProduct Riskを評価し、何をなぜどの深さでテストするか、テストレベル、観測方法、テスト重点、適用技法を決めます。
- **Output**: 変更・影響、Product Risk、テスト重点、テストレベル / 観測方法、最小限のテスト可能性、選択技法、対象外・残存リスクを説明できるテスト分析を作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
