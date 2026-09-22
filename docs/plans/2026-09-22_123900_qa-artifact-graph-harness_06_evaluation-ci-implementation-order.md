# Regression Suite / QA Activity 統合Plan

## 1. 評価方針

### deterministic

- project-wide TC discovery completeness
- initial baseline reconciliation
- Suite / Activity schema
- stable ref / artifact-local ref保持
- membership source ref / revision
- full / selected snapshot整合
- required execution route closure
- TC countとTCなし補助testware countの分離
- Activity lifecycle / immutable条件
- Activity discovery completeness
- direct ref / deterministic scan
- relation indexを実装する場合だけ再生成性 / query completeness

### semantic

- 継続Regression対象の判断
- Regression対象範囲変更時のmembership再評価対象
- Suiteとは独立したRegression対象範囲のcoverage
- selected scopeの妥当性
- TC → E2E実装のcoverage
- `test-target-inspection`とInvestigationの責務境界
- Finding classification / follow-up

### runtime smoke

- 既存TCを持つprojectでの初回baseline
- 新規・改修 → membership見直し
- scope変更のみ → membership再評価
- Suite → full Run → manual / E2E
- selected Run
- Activity block / resume / complete
- activity history
- exploratory-testing
- Finding → follow-up

## 2. 必須評価

### TC discovery / initial baseline

- project context等のauthoritative discovery rootから全current TC sourceを列挙できる
- sourceを1件欠落させたfixtureでbaseline completenessがPASSしない
- 既存TC A/B/Cがあり今回Cしか変更していなくても、初回baselineではA/B/Cの必要memberを判断する
- project-wide discoveryを保証できない場合、派生Suiteをfull / completeとして扱わない

### Regression対象範囲 / membership

- Suiteに存在しないcurrent対象責務をcoverage gapとして検出する
- Suite自身からRegression対象範囲を定義しない
- one-off migration TCをcurrentでも恒常memberにしない判断を許容する
- one-off責務自体がcurrent Regression対象範囲に残る場合はcoverage gapを黙らせない
- 調査専用TCを自動加入させない
- stable TC更新でidentityを維持する
- split / mergeはPR #11 lifecycleに従う
- deleted / superseded相当をcurrent memberとして数えない
- 今回の成果物にないだけで既存memberを削除しない
- feature tagがなくてもmembership / coverageを失敗させない
- feature renameでTC identityを変更しない
- TC無変更でもrole / test level / Regression scope / relevant Risk等が変われば影響membershipを再評価する
- membership影響範囲を限定できない場合はcurrent TC全体を再確認する

### Full / Selected

- user明示scopeを最優先する
- project policyがあれば利用する
- scope未定義時だけfull fallbackする
- fullはsnapshot全TC memberをselectedにする
- selectedはsnapshotのsubsetである
- selectedをSuite全体のRegression完了として扱わない
- 100 selected / 98 executed / 2 unexecutedを「100件実行済み」と表現しない

### manual / E2E route closure

- E2E存在だけでmanual不要と判断しない
- E2EがTCの一部だけをcoverする場合、required routeにmanualまたは追加E2Eを残す
- 1 TC → 2 E2Eで片方未実行ならlogical TCをexecuted countへ入れない
- manual + E2Eで片方未実行ならlogical TCをexecuted countへ入れない
- FAIL / 判定不能をPASSと扱わない一方、実行attempt自体は追跡できる
- 2 TC → 1 E2Eでは同じtestware executionを重複起動せず、両TCから同じexecution refを参照できる
- required routeすべてがexecutionへ閉じた場合だけlogical TCをexecutedとして数える

### TCなしE2E

- TCなしE2EへTC IDを創作しない
- user明示またはproject policyに補助testware refがある場合だけRegressionへ含める
- full Runでも案件方針にないTCなしE2Eを暗黙加入させない
- auxiliary selected / executed countをTC countと分離する
- TC-based coverageへ算入しない

### Activity provenance / lifecycle

- project context ref / revisionを保持する
- selected scope判断に使用したimpact / Risk / Finding等のinput refs / revisionsを保持する
- scope / baseline snapshot不変のblock → resumeは同じactivity refを使える
- scope / snapshot変更時は別activity / versionになる
- 完了後Activityを変更できない
- workflow完了と全TC PASSを混同しない
- past Activity snapshotをcurrent Suite更新で書き換えない

### Activity discovery

- fixed rootから発見可能ならindexなしで全Activityを列挙できる
- index方式の場合、project contextからindexを一意に発見できる
- index方式でActivity保存成功 / index登録失敗を保存完了扱いしない
- indexが存在しないartifact refを指せば失敗
- indexへTC / Result / Finding本文を複製しない

### PR #11 / #12境界

- PR #11のfreshness / `要再検証`を参照し、PR #13独自stateを生成しない
- past PASSをupstream変更だけでFAILへ書き換えない
- PR #12のTC snapshot / execution schemaをActivityへ複製しない
- `source_test_case_id`をglobal identityへしない

### candidate completeness

- discovery source不足 / unsupported / dangling / unmapped等があれば`complete=false`
- `complete=false`の空集合をRegression不要へ変換しない
- candidate不完全時は明示scope維持、current test basisへの拡大、full fallback / blockの順で安全側に扱う

### Exploration / Investigation routing

- current UI情報 / 既知範囲のふるまい収集 → `test-target-inspection`
- 既知TC実行 → `test-execution` / `e2e-test-execution`
- E2E failure → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- 仮説駆動で実対象を探索する必要があり既存責任Skillがない → `exploratory-testing(mode=investigation)`
- Findingを自動Defect化しない
- observationを仕様Authorityへ自動昇格しない

### relation index不要ケース

- TC → past Activityを固定rootのActivity scanだけで回答できるfixtureではrelation indexを要求しない
- deterministic scanで要件を満たす限りrelation indexを実装対象にしない

## 3. CI

実装開始時のPR #11 / #12 merge後CIを正本として追加先を決めます。

予定:

- Skill一覧へ`exploratory-testing`
- project context schema / docs同期
- trigger dataset
- deterministic output eval
- semantic dataset validation
- qa-workflow routing
- Regression Suite / Activity validator
- current TC discovery / initial baseline test
- Activity discovery test
- execution route closure test
- runtime smoke
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
- PR #11にcanonical project-wide TC inventoryが追加されたか確認する
- なければproject contextの既存QA成果物をTC discovery rootとして使えるか確認する
- TC discovery completenessを検証できるか確認する
- current lifecycleをPR #11だけで判断できるか確認する
- TC → E2E、execution historyを確認する
- Activity保存規約を確認する
- PR #11 / #12だけで解けるものをPR #13から除外する

### Step 1: initial baseline

既存current TCを持つfixtureで実証します。

```text
Regression対象範囲
→ authoritative TC discovery
→ 全current TC
→ membership判断
→ baseline
→ coverage-analysis
```

この段階ではGraph / relation indexを実装しません。

### Step 2: membership更新

- TC content / lifecycle変更
- role / function / test level等のRegression scope変更
- relevant Risk / test objective変更
- one-off終了
- impact範囲不明時の全current TC再確認

を検証します。

### Step 3: Suite → Regression Activity

```text
baseline
→ immutable member snapshot
→ full / selected
→ required execution routes
→ manual / E2E execution
→ Activity result
```

Suite、Run scope、actual execution、Resultを分離します。

### Step 4: E2E route / auxiliary testware

- partial automation
- manual + E2E
- 1 TC → 複数testware
- 複数TC → 1 testware
- TCなしE2E
- required route closure

### Step 5: Activity lifecycle / history

- selection provenance
- block / resume
- complete → immutable
- fixed root discovery
- 必要な場合だけactivity index

### Step 6: selected Regression / safety fallback

- user / project policy scope
- PR #11 impact
- Product Risk
- past FAIL / Finding
- query completeness
- safe broadening / block

### Step 7: exploratory-testing / Investigation

- `test-target-inspection`とのrouting境界
- Skill / validator
- browser safety
- Finding follow-up

### Step 8: relation index必要性gate

```text
direct ref
→ discovered artifact deterministic scan
→ 要件を満たすなら終了
→ 実測上不足するqueryだけrelation index
```

relation indexを実装しないことを正常な完了結果として許容します。

### Step 9: 全体回帰

- 既存Skill
- PR #11 runtime
- PR #12 execution
- E2E
- Suite / Activity
- exploratory-testing
- project context
- relation indexを実装した場合だけそのruntime
- CI / runtime smoke

## 5. 実装時に避けること

- TC discoveryの完全性を確認せず「見つかったTC = 全current TC」と扱う
- 初回baselineを増分更新だけで作る
- TC変更時だけmembershipを再評価する
- SuiteをTC lifecycleの第二の正本にする
- feature tagをcoverage / membershipの必須条件にする
- Suite自身からRegression対象範囲を作る
- full scopeと全件実行済みを混同する
- required routeの一部だけでlogical TCをexecuted扱いする
- E2E存在だけでmanual不要と判断する
- TCなしE2EへTCを創作する
- TCなしE2Eを暗黙にfull Regressionへ加入させる
- completed Activityを書き換える
- index登録に失敗したActivityを保存完了扱いする
- `test-target-inspection`の責務をgeneric investigationへ移す
- PR #11 design graphをPR #13へ複製する
- relation indexをreverse lookupがあるだけで導入する

## 6. 完了条件

- project-wide TC discoveryの入口とcomplete判定が決まっている
- 既存projectでinitial baselineを構築できる
- current Regression対象範囲がSuiteとは独立して定義される
- TC変更だけでなくscope / policy / Risk等の変更でもmembershipを適切に再評価できる
- 継続Regression対象のTCだけを基準集合へ反映できる
- feature tagなしでもSuite / coverageが成立する
- Suite completeness、Run scope、actual execution、PASS / FAILが分離されている
- logical TCのrequired execution route closureが一意に判定できる
- TCなしE2Eを明示方針だけで補助testwareとして扱える
- selection input refs / revisionsから当時のscope判断を再現できる
- Activityのblock / resume / complete / immutable境界が一意である
- past Activityを欠落なく決定論的に発見できる
- `test-target-inspection`とInvestigationのroutingが競合しない
- candidate query不完全時に安全側へ処理できる
- relation indexなしでも主workflowが成立する
- relation indexを追加する場合はdirect ref + deterministic scanでは不足した実証済みqueryだけを対象にする
- deterministic / semantic / runtime smokeと既存CIがPASSする
