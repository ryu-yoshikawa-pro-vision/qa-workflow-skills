# Regression / Exploratory Testing 統合Plan

## 1. regression-testingの目的

`regression-testing`は、既存のcurrent QA成果物を継続Regressionへ接続し、Regression固有のbaseline / membership / Run計画 / Activity / historyを管理するuser-facing Skillです。

新規・改修の仕様分析、Product Risk評価、TC設計、実対象操作は担当しません。

## 2. 起動する要求

### 単体で開始できる

- Regression baselineを初期構築 / 更新したい
- Regression membershipを確認 / 再評価したい
- 今回のRegression対象を選びたい
- full / selectedのRun計画を作りたい
- 過去のRegression Activityを確認したい
- Regressionのblocked / unexecuted / residual riskを確認したい

### qa-workflowから開始する

manual / E2E実行まで含むend-to-end要求:

- Regressionを実施して
- full Regressionを実施して
- 選定から実行・結果まで進めて
- 不具合修正を確認し、周辺Regressionもして

この場合、`qa-workflow`が複数Skillを接続します。

### routingしない

- 新規機能 / 変更機能のProduct Risk分析
- 変更による回帰影響候補の分析
- TR / TCN / CI / TC設計
- current UIの事実収集
- 既知TCの実操作そのもの
- E2E failure原因分析
- Confirmation executionそのもの
- Exploratory Testing

## 3. qa-workflowの対象 / 実行範囲

同一Skillを複数用途で使用する既存契約に従い、`regression-testing`は次の正規対象を持ちます。

- `baseline / membership`
- `Run計画`
- `Run結果更新`
- `履歴参照`

workflow state、開始Skill / 最終Skill、resume先ではこの値を使用します。

## 4. 入力

利用可能な範囲で次を使用します。

- userのRegression要求 / scope
- project context
- current Regression対象範囲
- authoritative TC discovery root
- PR #11 current TC identity / lifecycle / change impact / freshness
- current Product Risk / test objective
- current TC→E2E mapping
- previous baseline / membership metadata
- previous Regression Activity
- past FAIL / Finding
- user / project policyで明示されたTCなし補助testware

入力不足を推測で補いません。

## 5. 出力

### baseline / membership

- discovery snapshot ref / source revisions
- current Regression対象範囲
- member TC refs
- membership判断 / 理由
- membership source refs / revisions
- one-off / exclusions
- 判定済み / 未判定refs
- completeness

### Run計画

- baseline snapshot
- run scope: full / selected
- candidate / selected / excluded
- selection rationale
- selection input refs / revisions
- residual risk refs
- auxiliary testware
- required execution routes

### Run結果更新

- routeごとのexecution ref
- source開始状態
- source result / outcome
- executed / unexecuted / blocked
- source結果の集計
- cleanup / unresolved
- Activity state

## 6. initial baseline

```text
current Regression対象範囲
→ authoritative discovery snapshot
→ PR #11 current lifecycle
→ membership
→ coverage-analysis
→ baseline
```

全TCを漏れなく列挙できる根拠、current lifecycle、membershipが閉じない場合はcomplete baselineとして扱いません。

### batch / resume

TC数が多い場合は同一discovery snapshotをdeterministicに分割できます。

- 未判定TCを保持
- 全件判定まで`complete=false`
- resumeは同じsnapshotを使用
- snapshot source変更時は新snapshotで再評価

専用migration Skillは作りません。

### legacy

発見TCをPR #11 current lifecycleへ解決できない場合、自身でidentity / lifecycleを補修しません。

PR #11側のlegacy昇格または該当design Skillへroutingします。

## 7. membership

membership条件:

- current logical TC
- current Regression対象範囲内
- 継続的に再検証する意味がある

current仕様、Risk、test objectiveを参照しますが、新規分析をやり直しません。

one-off migration、調査専用、一時確認等は恒常memberから外せます。

高コスト / manual / 特殊環境だけを理由に外しません。

## 8. membership再評価 / currentness

trigger:

- TC lifecycle / content
- Regression対象範囲
- project Regression policy
- relevant Risk / test objective
- one-off / 対象外判断

PR #11 impact / traceabilityで安全に限定できる場合は影響TCだけ再評価します。

限定できなければcurrent TC全体を再確認します。

Run開始前にもbaseline source refs / revisionsとcurrent sourceを照合します。handoff漏れがあっても古いbaselineを黙って使いません。

E2E mapping変更はmembershipではなくrequired route再評価へ送ります。

## 9. test-analysisとの境界

```text
変更による回帰影響候補 / Product Risk分析
→ test-analysis

baselineと影響候補等を使って今回実行するTCを確定
→ regression-testing
```

現在の`test-analysis` positive triggerを`regression-testing`へ移しません。

## 10. full / selected

優先順位:

1. user明示scope
2. project policy
3. completeかつcurrentなbaselineがある場合だけfull fallback

### full

currentness確認済みbaseline snapshotの全memberをselectedにします。

### selected

PR #11 impact、current Risk、past FAIL / Finding、明示TC / filter等を入力にcandidate / selected / excludedを決めます。

判断根拠をActivityへ保存します。

## 11. residual risk

Product Riskを新規識別・再採点しません。

residual riskはexisting Risk等を参照し、

- excluded
- blocked
- unexecuted
- coverage gap

によって残る範囲を示します。

Risk自体の追加・impact / likelihood変更が必要なら`test-analysis`へ戻します。

## 12. coverage-analysisとの関係

`coverage-analysis`は検証役です。

必要に応じて:

- current Regression対象範囲 → Suite member TC
- selected scope → selected TC
- TC → E2E実装

の意味上coverageを確認します。

membership / Run selectionの判断主体は`regression-testing`です。

## 13. required execution route

selected TCごとに今回必要な検証手段を固定します。

required route:

- manual
- concrete E2E testware ref(s)
- manual + E2E testware ref(s)

`未実行` / `blocked` / `判定不能`はrouteではありません。

実操作は担当しません。

`qa-workflow`が`test-execution` / `e2e-test-execution`へroutingします。

## 14. execution結果の受け取り

execution artifactの存在だけではexecutedとしません。

source execution契約上の開始事実を確認します。

manual相当ではPR #12の「最初の`scenario.when`操作を開始した時点」を開始境界として利用します。

E2Eはmerge後の正規contractでactual attempt開始を確認します。

routeごとにsource開始状態 / result / evidenceへ追跡します。

## 15. Run結果 / Activity

Activityへsource結果を再判定せず投影します。

最低限:

- route execution ref
- source開始状態
- source result / outcome
- executed / unexecuted / blocked
- PASS / FAIL / 判定不能等の安全に投影できる集計
- cleanup / unresolved
- residual risk refs

全required routeの開始が確認できた場合だけlogical TCをexecutedとして数えます。

全TC PASSをActivity完了条件と同一視しません。

## 16. FAIL / Finding feedback

原因分析を自身で行いません。

execution結果に追加対応が必要なら`qa-workflow`へ戻します。

- E2E異常 → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis` / 必要時`spec-analysis`
- current実対象情報不足 → `test-target-inspection`
- TC問題 → `test-case-design`
- coverage gap → `coverage-analysis`
- owner不明の実対象仮説調査 → `exploratory-testing(mode=investigation)`

修正後はConfirmation executionを行い、QA成果物やbaseline入力が変わった場合はmembership / Run scopeを再評価します。

Finding / FAILを自動Defect化しません。

## 17. Confirmation Testingとの関係

Confirmationは`regression-testing`の内部modeにしません。

既知のFAIL / 再現TCを`test-execution` / `e2e-test-execution`で再実行します。

Confirmation後に周辺影響を確認する必要があれば、別途`regression-testing`でRegression Runを計画します。

## 18. TCなしE2E

参加条件:

- user明示
- project policyで補助testwareとして明示

TCを創作しません。

TC member / coverageとは別集計にします。

## 19. Activity lifecycle

state値は既存`qa-workflow`語彙を使用します。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

Regression Activityのdomain stateは本Skillが判断します。

`qa-workflow`はstateを独立再計算せずworkflowへ反映します。

- scope / snapshot不変 → 同Activityで再開可能
- scope / snapshot変更 → 別Activity / version
- 完了後 → immutable

## 20. history

固定Activity rootからのdeterministic scanを優先します。

history queryだけを理由にGraph / relation indexを必須化しません。

## 21. 新規・改修flowとの関係

新規・改修Skillはcurrent QA成果物を作ります。

Regression運用中のprojectまたはユーザーがRegression資産更新を要求したworkflowでは、membership入力変更を本Skillへhandoffします。

単体Skill利用ではRegression更新を強制しません。

ただしRun開始前currentness checkは常に行います。

## 22. 対象外

- 新規・改修の仕様分析 / Product Risk評価
- TR / TCN / CI / TC設計
- PR #11 impact / freshness再計算
- browser操作
- E2E failure原因分析
- Confirmation executionそのもの
- generic Exploration / Investigation
- Defect reportの生成・登録
- Graphを前提にした履歴管理
