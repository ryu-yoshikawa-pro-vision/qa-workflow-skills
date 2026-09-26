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

次をすべて確認します。

- WCAG 2.2 / Understanding
- WAI-ARIA 1.2 / current ARIA in HTMLのcoverage matrix対象requirement
- ACT Rules Format 1.1 / current WAI公開formal・proposed ACT Rules
- ISO 9241-110 interaction principles
- Cognitive Walkthroughの原著または手順・出典を追跡できる公開methodology
- web.dev Core Web Vitals / user-centric performance guidance
- Playwright locator / actionability / scrolling / keyboard / screenshot等の公式仕様

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

`assets/deterministic-check-catalog.json` も同時に実装し、今回扱うACT Rule / ACT外checkのmetadataを全件登録します。catalogはrule DSLではなく、`criterion_checks.py` の明示dispatchとsemantic/manual経路の入力契約です。

このStepではbrowserを操作しません。fixtureだけで次を確認します。

- same normalized input → same machine result
- artifact-local ref採番
- inspection scope closure
- cross-reference解決
- exact elapsed計算
- threshold比較
- threshold未定義
- fully automated checkのdispatch
- partial / manual checkを自動 `passed / failed` にしない
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

## 10. Step 8: accessibility / standard checks

`_05c_usability-inspection-coverage.md` のWCAG 2.2 / WAI-ARIA / ARIA in HTML coverage matrixを全件実装します。

target size / spacing、focus visible、keyboard operation、error identification、reflow / responsive、accessible name / role / state等を一部の代表項目として止めず、各Success Criterion / requirementをapplicability、必要evidence、判定owner、resultへ閉じます。

確認:

- applicability / exception
- observation / measurement
- formal ACT Rule等の対応済みdeterministic checkがある場合はtest rule result
- requirement result
- evidence
- product-wide conformanceへ昇格しないこと

criterionの具体値や例外はcurrent referenceを正本にし、Plan記載値だけを実装へ固定しません。

## 11. Step 9: visual / responsive

visual / responsive coverageとして、少なくとも次を対象UIの全applicable state / viewport boundaryで確認します。

- clipping
- overflow
- overlap
- primary action見切れ
- modal / popup
- unexpected horizontal scroll
- focus indicator
- visual instability

DOMだけで確定せず、画像が必要な項目はscreenshotを正式なevidenceとして使います。

## 12. Step 10: performance / responsiveness

### project thresholdあり

current Authorityにthresholdがある全measurementで、

- measurement
- threshold
- result
- evidence

を結び付けます。

### project thresholdなし

数値は取得するが、独自FAIL thresholdを作らないcaseを確認します。

### Playwright timing

actionability waitとactual input後のresponseを分離できることを確認します。

### Core Web Vitals

metric定義・測定条件を満たす場合だけmetric名を使います。

単一Playwright runをfield percentileの達成判定へ変換しないことを確認します。

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

`_05a_usability-inspection-package-and-evaluation.md` §7のCase A〜Xをすべて含めます。

### real Agent

実Agentがtaskなしのpage inspectionと、taskありのflow inspectionをcanonical live Web targetで完了できることを確認します。環境が利用できない場合はblockedであり、実装完了にはしません。

あわせて、

- objective factとAIの専門評価を分離する
- off-viewport locator shortcutでdiscoverability問題を隠さない
- actionability waitをpost-input responsivenessへ混ぜない
- strict criterionとadvisory guidanceを分ける
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
- ref採番、scope closure、数値計算、threshold比較をdeterministic runtimeへ移している
- runtime generatorとdeterministic validatorを別実装にしている
- objective observationとexpert evaluationを分離する
- applicable standard / binding requirementをcriterion単位で判定できる
- test rule resultとrequirement resultを分離できる
- requirement `satisfied` に必要なpopulation / required checks closureを検証できる
- criterionのapplicability / exception / evidenceを保持する
- advisory guidanceをstrict FAILへ変換しない
- project thresholdがなければ独自FAIL thresholdを作らない
- measurementのmethod / value / unit / evidenceを保持する
- single-run measurementを条件未達のfield metricへ昇格しない
- Playwright auto-scrollでdiscoverability問題を隠さない
- Playwright actionability waitとpost-input responsivenessを分離する
- hidden implementation情報でUI発見を先回りしない
- visual observationをscreenshot等へ追跡できる
- keyboard / focusの全applicable populationをcoverage matrixに従って確認する
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
3. 両Skillのqa-workflow routingと相互連携が成立する

まで完了扱いにしません。

### 全件coverage完了条件

- `_05c_usability-inspection-coverage.md` のWeb execution context matrixを閉じる
- WCAG 2.2の全Success Criteriaをcoverage matrixへ登録し、対象scopeで各行をclosure
- applicableなWAI-ARIA 1.2 / ARIA in HTML requirement populationをclosure
- current public formal / proposed ACT Rulesを全件inventoryし、source status・Format/version・execution mode・実装経路を記録
- ACT外checkをdeterministic-check-catalogへ全件登録
- measurement matrixのapplicable rowをすべて実行または理由付き `measurement-unavailable` へ閉じる
- general inspectionの全上位観点をclosure
- Case A〜XをすべてPASS
- canonical live Web E2EをPASS

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
