---
name: spec-analysis
description: Figma、要件書、Q&A、リポジトリ、リリース資料などの情報源から、SPEC・DECISION・INFERENCE・UNKNOWNを区別し、対象スコープのCurrent Effective Authorityを解決した追跡可能な仕様分析を作るSkill。テスト分析前の仕様整理、複数情報源の統合、矛盾・制約・状態・業務ルールの抽出に使用する。
---

# 仕様分析

## 実行契約

1. 実行前に `references/guidance.md` を読み、情報源の扱い、Current Effective Authority、分析手順、停止条件、品質ゲートに従います。
2. 案件固有の情報源優先順位・正式用語・対象範囲・Canonical Registryがある場合はそれを優先します。
3. 未定義の製品挙動を補完せず、`SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN` を区別します。
4. テスト要求・テスト観点・テストケースを先回りして作りません。
5. 既定出力形式が必要な場合は `assets/output-template.md` を使用します。案件固有形式がある場合は、意味上の出力契約と追跡性を維持する限りそちらを優先します。
6. 他Skillを参照するときはCanonical Skill名を使用します。

## 出力

追跡可能な仕様分析。対象範囲内の現在有効な期待挙動が情報源またはCanonical Registryへ戻れ、業務ルール、状態・遷移、フロー、制約、不明点を必要に応じて表現できる状態にします。

## リソース

- 詳細判断基準: `references/guidance.md`
- 既定出力形式: `assets/output-template.md`
