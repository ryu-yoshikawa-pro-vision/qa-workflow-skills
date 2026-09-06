---
name: qa-workflow
description: 新規機能・変更機能・指定対象機能を、仕様分析からローレベルテストケース、カバレッジ分析、反証レビューまで成果物ベースでルーティングするQAオーケストレーションSkill。複数QA Skillを順番に使う依頼、開始工程判断、停止・再開・既存成果物再利用が必要なときに使用する。
---

# QA Workflow

## 実行契約

1. 本SkillはOrchestrationだけを所有し、工程固有のDomain Logicを再定義しません。
2. ユーザー要求、要求成果物、対象範囲から最も早い開始Skillを判断し、有効な既存成果物があれば再利用します。
3. 必要Skillが利用できない、または担当Skillの必須入力が不足する場合は、そのSkillが必要な範囲だけをBlockedとして扱います。
4. 上流成果物の意味が変わった場合は、影響する下流だけを`要再検証`へ戻します。
5. Skillを参照するときはCanonical Skill名を使い、番号だけの参照は使用しません。
6. 開始点、再利用、Blocked / 再開、変更伝播、修正routing、Workflow完了判定の詳細が必要な場合は`references/guidance.md`を読みます。
7. 案件固有情報を新規整理する場合は必要に応じて`assets/project-context-template.md`を利用できます。
8. Workflow状態を明示する必要がある場合だけ`assets/workflow-state-template.md`を使用します。
9. 最終出力前に、実際に利用した入力が本SkillのInput Contractを満たし、停止条件に該当する未解決状態がないか確認します。あわせて、生成したOrchestration成果物へ本Skill自身のOutput Contract・品質ゲートを適用して自己検証します。明白かつ局所的で新しいDomain判断を必要としないOrchestration契約違反だけを最大1回修正し、修正後は修正箇所を含めて最終確認します。Authority不足、上流判断不足、他SkillのDomain Logicが必要な問題は推測補完せず既存の停止条件・Blocked・routingに従います。最終確認後も本Skill自身のOrchestration契約違反が残り、既存の停止条件・Blocked・routingに該当しない場合は2回目の自動修正を行わず、その成果物を契約適合済み・完成済みとして扱わず、現在残る契約上の制約だけを明示します。自己検証でも他SkillのDomain Logicを再判定・再設計せず、Self-Validationの経緯や修正回数は出力しません。

## インターフェース

- **Input**: ユーザー要求、要求する最終成果物、識別可能な対象範囲。情報源、既存QA成果物、案件コンテキスト、進行モード、既知のBlocked / 残存リスク / `要再検証`状態は利用可能な場合に補助入力とします。
- **Function**: 要求成果物に必要な開始Skillを決め、既存成果物の再利用可否、Skill routing、Blocked / 再開、上流変更の伝播、修正routing、Workflow完了状態を制御します。
- **Output**: ユーザーが要求した最終QA成果物と、必要に応じてWorkflow状態、Blocked範囲、残存リスク、`要再検証`対象、再開先Skillを返します。

## Domain Logicの担当

| Domain Logic | 担当Skill |
| --- | --- |
| Current Effective Authority | `spec-analysis` |
| 不明点・矛盾 / Assumption | `question-analysis` |
| Product Risk / テスト重点 | `test-analysis` |
| Test Requirement | `test-requirement-design` |
| Test Condition / Coverage Criteria / Item | `test-condition-design` |
| Low-Level Test Case / Oracle具体化 | `test-case-design` |
| Coverage / Gap | `coverage-analysis` |
| Cold Review / 重大度 | `adversarial-review` |

## Runtime前提

本Skillは、同一Agent client上で9 Skillすべてが利用可能で、Agentが必要なSkillを追加ロード / 利用できる環境を前提とします。これはAgent Skills Specificationが共通Skill-to-Skill APIを保証しているという意味ではありません。

## リソース

- Orchestration詳細: `references/guidance.md`
- 案件コンテキスト既定形: `assets/project-context-template.md`
- 任意のWorkflow状態表: `assets/workflow-state-template.md`
