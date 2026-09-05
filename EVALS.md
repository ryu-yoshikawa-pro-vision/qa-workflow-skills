# Agent Skills Eval方針

このリポジトリでは、Agent Skillsの形式適合、Skill選択、機械判定可能なOutput契約、意味品質、Workflow全体挙動を分離して評価します。

`evals/`、`EVALS.md`、train / validation分割、Deterministic Output Evalのdataset / graderはこのリポジトリ独自の開発・評価拡張です。Agent Skills Specificationの必須標準ディレクトリではありません。

## 評価レイヤー

1. **Spec Validation**: `SKILL.md` frontmatter / 命名規則等のAgent Skills仕様適合
2. **Trigger Eval**: `description`によるSkill選択・誤発火・routing
3. **Deterministic Output Eval**: 機械判定可能なOutput契約、ID・参照・閉鎖性・Invariant
4. **Semantic Output Eval**: 意味解釈が必要な成果物品質
5. **Workflow E2E Eval**: `qa-workflow`から担当Skillへ遷移し要求成果物まで完了できるか

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

train / validation datasetはdescription最適化の比較基準として固定します。description選定後のgeneralization checkでは、train / validationに使用していないfresh queryをholdoutとして使用します。

Dataset拡張では、QA専門用語を使わない依頼、省略表現、曖昧依頼、長いcontext、誤字 / 表記揺れ、暗黙的Skill要求等を扱います。

---

# Deterministic Output Eval

## 目的

各SkillのOutput契約 / 品質ゲートのうち、**意味解釈なしで正否を決められる部分だけ**を機械評価します。

```text
明確に機械判定できる      → ERROR assertion
疑わしいが誤検知し得る    → WARNING assertion
意味評価が必要             → Semantic Output Eval
```

独自weighted scoreは作りません。ERROR pass/fail、assertion pass rate、WARNING件数を保持します。

`assertion_pass_rate`は全Assertion中の`status=pass`比率であり、QA品質の総合点ではありません。

## Canonical Output制約

Deterministic Evalは、各Skillの既定`assets/output-template.md`を使ったMarkdownをCanonical対象とします。

`qa-workflow`は`assets/workflow-state-template.md`を基準とし、routing fixtureでは`開始Skill` / `最終Skill`を明示します。

案件固有フォーマットはCanonical Deterministic Evalの解析対象外です。案件固有フォーマットを許容するSkill契約自体は変更しません。

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

9 Skillすべてに最低2ケースあります。`expected.json`はGolden文章ではなく、known IDs、required IDs、fixture-backed closure、Risk level、Pairwise factor/value/constraint、状態遷移、既知欠陥等の既知事実だけを持ちます。

- `known_*`: Output中で参照可能なID集合。キー未指定ならその集合による参照検査を行わない。
- `required_*`: Outputに実際に存在しなければならないID / Entity集合。

`known_authorities`等は、**キー未指定**と**キーあり + 空集合**を区別します。後者は「このEvalで参照可能な対象が0件」を意味します。

## Required Output

Canonical Evalでvalidatorが利用する必須テーブル自体が欠落している場合はERRORです。fixtureが`required_*`を持つ場合、必要Entityの欠落もERRORです。

0件が正常なDisposition / Blocked / 仮定候補 / 指摘一覧等は、存在必須でも行数0を許容する場合があります。すべての表へ1件以上を強制しません。

`question-analysis`では、`required_approved_assumptions`に指定されたASMが`承認済み`としてOutputへ存在する必要があります。

`test-analysis`では、fixtureが`required_techniques` / `required_testability`を持つ場合、指定された技法 / テスト可能性がOutputへ存在する必要があります。

## ERROR / WARNING

ERROR例:
- 必須Output table / required Entity欠落
- 必須フィールド欠落
- 重複ID
- IDと分類不一致
- unknown upstream reference
- Risk Matrix不一致
- fixture上流項目の未閉鎖
- Pairwise生成組合せの未知Factor / Value、Constraint違反、必要Factor欠落
- Pairwise生成組合せの未知Coverage Item ID / Coverage Item ID重複 / 不正token
- Pairwise 2-wise不足
- 状態遷移が存在しないCoverage Item IDを参照
- 致命的 + 残存リスク受容
- Workflow状態Invariant違反

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

all modeは`<output-root>/<skill>/<eval-id>.md`を探索し、manifestに定義された**全Outputの存在を必須**とします。1件でも欠落すれば`missing_outputs`へ記録してFAILします。

## Pairwise / 状態遷移

Pairwise fixtureでは、2-wise Coverage計算の前に生成組合せそのものを検査します。

1. Factor / Value universe
2. `Factor=Value` token形式とFactor重複
3. 生成組合せの未知Factor
4. 未定義Value
5. forbidden constraint違反
6. 必要Factor欠落
7. 生成組合せが参照するCoverage Item IDの実在性 / 一意性
8. 有効な生成組合せだけを使ったfeasible pair 100% Coverage

`代表組合せ`にはPairwise保証を要求しません。

fixture-backed状態遷移では、required transitionの`対応Coverage Item ID`がCanonical Coverage Item一覧に存在する必要があります。fixtureに明示Dispositionがある遷移はCoverage Item参照を要求しません。

## Markdown parser制約

Canonical Markdown tableのみを対象とします。セル内のescaped pipe `\|`はセル内容として扱います。headerとrowの列数不一致はsilent truncateせず構造エラーとしてCLIをnon-zeroにします。

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

回帰テストでは、空Output、required table / Entity / field欠落、expected空集合、Authority型不一致、Pairwise不正組合せ / 不正Coverage Item参照、状態遷移の不正Coverage Item参照、required technique / testability / approved ASM欠落、Workflow状態Invariant、承認不一致、Markdown列数不一致を検査します。

CLI integration testではvalid outputのexit 0、invalid outputのexit 1、all modeのOutput欠落non-zeroを確認します。

CIでcompileとunit / integration testを実行します。

---

# Semantic Output Eval

LLM Judge等を使用する意味評価はDeterministic assertionと分離します。with-skill / without-skill、検証責務・Coverage・Oracle・第三者実施可能性などが対象です。

---

# Workflow E2E Eval

Deterministic `qa-workflow` validatorは出力された状態 / routing判断の整合だけを評価します。実Agent client上でのSkill load、不要Skill回避、既存成果物再利用、局所Blocked、変更伝播、要求成果物での終了、Domain Logic肩代わり防止はE2Eで評価します。

Agent Skills Specificationは共通Skill-to-Skill APIを規定しません。特定ClientのCompatibilityはE2Eで確認します。

## 実装状態

- 9 Skill Trigger dataset: 180 query
- Deterministic Output Eval: 9 Skill × 2 case以上
- Deterministic grader: 実装済み
- Semantic Output Eval: 未実装
- Workflow E2E Eval: 未実装
