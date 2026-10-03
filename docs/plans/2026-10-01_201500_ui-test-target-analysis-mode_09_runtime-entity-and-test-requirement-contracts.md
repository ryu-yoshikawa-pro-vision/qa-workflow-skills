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
- legacy readerがartifact内から抽出した各v1 JSON blockは、旧通常runtimeが生成可能だった2 MiB aggregate上限内でstrict decodeし、`runtime_contract_version=runtime-v1 / entity_schema_version=entity-state-v1`、Input / Result pair、Entity identity / dependency / stored fingerprintをfrozen v1規則で再検証する
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
- active TRを `update_scope_tr_ids[]` へ全件入れ、first v2 runをfull rebuildにする
- missing / extra / duplicate mappingをblockedにする

#### test-condition-design/runtime_v1_cutover.py

TCDはcurrent v2 model resultを後段へ使うため4 phaseで進めます。

`condition-structure`:
- v1 condition_structure input/resultをexactly 1 pair要求
- `tcn_id_state / model_key_state` をprevious stateへ移す
- TCN / model `draft_key ↔ *_id_map` をexact joinしてreuseへ固定
- active TCN / modelをfull rebuild scopeへ入れる

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
- previous target / semantic CI / CI ID / expected-result-root stateをv1 resultからprevious stateへ維持
- target annotation / disposition / merge groupのsemantic fieldを維持し、version fingerprintだけcurrent targetへrebase
- semantic coverage itemはv1 source_target_versionsで旧semantic_content_fingerprintを再計算してv1 mappingへ一意joinした後、current target versionへrebaseして同じCI IDをreuseする
- 0件 / 複数mapping、target集合 / merge membershipのsemantic driftをblockedにする

#### test-case-design/runtime_v1_cutover.py

expected unitは `artifact:case_structure:all` exactly 1件です。

- v1 inputのsemantic fieldを維持
- v1 result `tc_id_state` → `previous_tc_ids[]`
- `draft_key ↔ tc_id_map[]` をexact joinし、current TC draftをreuseへ固定
- active TCを `update_scope_tc_ids[]` へ全件入れてfull rebuild
- missing / extra / duplicate mappingをblockedにする

#### 9 Skillのruntime-v1 evidence処置

`runtime-v2 / entity-state-v2` へ上げる9 Skillについて、v1 artifactの扱いを次へ固定します。v1 envelope / Entity fingerprintをcurrent扱いせず、必要なstable identityだけを各Skillの正本から維持します。追加cutover helperを作るのはTRD / TCD / TCだけです。

| Skill | v1 artifactの扱い | v2移行方法 | stable identity | 再実行 / 再観測 |
| --- | --- | --- | --- | --- |
| spec-analysis | v1 Machine Entity / wrapperは破棄 | current canonical spec-analysis inputからAuthority Entityをv2再生成。UI target migration前は既存semantic rowを変更しない | SPEC / DEC / ASM等のsemantic IDをhuman-readable / canonical inputから維持 | deterministic evidence再生成。version bumpだけを理由に仕様再分析しない |
| test-analysis | v1 Runtime / Entity evidenceはcurrent扱いしない | 保存済みartifactのvalidated `Machine Runtime Input.input` をcanonical sourceとして同じgeneratorをfull rerunしv2 evidenceを再生成する。Machine Runtime Inputがmissing / invalidならMarkdownから再構築せず通常test-analysis再実行を要求する | RISK等のsemantic IDは保存済みinput / current artifact上のIDを維持し、v1 fingerprintをseedにしない | valid保存inputがあればdeterministic rerun。無ければ通常Skill rerun |
| test-requirement-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` でcomplete v2 inputを作りfull rebuild | TR ID / inactive・deleted履歴をcutoverで維持 | cutover必須 |
| test-condition-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` の4 phaseでcomplete v2 inputを作りfull rebuild | TCN / model / CI IDと履歴をcutoverで維持 | cutover必須 |
| test-case-design | v1 resultをprevious artifactへ直接渡さない | `runtime_v1_cutover.py` でcomplete v2 inputを作りfull rebuild | TC ID / inactive・deleted履歴をcutoverで維持 | cutover必須 |
| coverage-analysis | v1 aggregate evidenceをcarry-forwardしない | 保存済みMachine Runtime Inputがvalidならそのsemantic inputを現在のupstream v2 Entityへrebindして`traceability` / verifierをfull rerunする。保存inputが無ければcurrent upstream v2 evidenceから通常Skill契約どおり再生成する | 自Skill Entityをcarry-forwardしない既存契約を維持 | deterministic full rerun |
| qa-workflow | v1 aggregate evidenceをcarry-forwardしない | 各scope担当Skillのcurrent v2 evidenceを揃え、保存済みMachine Runtime Inputがvalidならそのworkflow semantic inputを再利用して`workflow_runtime.py` / final gateをfull rerunする。保存inputが無ければcurrent workflow state / routing入力から通常契約で再生成する | 自Skill Entityをcarry-forwardしない既存契約を維持 | orchestration evidenceを再生成 |
| usability-inspection | v1 runtime envelopeをcurrent扱いしない | 保存済みMachine Runtime Inputが存在し既存validator / currentness契約を満たす場合だけそのexact inputからv2 evidenceを再生成する。保存inputが無い / invalidならMarkdownから復元せず、既存Skill契約による通常再実行または必要なlive再観測を行う | runtime version bumpだけで新しいproduct identityを作らない | valid保存inputがある場合はversion bumpだけでlive再観測しない。無い場合は通常Skill判断 |
| wcag-conformance-evaluation | v1 runtime envelopeをcurrent扱いしない | 保存済みMachine Runtime Inputが存在し既存validator / WCAG-EM currentness契約を満たす場合だけそのexact inputからv2 evidenceを再生成する。保存inputが無い / invalidならreport proseから復元せず、既存sampling / procedure / handoff契約で通常再実行する | evaluation / sample等のsemantic identityは既存Skill契約を維持 | valid保存inputがある場合はversion bumpだけでlive再観測しない。無い場合は通常Skill判断 |

この表にないmigration wrapper / generic converterは追加しません。spec-analysisはcanonical spec成果物、runtime対応Skillはvalidated Machine Runtime Input、workflow系はcurrent workflow stateを正本とし、proseからv2 inputを推測変換しません。PR #14 merge後のStep 0では各Skillの保存input blockが実際に存在・parse可能であることだけを再計測し、存在しない場合は上表の通常rerun経路へ固定します。新しい設計判断はStep 0へ持ち越しません。

#### UI target migrationとの相対順序

既存runtime-v1 downstream artifactがあるworkflowでは次の順だけを許可します。

1. runtime-v1 downstreamを検出し、通常semantic update / partial rerunを停止
2. spec-analysis / test-analysisのsemantic内容を変えずruntime-v2 / entity-state-v2 evidenceを再生成
3. TRD → TCD → TCを上記Skill-local cutover helperでsemantic不変のままv2 full rebuildし、downstream v2 baselineを成立させる
4. v2 baselineがvalidate / freshnessを通過した後に、legacy / normal spec-analysis成果物をui-target-v1へmigrationしてUS / UC / Behavior / ACを生成
5. requirement-structure-v2を通常semantic updateとして再実行し、AC→TR / Dispositionを反映
6. AC / Authority変更でstaleになったTCD / TC / downstream evidenceを通常workflowで再実行

`UI target migration済み + runtime-v1 downstreamあり + cutover未完了` はblockedです。逆順を許可しません。runtime-v1 downstream artifactが存在しないworkflowだけ、UI target package migrationから直接normal v2 workflowへ進めます。

#### repository regression

- 3 helperのpackage単体compile / portability
- cutover外側transportは16 MiB accepted / 1 byte超過blocked。cutover処理によってgenerator上限を変えないことを確認し、別途§3の2 root runtimeだけaggregate 16 MiB、その他の通常generatorは2 MiBを維持する
- v1以外のsource runtime / entity schema、v1/v2混在、missing / extra / duplicate / incomplete pairをlegacy readerでrejectし、current v2 validatorがv1 sourceを誤ってreject/acceptする経路を持たない
- top-level artifact stringが64 KiBを超えてもaggregate 16 MiB以内ならcutover入口で受理し、artifact内JSON scalarが64 KiBを超える場合はrejectする回帰
- frozen v1 fingerprint / dependencyを改変したsource artifactをlegacy readerがrejectする回帰
- 内容不変cutoverでTR / TCN / model / CI / TC IDとdeleted / inactive identity historyを維持
- 各helper返却inputだけで次のv2 generatorを実行でき、Agent-side merge不要
- TCD target version rebase、derived child、semantic CI mappingをcurrent v2 resultへ正しく接続
- `UI target migration済み + runtime-v1 downstream + cutover未完了` をintegration testでblocked
- cutover完了後のUI target migration → AC semantic update → downstream stale / rerunを実Agent smokeで確認

## 3. spec-analysis normalized machine input

`ui_target_package.py build-machine-evidence(scope_ids=null)` はpackage-global evidenceと `ready_scope_ids[] / blocked_scope_ids[]` を決定論生成し、scope別full handoffを同じresponseへ複製しません。`build-machine-evidence(scope_ids=[...])` は各ready scopeを固定reachabilityで内部projectionし、Authority / current AC / Machine Entity / expected identityをstable identityでunion / dedupeした1つのbatch handoffを返します。canonical qa-workflowでは `scope_ids[]` をcurrent `ready_scope_ids[]` とexact一致させます。Markdownから次を決定論的に生成します。

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

qa-workflow / test-analysis / coverage-analysisへspec-analysis成果物を渡す場合、AgentがMarkdownからJSONを再構築しません。current `inspect.ready_scope_ids[]` 全件を `build-machine-evidence(scope_ids=ready_scope_ids)` へ渡し、helperが1つのcanonical batch handoffを生成します。既存runtime unit `artifact:analysis_entities:all` / `artifact:requirement_structure:all` は維持し、scopeごとの別runtime unitへ分割しません。

### ready-scope batch root runtime入力上限

`artifact:analysis_entities:all` / `artifact:requirement_structure:all` はready scope全件を1 requestへ集約するroot runtime unitなので、本PRで各entrypointを `run_cli(..., aggregate=True)` へ変更します。最終canonical stdinは2 MiBを超えても16 MiB以下なら処理し、16 MiB + 1 byteは `limit_exceeded` でfail-closedします。この上限はruntime unitのtransport契約としてdirect / artifactの両input modeに共通適用し、mode別のwrapperや例外経路は追加しません。その他の通常generatorは既存2 MiB上限を維持します。

qa-workflowはbatch handoffからroot runtimeの最終canonical stdinを構成した後に同じ16 MiB境界を事前検査します。超過時はruntimeを起動せずblockedにし、scope別個別run / subset run / Agent merge / silent truncate / auto splitで回避しません。`MAX_AGGREGATE_INPUT_BYTES`、depth、1文字列64 KiB、stdout等の既存安全制約を再利用し、新しい分割・merge契約は追加しません。

### 3.1 requirement-structure-v2 caller contract

`acceptance_refs[]` の意味対応だけをLLM判断に残し、known AC集合の取得経路とMachine Entity dependencyの扱いはinput modeごとに固定します。empty default用adapterは追加しません。

`requirement-structure-v2` raw generator inputはtop-level `acceptance_criteria[]` を必須とします。schemaはexactに次です。

```json
{
  "acceptance_criteria": [
    {"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
  ]
}
```

- `ac_id` はduplicate不可、canonical sortする
- `authority_refs[]` はduplicate不可で1件以上、top-level `authorities[]` のknown Authority IDだけを許可する
- ACなしworkflowは `acceptance_criteria=[]` を明示する
- 各 `test_requirements[]` draftの `acceptance_refs[]` も必須とし、known `acceptance_criteria[].ac_id` への存在参照だけをhelperが検証する

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
- ACの `ac_id / authority_refs[]` はknown-ID検証とclosureのsemantic inputであり、TR Entity contentへは従来どおり各TRの `acceptance_refs[]` を保存する

旧runtime-v1 / requirement-structure-v1からの初回cutoverは§2.7のtest-requirement-design `runtime_v1_cutover.py` がTRのstable identity / historyとsemantic draftをv2へ変換します。AC集合はv1 artifactから推測せず、v2 invocationのcallerが上記contractに従って渡します。UI target artifact経路ではspec-analysis helper返却値をそのまま使用します。

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
- `linked_ui_operations[]`: **状態=`mapped`** かつ `対応UC ID` に親UCを含むUIOPを `uiop_id` 昇順で `uiop_id / actor_role / target_structure_id / operation / authority_refs[]` として固定projection
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


## 5. test-requirement-design contract version

`requirement_structure.py` はinput schemaを変更するため、generator contractを明示的に次へ更新します。

- before: `requirement-structure-v1`
- after: `requirement-structure-v2`

shared runtime contractは `runtime-v2` を使用します。

repository内の固定contract mapping / fixture metadata / portability test / runtime test / vertical integrationで `requirement-structure-v1` を参照している箇所をcurrent v2へ同期します。

旧v1 Machine Runtime Resultをv2 current resultとして読み替えません。再利用が必要な成果物はcurrent normalized inputからv2を再実行します。

## 6. requirement_structure-v2 input

top-level required fields:

- `authorities`
- `risks`
- `acceptance_criteria`
- `test_requirements`
- `dispositions`
- `previous_tr_ids`
- `update_scope_tr_ids`

既存legacy promotion用 `legacy_tr_ids` の条件付き入力契約は維持します。

`acceptance_criteria[]` は§3.1のexact schemaを使用し、**current ACだけ**を含めます。blocked ACはknown current AC集合、Machine Entity、TRD closureの対象外です。`authority_refs[]` はtop-level `authorities[]` のknown IDへ存在検証します。ACなしworkflowでもkey省略は許可せず `[]` を明示します。

各 `test_requirements[]` draftへ `acceptance_refs[]` を必須追加します。該当ACがない横断的TRは `[]` を使用します。`acceptance_refs[]` の意味対応はLLMが判断し、generatorはtop-level known AC集合への存在参照だけを検証します。

## 7. requirement_structure-v2 deterministic processing

共通処理:

1. `acceptance_criteria[]` のschema / duplicate / canonical orderを検証し、各 `authority_refs[]` をtop-level `authorities[]` へ存在検証する
2. `test_requirements[].acceptance_refs[]` とAcceptance Criterion Dispositionのrefをknown AC集合へ存在検証する
3. closure universeへtop-level current ACを追加する
4. TR Entity contentへ `acceptance_refs[]` を保存する
5. AC linked + disposedの二重扱いを拒否する
6. linkedもdisposedもされないcurrent ACをunclosedとして拒否する
7. Authority / Product Risk / Acceptance Criteriaのclosure集合を別々に評価する。TRの `acceptance_refs[]` にACを追加しても、そのACのAuthorityをTR draftの `authority_refs[]` へ暗黙追加しない

artifact mode追加処理:

8. validated `metadata.upstream_entities` からcurrent Acceptance Criterion Entityを抽出し、top-level `acceptance_criteria[]` と `ac_id / authority_refs[]` がexact一致することを要求する
9. 各参照AC EntityをTR Entity `upstream_entity_dependencies[]` へ追加する
10. 各参照ACのcurrent Authority dependencyをTR Entity dependencyへ直接追加する
11. AC / Authority Entityが不足・不一致ならfail-closedする

direct mode追加処理:

8. upstream AC Entityの存在を必須にしない
9. 参照AC Entityが `metadata.upstream_entities` に実在する場合だけ、semantic `acceptance_criteria[]` の同一AC rowと `ac_id / authority_refs[]` 一致を検証したうえで、既存 `resolve_entity_dependencies(..., require_all=false)` と同じ方針でAC Entity dependencyへ追加する
10. top-level `acceptance_criteria[].authority_refs[]` だけを根拠にAC由来Authority dependencyを生成しない。TR自身の `authority_refs[]` による既存direct dependency解決を維持する

AC linkはACだけをclosureします。Authorityは従来どおりTR draftの `authority_refs[]` に明示linkされるか、Authority Dispositionへ入る必要があります。artifact modeのAC→Authority dependency展開はfreshnessのためであり、Authority closureを代理しません。direct modeではこの展開を行いません。

LLMはACとTRの意味上の対応、TRの分割 / 統合を判断します。scriptは対応関係の意味妥当性を決めません。
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
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

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
| current ACがblockedへ遷移しEntity集合から一時的に外れる | 関連TR missing dependency / stale。AC stable ID自体はretireせず、再current化時に同じIDを使う |
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

## 12. partial rerun

TRDの既存partial rerun contractを維持します。以下のAC semantic freshness regressionはartifact modeで固定します。direct modeでAC Entity dependencyが無いTRへ同じ保証を要求しません。

必須regression:

1. AC-001へ依存するTR-001が存在
2. AC-001が変更
3. TR-001が今回の `update_scope_tr_ids` 外
4. previous artifactからTR-001をcarry-forward
5. carry-forward TRが旧AC fingerprintを保持
6. current AC Entityとの不一致によりTR-001がstale
7. workflow completion不可

scope外であることを理由に、changed ACへ依存するTRをcurrent扱いしません。

## 13. qa-workflow / coverage-analysis integration

shared `_expected_entities()` がspec-analysis normalized inputからAuthority + AC expected identityを決定論導出します。

qa-workflow / coverage-analysisはcurrent Entity collectionへAC Entityが存在してもextra entity扱いしません。

coverage-analysisの既存traceability graph node typeへACを追加しません。AC→TRのmachine traceabilityはTR Entity dependencyとTRD closureで保証し、Authority / Risk / TR / TCN / CI / TCの既存coverage graphを不要に拡張しません。

## 14. repository tests

次を更新 / 追加します。

- PR #14後の9 Skill-local runtime_contract.py copies byte-identical
- active Machine Evidence template / fixtureが手書き擬似schemaを持たず、保持するfixtureはruntime-v2 / entity-state-v2 validatorでparse / validateできる
- generator contractの `-v1` をshared runtime v2へ誤って置換しない
- `acceptance_criterion` Machine Entity valid / unknown type regression
- shared canonicalization: `acceptance_refs` / `acceptance_criteria`
- spec-analysis expected Authority + **current ACだけ**のidentity。blocked ACをexpected Entityへ含めない
- AC-001 current → blocked → currentでstable IDを維持し、blocked期間はAC Entity / `acceptance_criteria[]` から除外、explicit retire時だけterminal retireする回帰
- 通常の非mode spec-analysis normalized inputで `acceptance_criteria` key省略を空集合として扱い、既存Authority expected Entityだけを維持
- qa-workflow expected / actual Entity exact match
- coverage-analysis current Entity parse compatibility
- requirement-structure-v2 valid / invalid schema
- requirement-structure-v2がtop-level `acceptance_criteria[]` をraw input必須とし、各rowの `ac_id / authority_refs[]` と各TRの `acceptance_refs[]` を検証すること。ACなしは `acceptance_criteria=[] / acceptance_refs=[]` を明示し、default補完adapter / shared runtime hookを追加しない
- artifact modeではsemantic `acceptance_criteria[]` とupstream Acceptance Criterion Entity集合をexact一致させ、AC Entity + AC Authority dependencyをTR freshnessへ追加する回帰
- direct modeではupstream AC Entityなしでもsemantic `acceptance_criteria[]` をknown ID集合として `acceptance_refs[]` / closureを検証でき、存在しないAC / AC由来Authority Machine Entity dependencyを合成しない回帰。AC Entityなしのdirect modeではAC本文 / 親chain変更のcross-run freshnessを保証しないことも契約化する。実在AC Entityをdependencyへ使う場合はsemantic rowとの `ac_id / authority_refs[]` 一致を要求し、そのEntity dependencyについて既存freshnessを利用できること
- AC-001をTRへlinkしても、そのACが参照するSPEC-001をTR authority_refs / Authority Dispositionで別途closeしない場合はSPEC-001 unclosedとなる
- TRD / TCD / TC Skill-local runtime_v1_cutover.pyのprojection、runtime-v1 / entity-state-v1以外の入力拒否、内容不変時stable ID保持、deleted / inactive identity history保持
- AC linked / disposed / unclosed / linked+disposed
- AC upstream skill/type mismatch
- artifact modeのAC dependency fingerprint propagation
- artifact modeでlinked UIOPの操作内容 / 対象構造変更によりAC本文 / 親chainが同じでもAC fingerprintが変わり関連TRがstaleになる回帰
- artifact modeでlinked UIOPだけが参照するAuthority contentを変更し、UIOP本文が同一でもAC Authority dependency / fingerprint変更から関連TRがstaleになる回帰
- artifact modeでAC / Behavior / UC / USの明示ref、linked UIOP target、linked domain itemから直接参照されるstructureと、そのancestor PAGE等のPath / 名称 / STATE軸を同一stable IDのまま変更するとAC fingerprintが変わる回帰
- artifact modeでAC chainから明示参照されたFIELD / RULE / FLOW / NOTIFY / INTERACTのcanonical内容変更でAC / TRがstaleになる回帰
- artifact modeでlinked INFのcanonical内容変更でAC / TRがstaleになる回帰
- artifact modeで同一PAGE / 同一Scopeに存在してもAC chainから明示参照されないdomain item変更ではAC / TRがstaleにならない回帰
- artifact modeでACが参照しない無関係structure / INF変更ではAC / TRがstaleにならない回帰
- parent_structure_idのmissing / self / cycleをrejectする回帰
- scopeの対象機能 / 領域またはscope Authority変更でAC fingerprint / dependencyが変わる回帰
- AC本文 / 親chain不変のままAuthority fingerprintだけ変更し、spec-analysisをcurrentへ再生成した後も未再実行TRが直接Authority dependencyによりstaleになる回帰
- artifact modeのpartial rerun stale carry-forward
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
- 9コピーがruntime-v2 / entity-state-v2へ同期され、requirement-structure-v2が明示される。TRD / TCD / TC固有cutover projectionはshared runtimeではなく各Skill-local helperにある
- helperからpackage-global spec-analysis evidence + ready / blocked scope ID indexと、current ready scope全件のcanonical batch handoffを別responseで決定論生成できる。package-global responseへscope別full payloadを複製しない
- qa-workflowが `inspect.ready_scope_ids[]` 全件をbatch inputにし、Authority / current AC / Machine Entity / expected identityをhelper側でunion / dedupeする。blocked scopeを含めず、Agentがmerge / filterしない
- batch handoffから構成する `artifact:analysis_entities:all` / `artifact:requirement_structure:all` のcanonical stdin全体を16 MiB境界で検証し、2 MiB超〜16 MiB以下を1回のaggregate root runtimeで処理できる。16 MiB超過時は個別scope run / subset run / silent truncate / auto splitで回避しない。その他の通常generatorは2 MiB上限を維持する
- test-requirement-designまで進むworkflowではcurrent ACがTRまたはDispositionへ完全に閉じる。仕様理解packageだけの要求ではこのclosureを要求しない
- UI target artifact workflowでは、AC / linked UIOP / scope / 明示linked FIELD-RULE-FLOW-NOTIFY-INTERACT / direct structure + ancestor / linked INF / 親Behavior-UC-US / Authority変更が必要なTR freshnessへ伝播し、無関係package row変更は伝播しない
- direct modeはknown AC ID / closureを保証し、AC Entity dependencyが無い場合のAC semantic cross-run freshnessを保証対象にしない
- 無関係TRを不必要にstale化しない
- artifact modeのpartial rerunでscope外TRがchanged ACを参照したままcurrentにならない
- existing coverage graphを目的なく拡張していない
