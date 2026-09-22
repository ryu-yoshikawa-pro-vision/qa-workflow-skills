# Regression / Exploratory Testing 統合Plan

## 1. 決定論的補助runtimeの位置づけ

補助runtimeはRegression固有の機械処理を支援しますが、user-facingな判断主体は`regression-testing`です。

補助runtimeへ意味判断を移しません。

必要な処理:

- current TC discovery / baseline completeness
- Suite / Regression Activity validation
- membership / source ref整合
- execution route closureの構造検査
- Activity discovery
- direct ref + deterministic scan
- 必要性を実証した場合だけrelation index build / query

## 2. 配置方針

Regression固有runtime / templateは`qa-workflow`配下へ置かず、`skills/regression-testing/`配下を第一候補とします。

予定:

```text
skills/regression-testing/
├── SKILL.md
├── references/
│   └── guidance.md
├── assets/
│   ├── regression-suite-template.md
│   └── regression-activity-template.md
└── scripts/
    ├── validate_regression_artifact.py
    └── discover_regression_artifacts.py
```

relation indexが不要ならindex builder / query scriptは追加しません。

## 3. current TC discovery

PR #11 merge後、identity / lifecycleとartifact discoveryを分けて確認します。

discovery root:

1. PR #11 merge後にproject-wide current TCを完全列挙できるcanonical inventoryがあれば再利用
2. なければproject contextの「既存QA成果物」にauthoritative TC成果物を列挙

current Regression対象範囲に関係するTC sourceを完全列挙できない場合、baseline completenessをtrueにしません。

汎用artifact registryは作りません。

## 4. Suiteの保持方法

### current TCとmembershipを再構成できる場合

Suiteは派生viewにします。

保持する必要があるのはRegression固有情報だけです。

- Regression対象範囲ref / revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

### 再構成できない場合

project-local Suite artifactへmember refを保持します。

TC本文、stable ID lifecycle、freshnessはPR #11を正本とします。

## 5. Activity discovery

固定project-relative rootを優先します。

固定rootを使える場合:

- indexを追加しない
- deterministic scanでActivityを発見する

固定rootを使えない場合だけproject-local activity indexを追加します。

indexの入口はproject contextの「既存QA成果物」から一意に参照できる1件に固定します。

Activity artifact保存とindex登録の両方が成功するまで保存完了にしません。

## 6. validator

### Regression Activity

- baseline / scope source ref / revision
- selection input ref / revision
- selected refsがsnapshot内にある
- fullの場合はsnapshot全memberをselectedにしている
- auxiliary TC-free testwareをTC countへ混ぜない
- selected TCごとのrequired route
- required routeとexecution refの対応
- executed / unexecuted / blockedとPASS / FAILを混同していない
- 完了後Activityを変更していない

### Suite / baseline

- duplicate member ref
- deleted / superseded相当をcurrent memberとして利用していない
- memberがPR #11 current TCへ解決できる
- membership source ref / revisionを辿れる
- feature tag不存在だけでは失敗にしない

### Exploration / Investigation

Exploration固有validatorは`exploratory-testing`側へ置きます。Regression runtimeへ混在させません。

## 7. execution route closure

`regression-testing`がselected logical TCごとにrequired routeを固定します。

route:

- manual
- 1件以上のE2E testware
- manual + E2E
- 未実行 / blocked

required routeの決定時、既存`coverage-analysis`によるTC→E2E実装coverage結果を参照できます。

executed判定:

- required routeが1件でも未実行 / 開始不能ならlogical TCをexecuted countへ入れない
- required routeがすべてexecution artifactへ閉じた場合にexecutedと数える
- FAIL / 判定不能と「実行したか」を分離する
- 1 executionが複数TCをcoverする場合は同一execution refを共有する
- 1 TCに複数required testwareがある場合は全routeを追跡する

source execution resultを再判定しません。

## 8. TCなしE2E

Regression参加条件:

- user明示
- project contextのRegression方針で補助testwareとして明示

TC memberとは別にselected / executed / blockedを集計し、TC-based coverageへ算入しません。

## 9. Activity lifecycle

Regression Activityの生成・更新・完了判定は`regression-testing`が担当します。

state値は既存`qa-workflow`語彙を再利用します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

scope / baseline snapshot不変なら同じactivity_refで再開できます。

scope / snapshot変更時は別Activity / versionとします。

完了後はimmutableです。

## 10. relation index gate

direct ref + deterministic scanで回答不能、またはscan costが実測要件を満たさない場合だけrelation indexを実装します。

design lifecycle / currentnessをPR #13へ持ち込みません。

## 11. versioning

persistするSuite metadata / Regression Activity machine blockにはschema versionを持たせます。

relation indexを実装しない場合、Graph schema versionやHarness contract versionは追加しません。
