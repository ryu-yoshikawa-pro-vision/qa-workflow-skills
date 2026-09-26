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
│   └── output-template.md
├── scripts/
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

## 3. output-template.md

固定section:

1. Evaluation Header
2. Scope
3. Accessibility Support Baseline
4. Target Exploration
5. Observation Handoffs
6. Structured Sample
7. Random Sample
8. Complete Processes
9. Sample Evaluation Results
10. Structured / Random Comparison
11. Findings
12. Evaluation Statement（作成した場合だけ）
13. Conformance Claim（作成条件を別途満たした場合だけ）
14. Limitations
15. Machine Runtime / Summary（runtimeを使用した場合）

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
- sample ref
- process ref（存在する場合）
- required requirement refs
- required state / action / sequence
- execution condition refs
- required evidence kind
- returned inspection artifact / evidence refs
- status: satisfied / blocked

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
- candidate scope / source
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
- new content type detected
- new finding detected
- new content / finding refs
- action: closed / return-to-step-2-3
- added structured sample refs
- next iteration ref

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

## 4. sampling.py

random selectionはpredictable fixed patternにしてはいけないため、production helperのうち選択処理は意図的にnon-deterministicです。

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

### select

有限なcandidate集合を取得できる場合だけ使用できます。

Input:

- candidate sample refs
- structured sample refs
- target count

Function:

- duplicate除去
- structured sample除外
- OSが提供するrandomnessを使用してunique sampleを選択
- fixed seedを受け付けない

Output:

- selected sample refs
- selection method
- available unique candidate count
- targetを満たせなかった場合のreason

同じInputから同じselectionを返すことは要求しません。

target全体を有限候補として列挙できない場合は、このselect機能を無理に使わず、WCAG-EM 2.0が許容する別のrandom selection methodを利用し、そのmethodとselected samplesを記録します。

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

- evaluation header
- scope draft
- accessibility support baseline drafts
- exploration drafts
- structured sample drafts
- random sample drafts
- complete process drafts
- observation handoff drafts
- returned inspection artifact / evidence refs
- sample result drafts
- comparison iteration drafts
- Finding refs
- optional evaluation statement
- optional conformance claim
- limitation

各draftはinvocation内で一意な `draft_key` を持ちます。

Function:

- unknown field / enum / required field検証
- artifact-local ref採番
  - accessibility support baseline: `BASELINE-001`
  - exploration: `EXPLORE-001`
  - observation handoff: `HANDOFF-001`
- draft key → final ref解決
- cross-reference解決
- WCAG-EM Step 1〜5 closure
- scope / accessibility support baseline closure
- exploration → structured sample traceability
- observation handoff closure
- complete process sequence closure
- required sample result coverage
- Step 4.3 iteration chain closure
- Step 5.1でStep 1〜4の各required outcomeが成果物へ存在すること
- evaluation statementを作成した場合のStep 5.3 minimum fieldsと生成条件
- report section order固定
- summary count生成

ref prefixはartifact-localです。

- sample: `SAMPLE-001`
- process: `PROC-001`
- sample result: `WCAG-RES-001`
- comparison: `CMP-001`

evaluation artifact自体のidentity / revisionはmerge後current artifact契約を再利用します。

Output:

- normalized WCAG-EM evaluation artifact
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
- accessibility support baseline
- structured sample traceability
- random sample target count
- random sample duplicate / overlap
- selection method
- complete process closure
- observation handoff / returned inspection artifact cross-reference
- sample result cross-reference
- target levelに必要なrequirement result coverage
- Step 4.3 comparison iteration chain
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

## 10. 完了条件

- package単体でSkill contractを理解できる
- sibling Skillのscriptsへruntime依存しない
- formal direct trigger後にlive observationが必要な場合、qa-workflowが利用可能ならhandoff → usability-inspection → formal Skill resumeへ遷移し、qa-workflowを利用できないstandalone環境だけblockedへ閉じられる
- WCAG-EM Report ToolをWCAG-EM 2 schema Authorityとして扱わず、runtime dependencyにもしていない
- random sample 10%整数化がscript化され、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- random selectionへfixed seedを要求しない
- sample / process / result / comparison refをAgentが手採番しない
- Step 4.3 loopをartifact上で追跡できる
- Step 5.1のrequired outcome closureとStep 5.3 evaluation statement minimum fieldsをvalidatorで検証できる
- production helperとvalidatorが別実装
- semantic Case A〜K PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureでWCAG-EM orchestration E2EをPASSできる
