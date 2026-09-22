# Regression / Exploratory Testing 統合Plan

## 1. 目的

PR #11 / #12後に残る課題を、既存の新規・改修SkillへRegression責務を追加せず解決します。

- current QA成果物を継続Regressionへ接続する
- Regression固有のbaseline / membership / Runを`regression-testing`へ集約する
- Suite自身とは独立したtest basisからRegression対象範囲を扱う
- project内のcurrent TCを発見し、initial baselineと以後のmembership更新を成立させる
- 古いbaselineを後日のRunで黙って再利用しない
- Regressionごとのselection / execution / source result / residual riskを履歴化する
- 修正確認を独立Skillにせず、既存TCが有効ならexecutionへ直接、設計不足がある場合だけ既存analysis / designを経由して実行する
- Exploration / Investigationを`exploratory-testing`として独立させる
- QA活動で得た対象・仕組み・テスト観点・環境の知識を、既存正本を壊さず継続再利用できるようにする
- 複数workflowが同時進行しても、workflow state・共有QA成果物・test environment / dataが混線しないようにする

PR #13で再実装しないもの:

- 新規・改修の仕様分析 / Product Risk分析 / TC設計
- SPEC → TR → TCN → CI → TCのdesign traceability
- design change impact
- freshness / stale / `要再検証`
- TC snapshot
- execution / result / rerun lineage

## 2. 新規・改修とRegressionの境界

既存flowはcurrentなQA設計を作ります。

```text
current仕様
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

`test-analysis`が扱う「回帰影響候補」は変更・Risk分析の一部です。

```text
変更影響候補 / Product Risk
→ test-analysis

既存Regression baselineから今回実行するTCを確定
→ regression-testing
```

この境界をtrigger / semantic evalでも維持します。

## 3. 新規・改修からRegressionへのhandoff

既存設計Skill自身はSuiteを更新しません。

次のいずれかを満たすworkflowでは、`qa-workflow`が変更成果物を`regression-testing`へhandoffします。

- projectでcurrent Regression baseline / policyを運用している
- ユーザーがRegression資産の更新まで要求している
- end-to-end QA workflowとしてRegressionまで要求されている

membership判断入力に影響する変更:

- TC lifecycle / content
- Regression対象範囲
- project contextのRegression方針
- relevant Product Risk / test objective
- one-off / 対象外判断の根拠

これらが変わった場合、`qa-workflow`上の`regression-testing | baseline / membership`を`要再検証`として扱い、次回Run開始前までにreconciliationを必須とします。

設計成果物の完成とRegression reconciliationの完成は分離できます。単体Skill利用でRegression更新を強制しません。ただしbaseline運用中のprojectで古いbaselineをcurrent扱いしません。

E2E mappingの変更は通常membership変更ではなくrequired execution route再評価要因です。TCの意味やRegression対象範囲自体が変わらない限り、mapping変更だけでmembershipを変えません。

## 4. Run開始時のbaseline currentness確認

handoff漏れや別sessionの変更があっても古いbaselineでRunを開始しないよう、各Runのsnapshot確定前に次を現在値と照合します。

- baselineが参照するauthoritative TC discovery snapshot / source revisions
- project context ref / revision
- current Regression対象範囲
- membership判断に使用したRisk / test objective等のsource refs / revisions
- PR #11のcurrent TC lifecycle / change impact / `要再検証`状態

差分があれば、PR #11 impact / traceabilityで安全に限定できる範囲をreconcileします。限定できない場合はcurrent TC全体を再確認します。

baseline currentnessを確認できない場合、Run scopeをfullと呼んで開始しません。

## 5. initial baseline

初回利用時は増分更新から開始しません。

最初にauthoritative discovery snapshotを固定します。

```text
current Regression対象範囲
→ authoritative TC discovery roots
→ source revisionを含むdiscovery snapshot
→ current TC candidate集合
→ membership判断
→ baseline
→ coverage-analysis
```

### 中断・再開

TC数が1回の処理量を超える場合、同じdiscovery snapshotをdeterministicな順序で複数batchへ分割できます。

最低契約:

- discovery snapshot自体を途中で差し替えない
- 判定済み / 未判定TC refを区別する
- 未判定TCが1件でも残る間は`complete=false`
- resumeは同じdiscovery snapshotから続行する
- snapshot sourceが変更された場合は旧baseline作業を履歴として閉じ、新しいsnapshotで再評価する

専用migration Skillやqueue frameworkは追加しません。

### legacy / 不完全TC

次を別々に判定します。

1. authoritative sourceからTCを発見できたか
2. PR #11上でcurrent / deleted / superseded相当を解決できるか
3. membershipを判断できるか
4. current Regression test basisからcoverageが閉じるか

TCを発見済みでもPR #11 lifecycleへ解決できない場合、discovery欠落とは扱いませんがcomplete baselineは成立させません。`regression-testing`がTCを独自修復せず、PR #11側のlegacy昇格または該当design Skillへroutingし、正規化後に再評価します。

traceability不足でcoverageが閉じない場合はcoverage gapとして扱い、inventory欠落と混同しません。

## 6. Regression対象範囲

既存`project-context-template.md`を再利用します。

- §3 テスト範囲
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

必要な案件だけ、既存欄と重複しないRegression方針を追加します。

- 既定Run scope / selection方針
- TCなしE2E等の補助testware refs

対象機能、role、業務フロー等をRegression専用欄へ複製しません。

`regression-testing`はproject context、current仕様、Risk等を入力として利用しますが、それらを再分析・再採点しません。

## 7. Suite materialization gate

project-wide current TCとpersistしたmembership判断からcurrent Suiteを決定論的に再構成できる場合、Suiteは派生viewにします。

保持するRegression固有情報:

- Regression対象範囲ref / revision
- TC refごとのmembership判断
- membership source refs / revisions
- one-off / 対象外理由
- optional filter

再構成できない場合だけproject-local Suite artifactへmember refを保持します。

TC本文、stable ID lifecycle、freshnessを複製しません。

## 8. membership再評価

再評価trigger:

- TC lifecycle / content
- current Regression対象範囲
- project contextのRegression方針
- relevant Product Risk / test objective
- one-off / 対象外判断根拠

PR #11 change impact / traceabilityで安全に限定できる場合はその範囲だけ再評価します。

限定できない場合はcurrent TC全体を再確認します。

## 9. 責務境界

### 新規・改修Skill

current QA成果物を作ります。Regression固有判断は行いません。

### regression-testing

- baseline / membership
- Run計画
- required execution route
- Run結果更新
- history

### qa-workflow

- 活動間routing
- 修正確認 + Regression等の複合workflow
- 共通workflow state
- blocked / resume
- 成果物間handoff

Regression membershipやRun selectionを独立再計算しません。

### coverage-analysis

指定されたRegression対象範囲やTC→E2Eの意味上coverageを検証します。membership / selectionの判断主体にはしません。

### 決定論的補助runtime

- discovery snapshot / completeness
- schema / ref整合
- batch progress整合
- Activity discovery
- execution route closureの構造検査
- query completeness

意味判断は行いません。
