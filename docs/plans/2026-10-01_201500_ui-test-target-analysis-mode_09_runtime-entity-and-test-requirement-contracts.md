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

既存runtime設計では `runtime_contract_version` は意味契約変更時に更新し、Machine Entity schemaの意味変更は `entity-state-v1` 自体のversion変更として扱う契約です。今回の `acceptance_criterion` Entity type、`acceptance_refs` / `acceptance_criteria` canonicalization、spec-analysis expected Entity導出追加は両方の意味契約変更に該当します。

9コピーで次を同時更新します。

- `RUNTIME_CONTRACT_VERSION`: `runtime-v1` → `runtime-v2`
- `ENTITY_SCHEMA_VERSION`: `entity-state-v1` → `entity-state-v2`
- `ALLOWED_ENTITY_TYPES`: `acceptance_criterion` を追加

envelope field shapeとfreshness algorithmは維持します。v1 / v2を同時解釈するcompatibility branchは追加しません。旧runtime-v1 / entity-state-v1 evidenceはv2 current evidenceとして読み替えず、current scriptで再実行・再検証します。9コピーのruntime implementation fingerprintも既存契約どおり変わります。

cutover後、旧v1 artifactを通常の `previous_artifact_markdown` としてpartial rerun / freshness検証へ渡しません。TRD / TCD / test-case-designを含む既存runtime Skillは、最初のv2実行を `partial_rerun=false` + `previous_artifact_markdown=null` のfull rebuildとして行います。stable identity / mapping historyは§2.7の専用 `project_v1_cutover` がv1 Runtime Input / Resultから各v2 generatorへそのまま渡せるcomplete `normalized_runtime_inputs[]` へ埋め込みます。Agent / LLMがseed patchを元JSONへmergeしません。v2 artifactが成立した後だけ既存partial rerun契約へ戻します。

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

shared `runtime_contract.py` に専用operation `project_v1_cutover` を追加します。これはv1 evidenceをcurrent / freshとして受理するcompatibility runtimeではなく、v2初回full rebuild用の**完成済みscript input**を決定論生成するone-time projectionです。Agent / LLMがseedを元JSONへ再マージしません。

#### direct CLI dispatcher

`project_v1_cutover` は各generatorの通常CLIではなく、Skill-local `runtime_contract.py` のdirect CLIから実行します。9コピーで同じdispatcherを持ちます。

- `runtime_contract.py` direct CLIのoperationは `verify_runtime_evidence / project_v1_cutover` の2つだけを許可する
- `project_v1_cutover` の `skill` は `test-requirement-design / test-condition-design / test-case-design` だけを許可する。他6 Skillで指定した場合はhandled `unsupported` とする
- unknown operationを通常runtime requestへfallthroughさせず `invalid_input` で返す
- direct dispatcherは16 MiB aggregate stdinを許可する。通常generator `run_cli()` は従来どおり2 MiB上限を維持する
- strict JSON stringの64 KiB上限例外は、direct dispatcherで `verify_runtime_evidence / project_v1_cutover` の `artifact_markdown` を読む場合だけ許可する。その他field / operationへ例外を広げない
- 現行 `verify_runtime_evidence_cli()` は `runtime_contract_cli()` へ一般化し、既存verify response contractを変更しない

stdin:

```json
{
  "operation":"project_v1_cutover",
  "skill":"test-requirement-design",
  "artifact_markdown":"<runtime-v1 / entity-state-v1 artifact>"
}
```

response:

```json
{
  "valid":true,
  "operation":"project_v1_cutover",
  "skill":"test-requirement-design",
  "source_runtime_contract_version":"runtime-v1",
  "source_entity_schema_version":"entity-state-v1",
  "normalized_runtime_inputs":[
    {
      "generator":"requirement_structure",
      "runtime_unit_key":"artifact:requirement_structure:all",
      "model_key":null,
      "normalized_input":{}
    }
  ],
  "issues":[]
}
```

handled failureは `valid=false`、`issues[]` へ既存runtime verifierと同じissue contractで返します。

#### 共通projection規則

- artifact内のMachine Runtime Input / Result pairがruntime-v1で、Machine Entity blockがentity-state-v1であることを確認する
- `verify_runtime_evidence` と同じpair extraction / duplicate検出 / expected runtime unit builderを再利用し、missing / extra / incomplete / duplicate unitをblockedにする
- v1 Machine Entityのfingerprint / freshness / generation fingerprintをv2 current evidenceとしてcarry-forwardしない
- v1 Machine Runtime Inputに保存済みの**script固有normalized input**だけをsemantic input正本として使用する。Markdown本文をLLMが読み直してJSONを再構築しない
- v1 Runtime Resultに保存済みのidentity / mapping stateを、対応scriptのv2 input schemaへhelperが直接埋め込む
- `normalized_runtime_inputs[]` はcallerがそのまま各v2 generatorの `input` に渡せる完成形とし、caller / Agentがfield mergeしない
- metadata、upstream Entity / runtime dependency、fingerprintは返さない。callerがcurrent v2 Entity / current dispatch結果から既存fixed builderで新規生成する
- cutoverとsemantic redesignを同じrunで混在させない。v1 normalized semantic inputの意味fieldは変更せず、v2必須の互換fieldとidentity stateだけを追加する
- `normalized_runtime_inputs[]` は既存dispatch順でcanonical sortし、同じv1 artifactから同じ配列を返す

#### test-requirement-design

expected runtime unitはexactly 1件です。

- `artifact:requirement_structure:all`

v1 inputをrequirement-structure-v2へ変換し、次を含む**完全なnormalized input**を返します。

- v1 `authorities / risks / test_requirements / dispositions` をsemantic変更せず維持
- top-level `acceptance_criteria=[]` を追加
- 各既存 `test_requirements[]` に `acceptance_refs=[]` を追加
- v1 result `tr_id_state` を `previous_tr_ids[]` へ保存
- v1 input `test_requirements[].draft_key` とv1 result `tr_id_map[]` をexact joinし、current draftを `identity_action="reuse" / reuse_id=<mapped tr_id>` へ固定
- all active previous TR IDを `update_scope_tr_ids[]` へ入れ、first v2 runをfull rebuildにする
- `legacy_tr_ids` は使わない
- draft_key missing / duplicate / map missing / extra / duplicateをblockedにする

#### test-condition-design

v1 artifactからexpected runtime unit集合を既存fixed builderで導出します。

- rootはexactly 1件の `artifact:condition_structure:all`
- model runtime unitはv1 expected集合どおり。各unitのscript固有inputをcanonical copyし、runtime-v2 metadataで再実行する
- active TCNごとに `artifact:materialize_coverage:<TCN-ID>` をexactly 1件要求する
- materialize unitはruntime_unit_key末尾のTCN IDとinput / result内TCN IDの一致を要求する
- missing / extra / duplicate materialize unitをblockedにする

`normalized_runtime_inputs[]` にはcondition_structure、各model generator、各materialize_coverageの**完成済みv2 script input**を返します。

`condition_structure` input:

- v1 inputのsemantic fieldを維持
- resultの `tcn_id_state / model_key_state` を `previous_tcn_ids / previous_model_keys` へ設定
- input `test_conditions[].draft_key` ↔ result `tcn_id_map[]` をjoinし、current TCN draftをreuseへ固定
- input `models[].draft_key` ↔ result `model_key_map[]` をjoinし、current model draftをreuseへ固定
- all active TCN / modelをfull rebuild scopeへ入れる

`materialize_coverage:<TCN-ID>` input:

- v1 script inputのsemantic target / candidate fieldを維持
-同じunitのv1 resultから `target_mapping_state / semantic_ci_mapping_state / ci_id_state / expected_result_root_state` を、それぞれ `previous_target_id_map / previous_semantic_ci_map / previous_ci_ids / previous_expected_result_roots` へ設定
- deleted / inactive mappingをprevious stateへ残す
- input / result / runtime_unit_keyのTCN ID不一致をblockedにする

model generator inputにはstable identity patchを追加せず、v1のscript固有inputをcanonical copyしてcurrent v2 metadataで再実行します。

#### test-case-design

expected runtime unitはexactly 1件です。

- `artifact:case_structure:all`

v1 inputをcase-structureのcurrent schemaへcanonical copyし、次を反映した**完全なnormalized input**を返します。

- v1 result `tc_id_state` を `previous_tc_ids[]` へ設定
- v1 input `test_cases[].draft_key` ↔ result `tc_id_map[]` をexact joinし、current TC draftを `identity_action="reuse" / reuse_id=<mapped tc_id>` へ固定
- all active TCをfull rebuild scopeへ入れる
- draft_key / map missing / extra / duplicateをblockedにする

#### canonical cutover sequence

PR #14 merge後、既存v1成果物を持つworkflowは次の順だけを許可します。

1. v1 artifactを検出し、通常update / partial rerunへ入らない
2. spec-analysis / test-analysisのhuman semantic contentを変更せず、runtime-v2 / entity-state-v2のMachine Entity / runtime evidenceを再生成する
3. test-requirement-design v1 artifactへ `project_v1_cutover` を実行し、返却されたcomplete `normalized_runtime_inputs[]` をそのままcurrent v2 metadataでdispatchする。`partial_rerun=false / previous_artifact_markdown=null`
4. v2 TR artifactを保存する
5. test-condition-design v1 artifactへ `project_v1_cutover` を実行し、返却unitを既存dispatch順でcurrent v2 metadataにより再実行する。current v2 TR Entityをupstreamに使う
6. v2 TCD artifactを保存する
7. test-case-design v1 artifactへ `project_v1_cutover` を実行し、返却inputをcurrent v2 metadataでfull rebuildする。current v2 TCN / CI等をupstreamに使う
8. v2 TC artifactを保存する
9. coverage-analysis / qa-workflow / usability-inspection / wcag-conformance-evaluation等、generator-owned stable identity seedを持たないruntime evidenceをcurrent v2 upstreamから再生成する
10. v2 artifact群がvalidate / freshness / closureを通過した後だけ通常semantic update / partial rerunを許可する

このsequence中にLLMがv1 inputを編集しません。cutover helperのcomplete normalized inputをそのまま使うため、「cutoverとsemantic redesignを同じrunで混ぜない」を決定論的に守ります。

repository regression:

- direct CLIのverify / cutover dispatcher、unknown operation、supported skill境界
- 16 MiB artifact accepted / 1 byte超過blocked、64 KiB超artifact string accepted、通常generator 2 MiB上限維持
- v1以外のsource runtime / entity schemaをreject
- missing / extra / duplicate / incomplete runtime unitをreject
- semantic内容不変のcutoverでcurrent TR / TCN / model / CI / TC IDが不変
- deleted TR / TCN / model / CI / TC identityがcutover後も使用済み履歴として保持される
- inactive target / semantic CI mappingが失われない
- cutover後のnew identityが過去最大IDを再利用しない
- returned normalized_runtime_inputsだけでv2 generatorを実行でき、Agent-side mergeを必要としない
- v1 Entity fingerprint / generation fingerprintをv2 current evidenceとしてcarry-forwardしない

## 3. spec-analysis normalized machine input

`ui_target_package.py build-machine-evidence` はMarkdownから次を決定論的に生成します。

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

`authority_refs[]` はAC / Behavior / UC / US chain全体のstable refsを09のCurrent Effective Authority集合へ解決したunionです。current SPEC / DECISION / approved ASMだけを残し、INF / UNK / inactive Authorityは除外します。helperが重複除去・昇順canonical化し、current ACでは1件以上を要求します。0件ならACをcurrent Entity化せずUNKNOWNへ戻します。Agent / LLMが同じAuthority集合を再構築しません。

qa-workflow / coverage-analysisへspec-analysis scopeを渡す場合、AgentがMarkdownからこのJSONを再構築しません。helper返却のcanonical `normalized_skill_input` をそのまま使用します。

### 3.1 normal spec-analysis handoff adapter

UI target modeでは `build-machine-evidence.normalized_skill_input` が `acceptance_criteria[]` を必ず持ちます。通常の非mode spec-analysisは既存互換のためkey省略を許可しますが、requirement-structure-v2へ渡す時点ではqa-workflow / shared runtimeのdeterministic adapterがv2 shapeへ正規化します。

- spec-analysis normalized inputに `acceptance_criteria` がない場合だけ `acceptance_criteria=[]` を追加する
- fieldが存在する場合はarray型を要求し、意味を変更しない
- nonmode由来の既存TR draftに `acceptance_refs` がない場合だけ `acceptance_refs=[]` を追加する
- fieldが存在する場合はarray型を要求し、既存値を上書きしない
- adapterはACを生成せず、mode判定を行わない
- Agent / LLMに空array補完をさせない

このadapter後のshapeだけをrequirement-structure-v2へ渡します。

## 4. Acceptance Criterion Machine Entity

identity:

- skill: `spec-analysis`
- entity_type: `acceptance_criterion`
- entity_ref: `AC-xxx`

current ACだけをEntity化します。blocked ACを完成済みcurrent Entityへ変換しません。

### 4.1 canonical content

AC Entity contentには次を固定projectionします。

- `ac_id`
- `acceptance_criteria`
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
- `scope_id`
- `authority_refs[]`: AC / Behavior / UC / US chain全体のstable refsをCurrent Effective Authorityへ解決し、current SPEC / DECISION / approved ASMだけを残した1件以上のunionを重複除去して昇順
- `structure_refs[]`: AC / Behavior / UC / US chain全体の関連構造ID unionを重複除去して昇順

これによりAC本文が同じでも、親US / UC / Behaviorの意味変更でAC content fingerprintが変わります。

### 4.2 dependencies

AC Entityの `upstream_entity_dependencies[]` は、AC / Behavior / UC / US chain全体のstable refsからfilterしたcurrent SPEC / DECISION / approved ASM Authority Entity unionへ固定します。INF / UNKをdependencyへ追加しません。

US / UC / Behaviorをdependency Entityとして追加しません。親chain自体をAC contentへ含めることで、不要なglobal entity typeを増やさずfreshnessを成立させます。


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

`acceptance_criteria` row:

```json
{"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
```

`authority_refs[]` はspec-analysis helperが生成したcanonical値をそのまま渡します。

- artifact modeでは、同じ `AC-xxx` Machine Entityの `upstream_entity_dependencies[]` から得られるAuthority identity集合とexact一致を要求する
- direct modeでは、top-level `authorities[]` のknown ID集合へ存在検証する
- ACが存在しないworkflowでもfield自体を省略せず `acceptance_criteria: []` とする

各 `test_requirements[]` draftへ `acceptance_refs` を必須追加します。該当ACがない横断的TRは `[]` を使用します。

## 7. requirement_structure-v2 deterministic processing

scriptは次を行います。

1. AC ID形式 / duplicate / `authority_refs[]` を検証
2. artifact modeでは `spec-analysis / acceptance_criterion / AC-xxx` current Entityへ完全解決し、input `authority_refs[]` がAC EntityのAuthority dependency identity集合とexact一致することを検証
3. direct modeではinputのknown AC集合とknown Authority集合へ存在検証
4. TR draftの `acceptance_refs` を検証
5. linked upstream集合へ `acceptance_criterion` を追加
6. closure universeへcurrent ACを追加
7. TR Entity contentへ `acceptance_refs` を保存
8. artifact modeではTR Entity `upstream_entity_dependencies[]` へ参照current AC Entityを追加する。direct modeではcurrent Machine Entityがないためdependencyを捏造せず、`acceptance_refs[]` をcontentへ保持する
9. 各参照ACの `authority_refs[]` をunionする。artifact modeでは解決できたcurrent Authority EntityをTR Entity `upstream_entity_dependencies[]` へ直接追加する。direct modeではknown Authority ID検証とcontent保持までとし、Machine Entity dependencyは作らない
10. AC linked + disposedの二重扱いを拒否
11. linkedもdisposedもされないcurrent ACをunclosedとして拒否
12. Authority / Product Risk / Acceptance Criteriaのclosure集合を別々に評価する。TRの `acceptance_refs[]` にACを追加しても、そのACの `authority_refs[]` をAuthority linked集合へ暗黙追加しない

AC linkはACだけをclosureします。Authorityは従来どおりTR draftの `authority_refs[]` に明示linkされるか、Authority Dispositionへ入る必要があります。AC→Authority unionはfreshness dependencyを直接保持するための展開であり、Authority closureを代理しません。

Authority dependencyの展開はID集合・Entity解決だけを行う決定論処理です。どのAuthorityがACを支えるかはspec-analysisでLLMが判断済みであり、test-requirement-design側で意味を再判断しません。存在しないMachine Entityをdirect modeでplaceholder生成する経路は追加しません。

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

次をrepository runtime testで固定します。

| 変更 | 期待 |
| --- | --- |
| AC本文変更 | 関連TR stale |
| AC削除 | 関連TR missing dependency / stale |
| 親Behavior変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親UC変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親US変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| artifact modeでAuthority変更、AC本文・親chain同じ、spec-analysis再実行済み | TRが保持する直接Authority dependency不一致 → 関連TR stale |
| 無関係UC / AC変更 | 無関係TRはcurrent |

freshness判定アルゴリズム自体は既存 `evaluate_entity_freshness` を再利用し、新しい伝播engineを作りません。

## 12. partial rerun

TRDの既存partial rerun contractを維持します。

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
- spec-analysis expected Authority + AC identity
- 通常の非mode spec-analysis normalized inputで `acceptance_criteria` key省略を空集合として扱い、既存Authority expected Entityだけを維持
- qa-workflow expected / actual Entity exact match
- coverage-analysis current Entity parse compatibility
- requirement-structure-v2 valid / invalid schema
- AC-001をTRへlinkしても、そのACが参照するSPEC-001をTR authority_refs / Authority Dispositionで別途closeしない場合はSPEC-001 unclosedとなる
- project_v1_cutoverのskill別projection、runtime-v1 / entity-state-v1以外の入力拒否、内容不変時stable ID保持、deleted / inactive identity history保持
- AC linked / disposed / unclosed / linked+disposed
- AC upstream skill/type mismatch
- AC dependency fingerprint propagation
- AC本文 / 親chain不変のままAuthority fingerprintだけ変更し、spec-analysisをcurrentへ再生成した後も未再実行TRが直接Authority dependencyによりstaleになる回帰
- partial rerun stale carry-forward
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
- 9コピーがruntime-v2 / entity-state-v2へ同期され、requirement-structure-v2が明示される
- helperからspec-analysis normalized_skill_inputとAuthority + AC Entityを決定論生成できる
- qa-workflowがAuthority + ACをexpectedとして内部導出できる
- test-requirement-designまで進むworkflowではcurrent ACがTRまたはDispositionへ完全に閉じる。仕様理解packageだけの要求ではこのclosureを要求しない
- AC / 親Behavior / 親UC / 親US / Authority変更が必要なTR freshnessへ伝播する
- 無関係TRを不必要にstale化しない
- partial rerunでscope外TRがchanged ACを参照したままcurrentにならない
- existing coverage graphを目的なく拡張していない
