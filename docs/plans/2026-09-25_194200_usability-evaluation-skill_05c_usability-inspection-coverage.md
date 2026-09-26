# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` のWeb live inspectionについて、実行条件、responsive / input coverage、WCAG / ARIA / ACT coverage、measurement、Cognitive Walkthrough、E2E完了条件を固定します。

一部のcriterionや一部のsemantic caseだけを実装して完了扱いにしないための正本です。

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

native screenshot / design artifact等は `usability-evaluation` の静的evidenceとして扱えます。native live automationを今回の未実装項目として残しません。

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

## 3. Web実行条件

### 明示条件を優先

user / project Authorityがbrowser、viewport、device、locale、input method、color scheme等を指定した場合はその条件を使用します。

### desktop Web

指定がない場合:

- current projectで使用するbrowser context
- current viewport
- pointer
- keyboard

を基本条件とします。

keyboard passはpointer操作で代替しません。

### responsive / mobile Web

responsive / mobileが対象の場合、次を確認します。

1. project / adopted Design Systemに公開されたbreakpointがある場合は全breakpointを列挙
2. current targetの公開CSS / machine-readable styleからwidth / heightに関係するmedia query / container query boundaryを取得できる場合は列挙
3. 各layout boundaryの直前・boundary・直後で重要情報 / operation / clipping / overflow / overlapを確認
4. WCAG 2.2 SC 1.4.10を評価する場合は、vertical scrolling contentを320 CSS px相当で確認し、該当する例外を評価
5. mobile / touch interactionが対象の場合は `hasTouch=true` のbrowser contextを使い、pointer-only成功をtouch成功へ読み替えない

同じ値の重複boundaryはcanonicalizeします。対象UIに存在しないbreakpointを創作しません。

orientation、zoom、color scheme、reduced motion等は、applicable requirement / project Authority / target featureがある場合にcoverage matrixへ追加し、未確認のまま省略しません。

## 4. discoverabilityとmachine population

DOM / accessibility tree / locatorは次に利用できます。

- standard criterionの対象母集団列挙
- applicability
- machine-readable attribute / state取得
- target発見後のautomation

visual / pointer userがcontrolを発見できた証拠には利用しません。

off-viewport targetのdiscoverability確認ではuser-facing scrollを行います。installed Playwrightがactionの `scroll: "none"` を提供する場合はreachability確認に使い、implicit auto-scroll成功をdiscoverability成功へ変換しません。

## 5. WCAG 2.2 coverage matrix

WCAG 2.2の全Success Criteriaを `references/standards-and-measurements.md` または専用coverage artifactへ登録します。

各rowは次を持ちます。

- Success Criterion
- conformance level: A / AA / AAA
- applicable population
- applicability evidence
- required observations
- related ACT Rule refs
- deterministic check refs
- semantic / interaction check
- exceptions
- execution owner
- evidence refs
- requirement result: satisfied / not-satisfied / undetermined
- limitation

A / AA / AAAをinventoryから省略しません。

projectが特定conformance levelをbinding Authorityとして採用している場合、そのlevelまでをbinding requirementとして扱います。それ以外のlevelもstandard comparisonとして評価できますが、project defect / specification FAILへ自動変換しません。

WCAG conformance claimはfull page等のconformance requirementを満たす場合だけ扱い、component / sample結果からproduct-wide conformanceを宣言しません。

## 6. WAI-ARIA / ARIA in HTML coverage

live target内のrole / state / property / host-language populationを列挙し、適用するWAI-ARIA 1.2 / current ARIA in HTML author requirementをcoverageへ登録します。

各requirementで次を閉じます。

- target population
- host language / role applicability
- required state / property / ownership関係
- machine-readable observation
- semantic exception
- evidence
- requirement result

APG exampleをnormative requirementへ昇格しません。

## 7. ACT Rules coverage

取得時点でW3Cが公開するformal ACT Rulesとproposed ACT Rulesを全件inventoryします。

各ruleについて次を保持します。

- rule ID / URL
- formal / proposed status
- ACT Rules Format version
- accessibility requirements mapping
- applicability
- expectation
- assumptions
- implementation execution mode: automatic / manual / semiAuto
- required observations
- Web-only scopeでの実行可否
- check key / semantic procedure
- limitation

### automatic

machine evidenceだけでrule全体を実行できる場合、`criterion_checks.py` の明示dispatchとして実装します。

### manual / semiAuto

browser ownerが必要evidenceを取得し、Agentがrule本文のapplicability / expectationに沿ってsemantic evaluationします。machine部分だけをrule全体のPASSへ昇格しません。

### Web-only scopeで実行不能

必要能力がnative app、human participant、取得不能external evidence等に依存しWeb live inspectionで閉じられない場合は理由をcoverageへ残し、rule outcomeを捏造しません。そのrule以外のrequired checks / evidenceでもmapped requirementを閉じられない場合だけrequirement resultを `undetermined` とします。

current WAI公開ACT RulesはACT Rules Format 1.1互換として扱い、outcomeは `inapplicable / passed / failed / cantTell / untested` を使用します。formal / proposedはsource statusで区別します。

## 8. ACT外check

ACT Ruleではないmachine checkも `assets/deterministic-check-catalog.json` へ全件登録します。

対象:

- artifact-local ref / cross-reference
- inspection scope closure
- bounding box / target geometry
- spacing calculation
- viewport / overflow geometry
- elapsed calculation
- threshold comparison
- project-specific machine-decidable rule
- ACT Rule implementation helperで、ACT Ruleそのものではないcheck

各checkはsource typeを明示し、独自checkをACT Ruleと呼びません。

## 9. deterministic-check-catalog.json

catalogはmetadataだけを持ち、式DSLやplugin registryにはしません。

各entry:

- check_key
- source_type
- source_rule_ref
- mapped_requirement_refs
- source_status
- act_rules_format_version
- execution_mode
- required_observation_fields
- output_scope
- implementation_dispatch_key
- checked_at / source_version

`criterion_checks.py` は `implementation_dispatch_key` に対応する明示実装だけを実行します。

## 10. performance / responsiveness measurement matrix

次を実装対象として定義します。

### Navigation / rendering diagnostic

取得条件を満たす場合:

- Navigation Timing
- FCP
- LCP
- CLS

### interaction

該当interactionで:

- observed user-facing input event → first visible feedback
- observed user-facing input event → task-ready state
- loading start → completion state

### INP

INPとして報告するのは、current metric定義と必要なinteraction observationを満たす場合だけです。単一の任意elapsedをINPと呼びません。

### 共通measurement contract

各measurement:

- metric / measurement name
- start event
- start acquisition method
- end event / predicate
- end acquisition method
- clock domain
- method
- value / unit
- viewport / device / input method
- browser / environment
- cache / navigation state等、値の解釈に必要な実行条件
- threshold
- threshold Authority ref
- evidence
- result

start / endは同一clock domainで取得します。保証できない場合は `measurement-unavailable` とします。

project thresholdがなければ値は報告しても仕様FAIL thresholdを創作しません。

field percentile / RUMを必要とする判定を単一Playwright runから作りません。

## 11. Cognitive Walkthrough

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

## 12. evidence freshness

PR #11 / #12 merge後のcurrent identity / fingerprint / freshness contractを再利用します。

既存evidenceをcurrentとして再利用するには、少なくとも対象identity、revision / fingerprint、state、environment、viewport / device、role / permission等、判定に影響する条件が今回scopeと一致する必要があります。

一致を確認できないevidenceはhistorical contextとしては使えてもcurrent observationの代替にはしません。

## 13. semantic / E2E validation

`_05a_usability-inspection-package-and-evaluation.md` のCase A〜Xをすべて実Judgeで評価します。

canonical real Agent validationでは次を必須にします。

- taskなしgeneral page inspection
- task / flowありinspection
- desktop pointer + keyboard
- responsive boundary
- mobile / touch applicable case
- accessibility criterion population closure
- ACT automatic case
- ACT manual / semiAuto case
- visual screenshot evidence
- thresholdあり / なしmeasurement
- usability-evaluation read-only連携
- cleanup

環境が利用できない場合はblockedであり、実装完了にしません。

## 14. 完了条件

- general inspectionの全上位観点がclosure
- Web execution condition matrixのapplicable rowがclosure
- WCAG 2.2全Success Criteriaがcoverage matrixへ登録済み
- applicable WCAG populationがclosure
- applicable WAI-ARIA / ARIA in HTML requirement populationがclosure
- current public formal / proposed ACT Rulesが全件inventory済み
- 各ACT Ruleにstatus / Format version / execution mode / implementation pathがある
- ACT外checkがcatalogへ全件登録済み
- applicable measurement matrixがclosure
- Cognitive Walkthrough対象caseが定義手順でclosure
- Case A〜X PASS
- canonical live Web E2E PASS
- blocked 0
