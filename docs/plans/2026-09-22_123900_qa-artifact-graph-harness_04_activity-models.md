# Regression / Exploratory Testing 統合Plan

## 1. 主要workflow入口

PR #13では、次を主要workflow入口 / 責任Skillとして扱います。

- 新規・改修: 既存設計Skill群
- Regression: `regression-testing`
- Exploration / Investigation: `exploratory-testing`

これはQA活動の排他的分類ではありません。

同一workflowで、

- 新規・改修 + Exploration
- 修正確認 + Regression
- Regression + Exploration
- Regression FAIL後のInvestigation + 修正確認

等を組み合わせられます。

## 2. 新規・改修からRegressionへの接続

既存flow:

```text
仕様根拠
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

このflowがcurrent QA成果物を確定します。

`test-analysis`は変更影響候補 / Product Risk等を扱いますが、既存Regression baselineから今回実行するTCを確定するRun selectionは行いません。

Regression運用中のprojectまたはユーザーがRegression資産更新を要求したworkflowでは、`qa-workflow`が変更成果物を`regression-testing | baseline / membership`へhandoffします。

設計成果物の完了とRegression reconciliationの完了は分離できます。

## 3. 修正確認のworkflow intent

Confirmation Testingに相当する修正確認は、元のdefectが修正されたことを確認するテスト目的です。PR #13では独立したSkill、Activity、artifact、stateを追加せず、`qa-workflow`が既存Skillを選ぶためのworkflow intentとして扱います。

### 既存の有効なTC / 再現経路がある場合

```text
defect fix
→ currentなknown failing TC / reproductionを特定
→ analysis / designを再実行せずtest-execution または e2e-test-execution
→ source result確認
```

前回execution refを利用できる場合はPR #12 / E2Eのrerun lineageを使用します。

### 既存成果物だけでは修正確認できない場合

期待結果、再現条件、current TCのいずれかが不足・陳腐化している場合だけ、`qa-workflow`が必要な最も早い既存analysis / design Skillへroutingします。必要な範囲を更新してcurrent TCを確定した後、通常のexecution Skillで実行します。

修正確認のためだけの専用analysis / design flowは作りません。

### Regressionとの関係

修正確認がPASSしても周辺Regression不要とは判断しません。

```text
defect fix
├→ 修正確認: 既存TCまたは必要最小限に更新したTCをexecution
└→ 周辺影響確認: 必要ならregression-testing
```

impact / Riskに基づくRegressionは別目的として`regression-testing`が扱います。

## 4. initial baseline

既存TCを持つprojectで初めてRegression管理を開始する場合、`regression-testing`がauthoritative discovery snapshotを固定して全current TCをreconcileします。

大量TCでは同じsnapshotをdeterministicに分割・再開できます。

`complete=true`にする条件:

- discovery sourceが閉じている
- PR #11 current lifecycleへ必要TCを解決できる
- 全current TCのmembershipが判定済み
- requiredなcoverage確認が完了している

legacy TCを`regression-testing`自身で修復しません。

## 5. Regression Run

### domain-only request

次のような要求は`regression-testing`単体から開始できます。

- baselineを更新して
- 今回のRegression対象だけ選んで
- 過去Regressionを確認して

### end-to-end Regression

「Regressionを実施して」のように実行まで含む要求は`qa-workflow`がオーケストレーションします。

```text
qa-workflow
→ regression-testing | Run計画
→ coverage-analysis（必要時）
→ test-execution / e2e-test-execution
→ regression-testing | Run結果更新
→ qa-workflow
```

`qa-workflow`自身はmembership、selection、required route、result判定を再計算しません。

## 6. Regression中のFAIL / Finding feedback

execution結果をActivityへ記録して終了するだけにしません。

### E2E異常

```text
e2e-test-execution
→ e2e-test-result-analysis
→ 最も早い責任Skill
```

### manual相当FAIL / 判定不能

証拠に応じて`qa-workflow`がroutingします。

- 仕様根拠 / 期待結果が不明 → `question-analysis` / 必要時`spec-analysis`
- currentな実対象情報が不足 → `test-target-inspection`
- TC自体の問題 → `test-case-design`
- coverage gap → `coverage-analysis` / 必要時design Skill
- ownerを確定できず実対象を使う仮説検証が必要 → `exploratory-testing(mode=investigation)`

原因を`regression-testing`が推測して確定しません。

### 修正後

```text
product / QA artifact修正
→ 既知TCの再実行による修正確認
→ QA成果物 / membership入力変更があればreconciliation
→ 必要なRegression rerun
```

Findingを自動Defect化しません。

## 7. Exploration

`exploratory-testing(mode=exploration)`を使用します。

```text
Charter
→ Session
→ Observation / Finding
→ Follow-up
```

FindingからQuestion / Risk / TC等が更新された場合、Regression運用中なら必要に応じて`regression-testing | baseline / membership`へhandoffします。

## 8. Investigation

既存責任Skillを先に判定します。

- currentなUI / 既知範囲のふるまい収集 → `test-target-inspection`
- 既知TC実行 → `test-execution` / `e2e-test-execution`
- E2E failure → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- coverage gap → `coverage-analysis`
- owner不明で実対象を操作しながら仮説検証 → `exploratory-testing(mode=investigation)`

Investigationを別Skill / 別runtimeにしません。

## 9. qa-workflow routing

`qa-workflow`は複合活動を接続します。

代表経路:

```text
新規・改修
→ existing design flow
→ 必要条件を満たす場合 regression-testing | baseline / membership

Regression対象の選定だけ
→ regression-testing | Run計画

Regression実施
→ qa-workflow
→ regression-testing | Run計画
→ execution
→ regression-testing | Run結果更新

不具合修正
→ 修正確認として既存TCをexecution
→ 必要なRegression

Exploration
→ exploratory-testing | exploration

Regression manual FAIL
→ owner判定
→ existing owner または exploratory-testing | investigation
→ 修正
→ 既存TC再実行による修正確認
→ 必要なRegression
```

workflow stateでは同一Skillの複数用途を`Skill + 対象 / 実行範囲`で識別します。

## 10. 継続利用する知識への反映

Activity / Session / executionで得たFindingやObservationを、そのままcurrentな知識へ昇格しません。

後続で再利用する価値がある場合:

1. 仕様 / Product Risk / TC / currentな実対象資料等の既存正本へ属するか判定する。
2. 属する場合は最も早い責任Skillへroutingして正本を更新する。
3. 既存正本へ自然に置けない継続知識だけ、project-levelの知識成果物候補にする。
4. source ref / revision、適用scope、environment / version条件を確認できない候補は`要再検証`のままにする。
5. 有効化したentryだけ、次回workflowの入力候補として利用する。

Regression historyやExploration Sessionは知識の由来として保持しますが、知識本文の第二の正本にはしません。

## 11. 複数workflowの同時進行

`qa-workflow`で管理する各workflowは独立した`workflow_ref`を持ちます。

例:

```text
workflow A: 新機能Aのdesign
workflow B: release Regression
workflow C: production issue investigation
workflow D: exploratory session
```

各workflowは自分が開始・利用したartifact / knowledge / project context / environment条件のref / revisionを保持します。

同時進行してもworkflow stateを1件のglobal current stateとして上書きしません。

### 進行中に別workflowが上流を更新した場合

workflow Aがsnapshot v1を使って実行中にworkflow Bがcurrentをv2へ更新しても、Aのhistorical execution / Activity / Sessionをv2へ差し替えません。

ただしAがlatest current stateに対する完了・再利用を主張する前に、参照revision / fingerprintを再確認します。

- 影響あり → 該当scopeを`要再検証`
- 影響なしをdependencyで確認できる → 継続
- 影響範囲を安全に限定できない → 必要scopeを再評価

これにより「当時の結果」と「現在も有効な結果」を分離します。

## 12. 共有current artifactの更新競合

複数workflowが同じcurrent artifactを更新する場合:

- 読み込み時revision / SHA / ETag / content identityを保持
- 保存直前にcurrent revisionを確認
- 変わっていれば古いbaseから上書きしない

stable ID / update scope等により変更範囲がdisjointと決定論的に確認できる場合だけ、current内容を再読込してscope外を維持した上で対象scopeを再適用できます。

scopeが重なる、または判定不能なら、責任Skillでcurrent内容を入力に再評価します。

LLMが競合したsemantic contentを無条件に自動mergeしません。

## 13. 共有環境の同時利用

Regression、Exploration、修正確認等が同時に実対象を操作する場合、環境・test user・test data・tenant・external account等が共有される可能性があります。

実操作を伴うworkflowは、必要なshared mutable resourceをActivity / Session / executionの入力として明示します。

- workflowごとに分離されたresource → 並行実行可能
- 同じresourceでも相互影響がないことを明示できる → project policyに従い並行可能
- 相互影響を否定できない → 直列化またはblock
- policy不明 → 同時利用可能と推測しない

cleanupは自workflowが所有するresource範囲だけを対象にします。

具体的なreservation / lease方式は実装前リサーチで決めます。
