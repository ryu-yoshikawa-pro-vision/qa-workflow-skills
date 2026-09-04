---
name: test-condition-design
description: Test Requirementを、どの条件・観点で検証するかへ展開し、同値分割、境界値分析、デシジョンテーブル、状態遷移、Pairwise、エラー推測、シナリオなどのCoverage CriteriaとCoverage Itemを定義するSkill。候補母集団とDispositionを管理し、テストケース設計前に必要Coverageを具体化するときに使用する。
---

# テスト観点・条件設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、Test Requirementの閉鎖、技法選択、Coverage Criteria / Coverage Item、Disposition、停止条件、品質ゲートに従います。
2. 技法を適用したという事実だけでカバレッジ済みと判断せず、「何をカバーすれば十分か」を明示します。
3. 複数候補を持つ場合は候補母集団を先に識別し、採用しない候補も明示Dispositionへ位置づけます。
4. 期待挙動をProduct Riskやテスト仮説から創作しません。
5. 実行手順は `test-case-design`（ローレベルテストケース設計）に委ねます。
6. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
7. 他Skillを参照するときはCanonical Skill名を使用します。

## インターフェース

- **Input**: 何を検証するかが明確なTest Requirementまたは同等の成果物。Current Effective Authority、Product Risk、状態モデル / 業務ルール等は利用可能な場合に補助入力とします。
- **Function**: Test Requirementを検証条件へ展開し、問題構造に合う技法、Coverage Criteria、Coverage Item、採用しない候補のDispositionを定義します。
- **Output**: Test Condition、適用技法、Coverage Criteria、必要なCoverage Item、関連Test Requirement / Authority / Product Risk、優先度、Test RequirementとCoverage候補のDispositionを作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
