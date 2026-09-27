# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` のSkill package、成果物、production helper、deterministic validator、semantic evalを固定します。formal observation handoffのworkflow state / CAS / resume物理契約は `_04c_wcag-observation-handoff-state-contract.md` を正本とします。

## 1. package

```text
skills/wcag-conformance-evaluation/
├── SKILL.md
├── references/
│   ├── source-catalog.md
│   ├── wcag-em-2.md
│   ├── wcag-overview.md
│   ├── wcag-quickref.md
│   ├── understanding-conformance.md
│   ├── wcag2mobile-22.md
│   ├── earl-1.0.md
│   └── report-tool.md
├── assets/
│   ├── output-template.md
│   ├── wcag-2.0-requirements.json
│   ├── wcag-2.1-requirements.json
│   ├── wcag-2.2-requirements.json
│   ├── wcag-evaluation-procedure-catalog.json
│   └── wcag-semantic-contracts.json
├── scripts/
│   ├── runtime_contract.py
│   ├── wcag_requirements.py
│   ├── wcag_criterion_plan.py
│   ├── wcag_em_structure.py
│   ├── sampling.py
│   └── earl_report.py
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
- WCAG Overview
- How to Meet WCAG 2 (Quick Reference)
- Understanding Conformance
- Guidance on Applying WCAG 2.2 to Mobile Applications（responsive / touch / mobile Webがcurrent targetに含まれる場合）
- ACT Rules Format 1.1 / All ACT Rules
- Evaluation and Report Language (EARL) 1.0 Schema
- WAI-ARIA / ARIA in HTML
- Understanding Accessibility Support

WAI OverviewはWCAG-EM 2.0のresourceとしてWCAG-EM Report Toolを案内しています。ただし、Report Toolのfield / export schemaがWCAG-EM 2.0本文のStep 5要件と完全に同一であることは確認できていないため、本Skillのoutput contractはWCAG-EM 2.0本文を正本にします。Report Toolは補助resourceとして保持し、runtime dependencyにもschema Authorityにもしません。`references/source-catalog.md` は `_02d_reference-artifact-schema.md` の共通Sources table契約を再利用します。

### supported WCAG version

現在のsupported WCAG versionは `2.0 / 2.1 / 2.2` です。各versionを別catalogとして保持します。

- `assets/wcag-2.0-requirements.json`
- `assets/wcag-2.1-requirements.json`
- `assets/wcag-2.2-requirements.json`

各catalogは少なくとも次を保持します。

- WCAG version / source canonical URI
- Conformance Claimに使用するguideline title / version / claim URI
- Success Criterion machine key / number / level / canonical criterion URI
- Success Criterionごとのevaluation metadata。詳細は `_05h_wcag-criterion-evaluation-contract.md` を正本とし、finite procedure catalogへ解決する `procedure_keys` とexternal evidence可否を保持する
- 5つのWCAG conformance requirement machine key / canonical URI
- Conformance Requirementごとの固定rule metadata
  - Conformance Level: target level required Success Criteria refs
  - Full Pages: full page / automatically presented responsive variation closure
  - Complete Processes: process全stepのsame-or-better conformance requirement
  - Only Accessibility-Supported Ways of Using Technologies: baseline ref requirement
  - Non-Interference: version固有の固定Success Criteria refs
- Conforming Alternate Version contract
  - designated level
  - same information / functionality / human language
  - currentness
  - W3Cが定めるreachability alternatives
- Conformance Claim required field keys
- versionで利用できるConformance Claim optional field keys
- third-party monitoring / repair contract metadata。repair windowは2 business days
- Statement of Partial Conformance type / required semantic input / version-specific render metadata

自然言語のSuccess Criterion本文をruntimeへ複製する必要はなく、source item / canonical URLへ追跡できるmetadataに限定します。version間でSuccess Criteria集合やclaim contractを合成せず、target versionのcatalogだけをrequirement universe / claim contractとして使用します。

catalogはPR #11のstatic data契約を再利用します。strict JSON decode後のcanonical JSON SHA-256をtarget versionに応じて次へ保持します。

- `static_data_versions.wcag_2_0_requirements`
- `static_data_versions.wcag_2_1_requirements`
- `static_data_versions.wcag_2_2_requirements`
- `static_data_versions.wcag_evaluation_procedures`
- `static_data_versions.wcag_semantic_contracts`

deterministic validatorは選択versionのassetからhashを独立再計算します。さらに各catalogについてW3C正本と照合済みの承認済みhashをcontract testへ固定し、Success Criterion / levelの欠落や変更をassetとvalidatorが同時に見逃す構造を避けます。

`wcag_requirements.py` はtarget version / levelから期待requirement集合を独立導出します。

- A → 指定versionのLevel A Success Criteria
- AA → 指定versionのLevel A + AA Success Criteria
- AAA → 指定versionのLevel A + AA + AAA Success Criteria
- いずれも指定versionのWCAG conformance requirementsを別集合として含める

target WCAG version自体が不明・未指定の場合はInput不足として `unresolved` にします。現在catalogを持たない将来version等が明示された場合は `support_status=unsupported` とし、別versionへ暗黙変換しません。WCAG 3はWCAG-EM 2.0が対象とするWCAG 2 conformanceではないため本Skillの対象外です。

### Success Criterion evaluation contract

target version / levelから必要Success Criterionを列挙するだけでは完了としません。

`wcag_criterion_plan.py` は `wcag_requirements.py` が導出したrequired集合、required presentation variation集合、versioned requirements assetのevaluation metadata、`wcag-evaluation-procedure-catalog.json` から、sample / variation / processごとのcriterion evaluation rowを全件生成します。required集合 × variation集合とrow集合の差分、required procedure、未完了criterion集合、summary countはscriptが導出します。

具体的な契約は `_05h_wcag-criterion-evaluation-contract.md` を正本とします。

## 3. output-template.md

固定section:

1. Evaluation Header
2. Scope
3. Accessibility Support Baseline
4. Target Exploration
5. Presentation Variations
6. Observation Handoffs
7. Sampling Procedure / Selected Sample Set
8. Structured Sample
9. Random Sample
10. Complete Processes
11. Criterion Evaluation Plan
12. Sample Evaluation Results
13. Structured / Random Comparison
14. Findings
15. Evaluation Specifics（記録する場合だけ）
16. Evaluation Statement（通常 / partial。作成した場合だけ）
17. WCAG Conformance Claim / Statement of Partial Conformance（作成条件を満たした場合だけ）
18. Machine-readable Report（生成する場合だけ）
19. Limitations
20. Machine Runtime / Summary

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
- scope coverage rows: third-party content / services、language versions、responsive / device-dependent variations、separately hosted related areas、authenticated / restricted views
- out-of-product boundary / reason（存在する場合）
- conformance target
- additional requirement refs（存在する場合）

### Additional Evaluation Requirements

存在する場合、各row:

- additional requirement ref
- requester / source
- requirement summary
- affected step / output refs
- status: applied / blocked / out-of-scope
- required evidence / output refs
- closure evidence / reason

semantic layerは要求の意味とaffected step / output、本Skill目的内かを判断します。scriptはref採番、status enum、cross-reference、closureを担当します。本Skill目的内のrequirementをout-of-scopeへ変換しません。

### Accessibility Support Baseline

- baseline ref / revision
- previous baseline ref（拡張時）
- baseline description
- browser / user agent conditions
- assistive technology / adaptive approach conditions
- other software / settings conditions
- source / Authority refs
- formal evidenceへ使用したenvironment refs
- added environment refs / extension reason（拡張時）
- limitation

initial baseline外のenvironmentをformal evidenceへ使用した場合、scriptがbaseline setを比較しnew revisionをmaterializeします。diagnostic-only environmentはsemantic inputでformal evidence対象外と明示し、baselineへ追加しません。

### Target Exploration

各row:

- exploration ref
- kind: common-view / essential-functionality / sample-type / technology-relied-upon / other-relevant
- target / locator
- description
- rationale
- evidence / source refs

### Presentation Variations

Full Pages requirementのため、selected sampleごとにcurrent evaluationで確認するautomatically presented variationを明示します。

各row:

- variation ref
- sample ref
- source: project / Design System Authority、current target observation、responsive condition / boundary inventory、user agent / device condition
- variation description
- presentation condition
- environment ref
- viewport / container condition refs（存在する場合）
- responsive condition / boundary refs（存在する場合）
- evidence refs
- coverage status: `required / evaluated / undetermined / blocked`
- limitation

variation refはartifact-localに `VAR-001` からscriptが採番します。

semantic layerは、同じpageで情報・機能・interaction / presentationが意味上異なるautomatically presented variationかを判断できます。scriptはAuthority / machine observationからcandidate variation rowを生成し、duplicate、ref、required set、evaluation coverageをmaterializeします。

current responsive condition / boundary inventoryがcompleteで、project / Design System Authorityと観測結果から既知のautomatically presented variation集合を閉じられる場合だけ、その集合をrequired variation setとして使用できます。

unreadable / unsupported / not-executable responsive condition、未知device-dependent variation、必要なvariationへ到達できない状態が残る場合はFull Pages requirementを `satisfied` にしません。`undetermined / blocked` として残します。

continuousなwidthの全CSS pixelをvariation rowとして列挙しません。distinct variationの意味判断とcriterion固有のviewport条件を分離し、Reflow等の特定viewport要求は `_05h` のcriterion procedureで別途評価します。

### Observation Handoffs

各row:

- handoff ref
- retry_of_handoff_ref（再観測の場合）
- originating evaluation artifact ref / revision
- workflow_ref（qa-workflow管理下の場合）
- resume operation: step-4.1-sample / step-4.2-process
- sample ref
- variation ref
- process ref（存在する場合）
- required requirement refs
- observation request refs / request kind (`wcag-machine-probe / semantic-observation`)
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
- previous evaluation / sample set ref（再評価の場合）
- rerun lineage: retained / replaced / added / unavailable sample refs（再評価の場合）
- sampling approach / size change reason（再評価で変更する場合）
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
- selection status: `target-met / exhausted-no-new-view / blocked`
- candidate scope / provenance
- finite inventory ref / completeness（finite inventoryを使う場合）
- selected sample refs
- duplicate replacement記録
- exhaustion evidence / provenance（`exhausted-no-new-view` の場合）
- blocked reason（`blocked` の場合）

`exhausted-no-new-view` はcomplete finite inventoryまたはscope-wide exhaustion evidenceを持つ場合だけmaterializeします。candidate取得不完全をno-new-sample completionとして保存しません。

### Complete Processes

各process:

- process ref
- starting sample ref
- default sequence。sample refとsample間actionを順序付きで保持
- commonly accessed / critical branch sequences
- process completion condition
- evidence / source refs

URLだけでdynamic state / process sampleを識別できない場合は、必要なstate / action / locatorを保持します。

### Criterion Evaluation Plan

`_05h_wcag-criterion-evaluation-contract.md` のcanonical outputを保存します。

各row:

- criterion evaluation ref
- sample ref
- variation ref
- process ref（存在する場合）
- criterion ref
- procedure execution refs
- applicable population: `present / none / unknown`
- execution status: `pending / in-progress / complete / blocked`
- result: `satisfied / not-satisfied / undetermined / null`
- observation / measurement / ACT / semantic / manual / AT / external evidence refs
- limitation / blocker

このsectionは `wcag_criterion_plan.py` のmachine-owned outputです。Agentが別のSuccess Criterion result一覧を手作成しません。

### Sample Evaluation Results

各row:

- sample result ref
- sample ref
- variation ref
- sample kind
- process ref（存在する場合）
- requirement ref
- Success Criterion / conformance requirement
- criterion evaluation ref（Success Criterion rowでは必須）
- result: satisfied / not-satisfied / undetermined
- observation / test rule result refs
- evidence refs
- unmet example refs（not-satisfiedの場合）
- reused result ref / unchanged-content evidence（Step 4.2でcurrent resultを再利用した場合）
- limitation

Success Criterion rowはcurrentな `criterion_evaluation_ref` の `execution_status=complete` / resultからだけscriptがmaterializeします。Conformance requirement rowはcurrent Success Criterion result集合とversioned conformance requirement metadataから導出します。

Conforming Alternate Versionを使う場合、alternate versionを別sample rowとして数えません。同じfull page resultへalternate version refsを紐付け、target level、same information / functionality / human language、currentness、reachability alternativeの各condition resultを保持します。Full Pagesはsampleのrequired variation集合すべてがtarget levelへ閉じている場合だけsatisfiedにできます。Non-Interferenceはtarget version catalogの固定Success Criteria refsからscriptがrequired result refsを生成します。

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
- not-satisfied Conformance Requirement / Success Criterionごとの最低1 example coverage
- Step 1.4で全occurrence報告が要求された場合の追加coverage
- human-readable report / Evaluation Statement / accompanying documentationのaccessible output closure

script / validatorは `not-satisfied requirement set - example-covered requirement set` を計算し、差分0を要求します。accessible output closureでは、少なくともheading hierarchy、table header、画像 / screenshot evidenceのtext description、色だけに依存しない状態表現、意味の分かるlink textを検証します。HTML / PDF等へ別ownerが変換した後の形式はこのclosureへ含めません。

Step 5.2 / 5.3 / 5.5はoptional methodology requirementですが、本Skillの目的内機能として実装します。利用者要求、Step 1.4 additional requirements、またはreport出力条件に応じて生成します。Step 5.4 aggregated scoreだけは、単一scoreが誤解を招きやすくWCAG 2もrating schemeを提供しないため、本Planの目的外として生成しません。

### Supported output formats / external template boundary

本Skillが直接materializeする物理出力は次へ固定します。

- `output-template.md` に基づくcanonical human-readable WCAG-EM report
- target WCAG 2.2で条件を満たす場合のEvaluation Statement section
- target version contractを満たす場合のWCAG Conformance Claim / Statement of Partial Conformance
- Step 5.5要求時の`earl-report.jsonld`

任意の外部document format、顧客固有template engine、PDF / Office generator、第三者report service exporterは追加しません。

追加評価要件がreportへ必要なfield / occurrence / sectionを要求する場合は、canonical report上で目的内情報として `applied / blocked` へ閉じます。別formatへの変換が必要ならcanonical field / refをdownstream ownerへ渡し、評価内容を欠落させたまま「format非対応」でout-of-scopeにはしません。

未知templateのためにgeneric renderer / plugin frameworkを作りません。
### Evaluation Specifics

Step 5.2を記録する場合、次をglobal / sample / individual checkの適切なscopeへ保持できます。

- evaluated sample archive ref。raw copyを保存する場合はimmutable ref / revision / SHA / content identityを必須にする
- screenshot / DOM等の保存済みevidence ref
- sampleへ到達するpath
- sample生成・navigationに使ったsettings / input / actions
- evaluation tool、browser、add-on、assistive technology、その他softwareのname / version
- evaluation method / procedure / technique
- record scope: evaluation / sample / check
- confidentiality / retention / access limitation

sample copyやDOM等を保存できない場合は無理に複製せず、保存不可理由と再取得可能な非secret参照を残します。password、token、cookie、storageState値等のsecretは保存しません。test accountが必要でもcredential valueを記録せず、role / 非secret alias / external credential refだけを保持します。不要な個人識別情報は複製しません。

### Evaluation Statement

現行WCAG-EM 2.0 Step 5.3はminimum fieldとしてWCAG 2.2を明示しているため、**このmethodologyに従うEvaluation Statementの生成対象はtarget WCAG 2.2だけ**とします。target WCAG 2.0 / 2.1のformal evaluationではStep 5.1 report、Step 5.2、Step 5.5、version別WCAG Conformance Claim / Statement of Partial Conformanceは利用できますが、WCAG 2.2を2.0 / 2.1へ読み替えたStep 5.3 Evaluation Statementは生成しません。

作成する場合は `statement type: full / partial` を必須にし、他sectionへのrefだけで意味が失われないよう、少なくとも次をstatement sectionへ明示します。

共通field:

- issued date
- WCAG 2.2 title / canonical URI
- evaluated conformance level
- digital product definition / scope ref
- technologies relied upon。Step 2.4のexploration refへ追跡可能にする
- accessibility support baseline ref
- product ownerのvalidity / accuracy維持commitmentを確認したevidence / ref

`full` はtarget WCAG versionが2.2で、全non-optional methodology requirementが完了し、全sampleがtarget conformance levelを満たす場合だけ生成できます。

`partial` はtarget WCAG versionが2.2で、全non-optional methodology requirementとproduct owner commitmentを満たしたうえで、次を追加で必須にします。

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

representative sampleだけではclaimを生成しません。claimに使用するguideline title / version / URIはtarget version catalogのclaim fieldを使い、source取得用canonical URLから推測しません。third-party contentを監視・修復する経路でfull claimを成立させる場合は、全該当pageでnon-conforming contentを識別できること、継続monitoringできること、検出したnon-conforming contentを2 business days以内にremove / bring into conformanceできることをevidenceで必須にします。scriptはrepair window / coverage guardを固定し、control ownershipやmonitoring可能性の意味判断だけをsemantic layerへ残します。

WCAG Statement of Partial ConformanceはConformance Claimではありません。次を別typeとして扱います。

- `third-party-content`: 対象pageが非適合だが、明示したuncontrolled contentを除けば指定version / levelへ適合する。該当contentがauthor control外で、利用者が識別できるdescriptionを持つこと
- `language`: 対象pageが非適合だが、明示したlanguageについてaccessibility supportが存在すれば指定version / levelへ適合すること

scriptはtarget version / levelと対象parts / languagesからW3Cのstatement formに沿うcanonical文をrenderし、LLMへ定型文を手書きさせません。semantic layerはcontrol ownership、language support不足、除外時に適合するという意味判断を行い、scriptはtype、必須field、対象範囲、target version / level、生成可否をmaterialize / validateします。

Conformance Claimのoptional componentsもevidenceがある場合に保持できます。

- claimed levelを超えて満たしたSuccess Criteria
- used but not relied upon technologies
- testingに使用したuser agents / assistive technologies
- versionで定義されているadditional accessibility characteristics
- Success Criteriaを超えて行った追加accessibility施策
- technologies relied uponのmachine-readable mirror
- conformance claimのmachine-readable mirror

optional componentsはrequired componentsを代替しません。machine-readable mirrorはMachine Runtimeのnormalized claim objectを正本とし、W3Cが指定していない独自claim標準を新設しません。

### Machine-readable Report

Step 5.5を生成する場合はEARL 1.0 vocabularyを使ったJSON-LD sidecar `earl-report.jsonld` を `earl_report.py` が生成します。物理serialization、固定 `@context`、node identity、Assertion / TestResult分離、outcome / mode mapping、byte-level deterministic renderingは `_05l_earl-jsonld-serialization-contract.md` を正本とします。追加RDF / JSON-LD libraryは導入せず、固定したEARL subsetを標準libraryでrenderします。ここでいうcanonicalはrepository内のdeterministic serializationであり、RDF dataset canonicalizationを意味しません。

formal requirement resultごとに少なくとも次を出力します。

- `earl:Assertion`
- `earl:assertedBy`
- `earl:subject`: canonical sample / variation identityから `_05l` のstable IRIを生成
- `earl:test`: target version static catalogが持つcanonical Success Criterion / conformance requirement URI
- `earl:result`。`earl:TestResult` nodeへのIRI参照
- `earl:mode`

対応する `earl:TestResult` nodeに `earl:outcome` を持たせます。`earl:outcome` をAssertion直下へ置きません。

outcome mapping:

- Success Criterion rowで `applicable_population=none` かつrequired closure complete → human-readable resultは `satisfied` のまま `earl:inapplicable`
- 上記以外の `satisfied → earl:passed`
- `not-satisfied → earl:failed`
- `undetermined → earl:cantTell`
- 未実施resultをblocked / incomplete artifactへ明示する場合だけ `earl:untested`

test modeはevidence provenanceから `automatic / manual / semiAuto / undisclosed / unknownMode` のいずれかを選び、判定できないmodeを推測しません。EARL側でapplicabilityを保持し、human-readable WCAG resultの `satisfied` と機械的に1対1対応させません。

EARL sidecarはhuman-readable WCAG-EM reportの代替ではありません。assertion数、stable assertion / subject identity、test / outcomeとhuman-readable formal result集合が一致することをdeterministic validatorで確認します。artifact-local refをEARL IRIとして直接公開しません。

## 3.1 wcag_requirements.py

Input:

- target WCAG version
- target conformance level

Function:

- target versionが2.0 / 2.1 / 2.2のどれかであることを検証
- target versionに対応するstatic catalogを選択
- target levelに必要なSuccess Criteria集合を導出
- target versionの5つのWCAG conformance requirement集合を導出
- Non-Interference required Success Criteria refsを導出
- Conforming Alternate Version required condition keys / reachability alternativesを導出
- target versionのclaim guideline title / version / URIとthird-party repair contractを導出
- WCAG 2.0 / 2.1の4.1.1についてcontent technologyがHTML / XMLなら `always-satisfied-html-xml`、それ以外は `evaluate-normative-rule`、WCAG 2.2はcriterion不存在というversion rule metadataを導出
- duplicate / unknown requirement keyをreject
- expected requirement setをcanonical sort
- target version以外のcatalogを混在させない

Output:

- support_status: supported / unsupported
- target WCAG version
- required Success Criterion refs（supported時だけ）
- required conformance requirement refs（supported時だけ）
- target versionに対応する `static_data_versions` key / hash
- target versionのconformance rule metadata
- target versionのclaim contract metadata
- issues

Agent / LLMが「今回評価すべきSuccess Criteria一覧」を完成集合として入力しません。semantic applicability / exceptionは各requirement result内で判断しますが、requirement universe自体は指定versionのstatic catalogが正本です。明示的なunsupported versionとmissing / unresolved inputもこのhelperの出力・呼び出し前validationで区別します。

## 3.2 runtime_contract.py

PR #11のcurrent Machine Runtime契約を再利用します。独自runtime envelopeは作りません。

deterministic runtimeへ載せるもの:

- `wcag_requirements.py` のversion / level → expected requirement集合 / Conformance Requirement fixed rule metadata
- finite procedure catalog hash / key解決 / machine dispatch contract
- sample identity registry / selected set / duplicate / overlap / union
- presentation variation registry / required variation coverage
- criterion evaluation planのrow / execution status / result closure
- rerun sample lineage / previous-current identity resolution
- random target count、candidate population fingerprint、selection result validation
- complete process materialization
- accessibility support baseline set / revision extension
- Conforming Alternate Version condition row skeleton / Non-Interference fixed Success Criteria refs
- Step 4.2 unchanged-result reuse eligibility
- Step 4.3 compare / reconcile
- Step 5.1 unmet-example coverage / accessible output closure
- freshness / currentnessに必要なnormalized input
- `wcag_em_structure.py` のclosure / cross-reference / Evaluation Specifics / statement / claim guard / machine-owned section materialization
- `earl_report.py` のhuman-readable result → `_05l` 固定EARL 1.0 JSON-LD graph / deterministic byte materialization

deterministic runtimeへ載せないもの:

- random sampleの実選択。OS randomnessや外部random mechanismを使うため、同一Input→同一Outputを要求しない
- structured sampleの代表性判断
- sample / content type / Findingの意味的同一性判断
- partial statement reason、third-party control、language support等の意味判断
- previous structured sampleのうち比較可能性 / current representativenessのため何をretain / replaceすべきか
- Conforming Alternate Versionのsame information / functionality / human language / currentnessの意味判断

random selection結果はmethod / provenance / selected sample identityとともに後続Machine Runtime Inputへ渡します。保存済みsample resultはPR #11 current verifierでfreshnessを再計算し、currentの場合だけ再利用します。

runtime Inputには少なくともtarget WCAG version / level、scope、scope coverage rows、normalized additional evaluation requirements、accessibility support baseline revision、environment、previous evaluation / sample lineage（再評価の場合）、sample identity、evidence identity、Authority / reference refs、選択versionのstatic data versionを含め、これらが変わった場合に旧resultをcurrent扱いしません。

## 3.2 wcag_criterion_plan.py

Input:

- target WCAG version / level
- `wcag_requirements.py` のrequired Success Criterion集合
- versioned requirements assetの `procedure_keys`
- `wcag-evaluation-procedure-catalog.json`
- canonical sample / required presentation variation / process refs
- current observation / measurement / supported ACT Rule refs
- semantic / manual / assistive technology / external evidence procedure result refs

Function:

- required sample × variation × Success Criterion全件を `CRIT-001` からartifact-localに採番
- procedure keyをfinite procedure catalogへ解決し、execution rowをmaterialize
- machine procedureのdispatch key / semantic decision key / required evidenceを検証
- selected procedureからlive observation requirementをdeduplicateしてformal handoff inputへ変換
- required criterion × variation集合とactual row集合の集合差分
- applicable population `present / none / unknown` のclosure
- execution status `pending / in-progress / complete / blocked` とresult `satisfied / not-satisfied / undetermined / null` の整合
- required procedure closure
- ACT Rule部分結果をSuccess Criterion全体の `satisfied` へ不当に昇格しない
- machine-owned criterion section / summaryをrender

Output:

- criterion evaluation plan rows
- formal handoff observation requirements
- missing / duplicate / unresolved criterion / variation refs
- procedure catalog resolution issues
- completion status
- rendered machine-owned section
- issues

scriptはSuccess Criterion本文を自然言語rule engineとして解釈しません。固定metadataと明示dispatchだけを扱います。

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

### materialize-repeat-evaluation

samplingを使う再評価で使用します。

Input:

- previous evaluation / sample set ref
- previous structured / random / process sample identities
- current canonical sample identity registry
- current exploration coverage refs
- semantic decision: significant change / structured retain-replace decisions
- current candidate population / provenance

Function:

- previous identityをcurrent identityへ解決し、見つからないものを `unavailable` にする
- structured sampleを `retained / replaced / added` へmaterialize
- stale / duplicate identityをrejectする
- significant changeで比較可能性を維持できない場合はprevious sampleをcurrent setへ無理に保持しない
- sampling approach / target size変更があればreasonを要求する
- random sampleのreplacement identityをLLM inputから受け付けず、current candidate populationから `select` へ渡す

Output:

- retained / replaced / added / unavailable sample refs
- current structured revision
- random replacement count / selection request
- sampling approach / size change reason
- issues

W3Cの「typically about half」はsemantic guidanceとして扱い、replacement ratioを固定値にはしません。

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
- selection status: `target-met / exhausted-no-new-view / blocked`
- targetを満たせなかった場合のreason
- exhaustion evidence / provenance（`exhausted-no-new-view` の場合）

`target-met` はselected unique countがtarget countへ到達した場合です。

`exhausted-no-new-view` はtarget count未満でも、complete finite inventoryのeligible unique candidateを全件消費した場合、または外部random mechanismがtarget scope全体を対象に追加unique viewなしまで探索したことをtool identity / method / candidate scope / completeness / provenance付きで返しvalidatorが確認できる場合だけ使用します。

listing truncation、crawler / search / log取得失敗、permission不足、rate limit、unknown completeness、外部toolが十分なsampleを返さなかっただけの状態は `blocked` とします。

同じInputから同じselectionを返すことは要求しません。

target全体を有限候補として列挙できない場合はfinite inventory経路を無理に使いません。semantic / research工程はmethodの適用性とcandidate scope / provenanceを判断できますが、個々のsample identityは選びません。candidate listを作れる場合はscriptがそこからrandom選択し、外部tool自体がrandom selectionする場合だけそのselected refsを受け取ります。target件数を満たせずscope-wide exhaustionも証明できない場合はStep 3.2を完了せず `blocked` にします。

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
- top-up / reselection結果が `blocked` の場合は次comparisonへ進まない。`exhausted-no-new-view` はscope-wide exhaustion evidenceを保持した場合だけcompletionに数える
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
- selection statusとselected count / target countの整合
- `exhausted-no-new-view` のcomplete candidate / scope-wide exhaustion evidence
- `blocked` をStep 3.2 completionへ数えていない
- no-new-sample exception整合

を検証します。

## 5. wcag_em_structure.py

final artifact assemblyのownerです。

Input:

- evaluation headerのsemantic field
- previous evaluation / sample lineage semantic input（再評価の場合）
- scope / scope coverage / accessibility support baselineのsemantic decisions
- formal evidenceへ採用するenvironment decisions
- additional evaluation requirement semantic decisions
- sampling procedure semantic decision: 製品全体を評価可能か
- exploration decisions
- structured sample selection decisions
- finite inventory / recorded random selection provenance
- process semantic definitions
- presentation variation semantic decisions / Authority / responsive condition / boundary inventory
- observation handoff semantic requirements
- qa-workflow handoff closure result / `may_resume` / current returned result refs（`_04c` のdeterministic helper出力）
- returned inspection artifact / evidence refs
- `wcag_criterion_plan.py` のcurrent criterion evaluation plan / procedure execution result
- Conforming Alternate Version semantic decisions: same information / functionality / human language / currentness
- Step 4.2 changed / unchanged content semantic identity decisions（machine identityだけで確定できない場合）
- content type / Finding grouping decisions
- Finding semantic input
- optional Evaluation Specifics input / archive refs
- optional Evaluation Statement semantic input
- optional WCAG Conformance Claim evidence / optional components
- optional WCAG Statement of Partial Conformance semantic input / evidence
- machine-readable report request / assertor metadata
- limitation

各draftはinvocation内で一意な `draft_key` を持ちます。

Function:

- unknown field / enum / required field検証
- `wcag_requirements.py` のexpected requirement universeを読み、LLM supplied listではなくtarget levelからrequired coverageを生成
- `sampling.py` のentire-product / candidate / selection / process / reconciliation / comparison resultだけからmachine-owned sample / comparison fieldをmaterialize
- canonical sample identity registryを先にmaterializeし、structured / random / process-added集合は同じsample refを参照する
- artifact-local ref採番
  - additional evaluation requirement: `ADDREQ-001`
  - accessibility support baseline: `BASELINE-001`
  - exploration: `EXPLORE-001`
  - presentation variation: `VAR-001`
  - observation handoff: `HANDOFF-001`
- draft key → final ref解決
- cross-reference解決
- WCAG-EM Step 1〜5 closure
- scope coverage row / in-scope closure
- accessibility support baseline set / revisionをmaterializeし、formal evidenceで使ったinitial-baseline外environmentを追加する
- previous evaluation / sample lineageをcurrent identityへ解決し、rerun retained / replaced / added / unavailable closureをmaterializeする
- additional evaluation requirementごとにaffected step / outputを固定し、`applied / blocked / out-of-scope` とrequired evidence / output refsのclosureをmaterializeする。目的内要件のout-of-scopeは禁止
- sampling procedure used / skippedとselected sample set closure
- sampling skippedではcomplete inventory → selected sample set traceabilityとstructured / random / Step 4.3 not-applicable closure
- sampling usedではexploration → structured sample traceability
- selected sampleごとにrequired presentation variation registryをmaterializeし、Full Pages variation coverageを閉じる。unknown / unreachable variationをsuccess扱いしない
- observation handoffごとにoriginating evaluation / revision / resume operation / sample / variation / expected observation refsをmaterializeする
- workflow stateへの永続化・returned result集合のcurrentness / supersedes / CAS closureは `_04c` のqa-workflow helperを正本とし、`wcag_em_structure.py` はその `may_resume` / current returned refsだけを受け取る
- `may_resume=false`、origin stale、handoff blockedのいずれかではformal aggregationへ進めない
- complete process sequence closure
- process-added sample coverage
- Conforming Alternate Versionを別sampleへ数えずfull page resultへcondition rowsをmaterializeする
- Non-Interference fixed Success Criteria refsをtarget version catalogからmaterializeする
- Step 4.2でcurrent unchanged resultのreuse eligibilityをmachine evidence / freshnessからmaterializeし、変化または不明なcontentを再評価対象へ送る
- `wcag_criterion_plan.py` のrequired criterion × variation coverage、execution status / result closureを正本としてSuccess Criterion sample resultをmaterializeし、LLM supplied result listを受け付けない
- target levelから独立導出したrequired sample result coverage
- Full Pages requirementはrequired variation集合の全current Success Criterion / target level resultからmaterializeする
- Step 4.3集合差分からiteration action / chain closureをmaterialize
- structured revision更新時のcandidate population fingerprint再計算、population同一時のold random retention / overlap removal / top-up、population変更時のreselection、process再materializeを反映
- sample result freshnessをPR #11 current verifier結果から反映し、stale resultをclosureへ数えない
- Step 5.1でStep 1〜4の各required outcomeが成果物へ存在すること
- not-satisfied Conformance Requirement / Success Criterionごとの最低1example coverageをmaterialize / validateする。Step 1.4でall-occurrence reportingを要求した場合は全occurrence closureも分離して検証する
- human-readable report / Evaluation Statement / accompanying documentationについて本Skill所有形式のaccessible output closureをmaterializeする
- Step 5.2 Evaluation Specificsのrecord scope / evidence refs / software metadata / secret非複製
- Evaluation Statementはtarget WCAG 2.2の場合だけfull / partial minimum fieldsと生成条件をmaterializeし、2.0 / 2.1ではStep 5.3 sectionを生成しない
- WCAG Conformance Claim / Statement of Partial Conformanceはtarget version catalogのclaim contractからtype別required / optional fieldsと生成条件をmaterialize。third-party monitoring / repair経路では2 business days / all-affected-pages identification guardを適用
- Step 5.5 EARL sidecar request / ref / closure
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

現行Step 5.3 contractに従い、target WCAG versionが2.2の場合だけ生成します。2.0 / 2.1のevaluation結果をStep 5.3準拠statementと表現しません。

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

## 8. earl_report.py

Input:

- evaluation / assertor identity
- canonical sample registry
- target version static catalog
- current sample requirement results
- evidence provenance / test mode
- optional pointer / human-readable info

Function:

- static catalogのcanonical criterion URIを使ってassertionを生成
- `_05l` のcanonical identityからsubject / assertion / TestResultのstable `urn:qa-workflow-skills:earl:...` IRIを生成し、artifact-local refをIRIへ直接使用しない
- formal criterion resultと `applicable_population` からEARL outcomeを固定mappingする。`applicable_population=none` かつcomplete closureならhuman-readable resultは `satisfied` のまま、EARL outcomeだけ `earl:inapplicable` とする
- modeはactual provenanceからのみmappingし、判定不能なら `unknownMode`
- `_05l` の固定key / node orderingでstable sort
- repository内deterministic JSON-LDをrender

Output:

- `earl-report.jsonld` content
- assertion refs / count
- issues

## 9. deterministic validator

production helperとは別実装で少なくとも次を検証します。

- output section / schema
- required Input
- supported WCAG version = 2.0 / 2.1 / 2.2
- explicit unsupported versionとmissing / unresolved inputが混同されていない
- target versionに対応する `static_data_versions` hashをassetから独立再計算
- target versionに対応する承認済みcatalog hashと一致
- `wcag-evaluation-procedure-catalog.json` のcanonical hash / approved hash一致
- `wcag-semantic-contracts.json` のcanonical hash / approved hash一致とtarget version criterion coverage
- requirement assetのprocedure key全件がprocedure catalogへ解決し、machine procedure全件に明示dispatchがある
- target version以外のcatalogをexpected requirement集合へ混在させていない
- static catalogから独立導出したtarget level required Success Criteria / conformance requirement集合とactual coverageの一致
- scope coverage rows / in-scope closure
- selected sampleごとのrequired presentation variation registry / completeness / evidence
- responsive condition / boundary inventory incomplete / not-executableをFull Pages satisfiedへ数えていない
- accessibility support baseline revision / extensionとformal evidence environmentの一致
- previous evaluation / rerun sample lineage（該当時）
- additional evaluation requirementsのref / affected step / status / output closure
- sampling procedure used / skippedとselected sample set closure
- sampling skipped時のcomplete inventory / selected set一致、structured / random / Step 4.3 not-applicable、complete process評価継続
- sampling used時のstructured sample traceability
- canonical sample identity registry
- random sample target count
- random sample duplicate / overlap
- finite inventory時のcandidate derivation / provenance、またはrecorded method時のcandidate scope provenance
- candidate population fingerprint
- selection method
- selection status `target-met / exhausted-no-new-view / blocked`
- `exhausted-no-new-view` のcomplete exhaustion evidence、`blocked` のreason
- process sequenceから導出したprocess-added sample / membership closure
- Conforming Alternate Versionが別sampleに数えられず、required condition / reachability alternativeがtarget version contractと一致
- Non-Interference fixed Success Criteria refs / result coverage
- Step 4.2 unchanged-result reuseがidentity / evidence / freshnessでcurrentなものだけに限定される
- observation handoffのoriginating evaluation / revision / resume operation / expected observation refsとreturned inspection artifact cross-reference
- `_04c` helperが出したhandoff state / CAS / current returned lineage / `may_resume` とformal artifactの整合
- sample result cross-reference
- target levelに必要なrequirement result coverage
- `wcag_criterion_plan.py` が生成したrequired Success Criterion × variation row coverage / procedure closure。required集合との差分、duplicate、pending / in-progress / blocked残存を完了へ数えない
- final Success Criterion resultがcurrent `criterion_evaluation_ref` から生成され、LLM supplied result listで迂回されていない
- applicable population noneがcomplete procedure evidenceなしに生成されていない
- normalized content type / Finding group keyの集合差分とStep 4.3 derived action / iteration chain
- structured revision更新後のcandidate population fingerprint再計算、population同一時のoverlap除外 / retained random / top-up、population変更時のreselection、process再materialize
- sample result freshness / stale再評価
- Step 5.1のStep 1〜4 outcome closure
- not-satisfied Conformance Requirement / Success Criterion setとexample-covered setの差分0
- Step 1.4 all-occurrence reporting指定時の全occurrence closure
- human-readable report / Evaluation Statement / accompanying documentationのaccessible output contract
- Step 5.2 Evaluation Specificsのscope / archive identity / tool metadata / secret・不要PII非複製
- Evaluation Statementはtarget WCAG 2.2だけでfull / partial生成条件とStep 5.3 minimum fieldsを検証し、2.0 / 2.1ではsection不存在を要求
- WCAG Conformance Claim required / optional fieldsをtarget version catalogのclaim contractから検証し、claim guideline URI / full-scope coverage / third-party 2-business-day monitoring-repair guardを適用
- WCAG Statement of Partial Conformance third-party / language guard / canonical wording
- Step 5.5 EARL固定 `@context`、Assertion / TestResult node shape、stable IRI、criterion URI、outcome mapping、mode provenance、deterministic bytes、human-readable reportとのassertion coverage一致
- Finding refs
- secret / credential非複製

random selectionの結果そのものが「十分randomだったか」を同じvalidatorで証明しません。method / candidate scope / fixed-seed禁止等の契約を検証します。

## 10. semantic eval

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

### Case C2: additional evaluation requirement

evaluation commissionerが「representative examplesだけでなく、検出したissueの全occurrenceをreportする」「Step 5.5 machine-readable reportを含める」等、本Skill目的内の追加要件を指定する。

→ semantic layerがaffected step / outputを確定し、scriptが `ADDREQ-001` 等を採番して必要outputへcross-referenceし、`applied` closureを作る。目的内だが環境不足なら `blocked`、human participant study等の明示目的外だけを理由付き `out-of-scope` とする。

### Case D: structured sample

Step 2 explorationを反映したsampleを選ぶ。

### Case E: random sample

structured sampleの10%要件、unique、non-overlap、selection methodを満たす。

### Case F: no unique random candidate

complete finite inventoryまたはscope-wide exhaustionを証明できる外部mechanismで、新しいunique sampleが存在しない。

→ `selection_status=exhausted-no-new-view` とevidenceを記録してStep 3.2を閉じる。

### Case F2: candidate acquisition incomplete

crawler / search / log / external random mechanismがtarget countを満たせず、listing / scope-wide exhaustionのcomplete evidenceもない。

→ `selection_status=blocked`。no-new-sample completionへ変換せずStep 3.2を完了しない。

### Case G: complete process

default / critical branch sequenceを含める。

### Case H: Step 4.3 retry

random sampleから新content type / findingを検出。

→ Step 2 / 3へ戻りstructured sampleを更新して再評価。

### Case I: full Evaluation Statement

target WCAG 2.2で、全non-optional methodology requirement、全sample target達成、product owner commitment、minimum fieldsが揃う。

→ `statement_type=full` を生成する。条件不足なら生成しない。

### Case J: partial Evaluation Statement

target WCAG 2.2で、一部sampleがtargetを満たさないが、全non-conforming areaをWCAG-EM 2.0のpartial理由へ対応付けられ、他の共通条件を満たす。

→ `statement_type=partial` とarea / reasonを生成する。許可reason外または未説明areaがあれば生成しない。

### Case K: expertise / environment limitation

必要なassistive technology / expert judgmentを利用できない。

→ blocked / undetermined。

### Case L: supported WCAG versions

WCAG 2.0 / 2.1 / 2.2をそれぞれ指定。

→ 各versionのcatalogだけを使い、version / levelに対応するexpected requirement集合を生成する。2.0 / 2.1を2.2へ変換しない。2.0 / 2.1でもformal reportは閉じるが、Step 5.3 Evaluation Statementは生成しない。

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

### Case X: Evaluation Specifics

Step 5.2記録を要求し、sample archive、browser / tool / assistive technology、path / settings / actionsを入力する。

→ immutable evidence refと再現情報を保存し、password / token / cookie / storageState値や不要PIIを保存しない。

### Case Y: EARL machine-readable report

Step 5.5を要求し、`satisfied / not-satisfied / undetermined` のformal resultを含む。

→ canonical JSON-LDを生成し、`passed / failed / cantTell` へ一意にmappingし、assertion coverageがhuman-readable reportと一致する。

### Case Z: optional Conformance Claim components

required claim fieldsを満たし、higher-level SC、not-relied-upon technology、user agent / AT等のoptional evidenceも存在する。

→ optional componentsをnormalized claimへ保持するが、required fieldの代替には使わない。

### Case AA: baseline extension

initial baseline外のscreen reader / browser combinationをformal evidence取得に使用する。

→ returned environmentをbaselineへ追加してnew baseline revisionを生成し、関連freshnessを再計算する。diagnostic-only利用なら追加しない。

### Case AB: repeat evaluation

previous evaluation / sample setがあり、current productにsignificant changeはなく一部sampleを比較用に保持しつつcoverageを更新する。

→ previous sampleをcurrent identityへ解決し、structured sampleをretained / replaced / addedへmaterializeする。50% replacementを固定規則にせず、random replacement identityはscript / external random mechanismが選ぶ。

### Case AC: conforming alternate version

primary contentがtarget levelを満たさないがalternate version候補がある。

→ alternate versionを別sampleへ数えず、target level、same information / functionality / human language、currentness、reachability alternativeの全conditionを閉じる。意味条件が不足すればConformance Levelをsatisfiedにしない。

### Case AD: non-interference

not-relied-upon contentを含むsampleを評価する。

→ target version catalogのNon-Interference Success Criteria refsをscriptが追加し、required resultが欠ければconformance requirementをsatisfiedにしない。

### Case AE: Step 5.1 example coverage / accessible report

複数のnot-satisfied Success Criterion / Conformance Requirementを含むreportを生成する。

→ 各not-satisfied refに最低1exampleを対応付け、human-readable reportのheading / table / image text / status expression contractを検証する。Step 1.4でall-occurrence reporting指定時は全occurrenceも閉じる。

### Case AF: third-party monitored full claim

uncontrolled third-party contentを含むpageについてmonitoring / repair経路でfull conformance claimを作る。

→ all affected pagesでcontentを識別でき、monitoring可能で、non-conforming contentを2 business days以内にremove / bring into conformanceできるevidenceが揃う場合だけclaim guardを通す。

### Case AG: required criterion execution coverage

target WCAG version / levelのrequired Success Criterion集合を生成し、1 criterionのevaluation rowを欠落させる。

→ `wcag_criterion_plan.py` / deterministic validatorが欠落を検出し、他criterionがすべて `satisfied` でもsampleをcompleteにしない。supported ACT Ruleがないcriterionもsemantic/manual / assistive technology経路を持ち、評価対象から落とさない。

### Case AH: responsive Full Pages variation

同じsampleにscreen sizeで自動提示される複数variationがあり、1 variationのcriterion resultが欠落する。

→ required variation registryとcriterion planの集合差分を検出し、Full Pagesをsatisfiedにしない。unreadable / unsupported / not-executable responsive conditionが残る場合もvariation completenessを推測しない。

### Case AI: browser再観測

`HANDOFF-001` でbrowserを開始済みだがreturned resultがstaleになり、同じorigin revisionで再観測が必要になる。

→ started claimを削除・再利用せず、`HANDOFF-002` を `retry_of_handoff_ref=HANDOFF-001` としてmaterializeし、新operation refで観測する。exact duplicate result再送はnew handoffを作らない。

### Case AJ: criterion plan bypass

LLM suppliedのSuccess Criterion resultをfinal sample resultへ直接入力する。

→ `wcag_em_structure.py` がrejectし、current criterion evaluation ref / complete procedure closureからだけsample resultを生成する。

## 11. 完了条件

- package単体でSkill contractを理解できる
- sibling Skillのscriptsへruntime依存しない
- formal direct trigger後にlive observationが必要な場合、qa-workflowが利用可能なら `_04c` のstate / CAS / claim / expected-returned closureを通ってhandoff → usability-inspection → formal Skill resumeへ遷移し、qa-workflowを利用できないstandalone環境だけblockedへ閉じられる
- WCAG-EM Report ToolをWCAG-EM 2 schema Authorityとして扱わず、runtime dependencyにもしていない
- Step 1.4 additional evaluation requirementsをartifact-local refへ採番し、目的内要件をaffected step / outputへ反映してappliedまたはblockedへ、明示目的外だけを理由付きout-of-scopeへ閉じられる
- scope coverageでthird-party / language / responsive-device / separately-hosted / authenticated-restricted領域を明示的に閉じられる
- initial baseline外environmentをformal evidenceへ使用した場合にbaseline revisionをscriptで拡張し、freshnessを再計算できる
- WCAG 2.0 / 2.1 / 2.2の各target version / levelからrequired Success Criteria / conformance requirement集合を該当versionのstatic catalogだけで独立導出できる
- 全Success Criterion rowにevaluation metadataがあり、`wcag_criterion_plan.py` がrequired criterion evaluation planを全件materializeできる。criterion選択・省略・required step countをLLMへ任せない
- 3 requirement catalog、finite procedure catalog、versioned semantic contract assetのcanonical hashをformal Skillの `static_data_versions` へ保持し、validator独立再計算と承認済みhash contract testをPASS
- missing / unresolved versionとunsupported / out-of-scope versionを区別し、別versionへ暗黙変換しない
- `runtime_contract.py` でPR #11 Machine Runtime / freshness契約を再利用し、random selectionそのものはdeterministic runtimeへ含めない
- sampling procedure used / skippedの両経路を持ち、skippedでは全in-scope sampleをselected sample setへmaterializeできる
- 再評価ではprevious sampleをcurrent identityへ解決し、retained / replaced / added / unavailable lineageをmaterializeできる。replacement ratioは固定しない
- random sample 10%整数化がscript化され、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- random selectionへfixed seedを要求しない
- canonical sample identity registryをscriptがmaterializeし、duplicate / overlap / union / process membershipを同じidentityで判定する
- selected sampleごとにrequired presentation variation registryをmaterializeし、unknown / unreachable / incomplete variationが残る場合にFull Pagesをsatisfiedにしない
- criterion evaluation planをsample × variation × required Success Criterionで全件materializeし、final Success Criterion resultをcurrent criterion evaluation refからだけ生成する
- finite inventory時のrandom candidate集合、process-added sample、Step 4.3のboolean / actionをscriptが導出し、Agentが手組みしない
- finite inventoryがない場合もLLMがselected sample identityを選ばず、scriptまたは外部random mechanismの結果だけを受ける。target count未達時はscope-wide exhaustionを証明できる場合だけ `exhausted-no-new-view`、証明できなければ `blocked`。selection status / exhaustion evidence / blocked reasonをcanonical Random Sample sectionへ保存する
- candidate population fingerprintをscriptが導出し、Step 4.3でstructured revisionが変わった場合、population同一時のrandom target再計算 / overlap除外 / retained random / 不足分top-up、population変更時のreselection、process再materializeを閉じる
- Conforming Alternate Versionを別sampleに数えずcondition closureをmaterializeし、Non-Interference fixed Success Criteria集合をcatalogから導出できる
- Step 4.2ではcurrent unchanged resultだけを再利用し、変化 / 不明contentとinteractionを再評価できる
- 既存sample resultはPR #11 freshness判定がcurrentの場合だけ再利用する
- sample / process / result / comparison refとmachine-owned structured sectionをscriptがmaterializeし、Agentが値単位で再構築しない
- Step 4.3 loopをartifact上で追跡できる
- Step 5.1 required outcome closureをvalidatorで検証できる
- 各not-satisfied Conformance Requirement / Success Criterionを最低1exampleへ対応付け、all-occurrence追加要件も別closureで検証できる
- human-readable report / Evaluation Statement / accompanying documentationを本Skill所有形式ではaccessible output contractへ閉じられる
- Step 5.2 Evaluation Specificsの安全なarchive / tool / method記録を実装し、secret / unnecessary PIIを複製しない
- Step 5.3 Evaluation Statementはtarget WCAG 2.2だけでfull / partial minimum fieldsをvalidator検証し、2.0 / 2.1ではStep 5.3 sectionを生成しない
- WCAG 2.0 / 2.1 / 2.2 Conformance Claimのrequired / optional fields / version別claim URI / full-scope guardをvalidatorで検証できる
- third-party monitoring / repair経路ではall affected pages identification / monitoring / 2 business days repair guardを検証できる
- WCAG Statement of Partial Conformance - Third Party Content / Languageのrequired fields / canonical wording / guardをvalidatorで検証できる
- Step 5.5 EARL 1.0 JSON-LD sidecarを `_05l` のfixed graph contractでdeterministically生成し、JSON-LD structural validation、再render byte一致、human-readable reportとのassertion coverage一致を検証できる
- WCAG 2.0 / 2.1 4.1.1のHTML / XML `always-satisfied` と非HTML/XMLのsemantic評価、WCAG 2.2でのcriterion不存在をversion別fixtureで検証できる
- Step 5.4 aggregated scoreは目的外として生成しない
- production helperとvalidatorが別実装
- semantic Case A〜AJ（Case C2を含む）PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureでWCAG-EM orchestration E2EをPASSできる
