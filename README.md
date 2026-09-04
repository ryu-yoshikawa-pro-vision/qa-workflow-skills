# QAテスト分析・設計 Agent Skills

新規機能・変更機能・指定対象機能を分析し、**テスト実施者が迷わず実行できるローレベルテストケースまで落とし込む**ためのAgent Skills群です。

## 目的

対象機能について、次の状態を作ります。

- 製品の期待挙動を権威ある情報源へ追跡できる
- 不明点・矛盾・仮定を仕様と混同しない
- Product Riskに応じてテスト重点・深度を決める
- 適切なテスト技法とCoverage Criteriaから必要なCoverage Itemを識別する
- テストケース単体で、開始状態・準備・操作・入力・合格条件を判断できる
- `Source / Decision / Approved Assumption → Test Requirement → Test Condition → Coverage Item → Test Case`を追跡できる
- カバレッジ分析と反証レビューで抜け・過剰・根拠のないOracleを検出する

毎回繰り返す回帰テストスイートの選定・保守・実行管理は主対象ではありません。

## 構造

```text
skills/
├── qa-workflow/
│   ├── SKILL.md
│   ├── references/guidance.md
│   └── assets/
│       ├── project-context-template.md
│       └── workflow-state-template.md
├── spec-analysis/
│   ├── SKILL.md
│   ├── references/guidance.md
│   └── assets/output-template.md
├── question-analysis/
├── test-analysis/
├── test-requirement-design/
├── test-condition-design/
├── test-case-design/
├── coverage-analysis/
└── adversarial-review/
```

各QA Skillは同じ責務分離を持ちます。

- `SKILL.md`: Skillの発見、使用条件、実行契約、出力責務
- `references/guidance.md`: 詳細な判断基準、手順、停止条件、品質ゲート
- `assets/output-template.md`: 既定の出力形式

テンプレートには判断ロジックを置きません。案件固有形式がある場合は、Skillの意味上の出力契約と必要な追跡性を維持できる限り案件固有形式を優先できます。

## Skill参照規則

SkillはYAML frontmatterの`name`と同じCanonical Skill名で参照します。順番だけの呼称は使用しません。

| Canonical Skill名 | 日本語名称 | 主な成果物 |
| --- | --- | --- |
| `spec-analysis` | 仕様分析 | 仕様分析 |
| `question-analysis` | 不明点・矛盾分析 | 不明点・矛盾 / 仮定候補 |
| `test-analysis` | テスト分析 | Product Risk / テスト重点 |
| `test-requirement-design` | テスト要求設計 | Test Requirement |
| `test-condition-design` | テスト観点・条件設計 | Test Condition / Coverage Item |
| `test-case-design` | ローレベルテストケース設計 | Test Case |
| `coverage-analysis` | カバレッジ分析 | Coverage Analysis |
| `adversarial-review` | 反証レビュー | Adversarial Review |
| `qa-workflow` | QA Workflow | ルーティング / 完了判断 |

## フルワークフロー

```text
spec-analysis
  ↓
question-analysis
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis
  ↓
adversarial-review
```

フルワークフローを使う場合は、`qa-workflow`と8個のQA Skillが利用可能であることを前提とします。有効な既存成果物がある場合は最も近い必要Skillから開始します。

## 基本原則

### 情報源とID

- `SPEC-xxx`: 権威ある情報源に明記された仕様
- `DEC-xxx`: 正式に確定した決定
- `INF-xxx`: 根拠はあるが未確定の推論
- `UNK-xxx`: 根拠不足で確定できない事項
- `ASM-xxx`: 明示的な仮定

`DEC-xxx`と`ASM-xxx`はProject Contextまたは案件で明示された同等のCanonical Registryへ一意に記録します。

### Oracle Authority

完成済みTest Caseの期待結果は原則として次へ追跡します。

1. `SPEC`
2. `DECISION`
3. `承認済み ASM`

Product Risk、実装、既存テスト、一般的慣習、未承認推論は単独でOracle Authorityにしません。複数の重要期待結果がある場合は、期待結果ごとにOracle Authorityを対応付けます。

### Assumption

分析・ドラフトでは明示的仮定で継続できる場合がありますが、完成済みTest CaseのPASS / FAILが未承認Assumptionに依存する範囲はBlockerです。

### Product Risk

テスト深度・優先度の判断にはProduct Riskを使います。Project Riskはリスク評価へ混ぜません。

案件固有方式がない場合は4×4のRisk Matrixを使用し、重大Impactが単純な積算によってLowへ落ちないようにします。

### Coverage Criteria / Coverage Item

複数候補を持つ技法では、**候補母集団 → Coverage Criteria → Coverage Item → 除外 / 削減候補のDisposition**の順に設計します。

技法名を書いただけでCoverage済みとは判断しません。

### ローレベルTest Case

重要ケースはケース単体から次を判断できる具体度にします。

1. 誰が / どの状態で開始するか
2. 何を準備するか
3. 何を操作するか
4. 何を入力・選択するか
5. 何が起きればPASSか

### 優先度

下流成果物は関連上流成果物の最も高い優先度を既定で引き継ぎます。優先度を下げる場合は理由を明示します。

### Blocker

不明点は影響成果物に応じて`Blocker` / `要確認` / `仮定可能` / `提案・任意`へ分類し、Blockerは可能な限り影響範囲だけを停止します。

### 上流修正

上流成果物の意味を変更した場合は、影響する下流成果物だけを再検証します。無関係な成果物を全再生成しません。

## 標準との関係

Agent Skillsの公開仕様に合わせ、各Skillを`SKILL.md`を持つ独立ディレクトリとして構成しています。

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このワークフローの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
