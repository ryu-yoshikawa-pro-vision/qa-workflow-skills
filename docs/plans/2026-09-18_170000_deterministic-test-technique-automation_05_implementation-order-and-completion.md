# テスト分析・テスト技法の決定論的自動化Plan

このファイルは実装順序、リスク、完了条件をまとめます。[評価・CI契約](./2026-09-18_170000_deterministic-test-technique-automation_05_evaluation-ci-implementation-order.md)および[validator・CI・文書更新](./2026-09-18_170000_deterministic-test-technique-automation_05_validation-ci-and-docs.md)と合わせて参照します。

## 12. 実装順序

### Step 0: 基準再確認

- main最新
- 関連Skill / validator / CI
- branch差分

### Step 1: 代表経路に必要な共通runtime契約

後続の汎用基盤を先に作り込まず、Step 2.5のEP縦断経路に必要な共通部分だけを先に実装します。

- Agent / hostがPython 3.11 interpreterで同梱scriptを実行し、stdin / stdout / stderr / return code相当を扱える実行境界。Skill契約ではinterpreter command名とtimeout APIを固定せず、CIではsetup済みPythonと30秒timeoutを使用する
- stdin / stdout / cwd非依存のCLI protocol
- strict JSON
- output envelope / status対応表
- canonicalization
- `metadata.input_mode=artifact|direct`と、途中工程開始・Skill単体利用時のdirect input契約
- envelope / runtime / generator contract version
- static data versions
- input / model / generation fingerprint。generationにはsort済み`upstream_entity_fingerprints`を含める
- runtime / generator implementation fingerprint。全runtime scriptはSkill-local importを`runtime_contract.py`だけに限定し、共通exact numeric / intersection / freshness等はfingerprint対象の`runtime_contract.py`へ置く
- `entity-state-v1` Machine Entity schema、`entity_type`、`content_fingerprint`、`upstream_entity_dependencies[] / runtime_dependencies[]`、identity=`(skill, entity_type, entity_ref)`
- `spec-analysis`へ`runtime_contract.py`のcanonical / Machine Entity helperと`authority_entities.py`を追加する。runtime unitは追加せず、実行失敗・Python unavailable時はAuthority Machine Entity / fingerprintを代替生成せずblockedにする
- support_statusと対応subset判定。runtime_requiredは入力fieldにせずruntime出力として導出
- `Machine Runtime Input / Result`の保存、決定論的抽出 / round-trip再投入。保存済みresultをcurrent cacheにはしない
- `runtime_contract.py`の固定projectionでmodel envelope → `current_model_result_row`、全runtime envelope → `runtime_unit_row`を生成し、`freshness_status=current`をcurrent再実行・envelope検証成功後だけ付与する
- 通常stdin 2 MiB / 集約stdin 16 MiB / stdout 16 MiB / depth / 探索node hard limit
- tie-break
- structured issue / blocking
- 複数用途Skillのruntime dispatchを`test-analysis: テスト分析`、`coverage-analysis: テスト設計`へ限定する
- `runtime_contract.py`をSkill-localに同梱し、repo root helperへ依存させない。canonical / Machine Entity helperの同一実装とLF正規化implementation fingerprintを検証する

このStepでは、全Skillのfreshness graph、全expected Entity集合、merge / unmerge、question再開等を完成させません。Step 2.5で実経路を確認してからStep 2.6で一般化します。

### Step 2: EP縦断経路に必要な最小identity / materialize

- canonical technique slugと内部`model_type`を分離し、まず`model_type=ep → equivalence_partitions.py`の固定dispatchを実装する
- `condition_structure.py`のTCN / EP model identity確定、`draft_key`、reuse / new、previous full snapshot、`update_scope_tcn_ids[] / update_scope_model_keys[]`を実装する
- `equivalence_partitions.py`を代表generatorとして実装する
- EP targetの`target_ref / target_content_fingerprint / canonical execution / execution_fingerprint`を共通post-processで生成する
- `materialize_coverage.py`はEP縦断経路に必要なtarget annotation、stable CI採番、previous mapping、current TCN単位のstate、CI Machine Entityまでを先に実装する
- TCN / model / CIのMachine Entityと、representative fixtureからactual集合と独立導出するexpected identityを実装する
- `input_mode=direct`で前工程Machine Entityなしのtest-condition-design単体経路、`input_mode=artifact`でcurrent Machine Entityを使う再利用経路を両方用意する
- representative pathに必要な範囲だけ共通freshness関数と`workflow_runtime.py`へ接続し、missing / stale / generation mismatchを検出する
- 正常fixtureからMachine Entityまたはruntime unitを1件削除してもexpected集合が変わらずmissing blockerになることを確認する
- machine evidence描画とMarkdown round-tripを実装する

### Step 2.5: 代表generatorと共通経路の成立確認

後続generatorやfull lifecycleを量産する前に、Step 1 / 2のEP経路を同一PR内で通します。Step 5ではEPを再実装せず、この実装へBVA等を追加します。

`LLM正規化 → input_mode選択 → condition_structure.py → TCN / EP model Machine Entity保存 → semantic dependency preflight → EP dispatch → runtime再実行 → Machine Runtime Input / Result保存 → target annotation → CI materialize → validator → workflow_runtime → Markdown再読込 → semantic dependency preflight → runtime再実行`

必須fixture:

- `direct`: 前工程Skill directory / Machine Entityなしで、既存test-condition-design入力契約からEP成果物を生成できる
- `artifact`: current Machine Entity付き成果物を使い、missing / extra dependencyを拒否できる
- partial rerun: scope外のactive TCN / model IDを維持し、scope内で明示的に外したIDだけdeletedへ遷移する
- 同一入力再実行でMachine Runtime Result、target / CI mapping、fingerprintが一致する
- 完成Markdownを保存・再読込し、同じinputでruntime再実行できる
- 実AgentでPython起動、stdout envelope parse、成果物保存まで確認する。Agent側artifact transport上限がruntime 16 MiBより低い場合は後続generator実装前に`runtime-v1`へ固定する

ここで共通契約不整合が見つかった場合はStep 1 / 2へ戻して修正します。この確認をPR完了の区切りにはせず、修正後は同じPRでStep 2.6以降へ進みます。

### Step 2.6: identity / workflow基盤の一般化

Step 2.5で成立した経路を、現在Planで必要な全Skill / lifecycleへ広げます。Step 2.5で実証していない将来用抽象化は追加しません。

- model dispatchを全固定`model_type → generator`表へ拡張する
- 内部adapterとCoverage child modelのidentity、`selection_source / selection_key / technique_slug / derived_from_model_key`、`semantic_parameter_requests[] / derived_child_inputs[]`を実装する
- `requirement_structure.py / condition_structure.py / case_structure.py`のTR / TCN・model / TC採番を完成させる
- previous ID stateは成果物系列full snapshotを維持し、`update_scope_tr_ids[] / update_scope_tcn_ids[] / update_scope_model_keys[] / update_scope_tc_ids[]`内だけdeleted遷移させる。scope外activeは維持する
- qa-workflow再利用元による成果物系列判定
- 既存成果物のsemantic model / draftを再利用する前に保存dependencyをcurrent Entityと比較し、不一致なら担当Skillへ`要再検証`として戻すpreflight
- 既存TR / TCN / TC / modelのID再利用規則、active / deleted machine state、999上限、1 model key = 1 TCN所属
- `materialize_coverage.py`をruntime target / stable semantic item / previous semantic mappingへ拡張する
- generator別`materializable` / canonical `execution`契約を共通post-processへ接続する
- merge / unmerge / target追加削除 / CI↔DispositionのID状態遷移とdownstream stale
- 同じtarget_refの内容変更時にCI IDを維持しつつannotation / Disposition / mergeと関連TCを`要再検証`へ戻す
- environment requirementは`environment_key`内だけ同時成立を検査し、異なるkeyを代替環境としてcross-intersectionしない
- test data requirementはmodel-wide / target-specificの適用範囲を維持し、target、merge group、TCで実際に同時成立する要求集合だけintersectionする。requirement identityは元の`requirement_key`を維持する
- upsert / stale / freshness status
- runtime / Machine Entity dependency graphを評価する共通freshness関数を全対象へ拡張し、traceabilityとworkflowで同じ関数を使う
- question-analysisのRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprint保持と回答適用前preflight
- coverage-analysisのModel Key / Disposition追跡
- 各Skillの固定builderがactual集合から独立したnormalized source / structure stateから`expected_runtime_units[] / expected_entities[]`を生成し、`workflow_runtime.py`が実際集合との完全一致を検査する
- `qa-workflow`を経由しないstandalone Skillでも、最終自己検証時に同じ固定builderでexpected runtime identity集合を導出し、保存した`Machine Runtime Input / Result` block identity集合と完全一致を確認する。必須runtime blockのmissing / unknown extraがあれば成果物を完成扱いしない
- `workflow_runtime.py`によるruntime metadataの機械集約。既存Skill状態表 / runtime状態表はqa-workflowが状態表示を行う場合だけ描画し、完了判定は表の存在に依存させない
- legacy昇格。初回は`input_mode=direct`で現在観測できるTR / TCN / CI / TCをactive seedへ取り込み、未知の過去deleted履歴を捏造しない。既存CI IDを維持する場合は初回だけ`legacy_ci_seed[]`でcurrent target / semantic itemへ一意に対応付ける。新契約保存後も必要な前工程Machine Entityが存在しない境界はdirectを維持し、必要な外部Entityがすべて揃った時点だけartifactへ切り替える
- `qa-workflow::artifact:workflow_runtime:all`自身を評価runtime集合から除外し、self inclusionを`invalid_input`にする

### Step 3: test-analysis

- runtimeは`対象 / 実行範囲=テスト分析`だけでdispatchする
- `analysis_entities.py`でProduct Risk / 技法選択 / change graph / environment requirement / test-analysis contextのMachine Entityとexpected identityを保存する
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
- schema parser / HTML control属性処理 / exact JSON number / scalar-null enum・const / root document + local `$ref` / OpenAPI request-response context。HTMLは抽出済みcontrol属性objectを入力とし、raw HTML parserを追加しない。OpenAPI runtime inputは解析済みstrict JSON objectに限定し、YAML parserや追加dependencyを実装しない
- HTML runtime-v1 typeを`text / number / date / datetime-local`へ限定し、disabled / readonlyのconstraint validation除外、pattern / unsupported typeを安全側へ閉じる
- schemaから、既に選択・採番済みのEP / BVA / combinatorial childへmachine skeletonを生成する。BVA / combinatorialで意味parameterが必要なら`schema_cases.py`自身が`unresolved` + `semantic_parameter_requests[]`を返し、同script再実行で完成`derived_child_inputs[]`とtest data requirementを生成する。schema runtime結果から新しい技法 / child modelを自動追加せず、選択済みchildへskeletonを作れない場合はselection source別に戻す
- test dataは同時成立する適用範囲だけcross-operator intersectionし、environmentは同一`environment_key`内だけintersectionする
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

- state / transition / reset action
- `all-states`はmodel内全state、`valid-transitions`はvalidと確定した全transitionをrequired母集団とし、setup不能なrequired itemを無言で除外せず`unresolved`にする
- `initial_state_key / initial_state_label / reset_key / reset_execution / setup_prefix / coverage_sequence`を持ち、transitionのfrom / event / toまで自己完結したcanonical state execution
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
- 全generatorについて`materializable`の固定値とcanonical `execution / execution_fingerprint` schemaを確認する。EP / BVA / Domain / Decision / combinatorial / grammar / Random / Metamorphicを含め、opaque keyだけでなく下流の手順化に必要なlabel / concrete value / expected relationをexecutionへ内包する。combinatorialはpartial target → deterministic full row mapping、adapter専用generatorは非materializeを回帰確認する
- mergeは同一model・同一executionに限定し、merge対象targetのtest data requirement unionへintersectionを再適用する。requirement identity自体はmergeしない。異なるmodelの同一TC実行はcase structureの複数`ci_refs[]`で検証し、そのTCの要求unionを再検査する
- target content / generation fingerprintとannotation / target disposition / mergeのversion一致を確認する。target Dispositionの`重複`はself / cycleを拒否し、current CI / semantic CIへ到達する終端を必須にする。semantic Coverage Itemはnew key発行、active→inactive、CI deleted、同一item復帰、deleted CIの別item再利用拒否、本文変更、model変更、同一modelのsource target version変更、partial / whole-model unsupported fallbackを含むlifecycleを確認する
- `model_completion[]`がmodelごとのrequired target / closed target / active CI / semantic itemをcurrent mappingから構築し、別modelのCI混入、stale CI、未閉鎖targetでfalseになることを確認する。whole-model unsupportedで成功rowを捏造しない
- target_ref → CI mapping / upsert、merge / unmerge / CI↔Dispositionの状態遷移を全generatorで回帰確認する
- CI Machine Entityの`covered_targets[]`へtarget content / execution fingerprintを保存し、stable target_refのままtarget内容が変わるcaseでもCI content fingerprintが変わることを確認する
- CI content変更後、既存TC Machine Entityがsemantic再確認前はstaleになることを確認する
- machine evidence描画
- CI canonical execution / semantic item本文、environment / test data requirementを入力に持つcase structureとTC Machine Entity
- `runtime_units / current_entities / current_runtime_units / expected_runtime_units / expected_entities / unsupported_item_closures`から共通freshness関数でEntity freshnessとmodel closureを算出するtraceability。materialize unitの`model_completion[] / target_mappings[] / target_dispositions[]`を使い、自身のtraceability unitとworkflow_runtime unitを3つのruntime集合へ含めない
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
- whole-model unsupported fallback。`llm_fallback`は同じmodelのcurrent semantic CIへ解決し、妥当なDispositionを含めcurrent closureがない場合は完了させない
- target Dispositionの`重複`graphがcycleせずcurrent CI / semantic CIへ終端することを全materialize unit横断で検証する
- runtime issue回答の再開preflightで、現在generation不一致時に旧回答を自動適用しない
- legacy
- runtime利用確認 / Markdown再読込

### Step 12: 全体検証・文書同期

- runtime unit / CLI integration / deterministic / semantic / workflow
- trigger datasetのSkill別exact count（repository合計328）・正負件数・境界scenario
- semantic datasetのSkill別exact count（repository合計51）と意味判断責務→case対応
- `test-analysis / test-condition-design / adversarial-review`の本Plan追加・更新semantic caseについて保存candidate outputを既存semantic runner + runner protocolに適合する外部Judge commandで実評価し、command / Judge結果をPR検証記録へ残す。特定provider用Judge adapterは本Planへ追加せず、Judge未実施ならsemantic case PASSを完了扱いしない
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

runtime dependencyはPython 3.11標準ライブラリだけとし、実装中の外部dependency追加を認めません。正確性とhard limitを満たせない場合はPlan未達として停止します。interpreter command名とtimeout機構はAgent / host依存とし、30秒timeoutはCIの安全策に限定します。

## 14. 完了条件

- model dispatchは`model_type → generator`固定表だけを使い、adapter親でCoverage child欠落を隠さない
- Machine Entityが既存Skillの後続利用fieldを保持する。TR / TCN / CI / TCの`priority_override_reason`、Product Riskの評価根拠・信頼度、Technique Selectionのundetermined signal closure、change graphの変更種別・想定影響、modelの`derived_from_model_key`をMarkdownだけへ残さない。CIからcanonical execution / semantic item本文、TCからenvironment / test data requirement依存を追跡できる
- canonicalization後の実処理順、stable ID採番順、deleted遷移、state / flow execution、grammar derivation、exact numericが固定規則と一致する

Plan完了には次をすべて満たす必要があります。

- `_01`で実装対象にした処理がruntimeまたは既存機械処理へ割り当てられている
- 目的内の技法・構造処理が本Plan外へ先送りされていない
- CLI / strict JSON / exact JSON number / envelope / canonicalization / envelope・runtime・generator contract versionが実装済み
- `spec-analysis / test-analysis / test-requirement-design / test-condition-design / test-case-design`がPython固定builderでcanonical `Machine Entities`とexpected Entity identityを生成・保存し、`entity_type`を含む`(skill, entity_type, entity_ref)` identity、content fingerprint、`upstream_entity_dependencies[] / runtime_dependencies[]`をMarkdown再解釈なしで再構築できる。actual Machine Entity集合からexpected集合を逆算しない
- script固有inputのsemantic reference集合から必要な`upstream_entities[]`を固定builderで完全導出し、そのmachine dataからcanonical contentを機械構築してcontent fingerprintをruntime計算できる。省略・余分な参照Entityを拒否し、sort済み`upstream_entity_fingerprints`を含むgeneration fingerprint、`(skill, runtime_unit_key)` upstream dependency、static data versions、input / model / LF正規化implementation fingerprintが再現可能
- model / artifact全runtime unitの`Machine Runtime Input / Result`を決定論的に抽出し、strict decode、fingerprint一致、同条件でのround-trip再実行が成立する。workflow再利用では保存済みresultをcurrent cacheとして採用せず現在scriptを再実行する。model resultと集約runtime rowは`runtime_contract.py`固定projectionから作り、`upstream_entity_fingerprints[]`や`freshness_status`をcaller / LLMが補完しない
- stable model key / TR / TCN / TCのruntime採番、active / deleted ID state、1 model = 1 TCN、target_ref、成果物系列、previous mapping、merge / unmerge / CI↔Disposition状態遷移を含むCI materializeが契約どおり。TR / TCN / model / TCのpartial rerunではprevious full snapshotを維持し、`update_scope_*`内だけdeleted遷移させてscope外activeを保持する。legacy初回昇格は現在観測できるactive IDだけをseedし、`legacy_ci_seed[]`で一意対応できる既存CIだけ通常mappingへ移す
- 各generatorのtargetがPlan固定の`materializable`を持ち、CI化する全targetがgenerator別canonical `execution / execution_fingerprint`を持つ。EP / BVA / Domain / Decision / combinatorial / grammar / Random / Metamorphicを含め、executionだけで下流が対象・値・条件・期待関係を理解できる。combinatorial targetはdeterministic full rowへ対応し、adapter専用generatorを直接CI化しない。同一CI mergeは同一TCN・同一model・同一execution・同一expected resultに限定される。異なるmodelの同一実行はTCの複数`ci_refs[]`で表現する
- 再実行がupsertされ重複machine evidenceを作らない
- semantic dependency preflight済みの現在script正常実行結果だけを保存時`freshness_status=current`とし、`workflow_runtime.py`が再検証してstale伝播する。freshnessの付与主体をworkflowだけに限定せずmaterialize前の循環を作らない
- stale派生成果物を完了扱いしない
- `technique_slug`が正規技法だけを表し、内部adapterは正規技法を所有しない。adapter / Coverage childを同じ`condition_structure.py`実行で先に採番し、childが`selection_source / selection_key / derived_from_model_key`を保持する。child model Entityはadapter model Entityへ依存するが未実行adapter runtimeへ依存せず、親adapter runtimeがcurrent readyかつ当該childの`derived_child_inputs[]`が1件になるまでchild generatorをdispatch / expected集合へ追加しない。adapterは意味parameter不足時に`semantic_parameter_requests[]`で`unresolved`、ready時に全child分の直接互換`derived_child_inputs[]`を返す。active Technique Selectionの各selected techniqueが1件以上のcurrent Coverage modelへ到達する。不適用 / 未解決はTechnique Selection更新または既存block / unresolvedで扱い、未定義のselection closureを作らない。エラー推測は1件以上のsemantic CIへ入る
- machine-readable schema / HTMLをLLMが手変換せず対応scriptが処理する。HTML runtime-v1は`text / number / date / datetime-local`のtype / attribute matrix、disabled / readonlyのvalidation除外、pattern等のunsupportedを契約どおり扱う。OpenAPI runtime-v1は解析済みstrict JSON objectを入力とし、YAML parserや追加dependencyをruntimeへ導入しない
- script間の機械変換ではadapter / child modelを親runtime実行前に`condition_structure.py`で採番し、adapter script自身が固定derived schemaと意味parameterからchild generator互換`derived_child_inputs[]`を生成する。LLMは`semantic_parameter_requests[]`で要求された意味parameterやtarget annotationだけを追加し、machine dataやruntime dependencyを再生成しない
- 全技法generatorと構造scriptにunit testがあり、Syntax-Based Testingのunreachable productionは`unresolved` issue、partial unsupported itemはscript別固定`reason_code`で検証される
- 通常/集約stdin、stdout、item数、byte、depth、state / flow / grammarを含む探索node hard limitとtie-breakが契約どおり。巨大exponentはcanonical文字列展開前に桁数上限を判定し、fixed-offset datetimeのrange比較はabsolute instantを使用する
- runtime出力と保存machine evidenceの一致をvalidatorが確認する
- support判定をruntimeが行い、whole-model `unsupported`、`partial`、Python unavailableを契約どおり区別する。script schemaで1件以上必須のfieldが空なら`invalid_input`、schemaは成立するが意味parameter / 母集団未確定なら`unresolved`とし、対応subset外の`unsupported / partial`と混同しない。supported inputをAgent判断だけでruntime省略しない
- model内Coverageと仕様全体Coverageを混同しない
- `workflow_runtime.py`は自身を除く本Plan対象runtime unitの期待集合が1件以上ある場合だけdispatchし、model / artifact両runtime unit、Machine Entityのsemantic / runtime dependency、upstream Entity内容変更、`(skill, runtime_unit_key)` dependency、Python固定builderがactualと独立導出したexpected runtime / Entity集合のmissing / extra、dependency missing / duplicate / cycle、generation / implementation変更、stale、current materialize `model_completion[] / target_mappings[] / target_dispositions[]`によるCoverage所有model単位の完了、target`重複`graph、partial / whole-model unsupported closure、局所ブロック、legacyを処理できる。自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`へ含めず、self inclusionを`invalid_input`にする。本Plan対象runtimeが0件のE2E-only経路ではdispatchせず既存`qa-workflow`契約を維持する。`can_complete`は本Planruntime範囲の必要条件であり、混在workflowでは既存E2E等の完了条件を別途満たすまでworkflow全体を完了にしない
- `traceability.py`と`workflow_runtime.py`が同じ`runtime_contract.py` freshness / closure関数から同じruntime / Entity freshnessとmodel closureを得る。workflow_runtime resultをtraceabilityの依存入力にせず、traceability自身とworkflow_runtime自身をtraceabilityのfreshness入力runtime集合へ含めない
- 既存成果物を再利用する場合、保存済みsemantic model / draftの上流Entity dependencyをruntime再実行前に確認し、不一致なら担当Skillで意味再確認する。freshな意味入力だけを現在scriptへ再投入し、materialize / traceability / workflow freshnessに循環を作らない
- 以前whole-model `unsupported`だった成果物も再利用時に現在runtimeでsupport判定を再実行し、現在supportedなら古いfallbackを維持しない
- question-analysis往復でRuntime Skill / Runtime Unit / model / target / generation fingerprintが失われず、`qa-workflow`の回答適用前preflightで未解決inputを現在runtimeへ再実行して世代一致を確認する。別generationまたはfingerprint未確定issueへ古い回答を自動適用しない
- target内容またはruntime generation変更時にstable `target_ref` / CI IDを維持しても、古いannotation / Disposition / merge判断と下流TCをcurrent扱いしない
- environment requirementは同一`environment_key`内だけ同時成立を検査し、異なるkeyを代替環境としてcross-intersectionしない。test data requirementはmodel-wide / target-specificの適用範囲を維持し、target・merge group・TCで実際に同時成立する要求集合だけintersectionする。どちらも元の`requirement_key` identityを維持する
- unsupported closureは対象generationとreasonが現在値に一致し、許可されたhandling・必要なcurrent`covered_by_entity`の完全identity / fingerprint・既存Disposition条件を満たす場合だけ閉鎖済みとして再利用する。`llm_fallback`は同じmodelのcurrent CIへ解決し、`ブロック中`closureは完了不可。target Dispositionの`重複`はself / cycleがなくcurrent CI / semantic CIへ終端する場合だけ閉鎖済みにする
- `input_mode=direct|artifact`が途中工程開始と成果物再利用を分離し、directでは前工程Machine Entity / Skill directoryを強制せず、artifactでは必要Machine Entityのmissing / extraを拒否する。direct由来成果物は自Skill Machine Entityを保存済みという理由だけでartifactへ強制移行せず、必要な外部Entityがすべて揃った時点だけ切り替える。途中工程開始と`Selection Source=analysis / condition_design / user`が既存workflowを壊さず、runtime派生元をSelection Sourceへ混ぜず、model reuseが選択元を失わず、undetermined signalが未閉鎖のまま完了しない
- CIでは全runtime scriptのdispatch / metadata整合、複数用途Skillの対象限定、active Coverage所有modelがあるTCNの`materialize_coverage.py`必須dispatch、E2E-onlyでの`workflow_runtime.py`非dispatch、Coverage targetのCI / Disposition閉鎖、Cause-Effect constraint伝播、Decision Table don't-care merge非破壊性、fork/join concurrencyのlinear execution禁止を確認し、実Agent smokeでは代表promptでPython起動、envelope parse、Machine Entity / runtime result採用、Markdown再読込、現在script再実行まで確認できる
- runtime対象6 Skillの単体移植性が成立し、`spec-analysis`を含む7 Skillのcanonical / Machine Entity helper内容一致を検証できる
- trigger datasetがSkill別exact count（repository合計328）を満たし、新規技法5種のselection / design境界をtrain・validation双方で検証する
- semantic datasetがSkill別exact count（repository合計51）を満たし、LLMへ残す意味判断責務が少なくとも1 caseへ対応する。加えて`test-analysis / test-condition-design / adversarial-review`の本Plan追加・更新caseは保存candidate outputを既存semantic runner + runner protocolに適合する外部Judge commandで実評価してPASSし、実行commandとJudge結果がPR検証記録に残る。dataset validation / fake judge CIだけをsemantic PASSとしない
- stateの`all-states`がmodel内全state、`valid-transitions`がvalidと確定した全transitionをrequired母集団とし、setup不能required itemを無言で除外しない。Round-tripは開始state違いを別targetとして扱い、Domain Testingがexact rationalで対象border以外のIN条件を検証し、Decision Tableのdon't-care mergeは対象conditionの成立可能な全関連valueが同一action vectorの場合だけ許可して多値conditionの一部一致を統合しない
- structure / traceabilityが共通Disposition schemaを扱い、JSON Schema 2020-12の`$id / $ref` resource境界と`$ref` sibling、local URI fragmentのpercent-decode / UTF-8 / RFC 6901 escape / array index、不正escape、self / mutual cycleの局所`unsupported`、OpenAPI 3.0 Reference Object / `nullable / readOnly / writeOnly`、HTML numberのdefault step / `step=any` / step baseをPlanの対応subsetどおり処理し、raw schema数値をstringと混同せずbinary float / context roundingなしで処理する
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
- runtime envelopeのpayloadをLLM / Agentが手でflattenしてmaterialize / workflow入力を作る
- `runtime_contract.py`以外のSkill-local helperへruntime実行ロジックを逃がし、implementation fingerprint対象外の変更を作る
- machine-readable入力を対応scriptがあるのにLLMへ再変換させる
- runtime dependencyを`runtime_unit_key`単独でSkill横断参照する
- target key componentへdelimiter `:`を許可する
- Domain borderやschema numeric keywordをbinary float / context roundingで近似する
- `workflow_runtime.py`自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`のいずれかへ含める
