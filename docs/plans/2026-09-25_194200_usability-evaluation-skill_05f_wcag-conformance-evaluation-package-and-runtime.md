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
│   ├── wcag-2.0-requirements.json
│   ├── wcag-2.1-requirements.json
│   └── wcag-2.2-requirements.json
├── scripts/
│   ├── runtime_contract.py
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

- WCAG 2.0
- WCAG 2.1
- WCAG 2.2
- WCAG-EM 2.0
- WCAG-EM Report Tool
- ACT Rules Format 1.1 / All ACT Rules
- WAI-ARIA / ARIA in HTML
- Understanding Accessibility Support

WAI OverviewはWCAG-EM 2.0のresourceとしてWCAG-EM Report Toolを案内しています。ただし、Report Toolのfield / export schemaがWCAG-EM 2.0本文のStep 5要件と完全に同一であることは確認できていないため、本Skillのoutput contractはWCAG-EM 2.0本文を正本にします。Report Toolは補助resourceとして保持し、runtime dependencyにもschema Authorityにもしません。`references/source-catalog.md` は `_02d_reference-artifact-schema.md` の共通Sources table契約を再利用します。

### supported WCAG version

現在のsupported WCAG versionは `2.0 / 2.1 / 2.2` です。各versionを別catalogとして保持します。

- `assets/wcag-2.0-requirements.json`
- `assets/wcag-2.1-requirements.json`
- `assets/wcag-2.2-requirements.json`

各catalogは少なくともSuccess Criterion number / levelと5つのWCAG conformance requirementの固定machine keyを保持します。自然言語のSuccess Criterion本文をruntimeへ複製する必要はなく、source item / canonical URLへ追跡できるmetadataに限定します。version間でSuccess Criteria集合を合成せず、target versionのcatalogだけをrequirement universeとして使用します。

catalogはPR #11のstatic data契約を再利用します。strict JSON decode後のcanonical JSON SHA-256をtarget versionに応じて次へ保持します。

- `static_data_versions.wcag_2_0_requirements`
- `static_data_versions.wcag_2_1_requirements`
- `static_data_versions.wcag_2_2_requirements`

deterministic validatorは選択versionのassetからhashを独立再計算します。さらに各catalogについてW3C正本と照合済みの承認済みhashをcontract testへ固定し、Success Criterion / levelの欠落や変更をassetとvalidatorが同時に見逃す構造を避けます。

`wcag_requirements.py` はtarget version / levelから期待requirement集合を独立導出します。

- A → 指定versionのLevel A Success Criteria
- AA → 指定versionのLevel A + AA Success Criteria
- AAA → 指定versionのLevel A + AA + AAA Success Criteria
- いずれも指定versionのWCAG conformance requirementsを別集合として含める

target WCAG version自体が不明・未指定の場合はInput不足として `unresolved` にします。現在catalogを持たない将来version等が明示された場合は `support_status=unsupported` とし、別versionへ暗黙変換しません。WCAG 3はWCAG-EM 2.0が対象とするWCAG 2 conformanceではないため本Skillの対象外です。

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
13. Evaluation Statement（通常 / partial。作成した場合だけ）
14. WCAG Conformance Claim / Statement of Partial Conformance（作成条件を満たした場合だけ）
15. Limitations
16. Machine Runtime / Summary

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

作成する場合は `statement type: full / partial` を必須にし、他sectionへのrefだけで意味が失われないよう、少なくとも次をstatement sectionへ明示します。

共通field:

- issued date
- target WCAG title / version / URI
- evaluated conformance level
- digital product definition / scope ref
- technologies relied upon。Step 2.4のexploration refへ追跡可能にする
- accessibility support baseline ref
- product ownerのvalidity / accuracy維持commitmentを確認したevidence / ref

`full` は全non-optional methodology requirementが完了し、全sampleがtarget conformance levelを満たす場合だけ生成できます。

`partial` は全non-optional methodology requirementとproduct owner commitmentを満たしたうえで、次を追加で必須にします。

- non-conforming product areas
- 各areaのreason: `third-party-content / lack-of-accessibility-support-for-languages`
- 全non-conforming areaが上記reasonのいずれかで説明されること

semantic layerはareaとreasonの意味妥当性を判断し、scriptはrequired field集合、reason enum、未説明area、生成可否を導出します。

### WCAG Conformance Claim / Statement of Partial Conformance

WCAG Conformance Claimは指定versionのWCAG側contractとして扱い、WCAG-EM Evaluation Statementと混同しません。作成する場合は少なくとも次を必須にします。

- claim date
- target WCAG title / version / canonical URI
- conformance level satisfied
- claim対象Web page群の簡潔なdescription。URI listまたは明確なscope expressionと、subdomainを含むか
- web content technologies relied upon
- claim scope内の全Web page / complete processを評価済みであるevidence、またはclaim scope内の各pageがconformance requirementsを満たすことを保証するprocess evidence

representative sampleだけではclaimを生成しません。third-party contentを監視・修復する経路でfull claimを成立させる場合は、WCAG側条件を満たすmonitoring / repair evidenceも必須にします。

WCAG Statement of Partial ConformanceはConformance Claimではありません。次を別typeとして扱います。

- `third-party-content`: 対象pageが非適合だが、明示したuncontrolled contentを除けば指定version / levelへ適合する。該当contentがauthor control外で、利用者が識別できるdescriptionを持つこと
- `language`: 対象pageが非適合だが、明示したlanguageについてaccessibility supportが存在すれば指定version / levelへ適合すること

semantic layerはcontrol ownership、language support不足、除外時に適合するという意味判断を行い、scriptはtype、必須field、対象範囲、target version / level、生成可否をmaterialize / validateします。

## 3.1 wcag_requirements.py

Input:

- target WCAG version
- target conformance level

Function:

- target versionが2.0 / 2.1 / 2.2のどれかであることを検証
- target versionに対応するstatic catalogを選択
- target levelに必要なSuccess Criteria集合を導出
- target versionの5つのWCAG conformance requirement集合を導出
- duplicate / unknown requirement keyをreject
- expected requirement setをcanonical sort
- target version以外のcatalogを混在させない

Output:

- support_status: supported / unsupported
- target WCAG version
- required Success Criterion refs（supported時だけ）
- required conformance requirement refs（supported時だけ）
- target versionに対応する `static_data_versions` key / hash
- issues

Agent / LLMが「今回評価すべきSuccess Criteria一覧」を完成集合として入力しません。semantic applicability / exceptionは各requirement result内で判断しますが、requirement universe自体は指定versionのstatic catalogが正本です。明示的なunsupported versionとmissing / unresolved inputもこのhelperの出力・呼び出し前validationで区別します。

## 3.2 runtime_contract.py

PR #11のcurrent Machine Runtime契約を再利用します。独自runtime envelopeは作りません。

deterministic runtimeへ載せるもの:

- `wcag_requirements.py` のversion / level → expected requirement集合
- sample identity registry / selected set / duplicate / overlap / union
- random target count、candidate population fingerprint、selection result validation
- complete process materialization
- Step 4.3 compare / reconcile
- freshness / currentnessに必要なnormalized input
- `wcag_em_structure.py` のclosure / cross-reference / statement / claim guard / machine-owned section materialization

deterministic runtimeへ載せないもの:

- random sampleの実選択。OS randomnessや外部random mechanismを使うため、同一Input→同一Outputを要求しない
- structured sampleの代表性判断
- sample / content type / Findingの意味的同一性判断
- partial statement reason、third-party control、language support等の意味判断

random selection結果はmethod / provenance / selected sample identityとともに後続Machine Runtime Inputへ渡します。保存済みsample resultはPR #11 current verifierでfreshnessを再計算し、currentの場合だけ再利用します。

runtime Inputには少なくともtarget WCAG version / level、scope、accessibility support baseline、environment、sample identity、evidence identity、Authority / reference refs、選択versionのstatic data versionを含め、これらが変わった場合に旧resultをcurrent扱いしません。

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
- canonical sample identity source

Function:

- scope外rowを除外
- semantic input / current test-target-inspection keyからcanonical artifact-local sample identity registryをmaterialize
- duplicate sample identityをreject / canonicalize
- structured sampleを除外
- deterministic sortしたeligible candidate setを生成
- normalized candidate scope / inventory / provenanceからcandidate population fingerprintを生成

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
- candidate population fingerprint
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
- previous candidate population fingerprint
- added structured sample refs
- current candidate scope / inventory / provenance
- current complete process definitions

Function:

- new structured revisionをmaterialize
- new structured countからrandom target countを再計算
- current candidate population fingerprintを再計算
- population fingerprintが同じ場合だけnew structured setと重複する旧random sampleを除外し、structuredと重複せずcurrentな旧random sampleを保持する
- population fingerprintが同じ場合はtarget countへ不足する件数だけ追加random selectionする
- population fingerprintが変わった場合は旧random selectionをstaleとしてcurrent populationからrandom setを再選択する
- 新random sampleに対してcomplete process由来sampleを再materialize
- PR #11 freshness検証でstaleになったsample resultを再評価対象へ戻す
- currentな既存resultと新たに必要なsample / processを分離して返す
- next comparison revisionを生成

Output:

- new structured / random revisions
- previous / current candidate population fingerprint
- retained / removed / added random sample refs
- random selection action: retained-top-up / reselection
- new target count
- process-added refs
- reusable current result refs
- stale / newly required evaluation refs
- issues

### validate

Input:

- structured sample refs
- random sample refs
- target random sample count
- selection method
- candidate population fingerprint
- no-new-sample reason（存在する場合）

Function:

- count
- duplicate
- structured / random overlap
- target count
- candidate population fingerprint
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
- optional Evaluation Statement semantic input
- optional WCAG Conformance Claim evidence
- optional WCAG Statement of Partial Conformance semantic input / evidence
- limitation

各draftはinvocation内で一意な `draft_key` を持ちます。

Function:

- unknown field / enum / required field検証
- `wcag_requirements.py` のexpected requirement universeを読み、LLM supplied listではなくtarget levelからrequired coverageを生成
- `sampling.py` のentire-product / candidate / selection / process / reconciliation / comparison resultだけからmachine-owned sample / comparison fieldをmaterialize
- canonical sample identity registryを先にmaterializeし、structured / random / process-added集合は同じsample refを参照する
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
- structured revision更新時のcandidate population fingerprint再計算、population同一時のold random retention / overlap removal / top-up、population変更時のreselection、process再materializeを反映
- sample result freshnessをPR #11 current verifier結果から反映し、stale resultをclosureへ数えない
- Step 5.1でStep 1〜4の各required outcomeが成果物へ存在すること
- Evaluation Statementのfull / partial minimum fieldsと生成条件
- WCAG Conformance Claim / Statement of Partial Conformanceのtype別required fieldsと生成条件
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

## 7. Evaluation Statement / WCAG claim

### WCAG-EM Evaluation Statement

`full` は次をすべて確認できる場合だけ生成します。

- 全non-optional methodology requirement完了
- 全sampleがtarget conformance levelを満たす
- product ownerがvalidity / accuracy維持責任を明示的に引き受ける
- §3のEvaluation Statement共通fieldをすべて埋められる

`partial` は全non-optional methodology requirement、product owner commitment、共通fieldを満たし、全non-conforming areaを `third-party-content / lack-of-accessibility-support-for-languages` のいずれかへ意味的に対応付けられる場合だけ生成します。全sampleがtargetを満たすことはpartial statementの前提にしません。

### WCAG Conformance Claim

通常のrepresentative sample evaluationからproduct-wide WCAG Conformance Claimを生成しません。

claimは、次をすべて満たす場合だけ生成します。

- claim scopeが明確
- claim scope内の全Web page / complete processを評価済み、または各pageがconformance requirementsを満たすことを保証するprocess evidenceがある
- target version / levelのSuccess Criteriaと5 conformance requirementsをclaim scope全体で満たす
- claim date
- target WCAG title / version / canonical URI
- conformance level satisfied
- claim対象Web page群のdescription / URI listまたはscope expression / subdomain扱い
- technologies relied upon

third-party contentについてWCAGが認めるmonitoring / repair経路でfull claimを作る場合は、その条件を満たすevidenceも必須にします。

### WCAG Statement of Partial Conformance

Conformance Claimとは別の非適合statementです。

- `third-party-content`: uncontrolled contentを除けば指定version / levelへ適合し、そのcontentがauthor control外で、利用者が識別可能
- `language`: 指定languageのaccessibility supportが存在すれば指定version / levelへ適合

semantic layerはcontrol ownership、language support不足、除外時に適合するという意味判断を行います。script / validatorはstatement type、target version / level、required field、対象area / language、生成可否を閉じます。

## 8. deterministic validator

production helperとは別実装で少なくとも次を検証します。

- output section / schema
- required Input
- supported WCAG version = 2.0 / 2.1 / 2.2
- explicit unsupported versionとmissing / unresolved inputが混同されていない
- target versionに対応する `static_data_versions` hashをassetから独立再計算
- target versionに対応する承認済みcatalog hashと一致
- target version以外のcatalogをexpected requirement集合へ混在させていない
- static catalogから独立導出したtarget level required Success Criteria / conformance requirement集合とactual coverageの一致
- accessibility support baseline
- sampling procedure used / skippedとselected sample set closure
- sampling skipped時のcomplete inventory / selected set一致、structured / random / Step 4.3 not-applicable、complete process評価継続
- sampling used時のstructured sample traceability
- canonical sample identity registry
- random sample target count
- random sample duplicate / overlap
- finite inventory時のcandidate derivation / provenance、またはrecorded method時のcandidate scope provenance
- candidate population fingerprint
- selection method
- process sequenceから導出したprocess-added sample / membership closure
- observation handoffのoriginating evaluation / revision / resume operation / expected refsとreturned inspection artifact cross-reference
- sample result cross-reference
- target levelに必要なrequirement result coverage
- normalized content type / Finding group keyの集合差分とStep 4.3 derived action / iteration chain
- structured revision更新後のcandidate population fingerprint再計算、population同一時のoverlap除外 / retained random / top-up、population変更時のreselection、process再materialize
- sample result freshness / stale再評価
- Step 5.1のStep 1〜4 outcome closure
- Evaluation Statement full / partial生成条件とStep 5.3 minimum fields
- WCAG Conformance Claim required fields / full-scope coverage guard
- WCAG Statement of Partial Conformance third-party / language guard
- Finding refs
- secret / credential非複製

random selectionの結果そのものが「十分randomだったか」を同じvalidatorで証明しません。method / candidate scope / fixed-seed禁止等の契約を検証します。

## 9. semantic eval

少なくとも次を実Judgeで確認します。

### Case A: formal request routing

「指定したWCAG 2.0 / 2.1 / 2.2のlevelへ適合しているか評価」

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

### Case I: full Evaluation Statement

全non-optional methodology requirement、全sample target達成、product owner commitment、minimum fieldsが揃う。

→ `statement_type=full` を生成する。条件不足なら生成しない。

### Case J: partial Evaluation Statement

一部sampleがtargetを満たさないが、全non-conforming areaをWCAG-EM 2.0のpartial理由へ対応付けられ、他の共通条件を満たす。

→ `statement_type=partial` とarea / reasonを生成する。許可reason外または未説明areaがあれば生成しない。

### Case K: expertise / environment limitation

必要なassistive technology / expert judgmentを利用できない。

→ blocked / undetermined。

### Case L: supported WCAG versions

WCAG 2.0 / 2.1 / 2.2をそれぞれ指定。

→ 各versionのcatalogだけを使い、version / levelに対応するexpected requirement集合を生成する。2.0 / 2.1を2.2へ変換しない。

### Case M: unsupported / unresolved WCAG version

version未指定は `unresolved`。現在catalogを持たない将来versionまたはWCAG 3指定は `unsupported / out-of-scope` とし、2.xへ暗黙変換しない。

### Case N: missing Success Criterion

target levelの静的expected setから1件を成果物で欠落させる。

→ deterministic validatorが欠落を検出し、LLMが「評価済み」と自己申告しても完了にしない。

### Case O: sampling procedure skipped

small / finite productでcomplete inventoryがあり、製品全体を評価可能。

→ 全in-scope sampleをselected sample setへmaterializeし、structured / random / Step 4.3をnot-applicableとして閉じる。complete process / Step 4.2評価は継続する。

### Case P: structured sample expansion

Step 4.3で新content type / findingが見つかりstructured sampleを追加。

→ new structured countからrandom targetを再計算し、overlapした旧random sampleを除外、currentな旧random sampleを保持、不足分だけ追加random selectionして次iterationへ進む。

### Case Q: non-finite random source

crawler / log / search等でtarget全体を有限inventoryにできない。

→ LLMはmethod / provenanceの適用性だけを判断し、sample identityはscriptまたは外部random mechanismが選択する。

### Case R: sample identity

同じURLで異なるapplication stateを持つ2 viewと、同じstateを別経路で観測した2 recordを入力する。

→ semantic同一性判断を受けてscriptがcanonical sample registryを作り、異なるstateは別sample、同じstateは同一sampleとしてdeduplicateする。

### Case S: candidate population changed

Step 4.3後にcandidate inventory / provenanceが変わる。

→ population fingerprint差分を検出し、旧random setをtop-upせずcurrent populationから再選択する。

### Case T: stale sample result

baseline、environment、evidence identity、catalog hash等を変更する。

→ PR #11 freshness判定で旧resultをstaleとし、再評価対象へ戻す。

### Case U: WCAG Conformance Claim

complete claim scope全件のconformance evidenceとrequired claim fieldsが揃う。

→ 指定WCAG versionのConformance Claimを生成する。representative sampleしかない場合は生成しない。

### Case V: WCAG partial conformance third-party

author control外で利用者が識別可能なthird-party contentを除けばtargetへ適合する。

→ WCAG Statement of Partial Conformance - Third Party Contentを生成する。

### Case W: WCAG partial conformance language

指定languageのaccessibility supportが存在すればtargetへ適合する。

→ WCAG Statement of Partial Conformance - Languageを生成する。

## 10. 完了条件

- package単体でSkill contractを理解できる
- sibling Skillのscriptsへruntime依存しない
- formal direct trigger後にlive observationが必要な場合、qa-workflowが利用可能ならhandoff → usability-inspection → formal Skill resumeへ遷移し、qa-workflowを利用できないstandalone環境だけblockedへ閉じられる
- WCAG-EM Report ToolをWCAG-EM 2 schema Authorityとして扱わず、runtime dependencyにもしていない
- WCAG 2.0 / 2.1 / 2.2の各target version / levelからrequired Success Criteria / conformance requirement集合を該当versionのstatic catalogだけで独立導出できる
- 3 catalogのcanonical hashをversion別 `static_data_versions` keyへ保持し、validator独立再計算と承認済みhash contract testをPASS
- missing / unresolved versionとunsupported / out-of-scope versionを区別し、別versionへ暗黙変換しない
- `runtime_contract.py` でPR #11 Machine Runtime / freshness契約を再利用し、random selectionそのものはdeterministic runtimeへ含めない
- sampling procedure used / skippedの両経路を持ち、skippedでは全in-scope sampleをselected sample setへmaterializeできる
- random sample 10%整数化がscript化され、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- random selectionへfixed seedを要求しない
- canonical sample identity registryをscriptがmaterializeし、duplicate / overlap / union / process membershipを同じidentityで判定する
- finite inventory時のrandom candidate集合、process-added sample、Step 4.3のboolean / actionをscriptが導出し、Agentが手組みしない
- finite inventoryがない場合もLLMがselected sample identityを選ばず、scriptまたは外部random mechanismの結果だけを受ける
- candidate population fingerprintをscriptが導出し、Step 4.3でstructured revisionが変わった場合、population同一時のrandom target再計算 / overlap除外 / retained random / 不足分top-up、population変更時のreselection、process再materializeを閉じる
- 既存sample resultはPR #11 freshness判定がcurrentの場合だけ再利用する
- sample / process / result / comparison refとmachine-owned structured sectionをscriptがmaterializeし、Agentが値単位で再構築しない
- Step 4.3 loopをartifact上で追跡できる
- Step 5.1のrequired outcome closureとStep 5.3 Evaluation Statement full / partial minimum fieldsをvalidatorで検証できる
- WCAG 2.0 / 2.1 / 2.2 Conformance Claimのrequired fields / full-scope guardをvalidatorで検証できる
- WCAG Statement of Partial Conformance - Third Party Content / Languageのrequired fields / guardをvalidatorで検証できる
- production helperとvalidatorが別実装
- semantic Case A〜W PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureでWCAG-EM orchestration E2EをPASSできる
