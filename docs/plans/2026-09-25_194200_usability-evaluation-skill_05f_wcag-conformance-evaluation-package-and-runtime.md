# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` のSkill package、成果物、production helper、deterministic validator、semantic evalを固定します。

## 1. package

```text
skills/wcag-conformance-evaluation/
├── SKILL.md
├── references/
│   ├── source-catalog.md
│   ├── wcag-em-2.md
│   └── report-tool.md
├── assets/
│   ├── output-template.md
│   └── wcag-2.2-requirements.json
├── scripts/
│   ├── wcag_requirements.py
│   ├── wcag_em_structure.py
│   └── sampling.py
└── evals/
    ├── trigger/
    ├── output/
    ├── deterministic/
    └── semantic/
```

新しいbrowser framework、accessibility engine、generic sampling frameworkは追加しません。

## 2. source catalog

少なくとも次を公式sourceとして保持します。

- WCAG 2.2
- WCAG-EM 2.0
- WCAG-EM Report Tool
- ACT Rules Format 1.1 / All ACT Rules
- WAI-ARIA / ARIA in HTML
- Understanding Accessibility Support

WAI OverviewはWCAG-EM 2.0のresourceとしてWCAG-EM Report Toolを案内しています。ただし、Report Toolのfield / export schemaがWCAG-EM 2.0本文のStep 5要件と完全に同一であることは確認できていないため、本Skillのoutput contractはWCAG-EM 2.0本文を正本にします。Report Toolは補助resourceとして保持し、runtime dependencyにもschema Authorityにもしません。`references/source-catalog.md` は `_02d_reference-artifact-schema.md` の共通Sources table契約を再利用します。

### supported WCAG version

初期実装でsupportedとするWCAG versionは `2.2` だけです。`assets/wcag-2.2-requirements.json` に、少なくともSuccess Criterion number / levelと5つのWCAG conformance requirementの固定machine keyを保持します。自然言語のSuccess Criterion本文をruntimeへ複製する必要はなく、source item / canonical URLへ追跡できるmetadataに限定します。

catalogはPR #11のstatic data契約を再利用します。strict JSON decode後のcanonical JSON SHA-256を `static_data_versions.wcag_2_2_requirements` としてruntime resultへ保持し、deterministic validatorはassetから独立再計算します。さらにcontract testへW3C正本と照合済みcatalogの承認済みhashを固定し、Success Criterion / levelの欠落や変更をassetとvalidatorが同時に見逃す構造を避けます。

`wcag_requirements.py` はtarget levelから期待requirement集合を独立導出します。

- A → Level A Success Criteria
- AA → Level A + AA Success Criteria
- AAA → Level A + AA + AAA Success Criteria
- いずれもWCAG conformance requirementsを別集合として含める

明示的に2.0 / 2.1等を指定された場合は2.2へ暗黙変換せず `support_status=unsupported` とし、expected requirement setを生成しません。target WCAG version自体が不明・未指定の場合はInput不足として `unresolved` にし、unsupportedと混同しません。別version対応はそのversionのstatic catalogとfixtureを追加した時点でsupportedにします。

## 3. output-template.md

固定section:

1. Evaluation Header
2. Scope
3. Accessibility Support Baseline
4. Target Exploration
5. Observation Handoffs
6. Sampling Procedure / Selected Sample Set
7. Structured Sample
8. Random Sample
9. Complete Processes
10. Sample Evaluation Results
11. Structured / Random Comparison
12. Findings
13. Evaluation Statement（作成した場合だけ）
14. Conformance Claim（作成条件を別途満たした場合だけ）
15. Limitations
16. Machine Runtime / Summary（runtimeを使用した場合）

### Evaluation Header

- evaluation ref / revision
- evaluator
- evaluation commissioner / self-evaluation
- date / period
- WCAG title / version / URI
- target level
- product scope
- project Authority / release gate
- previous evaluation ref（再評価の場合）

### Scope

- product enclosure
- in-scope root / boundary
- out-of-product boundary / reason（存在する場合）
- conformance target
- additional evaluation requirements（存在する場合）

### Accessibility Support Baseline

- baseline ref
- baseline description
- browser / user agent conditions
- assistive technology / adaptive approach conditions
- other software / settings conditions
- source / Authority refs
- limitation

### Target Exploration

各row:

- exploration ref
- kind: common-view / essential-functionality / sample-type / technology-relied-upon / other-relevant
- target / locator
- description
- rationale
- evidence / source refs

### Observation Handoffs

各row:

- handoff ref
- originating evaluation artifact ref / revision
- workflow_ref（qa-workflow管理下の場合）
- resume operation: step-4.1-sample / step-4.2-process
- sample ref
- process ref（存在する場合）
- required requirement refs
- required state / action / sequence
- execution condition refs
- required evidence kind
- returned inspection artifact / evidence refs
- status: satisfied / blocked

### Sampling Procedure / Selected Sample Set

少なくとも:

- sampling procedure: used / skipped
- decision rationale
- inventory / candidate scope provenance
- selected sample refs
- sampling skippedの場合のcomplete inventory ref / completeness
- sampling skippedの場合、Structured Sample / Random Sample / Structured / Random Comparisonがnot-applicableであること
- sampling skippedでもComplete Processes / Step 4.2評価が必要であること

sampling skippedではselected sample refsをcompleteなin-scope inventoryからscriptがmaterializeします。

### Structured Sample

各row:

- sample ref
- sample locator / state
- exploration refs
- covered common-view / essential-functionality / sample-type / technology refs
- process membership（存在する場合）
- inclusion rationale

### Random Sample

少なくとも:

- structured sample count
- target random sample count
- actual random sample count
- selection method
- candidate scope / provenance
- finite inventory ref / completeness（finite inventoryを使う場合）
- selected sample refs
- duplicate replacement記録
- no-new-sample completion reason（該当時）

### Complete Processes

各process:

- process ref
- starting sample ref
- default sequence。sample refとsample間actionを順序付きで保持
- commonly accessed / critical branch sequences
- process completion condition
- evidence / source refs

URLだけでdynamic state / process sampleを識別できない場合は、必要なstate / action / locatorを保持します。

### Sample Evaluation Results

各row:

- sample result ref
- sample ref
- sample kind
- process ref（存在する場合）
- requirement ref
- Success Criterion / conformance requirement
- result: satisfied / not-satisfied / undetermined
- observation / test rule result refs
- evidence refs
- limitation

### Structured / Random Comparison

各iteration:

- comparison ref
- structured sample revision
- random sample revision
- normalized content type keys / finding group keysへのref
- new content type detected
- new finding detected
- new content / finding refs
- action: closed / return-to-step-2-3
- added structured sample refs
- next iteration ref

content type / Findingの意味的groupingはsemantic layerが行いますが、boolean、集合差分、`closed / return-to-step-2-3` は `sampling.py compare` が導出します。

### Step 5 report closure

Step 5.1は、Step 1〜4のoutcomeを成果物内で追跡できることを必須にします。validatorは少なくとも次を確認します。

- Step 1.1 product scope
- Step 1.2 target WCAG level
- Step 1.3 accessibility support baseline
- Step 1.4 additional evaluation requirements（採用した場合）
- Step 2.1〜2.5 exploration outcome
- Step 3.1 structured sample
- Step 3.2 random sample
- Step 3.3 complete process
- Step 4.1 initial sample evaluation
- Step 4.2 complete process evaluation
- Step 4.3 structured / random comparisonと必要な再sampling loop

Step 5.2のevaluation specifics、Step 5.3のevaluation statement、Step 5.4のaggregated score、Step 5.5のmachine-readable reportはoptionalとして別扱いにします。本Planではaggregated scoreを生成しません。

### Evaluation Statement

作成する場合は、他sectionへのrefだけで意味が失われないよう、少なくとも次をstatement sectionへ明示します。

- issued date
- WCAG title / version / URI
- evaluated conformance level
- digital product definition / scope ref
- technologies relied upon。Step 2.4のexploration refへ追跡可能にする
- accessibility support baseline ref
- partial conformance statementの場合だけ、non-conforming product areas
- partial conformance statementの場合だけ、理由。WCAG-EM 2.0が定める理由語彙へ従う
- product ownerのvalidity / accuracy維持commitmentを確認したevidence / ref

## 3.1 wcag_requirements.py

Input:

- target WCAG version
- target conformance level

Function:

- supported versionが2.2であることを検証
- `assets/wcag-2.2-requirements.json` からtarget levelに必要なSuccess Criteria集合を導出
- 5つのWCAG conformance requirement集合を導出
- duplicate / unknown requirement keyをreject
- expected requirement setをcanonical sort

Output:

- support_status: supported / unsupported
- required Success Criterion refs（supported時だけ）
- required conformance requirement refs（supported時だけ）
- static_data_versions.wcag_2_2_requirements
- issues

Agent / LLMが「今回評価すべきSuccess Criteria一覧」を完成集合として入力しません。semantic applicability / exceptionは各requirement result内で判断しますが、requirement universe自体はstatic catalogが正本です。明示的なunsupported versionとmissing / unresolved inputもこのhelperの出力・呼び出し前validationで区別します。

## 4. sampling.py

random selectionはpredictable fixed patternにしてはいけないため、production helperのうち選択処理は意図的にnon-deterministicです。sampling procedureの適用可否と後続section closureはscriptで機械化し、random sample identityの選択だけをrandomnessへ委ねます。

### calculate

Input:

- structured sample count

Function:

```text
ceil(count * 0.10)
```

これはWCAG-EM 2.0本文が整数丸め方法を規定しているという意味ではなく、「10%を切り捨てて0件にしない」ための本Planの整数化規則です。少なくともstructured sample count = 1 / 9 / 10 / 11で、それぞれtarget = 1 / 1 / 1 / 2になるfixtureを持ちます。

Output:

- target random sample count

### materialize-entire-product

sampling procedureをskipする場合に使用します。

Input:

- current complete target inventory
- inventory provenance / completeness
- evaluation scope
- semantic decision: 製品全体を評価可能

Function:

- scope外rowを除外
- duplicate sample identityをreject / canonicalize
- complete inventoryであることを要求
- selected sample setへ全in-scope sample refsをmaterialize
- structured / random / Step 4.3をnot-applicableとしてclosure dataを生成

Output:

- selected sample refs
- sampling procedure = skipped
- skip rationale / provenance
- closure data
- issues

### derive-candidates

finite inventoryを取得できる場合に使用します。

Input:

- current target inventory rows
- inventory provenance / completeness
- evaluation scope
- structured sample refs

Function:

- scope外rowを除外
- duplicate sample identityをreject / canonicalize
- structured sampleを除外
- deterministic sortしたeligible candidate setを生成

LLMはeligible candidate refsを手で列挙しません。

### select

Input:

- `derive-candidates` のeligible candidate set、または外部random mechanismが返したselected sample record
- structured sample refs
- target count
- selection method / candidate scope provenance

Function:

- finite candidate list経路ではOSが提供するrandomnessを使用してunique sampleを選択
- crawler / server log / search / manual list等からcandidate listを得られる場合も、そのlistからの個々のsample選択はscriptが行う
- 外部tool自体がrandom selectionを行う経路ではselected refsを再選択せず、tool identity / method / candidate scope / provenance / count / duplicate / overlapを検証
- LLMがselected sample identityを直接入力する経路を許可しない
- fixed seedを受け付けない

Output:

- selected sample refs
- selection method
- available unique candidate count
- targetを満たせなかった場合のreason

同じInputから同じselectionを返すことは要求しません。

target全体を有限候補として列挙できない場合はfinite inventory経路を無理に使いません。semantic / research工程はWCAG-EM 2.0で許容されるmethodの適用性とcandidate scope / provenanceを判断できますが、個々のsample identityは選びません。candidate listを作れる場合はscriptがそこからrandom選択し、外部tool自体がrandom selectionする場合だけそのselected refsを外部random resultとして受け取ります。

### materialize-process

Input:

- process semantic definition: starting sample、default sequence、critical / commonly accessed branch sequence
- sequence内のsample refs / action refs
- current sample set

Function:

- sequence内sampleのunion
- duplicate除去
- current sample setにないsampleを `process-added` として導出
- process membership / sequence closureをmaterialize

LLMがsequenceと別にprocess-added sample集合を手組みしません。

### compare

Input:

- structured sample revisionと各sampleのnormalized content type keys / finding group keys
- random sample revisionと各sampleのnormalized content type keys / finding group keys

Function:

- structured / random set difference
- new content / finding refs導出
- `new content type detected` / `new finding detected` 導出
- 差分なし → `closed`
- 差分あり → `return-to-step-2-3`

global content type / Finding identityは作りません。keyの意味妥当性はsemantic evalが担当します。

### reconcile-after-structured-update

Step 4.3でstructured sampleへ追加が生じた場合に使用します。

Input:

- previous structured / random revisions
- added structured sample refs
- current candidate scope / provenance
- current complete process definitions

Function:

- new structured revisionをmaterialize
- new structured countからrandom target countを再計算
- new structured setと重複する旧random sampleを除外
- structuredと重複せずcurrentな旧random sampleを保持
- target countへ不足する件数だけ追加random selection
- 新random sampleに対してcomplete process由来sampleを再materialize
- 追加されたsample / processだけを未評価として返す
- existing current resultを保持
- next comparison revisionを生成

Output:

- new structured / random revisions
- retained / removed / added random sample refs
- new target count
- process-added refs
- newly required evaluation refs
- issues

### validate

Input:

- structured sample refs
- random sample refs
- target random sample count
- selection method
- no-new-sample reason（存在する場合）

Function:

- count
- duplicate
- structured / random overlap
- target count
- selection method存在
- no-new-sample exception整合

を検証します。

## 5. wcag_em_structure.py

final artifact assemblyのownerです。

Input:

- evaluation headerのsemantic field
- scope / accessibility support baselineのsemantic decisions
- sampling procedure semantic decision: 製品全体を評価可能か
- exploration decisions
- structured sample selection decisions
- finite inventory / recorded random selection provenance
- process semantic definitions
- observation handoff semantic requirements
- returned inspection artifact / evidence refs
- sample requirement result decisions / evidence
- content type / Finding grouping decisions
- Finding semantic input
- optional evaluation statement semantic input
- optional conformance claim evidence
- limitation

各draftはinvocation内で一意な `draft_key` を持ちます。

Function:

- unknown field / enum / required field検証
- `wcag_requirements.py` のexpected requirement universeを読み、LLM supplied listではなくtarget levelからrequired coverageを生成
- `sampling.py` のentire-product / candidate / selection / process / reconciliation / comparison resultだけからmachine-owned sample / comparison fieldをmaterialize
- artifact-local ref採番
  - accessibility support baseline: `BASELINE-001`
  - exploration: `EXPLORE-001`
  - observation handoff: `HANDOFF-001`
- draft key → final ref解決
- cross-reference解決
- WCAG-EM Step 1〜5 closure
- scope / accessibility support baseline closure
- sampling procedure used / skippedとselected sample set closure
- sampling skippedではcomplete inventory → selected sample set traceabilityとstructured / random / Step 4.3 not-applicable closure
- sampling usedではexploration → structured sample traceability
- observation handoffごとにoriginating evaluation / revision / resume operation / expected refsをmaterialize
- expected handoff集合とreturned current valid result集合のclosure
- complete process sequence closure
- process-added sample coverage
- target levelから独立導出したrequired sample result coverage
- Step 4.3集合差分からiteration action / chain closureをmaterialize
- structured revision更新時のrandom target再計算、old random retention / overlap removal / top-up、process再materializeを反映
- Step 5.1でStep 1〜4の各required outcomeが成果物へ存在すること
- evaluation statementを作成した場合のStep 5.3 minimum fieldsと生成条件
- report section order固定
- summary count生成
- machine-owned structured sectionをcanonical Markdownとしてrender。Agentがfinal refs / derived flags / counts / closure rowsを値単位で再構築しない

ref prefixはartifact-localです。

- sample: `SAMPLE-001`
- process: `PROC-001`
- sample result: `WCAG-RES-001`
- comparison: `CMP-001`

evaluation artifact自体のidentity / revisionはmerge後current artifact契約を再利用します。

Output:

- normalized WCAG-EM evaluation artifact
- rendered machine-owned structured sections
- summary
- issues

## 6. requirement / ACT result

個別sampleのrequirement resultは `satisfied / not-satisfied / undetermined` を使用します。

ACT Rule resultをWCAG Success Criterion全体へ自動変換しません。

supported ACT Ruleの利用条件は `_05d_accessibility-requirements-and-act.md` を再利用します。

## 7. evaluation statement / conformance claim

evaluation statementは次をすべて確認できる場合だけ生成します。

- 全non-optional methodology requirement完了
- 全sampleがtarget conformance levelを満たす
- product ownerがvalidity / accuracy維持責任を明示的に引き受ける
- §3のEvaluation Statement minimum fieldsをすべて埋められる

partial conformance statementを作る場合は、WCAG-EM 2.0 Step 5.3が要求するnon-conforming product areasとreasonも必須です。

通常のrepresentative sample evaluationからproduct-wide WCAG conformance claimを生成しません。

conformance claim fieldは、claim scopeに含まれる全Web page / complete processについてWCAG側のclaim requirementsを別途満たした証拠がある場合だけ使用できます。

## 8. deterministic validator

production helperとは別実装で少なくとも次を検証します。

- output section / schema
- required Input
- supported WCAG version = 2.2
- explicit unsupported versionとmissing / unresolved inputが混同されていない
- `static_data_versions.wcag_2_2_requirements` をassetから独立再計算
- contract testの承認済みWCAG 2.2 catalog hashと一致
- static catalogから独立導出したtarget level required Success Criteria / conformance requirement集合とactual coverageの一致
- accessibility support baseline
- sampling procedure used / skippedとselected sample set closure
- sampling skipped時のcomplete inventory / selected set一致、structured / random / Step 4.3 not-applicable、complete process評価継続
- sampling used時のstructured sample traceability
- random sample target count
- random sample duplicate / overlap
- finite inventory時のcandidate derivation / provenance、またはrecorded method時のcandidate scope provenance
- selection method
- process sequenceから導出したprocess-added sample / membership closure
- observation handoffのoriginating evaluation / revision / resume operation / expected refsとreturned inspection artifact cross-reference
- sample result cross-reference
- target levelに必要なrequirement result coverage
- normalized content type / Finding group keyの集合差分とStep 4.3 derived action / iteration chain
- structured revision更新後のrandom target再計算、overlap除外、retained random、top-up件数、process再materialize
- Step 5.1のStep 1〜4 outcome closure
- evaluation statement生成条件とStep 5.3 minimum fields
- product-wide claim guard
- Finding refs
- secret / credential非複製

random selectionの結果そのものが「十分randomだったか」を同じvalidatorで証明しません。method / candidate scope / fixed-seed禁止等の契約を検証します。

## 9. semantic eval

少なくとも次を実Judgeで確認します。

### Case A: formal request routing

「WCAG 2.2 AAへ適合しているか評価」

→ `wcag-conformance-evaluation` をmethodology ownerとして開始する。live observationが必要で `qa-workflow` を利用できる場合は、`qa-workflow → usability-inspection → qa-workflow → wcag-conformance-evaluation resume` まで同一要求内で閉じる。

### Case B: general accessibility boundary

「このDialogのaccessibilityを確認」

→ usability-inspection。formal evaluationへ昇格しない。

### Case C: required Input unresolved

target levelまたはaccessibility support baseline不明。

→ 推測せずunresolved。

### Case D: structured sample

Step 2 explorationを反映したsampleを選ぶ。

### Case E: random sample

structured sampleの10%要件、unique、non-overlap、selection methodを満たす。

### Case F: no unique random candidate

新しいunique sampleが存在しないことを記録してStep 3.2を閉じる。

### Case G: complete process

default / critical branch sequenceを含める。

### Case H: Step 4.3 retry

random sampleから新content type / findingを検出。

→ Step 2 / 3へ戻りstructured sampleを更新して再評価。

### Case I: evaluation statement

条件不足でstatementを生成しない。

### Case J: conformance claim

representative sampleが全PASSでもproduct-wide conformance claimを作らない。

### Case K: expertise / environment limitation

必要なassistive technology / expert judgmentを利用できない。

→ blocked / undetermined。

### Case L: unsupported WCAG version

WCAG 2.0 / 2.1等を明示指定。

→ `support_status=unsupported`。2.2へ暗黙変換せず、missing input由来の `unresolved` と混同しない。

### Case M: missing Success Criterion

target levelの静的expected setから1件を成果物で欠落させる。

→ deterministic validatorが欠落を検出し、LLMが「評価済み」と自己申告しても完了にしない。

### Case N: sampling procedure skipped

small / finite productでcomplete inventoryがあり、製品全体を評価可能。

→ 全in-scope sampleをselected sample setへmaterializeし、structured / random / Step 4.3をnot-applicableとして閉じる。complete process / Step 4.2評価は継続する。

### Case O: structured sample expansion

Step 4.3で新content type / findingが見つかりstructured sampleを追加。

→ new structured countからrandom targetを再計算し、overlapした旧random sampleを除外、currentな旧random sampleを保持、不足分だけ追加random selectionして次iterationへ進む。

### Case P: non-finite random source

crawler / log / search等でtarget全体を有限inventoryにできない。

→ LLMはmethod / provenanceの適用性だけを判断し、sample identityはscriptまたは外部random mechanismが選択する。

## 10. 完了条件

- package単体でSkill contractを理解できる
- sibling Skillのscriptsへruntime依存しない
- formal direct trigger後にlive observationが必要な場合、qa-workflowが利用可能ならhandoff → usability-inspection → formal Skill resumeへ遷移し、qa-workflowを利用できないstandalone環境だけblockedへ閉じられる
- WCAG-EM Report ToolをWCAG-EM 2 schema Authorityとして扱わず、runtime dependencyにもしていない
- WCAG 2.2 target levelからrequired Success Criteria / conformance requirement集合をversioned static catalogから独立導出でき、explicit unsupported versionとmissing / unresolved inputを区別し、2.2以外を暗黙変換しない
- WCAG 2.2 catalogのcanonical hashを `static_data_versions.wcag_2_2_requirements` へ保持し、validator独立再計算と承認済みhash contract testをPASS
- sampling procedure used / skippedの両経路を持ち、skippedでは全in-scope sampleをselected sample setへmaterializeできる
- random sample 10%整数化がscript化され、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- random selectionへfixed seedを要求しない
- finite inventory時のrandom candidate集合、process-added sample、Step 4.3のboolean / actionをscriptが導出し、Agentが手組みしない
- finite inventoryがない場合もLLMがselected sample identityを選ばず、scriptまたは外部random mechanismの結果だけを受ける
- Step 4.3でstructured revisionが変わった場合、random target再計算、overlap除外、retained random、不足分top-up、process再materializeをscriptで閉じる
- sample / process / result / comparison refとmachine-owned structured sectionをscriptがmaterializeし、Agentが値単位で再構築しない
- Step 4.3 loopをartifact上で追跡できる
- Step 5.1のrequired outcome closureとStep 5.3 evaluation statement minimum fieldsをvalidatorで検証できる
- production helperとvalidatorが別実装
- semantic Case A〜P PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureでWCAG-EM orchestration E2EをPASSできる
