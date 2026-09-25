# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. workflow上の位置づけ

`usability-inspection` はlive targetを能動操作する独立Activityです。

`test-target-inspection` や `test-execution` の暗黙の追加処理にはしません。

~~~text
user goal / task scenario
          ↓
 usability-inspection
          ↓
 live browser interaction
          ↓
 observation / timing / screenshot / accessibility evidence
          ↓
 usability-evaluation
          ↓
 UI / UX評価項目
          ↓ follow-upが必要
 Finding
~~~

`usability-inspection` がbrowser / session owner、`usability-evaluation` はread-only evaluatorです。

## 2. direct trigger

次のような依頼では `usability-inspection` を直接開始できます。

「ユーザビリティテストして」という表現もlive Web UIのtask-based検査を意図する場合はtrigger aliasとして受けますが、成果物はAIによる `usability-inspection` として記録します。

- 実際に画面を触って使い勝手を確認
- このサービスを初見ユーザーとして操作して問題を探す
- このtaskを実際に完了できるかユーザビリティテスト
- mobile Web viewportで操作して表示崩れや使いづらさを確認
- 操作後の表示やfeedbackが遅くないか実測
- keyboardだけで主要taskを完了できるか確認

一方、次は `usability-evaluation` を優先します。

- このDialog patternが妥当かレビュー
- このUIをbest practiceと照合
- Figma / screenshot / specificationからUI / UXレビュー
- WAI-ARIA / WCAG / Design Systemに照らして評価

「usabilityを確認」のように操作有無が明示されない場合は、利用可能なlive targetと依頼文から、実対象のtask実行が要求されているかをqa-workflowが判定します。

## 3. test-target-inspectionとの境界

`test-target-inspection` はcurrent target informationの収集・管理がownerです。

`usability-inspection` はcurrent target inventoryを更新するために動きません。

既存のcurrent target artifactが利用可能なら、read-onlyのpreflight contextとして

- entry point
- role / permission
- viewport
- current UI情報
- known state

をpreflightの補助に利用できます。

ただしtask実行では、current target artifactのlocatorやhidden implementation情報をuser-facing discoveryの代わりに使いません。

`usability-inspection` 中に得た新しいUI情報を、理由なくtest-target-inspectionの正本へ自動書き戻しません。

current target artifactが存在することだけを理由にusability-inspectionを起動しません。逆にusability-inspection実行時も、既存artifactからentry point、role、viewport、known state等を再利用できるなら重複確認を減らします。

## 4. test-executionとの境界

`test-execution` は詳細TCとexpected resultが正本です。

~~~text
test-execution
詳細step + expected result
→ 指定手順を忠実に実行
→ PASS / FAIL

usability-inspection
user goal + task scenario + success condition
→ user-facing情報から操作方法を探索
→ task outcome + usability observation
~~~

詳細TCが存在していても、usability-inspectionでそのstep sequenceを答えとして利用しません。

既存test-execution成果物は、対象機能・既知状態・既存evidence・仕様上のexpected resultを理解するread-only contextとして利用できます。ただし、その存在だけでusability-inspectionを起動せず、locatorやstep sequenceをtask pathの正解として利用しません。

「このTCを実行して」はtest-executionです。

「同じ機能を、手順を教えずuser goalだけで実際に使ってみて」はusability-inspectionです。

## 5. usability-evaluationとの統合

`usability-inspection` は実測を担当し、`usability-evaluation` はreference knowledgeによる意味判断を担当します。

### 受け渡すevidence

- task / success condition
- meaningful action trace
- before / after state
- screenshot
- DOM / accessibility evidence
- focus / keyboard result
- error / recovery result
- viewport
- measured system timing
- task outcome

### 実行タイミング

既定は次です。

1. usability-inspectionがtaskを安全なcheckpointまで進める
2. immutable evidenceをusability-evaluationへ渡す
3. usability-evaluationがread-onlyで評価
4. 追加観測が必要ならrequestを返す
5. usability-inspectionがscope / safetyを確認して追加観測

同じbrowser / sessionを両Skillが並行操作しません。

taskの各クリックごとにevaluationを割り込ませません。

意味判断に必要なcheckpointまたはtask終了時にまとめて評価します。

## 6. exploratory-testingとの境界

`usability-inspection` はuser goal / task scenario / success conditionを持ちます。

Charterだけを持って自由に未知の問題を探索する場合は `exploratory-testing` です。

実行中にtask goal自体を変更しながら別領域へ広く探索する必要が出た場合、

- 現在taskを閉じる
- Finding / Observationを残す
- exploratory-testingへroutingする

ことを優先します。

`usability-inspection` を汎用探索Skillへ拡張しません。

## 7. test-analysis / test-condition-design

### test-analysis

Product Riskや主要user goalから、usability-inspectionすべきtask候補を選ぶ入力にできます。

広いscopeではproject requirement、user research、analytics / support data、Product Risk、検証済みproject knowledge等からtask候補を作り、selected / not-selected / deferredとcoverage limitationを残します。task母集団の根拠がない場合はUIからの推定taskを代表taskとして扱いません。

ただしusability-inspection自身はProduct Riskを採点しません。

### test-condition-design

UI / UXに関するcoverage観点から、どのtask / stateをusability-inspectionで実測する価値があるかを入力にできます。

ただしtask scenarioを詳細TCへ変換しません。

## 8. regression-testing

全Regression Runへusability-inspectionを自動追加しません。

次の場合だけRegression scopeに含められます。

- usability regression taskが明示的に選定された
- 過去のusability Findingを再確認する
- 主要task flowをrelease前に再実行する方針がprojectにある

過去runのtask snapshotを再利用する場合も、role / goal / start state / success condition / environmentがcurrentか確認します。

再実行は新しいActivity / versionとして記録し、以前のtask outcomeを上書きしません。

初版では新しいglobalなUsability Test Case ID体系を追加しません。

## 9. qa-knowledge

project固有で繰り返し有効な知見は、PR #13のqa-knowledgeへroutingできます。

例:

- 特定user roleで毎回問題になるnavigation
- project独自UI convention
- projectで採用したresponse threshold
- 継続確認すべきinteraction上の注意

汎用UI pattern知識はusability-evaluationのreferenceへ保持し、qa-knowledgeへ複製しません。

## 10. qa-workflow

qa-workflowは最低限次をroutingします。

初版のlive executionはPlaywrightで到達可能なWeb UIだけを対象にします。native appの能動操作要求はusability-inspectionへ無理にroutingせず、静的資料やscreenshot等で評価可能ならusability-evaluationを利用します。

- reference-based UI / UX review → usability-evaluation
- live target task-based test → usability-inspection
- current target inventory → test-target-inspection
- prescribed detailed TC execution → test-execution
- Charter-based open exploration → exploratory-testing

Skill名の単語一致だけでroutingせず、ユーザー要求が「何を正本にして、何を実行したいか」で分けます。

## 11. browser ownership

usability-inspection実行中はusability-inspectionがbrowser / session ownerです。

別Agent / Skillが同一sessionを操作しません。

利用できるのは、

- read-only evidence evaluation
- ownerへ追加観測requestを返すこと

です。

PR #12 merge後に共通browser safety / side-effect / cleanup契約が実装されている場合はそれを再利用します。

存在しない汎用Skill-to-Skill browser APIを新設しません。

## 12. 副作用

task scenarioに、

- 削除
- 決済
- 外部送信
- 通知
- 権限変更
- shared data更新

等が含まれる場合、PR #12 merge後の許可scope / 最大回数 / cleanup契約を適用します。

user goalを達成するためでも、許可されていない副作用を実行しません。

安全にtaskを継続できない場合はtask outcomeを未達成または判定不能として閉じ、必要な条件を報告します。

## 13. performance系workflowとの境界

usability-inspectionが扱うのはtask中のuser-facing responsivenessです。

次は担当しません。

- load test
- stress test
- soak test
- backend profiling
- distributed tracing基盤
- RUM収集serviceの新設

performance専門調査が必要になった場合は、その担当workflowへroutingできるよう観測値と対象actionを残します。

初版では新しいperformance testing Skillを追加しません。
