---
name: test-condition-design
description: テスト要求を、どの条件・観点で検証するかへ展開し、同値分割、境界値分析、デシジョンテーブル、状態遷移、Pairwise、エラー推測、シナリオなどのCoverage CriteriaとCoverage Itemを定義するSkill。テストケース設計前に必要カバレッジを具体化するときに使用する。
---

# テスト観点・条件設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、技法選択、Coverage Criteria / Coverage Item、組合せ抑制、停止条件、品質ゲートに従います。
2. 技法を適用したという事実だけでカバレッジ済みと判断せず、「何をカバーすれば十分か」を明示します。
3. 1観点を満たすために複数の具体値・同値クラス・ルール・状態・遷移・組合せが必要な場合、または項目単位の追跡が必要な場合はCoverage Itemを独立表示します。観点自体が1つの具体条件を一意に表す場合だけ内包できます。
4. 期待挙動をProduct Riskやテスト仮説から創作しません。
5. 実行手順は `test-case-design`（ローレベルテストケース設計）に委ねます。
6. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
7. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

テスト観点・条件、適用技法、Coverage Criteria、必要なCoverage Item、関連要求・仕様・Product Risk、優先度、除外 / 統合根拠を作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
