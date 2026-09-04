# QAテスト分析・設計 Agent Skills

新規機能・変更機能・指定対象機能を分析し、**テスト実施者が迷わず実行できるローレベルTest Caseまで落とし込む**ためのAgent Skills群です。

毎回繰り返す回帰テストスイートの選定・保守・実行管理は主対象ではありません。

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

各Skillは`skills/<skill-name>/SKILL.md`を持つ独立Skillです。`qa-workflow`も同じく1つのAgent Skillとして扱います。

| Canonical Skill名 | 責務 | 主な成果物 |
| --- | --- | --- |
| `qa-workflow` | 開始点、再利用、routing、Blocked、再開、変更伝播、完了状態のOrchestration | Workflow状態 / routing |
| `spec-analysis` | 仕様分類とCurrent Effective Authority解決 | 仕様分析 / Current Effective Authority |
| `question-analysis` | 未解決事項の分類、停止・継続、回答正規化 | 不明点・矛盾分析 |
| `test-analysis` | Product Risk、テスト重点、深度、テストレベル、技法選択 | テスト分析 |
| `test-requirement-design` | 上流Authority / Riskを検証責務へ変換 | Test Requirement |
| `test-condition-design` | Test Requirementを条件・Coverage Criteria / Itemへ展開 | Test Condition / Coverage Item |
| `test-case-design` | Coverageを第三者が実施可能なケースへ具体化 | Low-Level Test Case |
| `coverage-analysis` | 成果物チェーンのCoverage / 閉鎖性 / Gap分析 | Coverage Analysis |
| `adversarial-review` | QA成果物をCold Reviewし重大度付き欠陥を検出 | Adversarial Review |

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

Product Riskはテスト深度・優先度を決める横断入力として下流へ追跡します。反証レビューは各成果物層へ適用できます。

## Domain LogicのSingle Source of Truth

工程固有の判断規則は担当SkillをSingle Source of Truthとします。`qa-workflow`や他Skillへ詳細アルゴリズムをコピーしません。

| Domain Logic | Single Source of Truth |
| --- | --- |
| Current Effective Authority / SPEC・DECISION・ASMの解決 | `spec-analysis` |
| Blocker / 要確認 / 仮定可能 / 提案・任意の分類、回答正規化 | `question-analysis` |
| Product Risk採点、Risk Matrix、設計深度 | `test-analysis` |
| Test Requirementの粒度・閉鎖 | `test-requirement-design` |
| Coverage Criteria / Coverage Item、BVA / Pairwise / 状態遷移等の技法 | `test-condition-design` |
| Low-Level Test Case具体性、期待結果 / Oracleの具体化 | `test-case-design` |
| Coverage / 閉鎖性 / Gap判定 | `coverage-analysis` |
| Cold Review、重大度、修正責務 | `adversarial-review` |
| Skill routing、Blocked状態、停止 / 再開、変更伝播、Workflow完了 | `qa-workflow` |

レビュー系Skillは担当Skillの成果物契約違反を検出できますが、担当Skill固有の詳細規則を別の正本として再定義しません。

## Progressive Disclosure方針

情報を次の3種類に分けます。

### A. 常に必要

Skill責務、Input / Function / Output、禁止事項、基本停止条件、最低品質条件など、毎回必要な契約です。`SKILL.md`へ置きます。

### B. 条件付きで必要

特定状況だけで必要な詳細判断です。`references/`へ置き、`SKILL.md`から**いつ読むか**を明示します。

今回、条件付き詳細が大きい次のSkillだけreferenceを細分化しています。

- `spec-analysis`: Authority競合 / version / Decision / ASM解決
- `test-condition-design`: テスト技法固有のCoverage規則
- `adversarial-review`: レビュー対象成果物に応じた詳細プローブ

その他のSkillは、現行`guidance.md`の大半が毎回の中心判断に関係するため、分割のための分割を行いません。

### C. 出力形式だけ

出力templateや固定resourceは`assets/`に置きます。判断規則をtemplateへ重複定義しません。

## Agent Skills仕様ベースの構造

Agent Skills Specificationに基づく部分:

```text
skills/<skill-name>/
├── SKILL.md       # 必須
├── references/    # 任意
├── assets/        # 任意
└── scripts/       # 必要な場合のみ
```

Agent Skills Specificationは`SKILL.md`を必須とし、`references/`、`assets/`、`scripts/`等を任意resourceとして扱います。追加ファイル / ディレクトリも許容されますが、以下の`evals/`命名や評価方式自体はSpecificationの標準要件ではありません。

## このリポジトリ独自の開発・評価拡張

```text
EVALS.md
skills/<skill-name>/evals/trigger/
├── train_queries.json
└── validation_queries.json
```

また、`qa-workflow`のProject Context / Workflow State、9 Skillを横断するOrchestration意味論もこのリポジトリ固有です。

Trigger Eval datasetはAgent Skills公開のdescription最適化ガイドを参考にしていますが、`evals/trigger/`は本リポジトリの配置規約です。

## qa-workflowのRuntime前提

`qa-workflow`は、**同一Agent client上で9 Skillすべてが利用可能で、Agentが要求に応じて必要なSkillを追加ロード / 利用できる環境**を前提とします。

Agent Skills Specificationは、Skill AがSkill Bを標準APIでinvokeする共通Skill-to-Skill protocolを規定していません。そのため、このWorkflow前提をAgent Skills標準仕様そのものとは扱いません。

特定Agent clientについて「対応済み」と事前に断定しません。Compatibilityは実Agent client上のWorkflow E2E Evalで確認します。

## Workflowの基本原則

`qa-workflow`はDomain Logicを肩代わりせず、次だけを制御します。

- 要求成果物に必要な開始Skillを決める
- 有効な既存成果物を再利用する
- 必要Skillへroutingする
- Blockedを影響範囲へ局所化する
- 停止 / 再開を管理する
- 上流変更時に影響下流だけを`要再検証`へ戻す
- 修正を最も早い責任Skillへ返す
- Full Workflowの状態と完了を判定する

既定経路:

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

これは依存関係を示す既定経路であり、全依頼で全Skillを実行する義務ではありません。

## Trigger Eval

現在、9 Skillすべてに固定Trigger Eval datasetがあります。

- train: 12件 / Skill（positive 6 / negative 6）
- validation: 8件 / Skill（positive 4 / negative 4）
- 合計: 180 query

Canonical Trigger Evalは9 Skillすべてを同時に利用可能にした状態で実施します。Skill単独 / 限定登録はDiagnostic Modeです。

現在のdescriptionをbaselineとして使用するため、実Trigger Eval結果取得前にはdescriptionを最適化しません。詳細は`EVALS.md`を参照してください。

## Evalの今後

Trigger EvalとOutput Quality Eval / Workflow E2E Evalは分離します。

今後の主な評価:

- Canonical Trigger baseline取得
- description optimization
- fresh queryによるfinal holdout
- Output Quality Eval（with-skill / baseline比較等）
- `qa-workflow` Workflow E2E Eval

空のEval frameworkやholdout datasetを先行作成しません。

## Validation

Agent Skills仕様適合と、このリポジトリ独自の構造検査を分離します。

- **公式仕様検証**: GitHub Actionsで公式`skills-ref validate <skill-directory>`を9 Skillへ実行
- **リポジトリ独自検査**: 9 Skill数、frontmatter最低項目、nameとdirectory一致、JSON parse、train / validation件数、boolean型、positive / negative件数、README / EVALSのSkill記載を確認

CIで使用する`skills-ref`は再現性のため公式`agentskills/agentskills`の特定commitへpinします。

## 標準との関係

ISTQB、IVEC、ISO/IEC/IEEE 29119等は、このWorkflowの目的に必要な考え方だけをテーラリングして利用し、完全準拠やテストプロセス全体の再現は目的としません。
