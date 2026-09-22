# Regression / Exploratory Testing 統合Plan

## 1. Regression Suiteの位置づけ

Regression Suiteは、現在のRegression対象範囲を継続的に検証するためのcurrentかつ再利用可能なlogical TCの基準集合です。

Suiteを全TCの履歴保管庫にしません。

Suiteの意味判断とRun利用は`regression-testing`が担当します。

## 2. Regression対象範囲

母集団はSuite自身から作りません。

入力:

- project context §3のtest level / 対象機能 / role / 業務フロー
- current仕様根拠
- Product Risk
- project context §8の非機能テスト範囲
- project context §11の対象外

`regression-testing`はこれらのcurrent成果物を参照してRegression対象範囲を扱いますが、新規・改修のRisk分析や仕様分析を再実行しません。

必要に応じて`coverage-analysis`へ、

```text
current Regression test basis
→ specification / Risk
→ TR
→ TCN / CI
→ current TC
→ Regression Suite
```

の閉鎖確認を依頼します。

## 3. membership

member条件:

- PR #11上でcurrentなlogical TC
- current Regression対象範囲内
- 将来も繰り返し検証する意味がある

one-off migration、調査専用、一時確認等はcurrent TCでも恒常memberにしない場合があります。

高コスト、特殊環境、manualであることだけを除外理由にしません。

membership判断は`regression-testing`が所有します。

判断時は既存のcurrent仕様、Risk、test objective、project contextを入力として参照し、それらの意味を再分析しません。

## 4. initial baseline

`regression-testing`は初回利用時にauthoritative TC sourceをproject-wideに列挙し、全current TCをmembership判定します。

成立条件:

- discovery rootが明示されている
- current scopeに属するTC sourceを完全列挙できる
- PR #11 lifecycleでcurrent TCを確定できる
- membership判断が全current TCで閉じる
- 必要なcoverage確認が完了する

満たせない場合、baselineをcompleteとして扱いません。

## 5. Suiteの保持方法

### current TC + membershipを再構成できる場合

Suiteは派生viewにします。

保持するRegression固有情報:

- Regression対象範囲ref / revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

### 再構成できない場合

project-local Suite artifactへmember refを保持します。

TC本文、freshness、deleted / superseded判定はPR #11を正本とします。

## 6. membership再評価

`regression-testing`は次をtriggerに再評価します。

- TC lifecycle / content
- Regression対象範囲
- project contextのRegression方針
- relevant Product Risk / test objective
- one-off / 対象外判断根拠

PR #11 change impact / traceabilityで安全に限定できる場合は影響範囲だけ再評価します。

限定できなければcurrent TC全体を再確認します。

## 7. feature tag / filter

feature tagは任意のhuman-friendly filterです。

- 既存の機能分類がある場合だけ再利用
- cross-feature TCを許容
- renameでTC identityを変更しない
- tagなしをmembership / coverage failureにしない
- hierarchyを追加しない

coverageの正本にはしません。

## 8. add / update / remove

- stable TC ID更新 → 同じmember ref
- 新規TC → `regression-testing`がmembership判断
- split / merge → PR #11 lifecycleに従う
- deleted / superseded → current Suiteから外す
- 今回の成果物にないだけ → 削除しない
- Regression scope変更 → 影響TCを再評価
- 影響範囲不明 → current TC全体を再確認

過去Regression Activity snapshotは書き換えません。

## 9. Full / Selected Run

`regression-testing`がRun scopeを決めます。

優先順位:

1. user明示scope
2. project contextのRegression方針
3. 未定義なら安全側のfull fallback

### full

snapshot時点の全TC memberをselectedにします。

project contextでfull対象と明示されたTCなし補助testwareは別枠で追加できます。

### selected

PR #11 impact、Product Risk、過去FAIL / Finding、明示TC / filter等を入力に`regression-testing`がcandidate / selected / excluded / rationale / residual riskを決定します。

`test-analysis`へRegression selection責務を追加しません。

selected RunをSuite全体のRegression完了と扱いません。

## 10. execution route

`regression-testing`がselected TCごとのrequired routeを決定します。

- manual
- 1件以上のE2E testware
- manual + E2E
- 未実行 / blocked

TC→E2E実装の十分性が必要な場合、`coverage-analysis`の結果を参照します。

E2E存在だけでmanual不要としません。

### completion

- required routeがすべてexecutionへ閉じた場合だけlogical TCをexecutedとして数える
- 一部未実行 / 開始不能ならexecuted countへ入れない
- FAIL / 判定不能と「実行したか」を分離
- 1 executionが複数TCをcoverする場合は同一refを共有
- 複数required testwareは全routeを追跡

source execution resultを再判定しません。

## 11. TCなしE2E

参加条件:

- user明示
- project contextのRegression方針に補助testware refがある

heuristicで既存E2Eを全件加入させません。

ActivityではTCとは別に、

- auxiliary selected testware refs
- auxiliary execution refs
- auxiliary executed / unexecuted / blocked count

を保持します。

TC count / TC-based coverageへ算入しません。

## 12. Regression Activity

`regression-testing`が生成・更新します。

最低限:

- activity ref
- activity state
- project context ref / revision
- baseline / scope source refs / revisions
- selection input refs / revisions
- member snapshot refs
- run scope
- candidate / selected / excluded TC refs
- auxiliary selected testware refs
- selection rationale
- query completeness
- residual risk
- required execution route refs
- execution refs
- TC executed / unexecuted / blocked
- auxiliary executed / unexecuted / blocked
- unresolved

TC本文やPR #12 snapshot本文を複製しません。

## 13. Activity lifecycle

状態値は既存`qa-workflow`の語彙を再利用しますが、Regression Activityの状態判断は`regression-testing`が担当します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

scope / baseline snapshot不変なら同じactivityを再開できます。

scope / snapshot変更時は別Activity / versionです。

完了後はimmutableです。

## 14. candidate不完全時

candidate queryが`complete=false`の場合、`regression-testing`はcandidateだけでscopeを狭めません。

1. user明示scopeを維持
2. current test basisから対象範囲を確定できればその範囲へ拡張
3. 対象範囲も確定できなければfullへ拡張、またはblock

候補0件をRegression不要と解釈しません。

## 15. 責務

| 処理 | 担当 |
| --- | --- |
| 新規・改修のRisk / test objective | `test-analysis` |
| TC設計 | `test-case-design` |
| design traceability / impact / freshness | PR #11 runtime |
| Regression baseline / membership / selection / Activity | `regression-testing` |
| Regression対象範囲のcoverage検証 | `coverage-analysis` |
| TC → E2E実装coverage検証 | `coverage-analysis` |
| workflow routing | `qa-workflow` |
| manual相当実行 | `test-execution` |
| E2E実行 | `e2e-test-execution` |
| E2E failure分析 | `e2e-test-result-analysis` |
