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
8. 最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成した成果物へ本Skill自身のOutput Contract・品質ゲートを適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。Product RiskのImpact / Likelihood等のRisk評価入力を新しい根拠・推測・再解釈で再採点しません。ただし、確定済みのRisk評価入力と既存Risk Matrixまたは採用済みの案件固有Risk評価方式から機械的に一意に導出できるRisk Level等の明白な整合性違反は、局所修正対象にできます。案件固有Risk評価方式自体をSelf-Validation中に新規設計・独自解釈・推測したり、採用されていない方式へ切り替えたりしません。Authority不足、上流判断不足、他SkillのDomain Logicが必要な問題は推測補完せず既存の停止条件・Blocked・routingに従います。最終確認後も本Skill自身の契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。Self-Validationの経緯や修正回数は出力しません。

## インターフェース

- **Input**: 対象挙動と要求範囲を理解できるCurrent Effective Authorityまたは同等の仕様情報。変更情報、既存テスト / 不具合、案件コンテキスト等は利用可能な場合に補助入力とします。
- **Function**: 対象のProduct Riskを評価し、何をなぜどの深さでテストするか、テストレベル、観測方法、テスト重点、適用技法を決めます。
- **Output**: 変更・影響、Product Risk、テスト重点、テストレベル / 観測方法、最小限のテスト可能性、選択技法、対象外・残存リスクを説明できるテスト分析を作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
