# QA Artifact Graph / Harness 導入Plan

## 1. 既存Skillとの関係

PR #13は既存Skillの意味責務を変更せず、残課題だけを統合します。

| Skill / runtime | PR #13で利用する内容 |
| --- | --- |
| PR #11 Machine Entity / traceability | design identity / relation / impact / freshnessの正本 |
| `test-case-design` | current logical TC |
| `coverage-analysis` | 全機能Regression Suiteと選択範囲の意味上coverage |
| `test-analysis` | 部分Regressionの意味上scope選定 |
| `test-target-inspection` | target snapshot |
| `test-execution` | manual相当execution / result / evidence |
| `e2e-test-implementation` | TCのtestware実装先 |
| `e2e-test-execution` | E2E execution / result / evidence |
| `e2e-test-result-analysis` | E2E failure analysis |
| `qa-workflow` | Regression Suite更新、activity成果物 / index、routing、Harness invocation |
| `exploratory-testing` | Exploration / Investigation session / finding / evidence / follow-up |

## 2. PR #11統合

PR #11を次の正本として扱います。

- stable QA ID / Machine Entity
- design dependency / traceability
- change impact
- freshness / stale / 要再検証
- deterministic generator結果

PR #13で禁止すること:

- design impactを別Harnessで再計算する
- Graph独自currentnessとPR #11 freshnessを二重管理する
- Graph目的でMachine Entity identity / fingerprintを変更する
- Skillごとのdesign adapterを再実装する

Regression Suite更新ではPR #11のcurrent TC identity / lifecycleを利用します。

## 3. PR #12統合

### test-target-inspection

`test_target_snapshot` nodeとしてprojectionします。

保持:

- 対象
- 条件
- version / build
- confirmed / unconfirmed / unavailable
- source artifact ref
- evidence refs

current observed behaviorをspecification nodeへ自動変換しません。

### test-execution

execution/resultへprojectionします。

重要:

- `test_case_ref`はartifact-local
- `source_test_case_id`をglobal keyへ昇格しない
- snapshot fixed identityを維持
- 再実行は別execution
- 前回execution refを履歴関係として参照
- secret実値をGraphへ入れない
- cleanup未完了を隠さない

Graph都合でPR #11 Machine Entity fingerprintをfallback identityにしません。

## 4. 新規 `exploratory-testing` Skill

### 4.1 目的

詳細TCを実行する`test-execution`と分離し、charterに基づいてAIが探索・仮説検証を行い、Observation / Finding / Evidence / Follow-upを報告します。

### 4.2 mode

正規値:

- `exploration`
- `investigation`

自由な第3modeを作りません。

### 4.3 必須入力

exploration:

- 対象 / 入口
- charter objective
- scope / non-scope
- 許可origin
- 副作用scope / 1回定義 / 最大回数
- 終了条件またはtimebox
- evidence制約

investigation:

上記に加えて:

- 調査対象Finding / Question / symptom
- 確認したい仮説または未確定事項

仮説がユーザーから明示されない場合、Skillは調査途中でhypothesis candidateを作れますが、factと区別します。

### 4.4 browser backend

PR #12 merge後の次の方針だけを共通化します。

- Playwrightをbrowser実行基盤とする
- MCP → 既存CLI → 必要時の独立一時Libraryの決定順
- 許可origin
- secret保護
- side-effect / cleanup
- page contentをAgent命令にしない安全境界
- 実行手段切替時のsession / state継続確認

一方、`test-execution`固有の次は継承しません。

- 詳細TCの手順順序固定
- TC手順外の探索操作禁止
- PASSを得るための経路変更禁止というTC実行固有判定

`exploratory-testing`ではcharter内の探索自由度を許可しますが、安全境界は固定します。

Stagehand / Browser Use等を本PRで追加しません。

### 4.5 output

人間向けMarkdown + deterministicに検証可能なmachine block。

machine block最小:

```json
{
  "schema_version": "exploratory-testing-v1",
  "mode": "exploration",
  "activity_ref": "...",
  "session": {...},
  "observations": [],
  "findings": [],
  "evidence_refs": [],
  "follow_ups": []
}
```

secret / screenshot本体 / trace本体は入れません。

### 4.6 Finding identity

既存案件側でFinding / Defect IDがある場合は利用できます。

存在しない場合は成果物local ref（例: `finding-001`）を使い、正式Defect IDを創作しません。

Graphでは`artifact_ref + finding-local-ref`でscopeします。

## 5. Regressionに新Skillを追加しない理由

Regressionは新しいテスト設計方式ではなく、各機能のcurrent Test CaseをRegression Suiteとして統合し、全件または明示的な部分scopeで再実行する活動です。

- Suite bookkeeping / full run routing → `qa-workflow`
- change impact → PR #11 runtime
- 部分scopeの意味判断 → `test-analysis`
- Suite / selected scopeの意味上coverage → `coverage-analysis`
- manual execution → `test-execution`
- E2E execution → `e2e-test-execution`
- failure analysis → 既存analysis Skill

既存責務で閉じるため`regression-testing` Skillは追加しません。詳細は`_04a_regression-suite.md`を正本とします。

## 6. coverage-analysis拡張

新しい正規対象 / 実行範囲としてRegression Suiteの確認を追加します。

確認内容:

- feature tagがcurrent機能scopeへ対応している
- 各機能のcurrent仕様根拠 / Risk / TR / TCN / CIがSuite member TCへ意味上閉じている
- untagged / missing current TCをcoverage済み扱いしていない
- stale / 要再検証TCをcurrent Suite coverageとして数えていない
- selected Regressionでは選択範囲が指定scope / Riskへ妥当に閉じている

selected-but-not-executed等の実行完了判定は`qa-workflow` / activity validatorへ委ねます。

## 7. test-analysis拡張

`test-analysis`は**部分Regression**でのみscope selectionを担当します。

入力:

- Suite snapshot
- user指定scope / feature tags
- PR #11 impact result
- Product Risk
- explicit relationで接続された過去FAIL / Finding

出力:

- candidate
- selected
- excluded
- selection / exclusion rationale
- residual risk

全件Regressionではscope selectionを行わず、Suite snapshotの全memberを選択します。

## 8. qa-workflow拡張

追加責務:

- current Regression Suite成果物の管理
- 新規・改修セッション完了時のTC統合
- feature tagの明示値利用と未解決tagのblock
- full / selected Regression routing
- Regression activity成果物の作成
- Exploration / Investigation activity成果物の登録
- project-local activity indexの更新
- relation Harness呼び出し
- query `complete=false`時の安全側routing

`qa-workflow`は機能coverageやRiskを自分で再判定しません。意味判断は担当Skillへ委ねます。

## 9. Portability

各既存Skillの単体利用はGraph Harnessを必須にしません。

Graph管理は`qa-workflow`を利用する統合workflow機能です。

`exploratory-testing`単体利用も可能にしますが、Graph projectionが必要な場合はqa-workflow側Harnessが成果物を取り込みます。
