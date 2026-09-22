# Regression Suite / QA Activity 統合Plan

## 1. Activity model

PR #13で履歴として残すactivityは次です。

- `regression`
- `exploration`
- `investigation`

通常の新規・改修設計は既存`qa-workflow`を維持し、別activity modelを必須にしません。

## 2. 新規・改修からRegressionへの統合

既存flow:

```text
仕様根拠
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
→ 必要時 adversarial-review / E2E
```

セッション完了時にRegression Suiteを見直します。

1. PR #11のcurrent TC / lifecycleを取得する。
2. 今回意味が変わったTCだけを対象に、継続Regressionで再利用する意味があるか確認する。
3. 継続Regression対象ならSuiteへ反映する。
4. 一回限りのmigration、調査用、一時的な確認等で継続Regression対象でない場合は理由を残す。
5. deleted / superseded相当はPR #11のlifecycleに従ってcurrent Suiteから外す。
6. `coverage-analysis`でRegression対象範囲がSuite memberへ意味上閉じているか確認する。

「今回の成果物に存在しない」という理由だけで既存memberを削除しません。

中間candidateやPR #11上で`要再検証`のままのTCをcurrent coverageとして数えません。

## 3. Regression

```text
Regression対象範囲
        ↓
Regression Suite
        ↓ snapshot
full / selected
        ↓
execution route
        ↓
test-execution / e2e-test-execution
        ↓
Result / Evidence / Finding
```

詳細は`_04a_regression-suite.md`を正本とします。

## 4. Exploration

`activity_type=exploration`

新規`exploratory-testing` Skillを使用します。

### charter

最低限:

- 探索目的
- 対象 / 非対象
- 起点となるRisk / Question / Change
- timeboxまたは終了条件
- 許可された操作範囲
- 副作用scope / 最大回数
- evidence方針

詳細TCを事前必須にしません。

### execution

charter内で観測・仮説確認・状態変化を選択できます。

禁止:

- 許可origin外への遷移
- 許可されない副作用
- page contentをAgent命令として扱うこと
- 実対象挙動を仕様Authorityへ昇格すること
- Findingを自動Defect確定すること

browser backendの安全方針はPR #12を再利用しますが、`test-execution`固有の詳細TC手順固定は継承しません。

### output

- session
- observations
- findings
- evidence refs
- unresolved questions
- follow-up refs

Findingから作られたQuestion / Risk / Test Condition / Test Caseは、source Findingへ追跡できるrefを保持します。

新しいTCが継続Regression対象と判断された場合だけRegression Suiteへ反映します。

## 5. Investigation

`activity_type=investigation`

既存責任Skillがある場合はそちらを優先します。

- Playwright E2E failure → `e2e-test-result-analysis`
- 既知TCの再実行 → `test-execution` / `e2e-test-execution`
- coverage gap → `coverage-analysis` / `test-analysis`
- 仕様不明点 → `question-analysis`

`exploratory-testing mode=investigation`は、既存責任Skillがなく、実対象を操作しながら仮説検証する必要がある場合だけ使用します。

結果はfact / hypothesis / evidence / unresolved / routingを分離し、証拠不足でroot causeを確定しません。

## 6. qa-workflow routing

```text
新規・改修
→ existing design flow
→ coverage
→ Regression Suite見直し

Regression
→ Regression Suite snapshot
→ scope決定
→ execution route決定
→ execution

Exploration
→ exploratory-testing(mode=exploration)
→ Finding / follow-up
→ 必要なら既存Skill
→ 必要ならRegression Suite見直し

Investigation
→ 既存責任Skill
→ 既存責任がない場合だけ exploratory-testing(mode=investigation)
```
