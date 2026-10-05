# UIテスト対象分析モード: runtime entity / test requirement contracts

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

関連Plan:
- 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- 2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md
- 2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md

この文書は、Acceptance Criteriaをshared runtime contractへ接続し、test-requirement-designまで進むworkflowでfreshness / closureを維持するためのcross-Skill runtime契約の正本です。仕様理解packageだけを要求された場合、Acceptance Criterion Machine Entity生成までは行いますが、test-requirement-designの起動とAC→TR / Disposition closureは完了条件にしません。

## 1. 固定方針

- US / UC / Behaviorはspec-analysis内部のstructured modelであり、global Machine Entity typeへ追加しない
- 下流handoff pointであるcurrent ACだけを `spec-analysis / acceptance_criterion / AC-xxx` Machine Entityへ変換する
- Authority Entityは既存 `authority_entities.py` を正本とする
- AC Entityは `ui_target_package.py build-machine-evidence` が決定論生成する
- Machine Entity wrapper / content fingerprint / expected identity / normalized machine inputをLLMに手組みさせない
- `acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACの追加はshared runtimeとMachine Entity schemaの意味契約変更なので、PR #14確認headに存在する9コピーを `runtime-v1 / entity-state-v1` から `runtime-v2 / entity-state-v2` へ同期する
- envelope field shape自体は変更しない
- test-requirement-designのinput schema変更は `requirement-structure-v2` として明示する
- v1とv2を同時に処理する分岐runtimeは作らない。旧v1 evidenceはcurrent evidenceとして再利用せず、current inputからv2を再実行する

## 2. shared runtime_contract.py

PR #16で更新するのは、PR #14確認headに存在する次の9 Skill-local `runtime_contract.py` です。

- skills/spec-analysis/scripts/runtime_contract.py
- skills/test-analysis/scripts/runtime_contract.py
- skills/test-requirement-design/scripts/runtime_contract.py
- skills/test-condition-design/scripts/runtime_contract.py
- skills/test-case-design/scripts/runtime_contract.py
- skills/coverage-analysis/scripts/runtime_contract.py
- skills/qa-workflow/scripts/runtime_contract.py
- skills/usability-inspection/scripts/runtime_contract.py
- skills/wcag-conformance-evaluation/scripts/runtime_contract.py

確認headでは9コピーが同一blobです。PR #16ではMachine Entity schema versionの意味を分岐させないため、9コピーを同一内容で更新し、repository byte-identity testの対象集合も9 Skillへ広げます。1コピーだけの変更は禁止します。

### 2.1 ALLOWED_ENTITY_TYPES

`acceptance_criterion` を追加します。

US / UC / Behaviorは追加しません。

### 2.2 canonicalization

共通canonicalizationへ次を追加します。

- set-like string refs: `acceptance_refs`
- record array: `acceptance_criteria` を `ac_id` でcanonical sort

duplicateをcanonicalizationで隠しません。schema validatorがduplicateを検出できる既存方針を維持します。

### 2.3 spec-analysis expected Entity

shared `_expected_entities()` の `skill == "spec-analysis"` branchを次へ拡張します。

- `normalized.get("authorities", [])` → `authority`
- `normalized.get("acceptance_criteria", [])` → `acceptance_criterion`

通常の非mode spec-analysisは従来どおり `acceptance_criteria` key省略を許可し、省略時は空集合として扱います。UI target modeの `build-machine-evidence` はcanonical outputとして必ず `acceptance_criteria` keyを出力します。

expected Entityをactual Machine Entity collectionから逆算しません。

spec-analysisはruntime unitを新設しません。expected Entity導出だけをshared runtime contractへ追加します。

### 2.4 runtime-v2 / entity-state-v2へ更新

既存runtime設計では `runtime_contract_version` は意味契約変更時に更新します。現行v1 validatorは `ALLOWED_ENTITY_TYPES` にないtypeをrejectするため、`acceptance_criterion` の追加後に生成されるEntity collectionはentity-state-v1と相互運用できません。さらに `acceptance_refs` / `acceptance_criteria` canonicalizationとspec-analysis expected Entity導出もruntimeの意味契約を変えます。このため `runtime-v2 / entity-state-v2` へのversion upを維持します。単なるimplementation fingerprint変更だけでは表現しません。

9コピーで次を同時更新します。

- `RUNTIME_CONTRACT_VERSION`: `runtime-v1` → `runtime-v2`
- `ENTITY_SCHEMA_VERSION`: `entity-state-v1` → `entity-state-v2`
- `ALLOWED_ENTITY_TYPES`: `acceptance_criterion` を追加

envelope field shapeとfreshness algorithmは維持します。v1 / v2を同時解釈するcompatibility branchは追加しません。旧runtime-v1 / entity-state-v1 evidenceはv2 current evidenceとして読み替えず、current scriptで再実行・再検証します。9コピーのruntime implementation fingerprintも既存契約どおり変わります。

cutover後、旧v1 artifactを通常の `previous_artifact_markdown` としてpartial rerun / freshness検証へ渡しません。TRD / TCD / test-case-designの最初のv2実行は `partial_rerun=false` + `previous_artifact_markdown=null` のfull rebuildとして行います。stable identity / mapping historyは§2.7の各Skill-local `runtime_v1_cutover.py` がv1 Runtime Input / Resultから各v2 generatorへそのまま渡せるcomplete inputへ埋め込みます。Agent / LLMがseed patchを元JSONへmergeしません。v2 artifactが成立した後だけ既存partial rerun契約へ戻します。

`runtime-v2` / `entity-state-v2` はshared contractのversionです。generator contractは別契約なので、意味変更のない `workflow-runtime-v1`、`schema-cases-v1`、`usability-inspection-runtime-v1`、`wcag-em-runtime-v1` 等は維持します。

### 2.5 current version reference synchronization

実装時はrepository current fileを検索し、shared runtime / Machine Entity schemaを表すcurrent referenceをv2へ同期します。対象は少なくとも次です。

- `scripts/skills/evals/deterministic/runtime_validator.py`: `entity-state-v2` と `acceptance_criterion`
- `tests/skills/runtime/*`: metadataの `runtime_contract_version=runtime-v2`、Machine Entity fixtureの `entity-state-v2`
- PR #14の `tests/skills/evals/deterministic/test_inspection_runtime_contract.py` / `test_wcag_runtime_contract.py`
- `skills/test-case-design/scripts/case_structure.py` 等、active codeでMachine Entity schema versionを直接比較する箇所
- current `SKILL.md` / output template / active eval fixture / `EVALS.md` / deterministic `ASSERTIONS.md` でshared runtimeまたはMachine Entity schemaを説明する箇所
- shared `runtime_contract.py` 内のcurrent contract名を表示するdocstring / error message

`docs/history/**` と完了済み旧Planの履歴記述は書き換えません。また、generator contract identifier内の `-v1` はshared runtime versionではないため、意味変更がない限り更新しません。単純なrepository-wide文字列置換は禁止します。

### 2.6 active Machine Evidence templateのcanonical化

v2同期ではversion文字列だけを置換しません。確認headで少なくとも次のactive templateに、current runtime parser / rendererと一致しない手書き擬似schemaがあります。

- `skills/spec-analysis/assets/output-template.md`
- `skills/test-analysis/assets/output-template.md`
- `skills/test-condition-design/assets/output-template.md`

既知の不一致:

- `entity_schema_version` を使用しているが、canonical Entity fieldは `schema_version`
- `dependencies` を使用しているが、canonical Entity fieldは `upstream_entity_dependencies[] / runtime_dependencies[]`
- runtime input例が `runtime_contract_version="runtime-contract-v1"` を使用しているが、shared metadata contractは `runtime-v2`
- runtime result例が `envelope_version="runtime-envelope-v1"` を使用しているが、shared envelope fieldは既存どおり `envelope_version="1"`
- canonical Machine Entityには `model_key` が必要

実装では、これらの手書きJSON例をv2へ文字列置換して残しません。

runtime Skill:

- `runtime_contract.py::render_runtime_input()`
- `runtime_contract.py::render_runtime_result()`
- `runtime_contract.py::render_machine_entities()`

の戻り値をmachine evidence serializationの正本とします。active output templateには、上記helperの戻り値をそのまま配置し、Agent / LLMがJSON fieldを手組みしないことを記載します。helperと重複する固定JSON例は削除します。

spec-analysis:

- 通常Authority Entityは `authority_entities.py` の生成結果を正本とする
- UI target modeは `ui_target_package.py build-machine-evidence` がshared `render_machine_entities()`で生成する `machine_entities_markdown` を正本とする
- output templateへ独自のMachine Entity JSON schemaを再定義しない

repository testでは、current active template / fixtureを検索し、Machine Evidence例としてdeprecatedな `entity_schema_version`、単一 `dependencies`、`runtime-contract-v1`、`runtime-envelope-v1` が残っていないことを確認します。Machine Evidence fixtureを保持する場合はv2 `runtime_validator.py` / Skill-local `runtime_contract.py` でparse / validateできるcanonical shapeだけを許可します。

`schema_cases.py` / `flow_paths.py` 等にある「runtime-v1未対応」のようなgenerator対応範囲の説明はshared runtime versionではありません。shared v2への機械置換を行わず、実装時に意味が曖昧なcurrent文言だけを `schema-cases-v1` / `flow-paths-v1` 等の実際のgenerator contract名へ直します。

### 2.7 v1 → v2 stable identity cutover

one-time migrationはshared `runtime_contract.py` のoperationにしません。現行shared module自身が「technique-specific generatorは各script側」と定義しているため、TRD / TCD / TC固有のschema projectionを9コピーすべてへ持たせません。

新規Skill-local helper:

- `skills/test-requirement-design/scripts/runtime_v1_cutover.py`
- `skills/test-condition-design/scripts/runtime_v1_cutover.py`
- `skills/test-case-design/scripts/runtime_v1_cutover.py`

各helperはPython標準ライブラリ + 同Skillのcurrent `runtime_contract.py` だけをimportします。ただし、**v1 source artifactの読取り・schema検証にはcurrent v2 `validate_machine_entity()` / version constantを使用しません。** 各 `runtime_v1_cutover.py` 内にread-only legacy readerを置き、PR #16実装開始時のpre-cutover baselineから `runtime-v1 / entity-state-v1` のrequired field、pair整合、canonical JSON / fingerprint再計算規則だけを固定します。別のgeneric migration moduleは作りません。current `runtime_contract.py` はlegacy readerで検証済みのsemantic dataをv2 generator inputへcanonicalize / validateする段階だけで再利用します。generator固有projectionは各helper内に置き、qa-workflow用のcutover wrapperは追加しません。

#### 共通CLI contract

stdinは1 JSON object、stdoutは1 JSON object + LFです。operationは `cutover` だけを許可します。

```json
{
  "operation":"cutover",
  "phase":"all",
  "artifact_markdown":"<runtime-v1 / entity-state-v1 artifact>",
  "current_v2_artifact_markdown":null
}
```

- TRD / TC: `phase=all` only
- TCD: `condition-structure / models / test-data-requirements / materialize-coverage`
- TCDの2 phase目以降だけ `current_v2_artifact_markdown` を要求する
- cutover helperの外側stdinはcurrent `runtime_contract.strict_loads()`へそのまま渡さない。各helperのcutover入口がstdlib JSON decoderでduplicate key、depth、container item数等の既存安全制約を維持しつつaggregate 16 MiBを検査する
- top-level `artifact_markdown / current_v2_artifact_markdown` だけは成果物全文transportとして64 KiB string上限を免除する。その他のtop-level scalarと、artifactから抽出したMachine Runtime Input / Result / Entity等のJSON scalarは通常の64 KiB上限を維持する
- legacy readerがartifact内から抽出した各v1 JSON blockは、旧通常runtimeが生成可能だった2 MiB aggregate上限内でstrict decodeする。Machine Runtime Input / Result metadataは `runtime_contract_version=runtime-v1`、Machine Entities wrapper / individual Entityは `schema_version=entity-state-v1` を要求し、Input / Result pair、Entity identity / dependency / stored fingerprintをfrozen v1規則で再検証する
- current v2 `strict_loads()` の `verify_runtime_evidence` 専用64 KiB exemptionをcutoverへ流用しない。cutover契約自体はgenerator input上限 / string上限を変更しない。ready-scope batchを受ける `artifact:analysis_entities:all` / `artifact:requirement_structure:all` のaggregate 16 MiB化は本節のcutoverとは独立した§3のroot runtime契約として扱う
- handled failureはexit 0 + `valid=false / issues[]`、unexpected internal errorだけexit 1
- `cutover_semantic_drift / cutover_dependency_incomplete` はblocking issueとする

response:

```json
{
  "valid":true,
  "phase":"all",
  "phase_complete":true,
  "source_runtime_contract_version":"runtime-v1",
  "source_entity_schema_version":"entity-state-v1",
  "normalized_runtime_inputs":[
    {"generator":"requirement_structure","runtime_unit_key":"artifact:requirement_structure:all","model_key":null,"normalized_input":{}}
  ],
  "issues":[]
}
```

#### 共通projection規則

- source artifactはruntime-v1 / entity-state-v1だけを受理する
- v1 Machine Entity fingerprint / freshness / generation fingerprintをv2 current evidenceとしてcarry-forwardしない
- v1 Machine Runtime Inputに保存済みのscript固有semantic inputを正本とし、Markdown本文をLLMが読み直してJSONを再構築しない
- v1 Runtime Resultに保存済みのidentity / mapping stateをv2 generator inputのprevious state / reuse fieldへ決定論projectionする
- 返却inputはそのままgeneratorへ渡せるcomplete shapeとし、caller / Agentへfield mergeを要求しない
- runtime metadata / dependency fingerprintは返却せず、current v2 dispatchが既存builderで新規生成する
- stable semantic identity / target_ref / semantic fieldがcutover中に変わる場合は自動補正せず `cutover_semantic_drift`
- cutoverとsemantic redesignを同じrunで混在させない

#### test-requirement-design/runtime_v1_cutover.py

expected unitは `artifact:requirement_structure:all` exactly 1件です。

- v1 `authorities / risks / test_requirements / dispositions` をsemantic変更せず維持
- 各既存TR draftへ `acceptance_refs=[]` を追加する。top-level `acceptance_criteria[]` はv2 invocationのcurrent semantic AC集合として必須とし、cutover helperは既存v1 artifactからACを推測生成しない。UI target modeの通常経路では `build-machine-evidence.normalized_skill_input.acceptance_criteria[]` を使用し、ACなしworkflowでは明示 `[]` とする
- v1 result `tr_id_state` → `previous_tr_ids[]`
- `draft_key ↔ tr_id_map[]` をexact joinし、current draftを `identity_action=reuse / reuse_id=<TR-ID>` に固定
- active TRを `update_scope_tr_ids[]` へ全件入れ、`inactive_tr_ids=[]` を明示してfirst v2 runをfull rebuildにする
- missing / extra / duplicate mappingをblockedにする

#### test-condition-design/runtime_v1_cutover.py

TCDはcurrent v2 model resultを後段へ使うため4 phaseで進めます。

`condition-structure`:
- v1 condition_structure input/resultをexactly 1 pair要求
- `tcn_id_state / model_key_state` をprevious stateへ移す
- TCN / model `draft_key ↔ *_id_map` をexact joinしてreuseへ固定
- active TCN / modelをfull rebuild scopeへ入れ、`inactive_tcn_ids=[] / inactive_model_keys=[]` を明示する

`models`:
- current v2 condition_structure pairを必須とする
- root modelはv1 saved inputをcanonical copy
- derived childはcurrent v2 parent resultの `derived_child_inputs[]` から生成し、v1 saved child inputとのsemantic driftを検出
- dependency順で今すぐ実行可能な未実行unitだけを返す
- 未実行modelが残るのにready unitが0件なら `cutover_dependency_incomplete`

`test-data-requirements`:
- v1 TDR unitがなければempty completion
- 存在時はsemantic fieldを維持し、target version fieldだけcurrent v2 model resultへrebase
- target_ref / source_model_key / execution identityのsemantic driftをblockedにする

`materialize-coverage`:
- current v2 condition / model / optional TDR resultからcomplete inputを再構築
- previous target / semantic CI / CI ID / expected-result-root stateをv1 resultからprevious stateへ維持し、`inactive_ci_ids=[]` を明示する
- target annotation / disposition / merge groupのsemantic fieldを維持し、version fingerprintだけcurrent targetへrebase
- semantic coverage itemはv1 source_target_versionsで旧semantic_content_fingerprintを再計算してv1 mappingへ一意joinした後、current target versionへrebaseして同じCI IDをreuseする
- 0件 / 複数mapping、target集合 / merge membershipのsemantic driftをblockedにする

#### test-case-design/runtime_v1_cutover.py

expected unitは `artifact:case_structure:all` exactly 1件です。

- v1 inputのsemantic fieldを維持
- v1 result `tc_id_state` → `previous_tc_ids[]`
- `draft_key ↔ tc_id_map[]` をexact joinし、current TC draftをreuseへ固定
- active TCを `update_scope_tc_ids[]` へ全件入れ、`inactive_tc_ids=[]` を明示してfull rebuild
- missing / extra / duplicate mappingをblockedにする

### 2.8 v1保存evidenceのread-only検証 / projection

TRD / TCD / TCの`runtime_v1_cutover.py`はstable identity / historyをv2 inputへprojectionするためのcutover helperです。spec-analysisはruntime unitを持たないため別fileを追加せず、既存 `authority_entities.py` にcanonical v1 Authority Entityからcurrent v2 Authority Entityへ再生成するread-only migration pathを追加します。さらに、runtime version変更だけを理由にsemantic再分析やlive再観測を強制しないため、保存済みv1 Runtime Inputを再利用する次の3 Skillだけにread-only readerを追加します。

- `skills/test-analysis/scripts/runtime_v1_input_reader.py`
- `skills/usability-inspection/scripts/runtime_v1_input_reader.py`
- `skills/wcag-conformance-evaluation/scripts/runtime_v1_input_reader.py`

generic migration module、shared `runtime_contract.py` のv1 compatibility branch、qa-workflow wrapperは追加しません。spec-analysis projectionと3 readerはいずれもv1 evidenceの**integrity検証とsemantic data抽出だけ**を担当し、v1 fingerprint / dependency / wrapperをcurrent v2へcarry-forwardしません。

#### spec-analysis Authority v1 projection

`skills/spec-analysis/scripts/authority_entities.py` の既存request `{"authorities":[...]}` とresponse shapeは維持します。migration時だけ、これと排他的なrequestを受けます。

```json
{"source_artifact_markdown":"<canonical v1 spec-analysis artifact>"}
```

この経路はexactly one `### Machine Entities: spec-analysis` blockを抽出し、current v2 `validate_machine_entity()` へ渡さず次をfrozen v1規則で検証します。

- wrapperはexact `{schema_version, skill, entities}`、`schema_version=entity-state-v1`、`skill=spec-analysis`
- individual Entityはv1 canonical exact field setを持ち、`schema_version=entity-state-v1`、`skill=spec-analysis`、`entity_type=authority`、`model_key=null`
- `content_fingerprint` をv1 canonical JSON規則で再計算して一致する
- `upstream_entity_dependencies=[]` / `runtime_dependencies=[]`
- `content` は `authority_entities.py build()` のexact Authority schema `{authority_id, authority_type, active_content, scope, source_refs, relations, related_authority_refs}` を満たし、`content.authority_id == entity_ref`
- duplicate Authority identityをrejectする

検証成功後はAuthority Entityの`content`だけを`authority_id`順に取り出し、current v2 `build(authorities)` へ渡して新しい `schema_version=entity-state-v2` / content fingerprint / wrapperを生成します。v1 wrapper / Entity fingerprint / dependencyをseedにしません。canonical v1 blockがmissing / invalidならhuman-readable `現在有効な仕様根拠` tableやproseからJSONを推測復元せず、通常spec-analysis semantic rerunへ戻します。

#### reader CLI contract

stdinは1 JSON object、stdoutは1 JSON object + LFです。

```json
{
  "operation":"extract-validated-inputs",
  "artifact_markdown":"<runtime-v1 artifact>"
}
```

外側transport / JSON safetyは§2.7のcutover helperと同じくaggregate 16 MiB、top-level `artifact_markdown`だけ64 KiB string上限免除とします。artifactから抽出した各Machine Runtime Input / Result JSON blockは旧v1の2 MiB / 64 KiB / depth等の安全制約で検証します。

成功response:

```json
{
  "valid":true,
  "source_runtime_contract_version":"runtime-v1",
  "normalized_runtime_inputs":[
    {
      "generator":"...",
      "runtime_unit_key":"artifact:...",
      "model_key":null,
      "normalized_input":{}
    }
  ],
  "issues":[]
}
```

handled failureはexit 0 + `valid=false / issues[]`、unexpected internal errorだけexit 1とします。

#### frozen v1 integrity規則

PR #14 merge後に#16をlatest mainへrebaseしたStep 0で、pre-cutover baselineの対象Skill `runtime_contract.py` と対象generatorのimplementation fingerprintを実測してreaderの固定期待値 / fixtureへ同期します。これは値の再計測であり、新しい設計判断にはしません。

readerは少なくとも次をfrozen v1規則で検証します。

- Machine Runtime Input / Resultのidentity、missing / extra / duplicate / incomplete pair
- `envelope_version`、`runtime_contract_version=runtime-v1`、generator contract、runtime unit / model identity
- input / model / generation fingerprintの再計算一致
- upstream Entity / runtime dependency schema、duplicate、保存fingerprint
- pre-cutover baselineのruntime / generator implementation fingerprint
- runtime resultの固定schemaとInput metadataとのpair整合
- source artifact中のv1 Machine Entityをv2 current Entityとして受理しない

reader成功は「保存v1 evidenceが当時のbaseline contractに対して改変されていない」ことだけを表します。**currentness=trueを意味しません。** v1 runtime metadata、generation fingerprint、dependency、Machine Entityはresponseへcarry-forwardせず、current v2 dispatchが新規生成します。

#### test-analysis

`test-analysis/runtime_v1_input_reader.py` はcurrent canonical test-analysis artifact内のv1 pairを検証し、LLM所有のsemantic fieldと各runtime unitの保存inputを返します。少なくともroot `artifact:analysis_entities:all` では次をsemantic fieldとして保持します。

- `test_analysis_context`
- `product_risks`
- `technique_selections`
- `change_nodes`
- `change_edges`
- `environment_requirements`

v1 root inputの `risk_matrix_results / technique_candidate_results / current_runtime_units` はv2へcarry-forwardしません。current v2 dispatchは保存済みchild inputを使って必要なdependent runtimeをfull rerunし、そのcurrent v2 resultからroot inputのmachine-owned fieldを再構築して `analysis_entities` をfull rerunします。

保存semantic inputを再利用できるのは、v1 metadataに保存されたupstream Entity identity / content fingerprintがcurrent v2 upstream Entityと一致し、その他のcurrent source / reference契約も成立する場合だけです。不一致・missing・reader invalidなら保存inputを使わず通常test-analysis rerunへ戻します。v1 fingerprintをRISK等のstable identity seedには使いません。

#### usability-inspection / wcag-conformance-evaluation

両readerはvalidated v1 pairからexact `Machine Runtime Input.input` だけを返します。reader自身はbrowser observation、sample、procedure、handoff、evidenceのcurrentnessを判定しません。

- `usability-inspection`: 既存artifact graph / browser handoff / evidence / document identity等のcurrentness契約が現在も成立する場合だけ保存inputをcurrent v2 `inspection_runtime.py` へ再投入する。成立を確認できない場合は既存Skill契約の通常rerunまたは必要なlive再観測へ戻る
- `wcag-conformance-evaluation`: 既存sampling / procedure / handoff / evidence freshness契約が現在も成立する場合だけ保存inputをcurrent v2 `wcag_runtime.py` へ再投入する。成立を確認できない場合は既存WCAG-EM workflowで通常再実行し、必要なbrowser workは既存handoff契約で再観測する

runtime version bumpだけを理由にlive再観測は要求しませんが、旧v1 pairのintegrityだけを根拠にcurrent扱いもしません。

#### coverage-analysis / qa-workflow

この2 Skillにはv1 input readerを追加しません。

- `coverage-analysis`: 保存v1 Machine Runtime Inputを再利用せず、current upstream v2 Entity / runtime evidenceから通常Skill契約どおり`traceability` / verifierをfull rerunする
- `qa-workflow`: 保存v1 Machine Runtime Inputを再利用せず、各scopeのcurrent v2 evidenceとcurrent workflow state / routing inputから`workflow_runtime.py` / final gateを再生成する

両Skillは自Skillstable identityをv1 resultから維持する必要がなく、既存のcurrent sourceから決定論再生成できるため、legacy readerを追加しません。

#### 9 Skillのruntime-v1 evidence処置

`runtime-v2 / entity-state-v2` へ上げる9 Skillについて、v1 artifactの扱いを次へ固定します。v1 envelope / Entity fingerprintをcurrent扱いせず、必要なstable identityだけを各Skillの正本から維持します。stable identity / historyをprojectionするcutover helperはTRD / TCD / TCだけに置き、保存v1 semantic inputを再利用するtest-analysis / usability-inspection / wcag-conformance-evaluationだけに§2.8のread-only input readerを置きます。

| Skill | v1 artifactの扱い | v2移行方法 | stable identity | 再実行 / 再観測 |
| --- | --- | --- | --- | --- |
| spec-analysis | v1 Machine Entity / wrapperはcurrent扱いしない | `authority_entities.py` の§2.8 frozen projectionでcanonical v1 Authority Entityの`content`だけを検証抽出し、current v2 `build()`でAuthority Entityを再生成する。v1 blockがmissing / invalidならtable/prose parserへfallbackせず通常spec-analysis semantic rerun | SPEC / DEC / ASM等のsemantic IDは検証済みAuthority `content.authority_id`を維持し、v1 fingerprintをseedにしない | valid canonical v1 Authority blockならdeterministic再生成。無ければ通常Skill rerun |
| test-analysis | v1 Runtime / Entity evidenceはcurrent扱いしない | `runtime_v1_input_reader.py` でv1 pair integrityを検証し、semantic field + saved child runtime inputだけを抽出する。current v2 upstream Entity identity / content fingerprint等のcurrent source契約が一致する場合だけdependent runtime→`analysis_entities`をfull rerunする。v1 rootのmachine-owned result fieldは再利用しない。reader invalid / currentness不一致は通常test-analysis rerun | RISK等のsemantic IDは検証済みsemantic input / current artifact上のIDを維持し、v1 fingerprintをseedにしない | reader valid + current source一致ならdeterministic full rerun。その他は通常Skill rerun |
| test-requirement-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` でcomplete v2 inputを作りfull rebuild | TR IDとv1のactive / deleted履歴を維持し、inactiveは空集合から開始 | cutover必須 |
| test-condition-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` の4 phaseでcomplete v2 inputを作りfull rebuild | TCN / model / CI IDとv1のactive / deleted履歴を維持し、inactiveは空集合から開始 | cutover必須 |
| test-case-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` でcomplete v2 inputを作りfull rebuild | TC IDとv1のactive / deleted履歴を維持し、inactiveは空集合から開始 | cutover必須 |
| coverage-analysis | v1 aggregate evidenceをcarry-forwardしない | 保存v1 Machine Runtime Inputは再利用せず、current upstream v2 Entity / runtime evidenceから通常Skill契約どおり`traceability` / verifierをfull rerunする | 自Skill Entityをcarry-forwardしない既存契約を維持 | current v2 upstreamからdeterministic full rerun |
| qa-workflow | v1 aggregate evidenceをcarry-forwardしない | 保存v1 Machine Runtime Inputは再利用せず、各scope担当Skillのcurrent v2 evidence + current workflow state / routing inputから`workflow_runtime.py` / final gateを再生成する | 自Skill Entityをcarry-forwardしない既存契約を維持 | current workflow stateからorchestration evidenceを再生成 |
| usability-inspection | v1 runtime envelopeをcurrent扱いしない | `runtime_v1_input_reader.py` でv1 pair integrityを検証し、既存artifact graph / browser handoff / evidence currentnessが現在も成立する場合だけexact inputからv2 evidenceを再生成する。reader invalid / currentness不明・不一致はMarkdownから復元せず通常再実行または必要なlive再観測 | runtime version bumpだけで新しいproduct identityを作らない | integrity + currentness成立時だけversion bumpによるlive再観測を省略する |
| wcag-conformance-evaluation | v1 runtime envelopeをcurrent扱いしない | `runtime_v1_input_reader.py` でv1 pair integrityを検証し、既存sampling / procedure / handoff / evidence freshnessが現在も成立する場合だけexact inputからv2 evidenceを再生成する。reader invalid / currentness不明・不一致はreport proseから復元せず既存WCAG-EM workflowで通常再実行する | evaluation / sample等のsemantic identityは既存Skill契約を維持 | integrity + currentness成立時だけversion bumpによる再観測を省略する |

この表にないmigration wrapper / generic converterは追加しません。spec-analysisは§2.8でfrozen検証したcanonical v1 Authority content、test-analysis / usability-inspection / wcag-conformance-evaluationはread-only readerでintegrity検証済みかつcurrentness条件を満たすsemantic input、coverage-analysisはcurrent upstream v2 evidence、qa-workflowは全必要current v2 evidenceが揃ったcurrent workflow state / routing inputを正本とし、proseからv2 inputを推測変換しません。PR #14 merge後のStep 0ではspec-analysis v1 Entityのexact baseline field / canonicalizationと、3 readerが固定するpre-cutover runtime / generator implementation fingerprint、保存input blockの存在・parse可能性を実測値へ同期します。存在しない / baseline不一致の場合は上表の通常rerun経路へ固定し、新しい設計判断はStep 0へ持ち越しません。

#### UI target migrationとの相対順序

既存runtime-v1 downstream artifactがあるworkflowでは次の依存順だけを許可します。

1. runtime-v1 downstreamを検出し、通常semantic update / partial rerunを停止する
2. spec-analysisは§2.8のfrozen Authority projectionでv2 Authority Entityを再生成し、projection不可なら通常spec-analysis semantic rerunでcurrent v2 baselineを作る
3. test-analysisは§2.8 readerでintegrityとcurrent v2 Authority整合を確認してdependent runtime → `analysis_entities` をfull rerunし、reader不可なら通常test-analysis rerunへ戻る
4. TRD → TCD → TCをSkill-local cutover helperでsemantic不変のままv2 full rebuildする
5. coverage-analysisをcurrent v2 TR / TCN / CI / TC / runtime evidenceからfull rerunする
6. workflowで必要なusability-inspection / wcag-conformance-evaluationを各Skillのreader integrity + currentness契約に従ってv2再生成し、必要なら通常rerun / re-observationする
7. qa-workflowを最後にcurrent v2 Entity / runtime evidence + current workflow state / routing inputからfull rerunし、v2 baselineのvalidate / freshness / final gateを成立させる
8. v2 baseline成立後にlegacy / normal spec-analysis成果物をui-target-v1へmigrationしてUS / UC / Behavior / ACを生成する
9. 既存active downstreamが `scope_refs=[]` の場合は、全current scope readyを要求してrequirement-structure-v2 → TCD → TCをscope ownership normalizationとして再実行し、coverage-analysis → qa-workflowまでcurrentにする。blocked scopeが残る場合は `scope_ownership_baseline_required` で停止する
10. scope ownership baseline成立後、AC / Authority変更でstaleになったdownstreamを通常の依存順で再実行し、以後のready / blocked partial progressionを許可する

`UI target migration済み + runtime-v1 downstreamあり + v2 baseline未成立` はblockedです。逆順を許可しません。runtime-v1 downstream artifactが存在しないworkflowだけ、UI target package migrationから直接normal v2 workflowへ進めます。

#### repository regression

- `authority_entities.py` v1 Authority projection、3 `runtime_v1_cutover.py`、3 `runtime_v1_input_reader.py` のpackage単体compile / portability
- cutover外側transportは16 MiB accepted / 1 byte超過blocked。cutover処理によってgenerator上限を変えないことを確認し、別途§3の2 root runtimeだけaggregate 16 MiB、その他の通常generatorは2 MiBを維持する
- spec-analysis projectionはcanonical v1 `Machine Entities: spec-analysis` wrapper / Authority Entityだけを受理し、`schema_version`不一致、content fingerprint改変、dependency混入、`authority_id != entity_ref`、duplicateをrejectする。cutover helperはv1以外のsource runtime / entity schema、v1/v2混在、missing / extra / duplicate / incomplete pairをlegacy readerでrejectする。input readerもv1以外、missing / extra / duplicate / incomplete pair、baseline implementation fingerprint不一致をrejectし、current v2 validatorへv1 sourceを渡す経路を持たない
- top-level artifact stringが64 KiBを超えてもaggregate 16 MiB以内ならcutover入口で受理し、artifact内JSON scalarが64 KiBを超える場合はrejectする回帰
- frozen v1 input / model / generation fingerprint、dependency、runtime / generator implementation fingerprintを改変したsource artifactをcutover helper / input readerがrejectする回帰
- 内容不変cutoverでTR / TCN / model / CI / TC IDとv1のactive / deleted identity historyを維持し、v1に存在しない `inactive_*` は空配列から開始する
- cutover helper返却inputだけで次のv2 generatorを実行でき、Agent-side merge不要。input readerはsemantic inputだけを返し、v2 metadata / dependencyを生成しない
- test-analysis reader成功後にdependent runtimeをv2 full rerunし、rootのmachine-owned result fieldをcurrent v2 resultから再構築する回帰
- usability-inspection / wcag-conformance-evaluationはreader validだけでは再利用せず、currentness成立時のみsaved inputでv2再生成し、不成立時は通常rerun / re-observationへ戻る回帰
- coverage-analysis / qa-workflowはvalidな保存v1 inputが存在しても無視し、current upstream v2 evidence / current workflow stateから再生成する回帰
- TCD target version rebase、derived child、semantic CI mappingをcurrent v2 resultへ正しく接続
- `UI target migration済み + runtime-v1 downstream + v2 baseline未成立` をintegration testでblocked
- spec-analysis/test-analysis v2再生成 → TRD/TCD/TC cutover → coverage-analysis → 必要なinspection/WCAG → qa-workflow final gateの順でv2 baselineが成立し、その後UI target migration → 既存downstreamがある場合は全scope readyでscope ownership normalization → coverage-analysis / qa-workflow再生成 → partial readiness / downstream rerunへ進むことをintegration test / 実Agent smokeで確認。ownership baseline前にblocked scopeがある場合は `scope_ownership_baseline_required`、downstream未作成ならone-time gate不要

## 3. spec-analysis normalized machine input

`ui_target_package.py build-machine-evidence(scope_ids=null)` はpackage-global evidenceと `ready_scope_ids[] / blocked_scope_ids[]` を決定論生成し、scope別full handoffを同じresponseへ複製しません。`build-machine-evidence(scope_ids=[...])` は各ready scopeを固定reachabilityで内部projectionし、Authority / current AC / Machine Entity / expected identityをstable identityでunion / dedupeした1つのbatch handoffに加え、ready scopeごとの `scope_id / target / ui_operation / authority_refs[]` を持つcompact `scope_index[]` を返します。canonical qa-workflowでは `ready_scope_ids[]` が1件以上の時だけ `scope_ids[]` を渡しcurrent ready集合とexact一致させます。`ready_scope_ids=[]` では空配列batchを生成しません。blocked scopeのID集合は `inspect.blocked_scope_ids[]` を正本とし、package-global Machine EntityやAuthority dependencyからscope ownershipを逆算しません。Markdownから次を決定論的に生成します。

- normalized Authority rows
- normalized current AC rows
- canonical `normalized_skill_input`
- Authority Machine Entities
- Acceptance Criterion Machine Entities
- canonical `machine_entities[]`
- canonical `expected_entity_identities[]`

`normalized_skill_input` の正本shape:

```json
{
  "authorities": [{"authority_id":"SPEC-001"}],
  "acceptance_criteria": [
    {"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
  ]
}
```

`authority_refs[]` は `_06 §9.2` の固定projectionで得たAC / Behavior / UC / US chain、linked UIOP、scope、linked domain item、linked UI structureのstable refsを09のCurrent Effective Authority集合へ解決したunionです。current SPEC / DECISION / approved ASMだけを残し、INF / UNK / inactive Authorityは除外します。helperが重複除去・canonical sortし、current ACでは1件以上を要求します。0件ならhelperはblocking issueを返してAC Entityを生成しません。AC semantic identityが同じなら同IDをblockedへ遷移させる、Behavior自体も未確定なら親Behaviorをblockedへ遷移させる、意味上廃止ならexplicit retireする、UNKNOWNをreuse / newする等のsemantic transitionはLLMが判断します。Agent / LLMがAuthority集合を再構築しません。

qa-workflow / test-analysis / coverage-analysisへspec-analysis成果物を渡す場合、AgentがMarkdownからJSONを再構築しません。current `inspect.ready_scope_ids[]` が1件以上なら全件を `build-machine-evidence(scope_ids=ready_scope_ids)` へ渡し、helperが1つのcanonical batch handoffと `scope_index[]` を生成します。`ready_scope_ids=[]` ではbatch handoffを生成せず後続runtimeをdispatchしません。test-analysis / TRDはscope所属の意味判断にこの `scope_index[]` を使いますが、下流Machine Entityのscope ownershipをAuthority共有や名称から推測しません。既存runtime unit `artifact:analysis_entities:all` / `artifact:requirement_structure:all` は維持し、scopeごとの別runtime unitへ分割しません。

### ready-scope batch root runtime入力上限

`artifact:analysis_entities:all` / `artifact:requirement_structure:all` はready scope全件を1 requestへ集約するroot runtime unitなので、本PRで各entrypointを `run_cli(..., aggregate=True)` へ変更します。最終canonical stdinは2 MiBを超えても16 MiB以下なら処理し、16 MiB + 1 byteは `limit_exceeded` でfail-closedします。この上限はruntime unitのtransport契約としてdirect / artifactの両input modeに共通適用し、mode別のwrapperや例外経路は追加しません。その他の通常generatorは既存2 MiB上限を維持します。

qa-workflowはbatch handoffからroot runtimeの最終canonical stdinを構成した後に同じ16 MiB境界を事前検査します。超過時はruntimeを起動せずblockedにし、scope別個別run / subset run / Agent merge / silent truncate / auto splitで回避しません。`MAX_AGGREGATE_INPUT_BYTES`、depth、1文字列64 KiB、stdout等の既存安全制約を再利用し、新しい分割・merge契約は追加しません。

### 3.1 requirement-structure-v2 caller contract

`acceptance_refs[]` とTRのscope所属の意味判断をLLMに残し、known AC集合・known ready Scope集合・Machine Entity dependencyの扱いはinput modeごとに固定します。empty default用adapterは追加しません。

`requirement-structure-v2` raw generator inputはtop-level `acceptance_criteria[] / scope_ids[]` を必須とします。

```json
{
  "acceptance_criteria": [
    {"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
  ],
  "scope_ids":["SCOPE-001","SCOPE-002"]
}
```

- `ac_id` はduplicate不可、canonical sortする
- `authority_refs[]` はduplicate不可で1件以上、top-level `authorities[]` のknown Authority IDだけを許可する
- `scope_ids[]` はduplicate不可・canonical sort済みのknown current Scope ID集合。UI target artifact workflowではcurrent `ready_scope_ids[]` とexact一致させる
- ACなしworkflowは `acceptance_criteria=[]` を明示する
- non-UI-target / migration baselineでは `scope_ids=[]` を許可する
- 各 `test_requirements[]` draftの `acceptance_refs[] / scope_refs[]` を必須とする。`acceptance_refs[]` はknown `acceptance_criteria[].ac_id`、`scope_refs[]` はknown `scope_ids[]` への存在参照だけをscriptが検証する
- UI target artifact workflowではcurrent TRの `scope_refs[]` を1件以上必須とする。LLMはbatch `scope_index[]` とTRの意味から所属scopeを決め、blocked Scope IDをcurrent TRへ割り当てない
- non-UI-target / migration baselineでは `scope_ids=[] / scope_refs=[]` を許可し、scope ownershipを推測生成しない

artifact mode:

- `metadata.upstream_entities` にcurrent `spec-analysis / acceptance_criterion` Entityを要求する
- semantic `acceptance_criteria[]` の `ac_id / authority_refs[]` 集合がupstream AC Entity contentとexact一致することを検証する。Entityに無いAC、semantic inputに無いcurrent ACを許可しない
- 参照AC EntityをTR dependencyへ追加し、参照ACのcurrent Authority Entity dependencyもfreshness用にTRへ直接追加する
- AC Entity / Authority Entityを全件解決できない場合はfail-closedする

direct mode:

- `acceptance_criteria[]` 自体をknown current AC集合の正本とし、`acceptance_refs[]` をその集合へ存在検証する
- upstream AC Entityは必須にしない。存在しないMachine Entityを合成しない
- `metadata.upstream_entities` に参照AC Entityが実在する場合だけ、そのAC Entity dependencyをTRへ追加できる。利用する実在AC Entityの `ac_id / authority_refs[]` はtop-level semantic `acceptance_criteria[]` の同一AC rowとexact一致を要求する。missing AC Entityはdirect modeではerrorにしない
- semantic `acceptance_criteria[].authority_refs[]` からAC由来Authority dependencyを合成しない。direct modeのAuthority dependencyは従来どおりTR自身の `authority_refs[]` で実在Entityを解決した範囲だけとする
- ACの `ac_id / authority_refs[]` はknown-ID検証とclosureのsemantic inputであり、TR Entity contentへは各TRの `acceptance_refs[] / scope_refs[]` を保存する

旧runtime-v1 / requirement-structure-v1からの初回cutoverは§2.7のtest-requirement-design `runtime_v1_cutover.py` がTRのstable identity / historyとsemantic draftをv2へ変換します。AC集合はv1 artifactから推測せず、v2 invocationのcallerが上記contractに従って渡します。v1にはUI target Scope IDが無いためcutover出力は `scope_ids=[]`、各TR `scope_refs=[]` とし、UI target migration後の最初のTRD semantic updateでcurrent active TR全件へscope ownershipを付与します。

空array補完だけのadapter、shared runtime hook、project固有legacy wrapperは追加しません。導入先projectが独自保存形式を持つ場合の外部変換はproject / harness側の責務です。runtime `input_fingerprint` はraw generator inputとshared runtime metadataから既存契約どおり計算します。

## 4. Acceptance Criterion Machine Entity

identity:

- skill: `spec-analysis`
- entity_type: `acceptance_criterion`
- entity_ref: `AC-xxx`

current ACだけをEntity化します。blocked ACを完成済みcurrent Entityへ変換しません。

Machine Entity identityには`package_ref`を追加しません。1つのcurrent Entity collectionへ投入するspec-analysis Authority / AC Entityは、1つのcurrent canonical UI target package / normalized inputから生成された集合に限定します。複数packageの `SPEC-xxx / AC-xxx` 等をそのまま連結してidentity衝突を解決することはしません。必要な場合はspec-analysisでpackageを意味統合してからMachine Entity化します。

### 4.1 canonical content

AC Entity contentには次を固定projectionします。

- `ac_id`
- `acceptance_criteria`
- `linked_ui_operations[]`: parent Behaviorの`関連操作ID`に明示されたUIOPを解決し、**状態=`mapped`**、同じScope、`対応UC ID`に親UCを含むことを検証したうえで、`uiop_id`昇順に `uiop_id / actor_role / target_structure_id / operation / authority_refs[]` として固定projectionする。同じUCに属するだけで`関連操作ID`にないUIOPは含めない
- `behavior_id`
- `behavior_result_classification`
- `behavior_text`
- `behavior_postcondition`
- `uc_id`
- `use_case`
- `trigger`
- `preconditions`
- `success_postcondition`
- `user_stories[]`: `us_id / actor_role / goal`。`us_id`昇順で固定
- `scope`: `scope_id / target / authority_refs[]`。`target` は00の `対象機能 / 領域` をtrimしたcanonical文字列
- `linked_domain_items[]`: AC / Behavior / UC / USの `関連構造ID` に明示されたdomain item ID（FIELD / RULE / FLOW / NOTIFY / INTERACT）だけを固定projectionする。linked UIOPの `対象構造ID`、同一PAGE、同一Scope、名称一致、Authority一致からdomain itemを逆引きしない。item typeごとにsource tableのsemantic field、scope refs、Authority refs、structure refsをcanonical化し、別domain itemへ再帰展開しない
- `linked_structures[]`: AC / Behavior / UC / USの `関連構造ID` に明示されたUI構造ID、linked UIOPの `対象構造ID`、linked domain itemの `対象構造ID / 関連構造ID` に明示されたUI構造IDをseedとし、各rowの `parent_structure_id` をrootまで辿ったancestor closureを `structure_id` のcanonical順で固定projectionする。各entryは `structure_id / type / name / state_axis / path_identifier / parent_structure_id / authority_refs[]` を持つ。missing parent / self-parent / cycleはrejectする
- `linked_inferences[]`: AC chain、linked UIOP、scope、linked structures、linked domain itemsが `関連仕様項目ID` で直接参照するcurrent INF rowを、09 `分析項目` のcanonical row内容で固定projectionする。INFはcontent fingerprintへ寄与するがupstream Entity dependencyにはしない
- `authority_refs[]`: AC / Behavior / UC / US chain、linked UIOP、scope、linked structures、linked domain itemsのstable refsをCurrent Effective Authorityへ解決し、current SPEC / DECISION / approved ASMだけを残した1件以上のunionを重複除去してcanonical sortする

これによりAC本文が同じでも、linked UIOPの操作対象 / 操作内容 / Authority、scopeの対象意味、**明示参照された**FIELD / RULE / FLOW / NOTIFY / INTERACT、そこから明示されたUI構造とancestor、linked INF、親US / UC / Behaviorの意味変更でAC content fingerprintが変わります。AC chainから明示参照されない同一PAGE / 同一Scopeのdomain itemはprojectionへ入れないため、無関係row変更でstale化しません。repository確認だけで成立したimplementation-only structureもtarget-model dependencyとしてfingerprintへ寄与しますが、Authorityへ昇格しません。

### 4.2 dependencies

AC Entityの `upstream_entity_dependencies[]` は、AC / Behavior / UC / US chain、linked UIOP、scope、linked structures、linked domain itemsのstable refsからfilterしたcurrent SPEC / DECISION / approved ASM Authority Entity unionへ固定します。INF / UNKをdependencyへ追加しません。linked INFはAC contentだけへ含めます。

UIOP / US / UC / Behavior / UI構造 / FIELD / RULE / FLOW / NOTIFY / INTERACT / INFを新しいdependency Entity typeとして追加しません。package-local rowはAC contentへ固定projectionし、Authorityだけ既存Entity dependencyへ展開することで、不要なglobal entity typeを増やさずfreshnessを成立させます。


## 5. downstream generator contract version

本PRではAcceptance Criteria接続に加え、readyだったscopeが一時blockedになった時のstable ID lifecycleをTRD → TCD → TCまで閉じるため、次のgenerator contractを同時に更新します。

- `requirement-structure-v1 → requirement-structure-v2`
- `condition-structure-v1 → condition-structure-v2`
- `materialize-coverage-v1 → materialize-coverage-v2`
- `case-structure-v1 → case-structure-v2`

shared runtime contractは `runtime-v2` を使用します。

`requirement-structure-v2` はAC schema、TR scope ownership、inactive lifecycle、残り3 generator v2はdownstream `scope_refs[]` 伝播とinactive lifecycleが意味契約変更です。repository内の固定contract mapping / fixture metadata / portability test / runtime test / vertical integrationで各 `-v1` contractを参照している箇所をcurrent v2へ同期します。generator contract versionとshared `runtime-v2` を同一文字列へ揃えません。

旧v1 Machine Runtime Resultをv2 current resultとして読み替えません。v1 cutover時点では既存 `active / deleted` historyをそのままv2へprojectionし、v1に存在しない `inactive` を推測生成しません。inactiveはv2通常workflowで実際に `ready → blocked` が発生した時だけ作成します。

## 6. requirement_structure-v2 input

top-level required fields:

- `authorities`
- `risks`
- `acceptance_criteria`
- `scope_ids`
- `test_requirements`
- `dispositions`
- `previous_tr_ids`
- `update_scope_tr_ids`
- `inactive_tr_ids`
- `inactive_tr_history`

既存legacy promotion用 `legacy_tr_ids` の条件付き入力契約は維持します。

`previous_tr_ids[]` はexact `{tr_id,status,scope_refs}` とし、`status` は `active / inactive / deleted` の3値です。`scope_refs[]` は最後にactiveだった時点のcanonical ownershipをinactive / deletedでも保持します。v1 cutover / non-UI-target baselineは `scope_refs=[]`、UI targetのscope ownership baseline成立後はactive / inactive TRで1件以上を要求します。

`inactive_tr_ids[] / inactive_tr_history[]` はLLM入力ではなく `downstream_state.py` のmachine-owned出力をそのまま渡します。`inactive_tr_ids[]` はprevious `active` TRだけを列挙し、`update_scope_tr_ids[]` と重複させません。`update_scope_tr_ids[]` はprevious `active / inactive` を参照でき、`deleted` は参照できません。inactive TRをLLMがsemantic identity同一としてreuseした場合は同じTR IDを `active` へ戻し、そのstate rowの `scope_refs[]` をcurrent draft値へ更新します。update scopeへ入れたinactive TRをreuseしない場合は `deleted` にします。update scope外のinactive TRはstatusと最後の`scope_refs[]`を維持します。new ID allocatorはactive / inactive / deletedをすべて使用済みIDとして扱います。

`acceptance_criteria[]` は§3.1のexact schemaを使用し、**current ACだけ**を含めます。blocked ACはknown current AC集合、Machine Entity、TRD closureの対象外です。`authority_refs[]` はtop-level `authorities[]` のknown IDへ存在検証します。ACなしworkflowでもkey省略は許可せず `[]` を明示します。

各 `test_requirements[]` draftへ `acceptance_refs[] / scope_refs[]` を必須追加します。該当ACがない横断的TRは `acceptance_refs=[]` を使用します。`acceptance_refs[]` と `scope_refs[]` の意味対応はLLMが判断し、generatorはそれぞれtop-level known AC / Scope集合への存在参照だけを検証します。

## 7. downstream scope ownership / requirement_structure-v2 deterministic processing

### 7.1 requirement_structure-v2

共通処理:

1. `acceptance_criteria[] / scope_ids[]` のschema / duplicate / canonical orderを検証し、各ACの `authority_refs[]` をtop-level `authorities[]` へ存在検証する
2. `test_requirements[].acceptance_refs[]` とAcceptance Criterion Dispositionのrefをknown AC集合へ存在検証する
3. `test_requirements[].scope_refs[]` をknown `scope_ids[]` のsubsetとしてduplicateなし・canonical sortで検証する。UI target artifact workflowでは各current TRに1件以上を要求する
4. closure universeへtop-level current ACを追加する
5. TR Entity contentへ `acceptance_refs[] / scope_refs[]` を保存する
6. AC linked + disposedの二重扱いを拒否する
7. linkedもdisposedもされないcurrent ACをunclosedとして拒否する
8. Authority / Product Risk / Acceptance Criteriaのclosure集合を別々に評価する。TRの `acceptance_refs[]` にACを追加しても、そのACのAuthorityをTR draftの `authority_refs[]` へ暗黙追加しない
9. `tr_id_state[]` は `{tr_id,status,scope_refs}` を生成し、active / reactivatedはcurrent Entity contentのscope_refsとexact一致、inactive / deletedはlast active scope_refsを保持する
10. `artifact:requirement_structure:all` root payloadへ `inactive_tr_history[]` を保存する。inactive TRのlast-active Machine Entity snapshotをidentity順で保持するmachine-owned historyとし、active→inactive時はprevious current TR Entityを追加、inactive継続時はcanonical bytesを維持、inactive→active reuseまたはdeleted遷移時は該当snapshotを除去する。history Entityはshared Entity schema / stored content fingerprint / identityとstate row `scope_refs[]` の一致だけを検証し、current Machine Entity / expected Entity / freshness対象へ入れない

artifact mode追加処理:

10. validated `metadata.upstream_entities` からcurrent Acceptance Criterion Entityを抽出し、top-level `acceptance_criteria[]` と `ac_id / authority_refs[]` がexact一致することを要求する
11. 各参照AC EntityをTR Entity `upstream_entity_dependencies[]` へ追加する
12. 各参照ACのcurrent Authority dependencyをTR Entity dependencyへ直接追加する
13. AC / Authority Entityが不足・不一致ならfail-closedする

direct mode追加処理:

10. upstream AC Entityの存在を必須にしない
11. 参照AC Entityが `metadata.upstream_entities` に実在する場合だけ、semantic `acceptance_criteria[]` の同一AC rowと `ac_id / authority_refs[]` 一致を検証したうえで、既存 `resolve_entity_dependencies(..., require_all=false)` と同じ方針でAC Entity dependencyへ追加する
12. top-level `acceptance_criteria[].authority_refs[]` だけを根拠にAC由来Authority dependencyを生成しない。TR自身の `authority_refs[]` による既存direct dependency解決を維持する

AC linkはACだけをclosureします。Authorityは従来どおりTR draftの `authority_refs[]` に明示linkされるか、Authority Dispositionへ入る必要があります。artifact modeのAC→Authority dependency展開はfreshnessのためであり、Authority closureを代理しません。direct modeではこの展開を行いません。

LLMはACとTRの意味上の対応、TRの分割 / 統合、TRのscope所属を判断します。scriptは対応関係の意味妥当性を決めません。

### 7.2 condition-structure-v2

- current `test_requirements[]` rowへTR Entityのcanonical `scope_refs[]` を含め、`tr_id / scope_refs[]` をcurrent TR Entity contentとexact一致させる
- TCN draft自身にLLM入力のscope fieldは追加しない。各current TCNの `scope_refs[]` は参照する `tr_refs[]` のTR scope_refs unionを重複除去・canonical sortして決定論生成する
- modelの `scope_refs[]` は親TCNのscope_refsとexact一致させる。derived childも親modelからではなくowner TCNのcurrent scope_refsを使う
- TCN / model Machine Entity contentへ `scope_refs[]` を保存する
- `previous_tcn_ids[]` は `{tcn_id,status,scope_refs}`、`previous_model_keys[]` は既存model identity field + `status / scope_refs` を持ち、inactive / deletedでもlast active scope_refsを保持する
- `artifact:condition_structure:all` root payloadへ `inactive_tcn_history[] / inactive_model_history[] / inactive_materialize_history[]` を保存する。前2つはinactive TCN / modelのlast-active Machine Entity snapshotをmachine-owned historyとして保持し、active→inactive時はprevious current Entityを追加、inactive継続は保持、reuse / deleted時は該当snapshotを除去する。history Entityはstored fingerprint / identity / state row scope_refsだけを検証しcurrent evidenceへ入れない
- `inactive_tcn_ids[] / inactive_model_keys[]` はactive previous identityだけをactive→inactiveへ遷移させる。inactive→active reuse時はcurrent upstreamから再導出したscope_refsへ更新する

### 7.3 materialize-coverage-v2

- current model Entity contentの `scope_refs[]` をscope ownershipの正本とし、Agent入力でCI scopeを再指定させない
- runtime target / semantic CIとも、生成するCI Entity contentの `scope_refs[]` はowner modelのscope_refsとexact一致させる。1つのmaterialize invocation内で複数sourceをmergeする場合は、それらowner model scope_refsのunionをcanonical化する
- `previous_ci_ids[]` / `ci_id_state[]` はexact `{ci_id,status,scope_refs}` とし、inactive / deletedでもlast active scope_refsを保持する
- `inactive_materialize_history[]` の各entryは `tcn_id / ci_entities[] / ci_id_state[] / target_mapping_state[] / semantic_ci_mapping_state[] / expected_result_root_state[]` のexact schemaを持ち、`tcn_id`順でcanonical sortする。`ci_entities[]` はlast-active CI Machine Entity snapshot、残り4配列はlast successful `materialize-coverage-v2` payloadの `ci_id_state / target_mapping_state / semantic_ci_mapping_state / expected_result_root_state` をそのままcanonical化して保存する。`ci_id_state[]` にはactive / inactive / deletedをすべて残し、inactive期間中もallocatorの使用済みCI ID集合を失わない
- active→inactive TCNでprevious current CIまたはmapping stateが存在する場合、`downstream_state.py` はverified previous TCD structure stateから該当materialize resultを読み、`inactive_materialize_history[]` を更新する。raw Markdown / stale runtime resultから復元しない。対応resultが必要なのに欠落・invalidなら `inactive_materialize_history_missing` でfail-closedする
- reactivated TCNの`materialize-coverage-v2`はcurrent previous materialize resultが無い場合だけmatching history entryを使い、`target_mapping_state → previous_target_id_map`、`semantic_ci_mapping_state → previous_semantic_ci_map`、`expected_result_root_state → previous_expected_result_roots`、`ci_id_state → previous_ci_ids` を決定論的に再構成する。historyはcurrent runtime evidenceではなくID / mapping seedだけで、generation / freshness / support statusをcarry-forwardしない
- history entryは同じTCNが再度active→inactiveになった時に最新successful materialize stateで置換する。active中に古いhistoryが残っていてもcurrent materialize resultを常に優先し、terminal deleted TCNではentryを除去する
- `inactive_ci_ids[]` はactive previous CIだけをactive→inactiveへ遷移させる。既存 `previous_target_id_map[].mapping_status / previous_semantic_ci_map[].mapping_status=active|inactive` は維持し、scope blockをsemantic deletionへ変換しない

### 7.4 case-structure-v2

- current TCN input rowへcurrent TCN Entityの `scope_refs[]` を含め、CI Entity contentの `scope_refs[]` も検証する
- TC draft自身にLLM入力のscope fieldは追加しない。各current TCの `scope_refs[]` は参照する `tcn_refs[] / ci_refs[]` のscope_refs unionを重複除去・canonical sortして決定論生成する
- TC Machine Entity contentへ `scope_refs[]` を保存する
- `previous_tc_ids[] / tc_id_state[]` はexact `{tc_id,status,scope_refs}` とし、inactive / deletedでもlast active scope_refsを保持する
- `artifact:case_structure:all` root payloadへ `inactive_tc_history[]` を保存する。inactive TCのlast-active Machine Entity snapshotをmachine-owned historyとして保持し、active→inactive時はprevious current TC Entityを追加、inactive継続は保持、reuse / deleted時は該当snapshotを除去する。stored fingerprint / identity / state row scope_refsだけを検証しcurrent evidenceへ入れない
- `inactive_tc_ids[]` はactive previous TCだけをactive→inactiveへ遷移させ、inactive→active reuse時はcurrent upstreamから再導出したscope_refsへ更新する

### 7.5 shared runtime state / currentness

- shared `runtime_contract.py` のprevious state parser / validatorはTR / TCN / model / CI / TC state rowの `scope_refs[]` を検証する。active stateは対応current Machine Entity contentのscope_refsとexact一致させ、inactive / deletedにはcurrent Entityを要求しない
- `verify_runtime_evidence.current_structure_state.runtime_results[]` に含まれる各root result payloadをmachine-owned historyの保存元とする。次runへ渡す際は、それらを個別artifactから直接読むのではなく、直前に完成扱いされたruntime-v2 qa-workflow artifactの保存済み `workflow_scopes[].current_structure_state` を `downstream_state.py` が上記§12.3の手順で再検証・抽出する。未検証artifact本文やcurrent inputでの旧artifact再検証からhistoryを復元しない
- activeだけをcurrent Machine Entity / expected Entity / carry-forward projectionへ含める。`inactive_*_history[]` / `inactive_materialize_history[]` はlast-active履歴としてexact schema、identity重複、canonical order、stored fingerprint、対応inactive state row / scope_refsとの整合だけを検証し、current Entity / current runtime / expected Entity / freshnessへ投入しない
- UI target migration前のv2 baselineは `scope_refs=[]` を許可する。UI target migration後の最初のTRD→TCD→TC更新でcurrent active downstream全件をscope ownership付きに正規化し、active TR / TCN / model / CI / TCに空scope_refsが残る間はpartial readinessを開始しない
- scope_refsはMachine Entity content fingerprintへ含まれるため、ownership変更は通常のfreshness伝播対象になる

## 8. AC disposition

既存共通Disposition schemaを再利用します。新しいDisposition形式は作りません。

`test-requirement-design` の許可upstream typeへ `acceptance_criterion` を追加します。

owner mapping:

- authority → spec-analysis
- product_risk → test-analysis
- acceptance_criterion → spec-analysis

ACで許可するhandlingは次の4値に固定します。

- 別テストレベル
- 残存リスク
- 対象外
- ブロック中

`acceptance_criterion` upstreamに `重複` は許可しません。Authority / Product RiskについてはPR #14後の既存Disposition handling契約を維持します。

人間向け `テスト要求を作らない上流項目` の種別へ `Acceptance Criteria` を追加します。

## 9. test-requirement output

`テスト要求一覧`:

| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

ACが存在しないworkflowでは `関連AC ID` を `-` とします。

`テスト要求を作らない上流項目` の種別:

- 仕様根拠
- プロダクトリスク
- Acceptance Criteria

## 10. deterministic output validator

`TR-OUT-003` のfixture contractを固定します。

expected keys:

- `known_acceptance_criteria`
- `required_linked_acceptance_ids`
- `expected_dispositions`

validatorはAuthority / Product Risk / Acceptance Criteriaをそれぞれ独立したclosure集合として扱います。各current ACはlinkedまたはdisposedのどちらか一方へ閉じ、各Authority / Product Riskも従来どおり自身のlinkまたはDispositionで閉じることを検証します。AC linkからAuthority closureを推論しません。

既存TR-OUT-001 / 002はACなしworkflowとして `known_acceptance_criteria=[]` 相当を確認し、従来挙動の回帰に使います。

## 11. freshness propagation

UI target packageからtest-requirement-designへ進むcanonical workflowはartifact modeを使用し、完全なAC semantic freshness保証はartifact modeの契約とします。次をrepository runtime testで固定します。

| 変更 | artifact modeの期待 |
| --- | --- |
| AC本文変更 | 関連TR stale |
| current ACが属するScopeがblockedへ遷移する | `inspect.blocked_scope_ids[]` とprevious downstream Entity `content.scope_refs[]` の積集合で該当TR / TCN / model / CI / TCを`inactive`へ遷移し、current freshness対象から外す。AC stable ID自体はretireせず、再ready化時にsemantic identity同一なら同じ下流IDも再利用できる |
| ACが意味上廃止されretired | 関連TR missing dependency / stale |
| linked UIOP変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親Behavior変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親UC変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親US変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| linked domain item / linked structure ancestor / linked INF変更 | AC fingerprint変更 → 関連TR stale |
| Authority変更、AC本文・親chain同じ、spec-analysis再実行済み | TRが保持する直接Authority dependency不一致 → 関連TR stale |
| 無関係UC / AC / domain item変更 | 無関係TRはcurrent |

direct modeは `acceptance_criteria[]` によるknown ID / closure検証を保証しますが、参照AC Entityが無いrunではAC本文・親chain・linked domain item等のcross-run semantic freshnessを保証しません。参照AC Entityが実在しTR dependencyへ記録された場合は、そのEntityについて既存freshness判定を利用できます。direct mode向けに別fingerprint schemaや新しいfreshness engineは追加しません。

freshness判定アルゴリズム自体は既存 `evaluate_entity_freshness` を再利用し、新しい伝播engineを作りません。

## 12. partial rerun / ready → blocked → ready

### 12.1 current upstream変更の既存freshness

readyのままcurrent AC等の内容が変わるpartial rerunは既存freshness契約を維持します。

1. AC-001へ依存するTR-001が存在
2. AC-001がcurrentのまま変更
3. TR-001が今回の `update_scope_tr_ids` 外
4. previous artifactからTR-001をactive carry-forward
5. carry-forward TRが旧AC fingerprintを保持
6. current AC Entityとの不一致によりTR-001がstale
7. workflow completion不可

scope外であることを理由に、**currentのまま変更された**upstreamへ依存する成果物をcurrent扱いしません。inactive契約はこのfreshness違反を隠すためには使いません。

### 12.2 downstream inactive state

TR / TCN / model / CI / TCのstable ID stateは次の3値です。

- `active`: current Machine Entity / current runtimeの対象
- `inactive`: semantic identityとlast active `scope_refs[]` を履歴として保持するが、一時的にcurrent対象外
- `deleted`: semantic identityが廃止されたterminal state。last active `scope_refs[]` は履歴として保持してよいが再利用しない

共通規則:

- `inactive` は `ready → blocked` の一時停止にだけ使い、semantic deletionの代替にしない
- activeだけをcurrent Machine Entity collection / expected Entity / carry-forward projectionへ含める。inactive / deletedはcurrent Entityへ含めず、inactive自体をmissing dependency / stale issueへ変換しない
- active / inactive / deletedの全IDをallocatorの使用済み集合へ含め、番号を再利用しない
- deletedはterminalで、reuse / reactivationを禁止する
- inactive state rowはlast active `scope_refs[]` を保持し、update scope外ならstatus / scope_refsを変更しない
- inactive IDをcurrent semantic draftがreuseし、LLMがsemantic identity同一と判断した場合だけactiveへ戻す。その際scope_refsはcurrent ready scopeから再確定した値へ更新する
- inactive IDをupdate scopeへ入れてreuseしない場合はdeletedへ遷移できる。意味が変わったcurrent itemはnew IDを採番する
- active previous IDをinactiveへ落とす集合はLLMに入力させず、§12.3のhelper出力だけを正本とする

generator / state contract:

- `requirement-structure-v2`: required machine-owned `inactive_tr_ids[] / inactive_tr_history[]`、`previous_tr_ids[] / tr_id_state[] = {tr_id,status,scope_refs}`
- `condition-structure-v2`: required machine-owned `inactive_tcn_ids[] / inactive_model_keys[] / inactive_tcn_history[] / inactive_model_history[] / inactive_materialize_history[]`、TCN / model state rowはstatus + scope_refsを保持する
- `materialize-coverage-v2`: required `inactive_ci_ids[]`、`previous_ci_ids[] / ci_id_state[] = {ci_id,status,scope_refs}`。reactivation時は§7.3のhistoryからprevious mapping inputを再構成できる
- `case-structure-v2`: required machine-owned `inactive_tc_ids[] / inactive_tc_history[]`、`previous_tc_ids[] / tc_id_state[] = {tc_id,status,scope_refs}`
- TCDの `current_structure_state.previous_ci_id_state` も同じ3状態 + scope_refsを保持する。TCN全体がinactiveで `materialize-coverage` をdispatchしない場合でも、condition-structure rootの `inactive_materialize_history[]` とCI stateでmapping / ID履歴を残す
- shared runtime previous state validationはactive stateだけをcurrent Machine Entity identity/content.scope_refsとexact一致させる

`inactive_*_ids[] / inactive_*_history[] / inactive_materialize_history[]` は各v2 generatorのraw inputに存在するmachine-owned fieldです。canonical qa-workflowでは `downstream_state.py` のvalidated outputをそのまま渡し、LLM / Agentが編集しません。full build、direct mode、またはinactive履歴が存在しないrunでもkey省略はせず空配列を明示します。generatorはcallerが任意に作ったhistoryをcurrent evidenceへ昇格させず、§7.5の検証条件を満たさないhistoryをrejectします。

inactive IDを所有するmodel/TCN向け個別runtime unitはcurrent expected/runtime集合へcarry-forwardしません。mixed ready/inactive状態でも `artifact:*:all` root unitはready/current入力から再生成してcurrentにできます。

### 12.3 blocked scopeからinactive集合を導出するhelper

新規 `skills/qa-workflow/scripts/downstream_state.py` はQA workflow固有のread-only deterministic helperです。generic graph frameworkや新しいfreshness engineにはしません。

input:

```json
{
  "workflow_ref":"<existing opaque UUID>",
  "workflow_state_record":{
    "workflow_ref":"<same opaque UUID>",
    "schema_version":"1",
    "state":{
      "last_completed_qa_workflow_artifact":{
        "artifact_ref":"...",
        "artifact_revision":"...",
        "artifact_sha256":"<lowercase-64-hex>"
      }
    }
  },
  "blocked_scope_ids":["SCOPE-002"],
  "previous_qa_workflow_artifact_markdown":"<workflow state bindingが指すexact historical revision>"
}
```

`workflow_state_record.state` の他fieldは既存workflow state契約のままopaqueとして扱い、helperは `last_completed_qa_workflow_artifact` だけを読みます。初回workflowはこのfieldを `null` とし、その場合だけ `previous_qa_workflow_artifact_markdown=null` を許可します。bindingがnon-nullならMarkdown必須、bindingがnullならMarkdown non-nullを拒否します。top-level artifact Markdownはcutover helperと同じ16 MiB aggregate transport / 64 KiB string exemptionを使い、通常generatorの2 MiB上限は変更しません。

output:

```json
{
  "inactive_tr_ids":["TR-002"],
  "inactive_tcn_ids":["TCN-003"],
  "inactive_model_keys":["decision-001"],
  "inactive_ci_ids":["TCN-003-CI01"],
  "inactive_tc_ids":["TC-004"],
  "inactive_tr_history":[],
  "inactive_tcn_history":[],
  "inactive_model_history":[],
  "inactive_materialize_history":[],
  "inactive_tc_history":[]
}
```

規則:

1. `blocked_scope_ids[]` はcurrent `ui_target_package.py inspect` の値をそのまま使い、Agentが追加・削除しない
2. `workflow_ref` は既存workflow stateのopaque UUIDをそのまま受けます。新しいlineage IDを作りません。`workflow_state_record.workflow_ref` とexact一致しなければrejectします
3. `workflow_state_record.state.last_completed_qa_workflow_artifact` はqa-workflowがcurrent artifact保存後にCAS更新したmachine-owned bindingだけを使います。bindingはexact `artifact_ref / artifact_revision / artifact_sha256` を持ち、Agent / LLMが組み立てません。qa-workflowは呼出前に既存 `artifact_graph.verify_historical_revision()` でstored revisionをhistorical refetchできることを確認します
4. bindingがnullならprevious Markdownもnullだけを許可します。bindingがnon-nullならprevious Markdown必須とし、raw UTF-8 bytesのSHA-256を再計算して `artifact_sha256` とexact一致させます。これにより別artifact / 1世代古いartifact / 改変artifactをrejectします
5. previous Markdownには `Machine Runtime Input / Result: qa-workflow::artifact:workflow_runtime:all` pairをexactly one要求します。qa-workflow runtime-v2 Inputの `workflow_ref` とResult payloadの `workflow_ref` はcurrent `workflow_ref` とexact一致させます
6. historical pairは `downstream_state.py` 内のqa-workflow専用frozen runtime-v2 integrity readerで検証します。保存Input / Resultのexact schema、runtime / envelope / generator contract version、pair identity、input / model / generation fingerprint、upstream Entity / runtime dependency、static data version、Machine Entity content fingerprintを保存値だけから再計算します。generation fingerprintは保存済み `runtime_implementation_fingerprint / generator_implementation_fingerprint` を入力としてfrozen v2式で再計算します
7. historical integrityでは保存されたimplementation fingerprintがlowercase digestとして自己整合することは要求しますが、**現在disk上のruntime_contract.py / generator実装fingerprintとの一致は要求しません**。現在実装との一致、current spec-analysis inputとの一致、current dependency freshnessはcurrentness判定であり、このreaderの成功条件にしません。current `verify_runtime_evidence()` / current result validatorをhistorical readerとして流用しません
8. 保存済みqa-workflow Inputの `workflow_scopes[] / current_entities[] / current_runtime_units[]` とResult payloadを検証します。Result payloadの `current_entities[]` はInputとexact一致させ、各workflow scopeの `current_structure_state` は同じ保存Input内の `normalized_input / current_entities / current_runtime_units` を使うfrozen v2 structure-state規則で自己整合を検証します。ここで検証できた `current_entities[]` とTRD / TCD / TCの `current_structure_state` だけをinternal previous snapshotとします
9. Agent / LLMは `previous_machine_entities[] / previous_structure_states` を入力しません。raw downstream artifact、個別Runtime Input / Result、人間向けruntime表、current inputに対する旧artifactの `verify_runtime_evidence` 結果からsnapshotを再構築しません。workflow state binding / historical revision / pair / integrityのいずれかが確認できなければfail-closedします
10. previous TR / TCN / model / CI / TC Entityはcanonical `content.scope_refs[]` を必須とし、duplicate / unsorted / non-stringをrejectします。UI target scope ownership baseline成立後に空scope_refsが残るactive downstream Entityは `scope_ownership_unavailable` でfail-closedします
11. `content.scope_refs[] ∩ blocked_scope_ids[]` が非空のprevious active Entityだけをinactive対象にします。Authority共有、名称、同一PAGE、AC dependency、runtime dependencyからscope所属を推測しません
12. 新たにinactiveになるTR / TCN / model / TCはprevious current Entity snapshotを対応historyへ追加します。既存inactive historyはidentityでmergeし、内容不一致をsilent overwriteしません
13. 新たにinactiveになるTCNがprevious current CI / target mapping / semantic mappingを持つ場合、検証済みprevious TCD `current_structure_state.runtime_results[]` の `artifact:materialize_coverage:<TCN-ID>` resultから `ci_entities / ci_id_state / target_mapping_state / semantic_ci_mapping_state / expected_result_root_state` を取得して§7.3のhistory entryを生成します。必要なresultが無い場合、またはCI state / mappingが相互不整合なら `inactive_materialize_history_missing` でfail-closedします
14. `scope_refs[]` がready / blocked双方を含むcross-scope Entityもentity単位でinactiveにします。ready側だけへ自動縮退しません
15. current packageで初めてblockedになりprevious Entityが存在しないitemはinactive IDを生成しません
16. outputはstable ID / history identity順でcanonical sort / dedupeします

qa-workflowはhelper outputを各generator / TCD current structure stateへ直接接続します。

### 12.4 再ready化

blocked Scopeがreadyへ戻ってもinactive IDを自動active化しません。

- current ready `scope_index[]` とcurrent upstreamからsemantic draftを再作成する
- LLMはinactive ID stateのlast active scope ownershipと `inactive_tr_history[] / inactive_tcn_history[] / inactive_model_history[] / inactive_tc_history[]` のlast-active contentを参照し、semantic identity同一かを判断する。historyをcurrent evidenceとして扱わない
- semantic identity同一なら既存IDをreuseし、generatorがinactive → activeを適用する。current `scope_refs[]` はready Scope集合のsubsetとして再確定する
- semantic identityが変わった場合は旧inactive IDをdeletedへ遷移し、new IDを採番する
- まだblockedなScopeだけに属するinactive IDはupdate scopeへ入れずinactiveのまま保持する
- cross-scope inactive Entityをready側だけへ縮退して同じIDをreuseするか、旧IDをdeletedにして分割するかはLLMのsemantic identity判断とする。helperは決めない
- current upstreamが不足した状態、またはcurrent `scope_refs[]` がknown ready Scope集合へ解決しない状態でinactive IDをactiveへ戻そうとした場合はfail-closedする

この経路により、SCOPE-A/Bが一度readyになった後Bだけblockedになっても、Bをscope_refsに持つ旧downstream Entityだけがcurrent freshness判定から外れ、A専用Entityのready-scope executionを不要に停止しません。AuthorityをA/Bで共有していてもscope ownershipは変わりません。package全体のstatusがpartial / blockedかどうかはspec-analysisの `scope_readiness[]` が引き続き正本です。

### 12.5 UI target migration後のscope ownership baseline

v1 cutover / non-UI-target v2 baselineではdownstream `scope_refs=[]` を許可しますが、この状態でready/blocked partial progressionは開始しません。

UI target package migration時点で既存active downstreamが1件以上あり、scope_refsが空のidentityを含む場合は、**全current scopeがreadyの1回だけ**をownership normalization gateとします。全scopeを含む `scope_index[]` から既存active TR全件へLLMが `scope_refs[]` を付与し、TCD / TCがscope_refsを決定論伝播してcurrent TR / TCN / model / CI / TCすべてのownershipを確立します。coverage-analysis / qa-workflowまで再生成してこのbaselineがcurrentになった後だけ、`downstream_state.py` によるpartial readinessを有効にします。

ownership baseline前に1件でもblocked scopeがある場合は `scope_ownership_baseline_required` でfail-closedします。ready scopeだけへ旧IDを推測割当したり、blocked scope由来と思われる旧IDを一律inactiveへ落としたりしません。downstream未作成の新規UI target workflowはこのone-time gateの対象外で、最初からcurrent ready scopeだけを使ってpartial progressionできます。

## 13. qa-workflow / coverage-analysis integration

shared `_expected_entities()` がspec-analysis normalized inputからAuthority + AC expected identityを決定論導出します。TRD / TCD / TCのprevious stateではactiveだけをexpected current Entityへ含め、inactive / deletedをextra/missing Entity判定のcurrent universeから除外します。

qa-workflow / coverage-analysisはcurrent Entity collectionへAC Entityが存在してもextra entity扱いしません。

### 13.1 qa-workflow runtime identity / completed artifact binding

`skills/qa-workflow/scripts/workflow_runtime.py` のruntime-v2 normalized inputへrequired `workflow_ref`を追加し、`artifact:workflow_runtime:all` Result payloadにも同じ値をechoします。`workflow_ref`は既存workflow stateのopaque UUIDであり、Machine Entity IDやpackage-local IDへ変換しません。Input / Result不一致はruntime invalidです。

UI target downstreamをcompleted baselineとして扱う時だけ、qa-workflowは保存済みworkflow stateの `last_completed_qa_workflow_artifact` を更新します。更新順は `qa-workflow runtime current verification PASS → artifact保存 → artifact_ref/revision取得 → historical refetch availability確認 → raw Markdown SHA-256計算 → workflow state CAS` とします。途中失敗では旧bindingを維持し、新artifactをlast completedとして扱いません。`ready_scope_ids=[]` でdownstream runtimeをdispatchしないrun、またはqa-workflow resultがunresolved / blockedのrunではbindingを更新しません。

coverage-analysisの既存traceability graph node typeへACを追加しません。AC→TRのmachine traceabilityはTR Entity dependencyとTRD closureで保証し、Authority / Risk / TR / TCN / CI / TCの既存coverage graphを不要に拡張しません。inactive TR / TCN / CI / TCはcurrent graph node / current runtime unitへ入れず、blocked scopeの再開情報はspec-analysisのscope readinessとdownstream ID stateのlast active `scope_refs[]` で保持します。

## 14. repository tests

次を更新 / 追加します。

- PR #14後の9 Skill-local runtime_contract.py copies byte-identical
- active Machine Evidence template / fixtureが手書き擬似schemaを持たず、保持するfixtureはruntime-v2 / entity-state-v2 validatorでparse / validateできる
- generator contractの `-v1` をshared runtime v2へ誤って置換しない。`requirement-structure / condition-structure / materialize-coverage / case-structure` だけは本Planでそれぞれ明示v2へ上げる
- `acceptance_criterion` Machine Entity valid / unknown type regression
- shared canonicalization: `acceptance_refs` / `acceptance_criteria`
- spec-analysis expected Authority + **current ACだけ**のidentity。blocked ACをexpected Entityへ含めない
- AC-001 current → blocked → currentでstable IDを維持し、blocked期間はAC Entity / `acceptance_criteria[]` から除外、explicit retire時だけterminal retireする回帰
- current UC → blocked UCのancestor state propagation。LLMがUC / Behavior / AC identity reuseを維持した場合、BH / ACは同じstable IDのeffective blockedへ決定論伝播し、ancestor由来だけでは子UNKNOWNを増やさず、UC blocker解消後に同じIDでcurrentへ戻る
- 通常の非mode spec-analysis normalized inputで `acceptance_criteria` key省略を空集合として扱い、既存Authority expected Entityだけを維持
- qa-workflow expected / actual Entity exact match
- coverage-analysis current Entity parse compatibility
- requirement-structure-v2 valid / invalid schema
- requirement-structure-v2がtop-level `acceptance_criteria[] / scope_ids[]` をraw input必須とし、各ACの `ac_id / authority_refs[]` と各TRの `acceptance_refs[] / scope_refs[]` を検証すること。ACなしは `acceptance_criteria=[] / acceptance_refs=[]`、non-UI-target baselineは `scope_ids=[] / scope_refs=[]` を明示し、default補完adapter / shared runtime hookを追加しない
- artifact modeではsemantic `acceptance_criteria[]` とupstream Acceptance Criterion Entity集合をexact一致させ、AC Entity + AC Authority dependencyをTR freshnessへ追加する回帰
- direct modeではupstream AC Entityなしでもsemantic `acceptance_criteria[]` をknown ID集合として `acceptance_refs[]` / closureを検証でき、存在しないAC / AC由来Authority Machine Entity dependencyを合成しない回帰。AC Entityなしのdirect modeではAC本文 / 親chain変更のcross-run freshnessを保証しないことも契約化する。実在AC Entityをdependencyへ使う場合はsemantic rowとの `ac_id / authority_refs[]` 一致を要求し、そのEntity dependencyについて既存freshnessを利用できること
- AC-001をTRへlinkしても、そのACが参照するSPEC-001をTR authority_refs / Authority Dispositionで別途closeしない場合はSPEC-001 unclosedとなる
- TRD / TCD / TC Skill-local runtime_v1_cutover.pyのprojection、runtime-v1 / entity-state-v1以外の入力拒否、内容不変時stable IDとv1 active / deleted history保持、初回v2 `inactive_*=[]`
- AC linked / disposed / unclosed / linked+disposed
- AC upstream skill/type mismatch
- artifact modeのAC dependency fingerprint propagation
- artifact modeでlinked UIOPの操作内容 / 対象構造変更によりAC本文 / 親chainが同じでもAC fingerprintが変わり関連TRがstaleになる回帰
- 同一UCに複数UIOP / Behavior / ACが存在し、各Behaviorが別の`関連操作ID`を持つ場合、UIOP-Aだけの変更でAC-A / TR-Aだけがstaleになり、Behavior-Bから参照されないUIOP-Aを理由にAC-B / TR-Bをstaleにしない回帰
- artifact modeでlinked UIOPだけが参照するAuthority contentを変更し、UIOP本文が同一でもAC Authority dependency / fingerprint変更から関連TRがstaleになる回帰
- artifact modeでAC / Behavior / UC / USの明示ref、linked UIOP target、linked domain itemから直接参照されるstructureと、そのancestor PAGE等のPath / 名称 / STATE軸を同一stable IDのまま変更するとAC fingerprintが変わる回帰
- artifact modeでAC chainから明示参照されたFIELD / RULE / FLOW / NOTIFY / INTERACTのcanonical内容変更でAC / TRがstaleになる回帰
- artifact modeでlinked INFのcanonical内容変更でAC / TRがstaleになる回帰
- artifact modeで同一PAGE / 同一Scopeに存在してもAC chainから明示参照されないdomain item変更ではAC / TRがstaleにならない回帰
- artifact modeでACが参照しない無関係structure / INF変更ではAC / TRがstaleにならない回帰
- parent_structure_idのmissing / self / cycleをrejectする回帰
- file applicabilityがnot-applicableのScopeを対応FIELD / FLOW / NOTIFY / INTERACT / IMPL rowが参照するpackageと、Behavior Decomposition=not-applicableのScopeにUIOP / US / UC / Behavior / ACが残るpackageをrejectし、ready-scope batchへ残存rowを混入させない回帰
- scopeの対象機能 / 領域またはscope Authority変更でAC fingerprint / dependencyが変わる回帰
- AC本文 / 親chain不変のままAuthority fingerprintだけ変更し、spec-analysisをcurrentへ再生成した後も未再実行TRが直接Authority dependencyによりstaleになる回帰
- artifact modeのpartial rerun stale carry-forward。currentのまま変更されたAC依存TRは従来どおりstaleでblockingになる
- SCOPE-A/B ready → `scope_index[]` からTR scope_refsをLLMが明示 → TCN / model / CI / TCへ決定論伝播 → Bだけblocked → `blocked_scope_ids[]` とprevious Entity `content.scope_refs[]` の積集合からB所有IDだけinactive → A専用current Entity/runtimeがfreshに完遂 → B再readyでsemantic identity同一なら同じIDをactiveへ復帰、というintegration regression
- 上記integration regressionのprevious snapshotはcurrent `workflow_ref` のworkflow state `last_completed_qa_workflow_artifact` が指すexact historical revisionからだけ抽出する。保存済み`artifact:workflow_runtime:all` Input / Result pair、Input `current_entities[]`、各scope `current_structure_state`の改変をrejectする。旧runtime-v2 implementation fingerprintのartifactでも保存値同士がfrozen v2規則で自己整合すればhistorical readerは受理し、current verifierではstaleになることを分離して確認する。別workflow_ref、1世代古いartifact、artifact SHA不一致、previousありなのにnull、historical refetch不能をfail-closedする
- AuthorityをA/Bで共有してもscope_refsがAだけのEntityはinactiveにしない回帰と、scope_refsがA/B双方のcross-scope Entityは保守的にinactiveへ落とす回帰
- v1 cutover / non-UI-target baselineの `scope_refs=[]` からUI target migrationする際、既存active downstreamがある場合は全scope readyでのみownership baselineを作成し、blocked scopeが残る間は `scope_ownership_baseline_required` でfail-closedする回帰。downstream未作成の新規workflowではpartial readinessを許可する
- inactive state rowがlast active `scope_refs[]` を保持し、`inactive_*_history[]` がlast-active Entity contentを保持するため、inactive期間を挟んでもre-ready時のsemantic ID reuse候補を失わない回帰
- SCOPE-A/Bのcompleted baseline後にA/Bともblockedとなって`ready_scope_ids=[]`になったrunではbatch handoff / downstream runtime / qa-workflow runtimeを起動せずlast completed bindingを維持し、その後Bだけreadyへ戻ったrunで同bindingからAをinactive、Bをreuse候補として復元できる回帰
- TCN active→inactiveでprevious current `materialize-coverage` の `ci_id_state / target_mapping_state / semantic_ci_mapping_state / expected_result_root_state` とCI Entityを `inactive_materialize_history[]` へ保存し、current runtime evidenceからは除外する回帰
- inactive TCN再ready時、current previous materialize resultが無くてもhistoryの `ci_id_state / mapping state` からprevious inputを再構成し、同一target / semantic identityへ同じCI IDをreuseできる回帰。inactive前にdeletedだったCI IDも使用済みID集合へ残り再採番されないこと、history欠落・改変は `inactive_materialize_history_missing` でblockedになること
- inactive IDはcurrent Entity / expected Entity / carry-forward runtimeへ含めず、inactive自体でqa-workflow / coverage-analysisをblockingしない。別のcurrent stale issueは従来どおりblockingする回帰
- inactive成果物を意味上廃止した場合はdeletedへ遷移し、そのIDを後続new allocation / reuseへ使わない回帰
- shared runtime-v1 / entity-state-v1 evidenceをruntime-v2 / entity-state-v2 current resultとして扱わない
- v2 cutover後の最初のpartial-rerun対応Skill実行がfull rebuildであり、v1 previous artifactを受け入れない

## 15. 対象外

- US / UC / Behaviorのglobal Machine Entity type追加
- 新しいfreshness engine
- coverage graphへのAC node追加
- v1 / v2の二重runtime実装
- Agent / LLMによるexpected Entity一覧の手組み
- actual Entity集合からexpected Entity集合を逆算すること

## 16. 完了条件

- PR #14後の9 runtime_contract.pyが同一内容でacceptance_criterionを扱える
- 9コピーがruntime-v2 / entity-state-v2へ同期され、`requirement-structure-v2 / condition-structure-v2 / materialize-coverage-v2 / case-structure-v2` が明示される。TRD / TCD / TC固有cutover projectionはshared runtimeではなく各Skill-local helperにある
- helperからpackage-global spec-analysis evidence + ready / blocked scope ID indexと、current ready scope全件のcanonical batch handoff + compact `scope_index[]` を別responseで決定論生成できる。package-global responseへscope別full payloadを複製しない
- qa-workflowは `inspect.ready_scope_ids[]` が1件以上の時だけ全件をbatch inputにし、Authority / current AC / Machine Entity / expected identityをhelper側でunion / dedupeする。`ready_scope_ids=[]` では空batch / downstream runtimeを起動しない。blocked scopeを含めず、Agentがmerge / filterしない。TR scope_refsはLLMがscope_indexから明示し、TCN / model / CI / TCはgeneratorが上流参照から決定論伝播する
- batch handoffから構成する `artifact:analysis_entities:all` / `artifact:requirement_structure:all` のcanonical stdin全体を16 MiB境界で検証し、2 MiB超〜16 MiB以下を1回のaggregate root runtimeで処理できる。16 MiB超過時は個別scope run / subset run / silent truncate / auto splitで回避しない。その他の通常generatorは2 MiB上限を維持する
- test-requirement-designまで進むworkflowではcurrent ACがTRまたはDispositionへ完全に閉じる。仕様理解packageだけの要求ではこのclosureを要求しない
- UI target artifact workflowでは、AC / linked UIOP / scope / 明示linked FIELD-RULE-FLOW-NOTIFY-INTERACT / direct structure + ancestor / linked INF / 親Behavior-UC-US / Authority変更が必要なTR freshnessへ伝播し、無関係package row変更は伝播しない
- direct modeはknown AC ID / closureを保証し、AC Entity dependencyが無い場合のAC semantic cross-run freshnessを保証対象にしない
- 無関係TRを不必要にstale化しない
- ready→blockedでは、existing `workflow_ref` とworkflow stateのlast completed bindingで特定したexact historical qa-workflow artifactから、frozen runtime-v2 integrity検証済みprevious Entity / structure stateだけを抽出する。historical integrityをcurrentnessへ読み替えず、`blocked_scope_ids[]` とprevious Entity `scope_refs[]` が交差するTR / TCN / model / CI / TCだけをinactiveとしてcurrent Entity/runtimeから外し、Authority共有だけでは無関係ready scopeを停止させない。inactive state + root payloadの `inactive_*_history[]` はlast-active ownership / semantic contentを保持し、TCDは `inactive_materialize_history[]` のCI state / mappingも保持するため、再ready時にsemantic identity同一なら同じstable IDへ復帰でき、削除済みCI IDも再利用しない。既存unscoped downstreamのUI target migrationでは全scope readyのone-time ownership baselineを要求し、baseline前にscope所属を推測しない
- artifact modeのpartial rerunでscope外TRがcurrentのままchanged ACを参照したままcurrentにならず、blockedによる一時非currentと通常staleを混同しない
- existing coverage graphを目的なく拡張していない
