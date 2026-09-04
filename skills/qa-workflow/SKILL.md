---
name: qa-workflow
description: 新規機能・変更機能・指定対象機能を、仕様分析からローレベルテストケース、カバレッジ分析、反証レビューまで成果物ベースでルーティングするQAオーケストレーションSkill。複数QA Skillを順番に使う依頼、開始工程判断、停止・再開・既存成果物再利用が必要なときに使用する。
---

# QA Workflow

## 実行契約

1. 実行前に `references/guidance.md` を読み、開始点、再利用、停止・再開、変更伝播、修正ルーティング、完了条件に従います。
2. 詳細なQA判断は担当Skillへ委譲し、このSkillで重複定義しません。
3. Skillを参照するときは必ずCanonical Skill名を使います。例: `test-condition-design`（テスト観点・条件設計）。番号だけの参照は使用しません。
4. フルワークフローを実行する場合は、`qa-workflow`と8個の担当QA Skillが利用可能であることを確認します。必要Skillが利用できない場合は、そのSkillが必要な範囲をBlockedとして扱います。
5. 案件固有情報を新規に整理する場合は `assets/project-context-template.md` を利用できます。既存の案件コンテキストがある場合はそちらを優先します。
6. Workflow状態を明示する必要がある場合だけ `assets/workflow-state-template.md` を使用します。

## インターフェース

- **Input**: ユーザー要求、要求する最終成果物、対象範囲、利用可能な情報源 / 既存QA成果物。案件コンテキスト、進行モード、既知のBlocked / 残存リスク / `要再検証`状態は利用可能な場合に補助入力とします。
- **Function**: 要求成果物に必要な開始Skillを決め、既存成果物の再利用可否、Skillルーティング、Blocked / 再開、上流変更の伝播、修正ルーティング、Workflow完了状態を制御します。
- **Output**: ユーザーが要求した最終QA成果物と、必要に応じてWorkflow状態、Blocked範囲、残存リスク、`要再検証`対象、再開先Skillを返します。

## 担当Skill

| Canonical Skill名 | 日本語名称 | 主な成果物 |
| --- | --- | --- |
| `spec-analysis` | 仕様分析 | 仕様分析 |
| `question-analysis` | 不明点・矛盾分析 | 不明点・矛盾分析 |
| `test-analysis` | テスト分析 | Product Risk / テスト重点 / 技法選択 |
| `test-requirement-design` | テスト要求設計 | テスト要求 |
| `test-condition-design` | テスト観点・条件設計 | テスト観点・条件 / Coverage Item |
| `test-case-design` | ローレベルテストケース設計 | ローレベルテストケース |
| `coverage-analysis` | カバレッジ分析 | カバレッジ分析 |
| `adversarial-review` | 反証レビュー | 反証レビュー |

## リソース

- 詳細判断基準: `references/guidance.md`
- 案件コンテキスト既定形: `assets/project-context-template.md`
- 任意のWorkflow状態表: `assets/workflow-state-template.md`
