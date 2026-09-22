# Regression / Exploratory Testing 統合Plan

## 1. 評価方針

### routing / responsibility

- 新規・改修要求は既存Skillへroutingされる
- Regression要求は`regression-testing`へroutingされる
- Exploration要求は`exploratory-testing`へroutingされる
- `test-analysis`がRegression membership / selection責務を持たない
- `qa-workflow`がRegression固有判断を再実装しない

### deterministic

- project-wide TC discovery completeness
- initial baseline reconciliation
- Suite / Activity schema
- membership source ref / revision
- full / selected snapshot整合
- required execution route closure
- TC countとTCなし補助testware countの分離
- Activity lifecycle / immutable条件
- Activity discovery completeness
- direct ref / deterministic scan
- relation indexを実装する場合だけ再生成性 / query completeness

### semantic

- `regression-testing`によるmembership判断
- Regression対象範囲変更時のmembership再評価
- full / selected selectionの妥当性
- residual risk
- Suiteとは独立したRegression対象範囲のcoverage
- TC→E2E実装coverage
- `test-target-inspection`とInvestigationの責務境界
- Finding / follow-up

### runtime smoke

- existing design flow → regression-testing handoff
- 既存TCを持つprojectでinitial baseline
- scope変更のみ → membership再評価
- regression-testing → full Run → manual / E2E
- selected Run
- Activity block / resume / complete
- exploratory-testing
- Finding → design flow → regression-testing handoff

## 2. 必須評価

### Skill routing

- 「新機能のテスト分析」→ `test-analysis`
- 「この変更のテストケースを設計」→ `test-case-design`
- 「Regressionを実施」→ `regression-testing`
- 「変更影響からRegression対象を選んで」→ `regression-testing`
- 「探索的テストをして」→ `exploratory-testing`
- 「現在のUI構造を確認」→ `test-target-inspection`
- Regression要求を`test-analysis`へ誤routingしない
- 新規・改修要求を`regression-testing`へ誤routingしない

### TC discovery / initial baseline

- authoritative discovery rootから全current TC sourceを列挙
- sourceを1件欠落させたfixtureでbaseline completenessがPASSしない
- 既存TC A/B/Cがあり今回Cしか変更していなくてもinitial baselineではA/B/Cを判断
- discoveryを保証できない場合、baselineをcompleteとして扱わない

### Regression membership

- one-off migration TCを恒常memberにしない
- one-off責務自体がcurrent Regression対象範囲に残る場合はcoverage gapを黙らせない
- stable TC update
- split / mergeはPR #11 lifecycleに従う
- deleted / supersededをcurrent memberにしない
- feature tagなしでも成立
- TC無変更でもrole / test level / Regression scope / relevant Risk変更で再評価
- 影響範囲不明ならcurrent TC全体を再確認

### Full / Selected

- user scope優先
- project policy利用
- 未定義時full fallback
- fullはsnapshot全TC member
- selectedはsubset
- selectedをSuite全体完了と扱わない
- selection rationale / residual riskを保持

### manual / E2E route closure

- E2E存在だけでmanual不要としない
- partial E2Eで必要routeを残す
- 1 TC → 2 E2Eで片方未実行ならexecutedにしない
- manual + E2Eで片方未実行ならexecutedにしない
- FAIL / 判定不能とexecutedを分離
- 2 TC → 1 E2Eでexecutionを重複起動しない
- required routeすべてがexecutionへ閉じた場合だけexecuted

### TCなしE2E

- TC IDを創作しない
- user明示またはproject policyだけで参加
- fullでも暗黙加入しない
- auxiliary countをTC countと分離
- TC-based coverageへ算入しない

### Activity

- project context ref / revision
- selection input refs / revisions
- block → resume
- scope / snapshot変更時は別Activity
- 完了後immutable
- workflow完了と全TC PASSを混同しない
- current Suite更新でpast Activityを書き換えない

### Activity discovery

- fixed rootならindexなしで全Activity列挙
- index方式ならproject contextからindexを一意に発見
- Activity保存成功 / index登録失敗を保存完了扱いしない
- dangling index refを拒否

### PR #11 / #12境界

- PR #11 freshnessを参照し独自stateを生成しない
- PR #12 TC snapshot / execution schemaをActivityへ複製しない
- `source_test_case_id`をglobal identityへしない

### candidate completeness

- discovery source不足 / unsupported / dangling / unmapped等で`complete=false`
- `complete=false`空集合をRegression不要へ変換しない
- safety fallbackを維持

### Exploration / Investigation

- current UI確認 → `test-target-inspection`
- 既知TC実行 → execution Skill
- E2E failure → result analysis
- 仕様不明 → question-analysis
- ownerなしの仮説駆動調査 → `exploratory-testing(mode=investigation)`
- Findingを自動Defect化しない

### relation index不要ケース

- TC → past Activityをdeterministic scanで回答できる場合はindex不要
- scanで要件を満たす限りrelation indexを実装しない

## 3. CI

実装開始時のPR #11 / #12 merge後CIへ次を追加・更新します。

- Skill一覧へ`regression-testing` / `exploratory-testing`
- trigger dataset
- semantic dataset
- deterministic validator / output eval
- qa-workflow routing
- Regression Suite / Activity validator
- current TC discovery / initial baseline test
- execution route closure test
- Activity discovery test
- runtime smoke
- project context schema / docs
- README / EVALS / ASSERTIONS
- `skills-ref validate`

relation indexを実装した場合だけrelation build / query testを追加します。

## 4. 実装順序

### Step 0: PR #11 / #12 merge後の再判定

- merge済み実装を確認
- project-wide TC inventory有無
- current lifecycle / impact契約
- TC→E2E / execution history
- Activity保存規約
- PR #11 / #12だけで解けるものを除外

### Step 1: regression-testing最小Skill

まず新しい責務境界を成立させます。

- `skills/regression-testing/SKILL.md`
- guidance
- trigger / negative routing
- initial baselineの最小artifact
- existing design SkillへRegression固有責務を追加しないことを確認

### Step 2: initial baseline / membership

```text
Regression対象範囲
→ authoritative TC discovery
→ current TC
→ regression-testing membership
→ baseline
→ coverage validation
```

### Step 3: membership更新

- TC変更
- scope / policy / Risk変更
- one-off終了
- impact範囲不明時の全current TC再確認

### Step 4: Regression Run / Activity

```text
baseline snapshot
→ regression-testing full / selected
→ required routes
→ execution Skills
→ regression-testing Activity update
```

### Step 5: execution route / auxiliary testware

- partial automation
- manual + E2E
- many-to-many
- TCなしE2E
- route closure

### Step 6: Activity lifecycle / history

- provenance
- block / resume
- complete → immutable
- discovery

### Step 7: exploratory-testing

- Skill / guidance
- routing
- browser safety
- Finding follow-up

### Step 8: end-to-end QA cycle

```text
新規・改修
→ current QA成果物
→ regression-testing
→ Regression
→ Finding /変更
→ 新規・改修flowまたはExploration
→ regression-testing再評価
```

### Step 9: relation index gate

direct ref → deterministic scanで不足した場合だけ実装します。

### Step 10: 全体回帰

既存Skill、PR #11 / #12、新規2 Skill、routing、CI、runtime smokeを確認します。

## 5. 実装時に避けること

- `test-analysis`へRegression membership / selection責務を追加する
- `qa-workflow`へRegression固有意味判断を追加する
- `coverage-analysis`へRegression selection責務を追加する
- 新規・改修SkillがSuiteを直接更新する
- TC discovery completenessを確認せずbaselineをcomplete扱いする
- TC変更時だけmembership再評価する
- SuiteをTC lifecycleの第二正本にする
- feature tagをcoverage / membership必須にする
- full scopeと全件実行済みを混同する
- required routeの一部だけでexecuted扱いする
- TCなしE2Eを暗黙加入する
- completed Activityを書き換える
- relation indexをreverse lookupだけで導入する

## 6. 完了条件

- `regression-testing`と`exploratory-testing`の責務が独立している
- 既存新規・改修SkillにRegression固有責務が追加されていない
- `qa-workflow`はroutingに留まる
- initial baselineを構築できる
- membershipをscope / policy / Risk変更でも再評価できる
- full / selected / execution / resultを分離できる
- required execution route closureを一意に判定できる
- TCなしE2Eを明示方針だけで扱える
- Regression Activityからselection判断を再現できる
- Activity lifecycle / discoveryが一意
- Exploration / Investigation routingが一意
- relation indexなしで主workflowが成立する
- deterministic / semantic / runtime smokeと既存CIがPASSする
