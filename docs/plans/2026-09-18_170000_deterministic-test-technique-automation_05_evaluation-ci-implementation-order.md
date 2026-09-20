# テスト分析・テスト技法の決定論的自動化Plan

## 1. 評価方針

評価を次の4層へ分けます。

1. runtime script unit test
2. 独立した決定論的validator
3. semantic eval
4. qa-workflow統合評価

generatorとvalidatorは実装helperを共有しません。expected fixtureをgenerator出力から自動生成しません。

## 2. runtime script unit test

`tests/skills/runtime/`直下へ配置し、Python 3.11の`unittest discover`で実行します。

対象:

```text
test_test_analysis_risk_matrix.py
test_test_analysis_technique_candidates.py
test_test_analysis_change_impact.py
test_test_analysis_environment_requirements.py
test_test_requirement_structure.py
test_test_condition_structure.py
test_test_condition_equivalence_partitions.py
test_test_condition_bva.py
test_test_condition_domain_testing.py
test_test_condition_decision_table.py
test_test_condition_combinatorial.py
test_test_condition_classification_tree.py
test_test_condition_state_transition.py
test_test_condition_flow_paths.py
test_test_condition_crud_matrix.py
test_test_condition_cause_effect.py
test_test_condition_grammar_cases.py
test_test_condition_schema_cases.py
test_test_condition_ui_pattern_candidates.py
test_test_condition_test_data_requirements.py
test_test_condition_random_testing.py
test_test_condition_metamorphic.py
test_test_condition_materialize_coverage.py
test_test_case_structure.py
test_coverage_analysis_traceability.py
test_qa_workflow_runtime.py
test_runtime_contract.py
test_runtime_markdown_roundtrip.py
test_runtime_determinism.py
test_runtime_workflow_integration.py
```

実行test数が0件ならCIを失敗させます。

各runtime scriptには`tests/skills/runtime/fixtures/<script-name>/valid_minimal.json`を1件必須とし、これをPlan `_03`のrequired input schemaの実行例とします。fixtureは手書きし、generator出力から生成しません。unknown field拒否、required field欠落、型不一致は各scriptのunit testで確認します。

CLI integration testは各runtime scriptの`valid_minimal.json`をsubprocessで`python <script-path>`起動し、stdinへJSONを渡してstdout envelopeを読む経路を使用します。加えて`_02` §2.1のSkill別dispatch表について、各scriptへ到達するprompt分類済みfixtureから期待script path・必須/条件付き・実行順を一意に決められることを機械テストします。派生modelでは親runtime → `condition_structure.py` → 派生generatorまで検証します。全scriptのdispatchはCIで検証し、実Agent smokeだけへ依存しません。CI subprocessとSkill実行時subprocessの安全timeoutは30秒です。

## 3. 共通契約の必須回帰

### strict JSON

- duplicate key拒否
- `NaN` / `Infinity`拒否
- 不正top-level type拒否
- UTF-8 decode前byte上限とdecode後nesting depth 64
- unpaired surrogate code point拒否
- model decimalの型保持
- raw JSON documentのnumberを通常のstringと異なる専用token型で受け、raw token長 / JSON number grammar検証後にcanonical integer / `coefficient + scale`へexact正規化し、binary float / `Decimal` contextへ依存しない
- canonical serializerがexact numeric表現を指数表記なしのJSON numberへ戻す
- `1 != "1"`、`1.0 != "1.0"`、`1e3 != "1e3"`を固定回帰にする
- raw numeric token / canonical numeric representationの4096 chars上限超過を`limit_exceeded`にし、丸めない
- nullと欠落の区別

### runtime envelope

- `envelope_version / skill / runtime_contract_version / generator_contract_version / generator / runtime_unit_key / model_key / input_fingerprint / model_fingerprint / generation_fingerprint / runtime_implementation_fingerprint / generator_implementation_fingerprint / upstream_entity_fingerprints / upstream_runtime_units / support_status / static_data_versions / runtime_status / result_status / runtime_required / deterministic_generated / fallback_reason / payload / issues`
- `skill`はscript所属Skillと一致必須で、runtime issueも`skill + runtime_unit_key`を保持する
- runtime生成issueはenvelopeの`generation_fingerprint`を保持し、質問・再開時に現在世代と一致しない回答を拒否する。timeout等のcaller生成issueだけ`generation_fingerprint=null`を許可する
- model scriptは`runtime_unit_key=model:<model_key>`、artifact全体scriptは`runtime_unit_key=artifact:<generator>:<scope_key>`を要求し、artifact全体scriptの`model_key`はnull
- runtime dependency参照は`(skill, runtime_unit_key)`を一意keyとし、Skillを跨いで`runtime_unit_key`単独をidentityにしない
- `ok / invalid_input / unsupported / limit_exceeded`は構造化結果を返せた扱いで終了code 0
- `internal_error`は可能ならenvelopeを返して終了code 1、envelope生成不能も1
- subprocess timeoutは新しいruntime statusを増やさず、`runtime_status=internal_error / support_status=unknown / result_status=blocked / runtime_required=true / deterministic_generated=false`へmappingし、`issue_type=runtime_execution_timeout`で原因を区別する
- Agent側は終了codeだけで判断せずstdout envelopeをparseする
- 対応subset判定は各runtime scriptが行い、model全体がsubset外なら`runtime_status=unsupported / support_status=unsupported / runtime_required=false / fallback_reason=outside_supported_subset`を返す
- 一部だけsubset外なら`support_status=partial`としてsupported部分を生成し、`unsupported_items[]`をfallback / Dispositionへ閉じるまで完了扱いしない
- `runtime_required`はruntime入力に存在せず、support判定結果からscriptが出力する。Agent側だけでsupport判定してruntimeを省略しない
- artifact scriptのscope keyがscript別固定値 / input由来値と一致する
- `test-analysis` runtimeは`対象 / 実行範囲=テスト分析`だけ、`coverage-analysis` runtimeは`対象 / 実行範囲=テスト設計`だけでdispatchし、同じSkillの他用途では本Planruntimeを起動しない
- `support_status=unknown`は`invalid_input / internal_error / not_run`だけで許可し、いずれも`runtime_required=true / result_status=blocked / deterministic_generated=false`を要求する
- Python unavailable / runtime未実行は`runtime_status=not_run / support_status=unknown / runtime_required=true / result_status=blocked / deterministic_generated=false / fallback_reason=python_unavailable`とし、fingerprintをnullで保持する
- status対応表どおりの`support_status / result_status / runtime_required / deterministic_generated`を要求
- model scriptでは`model_status=result_status`、artifact全体scriptでは`artifact_status=result_status`
- staleはruntime statusではなく`freshness_status`で表現する。semantic dependency preflight成功後に現在scriptを正常実行したresultは保存時に`current`、`workflow_runtime.py`は共通freshness関数で再検証して必要なresult / Entityを`stale`へ変更する
- stderrへ入力全文・secretを出さない
- unknown `route_to` / `resume_skill`を拒否

### canonicalization / fingerprint

- unordered record配列のraw入力順を変えてもcanonical input、fingerprint、machine result、stable ID mappingがすべて一致する
- generator / structure scriptがhash用canonical bytesだけでなく同じcanonicalized dataを実処理へ使う

- object key順が違ってもcanonical結果は同じ
- `authority_refs` / `reference_refs`の順序差でfingerprintが変わらない
- 順序に意味があるfactor / value / transition配列の順序変更はfingerprintへ反映
- decimal / date / fixed-offset datetimeの正規化
- 人間向け説明文だけを変えてもinput / model fingerprintが変わらない
- script固有input、`authority_refs`、`reference_refs`、modelの`selection_source`変更で`input_fingerprint`が変わる
- artifact全体scriptでもinput変更で`input_fingerprint / generation_fingerprint`が変わる
- `spec-analysis / test-analysis / test-requirement-design / test-condition-design / test-case-design`の`Machine Entities`をstrict decodeし、canonical Entity schema、`(skill, entity_type, entity_ref)`一意性、`content_fingerprint`再計算一致、人間向け表との主要field一致を検証する
- 異なる`entity_type`で同じ`entity_ref`を使うfixtureは許可し、同じ`(skill, entity_type, entity_ref)`重複だけを拒否する
- `upstream_entity_dependencies[]`と`current_entities[] / entity_freshness[]`で`entity_type`欠落またはtype不一致を拒否する
- upstream Entityのcanonical `content`からruntimeが`content_fingerprint`を計算し、output envelopeの`upstream_entity_fingerprints[]`へcanonical順で保存する。呼び出し側が渡したhashだけを信用しない
- upstream Entityの正規項目変更でその`content_fingerprint`だけが変わる
- `upstream_entity_fingerprints`の変更で`generation_fingerprint`が変わり、Authority IDが同じでも内容変更を同一generation扱いしない
- Machine Entityの`upstream_entity_dependencies[]`差分を再実行前に検出し、古いsemantic model / draftをそのまま現在runtimeへ投入しない
- 無関係なupstream Entity変更では対象runtime unitをstaleにしない
- 直接依存する上流runtime unitの`generation_fingerprint`変更で下流unitだけがstaleになる
- envelope version、generator、runtime contract、generator contract、実装fingerprint、static data version変更で`generation_fingerprint`が変わる
- runtime / generator source変更で実装fingerprintが変わり、意味契約を変えないbug fixでも旧machine evidenceを同一生成条件として再利用しない
- 既存成果物再利用時もdispatch対象runtimeを現在scriptで再実行し、保存済みruntime resultだけでcurrent判定しない
- 以前whole-model `unsupported`だったfixtureをruntime対応後に再実行するとsupported経路へ移り、古いfallbackを固定しない
- `condition_structure.py`を派生model追加のため再実行しても、既存model generatorがID割当てしか利用していない場合は同scriptをruntime dependencyへ登録せず、親generatorを自己stale化しない
- tie-break / Coverage / target key等の意味契約変更では実装fingerprintだけでなく対応contract versionも更新する
- model / artifact全runtime unitについて`Machine Runtime Input / Result`を保存→決定論的抽出→strict decode→canonical化し、input fingerprint、model scriptではmodel fingerprintも一致する。同条件でruntimeへ再投入すると同じmachine resultになる
- LF / CRLF差だけでimplementation fingerprintが変わらない
- canonical JSON static dataは整形・改行差だけでversion hashが変わらない

### 決定論性

同一fixtureを`PYTHONHASHSEED=1`と`PYTHONHASHSEED=999`の2条件で実行し、machine outputが一致することを確認します。

locale依存sort、set iteration順、dict insertion偶然性に依存する出力を禁止します。

### hard limit

- raw numeric token / canonical numeric表現4,096文字境界、exponent展開後超過を`limit_exceeded`にする
- BVA / range intersection / Metamorphic decimal演算がbinary floatやDecimal contextに依存せずexactになる

`_02`の固定上限について境界値をテストします。

- 通常runtime stdin 2 MiB、集約runtime stdin 16 MiB、stdout 16 MiBの各上限ちょうどは処理可能
- 複数modelを集約した`materialize_coverage.py`等は最終stdin全体へ16 MiB上限を適用し、個々の上流unit成功だけでは完了扱いしない
- nesting depth、1文字列、target / row / candidate上限を検証
- 探索nodeはroot=1。combinatorial / Decision Tableのpartial assignment、state / flowのpath / cycle prefix、grammarのpartial derivationを展開するたびに加算する
- output件数0でも探索node超過なら`limit_exceeded`
- target / row / candidateはstable key重複除去後に数える
- 1件または1 byte超過で`limit_exceeded`
- Coverage基準を自動で下げない
- 部分結果を100%としない
- 30秒timeoutは異常時の安全網であり、通常の探索結果をtimeout時刻で確定しない
- 代表generator実装後の実Agent smokeでstdout 16 MiB境界付近の取得・strict decode・成果物保存を確認し、実Agent側の安全上限が低い場合は後続generator量産前に`runtime-v1`へ固定する

## 4. 技法・構造処理の必須回帰

### risk matrix

- repository-default 4×4
- project-specific matrix完全性
- matrix levelごとの`priority_map`完全性
- mapped priorityが`高 / 中 / 低`のいずれか
- scheme外値拒否
- project-specificを標準方式で上書きしない
- mapped priorityが`test-requirement-design`の最低優先度判定へ渡る

### technique candidates

- 全signal key
- `true / false / null`
- `_03`のsignal → candidate mapping
- 複数`true`時のunionと安定順
- `undetermined_signals`
- `complete=false`だけではworkflowをブロックしない
- `Selection Source = analysis / condition_design / user`。runtime派生元は`upstream_runtime_units[]`で表し、既存model再利用は`identity_action=reuse`で表す
- ユーザー明示 / 既存成果物由来の技法をcandidate scriptが却下しない
- `undetermined_signals`の各signalを`resolved / selection_not_affected / question`へ閉じ、未閉鎖signalをworkflow完了にしない
- 新規正規技法名
- 選択技法のmodel / disposition閉鎖

### change impact

- node / edge type
- `depends_on / traces_to / derived_from`の探索方向
- unknown node / dangling edge
- 名称類似だけでedge追加しない
- upstream Entity content fingerprint変更時の影響model限定

### test environment requirement

- 同一dimension統合
- `eq × eq / eq × enum / eq × range / enum × enum / enum × range / range × range / version_range × version_range`の型互換intersection
- booleanと型互換`eq`の一致
- incompatible value / empty intersection矛盾
- 安全にintersectionできない型・operator組合せを`unsupported`として残す
- 実環境を勝手に推測しない

### test requirement structure

- Authority / Risk → TR closure
- linked + disposed重複
- unknown upstream ID
- 最低優先度
- 低い指定優先度 + 空の`priority_override_reason`をviolation
- 低い指定優先度 + 非空override reasonは値を保持し、自動補正しない
- `draft_key`を使ってLLM draftと最終TR ID mappingを安定追跡する
- `reuse_id / new`の意味判断とTR番号割当てを分離し、`previous_tr_ids[].status=active|deleted`を検証する
- reuseはactiveだけ許可し、新規はactive / deletedを含む最大番号+1で採番して削除済み番号を再利用しない
- outputの`tr_id_state[]`にdeleted IDも残し、次回入力の正本にする
- TR draftの`text / test_level / observation_method`をruntime inputへ保持し、structure scriptが内容を生成・欠落させない
- runtime output + draft意味fieldからTR Machine Entityを固定builderで生成する
- draft → runtime検査 → 再検査の処理順

### test condition structure

- TR入力、TCNの`tr_refs[]`、requirement Dispositionから各TRをTCNまたは扱いへちょうど1回閉じる
- unknown TR、linked + disposed重複、未閉鎖TRを検出する
- TCN priorityは関連TR最高優先度を既定とし、低いoverrideには理由を必須にする
- TCN / modelの`draft_key`、`reuse / new`意味判断と番号割当てを分離する
- `previous_tcn_ids[] / previous_model_keys[]`の`active|deleted`を検証し、reuseはactiveだけ許可する
- 新規TCNはactive / deletedを含む既存最大+1、999超過は`id_space_exhausted`
- model keyは同じ`model_type`のactive / deleted最大+1、削除済みkeyを同系列で再利用しない
- reuse時の`model_type / technique_slug / selection_source / selection_key / parent TCN / existing key`一致
- 1 model key = 1 TCN所属を検査し、同じmodel keyを複数TCNへ割り当てない
- outputの`tcn_id_state[] / model_key_state[]`にdeleted IDも残し、次回入力の正本にする
- TCN draftの`condition / category / technique_slugs[] / coverage_criterion / authority_refs / risk_refs`とmodel draftの`model_type / technique_slug / selection_source / selection_key`をruntime inputへ保持し、最終IDとjoinしてTCN / model metadata Machine Entityを固定生成する
- Coverage所有modelだけ`selection_source=analysis / condition_design / user`を持ち、内部adapterは`technique_slug / selection_source / selection_key=null`
- 各TCNの`technique_slugs[]`と所属Coverage所有modelのcanonical `technique_slug`集合を完全一致で検証する
- Classification Tree / Cause-Effect / schema adapterは正規技法を所有せず、child Coverage modelがcanonical techniqueと元のselection provenanceを持つ
- 1つのselectionは複数TCN / modelへ展開できるが、active Technique Selectionの`selected_techniques[]`に残る各技法は少なくとも1件のcurrent Coverage所有modelへ到達することを検証する
- 選択後に不適用 / 未解決となった技法はTechnique Selection Entity自体を更新してselected listから外すか既存block / unresolvedへ戻し、未定義のselection closureでは閉じない
- runtime非対応はCoverage所有model生成後のunsupported closureで扱う
- child Coverage model欠落をadapter親だけで閉鎖済みにしない
- `model_type=error-guessing / technique_slug=error-guessing`はruntime unitを要求せず、semantic Coverage ItemをCI Machine Entityへmaterializeできることを検証する。semantic item 0件では完了不可
- 各active Coverage所有modelは、1件以上のcurrent CI、または非空のrequired Coverage母集団がcurrent target Disposition / unsupported closureで全件閉じていることをmodel単位で検証する。別modelのCIが親TCNに存在するだけでは完了にしない
- `conditions=[] / actions=[] / factors=[] / relations=[] / source_inputs=[] / states=[]`等の空modelがvacuous completeにならず`invalid_input / unresolved`へ落ちることを検証する

### 同値分割 / Each Choice

- partition重複 / 衝突
- representative所属
- enum representative=nullは宣言順先頭を選ぶ
- integer range representative=nullはlower側の最初の有効整数を選ぶ
- decimal / date / datetime rangeでrepresentative未指定ならunresolved
- 成果物閉鎖とCoverageの分離
- DispositionをCoverage済みと数えない
- Authority付き成立不能だけを母集団から除外

### BVA

- `threshold / side / inclusive`から2-valueの`OTHER`を一意に決定
- 3-valueの`BELOW / AT / ABOVE`
- integer / Decimal / date / local datetime / fixed-offset datetime
- domain別step objectの型・正値検証
- 3-valueでは境界リスク、過去不具合、ユーザー明示等の具体的な`coverage_selection_reason`を必須にする
- schema由来BVAはboundary skeletonとLLMの`mode / coverage_selection_reason`を固定builderでjoinし、schema scriptだけで3-valueを自動選択しない
- fixed-offset datetime算術でoffsetを保持
- step不明時に隣接値を創作しない
- 同一具体値でもCoverage positionを区別

### Domain Testing

- Reliable Domain Coverageだけを実装
- linear border
- pivot / anchor / positive step
- `< / <= / > / >= / = / !=`
- closed `<= / >=`: ON=border、OFF=outside最隣接、IN=inside最隣接、OUT=さらにoutside
- open `< / >`: OFF=border、ON=inside最隣接、IN=さらにinside、OUT=outside最隣接
- `=`: ON + OFF_NEG + OFF_POS
- `!=`: OFF + ON_NEG + ON_POS
- `_03`で定義したpartition + border + relation別target key
- partition expressionの`and / or / border_ref`検証
- ON / INがpartition全体true、OFF / OUTがfalseになること
- 対象borderのON / IN pointが他border上に乗らず、他borderについてpartition内部であること
- OFF / OUTが対象borderを跨いだ結果としてpartition外であり、別borderだけを跨いだpointを誤採用しないこと
- 対象border以外の条件によりrequired pointを作れない場合のblocking
- coefficient / constant / anchorをexact rationalへ変換し、pivot計算でbinary float / Decimal roundingを使わない
- finite decimalへexact変換できるboundaryだけ生成し、`1/3`等は`unrepresentable_point` unsupported itemへする
- representable / unrepresentable boundary
- coefficient 0 / anchor不足
- override point所属・距離検証

### Decision Table

- 任意condition数
- action key完全性
- forbidden constraint
- unspecified
- duplicate / conflict
- don't-care merge candidateへstable `merge_key`を付ける
- accepted mergeは生成済み`merge_key`だけを受け付け、LLMが任意rule集合を構成できない
- merge後のCartesian productが成立可能な既知ruleだけを含み、未定義assignmentを増やさない
- Authority保持
- accepted don't-care merge前後で元の成立可能assignment target集合と`coverage_summary.required / covered`が変わらない
- accepted don't-care mergeを`materialize_coverage.py`の`merge_group`へ自動変換しない

### 組合せ

- exhaustive
- constraint付きBase Choice
- Pairwise / N-wise
- mixed-strength
- `SAT / UNSAT / limit_exceeded`
- `t-wise strength>2`またはmixed-strengthのいずれかのstrength>2では具体的な`coverage_selection_reason`を必須にする
- target union
- tie-break
- full Cartesian productの事前materializeを前提にしない

### 状態遷移

- 複数initial stateのtie-breakと`initial_state_key`をexecutionへ保持する
- resetが必要なtargetは`reset_key`をexecutionへ保持し、reset操作を空`setup_prefix`へ落とさない

- transition identity
- all state / all transition
- n-switchは`N+1`個の連続valid transition全sequence
- `switch_count=0..10`、`N>=2`では具体的な`coverage_selection_reason`必須
- Round-tripは開始終了stateのみ重複するsimple cycle、self-loop含む
- 開始stateをtarget identityに含め、同じ閉路でも開始state違いを別targetとして保持する。rotationで同一化しない
- guard feasibility
- reachable sourceの`guard_status=null`でCoverage completeにしない
- `guard_status=false`除外にはAuthorityを必須
- initial / reset
- setup prefix
- shortest path tie-break
- 実行開始不能sequenceを正式Coverageにしない

### flow

- simple-loop 0 / 1 / typical / maximumはprefix + cycle×N + canonical exit edgeでexecutionを作る
- `exit_edge_keys[]`、複数exit tie-break、exitなしspecの`invalid_input`、複数initial nodeの`initial_node_key`保持を検証する

- `initial_node_keys[]`必須
- node / edge / initial→terminal bounded path
- `max_path_length=1..1000`
- explicit `loop_specs[]`の0 / 1 / typical / max iteration target
- `maximum_iterations=null` / typical重複時のtarget dedupe
- explicit `regions[] / branches[]`の連続path検証
- nested region
- crossing regionは`unsupported`
- reachable sourceの`guard_status=null`でCoverage completeにしない
- `guard_status=false`除外にはAuthorityを必須
- scheduler interleavingを勝手に生成しない
- edge証拠とpath証拠の分離

### CRUD

- completeness / consistencyを別Coverage summaryで返す
- matrix operation target
- entity単位でC/R/U/D欠落を`crud:missing:*` anomalyとして列挙
- Authority付き`not_applicable` dispositionでのみmissing operationを閉じる
- lifecycle sequence
- Authority付きnegative sequence
- matrixに存在しないsequence stepを拒否
- consistency未正規化または未処置missing operationではCRUD全体をcompleteにしない
- 個々の空cellを自動欠陥化せず、専用`excluded_cells[]`も持たない。entity全体のmissing operationだけ`operation_dispositions[]`で閉じる

### Cause-Effect

- boolean AST
- unknown cause
- cycle禁止
- Authority付き`constraints[]`でcause間の成立不能partial assignmentを表現する
- constraintに一致するcause assignmentを正式known rule / Coverage母集団へ入れない
- assignment hard limit
- `derived.decision_table`が`conditions / actions / known_rules / constraints / accepted_merges=[]`を持ち、入力constraintを失わずDecision Table inputと直接互換

### Syntax-Based Testing

- 同じnonterminalが複数出現するgrammarでもleftmost derivationで展開位置を一意にする
- `max_depth`をroot=0のparse tree depthとして検証し、epsilon production境界を確認する

- production_key一意性
- undefined nonterminal
- unreachable production
- recursion / max depth
- production適用回数最小 + production key列辞書順tie-breakのshortest derivation
- valid case集合が各production shortest derivationのdedupe unionだけであること
- production Coverage
- `symbol_index`境界とterminal item検証
- `delete_terminal / replace_terminal / insert_terminal`だけをmutationとして許可
- mutation後grammarで対象productionを使うshortest derivationを生成
- max_depth内で導出不能なら`unreachable_mutation`
- mutation結果を自動で製品上invalidと断定しない

### schema / HTML

raw machine-readable入力をfixtureにします。

- JSON Schema 2020-12対応keyword
- raw JSON numberをtoken文字列で受け、共通numeric validator後にcanonical integer / exact decimalへ正規化する
- scalar / nullの`enum / const`を処理し、object / array値はsubtree単位`unsupported`
- `$defs`をlocal `$ref`参照先containerとして扱う
- single typeと`[base, null]`だけを対応し、nullableを`allows_null`へ正規化
- `properties / items` traversal
- JSON Schema 2020-12は同一schema resource内の`#/...`だけをlocal `$ref`として解決する
- root `$id`はmetadataとして許可し、nested `$id`、`$anchor / $dynamicAnchor / $dynamicRef`、外部URI referenceをruntime-v1 `unsupported`にする
- JSON Schema 2020-12で`$ref` siblingの対応keywordも評価し、`$ref`だけを見てsiblingsを捨てない
- cyclic local `$ref` subtreeは`unsupported`
- OpenAPI 3.0はJSON Schema 2020-12と別semanticsで解釈し、`#/components/...`のlocal referenceをOpenAPI Reference Object規則で解決する
- OpenAPI Reference Objectの追加propertyをsibling Schema assertionとして扱わず、runtime-v1では追加property付きReference Objectを`unsupported`
- external `$ref`は事前dereference要求
- OpenAPI 3.0 `nullable` / boolean exclusive boundary
- OpenAPI `context=request|response`と`readOnly / writeOnly + required`の方向別意味
- 同一propertyの`readOnly=true && writeOnly=true`を拒否
- HTML constraint validation
- html-control runtime-v1は`text / number / date / datetime-local`だけをconstraint生成対象にする
- `disabled=true`または対応typeの`readonly=true`ではconstraint validation targetを生成しない
- `type=text`でvalidationへ適用される`pattern`を無視せず`unsupported`とし、Python `re`で代用しない
- `multiple`がvalidation意味を持つtypeはruntime-v1対応外として`unsupported`にする
- unsupported applicator
- `$schema`とroot `$id`だけをmetadataとして許可し、annotation allowlistだけをvalidation非影響として許可
- unsupported keywordが意味へ影響するsubtreeだけを局所`unsupported`
- 親validation意味を左右する場合は親subtree全体を`unsupported`
- HTML `pattern`を対応済みconstraintとして扱わず、適用されるcontrolでは`unsupported`を返す
- JSON Schema `multipleOf` → `grid(base=0, step=m)`
- HTML `number`はstep省略時default step=1、`step=any`はgridなし、step baseは`min → value → 0`の順で固定し、minなしを即unsupportedにしない
- invalid / zero / negative HTML stepの扱いをruntime-v1で固定し、制約なしとしてcompleteにしない
- date / datetime-local系stepはruntime-v1 `unsupported`
- `derived.ep_inputs / derived.bva_boundary_skeletons / derived.combinatorial_constraints / derived.test_data_requirements`を固定schemaで出す
- BVAはboundary skeletonへLLMが`mode / coverage_selection_reason`だけを追加し、固定builderで`bva.py` inputへする
- range / enum / requiredはEP / BVA / combinatorial / test dataへ、gridはschema Coverage / BVA / combinatorialだけへ渡す

### UI pattern

- `pattern_key / name / alias`のcatalog全体一意性と相互衝突
- pattern内`candidate_key`一意性とcategory許可値
- `ui:<pattern_key>:<candidate_key>` stable target
- catalog SHA-256
- catalog変更で旧結果stale
- external referenceをAuthorityへ昇格しない
- 未知patternを自動登録しない

### test data requirement

- scalar equality / enum set / numeric・date・datetime range / version range / boolean
- test environmentと同じcross-operator intersection
- incompatible constraint / empty intersection
- unsupported operatorまたは安全にintersectionできない型組合せ
- `source_target_versions[]`で`target_ref / target_content_fingerprint / generation_fingerprint`を保持し、`target_key`単独やstable IDだけをidentityに使わない
- 実データを自動取得しない

### Random Testing

- `pcg32-v1`のstate / seeding / XSH RR / rejection sampling
- seed=42固定raw output vector
- non-power-of-two bound（少なくともbound=10）のbounded integer固定vectorでrejection発生を含め、単純modulo実装を検出する
- 同seedで同列
- seed差
- `uniform_finite`: typed value、non-empty / duplicate拒否、宣言順sample mapping
- `uniform_integer`: inclusive min/max、domain size `<= 2^32`
- `categorical`: typed value、positive integer weightのみ、value重複拒否、weight合計 `<= 2^32`、宣言順累積区間
- 全distributionが復元抽出で同値の再出現を許可
- case count limit
- 一般Coverage 100%を作らない
- `required_case_count / generated_case_count / complete`による終了条件

### Metamorphic Testing

- `follow_ups[]`の`follow_up_key`一意性と1..10,000件
- 各follow-upの`transforms[]`を宣言順に逐次適用
- `set / add_decimal / multiply_decimal / append / permute / sort`のrequired parameter
- `sort`はnumber homogeneous arrayをexact numeric order、string homogeneous arrayをUnicode code point順で処理し、異種型 / boolean / null / enumを`unsupported`にする
- JSON pathはobject key / array indexだけ
- `permute` indicesが完全bijection
- `expected_relation.output_kind`必須
- `equal / not_equal`、numeric monotonic、unique scalar array subset / supersetの`op × output_kind`互換性
- unsupported transform / path / relation
- source → follow-up traceability
- `required_pairs = source数 × follow_up数`
- 一般Coverage 100%を作らない
- 各MRを1回扱っただけで十分と判定しない
- relation自体をscriptが創作しない

### Coverage target materialize / Disposition

- semantic-only Error Guessing、fork-join、whole-model unsupported fallbackでも`materialize_coverage.py`をdispatchする
- `active_model_metadata[]`でruntimeなしmodelのTCN所属を検証する
- semantic itemのstable key / previous mapping / reuse CIを検証し、別item・別model・runtime target CIへの横取りを拒否する
- test data requirement Entity fingerprint変更をCI / TC staleへ反映する

- materialize入力modelは`runtime_status=ok / result_status=ready / deterministic_generated=true / freshness=current`を必須にし、supportedまたは分離済みpartialだけ許可する
- unresolved / blocked / stale modelからCIを作らない
- generator targetは`materializable=true|false`を必須にし、`true`だけmachine targetとしてCI materialize / target Dispositionの対象とする。adapter / diagnostic専用`false` targetはmachine evidenceとして保持してCIを要求しない。一方、fork-join branch等の正規Coverage基準上必要な`false` targetは、現在target versionを参照するsemantic Coverage Itemまたは既存Skillで許可されたDispositionへ閉じるまで完了させない
- 同一target_refへ`target_annotations[]`と`target_dispositions[]`を同時指定しない
- CI化するtargetだけ`target_annotations[]`を1対1で要求し、unknown / duplicate target_refを拒否する
- CI化targetはgenerator別にPlanで固定したcanonical `execution`とruntime計算済み`execution_fingerprint`を必須とする
- combinatorialはfull rowへ`row_ref=sha256(canonical assignment)`を付与し、各SAT targetをそのtargetをcoverする生成済みrowのうち生成順で最初のrowへ対応付ける。同じrowを使うtargetは同じ`execution_fingerprint`になる
- `classification_tree.py / cause_effect.py / schema_cases.py / ui_pattern_candidates.py`は直接CI化せず、Planで定義したderived model / 意味判断先だけをmaterialize対象にする
- stateのinvalid transitionは`attempted_transition`をcanonical executionへ保持し、valid transition列へ混ぜない。flowのnode / edgeはinitialから対象までの最短witness、bounded-pathはinitial→terminal pathを使用する。fork-join branchは単一`edge_sequence`へ順序化せず、semantic Coverage Itemの`source_target_versions[]`が現在branch targetと一致するまで完了させない
- annotation / Dispositionの`target_content_fingerprint / generation_fingerprint`が現在target / modelと一致しない場合は拒否する
- `target_dispositions[].handling`は`対象外 / 別テストレベル / 残存リスク / ブロック中 / 重複`だけを許可する
- `重複`ではcurrentな`covered_by_target_version={target_ref,target_content_fingerprint,generation_fingerprint,execution_fingerprint}`を必須にする
- generator生成後に`成立不能`Dispositionへ変更しない。成立不能根拠が得られた場合はmodel / constraintを更新してgeneratorを再実行する
- Disposition済みtargetへCIを採番せず、同時にgeneratorの`coverage_summary.required / covered / complete`を変更しない
- `ブロック中`Dispositionはworkflow完了を妨げる
- materialize outputから生成したCI Machine Entityは、machine target由来ではcanonical `execution`まで保存する。semantic item由来ではstable `semantic_item_key`と`semantic_item_text / source_target_versions[]`を保存し、本文変更でCI content fingerprintを変える
- stable target_refのままtarget content / executionが変わった場合、CI Machine Entityのcontent fingerprintが変わり、参照TCへstaleが伝播する
- `test_data_requirement_refs[]`は同じmaterialize inputの`data:<requirement_key>`へ解決できることを必須にする
- merge groupはDispositionされていない同一TCN・同一`model_key`のtargetだけを含み、全targetの`execution_fingerprint`と`expected_result_root`の一致を要求する
- 異なるmodel / 技法のtargetを同一CIへmergeせず、同一TCで実行できる場合は`case_structure.py`の複数`ci_refs[]`で表現する
- merge targetの追加test data requirementsを§16と同じintersection規則で統合し、矛盾 / unsupportedならmerge拒否
- 同じ期待挙動groupを再利用すると判断した場合は既存`expected_result_root`を維持し、意味不変のkey churnをsemantic evalで検出する

### test case structure

- CIの親TCNとTCの`tcn_refs[]`、TCNの`tr_refs[]` unionとTCの`tr_refs[]`を整合検証する
- CI canonical `execution` / semantic item本文、environment / test data requirementをMachine Entityから入力し、Markdown再解釈なしでTCを検証する
- requirement content変更で関連TCをstaleにする

- Dispositionは完全Machine Entity参照を持つ共通schema`{upstream_entity, handling, reason, authority_refs[], covered_by_entity}`を使う
- `draft_key`を使ってLLM draftと最終TC ID mappingを安定追跡する
- `previous_tc_ids[].status=active|deleted`を検証し、reuseはactiveだけ、新規はactive / deletedを含む最大番号+1とする
- 削除済みTC IDを再利用せず、999超過は`id_space_exhausted`
- outputの`tc_id_state[]`にdeleted IDも残し、次回入力の正本にする
- TCN / CI → TC closure
- linked + disposed重複
- unknown upstream
- highest priority
- 低い指定優先度 + 空の`priority_override_reason`をviolation
- 低い指定優先度 + 非空override reasonは値を保持し、自動補正しない
- `title_or_purpose / tr_refs / preconditions / test_data / steps / postconditions_or_cleanup`をruntime inputへ保持し、structure scriptが意味内容を生成・欠落させない
- numbered expected result / Authority
- runtime output + draft意味fieldからTC Machine Entityを固定builderで生成する
- runtime検査後の再検査

### traceability

- Dispositionはstructure scriptと同じ共通schemaをそのまま受け取り、Markdownから再解釈しない
- `traceability.py`と`workflow_runtime.py`が同じ`runtime_contract.py` freshness関数・同じ`runtime_units / current_entities / current_runtime_units / expected_runtime_units / expected_entities` schemaを使う
- Machine Entityの`upstream_entity_dependencies[] / runtime_dependencies[]`から`entity_freshness[]`を同じ結果として算出し、missing / generation mismatch / dependency cycleを検出する
- `traceability.py`は`workflow_runtime.py` resultを依存入力にせず、`coverage-analysis::artifact:traceability:all`自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`へ含めない。self inclusionを`invalid_input`として回帰検出する
- Authority / Risk → TRまたはDisposition
- TR → TCNまたはDisposition
- TCN → CI → TC、CIなしTCN → TC、または既存Skill契約で許可されたDisposition
- 許可直接edge以外をclosure根拠にしない
- Dispositionのhandling / reason / Authority条件
- missing / orphan / unknown
- stale downstream
- 技法Coverageを再計算しない

## 5. stable identity・再実行の回帰

- TR / TCN / model / TCはprevious activeでcurrent reuseされないIDをdeletedへ遷移し、deleted rowをfull snapshotに保持する
- 複数new draftはcanonical `draft_key`順、semantic CIはcanonical candidate順で採番し、raw入力配列順へ依存しない

- 同じmodel改訂で`model_key`維持
- 新modelは同じ`model_type`の最大番号+1、新系列は001
- 削除keyを同系列で再利用しない
- qa-workflowの再利用元有無で成果物系列を一意に判定
- TR / TCN / TC / modelは意味上同一の既存Entityを再利用できる場合だけID維持し、runtimeがsemantic matchingしない。LLMはreuse/newだけを決め、番号はruntimeが割り当てる
- TR / TCN / TCの新規IDは最大番号+1、999到達後は`id_space_exhausted`。model keyは同じ`model_type`の最大番号+1で3桁以上を許可する
- 同じmodel keyを複数TCNへ所属させない
- `target_ref = sha256({model_key,target_key})`を独立再計算
- 同じTCN内に同名target keyを持つ複数modelがあってもtarget_refが衝突しない
- 初回mappingはruntime target / semantic itemを`(model_key, source_kind, source_key)`のcanonical順でCI01から採番する
- existing mappingは同一target_refで維持し、新target_refだけ最大番号+1
- 同じtarget_refで`target_content_fingerprint`だけが変わった場合はCI IDを維持するが、関連CI / TCを`要再検証`へし、以前のannotation / Disposition / merge判断を現在targetへ自動適用しない
- Disposition targetはCI mapping対象から除外し、generator Coverage値は変更しない
- target_ref内容不一致、1 target_ref→複数CI、parent mismatchを拒否
- `target_annotations[]`が全targetへ1対1対応し、unknown / duplicate target_refを拒否する
- annotation / Dispositionの`target_content_fingerprint`が現在machine targetと一致しない場合は拒否する
- merge groupの全targetについて保存fingerprintが現在machine targetと一致しない場合は拒否する
- `expected_result_root`は同一TCN内の内部用local keyで、同じ期待挙動と意味判断したtargetだけ同値になる
- 同一CIへの複数target_refは、同じ`expected_result_root`を持つ同一merge groupだけ許可する
- unmerged→mergedでは既存CIの最小番号を存続CIとし、他CIをdeletedへする
- merge groupへのtarget追加 / 削除、CI→Disposition、Disposition→CIの各状態遷移で`_02` §7.2.2どおりID維持・deleted・再採番を行う
- merge解除時は辞書順先頭targetへ既存CIを維持し、残りを過去使用済み最大番号+1で再採番して関連TCを`要再検証`へする
- `target_mapping_state[] / ci_id_state[]`にinactive / deleted履歴を残す
- 消滅targetで下流`要再検証`
- 同じ実行を2回行ってmachine evidenceが重複しない
- stale rowを完了扱いしない

## 6. 既存validatorの更新

### 共通ID

`CI\d{2,}`を許可します。ただし`TCN-\d{3}-CI\d{2,}`だけをCIとして認識し、`SPEC-001-CI01`等を誤認しません。

### `test-analysis`

- risk scheme分岐
- technique selection machine evidence
- change graph
- environment requirement

### `test-requirement-design`

既存`TR-D001`〜を維持し、runtimeと同じfixtureで独立照合します。

### `test-condition-design`

自由文検索依存を減らし、技法固有key、model、target、Coverage、runtime metadataを検査します。

正規化model fingerprintと保存済みmachine evidenceの不一致を検出します。

### `test-case-design`

既存構造契約を維持し、runtimeと独立にclosure / priority / Authority mappingを検証します。

### `coverage-analysis`

`assets/output-template.md`を次のように更新します。

- `カバレッジ基準確認`へ`Model Key`列を追加
- `カバレッジ項目の扱い`へ`Model Key`列を追加
- `陳腐化 / 孤立分析`へ`Model Key`列を追加
- modelを持たないlegacy / E2E経路では空欄を許可

validatorはruntime traceabilityと独立にmissing / orphan / unknown / staleを検出し、stale / gapをTCN / CIだけでなく関連`model_key`まで追跡します。

### `question-analysis`

`assets/output-template.md`の`不明点 / 質問一覧`と`ブロック中範囲`へ、既存の`再開対象 / 実行範囲`とは別に`Runtime Skill`、`Runtime Unit Key`、`Model Key`、`Target Key`、`Generation Fingerprint`列を追加します。

- `再開対象 / 実行範囲`は既存`QUESTION-D017`のSkill用途判定だけに使用する
- `Runtime Skill`と`Runtime Unit Key`はruntime issue由来の質問で必須で、組を一意identityとして扱う
- model issueでは`Model Key`を必須、artifact全体script issueでは空欄
- target固有issueだけ`Target Key`を必須
- runtime生成issueでは`Generation Fingerprint`を必須にし、回答適用時に現在runtime unitのgenerationと一致することを確認する。timeout等のcaller生成issueだけ空欄を許可する
- 同じブロッカーIDについて質問一覧とブロック中範囲のRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprintが一致することをvalidatorで確認する
- runtime issue由来でない質問では5列を空欄にできる
### `qa-workflow`

既存Skill状態表は`qa-workflow`出力時に引き続き必須とし、`WF-D009`は維持します。ただし永続正本にはせず、成果物metadataから再構築可能にします。

`assets/workflow-state-template.md`へ別表`runtime状態`を追加します。

`Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue`

- `Runtime Unit Key`は同一Skill内一意
- model scriptではModel Key必須、artifact全体scriptでは空欄
- `Support Status = supported / partial / unsupported / unknown`
- `Result Status = ready / unresolved / blocked`
- `Freshness = current / stale`
- `Runtime Status = ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Runtime Required / Deterministic Generated = Yes / No`
- `Fallback Reason`は空欄 / `outside_supported_subset` / `python_unavailable`
- Skill状態表の`WF-D012`は従来どおりSkill + 対象にだけ適用し、runtime状態表へ流用しない
- ワークフロー全体`完了`では全runtime unitが`Result Status=ready / Freshness=current`であることを追加検査する
- `Runtime Required=Yes`のunitでは、さらに`Deterministic Generated=Yes`を要求する
- `Runtime Required=No`のfallback unitも`Result Status != ready`なら完了を妨げる
- `Support Status=partial`では`unsupported_items[]`が許可されたhandling、必要なcurrent`covered_by_entity`、既存Disposition条件を満たすclosureへすべて閉じていることを要求する。closure行の存在だけでは完了条件を満たさない
- `workflow_runtime.py`が上流Entity fingerprint、`upstream_runtime_units`、runtime metadata、`unsupported_item_closures[]`からstale / 完了可否を計算し、LLMが表を手計算しない
- partial supportは全unsupported item keyにclosureがあり、closureの`generation_fingerprint / reason_code`が現在unsupported itemと一致することに加え、`handling`が許可集合内であることを要求する。`llm_fallback / 重複`はcurrentな`covered_by_entity`の完全identity / fingerprint必須、`ブロック中`は完了不可、その他Dispositionは既存Skill条件を満たすことを検証する。whole-model unsupportedも同じclosure規則と`generation_fingerprint`一致を必須にする

完了条件・再利用条件へ次を追加します。

- envelope / runtime / generator contract version
- upstream Entity別content fingerprint
- input / model / generation fingerprint
- stale派生成果物
- runtime unit単位の`要再検証` / ブロック中
- runtime未実行 / unsupportedとQA成果物状態の分離
- legacy成果物の昇格
### output eval fixture schema

runtime対応Skillの`evals/output/cases/*/expected.json`では、既存fieldに加えて必要なcaseだけ次の`runtime_contract` objectを持てるようにします。Machine Entityを持つSkillではruntime有無にかかわらず`machine_entities` objectも使用できます。

```json
{
  "machine_entities": {
    "expected_entities": [
      {"skill":"test-condition-design","entity_type":"tcn","entity_ref":"TCN-001"},
      {"skill":"test-condition-design","entity_type":"ci","entity_ref":"TCN-001-CI01"}
    ],
    "expected_stale_entities": []
  },
  "runtime_contract": {
    "expected_skill": "test-condition-design",
    "expected_runtime_unit_key": "model:comb-001",
    "upstream_entities": [
      {"skill":"spec-analysis","entity_type":"authority","entity_ref":"SPEC-001","content_fingerprint":"sha256:..."}
    ],
    "expected_target_keys": [],
    "expected_support_status": "supported",
    "expected_runtime_status": "ok",
    "expected_result_status": "ready",
    "expected_runtime_required": true,
    "expected_deterministic_generated": true,
    "expected_fallback_reason": null,
    "expected_freshness_status": "current",
    "expected_target_id_map": []
  }
}
```

- `machine_entities.expected_entities[]`は成果物から抽出した`(skill, entity_type, entity_ref)`集合と一致させ、各contentはentity type別canonical schemaと人間向け表の主要fieldへ独立照合する
- `spec-analysis`ではruntime_contractなしでMachine Entity fixtureを使用し、Authority表とcanonical Authority contentの一致を検証する
- expected target / Coverageは手書きfixtureから独立計算または明示し、generator出力をexpectedへコピーしない
- `expected_target_id_map`はstateful materialize caseだけ使用し、`{target_ref, target_content_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`配列で保持する
- validatorは全runtime unitの保存済み`Machine Runtime Input / Result`から`input_fingerprint`、model scriptでは`model_fingerprint`、全scriptで`generation_fingerprint`を独立再計算し、fixtureに書いたhash文字列を盲信しない
- upstream Entity差分caseでは無関係Entityの変更が対象modelをstaleにしないことを確認する
- upstream runtime差分caseでは直接依存unitだけがstaleになり、依存していないmodelへ伝播しないことを確認する
- implementation fingerprintはruntime / generator sourceから独立再計算し、fixtureの文字列を盲信しない
## 7. semantic eval

維持・追加する主な確認:

- 正規化modelがAuthority / Risk / TRの意味を必要十分に表している
- partition / boundary / Domain borderの意味
- Decision Table condition / action / constraint
- factor / strength / mixed-strength選択
- state / guard / reset / flow / fork-joinの意味
- CRUD completeness / consistency model
- Syntax-Based Testingのgrammar / production / mutation意味
- operational profile / Random Testing採用
- metamorphic relation
- UI pattern分類
- test data / environment requirement
- merge groupの意味上の妥当性と`target_refs[]`の同一TCN制約
- model内100%を対象仕様全体100%と誤認しない
- scriptがexpected resultを創作していない

semantic referenceをgenerator outputから自動生成しません。

### semantic dataset件数

semantic dataset件数は次で固定します。

| Skill | case数 |
| --- | ---: |
| `test-analysis` | 7 |
| `test-condition-design` | 14 |
| `adversarial-review` | 8 |
| その他11 Skill | 各2 |
| repository合計 | 51 |

- `test-analysis`: 既存2 caseを維持し、Domain / CRUD / Random / Metamorphic / Syntax-Basedの採用判断を主対象とする5 caseを追加する
- `test-condition-design`: 既存2 caseを維持し、Domain / CRUD / Random / Metamorphic / Syntax-Basedに加え、Decision Table / Cause-Effect、Classification Tree / combinatorial strength、Round-trip / n-switch、flow、schema / OpenAPI、UI pattern、test data / environment、merge / Coverage範囲の意味判断を各caseで最低1回検証できるよう合計14 caseへする。1 caseで複数責務を検証してよいが、各責務とcase IDの対応表を`EVALS.md`へ記録する
- `adversarial-review`: 既存2 caseを維持し、下記6誤用を主対象とする6 caseを追加する
- case IDはSkill内一意
- `tests/skills/evals/semantic/test_semantic_datasets.py`はSkill別expected count mapと合計51を検証し、`EVALS.md`の意味判断責務→case対応が空になっていないこともrepository testで確認する

`adversarial-review`には技法アルゴリズムを複製せず、次の6 caseを追加します。

- Random Testingを一般的な「100% Coverage」と記載する
- Metamorphic TestingでMRを1回だけ扱ったことを十分なCoverageと断定する
- Domain Testingでrelation別required pointを欠落させる
- CRUD completenessだけでconsistencyも完了したと断定する
- Syntax-Based Testingのmutation candidateをAuthorityなしで製品上invalidと断定する
- 新規技法のexpected resultをAuthorityなしで創作する
### 発火評価

既存queryは削除せず、新規技法5種の責務境界を追加します。件数は次で固定します。

| Skill | train | validation |
| --- | ---: | ---: |
| `test-analysis` | 24（positive 12 / negative 12） | 20（positive 10 / negative 10） |
| `test-condition-design` | 24（positive 12 / negative 12） | 20（positive 10 / negative 10） |
| その他12 Skill | 各12（6 / 6） | 各8（4 / 4） |
| repository合計 | 192 | 136 |

repository全体は328 queryです。

`test-analysis` / `test-condition-design`では、Domain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testingの各技法についてtrainとvalidationの双方に次の10 queryを追加します。

1. `test-analysis` positive: 技法を採用すべきか判断する依頼 × 5技法
2. `test-analysis` negative: その技法で具体的なCoverage / 条件を設計する依頼 × 5技法
3. `test-condition-design` positive: 技法を使って具体的なCoverage / 条件を設計する依頼 × 5技法
4. `test-condition-design` negative: 技法の採用可否だけを判断する依頼 × 5技法

さらに各datasetへ、各Skillについて「技法とは何か説明して」という説明依頼negativeを1件と、既存責務の一般positiveを1件追加してbalanceを維持します。train / validation間のquery重複は禁止します。

`.github/workflows/validate-skills.yml`は上表のSkill別exact count、positive / negative exact count、repository合計328を検証します。`EVALS.md`へ新規query IDと責務境界の対応を記録します。
## 8. qa-workflow統合評価

次の9シナリオをE2E fixture / smokeとして検証します。

1. 新規設計
   - test-analysisで技法選択
   - model作成
   - runtime生成
   - CI / TC
   - coverage-analysis
   - workflow完了

2. 上流Authority / runtime変更
   - upstream Entity content fingerprint変更
   - runtime `generation_fingerprint`へupstream Entity fingerprintが含まれ、同じAuthority IDでも内容変更で別generationになる
   - 保存済みsemantic model / draftの`upstream_entity_dependencies[]`不一致をruntime再実行前に検出し、担当Skillで意味再確認するまで古い入力を再投入しない
   - Machine Entityのupstream / runtime dependencyからEntity freshnessがstaleになり、`traceability.py`と`workflow_runtime.py`で同じ結果になる
   - 人間向け説明文だけの変更ではfingerprint不変
   - 直接依存する上流runtime unitのgeneration fingerprint変更
   - 影響modelと依存下流unitだけ`要再検証`
   - 無関係modelへstaleを伝播しない
   - stale派生物を拒否
   - 再生成後に再利用可能

3. model / generator変更
   - model意味変更で`model_fingerprint`変更
   - generator contract / static data / generator implementation変更で`generation_fingerprint`変更
   - contractを変えないbug fixでもimplementation fingerprint差で旧machine evidenceを再利用しない
   - 旧machine evidence拒否

4. 局所ブロック
   - 1 modelだけ未解決
   - `question-analysis`往復で`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`維持
   - 質問後にgenerationが変わった場合は以前の回答を自動適用せず、現在世代でissueが残るか再評価する
   - 独立modelは継続
   - 成果物metadataから状態を再構築し、qa-workflow出力時は既存Skill状態表と新しいruntime状態表へ反映
   - workflowは部分完了

5. runtime support / fallback / unavailable
   - model全体が対応subset外ならscript自身が`support_status=unsupported / runtime_status=unsupported / runtime_required=false / deterministic_generated=false / fallback_reason=outside_supported_subset`を返し、既存Skill契約を満たすLLM fallbackで完了可能
   - 既存fallback成果物を再利用するときも現在runtimeでsupport判定を再実行し、runtime更新でsupportedになったfixtureを古いfallbackへ固定しない
   - 一部subset外なら`support_status=partial`でsupported部分を生成し、unsupported itemをfallback / Dispositionへ閉じるまで完了不可
   - `runtime_required`をcaller inputから与えず、runtimeのsupport判定出力として検証する
   - Python unavailableなら`support_status=unknown / runtime_required=true / runtime_status=not_run / result_status=blocked / deterministic_generated=false`を保持し、workflowを完了にしない
   - QA成果物状態とruntime状態を分離
   - 「決定論的生成済み」と誤表示しない

6. legacy成果物
   - 旧成果物を参照
   - 変更時に新modelへ昇格
   - 以後version / fingerprint契約で再利用

7. runtime利用確認
   - 全runtime scriptについてdispatch fixtureから期待script pathへ到達し、CLI実行結果metadataが存在する
   - `test-analysis: E2E対象選定`と`coverage-analysis: TC → E2E実装 / E2E実装 → 実行結果`では本Planruntimeをdispatchしない
   - supported inputが`unsupported`になる、またはsupport判定前にAgentがscriptを省略する場合は失敗
   - 保存済み`Machine Runtime Input / Result`を決定論的に抽出してround-trip検証できるが、workflow再利用では保存済みresultをcurrent cacheにせず現在scriptを再実行する
   - LLM手計算だけの成果物を決定論的生成済みと判定しない

8. 途中工程開始
   - ユーザーが技法を明示したTRから`test-condition-design`を開始し、`Selection Source=user`をmodel metadataへ保持する
   - ユーザー明示がなくても`test-condition-design`自身が問題構造から技法を選べる正常経路を`Selection Source=condition_design`で検証する
   - 既存modelをreuseした場合は元のSelection Source / selection keyを維持し、reuseを`existing_artifact` sourceへ置き換えない
   - `test-analysis`の技法選択行を作るためだけに上流へ戻らない

9. 実Agent runtime smoke
   - 全scriptのdispatch網羅はCIで保証し、実Agent smokeを全script分へ重複させない
   - 実装完了前にAgent環境で`test-analysis`と`test-condition-design`の代表promptを各1件実行し、Python runtime起動、stdout envelope parse、machine result採用、Markdown保存・再読込まで確認する
   - 1件は可能な範囲で大きいmachine outputも扱い、artifact transport上限がruntime 16 MiBより低くないか確認する
   - command / script path、return code、stdout envelopeが確認できる実行logをPRの検証記録へ残す
   - runtime適用可能なpromptで`deterministic_generated=true`になることを確認する

## 9. CI

既存`.github/workflows/deterministic-output-evals.yml`へ追加します。

```bash
python -m compileall -q skills/test-analysis/scripts
python -m compileall -q skills/test-requirement-design/scripts
python -m compileall -q skills/test-condition-design/scripts
python -m compileall -q skills/test-case-design/scripts
python -m compileall -q skills/coverage-analysis/scripts
python -m compileall -q skills/qa-workflow/scripts
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v
```

既存のdeterministic eval、semantic dataset validation、Skill validationも維持します。

`.github/workflows/validate-skills.yml`のrepository eval structureは次へ変更します。

- trigger dataset: 上記Skill別exact countとpositive / negative exact countを検証
- total trigger query: 328
- train / validation disjointを維持
- semantic dataset: `test-analysis=7 / test-condition-design=14 / adversarial-review=8 / その他=2`、repository合計51を検証

`validate-skills.yml`へruntime unit testを重複追加しません。runtime testは`deterministic-output-evals.yml`だけで実行します。

## 10. Skill単体移植性

次の6 Skillを単体コピーして代表scriptをCLI実行します。

- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `qa-workflow`

確認:

- repo rootのeval helperをimportしない
- 6 Skillの`scripts/runtime_contract.py`がLF正規化後のSHA-256で一致
- network不要
- runtime dependencyがPython 3.11標準ライブラリだけで、外部package manifestを必要としない
- generator scriptがSkill-local Python moduleとしてimportできるのは`runtime_contract.py`だけで、fingerprint対象外helperへ実行ロジックを逃がさない
- Skill rootからscriptを解決
- stdout envelopeを読める
- Python unavailable時にSkill全体を利用不能と誤判定しない
- runtime未実行を決定論的生成済みと表現しない

## 11. ドキュメント更新

### README

- LLM / runtime責務境界
- contract / static data version
- stale / legacy / 再利用
- Python要件
- Skill package内script

### `spec-analysis`

- runtimeは追加しない
- `assets/output-template.md`へAuthorityの`Machine Entities` canonical JSON blockを追加する
- Authority表とMachine EntityのID / 種別 / 現在有効な内容 / 適用範囲 / 情報源 / 関係 / 関連Authorityの一致をvalidatorで確認する

### `test-analysis`

- `SKILL.md` / `references/guidance.md`へ新規正規技法と選択条件を追加
- `assets/output-template.md`へ`Machine Entities`、`Machine Runtime Input / Result`、`Selection Source`、技法選択machine evidence、undetermined signalの`resolved / selection_not_affected / question`閉鎖状態を追加
- Product Risk Machine EntityはLLM意味fieldと`risk_matrix.py`の`level / mapped_priority`を固定builderでjoinする
- risk scheme / priority mapping
- change graph
- environment requirement
- deterministic / semantic / trigger evalを更新

### `test-requirement-design`

- runtime structure検査の処理順
- `assets/output-template.md`へTRの`Machine Entities`、`Machine Runtime Input / Result`、TR active / deleted ID stateを追加

### `test-condition-design`

- `SKILL.md`の対象技法を更新
- `references/coverage-techniques.md`へ全実装技法の適用条件、Coverageまたは終了条件を追加
- `assets/output-template.md`へTCN / model metadata / CI mappingの`Machine Entities`、`Machine Runtime Input / Result`、active / deleted ID state、stable target / CI mappingを追加
- Random / Metamorphicは一般Coverage 100%を定義しない
- runtime metadata
- test data requirement
- deterministic / semantic / trigger evalを更新

### `test-case-design`

- runtime structure検査の処理順
- `assets/output-template.md`へTCの`Machine Entities`、`Machine Runtime Input / Result`、TC active / deleted ID stateを追加
- stable ID / active・deleted ID state / stale

### `coverage-analysis`

- `assets/output-template.md`へ`Machine Runtime Input / Result`を追加
- `assets/output-template.md`のカバレッジ基準確認・カバレッジ項目の扱い・陳腐化 / 孤立分析へ`Model Key`列を追加
- stale / fingerprint / test-design traceability
- model_key単位のgap / stale参照
- deterministic validatorでModel Keyの既知model照合を追加

### `question-analysis`

- `不明点 / 質問一覧`と`ブロック中範囲`へ`Runtime Skill / Runtime Unit Key / Model Key / Target Key / Generation Fingerprint`列を追加
- runtime issueの`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問・ブロック・再開まで保持
- `再開対象 / 実行範囲`へmodel keyを流用せず、既存`QUESTION-D017`契約を維持

### `qa-workflow`

- `assets/workflow-state-template.md`へ`workflow_runtime.py`の`Machine Runtime Input / Result`を追加
- `scripts/workflow_runtime.py`を追加し、runtime metadata集約、Machine Entityのupstream / runtime dependency、runtime unit fingerprint比較、runtime / Entity freshness、stale伝播、機械的完了判定をLLMから分離
- runtime dependency identityは`(skill, runtime_unit_key)`で固定する
- `workflow_runtime.py`自身を評価対象`runtime_units[]`から除外し、self dependencyを禁止する
- missing dependencyはstale + blocker、duplicate / cycleは`invalid_input`
- 既存Skill状態表を維持し、別表`runtime状態`を追加
- model単位状態を成果物metadataから再構築
- legacy昇格
- upstream Entity別content fingerprint / Machine Entityの`upstream_entity_dependencies[] / runtime_dependencies[]` / upstream runtime dependency / stale伝播
- `traceability.py`と同じ`runtime_contract.py` freshness関数を使用し、workflow_runtime resultをtraceabilityの依存入力にしない
- 完了条件

### `EVALS.md` / `ASSERTIONS.md`

新契約と独立評価を記録します。

## 12. 実装順序

### Step 0: 基準再確認

- main最新
- 関連Skill / validator / CI
- branch差分

### Step 1: 共通runtime契約

- stdin / stdout / cwd非依存のCLI契約
- Skill実行時subprocessの30秒安全timeout
- strict JSON
- output envelope / status対応表
- canonicalization
- envelope / runtime / generator contract version
- static data versions
- input / model / generation fingerprint。generationにはsort済み`upstream_entity_fingerprints`を含める
- runtime / generator implementation fingerprint
- `entity-state-v1` Machine Entity schema、`entity_type`、`content_fingerprint`、`upstream_entity_dependencies[] / runtime_dependencies[]`、identity=`(skill, entity_type, entity_ref)`
- `spec-analysis` Authority Machine Entity blockとvalidator。`spec-analysis`へruntimeは追加しない
- `(skill, runtime_unit_key)` upstream runtime dependency
- support_statusと対応subset判定。`runtime_required`は入力fieldにせずruntime出力として導出
- 全runtime unitの`Machine Runtime Input / Result`保存、決定論的抽出 / round-trip再投入。workflow再利用では保存済みresultをcurrent cacheにしない
- 通常stdin 2 MiB / 集約stdin 16 MiB / stdout 16 MiB / depth / 探索node hard limit
- tie-break
- runtime / Machine Entity dependencyを評価する共通freshness関数。6 Skillの`runtime_contract.py`で同一実装にする
- structured issue / blocking
- 複数用途Skillのruntime dispatchを`test-analysis: テスト分析`、`coverage-analysis: テスト設計`へ限定する
- 6 Skillの`runtime_contract.py`同一実装とLF正規化implementation fingerprint

### Step 2: identity / workflow基盤

- canonical technique slugと内部`model_type`を分離し、dispatchは`model_type → generator`固定表だけを使う
- 内部adapterは正規技法を所有せず、Coverage child modelが`selection_source / selection_key / technique_slug`を保持する。1 selection → 複数modelを許可する
- `requirement_structure.py` / `case_structure.py`によるTR / TC採番
- qa-workflow再利用元による成果物系列判定
- 既存成果物のsemantic model / draftを再利用する前に保存`upstream_entities[]`とMachine Entityの`upstream_entity_dependencies[]`を現在Entityと比較し、不一致なら担当Skillへ`要再検証`として戻すpreflight
- 既存TR / TCN / TC / modelのID再利用規則、active / deleted machine state、999上限
- 1 model key = 1 TCN所属
- `materialize_coverage.py`本体を実装し、`active_model_metadata[]`、runtime target、stable semantic item、previous semantic mappingを同じCI allocator / Machine Entity builderへ載せる
- generator別`materializable` / canonical `execution`契約を共通post-processへ接続し、adapter専用generatorを直接CI化しない
- CI化targetのcanonical `execution` / `execution_fingerprint`を共通post-processで生成し、mergeは同一TCN・同一model・同一execution・同一expected resultだけ許可する。異なるmodelはCIを分ける
- merge / unmerge / target追加削除 / CI↔DispositionのID状態遷移とdownstream stale
- 同じtarget_refの内容変更時にCI IDを維持しつつannotation / Disposition / mergeと関連TCを`要再検証`へ戻す
- upsert / stale / freshness status
- upstream Entity別content fingerprint / semantic dependency / upstream runtime dependency
- Machine Entityのruntime dependencyとsemantic dependencyからEntity freshnessを計算し、traceabilityとworkflowで同じ共通関数を使用する
- question-analysisのRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprint保持
- coverage-analysisのModel Key / Disposition追跡
- 各Skillがactual集合から独立した固定sourceから`expected_runtime_units[] / expected_entities[]`を生成し、`workflow_runtime.py`が実際集合との完全一致を検査する。expected生成で`current_entities[] / runtime_units[] / current_runtime_units[]`や保存済みMachine Entity blockを参照しない
- 正常fixtureからMachine Entity 1件を削除しても`expected_entities[]`が変わらずmissing blockerになる回帰と、runtime unit 1件を削除しても`expected_runtime_units[]`が変わらずmissing blockerになる回帰を必須にする
- `workflow_runtime.py`によるSkill状態表 + runtime状態表（model / artifact両runtime unit）の機械集約。`qa-workflow::artifact:workflow_runtime:all`自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`の3集合すべてから除外し、self inclusionを`invalid_input`にする
- legacy昇格

### Step 2.5: 代表generatorと共通経路の成立確認

後続generatorを量産する前に、代表generatorとして`equivalence_partitions.py`を先行実装し、次を同一PR内で通します。Step 5ではEPを再実装せず、この実装へBVA等を追加します。

`LLM正規化 → Machine Entity保存 → semantic dependency preflight → dispatch → runtime再実行 → Machine Runtime Input / Result保存 → target annotation → CI materialize → validator → workflow_runtime → Markdown再読込 → semantic dependency preflight → runtime再実行`

この時点で実Agentのartifact transport境界も確認し、16 MiB未満の上限が必要なら後続generator実装前に`runtime-v1`へ固定します。

ここで見つかった共通契約不整合はStep 1 / 2へ戻して修正します。この確認を完了扱いの区切りにはせず、修正後は同じPRでStep 3以降の全対象を実装します。

### Step 3: test-analysis

- runtimeは`対象 / 実行範囲=テスト分析`だけでdispatchする
- Product Risk / 技法選択 / change graph / environment requirementのMachine Entityを固定builderで保存する
- risk scheme / priority mapping
- technique candidates / Selection Source / undetermined signal閉鎖
- 新規正規技法のSkill契約
- trigger eval更新
- change graph / impact。cycleを含むgraphでshortest path 1本だけを返し、同距離はedge key列→node key列でtie-breakする。visitedの実装差でpathが欠落しないことを検証する
- environment requirement

### Step 4: test-requirement-design

- TR draftの本文・テストレベル / 観測方法を含むrequirement structure
- runtime outputと意味fieldをjoinしたTR Machine Entity
- runtime再検査

### Step 5: condition design 基本技法

- Step 2.5で先行実装したEP / Each Choiceの回帰を維持
- BVA 2-value / 3-value target
- Domain Testing Reliable Domain Coverage（`< <= > >= = !=`）とexact rational border arithmetic
- schema / HTML parser / exact JSON number / scalar-null enum・const / root document + local `$ref` / OpenAPI request-response context
- HTML runtime-v1 typeを`text / number / date / datetime-local`へ限定し、disabled / readonlyのconstraint validation除外、pattern / unsupported typeを安全側へ閉じる
- schemaからEP / BVA boundary skeleton / combinatorial / test dataへの固定derived inputとBVA意味parameter join
- test data / environment cross-operator intersection
- 新規技法のSkill / reference / template / eval契約

### Step 6: rule / model技法

- Decision Table / don't-care候補
- Cause-Effect + Authority付きcause constraintのDecision Table伝播
- CRUD
- Syntax-Based Testing

### Step 7: 組合せ

- exhaustive
- constraint付きBase Choice
- Pairwise / N-wise
- mixed-strength
- `classification_tree.py` adapter

### Step 8: state / scenario

- state / transition
- `initial_state_key / reset_key / setup_prefix / coverage_sequence`を持つcanonical state execution
- n-switch / Round-trip（開始stateを保持しrotation同一化しない）
- simple loopのprefix + cycle×N + exit execution
- fork / join

### Step 9: Random / Metamorphic / UI

- `pcg32-v1`固定test vector
- Random completion criterion
- Metamorphic relation / completion criterion
- UI catalog / static version

### Step 10: 全generator統合 / test-case / traceability

- Step 2で実装済みの`materialize_coverage.py`を全generator出力へ接続し、model status / freshness gateを回帰確認する
- 全generatorについて`materializable`の固定値とcanonical `execution / execution_fingerprint` schemaを確認する。combinatorialはpartial target → deterministic full row mapping、state / flowはwitness sequence / path、adapter専用generatorは非materializeを回帰確認する
- mergeは同一model・同一executionに限定し、追加test data requirement参照のintersectionを確認する。異なるmodelの同一TC実行はcase structureの複数`ci_refs[]`で検証する
- target content / generation fingerprintとannotation / target disposition / mergeのversion一致を確認する。semantic Coverage Itemはnew key発行、active→inactive、CI deleted、同一item復帰、deleted CIの別item再利用拒否、本文変更、model変更、source target version変更を含むlifecycleを確認する
- target_ref → CI mapping / upsert、merge / unmerge / CI↔Dispositionの状態遷移を全generatorで回帰確認する
- CI Machine Entityの`covered_targets[]`へtarget content / execution fingerprintを保存し、stable target_refのままtarget内容が変わるcaseでもCI content fingerprintが変わることを確認する
- CI content変更後、既存TC Machine Entityがsemantic再確認前はstaleになることを確認する
- machine evidence描画
- CI canonical execution / semantic item本文、environment / test data requirementを入力に持つcase structureとTC Machine Entity
- `runtime_units / current_entities / current_runtime_units / expected_runtime_units / expected_entities`から共通freshness関数でEntity freshnessを算出するtraceability。自身のtraceability unitを3つのruntime集合へ含めない
- stale downstream

### Step 11: workflow統合

- end-to-end path
- 既存成果物再利用でもruntime対象unitを現在scriptで再実行し、保存済みresultをcacheにしない
- whole-model fallbackを再利用する場合もsupport判定を再実行する
- runtime対象を既存`対象 / 実行範囲`へ限定したうえでの`(skill, runtime_unit_key)` dependency identity / missing / duplicate / cycle / self除外。workflow runtime自身は3つのruntime集合すべてでself inclusionを拒否する
- expected runtime / Entity集合と実際集合の完全一致。必須unit / Entity丸ごと欠落はblocker、未知の余分なcurrent itemは`invalid_input`。`test_analysis_context / product_risk / technique_selection / change_node / change_edge / environment_requirement / test_data_requirement / disposition`も期待集合から省略しない
- upstream Entity / semantic dependency / upstream runtime変更とEntity freshness
- model / implementation変更
- local block / partial unsupported。closureのhandling / currentな完全Machine Entity参照`covered_by_entity` / 既存Disposition条件まで検査し、closure行の存在だけで完了させない
- whole-model unsupported fallback。currentなfallback先または妥当なDispositionへ閉じていない場合は完了させない
- legacy
- runtime利用確認 / Markdown再読込

### Step 12: 全体検証・文書同期

- runtime unit / CLI integration / deterministic / semantic / workflow
- trigger datasetのSkill別exact count（repository合計328）・正負件数・境界scenario
- semantic datasetのSkill別exact count（repository合計51）と意味判断責務→case対応
- CI
- portability
- 実Agent runtime smoke
- README / references / templates / EVALS / ASSERTIONS

## 13. リスク

### LLMの正規化誤り

semantic evalとAuthority traceで検出し、scriptが意味を補完しません。

### 計算量

固定hard limitを使用し、超過時にCoverage基準を下げません。output件数だけでなくstate / flow / grammarを含む探索nodeを計測し、timeoutを正常終了条件にしません。

### generator / validator同時誤り

helperとexpected fixtureを共有しません。

### stale成果物

Machine Entityの`content_fingerprint / upstream_entity_dependencies[] / runtime_dependencies[]`、runtimeのupstream Entity / upstream runtime generation fingerprint、runtime・generator contract / implementation fingerprint / static data versionsを保持し、共通freshness関数で依存範囲だけを`要再検証`へ戻します。

### runtime非対応環境

runtime状態とQA成果物状態を分離します。

### 依存関係

runtime dependencyはPython 3.11標準ライブラリだけとし、実装中の外部dependency追加を認めません。正確性・hard limit・30秒timeoutを満たせない場合はPlan未達として停止します。

## 14. 完了条件

- model dispatchは`model_type → generator`固定表だけを使い、adapter親でCoverage child欠落を隠さない
- Machine Entityが既存Skillの後続利用fieldを保持し、CIからcanonical execution / semantic item本文、TCからenvironment / test data requirement依存を追跡できる
- canonicalization後の実処理順、stable ID採番順、deleted遷移、state / flow execution、grammar derivation、exact numericが固定規則と一致する

Plan完了には次をすべて満たす必要があります。

- `_01`で実装対象にした処理がruntimeまたは既存機械処理へ割り当てられている
- 目的内の技法・構造処理が本Plan外へ先送りされていない
- CLI / strict JSON / exact JSON number / envelope / canonicalization / envelope・runtime・generator contract versionが実装済み
- `spec-analysis / test-analysis / test-requirement-design / test-condition-design / test-case-design`がcanonical `Machine Entities`を保存し、`entity_type`を含む`(skill, entity_type, entity_ref)` identity、content fingerprint、`upstream_entity_dependencies[] / runtime_dependencies[]`をMarkdown再解釈なしで再構築できる
- upstream Entityのmachine dataからcanonical contentを機械構築してcontent fingerprintをruntime計算でき、sort済み`upstream_entity_fingerprints`を含むgeneration fingerprint、`(skill, runtime_unit_key)` upstream dependency、static data versions、input / model / LF正規化implementation fingerprintが再現可能
- model / artifact全runtime unitの`Machine Runtime Input / Result`を決定論的に抽出し、strict decode、fingerprint一致、同条件でのround-trip再実行が成立する。workflow再利用では保存済みresultをcurrent cacheとして採用せず現在scriptを再実行する
- stable model key / TR / TCN / TCのruntime採番、active / deleted ID state、1 model = 1 TCN、target_ref、成果物系列、previous mapping、merge / unmerge / CI↔Disposition状態遷移を含むCI materializeが契約どおり
- 各generatorのtargetがPlan固定の`materializable`を持ち、CI化する全targetがgenerator別canonical `execution / execution_fingerprint`を持つ。combinatorial targetはdeterministic full rowへ対応し、adapter専用generatorを直接CI化しない。同一CI mergeは同一TCN・同一model・同一execution・同一expected resultに限定される。異なるmodelの同一実行はTCの複数`ci_refs[]`で表現する
- 再実行がupsertされ重複machine evidenceを作らない
- semantic dependency preflight済みの現在script正常実行結果だけを保存時`freshness_status=current`とし、`workflow_runtime.py`が再検証してstale伝播する。freshnessの付与主体をworkflowだけに限定せずmaterialize前の循環を作らない
- stale派生成果物を完了扱いしない
- `technique_slug`が正規技法だけを表し、内部adapterは正規技法を所有しない。Coverage child modelがselection provenanceを持ち、active Technique Selectionの各selected techniqueが1件以上のcurrent Coverage modelへ到達する。不適用 / 未解決はTechnique Selection更新または既存block / unresolvedで扱い、未定義のselection closureを作らない。エラー推測は1件以上のsemantic CIへ入る
- machine-readable schema / HTMLをLLMが手変換せず対応scriptが処理する。HTML runtime-v1は`text / number / date / datetime-local`のtype / attribute matrix、disabled / readonlyのvalidation除外、pattern等のunsupportedを契約どおり扱う
- script間の機械変換では固定derived schema / builderを使い、派生modelを`condition_structure.py`で採番し、LLMは意味パラメータやtarget annotationだけを追加してmachine dataを再生成しない
- 全技法generatorと構造scriptにunit testがある
- 通常/集約stdin、stdout、item数、byte、depth、state / flow / grammarを含む探索node hard limitとtie-breakが契約どおり
- runtime出力と保存machine evidenceの一致をvalidatorが確認する
- support判定をruntimeが行い、whole-model `unsupported`、`partial`、Python unavailableを契約どおり区別する。supported inputをAgent判断だけでruntime省略しない
- model内Coverageと仕様全体Coverageを混同しない
- `workflow_runtime.py`がmodel / artifact両runtime unit、Machine Entityのsemantic / runtime dependency、upstream Entity内容変更、`(skill, runtime_unit_key)` dependency、actualから独立導出したexpected runtime / Entity集合のmissing / extra、dependency missing / duplicate / cycle、generation / implementation変更、stale、Coverage所有model単位のCI / closure完了、局所ブロック、partial / whole-model fallback、legacyを処理でき、自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`へ含めず、self inclusionを`invalid_input`にする
- `traceability.py`と`workflow_runtime.py`が同じ`runtime_contract.py` freshness関数から同じruntime / Entity freshnessを得て、workflow_runtime resultをtraceabilityの依存入力にしない。traceability自身もfreshness入力runtime集合へ含めない
- 既存成果物を再利用する場合、保存済みsemantic model / draftの上流Entity dependencyをruntime再実行前に確認し、不一致なら担当Skillで意味再確認する。freshな意味入力だけを現在scriptへ再投入し、materialize / traceability / workflow freshnessに循環を作らない
- 以前whole-model `unsupported`だった成果物も再利用時に現在runtimeでsupport判定を再実行し、現在supportedなら古いfallbackを維持しない
- question-analysis往復でRuntime Skill / Runtime Unit / model / target / generation fingerprintが失われず、別generationへ古い回答を自動適用しない
- target内容またはruntime generation変更時にstable `target_ref` / CI IDを維持しても、古いannotation / Disposition / merge判断と下流TCをcurrent扱いしない
- unsupported closureは対象generationとreasonが現在値に一致し、許可されたhandling・必要なcurrent`covered_by_entity`の完全identity / fingerprint・既存Disposition条件を満たす場合だけ閉鎖済みとして再利用する。`ブロック中`closureは完了不可
- 途中工程開始と`Selection Source=analysis / condition_design / user`が既存workflowを壊さず、runtime派生元をSelection Sourceへ混ぜず、model reuseが選択元を失わず、undetermined signalが未閉鎖のまま完了しない
- CIでは全runtime scriptのdispatch / metadata整合、複数用途Skillの対象限定、Coverage targetのCI / Disposition閉鎖、Cause-Effect constraint伝播、Decision Table don't-care merge非破壊性を確認し、実Agent smokeでは代表promptでPython起動、envelope parse、Machine Entity / runtime result採用、Markdown再読込、現在script再実行まで確認できる
- 6 Skillの単体移植性が成立し、共通runtime helperの内容一致を検証できる
- trigger datasetがSkill別exact count（repository合計328）を満たし、新規技法5種のselection / design境界をtrain・validation双方で検証する
- semantic datasetがSkill別exact count（repository合計51）を満たし、LLMへ残す意味判断責務が少なくとも1 caseへ対応したうえでtest-analysis / test-condition-design / adversarial-reviewのcaseがPASSする
- Round-tripが開始state違いを別targetとして扱い、Domain Testingがexact rationalで対象border以外のIN条件を検証し、Decision Table mergeが未定義assignmentを包含しない
- structure / traceabilityが共通Disposition schemaを扱い、JSON Schema 2020-12の`$id / $ref` resource境界と`$ref` sibling、OpenAPI 3.0 Reference Object / `nullable / readOnly / writeOnly`、HTML numberのdefault step / `step=any` / step baseをPlanの対応subsetどおり処理し、raw schema数値をstringと混同せずbinary float / context roundingなしで処理する
- Python 3.11 compile / runtime unit / deterministic eval / semantic validation / workflow統合評価がPASS
- `skills-ref validate`がPASS
- README、Skill、reference、template、EVALS、ASSERTIONSが実装と一致
- Error Guessing、Exploratory Testing、risk発見、expected result等の意味判断をscriptへ移していない

## 15. 実装時に避けること

- eval helperをruntimeからimportする
- generator outputをexpected fixtureへ使う
- 任意Python式を`eval()` / `exec()`で実行する
- 将来用plugin / adapterを作る
- Coverage基準をlimit都合で下げる
- stale派生成果物を再利用する
- runtime `unsupported`をQA成果物の`対象外`と同一視する
- `null` signalを`false`へ変換する
- model内100%を仕様全体100%と表現する
- Random Testing / Metamorphic Testingへ一般的な100% Coverageを作る
- external referenceを製品Authorityへ昇格する
- 意味判断なしにinvalid behavior / expected result / riskを創作する
- machine evidenceをLLMに手計算させる
- machine-readable入力を対応scriptがあるのにLLMへ再変換させる
- runtime dependencyを`runtime_unit_key`単独でSkill横断参照する
- target key componentへdelimiter `:`を許可する
- Domain borderやschema numeric keywordをbinary float / context roundingで近似する
- `workflow_runtime.py`自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`のいずれかへ含める
