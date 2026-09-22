# Regression / Exploratory Testing 統合Plan

## 1. 決定論的補助runtimeの位置づけ

補助runtimeは機械判定可能な整合性だけを担当します。

user-facingな意味判断は`regression-testing` / `exploratory-testing`へ残します。

必要な処理:

- current TC discovery snapshot
- initial baseline progress / completeness
- Suite / Regression Activity validation
- membership / source ref整合
- required execution routeとsource execution stateの整合
- Activity discovery
- direct ref + deterministic scan

relation index runtimeはgateを通るまで追加しません。

## 2. 配置方針

Regression固有runtime / templateは`skills/regression-testing/`配下を第一候補とします。

予定:

```text
skills/regression-testing/
├── SKILL.md
├── references/
│   └── guidance.md
├── assets/
│   ├── regression-suite-template.md
│   └── regression-activity-template.md
├── evals/
└── scripts/
    ├── validate_regression_artifact.py
    └── discover_regression_artifacts.py
```

既存Skill評価runtimeで表現できるvalidatorは既存の`evals/deterministic/validator.py`を優先し、user-facing runtime用scriptを重複させません。

Exploratory Testing固有契約は`skills/exploratory-testing/`に置き、Regression runtimeへ混在させません。

## 3. current TC discovery snapshot

PR #11 merge後、identity / lifecycleとartifact discoveryを分けて確認します。

discovery root:

1. PR #11 merge後にproject-wide current TCを列挙できるcanonical inventoryがあれば再利用する
2. なければproject contextの「既存QA成果物」をauthoritative sourceの入口にする

initial baseline開始時に、次を含むdiscovery snapshotを固定します。

- discovery roots
- source refs / revisions
- 発見したTC refs
- deterministic ordering
- 判定済み / 未判定refs
- completeness

TC数が多い場合、同じsnapshotを複数batchへ分けて処理できます。

全TCのmembershipが閉じるまで`complete=false`です。

source revisionが途中で変わった場合、旧snapshotへ新しいTCを継ぎ足さず、新しいsnapshotでreconciliationを開始します。

## 4. completenessを分解する

少なくとも次を別判定にします。

- discovery completeness: authoritative sourceを列挙できたか
- lifecycle resolvability: 発見TCをPR #11 current stateへ解決できたか
- membership completeness: 全current TCのmembershipが閉じたか
- coverage adequacy: current Regression test basisがmember TCへ意味上閉じるか

legacy TCを発見したがPR #11 lifecycleへ解決できない場合はdiscovery失敗にはしません。一方、current baselineを確定できないためoverall baseline completenessはfalseです。

coverage gapはinventory欠落とは別に保持します。

## 5. Suiteの保持方法

### 再構成できる場合

current TCとpersistしたmembership判断からSuiteを再構成し、派生viewを優先します。

保持するRegression固有情報:

- Regression対象範囲ref / revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

### 再構成できない場合

project-local Suite artifactへmember refを保持します。

TC本文、stable ID lifecycle、freshnessはPR #11を正本とします。

## 6. Regression Activity validator

確認すること:

- baseline / project context / selection inputのsource ref / revisionがある
- selected TCがmember snapshot内にある
- fullの場合、complete baseline snapshotの全memberがselectedである
- incomplete baselineをfullとして確定していない
- TCなし補助testwareをTC countへ混ぜていない
- selected TCごとにrequired execution routeがある
- required routeとsource execution ref / state / resultを辿れる
- execution artifactの存在だけでexecutedへ数えていない
- executed / unexecuted / blockedとsource resultを混同していない
- completed Activityを上書きしていない

## 7. required execution routeと実行状態

required routeは「今回何を実行する必要があるか」だけを表します。

許可する構成:

- manual
- 1件以上の具体的E2E testware ref
- manual + E2E testware ref(s)

`未実行` / `blocked` / `判定不能`はrequired routeの種類にしません。

### source execution state

routeごとにPR #12 / E2Eのsource execution契約を参照します。

manual相当`test-execution`では、PR #12の契約上、最初の`scenario.when`操作を開始した時点が開始済み境界です。preflightだけで成果物が生成されてもexecutedには数えません。

E2Eもmerge後の実契約で実際のattempt開始条件を確認し、preflight block等でartifactだけ存在する状態をexecuted扱いしません。

### logical TCのexecuted

logical TCをexecutedとして数えるのは、今回requiredとした全routeについてsource execution契約上の開始事実が確認できる場合だけです。

- 1 routeでも未開始ならTC全体をexecutedへ入れない
- blockedは未開始routeの状態として別に保持する
- source resultがFAIL / 判定不能でも、開始済みであれば「実行した」事実とは両立する
- 1 executionが複数TCをcoverする場合、同じexecution refを再利用できる
- 1 TCに複数E2E testwareがrequiredなら全routeを追跡する

## 8. source resultの投影

Regression Activityはsource execution resultを再判定しません。

routeごとに少なくとも次へ辿れるようにします。

- execution ref
- source上の開始状態
- source result / outcome
- evidence ref
- cleanup / unresolved（Run完了へ影響する場合）

Activity summaryでPASS / FAIL / 判定不能等を表示する場合、PR #12 / E2E merge後の正規状態から決定論的に投影できる範囲だけ集計します。

独自の別result taxonomyは作りません。

## 9. Activity discovery

固定project-relative rootを優先します。

固定rootを使える場合:

- indexを追加しない
- deterministic scanで全Activityを発見する

固定rootを使えない場合だけproject-local activity indexを検討します。

indexが必要になった場合もproject contextから一意に発見できる入口にし、Activity artifact保存とindex登録の両方が成功するまで保存完了にしません。

## 10. Activity lifecycle

Regression Activityのdomain stateは`regression-testing`が判断します。

state値は既存`qa-workflow`語彙を再利用します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

`qa-workflow`は同じstateを独立計算せず、Regression Activity stateをworkflow stateへ反映します。

- scope / baseline snapshot不変 → 同じActivityを再開可能
- scope / snapshot変更 → 別Activity / version
- 完了後 → immutable

## 11. versioning

persistするSuite metadata / Activity machine blockには必要なschema versionを持たせます。

relation indexを実装しない限りGraph schema versionやrelation schema versionを追加しません。
