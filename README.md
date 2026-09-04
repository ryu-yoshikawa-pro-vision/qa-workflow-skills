# QAテスト分析・設計 Agent Skills

新規機能・変更機能・指定対象機能を分析し、**テスト実施者が迷わず実行できるローレベルテストケースまで落とし込む**ためのAgent Skills群です。

## 目的

対象機能について、次の状態を作ります。

- 製品の期待挙動を権威ある情報源へ追跡できる
- 不明点・矛盾・仮定を仕様と混同しない
- Product Riskに応じてテスト重点・深度を決める
- 適切なテスト技法とCoverage Criteriaから必要なCoverage Itemを識別する
- テストケース単体で、開始状態・準備・操作・入力・合格条件を判断できる
- `Source → Specification → Test Requirement → Test Condition → Coverage Item → Test Case` を追跡できる
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

テンプレートには判断ロジックを置きません。案件固有のExcel、Spreadsheet、文書形式がある場合は、Skillの意味上の出力契約と必要な追跡性を維持できる限り案件固有形式を優先できます。

## Skill参照規則

Skillは必ずYAML frontmatterの`name`と同じCanonical Skill名で参照します。

例:

- `spec-analysis`（仕様分析）
- `test-condition-design`（テスト観点・条件設計）
- `test-case-design`（ローレベルテストケース設計）

`Skill 05`、`スキル06`のような順番だけの呼称は使用しません。順序はWorkflowが表現し、Skill識別子には含めません。

## Skill一覧

| Canonical Skill名 | 日本語名称 | 主な問い | 主な成果物 |
| --- | --- | --- | --- |
| `spec-analysis` | 仕様分析 | 製品はどう動くべきか？ | 仕様分析 |
| `question-analysis` | 不明点・矛盾分析 | 分からないことのうち、どれが設計を止めるか？ | 不明点・矛盾分析 |
| `test-analysis` | テスト分析 | どこが壊れると困り、どこを厚く確認すべきか？ | Product Risk / テスト重点 |
| `test-requirement-design` | テスト要求設計 | 何を保証する必要があるか？ | テスト要求 |
| `test-condition-design` | テスト観点・条件設計 | どんな条件をカバーすれば十分か？ | テスト観点・条件 / Coverage Item |
| `test-case-design` | ローレベルテストケース設計 | 実際に何をして、何が起きれば合格か？ | ローレベルテストケース |
| `coverage-analysis` | カバレッジ分析 | 必要なものがケースまで落ちているか？ | カバレッジ分析 |
| `adversarial-review` | 反証レビュー | 誤り・抜け・過剰がないか？ | 反証レビュー |
| `qa-workflow` | QA Workflow | どのSkillをどの順で使うか？ | ルーティング / 完了判断 |

## 既定フロー

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

必要な有効成果物が既に存在する場合は、最も近い必要Skillから開始します。

## 基本原則

### 情報源への忠実性

- `SPEC`: 権威ある情報源に明記された仕様
- `DECISION`: 正式に確定した決定
- `INFERENCE`: 根拠はあるが未確定の推論
- `UNKNOWN`: 根拠不足で確定できない事項

`INFERENCE`や`UNKNOWN`を暗黙に仕様へ昇格させません。

### Oracle Authority

完成済みテストケースの期待結果は原則として次へ追跡します。

1. `SPEC`
2. `DECISION`
3. `承認済み ASM`

Product Risk、実装、既存テスト、一般的慣習、未承認の推論は単独でOracle Authorityにしません。

### Product Risk

テスト深度・優先度の判断にはProduct Riskを使います。人員、納期、予算、環境準備などのProject Riskはリスクスコアへ混ぜません。

### テストレベル

指定がなく、依頼が別レベルを明示していない場合はシステムテストを既定とします。

### ローレベルテストケース

重要ケースはケース単体から次を判断できる具体度にします。

1. 誰が / どの状態で開始するか
2. 何を準備するか
3. 何を操作するか
4. 何を入力・選択するか
5. 何が起きれば合格か

### Coverage Criteria / Coverage Item

技法名を書いただけでカバレッジ済みとは判断しません。何をカバーすれば十分かを定義し、必要な具体要素をCoverage Itemとして追跡します。

### Blocker

不明点は影響する成果物に応じて`Blocker` / `要確認` / `仮定可能` / `提案・任意`に分類します。Blockerは可能な限り影響範囲だけを停止します。

## 標準との関係

Agent Skillsの公開仕様に合わせ、各Skillを`SKILL.md`を持つ独立ディレクトリとして構成しています。

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このワークフローの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
