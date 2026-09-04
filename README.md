# QAテスト分析・設計 Agent Skills

新規機能・変更機能・指定対象機能を分析し、**テスト実施者が迷わず実行できるローレベルテストケースまで落とし込む**ためのAgent Skills群です。

## 目的

対象機能について、次の状態を作ります。

- 現在有効な製品の期待挙動を権威ある情報源・正式決定へ追跡できる
- 不明点・矛盾・仮定を仕様と混同しない
- Product Riskに応じてテスト重点・深度を決める
- 適切なテスト技法とCoverage Criteriaから必要なCoverage Itemを識別する
- 対象内の上流項目を無言で落とさず、下流成果物または明示Dispositionへ閉じる
- すべてのTest Caseを、ケース単体で開始状態・準備・操作・入力・PASS条件を判断できる粒度にする
- `Current Effective Authority / Product Risk → Test Requirement → Test Condition → Coverage Item → Test Case` を追跡できる
- Coverage Analysisと反証レビューで抜け・過剰・不正Disposition・根拠のないOracleを検出する

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

案件固有形式がある場合は、Skillの意味上の出力契約と必要な追跡性を維持できる限り案件固有形式を優先できます。

## Skill参照規則

SkillはYAML frontmatterの`name`と同じCanonical Skill名で参照します。順番だけの呼称は使用しません。

| Canonical Skill名 | 日本語名称 | 主な成果物 |
| --- | --- | --- |
| `spec-analysis` | 仕様分析 | 仕様分析 / Current Effective Authority |
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

### Current Effective Authority

期待挙動は固定順位で決めず、対象スコープで現在有効なAuthorityを解決します。

- 有効な`DECISION`が旧仕様・旧Decisionを上書きする場合はそのスコープでDecisionを採用
- それ以外は情報源優先順位・鮮度に従って現在有効な`SPEC`を採用
- `承認済み ASM`は有効な`SPEC` / `DECISION`で未定義の隙間だけを暫定的に補完
- 解決不能なAuthority競合はBlocker

### ID / Canonical Registry

- `SPEC-xxx`: 権威ある情報源に明記された仕様
- `DEC-xxx`: 正式に確定した決定
- `INF-xxx`: 根拠はあるが未確定の推論
- `UNK-xxx`: 根拠不足で確定できない事項
- `ASM-xxx`: 明示的な仮定

`DEC-xxx` / `ASM-xxx`はProject Contextまたは案件で明示された同等のCanonical Registryへ一意に記録します。

### Product Risk

テスト深度・優先度の判断にはProduct Riskを使います。Project Riskはリスク評価へ混ぜません。

案件固有方式がない場合は4×4 Risk Matrixを使います。Product RiskはCoverageの深度を変えるために使い、対象内の仕様・要求を無言で削除する理由にはしません。

### Coverageの閉鎖性

フルワークフローでは、対象内のCurrent Effective Authority、Product Risk、Test Requirement、Test Condition、Coverage Itemを、下流成果物または明示Dispositionへ閉じます。

複数候補を持つ技法では、**候補母集団 → Coverage Criteria → Coverage Item → 採用しない候補のDisposition**の順に設計します。

### 主な技法の既定

- 同値分割: 対象Partitionを候補化し、採用またはDisposition
- BVA: 2-valueを既定とし、必要時3-value。採用方式から具体Coverage Itemを定義
- Decision Table: 実行可能ルールを候補化し、採用またはDisposition
- 状態遷移: 対象範囲内の全有効遷移Coverageを既定
- Pairwise: 成立可能な全Value Pairの2-wise Coverageを確認できる場合だけPairwiseと呼ぶ
- Error Guessing: 選択した失敗仮説だけをCoverage対象とし、完全網羅とは表現しない

### ローレベルTest Case

出力するすべてのTest Caseは、ケース単体から次を判断できる具体度にします。

1. 誰が / どの状態で開始するか
2. 何を準備するか
3. 何を操作するか
4. 何を入力・選択するか
5. 何が起きればPASSか

重要期待結果はCurrent Effective Authorityへ追跡し、複数の重要期待結果がある場合は期待結果ごとにAuthorityを対応付けます。

### Blocker / Disposition

Blockerは可能な限り影響範囲だけを停止します。

対象内項目を下流へ展開しない場合は、理由に応じて別テストレベル / 残存リスク / 対象外 / Blocked等へ明示的に位置づけます。低Product Riskだけを理由に`対象外`へ送りません。

### 上流修正

上流成果物の意味を変更した場合は、影響する下流成果物だけを`要再検証`として再確認します。無関係な成果物を全再生成しません。

## 標準との関係

Agent Skillsの公開仕様に合わせ、各Skillを`SKILL.md`を持つ独立ディレクトリとして構成しています。

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このワークフローの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
