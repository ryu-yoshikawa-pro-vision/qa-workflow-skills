# Agent Skills Eval方針

このリポジトリでは、Agent Skillsの形式適合、Skill選択、機械判定可能なOutput契約、意味品質、Workflow全体挙動を分離して評価します。

`evals/`、`EVALS.md`、train / validation分割、Deterministic Output Evalのdataset / graderはこのリポジトリ独自の開発・評価拡張です。Agent Skills Specificationの必須標準ディレクトリではありません。

## 評価レイヤー

1. **Spec Validation**: `SKILL.md` frontmatter / 命名規則等のAgent Skills仕様適合
2. **Trigger Eval**: `description`によるSkill選択・誤発火・routing
3. **Deterministic Output Eval**: 機械判定可能なOutput契約、ID・参照・閉鎖性・Invariant
4. **Semantic Output Eval**: 意味解釈が必要な成果物品質（将来）
5. **Workflow E2E Eval**: `qa-workflow`から担当Skillへ遷移し要求成果物まで完了できるか（将来）

どのレイヤーも単独ではQA成果物品質全体を保証しません。

---

# Trigger Eval

## Canonical / Diagnostic

Canonical Trigger Evalは**9 Skillすべてを同一Agent client上で同時に利用可能**にし、queryごとにclean contextで独立実行します。Target Trigger / Unexpected Trigger / Routing Correctnessを確認します。

対象Skill: `qa-workflow`, `spec-analysis`, `question-analysis`, `test-analysis`, `test-requirement-design`, `test-condition-design`, `test-case-design`, `coverage-analysis`, `adversarial-review`。

対象Skill単独または限定Skillだけを利用可能にする実行はDiagnostic Modeです。Canonical Trigger Scoreには使いません。

既定では各queryを3回実行し、`trigger_rate = 発火回数 / 実行回数`を使います。`should_trigger: true`は`> 0.5`、falseは`< 0.5`を既定とします。回答内容から発火を推測せず、Skill loadingを観測できるlog等を使用します。

## Dataset

```text
skills/<skill-name>/evals/trigger/
├── train_queries.json
└── validation_queries.json
```

- train: 12件 / Skill（positive 6 / negative 6）
- validation: 8件 / Skill（positive 4 / negative 4）
- 9 Skill合計: 180 query

現descriptionと180 queryはbaseline取得前のため固定します。description選定後、train / validationに未使用のfresh queryでfinal holdoutを行い、holdout queryは最終評価直前または別PRで作成します。

baseline取得後は、QA専門用語を使わない依頼、省略表現、曖昧依頼、長いcontext、誤字 / 表記揺れ、暗黙的Skill要求等を別変更で追加検討します。

---

# Deterministic Output Eval

## 目的

各SkillのOutput契約 / 品質ゲートのうち、**意味解釈なしで正否を決められる部分だけ**を機械評価します。

```text
明確に機械判定できる      → ERROR assertion
疑わしいが誤検知し得る    → WARNING assertion
意味評価が必要             → Semantic Output Evalへ残す
```

独自weighted scoreは作りません。ERROR pass/fail、assertion pass rate、WARNING件数を保持します。

## Canonical Output制約

初期Deterministic Evalは、各Skillの既定`assets/output-template.md`を使ったMarkdownだけをCanonical対象とします。

`qa-workflow`は`assets/workflow-state-template.md`を基準とし、routing fixtureでは`開始Skill` / `最終Skill`を明示します。

案件固有フォーマットを許容するSkill契約自体は変更しません。任意形式を万能parserで解析することは今回のscope外です。

## Dataset

```text
skills/<skill-name>/evals/
├── trigger/
│   ├── train_queries.json
│   └── validation_queries.json
└── output/
    ├── evals.json
    └── cases/
        ├── case-001/
        │   ├── input.md
        │   └── expected.json
        └── case-002/
            ├── input.md
            └── expected.json
```

9 Skillすべてに最低2ケースあります。`expected.json`はGolden文章ではなく、known IDs、fixture-backed closure、Risk level、Pairwise factor/value/constraint、状態遷移、既知欠陥等の既知事実だけを持ちます。

## Grader Architecture

```text
scripts/evals/deterministic/
├── run.py
├── markdown_parser.py
├── result.py
├── common.py
├── validators/
│   ├── qa_workflow.py
│   ├── spec_analysis.py
│   ├── question_analysis.py
│   ├── test_analysis.py
│   ├── test_requirement_design.py
│   ├── test_condition_design.py
│   ├── test_case_design.py
│   ├── coverage_analysis.py
│   └── adversarial_review.py
└── tests/
    └── test_deterministic.py
```

Python標準ライブラリだけを使用します。共通層はMarkdown table解析、ID抽出 / 一意性、参照存在、allowed values、required fields、Disposition、graph closure、Pairwise feasible / covered pair計算、結果集計を担当します。Skill固有契約だけを各validatorへ置きます。

Assertion ID一覧は`scripts/evals/deterministic/ASSERTIONS.md`を正本とします。

## ERROR / WARNING

ERROR例:
- 重複ID
- IDと分類不一致
- unknown upstream reference
- Risk Matrix不一致
- fixture上流項目の未閉鎖
- Pairwise 2-wise不足
- 致命的 + 残存リスク受容
- `完了` + Blocked / 要再検証

WARNING例:
- 期待結果中の「正常」「正しく」「問題ない」「適切」
- 他Test Case依存らしき表現
- Product Risk表へProject Riskらしき語が混入

WARNINGだけではEval全体をfailにしません。

## CLI

Agent実行とOutput保存はgraderの責務外です。

```bash
python scripts/evals/deterministic/run.py \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output path/to/generated-output.md
```

```bash
python scripts/evals/deterministic/run.py \
  --skill all \
  --output-root path/to/saved-outputs
```

all modeは`<output-root>/<skill>/<eval-id>.md`を探索します。

## 主要Invariant

- **spec-analysis**: ID / 分類、SRC参照、Current Effective Authority種別・関係・参照、撤回 / 置換済みDecision禁止
- **question-analysis**: Q ID、分類 / 正規化先、再開Skill、Blocker-Blocked整合、Assumption状態 / ASM ID、fixture-backed分類
- **test-analysis**: RISK ID、必須列、Impact / Likelihood 1..4、4x4 Risk Matrix再計算、参照、testability / technique values
- **test-requirement-design**: TR ID、Authority / Risk参照、優先度、観測方法、Disposition、Authority / Risk closure、最高Risk優先度継承
- **test-condition-design**: TCN / CI ID、親TCN、参照、TR closure、Disposition、Pairwise 2-wise、fixture-backed状態遷移 / BVA
- **test-case-design**: TC ID、Low-Level必須列、上流 / Authority参照、CI / TCN closure、Disposition、優先度維持、番号付き期待結果と根拠対応、曖昧表現WARNING
- **coverage-analysis**: fixture graphからGap / orphanを独立再計算し、Outputの認識、Blocked誤分類、修正Skillを確認
- **adversarial-review**: REV ID、重大度、対象、修正Skill、処置、致命的受容禁止、重大受容時承認、重大度別件数、fixture-backed決定論的欠陥
- **qa-workflow**: Workflow / Skill状態、Canonical Skill名、Blocked / 要再検証残存時の完了禁止、fixture-backed routing

## Semantic Output Evalへ残すもの

Deterministic EvalでERRORにしません。

- 仕様内容そのものの正しさ / 抽出網羅性
- Current Effective Authority解決の意味的妥当性
- 本当にBlocker / 要確認 / 仮定可能か
- Product Riskの意味的なImpact / Likelihood妥当性
- Test Requirementが適切な検証責務か
- 技法選択自体が妥当か
- Coverage Criteriaの意味的十分性
- Error Guessing / scenarioの妥当性
- Oracle内容の意味的正しさ
- Test Case文章の明瞭さ（WARNING以上の断定）
- Coverageが製品リスクに対して十分か
- Adversarial Reviewの指摘内容 / 重大度の意味的正しさ
- Workflow routingが実案件上最適か（fixtureで明示されたケースを除く）

## Grader Self-Test

各validatorについてvalid fixtureがPASSし、deliberately invalid fixtureで期待AssertionがFAILするunit testを持ちます。

重点: Risk Matrix誤り、重複ID、unknown reference、未閉鎖Coverage、Pairwise不足Pair、致命的 + 残存リスク受容、Workflow完了 + Blocked。

CIでunit testを実行します。

---

# Semantic Output Eval（将来）

LLM Judge等を導入する場合もDeterministic assertionと混同しません。with-skill / without-skill、検証責務・Coverage・Oracle・第三者実施可能性などの意味評価は別PRで扱います。今回は実装しません。

---

# Workflow E2E Eval（将来）

Deterministic `qa-workflow` validatorは出力された状態 / routing判断の整合だけを評価します。実Agent client上で、正しい開始Skill load、不要Skill回避、既存成果物再利用、局所Blocked、変更伝播、要求成果物での終了、Domain Logic肩代わり防止を確認するE2Eは別評価です。

Agent Skills Specificationは共通Skill-to-Skill APIを規定しません。特定ClientのCompatibilityはE2Eで確認します。

## 現在の状態

- 9 Skill Trigger dataset: 180 query、未変更
- description: 未変更
- Deterministic Output Eval: 9 Skill × 2 case以上
- Deterministic grader: 実装済み
- LLM Judge: 未導入
- Semantic Output Eval: 未実装
- Workflow E2E Eval: 未実装
