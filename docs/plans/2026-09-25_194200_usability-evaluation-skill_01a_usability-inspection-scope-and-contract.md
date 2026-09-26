# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 追加するSkill

`usability-inspection` は、生きたWeb UIをAIエージェントが実際に操作・観測し、ユーザビリティ上の問題候補を検出するSkillです。

`usability-evaluation` とは責務を分けます。

| Skill | 主責務 | 実対象の能動操作 | 主な根拠 |
| --- | --- | --- | --- |
| `usability-evaluation` | UI pattern / principle / standard / Design System知識からUI / UX上の意味を評価 | 所有しない | reference knowledge + evidence |
| `usability-inspection` | live Web UIを操作・観測し、客観的事実・測定値・適用可能な標準判定を取得 | 所有する | live observation / measurement + applicable criteria |
| `test-target-inspection` | currentなテスト対象情報を収集・管理 | 必要範囲で行う | current target state |
| `test-execution` | 定義済み詳細TCを実行し期待結果と比較 | 行う | TC expected result |

`test-target-inspection` / `test-execution` は本Skillの代替ではありません。

## 2. 目的

本Skillの目的は、詳細TCやpersonaを前提にせず、対象UIを実際に操作・観測して、ユーザビリティ上の問題がないかを検査することです。

最低限、対象scopeに応じて次を確認します。

- controlを実際に操作できるか
- 操作可能なものを発見・識別できるか
- 操作後の状態変化やfeedbackを確認できるか
- loading / processing / success / error等の状態が分かるか
- errorや失敗状態から回復できるか
- keyboardで必要な操作を行えるか
- focusが適切に移動し、視認できるか
- role / accessible name / state等、観測可能なaccessibility情報に問題がないか
- viewport変更で重要な情報・操作が欠けないか
- overlap、clipping、overflow、見切れ、不要な横scroll等がないか
- pointer targetやcontrast等、数値・標準で判定可能な項目が要件を満たすか
- user actionに対するsystem responsivenessを測定できるか
- task / flowが明示された場合、そのtaskを実際に進める際に詰まりがないか

task / flowが指定されていない場合でも実行できます。

## 3. human usability testingとの境界

本Skillはhuman participantを用いるusability testingやuser researchを代替しません。

AIエージェントが実際にUIを操作した結果は、AI Agentによるinspection結果です。次を本Skill単独の事実として確定しません。

- 人間にとって使いやすいこと
- human satisfaction
- 実ユーザーの認知負荷
- 実ユーザーの学習容易性
- human task completion rate
- human task time
- 実ユーザー集団でのperformance percentile

「初見ユーザーとして確認」のような依頼がない限り、personaや経験レベルを作りません。

既定では、製品固有の正解手順、hidden implementation情報、test id、Page Object等を事前知識として使わず、一般的なWeb UIとして提示される情報から操作します。

これは人間の初見ユーザーを再現するという意味ではありません。

## 4. 初版のlive実行対象

初版の能動操作対象は、既存Playwright / browser経路で到達できるWeb UIに限定します。

- desktop Web
- responsive Web
- mobile Web viewport

native iOS / Android app、desktop native app等の能動操作は、対応runtimeがrepositoryへ実際に導入されるまで対象外です。

`usability-evaluation` 自体はplatform非依存のreference-based評価を維持します。

## 5. 入力とscope

### 必須

最低限、次を確定します。

- target / entry point
- 今回検査する画面・機能・領域
- environment / origin
- viewport / device条件。指定がなければ現在の実行条件
- input method。指定がなければpointer + keyboardを基本とする
- role / permissionが必要な場合は利用条件
- 許可された副作用scope
- 利用可能なtest data / account
- project固有の仕様 / Design System / accessibility基準 / performance thresholdがある場合はそのAuthority

### 任意

ユーザーまたは案件が明示した場合だけ利用します。

- user goal
- task / flow
- start state
- success condition
- 特定の利用者条件
- 特定のinput method
- 特定viewport / device
- 特定のperformance目標

Skill自身がpersona、業務経験年数、初見 / 熟練等を自動生成しません。

## 6. inspection scopeの固定

実操作前に今回確認するscopeを固定します。

scopeは次から必要なものを選びます。

- interaction / operability
- feedback / system status
- error prevention / recovery
- accessibility
- visual integrity / responsive
- measurable standard criteria
- user-facing performance / responsiveness
- task / flow（明示された場合）

各観点を無条件に全件実施するのではなく、対象UIに適用可能かを確認します。

「今回確認する」とした観点は、最後に少なくとも次のいずれかへ閉じます。

- 問題を確認
- 問題なし
- 判定不能
- 対象外

`問題なし` は今回のscope、実行条件、観測証拠の範囲で問題を確認しなかったことを意味し、製品全体のusabilityを保証しません。

## 7. 観測事実・標準判定・専門評価を分離する

成果物では次を混ぜません。

### 観測事実

実対象から直接確認した内容です。

例:

- buttonのbounding boxが18 × 18 CSS px
- 320 CSS px viewportでprimary actionが画面外へclippingしている
- Tabでfocusがbuttonへ移動した
- focus indicatorを画像で確認できない
- submit後にerror messageがtextで表示された
- click後184 msでloading indicatorが表示された

観測事実にはevidence refを持たせます。

### 標準・明示基準による判定

適用条件と判定方法を満たす場合だけ、明確なcriterion単位で判定します。

例:

- WCAG Success Criterion
- projectで採用したaccessibility基準
- project Design Systemのbinding requirement
- project performance budget / SLO

criterion resultは次です。

- PASS
- FAIL
- 判定不能
- 対象外

criterion ref、適用条件、観測値 / 観測事実、判定根拠、evidence refを必ず保持します。

単一componentや単一画面のcriterion結果から、製品全体のWCAG conformance等を宣言しません。

### 専門評価

UI pattern、heuristic、ISO interaction principles、Design System guidance等に基づく「なぜ問題か」「どのようなUX上の懸念があるか」は `usability-evaluation` が担当します。

一般的なguidanceやheuristicによる専門評価を、標準のFAILや製品仕様違反へ自動変換しません。

## 8. user-facing情報とPlaywrightの境界

### 操作対象の発見

通常のpointer / visual inspectionでは、操作対象を次のuser-facing情報から発見します。

- 現在viewportにrenderされているUI
- visible text
- visible control
- visible icon / label
- visible feedback
- screenshot

keyboard inspectionではfocus可能なcontrol、focus order、focus indicatorを利用できます。

accessibility inspectionではaccessibility tree、role、accessible name / description、state / propertyを利用できます。

### 正解経路の先回りに使わないもの

- test id
- hidden DOM
- source code
- Page Object locator
- internal route knowledge
- backend API / DB
- localStorage / sessionStorage
- hidden application state
- network responseの内部値

### locatorの利用

Playwrightで、既にuser-facing情報から対象と判断したcontrolを実際に操作するためにrole / name等のlocatorを使うことはできます。

ただしlocator検索結果を、visual userがまだ発見していないoff-viewport controlの存在を知るためのshortcutにしません。

visual / pointer inspectionでoff-viewport controlへ進む必要がある場合、scroll自体をuser actionとして実行・記録します。

Playwrightのimplicit auto-scrollによって、発見できていないcontrolへ直接到達した結果を「問題なく操作できた」と扱いません。

### actionability auto-wait

Playwrightがaction前に行うVisible / Stable / Receives Events / Enabled等のactionability待機は、操作後のsystem responsivenessと分離します。

actionability wait自体がUI上の利用可能性や待機状態として意味を持つ場合は、その事実を別Observationとして記録できます。

## 9. 実行手順

### Step 1: preflight

確認します。

- targetへ安全に到達できる
- inspection scope
- environment / origin
- role / permission
- viewport / input method
- side effect scope
- cleanup
- project Authority
- browser / computer操作能力

task / flowが明示されている場合だけ、start state / success conditionも確認します。

### Step 2: initial observation

対象scopeの現在状態を確認します。

- visible regions
- interactive controls
- navigation
- current state
- forms
- loading / empty / error等の状態
- screenshot
- accessibility情報
- viewport

全DOM要素を無条件にinventory化しません。

### Step 3: systematic inspection

今回scopeに応じて、安全な範囲で実操作します。

- control activation
- navigation
- open / close
- submit / cancel
- validation
- error / recovery
- focus / keyboard
- resize / responsive
- scroll
- state transition

破壊的操作や外部送信等はPR #12 merge後のside-effect契約へ従います。

### Step 4: measurable checks

適用可能なcriterion / metricについて測定します。

例:

- target size / spacing
- reflow
- focus visibility
- keyboard operation
- error identification
- accessible name / state
- contrast
- visual clipping / overflow
- project performance threshold
- browser / page側で取得可能なperformance metric

criterionのexceptionやapplicabilityを無視して数値だけでFAILにしません。

### Step 5: optional task / flow

ユーザーまたは案件がtask / flowを指定している場合だけ実行します。

詳細TCが正本で、その手順とexpected resultを忠実に実行する要求は `test-execution` へroutingします。

usability-inspectionではtaskを実行しても、結果をTCのPASS / FAILへ変換しません。

### Step 6: usability-evaluation

取得したimmutable evidence、measurement、criterion resultを `usability-evaluation` へ渡し、UI pattern / heuristic / standard / Design System等から意味を評価します。

`usability-evaluation` はread-onlyで、browser / session ownerは `usability-inspection` のままです。

追加のlive観測が必要な場合は `usability-inspection` がscope / safetyを再確認して実施します。

### Step 7: cleanup

副作用がある場合はPR #12 merge後のcleanup契約を再利用します。

cleanup結果と残存状態を記録します。

## 10. Cognitive Walkthrough

Cognitive Walkthroughは必須工程にしません。

次のような依頼・状況で有用な場合にだけ、`usability-inspection` / `usability-evaluation` が利用できる参考技法とします。

- learnabilityを重点的に確認する
- 新しい機能の操作理解を確認する
- user flowのstepごとにdiscoverability / feedbackを詳しく診断する

current specification、user flow、validated TC等からintended flowを確認できる場合だけ利用し、正しいstep sequenceを創作しません。

独立Skill、独立runtime、独立Finding lifecycleは追加しません。

## 11. performance / responsiveness

### project thresholdがある場合

現在有効なperformance budget、SLO、仕様等をAuthorityとして比較できます。

### 標準metric / benchmarkを使う場合

metricの定義・測定条件を満たす場合だけ、そのmetric名で報告します。

Core Web Vitals等でfield dataやpercentileを要求する判定は、単一のPlaywright runだけから達成 / 不達成を宣言しません。

### interaction measurement

独自に測る場合は、何を測ったかを明示します。

例:

- actual input dispatch → first visible feedback
- actual input dispatch → task-ready state
- navigation start →主要内容が利用可能
- loading start → completion state

測定には、

- start event
- end event / predicate
- measurement method
- elapsed time
- viewport / device
- environment
- threshold Authority（存在する場合）
- evidence ref

を残します。

Playwright action呼び出し開始からの時間を、そのまま「ユーザー操作後の応答時間」とみなしません。actionability wait等のpre-action時間とpost-input responseを分離します。

project thresholdがない場合、独自の仕様FAIL thresholdを作りません。

## 12. task / flowを実行した場合の結果

task / flowが指定された場合だけ、必要に応じて次を保持できます。

- 達成
- 未達成
- 判定不能
- 未実行

Agent / tool limitationとproduct側の阻害を分離します。

Agentがcontrolを見つけられなかったという事実だけでproduct usability問題を確定しません。

task結果は補助情報であり、本Skillの完了条件そのものではありません。

## 13. Finding

PR #13 merge後のFinding契約を再利用します。

Finding候補になり得るもの:

- applicable standard / binding requirementのFAIL
- UI操作不能
- user-facing feedback欠如
- error recovery不能
- keyboard / focus上の問題
- taskを阻害するvisual breakage
- project threshold違反
- 専門評価でfollow-upが必要と判断されたUI / UX上の懸念

一般的なheuristicとの差異だけで製品Defectを確定しません。

## 14. 担当しないこと

- representative userを用いたUX research
- user interview / satisfaction調査
- human task completion rate / human task timeの測定
- persona生成
- user experience levelの推定
- eye tracking
- session replay analytics
- RUM基盤の新設
- load / stress / soak test
- backend performance profiling
- detailed TCのPASS / FAIL
- current target inventoryの正本管理
- exploratory Session lifecycle
- pixel-perfect visual regression framework
- 新しいbrowser automation framework
- native mobile / desktop app向けlive automation runtime
- project requirementにないperformance thresholdの創作

## 15. 完了条件

1つのusability-inspection Activityは、最低限次を満たせば完了できます。

- inspection scopeが固定されている
- 「今回確認する」とした観点が問題を確認 / 問題なし / 判定不能 / 対象外へ閉じている
- 観測事実とevidenceが追跡できる
- standard / binding criterionを判定した場合はcriterion ref、applicability、観測値 / 事実、result、evidenceへ追跡できる
- measurementを報告する場合は測定区間・方法・実測値へ追跡できる
- Playwrightのauto-scroll / actionability waitでinspection対象のfrictionを隠していない
- hidden implementation情報で操作対象を先回りしていない
- task / flowが指定された場合は、その実行結果と制約を記録している
- side effect / cleanup契約が閉じている
- `usability-evaluation` を実行した場合は、観測事実 / criterion resultと専門評価が分離されている
- 必要なFindingがroutingされている
- human usability / satisfactionを捏造していない

問題が0件でも完了できます。
