---
name: test-requirement-design
description: 仕様分析とテスト分析から、何を検証・保証すべきかというテスト要求を定義するSkill。仕様・決定・承認済み仮定への追跡性を保ち、テスト観点や実行手順へ先回りせず検証責務を整理するときに使用する。
---

# テスト要求設計

## 実行契約

1. 実行前に `references/guidance.md` を読み、要求の抽象度、分割・統合、追跡性、Oracle Authority、停止条件、品質ゲートに従います。
2. テスト要求は「何を検証するか」に留め、具体条件、組合せ、実行手順を書きません。
3. 期待挙動の根拠は原則 `SPEC` / `DECISION` / `承認済み ASM` とします。Product Risk、実装、既存テスト、未承認INFERENCEだけで製品挙動を確定しません。
4. 重要な現在レベル外要件は、別テストレベルまたは残存リスクとして失わず保持します。
5. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。
6. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

安定したID、検証責務、上流根拠、関連Product Risk、優先度、テストレベル / 観測方法を持つテスト要求を作ります。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
