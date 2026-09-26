# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 実装開始条件

`usability-inspection` の実装は、次を確認してから開始します。

- PR #11 / #12 / #13がmainへmerge済み
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

最低限:

- WCAG 2.2 / Understanding
- WAI-ARIA / ARIA in HTMLの必要箇所
- ISO 9241-110 interaction principles
- Cognitive Walkthroughの代表的methodology
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

- inspection scope
- objective observation
- standard / binding criterion check
- measurement
- Playwright action trace
- optional task / flow result
- usability-evaluation ref
- Finding ref

task / persona / prior knowledgeを必須schemaにしません。

## 5. Step 3: criterion / measurement contract

fixtureで次を成立させます。

- criterion ref
- applicability
- exception
- observed fact / value
- unit
- PASS / FAIL / 判定不能 / 対象外
- project binding時のAuthority ref
- thresholdの有無
- thresholdなしの場合に独自FAILを作らない
- advisory guidanceをstrict FAILへ変換しない
- 単一criterion結果を製品全体のconformanceへ昇格しない

task / flow未指定caseでも成果物が成立することを確認します。

## 6. Step 4: browser observation contract

PR #12 merge後のbrowser実行基盤を再利用します。

初版のlive実行対象は既存Playwright経路で到達可能なWeb UIに限定します。

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

`usability-inspection` がbrowser / session ownerになります。

## 7. Step 5: Playwright固有の検査境界

通常E2E向けのPlaywright behaviorでusability frictionを隠さないことを先に検証します。

### auto-scroll

代表case:

- controlはDOM上に存在する
- current viewportからは見えない
- locator.click()なら操作可能

確認:

- visual / pointer inspectionでlocatorのimplicit auto-scrollをdiscoverability成功にしない
- 必要なscrollをexplicit user actionとして扱う
- scroll前後のevidenceを残せる

### locator

確認:

- role / name locatorは、user-facing情報から対象と判断した後のautomation手段として使える
- test id / hidden DOM / implementation-specific selectorでUI発見を先回りしない

### actionability / auto-wait

代表case:

- controlが操作可能になるまで待機時間あり
- input dispatch後のvisible feedbackは短い

確認:

- pre-action actionability waitとpost-input responsivenessを分離
- locator action呼び出し開始からのwall-clockをそのままuser response timeへしない
- actionability wait自体にUI上の問題がある場合は別Observationにできる

## 8. Step 6: page inspection vertical slice

taskを与えない代表caseで、1画面 / 1機能を端から端まで検査します。

確認:

- inspection scope固定
- initial observation
- safe interaction
- keyboard / focus
- screenshot
- responsive observation
- criterion check
- measurement
- usability-evaluation連携
- cleanup
- output validator

「taskがないので実行不能」にならないことを確認します。

この段階では全製品scanへ広げません。

## 9. Step 7: accessibility / standard checks

適用可能な代表criterionを実際に判定します。

最低限、代表caseとして次を含めます。

- target size / spacing
- focus visible
- keyboard operation
- error identification
- reflow / responsive
- accessible name / role / state

確認:

- applicability / exception
- observation / measurement
- criterion result
- evidence
- product-wide conformanceへ昇格しないこと

criterionの具体値や例外はcurrent referenceを正本にし、Plan記載値だけを実装へ固定しません。

## 10. Step 8: visual / responsive

代表caseで、

- clipping
- overflow
- overlap
- primary action見切れ
- modal / popup
- unexpected horizontal scroll
- focus indicator
- visual instability

を確認します。

DOMだけで確定せず、画像が必要な項目はscreenshotを正式なevidenceとして使います。

## 11. Step 9: performance / responsiveness

### project thresholdあり

current Authorityにthresholdがある代表caseで、

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

## 12. Step 10: optional task / flow

task / flowが明示された代表caseだけ実施します。

確認:

- task / flow未指定では必須にならない
- 指定されたflowは実操作できる
- detailed TC実行要求はtest-executionへrouting
- task resultをTC PASS / FAILへ変換しない
- Agent / tool limitationをproduct defectへ自動変換しない

## 13. Step 11: Cognitive Walkthrough optional case

learnabilityを重点確認する代表caseでだけCognitive Walkthroughを利用します。

確認:

- 通常inspectionの固定工程ではない
- intended flowを確認できるsourceがある場合だけ利用
- 正しいstep sequenceを創作しない
- 独立Skill / runtimeを追加しない

## 14. Step 12: usability-evaluation統合

objective observation、criterion result、measurementを `usability-evaluation` へ渡します。

確認:

- inspectionがbrowser ownerを維持
- evaluationがread-only
- objective factとexpert evaluationを混ぜない
- standard / project binding resultとadvisory evaluationを混ぜない
- additional observationはinspection側でscope / safety確認
- finding traceability

同一sessionへの並行操作を行いません。

## 15. Step 13: workflow integration

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

## 16. Step 14: repository eval

### trigger

repository標準件数に合わせます。

### deterministic

最低限:

- output schema
- inspection scope closure
- observation / criterion / measurement refs
- criterion result / applicability / evidence
- project Authority ref
- threshold整合
- task optionality
- Playwright observation fields
- cleanup
- evaluation / Finding ref

### semantic

`_05a_usability-inspection-package-and-evaluation.md` §7のcaseを最低限含めます。

### real Agent

利用可能な環境で、実Agentがtaskなしのpage inspectionを完了できることを確認します。

あわせて、

- objective factとAIの専門評価を分離する
- off-viewport locator shortcutでdiscoverability問題を隠さない
- actionability waitをpost-input responsivenessへ混ぜない
- strict criterionとadvisory guidanceを分ける
- taskが指定された場合だけtask modeを使う

ことを確認します。

## 17. Step 15: repository integration

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

## 18. 完了条件

次をすべて満たしたら `usability-inspection` 実装完了とします。

- Agent Skills仕様を満たす
- task / user personaなしでもlive Web UIを検査できる
- inspection scopeを固定し、選定観点をclosureできる
- objective observationとexpert evaluationを分離する
- applicable standard / binding criterionをcriterion単位で判定できる
- criterionのapplicability / exception / evidenceを保持する
- advisory guidanceをstrict FAILへ変換しない
- project thresholdがなければ独自FAIL thresholdを作らない
- measurementのmethod / value / unit / evidenceを保持する
- single-run measurementを条件未達のfield metricへ昇格しない
- Playwright auto-scrollでdiscoverability問題を隠さない
- Playwright actionability waitとpost-input responsivenessを分離する
- hidden implementation情報でUI発見を先回りしない
- visual observationをscreenshot等へ追跡できる
- keyboard / focus representative caseを確認する
- task / flowは指定された場合だけ扱う
- detailed TC実行をtest-executionと分離する
- Cognitive Walkthroughをoptional techniqueとして扱う
- browser ownerがusability-inspectionである
- usability-evaluationとのread-only連携が成立する
- same session concurrent manipulationを要求しない
- side-effect / cleanup契約を満たす
- FindingがPR #13契約へ接続する
- human usability studyを実施したと偽らない
- test-target-inspection / test-execution / exploratory-testingと責務重複しない
- trigger / deterministic / semantic eval PASS
- repository validation PASS
- README / EVALS / Skill一覧整合
- git diff --check PASS

## 19. Plan全体の完了

本PRの後続実装は、

1. `usability-evaluation` が `_06_evaluation-ci-implementation-order.md` の完了条件を満たす
2. `usability-inspection` が本ファイル§18の完了条件を満たす
3. 両Skillのqa-workflow routingと相互連携が成立する

まで完了扱いにしません。

## 20. 対象外

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
