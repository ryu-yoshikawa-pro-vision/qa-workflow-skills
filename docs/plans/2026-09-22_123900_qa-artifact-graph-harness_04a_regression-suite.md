# Regression / Exploratory Testing 統合Plan

## 1. Regression Suiteの位置づけ

Regression Suiteは、current Regression対象範囲を継続的に検証するためのcurrentかつ再利用可能なlogical TCの基準集合です。

全current TCの履歴保管庫にはしません。

Suiteのmembership判断とRun利用は`regression-testing`が担当します。

## 2. Regression対象範囲

母集団はSuite自身から作りません。

入力:

- project context §3のtest level / 対象機能 / role / 業務フロー
- current仕様根拠
- current Product Risk / test objective
- currentness確認済みの関連QA knowledge refs / revisions
- project context §8の非機能テスト範囲
- project context §11の対象外

`regression-testing`はこれらのcurrent成果物を参照しますが、仕様分析やProduct Riskの新規評価・再採点を行いません。

必要に応じて`coverage-analysis`へ次の閉鎖確認を依頼します。

```text
current Regression test basis
→ specification / Risk
→ TR
→ TCN / CI
→ current TC
→ Regression Suite
```

## 3. membership

member条件:

- PR #11上でcurrentなlogical TC
- current Regression対象範囲内
- 継続的に再検証する意味がある

one-off migration、調査専用、一時確認等はcurrent TCでも恒常memberにしない場合があります。

高コスト、特殊環境、manualであることだけを除外理由にしません。

membership判断は`regression-testing`が所有します。

判断結果はTC ref、理由、判断に使用したsource refs / revisionsとともに保持します。

## 4. initial baseline

最初にauthoritative discovery snapshotを固定します。

snapshot:

- discovery roots
- source refs / revisions
- 発見TC refs
- deterministic ordering
- 判定済み / 未判定refs
- completeness

`regression-testing`はこのsnapshot内の全current TCをmembership判定します。

### 大量TC

1回で全件を処理できない場合は同じsnapshotをdeterministicなbatchへ分割できます。

- 未判定TCが残る間は`complete=false`
- resumeは同じsnapshotを使用する
- snapshot source revisionが変わった場合は旧作業へ追加せず、新snapshotで再評価する

### legacy TC

TCを発見済みでもPR #11 current lifecycleへ解決できない場合:

- discovery自体は成功として保持する
- overall baseline completeは成立させない
- `regression-testing`が独自にTC identity / lifecycleを修復しない
- PR #11側のlegacy昇格または該当design Skillへroutingする
- 正規化後にbaselineを再評価する

traceability不足によるcoverage gapはinventory欠落と分離します。

## 5. Suiteの保持方法

### current TC + membershipを再構成できる場合

Suiteは派生viewにします。

persistするのは必要なRegression固有情報だけです。

- Regression対象範囲ref / revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

### 再構成できない場合

project-local Suite artifactへmember refを保持します。

TC本文、freshness、deleted / superseded相当の判定はPR #11を正本とします。

## 6. membership再評価

trigger:

- TC lifecycle / content
- Regression対象範囲
- project contextのRegression方針
- relevant Product Risk / test objective
- one-off / 対象外判断根拠

PR #11 change impact / traceabilityで安全に限定できる場合は影響TCだけ再評価します。

限定できなければcurrent TC全体を再確認します。

E2E mapping変更だけではmembershipを自動変更しません。必要なexecution routeを再評価します。

## 7. Run開始前currentness

各Runのbaseline snapshot確定前に、保存済みmembership sourceとcurrent sourceを照合します。

確認:

- discovery snapshot / source revisions
- project context revision
- current Regression対象範囲
- relevant Risk / test objective revisions
- PR #11 current lifecycle / `要再検証`

差分がある場合は必要範囲をreconcileしてからRun snapshotを確定します。

baseline completeness / currentnessを確認できない状態で`full`と宣言しません。

## 8. feature tag / filter

feature tagは任意のhuman-friendly filterです。

- 既存分類がある場合だけ再利用
- cross-feature TCを許容
- renameでTC identityを変更しない
- tagなしをmembership / coverage failureにしない
- hierarchyを新設しない

coverageの正本にはしません。

## 9. Full / Selected Run

`regression-testing`がRun scopeを決めます。

優先順位:

1. user明示scope
2. project contextのRegression方針
3. 未定義なら安全側のfull fallback

### full

`complete=true`かつcurrentness確認済みのbaseline snapshot全TC memberをselectedにします。

baselineがincompleteの場合、見つかったmember全件をselectedにしても「full Regression」とは扱いません。

project contextでfull対象と明示されたTCなし補助testwareは別枠で追加できます。

### selected

PR #11 impact、current Product Risk、past FAIL / Finding、currentness確認済みの関連QA knowledge、明示TC / filter等を入力にcandidate / selected / excluded / rationaleを決定します。

`test-analysis`へRun selection責務を追加しません。

selected RunをSuite全体のRegression完了と扱いません。

## 10. residual risk

`regression-testing`はProduct Riskを新規識別・再採点しません。

Activityで示すresidual riskは、currentな既存Risk等に対して、

- excluded
- blocked
- unexecuted
- coverage gap

によって今回のRunで十分にmitigateできていない範囲を参照して示すものです。

新しいRiskの識別やimpact / likelihood変更が必要なら`test-analysis`へroutingします。

## 11. required execution route

selected logical TCごとに「今回何を実行する必要があるか」を固定します。

required routeに含められるもの:

- manual
- 具体的なE2E testware ref
- manual + 1件以上のE2E testware ref

`未実行` / `blocked` / `判定不能`はroute種別にしません。

TC→E2E実装の十分性が必要な場合、`coverage-analysis`の結果を参照します。

E2Eが存在するだけでmanual不要と判断しません。

## 12. route実行状態とlogical TCのexecuted

routeごとの開始状態 / resultはPR #12 / E2E source executionを正本とします。

manual相当ではPR #12の正規契約に従い、最初の`scenario.when`操作開始前は`未実行`です。preflight blockでartifactが作られただけではexecutedにしません。

E2Eもmerge後のsource契約でactual attempt開始を確認します。

logical TCをexecutedとして数える条件:

- required routeすべてでsource契約上の実行開始が確認できる

したがって:

- 1 routeでも未開始ならTC全体をexecuted countへ入れない
- blockedは未開始routeの状態として別に保持する
- FAIL / 判定不能でも実際に開始済みなら「実行した」事実とは両立する
- 1 executionが複数TCをcoverする場合は同一execution refを共有できる
- 1 TCに複数required E2Eがある場合は全routeを追跡する

## 13. TCなしE2E

参加条件:

- user明示
- project contextのRegression方針に補助testware refがある

heuristicで既存E2Eを全件加入させません。

ActivityではTCとは別に、

- auxiliary selected testware refs
- auxiliary execution refs
- auxiliary started / unstarted / blocked
- source result refs

を保持します。

TC member count / TC-based coverageへ算入しません。

## 14. Regression Activity

`regression-testing`が生成・更新します。

最低限:

- activity ref
- activity state
- project context ref / revision
- baseline / discovery snapshot ref / revision
- selection input refs / revisions
- member snapshot refs
- run scope
- candidate / selected / excluded TC refs
- auxiliary selected testware refs
- selection rationale
- query completeness
- residual risk refs / reason
- required execution routes
- routeごとのexecution ref
- routeごとのsource開始状態
- routeごとのsource result / outcome
- TC executed / unexecuted / blocked集計
- source resultから安全に投影できるPASS / FAIL / 判定不能等の集計
- unresolved

source execution resultを再判定しません。

TC本文やPR #12 snapshot本文を複製しません。

## 15. Activity lifecycle

state値は既存`qa-workflow`語彙を再利用します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

Regression Activityのdomain stateは`regression-testing`が判断します。

`qa-workflow`は独立に同じ状態を計算せず、workflow stateへ反映します。

- scope / baseline snapshot不変 → 同じActivityを再開可能
- scope / snapshot変更 → 別Activity / version
- 完了後 → immutable

全TC PASSをActivity完了条件と同一視しません。

## 16. candidate不完全時

candidate queryが`complete=false`の場合、candidateだけでscopeを狭めません。

1. user明示scopeを維持
2. current test basisから対象範囲を確定できればその範囲へ拡張
3. 対象範囲も確定できなければ、complete baselineがある場合のみfullへ拡張
4. complete baselineもない場合は必要範囲をblockする

候補0件をRegression不要と解釈しません。

## 17. 責務

| 処理 | 担当 |
| --- | --- |
| 新規・改修の変更影響候補 / Product Risk | `test-analysis` |
| TC設計 | `test-case-design` |
| design traceability / impact / freshness | PR #11 runtime |
| Regression baseline / membership / Run selection / Activity | `regression-testing` |
| Regression対象範囲のcoverage検証 | `coverage-analysis` |
| TC → E2E実装coverage検証 | `coverage-analysis` |
| workflow orchestration | `qa-workflow` |
| manual相当実行・既存TCの修正確認 | `test-execution` |
| E2E実行 | `e2e-test-execution` |
| E2E failure分析 | `e2e-test-result-analysis` |
