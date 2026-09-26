# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. workflow上の位置づけ

`usability-inspection` はlive Web UIを能動操作し、ユーザビリティ上の問題を検査する独立Activityです。

`test-target-inspection` や `test-execution` の暗黙の追加処理にはしません。

~~~text
live Web UI
    ↓
usability-inspection
    ├→ objective observation / measurement
    ├→ applicable standard / binding criterion check
    └→ optional task / flow execution
             ↓
      immutable evidence
             ↓
      usability-evaluation
             ↓
      reference-based UI / UX evaluation
             ↓
      follow-upが必要な場合だけFinding
~~~

`usability-inspection` がbrowser / session owner、`usability-evaluation` はread-only evaluatorです。

## 2. direct trigger

次のような依頼では `usability-inspection` を直接開始できます。

- この画面を実際に触ってユーザビリティ上の問題を確認
- この機能のUI / UXを実画面で検査
- mobile Web viewportで表示崩れや操作性を確認
- keyboard操作やfocusに問題がないか確認
- target sizeやaccessible name等を標準に照らして確認
- 操作後のfeedbackや表示速度を実測
- このflowを実際に操作しながら使い勝手を確認

「ユーザビリティテストして」という依頼も、live Web UIの検査を意図する場合はtrigger aliasとして扱えます。ただし成果物ではAIによる `usability-inspection` として記録します。

一方、次は `usability-evaluation` を優先します。

- このDialog patternが妥当かレビュー
- このUIをbest practiceと照合
- Figma / screenshot / specificationからUI / UXレビュー
- WAI-ARIA / WCAG / Design Systemに照らして設計を評価

「usabilityを確認」のように実操作有無が明示されない場合は、live targetを操作して確認する要求か、design artifact / 取得済みevidenceをreference knowledgeへ照合する要求かでroutingします。

## 3. test-target-inspectionとの境界

`test-target-inspection` はcurrent target informationの収集・管理がownerです。

`usability-inspection` はcurrent target inventoryを更新するために動きません。

既存のcurrent target artifactが利用可能なら、read-onlyのpreflight contextとして次を利用できます。

- entry point
- role / permission
- viewport
- current UI情報
- known state

ただしcurrent target artifactのlocator、test id、hidden implementation情報を、inspection中のUI発見shortcutとして使いません。

current target artifactが存在することだけを理由にusability-inspectionを起動しません。

## 4. test-executionとの境界

`test-execution` は詳細TCとexpected resultが正本です。

~~~text
test-execution
詳細step + expected result
→ 指定手順を忠実に実行
→ PASS / FAIL

usability-inspection
検査scope
→ live UIを操作・観測
→ objective fact / measurement / criterion result
→ UI / UX問題候補
~~~

特定task / flowが依頼に含まれる場合、usability-inspectionでもそのflowを実際に操作できます。

ただし詳細TCの忠実な実行と仕様上のPASS / FAILが目的なら `test-execution` へroutingします。

既存test-execution成果物は、対象機能、既知状態、既存evidence、仕様上のexpected resultを理解するread-only contextとして利用できます。

TCのstep sequenceやlocatorを、usability-inspectionのUI発見shortcutとして利用しません。

## 5. usability-evaluationとの統合

`usability-inspection` は実対象から事実と測定値を取得します。

`usability-evaluation` は、そのevidenceをUI pattern、standard、Design System、heuristic等へ照合して意味を評価します。

### 受け渡すevidence

- inspection scope
- observed fact
- screenshot
- DOM / accessibility evidence
- focus / keyboard result
- visual measurement
- standard / binding criterion result
- performance measurement
- task / flow result（実施した場合）

### 実行順

既定は次です。

1. usability-inspectionが必要なlive observation / measurementを取得
2. 適用可能なstandard / binding criterionを明確な条件で判定
3. immutable evidenceをusability-evaluationへ渡す
4. usability-evaluationがread-onlyで専門評価
5. 追加観測が必要ならrequestを返す
6. usability-inspectionがscope / safetyを確認して追加観測

追加観測によって既存の観測事実や測定値を書き換えません。新しい証拠として追加します。

同じbrowser / sessionを両Skillが並行操作しません。

## 6. Cognitive Walkthrough

Cognitive Walkthroughはworkflowの固定工程にしません。

learnability、新機能の操作理解、stepごとのdiscoverability / feedback等を重点確認する依頼で有用な場合に、既存2 Skill内の参考技法として利用できます。

current specification、user flow、validated TC等からintended flowを確認できない場合は正しいstep sequenceを創作しません。

独立Skillへ分離しません。

## 7. exploratory-testingとの境界

`usability-inspection` はユーザビリティ観点の体系的な検査です。

Charterに基づいて対象領域を自由に探索し、未知のProduct Riskや問題を広く探す場合は `exploratory-testing` です。

usability-inspection中にscope外の未知領域へ探索を広げる必要が出た場合は、現在のinspection結果を閉じ、必要に応じてexploratory-testingへroutingします。

## 8. test-analysis / test-condition-design

### test-analysis

`usability-evaluation` / `usability-inspection` の結果をProduct Risk候補の入力にできます。

ただし両Skill自身はProduct Riskを採点しません。

### test-condition-design

UI / UX上のfailure mode、standard criterion、interaction / accessibility / responsive観点をテスト条件候補の入力にできます。

ただし一般guidanceを製品期待結果へ自動昇格しません。

## 9. regression-testing

全Regression Runへusability-inspectionを自動追加しません。

次の場合だけRegression scopeに含められます。

- 過去のusability Findingを再確認する
- release前に特定UI / flowのusability regression inspectionを行う方針がある
- applicable standard / project criterionを継続確認する

再実行は新しいActivity / versionとして記録し、以前の観測値を上書きしません。

初版では新しいglobalなusability-inspection task ID体系を追加しません。

## 10. qa-knowledge

project固有で繰り返し有効な知見は、PR #13のqa-knowledgeへroutingできます。

例:

- project独自UI convention
- projectで採用したDesign System requirement
- projectで採用したperformance threshold
- 継続確認すべきinteraction上の注意

汎用UI pattern knowledgeや標準知識はusability-evaluationのreferenceへ保持し、qa-knowledgeへ複製しません。

## 11. qa-workflow

qa-workflowは最低限次をroutingします。

- design artifact / 取得済みevidenceのreference-based UI / UX review → usability-evaluation
- live Web UIのユーザビリティ検査 → usability-inspection
- current target inventory → test-target-inspection
- prescribed detailed TC execution → test-execution
- Charter-based open exploration → exploratory-testing

初版のlive executionはPlaywrightで到達可能なWeb UIだけを対象にします。

native appの能動操作要求はusability-inspectionへ無理にroutingせず、静的資料やscreenshot等で評価可能ならusability-evaluationを利用します。

## 12. browser ownership

usability-inspection実行中はusability-inspectionがbrowser / session ownerです。

別Agent / Skillが同一sessionを操作しません。

`usability-evaluation` が行えるのは、

- immutable evidenceのread-only評価
- ownerへ追加観測requestを返すこと

です。

PR #12 merge後に共通browser safety / side-effect / cleanup契約が実装されている場合はそれを再利用します。

存在しない汎用Skill-to-Skill browser APIを新設しません。

## 13. Playwright固有の検査境界

通常のE2Eで便利なPlaywrightの挙動が、usability問題を隠さないようにします。

### auto-scroll

visual / pointer inspectionでは、現在viewportに見えていないcontrolをlocatorで直接指定してimplicit auto-scrollさせた結果を「発見・操作できた」と扱いません。

必要なscrollはuser actionとして実行・記録します。

### actionability auto-wait

Playwrightがclick等の前に行うactionability waitを、操作後のsystem responsivenessへ含めません。

actionability wait自体が長い、または操作可能になるまでのUI feedbackに問題がある場合は別Observationとして扱えます。

### locator

role / name等のuser-facing locatorは、既に対象と判断したcontrolを実操作するために利用できます。

test id、hidden DOM、implementation-specific selector等を、UI上で発見できないcontrolの存在を知るshortcutにしません。

## 14. 副作用

inspection中の操作に、

- 削除
- 決済
- 外部送信
- 通知
- 権限変更
- shared data更新

等が含まれる場合、PR #12 merge後の許可scope / 最大回数 / cleanup契約を適用します。

ユーザビリティ検査を理由に、許可されていない副作用を実行しません。

## 15. performance系workflowとの境界

usability-inspectionが扱うのは、user-facingな表示・interactionの実測です。

次は担当しません。

- load test
- stress test
- soak test
- backend profiling
- distributed tracing基盤
- RUM収集serviceの新設

project thresholdや有効な標準metricがある場合は、その定義に従って評価できます。

条件を満たさない単一runの値をfield metricや製品全体のperformance判定へ昇格しません。

初版では新しいperformance testing Skillを追加しません。
