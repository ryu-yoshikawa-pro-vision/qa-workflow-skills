# Regression / Exploratory Testing 統合Plan

## 1. 目的

PR #11 / #12後に残る課題を、既存の新規・改修Skillへ責務追加せず解決します。

- 新規・改修で作成したcurrent QA成果物を継続Regressionへ接続する
- Regression固有のbaseline / membership / Runを`regression-testing`へ集約する
- 現在のRegression対象範囲をSuite自身とは独立したtest basisから確定する
- project内のcurrent TCを漏れなく発見し、initial baselineとmembership更新を成立させる
- Regressionごとのselection / execution / residual riskをActivityとして残す
- Exploration / Investigationを`exploratory-testing`として独立させる
- release / sessionを跨いで過去Activityを欠落なく発見する

次はPR #13で再実装しません。

- 新規・改修の仕様分析 / Risk分析 / TC設計
- SPEC → TR → TCN → CI → TCのdesign traceability
- design change impact
- freshness / stale / `要再検証`
- TC snapshot
- execution / result / rerun lineage

## 2. 新規・改修とRegressionの境界

既存の新規・改修flowは変更しません。

```text
current仕様
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

このflowが生成するcurrent成果物を`regression-testing`が参照します。

既存Skillへ次を追加しません。

- Regression membership判断
- Regression baseline管理
- full / selected Regression選定
- Regression Activity管理
- Regression Run完了判定

新規・改修でTC / Risk / scope等が変わった場合、`qa-workflow`は変更済み成果物を`regression-testing`の再評価入力としてroutingします。

## 3. 実装開始時の確認

PR #11 / #12 merge後に次を確認します。

1. latest `main`のMachine Entity、traceability、change impact、freshness、execution、rerun契約を取得する。
2. PR #11のcurrent TC identity / lifecycleとproject-wide artifact discoveryを分けて確認する。
3. project contextの「既存QA成果物」またはPR #11側のcanonical inventoryからauthoritative TC sourceを決定論的に列挙できるか確認する。
4. discovery sourceからcurrent TCを抽出し、PR #11 lifecycleでcurrent / deleted / superseded相当を解決できるか確認する。
5. source登録漏れを検出できない場合、project-wide current TC集合をcompleteとみなさない。
6. TC → current E2E testware、execution → TC snapshot / target version / previous executionを確認する。
7. Activityを固定project-relative rootから列挙できるか確認する。
8. relation index前にdirect ref + deterministic scanで必要queryを回答できるか確認する。

## 4. initial baseline

初回利用時は増分更新から始めません。

```text
current Regression対象範囲
→ authoritative TC discovery
→ 全current TC
→ regression-testingによるmembership判断
→ Regression baseline
→ coverage-analysisによる閉鎖確認
```

このreconciliationが完了するまでbaselineをcompleteとして扱いません。

専用migration Skillは追加しません。

## 5. Regression対象範囲

既存`project-context-template.md`を再利用します。

- §3 テスト範囲
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

必要な案件だけ、既存欄と重複しないRegression方針を追加します。

- 既定Run scope / selection方針
- TCなしE2E等の補助testware refs

対象機能、role、業務フロー等をRegression専用欄へ複製しません。

`regression-testing`はproject context、current仕様、Risk等を入力として利用しますが、それらを再分析しません。

## 6. Suite materialization gate

project-wide current TCとRegression membershipを決定論的に再構成できる場合、Suiteは派生viewにします。

必要な追加情報だけ保持します。

- Regression対象範囲ref / source revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

再構成できない場合だけproject-local Suite artifactへmember refを保持します。

TC本文、stable ID lifecycle、freshnessを複製しません。

## 7. membership再評価

`regression-testing`は次の変更を再評価triggerとして扱います。

- TC lifecycle / content
- current Regression対象範囲
- project contextのRegression方針
- relevant Product Risk / test objective
- one-off / 対象外判断の根拠

PR #11 change impact / existing traceabilityで影響範囲を安全に限定できる場合はその範囲だけ再評価します。

限定できない場合は古いmembershipを維持せずcurrent TC全体を再確認します。

## 8. 責務境界

### 新規・改修Skill

current QA成果物を作ります。

Regression固有判断は行いません。

### regression-testing

- initial baseline
- membership / membership再評価
- full / selected
- selection rationale / residual risk
- required execution route
- TCなし補助testware
- Regression Activity
- Run完了判定

### qa-workflow

- 新規・改修 / Regression / Explorationのrouting
- 共通workflow state
- blocked / resumeの共通制御
- 成果物間のhandoff

Regression membershipやselectionを再判定しません。

### coverage-analysis

`regression-testing`の判断を置換せず、指定されたRegression対象範囲やTC→E2Eの意味上coverageを検証します。

### 決定論的補助runtime

- discovery / schema / ref整合
- baseline completeness
- Activity discovery
- execution route closureの構造検査
- query completeness

意味判断は行いません。
