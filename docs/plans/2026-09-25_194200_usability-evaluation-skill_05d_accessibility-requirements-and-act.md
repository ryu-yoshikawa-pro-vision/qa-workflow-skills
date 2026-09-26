# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、general accessibility inspection、WCAG / WAI-ARIA requirement result、ACT Ruleの利用契約を固定します。

formalなWCAG conformance evaluationのscope / sampling / reportは `_01b_wcag-conformance-evaluation-scope-and-contract.md` と `_05f_wcag-conformance-evaluation-package-and-runtime.md` を正本とします。

## 1. owner境界

### usability-inspection

対象UIへapplicableなaccessibility concern / requirementを確認します。

- page / component / flowのgeneral accessibility inspection
- machine-readable observation
- supported ACT Rule
- requirement check
- keyboard / focus / semantics / visual accessibility concern

を扱います。

WCAG-EM sample selectionやproduct-wide conformance evaluationは担当しません。

### wcag-conformance-evaluation

formalなWCAG conformance要求で、

- target version / level
- product scope
- accessibility support baseline
- target exploration
- representative sample
- complete process
- sample evaluation
- structured / random comparison
- report

を所有します。

個別sampleのlive observationでは本ファイルのrequirement / ACT semanticsを再利用できます。

## 2. requirement result

明確なstandard / project binding requirementのresultは、

- `satisfied`
- `not-satisfied`
- `undetermined`

を使用します。

inspection scopeで扱わない項目の `対象外` はrequirement resultではなくscope closure側で保持します。

### not-satisfied

applicable requirementの違反を、必要なscope・evidenceとともに確認できた場合に使用できます。

### satisfied

宣言したevaluation scopeについて必要な、

- applicable population
- exception
- required checks

を閉じた場合だけ使用します。

単一element、単一component、抜き取りsampleがpassedであることだけからpage / productのSuccess Criterionを `satisfied` にしません。

applicable contentが存在しないこと自体がrequirement satisfactionに関係する場合は、そのpopulation closureをevidenceとして保持します。

### undetermined

必要population、exception、manual judgment、required evidence等を閉じられない場合に使用します。

## 3. general accessibility inspection

general inspectionではWCAG 2.2の全Success Criteriaを毎回実行しません。

対象UI・requested scope・project Authorityからapplicable concernを列挙し、少なくとも次を対象にできます。

- semantics / native HTML
- accessible name / description
- role / state / property
- keyboard operation
- focus order / focus visibility
- target size / spacing
- text / non-text alternatives
- labels / instructions / errors
- contrast等、現在の観測手段で判定できるvisual requirement
- reflow / zoom / text spacing等、requested scopeやapplicabilityがある項目
- status message / dynamic update
- input purpose / autocomplete等、target populationがある項目

明確なviolationを確認できたrequirementは `not-satisfied` とできます。

requirement全体のsatisfactionを閉じられない場合は `undetermined` またはObservationだけを保持します。

general inspectionの結果だけでformal WCAG conformance evaluationを完了したと扱いません。

## 4. WAI-ARIA / ARIA in HTML

live target内のrole / state / property / host-language populationに対して、applicableなWAI-ARIA 1.2 / current ARIA in HTML author requirementを評価します。

保持するもの:

- target population
- host language / role applicability
- required state / property / ownership関係
- native HTMLで代替すべき条件
- machine-readable observation
- semantic exception
- evidence
- requirement result

APG exampleはinformative guidanceであり、normative requirementへ昇格しません。

## 5. ACT Rules

ACT RulesはWCAG / ARIA testing methodのinformative sourceとして使用します。

`skills/usability-evaluation/references/source-catalog.md` と `skills/usability-inspection/references/source-catalog.md`、formal evaluation時は `skills/wcag-conformance-evaluation/references/source-catalog.md` からAll ACT Rulesの公式URLを辿れるようにします。

全ACT Rulesをsupported implementationへすることは完成条件にしません。

### supported rule

ACT Ruleをsupported ruleとして登録する条件:

- Web-only scopeへapplicable
- ruleのapplicability / expectation / assumptionsを忠実に実装できる
- required evidenceを現在のbrowser observation契約で取得できる
- machine-onlyかsemantic/manualかを明示できる
- ACT Rules Format 1.1 §4.14.1のconsistencyをofficial examples / requirement mappingで検証できる

条件を満たすruleだけ `test-rule-catalog.json` またはsemantic procedureへ登録します。

### unsupported rule

unsupported ruleはcatalog上のsourceとして存在していてもexecution modeを割り当てません。

評価を実施していないunsupported ruleへ `untested` resultを作りません。

必要なWCAG / ARIA requirementは、ACT Rule以外のobservation / manual evaluationでも評価できます。

## 6. ACT outcome

supported ACT RuleではACT Rules Format 1.1のoutcomeを使用します。

- `inapplicable`
- `passed`
- `failed`
- `cantTell`
- `untested`

使い分けはACT Rules Format 1.1のOutcome定義に従います。

- `inapplicable`: applicabilityを評価し、test subject内にtest targetがない
- `passed / failed`: test targetを評価し、expectation結果を確定した
- `cantTell`: evaluationを開始したが、applicabilityまたはexpectationを完全に判定できない
- `untested`: supported ruleが今回scopeへ選定されたが、test subjectを評価していない

automatic implementationを実行済みなのに必要evidenceが不足した場合、単に `untested` へ落とさず、`cantTell` またはstructured limitationへ閉じます。unsupported ruleにはこれらのoutcome自体を生成しません。

formal / proposedはsource statusとして分離します。

rule outcomeをmapped WCAG / ARIA requirement全体のresultへ自動変換しません。

## 7. ACT implementation consistency

ACT Ruleをsupported implementationとして扱う場合は、ACT Rules Format 1.1 §4.14.1のconsistency判定をfixture化します。

少なくとも次を確認します。

- passed / inapplicable exampleを `failed` と報告しない
- failed exampleを `passed / inapplicable` と報告しない
- consistency評価対象で `untested` を残さない
- failed exampleの少なくとも1件を `failed` と識別できる
- implementationがreportするmapped accessibility requirementsがruleのconformance / secondary requirement mappingと整合する
- 1 exampleに複数outcomeがある場合はACT Rules Format 1.1のconsistency判定順序を使用する

manual / semiAuto implementationでも同じconsistency契約を使います。

条件を満たせないcheckはそのACT Ruleのsupported implementationとは扱わず、ACT Rule identityから分離したproject rule / observation aidとして扱います。

## 8. test-rule-catalog

catalogへ登録するのはtest ruleとしてidentityを持つsupported ruleだけです。

含める:

- supported ACT Rule
- project固有ruleで、明示的なrule identityを持つもの

含めない:

- ref採番
- artifact cross-reference
- scope closure
- bounding box算術
- elapsed計算
- threshold比較
- viewport geometry helper

これらは `inspection_structure.py` / `measurement.py` の責務です。

catalog field:

- check_key
- source_type: act-rule / project-rule
- source_rule_ref
- source_status: formal / proposed / project
- act_rules_format_version（ACT Ruleの場合）
- mapped_requirement_refs
- execution_mode: automatic / manual / semiAuto
- required_observation_fields
- output_scope
- implementation_dispatch_key（automaticの場合）
- checked_at / source_version

`source_type` と `source_status` を同じfieldへ混ぜません。

## 9. formal WCAG evaluationとの再利用

`wcag-conformance-evaluation` が個別sampleのrequirement checkを行う際も、

- requirement result vocabulary
- population closure
- WAI-ARIA / ARIA in HTML
- supported ACT Rule
- ACT consistency

は本ファイルの契約を再利用します。

ただし、

- sample selection
- WCAG-EM Step 4.3 comparison
- evaluation statement
- product-wide claim

は本ファイルで決めません。

## 10. 完了条件

- general accessibility inspectionとformal WCAG conformance evaluationのownerが分離
- Success Criterion / requirement resultを `satisfied / not-satisfied / undetermined` へ閉じられる
- sample / element resultをpage / productへ不当に昇格しない
- applicable WAI-ARIA / ARIA in HTML requirementを評価できる
- APGをnormative requirementへ昇格しない
- supported ACT Ruleだけがcatalog / semantic procedureへ登録される
- unsupported ACT Ruleへexecution modeや架空の `untested` resultを作らない
- supported ACT RuleはACT Rules Format 1.1 §4.14.1 consistency fixtureをPASS
- ACT rule resultとrequirement resultを分離
- helper処理をtest-rule-catalogへ混ぜない
