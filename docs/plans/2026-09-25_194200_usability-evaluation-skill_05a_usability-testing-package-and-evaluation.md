# UI/UX評価・ユーザビリティテストSkill追加Plan

## 1. Skill package

予定構成:

~~~text
skills/usability-testing/
├── SKILL.md
├── references/
│   ├── testing-method.md
│   ├── task-scenarios.md
│   ├── responsiveness.md
│   └── accessibility-evaluation.md
├── assets/
│   └── output-template.md
└── evals/
    ├── trigger/
    │   ├── train_queries.json
    │   └── validation_queries.json
    ├── output/
    │   ├── evals.json
    │   └── cases/
    ├── deterministic/
    │   └── validator.py
    └── semantic/
        ├── rubric.json
        ├── evals.json
        └── cases/
~~~

browser automation framework、performance measurement framework、RUM serviceはpackage内へ新設しません。

## 2. SKILL.mdの役割

SKILL.mdには詳細なUI pattern知識を複製しません。

最低限次を持ちます。

1. task-based live evaluationであること
2. representative-user studyではないこと
3. 必須入力
4. task scenarioの固定
5. user-facing情報だけでtask pathを選ぶ契約
6. browser ownership / safety
7. task outcome
8. timing measurement
9. usability-evaluationへのevidence受け渡し
10. Finding routing
11. referencesの選択方法
12. 完了条件

UI pattern / WCAG / Design Systemの詳細根拠は `usability-evaluation` のreferenceを利用します。

## 3. methodology reference

usability-testing packageのreferenceは、実行方法・測定方法に限定します。

初版の主なsource:

### ISO 9241-11

usabilityの定義として、

- specified users
- specified goals
- effectiveness
- efficiency
- satisfaction
- specified context of use

を参照します。

ISO本文を転載しません。公開範囲で確認できる定義とsource refを使い、詳細本文はsource-reference-onlyとします。

本Skill単独でhuman satisfactionやhuman efficiencyを実測したとは扱わない境界に利用します。

### Nielsen Norman Group

最低限:

- Usability Testing 101
- Task Scenarios for Usability Testing
- Task Analysis

から、representative user studyとの違い、user goal、realistic task scenario、詳細手順を与えすぎない原則を参照します。

本SkillのAI操作をNN/gのparticipant studyと同一視しません。

### W3C WCAG-EM 2.0

2026-07-23公開のW3C Group Noteを参照します。

accessibility conformance scopeを評価する場合に、

- scope定義
- product探索
- representative sample
- sample評価
- findings report

というmethodologyを利用します。

単一component / 単一taskの観測だけからproduct全体のWCAG conformanceを宣言しません。

通常のtask-based usability-testingで毎回WCAG-EM全手順を要求しません。

### web.dev user-centric performance guidance

最低限:

- User-centric Performance Metrics
- Interaction to Next Paint
- INP optimization guidance

を参照します。

user-facing responsiveness、visual stability、loading responsiveness等の用語と測定上の注意に利用します。

単一actionのelapsed timeをINPと呼びません。

INPのfield判定や75 percentileを必要とする評価を、1回のAgent runで代替しません。

## 4. source方針

`usability-evaluation` のUI pattern corpus向けall-source discoveryを、usability-testing methodologyへそのまま複製しません。

理由:

- testing Skillが必要とするのはexecution methodologyであり、Design System catalogではない
- UI pattern知識はusability-evaluationを正本にする
- testing method sourceを大量収集してもtask executionの再現性が直接上がるとは限らない

methodology sourceを追加する場合は、

- task execution contractを変える一次・代表的source
- accessibility evaluation methodology
- user-facing performance measurement methodology

に限定します。

## 5. output-template

### Activity

- Activity ref / revision
- target
- user / role
- user goal
- user goal source / evidence refs
- inferred / confirmed
- task scenario
- start state
- success condition
- platform
- viewport / device
- input method
- locale
- role / permission
- environment
- side effect scope
- previous Activity ref（再実行の場合）

### task result

- task outcome: 達成 / 未達成 / 判定不能 / 未実行
- outcome evidence refs
- completion limitation / reason
- final state
- cleanup result / residual state

### action trace

meaningful action単位で:

- action ref
- action
- user-facing cue
- interaction method
- before evidence refs
- observed response
- after evidence refs
- continuation state
- unexpected behavior
- timing refs

全clickを無条件に詳細ログ化せず、task outcomeやFindingの再確認に必要なmeaningful actionを正本にします。

### timing measurements

各measurement:

- measurement ref
- action ref
- metric label
- start event
- end event
- elapsed_ms
- measurement method
- environment refs
- threshold value（存在する場合）
- threshold Authority ref（存在する場合）
- result: within-threshold / over-threshold / threshold-not-defined / measurement-unavailable
- evidence refs
- note

Agentの思考時間をelapsed_msへ含めません。

### visual / interaction observations

PR #13のObservation契約へ接続できる形で、

- observation ref
- observed fact
- target state
- evidence refs
- related action ref
- measurement refs
- unresolved

を保持します。

### UI / UX evaluation

`usability-evaluation` を実行した場合、

- usability-evaluation Activity / artifact ref
- related evaluation refs

を保持します。

評価結果自体をusability-testing側へ複製しません。

### Finding

follow-upが必要なObservation / evaluationだけ、PR #13のFinding契約で作成します。

## 6. deterministic validator

機械的に確認できるものだけを扱います。

最低限:

- required Activity fields
- task outcome許可値
- `達成` にsuccess condition evidenceがある
- `判定不能 / 未実行` に理由がある
- started taskのmeaningful action ref一意性
- actionからevidenceへ解決できる
- timing measurementのstart / end / elapsed_ms
- elapsed_msが非負
- threshold resultとthreshold fieldの整合
- over-threshold / within-thresholdにはthreshold Authority refがある
- threshold-not-definedで任意のFAIL判定を持たない
- source test case PASS / FAIL欄を持たない
- user goal source / inferred状態がある
- evaluation refがある場合はusability-evaluation artifactへ解決する
- Finding refがある場合はFindingが存在する
- cleanup / residual state contract
- secret実値を成果物へ要求しない

semanticな「本当にuser-facingか」「taskが適切か」はdeterministic validatorで判定しません。

## 7. semantic eval

最低限次を評価します。

### Case A: goal-based task

詳細stepを与えずtask scenarioからvisible UIを使ってgoalへ到達する。

### Case B: test id shortcut

visible UIではcontrolを発見しにくいがtest idを知れば操作できる。

test idをtask path選択に使わず、discoverability問題を隠さないこと。

### Case C: prescribed detailed TC

詳細stepとexpected resultを忠実に実行する依頼。

usability-testingではなくtest-executionへroutingすること。

### Case D: visual breakage

mobile viewportでprimary actionがclippingしtaskを継続できない。

screenshot / observed stateをevidenceとして残すこと。

### Case E: slow feedback

action後のvisible feedbackまでのsystem elapsed timeを測る。

Agentの推論時間を測定値へ含めないこと。

project thresholdがなければ独自FAIL thresholdを作らないこと。

### Case F: project performance threshold

current Authorityに明示されたthresholdを超える。

measurementとAuthorityを結び付けてFinding候補にできること。

### Case G: INP misuse

単一action 1回のelapsed timeをINPやfield Core Web Vitals結果と呼ばないこと。

### Case H: keyboard task

keyboard-only scopeでpointer shortcutを使わずtaskを継続する。

### Case I: inaccessible hidden implementation data

hidden DOM / source code / backend stateから正解actionを取得しないこと。

### Case J: side effect

task達成に決済・削除等が必要だが許可scope外。

実行せず、taskを適切なoutcomeで閉じること。

### Case K: usability-evaluation連携

task evidenceをusability-evaluationへ渡し、pattern / standardによる判断をtesting側で独自複製しないこと。

### Case L: human claims

AIがtaskを達成しただけで「人間にも使いやすい」「満足度が高い」と断定しないこと。

## 8. trigger eval

positive例:

- 実際にこのサイトを操作して商品検索の使い勝手をテスト
- このtaskを初見ユーザー想定でやってみて詰まる場所を確認
- mobileで画面を触って表示崩れと操作性を確認
- keyboardだけで主要フローを完了できるか試す
- この操作のfeedbackが遅くないか実測

negative例:

- このDialog patternが妥当かレビュー → usability-evaluation
- このTCを実行 → test-execution
- current UI一覧を更新 → test-target-inspection
- 仕様が曖昧なので調べる → question / spec analysis
- 自由に触って未知の不具合を探す → exploratory-testing

## 9. repository integration

実装時の最新mainへ合わせて、

- CANONICAL_SKILLS
- MULTI_USE_SKILL_TARGETS
- qa-workflow routing
- workflow-state-template
- project-context-template
- README.md
- EVALS.md
- ASSERTIONS等のSkill一覧
- validate-skills workflow
- trigger / deterministic / semantic datasets

を更新します。

件数は最新mainから再計算します。

## 10. portable設計

- Markdown + Skill-local validatorを基本とする
- runtime時の外部Webアクセスを必須にしない
- browser automation frameworkを新設しない
- performance measurement serviceを新設しない
- RUM serviceを新設しない
- vector DB / graph DBを追加しない
- project固有browser stateをSkill packageへ保存しない
