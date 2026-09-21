# テスト分析・テスト技法の決定論的自動化Plan

## 1. 実行時アーキテクチャ

### 1.1 処理境界

処理順は次で固定します。

```text
現在有効な仕様根拠・既存QA成果物
  ↓
LLM: 意味判断と正規化
  ↓
canonicalな正規化済みモデル
  ↓
Skill runtime script: 列挙・計算・構造検査
  ↓
機械証拠 / 構造化された未解決事項
  ↓
LLM: 人間向け説明、意味上の統合、必要な質問
  ↓
runtime構造再検査
  ↓
QA成果物
  ↓
独立validator / semantic eval
  ↓
qa-workflow: 再利用・変更伝播・完了判定
```

scriptは自然言語の仕様本文を直接解釈しません。machine-readableなJSON Schema / OpenAPI / HTML属性等、このPlanで対応subsetを明示する入力はscriptが直接正規化してよく、LLMへ機械変換を戻しません。

正規化済みモデルを正本とします。Coverage表、生成組合せ、Coverage Itemの機械部分、traceability集計等は派生成果物です。正本が変わった場合は派生成果物を再生成・再検証します。

### 1.2 評価runtimeとの分離

Skill runtimeは次をimportまたは直接呼び出しません。

- `scripts/skills/evals/deterministic/`
- `scripts/skills/evals/semantic/`
- `skills/*/evals/deterministic/validator.py`

generatorとvalidatorは独立実装とし、同じ不具合で生成と評価が同時に誤る構造を避けます。

## 2. 追加する実行時script

### `spec-analysis`

`spec-analysis`にはruntime unitを追加しません。ただしAuthority Machine EntityをLLMの手計算で組み立てないため、`scripts/runtime_contract.py`のcanonical JSON / Machine Entity helperと、`scripts/authority_entities.py`を追加します。`authority_entities.py`はAuthority表の正規化済みfieldを受け取り、canonical `content`、`content_fingerprint`、Machine Entity wrapper、期待Authority identityを決定論的に生成します。これはgenerator dispatch、`Machine Runtime Input / Result`、`expected_runtime_units[]`の対象には含めません。

### `test-analysis`

```text
skills/test-analysis/scripts/
├── runtime_contract.py
├── analysis_entities.py
├── risk_matrix.py
├── technique_candidates.py
├── change_impact.py
└── environment_requirements.py
```

- `analysis_entities.py`: test-analysis context / Product Risk / Technique Selection / change graph / environment requirementのLLM意味fieldとcurrent runtime resultを固定schemaでjoinし、Machine Entity、dependency、expected Entity identityを決定論的に生成するartifact runtime。意味判断は行わず、保存前に必ず実行する
- `risk_matrix.py`: repository-defaultまたは明示済みproject-specific schemeからrisk levelを計算する
- `technique_candidates.py`: 正規化済みproblem signalから技法候補を返す
- `change_impact.py`: 明示済みnode / edgeから影響候補を抽出する
- `environment_requirements.py`: 構造化済み環境要求を重複統合し矛盾を検出する

### `test-requirement-design`

```text
skills/test-requirement-design/scripts/
├── runtime_contract.py
└── requirement_structure.py
```

TR本文は生成せず、Authority / Risk → TRの閉鎖、未知参照、Disposition重複、優先度を計算します。

### `test-condition-design`

```text
skills/test-condition-design/scripts/
├── runtime_contract.py
├── condition_structure.py
├── equivalence_partitions.py
├── bva.py
├── domain_testing.py
├── decision_table.py
├── combinatorial.py
├── classification_tree.py
├── state_transition.py
├── flow_paths.py
├── crud_matrix.py
├── cause_effect.py
├── grammar_cases.py
├── schema_cases.py
├── ui_pattern_candidates.py
├── test_data_requirements.py
├── random_testing.py
├── metamorphic.py
└── materialize_coverage.py
```

### `test-case-design`

```text
skills/test-case-design/scripts/
├── runtime_contract.py
└── case_structure.py
```

具体的な前提、操作、実データ、expected resultは生成せず、TCN / CI → TCの閉鎖、未知参照、優先度、Authority対応を検査します。

### `coverage-analysis`

```text
skills/coverage-analysis/scripts/
├── runtime_contract.py
└── traceability.py
```

対象はテスト設計のAuthority / Risk → TR → TCN → CI → TCです。既存SkillがCIなしTCN → TCを許可する場合も、当該TCNにactiveなCoverage所有modelがない契約に限ります。Coverage所有modelがあるTCNは、各modelのcurrent CIまたは許可されたcurrent closureを先に満たさなければならず、直接TCN → TCでCoverage closureを迂回できません。E2E実装・実行結果は既存責務のままです。

### `qa-workflow`

```text
skills/qa-workflow/scripts/
├── runtime_contract.py
└── workflow_runtime.py
```

`workflow_runtime.py`は工程固有の意味判断を行いません。各成果物へ保存されたruntime metadata、上流Entity、runtime unit依存、fingerprintを入力として、runtime状態集約、freshness、stale伝播、機械的な完了可否を計算します。開始Skill、意味上の変更影響、既存成果物を意味的に再利用できるかの判断は既存`qa-workflow`責務に残します。

### 2.1 Skill実行時のdispatch契約

runtime対象Skillは、Skill instructionへscript選択表を持ち、次の順序で実行します。

1. LLMがAuthority、Risk、TR等を意味的に解釈し、Planで固定したcanonical inputへ正規化する
2. `runtime_contract.py`がcanonicalizationを適用した正規化済み入力を返し、fingerprint計算とgenerator本体の両方が同じ正規化済み値を使う
3. script選択表からruntime scriptを選ぶ。script pathを自由文や`technique_slug`から推測しない
4. 保存済み`Machine Runtime Input / Result`を再利用する場合はstrict decode、runtime identity、model key、fingerprint一致を検証する
5. stdinへ共通metadataとscript固有inputを渡してscriptを起動する
6. stdout envelopeをstrict decodeし、return code、runtime status、issuesを合わせてroutingする
7. 意味判断が必要なissueは既存Skillまたは`question-analysis`へ戻し、機械結果をLLMが再計算しない
8. 意味入力を更新した場合はruntimeを再実行し、保存machine evidenceを置換する

`runtime_required`はscriptの入力検証結果として決定し、Agentが自然言語だけから`false`を確定してscriptを省略しません。

既存Skillの途中工程開始・単体利用を維持するため、runtime invocationは`metadata.input_mode=artifact|direct`を必須にします。

- `artifact`: 前工程または再利用成果物のcanonical Machine Entityを使う経路です。script固有inputが参照する外部semantic dependencyのうち、PlanでMachine Entity化すると定義したものがすべてcurrent Machine Entityとして実在する場合だけ使用します。`upstream_entities[]`へ完全に解決し、missing / extra / duplicateを拒否します
- `direct`: 既存Skillの入力契約が許すユーザー入力または同等の成果物から、そのSkillを途中工程として直接開始する経路です。存在しない前工程Machine Entityを捏造せず、欠落とも扱いません。実際に消費する意味fieldはscript固有inputへ正規化し、`input_fingerprint`へ含めます。現在invocationが生成するEntityはstructure / builder runtime dependencyを持つため、direct input変更もgeneration差分として検出します
- `direct`でもcurrent Machine Entityが明示的に渡された参照は通常どおり検証してsemantic dependencyへ保存します。Machine Entityを渡した参照だけを無視してdirect inputへ黙って置き換えません
- direct開始で外部semantic dependencyの一部がMachine Entity化されていない成果物は、自SkillのMachine Entityを保存済みという理由だけで次回`artifact`へ切り替えません。再利用時も不足する前工程Entityを合成せず`direct`を維持します
- `direct → artifact`へ切り替えるのは、そのscriptが必要とする外部semantic dependencyがすべてcurrent Machine Entityとして実在し、固定builderで完全解決できる時点だけです。切替時は`input_mode`変更を`input_fingerprint`へ反映してruntimeを再実行し、旧generationをcurrent扱いしません
- `qa-workflow`が必要な外部Machine Entityをすべて持つ成果物を再利用する場合は`artifact`、既存Skill契約に従って途中工程から直接開始する場合とlegacy成果物を新契約へ初回昇格する場合は`direct`を使用します。legacy昇格後も前工程Machine Entityが存在しない境界は上記規則に従って`direct`を維持できます

これによりSkill単体コピー時に前工程Skillの成果物生成を強制せず、workflow内で実在するMachine Entity dependencyも失いません。

| Skill | 対象 / 実行範囲 | 条件 | script | 実行 |
| --- | --- | --- | --- | --- |
| `test-analysis` | `テスト分析` | Product Riskがある | `risk_matrix.py` | 条件付き |
| `test-analysis` | `テスト分析` | 技法選択を行う | `technique_candidates.py` | 必須 |
| `test-analysis` | `テスト分析` | 変更影響graphがある | `change_impact.py` | 条件付き |
| `test-analysis` | `テスト分析` | 環境要求がある | `environment_requirements.py` | 条件付き |
| `test-analysis` | `テスト分析` | test-analysis成果物を保存する | `analysis_entities.py` | 必須 |
| `test-requirement-design` | 単一用途 | 成果物確定前 | `requirement_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | TCN / model draft作成後 | `condition_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | active modelの`model_type`が下表のgeneratorを持つ。adapter派生childは親adapterがcurrent `result_status=ready`で対応`derived_child_inputs[]`がちょうど1件ある | model type対応generator | modelごとに必須 |
| `test-condition-design` | 単一用途 | test data要求が1件以上ある | `test_data_requirements.py` | 条件付き |
| `test-condition-design` | 単一用途 | TCN配下にactiveなCoverage所有modelが1件以上ある | `materialize_coverage.py` | TCNごとに必須 |
| `test-case-design` | 単一用途 | 成果物確定前 | `case_structure.py` | 必須 |
| `coverage-analysis` | `テスト設計` | traceabilityを検査する | `traceability.py` | 必須 |
| `qa-workflow` | 単一用途 | `workflow_runtime.py`自身を除く本Plan対象runtime unitの期待集合が1件以上ある | `workflow_runtime.py` | 条件付き |

`materialize_coverage.py`はcurrent machine targetやsemantic itemが0件でも、TCN配下にactiveなCoverage所有modelが1件以上あれば実行します。runtimeなしsemantic modelやtarget 0件のmodelも`model_completion[]`を明示し、空入力をvacuous completeにしません。whole-model `unsupported`は既存のunsupported closure契約で閉じ、成功`model_completion[]`を捏造しません。

`workflow_runtime.py`は、`workflow_runtime.py`自身を除く本Plan対象runtime unitの期待集合が1件以上ある場合だけdispatchします。`test-analysis: E2E対象選定`、`coverage-analysis: TC → E2E実装 / E2E実装 → 実行結果`等、本Plan対象runtime unitが0件のE2E-only経路ではdispatchせず、既存`qa-workflow`の完了契約を維持します。Python unavailableだけを理由に本Plan対象runtimeがない経路を`blocked`へ変更しません。

model typeからgeneratorへの対応は次だけを許可します。model runtimeの`expected_runtime_units[]`はこの表から、artifact runtimeの`expected_runtime_units[]`は直前のSkill dispatch表から導出し、両集合を連結します。adapter派生child（`derived_from_model_key != null`）は、親adapter runtimeがcurrent `result_status=ready`で、そのchildに対応する`derived_child_inputs[]` rowがちょうど1件存在する場合だけdispatch対象かつ期待runtime集合へ追加します。親adapterが`unresolved / blocked / stale`、未実行、または対応row欠落の間はchild runtime unitを期待集合へ入れず、親adapter側のissue / freshnessをblockerとして扱います。

| model_type | generator |
| --- | --- |
| `ep` | `equivalence_partitions.py` |
| `bva` | `bva.py` |
| `domain` | `domain_testing.py` |
| `decision` | `decision_table.py` |
| `comb` | `combinatorial.py` |
| `classification` | `classification_tree.py` |
| `state` | `state_transition.py` |
| `flow` | `flow_paths.py` |
| `crud` | `crud_matrix.py` |
| `cause-effect` | `cause_effect.py` |
| `syntax` | `grammar_cases.py` |
| `schema` | `schema_cases.py` |
| `ui` | `ui_pattern_candidates.py` |
| `random` | `random_testing.py` |
| `metamorphic` | `metamorphic.py` |
| `error-guessing` | runtime generatorなし |

`materialize_coverage.py`はruntime generatorを持たないエラー推測やunsupported fallbackのsemantic Coverage Itemだけでもdispatch対象にします。

freshnessは既存契約どおり、現在のcanonical machine Entityと正規化済み入力からruntimeを再実行して判定します。保存済みruntime resultを現在世代のcacheとして使いません。

### 2.2 派生modelの生成

Cause-Effect → Decision Table、Classification Tree → combinatorial、schema → EP / BVA等で別generatorを起動する場合、親runtime結果を匿名の別model inputとして扱いません。また、active Technique Selectionの閉鎖確認より後にchild modelを作る循環を作りません。

1. adapterを採用する時点で、adapter model draftとCoverage所有child model draftを同じ`condition_structure.py`入力へ含める。childの`model_type / technique_slug`はcurrent Technique Selectionまたは`selection_source=condition_design|user`で既に採用した正規技法から決め、adapter runtime出力を見て新しい技法を自動選択しない
2. child model draftは`derived_from_model_draft_key`で同じ入力内のadapter draftを1件だけ参照する。adapterでない親、unknown draft、自己参照、複数親は`invalid_input`
3. `condition_structure.py`がadapter / child双方の`model_key`と親TCNを先に確定し、active Technique Selectionの`selected_techniques[]`がCoverage所有child modelへ到達することをこの時点で検証する
4. adapter modelは`technique_slug=null / selection_source=null / selection_key=null`、child modelはcanonical `technique_slug`と`selection_source=analysis / condition_design / user`を持つ。`analysis`由来childだけ元の`selection_key`を保持する
5. 確定したadapter `model_key`とchild model identityをadapter runtimeへ渡す。adapterはmachine-readable sourceを解析してchild用skeletonと、完成inputに必要だがまだ未確定な意味parameterを`semantic_parameter_requests[]`として返せる
6. 意味parameter不足時はadapter自身が`result_status=unresolved`と構造化issueを返す。LLMはissueで要求された意味parameterだけを補い、machine skeletonやkeyを再生成しない
7. 同じadapter scriptを意味parameter込みで再実行し、`derived_child_inputs[]: {child_model_key, model_type, input}`を返す。各`input`は対応child generatorのscript固有inputと直接互換にし、別の匿名builderでjoinしない
8. child generatorはadapterの最終`generation_fingerprint`を`upstream_runtime_units[]`へ固定転記し、対応する`derived_child_inputs[]` rowをそのままscript固有inputへ使う。unknown / duplicate child、model type不一致、ready adapterなのにselected childのrowが欠落する場合は`invalid_input`または`unresolved`とし、空modelを実行しない
9. adapter出力を正規技法として採用した場合は対応childを必須にし、採用しない候補はTechnique Selectionの`selected_techniques[]`へ残さない。adapter親や別のclosure行でchild欠落を隠さない

固定対応:

- `classification` adapter → child `comb`
- `cause-effect` adapter → child `decision`
- `schema` adapter → 採用済み正規技法slug `ep / bva / comb`に対応してchild `ep / bva / comb`。schema runtimeはchild typeを新規決定せず、そのchild用derived inputだけを生成する
- `ui` adapter → 正規技法modelを自動生成せず、既存`test-condition-design`の意味判断へ候補を渡す

同じcanonical adapter inputと同じ意味parameterから同じ`derived_child_inputs[]`をadapter runtime自身が生成します。child inputの生成をAgent側helperやLLMへ分散しません。

## 3. 共通JSON契約

### 3.0 CLI契約

すべてのruntime scriptは同じCLI契約を使用します。

- Skill側の実行契約は「Python 3.11 interpreterで同梱scriptを実行できること」とし、interpreterのcommand名は固定しない。`python` / `python3` / `py -3.11`等の選択はAgent / host実装に委ねる。CIの標準実行例は`python <script-path>`とする
- stdinからUTF-8のstrict JSON objectを1件だけ読む
- positional argument、入力file path、環境変数から業務入力を受け取らない
- cwdへ依存せず、Skill root相対のassetは`__file__`から解決する
- stdoutはruntime envelopeのJSON object 1件だけ。logや説明文を混在させない
- stderrは人間向け診断だけに使う
- stdinが空、JSONが複数、末尾に非空白データが残る場合は`invalid_input`
- strict decode前に失敗し、`runtime_unit_key / input_fingerprint / model_fingerprint / generation_fingerprint`を確定できない場合も、可能なら§3.3のpre-parse error envelopeをstdoutへ返す。callerが推測したfingerprintを補わない
- Agent / host側のscript runnerはstdout / stderr / return code相当を取得し、return codeだけでroutingしない。CIではsubprocessを使用する
- timeoutはAgent Skillsの共通runtime要件にせず、Agent / host / CI側の安全策とする。CIでは30秒を使用する。通常の探索停止は§5.3の決定論的hard limitで行い、timeoutをCoverageや探索アルゴリズムの正常終了条件にしない。hostがtimeoutを検出した場合はmachine resultを採用せず、成果物metadataでは`runtime_status=internal_error / support_status=unknown / result_status=blocked / runtime_required=true / deterministic_generated=false`として扱い、構造化issueの`issue_type=runtime_execution_timeout`で原因を区別する。`runtime_execution_timeout`を新しい`runtime_status`にはしない

### 3.1 strict JSON

すべてのruntime scriptはstrict JSONを使用します。

- duplicate object keyを拒否する
- `NaN`、`Infinity`、`-Infinity`を拒否する
- top-level typeをscriptごとに固定する
- UTF-8で解釈する
- model内のdecimalはJSON numberへ丸めず、`{"type":"decimal","value":"0.1"}`のような10進文字列で扱う
- JSON numberはまず元token文字列として取得し、§5.1の長さ・形式検証後にcanonical integerまたは`coefficient + scale`へexact正規化する。binary `float`や未検証の巨大`int / Decimal`へ直接変換しない
- canonical JSONへ再serializeするexact numeric内部表現は、共通canonical serializerが検証済みnumber tokenとして指数表記なしの正規化済みJSON numberへ出力する。専用number型を通常の`json.dumps()`へ渡してstring化する実装は禁止する
- date / datetimeは契約で許可したISO 8601形式以外を拒否する

Python実装では、duplicate key検出用`object_pairs_hook`、`parse_int / parse_float`でJSON numberだけを表す専用の内部token型を返すhook、非有限数拒否、`allow_nan=False`相当の出力を共通方針とします。number tokenを通常のPython `str`として返してJSON stringと同一視しません。strict decode後、すべてのstring valueを走査してunpaired surrogate code pointを拒否し、number tokenはJSON number grammar・raw token長を検証してからcanonical integerまたは`coefficient + scale`へ変換します。

入力byte上限はUTF-8 decode前に検査します。UTF-8 decode後、`json.loads()`より前にstring / escapeを認識する軽量な構造scanで`{[` / `]}`のnesting depthを数え、§5.3の上限64を超えた時点で`limit_exceeded`にします。これにより深いJSONがPython parserの再帰上限や例外形へ先に到達することを避けます。strict parse後はobject keyを含むすべてのstringのsurrogate妥当性を検証し、不正は`invalid_input`へ正規化します。少なくとも`1 != "1"`、`1.0 != "1.0"`、`1e3 != "1e3"`を回帰fixtureで固定します。

### 3.2 共通入力metadata

runtime入力は`metadata`とscript固有`input`を分けます。

```json
{
  "metadata": {
    "envelope_version": "1",
    "skill": "test-condition-design",
    "runtime_contract_version": "runtime-v1",
    "generator_contract_version": "combinatorial-v1",
    "runtime_unit_key": "model:comb-001",
    "model_key": "comb-001",
    "model_type": "comb",
    "technique_slug": "comb",
    "selection_source": "analysis",
    "selection_key": "SEL-001",
    "scope_key": null,
    "input_mode": "artifact",
    "upstream_entities": [
      {
        "skill": "test-requirement-design",
        "entity_type": "tr",
        "entity_ref": "TR-001",
        "content": {}
      }
    ],
    "upstream_runtime_units": [
      {
        "skill": "test-requirement-design",
        "runtime_unit_key": "artifact:requirement_structure:all",
        "generation_fingerprint": "sha256:..."
      }
    ],
    "static_data_versions": {},
    "authority_refs": ["SPEC-001"],
    "reference_refs": []
  },
  "input": {}
}
```

共通metadataは少なくとも次を持ちます。

- `envelope_version`: runtime envelope形式のversion
- `skill`: runtime scriptが所属する既存Skill名。script pathから決まる値をruntime側の正本とし、入力値が不一致なら`invalid_input`
- `runtime_contract_version`: strict JSON、canonicalization、共通status、fingerprint等の共通処理version
- `generator_contract_version`: script固有の入出力・Coverage契約version。生成結果、tie-break、Coverage、target keyへ影響する変更では必ず更新する
- `runtime_unit_key`: すべてのruntime invocationで必須。model scriptは`model:<model_key>`、artifact scriptは`artifact:<generator>:<scope_key>`
- `model_key`: model scriptだけ必須。形式は`<model_type>-\d{3,}`。artifact scriptでは`null`
- `model_type`: model scriptだけ必須で§4.3の固定値。artifact scriptでは`null`
- `technique_slug`: Coverage所有modelでは§4.3のcanonical technique slug、内部adapterとartifact scriptでは`null`
- `selection_source`: Coverage所有modelでは`analysis / condition_design / user`のいずれか。内部adapterとartifact scriptでは`null`
- `selection_key`: `selection_source=analysis`だけ必須。その他は`null`
- `scope_key`: artifact scriptだけ必須。model scriptでは`null`
- `input_mode`: `artifact / direct`。§2.1の途中工程開始・単体利用契約に従う
- `upstream_entities`: `input_mode=artifact`ではscript固有input内のAuthority / Risk / TR / TCN等の参照のうち、そのscript契約で**実行前から存在する外部semantic dependency**と定義したMachine Entityから固定builderが完全導出する。callerが参照Entityを任意に省略・追加しない。`input_mode=direct`では、存在するcurrent Machine Entityとして明示された参照だけを同じ規則で検証し、存在しない前工程Entityを期待集合へ追加しない。同一runtime invocationで新規生成するEntity同士の依存はどちらのmodeでも事前投入せず、script内の固定builderが生成済みcanonical contentからfingerprintを計算して`upstream_entity_dependencies[]`へ接続する。runtimeは受け取った外部Entityのcanonical `content`から`content_fingerprint`を再計算する
- `upstream_runtime_units`: 他runtime結果を直接利用した場合に`skill + runtime_unit_key + generation_fingerprint`を一意参照として保持する。runtime派生child modelの派生元もここで表し、Selection Sourceへ混ぜない
- `static_data_versions`: generator結果に影響する静的参照データversion
- `authority_refs / reference_refs`: 現在有効な製品根拠と補助情報

artifact scriptは`risk_matrix.py`、`technique_candidates.py`、`change_impact.py`、`environment_requirements.py`、`analysis_entities.py`、`test_data_requirements.py`、`requirement_structure.py`、`condition_structure.py`、`materialize_coverage.py`、`case_structure.py`、`traceability.py`、`workflow_runtime.py`で固定します。`scope_key`はscriptごとに次へ固定します。

- `technique_candidates.py`: 入力`selection_key`
- `materialize_coverage.py`: 入力`tcn_id`
- `analysis_entities.py`: literal `all`
- その他のartifact script: literal `all`

同一Skill内で同じ`artifact:<generator>:<scope_key>`を同時に複数定義しません。

`runtime_contract_version`、`generator_contract_version`、runtime実装hash、generator実装hash、fileから導出できる`static_data_versions`はruntime側を正本にします。呼び出し側metadataへ同じ値を持たせる場合はruntime実値と一致しなければ`invalid_input`です。

`static_data_versions`はkeyを`^[a-z][a-z0-9_]*$`、valueを`sha256:<64 lowercase hex>`または明示的なcontract version文字列`^[A-Za-z0-9][A-Za-z0-9._-]*$`とします。

script固有入力は必ず`input`配下に置き、metadataと同じkeyを再定義しません。target / result keyへ文字列として直接埋め込むstable component keyは`^[A-Za-z][A-Za-z0-9._-]{0,64}$`（最大65文字）で固定し、delimiterの`:`を禁止します。任意文字列を含むidentityはcanonical JSONをSHA-256化し、digestをstable component keyへ変換する場合は`h` + 64桁lowercase hexのfull digest（計65文字）で固定します。full digest自体を保存するfieldでは`sha256:<64 lowercase hex>`を使います。

### 3.3 runtime出力envelope

scriptが実行できた場合、stdoutは次のJSON object 1件だけです。

```json
{
  "envelope_version": "1",
  "skill": "test-condition-design",
  "runtime_contract_version": "runtime-v1",
  "generator_contract_version": "combinatorial-v1",
  "generator": "combinatorial",
  "runtime_unit_key": "model:comb-001",
  "model_key": "comb-001",
  "input_fingerprint": "sha256:...",
  "model_fingerprint": "sha256:...",
  "generation_fingerprint": "sha256:...",
  "runtime_implementation_fingerprint": "sha256:...",
  "generator_implementation_fingerprint": "sha256:...",
  "upstream_entity_fingerprints": [
    {
      "skill":"test-requirement-design",
      "entity_type":"tr",
      "entity_ref":"TR-001",
      "content_fingerprint":"sha256:..."
    }
  ],
  "upstream_runtime_units": [
    {
      "skill":"test-requirement-design",
      "runtime_unit_key":"artifact:requirement_structure:all",
      "generation_fingerprint":"sha256:..."
    }
  ],
  "support_status": "supported",
  "static_data_versions": {},
  "runtime_status": "ok",
  "result_status": "ready",
  "runtime_required": true,
  "deterministic_generated": true,
  "fallback_reason": null,
  "payload": {},
  "issues": []
}
```

output envelopeの`skill`はinput metadataおよびscript所属Skillと一致必須です。`upstream_entity_fingerprints[]`はinput metadataの`upstream_entities[]`からruntimeが計算し、`upstream_runtime_units[]`は入力参照をcanonical順で正規化して保存します。callerがfingerprint結果だけを出力へ注入しません。

現在実行結果を下流runtimeへ渡すときは、各Skillの`runtime_contract.py`に置く固定projectionだけを使用します。LLM / Agentがenvelopeの`payload`をflattenしたりmetadataを補完したりしません。

- model generator → `materialize_coverage.py`では、current envelopeとcurrent model metadataから`current_model_result_row`を作る。`model_key / model_type / technique_slug / skill / runtime_unit_key / input_fingerprint / model_fingerprint / generation_fingerprint / generator_contract_version / support_status / runtime_status / result_status / deterministic_generated`はenvelopeまたはcurrent model metadataから固定転記し、`targets[] / unsupported_items[] / coverage_summary / completion_summary`等はenvelopeの`payload`からmodel type別schemaどおり投影する
- `freshness_status=current`はsemantic dependency preflightに成功したcurrent inputをcurrent scriptで再実行し、envelope検証まで成功したrowに固定projectionが付与する。保存済みresultやcaller申告値から付与しない
- `traceability.py / workflow_runtime.py`へ渡す`runtime_unit_row`はcurrent envelopeから`skill / runtime_unit_key / model_key / support_status / result_status / runtime_status / runtime_required / deterministic_generated / generation_fingerprint / upstream_entity_fingerprints[] / upstream_runtime_units[] / unsupported_items[]`を固定転記する。`model_completion[] / target_mappings[] / target_dispositions[]`は`materialize_coverage.py` unitだけcurrent materialize resultから追加し、他unitでは空配列固定とする
- これらのprojectionは保存用`Machine Runtime Result`と同じsource envelopeから作り、field名の別解釈や匿名の中間schemaを作らない

strict JSON objectと共通metadataを確定する前に失敗した場合はpre-parse error envelopeを使用します。`skill / generator / runtime_contract_version / generator_contract_version / runtime_implementation_fingerprint / generator_implementation_fingerprint / runtime_status / support_status / result_status / runtime_required / deterministic_generated / payload / issues`は返し、未確定の`runtime_unit_key / model_key / input_fingerprint / model_fingerprint / generation_fingerprint`は`null`、`upstream_entity_fingerprints / upstream_runtime_units`は空配列にします。byte上限やdepth上限をstrict decode前に検出した場合も同じ形で返し、入力内容からidentityを推測しません。

`support_status`は`supported / partial / unsupported / unknown`です。`partial`は同一input内に、独立して機械処理できる範囲と対応subset外の範囲が共存する場合だけ使用します。対応subset外部分は`payload.unsupported_items[]`へstable key、理由、Authorityを保持し、黙って削除しません。`unknown`はsupport判定を完了できなかった場合だけ使用し、`invalid_input / internal_error / not_run`とstrict decode前の`limit_exceeded`以外では返しません。

`runtime_status`:

- `ok`: script責務を完了。`support_status=partial`でも機械処理できる範囲を正しく生成できた場合は`ok`
- `invalid_input`: 入力契約違反
- `unsupported`: 入力は妥当だがmodel全体が本Planの対応subset外
- `limit_exceeded`: 契約上限を超過
- `internal_error`: 想定外障害
- `not_run`: script未実行。Python unavailable時だけ成果物metadataで使用し、script自身は返さない

`result_status`:

- `ready`: runtime unitとして下流へ利用可能。`support_status=partial / unsupported`ではQA成果物全体の完了を意味せず、unsupported itemまたはfallbackが既存Skill契約へ閉じていることを別途要求する
- `unresolved`: 追加情報または意味判断後の再実行が必要
- `blocked`: 入力違反、上限超過、runtime障害等で継続不可

status対応は次で固定します。

| runtime_status | support_status | result_status | runtime_required | deterministic_generated | 扱い |
| --- | --- | --- | --- | --- | --- |
| `ok` | `supported` | `ready` | `true` | `true` | runtime結果を利用可能 |
| `ok` | `supported` | `unresolved` | `true` | `true` | 質問・意味判断後に再実行 |
| `ok` | `partial` | `ready`または`unresolved` | `true` | `true` | supported部分を利用し、unsupported itemは後述のclosure契約へ閉じる |
| `invalid_input` | `unknown` | `blocked` | `true` | `false` | 入力契約違反でsupport判定を完了できない。入力契約を修正 |
| `unsupported` | `unsupported` | `ready` | `false` | `false` | runtime unitとしてfallback可能。QA成果物全体はfallbackが既存Skill契約へ閉じた場合だけ完了可能 |
| `limit_exceeded` | `supported`または`partial` | `blocked` | `true` | `false` | decode済みinputの契約上限超過。model分割またはcontract変更が必要 |
| `limit_exceeded` | `unknown` | `blocked` | `true` | `false` | decode前のbyte / depth上限超過。pre-parse error envelopeを返す |
| `internal_error` | `unknown` | `blocked` | `true` | `false` | support判定完了前後を問わず安全側でruntime requiredとして扱い、runtime不具合を修正 |
| `not_run` | `unknown` | `blocked` | `true` | `false` | Python unavailable。成果物metadataだけで表現 |

`stale`は`result_status`ではありません。semantic dependency preflightに成功した現在inputを現在scriptで正常実行したruntime resultは、保存時に`freshness_status=current`とします。`workflow_runtime.py`は保存済みdependencyと現在generationを共通freshness関数で再検証し、差分があれば`stale`へ変更して下流へ伝播します。`qa-workflow`だけをfreshnessの唯一の付与主体にせず、実行直後のcurrent判定と最終集約を分離します。

`fallback_reason`は`null / outside_supported_subset / python_unavailable`だけを許可します。`runtime_status=unsupported`では`outside_supported_subset`、`runtime_status=not_run`では`python_unavailable`です。`runtime_status=not_run`では`input_fingerprint / model_fingerprint / generation_fingerprint`を`null`とし、決定論的再利用の証拠に使いません。`support_status=partial`のunsupported itemはitem単位で後述の`unsupported_item_closures[]`へ閉じ、その閉鎖情報を成果物へ保存します。

技法modelでは成果物metadataの`model_status`を`result_status`と同じ値にします。artifact全体scriptでは`artifact_status`を同じ値にします。

対応subset外かどうかはruntimeのsupport判定を正本とします。model全体がsubset外なら`runtime_status=unsupported / support_status=unsupported / runtime_required=false / result_status=ready / deterministic_generated=false / fallback_reason=outside_supported_subset`を保存します。これはruntime unitとしてfallback可能という意味であり、QA成果物全体はLLM fallbackが既存Skill契約を満たした場合だけ完了できます。`runtime_required=true`のunitで`deterministic_generated=false`なら決定論的処理未完了であり、ワークフロー全体を`完了`にしません。

Python unavailable時はsupport判定自体を実行できないため、runtime対象として選択済みのunitを`runtime_required=true / runtime_status=not_run / support_status=unknown / result_status=blocked / deterministic_generated=false / fallback_reason=python_unavailable`として保持し、ワークフローを`完了`にしません。LLMが成果物本文を作成しても決定論的処理済みとは扱いません。

`ok`、`invalid_input`、`unsupported`、`limit_exceeded`は終了code 0とします。`internal_error`は可能なら構造化envelopeを返して終了code 1、envelope自体を生成できない障害も終了code 1とします。Agent側は終了codeだけでroutingせずstdout envelopeをparseします。stderrは人間向け診断だけに使い、入力全文、secret、tokenを出しません。

`unsupported`はmodel全体が対応subset外であることをruntimeが確認した正常なfallback経路です。`partial`は独立して処理できるsupported部分を生成し、unsupported部分を`unsupported_items[]`として残します。Agent側でsupport判定を再実装せず、runtime対象modelをsupport判定前に省略することを禁止します。
### 3.4 構造化された未解決事項

`issues`は次のfieldを持ちます。

```json
{
  "issue_type": "unspecified_rule",
  "blocking": true,
  "skill": "test-condition-design",
  "runtime_unit_key": "model:decision-001",
  "model_key": "decision-001",
  "target_key": "R4",
  "generation_fingerprint": "sha256:...",
  "authority_refs": ["SPEC-001"],
  "required_information": "条件組合せに対する期待action",
  "route_to": "question-analysis",
  "resume_skill": "test-condition-design"
}
```

- `issue_type`、`blocking`、`skill`、`runtime_unit_key`は必須。runtime issue identityは`(skill, runtime_unit_key)`で扱う
- runtimeがcanonical inputを確定した後に生成したissueでは`generation_fingerprint`を必須にし、そのissueがどのruntime世代に対するものかを固定する。pre-parse errorまたはsubprocess timeout等でgenerationを確定できないissueだけ`generation_fingerprint=null`を許可する
- model scriptでは`model_key`必須、artifact scriptでは`model_key=null`
- target固有issueだけ`target_key`必須
- `route_to` / `resume_skill`は既存Skill名だけを許可
- `question-analysis`へ送る場合はRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprintを質問・ブロック・回答後の再開まで保持し、現在のruntime unitの`generation_fingerprint`と一致しない過去回答を自動適用しない
- 自由文stderrをrouting入力に使わない

## 4. canonicalization・version・fingerprint

### 4.1 canonical input・model・generation fingerprint

fingerprintはSHA-256で計算します。入力はUTF-8のcanonical JSONです。

- object keyはUnicode code point順
- `authority_refs` / `reference_refs`等の集合扱い配列は重複除去してsort
- 順序が意味として明示された配列だけ宣言順を保持する。factor、condition、action、state、transition、edge、production、Random distribution values等が該当する
- 順序に意味がないkey付きrecord配列は指定primary keyでcanonical sortする。`upstream_entities`は`(skill, entity_type, entity_ref)`、`upstream_runtime_units`は`(skill, runtime_unit_key)`、`previous_*`は各ID、`target_annotations / target_dispositions`は`target_ref`、`merge_groups`は`merge_group_key`でsortする
- assignment objectのkeyはsort
- decimal / date / datetimeは共通表現へ正規化
- JSON serializationはUTF-8、`ensure_ascii=false`相当、separatorは`,`と`:`、末尾改行なし
- canonicalizationはhash用bytesだけを作る処理にしない。strict decode後の値へ同じsort / dedup / decimal正規化を適用した`canonical_input`を作り、generator本体・structure script・ID allocatorはraw入力ではなくこの`canonical_input`を処理する
- 順序に意味がないrecord配列を並べ替えた入力は、fingerprintだけでなくmachine result / stable ID mappingも同一にする
- string valueはUnicode normalizationを行わず入力code point列を保持する
- decimalは指数表記を使わず、整数部の不要な先頭0と小数部の末尾0を除去し、`-0`は`0`へ正規化する
- dateは`YYYY-MM-DD`、local datetimeは`YYYY-MM-DDTHH:MM:SS`、fixed-offset datetimeは`YYYY-MM-DDTHH:MM:SS±HH:MM`だけをcanonical表現とし、fractional secondを禁止する
- fixed-offset datetimeのoffsetは意味データとして保持し、fingerprint用にUTCへ変換しない
- fixed-offset datetimeの大小比較・range intersectionはoffsetを適用したabsolute instantで行う。canonical value / fingerprintでは入力のoffset表現を保持し、named timezone / DST ruleを導入しない
- JSON whitespaceは除去
- 非有限数は不可

`input_fingerprint`はすべてのruntime scriptで必須です。次をcanonical JSON化してSHA-256を計算します。

- `skill`
- `runtime_unit_key`
- `input_mode`
- script固有`input`
- `authority_refs`
- `reference_refs`
- model scriptでは`selection_source`

`upstream_entities`はscript固有inputとは分離するため`input_fingerprint`へ含めません。ただし各`content_fingerprint`は`generation_fingerprint`へ含め、同じIDのAuthority / Risk / TR等の内容変更を別generationとして扱います。`static_data_versions`もgeneration条件として扱います。

`model_fingerprint`はmodel scriptだけ使用し、次をcanonical JSON化してSHA-256を計算します。

- `model_key`
- `model_type`
- `technique_slug`
- `selection_source`
- `selection_key`
- `input_fingerprint`

artifact全体scriptでは`model_fingerprint=null`です。ただし`input_fingerprint`が必ず存在するため、artifact input変更を検知できます。

`generation_fingerprint`は次をcanonical JSON化してSHA-256を計算します。

- `generator`
- `envelope_version`
- `input_fingerprint`
- `model_fingerprint`
- `runtime_contract_version`
- `generator_contract_version`
- `runtime_implementation_fingerprint`
- `generator_implementation_fingerprint`
- `upstream_entity_fingerprints`: 実際に消費した`upstream_entities[]`を`(skill, entity_type, entity_ref)`でsortした`{skill, entity_type, entity_ref, content_fingerprint}`配列
- `static_data_versions`

`runtime_implementation_fingerprint`は実行した`runtime_contract.py`、`generator_implementation_fingerprint`は実行scriptについて、UTF-8 textの`CRLF / CR`を`LF`へ正規化したbytesをSHA-256した値です。runtime自身が計算し、呼び出し側の申告値を正本にしません。本Planで追加する全runtime scriptはPython標準ライブラリと同一Skillの`runtime_contract.py`以外のSkill-local Python moduleをimportしません。model generatorだけでなくartifact scriptも同じ制約です。共通exact numeric、intersection、canonicalization、freshness等の現在必要な共有処理は`runtime_contract.py`へ置き、implementation fingerprint対象外helperへ実行ロジックを逃がしません。

したがって、同じartifact scriptでも入力、実際に消費した上流Entityのcanonical content、runtime contract、generator contract、実装内容、静的参照データのいずれかが変われば`generation_fingerprint`は変わります。`authority_refs`等のID文字列が同じでも、対応するEntity contentが変われば同じgenerationにはなりません。

`runtime_contract_version` / `generator_contract_version`は意味契約変更時に更新します。bug fixや内部refactorで意味契約を変えない場合も実装fingerprintが変わるため旧machine evidenceを同一生成条件として再利用しません。探索順、tie-break、Coverage、target key等の契約自体を変える場合は実装fingerprintだけで済ませず対応contract versionも更新します。

generatorが返すtarget集合とCoverage計算は純粋な決定論処理です。target → CI ID等のID維持はstateful materialize処理であり、同じgenerator結果、`target_annotations / target_dispositions / merge_groups`、`previous_target_id_map / previous_ci_ids / previous_expected_result_roots`から同じmappingとID状態を得ることを保証します。
### 4.2 静的参照データ

generator結果に影響する静的データはversionを持ちます。

- `ui-pattern-catalog.json`: strict JSON decode → canonical JSON → SHA-256。改行や整形差だけではversionを変えない
- repository-default risk scheme: `risk-scheme-v1`
- project-specific scheme: 正規化schemeのfingerprint
- grammar / distribution / metamorphic relation等が外部assetの場合: そのasset versionまたはfingerprint

同じscriptでも静的データversionが異なる場合は同じ再現条件とは扱いません。

### 4.3 正規技法slugとmodel_keyの安定性

`technique_slug`はSkill契約上の正規テスト技法だけを表します。

| 正規テスト技法 | technique slug |
| --- | --- |
| 同値分割 | `ep` |
| 境界値分析 | `bva` |
| Domain Testing | `domain` |
| デシジョンテーブル | `decision` |
| Pairwise / 組合せ | `comb` |
| 状態遷移 | `state` |
| エラー推測 | `error-guessing` |
| シナリオ / ユースケース | `scenario` |
| CRUD Testing | `crud` |
| Syntax-Based Testing | `syntax` |
| Random Testing | `random` |
| Metamorphic Testing | `metamorphic` |

runtime内部identityは`model_type`で分けます。

| model / adapter | model_type | Coverage所有時のtechnique_slug |
| --- | --- | --- |
| EP model | `ep` | `ep` |
| BVA model | `bva` | `bva` |
| Domain model | `domain` | `domain` |
| Decision Table model | `decision` | `decision` |
| combinatorial model | `comb` | `comb` |
| Classification Tree adapter | `classification` | `null` |
| state model | `state` | `state` |
| flow model | `flow` | `scenario` |
| CRUD model | `crud` | `crud` |
| Cause-Effect adapter | `cause-effect` | `null` |
| Syntax model | `syntax` | `syntax` |
| schema / HTML adapter | `schema` | `null` |
| UI pattern adapter | `ui` | `null` |
| Random model | `random` | `random` |
| Metamorphic model | `metamorphic` | `metamorphic` |
| エラー推測 semantic model | `error-guessing` | `error-guessing` |

`model_key=<model_type>-\d{3,}`です。内部adapterは`technique_slug / selection_source / selection_key=null`とし、Coverage所有child modelがcanonical `technique_slug`と技法選択元を持ちます。

エラー推測はsemantic modelを持ちますが専用runtime generatorは追加しません。generator dispatchは§2.1の`model_type → generator`表だけを使います。

同じmodel type・同じ検証責務を改訂する場合は既存`model_key`を維持し、意味上別modelだけ同じ`model_type`の最大番号+1で採番します。削除済みkeyを別modelへ再利用しません。

### 4.4 上流変更

同じIDでも上流Entityの構造化内容は変わり得るため、自由記述versionやMarkdown全文hashではなく、実際に消費したEntityのcanonicalな構造化内容から`content_fingerprint`を計算します。これは意味同値性を推論するhashではなく、正規項目の変更検出用です。

#### canonical machine Entityの保存

下流fingerprint対象となるEntityは、runtimeの有無にかかわらず各担当Skillの成果物へcanonical JSONとして保存します。Markdown表を再読解してEntity JSONを再生成しません。

````markdown
### Machine Entities: test-requirement-design

```json
{
  "schema_version":"entity-state-v1",
  "skill":"test-requirement-design",
  "entities":[
    {
      "entity_type":"tr",
      "entity_ref":"TR-001",
      "model_key":null,
      "content":{...},
      "content_fingerprint":"sha256:...",
      "upstream_entity_dependencies":[
        {
          "skill":"spec-analysis",
          "entity_type":"authority",
          "entity_ref":"SPEC-001",
          "content_fingerprint":"sha256:..."
        }
      ],
      "runtime_dependencies":[
        {
          "skill":"test-requirement-design",
          "runtime_unit_key":"artifact:requirement_structure:all",
          "generation_fingerprint":"sha256:..."
        }
      ]
    }
  ]
}
```
````

- `spec-analysis`はruntime unitを追加せず、解決済みAuthorityの正規化済みfieldを`authority_entities.py`へ渡し、同scriptがcanonical `content`、`content_fingerprint`、Machine Entity wrapper、expected identityを生成してblockへ保存する。LLMがAuthority Machine Entity JSONやfingerprintを手計算しない。`authority_entities.py`の実行・strict decode・schema検証に失敗した場合はAuthority Machine Entityを未生成のまま対象範囲を`blocked`とし、LLMや別builderがfingerprint / Machine Entityを代替生成しない。Python unavailable時も同様に決定論的Entity生成済みとは扱わない
- `test-analysis`は`analysis_entities.py`がLLMの意味fieldとcurrent runtime resultを固定schemaでjoinして保存する。例えばProduct Riskは`failure / authority_refs / impact / likelihood / assessment_reason / confidence_note`と`risk_matrix.py`の`level / mapped_priority`をjoinする。Technique Selectionでは候補runtime結果と最終選択・undetermined signal closureをjoinし、change graph / environment requirementも同じbuilderでMachine Entity化する
- `test-requirement-design` / `test-condition-design` / `test-case-design`はstructure scriptへ渡した意味fieldとruntimeが確定したID・優先度等を固定builderでjoinして保存する
- Markdownの人間向け表はMachine Entityと同じ意味fieldを表示し、validatorでID・参照・優先度・期待結果等の一致を確認する。Machine Entityにない意味fieldをMarkdownだけへ追加して下流正本にしない
- `entity_type`は`authority / test_analysis_context / product_risk / technique_selection / change_node / change_edge / environment_requirement / test_data_requirement / tr / tcn / model / ci / tc / disposition`の固定値だけを許可する。Machine Entity identityは`(skill, entity_type, entity_ref)`で一意とし、異なるtypeの同名keyを衝突扱いしない
- `entity_ref`は各typeのstable ID / keyを使用する。test-analysis contextは`analysis-context:all`。Dispositionは`<upstream entity_type>:<upstream entity_ref>`とし、bare IDだけをidentityにしない
- `content_fingerprint`は`content`からruntime / validatorが再計算し、保存値と一致必須にする
- `content`は意味上のEntity本体、`upstream_entity_dependencies[] / runtime_dependencies[]`はfreshness用の機械metadataであり`content_fingerprint`へ含めない
- `upstream_entity_dependencies[]`はその意味判断を行った時点で実際に参照した上流Entityの`skill / entity_type / entity_ref / content_fingerprint`を保存する。上流内容が変わった場合は、同じEntity IDでも意味判断を再確認するまでこのEntityを`stale`とする
- `runtime_dependencies[]`はそのEntityの現在状態を成立させるruntime unitだけを列挙する。Authority等、上流もruntimeも持たないsource Entityでは両配列を空にできる
- 複数用途SkillでMachine Entityを保存する場合は既存`対象 / 実行範囲`をblock metadataへ保持し、本Planでruntime対象となる`test-analysis: テスト分析`と他用途を混在させない

`spec-analysis`のAuthority Entityでは次の項目をcanonical化します。

- 仕様根拠ID
- 種別
- 現在有効な内容
- 適用範囲
- 情報源 / 正本一覧
- 関係
- 関連仕様根拠ID

以降のQA成果物は、下流が実際に利用するEntity単位でfingerprint対象項目を固定します。

- `test-analysis` context: テスト分析範囲、案件固有のテスト目的 / 重点、テストレベル、環境制約、対象外、ブロッカー、テスト重点、テスト可能性 / テストレベル判断、残存リスク
- `test-analysis` Product Risk: リスクID、失敗、関連する現在有効な仕様根拠 / 変更 / 依存、影響度、発生可能性、評価根拠、信頼度補足、level、mapped priority
- `test-analysis` 技法選択: selection key、適用領域、selection source、signals、候補、undetermined signal closure、最終採用技法、選択理由、関連Risk / Authority、`test-condition-design`への着眼点、状態
- `test-analysis` change graph: node / edge key、type、from / to、source ref、変更種別、想定影響、evidence
- `test-analysis` 環境要求: requirement key、dimension、operator、正規化値、Authority
- `test-requirement-design`: TR ID、本文、Authority、Risk、優先度、`priority_override_reason`、テストレベル / 観測方法、およびDisposition行
- `test-condition-design`: TCN ID、TR、条件、技法、Coverage基準、Authority / Risk、優先度、`priority_override_reason`、`derived_from_model_key`を含むmodel metadata、target → CI mapping、およびDisposition行
- `test-case-design`: TC ID、関連TR / TCN / CI、優先度、`priority_override_reason`、前提、データ、手順、期待結果、期待結果Authority、およびDisposition行

fingerprint対象の`content`はLLMが自由に再構成しません。各担当Skillが保存するmachine dataから次のcanonical schemaで機械的に組み立てます。

- Authority: `{authority_id, authority_type, active_content, scope, source_refs[], relations[], related_authority_refs[]}`
- test-analysis context: `{scope, objectives[], test_levels[], environment_constraints[], exclusions[], blockers[], test_focus_items[], testability_decisions[], residual_risks[]}`
- Product Risk: `{risk_id, failure, source_refs[], authority_refs[], impact, likelihood, assessment_reason, confidence_note, level, mapped_priority}`
- 技法選択: `{selection_key, applicability_scope, selection_source, signals, candidates[], undetermined_signal_closures[], selected_techniques[], selection_reason, risk_refs[], authority_refs[], condition_design_focus[], status}`。`status=active|blocked|unresolved`。`undetermined_signal_closures[]`はcurrent `undetermined_signals[]`ごとに`{signal_key, handling, reason, question_id}`を1件持ち、`handling=selection_not_affected|question`だけを許可する。`selection_not_affected`は非空`reason`かつ`question_id=null`、`question`は`question_id=Q-\d{3}`を必須にする。current signalを解決できた場合はclosureへ`resolved`を残さず、`signals`を`true / false`へ更新して`technique_candidates.py`を再実行する。`status=active`では全current undetermined signalが`selection_not_affected`で閉じていることを必須にし、`question`が1件でもあればactiveにしない
- change graph node / edge: `{node_key, node_type, source_ref, change_kind, expected_impact}` / `{edge_key, from, to, edge_type, evidence_refs[]}`。人間向け変更表にある変更種別・想定影響をMachine Entityから落とさない
- 環境 / test data要求: `{requirement_key, environment_key, dimension_key, operator, normalized_value, authority_refs[], source_model_key, source_target_versions[]}`。environmentでは`environment_key`を必須とし、`source_model_key=null / source_target_versions=[]`。同じ`environment_key`内だけ同時成立を要求し、異なるkeyは代替環境として扱う。test dataでは`environment_key=null`、current model metadataの`source_model_key`を必須とする。model-wide requirementでは`source_target_versions=[]`を許可し、schema等のadapter由来ならそのcurrent adapter modelをsourceにできる。target-specific requirementではsource modelをCoverage所有modelとし、各source targetの`target_ref / target_content_fingerprint / generation_fingerprint`を1件以上保持する
- TR: `{tr_id, text, authority_refs[], risk_refs[], priority, priority_override_reason, test_level, observation_method}`
- TCN: `{tcn_id, tr_refs[], condition, category, technique_slugs[], coverage_criterion, authority_refs[], risk_refs[], priority, priority_override_reason}`
- model metadata: `{model_key, model_type, technique_slug, parent_tcn_id, selection_source, selection_key, derived_from_model_key}`。内部adapterでは`technique_slug / selection_source / selection_key / derived_from_model_key=null`。直接定義したCoverage所有modelでは`selection_source=analysis / condition_design / user`を必須とし、`analysis`だけ`selection_key`必須。adapter派生childでは`derived_from_model_key`へ同一TCNのcurrent adapter modelを必須で保持する
- CI: `{ci_id, tcn_id, model_key, source_kind, covered_targets[], execution, semantic_item_key, semantic_item_text, semantic_source_targets[], priority, priority_override_reason, expected_result_root, authority_refs[], reference_refs[], test_data_requirement_refs[], status}`。`source_kind=runtime_target`では`covered_targets[]`を1件以上持ち、同一`execution_fingerprint`のcanonical `execution`を保存する。`source_kind=semantic_item`では`covered_targets=[] / execution=null`、`semantic_item_key / semantic_item_text`を必須とする。fork-join等のmachine targetからsemantic itemへ閉じる場合は`semantic_source_targets[]`へ`{target_ref, target_content_fingerprint, generation_fingerprint}`を保存し、エラー推測のように元machine targetがない場合は空配列とする。`covered_targets[]`は`{target_ref, target_key, target_content_fingerprint, execution_fingerprint}`を`target_ref`順で保持し、stable target_refのままtarget内容が変わった場合もCI content fingerprintが変わる
- TC: `{tc_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], environment_requirement_refs[], test_data_requirement_refs[], priority, priority_override_reason, preconditions, test_data, steps, expected_results[], postconditions_or_cleanup}`
- Disposition: `{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`。`covered_by_entity`は`null`または同じ4 fieldを持つ完全Machine Entity参照。これはAuthority / Risk / TR / TCN / CI等のMachine Entityを閉じる共通Dispositionです。Coverage targetの`target_dispositions[]`はMachine Entityではなく`materialize_coverage.py`のruntime stateとして保持し、このschemaへ無理に変換しません

machine dataに存在しない表示専用の備考やMarkdown整形は`content`へ入れません。Machine Entity schemaの意味変更は`entity-state-v1`のversion変更として扱い、そのschemaを消費するruntime contractも更新します。

Machine Entityの`upstream_entity_dependencies[]`は次を最低限含めます。直接参照していない無関係Entityを追加しません。

`input_mode=artifact`では以下に列挙した外部semantic dependencyをcurrent Machine Entityへ完全解決します。`input_mode=direct`では、既存Skill契約が許す直接入力のうち実際にcurrent Machine Entityとして渡された参照だけを`upstream_entity_dependencies[]`へ保存し、存在しない前工程Entityを合成しません。direct inputの構造化内容自体はstructure / artifact runtimeの`input_fingerprint / generation_fingerprint`へ入り、そのruntimeを生成Entityの`runtime_dependencies[]`へ保存するため、直接入力の内容変更もstale判定できます。

- Authority: なし。関連Authority IDはcontent内の関係として保持するが、別Authorityの内容変更で自動staleにするかは既存`spec-analysis`の関係解決結果に従う
- test-analysis context: scope / objective / test level / environment constraint / exclusion / blocker / test focus / testability判断で実際に参照したAuthority / Product Risk
- Product Risk: `authority_refs[]`のAuthorityに加え、`source_refs[]`のうちrisk判断より上流のAuthority / change graph等としてMachine Entityへ解決でき、実際に使用したsource Entity。既存TR / TCN / CI / TC等の下流QA成果物をrisk evidenceとして参照しても`upstream_entity_dependencies[]`へ逆向きedgeを作らず、content上のsource referenceとして保持する。これにより`Risk → … → TC → Risk`のdependency cycleを作らない
- 技法選択: selection判断で実際に参照したAuthority / Product Risk。後続のTR / TCN / CI / TCをsemantic dependencyへ逆参照しない
- change graph node / edge: `source_ref / evidence_refs[]`のうちAuthority等の上流Entityとして解決でき、node / edge判断へ実際に使用したsource Entity。Risk / TR / TCN / CI / TC等の下流QA成果物をgraph nodeとして表す場合はcontent上の参照に留め、`upstream_entity_dependencies[]`へ逆向きedgeを作らない
- environment requirement: `authority_refs[]`のAuthority
- test data requirement: `authority_refs[]`のAuthorityと`source_model_key`のcurrent model metadata。`source_target_versions=[]`のmodel-wide requirementではcurrent adapter modelも許可する。target-specific requirementではsource modelをCoverage所有modelに限定し、`source_target_versions[]`が同じ`source_model_key`のcurrent target versionと一致することを必須にする。source modelがruntime generatorを持つ場合は、そのcurrent model runtime unitも`runtime_dependencies[]`へ間接的に反映できるよう`test_data_requirements.py`の`upstream_runtime_units[]`へ保持する。source modelまたはtarget versionが変わればcurrent扱いしない
- TR: `authority_refs[]`のAuthorityと`risk_refs[]`のProduct Risk
- TCN: `tr_refs[]`のTR、直接`authority_refs[] / risk_refs[]`を持つ場合はそのAuthority / Product Risk
- model metadata: 親TCN。`selection_source=analysis`では技法選択Entity。`derived_from_model_key`が非nullのchildでは参照adapter model Entityをsemantic dependencyとして持つ。child model Entityは`condition_structure.py`でadapter runtime実行前に生成されるため、まだ存在しないadapter runtime generationを`runtime_dependencies[]`へ要求しない。adapter runtime generationへの依存はchild generatorの`upstream_runtime_units[]`で保持し、そのchild runtimeへ依存する下流Entityへfreshnessを伝播する
- CI: 親TCN、Coverage所有model metadata、参照するtest data requirement Entity。runtime targetでは現在target version、semantic itemでは本文と`source_target_versions[]`をcontentへ含める
- TC: `tr_refs[] / tcn_refs[] / ci_refs[] / environment_requirement_refs[] / test_data_requirement_refs[]`の各Entityと各expected resultで実際に参照したAuthority
- Disposition: `upstream_entity`、Authority、`covered_by_entity`がある場合はその参照先Entity。保存fingerprint不一致はstale

structure / materialize / generator等がEntity状態を機械的に成立させる場合は、そのruntime unitを`runtime_dependencies[]`へ追加します。semantic dependencyとruntime dependencyを相互代用しません。

modelは実際に消費したEntityを`upstream_entities`へ1件ずつ保持し、runtimeがcanonical `content`から`content_fingerprint`を計算します。`skill + entity_type + entity_ref`が同じEntityの`content_fingerprint`だけを比較し、不一致となったEntityを参照するmodelだけを`要再検証`へ戻します。無関係なEntity変更ではmodelをstaleにしません。

他runtime結果を直接利用したunitは`upstream_runtime_units`も`(skill, runtime_unit_key)`で比較します。保存した`generation_fingerprint`と現在の上流runtime unitが一致しなければ下流unitをstaleとし、その下流へも依存関係に従って伝播します。参照先が存在しない場合はstale + blocker、同じ`(skill, runtime_unit_key)`が重複する場合またはruntime dependency graphにcycleがある場合は`invalid_input`です。LLMはこのfingerprint比較を手計算しません。
## 5. 値・順序・tie-break

### 5.1 typed value

対応型は既存のinteger / boolean / string / enum / decimal / null / date / datetimeを維持します。

integer / decimalはstrict JSON decode時にPythonの`int` / `float` / `Decimal`へ即時変換せず、数値tokenを字句列として共通numeric validatorへ渡します。

- raw numeric tokenは4,096文字以下
- canonical整数 / decimal表現は符号と小数点を含め4,096文字以下
- exponent入力は許可するが、coefficient桁数・scale・exponentから展開後canonical表現の桁数を文字列展開前に計算し、4,096文字を超える場合は巨大なゼロ埋めや整数生成を行わず`limit_exceeded`
- 非有限数とJSON規格外number tokenは`invalid_input`
- decimalは`integer coefficient + base-10 scale`へ正規化し、比較・加減算・乗算をexactに行う。Python `Decimal` context precisionやbinary floatへ結果を依存させない
- BVA、range intersection、Metamorphic `add_decimal / multiply_decimal`は同じhelperを使う
- 演算結果が上限を超える場合は`limit_exceeded`で止め、丸めない

nullable factorやtimezoneの既存契約は維持します。

### 5.2 順序

- 宣言順を意味に使う配列は入力順を維持
- 集合扱いのrefs / key集合はcanonical sort
- factor subsetは入力factor indexのtuple昇順
- uncovered targetはcanonical target key昇順
- greedy completionは「新たにCoverageするtarget数が多い候補」を優先
- 同scoreならvalue indexの辞書順
- 生成rowは生成順を保持
- locale依存sortを使用しない

### 5.3 共通hard limit

上限の計測規則を先に固定します。

- 入力JSON byte数: stdinで受け取ったUTF-8 bytesをdecode前に数える
- nesting depth: object / array containerを1階層としてroot containerを1と数える
- 1文字列: UTF-8 bytesで数える
- 探索node: rootを1とし、combinatorial / Decision Tableでは新しいpartial assignment、state / flowでは新しいpath / cycle prefix、grammarでは新しいpartial derivationを展開するたびに1加算する。cache hitで再探索しない場合は加算しない
- target / row / candidate総数: stable keyによる重複除去後、Markdown materialize前に数える
- stdout JSON: UTF-8 serialization後のbytesを数える

次を契約値として固定します。

| 対象 | 上限 |
| --- | ---: |
| 通常runtime入力JSON | 2 MiB |
| 集約runtime入力JSON（`materialize_coverage.py` / `traceability.py` / `workflow_runtime.py`） | 16 MiB |
| JSON / schema / ASTのnesting depth | 64 |
| 1文字列 | 64 KiB |
| Decision Table / Cause-Effectのassignment | 65,536 |
| Pairwise / N-wise / mixed-strengthのCoverage target | 100,000 |
| 探索node | 1,000,000 |
| 生成row / test data candidate / Domain point | 10,000 |
| state sequence / flow path | 10,000 |
| grammar生成case | 10,000 |
| Random Testing生成case | 10,000 |
| 1 modelのtarget / row / candidate総数 | 100,000 |
| stdout JSON | 16 MiB |

上限を超えた場合は`limit_exceeded`とし、Coverage基準、strength、path深度等を自動で下げません。item数が上限内でもbyte / depth上限を超える入力・出力は処理しません。集約scriptは複数上流結果をまとめた**最終stdin全体**へ16 MiB上限を適用し、個々の上流unitが成功していても集約入力が上限を超えればworkflowを完了にしません。これによりstage間transport上限を明示し、暗黙のtruncateや分割で意味を変えません。上限変更は実装者判断ではなくcontract変更としてPlanを更新します。16 MiBはruntime engineのstdout / 集約stdin上限であり、Agentが同量を安全に成果物へ統合できることを意味しません。代表generator実装後の共通経路smokeで実Agentのstdout取得・strict decode・成果物保存を境界付近まで確認し、16 MiB未満の実用上限が必要なら後続generatorを量産する前に`runtime-v1`へ固定します。上限超過時にmachine evidenceをtruncate / 要約しません。

## 6. 根拠・constraint

### 6.1 根拠継承

- model-level refsはmodel全体の既定根拠
- element-level refsはその要素固有の根拠
- 生成候補は、関連model-level refsと実際に関与したelement / constraint refsだけを重複除去して継承
- 無関係な要素のrefsを伝播しない
- `reference_refs`だけで製品固有expected resultを確定しない

Coverage母集団から除外するconstraintは1件以上の`authority_refs`を必須にします。

### 6.2 constraint表現

任意Python式は受け付けません。有限domainでは部分assignmentベースの禁止制約を共通形式とします。

```json
{
  "constraint_key": "C1",
  "assignment": {"role": "guest", "visibility": "private"},
  "authority_refs": ["SPEC-002"]
}
```

Domain Testingは[基本generator契約](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md) §5で固定した線形border schemaだけを使用し、共通constraint以外の任意ASTや式言語を追加しません。

## 続き

[stable ID・materialize・workflow契約](./2026-09-18_170000_deterministic-test-technique-automation_02_identity-materialize-and-workflow-contracts.md) に続きます。
