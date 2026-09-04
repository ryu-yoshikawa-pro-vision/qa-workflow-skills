---
name: test-requirement-design
description: Current Effective Authorityとテスト分析から、何を検証・保証すべきかというTest Requirementを定義するSkill。上流Authority・Product Riskへの追跡性を保ち、テスト観点や実行手順へ先回りせず検証責務を整理するときに使用する。
---

# テスト要求設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、要求の抽象度、上流項目の閉鎖、分割・統合、追跡性、Oracle Authority、停止条件、品質ゲートに従います。
2. Test Requirementは「何を検証するか」に留め、具体条件、組合せ、実行手順を書きません。
3. 期待挙動はCurrent Effective Authorityへ追跡し、Product Risk、実装、既存テスト、未承認INFERENCEだけで製品挙動を確定しません。
4. 対象範囲内のCurrent Effective Authority / Product Riskを、Test Requirementまたは明示Dispositionへ閉じます。
5. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
6. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

安定したID、検証責務、Current Effective Authority、関連Product Risk、優先度、テストレベル / 観測方法を持つTest Requirementと、Test Requirementを作らない上流項目のDispositionを作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
