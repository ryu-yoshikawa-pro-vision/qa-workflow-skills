# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` がtarget WCAG version / levelから導出した全Success Criterionについて、各sampleで「何を確認し、どの処理が担当し、何が不足すると完了できないか」を固定します。

目的は、target levelのSuccess Criterion集合を列挙するだけで終わらせず、各criterionの評価経路を機械的にmaterializeし、LLMが評価対象のcriterionを選択・省略したり、実装時に評価方法をその場で決めたりしないことです。

WCAG-EM 2.0のsample / process / report契約は `_05f_wcag-conformance-evaluation-package-and-runtime.md`、live browser observationは `_05g_usability-inspection-browser-observation-contract.md`、general accessibility / ACT Rule semanticsは `_05d_accessibility-requirements-and-act.md` を正本とします。

## 1. owner境界

`wcag_requirements.py` はtarget WCAG version / levelからrequired Success Criterion集合を導出します。

`wcag_criterion_plan.py` は、そのrequired集合とversioned requirements assetのevaluation metadataから、sample / processごとのcriterion evaluation planを全件materializeします。

`usability-inspection` は、planが要求するlive observation / measurement / supported ACT Ruleをbrowser ownerとして実行します。

`wcag-conformance-evaluation` のsemantic layerは、machine evidenceだけで決められないapplicability、exception、meaning、assistive technology上の評価、manual judgmentを担当します。

`wcag_em_structure.py` はcurrentなcriterion evaluation rowがrequired集合をすべて閉じていることを確認してsample resultをmaterializeします。

LLMはrequired Success Criterion集合、criterion row、required machine step、未完了criterion集合、summary countを手作成しません。

## 2. versioned requirements assetへ追加するevaluation metadata

既存の

- `assets/wcag-2.0-requirements.json`
- `assets/wcag-2.1-requirements.json`
- `assets/wcag-2.2-requirements.json`

の各Success Criterion rowへevaluation metadataを追加します。別のgeneric rule catalogは作りません。

各Success Criterionは少なくとも次を持ちます。

```json
{
  "criterion_ref": "wcag22:2.4.2",
  "evaluation": {
    "procedure_ref": "source item ref",
    "required_capabilities": ["dom"],
    "machine_steps": ["act:2779a5"],
    "semantic_steps": ["descriptive-title"],
    "assistive_technology_required": false,
    "external_evidence_allowed": false
  }
}
```

`evaluation` が存在しないSuccess Criterionをsupported WCAG versionのrequired集合へ含めません。3 versionのassetは既存の `static_data_versions` / approved hash契約の対象なので、evaluation metadataもhashへ含めます。

### `procedure_ref`

W3CのSuccess Criterion、Understanding、Technique / Failure、ACT Rule等、今回の評価procedureを追跡するsource item refです。

Techniqueを唯一の適合方法へ昇格しません。複数の評価方法があり得るcriterionでは、本Skillが採用するprocedureと不足時のsemantic/manual経路を明示します。

### `required_capabilities`

fixed vocabularyです。

- `dom`
- `accessibility-semantics`
- `keyboard`
- `focus`
- `visual`
- `viewport`
- `computed-style`
- `timing`
- `assistive-technology`
- `external-evidence`

未知値を許可しません。

### `machine_steps`

現在の実装で決定論的に実行するstepだけを固定keyで列挙します。式や任意JavaScriptをassetへ入れません。

少なくとも次を実装対象にします。

- supported ACT Rule dispatch
- target geometry / spacing calculation
- contrast ratio calculation
- viewport / scroll extent / overflow calculation
- elapsed / threshold calulation
- fixed string emptiness等かsupported ACT Ruleが要求するmachine comparison

machine stepがcriterion全体を満たすことを意味しません。machine resultがcriterion全体の `satisfied` を�{��明できるかはcriterion metadataで明示し、既定ではfalseです。

### `semantic_steps`

意味判断が必要な確認項目を有限のprocedure keyで保持します。自然言語本文をruntime rule DSLとして解釈しません。

例:

- accessible nameが目的を表すか
- page titleが内容 / purposeを表すか
- contrast対象population / exception
- target size exception
- focus orderの意味妥当性
- status messageの意味
- language / human-languageの判断

procedure keyの内容はSkill referenceへ追跡できるようにします。

### assistive technology / external evidence

必要なcriterionでは `assistive_technology_required=true` とします。

field data、既存監査結果、project instrumentation等を正式evidenceとして利用できるcriterionだけ `external_evidence_allowed=true` とし、source / version / environment / freshnessを必須にします。

必要なassistive technologyやexpertiseを利用できない場合、LLMの推測で閉じません。

## 3. criterion evaluation plan

`wcag_criterion_plan.py materialize` はsample / processごとにrequired Success Criterion全件をrow化します。

各row:

- criterion evaluation ref
- sample ref
- process ref（存在する場合）
- criterion ref
- target WCAG version / level
- procedure ref
- required capabilities
- required machine step refs
- required semantic step refs
- assistive technology requirement
- external evidence requirement
- observation request refs
- measurement refs
- supported ACT Rule result refs
- semantic/manual decision refs
- status: `pending / in-progress / satisfied / not-satisfied / undetermined / blocked`
- limitation / blocker

criterion evaluation refはartifact-localに `CRIT-001` から決定論的に採番します。

required criterion setとrow setの集合差分はscriptが計算し、差分が1件でもあればsample evaluationをcomplete扱いしません。

## 4. live observation requestへの変換

`wcag_criterion_plan.py` はcriterion metadataから必要capabilityとmachine stepを集約し、formal handoffへ渡すobservation requirementを生成します。

同一sample / stateで共有できるprobeはdeduplicateします。

例:

- `dom` + supported ACT Rule → title / element population / relevant DOM fields
- `accessibility-semantics` → role / accessible name / description / state
- `viewport` → viewport-state / element-geometry
- `computed-style` →必要propertyだけ
- `visual` →必要state / viewportのscreenshot
- `timing` →fixed interaction timing request

LLMはcriterionごとにprobe keyを手列挙しません。

machine observationの具体的なprobeへの変換は `_05g` の `observation_contract.py` が所有します。

## 5. 現時点でscriptへ移すmachine処理

すでにPlanの目的内で、入力が揃えば決定論的に処理できるものは今回実装します。

### target geometry / spacing

`measurement.py` がnormalized bounding box / neighboring target geometryから必要なwidth / height / spacingを計算します。

WCAG criterionのexception、equivalent target、inline target等の意味判断はsemantic layerに残します。

### contrast ratio

`measurement.py` がnormalized sRGB foreground / effective background colorからrelative luminanceとcontrast ratioを計算します。

- alpha合成後のeffective colorをbrowser probeで確定できる場合だけ計算
- gradient、image background、blend等でeffective colorを一意に取得できない場合は `measurement-unavailable`
- large text / graphical object / inactive control等のapplicabilityやexceptionはsemantic layer

LLMへrelative luminance計算やratio比較をさせません。

### viewport / overflow / reflow

`observation_contract.py` がcanonical viewport / geometryを返し、`measurement.py` がscroll extent、viewport overflow等の数値を導出します。

reflow criterionのexceptionや「二次元layoutを必要とするcontent」等の意味判断はsemantic layerです。

### elapsed / threshold

`_05e_performance-measurement.md` のcurrent契約を再利用します。

### supported ACT Rule

`_05d` で固定したsupported ACT Ruleだけ `criterion_checks.py` が実行します。

ACT Ruleのoutcome mappingどおり、`failed` がmapped requirementの `not-satisfied` を証明できる場合はその関係を保持します。`passed / inapplicable` だけでSuccess Criterion全体を `satisfied` にしません。

## 6. semantic / manual処理

scriptへ移せないものも実行経路を未定義にしません。

criterion metadataに基づき、semantic/manual rowを必ずmaterializeします。

semantic layerが返すのは、そのrowで必要な意味判断だけです。

- applicability
- exception
- purpose / meaning
- content equivalence
- reading / focus orderの妥当性
- user instruction / error messageの意味
- ATで観測したbehaviorの解釈

「どのcriterionを確認するか」「何を未実施として残すか」はsemantic layerに任せません。

manual / semantic確認に必要なevidenceが不足する場合は `undetermined`、必要環境自体がなく実施不能なら `blocked` へ閉じます。

## 7. Success Criterion result

sample単位のSuccess Criterion resultは既存どおり、

- `satisfied`
- `not-satisfied`
- `undetermined`

です。

`not-satisfied` は、applicableなviolationを必要evidenceで確認できた場合に使用できます。

`satisfied` は、そのcriterion metadataが要求するmachine / semantic / manual / AT stepとapplicable populationを宣言scopeで閉じた場合だけ使用します。

machine stepの一部PASS、単一ACT RuleのPASS、単一elementのPASSだけから `satisfied` を生成しません。

`undetermined` がrequired Success Criterionへ残るsampleは、target conformance levelを満たしたsampleとして扱いません。

## 8. supported ACT Rule inventoryとの関係

ACT RuleはWCAG conformance評価の必須手段ではありません。

`_05d` で固定したsupported ACT Ruleは、対応criterionのevaluation plan内で利用できるmachine stepとして扱います。

supported ACT Ruleがないcriterionも、本ファイルのsemantic/manual / observation procedureによって評価対象から落としません。

このため、ACT Rule coverageの少なさを理由にrequired Success Criterionを省略する経路はありません。

## 9. deterministic validator

production `wcag_criterion_plan.py` とは別実装で少なくとも次を検証します。

- target version / level required Success Criterion集合とcriterion plan row集合が一致
- duplicate criterion rowがない
- each criterion asset rowにevaluation metadataがある
- required capability / machine step / semantic stepが許可値
- unknown machine stepをreject
- required observation / measurement / ACT result / semantic decision refsが解決
- `satisfied` にrequired step未完了がない
- `not-satisfied` にviolation evidenceがある
- `undetermined / blocked` のreasonがある
- required criterionにpending / in-progressが残ったartifactをcompleteにしない
- ACT `passed / inapplicable` だけからSuccess Criterion `satisfied` を生成していない
- target level coverage countをLLM supplied countから採用していない
- versioned requirement asset hash / approved hashが一致

## 10. fixture

最低限、次を持ちます。

- WCAG 2.0 / A, AA, AAA
- WCAG 2.1 / A, AA, AAA
- WCAG 2.2 / A, AA, AAA
- required criterion 1件欠落 → invalid
- duplicate criterion row → invalid
- evaluation metadata欠落 → invalid
- supported ACT Rule failed → mapped requirement not-satisfied可能
- supported ACT Rule passedだけ → requirement satisfied不可
- target-size machine calculation + exception semantic judgment
- contrast ratio machine calculation + gradient background unavailable
- reflow geometry + semantic exception
- AT required / unavailable → blocked
- manual evidence不足 → undetermined
- all required step closure → satisfied可能
- stale observation / measurement → completion不可

## 11. 完了条件

- supported WCAG 2.0 / 2.1 / 2.2の全Success Criterionにevaluation metadataがある
- target version / levelからrequired criterion planをscriptが全件materializeする
- required criterionの選択・省略をLLMへ任せない
- machine処理可能なgeometry / contrast / overflow / elapsed / ACT checkをscriptへ移す
- machineだけで閉じないcriterionにもsemantic/manual / AT経路が明示される
- required evidence不足を推測で埋めない
- supported ACT Ruleがないcriterionも評価対象から落ちない
- sample resultとcriterion plan coverageをdeterministic validatorが独立検証する
