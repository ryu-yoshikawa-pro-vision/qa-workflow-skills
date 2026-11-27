# Planの保存と実装契約

一般的なrepository調査、曖昧さの扱い、Planの構成は[`feature-plan Skill`](.agents/skills/feature-plan/SKILL.md)を正本とします。

## 共通設計前提

すべての新規・改修Planは[QA Skill設計・開発の共通原則](docs/reference/qa-skill-design-principles.md)に従います。目的、必要な責務、既存手段の不足、削減・維持・委譲の判断を必要範囲で記録し、過剰設計・過剰防衛を避けます。既存のPlan・レビュー・評価経路に統合し、未改修契約との変更境界、変更対象と必要な互換性・検証を対象Planで明示します。変更に伴う関連コード・Skill・文書・テスト・設定の同期と、不要になった実装・記述の除去を実装範囲に含めます（PRN-09）。

[運用改善候補（2026-11-25）](docs/reports/2026-11-25_qa-workflow-operating-improvements.md)は後続Planの検討資料です。承認済みPlanとは区別します。

## PR #22関連のQA全工程Plan

開発連動QAとQA全工程の追加責務について、Planの目的・責務・依存関係は[Planインデックス](docs/plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)で整理します。索引は実装Planではなく、本文・完了条件の正本は各Planとその詳細文書です。過去のPlan全件を置き換えるものではありません。

## 保存

- 合意済みPlanは`docs/plans/`へ保存します。
- ファイル名は`docs/plans/{yyyy-mm-dd}_{HHMMSS}_{plan_name}.md`とし、timestampはJST（`Asia/Tokyo`）を使います。
- 再利用可能なひな形には[`plan-template.md`](.agents/skills/feature-plan/assets/plan-template.md)を使います。
- 既存Planの重要な目的、scope、validation、完了条件を実装時の独自判断で変えません。根拠のある必要最小限の修正は、理由をPlanと実装結果に記録します。

## 実装と完了

- Plan-onlyではPlanだけを変更し、実装しません。
- 実装依頼ではPlanの順序に従い、検証結果を完了条件ごとに確認します。
- 独立したvalidationは個別に実行・判定します。1つのfailureを後段のsuccessで隠しません。
- 未実行、実行不能、失敗したvalidationはPASSと区別して記録し、Planが定めるblocked条件を維持します。ユーザーが特定作業のPlan変更を明示的に承認した場合は、その作業に限って改訂後の完了条件を適用し、他のPlanへ省略条件を一般化しません。
- Planの完了条件がすべて満たされた場合だけ実装完了とします。
