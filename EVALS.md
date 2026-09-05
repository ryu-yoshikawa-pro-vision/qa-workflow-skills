# Agent Skills Eval方針

このリポジトリでは、Agent Skillsの形式適合、Skill選択、機械判定可能なOutput契約、意味品質、Workflow全体挙動を分離して評価します。

`evals/`、`EVALS.md`、train / validation分割、Deterministic Output Evalのdataset / graderはこのリポジトリ独自の開発・評価拡張です。Agent Skills Specificationの必須標準ディレクトリではありません。

## 評価レイヤー

1. **Spec Validation**: `SKILL.md` frontmatter / 命名規則等のAgent Skills仕様適合
2. **Trigger Eval**: `description`によるSkill選択・誤発火・routing
3. **Deterministic Output Eval**: 機械判定可能なOutput契約、ID・参照・閉鎖性・Invariant
4. **Semantic Output Eval**: 意味解釈が必要な成果物品質（未実装）
5. **Workflow E2E Eval**: `qa-workflow`から担当Skillへ遷移し要求成果物まで完了できるか（未実装）

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

現descriptionと180 queryはbaselineとして固定します。description選定後、train / validationに未使用のfresh queryでfinal holdoutを行います。

---

# Deterministic Output Eval

## 目的

各SkillのOutput契約 / 品質ゲートのうち、**意味解釈なしで正否を決められる部分だけ**を機械評価します。

```text
明確に機械判定できる      → ERROR assertion
疑わしいが誤検知し得る    → WARNING assertion
意味評価が必要             → Semantic Output Evalへ残す
```

独自weighted scoreは作りません。ERROR pass/fail、assertion pass rate、WARNING件数を保持します。`assertion_pass_rate`は全Assertion中の`status=pass`比率であり、QA品質の総合点ではありません。

## Canonical Output制約

Deterministic Evalは各Skillの既定`assets/output-template.md`を使ったMarkdownをCanonical対象とします。`qa-workflow`は`assets/workflow-state-template.md`を基準とします。

案件固有フォーマットを許容するSkill契約自体は変更しません。任意形式を万能parserで解析することは対象外です。

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

9 Skillすべてに最低2ケースあります。`expected.json`はGolden文章ではなく、graderが比較する既知事実だけを持ちます。

### expected.jsonの基本契約

- `known_*`: fixture側で既知の外部参照集合。キー未指定ならその集合による参照検査を行わない。Skill自身がOutput内で生成するEntityは各Skill契約に従い追加で有効な参照対象になり得る。`spec-analysis`ではOutput内で正しく生成されたSPEC / DECISION等がCurrent Effective Authority候補になり得る。
- `required_*`: Outputに実際に存在しなければならないID / Entity / 値。
- キー未指定とキーあり+空集合は区別する。
- `approved_assumptions`: 承認済みとしてOutputに登場できるCanonical ASM IDのlist。
- `required_approved_assumptions`: Outputに承認済みとして存在しなければならないCanonical ASM IDのlist。

## Required Output / Required Entity

Canonical Evalで必須テーブル自体が欠落している場合はERRORです。fixtureが`required_*`を持つ場合、必要Entityや値の欠落もERRORです。

0件が正常なDisposition / Blocked / 仮定候補 / 指摘一覧等は、存在必須でも行数0を許容する場合があります。

## 参照整合

Output中で明示されたIDは、fixtureが対応するknown集合を指定している場合、その集合または各Skill契約上Output内で正当に生成された参照対象に存在する必要があります。`known_*`だけを全Skill共通のstrict whitelistとして扱いません。

- `spec-analysis`: 分析項目が参照するSRC、Current Effective Authority / 関連Authority
- `test-requirement-design`: Authority / Product RiskとDispositionの上流ID
- `test-condition-design`: TR / Authority / Product Risk、TR Disposition、Coverage Item根拠
- `test-case-design`: TCN / Coverage Item / TR / Authority、Dispositionの上流ID
- `coverage-analysis`: fixture graph上のnode
- `adversarial-review`: 対象成果物

`spec-analysis`の情報源行は`SRC-xxx`の一意な`参照ID`と`情報源 / Canonical Registry`を持ちます。

## Product Risk

Impact / Likelihoodは1〜4のみ許可し、Risk Levelを以下の4×4 matrixから再計算します。

```text
Impact 4: 1=中, 2=高, 3=高, 4=高
Impact 3: 1=中, 2=中, 3=高, 4=高
Impact 2: 1=低, 2=中, 3=中, 4=高
Impact 1: 1=低, 2=低, 3=低, 4=中
```

fixtureが`required_techniques` / `required_testability`を指定する場合、対応する技法・テスト可能性Outputを必須とします。

## Pairwise / 状態遷移

Pairwise fixtureでは、2-wise Coverage計算の前に生成組合せ自体を検査します。

1. Factor / Value universe
2. `Factor=Value` token構造とFactor重複
3. 未知Factor / 未定義Value
4. forbidden constraint違反
5. 必要Factor欠落
6. 生成組合せが参照するCoverage Item IDの実在性 / 一意性
7. 有効な生成組合せだけを使ったfeasible pair 100% Coverage

fixture-backed状態遷移は、required transitionが実在するCoverage Itemへ閉鎖することを確認します。

## Adversarial Review

指摘の重大度、対象、修正先、処置、必須フィールド、重大度別件数を検査します。

修正先はCanonical Skillまたは`Project Context / 仕様決定`を許可します。

- `致命的` + `残存リスクとして受容`は禁止。
- `重大` + `残存リスクとして受容`はfixture承認情報がある場合、その参照と一致する必要がある。
- 指摘概要の重要度は`致命的 / 重大 / 軽微 / 提案`のみで、各重要度は一意。
- `expected_defects`に`severity`または`repair_target`が指定された場合だけ、対象Findingの重大度または修正先との一致をfixture-backed条件として要求する。

## Workflow State

Workflow状態表はCanonical Skill名・Skill状態・Skill行一意性を検査します。

- `完了`: `実行中 / Blocked / 要再検証`を残せない。
- `部分完了（Blockedあり）`: 1件以上のBlocked Skillが必要。
- `Blocked`: 1件以上のBlocked Skillが必要。

fixtureに開始Skill / 最終Skill / 利用Skillが明示されている場合はOutputされたrouting判断と比較します。`expected_overall_state`または`expected_skill_states`が指定された場合は、Workflow全体状態または各Skill状態との一致も検査します。

## Markdown parser制約

Canonical Markdown tableのみを対象とします。セル内のescaped pipe `\|`はセル内容として扱います。headerとrowの列数不一致はsilent truncateせず構造エラーにします。

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

all modeはmanifestに定義された全Outputファイルの存在を要求し、欠落を`missing_outputs`へ記録してFAILします。

## Semantic Output Evalへ残すもの

Deterministic EvalでERRORにしません。

- 仕様内容そのものの正しさ / 抽出網羅性
- Current Effective Authority解決の意味的妥当性
- Blocker / 要確認 / 仮定可能の意味的分類
- Product RiskのImpact / Likelihood自体の妥当性
- Test Requirementが適切な検証責務か
- 技法選択自体が妥当か
- Coverage Criteriaの意味的十分性
- Error Guessing / scenarioの妥当性
- Oracle内容の意味的正しさ
- Test Case文章の意味的明瞭さ
- CoverageがProduct Riskに対して十分か
- Adversarial Reviewの指摘内容 / 重大度の意味的妥当性
- Workflow routingが実案件上最適か（fixtureで明示されたケースを除く）

## Grader Self-Test

`test_deterministic.py`、`test_false_pass_regressions.py`、`test_cli_integration.py`で、正常Output、決定論的な不正Output、CLI exit codeを検証します。

CIでは次を実行します。

```bash
python -m compileall -q scripts/evals/deterministic
python -m unittest discover -s scripts/evals/deterministic/tests -v
```

---

# Semantic Output Eval

未実装です。意味品質を評価する場合もDeterministic assertionとは分離します。

---

# Workflow E2E Eval

未実装です。Deterministic `qa-workflow` validatorは出力された状態 / routing判断の整合だけを評価し、実Agent client上のSkill遷移はE2Eで評価します。

Agent Skills Specificationは共通Skill-to-Skill APIを規定しません。特定ClientのCompatibilityはE2Eで確認します。
