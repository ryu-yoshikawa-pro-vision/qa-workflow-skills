# テスト分析・テスト技法の決定論的自動化Plan

このファイルは実装順序、リスク、完了条件をまとめます。[評価・CI契約](./2026-09-18_170000_deterministic-test-technique-automation_05_evaluation-ci-implementation-order.md)および[validator・CI・文書更新](./2026-09-18_170000_deterministic-test-technique-automation_05_validation-ci-and-docs.md)と合わせて参照します。

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
- `spec-analysis`へ`runtime_contract.py`のcanonical / Machine Entity helperと`authority_entities.py`を追加し、Authority Machine Entity / expected identityを決定論的に生成する。runtime unitは追加しない
- `(skill, runtime_unit_key)` upstream runtime dependency
- support_statusと対応subset判定。`runtime_required`は入力fieldにせずruntime出力として導出
- 全runtime unitの`Machine Runtime Input / Result`保存、決定論的抽出 / round-trip再投入。workflow再利用では保存済みresultをcurrent cacheにしない
- 通常stdin 2 MiB / 集約stdin 16 MiB / stdout 16 MiB / depth / 探索node hard limit
- tie-break
- runtime / Machine Entity dependencyを評価する共通freshness関数。runtime対象6 Skillで使用し、canonical / Machine Entity helper部分は`spec-analysis`を含む7 Skillの`runtime_contract.py`で同一実装にする
- structured issue / blocking
- 複数用途Skillのruntime dispatchを`test-analysis: テスト分析`、`coverage-analysis: テスト設計`へ限定する
- 7 Skillの`runtime_contract.py`でcanonical / Machine Entity helper内容を一致させ、runtime対象6 Skillではruntime実行部分も一致させる。LF正規化implementation fingerprintを検証する

### Step 2: identity / workflow基盤

- canonical technique slugと内部`model_type`を分離し、dispatchは`model_type → generator`固定表だけを使う
- 内部adapterは正規技法を所有せず、Coverage child modelが`selection_source / selection_key / technique_slug / derived_from_model_key`を保持する。adapter draftとchild draftを同じ`condition_structure.py`実行へ入れて先にidentityを確定する。adapter scriptは不足する意味parameterを`semantic_parameter_requests[]`で返し、再実行後にchild generatorと直接互換な`derived_child_inputs[]`を生成する。親runtime後に新しいchild identityを追加する循環や匿名builderでmachine inputをjoinする経路を作らない。1 selection → 複数modelを許可する
- `requirement_structure.py` / `condition_structure.py` / `case_structure.py`によるTR / TCN・model / TC採番
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
- question-analysisのRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprint保持と、回答適用前の`qa-workflow`再開preflight。現在runtime generationが質問generationと不一致なら旧回答を適用しない
- coverage-analysisのModel Key / Disposition追跡
- 各SkillのPython固定builderがactual集合から独立したnormalized source / structure stateから`expected_runtime_units[] / expected_entities[]`を生成し、`workflow_runtime.py`が実際集合との完全一致を検査する。Agentが期待identityを手入力せず、expected生成で`current_entities[] / runtime_units[] / current_runtime_units[]`や保存済みMachine Entity blockを参照しない
- 正常fixtureからMachine Entity 1件を削除しても`expected_entities[]`が変わらずmissing blockerになる回帰と、runtime unit 1件を削除しても`expected_runtime_units[]`が変わらずmissing blockerになる回帰を必須にする
- `workflow_runtime.py`によるSkill状態表 + runtime状態表（model / artifact両runtime unit）の機械集約。`qa-workflow::artifact:workflow_runtime:all`自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`の3集合すべてから除外し、self inclusionを`invalid_input`にする
- legacy昇格

### Step 2.5: 代表generatorと共通経路の成立確認

後続generatorを量産する前に、代表generatorとして`equivalence_partitions.py`を先行実装し、次を同一PR内で通します。Step 5ではEPを再実装せず、この実装へBVA等を追加します。

`LLM正規化 → condition_structure.py → TCN / EP model Machine Entity保存 → semantic dependency preflight → EP dispatch → runtime再実行 → Machine Runtime Input / Result保存 → target annotation → CI materialize → validator → workflow_runtime → Markdown再読込 → semantic dependency preflight → runtime再実行`

この時点で実Agentのartifact transport境界も確認し、16 MiB未満の上限が必要なら後続generator実装前に`runtime-v1`へ固定します。

ここで見つかった共通契約不整合はStep 1 / 2へ戻して修正します。この確認を完了扱いの区切りにはせず、修正後は同じPRでStep 3以降の全対象を実装します。

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
- schema / HTML parser / exact JSON number / scalar-null enum・const / root document + local `$ref` / OpenAPI request-response context
- HTML runtime-v1 typeを`text / number / date / datetime-local`へ限定し、disabled / readonlyのconstraint validation除外、pattern / unsupported typeを安全側へ閉じる
- schemaから、既に選択・採番済みのEP / BVA / combinatorial childへmachine skeletonを生成する。BVA / combinatorialで意味parameterが必要なら`schema_cases.py`自身が`unresolved` + `semantic_parameter_requests[]`を返し、同script再実行で完成`derived_child_inputs[]`とtest data requirementを生成する。schema runtime結果から新しい技法 / child modelを自動追加せず、選択済みchildへskeletonを作れない場合はselection source別に戻す
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
- mergeは同一model・同一executionに限定し、追加test data requirement参照のintersectionを確認する。異なるmodelの同一TC実行はcase structureの複数`ci_refs[]`で検証する
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
- `test-analysis / test-condition-design / adversarial-review`の本Plan追加・更新semantic caseについて保存candidate outputを既存semantic runner + LLM Judge adapterで実評価し、command / Judge結果をPR検証記録へ残す。外部JudgeをCIへ追加せず、Judge未実施ならsemantic case PASSを完了扱いしない
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
- Machine Entityが既存Skillの後続利用fieldを保持する。TR / TCN / CI / TCの`priority_override_reason`、Product Riskの評価根拠・信頼度、Technique Selectionのundetermined signal closure、change graphの変更種別・想定影響、modelの`derived_from_model_key`をMarkdownだけへ残さない。CIからcanonical execution / semantic item本文、TCからenvironment / test data requirement依存を追跡できる
- canonicalization後の実処理順、stable ID採番順、deleted遷移、state / flow execution、grammar derivation、exact numericが固定規則と一致する

Plan完了には次をすべて満たす必要があります。

- `_01`で実装対象にした処理がruntimeまたは既存機械処理へ割り当てられている
- 目的内の技法・構造処理が本Plan外へ先送りされていない
- CLI / strict JSON / exact JSON number / envelope / canonicalization / envelope・runtime・generator contract versionが実装済み
- `spec-analysis / test-analysis / test-requirement-design / test-condition-design / test-case-design`がPython固定builderでcanonical `Machine Entities`とexpected Entity identityを生成・保存し、`entity_type`を含む`(skill, entity_type, entity_ref)` identity、content fingerprint、`upstream_entity_dependencies[] / runtime_dependencies[]`をMarkdown再解釈なしで再構築できる。actual Machine Entity集合からexpected集合を逆算しない
- script固有inputのsemantic reference集合から必要な`upstream_entities[]`を固定builderで完全導出し、そのmachine dataからcanonical contentを機械構築してcontent fingerprintをruntime計算できる。省略・余分な参照Entityを拒否し、sort済み`upstream_entity_fingerprints`を含むgeneration fingerprint、`(skill, runtime_unit_key)` upstream dependency、static data versions、input / model / LF正規化implementation fingerprintが再現可能
- model / artifact全runtime unitの`Machine Runtime Input / Result`を決定論的に抽出し、strict decode、fingerprint一致、同条件でのround-trip再実行が成立する。workflow再利用では保存済みresultをcurrent cacheとして採用せず現在scriptを再実行する
- stable model key / TR / TCN / TCのruntime採番、active / deleted ID state、1 model = 1 TCN、target_ref、成果物系列、previous mapping、merge / unmerge / CI↔Disposition状態遷移を含むCI materializeが契約どおり
- 各generatorのtargetがPlan固定の`materializable`を持ち、CI化する全targetがgenerator別canonical `execution / execution_fingerprint`を持つ。EP / BVA / Domain / Decision / combinatorial / grammar / Random / Metamorphicを含め、executionだけで下流が対象・値・条件・期待関係を理解できる。combinatorial targetはdeterministic full rowへ対応し、adapter専用generatorを直接CI化しない。同一CI mergeは同一TCN・同一model・同一execution・同一expected resultに限定される。異なるmodelの同一実行はTCの複数`ci_refs[]`で表現する
- 再実行がupsertされ重複machine evidenceを作らない
- semantic dependency preflight済みの現在script正常実行結果だけを保存時`freshness_status=current`とし、`workflow_runtime.py`が再検証してstale伝播する。freshnessの付与主体をworkflowだけに限定せずmaterialize前の循環を作らない
- stale派生成果物を完了扱いしない
- `technique_slug`が正規技法だけを表し、内部adapterは正規技法を所有しない。adapter / Coverage childを同じ`condition_structure.py`実行で先に採番し、childが`selection_source / selection_key / derived_from_model_key`を保持する。adapterは意味parameter不足時に`semantic_parameter_requests[]`で`unresolved`、ready時に全child分の直接互換`derived_child_inputs[]`を返す。active Technique Selectionの各selected techniqueが1件以上のcurrent Coverage modelへ到達する。不適用 / 未解決はTechnique Selection更新または既存block / unresolvedで扱い、未定義のselection closureを作らない。エラー推測は1件以上のsemantic CIへ入る
- machine-readable schema / HTMLをLLMが手変換せず対応scriptが処理する。HTML runtime-v1は`text / number / date / datetime-local`のtype / attribute matrix、disabled / readonlyのvalidation除外、pattern等のunsupportedを契約どおり扱う
- script間の機械変換ではadapter / child modelを親runtime実行前に`condition_structure.py`で採番し、adapter script自身が固定derived schemaと意味parameterからchild generator互換`derived_child_inputs[]`を生成する。LLMは`semantic_parameter_requests[]`で要求された意味parameterやtarget annotationだけを追加し、machine dataやruntime dependencyを再生成しない
- 全技法generatorと構造scriptにunit testがある
- 通常/集約stdin、stdout、item数、byte、depth、state / flow / grammarを含む探索node hard limitとtie-breakが契約どおり
- runtime出力と保存machine evidenceの一致をvalidatorが確認する
- support判定をruntimeが行い、whole-model `unsupported`、`partial`、Python unavailableを契約どおり区別する。supported inputをAgent判断だけでruntime省略しない
- model内Coverageと仕様全体Coverageを混同しない
- `workflow_runtime.py`がmodel / artifact両runtime unit、Machine Entityのsemantic / runtime dependency、upstream Entity内容変更、`(skill, runtime_unit_key)` dependency、Python固定builderがactualと独立導出したexpected runtime / Entity集合のmissing / extra、dependency missing / duplicate / cycle、generation / implementation変更、stale、current materialize `model_completion[] / target_mappings[] / target_dispositions[]`によるCoverage所有model単位の完了、target`重複`graph、partial / whole-model unsupported closure、局所ブロック、legacyを処理でき、自身を`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`へ含めず、self inclusionを`invalid_input`にする
- `traceability.py`と`workflow_runtime.py`が同じ`runtime_contract.py` freshness / closure関数から同じruntime / Entity freshnessとmodel closureを得る。workflow_runtime resultをtraceabilityの依存入力にせず、traceability自身とworkflow_runtime自身をtraceabilityのfreshness入力runtime集合へ含めない
- 既存成果物を再利用する場合、保存済みsemantic model / draftの上流Entity dependencyをruntime再実行前に確認し、不一致なら担当Skillで意味再確認する。freshな意味入力だけを現在scriptへ再投入し、materialize / traceability / workflow freshnessに循環を作らない
- 以前whole-model `unsupported`だった成果物も再利用時に現在runtimeでsupport判定を再実行し、現在supportedなら古いfallbackを維持しない
- question-analysis往復でRuntime Skill / Runtime Unit / model / target / generation fingerprintが失われず、`qa-workflow`の回答適用前preflightで未解決inputを現在runtimeへ再実行して世代一致を確認する。別generationまたはfingerprint未確定issueへ古い回答を自動適用しない
- target内容またはruntime generation変更時にstable `target_ref` / CI IDを維持しても、古いannotation / Disposition / merge判断と下流TCをcurrent扱いしない
- unsupported closureは対象generationとreasonが現在値に一致し、許可されたhandling・必要なcurrent`covered_by_entity`の完全identity / fingerprint・既存Disposition条件を満たす場合だけ閉鎖済みとして再利用する。`llm_fallback`は同じmodelのcurrent CIへ解決し、`ブロック中`closureは完了不可。target Dispositionの`重複`はself / cycleがなくcurrent CI / semantic CIへ終端する場合だけ閉鎖済みにする
- 途中工程開始と`Selection Source=analysis / condition_design / user`が既存workflowを壊さず、runtime派生元をSelection Sourceへ混ぜず、model reuseが選択元を失わず、undetermined signalが未閉鎖のまま完了しない
- CIでは全runtime scriptのdispatch / metadata整合、複数用途Skillの対象限定、Coverage targetのCI / Disposition閉鎖、Cause-Effect constraint伝播、Decision Table don't-care merge非破壊性を確認し、実Agent smokeでは代表promptでPython起動、envelope parse、Machine Entity / runtime result採用、Markdown再読込、現在script再実行まで確認できる
- runtime対象6 Skillの単体移植性が成立し、`spec-analysis`を含む7 Skillのcanonical / Machine Entity helper内容一致を検証できる
- trigger datasetがSkill別exact count（repository合計328）を満たし、新規技法5種のselection / design境界をtrain・validation双方で検証する
- semantic datasetがSkill別exact count（repository合計51）を満たし、LLMへ残す意味判断責務が少なくとも1 caseへ対応する。加えて`test-analysis / test-condition-design / adversarial-review`の本Plan追加・更新caseは保存candidate outputを既存semantic runner + LLM Judge adapterで実評価してPASSし、実行commandとJudge結果がPR検証記録に残る。dataset validation / fake judge CIだけをsemantic PASSとしない
- stateの`all-states`がmodel内全state、`valid-transitions`がvalidと確定した全transitionをrequired母集団とし、setup不能required itemを無言で除外しない。Round-tripは開始state違いを別targetとして扱い、Domain Testingがexact rationalで対象border以外のIN条件を検証し、Decision Table mergeが未定義assignmentを包含しない
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
