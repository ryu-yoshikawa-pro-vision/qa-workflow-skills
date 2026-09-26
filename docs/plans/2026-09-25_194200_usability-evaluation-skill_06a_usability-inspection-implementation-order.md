# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 実装開始条件

`usability-inspection` の実装は、次を確認してから開始します。

- PR #11のmerge済みruntime実装をlatest mainで確認済み
- PR #12 / #13がmainへmerge済み
- `usability-evaluation` の少なくともDialog縦断検証が成立済み
- 最新mainのbrowser safety / side-effect / cleanup契約
- 最新mainのqa-workflow / Activity / Finding契約
- Playwright利用経路
- repository標準のtrigger / deterministic / semantic eval構成

依存PRやusability-evaluation実装がPlanから変わった場合はcurrent implementationを正本にします。

## 2. Step 0: baseline再確認

最新mainとcurrent branchを同期した状態で、

- Skill一覧
- browser ownership
- side-effect contract
- Activity / artifact identity
- Finding
- qa-workflow routing
- evaluation runner
- Playwright version /利用可能API

を確認します。

同じ責務が既に実装されている場合は重複実装しません。

## 3. Step 1: methodology / official reference

`_05a_usability-inspection-package-and-evaluation.md` のsourceをcurrentな公式資料で確認します。

次をすべて確認し、`references/source-catalog.md` へcanonical URL / status / checked_atを記録します。

- WCAG 2.2 / Understanding
- WAI-ARIA 1.2 / current ARIA in HTML
- ACT Rules Format 1.1 / All ACT Rules
- ISO 9241-110 interaction principles
- Cognitive Walkthroughの原著または手順・出典を追跡できる公開methodology
- Navigation Timing / Paint Timing
- web.dev Core Web Vitals / field measurement guidance
- Playwright emulation / BrowserContext / locator / actionability / scrolling / keyboard / screenshot等の公式仕様

current URL / publication state /利用条件を確認します。

長文本文をrepositoryへ複製しません。

## 4. Step 2: package skeleton / output contract

先に次を実装します。

- `skills/usability-inspection/SKILL.md`
- inspection-specific references
- `assets/output-template.md`
- deterministic validator最小schema
- trigger fixture
- output fixture

まだ実browser操作を追加しません。

先に次の分離をschemaで固定します。

- inspection scope / closure rows
- objective observation
- standard / binding requirement check
- measurement
- Playwright action trace
- optional task / flow result
- usability-evaluation ref
- Finding ref

task / persona / prior knowledgeを必須schemaにしません。

## 5. Step 3: deterministic runtime skeleton

`_05b_usability-inspection-deterministic-runtime.md` に従い、PR #11 current runtime contractを再利用して次を先に実装します。

~~~text
skills/usability-inspection/scripts/
├── runtime_contract.py
├── inspection_structure.py
├── measurement.py
└── criterion_checks.py
~~~

`assets/test-rule-catalog.json` も同時に実装します。登録対象は `_05d_accessibility-requirements-and-act.md` のsupported ACT Rule / project ruleだけです。artifact structure、ref、geometry、elapsed、threshold等のhelperはcatalogへ入れません。catalogはrule DSLではなく、`criterion_checks.py` の明示dispatchとsemantic/manual経路の入力契約です。

このStepではbrowserを操作しません。fixtureだけで次を確認します。

- same normalized input → same machine result
- observation / measurement / test rule / requirement / action draftを `inspection_structure.py` が一括してartifact-local refへ採番
- inspection scope closure
- draft key → final ref / cross-reference解決
- exact elapsed計算
- threshold比較
- threshold未定義
- supported automatic test ruleのdispatch
- source type / source statusを分離
- structure / measurement helperをtest rule catalogへ混ぜない
- manual / semiAuto ruleを自動 `passed / failed` にしない
- ACT Rules Format 1.1の `inapplicable / passed / failed / cantTell / untested` を保持する
- ACT Rule resultとrequirement resultを分離
- insufficient evidenceをrequirement `undetermined` へ残す
- runtime generatorとdeterministic validatorを別実装にする

新しいrule DSL、plugin framework、browser runnerは追加しません。

## 6. Step 4: criterion / measurement contract

fixtureで次を成立させます。

- requirement ref
- applicability
- exception
- observed fact / value
- unit
- requirement result: `satisfied / not-satisfied / undetermined`
- inspection scopeで扱わない場合の `対象外` はscope closure側で保持
- project binding時のAuthority ref
- thresholdの有無
- thresholdなしの場合に独自FAILを作らない
- advisory guidanceを `not-satisfied` へ変換しない
- 単一requirement resultを製品全体のconformanceへ昇格しない
- requirement `satisfied` には宣言scopeのpopulation / required checks closureが必要
- ACT Rule等のtest rule resultとrequirement resultを分離する

task / flow未指定caseでも成果物が成立することを確認します。

## 7. Step 5: browser observation contract

PR #12 merge後のbrowser実行基盤を再利用します。

今回のlive実行対象は既存Playwright経路で到達可能なWeb UIに限定します。

新しいbrowser frameworkを作りません。

確認:

- rendered UI / screenshot observation
- DOM / accessibility observation
- viewport
- pointer
- keyboard
- focus
- explicit scroll
- resize
- form / error state
- safe state transition
- raw screenshot / DOM / accessibility treeを必要最小限にする
- secret・個人データ・機密情報を含むraw evidenceを安全に保存できない場合の非保存契約

`usability-inspection` がbrowser / session ownerになります。

## 8. Step 6: Playwright固有の検査境界

通常E2E向けのPlaywright behaviorでusability frictionを隠さないことを先に検証します。

### auto-scroll

必須case:

- controlはDOM上に存在する
- current viewportからは見えない
- locator.click()なら操作可能

確認:

- visual / pointer inspectionでlocatorのimplicit auto-scrollをdiscoverability成功にしない
- current Playwright versionでimplicit scrollを無効化する正式オプションが利用可能ならnative機能を優先する
- 利用できないversionではaction前viewport確認 + wheel / keyboard / viewport単位のuser-facingなexplicit scrollで代替する
- target発見前のtargeted scrollをdiscoverability evidenceへ数えない
- target発見後のautomation補助scrollとdiscoverability用scrollを区別する
- scroll前後のevidenceを残せる

### locator

確認:

- role / name locatorは、user-facing情報から対象と判断した後のautomation手段として使える
- test id / hidden DOM / implementation-specific selectorでUI発見を先回りしない

### actionability / auto-wait

必須case:

- controlが操作可能になるまで待機時間あり
- input dispatch後のvisible feedbackは短い

確認:

- pre-action actionability waitとpost-input responsivenessを分離
- locator action呼び出し開始からのwall-clockをそのままuser response timeへしない
- start event / end predicateの取得方法とclock domainを固定する
- elapsedを導出するstart / endは同一clock domainで取得する
- clock domain不一致は `measurement-unavailable` にする
- end predicateを原則action前に定義する
- actionability wait自体にUI上の問題がある場合は別Observationにできる

## 9. Step 7: page inspection vertical slice

taskを与えないcanonical caseで、1画面 / 1機能を端から端まで検査します。

確認:

- inspection scope固定 / closure row生成
- deterministic runtime実行
- initial observation
- safe interaction
- keyboard / focus
- screenshot
- responsive observation
- requirement check
- measurement
- usability-evaluation連携
- cleanup
- output validator

「taskがないので実行不能」にならないことを確認します。

この段階では全製品scanへ広げません。

## 10. Step 8: general accessibility

`_05d_accessibility-requirements-and-act.md` に従い、targetへapplicableなaccessibility concern / requirementを観測・評価します。

確認:

- WCAG全Success Criteriaを毎回実行しない
- applicability / exception
- observation / measurement
- supported ACT Ruleがある場合のtest rule result
- requirement result
- sample / element resultからpage / product `satisfied` へ昇格しない
- WAI-ARIA / ARIA in HTMLのhost language requirement
- APGをnormative requirementへ昇格しない
- supported ACT RuleのACT Rules Format 1.1 §4.14.1 consistency fixture
- formal WCAG conformance要求を検出した場合は `wcag-conformance-evaluation` へroutingし、本Skill内でWCAG-EM modeへ変形しない

criterionの具体値や例外はcurrent referenceを正本にし、Plan記載値だけを実装へ固定しません。

## 11. Step 9: visual / responsive / mobile

`_05c_usability-inspection-coverage.md` に従い、responsive viewport、touch-capable、mobile device emulationを別条件として実装します。

確認:

- project / targetのlayout boundary列挙
- boundary直前 / boundary / 直後
- clipping / overflow / overlap
- primary action見切れ
- modal / popup
- unexpected horizontal scroll
- focus indicator
- visual instability
- text loss / wrapping
- screenshot evidence
- touch-capable成功をmobile emulation成功へ読み替えない
- mobile device emulationではdevice profile / viewport / screen / userAgent / deviceScaleFactor / hasTouch / isMobileを記録
- full mobile profileを構成できない場合はresponsive / touchとしてscopeを限定

DOMだけで確定せず、画像が必要な項目はscreenshotを正式なevidenceとして使います。

## 12. Step 10: performance / responsiveness

`_05e_performance-measurement.md` に従います。

直接取得するもの:

- Navigation Timing
- FCP
- actual input event → first visible feedback
- actual input event → task-ready state
- loading start → completion state

確認:

- same clock domain
- actionability waitとpost-input responseの分離
- project thresholdあり / なし
- threshold Authority
- metric source type
- cache / navigation / device profile等の実行条件

Core Web Vitals:

- LCP / CLS / INPを独自algorithmで再実装しない
- project既存RUM / CrUX / web-vitals instrumentation / Lighthouse等、provenanceを確認できるsourceがある場合だけmetricとして受け取る
- sourceがなければ `measurement-unavailable`
- lab / single sessionをfield percentileへ変換しない

## 13. Step 11: optional task / flow

task / flowが明示されたsemantic / E2E caseで実施します。task未指定のgeneral inspectionへflowを創作しません。

確認:

- task / flow未指定では必須にならない
- 指定されたflowは実操作できる
- detailed TC実行要求はtest-executionへrouting
- task resultをTC PASS / FAILへ変換しない
- Agent / tool limitationをproduct defectへ自動変換しない

## 14. Step 12: Cognitive Walkthrough optional case

learnabilityを重点確認する入力条件に該当する全caseでCognitive Walkthroughを利用します。

確認:

- 通常inspectionの固定工程ではない
- intended flowを確認できるsourceがある場合だけ利用
- 正しいstep sequenceを創作しない
- 独立Skill / runtimeを追加しない

## 15. Step 13: usability-evaluation統合

objective observation、requirement result、measurementを `usability-evaluation` へ渡します。

確認:

- inspectionがbrowser ownerを維持
- evaluationがread-only
- objective factとexpert evaluationを混ぜない
- standard / project binding resultとadvisory evaluationを混ぜない
- additional observationはinspection側でscope / safety確認
- finding traceability

同一sessionへの並行操作を行いません。

## 16. Step 14: workflow integration

`_04a_usability-inspection-workflow-integration.md` に従い、

- direct trigger
- qa-workflow
- usability-evaluation
- test-target-inspection境界
- test-execution境界
- exploratory-testing境界
- regression-testing
- qa-knowledge

を接続します。

test-target-inspection / test-executionのownerロジックへusability-inspection固有処理を埋め込みません。

## 17. Step 15: repository eval

### trigger

repository標準件数に合わせます。

### deterministic

次をすべて検証します。

- output schema
- inspection scope closure
- runtime script fixture / dispatch
- observation / test rule / requirement / measurement refs
- requirement result / applicability / evidence
- project Authority ref
- requirement `satisfied` のpopulation closure
- ACT Rule resultとrequirement resultの分離
- threshold整合
- task optionality
- Playwright observation fields
- cleanup
- evaluation / Finding ref

### semantic

`_05a_usability-inspection-package-and-evaluation.md` §7のCase A〜ADをすべて含めます。

### real Agent

`_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureを使い、実Agentがtaskなしのpage inspectionとtaskありのflow inspectionを完了できることを確認します。外部実対象や実アカウントが提供されていないことだけでrepository implementationを未完了にしません。

あわせて、

- objective factとAIの専門評価を分離する
- off-viewport locator shortcutでdiscoverability問題を隠さない
- actionability waitをpost-input responsivenessへ混ぜない
- strict requirementとadvisory guidanceを分ける
- general accessibility inspectionとformal WCAG conformance evaluationのSkill routingを分ける
- responsive / touch-capable / mobile device emulationを分ける
- Core Web Vitalsを独自算出しない
- taskが指定された場合だけtask modeを使う

ことを確認します。

## 18. Step 16: repository integration

最新mainを基準に、

- Skill一覧
- README
- EVALS
- ASSERTIONS
- qa-workflow
- validation workflow
- dataset counts

を同期します。

数値をPlan記載値で固定しません。

## 19. 完了条件

次をすべて満たしたら `usability-inspection` 実装完了とします。

- Agent Skills仕様を満たす
- task / user personaなしでもlive Web UIを検査できる
- inspection scopeを固定し、選定観点をclosureできる
- scope / observation / measurement / test rule / requirement / action ref採番とcross-referenceを `inspection_structure.py` へ一元化し、数値計算・threshold比較をdeterministic runtimeへ移している
- runtime generatorとdeterministic validatorを別実装にしている
- objective observationとexpert evaluationを分離する
- applicable standard / binding requirementをcriterion単位で判定できる
- test rule resultとrequirement resultを分離できる
- requirement `satisfied` に必要なpopulation / required checks closureを検証できる
- general accessibility inspectionを本Skillで完結できる
- formal WCAG conformance要求を `wcag-conformance-evaluation` へroutingし、本Skillでproduct-level WCAG-EM評価を実装していない
- criterionのapplicability / exception / evidenceを保持する
- advisory guidanceをstrict FAILへ変換しない
- project thresholdがなければ独自FAIL thresholdを作らない
- measurementのmetric source / method / value / unit / device profile / evidenceを保持する
- external Core Web Vitalsをsource name / version / mode / population / period / device class / percentileへ追跡できる
- LCP / CLS / INPを独自algorithmで再実装しない
- existing Core Web Vitals sourceがない場合を `measurement-unavailable` へ閉じられる
- single-run measurementを条件未達のfield metricへ昇格しない
- Playwright auto-scrollでdiscoverability問題を隠さない
- Playwright actionability waitとpost-input responsivenessを分離する
- hidden implementation情報でUI発見を先回りしない
- visual observationをscreenshot等へ追跡できる
- keyboard / focusのapplicable populationをrequested scope / accessibility経路に従って確認する
- responsive viewport / touch-capable / mobile device emulationを区別する
- task / flowは指定された場合だけ扱う
- detailed TC実行をtest-executionと分離する
- Cognitive Walkthroughを定義済み入力条件で実行し、通常inspectionへ無条件適用しない
- browser ownerがusability-inspectionである
- usability-evaluationとのread-only連携が成立する
- same session concurrent manipulationを要求しない
- side-effect / cleanup契約を満たす
- raw screenshot / DOM / accessibility tree等を必要以上に永続化せず、PR #12のevidence安全契約を満たす
- FindingがPR #13契約へ接続する
- human usability studyを実施したと偽らない
- test-target-inspection / test-execution / exploratory-testingと責務重複しない
- trigger / deterministic / semantic eval PASS
- repository validation PASS
- README / EVALS / Skill一覧整合
- git diff --check PASS

## 20. Plan全体の完了

本PRの後続実装は、

1. `usability-evaluation` が `_06_evaluation-ci-implementation-order.md` の完了条件を満たす
2. `usability-inspection` が本ファイル§19の完了条件を満たす
3. `wcag-conformance-evaluation` が `_06b_wcag-conformance-evaluation-implementation-order.md` の完了条件を満たす
4. 3 Skillのqa-workflow routingと相互連携が成立する

まで完了扱いにしません。

### coverage完了条件

- `_05c_usability-inspection-coverage.md` のWeb / responsive / touch / mobile / discoverability契約を閉じる
- `_05d_accessibility-requirements-and-act.md` のgeneral accessibility / ARIA / supported ACT契約を閉じる
- formal WCAG conformanceは `_06b_wcag-conformance-evaluation-implementation-order.md` 側で閉じる
- supported ACT RuleはACT Rules Format 1.1 §4.14.1 consistency fixtureをPASS
- `_05e_performance-measurement.md` のdirect measurement / external Core Web Vitals source境界を閉じる
- general inspectionの全上位観点をclosure
- Case A〜ADをすべてPASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical live Web E2EをPASS

## 21. 対象外

- human participant recruitment / study management
- persona generation
- survey platform
- eye tracking
- session replay基盤
- RUM collection service
- load / stress / soak testing
- backend profiler
- performance observability platform
- screenshot pixel-diff engine
- 新browser framework
- global usability-inspection task ID体系
- native mobile / desktop app live automation runtime
