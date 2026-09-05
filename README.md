# QAテスト分析・設計 Agent Skills

新規機能・変更機能・指定対象機能を分析し、**テスト実施者が迷わず実行できるLow-Level Test Caseまで落とし込む**ためのAgent Skills群です。

## Skill構成

```text
skills/
├── qa-workflow/
├── spec-analysis/
├── question-analysis/
├── test-analysis/
├── test-requirement-design/
├── test-condition-design/
├── test-case-design/
├── coverage-analysis/
└── adversarial-review/
```

各Skillは`skills/<skill-name>/SKILL.md`を持つ独立Skillです。`qa-workflow`も1 Skillとして扱います。

| Skill | 責務 |
| --- | --- |
| `qa-workflow` | 開始点、再利用、routing、Blocked、再開、変更伝播、完了 |
| `spec-analysis` | 仕様分類 / Current Effective Authority |
| `question-analysis` | 未解決事項分類 / Assumption / 回答正規化 |
| `test-analysis` | Product Risk / 重点 / 深度 |
| `test-requirement-design` | 検証責務 |
| `test-condition-design` | Test Condition / Coverage Criteria / Item |
| `test-case-design` | Low-Level Test Case / Oracle具体化 |
| `coverage-analysis` | Coverage / 閉鎖性 / Gap |
| `adversarial-review` | Cold Review / 重大度 |

## 成果物チェーン

```text
Current Effective Authority
  ↓
Test Requirement
  ↓
Test Condition
  ↓
Coverage Item
  ↓
Test Case
  ↓
Coverage Analysis
```

Product Riskは深度・優先度の横断入力です。

## Domain LogicのSingle Source of Truth

工程固有ルールは担当Skillを正本とし、`qa-workflow`やreview Skillへ詳細アルゴリズムを複製しません。

| Domain Logic | Single Source of Truth |
| --- | --- |
| Current Effective Authority / SPEC・DECISION・ASM | `spec-analysis` |
| 不明点 / Assumption | `question-analysis` |
| Product Risk | `test-analysis` |
| Test Requirement | `test-requirement-design` |
| Coverage Criteria / Item / テスト技法 | `test-condition-design` |
| Low-Level Test Case / Oracle | `test-case-design` |
| Coverage / Gap | `coverage-analysis` |
| Cold Review / 重大度 | `adversarial-review` |
| routing / Blocked / 再開 / Workflow完了 | `qa-workflow` |

## Progressive Disclosure

- `SKILL.md`: 常に必要な契約
- `references/`: 条件付き / 詳細判断
- `assets/`: 出力template / resource

## Agent Skills仕様と独自拡張

Agent Skills仕様ベース:

```text
skills/<skill-name>/
├── SKILL.md
├── references/
├── assets/
└── scripts/      # 必要な場合
```

このリポジトリ独自の開発・評価拡張:

```text
EVALS.md
scripts/evals/deterministic/
skills/<skill-name>/evals/
├── trigger/
└── output/
```

`evals/`やgraderはAgent Skills Specificationの必須標準機能ではありません。

## Eval

### Trigger Eval
Skill選択精度を評価します。datasetは9 Skill × 20 query = 180 queryです。Canonical Modeは9 Skill同時利用、単独SkillはDiagnostic Modeです。

### Deterministic Output Eval
Canonical output templateを使った出力について、ID / 参照 / allowed values / required fields / Risk Matrix / closure / Pairwise / review・Workflow invariant等、機械判定可能な契約だけを評価します。

`known_*`は「参照可能なID集合」、`required_*`は「Outputへ実際に存在すべきEntity」です。キー未指定と空集合は区別します。

必須Output tableやrequired Entityの欠落はERRORです。`--skill all`はmanifest上の全Outputファイルを要求し、欠落が1件でもあればFAILします。

Pairwise生成組合せはFactor / Value / constraintだけでなく、参照するCoverage Item IDの実在性・一意性も検査します。fixture-backed状態遷移も実在するCoverage Item IDへ閉鎖する必要があります。

```bash
python scripts/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

Deterministic Evalだけで意味品質全体を保証しません。`assertion_pass_rate`はAssertionのpass比率であり、QA品質の総合点ではありません。詳細は`EVALS.md`を参照してください。

### 評価レイヤー
- Trigger Eval
- Deterministic Output Eval
- Semantic Output Eval
- Workflow E2E Eval

## qa-workflow Runtime前提

同一Agent client上で9 Skillすべてが利用可能で、Agentが必要なSkillを追加ロード / 利用できる環境を前提とします。Agent Skills Specificationが共通Skill-to-Skill APIを保証するとは扱いません。

## Validation

CIで、公式`skills-ref validate`、Trigger dataset構造、Deterministic Output Eval dataset構造、grader unit / integration testを分離して実行します。

## 標準との関係

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このWorkflowの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
