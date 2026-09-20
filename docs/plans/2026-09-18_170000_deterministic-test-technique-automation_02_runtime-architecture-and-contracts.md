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

| Skill | 対象 / 実行範囲 | 条件 | script | 実行 |
| --- | --- | --- | --- | --- |
| `test-analysis` | `テスト分析` | Product Riskがある | `risk_matrix.py` | 条件付き |
| `test-analysis` | `テスト分析` | 技法選択を行う | `technique_candidates.py` | 必須 |
| `test-analysis` | `テスト分析` | 変更影響graphがある | `change_impact.py` | 条件付き |
| `test-analysis` | `テスト分析` | 環境要求がある | `environment_requirements.py` | 条件付き |
| `test-analysis` | `テスト分析` | test-analysis成果物を保存する | `analysis_entities.py` | 必須 |
| `test-requirement-design` | 単一用途 | 成果物確定前 | `requirement_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | TCN / model draft作成後 | `condition_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | active modelの`model_type`が下表のgeneratorを持つ | model type対応generator | modelごとに必須 |
| `test-condition-design` | 単一用途 | test data要求が1件以上ある | `test_data_requirements.py` | 条件付き |
| `test-condition-design` | 単一用途 | current machine targetまたは`semantic_coverage_items[]`が1件以上ある | `materialize_coverage.py` | TCNごとに必須 |
| `test-case-design` | 単一用途 | 成果物確定前 | `case_structure.py` | 必須 |
| `coverage-analysis` | `テスト設計` | traceabilityを検査する | `traceability.py` | 必須 |
| `qa-workflow` | 単一用途 | runtime状態を集約する | `workflow_runtime.py` | 必須 |

model typeからgeneratorへの対応は次だけを許可します。model runtimeの`expected_runtime_units[]`はこの表から、artifact runtimeの`expected_runtime_units[]`は直前のSkill dispatch表から導出し、両集合を連結します。

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

1. LLMがadapterを採用する時点で、adapter model draftと、それから派生させるCoverage所有child model draftを同じ`condition_structure.py`入力へ含める
2. child model draftは`derived_from_model_draft_key`で同じ入力内のadapter draftを1件だけ参照する。adapterでない親、unknown draft、自己参照、複数親は`invalid_input`
3. `condition_structure.py`がadapter / child双方の`model_key`と親TCNを先に確定し、active Technique Selectionの`selected_techniques[]`がCoverage所有child modelへ到達することをこの時点で検証する
4. adapter modelは`technique_slug=null / selection_source=null / selection_key=null`、child modelはcanonical `technique_slug`と`selection_source=analysis / condition_design / user`を持つ。`analysis`由来childだけ元の`selection_key`を保持する
5. 確定したadapter `model_key`で親runtimeを実行し、`derived.*`を生成する
6. 固定builderはchildの`derived_from_model_key`から親adapter runtime unitを一意に解決し、child generatorの`upstream_runtime_units[]`へそのcurrent generationを保存する。LLMはruntime dependencyを手入力しない
7. LLMは派生先で必要な意味パラメータだけを補い、固定builderが親runtimeのmachine outputとjoinして既に採番済みのchild model inputを作る
8. adapter出力を正規技法として採用した場合は対応childを必須にし、採用しない候補はTechnique Selectionの`selected_techniques[]`へ残さない。adapter親や別のclosure行でchild欠落を隠さない

固定対応:

- `classification` adapter → child `comb`
- `cause-effect` adapter → child `decision`
- `schema` adapter → 採用したCoverageに応じてchild `ep / bva / comb`
- `ui` adapter → 正規技法modelを自動生成せず、既存`test-condition-design`の意味判断へ候補を渡す

同じ親runtime generationから同じchild inputを作る場合は固定builderを使います。

## 3. 共通JSON契約

### 3.0 CLI契約

すべてのruntime scriptは同じCLI契約を使用します。

- 起動は`python <script-path>`
- stdinからUTF-8のstrict JSON objectを1件だけ読む
- positional argument、入力file path、環境変数から業務入力を受け取らない
- cwdへ依存せず、Skill root相対のassetは`__file__`から解決する
- stdoutはruntime envelopeのJSON object 1件だけ。logや説明文を混在させない
- stderrは人間向け診断だけに使う
- stdinが空、JSONが複数、末尾に非空白データが残る場合は`invalid_input`
- strict decode前に失敗し、`runtime_unit_key / input_fingerprint / model_fingerprint / generation_fingerprint`を確定できない場合も、可能なら§3.3のpre-parse error envelopeをstdoutへ返す。callerが推測したfingerprintを補わない
- subprocess呼び出し側はstdout / stderr / return codeをすべて取得し、return codeだけでroutingしない
- Skill実行時のsubprocessにも30秒の安全timeoutを設定する。通常の探索停止は§5.3の決定論的hard limitで行い、timeoutをCoverageや探索アルゴリズムの正常終了条件にしない。timeout時はmachine resultを採用せず、成果物metadataでは`runtime_status=internal_error / support_status=unknown / result_status=blocked / runtime_required=true / deterministic_generated=false`として扱い、構造化issueの`issue_type=runtime_execution_timeout`で原因を区別する。`runtime_execution_timeout`を新しい`runtime_status`にはしない

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
- `upstream_entities`: script固有input内のAuthority / Risk / TR / TCN等の参照のうち、そのscript契約でsemantic dependencyと定義したMachine Entityから固定builderが導出する。callerが参照Entityを任意に省略・追加しない。runtimeはcanonical `content`から`content_fingerprint`を再計算し、参照集合との不足・余分・重複を`invalid_input`にする
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

script固有入力は必ず`input`配下に置き、metadataと同じkeyを再定義しません。target / result keyへ文字列として直接埋め込むstable component keyは`^[A-Za-z][A-Za-z0-9._-]{0,63}$`で固定し、delimiterの`:`を禁止します。任意文字列を含むidentityはcanonical JSONをhashしてkey化します。

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
- JSON whitespaceは除去
- 非有限数は不可

`input_fingerprint`はすべてのruntime scriptで必須です。次をcanonical JSON化してSHA-256を計算します。

- `skill`
- `runtime_unit_key`
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

`runtime_implementation_fingerprint`は実行した`runtime_contract.py`、`generator_implementation_fingerprint`は実行scriptについて、UTF-8 textの`CRLF / CR`を`LF`へ正規化したbytesをSHA-256した値です。runtime自身が計算し、呼び出し側の申告値を正本にしません。generator scriptはPython標準ライブラリと同一Skillの`runtime_contract.py`以外のSkill-local Python moduleをimportしません。これによりgenerator実装fingerprintの対象外で実行ロジックが変わる経路を作りません。

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

- `spec-analysis`はruntimeを追加せず、解決済みAuthorityをこのblockの`content`へ直接保存する
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
- `coverage-analysis`: 対象上流 / 下流ID、Model Key、coverage / stale状態、修正Skill

fingerprint対象の`content`はLLMが自由に再構成しません。各担当Skillが保存するmachine dataから次のcanonical schemaで機械的に組み立てます。

- Authority: `{authority_id, authority_type, active_content, scope, source_refs[], relations[], related_authority_refs[]}`
- test-analysis context: `{scope, objectives[], test_levels[], environment_constraints[], exclusions[], blockers[], test_focus_items[], testability_decisions[], residual_risks[]}`
- Product Risk: `{risk_id, failure, source_refs[], authority_refs[], impact, likelihood, assessment_reason, confidence_note, level, mapped_priority}`
- 技法選択: `{selection_key, applicability_scope, selection_source, signals, candidates[], undetermined_signal_closures[], selected_techniques[], selection_reason, risk_refs[], authority_refs[], condition_design_focus[], status}`。`status=active|blocked|unresolved`、`undetermined_signal_closures[]`は各null signalを`resolved / selection_not_affected / question`のいずれかへ1回だけ閉じ、未閉鎖signalがある状態で`active`にしない
- change graph node / edge: `{node_key, node_type, source_ref, change_kind, expected_impact}` / `{edge_key, from, to, edge_type, evidence_refs[]}`。人間向け変更表にある変更種別・想定影響をMachine Entityから落とさない
- 環境 / test data要求: `{requirement_key, dimension_key, operator, normalized_value, authority_refs[], source_model_key, source_target_versions[]}`。environmentでは`source_model_key=null / source_target_versions=[]`。test dataではcurrent model metadataの`source_model_key`を必須とする。model-wide requirementでは`source_target_versions=[]`を許可し、schema等のadapter由来ならそのcurrent adapter modelをsourceにできる。target-specific requirementではsource modelをCoverage所有modelとし、各source targetの`target_ref / target_content_fingerprint / generation_fingerprint`を1件以上保持する
- TR: `{tr_id, text, authority_refs[], risk_refs[], priority, priority_override_reason, test_level, observation_method}`
- TCN: `{tcn_id, tr_refs[], condition, category, technique_slugs[], coverage_criterion, authority_refs[], risk_refs[], priority, priority_override_reason}`
- model metadata: `{model_key, model_type, technique_slug, parent_tcn_id, selection_source, selection_key, derived_from_model_key}`。内部adapterでは`technique_slug / selection_source / selection_key / derived_from_model_key=null`。直接定義したCoverage所有modelでは`selection_source=analysis / condition_design / user`を必須とし、`analysis`だけ`selection_key`必須。adapter派生childでは`derived_from_model_key`へ同一TCNのcurrent adapter modelを必須で保持する
- CI: `{ci_id, tcn_id, model_key, source_kind, covered_targets[], execution, semantic_item_key, semantic_item_text, semantic_source_targets[], priority, priority_override_reason, expected_result_root, authority_refs[], reference_refs[], test_data_requirement_refs[], status}`。`source_kind=runtime_target`では`covered_targets[]`を1件以上持ち、同一`execution_fingerprint`のcanonical `execution`を保存する。`source_kind=semantic_item`では`covered_targets=[] / execution=null`、`semantic_item_key / semantic_item_text`を必須とする。fork-join等のmachine targetからsemantic itemへ閉じる場合は`semantic_source_targets[]`へ`{target_ref, target_content_fingerprint, generation_fingerprint}`を保存し、エラー推測のように元machine targetがない場合は空配列とする。`covered_targets[]`は`{target_ref, target_key, target_content_fingerprint, execution_fingerprint}`を`target_ref`順で保持し、stable target_refのままtarget内容が変わった場合もCI content fingerprintが変わる
- TC: `{tc_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], environment_requirement_refs[], test_data_requirement_refs[], priority, priority_override_reason, preconditions, test_data, steps, expected_results[], postconditions_or_cleanup}`
- Disposition: `{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`。`covered_by_entity`は`null`または同じ4 fieldを持つ完全Machine Entity参照。これはAuthority / Risk / TR / TCN / CI等のMachine Entityを閉じる共通Dispositionです。Coverage targetの`target_dispositions[]`はMachine Entityではなく`materialize_coverage.py`のruntime stateとして保持し、このschemaへ無理に変換しません

machine dataに存在しない表示専用の備考やMarkdown整形は`content`へ入れません。Machine Entity schemaの意味変更は`entity-state-v1`のversion変更として扱い、そのschemaを消費するruntime contractも更新します。

Machine Entityの`upstream_entity_dependencies[]`は次を最低限含めます。直接参照していない無関係Entityを追加しません。

- Authority: なし。関連Authority IDはcontent内の関係として保持するが、別Authorityの内容変更で自動staleにするかは既存`spec-analysis`の関係解決結果に従う
- test-analysis context: scope / objective / test level / environment constraint / exclusion / blocker / test focus / testability判断で実際に参照したAuthority / Product Risk
- Product Risk: `authority_refs[]`のAuthorityに加え、`source_refs[]`のうちrisk判断より上流のAuthority / change graph等としてMachine Entityへ解決でき、実際に使用したsource Entity。既存TR / TCN / CI / TC等の下流QA成果物をrisk evidenceとして参照しても`upstream_entity_dependencies[]`へ逆向きedgeを作らず、content上のsource referenceとして保持する。これにより`Risk → … → TC → Risk`のdependency cycleを作らない
- 技法選択: selection判断で実際に参照したAuthority / Product Risk。後続のTR / TCN / CI / TCをsemantic dependencyへ逆参照しない
- change graph node / edge: `source_ref / evidence_refs[]`のうちMachine Entityとして解決でき、node / edge判断へ実際に使用したsource Entity
- environment requirement: `authority_refs[]`のAuthority
- test data requirement: `authority_refs[]`のAuthorityと`source_model_key`のcurrent model metadata。`source_target_versions=[]`のmodel-wide requirementではcurrent adapter modelも許可する。target-specific requirementではsource modelをCoverage所有modelに限定し、`source_target_versions[]`が同じ`source_model_key`のcurrent target versionと一致することを必須にする。source modelまたはtarget versionが変わればcurrent扱いしない
- TR: `authority_refs[]`のAuthorityと`risk_refs[]`のProduct Risk
- TCN: `tr_refs[]`のTR、直接`authority_refs[] / risk_refs[]`を持つ場合はそのAuthority / Product Risk
- model metadata: 親TCN。`selection_source=analysis`では技法選択Entity。`derived_from_model_key`が非nullのchildでは参照adapter model Entityと、そのadapterのcurrent runtime unitをdependencyへ持つ
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
- exponent入力は許可するが、展開後canonical表現が4,096文字を超える場合は`limit_exceeded`
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

Domain Testingは`_03` §5で固定した線形border schemaだけを使用し、共通constraint以外の任意ASTや式言語を追加しません。

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

TR / TCN / TCは既存の3桁形式をこのPlanで変更しません。最大番号が999に達した成果物系列で新規IDが必要な場合は削除済みIDを再利用せず、`id_space_exhausted` issueとしてブロックします。CIは`CI\d{2,}`のため同じ上限を持ちません。

### 7.2 Coverage targetとCI

generator内の`target_key`はmodel内で安定させます。異なるmodel間の衝突を避けるため、成果物横断のtarget identityとして`target_ref`を追加します。

`target_ref = sha256(canonical JSON({"model_key": <model_key>, "target_key": <target_key>}))`

- `target_ref`は`sha256:<64 lowercase hex>`
- model generatorの共通post-processで各targetへ`target_ref`を付与する
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

TR / TCN / model / TCはpreviousでactiveだったIDがcurrentでactive reuseされなければ同じrowを`deleted`へ遷移させます。previous deleted rowは保持し、別項目へ再利用・復活させません。

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

`previous_target_id_map[]`はactive mappingだけでなく`mapping_status=active|inactive`、直近`ci_id`、その判断時点の`target_content_fingerprint`を保持し、Disposition中のtargetも過去mappingを失いません。CI番号は`CI\d{2,}`を許可します。
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
- undetermined signalは既存契約どおり`resolved / selection_not_affected / question`へ閉じる

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

各Skillは同じ正規化済みsourceから`expected_entity_identities[]`を固定builderで生成し、Machine Entity actual rowの存在を入力にして期待identityを逆算しません。`workflow_runtime.py`へ渡す際はbuilder出力をそのまま連結し、callerがidentityを追加・削除しません。期待runtime unitもdispatch表とactive model stateから固定builderで生成し、actual runtime集合から逆算しません。

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
- 本Planのdispatch対象runtime unitは、既存成果物を再利用する場合も現在のMachine Entity、保存済み意味parameter、previous ID stateからcanonical inputを組み立て直し、現在のscriptを必ず再実行する
- 保存済み正規化model / semantic draftを入力へ再利用する前に、そのruntime inputへ保存した`upstream_entities[]`および対応Machine Entityの`upstream_entity_dependencies[]`を現在のcanonical Entityと比較する。不一致があれば古い意味入力のままscriptを再実行せず、担当Skillへ`要再検証`として戻す。LLMが意味を再確認して現在のdependency fingerprintを保存した後にruntimeを実行する
- 保存済み`Machine Runtime Input / Result`はprevious state、差分確認、round-trip検証に使うが、現在のcontract / implementation / static data / support判定を省略するcacheにはしない
- 再実行した`generation_fingerprint`が以前と同じ場合はstable IDと現在も一致する意味判断を維持できる。generationが変わった場合はannotation / Disposition / merge / question回答 / unsupported closureの世代一致を再確認する
- 以前`runtime_required=false`だったwhole-model fallbackも現在runtimeでsupport判定を再実行し、現在supportedになったunitをfallbackのまま固定しない
- stale / `要再検証` / unresolvedなmodelが残っていないことを最終完了条件とする
- runtime対象unitをPython unavailable等で再実行できない場合は既存resultへfallbackせず`not_run / blocked`として保持する

### 13.2 legacy成果物

contract versionを持たない既存成果物を一律破棄しません。

- 従来契約を満たす間はlegacy成果物として参照可能
- その成果物を変更・再利用して本Plan対象の決定論的処理へ入る時点で、担当Skillが正規化modelを作成して新契約へ昇格
- legacy成果物を「決定論的生成済み」と表現しない

### 13.3 局所状態

runtime単位状態の正本は各成果物に保存した`runtime_unit_key`、`result_status`、`runtime_required`、`deterministic_generated`、`freshness_status`、fingerprint、構造化issueです。

`qa-workflow`を出力する場合は既存のSkill状態表を必須で維持しますが、この表は集約表示であり唯一の永続正本ではありません。他Skill実行の前提としてworkflow状態表の存在は要求せず、必要時は成果物metadataから状態を再構築します。

`qa-workflow`には既存Skill状態表とは別に次の`runtime状態`表を追加します。

`Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue`

- `Runtime Unit Key`は同一Skill内一意
- model scriptは`Runtime Unit Key = model:<model_key>`とし、`Model Key`を必須
- artifact全体scriptは`Runtime Unit Key = artifact:<generator>:<scope_key>`とし、`Model Key`は空欄
- `Support Status`は`supported / partial / unsupported / unknown`
- runtime集約inputの各runtime unitは共通`model_completion[] / target_mappings[] / target_dispositions[]` fieldを持ち、`artifact:materialize_coverage:<tcn_id>`だけ非空を許可する。他unitでは3配列を空固定とする。`target_mappings[]`はmaterialize outputの`target_id_map[]`を同名row schema `{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`で固定転記し、`target_dispositions[]`は`disposed_target_refs[]`へ`reason / authority_refs[]`を含むcurrent input dispositionをjoinして`_02` §7.4の完全schemaで転記する。LLMが生成しない。`traceability.py`と`workflow_runtime.py`は全materialize unitのtarget mapping / dispositionを集約し、`重複`参照のmissing / stale / cycle / terminal coverageを同じ規則で検査する
- `Result Status`は`ready / unresolved / blocked`
- `Freshness`は`current / stale`
- `Runtime Status`は`ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Runtime Required`と`Deterministic Generated`は`Yes / No`
- `Fallback Reason`は空欄 / `outside_supported_subset` / `python_unavailable`
- Skill状態表の`WF-D012`は既存Skill状態表だけへ適用し、runtime状態表へ流用しない
- 1 runtime unitだけ`blocked / unresolved / stale`でも独立した他unitは継続可能
- すべてのruntime unitで`Result Status=ready / Freshness=current`を必須とする
- `Runtime Required=Yes`のunitでは、さらに`Deterministic Generated=Yes`を必須とする
- `Runtime Required=No`のfallback unitは、既存Skill契約を満たして`Result Status=ready`になった場合だけworkflow完了を妨げない
- `Support Status=partial`のunitは`unsupported_items[]`がすべて§13.3のclosure契約へ妥当に閉じていることを完了条件にする。closure行が存在するだけでは閉鎖済みとみなさない
- model issueを`question-analysis`へroutingする場合は`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問一覧・ブロック中範囲・回答後の再開情報へ保持する
- artifact全体scriptのissueも`skill / runtime_unit_key / generation_fingerprint`をBlocker / Issueへ保持し、model keyを捏造しない
- unsupported item closureの`handling`は`llm_fallback / 対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複 / ブロック中`だけを許可する。`llm_fallback`と`重複`はcurrentな`covered_by_entity`を必須にし、`ブロック中`はclosure行があってもworkflow完了不可とする。その他のDispositionは既存`test-condition-design`のreason / Authority条件をそのまま適用する
- `llm_fallback`の`covered_by_entity`は同じunsupported itemを意味上カバーするcurrentなTCN / CI等のMachine Entityを参照し、参照先missing / stale / 対象modelと無関係なら未閉鎖として扱う。whole-model unsupportedも同じ規則でfallback先のcurrent性を確認する
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

Planで定義した正確性、hard limit、30秒のCLI test timeoutを標準ライブラリ実装で満たせない場合は、その実装をPlan未達として停止し、暗黙にCoverage基準を下げたり依存関係を変更したりしません。将来用adapterも作りません。
