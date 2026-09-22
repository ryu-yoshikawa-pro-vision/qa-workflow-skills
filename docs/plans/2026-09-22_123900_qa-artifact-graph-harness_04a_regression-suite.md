# Regression Suite / QA Activity 統合Plan

## 1. Regression Suiteの位置づけ

Regression Suiteは、**現在のRegression対象範囲を継続的に検証するための、currentかつ再利用可能な論理Test Caseの基準集合**です。

Suiteを全TCの履歴保管庫にしません。

各新規・改修セッションではSuiteを見直しますが、current TCを機械的に全件加入させません。

## 2. Regression対象範囲

Suiteの完全性を判定する母集団はSuite自身から作りません。

入力:

- project context §3のtest level / 対象機能 / role / 業務フロー
- current仕様根拠
- Product Risk
- project context §8の明示された非機能テスト範囲
- project context §11の対象外

`coverage-analysis`はこの独立したtest basisから、既存traceabilityを使ってSuite memberへ閉じているか確認します。

```text
current Regression test basis
→ specification / Risk
→ TR
→ TCN / CI
→ current TC
→ Regression Suite
```

Activityは当時利用したproject context ref / revisionと必要なbasis source refs / revisionsを固定します。

独立したRegression scope state machineは作りません。

## 3. Suite membership

member条件:

- PR #11上でcurrentな論理TCである
- 現在のRegression対象範囲に属する
- 今後の変更後にも繰り返し検証する意味がある

one-off migration、調査専用、一時確認等はcurrent TCでも恒常memberにしないことがあります。

実行コストが高い、特殊環境が必要、manualであることだけをmembership除外理由にしません。

membershipの意味判断は`test-analysis`が担当し、`qa-workflow`は判断結果とsource ref / revisionを記録します。

## 4. 初回baseline

PR #13初回導入時は、current Regression対象範囲に関係するauthoritative TC sourceをproject-wideに列挙し、全current TCを一度membership判定します。

成立条件:

- discovery rootが明示されている
- current対象scopeに属するauthoritative TC sourceを完全に列挙できる
- PR #11 lifecycleでcurrent TCを確定できる
- membership判断が全current TCについて閉じる
- `coverage-analysis`でcurrent Regression対象範囲がmember TCへ閉じる

いずれかを満たせない場合、baselineをfull / completeとして扱いません。

## 5. Suiteの保持方法

### current TC + membershipを再構成できる場合

Suiteは派生viewとします。

必要な追加情報だけ保持します。

- Regression対象範囲ref / source revision
- TC refごとのmembership判断
- membership source refs / revisions
- 一時検証 / 対象外理由
- optional filter

### 再構成できない場合

project-localなSuite artifactへmember refを保持します。

それでもTC本文、freshness、deleted / superseded判定はPR #11を正本とします。

## 6. membership再評価

次の変更をtriggerにします。

- TC lifecycle / content
- current Regression対象範囲
- project contextのRegression方針
- membership判断に利用したProduct Risk / test objective
- one-off / 対象外判断の根拠

PR #11 change impact / existing traceabilityで影響TCを安全に限定できる場合はその範囲だけ再評価します。

限定できない場合は古いmembershipを維持せずcurrent TC全体を再確認します。

専用freshness stateは追加しません。

## 7. feature tag / filter

feature tagは任意のhuman-friendly filterです。

- projectに既存の機能分類がある場合だけ再利用できる
- 1 TCに複数tagを付けてもよい
- cross-feature TCを許容する
- renameでTC identityを変更しない
- tagがないことだけでmembership / coverageをblockしない
- hierarchyはv1で追加しない

feature指定Regressionを要求されたのにfilterとcurrent scopeのmappingを確定できない場合だけ、そのselected scopeをblockまたは安全側へ拡張します。

coverageはtagではなく既存traceabilityを正本とします。

## 8. add / update / remove

- stable TC IDが維持された変更 → 同じmember refとしてcurrent sourceを更新
- 新規TC → membership判断後に追加
- split / merge → PR #11のidentity / lifecycle判断に従う
- deleted / superseded相当 → current Suiteから外す
- 今回の成果物に存在しないだけ → 削除しない
- Regression対象範囲の変更 → 影響TCのmembershipを再評価
- membership sourceを安全に特定できない → current TC全体を再確認

過去Regression Activity snapshotはcurrent Suite更新で書き換えません。

## 9. Full / Selected Run

### scope決定

1. ユーザーが明示したscope
2. project contextのRegression方針
3. 未定義なら安全側fallbackとしてfull

### full

snapshot時点の全TC memberをselectedにします。

project contextでfull対象と明示されたTCなし補助testwareがある場合は、TC memberとは別枠で対象に加えます。

`full`はscopeの意味であり、全対象を実際に実行済みという意味ではありません。

### selected

feature filter、明示TC、PR #11 impact、Product Risk、過去FAIL / Finding等からTC subsetを選べます。

TCなし補助testwareはユーザーまたはproject contextで今回scopeへ明示された場合だけ加えます。

`test-analysis`が意味上のselectionを行い、candidate / selected / excluded / rationale / residual riskをActivityへ残します。

selected RunをSuite全体のRegression完了として扱いません。

## 10. execution route

selected logical TCごとに今回requiredなexecution routeを固定します。

- manual
- 1件以上のE2E testware
- manual + E2E
- 未実行 / blocked

E2E存在だけでmanual不要と判断しません。

`coverage-analysis`（`TC → E2E実装`）で今回の検証責務を満たすrouteを判断します。

### completion

- required routeがすべて実executionへ閉じた場合だけlogical TCをexecutedとして数える
- required routeの一部が未実行 / 開始不能ならlogical TCをexecuted countへ入れない
- FAIL / 判定不能は「実行した」事実として扱えるがPASSとは別
- blocked / unresolvedは別集計する
- 同一E2E executionが複数TCをcoverする場合は1回だけ実行し、複数TCから同じexecution refを参照する
- 1 TCに複数required testwareがある場合は全required routeを追跡する

PR #13でsource execution resultを再判定しません。

## 11. TCなしE2E

TCなしE2EをRegressionへ参加させる正本は次だけです。

- user明示
- project contextのRegression方針に明示された補助testware ref

heuristicで既存E2Eを全件加入させません。

ActivityではTCとは別に、

- auxiliary selected testware refs
- auxiliary execution refs
- auxiliary executed / unexecuted / blocked count

を保持できます。

TC member count、TC-based coverageには算入しません。

## 12. Regression Activity成果物

最低限:

- activity ref
- activity state
- project context ref / revision
- baseline / scope source refs / revisions
- selection input refs / revisions
- member snapshot refs
- run scope: `full` / `selected`
- candidate TC refs（selected時）
- selected TC refs
- excluded TC refsと理由
- auxiliary selected testware refs（利用時）
- selection rationale
- query completeness（利用時）
- residual risk
- required execution route refs
- execution refs
- TC executed / unexecuted / blocked集計
- auxiliary testware executed / unexecuted / blocked集計
- unresolved

TC本文のsnapshotをActivityへ複製しません。実行時TC snapshotはPR #12を正本とします。

## 13. Activity lifecycle

既存`qa-workflow`状態語彙を再利用します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

scope / baseline snapshotが不変なら同じactivityを再開できます。

scope / baseline snapshotを変更する場合は別activity / versionとして扱います。

完了後はimmutableです。

## 14. candidate不完全時

candidate queryが`complete=false`の場合、そのcandidateだけでscopeを狭めません。

1. ユーザー明示scopeがあれば維持する
2. current test basisから対象範囲を確定できるなら、その範囲のSuite memberまで広げる
3. 対象範囲も確定できなければfullへ広げる、または必要範囲をblockする

候補0件だけを根拠にRegression不要と判断しません。

## 15. 責務

| 処理 | 担当 |
| --- | --- |
| TC設計 | `test-case-design` |
| design traceability / impact / freshness | PR #11 runtime |
| 継続Regression対象かの意味判断 | `test-analysis` |
| Regression対象範囲の意味上coverage | `coverage-analysis` |
| initial baseline / Suite反映 / snapshot / routing | `qa-workflow` |
| TC → E2E実装coverage | `coverage-analysis` |
| manual相当実行 | `test-execution` |
| E2E実行 | `e2e-test-execution` |
| E2E failure分析 | `e2e-test-result-analysis` |
