# Regression Suite / QA Activity 統合Plan

## 1. 評価方針

### deterministic

- Suite / Activity schema
- stable ref / artifact-local ref保持
- duplicate / dangling ref
- full / selected snapshot整合
- executed / unexecuted / blocked集計
- activity discovery
- direct ref整合
- relation indexを実装する場合だけ、その再生成性 / query completeness

### semantic

- 継続Regression対象の判断
- Suiteとは独立したRegression対象範囲のcoverage
- selected scopeの妥当性
- TC → E2E実装のcoverage
- Exploration / Investigationの責務境界
- Finding classification / follow-up

### runtime smoke

- 新規・改修 → Suite見直し
- Suite → full Run → manual / E2E
- selected Run
- activity history
- exploratory-testing
- Finding → follow-up

## 2. 必須評価

### Regression対象範囲

- Suiteに存在しないcurrent対象機能があればcoverage gapとして検出できる
- Suite自身のfeature tag一覧だけで「全機能」を定義しない
- 非機能testを明示対象にしていない場合、機械的に機能Suiteへ追加しない

### membership

- 継続的なcurrent機能TCをmemberへ反映できる
- 一回限りmigration TCをcurrentでも恒常memberにしない判断を許容する
- 調査専用TCを自動加入させない
- stable TC更新でidentityを維持する
- split / mergeはPR #11 lifecycleに従う
- deleted / superseded相当をcurrent memberとして数えない
- 今回の成果物にないだけで既存memberを削除しない
- feature tagがなくてもmembership / coverageを失敗させない
- feature renameでTC identityを変更しない

### Full / Selected

- user明示scopeを最優先する
- project policyがあれば利用する
- scope未定義時だけfull fallbackする
- fullはsnapshot全memberをselectedにする
- selectedはsnapshotのsubsetである
- selectedをSuite全体のRegression完了として扱わない
- 100 selected / 98 executed / 2 unexecutedを「100件実行済み」と表現しない
- unexecuted / blockedを集計して保持する

### manual / E2E

- E2E testware追加だけでSuite memberを複製しない
- E2E存在だけでmanual不要と判断しない
- E2EがTCの一部だけをcoverする場合、E2Eだけでlogical TCを閉じない
- 1 TC → 複数testwareを扱える
- 複数TC → 1 testwareを扱える
- TCなしE2EへTC IDを創作しない
- TCなしE2EをTC-based coverageへ自動算入しない

### Activity history

- past activity snapshotをcurrent Suite更新で書き換えない
- fixed pathから発見可能ならindexなしで列挙できる
- indexが必要な場合、存在しないartifact refを検出する
- indexへTC / Result / Finding本文を複製しない

### PR #11 / #12境界

- PR #11のfreshness / `要再検証`を参照し、PR #13独自stateを生成しない
- past PASSをupstream変更だけでFAILへ書き換えない
- PR #12のTC snapshot / execution schemaをactivityへ複製しない
- `source_test_case_id`をglobal identityへしない

### candidate completeness

- unsupported / dangling / unmapped等があれば`complete=false`
- `complete=false`の空集合をRegression不要へ変換しない
- candidate不完全時は明示scope維持、current test basisへの拡大、full fallback / blockの順で安全側に扱う

### Exploration / Investigation

- Finding local ref一意
- evidence / follow-up ref整合
- observationを仕様Authorityへ自動昇格しない
- Findingを自動Defect化しない
- E2E failureをgeneric investigationへ奪わない

## 3. CI

実装開始時のPR #11 / #12 merge後CIを正本として追加先を決めます。

予定:

- Skill一覧へ`exploratory-testing`
- trigger dataset
- deterministic output eval
- semantic dataset validation
- qa-workflow routing
- Regression Suite / Activity validator
- activity discovery test
- 必要なruntime smoke
- `skills-ref validate`
- README / EVALS / ASSERTIONS同期

relation indexを実装した場合だけ追加:

- relation build / query unit test
- canonical reproducibility
- completeness test

Graph Harness専用CIを先に固定しません。

## 4. 実装順序

### Step 0: PR #11 / #12 merge後の再判定

- merge済み実装を確認する
- project全current TCを列挙できるか確認する
- current lifecycleをPR #11だけで判断できるか確認する
- TC → E2E、execution historyを確認する
- activity保存規約を確認する
- PR #11 / #12だけで解けるものをPR #13から除外する

### Step 1: Regression対象範囲 / membership vertical slice

小さいfixtureで次を確認します。

- 継続的なcurrent TC
- 一回限りTC
- stable TC更新
- deleted TC

Graph、feature tag必須、relation indexを入れません。

### Step 2: Suite → Regression Activity

```text
Regression対象範囲
→ Suite
→ immutable snapshot
→ full / selected
→ execution route
→ manual / E2E execution
→ activity result
```

SuiteとRun、Run scopeとactual executionを分離できることを確認します。

### Step 3: coverage / E2E route

- Suiteとは独立したtest basisからcoverage
- TC → E2E実装coverage
- partial automation
- TCなしE2E
- many-to-many

### Step 4: Activity history / discovery

- fixed pathで十分ならindexを追加しない
- 必要な場合だけ最小activity index
- cross-run historyを確認する

### Step 5: relation index必要性gate

direct refでは回答できないqueryを実際に列挙します。

例:

- TC → 過去Regression activity
- testware → 複数release execution
- Finding → follow-up TC → 後続Regression

必要性を確認できたqueryだけ最小relation indexへ追加します。

必要性を確認できなければrelation indexを実装しません。

### Step 6: selected Regression / safety fallback

- user / project policy scope
- PR #11 impact
- Product Risk
- past FAIL / Finding
- query completeness
- safe broadening / block

### Step 7: exploratory-testing / Investigation

- Skill / validator
- browser safety
- activity history
- Finding follow-up

### Step 8: 全体回帰

- 既存Skill
- PR #11 runtime
- PR #12 execution
- E2E
- Suite / Activity
- exploratory-testing
- relation indexを実装した場合だけそのruntime
- CI / runtime smoke

## 5. 実装時に避けること

- current TCを意味判断なしに全件Suiteへ加入させる
- SuiteをTC lifecycleの第二の正本にする
- feature tagをcoverage / membershipの必須条件にする
- Suite自身から「全機能」の母集団を作る
- full scopeと全件実行済みを混同する
- E2E存在だけでmanual不要と判断する
- TCなしE2EへTCを創作する
- PR #11 design graphをPR #13へ複製する
- PR #13独自currentness / `revalidation_required`を作る
- relation indexをQA全体の新基盤にする
- direct refで足りる関係を重複保存する
- LLMへduplicate / dangling / completeness判定を委ねる

## 6. 完了条件

- PR #11 / #12の実契約を正本として再利用している
- current Regression対象範囲がSuiteとは独立して定義される
- 継続Regression対象のTCだけを基準集合へ反映できる
- 一回限りTCを恒常memberへ自動加入させない
- feature tagなしでもSuite / coverageが成立する
- Suite completenessとRun scopeが分離されている
- full / selectedとactual execution件数が分離されている
- logical TCとmanual / E2E execution routeが分離されている
- partial E2Eでlogical TCを誤って実行済みにしない
- TCなしE2Eの既存契約を壊さない
- past activity snapshotを保持できる
- past activityを決定論的に発見できる
- candidate query不完全時に安全側へ処理できる
- PR #11のfreshness / `要再検証`を参照し、独自stateを作らない
- relation indexなしでもRegression / Exploration / Investigation workflowが成立する
- relation indexを追加する場合は実証済みqueryだけを対象にする
- deterministic / semantic / runtime smokeと既存CIがPASSする
