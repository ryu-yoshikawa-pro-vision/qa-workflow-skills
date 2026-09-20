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
test_spec_analysis_authority_entities.py
test_test_analysis_entities.py
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

各runtime scriptには`tests/skills/runtime/fixtures/<script-name>/valid_minimal.json`を1件必須とし、これをPlan `_03`のrequired input schemaの実行例とします。`spec-analysis/authority_entities.py`にもbuilder用`valid_minimal.json`を1件置き、runtime envelopeではなくMachine Entity / expected identity出力を検証します。fixtureは手書きし、generator出力から生成しません。unknown field拒否、required field欠落、型不一致は各scriptのunit testで確認します。

CLI integration testは各runtime scriptの`valid_minimal.json`をsubprocessで`python <script-path>`起動し、stdinへJSONを渡してstdout envelopeを読む経路を使用します。`authority_entities.py`もsubprocessでbuilder入出力を検証します。加えて`_02` §2.1のSkill別dispatch表について、各scriptへ到達するprompt分類済みfixtureから期待script path・必須/条件付き・実行順を一意に決められることを機械テストします。派生modelでは`condition_structure.py`でadapter / child identity確定 → 親adapter runtime → child generatorまで検証します。全scriptのdispatchはCIで検証し、実Agent smokeだけへ依存しません。CI subprocessとSkill実行時subprocessの安全timeoutは30秒です。

## 3. 共通契約の必須回帰

### strict JSON

- duplicate key拒否
- `NaN` / `Infinity`拒否
- 不正top-level type拒否
- UTF-8 decode前byte上限と、`json.loads()`前のstring / escape aware構造scanによるnesting depth 64。depth 65以上をparser依存エラーではなく`limit_exceeded`にする
- object key / string valueのunpaired surrogate code point拒否
- model decimalの型保持
- raw JSON documentのnumberを通常のstringと異なる専用token型で受け、raw token長 / JSON number grammar検証後にcanonical integer / `coefficient + scale`へexact正規化し、binary float / `Decimal` contextへ依存しない
- canonical serializerが専用number型をstring化せず、exact numeric表現を指数表記なしのJSON numberへ戻す
- `1 != "1"`、`1.0 != "1.0"`、`1e3 != "1e3"`を固定回帰にする
- raw numeric token / canonical numeric representationの4096 chars上限超過を`limit_exceeded`にし、丸めない
- nullと欠落の区別

### runtime envelope

- `envelope_version / skill / runtime_contract_version / generator_contract_version / generator / runtime_unit_key / model_key / input_fingerprint / model_fingerprint / generation_fingerprint / runtime_implementation_fingerprint / generator_implementation_fingerprint / upstream_entity_fingerprints / upstream_runtime_units / support_status / static_data_versions / runtime_status / result_status / runtime_required / deterministic_generated / fallback_reason / payload / issues`
- `skill`はscript所属Skillと一致必須で、runtime issueも`skill + runtime_unit_key`を保持する
- canonical input確定後のruntime issueはenvelopeの`generation_fingerprint`を保持し、質問・再開時に現在世代と一致しない回答を拒否する。pre-parse error / timeout等でgenerationを確定できないissueだけ`generation_fingerprint=null`を許可する
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
- `support_status=unknown`は`invalid_input / internal_error / not_run`に加え、strict decode前の`limit_exceeded`だけで許可する。いずれも`runtime_required=true / result_status=blocked / deterministic_generated=false`を要求する
- Python unavailable / runtime未実行は`runtime_status=not_run / support_status=unknown / runtime_required=true / result_status=blocked / deterministic_generated=false / fallback_reason=python_unavailable`とし、fingerprintをnullで保持する
- status対応表どおりの`support_status / result_status / runtime_required / deterministic_generated`を要求
- model scriptでは`model_status=result_status`、artifact全体scriptでは`artifact_status=result_status`
- staleはruntime statusではなく`freshness_status`で表現する。semantic dependency preflight成功後に現在scriptを正常実行したresultは保存時に`current`、`workflow_runtime.py`は共通freshness関数で再検証して必要なresult / Entityを`stale`へ変更する
- strict decode前の空stdin / 不正UTF-8 / duplicate JSON / byte・depth上限ではpre-parse error envelopeを返し、未確定の`runtime_unit_key / model_key / input_fingerprint / model_fingerprint / generation_fingerprint=null`を検証する。callerが推測値を補わない
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
- 実行前から存在する外部upstream Entityはcanonical `content`からruntimeが`content_fingerprint`を計算し、output envelopeの`upstream_entity_fingerprints[]`へcanonical順で保存する。script固有inputのsemantic reference集合から固定builderが期待する外部`upstream_entities[]`と完全一致することを検査し、省略・余分・重複を許可しない。同一runtime invocationで生成するEntity間依存は入力`upstream_entities[]`へ要求せず、固定生成順で確定したcontent fingerprintをdependencyへ使う
- upstream Entityの正規項目変更でその`content_fingerprint`だけが変わる
- `upstream_entity_fingerprints`の変更で`generation_fingerprint`が変わり、Authority IDが同じでも内容変更を同一generation扱いしない
- Machine Entityの`upstream_entity_dependencies[]`差分を再実行前に検出し、古いsemantic model / draftをそのまま現在runtimeへ投入しない
- 無関係なupstream Entity変更では対象runtime unitをstaleにしない
- 直接依存する上流runtime unitの`generation_fingerprint`変更で下流unitだけがstaleになる
- envelope version、generator、runtime contract、generator contract、実装fingerprint、static data version変更で`generation_fingerprint`が変わる
- runtime / generator source変更で実装fingerprintが変わり、意味契約を変えないbug fixでも旧machine evidenceを同一生成条件として再利用しない
- 既存成果物再利用時もdispatch対象runtimeを現在scriptで再実行し、保存済みruntime resultだけでcurrent判定しない
- 以前whole-model `unsupported`だったfixtureをruntime対応後に再実行するとsupported経路へ移り、古いfallbackを固定しない
- adapter / child modelを同じ`condition_structure.py`実行で先に採番し、childの`derived_from_model_draft_key → derived_from_model_key`を固定する。adapter実行後にchildを追加してTechnique Selection閉鎖を一時的に破る経路を作らない
- `condition_structure.py`を派生modelのidentity確定に再利用しても、既存model generatorがID割当てしか利用していない場合は同scriptをruntime dependencyへ登録せず、親generatorを自己stale化しない
- tie-break / Coverage / target key等の意味契約変更では実装fingerprintだけでなく対応contract versionも更新する
- model / artifact全runtime unitについて`Machine Runtime Input / Result`を保存→決定論的抽出→strict decode→canonical化し、input fingerprint、model scriptではmodel fingerprintも一致する。同条件でruntimeへ再投入すると同じmachine resultになる
- LF / CRLF差だけでimplementation fingerprintが変わらない
- canonical JSON static dataは整形・改行差だけでversion hashが変わらない

- hash由来stable component keyは`h` + full SHA-256 64 hexの65文字に固定し、digestを切り詰めない

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
- output `risks[]`が全input riskを`risk_id`順で1回ずつ返し、`{risk_id, level, mapped_priority}`以外の意味fieldをruntimeが創作しない

### technique candidates

- 全signal key
- `true / false / null`
- `_03`のsignal → candidate mapping
- 複数`true`時のunionと安定順
- outputがinput `selection_key`を保持する
- `undetermined_signals`
- `complete=false`だけではworkflowをブロックしない
- `Selection Source = analysis / condition_design / user`。runtime派生元は`upstream_runtime_units[]`で表し、既存model再利用は`identity_action=reuse`で表す
- ユーザー明示 / 既存成果物由来の技法をcandidate scriptが却下しない
- `undetermined_signals`の各signalを`resolved / selection_not_affected / question`へ閉じ、未閉鎖signalをworkflow完了にしない
- 新規正規技法名
- 選択技法のmodel / disposition閉鎖

### test-analysis Machine Entity builder

- `analysis_entities.py`はcurrent `risk_matrix.py` payloadの`risks[]`とcurrent `technique_candidates.py` payloadを固定抽出したresult rowだけを受け、runtime envelope全文やMarkdownを再解釈しない
- Product Risk draftと`risk_matrix_results[]`、Technique Selection draftと`technique_candidate_results[]`をidentityで1対1joinし、missing / duplicate / unknown rowを`invalid_input`にする
- change graph / environment → Product Risk → Technique Selection / test-analysis contextの固定順で同一invocation内Entity dependencyを生成する。同じtest-analysis実行でdispatchされたrisk / technique / change impact / environment runtime unitをcurrent upstream runtime dependencyとして保持し、未dispatchの条件付きunitを追加しない
- output `expected_entity_identities[]`はdraft / normalized resultから独立導出し、生成済み`machine_entities[]`から逆算しない
- Product Riskの`assessment_reason / confidence_note`、Technique Selectionの`undetermined_signal_closures[]`、change graphの`change_kind / expected_impact`をMachine Entityへ保持する

### change impact

- node / edge type
- `change_kind / expected_impact`を探索ロジックで創作・欠落させずMachine Entityへ保持する
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
- reuse時の`model_type / technique_slug / selection_source / selection_key / derived_from_model_key / parent TCN / existing key`一致
- 1 model key = 1 TCN所属を検査し、同じmodel keyを複数TCNへ割り当てない
- outputの`tcn_id_state[] / model_key_state[]`にdeleted IDも残し、次回入力の正本にする
- TCN draftの`condition / category / technique_slugs[] / coverage_criterion / authority_refs / risk_refs / priority_override_reason`とmodel draftの`model_type / technique_slug / selection_source / selection_key / derived_from_model_draft_key`をruntime inputへ保持し、最終IDとjoinしてTCN / model metadata Machine Entityを固定生成する
- 同一`condition_structure.py` invocationで生成するparent TCN / adapter modelを事前`upstream_entities[]`へ要求せず、TCN → adapter model → child modelの固定生成順でEntity dependencyを接続する
- Coverage所有modelだけ`selection_source=analysis / condition_design / user`を持ち、内部adapterは`technique_slug / selection_source / selection_key=null`
- 各TCNの`technique_slugs[]`と所属Coverage所有modelのcanonical `technique_slug`集合を完全一致で検証する
- Classification Tree / Cause-Effect / schema adapterは正規技法を所有せず、child Coverage modelがcanonical techniqueと元のselection provenance、`derived_from_model_key`を持つ
- 1つのselectionは複数TCN / modelへ展開できるが、active Technique Selectionの`selected_techniques[]`に残る各技法は少なくとも1件のcurrent Coverage所有modelへ到達することを検証する
- 選択後に不適用 / 未解決となった技法はTechnique Selection Entity自体を更新してselected listから外すか既存block / unresolvedへ戻し、未定義のselection closureでは閉じない
- runtime非対応はCoverage所有model生成後のunsupported closureで扱う
- child Coverage model欠落をadapter親だけで閉鎖済みにしない
- `model_type=error-guessing / technique_slug=error-guessing`はruntime unitを要求せず、semantic Coverage ItemをCI Machine Entityへmaterializeできることを検証する。semantic item 0件では完了不可
- 各active Coverage所有modelはmodel単位で検証する。supported / partial / runtimeなしsemantic modelではcurrent materialize runtime unitの`model_completion[]` rowが必須で、current CI / target Disposition / semantic source targetから決まる`materialize_complete`を確認する。partialはunsupported item closureも別途全件必要、whole-model unsupportedはcurrent whole-model closureが必要。別modelのCIが親TCNに存在するだけでは完了にしない
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
- integer / exact decimal（coefficient + scale） / date / local datetime / fixed-offset datetime
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

- 複数initial stateのtie-breakと`initial_state_key / initial_state_label`をexecutionへ保持する。reset使用時は`reset_execution.action / to_state`まで保存し、setup / coverage transitionはfrom / event / toの状態意味を内包する
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

- nodeの`label`をnormalized inputへ保持し、node targetがinitial node自身でedge sequenceが空でも`target_node`から意味を解決できる
- canonical edge sequenceへfrom / label / toのnode意味を保存し、stable keyだけをtest-case-designへ渡さない

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

- entity / functionの非空`label`をnormalized inputへ保持し、operation / consistency sequenceのcanonical executionへlabelを複製する。`entity_key / function_key`だけを下流の実行意味にしない

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
- `max_depth`を1..64、root=0のparse tree depthとして検証し、epsilon production境界を確認する

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
- OpenAPI Reference Objectの追加propertyを仕様どおり無視し、sibling Schema assertionとして扱わない
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
- invalid / zero / negative HTML stepはdefault step=1へfallbackし、制約なしとしてcompleteにしない
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
- test dataは`source_model_key`を必須にし、model-wide requirementでは`source_target_versions=[]`とcurrent adapter / Coverage model metadataの一致、target-specific requirementでは1件以上の`source_target_versions[]`と`current_source_targets[]`の同一Coverage model / current version一致を検証する。`target_key`単独やstable IDだけをidentityに使わない
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

- semantic-only Error Guessing、fork-join、partial / whole-model unsupportedの`llm_fallback`でも`materialize_coverage.py`をdispatchする
- `active_model_metadata[]`でruntimeなしmodelのTCN所属を検証する
- semantic itemのstable key / previous mapping / reuse CIを検証し、別item・別model・runtime target CIへの横取りを拒否する。`source_target_versions[]`はsemantic item自身の`model_key`に属するcurrent targetだけを許可する
- test data requirement Entity fingerprint変更をCI / TC staleへ反映する

- materialize入力modelは`runtime_status=ok / result_status=ready / deterministic_generated=true / freshness=current`に加え、model type別の`coverage_summary.complete`または`completion_summary.complete`を必須にする。CRUDはcompleteness / consistency双方のcompleteを要求し、Random / Metamorphicの件数未達をCI化しない。supportedまたは分離済みpartialだけ許可する
- unresolved / blocked / stale modelからCIを作らない
- generator targetは`materializable=true|false`を必須にし、`true`だけmachine targetとしてCI materialize / target Dispositionの対象とする。adapter / diagnostic専用`false` targetはmachine evidenceとして保持してCIを要求しない。一方、fork-join branch等の正規Coverage基準上必要な`false` targetは、現在target versionを参照するsemantic Coverage Itemまたは既存Skillで許可されたDispositionへ閉じるまで完了させない
- 同一target_refへ`target_annotations[]`と`target_dispositions[]`を同時指定しない
- CI化するtargetだけ`target_annotations[]`を1対1で要求し、unknown / duplicate target_refを拒否する
- CI化targetはgenerator別にPlanで固定したcanonical `execution`とruntime計算済み`execution_fingerprint`を必須とし、opaqueなstable keyだけではなく`test-case-design`が入力対象・条件・操作を再構築できるlabel / concrete value / expected relationを保持する
- combinatorialはfull rowへ`row_ref=sha256(canonical assignment)`を付与し、各SAT targetをそのtargetをcoverする生成済みrowのうち生成順で最初のrowへ対応付ける。同じrowを使うtargetは同じ`execution_fingerprint`になる
- `classification_tree.py / cause_effect.py / schema_cases.py / ui_pattern_candidates.py`は直接CI化せず、Planで定義したderived model / 意味判断先だけをmaterialize対象にする
- stateのinvalid transitionは`attempted_transition`をcanonical executionへ保持し、valid transition列へ混ぜない。flowのnode / edgeはinitialから対象までの最短witness、bounded-pathはinitial→terminal pathを使用する。fork-join branchは単一`edge_sequence`へ順序化せず、semantic Coverage Itemの`source_target_versions[]`が現在branch targetと一致するまで完了させない
- annotation / Dispositionの`target_content_fingerprint / generation_fingerprint`が現在target / modelと一致しない場合は拒否する
- `target_dispositions[].handling`は`対象外 / 別テストレベル / 残存リスク / ブロック中 / 重複`だけを許可する
- `重複`では完全`covered_by_target_version={target_ref,target_content_fingerprint,generation_fingerprint,execution_fingerprint}`を必須にし、参照先runtime targetではexecution fingerprint非null一致、semantic targetではnullを要求してself参照を拒否する。同一materialize input内の参照先は即時照合し、別TCNの参照先は`target_mappings[]`またはsemantic CIの`semantic_source_targets[]`を使って最終集約時にcurrent version一致を確認する。missing / generation mismatch / content mismatch / execution mismatch / cycleを拒否し、chain終端がcurrent CI mappingまたはcurrent semantic CIへ到達することを要求する
- generator生成後に`成立不能`Dispositionへ変更しない。成立不能根拠が得られた場合はmodel / constraintを更新してgeneratorを再実行する
- Disposition済みtargetへCIを採番せず、同時にgenerator固有の`coverage_summary`または`completion_summary`を変更しない
- `ブロック中`Dispositionはworkflow完了を妨げる
- materialize outputから生成したCI Machine Entityは、machine target由来ではcanonical `execution`まで保存する。semantic item由来ではstable `semantic_item_key`と`semantic_item_text / source_target_versions[]`を保存し、`priority_override_reason`を含む意味field変更でCI content fingerprintを変える
- stable target_refのままtarget content / executionが変わった場合、CI Machine Entityのcontent fingerprintが変わり、参照TCへstaleが伝播する
- `test_data_requirement_refs[]`は同じmaterialize inputの`data:<requirement_key>`へ解決できることを必須にする
- merge groupは`{merge_group_key, model_key, target_refs[], target_versions[]}`を使い、Dispositionされていない同一TCN・同一`model_key`のtargetだけを含む。各`target_versions[]`は`target_ref / target_content_fingerprint / generation_fingerprint / execution_fingerprint`を保持し、全targetの`execution_fingerprint`と`expected_result_root`の一致を要求する
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
- `traceability.py`と`workflow_runtime.py`が同じ`runtime_contract.py` freshness / closure関数と、`runtime_units / current_entities / current_runtime_units / expected_runtime_units / expected_entities / unsupported_item_closures` schemaを使う
- Machine Entityの`upstream_entity_dependencies[] / runtime_dependencies[]`から`entity_freshness[]`を同じ結果として算出し、missing / generation mismatch / dependency cycleを検出する
- `traceability.py`は`workflow_runtime.py` resultを依存入力にせず、`coverage-analysis::artifact:traceability:all`自身と`qa-workflow::artifact:workflow_runtime:all`を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`へ含めない。いずれかのinclusionを`invalid_input`として回帰検出する
- Authority / Risk → TRまたはDisposition
- TR → TCNまたはDisposition
- TCN → CI → TC、条件付きCIなしTCN → TC、または既存Skill契約で許可されたDisposition。CIなし経路はactive Coverage所有modelが0件のTCNだけ許可し、Coverage所有modelがあるTCNではmodel単位のcurrent CI / closureを先に必須とする
- 許可直接edge以外をclosure根拠にしない
- Dispositionのhandling / reason / Authority条件
- materialize runtime unitの`target_mappings[] / target_dispositions[]`と`unsupported_item_closures[]`を使い、target重複chainのmissing / stale / cycle / terminal coverage、partial / whole-model unsupported closureをmodel単位で検査する
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
- merge groupへのtarget追加 / 削除、CI→Disposition、Disposition→CIの各状態遷移で[identity・materialize契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) §7.2.2どおりID維持・deleted・再採番を行う
- merge解除時は辞書順先頭targetへ既存CIを維持し、残りを過去使用済み最大番号+1で再採番して関連TCを`要再検証`へする
- `target_mapping_state[] / ci_id_state[]`にinactive / deleted履歴を残す
- 消滅targetで下流`要再検証`
- 同じ実行を2回行ってmachine evidenceが重複しない
- stale rowを完了扱いしない

## 続き

[validator・semantic eval・CI・文書更新](./2026-09-18_170000_deterministic-test-technique-automation_05_validation-ci-and-docs.md) に続きます。
