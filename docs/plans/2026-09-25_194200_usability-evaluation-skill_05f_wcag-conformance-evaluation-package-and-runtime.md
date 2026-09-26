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

WCAG-EM Report Toolはfield / report構造のreferenceとして利用できますが、tool自体をruntime dependencyにはしません。`references/source-catalog.md` の物理schemaは `_02d_reference-artifact-schema.md` のSources table契約を再利用します。

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

## 4. sampling.py

random selectionはpredictable fixed patternにしてはいけないため、production helperのうち選択処理は意図的にnon-deterministicです。

### calculate

Input:

- structured sample count

Function:

```text
ceil(count * 0.10)
```

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
- report Step 1〜4 outcome
- evaluation statement生成条件
- product-wide claim guard
- Finding refs
- secret / credential非複製

random selectionの結果そのものが「十分randomだったか」を同じvalidatorで証明しません。method / candidate scope / fixed-seed禁止等の契約を検証します。

## 9. semantic eval

少なくとも次を実Judgeで確認します。

### Case A: formal request routing

「WCAG 2.2 AAへ適合しているか評価」

→ wcag-conformance-evaluation。

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
- live observation不足時にnormalized handoffを出してblockedへ閉じられる
- WCAG-EM Report Toolをruntime dependencyにしない
- random sample 10%整数化がscript化されている
- random selectionへfixed seedを要求しない
- sample / process / result / comparison refをAgentが手採番しない
- Step 4.3 loopをartifact上で追跡できる
- production helperとvalidatorが別実装
- semantic Case A〜K PASS
- real Web targetでcanonical WCAG-EM E2Eを実行できる
