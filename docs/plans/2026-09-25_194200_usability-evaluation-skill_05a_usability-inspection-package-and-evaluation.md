# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. Skill package

予定構成:

~~~text
skills/usability-inspection/
├── SKILL.md
├── references/
│   ├── inspection-method.md
│   ├── standards-and-measurements.md
│   └── playwright-observation.md
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

browser automation framework、performance measurement service、RUM serviceはpackage内へ新設しません。

## 2. SKILL.mdの役割

SKILL.mdにはUI pattern知識を複製しません。

最低限次を持ちます。

1. live Web UIのユーザビリティ検査Skillであること
2. 初版のlive execution scopeはPlaywrightで到達可能なWeb UIであること
3. human usability testing / user researchではないこと
4. inspection scopeの決め方
5. objective observation / measurementの取得方法
6. applicable standard / binding criterionの判定方法
7. user-facing情報とPlaywright automationの境界
8. visual / keyboard / accessibility / responsive inspection
9. performance / responsiveness measurement
10. optional task / flow execution
11. browser ownership / side-effect / cleanup
12. usability-evaluationへのevidence受け渡し
13. Finding routing
14. 完了条件

UI pattern、heuristic、Design System、WCAG等の詳細knowledgeは `usability-evaluation` のreferenceを正本とします。

## 3. methodology / reference

usability-inspection packageのreferenceは、実対象の検査・測定・Playwright上の観測方法に限定します。

### accessibility / standard criteria

適用可能なWCAG Success Criterion等をcriterion単位で評価します。

例:

- target size / spacing
- keyboard operation
- focus visibility
- reflow
- error identification
- accessible name / role / state
- contrast

criterionの例外、applicability、必要な証拠を無視して数値だけでFAILにしません。

WCAG / WAI-ARIA / ARIA in HTML等の詳細referenceは `usability-evaluation` のsource catalogを再利用します。

### interaction principles / UI pattern

ISO 9241-110等のinteraction principles、Nielsen等のheuristic、Design System guidance、UI pattern knowledgeは、strictなcriterion resultではなく専門評価の根拠として `usability-evaluation` が利用します。

一般guidanceをproduct specificationへ自動昇格しません。

### Cognitive Walkthrough

Cognitive Walkthroughは任意のinspection techniqueとしてreferenceに残します。

learnabilityやstepごとのdiscoverability / feedbackを重点確認する必要がある場合だけ利用します。

固定workflow、独立Skill、独立成果物種別にはしません。

### performance

最低限、currentなweb.dev等から次を確認します。

- Core Web Vitalsのmetric定義
- LCP / INP / CLSの判定条件
- lab / fieldの違い
- user-centric performance measurement
- browser Performance API等で取得できるmeasurement

単一Playwright runでfield dataのpercentileを満たしたと扱いません。

### Playwright

公式Playwright documentationから最低限次を確認します。

- locator
- actionability / auto-wait
- viewport / visibility
- scroll
- screenshot
- keyboard
- accessibility-related observation
- browser / page performance measurementに利用できる機構

通常E2E向けのauto-wait / auto-scrollがusability frictionを隠さないようにする契約へ利用します。

## 4. source方針

`usability-evaluation` のUI pattern corpus向けall-source discoveryを、usability-inspection packageへ複製しません。

理由:

- UI / UX knowledgeの正本を1箇所に保つ
- inspection packageはlive execution / observation方法に集中する
- Design Systemやpattern catalogを重複保持しない
- source freshness / license確認を二重化しない

usability-inspection固有sourceを追加するのは、実行・測定契約を変える公式または代表的なmethodologyに限定します。

## 5. output-template

### inspection

- Activity ref / revision
- target / entry point
- requested scope
- inspected scope
- environment / origin
- viewport / device
- input method
- role / permission（必要な場合）
- side effect scope
- unresolved / limitation
- previous Activity ref（再実行の場合）

task / flowは指定された場合だけ保持します。

- task / flow
- start state
- success condition
- task result

### objective observations

各Observation:

- observation ref
- category
- target / region / state
- observed fact
- observed value（数値がある場合）
- unit（数値がある場合）
- interaction / input method
- evidence refs
- limitation
- related measurement refs
- related criterion check refs

観測事実に「使いにくい」「分かりづらい」等の専門評価を書きません。

### standard / binding criterion checks

明確なrequirementを判定できる場合だけ保持します。

- criterion check ref
- criterion ref / source item ref
- criterion type: standard / project requirement / adopted Design System / performance threshold
- applicability
- applicability reason
- expected requirement / threshold
- observed fact / value
- result: PASS / FAIL / 判定不能 / 対象外
- evidence refs
- project Authority refs（project bindingの場合）
- note

一般heuristicやadvisory guidanceをこの表へFAILとして入れません。

単一criterionのPASSを製品全体のconformanceへ昇格しません。

### measurements

各measurement:

- measurement ref
- metric / measurement label
- target action / region
- start event
- end event / predicate
- measurement method
- elapsed / value
- unit
- environment / viewport
- threshold value（存在する場合）
- threshold source / Authority（存在する場合）
- result: within-threshold / over-threshold / threshold-not-defined / measurement-unavailable
- evidence refs
- limitation

Playwright actionability waitをpost-input responsivenessへ含めたかどうかを曖昧にしません。

独自measurementを既存metric名へ読み替えません。

### Playwright action trace

全clickの詳細logを必須にしません。

usability判断に意味があるactionだけを記録します。

- action ref
- action
- discovery basis
- target visibility / viewport state before action
- explicit scroll performed: true / false
- locator type
- Playwright actionability waitが観測上意味を持ったか
- before evidence refs
- after evidence refs
- related observation / measurement refs

visual / pointer inspectionでoff-viewport controlへ到達するためのimplicit auto-scrollを、userがcontrolを発見できた証拠にしません。

### usability-evaluation

専門評価を実行した場合:

- usability-evaluation Activity / artifact ref
- related evaluation refs

専門評価本文をinspection成果物へ複製しません。

最終報告ではobjective observation / criterion result / measurementとexpert evaluationを別sectionで表示できます。

### Finding

follow-upが必要なObservation、criterion FAIL、measurement、専門評価だけPR #13のFindingへroutingします。

## 6. deterministic validator

機械的に確認できるものだけを扱います。

最低限:

- required inspection fields
- inspection scope closure
- observation ref一意性
- measurement ref一意性
- criterion check ref一意性
- evidence ref解決
- 数値Observationのunit
- criterion result許可値
- criterion checkにcriterion ref / applicability / observed factまたはvalue / evidenceがある
- standard / binding criterion以外をstrict FAILとして扱っていない
- project binding checkにproject Authority refがある
- measurementのmethod / value / unit
- threshold resultとthreshold fieldの整合
- threshold-not-definedで仕様FAIL判定を持たない
- task / flow未指定時にtask fieldsを必須要求しない
- task / flow指定時だけtask result contractを適用する
- Playwright actionability waitをpost-input responsivenessへ無根拠に含めない
- evaluation refがある場合はusability-evaluation artifactへ解決する
- Finding refがある場合はFindingが存在する
- cleanup / residual state contract
- secret実値を成果物へ要求しない

semanticな適用性やUI / UX上の意味判断をdeterministic validatorで代替しません。

## 7. semantic eval

最低限次を評価します。

### Case A: page inspection without task

「この画面のユーザビリティを検査して」という依頼。

user goal / task / personaを創作せず、applicableなinteraction、feedback、accessibility、visual、responsive、measurementを検査できること。

### Case B: optional task

「商品を検索して詳細へ進むflowの使い勝手を確認」という依頼。

指定されたflowを実操作できるが、詳細TCのPASS / FAILには変換しないこと。

### Case C: prescribed detailed TC

詳細stepとexpected resultを忠実に実行する依頼。

usability-inspectionではなくtest-executionへroutingすること。

### Case D: WCAG target size

pointer targetのsize / spacingを測定し、applicable criterionとexceptionを確認して判定すること。

単純に24 CSS px未満という理由だけでexception確認なしにFAILへしないこと。

### Case E: focus / keyboard

keyboardでfocusを移動し、focus indicator、focus order、operationを観測すること。

画像・DOM / accessibility evidenceを適切に使い分けること。

### Case F: form error

invalid inputを安全に作れる場合、error identification / feedback / recoveryを観測すること。

一般的な「分かりにくい」という感想とcriterion判定を分離すること。

### Case G: responsive visual issue

viewport変更でprimary actionがclippingする。

screenshotとviewport条件をevidenceとして残すこと。

### Case H: project performance threshold

current Authorityに明示されたthresholdを超える。

measurementとAuthorityを結び付けてcriterion FAIL / Finding候補にできること。

### Case I: performance without threshold

操作後のvisible feedbackまでの実測値を取得するが、project thresholdがない。

値を報告し、独自FAIL thresholdを作らないこと。

### Case J: Core Web Vitals misuse

単一Playwright runのinteraction elapsed timeをfield INPやCore Web Vitals達成判定と呼ばないこと。

### Case K: Playwright auto-scroll

controlがDOM上には存在するが現在viewport外にある。

visual / pointer inspectionでlocatorから直接clickしてimplicit auto-scrollした結果をdiscoverability成功としないこと。

必要なscrollをuser actionとして扱うこと。

### Case L: Playwright actionability wait

controlが操作可能になるまでPlaywrightが800 ms待機し、実際のinput dispatch後120 msでvisible feedbackが出る。

post-input responsivenessを920 msと誤計測せず、pre-action waitとpost-input responseを分離すること。

### Case M: hidden implementation shortcut

test id / hidden DOM / source code / backend stateから、UI上で発見できないcontrolや正解経路を取得しないこと。

### Case N: usability-evaluation integration

objective observation / criterion result / measurementをusability-evaluationへ渡し、専門評価と客観観測を混ぜないこと。

### Case O: advisory guidance

一般heuristicや第三者Design System guidanceに違反して見えるが、project binding requirementではない。

strict FAILへ変換せず、usability-evaluationの専門評価として扱うこと。

### Case P: side effect

inspectionで決済・削除等の状態変更が必要だが許可scope外。

実行せず、判定可能な範囲だけ閉じること。

### Case Q: Agent limitation

Agent / tool limitationで操作を完了できない。

それだけをproduct usability defectとして確定しないこと。

### Case R: human claim

AIが問題なく操作できても「人間にも使いやすい」「初見ユーザーでも必ず使える」と断定しないこと。

### Case S: Cognitive Walkthrough optional

learnabilityを重点確認する依頼ではCognitive Walkthroughを利用できる。

通常のpage inspectionでは必須工程にしないこと。

### Case T: native app

native iOS / Android appの実機操作を要求された場合、初版Web scopeで対応可能と偽らないこと。

## 8. trigger eval

positive例:

- このWeb画面を実際に触ってユーザビリティ上の問題を確認
- この機能のUI / UXを実画面で検査
- mobile Webで表示崩れと操作性を確認
- keyboard / focus / error表示を確認
- target sizeなどをWCAG基準で確認
- この操作のfeedback速度を実測
- このflowを実際に操作して使い勝手を確認

negative例:

- このDialog patternが妥当かレビュー → usability-evaluation
- このscreenshotをUI pattern knowledgeで評価 → usability-evaluation
- このTCを実行 → test-execution
- current UI一覧を更新 → test-target-inspection
- 自由に未知の不具合を探索 → exploratory-testing

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
