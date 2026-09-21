# テスト分析・テスト技法の決定論的自動化Plan

このファイルは実行時契約の後半です。[共通runtime・Machine Entity契約](./2026-09-18_170000_deterministic-test-technique-automation_02_runtime-architecture-and-contracts.md)から続けて参照します。

## 7. stable ID・upsert・stale

### 7.1 QA ID

既存prefixは維持します。

- `TR-`
- `TCN-`
- `TCN-xxx-CIyy`
- `TC-`

同じ意味の既存項目を再利用できる場合は既存IDを維持します。TR / TCN / TCおよび技法modelの意味上の同一性判断は担当SkillのLLM責務であり、runtimeがsemantic matchingしません。LLMは各draft entityへ`reuse_id`または`new`を明示し、実際の番号割当てはruntimeが行います。

- `requirement_structure.py`: TRの既存ID維持 / 新規採番
- `condition_structure.py`: TCNと`model_key`の既存ID維持 / 新規採番、modelと親TCNの1対1所属検証
- `materialize_coverage.py`: CI採番
- `case_structure.py`: TCの既存ID維持 / 新規採番

qa-workflowが再利用元として選んだ同種成果物を同じ系列とし、新規項目だけその成果物内の最大番号+1で採番します。再利用元がない新規成果物では001から開始し、削除済みIDを同じ系列で再利用しません。

同一実行で複数の`new` draftへ採番する場合はcanonicalization後の`draft_key`順で割り当て、raw JSON配列順を使いません。CIは`materialize_coverage.py`のcanonical candidate順を使います。1つの`model_key`は同時に1つのTCNだけへ所属し、別TCNで同じmodelを再利用する場合は意味上別modelとして別`model_key`を発行します。

TR / TCN / TCは既存の3桁形式をこのPlanで変更しません。最大番号が999に達した成果物系列で新規IDが必要な場合は削除済みIDを再利用せず、`id_space_exhausted` issueとしてブロックします。CIは完全IDを`TCN-\d{3}-CI\d{2,}`、TCN配下の採番suffixを`CI\d{2,}`とします。`previous_ci_ids[] / legacy_ci_ids[] / mapping / Machine Entity`は常に完全`ci_id`を保持し、採番・最大番号比較時だけ同一TCN prefixを検証したうえで末尾のCI番号を取り出します。CI suffixは2桁以上を許可するため999上限を持ちません。

### 7.1.1 部分更新時のID状態

`qa-workflow`は既存契約どおり影響範囲だけを担当Skillへ戻せるため、structure scriptは「current draftに出なかったprevious active IDをすべてdeletedにする」と解釈しません。

- previous ID stateは成果物系列全体のfull snapshotを渡し、過去最大番号とdeleted履歴を失わない
- 各structure scriptへ、今回そのscriptがlifecycleを確定する既存IDの集合を`update_scope_*`として明示する
- `update_scope_*`内のprevious active IDだけ、currentでreuseされなければ`deleted`へ遷移する
- `update_scope_*`外のprevious active / deleted rowは状態を変更せずそのまま次のfull snapshotへ引き継ぐ
- reuse対象は対応する`update_scope_*`内のactive IDに限定する。意図した削除はIDをscopeへ含めたうえでcurrent draftから外すことで表現する
- full rebuildではprevious active IDをすべて`update_scope_*`へ含める
- new draftはscope指定を必要とせず、過去のactive / deleted全行から算出した最大番号の次を採番する

対象は`requirement_structure.py`のTR、`condition_structure.py`のTCN / model、`case_structure.py`のTCです。`materialize_coverage.py`は既存どおりTCN単位を更新境界とし、TCN配下の全current active model metadataとmapping stateを受けるため、modelの一部だけを渡して他modelのCIを暗黙削除する経路を作りません。

### 7.2 Coverage targetとCI

generator内の`target_key`はmodel内で安定させます。異なるmodel間の衝突を避けるため、成果物横断のtarget identityとして`target_ref`を追加します。

`target_ref = sha256(canonical JSON({"model_key": <model_key>, "target_key": <target_key>}))`

- `target_ref`は`sha256:<64 lowercase hex>`
- model generatorの共通post-processで各targetへ`target_ref`を付与する
- この共通post-processは`test-condition-design/scripts/runtime_contract.py`の固定helperとして実装し、`target_ref / execution_fingerprint / target_content_fingerprint`を同じcanonicalization規則から生成する。各generatorへ同じhash処理を複製せず、generatorは技法固有のmachine fieldとcanonical `execution`だけを返す
- 同じ`model_key + target_key`から常に同じ`target_ref`を得る
- CIへmaterialize可能な各targetは、具体的にそのCoverageを実行する値・assignment・sequence・path等をgenerator固有のcanonical object `execution`として持つ。診断metadataだけではCI化しない
- 共通post-processで`execution_fingerprint = sha256(canonical JSON(execution))`を付与する。LLMが`execution`やhashを再生成しない
- 各targetへ`target_content_fingerprint = sha256(canonical JSON(targetのうちtarget_ref / target_content_fingerprint / execution_fingerprintを除く全machine field))`を付与する。`execution`、Authority / Reference、技法固有fieldを含める
- `target_ref`はstable ID、`target_content_fingerprint`はその時点のtarget内容、`execution_fingerprint`は具体実行の同一性確認に使う。target内容が変わってもstable ID維持のため`target_ref`は変えない
- hashが同じなのにmodel_key / target_keyが異なる場合は`internal_error`

`materialize_coverage.py`のinputには`previous_target_id_map[]`を明示的に渡します。

```json
[
  {
    "target_ref":"sha256:...",
    "model_key":"bva-001",
    "target_key":"bva:age-lower:AT",
    "target_content_fingerprint":"sha256:...",
    "ci_id":"TCN-001-CI01",
    "mapping_status":"active"
  }
]
```

- 初回mappingがない場合、同一TCN内のtargetを`model_key`、次に`target_key`のUnicode code point辞書順でsortし、`CI01`から順に採番する
- 既存active mappingがある場合、同じ`target_ref`は既存CI IDを維持する。inactive mappingは§7.2.2の復帰規則でだけ再利用する
- 同じ`target_ref`でも`target_content_fingerprint`が前回mappingから変わった場合はCI IDを維持したままそのCIと下流TCを`要再検証`へし、旧`target_annotations / target_dispositions / merge_group`を現在targetへ自動再利用しない。generationだけが変わった場合も意味判断は再確認するが、stable ID自体は維持できる
- 新しい`target_ref`は同一TCN内の既存CI最大番号+1から採番する
- 消滅target_refのCIはstaleとし、下流TCを`要再検証`へする
- 削除済みCI番号を再利用せず、既存CI番号の詰め直しを行わない
- previous mappingの`target_ref`をmodel_key / target_keyから再計算し、不一致を拒否する
- 同一`target_ref`が複数CIへ割り当てられる場合、親TCN不一致、merge group外で同一CIへ複数target_refが割り当てられる場合は`invalid_input`
- 同一CIへ複数target_refを割り当てるのは、同一`merge_group`で明示されたtargetだけ許可する。mappingはtarget_refごとに1行保持し、同じ`ci_id`を共有できる
merge / unmerge / target追加削除 / CI↔Dispositionの詳細な状態遷移は§7.2.2を正本とします。

### 7.2.1 ID状態の永続化

各成果物へactive / deleted状態をfull snapshotとして保存します。

- TR: `{tr_id, status}`
- TCN: `{tcn_id, status}`
- model: `{model_key, model_type, technique_slug, parent_tcn_id, selection_source, selection_key, status}`
- TC: `{tc_id, status}`
- CI: `{ci_id, status}`

TR / TCN / model / TCは§7.1.1の`update_scope_*`規則に従い、今回の更新scope内にあるprevious active IDだけをcurrentでreuseされなければ`deleted`へ遷移させます。scope外activeは維持し、previous deleted rowも保持して別項目へ再利用・復活させません。

CIは§7.2.2のtarget mapping状態遷移を優先し、同sectionで明示した同一targetへの復帰以外でdeleted番号を再利用しません。

### 7.2.2 CI mappingの状態遷移

再実行時は次を固定します。

- unmerged → merged: group内に既存active CIが複数ある場合、数値部分が最小のCIを存続CIとし、他CIをdeletedへ移す。存続CIを含む関連TCも意味変更として`要再検証`
- merged groupへtarget追加: 既存groupの存続CIへ追加し、関連TCを`要再検証`
- merged groupからtarget削除 / Disposition: 残存targetが1件以上なら存続CIを維持し、関連TCを`要再検証`。0件ならCIをdeleted
- merged → unmerged: 辞書順で最初の存続targetへ既存CIを維持し、他targetへ同一TCNの過去使用済み最大CI番号+1から新規採番
- CI → Disposition: targetのactive mappingを外す。CIを共有する他targetがなければCIをdeleted、共有targetが残ればCIは維持する。どちらも関連TCを`要再検証`
- Disposition → CI: targetの直近CIがdeletedで、現在ほかのactive targetへ割り当てられていなければ同じCIを復帰してよい。そうでなければ過去使用済み最大CI番号+1から新規採番
- deleted CI番号を別targetへ再利用しない

`previous_target_id_map[]`はactive mappingだけでなく`mapping_status=active|inactive`、直近`ci_id`、その判断時点の`target_content_fingerprint`を保持し、Disposition中のtargetも過去mappingを失いません。`ci_id`は完全形式`TCN-\d{3}-CI\d{2,}`を保持し、同一TCN内の採番比較ではsuffix `CI\d{2,}`の数値部分だけを使用します。
### 7.3 upsert

再実行はappendではなくstable keyでupsertします。

- 同じ`target_ref`は置換する。`target_content_fingerprint`が変わった場合はstable IDを維持しても意味変更として扱い、関連CI / TCと意味判断を`要再検証`へ戻す
- 生成されなくなった派生行はstaleとして除去候補にする
- 同一再実行で重複machine evidenceを作らない
- staleな派生成果物が残る状態を完了扱いしない

### 7.4 Coverage targetの成果物上の閉鎖

各`target_ref`はCI mappingまたは`target_dispositions[]`のどちらか一方へ閉じます。

`target_dispositions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint, handling, reason, authority_refs[], covered_by_target_version}`です。

- source targetのcontent / generation fingerprintは現在値と一致必須
- `handling=対象外 / 別テストレベル / 残存リスク / ブロック中 / 重複`だけを許可
- `重複`では`covered_by_target_version={target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint}`を必須とする。`execution_fingerprint`は参照先が`materializable=true`なら非null current値、semantic Coverage Itemへ閉じる`materializable=false` targetなら`null`とする。source target自身の参照を禁止する。同一`materialize_coverage.py`入力内に参照先targetが存在する場合はそのcurrent versionと即時照合し、別TCN等でlocal inputに存在しない参照先は完全versionを保持したまま最終集約へ渡す。`traceability.py / workflow_runtime.py`が全materialize結果を集約して参照先current target versionとの完全一致、missing / stale、cycleを検査し、`重複`chainの終端がcurrent CI mappingまたはcurrent semantic Coverage Itemへ到達しない場合は閉鎖済みに数えない
- 他handlingでは`covered_by_target_version=null`
- 同一targetへCI mappingとDispositionを同時指定しない
- `ブロック中`はworkflow完了不可

Dispositionはgeneratorの`coverage_summary`または`completion_summary`を書き換えません。

`merge_groups[]`は`{merge_group_key, model_key, target_refs[], target_versions[]}`で固定します。`merge_group_key`はstable component key、`target_refs[]`は2件以上で重複不可、`target_versions[]`は各targetについて`{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint}`を1件ずつ持ちます。全targetは同一TCN・同一`model_key`・Dispositionなし・current versionで、`execution_fingerprint`と`expected_result_root`が一致する場合だけmergeできます。入力は`merge_group_key`順、各group内は`target_ref`順にcanonicalizeします。

## 8. machine evidenceとMarkdown

### 8.1 正規化済みモデル

`test-condition-design`を中心に、scriptへ再投入できる正規化済みJSONを成果物へ保持します。

一覧表:

`Runtime Unit Key | モデルキー | 観点ID | 技法 | runtime contract version | generator contract version | input fingerprint | model fingerprint | generation fingerprint | upstream entity count | static data versions | runtime status | result status | runtime required | freshness | deterministic generated | fallback reason`

全runtime unitについてcanonicalな実行入力と実行結果を成果物へ保存します。

````markdown
### Machine Runtime Input: test-condition-design::model:comb-001

```json
{"metadata":{...},"input":{...}}
```

### Machine Runtime Result: test-condition-design::model:comb-001

```json
{"runtime_unit_key":"model:comb-001",...}
```
````

見出しidentityは`<skill>::<runtime_unit_key>`で、JSON内metadataのSkill所属と`runtime_unit_key`が一致しなければvalidatorを失敗させます。model scriptでは`Machine Runtime Input.input`が正規化modelの正本です。必要なら`Machine Model: <model_key>`表示をruntimeから派生描画できますが、LLMが別JSONを作らず、canonical `input` subtreeと一致を必須にします。artifact全体scriptも同じ形式で入力を保存するため、validatorは全scriptの`input_fingerprint`を保存済み入力から再計算できます。

ここへ保存するruntime inputとMachine Entityは[実行時アーキテクチャ・契約](./2026-09-18_170000_deterministic-test-technique-automation_02_runtime-architecture-and-contracts.md)の機密情報規則を適用済みのcanonical dataだけを使用します。password、token、cookie、secret値そのものをround-trip可能なmachine evidenceへ保存しません。

人間向け説明文はLLMが生成して構いません。machine evidenceのJSON、key、ID対応、Coverage値をLLMが再計算・改変しません。runtime blockのJSON抽出もLLMへ委ねず、`runtime_contract.py`の抽出処理を使用します。

§4.4の`Machine Entities` blockはruntime evidenceとは別の意味上の正本です。`spec-analysis`を含む各担当Skillのvalidatorはstrict JSON decode、schema、`(skill, entity_type, entity_ref)`一意性、`content_fingerprint`再計算一致、人間向け表との主要field一致を確認します。既存成果物を再利用するときはこのblockから現在のcanonical Entityを取得し、runtime対象unitの入力を組み立て直します。保存済み`Machine Runtime Result`を現在世代のresultとしてそのまま採用しません。

### 8.2 machine evidenceの描画

共通のJSON fence出力、Markdown escape、runtime metadata行の描画は各Skill同梱の`scripts/runtime_contract.py`が担当します。Coverage target → CI materialize、merge group統合、Coverage Item表のmachine row生成は`test-condition-design/scripts/materialize_coverage.py`が担当します。

validatorはfenced JSON blockを抽出してstrict JSON decodeし、canonical化したmodel / fingerprint / machine evidenceが一致することを確認します。

必須round-trip test:

1. canonical runtime input / resultをMarkdownへ保存
2. `<skill>::<runtime_unit_key>`に対応するJSON fenceを一意に抽出
3. strict JSON decode
4. canonical化
5. 元の`input_fingerprint`、model scriptでは`model_fingerprint`も一致
6. 抽出したruntime inputを同じscriptへ再投入し、同一contract / implementation / static data条件なら同じmachine resultを得る

これにより`|`、backslash、改行を含む値をMarkdown table escapeへ依存させません。

## 9. 技法選択とmodelの閉鎖

正規技法modelのSelection Sourceは`analysis / condition_design / user`だけです。runtime派生元は`upstream_runtime_units[]`で表します。内部adapterは`technique_slug / selection_source / selection_key=null`です。

- `analysis`: `test-analysis`で技法を選択。`selection_key`必須
- `condition_design`: `test-condition-design`自身が正規技法を選択。`selection_key=null`
- `user`: ユーザー明示。`selection_key=null`
- model再利用は`identity_action=reuse|new`で管理し、Selection Sourceへ混ぜない
- `selection_source=analysis`の各Coverage所有modelは参照selectionの`selected_techniques[]`に同じ`technique_slug`が存在必須
- 1つの`selection_key + technique_slug`は複数TCN / modelへ展開してよい。ただしactiveなTechnique Selectionの`selected_techniques[]`に残っている各技法は、少なくとも1件のcurrent Coverage所有modelへ到達必須とし、ちょうど1 modelへ限定しない
- 選択後に不適用または未解決と判明した技法を「selection closure」という別schemaで閉じない。意味判断が変わった場合はTechnique Selection Entityを更新して`selected_techniques[]`から外すか、既存のblock / unresolved / question経路へ戻す
- runtime非対応はCoverage所有model生成後に既存の`unsupported_item_closures[]`またはwhole-model unsupported処理で閉じる。adapterだけ、Disposition行だけ、または未定義のselection closureだけでselected techniqueを完了扱いしない
- TCNの`technique_slugs[]`は所属Coverage所有modelの非null`technique_slug`集合と一致させる
- Classification Tree / Cause-Effect / schema / UI adapterは正規技法を所有しない。child Coverage modelがcanonical techniqueとselection provenanceを持つ
- エラー推測はsemantic CIを作るまで完了扱いしない
- current undetermined signalは`selection_not_affected`または`question`へ閉じる。解決できたsignalは`signals`を`true / false`へ更新して`technique_candidates.py`を再実行し、current undetermined集合から外す。`question`が残るTechnique Selectionをactiveにしない

## 10. change impact graph

`test-analysis`成果物へ自由文とは別に機械graphを追加します。

`Node Key | Node Type | Source Ref`

`Edge Key | From | To | Edge Type | Authority / Evidence`

許可するedge typeは次の3種だけです。

- `depends_on`
- `traces_to`
- `derived_from`

`change_impact.py`はchanged nodeからedge directionに従って下流候補を辿ります。`depends_on`は「FromがToへ依存する」と定義し、To変更時は逆向きに依存元を探索します。`traces_to` / `derived_from`は上流→下流として探索します。名称類似や同一画面だけでedgeを追加しません。

## 11. Skill間の機械接続

LLMによるmachine JSON再生成を挟まず、固定builderで接続します。ここでいう固定builderは文書上の手順ではなくPythonの決定論的処理です。runtimeを持つSkillでは各`runtime_contract.py`の共通Machine Entity builderを既存artifact / model scriptから呼び、structure / materialize scriptが所有するEntityはそのscriptが最終`content`とdependencyを返します。`spec-analysis`だけは§2の`authority_entities.py`が同じcanonicalization規則でAuthority Entityを生成します。AgentがMachine Entity wrapper、content fingerprint、期待identityを手で組み立てる経路を許可しません。

各Skillは同じ正規化済みsourceから`expected_entity_identities[]`を固定builderで生成し、Machine Entity actual rowの存在を入力にして期待identityを逆算しません。`workflow_runtime.py`へ渡す際はbuilder出力をそのまま連結し、callerがidentityを追加・削除しません。期待runtime unitについては、各Skill-local `runtime_contract.py`がcanonical normalized input、対象 / 実行範囲、current structure / identity state、active model metadata、adapter parentのcurrent runtime state、条件付き入力の有無から`dispatch_source_state`を固定生成し、そのsourceからexpected-runtime builderが期待集合を作ります。Agent / LLMが`dispatch_source_state`や`expected_runtime_units[]`を手組み・削減せず、actual runtime集合からも逆算しません。

`qa-workflow`を経由しないSkill単体利用でも、このexpected runtime builderを最終自己検証に使用します。担当Skillは保存予定の`Machine Runtime Input / Result` block identity集合を`expected_runtime_units[]`と完全一致で検査し、必須unitのmissingまたは未知のextraがある場合は成果物を契約適合済み・完成済みとして扱いません。`workflow_runtime.py`だけをruntime省略検出の唯一の経路にしません。

- Cause-Effect → child Decision Table
- Classification Tree → child combinatorial
- schema / HTML → child EP / BVA / combinatorial / test data requirement
- generator target / semantic Coverage Item → CI
- CI canonical execution / semantic item本文、test data / environment requirement → test-case-design

`materialize_coverage.py`はcurrent generator result用`models[]`とは別に、TCN配下の全current `active_model_metadata[]`を受けます。runtime generatorを持たないエラー推測やunsupported fallbackもmodel所属を検証できます。

semantic Coverage Itemのinput draftは`{draft_key, model_key, identity_action, reuse_semantic_item_key, reuse_ci_id, source_target_versions[], item_text, authority_refs[], reference_refs[], priority, priority_override_reason, expected_result_root, test_data_requirement_refs[]}`です。runtime generatorを持たないsemantic model、fork-join等の非linear target、partial / whole-model unsupportedの`llm_fallback`だけに使用します。新規itemではreuse fieldをnull、再利用では`reuse_semantic_item_key`と`reuse_ci_id`をprevious semantic mappingの同じrowへ一致させます。

semantic item lifecycleは次で固定します。

- new候補はcanonical `(model_key, draft_key)`順でCIを採番し、確定CI IDから`semantic_item_key=semantic:<ci_id>`をruntimeが発行する。LLMが新規stable keyを任意生成しない
- `previous_semantic_ci_map[]`は`{semantic_item_key, model_key, ci_id, mapping_status, semantic_content_fingerprint}`をfull snapshotで保持し、`mapping_status=active|inactive`
- previous active itemがcurrentでreuseされなければmappingをinactiveへ遷移し、そのsemantic CIをdeletedへ移す。row自体は削除しない
- inactive itemが意味上同一として復帰する場合、`identity_action=reuse`で同じsemantic item key / model / CIを指定し、そのCIが別itemへ再利用されていなければ同じkey / CIを復帰できる
- deleted CIやinactive semantic item keyを別itemへ再利用しない。modelが変わる場合は意味上別itemとしてnewにする
- 同じsemantic item keyをreuseしても`item_text / source_target_versions[] / Authority / Reference / priority / expected_result_root / test data requirement`が変わればCI content fingerprintを変え、下流TCをstaleにする
- `source_target_versions[]`を持つitemは現在targetの`target_ref / target_content_fingerprint / generation_fingerprint`と完全一致し、全source targetがsemantic item自身の`model_key`に所属しなければcurrentにしない。別modelのtargetで当該modelのclosureを代替しない

machine target由来CIはcanonical `execution`を、semantic item由来CIは`semantic_item_key / semantic_item_text / semantic_source_targets[]`をMachine Entityへ保存します。test data requirementはcurrent Machine Entityのcontent fingerprintをCI dependencyへ保存します。

各active Coverage所有modelは、少なくとも1件のcurrent CIを持つか、非空のcurrent Coverage母集団が既存のtarget Disposition / unsupported closure契約で全件閉じている必要があります。`materialize_coverage.py`はsupported / partial / runtimeなしsemantic modelについてmodel単位の`model_completion[]`を決定論的に返し、固定builderがそのrowをcurrent materialize runtime unitへ載せます。`traceability.py`と`workflow_runtime.py`はcurrent materialize generationの同じrowを使用し、TCN全体のCI有無からmodel完了を推測しません。whole-model unsupportedだけはcurrent `unsupported_item_closures[]`を最終closureとして使用します。空の入力・空のCoverage母集団をvacuous completeにしません。特にエラー推測semantic modelは1件以上のcurrent semantic CIを必須とし、semantic item 0件では完了不可です。

`test-case-design`はCI Machine Entityの`execution`を下流で再解釈不要な自己完結表現として扱います。state / flow / CRUD等のexecutionはstable key列だけでなく、具体的な実行手順を組み立てるために必要なevent / operation / input / from / to等のmachine meaningをgenerator側で含めます。下流が人間向けCoverage表やgenerator内部modelを再読解して意味を補完しません。

`test-case-design`はこれらのMachine Entityから具体手順・データを作り、人間向けCoverage Item表からmachine値を再抽出しません。

mergeは既存契約どおり同一model・同一execution fingerprintだけを許可します。

## 12. runtime自己検査の処理順

`test-requirement-design`、`test-condition-design`、`test-case-design`では、既存evalのruntime複製で終わらせません。

1. LLMがdraftを作成
2. runtime structure scriptを実行
3. gap / unknown / priority結果を受け取る
4. 意味判断が不要な局所修正は機械結果に合わせる
5. 意味判断が必要なら担当Skillまたは`question-analysis`へ戻す
6. runtime scriptを再実行
7. unresolvedな構造違反がない状態で成果物を確定

## 13. qa-workflow統合

### 13.1 再利用

既存成果物の再利用では次を固定します。

- canonical `Machine Entities`とstable ID / previous stateは、現在の対象範囲と担当Skill契約を満たす場合に再利用できる
- 本Planのdispatch対象runtime unitは、既存成果物を再利用する場合も現在のMachine Entity、保存済み意味parameter、previous ID stateから`_02_runtime-architecture-and-contracts.md` §2.1の`direct / artifact`条件に従ってcanonical inputを組み立て直し、現在のscriptを必ず再実行する。前工程Machine Entityが存在しないdirect由来成果物を、自SkillのMachine Entityがあるという理由だけでartifactへ強制昇格しない
- 保存済み正規化model / semantic draftを入力へ再利用する前に、そのruntime inputへ保存した`upstream_entities[]`および対応Machine Entityの`upstream_entity_dependencies[]`を現在のcanonical Entityと比較する。不一致があれば古い意味入力のままscriptを再実行せず、担当Skillへ`要再検証`として戻す。LLMが意味を再確認して現在のdependency fingerprintを保存した後にruntimeを実行する
- 保存済み`Machine Runtime Input / Result`はprevious state、差分確認、round-trip検証に使うが、現在のcontract / implementation / static data / support判定を省略するcacheにはしない
- 再実行した`generation_fingerprint`が以前と同じ場合はstable IDと現在も一致する意味判断を維持できる。generationが変わった場合はannotation / Disposition / merge / question回答 / unsupported closureの世代一致を再確認する
- 以前`runtime_required=false`だったwhole-model fallbackも現在runtimeでsupport判定を再実行し、現在supportedになったunitをfallbackのまま固定しない
- stale / `要再検証` / unresolvedなmodelが残っていないことを最終完了条件とする
- runtime対象unitをPython unavailable等で再実行できない場合は既存resultへfallbackせず`not_run / blocked`として保持する

### 13.2 legacy成果物

contract versionを持たない既存成果物を一律破棄しません。

- 従来契約を満たす間はlegacy成果物として参照可能
- その成果物を変更・再利用して本Plan対象の決定論的処理へ入る時点で、担当Skillが`input_mode=direct`として正規化model / 構造入力を作成して新契約へ昇格する
- legacy初回昇格では、現在のlegacy成果物に存在するTR / TCN / CI / TC IDを「現在確認できるactive ID」としてstructure / materialize script自身がprevious stateへseedする。AgentやLLMが`previous_*[]`を手組みしない。過去に削除済みだったが現成果物から消えているID履歴は復元できないため、昇格前のdeleted履歴を捏造しない。新規採番は現在観測できる同系列IDの最大番号+1から開始し、互換保証は昇格時点以降のfull snapshotへ限定する
- 初回昇格入力は`input_mode=direct`かつnormal previous stateが空の場合だけ許可する。`requirement_structure.py`は`legacy_tr_ids[]`、`condition_structure.py`は`legacy_tcn_ids[]`、`case_structure.py`は`legacy_tc_ids[]`をoptionalで受け、各scriptが`runtime_contract.py`の同一legacy ID seed helperで`status=active`のprevious stateへ変換してから通常のscope / reuse / new採番処理へ入る。normal previous stateとlegacy ID入力の併用は`invalid_input`
- TR / TCN / TCは、担当Skillが意味上同一と判断した既存rowについて既存`reuse_id`経路を使ってlegacy IDを維持する。legacy成果物にmodel keyが存在しない場合は`previous_model_keys=[]`からmodel keyを新規採番し、存在しない過去model identityを復元しない
- `materialize_coverage.py`の各TCN単位実行では、対象TCNに存在する全legacy CI IDを`legacy_ci_ids[]`として渡し、同TCNのnormal `previous_ci_ids[]`が空の初回昇格だけ全件`status=active`へseedする。これにより意味対応できないlegacy CIもそのTCNの過去最大番号へ含め、別の新規CIへ番号を再利用しない
- 対象TCNのlegacy CIを現在generator target / semantic Coverage Itemへ対応付けてIDを維持する場合だけ、`legacy_ci_ids[]`のsubsetとして初回昇格用`legacy_ci_seed[]`を渡す。schemaは`{ci_id, model_key, source_kind, target_ref, semantic_item_draft_key}`とし、`source_kind=runtime_target`ではcurrent `target_ref`だけ、`source_kind=semantic_item`ではcurrent `semantic_item_draft_key`だけを必須にする。LLMは意味上の同一性だけを判断し、固定builderがcurrent TCN / model / target / draftの存在、一意対応、CI親TCN、duplicate reuseを検証する
- `legacy_ci_seed[]`により対応できたCIはその既存CI IDを初回normal mappingへ移し、`materialize_coverage.py`が通常の`target_mapping_state[] / semantic_ci_mapping_state[] / ci_id_state[]`を出力する。対応できないlegacy CIはcurrent mappingへ推測割当てせず通常lifecycleでdeletedへ遷移し、当該CIを参照していた既存TCを`要再検証`にする。ID row自体はfull snapshotへ残す
- `legacy_tr_ids[] / legacy_tcn_ids[] / legacy_tc_ids[] / legacy_ci_ids[] / legacy_ci_seed[]`は初回昇格だけ許可し、normal state生成後は受理しない。以降は既存のprevious mapping / full snapshot契約だけを正本にする
- 新契約Machine Entity保存後も、必要な前工程Machine Entityが存在しない境界は`direct`を維持できる。必要な外部semantic dependencyがすべてcurrent Machine Entityとして揃った場合だけ`artifact`へ切り替える
- legacy成果物を「決定論的生成済み」と表現しない

### 13.3 局所状態

runtime単位状態の正本は各成果物に保存した`runtime_unit_key`、`result_status`、`runtime_required`、`deterministic_generated`、`freshness_status`、fingerprint、構造化issueです。

既存`qa-workflow`契約どおり、Skill状態表はワークフロー状態を明示する必要がある場合だけ使用します。表を表示する場合も集約表示であり唯一の永続正本ではありません。他Skill実行、freshness判定、workflow完了判定は状態表の存在に依存せず、成果物metadataから状態を再構築します。

ワークフロー状態を表示する場合は、既存Skill状態表に加えて次の`runtime状態`表を追加します。通常出力で状態表示が不要な場合は両表を省略でき、runtime metadata自体は各成果物へ保存します。

`Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue`

- `Runtime Unit Key`は同一Skill内一意
- model scriptは`Runtime Unit Key = model:<model_key>`とし、`Model Key`を必須
- artifact全体scriptは`Runtime Unit Key = artifact:<generator>:<scope_key>`とし、`Model Key`は空欄
- `Support Status`は`supported / partial / unsupported / unknown`
- runtime集約inputの各runtime unitは共通`model_completion[] / target_mappings[] / target_dispositions[]` fieldを持ち、`artifact:materialize_coverage:<tcn_id>`だけ非空を許可する。他unitでは3配列を空固定とする。`target_mappings[]`はmaterialize outputの`target_id_map[]`を同名row schema `{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`で固定転記し、`target_dispositions[]`は`disposed_target_refs[]`へ`reason / authority_refs[]`を含むcurrent input dispositionをjoinして§7.4の完全schemaで転記する。LLMが生成しない。`traceability.py`と`workflow_runtime.py`は全materialize unitのtarget mapping / dispositionを集約し、`重複`参照のmissing / stale / cycle / terminal coverageを同じ規則で検査する
- `Result Status`は`ready / unresolved / blocked`
- `Freshness`は`current / stale`
- `Runtime Status`は`ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Runtime Required`と`Deterministic Generated`は`Yes / No`
- `Fallback Reason`は空欄 / `outside_supported_subset` / `python_unavailable`
- Skill状態表を表示する場合、`WF-D012`は既存Skill状態表だけへ適用し、runtime状態表へ流用しない。canonical deterministic evalで状態表を要求するfixtureは別途`WF-D009`を維持する
- 1 runtime unitだけ`blocked / unresolved / stale`でも独立した他unitは継続可能
- 本Plan対象runtime範囲の機械的完了には、すべてのruntime unitで`Result Status=ready / Freshness=current`を必須とする。この条件や`workflow_runtime.py`の`can_complete`を、E2E実装・実行・分析・報告等を含む既存`qa-workflow`全体の完了条件へ置き換えない。workflow全体`完了`は既存`qa-workflow`完了条件を満たしたうえで、`workflow_runtime.py`をdispatchした場合だけさらに`can_complete=true`を必要条件として加える
- `Runtime Required=Yes`のunitでは、さらに`Deterministic Generated=Yes`を必須とする
- `Runtime Required=No`のfallback unitは、既存Skill契約を満たして`Result Status=ready`になった場合だけworkflow完了を妨げない
- `Support Status=partial`のunitは`unsupported_items[]`がすべて§13.3のclosure契約へ妥当に閉じていることを完了条件にする。closure行が存在するだけでは閉鎖済みとみなさない
- model issueを`question-analysis`へroutingする場合は`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問一覧・ブロック中範囲・回答後の再開情報へ保持する
- artifact全体scriptのissueも`skill / runtime_unit_key / generation_fingerprint`をBlocker / Issueへ保持し、model keyを捏造しない
- unsupported item closureの`handling`は`llm_fallback / 対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複 / ブロック中`だけを許可する。`llm_fallback`と`重複`はcurrentな`covered_by_entity`を必須にし、`ブロック中`はclosure行があってもworkflow完了不可とする。その他のDispositionは既存`test-condition-design`のreason / Authority条件をそのまま適用する
- 通常Coverage modelの`llm_fallback`は対象unsupported item / whole-modelと同じ`model_key`に属するcurrent CI Machine Entityだけを参照する。internal adapterはCoverageを所有しないため例外とし、`_02_runtime-architecture-and-contracts.md` §2.2のfallback手順で追加した同一TCNの直接定義Coverage modelに属するcurrent CIだけを`covered_by_entity`へ指定できる。partial adapterではunsupported itemの`affected_technique_slug`と直接定義modelの`technique_slug`を一致必須とする。whole-model adapterではactiveのまま残す各selected child techniqueについて少なくとも1件のcurrent直接定義Coverage model / CIまたは既存Disposition closureへ到達することを必須とする。adapterと無関係なTCN / model / techniqueのCI、TCNやmodel metadataだけをfallback Coverage evidenceにせず、参照先missing / staleなら未閉鎖として扱う
- `coverage-analysis`はstale / gapをTCN / CIだけでなく関連`model_key`まで追跡する

Machine Entityのfreshnessは`runtime_contract.py`の共通関数で計算します。各Machine Entityの`runtime_dependencies[]`と現在runtime unitのgenerationを比較し、次のschemaへ正規化します。

```json
{
  "skill":"test-case-design",
  "entity_type":"tc",
  "entity_ref":"TC-001",
  "model_key":null,
  "freshness_status":"current",
  "stale_reasons":[]
}
```

- upstream / runtime dependencyを持たないAuthority等のsource Entityは、その担当Skill成果物が現在有効なら`current`
- `upstream_entity_dependencies[]`のcontent fingerprint不一致、参照先missing、または参照先Entity自体がstaleならそのEntityを`stale`
- `runtime_dependencies[]`の参照先がmissing / stale、または保存generationと現在generationが不一致ならそのEntityを`stale`
- `workflow_runtime.py`と`traceability.py`は同じ共通関数・同じ入力schemaを使用し、runtime unit freshnessからEntity freshnessへの別々の変換規則を持たない
- `traceability.py`は`workflow_runtime.py`のresultをruntime dependencyとして参照せず、同じcurrent runtime / Machine Entity stateから共通関数を呼ぶ。これによりworkflow_runtimeとのcycleを作らない

### 13.4 上流変更

上流Entityの`content_fingerprint`または直接依存する上流runtime unitの`generation_fingerprint`が変わった場合:

1. 最も早い変更成果物を特定
2. change impact / traceabilityで影響modelを特定
3. 影響modelとその派生成果物だけを`要再検証`
4. 正規化modelを更新
5. generator再実行
6. target内容が変わった場合は、同じ`target_ref`でも`target_content_fingerprint`差分によりannotation / Disposition / merge判断と関連CI / TCを`要再検証`へ戻す。target内容が同じでも`generation_fingerprint`が変わった場合はannotation / Disposition / merge判断の世代一致を再確認する
7. question回答、unsupported closure等の意味判断は対象`generation_fingerprint`が現在世代と一致するものだけ再利用する
8. 下流structure / Coverageを再検査
9. staleが消えた範囲だけ再利用可能に戻す

## 14. 移植性と依存関係

各Skillは単体コピー可能な既存契約を維持します。

`spec-analysis`を含む7 Skillへ`scripts/runtime_contract.py`を同梱し、canonical JSON / Machine Entity helperは同一実装にします。runtime dispatchを持つのは従来どおり6 Skillだけで、`spec-analysis`のhelperはruntime unitとして数えません。repo rootの共通helperへ依存させません。`runtime_contract_version`をfile内定数として持ち、意味契約を変更した場合にversionを更新します。repository testでは改行をLFへ正規化した内容のSHA-256一致を検証し、Skillごとの実装差を許可しません。実装内容の変更は同じLF正規化規則で`runtime_implementation_fingerprint`へ反映します。技法固有ロジックはこの共通helperへ入れません。

本Planのruntime dependencyはPython 3.11標準ライブラリだけに固定します。外部PyPI package、外部binary、network serviceをruntime依存へ追加しません。

Planで定義した正確性とhard limitをPython 3.11標準ライブラリ実装で満たせない場合は、その実装をPlan未達として停止し、暗黙にCoverage基準を下げたり依存関係を変更したりしません。interpreterのcommand名とtimeout機構はAgent / host実装に依存させ、CIでは`python`と30秒timeoutを安全策として使用します。将来用adapterも作りません。
