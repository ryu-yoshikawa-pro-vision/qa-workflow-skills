---
name: adversarial-review
description: 仕様分析、不明点・仮定、テスト分析、テスト要求、テスト観点・条件、Coverage Item、ローレベルテストケース、カバレッジ分析を反証的にレビューし、誤り・抜け・過剰・根拠のない期待結果・追跡性欠陥を検出するSkill。成果物の最終品質確認や重大欠陥の洗い出しに使用する。
---

# 反証レビュー

## 実行契約

1. 成果物を肯定するためではなく、誤り・抜け・過剰・根拠不足・追跡性欠陥を見つけるためにCold Reviewします。
2. 生成時の説明や意図を正当化根拠にせず、利用可能な上流根拠と成果物から判断します。
3. 重大度、処置、修正routing、レビュー制約の基本は`references/guidance.md`に従います。
4. 仕様分析 / 不明点をレビューする場合だけ`references/authority-question-probes.md`を追加で読みます。
5. Product Risk / Test Requirement / Test Condition / Coverage Item / Test Caseをレビューする場合だけ`references/test-design-probes.md`を追加で読みます。
6. Coverage Analysis / 残存リスクをレビューする場合だけ`references/coverage-probes.md`を追加で読みます。
7. 工程固有の詳細Domain Logicは担当SkillをSingle Source of Truthとし、本Skillへ別正本として複製しません。
8. 修正が必要でも本Skill自身が他層成果物を再設計せず、`qa-workflow`を介して最も早い責任Skillへ戻します。
9. 既定出力形式が必要な場合は`assets/output-template.md`を使用します。
10. 最終出力前に、本Skill自身のInput / Output Contract・停止条件・品質ゲートをレビュー結果へ適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としない契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。最終確認で問題が残る場合は2回目の自動修正を行わず、既存の停止条件・Blocked・routingに従います。Self-Validationは自身の出力契約確認に限定し、レビュー結果自体へ新たな意味評価を重ねません。

## インターフェース

- **Input**: レビュー対象QA成果物。Current Effective Authority、Product Risk、Coverage Criteria、Canonical Registry、案件コンテキスト、前後成果物等は判定対象に応じた根拠入力とします。
- **Function**: 生成時の意図を引き継がずCold Reviewし、判定可能な範囲で誤り・抜け・過剰・根拠不足・追跡性欠陥を重大度付きで検出して責任Skillへ戻します。
- **Output**: 重大度、対象、問題、根拠、影響、推奨修正先、処置状態を持つ反証レビュー結果。判定に必要な根拠がない観点はレビュー制約 / 判定不能として明示します。

## 基本原則

- 必要根拠が不足する観点だけを判定不能とし、判定可能な他範囲は継続する
- 好みを欠陥として報告しない
- 一般的チェックリストを根拠なく機械適用しない
- 工程固有ルールの詳細正誤は担当Skillの契約を基準とする

## リソース

- 重大度 / 処置 / routing / 品質ゲート: `references/guidance.md`
- 仕様分析 / 不明点プローブ: `references/authority-question-probes.md`
- テスト設計成果物プローブ: `references/test-design-probes.md`
- Coverage Analysis / 残存リスクプローブ: `references/coverage-probes.md`
- 既定出力形式: `assets/output-template.md`
