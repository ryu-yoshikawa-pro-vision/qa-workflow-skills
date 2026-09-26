# テスト分析・テスト技法の決定論的自動化Plan

このファイルはartifact処理とscript別入出力契約をまとめます。[generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md)および[追加generator](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md)と合わせて参照します。

## 19. テスト環境要求

### `test-analysis/scripts/environment_requirements.py`

構造化済み要求例:

- browser / version range
- OS / device class
- role / permission
- feature flag
- external integration
- locale / timezone requirement
- network / storage等の前提

対応constraint operatorは`test_data_requirements.py`と同じく、scalar equality、finite enum set、numeric / date / datetime range、version range、boolean requirementです。

各要求は`environment_key`を持ちます。同じ`environment_key`は1つの実行環境として同時成立が必要な要求集合、異なる`environment_key`は別の実行環境候補です。同じdimensionでも異なる`environment_key`間ではintersectionせず、Chrome用環境とSafari用環境等を矛盾扱いしません。同一`environment_key`内だけcross-operator intersectionで互換性を検査し、互換しない値を矛盾として返します。`requirement_key`は入力identityのまま維持し、複数requirementを別の新しいrequirement identityへ統合しません。

`test-case-design`は意味判断としてTCへ適用する`environment_key`を選び、そのkeyを選ぶ場合はcurrentな同keyのrequirement refsを一式渡します。複数`environment_key`を指定した場合は代替実行環境として扱い、相互にintersectionしません。`case_structure.py`は選択された各keyのrequirement集合がcurrentで完全か、各key内が互換かを検査します。どの環境をTCへ適用するか自体はruntimeが推測しません。

未対応operatorまたは安全にintersectionできない型組合せは`unsupported`とし、環境を実際に準備・検出しません。

## 20. 変更影響分析

### `change_impact.py`

`_02`で定義したnode / edge契約だけを使用します。

- changed nodeから許可edgeを探索する
- Authority / TR / TCN / CI / TC候補を重複除去する
- dangling edge / unknown nodeを検出する
- 意味上のedgeを新規推測しない

payloadの`paths[]`は各impacted nodeに対する**shortest impact pathを1本**だけ返します。探索中のvisitedはgraph全体で「一度見たnodeを永久に捨てる」集合にせず、shortest distanceとcanonical predecessorを管理します。同じ最短距離の候補が複数ある場合はedge key列、次にnode key列のUnicode code point辞書順で1本へ固定します。cycleはshortest distanceを改善しない再訪として打ち切ります。

出力はimpacted nodeをnode key順、pathを終点node key順でcanonical sortします。all simple pathsの列挙は行いません。

## 21. テスト要求の構造処理

### `requirement_structure.py`

LLMはTRの本文、テストレベル / 観測方法と、既存TRを再利用するか新規TRにするかを判断します。これらの意味fieldもruntime inputへそのまま渡し、structure scriptは内容を生成・要約せずschemaと構造だけを検査します。Dispositionのmachine schemaはstructure / traceabilityで共通して`{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`とし、`covered_by_entity`は不要なhandlingではnullです。既存ID再利用時は`reuse_id`、新規時は`new`を指定し、runtimeが最終TR IDを割り当てます。

LLM draft後に次を計算します。

- Authority / RiskがTRまたはDispositionのどちらか一方へ閉じるか
- unknown upstream ID
- linked + disposed重複
- 関連Product Riskからの最低優先度
- TRの指定優先度が最低優先度以上ならそのまま保持
- 指定優先度が最低優先度より低く`priority_override_reason`が空ならviolation
- 指定優先度が低くても`priority_override_reason`が非空ならoverrideとして保持し、runtimeが自動で優先度を書き換えない
- reuse指定のTR IDが直前成果物系列に存在し、同じIDを複数draftへ割り当てていないことを検証する
- new指定だけ既存最大TR番号+1から採番し、削除済みTR番号を再利用しない
- outputへactive / deletedを含む`tr_id_state[]`を返し、次回の`previous_tr_ids[]`の正本にする

TR本文、テストレベル / 観測方法、粒度、既存TRとの意味上の同一性は変更・推論しません。runtime outputと入力meaning fieldを固定builderでjoinし、`_02` §4.4のTR Machine Entityを作ります。

## 22. テストケースの構造処理

### `case_structure.py`

LLMはTCのタイトル / 目的、前提・手順・データ・expected result・事後状態 / 後処理と、既存TCを再利用するか新規TCにするかを判断します。これらの意味fieldもruntime inputへそのまま渡し、structure scriptは内容を生成せず構造・参照・優先度・expected result番号とAuthority対応を検査します。Dispositionは`requirement_structure.py`と同じ共通schemaを使用します。既存ID再利用時は`reuse_id`、新規時は`new`を指定し、runtimeが最終TC IDを割り当てます。

LLM draft後に次を計算します。

- TCN / CIがTCまたはDispositionへ閉じるか
- unknown upstream ID
- linked + disposed重複
- Coverage Itemから要求される最高優先度
- TCの指定優先度が要求優先度以上ならそのまま保持
- 指定優先度が要求より低く`priority_override_reason`が空ならviolation
- 指定優先度が低くても`priority_override_reason`が非空ならoverrideとして保持し、runtimeが自動で優先度を書き換えない
- 番号付きexpected resultとAuthority対応
- reuse指定のTC IDが直前成果物系列に存在し、同じIDを複数draftへ割り当てていないことを検証する
- new指定だけ既存最大TC番号+1から採番し、削除済みTC番号を再利用しない
- outputへactive / deletedを含む`tc_id_state[]`を返し、次回の`previous_tc_ids[]`の正本にする

具体的なタイトル / 目的、前提・操作・データ・expected result・事後状態 / 後処理、既存TCとの意味上の同一性は生成・推論しません。runtime outputと入力meaning fieldを固定builderでjoinし、`_02` §4.4のTC Machine Entityを作ります。

## 23. traceability

### `coverage-analysis/scripts/traceability.py`

対象はテスト設計です。

- Authority / Risk → TRまたはDisposition
- TR → TCNまたはDisposition
- TCN → CI → TC、または各層の既存Skill契約で許可されたDisposition
- CIなし契約のTCN → TCまたはDispositionは、そのTCNにactiveなCoverage所有modelが存在せず、既存Skill契約が明示的にCIなしを許可する場合だけ認める
- missing edge
- orphan
- unknown reference
- stale downstream

許可する直接edgeは`Authority→TR`、`Risk→TR`、`TR→TCN`、`TCN→CI`、`CI→TC`、条件付きのCIなし`TCN→TC`だけです。CIなし`TCN→TC`は当該TCNにactiveなCoverage所有modelが0件で、既存Skill契約が明示的に許可する場合だけ有効です。Coverage所有modelが1件でもあるTCNでは、current materialize runtime unitの`model_completion[]`とcurrent unsupported closureから各modelの完了を先に検査し、直接edgeをCoverage closureの代替にしません。別層を飛び越えるedgeや逆向きedgeをclosure根拠として数えません。Dispositionは既存各Skillのhandling集合と必要なreason / Authority条件を検証し、正常なDispositionをmissing扱いしません。

技法別Coverage数値は各技法scriptを正本とし、traceabilityで再計算しません。

## 24. 複数Coverage targetの扱い

CI単位の`merge_group`と、TCが複数CIを参照する意味判断を分離します。

`materialize_coverage.py`の`merge_group`は、同一TCN・同一`model_key`・同一`execution_fingerprint`・同一`expected_result_root`のtargetだけを対象にします。LLMはその範囲で`merge_group`を明示し、scriptは次を機械統合します。

- Covered Target Refs
- Authority refs
- Reference refs
- 優先度は既存規則の最高値
- 追加test data requirements

異なるmodel / 技法、異なるexecution、異なるexpected resultを同一CIへ統合しません。異なるCIを1つの詳細TCで検証できるかは`test-case-design`の意味判断に残し、成立する場合だけ1つのTC draftの`ci_refs[]`へ複数CIを明示します。runtimeはこのTC判断を`merge_group`へ逆変換しません。

## 25. script別入出力契約

次のkeyを全実装で固定します。hash由来のstable key componentは、指定したcanonical objectのSHA-256 full digestを`h<64 lowercase hex>`で表します。`target_ref`、各種`*_fingerprint`、static data version等のdigest専用fieldは`sha256:<64 lowercase hex>`で表します。stable key componentへ`sha256:<hex>`を埋め込みません。

| script | required input | stable result / target key | 主payload |
| --- | --- | --- | --- |
| `risk_matrix.py` | `scheme, risks[]` | `risk_id` | level、mapped priority |
| `technique_candidates.py` | 全signal、selection key | `selection_key` | candidates、undetermined、complete |
| `change_impact.py` | changed node、nodes、edges | `impact:<node_key>` | impacted nodes / paths |
| `environment_requirements.py` | requirements[] | `env:<requirement_key>` | normalized requirements / per-environment conflicts |
| `analysis_entities.py` | test-analysis意味field + current runtime result | `(entity_type, entity_ref)` | Machine Entity / expected identity |
| `requirement_structure.py` | authorities、risks、TR、Disposition、previous ID state | `violation:<type>:<entity_id>` | violations / derived priority / TR ID mapping |
| `condition_structure.py` | TCN、models、previous ID state | `violation:<type>:<entity_id>` | violations / TCN・model key mapping |
| `equivalence_partitions.py` | sets[] / partitions[] | `ep:<set_key>:<partition_key>` | representative / Coverage |
| `bva.py` | boundaries[] | `bva:<boundary_key>:<position>` | typed value / Coverage |
| `domain_testing.py` | partitions[] / borders[] | §5のpartition + border + relation別key | point / Coverage |
| `decision_table.py` | conditions、actions、known rules、constraints、accepted merges | `dt:h<assignment_hash>` | rule assignment / action vector / Coverage |
| `combinatorial.py` | mode、factors、constraints、strength | `comb:<mode>:h<target_hash>` | target tuple / rows / Coverage |
| `classification_tree.py` | classifications[] / classes[] / constraints[] / child_models[] | `class:<classification_key>:<class_key>` | factor skeleton / semantic_parameter_requests / derived_child_inputs |
| `state_transition.py` | states、transitions、reset、coverage mode、n-switch時switch_count | [基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §9のstate / transition / n-switch / round-trip / invalid key | setup / sequence / Coverage |
| `flow_paths.py` | nodes、edges、initial nodes、regions、loop specs、max path length、coverage mode | [追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §10のnode / edge / path / loop / branch key | paths / loops / branch Coverage |
| `crud_matrix.py` | matrix、consistency sequences、operation dispositions | [追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §11のoperation / missing / sequence key | completeness / consistency / anomalies |
| `cause_effect.py` | causes、effects、constraints、AST | `ce:h<cause_assignment_hash>` | Decision Table互換rules |
| `grammar_cases.py` | start、key付きproductions、max depth、mutations | `syntax:prod:<production_key>`、mutationは`syntax:mutation:<mutation_key>` | derivations / production Coverage |
| `schema_cases.py` | `schema_kind, document, schema_pointer, context` | `schema:h<source_hash>` | normalized constraints / downstream inputs / unsupported subtrees |
| `ui_pattern_candidates.py` | pattern / alias、attributes | `ui:<pattern_key>:<candidate_key>` | candidate / references |
| `test_data_requirements.py` | requirements[] | `data:<requirement_key>` | normalized requirements / applicable-scope conflicts |
| `random_testing.py` | seed、case count、distribution | `random:case:<1-based zero-padded 6 digits>` | generated input / completion |
| `metamorphic.py` | relations[] | [追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §18 key | follow-up input / completion |
| `case_structure.py` | TCN / CI / TC / Disposition | `violation:<type>:<entity_id>` | violations / derived priority |
| `traceability.py` | nodes / edges / dispositions / runtime units / Machine Entity state | `gap:<type>:<entity_id>` | gaps / orphan / stale / closed dispositions |
| `materialize_coverage.py` | TCN、generator targets、target annotations、previous mapping、merge groups | target ref → CI ID | CI mapping / stale / machine rows |
| `workflow_runtime.py` | runtime units、current Machine Entities / runtime units、unsupported item closure | `runtime_unit_key` | runtime / Entity freshness、stale propagation、completion blockers |

assignment / tuple / sequence / pathのhash対象はIDや表示文ではなく、そのtargetを定義するcanonical key/value構造だけです。hash collisionを検出した場合は`internal_error`として停止し、別targetを同一keyへ統合しません。

### 25.1 共通値schema

技法model内の業務値は、Pythonの型同一視へ依存しないよう次のtyped valueを使用します。

```json
{"type":"integer","value":1}
{"type":"boolean","value":true}
{"type":"string","value":"A"}
{"type":"enum","value":"admin"}
{"type":"decimal","value":"0.10"}
{"type":"null","value":null}
{"type":"date","value":"2026-09-19"}
{"type":"local_datetime","value":"2026-09-19T12:30:00"}
{"type":"fixed_offset_datetime","value":"2026-09-19T12:30:00+09:00"}
```

- integerはstrict JSON decodeで取得した専用number tokenをgrammar / raw length検証してからcanonical integerへ変換する。JSON stringの`"1"`と混同しない
- decimalはtyped valueでは符号付き10進文字列で指数表記を禁止し、共通exact helperで`integer coefficient + base-10 scale`へ正規化する。Python `Decimal` context precisionやbinary floatへ結果を依存させない
- raw numeric tokenとcanonical numeric representationはいずれも4096 chars上限。超過時は`limit_exceeded`とし、丸めない
- date / datetimeは`_02`のISO 8601契約へ従う
- enumとstringは同じ文字列でも別型として扱う
- nullは`value:null`だけを許可する
- assignmentのvalueはすべてtyped value

共通constraint:

```json
{
  "constraint_key":"C1",
  "assignment":{"role":{"type":"enum","value":"guest"}},
  "authority_refs":["SPEC-001"]
}
```

`assignment`は1件以上のfactor / condition keyを持つpartial assignmentです。

### 25.2 script固有input schema

以下で`required`に記載したfieldは必須、`optional`に記載したfieldだけ省略可能です。未知fieldは`invalid_input`です。配列内の`*_key` / IDは各配列内一意です。

#### `risk_matrix.py`

- required: `scheme`, `risks[]`
- `scheme.kind = repository-default | project-specific`
- repository-default: `scheme_key="risk-scheme-v1"`
- project-specific: [基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §1の`scheme_key / dimensions / matrix / priority_map`を必須
- `risks[]`: `{risk_id, impact, likelihood}`。impact / likelihoodはschemeで宣言したinteger value

#### `technique_candidates.py`

- required: `selection_key`, `signals`
- `selection_key`はstable result keyとして`_02` §3.2と同じ`^[A-Za-z][A-Za-z0-9._-]{0,64}$`を使用し、`:`を許可しない
- `signals`は§2で列挙した12 keyをすべて持ち、値は`true / false / null`
- signal以外の技法選択、`selection_source`、最終採用技法はこのscript入力に含めない

#### `change_impact.py`

- required: `changed_node_keys[]`, `nodes[]`, `edges[]`
- node: `{node_key, node_type, source_ref, change_kind, expected_impact}`。`change_kind`は既存`test-analysis`契約の`新規 / 変更 / 削除 / 回帰影響 / 参考`またはnull、`expected_impact`は非空文字列またはnullとする。探索順・到達判定には使わずMachine Entityへそのまま保持する
- `node_type = Authority | Risk | TR | TCN | CI | TC`
- edge: `{edge_key, from, to, edge_type, evidence_refs[]}`
- `edge_type = depends_on | traces_to | derived_from`
- changed nodeはnodesに存在必須

#### `environment_requirements.py` / `test_data_requirements.py`

- environment required: `requirements[]`
- test data required: `requirements[]`, `current_source_targets[]`
- `current_source_targets[]`: `{source_model_key, target_ref, target_content_fingerprint, generation_fingerprint}`。同一target identityの重複を拒否し、current generator resultから固定builderが作る
- requirement: `{requirement_key, environment_key, dimension_key, operator, authority_refs, source_model_key, source_target_versions}`。environmentでは`environment_key`をstable component keyとして必須、`source_model_key=null / source_target_versions=[]`。同じ`environment_key`の要求だけを同時成立対象とし、異なるkeyは代替環境としてcross-intersectionしない。test dataでは`environment_key=null`、current model keyを必須とし、model-wide requirementではcurrent adapter modelを許可、target-specific requirementではCoverage所有modelを必須にする
- `operator=eq`: `value` typed value必須
- `operator=enum`: `values[]` typed valueを1件以上、重複不可
- `operator=range`: `minimum / maximum` typed value、`minimum_inclusive / maximum_inclusive` boolean必須
- `operator=version_range`: `minimum / maximum` version文字列、inclusive boolean必須
- `operator=boolean`: `value` boolean必須
- `source_target_versions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint}`。environmentとmodel-wide test dataでは空配列を許可する。target-specific test dataでは1件以上必須とし、全rowが`current_source_targets[]`の同じ`source_model_key`へ完全一致しなければ`invalid_input`とする。model-wide test dataでは`current_source_targets[]`照合を要求せず、`source_model_key`のcurrent model metadata一致だけを必須にする。test dataの`source_model_key`がruntime generatorを持つmodelの場合、固定builderはそのcurrent model runtime unitを`upstream_runtime_units[]`へ必須で追加し、保存generation不一致をstaleとして扱う。別modelのtargetや古いversionを受理せず、modelを跨ぐtraceabilityへ`target_key`単独を使用しない
- `test_data_requirements.py`は異なる`requirement_key`を新しいidentityへmergeしない。model-wide要求は同じ`source_model_key`の各targetへ適用し、target-specific要求は`source_target_versions[]`で参照したtargetだけへ適用する。各current targetについて「同modelのmodel-wide要求 + そのtargetを参照するtarget-specific要求」の同一dimensionだけをintersectionし、互換性を検査する。互いに参照targetが重ならないtarget-specific要求同士はこの段階でintersectionしない
- `test_data_requirements.py`の各正規化済み要求は元の`requirement_key`を維持して`data_ref=data:<requirement_key>`を返し、`materialize_coverage.py`の`test_data_requirement_refs[]`はこの`data_ref`だけを参照する。複数targetを同一CIへmergeする場合はmerge対象targetの要求unionを、複数CIを同一TCへ入れる場合はそのTCが参照する要求unionを同じintersection関数で再検査する

#### `analysis_entities.py`

- required: `test_analysis_context`, `product_risks[]`, `technique_selections[]`, `change_nodes[]`, `change_edges[]`, `environment_requirements[]`, `risk_matrix_results[]`, `technique_candidate_results[]`
- `test_analysis_context`は`_02` §4.4のcontext contentと同じ意味fieldを持つ。canonical schemaは`{scope, objectives[], test_levels[], environment_constraints[], exclusions[], blockers[], test_focus_items[], testability_decisions[], residual_risks[], authority_refs[], risk_refs[]}`。`authority_refs[]`は実際に参照したAuthority Machine Entityの`entity_ref`、`risk_refs[]`は実際に参照したProduct Riskの`risk_id`。両配列は文字列・重複不可・昇順canonical。自然言語fieldから参照を推測しない
- `risk_matrix_results[]`はcurrent `risk_matrix.py` payloadの`risks[]`を固定抽出した`{risk_id, level, mapped_priority}`だけを受ける。Product Risk draftは`{risk_id, failure, source_refs[], authority_refs[], impact, likelihood, assessment_reason, confidence_note}`。各`risk_id`は入力内一意で、result rowと1対1でjoinする。missing / duplicate / unknown resultを`invalid_input`にする
- `technique_candidate_results[]`はcurrent `technique_candidates.py` payloadから固定抽出した`{selection_key, candidates[], undetermined_signals[]}`だけを受ける。Technique Selection draftは`{selection_key, applicability_scope, selection_source, signals, selected_techniques[], selection_reason, risk_refs[], authority_refs[], condition_design_focus[], undetermined_signal_closures[], status}`。closure rowは`{signal_key, handling, reason, question_id}`で、current result rowの`undetermined_signals[]`とsignal key集合を完全一致させる
- closureの`handling`は`selection_not_affected|question`だけを許可する。`selection_not_affected`は非空`reason / question_id=null`、`question`は`question_id=Q-\d{3}`を必須とする。`status=active`では全current `undetermined_signals[]`が`selection_not_affected`で閉じていることを必須にし、`question` closureがあれば`status=blocked|unresolved`にする。signal自体を解決した場合は`signals`をbooleanへ更新しcandidate runtimeを再実行する
- change node / edgeは`_02` §4.4の`change_kind / expected_impact / evidence_refs[]`を含むcontent schemaをそのまま使う
- `environment_requirements[]`はcurrent `environment_requirements.py` resultから固定builderが渡す正規化済み要求で、同runtime unitを`upstream_runtime_units[]`へ保持する
- `analysis_entities.py`は同じtest-analysis実行でdispatchされたcurrent `risk_matrix.py / technique_candidates.py / change_impact.py / environment_requirements.py`をすべて`upstream_runtime_units[]`へ保持する。条件付きscriptが未dispatchなら依存を捏造しない。change impact resultはchange graph contentの正本にはせず、別runtime resultとして保存する
- 同一invocation内のEntity生成順は、(1) change graph / environment requirement、(2) Product Risk、(3) Technique Selection / test-analysis contextで固定する。後段Entityが前段Entityをsemantic dependencyとして参照する場合は、同じ実行で確定した前段Entityのcanonical content fingerprintを使用する
- contextの`authority_refs[]`はartifact modeでcurrent Authority Machine Entityへ完全解決し、unknown / missing参照を`invalid_input`にする。direct modeでも全refを実際に渡されたcurrent Authority Machine Entityへ解決し、そのEntityだけをdependencyへ含める。unknown refは`invalid_input`とし、Entityを合成しない。`risk_refs[]`は同一invocationで生成したProduct Riskへ完全解決し、同Entityのcurrent canonical `content_fingerprint`を使用する。unknown risk / duplicate refは`invalid_input`にする。callerからdependency fingerprintを受け取らない
- change graph内のRisk / TR / TCN / CI / TC nodeは構造参照であり、それら下流QA Entityへのdependencyを自動追加しない。これによりProduct Riskがchange graphを参照してもdependency cycleを作らない
- outputはcanonical sort済み`machine_entities[]`と`expected_entity_identities[]`。expected identityはdraft / normalized resultのidentity sourceから導出し、生成済み`machine_entities[]`の存在から逆算しない
- Machine Entity wrapper / content fingerprint / dependencyは`runtime_contract.py`の共通builderで生成し、LLMがJSONを再構築しない

#### `requirement_structure.py`

- required: `authorities[]`, `risks[]`, `test_requirements[]`, `dispositions[]`, `previous_tr_ids[]`, `update_scope_tr_ids[]`
- optional: `legacy_tr_ids[]`。初回legacy昇格時だけ使用し、`input_mode=direct / previous_tr_ids=[]`を必須にする。各値は一意な`TR-\d{3}`で、`runtime_contract.py`のlegacy ID seed helperが`{tr_id,status:"active"}`へ変換してから通常処理へ入る。normal previous stateと併用した場合は`invalid_input`
- TR draft: `{draft_key, identity_action, reuse_id, text, authority_refs[], risk_refs[], priority, priority_override_reason, test_level, observation_method}`
- `draft_key`は入力内一意、`identity_action=reuse|new`。reuse時だけactiveな既存`TR-\d{3}`を`reuse_id`へ指定し、new時は`reuse_id=null`
- `previous_tr_ids[]`: `{tr_id, status}`、`status=active|deleted`の成果物系列full snapshot
- `update_scope_tr_ids[]`は今回の実行でlifecycleを確定するprevious active TRだけを重複なしで列挙する。unknown / deleted IDを拒否する
- canonicalized `test_requirements[]`を`draft_key`順で処理し、複数new TRへその順で採番する
- reuse対象は`update_scope_tr_ids[]`内のactive IDに限定し、不存在 / deleted / scope外 / 同一IDのduplicate reuseを`invalid_input`にする。new採番はscope外も含むprevious full snapshotの過去最大番号+1。999超過は`id_space_exhausted`
- `update_scope_tr_ids[]`内のprevious active TRだけ、currentでreuseされなければ`deleted`へ遷移する。scope外のactive / deleted rowは状態を変更せず保持する
- `priority_override_reason`は関連Riskから導出した最低優先度より低くする場合だけ非空必須で、runtimeが意味判断として優先度を自動補正しない
- dispositionは`{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`を使う
- outputは`tr_id_map[]: {draft_key, tr_id, identity_action}`とactive / deleted全行を含むfull snapshotの`tr_id_state[]`

#### `condition_structure.py`

- required: `test_requirements[]`, `technique_selections[]`, `test_conditions[]`, `requirement_dispositions[]`, `models[]`, `previous_tcn_ids[]`, `previous_model_keys[]`, `update_scope_tcn_ids[]`, `update_scope_model_keys[]`
- optional: `legacy_tcn_ids[]`。初回legacy昇格時だけ使用し、`input_mode=direct / previous_tcn_ids=[] / previous_model_keys=[]`を必須にする。各値は一意な`TCN-\d{3}`で、helperがactive previous TCN stateへseedする。legacyにmodel keyがない場合はmodel stateを捏造せずcurrent model draftをnew採番する。normal previous stateと併用した場合は`invalid_input`
- TR: `{tr_id, priority, authority_refs[], risk_refs[]}`。各`tr_id`は入力内一意
- Technique Selection: `{selection_key, selected_techniques[], undetermined_signal_closures[], status}`。`selection_key`は入力内一意、`selected_techniques[]`はcanonical technique slugで重複不可。`status=active`だけmodel閉鎖の対象にし、activeではcurrent undetermined signalがすべて`selection_not_affected`で閉じ、`question` closureが0件であることを必須にする
- TCN draft: `{draft_key, identity_action, reuse_id, tr_refs[], condition, category, technique_slugs[], coverage_criterion, authority_refs[], risk_refs[], priority, priority_override_reason}`。`draft_key`は入力内一意、`condition / coverage_criterion`は非空文字列、`category`は文字列またはnull、`technique_slugs[]`は`_02` §4.3のcanonical technique slugだけを許可し重複不可。意味上の同一性はLLMが`identity_action=reuse|new`で決め、reuse時だけactiveな既存`TCN-\d{3}`を`reuse_id`へ指定する
- requirement dispositionは`_02`の共通Disposition schemaを使用する
- 各current TRはTCNの`tr_refs[]`またはrequirement dispositionのどちらか一方へ閉じる。unknown TR、linked + disposed重複、未閉鎖TRをviolationにする
- TCNの既定priorityは関連TRの最高優先度。より低いpriorityを指定する場合だけ非空`priority_override_reason`を必須にし、runtimeが自動補正しない
- model draft: `{draft_key, model_type, technique_slug, selection_source, selection_key, derived_from_model_draft_key, identity_action, reuse_model_key, parent_tcn_draft_key}`。`model_type`は`_02` §4.3の内部model type。adapterでは`technique_slug / selection_source / selection_key=null`、Coverage所有modelではcanonical `technique_slug`と`selection_source=analysis|condition_design|user`を必須とする。`selection_source=analysis`だけ`selection_key`必須、その他はnull
- `previous_tcn_ids[]`: `{tcn_id, status}`、`previous_model_keys[]`: `{model_key, model_type, technique_slug, parent_tcn_id, selection_source, selection_key, derived_from_model_key, status}`。`status=active|deleted`の成果物系列full snapshot
- `update_scope_tcn_ids[] / update_scope_model_keys[]`は今回lifecycleを確定するprevious active TCN / modelだけを列挙する。unknown / deletedを拒否し、reuse対象は対応scope内のactive ID / keyに限定する。full rebuildでは全previous active TCN / modelをscopeへ含める
- runtimeはreuse対象の存在、status、duplicate reuse、`model_type / technique_slug / selection_source / selection_key / derived_from_model_key`、最終親TCN一致を検証する。reuse modelを別TCNへ移さない。`derived_from_model_draft_key`は同じTCN draft配下のadapter draftだけを許可し、確定後の`derived_from_model_key`へ一意変換する
- TCN draftはcanonical `draft_key`順、model draftは`(parent_tcn_draft_key, model_type, draft_key)`順でnew IDを割り当てる。raw入力順を採番へ使わない
- 1つのmodel keyは同時に1つのTCNだけへ所属する。`update_scope_tcn_ids[] / update_scope_model_keys[]`内のprevious active TCN / modelだけ、currentにreuseされなければdeletedへ遷移する。scope外のactive / deleted rowは状態を変更せずfull snapshotへ保持する
- 各TCN draftの`technique_slugs[]`は、そのTCNを`parent_tcn_draft_key`に持つcurrent Coverage所有model draftの非null `technique_slug`集合と完全一致させる。`model_type`を集合へ入れずadapterはTCNの適用技法を増やさない
- Classification Tree / Cause-Effect / schema / UI等のadapterはcanonical techniqueを所有しない。Coverageを実際に所有するchild modelが`technique_slug / selection_source / selection_key`を持つ
- adapter派生childのmodel metadataは親adapter実行前に確定するが、child generatorのdispatch / `expected_runtime_units[]`追加は親adapter runtimeがcurrent `result_status=ready`となり、当該child向け`derived_child_inputs[]`がちょうど1件得られた後だけ行う。親adapterがunresolved / blocked / staleの間はchild runtime missingを別blockerとして重複計上しない
- `selection_source=analysis`のCoverage所有modelは参照Technique Selectionに同じ`technique_slug`が存在必須。1つの`selection_key + technique_slug`から複数TCN / modelへ展開してよい
- active Technique Selectionの`selected_techniques[]`に残る各技法は、少なくとも1件のcurrent Coverage所有modelへ到達必須。後から不適用 / 未解決と判断した場合はTechnique Selection Entity自体を更新してselected listから外すか既存block / unresolvedへ戻し、未定義のselection closureで閉じない
- `model_type=error-guessing / technique_slug=error-guessing`はmodel metadataを作るがgenerator runtime unitを期待集合へ追加しない。semantic Coverage Itemを1件以上のcurrent CIへmaterializeするまで完了不可
- outputは`tcn_id_map[]: {draft_key, tcn_id, identity_action}`、`model_key_map[]: {draft_key, model_key, model_type, technique_slug, parent_tcn_id, derived_from_model_key, identity_action}`、full snapshotの`tcn_id_state[]`、`model_key_state[]`を返す
- 固定builderはTCN draftの意味field（`priority_override_reason`を含む）と最終TCN IDをjoinしてTCN Machine Entityを、model draftの`model_type / technique_slug / selection_source / selection_key / derived_from_model_draft_key`と最終model key / parent TCN / `derived_from_model_key`をjoinしてmodel metadata Entityを生成する。LLMがMachine Entity JSONを再生成しない
- TCN / modelは同一`condition_structure.py` invocationで生成するため、model metadataの親TCNと`derived_from_model_key`のadapter modelは入力`upstream_entities[]`へ事前要求しない。TCN Entityを先に、adapter modelをchild modelより先に固定生成し、そのcurrent content fingerprintをmodel Entityの`upstream_entity_dependencies[]`へ設定する
- 999到達後の新規TCNは`id_space_exhausted`。model keyは3桁以上を許可し999上限を設けない

#### `equivalence_partitions.py`

- required: `sets[]`
- set: `{set_key, label, partitions[]}`。`label`は非空文字列
- partition: `{partition_key, label, validity, definition, representative, authority_refs}`。`label`は非空文字列
- `validity = valid | invalid`
- `definition.type=enum`: `values[]` typed valueを1件以上
- `definition.type=range`: `minimum / maximum / minimum_inclusive / maximum_inclusive`
- `representative`はtyped valueまたはnull。nullならscriptが一意に選べるenum / numeric rangeだけ自動生成

#### `bva.py`

- required: `boundaries[]`
- boundary: `{boundary_key, label, side, threshold, inclusive, step, mode, coverage_selection_reason, authority_refs}`。`label`は非空文字列
- `side=lower|upper`, `mode=2-value|3-value`。`mode=3-value`では境界リスク、過去不具合、ユーザー明示等の具体的な`coverage_selection_reason`を非空必須とし、2-valueでは空文字を許可する
- `threshold`はtyped integer / decimal / date / local_datetime / fixed_offset_datetime
- `step`は§4のdomain別object形式だけを許可し、threshold型と互換であることを必須にする

#### `domain_testing.py`

- required: `partitions[]`, `borders[]`
- partition: `{partition_key, label, dimensions[], expression, authority_refs}`。`label`は非空文字列、`dimensions[]`は`{dimension_key,label}`を1件以上持ち、expressionは§5の`border_ref / and / or` ASTだけ
- borderは§5の`border_key / label / partition_key / relation / coefficients / constant / pivot_key / anchor / pivot_step / authority_refs`だけ。`label`は非空文字列、coefficient / anchorのdimension keyは同partitionの`dimensions[]`へ解決必須
- coefficient / constant / pivot_stepはdecimal文字列
- anchor valueはtyped integer / decimalだけ
- 各borderは同じ`partition_key`のpartition expressionから1回以上参照されること

#### `decision_table.py`

- required: `conditions[]`, `actions[]`, `known_rules[]`, `constraints[]`, `accepted_merges[]`
- condition: `{condition_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- action: `{action_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- known rule: `{rule_key, when, then, authority_refs}`。`when`は全condition keyを1回ずつ、`then`は全action keyを1回ずつ持つ
- constraintsは共通partial assignment
- accepted mergeは§6.1形式

#### `combinatorial.py`

- required: `mode`, `factors[]`, `constraints[]`
- factor: `{factor_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- `mode=exhaustive`: 追加fieldなし
- `mode=base-choice`: `base_assignment`を全factorについて必須
- `mode=t-wise`: `strength` integerを2..factor数で必須。`strength>2`では`coverage_selection_reason`を非空必須
- `mode=mixed-strength`: `global_strength` integerを2..factor数、`subsets[]`を1件以上必須。subsetは`factor_keys[]`と`strength`を持ち、strengthは2..subset factor数。globalまたはsubsetのいずれかがstrength>2なら`coverage_selection_reason`を非空必須

#### adapter共通child契約

`classification_tree.py / cause_effect.py / schema_cases.py`は、`condition_structure.py`で先に確定したchild identityだけを受けます。

- `child_models[]`: `{child_model_key, model_type, derived_from_model_key, semantic_parameters}`。`child_model_key`は入力内一意、`derived_from_model_key`はadapter runtimeの共通metadata `model_key`と完全一致必須
- adapterごとに許可した`model_type`以外は`invalid_input`。unknown child、duplicate child、自己parent不一致を拒否する
- 意味parameterが不足する場合は`semantic_parameter_requests[]: {child_model_key, model_type, source_key, required_fields[]}`をstable sortして返し、`result_status=unresolved`にする。`source_key`はboundary / factor group等のstable machine keyで、自由文をidentityにしない
- `result_status=ready`では`semantic_parameter_requests=[]`かつ各`child_models[]`にちょうど1件の`derived_child_inputs[]: {child_model_key, model_type, input}`を返す。`input`は対応child generatorのscript固有inputと直接互換にする
- child generatorは`derived_child_inputs[].input`を変更せず使用し、adapterのcurrent generationを`upstream_runtime_units[]`へ保持する

#### `classification_tree.py`

- required: `classifications[]`, `constraints[]`, `child_models[]`
- `child_models[]`は1件だけで`model_type=comb`必須
- classification: `{classification_key, label, classes[], authority_refs}`。`label`は非空文字列
- class: `{class_key, value, authority_refs}`。valueはtyped value
- 同一classificationのclass valueは重複不可
- `semantic_parameters`はnullまたは`combinatorial.py`の戦略field `{mode, strength, global_strength, subsets, base_assignment, coverage_selection_reason}`。mode別に不要なfieldは拒否する
- strategy未確定ならfactor key集合を`source_key`として`semantic_parameter_requests[]`を返す。確定後は`derived_child_inputs[].input`を`combinatorial.py` inputと完全互換にする

#### `state_transition.py`

- required: `states[]`, `initial_states[]`, `terminal_states[]`, `transitions[]`, `reset_options[]`, `invalid_transition_candidates[]`, `coverage_mode`
- optional: `switch_count`, `coverage_selection_reason`。`coverage_mode=n-switch`だけ`switch_count`必須、`switch_count>=2`では`coverage_selection_reason`を非空必須
- state: `{state_key, label, authority_refs}`。`label`は非空文字列
- transition: `{transition_key, from, event, guard_status, guard_refs, to, authority_refs}`
- `guard_status=true|false|null`
- resetは[基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §9形式で`action`を非空文字列必須とする
- coverage mode: `all-states | valid-transitions | n-switch | round-trip | invalid-transitions`
- `switch_count`はinteger 0..10
- n-switch / round-tripのtarget定義とcanonicalizationは[基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §9を正本とする
- invalid candidateは[基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §9形式

#### `flow_paths.py`

- required: `nodes[]`, `edges[]`, `initial_node_keys[]`, `regions[]`, `loop_specs[]`, `coverage_mode`, `max_path_length`
- node: `{node_key, label, kind, authority_refs}`。`label`は非空文字列、kindは`normal / fork / join / terminal`
- edge: `{edge_key, from, to, guard_status, guard_refs, label, authority_refs}`
- region: `{region_key, fork_node_key, join_node_key, branches[]}`。branchは`{branch_key, edge_keys[]}`
- loop spec: `{loop_key, entry_node_key, edge_keys[], exit_edge_keys[], typical_iterations, maximum_iterations, authority_refs}`
- `initial_node_keys[]`は1件以上
- `coverage_mode = node | edge | bounded-path | simple-loop | fork-join`
- `max_path_length`は1..1000
- region / loopの連続性・nest・iteration規則は[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §10を正本とする

#### `crud_matrix.py`

- required: `entities[]`, `functions[]`, `cells[]`, `consistency_sequences[]`, `operation_dispositions[]`
- entity: `{entity_key, label, authority_refs}`。`label`は非空文字列
- function: `{function_key, label, authority_refs}`。`label`は非空文字列
- cell: `{entity_key, function_key, operations[], authority_refs}`。operationsは`C/R/U/D`の重複なし集合
- consistency sequenceは[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §11形式
- 個々の空cellは欠陥・N/Aを意味しないため専用`excluded_cells[]`を持たない。entity全体でoperationが存在しない場合だけ`operation_dispositions[]`で扱う
- operation disposition: `{entity_key, operation, handling, reason, authority_refs}`。`handling=not_applicable`、Authority 1件以上

#### `cause_effect.py`

- required: `causes[]`, `effects[]`, `constraints[]`, `child_models[]`
- `child_models[]`は1件だけで`model_type=decision / semantic_parameters=null`必須
- cause: `{cause_key, label, authority_refs}`。`label`は非空文字列
- effect: `{effect_key, label, expression, true_value, false_value, authority_refs}`。`label`は非空文字列
- expression ASTは`{"op":"ref","key":"C1"}`、`{"op":"not","arg":...}`、`{"op":"and|or","args":[...,...]}`だけ
- refはcause keyだけを許可し、effect参照は禁止
- true / false valueはtyped value
- constraintは§25.1の共通partial assignmentで、assignment keyはcause keyだけを許可する。valid inputでは`semantic_parameter_requests=[]`とし、`derived_child_inputs[].input`へDecision Table互換の`conditions / actions / known_rules / constraints / accepted_merges=[]`を返す

#### `grammar_cases.py`

- required: `input_label`, `start`, `productions[]`, `max_depth`, `mutations[]`
- `input_label`は生成文字列を適用する入力対象を第三者が識別できる非空文字列
- productionは`{production_key,lhs,rhs[]}`。RHS itemは`{"terminal":"..."}`または`{"nonterminal":"..."}`のどちらか一方で、`rhs=[]`をepsilonとして許可する
- `max_depth`は1..64のparse tree depth上限でroot start symbolをdepth 0とする
- derivationはleftmost固定。各production targetは対象productionを1回以上含むproduction適用回数最小のderivation、同数ならproduction key列辞書順
- valid case集合は各production shortest derivationのunionで、生成文字列 + production key列が同一なら重複除去
- mutation: `{mutation_key, op, production_key, symbol_index, value}`。opは`delete_terminal / replace_terminal / insert_terminal`
- deleteではvalue禁止、replace / insertではvalue string必須
- delete / replaceは`symbol_index`がterminal itemを指すこと、insertは0..len(rhs)を許可
- mutation後もleftmost / depth / shortest tie-breakを適用し、対象productionを含む導出がなければ`unreachable_mutation`
- stable targetはproduction `syntax:prod:<production_key>`、mutation `syntax:mutation:<mutation_key>`

#### `schema_cases.py`

- required: `schema_kind`, `document`, `schema_pointer`, `context`, `child_models[]`
- `child_models[]`の`model_type`は`ep / bva / comb`だけを許可する。同じmodel typeを複数childへ使う場合も`child_model_key`ごとに別rowとして扱う
- `ep`の`semantic_parameters`はnull固定
- `bva`の`semantic_parameters`はnullまたは`boundaries[]: {boundary_key, mode, coverage_selection_reason}`。生成skeletonの全boundary keyを1回ずつ指定し、unknown / missing / duplicate boundaryを拒否する
- `comb`の`semantic_parameters`はnullまたは`combinatorial.py`の戦略field `{mode, strength, global_strength, subsets, base_assignment, coverage_selection_reason}`。factor keyはschema解析結果へ解決必須
- selected childに適用可能なskeletonが0件なら`issue_type=selected_technique_not_derivable / blocking=true`を返す。`selection_source=analysis`なら`route_to=test-analysis`、`condition_design`なら`route_to=test-condition-design`、`user`なら`route_to=question-analysis / resume_skill=test-condition-design`とする
- BVA / combinatorialの意味parameter不足時はstable boundary / factor keyを`semantic_parameter_requests[]`へ返す。要求が0件になったready実行だけ`derived_child_inputs[]`を返す
- arbitrary JSON Pointerやproperty名をstable component keyへ直接埋め込まない。`source_digest`は`canonical JSON({schema_kind,schema_pointer,keyword,role})`のSHA-256 64桁lowercase hexとし、schema targetは`schema:h<source_digest>`を使う。下流へ渡す`set_key / partition_key / boundary_key / factor_key / requirement_key`は同じsource objectへ用途`role`を加えたfull digestから`_02` §3.2の`h` + 64 hex component keyを固定生成する。元pointer / keyword / full digestもpayloadへ保持する
- `schema_kind = json-schema-2020-12 | openapi-3.0 | html-control`
- numberは共通strict JSONの専用number tokenからcanonical integer / exact `coefficient + scale`へ正規化し、binary float / `Decimal` contextへ依存しない
- JSON Schema 2020-12ではroot `$id`だけmetadataとして許可し、nested `$id`、`$anchor / $dynamicAnchor / $dynamicRef`、外部URI referenceはruntime-v1 `unsupported`。対応`$ref`は同一schema resource内の`#/...`だけ
- JSON Schema 2020-12の`$ref` siblingは対応keywordなら通常どおり評価し、`$ref`だけを見てsiblingsを捨てない
- OpenAPI 3.0はJSON Schema 2020-12と別semanticsで、`nullable`、boolean exclusive boundary、`readOnly / writeOnly`、Reference Objectを[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §14どおり処理する
- OpenAPI Reference Objectは`$ref`以外の追加propertyを仕様どおり無視し、sibling Schema assertionとして解釈しない
- `enum / const`はscalar / nullだけruntime-v1対応。object / array値を含むsubtreeはunsupported itemへ出す
- `context`はJSON Schemaでは`validation`、OpenAPIでは`request|response`、HTMLでは`form-control`
- html-control `document`は`{type, required, min, max, minlength, maxlength, step, value, pattern, disabled, readonly, multiple}`。numberのdefault step=1、`step=any`、step base=min→value→0を[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §14どおり扱う
- `pattern`等の未対応constraintを無視してcompleteにせず、validation意味へ影響するsubtreeを`unsupported`
- `multipleOf`と対応可能なnumber `step`は[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §14の`grid` constraintへ正規化する
- annotation allowlistとunsupported subtree規則は[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §14を正本とする

#### `ui_pattern_candidates.py`

- required: `pattern`, `attributes`
- `pattern`はcatalog正規名またはalias
- `attributes`は`type / role / required / min / max / minlength / maxlength / step / disabled / readonly / multiple`だけを許可
- catalogにないpatternは`unsupported`

#### `random_testing.py`

- required: `input_label`, `seed`, `case_count`, `distribution`
- `input_label`は生成値を適用する入力対象を第三者が識別できる非空文字列
- distributionは[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §17の3 schemaのいずれか一つ

#### `metamorphic.py`

- required: `relations[]`
- relationは[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §18形式に`relation_label`を加え、`relation_label`を非空必須とする。`expected_relation.output_path / output_kind`も必須
- `source_id`はrelation内一意
- `follow_ups[]`は1..10,000件で`follow_up_key`をrelation内一意
- 各follow-upの`transforms[]`は1件以上で宣言順に適用する

#### `case_structure.py`

- required: `test_conditions[]`, `coverage_items[]`, `environment_requirements[]`, `test_data_requirements[]`, `test_cases[]`, `dispositions[]`, `previous_tc_ids[]`, `update_scope_tc_ids[]`
- optional: `legacy_tc_ids[]`。初回legacy昇格時だけ使用し、`input_mode=direct / previous_tc_ids=[]`を必須にする。各値は一意な`TC-\d{3}`で、helperがactive previous TC stateへseedする。normal previous stateと併用した場合は`invalid_input`
- TCN: `{tcn_id, tr_refs[], priority}`
- CI: `{ci_id, tcn_id, model_key, priority, authority_refs[], source_kind, execution, semantic_item_key, semantic_item_text, semantic_source_targets[], test_data_requirement_refs[]}`
- environment / test data requirementはcurrent Machine Entityのcanonical contentとcontent fingerprintを渡す
- TC draft: `{draft_key, identity_action, reuse_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], environment_requirement_refs[], test_data_requirement_refs[], priority, priority_override_reason, preconditions[], test_data[], steps[], expected_results[], postconditions_or_cleanup[]}`
- TC draftの`preconditions[] / test_data[] / steps[] / expected_results[] / postconditions_or_cleanup[]`へpassword、token、cookie、secret値そのものを保存しない。認証が必要な場合は取得方法、環境変数名等の値を含まない参照だけを記述する。`case_structure.py`へ汎用secret scannerは追加せず、Agent / LLMの意味正規化とscript固有schemaでsecret値をmachine evidenceへ持ち込まない境界を維持する
- stepは`{number,text}`で1から連番。expected resultは`{number,text,authority_refs[]}`で1から連番
- `previous_tc_ids[]`は`{tc_id,status}`の成果物系列full snapshot。`update_scope_tc_ids[]`は今回lifecycleを確定するprevious active TCだけを列挙し、reuseはscope内activeだけ、duplicate reuse禁止。newはscope外 / deletedも含む過去最大番号+1、999超過は`id_space_exhausted`
- 各`ci_ref`の親TCNは`tcn_refs[]`に必須。TCの`tr_refs[]`は参照TCNのTR unionと一致させる
- CIのtest data requirement refsはTCのrefsへ含め、environment / test data requirementの存在とcontent fingerprintを検証する。TCが参照するtest data requirement unionは同一dimensionのintersectionを再検査し、複数CI統合で初めて生じるconflict / unsupportedをviolationにする
- environment requirementは`environment_key`ごとにcurrent要求集合を構成する。TCがある`environment_key`を選んだ場合、そのkeyのcurrent requirement refsを一式含むことを必須にし、key内だけintersectionを検査する。複数keyは代替実行環境としてcross-intersectionしない。どのkeyを選ぶかはLLMの意味判断に残す
- `priority_override_reason`はCoverage Itemから要求される優先度より低くする場合だけ非空必須
- LLMはCIの自己完結canonical `execution`または`semantic_item_text`とcurrent requirementsを使い、Markdown Coverage Item表やgenerator内部modelからmachine meaningを再抽出しない
- canonicalized TC draftを`draft_key`順で採番し、`update_scope_tc_ids[]`内のprevious active TCだけcurrentでreuseされなければdeletedへ遷移する。scope外のactive / deleted rowは状態を維持する
- dispositionは完全Machine Entity参照schemaを使う
- outputは`tc_id_map[]: {draft_key,tc_id,identity_action}`とactive / deleted全行を含む`tc_id_state[]`

#### `traceability.py`

- required: `analysis_scopes[]`, `nodes[]`, `edges[]`, `dispositions[]`, `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`, `unsupported_item_closures[]`
- node: `{node_key, node_type}`。node_typeは`Authority / Risk / TR / TCN / CI / TC`
- edge: `{from, to}`。from / toは既知nodeで、§23の許可直接edgeだけを認める
- disposition: `{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`。handlingは対象上流型に対して既存担当Skillが許可するDisposition集合だけを認め、必要なreason / Authority / covered_by_entityを検証する
- `analysis_scopes[]`は`coverage-analysis`が既存契約の「分析モードと対象範囲」を意味判断して正規化したSkill実行単位で、row schemaは`{skill, target, execution_range, input_mode, normalized_input, current_structure_state}`とする。`target / execution_range`は既存Skillの正規値、単一用途Skillではnullを許可する。`normalized_input`はそのscopeで使うcanonical normalized input、`current_structure_state`は必要な場合だけcurrent structure / materialize resultから`runtime_contract.py`固定projectionしたmachine stateとする。Agent / LLMはexpected identity一覧をここへ埋め込まない
- `runtime_units / current_entities / current_runtime_units / unsupported_item_closures`のrow schemaとfreshness / closure規則は`workflow_runtime.py`と共通化する。`traceability.py`は各`analysis_scopes[]` rowから同じ`runtime_contract.py` fixed builderを呼んで`expected_runtime_units[] / expected_entities[]`を内部導出し、inputとして完成済みexpected配列を受け取らない。actual runtime / Entity集合からexpectedを逆算しない。materialize runtime unitの`model_completion[] / target_mappings[] / target_dispositions[]`は同じcurrent resultから受け取る
- `coverage-analysis::artifact:traceability:all`自身と`qa-workflow::artifact:workflow_runtime:all`は`runtime_units[] / current_runtime_units[]`と内部導出する`expected_runtime_units[]`のすべてから除外する。いずれかに含まれていた場合は`invalid_input`とし、traceability → workflow_runtime → traceabilityのcycleを作らない
- `traceability.py`は各Skillの同一内容`runtime_contract.py`にある共通freshness評価関数を呼び、`runtime_freshness[] / entity_freshness[]`を決定論的に算出する。workflow_runtime resultを入力へ渡さず、self/cycle dependencyを作らない
- stale分析では`entity_freshness[]: {skill, entity_type, entity_ref, model_key, freshness_status, stale_reasons[]}`を正本にし、stale Entityがcurrentな下流で閉鎖済みと誤判定しない

#### `materialize_coverage.py`

- required: `tcn_id`, `active_model_metadata[]`, `models[]`, `semantic_coverage_items[]`, `target_annotations[]`, `target_dispositions[]`, `test_data_requirements[]`, `previous_target_id_map[]`, `previous_semantic_ci_map[]`, `previous_ci_ids[]`, `previous_expected_result_roots[]`, `merge_groups[]`
- optional: `legacy_ci_ids[]`, `legacy_ci_seed[]`。normal target / semantic mapping stateと`previous_ci_ids[]`がまだ存在しないlegacy初回昇格だけ許可し、通常再実行ではfield自体を渡さない
- `legacy_ci_ids[]`はinputの`tcn_id`配下に存在する全legacy CI IDを完全形式`TCN-\d{3}-CI\d{2,}`で一意に列挙する。各IDのTCN prefixはinput `tcn_id`と一致必須。`runtime_contract.py`のlegacy ID seed helperが全件`status=active`の同TCN `previous_ci_ids[]`へ変換し、未対応CIもそのTCNの過去最大番号と再利用禁止stateへ含める。最大番号比較時だけsuffix `CI\d{2,}`の数値部分を使う
- `legacy_ci_seed[]`は`legacy_ci_ids[]`のsubsetで、意味上current target / semantic itemへ対応付けて既存CI IDを維持するrowだけを持つ。`legacy_ci_seed[]`だけから全previous CI stateを逆算しない
- `tcn_id`は`TCN-\d{3}`
- `active_model_metadata[]`: `{model_key, model_type, technique_slug, parent_tcn_id, content_fingerprint}`。TCN配下の全current modelを渡し、`parent_tcn_id`はinputの`tcn_id`と一致必須
- TCN配下にactiveなCoverage所有modelが1件以上あれば、current machine target / semantic itemが0件でも`materialize_coverage.py`をdispatchする。runtimeなしsemantic modelでは0件を成功扱いせず対応`model_completion[]`を`materialize_complete=false`とする。whole-model `unsupported`は成功rowを作らずunsupported closureを最終条件にする
- `models[]`の各model resultは`runtime_contract.py`の`current_model_result_row`固定projectionだけから受け取る。共通metadataは`{model_key, model_type, technique_slug, skill, runtime_unit_key, input_fingerprint, model_fingerprint, generation_fingerprint, generator_contract_version, support_status, runtime_status, result_status, deterministic_generated, freshness_status, targets[], unsupported_items[]}`で、model type別summaryを加える。通常Coverage modelは`coverage_summary={criterion,required,covered,complete}`、CRUDは`coverage_summary={completeness:{criterion,required,covered,complete},consistency:{criterion,required,covered,complete},complete}`、Random / Metamorphicは各節の`completion_summary`を必須とし、他形式を拒否する
- materialize対象model resultは`runtime_status=ok / result_status=ready / deterministic_generated=true / freshness_status=current`を必須にする。加えて通常Coverage modelは`coverage_summary.complete=true`、CRUDは`coverage_summary.completeness.complete=true / consistency.complete=true / complete=true`、Random / Metamorphicは`completion_summary.complete=true`を必須にする。`support_status=supported`または、unsupported itemと対応可能targetが分離済みの`partial`だけ許可し、partialではsupported範囲のsummaryだけをcompleteにできる。runtimeなしsemantic modelやwhole-model unsupportedを成功resultとして`models[]`へ偽装しない
- `freshness_status=current`は現在のMachine Entity / normalized inputをpreflight確認した後、現在scriptを再実行して正常生成したresultだけに付与する。保存済みgenerator resultをmaterialize入力のcurrent cacheとして直接再利用しない
- semantic item draft: `{draft_key, model_key, identity_action, reuse_semantic_item_key, reuse_ci_id, source_target_versions[], item_text, authority_refs[], reference_refs[], priority, priority_override_reason, expected_result_root, test_data_requirement_refs[]}`。`draft_key`は入力内一意、`item_text`は非空。runtime generatorへ移さないsemantic model、fork-join等の直接linear executionへ落とさないCoverage Item、またはpartial / whole-model unsupportedの`llm_fallback`だけに使用する
- new semantic itemは`reuse_semantic_item_key / reuse_ci_id=null`とし、canonical `(model_key, draft_key)`順でCIを採番した後にruntimeが`semantic_item_key=semantic:<ci_id>`を発行する。reuseではactive / inactiveのprevious rowにある同じsemantic item key / model / CIをすべて指定し、別item・別model・runtime target CIへの横取りを拒否する
- `semantic_content_fingerprint`は`model_key / source_target_versions[] / item_text / authority_refs[] / reference_refs[] / priority / priority_override_reason / expected_result_root / test_data_requirement_refs[]`をcanonical JSON化してSHA-256する。identity_action / reuse fieldはfingerprintへ含めない
- `source_target_versions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint}`。machine targetを意味判断へ渡す場合は現在targetと完全一致し、全targetがsemantic item自身の`model_key`に所属することを必須にする。エラー推測またはwhole-model unsupported fallbackのように元machine targetがないsemantic itemでは空配列を許可する。machine target / execution / generation fingerprintを捏造しない
- machine target: `{target_ref, target_content_fingerprint, materializable, execution_fingerprint, target_key, execution, authority_refs, reference_refs, ...技法固有machine fields}`。`materializable=true`では自己完結`execution`と`execution_fingerprint`必須、falseでは両方null。fingerprintは[identity・materialize契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) §7.2の式をruntimeが再計算する
- target annotation: `{target_ref, target_content_fingerprint, generation_fingerprint, priority, priority_override_reason, expected_result_root, test_data_requirement_refs[]}`。Dispositionされないmaterializable targetにちょうど1件対応し、unknown / duplicate target_refを拒否する。target / generation versionは現在model resultと一致必須
- `expected_result_root`は同一TCN内の内部用local keyでstable component key形式を使う。同じkeyはLLMがAuthorityに基づき同じ期待挙動へ統合可能と判断したtargetだけへ付与し、製品Authorityそのものとして扱わない。意味上同じgroupをreuseする場合だけactiveなprevious keyを維持し、新規groupは未使用keyを追加する
- target disposition: `{target_ref, target_content_fingerprint, generation_fingerprint, handling, reason, authority_refs[], covered_by_target_version}`。`covered_by_target_version`はnullまたは`{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint}`。source targetの現在target / generationは完全一致必須で、同一targetへannotationとDispositionを同時指定しない。`handling=重複`では完全`covered_by_target_version`必須かつself参照禁止。参照先`materializable=true`ではcurrent `execution_fingerprint`を必須、semantic Coverage Itemへ閉じる`materializable=false` targetでは`execution_fingerprint=null`を必須にする。同一input内の参照先targetは即時にcurrent version照合し、local input外の参照先は最終`traceability.py / workflow_runtime.py`で全materialize unit横断照合する
- `target_ref`は[identity・materialize契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) §7.2の式を再計算して一致必須
- `test_data_requirements[]`: `{data_ref, requirement_key, environment_key:null, dimension_key, operator, source_model_key, source_target_versions, ...}`。`data_ref=data:<requirement_key>`を一意にし、annotation / semantic itemの全`test_data_requirement_refs[]`はcurrent集合に存在必須
- `previous_target_id_map[]`: `{target_ref, model_key, target_key, target_content_fingerprint, ci_id, mapping_status}`。`mapping_status=active|inactive`。Disposition中targetの直近CIもinactiveとして保持し、同じtarget_refでcontent fingerprintが変わればCI IDを維持しても`stale_ci_ids[]`へ追加する
- `previous_semantic_ci_map[]`: `{semantic_item_key, model_key, ci_id, mapping_status, semantic_content_fingerprint}`。`mapping_status=active|inactive`
- `previous_ci_ids[]`: `{ci_id, status}`。`status=active|deleted`で削除済み番号も保持する
- `previous_expected_result_roots[]`: `{expected_result_root, status}`。`status=active|deleted`。same-meaning groupのreuse可否はLLMが判断し、runtimeはunknown / duplicate / deleted keyの不正reuseを検査する
- `legacy_ci_seed[]`: `{ci_id, model_key, source_kind, target_ref, semantic_item_draft_key}`。`source_kind=runtime_target|semantic_item`。runtime targetではcurrent targetに一致する`target_ref`必須 / semantic draft keyはnull、semantic itemではcurrent draftに一致する`semantic_item_draft_key`必須 / target refはnull。`ci_id`は`legacy_ci_ids[]`に存在必須。既存CI IDはinputの`tcn_id`配下であること、modelがcurrent active modelであること、1 CI / 1 target / 1 semantic draftを複数seedへ重複利用しないことを検証する。seedされたidentityは通常のtarget / semantic mappingへ変換し、以後legacy専用stateとして保持しない
- `legacy_ci_ids[]`に存在して`legacy_ci_seed[]`へ対応しなかったCIは新targetへ推測割当てせず、current TCNの通常lifecycleでdeletedへ遷移させる。番号rowは`ci_id_state[]` full snapshotへ残し、そのCIを参照するlegacy TCは`要再検証`対象とする
- previous active target / semantic mappingがcurrentでreuseされなければinactiveへ遷移する。共有targetのないruntime CIまたは消滅したsemantic CIはdeletedへ移し、inactive / deleted rowをfull snapshotから消さない
- inactive target / semantic itemの復帰は同じidentityへの明示reuseかつ過去CIが別identityへ再利用されていない場合だけ同じCIを復帰できる。deleted CI / semantic item keyを別identityへ再利用しない
- semantic itemのmodel変更はreuse不可。同じsemantic item keyをreuseしてもcontent fingerprintが変わればCI content fingerprintを変え、既存TCをstaleにする
- merge groupは[identity・materialize契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) §7.4の`{merge_group_key, model_key, target_refs[], target_versions[]}`を使う。Dispositionされていない同一TCN・同一model内targetだけを許可し、全target versionを現在model resultへ一致させる。`execution_fingerprint`と`expected_result_root`が全件一致する場合だけ同一CIへ統合し、異なるmodel / 技法 / execution / expected resultを統合しない
- merge group内の追加test data requirementは[追加generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) §16と同じintersection規則で統合し、conflict / unsupportedならmergeを拒否する。異なるCIを1つのTCへまとめる意味判断は`case_structure.py`の`ci_refs[]`で行い、merge groupへ逆変換しない
- `materializable=false`のadapter / diagnostic専用targetはCI採番、annotation、Dispositionの対象外。正規Coverage基準上必要だがlinear executionへ落とせないtargetはcurrent target versionを持つsemantic Coverage Itemまたは既存Skillで許可されたtarget Dispositionへ1回だけ閉じる
- `target_dispositions[]`にあるmaterializable targetはCI採番対象から除外するが、generator固有の`coverage_summary`または`completion_summary`自体は変更しない
- new CI候補はcanonical `(model_key, source_kind, source_key)`順で採番する。`runtime_target < semantic_item`、runtime targetのsource keyは`target_ref`、semantic itemはnewなら`draft_key`、reuseなら`reuse_semantic_item_key`。raw入力順で採番しない
- runtime target mapping、semantic reuse、mergeの全経路で同一CIを別identityへ不正reuseするduplicateを拒否する。new CIはdeletedを含む同一TCNの完全`ci_id`からsuffix数値の過去最大+1を取り、`<tcn_id>-CI<2桁以上>`として割り当てる。完全IDは`TCN-\d{3}-CI\d{2,}`で、CI suffix自体には上限を設けない
- outputは`target_id_map[]`、`target_mapping_state[]`、`semantic_ci_mapping_state[]`、`ci_id_state[]`、`expected_result_root_state[]`、`disposed_target_refs[]`、`coverage_item_rows[]`、`stale_ci_ids[]`、`model_completion[]`、`issues[]`
- `target_id_map[]`: `{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`。`generation_fingerprint`はsource model resultのcurrent generationを固定転記する。active mappingだけを返し、1 target_refから複数CIへのmappingを禁止する
- `target_mapping_state[] / semantic_ci_mapping_state[] / ci_id_state[] / expected_result_root_state[]`はactive / inactive / deletedを含む必要なfull snapshotを返し、次回previous stateの正本にする
- 固定builderはactive CIごとに`_02`のCI Machine Entityを生成する。machine target由来は`source_kind=runtime_target`として`covered_targets[]`をtarget_ref順で集約しcanonical `execution`を保存する。semantic item由来は`source_kind=semantic_item / covered_targets=[] / execution=null / semantic_item_key / semantic_item_text / semantic_source_targets[]`を保存する
- CI Machine Entityの`runtime_dependencies[]`にはcurrent `materialize_coverage.py` generationを、`upstream_entity_dependencies[]`には親TCN、model metadata、current test data requirement Entityを保存する。priority / expected result root / Authority / Reference / test data requirementは現在annotation / target / semantic itemから固定joinし、LLMがCI Entity JSONを再生成しない
- `disposed_target_refs[]`: `{target_ref, target_content_fingerprint, generation_fingerprint, handling, covered_by_target_version}`。`covered_by_target_version`は[identity・materialize契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) §7.4と同じ4 fieldを保持し、Coverage済みtarget数の計算には使用しない
- `model_completion[]`: `{model_key, required_target_refs[], closed_target_refs[], active_ci_ids[], semantic_item_keys[], materialize_complete}`。supported / partial runtime modelとruntimeなしsemantic modelを対象にする。adapter / diagnosticをrequired targetへ数えない
- runtime targetを持つmodelは`required_target_refs[]`が非空かつ全件`closed_target_refs[]`に含まれる場合だけ`materialize_complete=true`。target disposition、current CI mapping、target version一致済みsemantic itemだけをclosureへ数える
- エラー推測等のtargetなしsemantic modelは1件以上のactive semantic CIがある場合だけtrue。partial modelのunsupported item closureはここで完了扱いせず`workflow_runtime.py`が別途検査する。whole-model unsupportedはLLM fallback CIのmaterialize自体は許可するが`model_completion[]`へ成功rowを捏造せず、workflow側のcurrent whole-model closureを最終条件にする
- `conditions=[] / actions=[] / factors=[] / relations=[] / source_inputs=[] / states=[]`等、Coverage所有modelの意味母集団が空でrequired target / pair / caseが0件になる入力をvacuous completeにしない。各script schemaで1件以上を必須としたfieldが空なら`invalid_input`、schema自体は成立しているが技法を完成させる意味parameter / 母集団が未確定なら`unresolved`、runtime-v1の対応subset外なら`unsupported`または独立処理可能範囲を残した`partial`とする。実装者判断でこれらを相互置換しない

#### `workflow_runtime.py`

- 既存`qa-workflow`が意味判断で確定したcanonical `workflow_scopes[]`に本Planruntime対象scopeが1件以上ある場合だけdispatchする。本Planruntime対象scopeが0件のE2E-only経路ではこのartifact runtime unit自体を作らず、既存`qa-workflow`の完了契約を使用する
- required: `workflow_scopes[]`, `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`, `unsupported_item_closures[]`
- `workflow_scopes[]`はqa-workflowが選択したSkill実行単位を`{skill, target, execution_range, input_mode, normalized_input, current_structure_state}`で保持する。`target / execution_range`は既存qa-workflowの正規値で、単一用途Skillではnullを許可する。`normalized_input`はそのSkill実行で使用したcanonical normalized input、`current_structure_state`は必要な場合だけcurrent structure / adapter parent runtime resultから同一`runtime_contract.py`が固定projectionしたmachine stateとする。Agent / LLMがexpected identity一覧をここへ埋め込まない
- `workflow_scopes[]`のSkill / 対象 / 実行範囲の選択自体は既存`qa-workflow`の意味判断を正本とし、`workflow_runtime.py`は自然言語要求から必要Skillを再推論しない。scope routingの妥当性はtrigger / semantic evalで検証する。一方、選択済みscope内のruntime / Entity完全性は以下の固定builderで機械検査する
- `qa-workflow::artifact:workflow_runtime:all`自身は`runtime_units[] / current_runtime_units[]`と、内部導出する`expected_runtime_units[]`のすべてから除外する。いずれかに自身が含まれていた場合は`invalid_input`とし、self dependencyも禁止する
- runtime unit: `{skill, runtime_unit_key, model_key, support_status, result_status, runtime_status, runtime_required, deterministic_generated, generation_fingerprint, result_fingerprint, upstream_entity_fingerprints[], upstream_runtime_units[], unsupported_items[], model_completion[], target_mappings[], target_dispositions[]}`。`runtime_contract.py`の`runtime_unit_row`固定projectionだけから作り、raw envelope / payloadをcallerが再構成しない。`result_fingerprint`はMachine Runtime Result envelope全体のcanonical JSON SHA-256であり、入力・実装由来の`generation_fingerprint`とは別に保存結果の一致を検証する。`model_completion[] / target_mappings[] / target_dispositions[]`は`artifact:materialize_coverage:<tcn_id>`だけ非空を許可し、current materialize resultから固定builderで転記する。他unitは3配列とも空固定
- `current_entities[]`: `{skill, entity_type, entity_ref, model_key, content, content_fingerprint, upstream_entity_dependencies[], runtime_dependencies[]}`。`content`は`_02` §4.4のMachine Entityと同一で、共通関数が`content_fingerprint`を再計算して保存値と一致確認する
- `current_runtime_units[]`は現在のcanonical inputからscriptを再実行して固定builderが生成したruntime row projectionで、`(skill, runtime_unit_key)`を一意keyとし、runtime unit rowと同じidentity/status/metadata/dependency/result projectionおよび`result_fingerprint`を持つ。保存側`runtime_units[]`は期待identityに対するmissing / extraとcurrent resultとの一致検証に使い、freshness、completion、target mapping / disposition、unsupported closure等のcurrent semantic判定は`current_runtime_units[]`を正本とする。保存側とcurrent側はgenerationが同じでもprojectionまたは`result_fingerprint`が異なればcurrentとして扱わない
- `workflow_runtime.py`は各`workflow_scopes[]` rowについて、まず`skill + target / execution_range + normalized_input`と`_02` §2.1の固定dispatch表からroot `expected_runtime_units[]`を内部導出する。条件付きmodel / child runtimeは、source generationが`current_runtime_units[]`と一致する`current_structure_state`から同helperが段階的に導出する。root期待unitがmissing / staleなら、その欠落をblockerにしたうえでdownstream期待集合を空へ縮退させない
- `expected_entities[]`も入力fieldにせず、各scopeのnormalized sourceとcurrentなstructure / materialize machine stateから同じ固定builderで内部導出する
  - `spec-analysis`: Authority表 / canonical source inventory
  - `test-analysis`: `analysis_entities.py`の正規化inputとcurrent risk / technique / environment runtime resultからcontext / Product Risk / Technique Selection / change graph / environment requirement
  - `test-requirement-design`: `requirement_structure.py`のinput draft + ID mapping / full stateからTR / Disposition
  - `test-condition-design`: `condition_structure.py`のinput draft + ID mapping / full state、current generator dispatch、`test_data_requirements.py`の正規化input / result、`materialize_coverage.py` mappingからTCN / model / CI / test data requirement / Disposition
  - `test-case-design`: `case_structure.py`のinput draft + ID mapping / full stateからTC / Disposition
- 禁止: Agent / LLMが完成済み`expected_runtime_units[] / expected_entities[]`を`workflow_runtime.py`へ渡す、`current_entities[]`を読んでexpectedを作る、保存済みMachine Entity blockを期待集合の正本にする、missing actual Entityの存在を前提にexpected identityを作る
- `runtime_units[]`のidentity集合は内部導出した`expected_runtime_units[]`と完全一致、`current_entities[]`のidentity集合は内部導出した`expected_entities[]`と完全一致を必須にする。期待item欠落はblocker、未知の余分なcurrent itemは`invalid_input`とする
- completionでは各active Coverage所有modelをmodel単位で検査する。supported / partial / runtimeなしsemantic modelはcurrent materialize runtime unitの対応`model_completion[]` rowを必須とし、`materialize_complete=true`かつrow内`active_ci_ids[]`がcurrent CI Machine Entityと一致することを検証する。partialではさらにcurrent unsupported item closureを全件必須とする。whole-model unsupportedは対応generationのwhole-model `unsupported_item_closures[]`を必須とする。親TCNに別modelのCIがあるだけで当該modelを完了扱いしない
- 各Skillの同一内容`runtime_contract.py`にruntime dependency graphとMachine Entity dependency graphを評価する共通関数を置く。missing dependencyはstale + blocker、duplicateまたはcycleは`invalid_input`
- `unsupported_item_closures[]`: `{skill, runtime_unit_key, generation_fingerprint, item_key, reason_code, handling, reason, authority_refs, covered_by_entity}`。`covered_by_entity`は`null`または`{skill, entity_type, entity_ref, content_fingerprint}`の完全Machine Entity参照。`handling`は`llm_fallback / 対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複 / ブロック中`だけを許可する。closureの`generation_fingerprint`は対象runtime unitの現在値と一致必須。`support_status=partial`では`item_key`をunsupported itemのstable keyで必須とし、`reason_code`も現在unsupported itemと一致必須。同じ`(skill, runtime_unit_key, generation_fingerprint, item_key)`のclosureはちょうど1件とし、duplicateを`invalid_input`にする。whole-model `unsupported`では`item_key=null / reason_code=null`を許可するが、同じ`(skill, runtime_unit_key, generation_fingerprint)`のwhole-model closureはちょうど1件だけ許可する。世代またはreasonが変わった以前のclosureを自動再利用しない
- `llm_fallback`と`重複`は`covered_by_entity`必須で、currentなMachine Entityへ解決できることを検証する。通常Coverage modelの`llm_fallback`は同じ`model_key`に属するcurrent CI Machine Entityを必須とする。internal adapterのpartial unsupported closureだけは、`_02_runtime-architecture-and-contracts.md` §2.2の手順で同じTCNへ追加した直接定義Coverage modelのcurrent CIを許可し、そのmodelの`technique_slug`は対応unsupported itemの`affected_technique_slug`と一致必須とする。whole-model adapterではactiveのまま残す各selected child techniqueがcurrentな直接定義Coverage model / CIまたは既存Disposition closureへ到達していることを別途検査する。親TCNやmodel metadataだけをfallback Coverage evidenceにしない。`対象外 / 別テストレベル / 残存リスク / 成立不能`は既存`test-condition-design`のDisposition条件をそのまま適用し、不要な`covered_by_entity`はnullとする。`ブロック中`はclosure rowとして保持しても閉鎖済みには数えず`can_complete=false`とする
- runtimeは意味上の再利用可否、開始Skill、仕様Authorityの優先関係を再判断しない
- outputは`freshness[]: {skill, runtime_unit_key, generation_fingerprint, freshness_status, stale_reasons[]}`、`entity_freshness[]: {skill, entity_type, entity_ref, model_key, freshness_status, stale_reasons[]}`、`completion: {can_complete, blockers[]}`、runtime状態表用の正規化rowを返す
- `can_complete`は本Planが追加するruntime / Machine Entity / Coverage closure範囲だけの機械的完了可否であり、既存`qa-workflow`全体の完了を表さない
- `can_complete=true`には、expected runtime / Entity集合が完全一致し、全runtime unitと対象Machine Entityがcurrent、全unitの`result_status=ready`、runtime required unitが`deterministic_generated=true`であることに加え、partial / unsupportedの各itemが上記closure契約を満たし、`ブロック中`closure、missing / stale / fingerprint不一致な`covered_by_entity`、既存Disposition条件違反が0件であることを必須にする。E2E実装・実行・分析・報告等を要求するworkflowでは、既存`qa-workflow`完了条件が別途すべて成立し、かつ本scriptをdispatchした場合に`can_complete=true`であることを追加の必要条件とする

### unsupported item共通schema

`support_status=partial`で返す`payload.unsupported_items[]`は`{item_key, item_type, source_key, reason_code, affected_technique_slug, authority_refs[]}`で固定します。通常Coverage generatorでは`affected_technique_slug=null`固定です。Coverageを所有しないinternal adapterだけ、partial unsupported itemごとに事前採用済みchild techniqueのcanonical `technique_slug`を必須にします。1つのunsupported箇所が複数child techniqueへ影響する場合はtechniqueごとにitemを分けます。`reason_code`は機械的な非対応理由であり、workflow完了可否は`unsupported_item_closures[]`の`handling / covered_by_entity`を別途検査して決めます。

- `item_key`は`unsupported:<generator>:h<canonical identity SHA-256 64 lowercase hex>`で、generator、`item_type`、`source_key`、`affected_technique_slug`をcanonical JSON化して作る。通常generatorはnullを含め、adapterで同じsource/reasonが複数techniqueへ影響してもitem keyを衝突させない
- `source_key`は対応できないsubtree / region / operator等のstable component keyまたはJSON Pointer
- `reason_code`はscriptごとにPlan / Skill referenceで列挙した固定値だけを使用し、自由文をidentityに含めない
- runtime-v1でpartial unsupported itemを返すscriptの最低限の固定値は次とする。より細かい理由へ分割する場合はcontract変更としてPlan / Skill referenceと回帰fixtureを同時更新し、実装者判断で自由なcodeを追加しない
  - `domain_testing.py`: `unrepresentable_point`
  - `flow_paths.py`: `concurrent_flow_requires_semantic_execution`
  - `schema_cases.py`: `cyclic_local_ref / unsupported_reference / unsupported_schema_keyword / unsupported_value_shape / unsupported_html_control / unsupported_html_constraint`
  - `test_data_requirements.py`: `unsupported_intersection`
  - `metamorphic.py`: `unsupported_transform / unsupported_path / unsupported_relation`
- 再実行で同じunsupported箇所は同じ`item_key`を維持し、`workflow_runtime.py`のclosure再利用に使う

`valid_minimal.json`は上記schemaの実行例であり正本ではありません。optional fieldは上記で明記したものだけとし、Skill referenceはこのPlanのschemaをそのまま説明します。

### stable component key

target / result keyへ文字列連結する`set_key / partition_key / boundary_key / border_key / condition_key / action_key / rule_key / factor_key / classification_key / class_key / state_key / transition_key / candidate_key / region_key / branch_key / loop_key / entity_key / function_key / sequence_key / cause_key / effect_key / production_key / mutation_key / relation_key / source_id / follow_up_key / requirement_key / dimension_key`は`_02` §3.2のstable component key形式に従い、`:`を含めません。

### grammar production key

`grammar_cases.py`のproductionは配列indexへ依存せず、各productionを`{"production_key":"P-001","lhs":"expr","rhs":[...]}`形式で与えます。`production_key`はmodel内一意で、並べ替えではtarget keyを変えません。

## 26. scriptが生成しないもの

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- 新しいrisk score入力
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle
- 意味上の同一性・統合可否

scriptの責務は、対応contractとhard limitの範囲で、与えられたmodelを再現可能に展開し、未解決・非対応・limit超過を隠さないことです。
