# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. Skill package

予定構成:

~~~text
skills/usability-inspection/
├── SKILL.md
├── references/
│   ├── inspection-method.md
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

1. task-based live inspectionであること
2. 初版のlive execution scopeはPlaywrightで到達可能なWeb UIであること
3. representative-user studyではないこと
4. 必須入力
5. task selection / task scenarioの固定
6. user-facing情報だけでtask pathを選ぶ契約
7. browser ownership / safety
8. task outcome
9. Agent / tool limitationとの切り分け
10. timing measurement
11. usability-evaluationへのevidence受け渡し
12. Finding routing
13. referencesの選択方法
14. 完了条件

UI pattern / WCAG / Design Systemの詳細根拠は `usability-evaluation` のreferenceを利用します。

## 3. methodology reference

usability-inspection packageのreferenceは、実行方法・測定方法に限定します。

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

### Nielsen Norman Group / NIST

human participantを用いるusability testingとの違いを理解する資料として、最低限次を確認します。

- NN/g Usability Testing 101
- NN/g Task Scenarios for Usability Testing
- NN/g Task Analysis

Agentによるtask-based inspectionの主要methodologyとして、最低限次を確認します。

- NN/g Cognitive Walkthroughs
- NN/g Summary of Usability Inspection Methods
- NISTのCognitive Walkthrough / usability inspection guidance

これらから、user goal、realistic task scenario、詳細手順を与えすぎない原則、user視点でtaskをstep-by-stepに検査する方法、human studyとの境界を参照します。

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

通常のtask-based usability-inspectionで毎回WCAG-EM全手順を要求しません。

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

`usability-evaluation` のUI pattern corpus向けall-source discoveryを、usability-inspection methodologyへそのまま複製しません。

理由:

- inspection Skillが必要とするのはexecution methodologyであり、Design System catalogではない
- UI pattern知識はusability-evaluationを正本にする
- testing method sourceを大量収集してもtask executionの再現性が直接上がるとは限らない

methodology sourceを追加する場合は、

- task execution contractを変える一次・代表的source
- accessibility evaluation methodology
- user-facing performance measurement methodology

に限定します。

## 5. output-template

### task selection summary

広いscopeから複数taskを選ぶ場合だけ、Activity群の前にcoordination情報として保持します。独立Machine Entityにはしません。

- requested scope
- task candidate
- candidate source / evidence refs
- selected / not-selected / deferred
- selection reason
- coverage limitation

明示taskが1件だけの場合、このsummaryは省略できます。

### Activity

- Activity ref / revision
- target
- user / role
- prior knowledge / experience assumptions
- prior knowledge state: confirmed / inferred / unknown
- prior knowledge / experience assumption source / evidence refs
- user goal
- user goal source / evidence refs
- goal state: confirmed / inferred / unknown
- task scenario
- start state
- success condition
- platform: 初版live executionはWeb
- viewport / device
- input method
- locale
- role / permission
- environment
- side effect scope
- previous Activity ref（再実行の場合）

### task result

- primary outcome fixed before diagnosis: true / false
- primary outcome fixed_at
- task outcome: 達成 / 未達成 / 判定不能 / 未実行
- outcome basis: success-observed / product-blocker-observed / agent-tool-limitation / environment-external / unresolved / not-started

対応は固定します。

- `達成` → `success-observed`
- `未達成` → `product-blocker-observed`
- `判定不能` → `agent-tool-limitation / environment-external / unresolved`
- `未実行` → `not-started`
- outcome evidence refs
- completion limitation / reason
- final state
- cleanup result / residual state

### action trace

meaningful action単位で:

- action ref
- action
- action type: normal / retry / backtrack / recovery
- related action ref（retry / backtrack / recoveryで必要な場合）
- user-facing cue
- interaction method
- before evidence refs
- observed response
- after evidence refs
- continuation state
- unexpected behavior
- timing refs

全clickを無条件に詳細ログ化せず、task outcomeやFindingの再確認に必要なmeaningful actionを正本にします。

### Agent run上の操作負荷

必要範囲でaction traceから次を保持します。

- meaningful_action_count
- retry_count
- backtrack_count
- dead_end_count
- error_count
- recovery_count

集計規則:

- meaningful_action_count: action trace件数
- retry_count: action type=`retry` 件数
- backtrack_count: action type=`backtrack` 件数
- recovery_count: action type=`recovery` 件数
- dead_end_count: observation category=`dead-end` 件数
- error_count: observation category=`user-facing-error` 件数。Agent / tool / browser自身のerrorは含めない

これらはAgent runの観測値であり、human efficiency metricや総合usability scoreではありません。任意thresholdによる合否判定をしません。

### timing measurements

各measurement:

- measurement ref
- action ref
- metric label
- start event
- end predicate
- measurement method
- definition fixed before action: true / false
- elapsed_ms
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
- observation category: dead-end / user-facing-error / visual-breakage / feedback / other
- observed fact
- target state
- evidence refs
- related action ref
- measurement refs
- unresolved

を保持します。

### post-task diagnosis

primary task outcome固定後にdiagnosisを実施した場合だけ保持します。

- diagnosis ref
- method: cognitive-walkthrough / evaluation-requested-observation
- intended flow source refs（Cognitive Walkthroughの場合）
- diagnostic evidence refs
- related primary action refs
- note

Cognitive Walkthroughでは、intended flowをcurrentなspecification、user flow、検証済みTC等から確認できる場合だけ使います。正しいstep sequenceを推測で作りません。

post-task diagnosisはprimary task outcome / primary action traceを書き換えません。

### UI / UX evaluation

`usability-evaluation` を実行した場合、

- usability-evaluation Activity / artifact ref
- related evaluation refs

を保持します。

評価結果自体をusability-inspection側へ複製しません。

usability-evaluationからの追加観測はpost-task diagnosisとして記録し、primary task outcomeを変更しません。

### Finding

follow-upが必要なObservation / evaluationだけ、PR #13のFinding契約で作成します。

## 6. deterministic validator

機械的に確認できるものだけを扱います。

最低限:

- required Activity fields
- task outcome許可値
- outcome basis許可値とtask outcomeの整合
- `未達成` はoutcome basis=`product-blocker-observed` かつuser-facing evidenceを持つ
- Agent / tool limitation、environment / external、unresolvedは `判定不能` へ閉じる
- broad scopeのtask selection summaryではselected taskが各Activityへ対応し、coverage limitationがある
- `達成` にsuccess condition evidenceがある
- `判定不能 / 未実行` に理由がある
- started taskのmeaningful action ref一意性
- actionからevidenceへ解決できる
- action type / observation categoryの許可値
- Agent run上の操作負荷countがaction trace / Observationから導出できる
- timing measurementのstart event / end predicate / measurement method / definition fixed before action / elapsed_ms
- elapsed_msが非負
- browser / page側の同一計測系で区間を測定できない場合にsystem responsiveness値を確定しない
- definition fixed before action=falseのmeasurementをperformance判定根拠にしない
- threshold resultとthreshold fieldの整合
- over-threshold / within-thresholdにはthreshold Authority refがある
- threshold-not-definedで任意のFAIL判定を持たない
- source test case PASS / FAIL欄を持たない
- user goal sourceとgoal state（confirmed / inferred / unknown）がある
- prior knowledge / experience assumptions、prior knowledge state（confirmed / inferred / unknown）、source / evidence refsがある。根拠がなければstate=unknownとして表現する
- primary outcome fixed before diagnosis=trueでないActivityにpost-task diagnosis / usability-evaluation refを持たせない
- Cognitive Walkthrough diagnosisがある場合はintended flow source refsがあり、primary outcome固定後の診断として記録される
- evaluation-requested-observationがある場合はpost-task diagnosisとして記録される
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

usability-inspectionではなくtest-executionへroutingすること。

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

primary task中にusability-evaluationを割り込ませず、task outcome / primary action traceを固定してからevidenceを渡すこと。

pattern / standardによる判断をinspection側で独自複製しないこと。

usability-evaluationから追加観測requestが返ってもpost-task diagnosisとして扱い、primary task outcomeを書き換えないこと。

### Case L: human claims

AIがtaskを達成しただけで「人間にも使いやすい」「満足度が高い」と断定しないこと。

### Case M: broad scope task selection

「サービス全体の使い勝手を確認」という依頼で、根拠のない1 taskだけを実行して全体評価としないこと。task候補、選定根拠、未選定scope、coverage limitationを残すこと。

### Case N: Agent failure

Agentがcontrolを見つけられないが、screenshot / accessibility evidenceでは明確なuser-facing cueが存在する。

product側のdiscoverability defectへ昇格せず、Agent / tool limitationまたは切り分け不能として `判定不能` にすること。

### Case O: product-side blocker

必要controlがviewport外へclippingし、許可されたinteraction modeでは操作不能であることをevidenceで確認できる。

`未達成` + product-blocker-observedを許可し、必要ならFinding候補へできること。

### Case P: timing endpoint post hoc

結果を見た後で都合のよいend predicateへ差し替えないこと。measurement definitionがaction前に固定されていない場合はperformance判定根拠にしないこと。

### Case Q: native app

native iOS / Android appの実機操作を要求された場合、初版のPlaywright Web live scopeで対応可能と偽らないこと。静的資料のUI / UX評価が可能ならusability-evaluationへroutingできること。

### Case R: prior knowledge

同じtaskでも「製品初回利用・一般的なWeb UI経験あり」と「製品熟練利用者」でdiscoverabilityの期待が異なるcase。

user / roleだけから経験レベルを推測せず、prior knowledge / experience assumptions、prior knowledge state、根拠をtask snapshotへ固定すること。

### Case S: post-task Cognitive Walkthrough

primary runではTC stepを見ずにuser-facing情報だけでtaskを実行してoutcomeを固定する。

その後、current specification / user flow / validated TCからintended flowを確認できる場合だけCognitive Walkthroughを実施し、各stepのgoal / action visibility / mapping / execution / feedbackを診断すること。

walkthrough結果でprimary outcomeを書き換えないこと。

### Case T: no authoritative flow

primary run後にCognitive Walkthroughを行いたいが、currentなuser flow / specification / validated TCを確認できない。

正しいstep sequenceを創作せずwalkthroughを省略し、利用できるevidenceだけをusability-evaluationへ渡すこと。

## 8. trigger eval

positive例:

- 実際にこのサイトを操作して商品検索の使い勝手をテスト
- このtaskを初見ユーザー想定でやってみて詰まる場所を確認
- mobile Web viewportで画面を触って表示崩れと操作性を確認
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
