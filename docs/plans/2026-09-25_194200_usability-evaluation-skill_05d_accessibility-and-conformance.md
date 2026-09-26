# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` におけるaccessibility inspection、WCAG conformance evaluation、WAI-ARIA / ARIA in HTML、ACT Rulesの責務境界を固定します。

一般的なUI inspectionと、WCAG conformance evaluationを同じ完了条件へしません。

## 1. 2つの実行経路

### accessibility inspection

次のような要求です。

- この画面のaccessibilityも確認して
- keyboard / focus / accessible nameを確認して
- UIの使い勝手とaccessibility上の問題を見て

この経路では、live targetへapplicableなaccessibility concern、明確に判定可能なrequirement、supported test ruleを確認します。

WCAG全体へのconformance claimは作りません。

### WCAG conformance evaluation

次のような要求です。

- WCAG 2.2 AAに適合しているか評価して
- このWeb productのWCAG conformance evaluationをして
- projectのrelease gateとしてWCAG適合評価をして

この経路ではWCAG-EM 2.0をmethodologyとして使用します。

## 2. conformance evaluationの必須入力

WCAG conformance evaluationでは、評価開始前に次を確定します。

- target WCAG version
- target conformance level
- evaluation scope
- product / page / view / stateの集合
- complete processの有無
- technologies relied upon
- user agent / assistive technology前提がproject Authorityで指定される場合はその条件
- excluded scopeと根拠
- project Authority / release gateとの関係

target level等をproject / user要求から確定できない場合は勝手にAA等を選ばず `unresolved` とします。

## 3. WCAG-EM 2.0

explicit conformance evaluationではcurrent WCAG-EM 2.0に従い、少なくとも次の工程を成果物へ対応付けます。

1. evaluation scopeを定義
2. target productを探索
3. representative sampleを選定
4. selected sampleを評価
5. findingsを集約・報告

representative sampleを選んだことと、製品全体の全DOM nodeを全件scanしたことを同義にしません。

WCAG-EMを一般的なpage inspectionへ無条件適用しません。

## 4. WCAG Success Criterion result

requirement resultは、

- `satisfied`
- `not-satisfied`
- `undetermined`

を使用します。

### `not-satisfied`

applicable requirementの違反を、必要なscope・evidenceとともに確認できた場合に使用できます。

### `satisfied`

Success Criterionを `satisfied` とするのは、そのresultを宣言するscopeについて必要なpopulation、exception、required checksを閉じた場合だけです。

単一element、単一component、抜き取りsampleがpassedであることだけから、page / productのSuccess Criterionを `satisfied` にしません。

### `undetermined`

必要population、exception、manual judgment、complete process等を閉じられない場合に使用します。

## 5. WCAG-EM評価報告とWCAG conformance claimを分離する

### WCAG-EM evaluation report

explicit WCAG conformance evaluationでは、WCAG-EM 2.0 Step 5.1に従いStep 1〜4のoutcomeを記録します。

成果物には少なくとも次を持ちます。

- evaluation type: `wcag-em-2-evaluation`
- evaluation date / period
- evaluator
- evaluation commissioner。self-evaluationの場合はself-evaluationであることと責任主体を記録
- target WCAG title / version / URI
- target conformance level
- digital product scope
- accessibility support baseline
- technologies relied upon
- target exploration結果
- representative sample set
- complete process set
- sampleごとのSuccess Criterion / conformance requirement result
- unmet Success Criterion / conformance requirementの例
- evaluation method / browser / tool / assistive technology等、記録可能な実行条件
- limitations
- Finding refs

secret・credential等はPR #12のevidence安全契約に従い、reportへ実値を埋め込みません。

### evaluation statement

WCAG-EM 2.0 Step 5.3に相当するevaluation statementはoptionalです。

作成するのは次をすべて満たす場合だけです。

- WCAG-EM 2.0のnon-optional methodology requirementをすべて満たす
- evaluationで選定した全sampleがStep 1.2のconformance targetを満たす
- product ownerがstatementのvalidityを担保しaccuracyを維持する責任を明示的に引き受ける

条件を1つでも確認できない場合はevaluation reportだけを作り、statementを生成しません。

statementを作成する場合は少なくとも、

- issued date
- WCAG title / version / URI
- evaluated conformance level
- digital product scope
- technologies relied upon
- accessibility support baseline

を保持します。partial conformance statementを扱う場合はWCAG-EM 2.0 Step 5.3の追加fieldを保持します。sample評価から分かる範囲を超えて表現しません。

### WCAG conformance claim

WCAG-EMのrepresentative sampleがすべてtargetを満たしたことだけでは、製品全体のWCAG conformance claimを作りません。

WCAG conformance claimを作成できるのは、claim scopeに含まれる全Web page / complete processがWCAG 2のclaim要件を満たすことを別途確認できる場合だけです。

この条件を満たせない通常のWCAG-EM評価では、

- evaluated sampleでtargetを満たした
- evaluated sampleにnon-conformanceを確認した
- evaluation全体として未確定事項がある

というevaluation outcomeを報告し、product-wide `conforms` を宣言しません。

general accessibility inspectionではconformance claimもWCAG-EM evaluation statementも作りません。

WCAG-EM 2.0 Step 5.4のaggregated scoreはoptionalですが、本Skillは独自UX / accessibility総合scoreを正本にしないため生成しません。

## 6. general accessibility inspection

general inspectionではWCAG 2.2の全Success Criteriaを毎回実行しません。

対象UI・requested scope・project Authorityからapplicable concernを列挙し、次を確認します。

- semantics / native HTML
- accessible name
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

明確なviolationを確認できたrequirementは `not-satisfied` とできます。requirement全体のsatisfactionを閉じられない場合は `undetermined` またはObservationだけを保持します。

## 7. WAI-ARIA / ARIA in HTML

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

## 8. ACT Rules

ACT RulesはWCAG / ARIA testing methodのinformative sourceとして使用します。

`skills/usability-evaluation/references/source-catalog.md` と `skills/usability-inspection/references/source-catalog.md` にはAll ACT Rulesの公式URLを保持します。

本Skillは「全ACT Rules実装済み」を完成条件にしません。

### supported rule

ACT Ruleを本Skillのsupported ruleとして登録する条件:

- live Web scopeへapplicable
- ruleのapplicability / expectation / assumptionsを忠実に実装できる
- required evidenceを現在のbrowser observation契約で取得できる
- machine-onlyかsemantic/manualかを明示できる
- ACT Rules Format 1.1 §4.14.1のconsistencyをofficial examples / requirement mappingで検証できる

条件を満たすruleだけ `test-rule-catalog.json` またはsemantic procedureへ登録します。

### unsupported rule

未実装ruleが存在してもWCAG evaluation自体を未完了にはしません。ACT RulesはWCAG conformanceの必須条件ではありません。

必要なWCAG requirementは、ACT Rule以外の観測・manual evaluationで評価できます。

## 9. ACT outcome

supported ACT RuleではACT Rules Format 1.1のoutcomeを使用します。

- `inapplicable`
- `passed`
- `failed`
- `cantTell`
- `untested`

formal / proposedはsource statusとして分離します。

rule outcomeをmapped WCAG / ARIA requirement全体のresultへ自動変換しません。

## 10. ACT implementation consistency

ACT Ruleをsupported implementationとして扱う場合は、ACT Rules Format 1.1 §4.14.1のconsistency判定をfixture化します。

少なくとも次を確認します。

- passed / inapplicable exampleを `failed` と報告しない
- failed exampleを `passed / inapplicable` と報告しない
- consistency評価対象で `untested` を残さない
- failed exampleの少なくとも1件を `failed` と識別できる
- implementationがreportするmapped accessibility requirementsがruleのconformance / secondary requirement mappingと整合する
- 1 exampleに複数outcomeがある場合はACT Rules Format 1.1のconsistency判定順序を使用する

manual / semiAuto implementationでも同じconsistency契約を使います。

この条件を満たせないcheckはそのACT Ruleのsupported implementationとは扱わず、独自の部分check / observation aidとしてACT Rule identityから分離します。

## 11. test-rule-catalogとの関係

catalogへ登録するのはtest ruleとしてidentityを持つcheckだけです。

含める:

- supported ACT Rule
- project固有のmachine-decidable requirement checkで、明示的なrule identityを持つもの

含めない:

- ref採番
- artifact cross-reference
- scope closure
- bounding box算術
- elapsed計算
- threshold比較
- viewport geometry helper

これらは `inspection_structure.py` / `measurement.py` の責務です。

catalogのfield:

- check_key
- source_type: act-rule / project-rule
- source_rule_ref
- source_status: formal / proposed / project
- act_rules_format_version（ACT Ruleの場合）
- mapped_requirement_refs
- execution_mode: automatic / manual / semiAuto
- required_observation_fields
- output_scope
- implementation_dispatch_key
- checked_at / source_version

`source_type` と `source_status` を同じfieldへ混ぜません。

## 12. 完了条件

- general accessibility inspectionとWCAG conformance evaluationのtrigger / outputが分離されている
- conformance evaluationはWCAG-EM 2.0工程へ追跡できる
- target WCAG version / level / scopeを創作しない
- Success Criterionの `satisfied` をsample結果から昇格しない
- representative sampleだけからproduct-wide WCAG conformance claimを作らない
- WCAG-EM evaluation reportの必須outcomeを記録できる
- optional evaluation statementは全non-optional methodology requirement / 全sample target達成 / product owner commitmentが確認できる場合だけ生成する
- evaluation statementとWCAG conformance claimを区別する
- aggregated scoreを生成しない
- applicable WAI-ARIA / ARIA in HTML requirementを評価できる
- APGをnormative requirementへ昇格しない
- supported ACT Ruleだけがcatalog / semantic procedureへ登録される
- supported ACT RuleはACT Rules Format 1.1 §4.14.1のconsistency fixtureをPASS
- unsupported ACT Ruleが存在してもWCAG評価をblockしない
- test rule resultとrequirement resultを分離する
