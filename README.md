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

## 現行QA業務フロー（テスト分析・設計）

以下は、対象範囲の成果物を新規に作成する場合のFull Workflowの代表経路です。実際には要求成果物と有効な既存成果物に応じて開始 / 再開工程を決め、途中工程からの開始、既存成果物の再利用、不要工程の省略を行います。

不明点・矛盾はどの工程からでも`question-analysis`へroutingでき、解消後は影響する再開先工程へ戻ります。上流成果物の意味が変わった場合も、無関係な成果物を全再生成せず、影響する下流だけを`要再検証`として扱います。

```mermaid
flowchart TD
    A[QA対象の発生<br/>新規機能・変更機能・指定対象機能]
    B[対象範囲・要求成果物・既存成果物を確認]
    C[必要な開始 / 再開工程を決定]
    D[仕様分析]
    E[不明点・矛盾分析]
    F{未解決事項の影響}
    G[局所Blockedを記録<br/>影響しない範囲は継続]
    H[関係者へ確認]
    I[回答・判断を反映]
    J[影響する再開先工程へrouting]
    K[テスト分析]
    L[テスト要求設計]
    M[テスト観点・条件設計<br/>Test Condition / Coverage Item]
    N[Low-Level Test Case設計]
    O[Coverage Analysis]
    P[Adversarial Review]
    Q{重大な問題・抜けがあるか}
    R[最も早い責任工程を特定]
    S[影響範囲のみ修正・再検証]
    T{Blocked / 要再検証の最終状態}
    U[影響範囲を担当工程で再検証]
    V[必要なCoverage / Reviewを再実行]
    W[部分完了<br/>Blockedあり]
    X[Blocked]
    Y[完了]

    A --> B
    B --> C
    C -->|Full Workflow代表経路| D
    D --> E
    E --> F

    F -->|継続可能| K
    F -->|局所Blocked| G
    G --> K
    G -.-> H
    H --> I
    I --> J
    J --> C
    F -->|全体Blocked| X

    K --> L
    L --> M
    M --> N
    N --> O
    O --> P

    P --> Q
    Q -->|あり| R
    R --> S
    S --> V
    V --> T

    Q -->|なし| T
    T -->|要再検証あり| U
    U --> V
    T -->|局所Blockedあり| W
    T -->|全体Blocked| X
    T -->|なし| Y

    W -.->|Blocked解除後| J
    X -.->|Blocked解除後| J
```

図中の修正routingや再開先の詳細は`qa-workflow`が管理し、各工程固有の判断規則は担当SkillをSingle Source of Truthとします。

### 各工程をQA業務として言い換えると

| # | QA業務 | 実際にやること | 主な成果物 | 対応Skill |
| --- | --- | --- | --- | --- |
| 1 | QA対象・スコープ確認 | 何をQAするのか、どこまでを対象とするか、要求成果物と利用可能な既存成果物を確認し、必要な開始 / 再開工程を決める | 対象範囲、Workflow状態 | `qa-workflow` |
| 2 | 仕様整理・仕様分析 | Figma、要件書、Q&A、リポジトリ、リリース資料などを確認し、現在有効な仕様と根拠を整理する | Current Effective Authority、仕様分析 | `spec-analysis` |
| 3 | 不明点・矛盾整理 | 仕様やQA成果物の不足・矛盾・曖昧さを整理し、Blocked範囲、継続可否、回答後の再開先を決める | Blocker、要確認、仮定可能事項、再開先 | `question-analysis` |
| 4 | テスト分析 | 変更影響とProduct Riskを分析し、何をなぜどの深さでテストするかを決める | Product Risk、テスト重点、テストレベル、観測方法 | `test-analysis` |
| 5 | テスト要求設計 | Current Effective AuthorityとProduct Riskから、何を検証・保証すべきかを定義する | Test Requirement | `test-requirement-design` |
| 6 | テスト観点・条件設計 | Test Requirementを、どの条件・観点・組合せで検証するかへ展開する | Test Condition、Coverage Criteria、Coverage Item | `test-condition-design` |
| 7 | Low-Level Test Case設計 | 第三者が単独で実施し、PASS / FAILを判断できる具体的な前提条件・手順・期待結果へ落とし込む | Low-Level Test Case | `test-case-design` |
| 8 | 網羅性・追跡性確認 | AuthorityからTest Caseまでの意味上のつながり、Coverage Criteria充足、未カバー・重複・根拠不足を確認する | Coverage Analysis、Gap、残存リスク | `coverage-analysis` |
| 9 | 反証レビュー | 成果物をCold Reviewし、誤り・抜け・過剰・根拠不足・追跡性欠陥を重大度付きで検出する | Adversarial Review結果 | `adversarial-review` |
| 10 | 修正routing・完了判断 | 指摘を最も早い責任工程へ戻し、影響範囲だけを修正・再検証して、Blocked / 要再検証を含むWorkflow全体状態を判定する | 完了 / 部分完了（Blockedあり） / Blocked | `qa-workflow` |

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

skills/<skill-name>/evals/
├── trigger/
├── output/
├── deterministic/
│   └── validator.py
└── semantic/
    ├── rubric.json
    ├── evals.json
    └── cases/
        ├── case-001/
        │   ├── input.md
        │   └── reference.md
        └── case-002/
            ├── input.md
            └── reference.md

scripts/skills/evals/
├── deterministic/
│   ├── run.py
│   ├── loader.py
│   ├── markdown_parser.py
│   ├── common.py
│   ├── result.py
│   └── tests/
└── semantic/
    ├── run.py
    ├── loader.py
    ├── prompt_builder.py
    ├── result.py
    ├── validate.py
    └── tests/

tests/skills/evals/
├── deterministic/
└── semantic/
```

Skill固有のTrigger dataset、Output fixture、Deterministic validator、Semantic rubric / fixtureは各Skillの`evals/`配下に置きます。

`scripts/skills/evals/deterministic/tests/`と`scripts/skills/evals/semantic/tests/`はShared Runtime固有のportable self-testを保持します。`tests/skills/evals/`はこのリポジトリ固有のSkill構造、dataset、validator contract、CLI、portabilityを検証します。

Skillを利用するだけの場合は`skills/<skill-name>/`のみをコピーします。Evalも含めてSkillを移植する場合は、`skills/<skill-name>/`（Skill Package）と`scripts/skills/evals/`（Shared Skill Eval Runtime）をコピーします。`scripts/skills/evals/`はAgent Skills Specificationが要求する標準ディレクトリではなく、このリポジトリ独自の評価Runtimeです。

`evals/`やgraderはAgent Skills Specificationの必須標準機能ではありません。

## Eval

### Trigger Eval

9 Skillの選択精度を評価します。Canonical Modeは9 Skill同時利用、単独・限定SkillはDiagnostic Modeです。

### Deterministic Output Eval

9 SkillのCanonical outputについて、ID、参照整合、required fields、Risk Matrix、成果物閉鎖、Pairwise、review / Workflow invariant等、意味解釈なしで判定できる契約を評価します。

- `known_*`: fixture側で既知の参照集合。Skill自身がOutput内で生成するEntityの扱いは各Skill契約に従う。キー未指定なら対応する参照検査を行わない。
- `required_*`: Outputに実際に存在しなければならないEntity / 値。

```bash
python scripts/skills/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

### Semantic Output Eval

Deterministicでは確定できない意味的正しさ、妥当性、十分性、適切な抽象度、根拠整合、明瞭性を、Skill固有rubricとSemantic fixtureに基づくLLM Judgeで評価します。Judgeはcriterionごとのratingと根拠だけを返し、criterion statusとoverall verdictはShared Runtimeが算出します。

```bash
python scripts/skills/evals/semantic/run.py \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --output path/to/generated-output.md \
  --judge-command python path/to/judge_adapter.py
```

Agent実行とCandidate Output生成はDeterministic / Semantic Runtimeの責務外です。詳細な評価契約、dataset、CLI、Judge contract、Deterministic / Semantic境界は`EVALS.md`を正本とします。

## qa-workflow Runtime前提

同一Agent client上で9 Skillすべてが利用可能で、Agentが必要なSkillを追加ロード / 利用できる環境を前提とします。Agent Skills Specificationが共通Skill-to-Skill APIを保証するとは扱いません。

## Validation

CIで、公式`skills-ref validate`、Trigger dataset構造、Deterministic Output Eval、Semantic Output Evalを分離して検証します。外部LLM APIはCIから呼ばず、Semantic judge execution contractはfake judgeで検証します。

## 標準との関係

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このWorkflowの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
