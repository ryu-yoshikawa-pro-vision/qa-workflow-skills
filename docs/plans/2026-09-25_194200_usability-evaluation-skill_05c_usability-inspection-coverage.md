# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` のWeb live inspectionについて、general inspectionのscope、Web実行条件、responsive / mobile、discoverability、Cognitive Walkthrough、evidence freshness、E2E完了条件を固定します。

accessibility / WCAG conformanceは `_05d_accessibility-requirements-and-act.md`、performance measurementは `_05e_performance-measurement.md`、browser observation request / fixed probe / result normalizationは `_05g_usability-inspection-browser-observation-contract.md` を正本とします。

## 1. live対象

能動操作対象はPlaywright / browser経路で到達可能なWeb UIだけです。

対象:

- desktop Web
- responsive Web
- mobile Web

対象外:

- native iOS / Android app
- desktop native app
- human participantを用いるusability study

native screenshot / design artifact等は `usability-evaluation` の静的evidenceとして扱えます。native live automationを未実装項目として残しません。

## 2. general inspectionのscope

ユーザーが特定観点へ限定していないgeneral inspectionでは、次の全上位観点をscope rowへ作ります。

- interaction / operability
- feedback / system status
- error prevention / recovery
- accessibility
- visual integrity / responsive
- measurable standard criteria
- user-facing performance / responsiveness

各rowは実操作前に `今回確認する / 対象外` へ固定し、完了時に `問題を確認 / 問題なし / 判定不能 / 対象外` へ閉じます。

対象外にはpopulation不存在、責務外、必要evidenceを安全に取得できない等の理由を必須にします。

task / flowはユーザーまたは案件が明示した場合だけ追加します。

scope rowの有無は `_05g` のinspection mode契約で機械化します。`general` は上記7観点を全件生成し、`scoped` はsemantic layerがraw依頼を正規aspect keyへmappingした集合だけを生成し、`formal-handoff` はhandoff required scopeを正本にします。LLMが毎回7観点のON/OFFを完成rowとして入力しません。

accessibility rowを選んだことだけでWCAG conformance evaluationへ切り替えません。

## 3. Web実行条件

### 明示条件を優先

user / project Authorityがbrowser、viewport、device profile、locale、input method、color scheme等を指定した場合はその条件を使用します。

### desktop Web

指定がない場合:

- current projectで使用するbrowser context
- current viewport
- pointer
- keyboard

を基本条件とします。

keyboard passはpointer操作で代替しません。

## 4. responsive / touch / mobileを分離する

### responsive viewport inspection

layout breakpointやWCAG reflow等を確認する目的です。

- current browser engineを維持
- project / adopted Design Systemのbreakpointを列挙
- current targetから取得できるmedia query / container query boundaryを列挙
- boundary直前 / boundary / 直後を確認
- viewport変更だけでdevice-specific behaviorを確認したとは扱わない

### touch-capable inspection

touch targetやtap操作等を確認する目的です。

- `hasTouch=true` 等のtouch-capable contextを使用
- touch成功をpointer成功から推測しない
- touch-capableであることだけをmobile device emulationと呼ばない

### mobile device emulation

mobile browser behavior自体を確認する要求で使用します。

user / projectがdevice profileを指定した場合はそのprofileを使います。

指定がない場合は、現在利用するPlaywright実行経路が提供するbuilt-in device / generic mobile profileを使用し、実際に使用した

- browser engine
- device profile
- viewport
- screen
- user agent
- device scale factor
- `hasTouch`
- `isMobile`

を成果物へ記録します。

現在の実行経路で完全なmobile profileを構成できない場合は、responsive viewport / touch-capable inspectionとして実行できる範囲を明示し、device-specific mobile behaviorを確認済みとは扱いません。

`isMobile` 等がbrowser engineでunsupportedな場合も同様です。

## 5. responsive coverage

### general inspectionの既定

`general` modeでは `visual-responsive` rowを必ず生成するため、responsive確認を「ユーザーがresponsiveと言った場合だけ」にしません。

1. project / adopted Design Systemに公開されたboundaryがある場合は全件取得し、CSS pxとして明示済みの値または `_05g` の固定procedureでcurrent browser上のCSS pxへ正規化できる値をmachine boundaryとして扱う
2. current targetのCSSOMから `_05g` のresponsive condition inventoryを取得する。既知の有効なmedia / container queryをPlan側parserの対応範囲だけで省略せず、browserが評価できるconditionを保持する
3. boundary inventoryがcompleteで1件以上ある場合、`observation_contract.py` がduplicate除去・sort・before / boundary / after集合を生成し、全boundaryを確認する
4. inventoryがcompleteでboundaryが0件の場合、current viewportでvisual integrityを確認し、responsive boundary sub-scopeは `not-applicable:no-boundary` として閉じる
5. unreadable / unsupported query等でinventoryがincompleteの場合、project / Design System Authority等の別sourceで不足範囲を閉じられなければ `visual-responsive` を `問題なし` にせず `判定不能` とする

touch-capable inspection / mobile device emulationは引き続き明示要求またはproject条件がある場合だけ追加し、responsive viewport inspectionと混同しません。

### boundary実行

1. project / adopted Design Systemに公開されたbreakpointがある場合は全boundaryを列挙
2. current targetのCSSOM / machine-readable styleからmedia / container size / style / scroll-state conditionを `_05g` の `responsive-conditions` probeで取得し、size conditionだけ `responsive-boundaries` でnumeric transitionへmaterializeする
3. `observation_contract.py` がboundary detectionとexecution feasibilityを分離し、canonicalize / duplicate除去 / sortを行う
4. `executable` なboundaryだけbefore / boundary / after target stateを生成し、重要情報 / operation / clipping / overflow / overlapを確認する。normalizedできても安全にそのstateを実現できないboundaryは `not-executable / incomplete` として残す
5. applicable requirementがある場合はorientation、zoom、color scheme、reduced motion等もscopeへ追加

CSSOM / browser評価の契約は `_05g` を正本とします。size queryはbrowser自身のcondition evaluationと実際のmatch transitionを正本にし、`px / em / rem / viewport-relative / container-relative / calc()` 等を独自換算しません。`var()` 等もsource textから手計算せず、browserがconditionを評価できる場合はその結果を利用します。style / scroll-state queryは数値boundaryへ変換せずpresentation variationとして扱います。

対象UIに存在しないbreakpointを創作しません。

cross-origin stylesheet等をbrowserから読めず、project / adopted Design SystemのAuthorityでも不足boundaryを閉じられない場合はboundary inventoryをcomplete扱いしません。`incomplete` とunreadable source情報を保持し、LLMが「たぶん他にない」と補完しません。

## 6. discoverabilityとmachine population

DOM / accessibility tree / locatorは次に利用できます。

- requirement / test ruleの対象母集団列挙
- applicability
- machine-readable attribute / state取得
- target発見後のautomation

visual / pointer userがcontrolを発見できた証拠には利用しません。

off-viewport targetのdiscoverability確認ではuser-facing scrollを行います。installed Playwrightがactionのimplicit scrollを抑止する正式機能を提供する場合はreachability確認に使い、implicit auto-scroll成功をdiscoverability成功へ変換しません。

target発見後のtargeted scrollはautomation補助として使えますが、discoverability evidenceへ数えません。

## 7. visual / responsive concern

対象UIのapplicable state / viewport boundaryで次を確認します。

- clipping
- overflow
- overlap
- important / primary action見切れ
- modal / popup positioning
- unexpected horizontal scroll
- focus indicator visibility
- visual instability
- text loss / unreadable wrapping
- status / error visibility

DOM geometryだけで意味を確定できない場合はscreenshotを正式evidenceとして使用します。

## 8. Cognitive Walkthrough

次のいずれかが明示された場合に実行します。

- learnabilityの確認
- 新機能を初見で理解できるかの専門評価
- specified flowのstepごとのdiscoverability / feedback診断

intended flowはcurrent specification / user flow / validated TC等から確認し、確認できなければWalkthroughを `判定不能` とします。

各stepで4問を確認します。

1. ユーザーが正しい効果を達成しようとする根拠があるか
2. 正しいactionを認識できるか
3. actionと期待する効果を結び付けられるか
4. action後に進行・結果を認識できるfeedbackがあるか

各回答にevidence、reference、status reasonを保持します。

## 9. evidence freshness

PR #12 / #13 merge後の実装が実際に提供するartifact identity / revision / SHA / content identity / currentness条件を再利用します。

上流成果物がfingerprintを正式に持つ場合だけ、そのfingerprintを利用します。PR #14のためにPR #12成果物へ新しいfingerprint contractを要求しません。

既存evidenceをcurrentとして再利用するには、少なくとも判定に影響する次の条件を今回scopeと照合します。

- target identity
- artifact revision / content identity
- environment / origin
- version / build（取得できる場合）
- viewport / device profile
- role / permission
- locale / feature flag / test data等、元成果物がcurrentness条件として保持する値

一致を確認できないevidenceはhistorical contextとしては使えてもcurrent observationの代替にはしません。

## 10. semantic / E2E validation

`_05a_usability-inspection-package-and-evaluation.md` のCase A〜AGを実Judgeで評価します。

canonical real Agent validationは `_06c_canonical-live-validation.md` を正本とし、repository-controlled fixtureで次を含めます。

- taskなしgeneral page inspection
- task / flowありinspection
- desktop pointer + keyboard
- responsive boundary
- touch-capable case
- fixtureで提供可能なmobile device emulation
- accessibility inspection
- formal WCAG conformance request routing（wcag-conformance-evaluationへhandoff）
- visual screenshot evidence
- fixed probe request → browser result → `observation_contract.py` normalization
- responsive boundary sourceのreadable / unreadable両case
- thresholdあり / なしmeasurement
- fixtureまたは保存済みprovenanceで閉じられるexternal Core Web Vitals sourceあり / なしの契約case
- usability-evaluation read-only連携
- cleanup

外部実対象、実アカウント、特定assistive technology等が必要なacceptanceは別statusです。それらが利用できないことだけでrepository implementationを未完了にしません。

## 11. 完了条件

- general inspectionの全上位観点がclosure
- responsive / touch / mobileの実行条件が区別される
- applicable responsive boundaryがclosure
- discoverabilityとmachine populationが分離される
- applicable visual concernがclosure
- Cognitive Walkthrough対象caseが定義手順でclosure
- PR #12 currentness契約に存在しないfingerprintを要求しない
- `_05d_accessibility-requirements-and-act.md` のgeneral accessibility / WAI-ARIA / ACT完了条件を満たす
- formal WCAG conformance要求を `wcag-conformance-evaluation` へroutingできる
- `_05e_performance-measurement.md` の完了条件を満たす
- Case A〜AG PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical live Web E2E PASS
- repository-controlled validationのblocked 0。external acceptance未実施は別statusとして扱う
