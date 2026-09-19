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

### `test-analysis`

```text
skills/test-analysis/scripts/
├── runtime_contract.py
├── risk_matrix.py
├── technique_candidates.py
├── change_impact.py
└── environment_requirements.py
```

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

対象はテスト設計のAuthority / Risk → TR → TCN → CI → TC、またはCIを持たない契約でのTCN → TCです。E2E実装・実行結果は既存責務のままです。

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
2. script選択表から、その時点で条件を満たすruntime scriptを必須/条件付きと実行順に従って選ぶ。1回のSkill実行で複数scriptを順に呼べるが、script pathを自由文から推測しない
3. 保存済み`Machine Runtime Input / Result`を再利用する場合は`runtime_contract.py`が対象見出し直下のJSON fenceを抽出し、strict decode、runtime identity、model key、fingerprint一致を確認する。LLMがMarkdownからJSONを再生成しない
4. stdinへ共通metadataとscript固有inputを渡してscriptを起動する
5. stdout envelopeをstrict decodeし、return code、runtime status、issuesを合わせてroutingする
6. 意味判断が必要なissueは既存Skillまたは`question-analysis`へ戻し、機械結果をLLMが再計算しない
7. 意味入力を更新した場合はruntimeを再実行し、保存machine evidenceを置換する

各scriptは入力検証の一部として対応subset判定を行い、`runtime_required`を出力として決定します。`runtime_required`はruntime入力へ渡さず、Agentが自然言語だけから`runtime_required=false`を確定してscriptを省略しません。

dispatchは次で固定します。

| Skill | 対象 / 実行範囲 | 条件 | script | 実行 |
| --- | --- | --- | --- | --- |
| `test-analysis` | `テスト分析` | Product Riskがある | `risk_matrix.py` | 条件付き |
| `test-analysis` | `テスト分析` | 技法選択を行う | `technique_candidates.py` | 必須 |
| `test-analysis` | `テスト分析` | 変更影響graphがある | `change_impact.py` | 条件付き |
| `test-analysis` | `テスト分析` | 環境要求がある | `environment_requirements.py` | 条件付き |
| `test-requirement-design` | 単一用途 | 成果物確定前 | `requirement_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | TCN / model draft作成後 | `condition_structure.py` | 必須 |
| `test-condition-design` | 単一用途 | modelのtechnique slugが対応する | 各技法generator | modelごとに必須 |
| `test-condition-design` | 単一用途 | test data要求が1件以上ある | `test_data_requirements.py` | 条件付き |
| `test-condition-design` | 単一用途 | generator targetの閉鎖前 | `materialize_coverage.py` | TCNごとに必須 |
| `test-case-design` | 単一用途 | 成果物確定前 | `case_structure.py` | 必須 |
| `coverage-analysis` | `テスト設計` | テスト設計traceabilityを検査する | `traceability.py` | 必須 |
| `qa-workflow` | 単一用途 | runtime状態を集約する | `workflow_runtime.py` | 必須 |

複数用途Skillでは上表の正規`対象 / 実行範囲`にだけ本Planのruntimeをdispatchします。`test-analysis: E2E対象選定`や`coverage-analysis: TC → E2E実装 / E2E実装 → 実行結果`では本Planのruntime unitを作りません。これにより既存`qa-workflow`の複数用途状態を維持したまま、`(skill, runtime_unit_key)`を本Plan対象runtime内で一意にします。

`test-condition-design`のmodel slug → generatorは`_02` §4.3と`_03`のscript一覧を1対1対応の正本とします。artifact全体scriptを「常に全部実行する」とは扱わず、上表の条件を満たす場合だけ実行します。

freshnessは次の順序で扱います。

- 既存成果物を再利用する場合も、dispatch対象のruntime unitは保存済みresultを現在世代のcacheとして採用せず、現在のcanonical machine Entityと正規化済み入力からscriptを再実行する。保存済みMachine Runtime Input / Resultはprevious state、stable ID、round-trip検証の証拠として使用する
- whole-model `unsupported`やpartial fallbackも再利用時に現在runtimeでsupport判定を再実行する。以前unsupportedだったことだけを理由にscriptを省略しない
- 同じSkill実行内で現在のcanonical inputから正常に生成したruntime resultは、その実行内の直後の下流処理では`current`として扱う
- `materialize_coverage.py`は今回再実行して得た`current` model resultだけを受け取る
- `traceability.py`と`workflow_runtime.py`は同じ`runtime_contract.py`のfreshness評価関数を使い、保存済みruntime dependencyと現在runtime generationを比較する。AgentやLLMがfreshnessを手計算しない
- ワークフロー完了前に`workflow_runtime.py`を実行し、全runtime unitとMachine Entityのfreshness、完了可否を最終確認する

### 2.2 派生modelの生成

Cause-Effect → Decision Table、Classification Tree → combinatorial、schema → EP / BVA等の機械接続で別generatorを起動する場合は、親runtimeの出力を直接「別modelのinput」として匿名利用しません。

1. 親runtimeが`derived.*`を生成する
2. LLMは派生先で必要な意味パラメータだけを補う。親runtimeが生成したmachine fieldを再生成しない
3. `condition_structure.py`へ派生model draftを渡し、`model_key`と親TCNを確定する
4. 派生modelは`selection_source=derived`とする
5. 派生modelの`upstream_runtime_units[]`へ親generatorの`skill + runtime_unit_key + generation_fingerprint`を必須で保存する
6. 派生generatorを実行する

`condition_structure.py`はTCN / model keyの採番・所属検査を担当しますが、**そのID割当て結果だけを利用する既存model generatorの`upstream_runtime_units[]`へ`condition_structure.py`自身を登録しません**。派生model追加のために`condition_structure.py`を再実行してgeneration fingerprintが変わっても、既存model key・親TCNが維持されている限り親generatorをstaleにしません。generatorが`condition_structure.py`の別のmachine resultを実際に消費する場合だけ通常のruntime dependencyとして扱います。

同じ親runtime・同じ派生技法・同じ検証責務を再利用するとLLMが判断した場合は既存model keyを維持します。派生modelを作るためだけの汎用model factoryやplugin機構は追加しません。

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
- subprocess呼び出し側はstdout / stderr / return codeをすべて取得し、return codeだけでroutingしない
- Skill実行時のsubprocessにも30秒の安全timeoutを設定する。通常の探索停止は§5.3の決定論的hard limitで行い、timeoutをCoverageや探索アルゴリズムの正常終了条件にしない。timeout時はmachine resultを採用せず、成果物metadataでは`runtime_status=internal_error / support_status=unknown / result_status=blocked / runtime_required=true / deterministic_generated=false`として扱い、構造化issueの`issue_type=runtime_execution_timeout`で原因を区別する。`runtime_execution_timeout`を新しい`runtime_status`にはしない

### 3.1 strict JSON

すべてのruntime scriptはstrict JSONを使用します。

- duplicate object keyを拒否する
- `NaN`、`Infinity`、`-Infinity`を拒否する
- top-level typeをscriptごとに固定する
- UTF-8で解釈する
- model内のdecimalはJSON numberへ丸めず、`{"type":"decimal","value":"0.1"}`のような10進文字列で扱う
- raw JSON Schema / OpenAPI document等に含まれるJSON integerはPython `int`、非整数JSON numberは`Decimal`としてexactにparseし、binary `float`を経由しない
- canonical JSONへ再serializeする`Decimal`は指数表記を使わない正規化済みJSON numberとして出力する
- date / datetimeは契約で許可したISO 8601形式以外を拒否する

Python実装では、duplicate key検出用`object_pairs_hook`、`parse_float=Decimal`相当、非有限数拒否、`allow_nan=False`相当の出力を共通方針とします。

### 3.2 共通入力metadata

runtime入力は`metadata`とscript固有`input`を分けます。

```json
{
  "metadata": {
    "envelope_version": "1",
    "skill": "test-condition-design",
    "runtime_contract_version": "runtime-v1",
    "generator_contract_version": "combinatorial-v1",
    "runtime_unit_key": "model:pairwise-001",
    "model_key": "pairwise-001",
    "scope_key": null,
    "selection_source": "analysis",
    "upstream_entities": [
      {
        "skill": "test-requirement-design",
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

- `envelope_version`: runtime envelope形式のversion
- `skill`: runtime scriptが所属する既存Skill名。script pathから決まる値をruntime側の正本とし、入力値が不一致なら`invalid_input`
- `runtime_contract_version`: strict JSON、canonicalization、共通status、fingerprint等の共通処理version
- `generator_contract_version`: script固有の入出力・Coverage契約version。schema互換でも生成結果、tie-break、Coverage、target keyへ影響する変更では必ず更新する
- `runtime_unit_key`: すべてのruntime invocationで必須。model scriptは`model:<model_key>`、artifact全体scriptは`artifact:<generator>:<scope_key>`
- `model_key`: 技法modelを処理するscriptだけ必須。形式は`<technique-slug>-\d{3,}`。artifact全体scriptでは`null`
- artifact全体scriptは`risk_matrix.py`、`technique_candidates.py`、`change_impact.py`、`environment_requirements.py`、`test_data_requirements.py`、`requirement_structure.py`、`condition_structure.py`、`materialize_coverage.py`、`case_structure.py`、`traceability.py`、`workflow_runtime.py`で固定する
- `scope_key`: artifact全体scriptだけ必須。`^[A-Za-z][A-Za-z0-9._:-]{0,63}$`。model scriptでは`null`
- artifact全体scriptの`scope_key`はscriptごとに固定する
  - `technique_candidates.py`: 入力`selection_key`
  - `materialize_coverage.py`: 入力`tcn_id`
  - その他のartifact全体script: literal `all`
- 同一Skill内で同じ`artifact:<generator>:<scope_key>`を同時に複数定義しない
- `selection_source`: model scriptだけ`analysis / user / existing_artifact / derived`のいずれかを必須。artifact全体scriptでは`null`。`derived`では親runtimeを`upstream_runtime_units[]`へ1件以上必須にする
- `upstream_entities`: 実際に消費した上流Entity単位で保持する。`skill + entity_ref`を一意keyとし、呼び出し側はPlanで固定した項目のcanonicalな`content`を渡す。`content_fingerprint`はruntimeが`content`から計算してenvelopeと成果物へ保存し、LLMからhash値だけを受け取らない
- `upstream_runtime_units`: 他runtime結果を直接利用した場合に必須。`skill + runtime_unit_key + generation_fingerprint`を一意参照として保持する。`runtime_unit_key`単独をSkill横断identityに使わない
- `runtime_contract_version`、`generator_contract_version`、runtime実装hash、generator実装hash、fileから導出できる`static_data_versions`はruntime側を正本とする。入力metadataに同じ値を持たせる場合はruntime実値と一致しなければ`invalid_input`
- `static_data_versions`: keyは`^[a-z][a-z0-9_]*$`、valueは`sha256:<64 lowercase hex>`または明示的なcontract version文字列`^[A-Za-z0-9][A-Za-z0-9._-]*$`
- `authority_refs`: 製品固有expected resultを確定できる現在有効な根拠
- `reference_refs`: 外部標準、一般UI資料、DOM / 実装事実等の補助情報
- script固有入力は必ず`input`配下に置き、metadataと同じkeyを再定義しない
- target / result keyへ文字列として直接埋め込むcomponent keyは`^[A-Za-z][A-Za-z0-9._-]{0,63}$`を共通形式とし、delimiterの`:`を禁止する。任意文字列を含むidentityはcanonical JSONをhashしてkey化する
### 3.3 runtime出力envelope

scriptが実行できた場合、stdoutは次のJSON object 1件だけです。

```json
{
  "envelope_version": "1",
  "skill": "test-condition-design",
  "runtime_contract_version": "runtime-v1",
  "generator_contract_version": "combinatorial-v1",
  "generator": "combinatorial",
  "runtime_unit_key": "model:pairwise-001",
  "model_key": "pairwise-001",
  "input_fingerprint": "sha256:...",
  "model_fingerprint": "sha256:...",
  "generation_fingerprint": "sha256:...",
  "runtime_implementation_fingerprint": "sha256:...",
  "generator_implementation_fingerprint": "sha256:...",
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

output envelopeの`skill`はinput metadataおよびscript所属Skillと一致必須です。

`support_status`は`supported / partial / unsupported / unknown`です。`partial`は同一input内に、独立して機械処理できる範囲と対応subset外の範囲が共存する場合だけ使用します。対応subset外部分は`payload.unsupported_items[]`へstable key、理由、Authorityを保持し、黙って削除しません。`unknown`はsupport判定を完了できなかった場合だけ使用し、`invalid_input / internal_error / not_run`以外では返しません。

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
| `ok` | `partial` | `ready`または`unresolved` | `true` | `true` | supported部分を利用し、unsupported itemはfallbackまたはDispositionへ閉じる |
| `invalid_input` | `unknown` | `blocked` | `true` | `false` | 入力契約違反でsupport判定を完了できない。入力契約を修正 |
| `unsupported` | `unsupported` | `ready` | `false` | `false` | runtime unitとしてfallback可能。QA成果物全体はfallbackが既存Skill契約へ閉じた場合だけ完了可能 |
| `limit_exceeded` | `supported`または`partial` | `blocked` | `true` | `false` | model分割またはcontract変更が必要 |
| `internal_error` | `unknown` | `blocked` | `true` | `false` | support判定完了前後を問わず安全側でruntime requiredとして扱い、runtime不具合を修正 |
| `not_run` | `unknown` | `blocked` | `true` | `false` | Python unavailable。成果物metadataだけで表現 |

`stale`は`result_status`ではありません。成果物保存時の`freshness_status = current / stale`として`qa-workflow`がfingerprint比較から付与します。

`fallback_reason`は`null / outside_supported_subset / python_unavailable`だけを許可します。`runtime_status=unsupported`では`outside_supported_subset`、`runtime_status=not_run`では`python_unavailable`です。`runtime_status=not_run`では`input_fingerprint / model_fingerprint / generation_fingerprint`を`null`とし、決定論的再利用の証拠に使いません。`support_status=partial`のunsupported itemはitem単位でfallbackまたはDispositionへ閉じ、その閉鎖情報を成果物へ保存します。

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
- runtimeが生成したissueでは`generation_fingerprint`を必須にし、そのissueがどのruntime世代に対するものかを固定する。subprocess timeout等でgenerationを確定できないcaller生成issueだけ`generation_fingerprint=null`を許可する
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
- 順序に意味がないkey付きrecord配列は指定primary keyでcanonical sortする。`upstream_entities`は`(skill, entity_ref)`、`upstream_runtime_units`は`(skill, runtime_unit_key)`、`previous_*`は各ID、`target_annotations / target_dispositions`は`target_ref`、`merge_groups`は`merge_group_key`でsortする
- assignment objectのkeyはsort
- decimal / date / datetimeは共通表現へ正規化
- JSON serializationはUTF-8、`ensure_ascii=false`相当、separatorは`,`と`:`、末尾改行なし
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
- `upstream_entity_fingerprints`: 実際に消費した`upstream_entities[]`を`(skill, entity_ref)`でsortした`{skill, entity_ref, content_fingerprint}`配列
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

### 4.3 model_keyの安定性

技法slugは次で固定します。

| 技法 / model | slug |
| --- | --- |
| 同値分割 | `ep` |
| 境界値分析 | `bva` |
| Domain Testing | `domain` |
| Decision Table | `decision` |
| Pairwise / 組合せ | `comb` |
| Classification Tree | `classification` |
| 状態遷移 | `state` |
| シナリオ / Use Case | `flow` |
| CRUD Testing | `crud` |
| Cause-Effect Graph | `cause-effect` |
| Syntax-Based Testing | `syntax` |
| schema / HTML constraint | `schema` |
| UI pattern | `ui` |
| Random Testing | `random` |
| Metamorphic Testing | `metamorphic` |

`model_key`は`<slug>-\d{3,}`です。

- qa-workflowが再利用元として選んだ直前の`test-condition-design`成果物を同じ成果物系列とする。再利用元がない場合は新しい系列
- 同じ技法・同じ検証責務のmodelを改訂する場合は既存`model_key`を維持する
- 意味上別modelと判断した場合だけ、同じslugの既存最大番号+1で新しいkeyを発行する
- 新しい系列では各slugを001から開始する
- 削除済みkeyは同じ系列で再利用しない
- 同じ`(技法, model_key)`に異なる同時定義を置かない

意味上同じmodelかどうかの判断はLLMに残し、番号割当てだけを機械規則として固定します。

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
      "entity_ref":"TR-001",
      "model_key":null,
      "content":{...},
      "upstream_entity_dependencies":[
        {
          "skill":"spec-analysis",
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
- `test-analysis`はLLMが作るProduct Risk等の意味fieldとruntime resultを固定builderでjoinして保存する。例えばProduct Riskは`failure / authority_refs / impact / likelihood`と`risk_matrix.py`の`level / mapped_priority`をjoinする
- `test-requirement-design` / `test-condition-design` / `test-case-design`はstructure scriptへ渡した意味fieldとruntimeが確定したID・優先度等を固定builderでjoinして保存する
- Markdownの人間向け表はMachine Entityと同じ意味fieldを表示し、validatorでID・参照・優先度・期待結果等の一致を確認する。Machine Entityにない意味fieldをMarkdownだけへ追加して下流正本にしない
- `content`は意味上のEntity本体、`upstream_entity_dependencies[] / runtime_dependencies[]`はfreshness用の機械metadataであり`content_fingerprint`へ含めない
- `upstream_entity_dependencies[]`はその意味判断を行った時点で実際に参照した上流Entityの`skill / entity_ref / content_fingerprint`を保存する。上流内容が変わった場合は、同じEntity IDでも意味判断を再確認するまでこのEntityを`stale`とする
- `runtime_dependencies[]`はそのEntityの現在状態を成立させるruntime unitだけを列挙する。Authority等、上流もruntimeも持たないsource Entityでは両配列を空にできる
- 複数用途SkillでMachine Entityを保存する場合は既存`対象 / 実行範囲`をblock metadataへ保持し、本Planでruntime対象となる`test-analysis: テスト分析`と他用途を混在させない

`spec-analysis`のAuthority Entityでは次の項目をcanonical化します。

`spec-analysis`のAuthority Entityでは次の項目をcanonical化します。

- 仕様根拠ID
- 種別
- 現在有効な内容
- 適用範囲
- 情報源 / 正本一覧
- 関係
- 関連仕様根拠ID

以降のQA成果物は、下流が実際に利用するEntity単位でfingerprint対象項目を固定します。

- `test-analysis` Product Risk: リスクID、失敗、関連根拠、影響度、発生可能性、level、mapped priority
- `test-analysis` 技法選択: selection key、適用領域、selection source、signals、候補、最終採用技法、状態
- `test-analysis` change graph: node / edge key、type、from / to、Source / Authority
- `test-analysis` 環境要求: requirement key、operator、value / range、Authority
- `test-requirement-design`: TR ID、本文、Authority、Risk、優先度、テストレベル / 観測方法、およびDisposition行
- `test-condition-design`: TCN ID、TR、条件、技法、Coverage基準、Authority / Risk、優先度、model metadata、target → CI mapping、およびDisposition行
- `test-case-design`: TC ID、関連TR / TCN / CI、優先度、前提、データ、手順、期待結果、期待結果Authority、およびDisposition行
- `coverage-analysis`: 対象上流 / 下流ID、Model Key、coverage / stale状態、修正Skill

fingerprint対象の`content`はLLMが自由に再構成しません。各担当Skillが保存するmachine dataから次のcanonical schemaで機械的に組み立てます。

- Authority: `{authority_id, authority_type, active_content, scope, source_refs[], relations[], related_authority_refs[]}`
- Product Risk: `{risk_id, failure, authority_refs[], impact, likelihood, level, mapped_priority}`
- 技法選択: `{selection_key, applicability_scope, selection_source, signals, candidates[], selected_techniques[], status}`
- change graph node / edge: `{node_key, node_type, source_ref}` / `{edge_key, from, to, edge_type, evidence_refs[]}`
- 環境 / test data要求: `{requirement_key, dimension_key, operator, normalized_value, authority_refs[], source_target_refs[]}`
- TR: `{tr_id, text, authority_refs[], risk_refs[], priority, test_level, observation_method}`
- TCN: `{tcn_id, tr_refs[], condition, category, technique, coverage_criterion, authority_refs[], risk_refs[], priority}`
- model metadata: `{model_key, technique_slug, parent_tcn_id, selection_source}`
- CI mapping: `{target_ref, model_key, target_key, ci_id, status}`
- TC: `{tc_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], priority, preconditions, test_data, steps, expected_results[], postconditions_or_cleanup}`
- Disposition: `{upstream_id, handling, reason, authority_refs[], covered_by_ref}`

machine dataに存在しない表示専用の備考やMarkdown整形は`content`へ入れません。Machine Entity schemaの意味変更は`entity-state-v1`のversion変更として扱い、そのschemaを消費するruntime contractも更新します。

modelは実際に消費したEntityを`upstream_entities`へ1件ずつ保持し、runtimeがcanonical `content`から`content_fingerprint`を計算します。`skill + entity_ref`が同じEntityの`content_fingerprint`だけを比較し、不一致となったEntityを参照するmodelだけを`要再検証`へ戻します。無関係なEntity変更ではmodelをstaleにしません。

他runtime結果を直接利用したunitは`upstream_runtime_units`も`(skill, runtime_unit_key)`で比較します。保存した`generation_fingerprint`と現在の上流runtime unitが一致しなければ下流unitをstaleとし、その下流へも依存関係に従って伝播します。参照先が存在しない場合はstale + blocker、同じ`(skill, runtime_unit_key)`が重複する場合またはruntime dependency graphにcycleがある場合は`invalid_input`です。LLMはこのfingerprint比較を手計算しません。
## 5. 値・順序・tie-break

### 5.1 typed value

対応型:

- integer
- boolean
- string / enum
- decimal
- null
- date
- local datetime
- fixed-offset datetime

nullable factorは「1つのnon-null base type + null」を許可します。Pythonの`True == 1`等に依存せず、型を含むcanonical表現で比較します。

named timezone / DST transition自体を一般BVAとして推測しません。明示されたtimezone ruleを扱う技法modelがある場合だけ処理します。

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

qa-workflowが再利用元として選んだ同種成果物を同じ系列とし、新規項目だけその成果物内の最大番号+1で採番します。再利用元がない新規成果物では001から開始し、削除済みIDを同じ系列で再利用しません。1つの`model_key`は同時に1つのTCNだけへ所属し、別TCNで同じmodelを再利用する場合は意味上別modelとして別`model_key`を発行します。

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

削除済みIDを将来再利用しないため、各成果物へactive / deleted状態をmachine dataとして保存します。

- TR: `{tr_id, status}`
- TCN: `{tcn_id, status}`
- model: `{model_key, technique_slug, parent_tcn_id, status}`
- TC: `{tc_id, status}`
- CI: `{ci_id, status}`

`status=active|deleted`です。structure / materialize scriptの`previous_*`入力はこのmachine stateからだけ構築し、人間向け表から削除済みIDを推測しません。削除されたID rowも同じ成果物系列のmachine stateには残します。

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

generatorが返した各`target_ref`は、最終的に次のどちらか一方へ閉じます。

- `materialize_coverage.py`でCIへ割り当てる。複数targetを同じCIへ割り当てる場合は§11の`merge_group`を必須にする
- `target_dispositions[]`で既存`test-condition-design`契約上の扱いへ明示する

`target_dispositions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint, handling, reason, authority_refs, covered_by_target_ref}`です。`target_content_fingerprint`と`generation_fingerprint`は現在machine target / modelと一致必須で、過去targetまたは過去generationに対するDispositionを現在世代へ流用しません。

- `handling=対象外 / 別テストレベル / 残存リスク / ブロック中 / 重複`だけを許可する
- `重複`では`covered_by_target_ref`を必須にし、同一TCN内のcurrentかつCIへmaterializeされるtargetを参照する。他handlingでは`covered_by_target_ref=null`
- generatorが成立可能targetとして生成した後に`成立不能`へ変更しない。新しいAuthorityで成立不能と判明した場合は正規化model / constraintを更新してgeneratorを再実行し、Coverage母集団から機械的に除外する
- 同一target_refへCI mappingとDispositionを同時に持たせない
- `ブロック中`はworkflow完了を妨げる。`対象外 / 別テストレベル / 残存リスク / 重複`は既存Skill契約上の根拠条件を満たせば成果物上は閉鎖できる

Dispositionはgeneratorの`coverage_summary`を書き換えません。技法内Coverageは正規化modelとgenerator結果を正本とし、成果物上の未実施・別レベル・残存リスク等は`coverage-analysis`で別に追跡します。これにより、DispositionしたtargetをCoverage済みと誤計上しません。

## 8. machine evidenceとMarkdown

### 8.1 正規化済みモデル

`test-condition-design`を中心に、scriptへ再投入できる正規化済みJSONを成果物へ保持します。

一覧表:

`Runtime Unit Key | モデルキー | 観点ID | 技法 | runtime contract version | generator contract version | input fingerprint | model fingerprint | generation fingerprint | upstream entity count | static data versions | runtime status | result status | runtime required | freshness | deterministic generated | fallback reason`

全runtime unitについてcanonicalな実行入力と実行結果を成果物へ保存します。

````markdown
### Machine Runtime Input: test-condition-design::model:pairwise-001

```json
{"metadata":{...},"input":{...}}
```

### Machine Runtime Result: test-condition-design::model:pairwise-001

```json
{"runtime_unit_key":"model:pairwise-001",...}
```
````

見出しidentityは`<skill>::<runtime_unit_key>`で、JSON内metadataのSkill所属と`runtime_unit_key`が一致しなければvalidatorを失敗させます。model scriptでは`Machine Runtime Input.input`が正規化modelの正本です。必要なら`Machine Model: <model_key>`表示をruntimeから派生描画できますが、LLMが別JSONを作らず、canonical `input` subtreeと一致を必須にします。artifact全体scriptも同じ形式で入力を保存するため、validatorは全scriptの`input_fingerprint`を保存済み入力から再計算できます。

人間向け説明文はLLMが生成して構いません。machine evidenceのJSON、key、ID対応、Coverage値をLLMが再計算・改変しません。runtime blockのJSON抽出もLLMへ委ねず、`runtime_contract.py`の抽出処理を使用します。

§4.4の`Machine Entities` blockはruntime evidenceとは別の意味上の正本です。`spec-analysis`を含む各担当Skillのvalidatorはstrict JSON decode、schema、entity_ref一意性、人間向け表との主要field一致を確認します。既存成果物を再利用するときはこのblockから現在のcanonical Entityを取得し、runtime対象unitの入力を組み立て直します。保存済み`Machine Runtime Result`を現在世代のresultとしてそのまま採用しません。

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

`test-analysis`の技法選択用signalを機械証拠として保存します。

`選択キー | 適用領域 | Selection Source | Signals JSON | Candidates JSON | Undetermined Signals JSON | 最終採用技法 | 状態`

`Selection Source`は`analysis / user / existing_artifact / derived`のいずれかです。技法modelのmetadataにも`selection_source`を必須で保存します。`test-analysis`を通った場合はその選択行からコピーし、途中工程開始でユーザーが技法を明示した場合は`user`、再利用した既存modelは`existing_artifact`、親runtimeのmachine outputから派生したmodelは`derived`とします。

- `true / false / null`を区別
- `technique_candidates.py`の`complete`は`undetermined_signals`が空かだけを表す診断値であり、`complete=false`だけを理由にworkflowをブロックしない。ただし各undetermined signalは`test-analysis`成果物で`resolved / selection_not_affected / question`のいずれかへ閉じ、未閉鎖signalが残る状態をworkflow完了にしない
- ユーザー明示または有効な既存成果物由来の技法をcandidate scriptが勝手に却下しない
- 選択した技法は`test-condition-design`のmodel、対象外、未解決、または`runtime_required=false`の対応subset外fallbackへ必ず閉じる
- 選択技法だけ存在しmodel化されない状態を完了扱いしない
- 新しい正規技法名を追加した場合はsignal / validator / semantic evalも同時に更新する

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

次の変換でLLMによるJSON再生成を挟みません。

- Cause-Effect → Decision Table
- Classification Tree normalized classifications / classes → `classification_tree.py` → combinatorial
- schema / HTML constraints → EP / BVA / test data requirement
- Domain / CRUD / state / flow等のgenerator → machine evidence
- Coverage target → CI mapping

機械接続は次で固定し、未定義の汎用adapterは作りません。

- `cause_effect.py`の`derived.decision_table`は`conditions / actions / known_rules / constraints / accepted_merges=[]`を必ず持ち、`decision_table.py`のscript固有`input`と完全互換にする
- `classification_tree.py`は`derived.combinatorial_input`へ`factors / constraints`を出力する。LLMは`mode / strength / mixed-strength subsets`だけを意味判断として追加し、factor / class / constraintを再生成しない。最終inputは固定builderが機械的にjoinする
- `schema_cases.py`は`derived.ep_inputs / derived.bva_boundary_skeletons / derived.combinatorial_constraints / derived.test_data_requirements`を固定schemaで返す。BVAはschemaから`boundary / threshold / side / inclusive / step`までを機械生成し、`mode / coverage_selection_reason`はLLMが意味判断として追加して固定builderが`bva.py`入力を作る。EP / combinatorial / test dataも固定builder以外でmachine fieldを再生成しない
- 各generatorのmachine targetと、LLMがtarget_ref単位で付与した`target_annotations[]`を`materialize_coverage.py`がjoinする。generator target JSONをLLMが再生成しない

意味上の判断だけLLMに残します。CIへmaterializeするtargetの意味情報は`target_annotations[]`へ`{target_ref, target_content_fingerprint, generation_fingerprint, priority, expected_result_root, test_data_requirement_refs[]}`として保持します。`target_content_fingerprint`と`generation_fingerprint`は現在machine target / modelと一致必須で、target内容または上流Entity内容・runtime generationが変わった場合はLLMが意味判断を再確認して現在値でannotationを更新するまでmaterializeしません。Disposition済みtargetにはannotationを要求せず、同一targetへannotationとDispositionを同時指定しません。`expected_result_root`は期待結果本文ではなく、同じ期待挙動へまとめてよいかをLLMが判定したstable keyです。

同じ実行で複数Coverage targetを満たせる場合だけLLMは`merge_group`を明示できます。runtime-v1ではmerge対象を**同じ`model_key`かつ同じ`execution_fingerprint`**へ限定します。異なる技法 / modelのCoverage ItemはCIを分けたまま保持し、同じ詳細TCで実行できる場合は`test-case-design`で1つのTC draftから複数`ci_refs[]`を参照します。これによりCI統合のためだけに技法間の汎用互換adapterを追加しません。

`merge_group` inputは`{"merge_group_key":"MG-001","model_key":"pairwise-001","target_refs":["sha256:...","sha256:..."],"target_versions":[{"target_ref":"sha256:...","target_content_fingerprint":"sha256:...","generation_fingerprint":"sha256:...","execution_fingerprint":"sha256:..."}],"authority_refs":["SPEC-001"]}`です。`target_versions[]`は全`target_refs[]`へ1対1対応し、現在machine target / modelと一致必須です。target refは2件以上、重複不可、同一TCN・同一`model_key`だけを許可し、全targetの`execution_fingerprint`が一致しなければ`invalid_input`とします。各targetの`target_annotations.expected_result_root`も一致必須です。各targetが参照する追加test data requirementは`_03` §16と同じintersection規則で機械統合し、矛盾またはunsupportedな組合せならmergeを拒否します。`test_data_requirement_refs[]`は`data:<requirement_key>`形式で、同一materialize入力の正規化済みtest data requirementに存在することを必須にします。

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
- `Support Status=partial`のunitは`unsupported_items[]`がすべてfallbackまたはDispositionへ閉じていることを完了条件にする
- model issueを`question-analysis`へroutingする場合は`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問一覧・ブロック中範囲・回答後の再開情報へ保持する
- artifact全体scriptのissueも`skill / runtime_unit_key / generation_fingerprint`をBlocker / Issueへ保持し、model keyを捏造しない
- `coverage-analysis`はstale / gapをTCN / CIだけでなく関連`model_key`まで追跡する

Machine Entityのfreshnessは`runtime_contract.py`の共通関数で計算します。各Machine Entityの`runtime_dependencies[]`と現在runtime unitのgenerationを比較し、次のschemaへ正規化します。

```json
{
  "skill":"test-case-design",
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

strict JSON、canonicalization、fingerprint、envelope処理はruntime対象6 Skillそれぞれの`scripts/runtime_contract.py`へ同じ実装を同梱します。repo rootの共通helperへ依存させません。`runtime_contract_version`をfile内定数として持ち、意味契約を変更した場合にversionを更新します。repository testでは改行をLFへ正規化した内容のSHA-256一致を検証し、Skillごとの実装差を許可しません。実装内容の変更は同じLF正規化規則で`runtime_implementation_fingerprint`へ反映します。技法固有ロジックはこの共通helperへ入れません。

本Planのruntime dependencyはPython 3.11標準ライブラリだけに固定します。外部PyPI package、外部binary、network serviceをruntime依存へ追加しません。

Planで定義した正確性、hard limit、30秒のCLI test timeoutを標準ライブラリ実装で満たせない場合は、その実装をPlan未達として停止し、暗黙にCoverage基準を下げたり依存関係を変更したりしません。将来用adapterも作りません。
