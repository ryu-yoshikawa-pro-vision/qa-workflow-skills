# Regression Testing guidance

## 責務

`regression-testing`は既存のcurrent QA成果物を使って、Regression対象範囲、Suite membership、initial baseline、Run selection、required route、Activity/historyを管理します。新規・改修の仕様分析、Product Risk評価、TC設計、browser操作、execution結果の原因分析は行いません。

| 要求 | owner |
| --- | --- |
| 変更影響候補 / Product Risk | `test-analysis` |
| current TC identity / lifecycle / freshness | PR #11 `test-case-design` runtime |
| TC設計 / legacy TCの昇格 | `test-case-design` |
| Regression membership / selection / Activity | `regression-testing` |
| Regression / TC-to-E2E coverage | `coverage-analysis` |
| manual TC実行・修正確認 | `test-execution` |
| E2E実行・cleanup | `e2e-test-execution` |
| E2E failure analysis | `e2e-test-result-analysis` |
| orchestration / resume / workflow state | `qa-workflow` |

## Baseline reconciliation

1. Project ContextのRegression scope / policyとauthoritative TC discovery rootsを解決します。
2. root listingが完全であること、各source revision、決定論的なTC ref順を固定し、discovery snapshotを作ります。
3. ownerから渡されたPR #11 current lifecycle resolutionを使用します。legacy / unresolved TCは発見済みのまま記録し、baselineをincompleteにしてownerへ戻します。
4. 母集団全体をmembership判定します。current TCの全件列挙、lifecycle resolution、membership判断、traceability coverage gapを別々に記録します。
5. batch処理ではsnapshot ref / source revisionを固定します。resumeは同じsnapshotを使い、source revision変更時は新snapshotを開始します。
6. query incomplete、未判定TC、unresolved lifecycleが1件でもあればcomplete baselineにしません。

Membershipはcurrent logical TC、current Regression scope、継続的な再検証価値を根拠に判断します。one-off / migration / 調査専用は除外できますが、manual、高コスト、特殊環境だけを除外理由にしません。判断とsource refs / revisionsを保持します。Suiteは再構成できるなら派生viewとし、再構成不能なときだけmember refsを保存します。

## Run selection / currentness

Run前にdiscovery、scope、project context、relevant Risk / test objective、TC lifecycleのcurrentnessを照合します。差分があれば必要範囲をreconcileし、currentnessが閉じるまでold baselineを使いません。E2E mapping変更はmembershipでなくrequired routeの再評価へ送ります。

Run scopeはuser指定、Project Context policy、complete current baselineに基づくfull fallbackの順です。fullはcurrent baselineの全member。selectedは明示TC / filter、PR #11 impact、current Risk、過去Finding、current knowledgeを用いて候補・選択・除外とrationaleを記録します。不完全なcandidate queryだけで範囲を狭めません。候補0件をRegression不要と扱いません。scope selection、required route確定、execution startは別々に記録し、selection-only要求ではroute未解決を理由にscope判断自体をblockしません。実行を求められた場合はrouteが揃うまでexecution readinessを未解決とし、開始済みとは扱いません。

Product Riskは新規採点しません。Runに関係する既存Riskごとに、関連するTCのselected / excluded / blocked / unexecuted状態と、そのRunで残る未検証影響をRisk refと理由に結び付けて記録します。明示的な除外はそのTCの検証を完了させず、Riskの検証済み根拠にもなりません。TCとRiskのtraceabilityが入力から確認できない場合は関係を推測せず未解決にします。新しいRiskやscore変更が必要なら`test-analysis`へ戻します。

## Required routes / Activity

- routeは`manual`または具体的E2E testware refで表し、`未実行` / `blocked` / `判定不能`をroute typeにしません。
- E2Eが存在するだけでmanual routeを不要と判断しません。必要時はmanual + E2Eを設定し、coverage判断は`coverage-analysis`へ依頼します。
- PR #12 manual executionは最初の`scenario.when`操作開始、E2Eはsource contractでactual attempt開始を確認します。artifact作成やpreflight通過だけでは開始扱いにしません。
- 全required routeのactual startが確認できた場合だけlogical TCをexecutedと数えます。FAIL / 判定不能でも開始済みならexecutedの事実と両立します。
- source result / outcome / evidence / cleanupを再解釈せず参照し、履歴へ投影します。
- TCなしE2Eはuser / policyで指定された補助testwareだけを別枠集計します。TC IDを作りません。
- scope / snapshot不変のblockは同Activityでresumeできます。scope / snapshot変更は別Activity / versionです。完了Activityはimmutableです。

## Failure feedback

原因分析は担当ownerへ戻します。E2E異常は`e2e-test-result-analysis`、manual FAILで期待結果や仕様authorityが不明なら`question-analysis`で不足条件を確認し、既存仕様の解釈・Authority確定が必要な場合は`spec-analysis`へ渡します。current UI情報不足は`test-target-inspection`、TC問題は`test-case-design`、coverage gapは`coverage-analysis`、owner不明の実対象仮説調査は`exploratory-testing | investigation`です。ユーザー向けfeedbackには「FAIL / FindingだけではDefectへ自動登録しない」と明記し、原因が確定する前にRegression Skillが再判定しません。修正後はcurrentな既存TCを既存execution Skillで再利用します。周辺Regressionも要求された場合は、修正確認とは別のRun目的として`regression-testing`で選定し、更新されたsource / baseline currentnessを確認します。専用fix confirmation Skill / artifact / stateは作りません。

## Storage and history

固定rootの完全scanとdirect refsを優先します。scan error / truncationは`complete=false`です。historical revisionは実際に再取得できるrevisionのみ入力に使います。state / Activityのexpected revisionをatomic conditional writeへ渡せない場合、mutable updateは`blocked`です。過去Activityの入力snapshotは後続変更で書き換えません。
