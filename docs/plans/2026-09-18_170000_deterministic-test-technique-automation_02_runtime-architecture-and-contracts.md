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
2. script選択表から1つのruntime scriptを選ぶ。script pathを自由文から推測しない
3. 保存済みMachine Modelを再利用する場合は`runtime_contract.py`が対象見出し直下のJSON fenceを抽出し、strict decode、model key一致、fingerprint一致を確認する。LLMがMarkdownからJSONを再生成しない
4. stdinへ共通metadataとscript固有inputを渡してscriptを起動する
5. stdout envelopeをstrict decodeし、return code、runtime status、issuesを合わせてroutingする
6. 意味判断が必要なissueは既存Skillまたは`question-analysis`へ戻し、機械結果をLLMが再計算しない
7. 意味入力を更新した場合はruntimeを再実行し、保存machine evidenceを置換する

各scriptは入力検証の一部として対応subset判定を行い、`runtime_required`を出力として決定します。`runtime_required`はruntime入力へ渡さず、Agentが自然言語だけから`runtime_required=false`を確定してscriptを省略しません。

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

### 3.1 strict JSON

すべてのruntime scriptはstrict JSONを使用します。

- duplicate object keyを拒否する
- `NaN`、`Infinity`、`-Infinity`を拒否する
- top-level typeをscriptごとに固定する
- UTF-8で解釈する
- decimalはJSON numberへ丸めず、`{"type":"decimal","value":"0.1"}`のような10進文字列で扱う
- date / datetimeは契約で許可したISO 8601形式以外を拒否する

Python実装では、duplicate key検出用`object_pairs_hook`、非有限数拒否、`allow_nan=False`相当の出力を共通方針とします。

### 3.2 共通入力metadata

runtime入力は`metadata`とscript固有`input`を分けます。

```json
{
  "metadata": {
    "envelope_version": "1",
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
- `selection_source`: model scriptだけ`analysis / user / existing_artifact`のいずれかを必須。artifact全体scriptでは`null`
- `upstream_entities`: 実際に消費した上流Entity単位で保持する。`skill + entity_ref`を一意keyとし、呼び出し側はPlanで固定した字段のcanonicalな`content`を渡す。`content_fingerprint`はruntimeが`content`から計算してenvelopeと成果物へ保存し、LLMからhash値だけを受け取らない
- `upstream_runtime_units`: 他runtime結果を直接利用した場合に必須。直接利用した`runtime_unit_key + generation_fingerprint`を保持し、上流runtime結果が変わったときに依存unitだけをstaleへ戻せるようにする
- `runtime_contract_version`、`generator_contract_version`、runtime実装hash、generator実装hash、fileから導出できる`static_data_versions`はruntime側を正本とする。入力metadataに同じ値を持たせる場合はruntime実値と一致しなければ`invalid_input`
- `static_data_versions`: keyは`^[a-z][a-z0-9_]*$`、valueは`sha256:<64 lowercase hex>`または明示的なcontract version文字列`^[A-Za-z0-9][A-Za-z0-9._-]*$`
- `authority_refs`: 製品固有expected resultを確定できる現在有効な根拠
- `reference_refs`: 外部標準、一般UI資料、DOM / 実装事実等の補助情報
- script固有入力は必ず`input`配下に置き、metadataと同じkeyを再定義しない
### 3.3 runtime出力envelope

scriptが実行できた場合、stdoutは次のJSON object 1件だけです。

```json
{
  "envelope_version": "1",
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

`support_status`は`supported / partial / unsupported`です。`partial`は同一input内に、独立して機械処理できる範囲と対応subset外の範囲が共存する場合だけ使用します。対応subset外部分は`payload.unsupported_items[]`へstable key、理由、Authorityを保持し、黙って削除しません。

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
| `invalid_input` | 任意 | `blocked` | support判定結果 | `false` | 入力契約を修正 |
| `unsupported` | `unsupported` | `ready` | `false` | `false` | runtime unitとしてfallback可能。QA成果物全体はfallbackが既存Skill契約へ閉じた場合だけ完了可能 |
| `limit_exceeded` | `supported`または`partial` | `blocked` | `true` | `false` | model分割またはcontract変更が必要 |
| `internal_error` | 任意 | `blocked` | support判定結果 | `false` | runtime不具合として扱う |
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
  "runtime_unit_key": "model:decision-001",
  "model_key": "decision-001",
  "target_key": "R4",
  "authority_refs": ["SPEC-001"],
  "required_information": "条件組合せに対する期待action",
  "route_to": "question-analysis",
  "resume_skill": "test-condition-design"
}
```

- `issue_type`、`blocking`、`runtime_unit_key`は必須
- model scriptでは`model_key`必須、artifact scriptでは`model_key=null`
- target固有issueだけ`target_key`必須
- `route_to` / `resume_skill`は既存Skill名だけを許可
- `question-analysis`へ送る場合はRuntime Unit / Model / Targetを質問・ブロック・回答後の再開まで保持する
- 自由文stderrをrouting入力に使わない

## 4. canonicalization・version・fingerprint

### 4.1 canonical input・model・generation fingerprint

fingerprintはSHA-256で計算します。入力はUTF-8のcanonical JSONです。

- object keyはUnicode code point順
- `authority_refs` / `reference_refs`等の集合扱い配列は重複除去してsort
- factor、condition、action、state、transition、edge、production等、tie-breakや意味に入力順を使う配列は宣言順を保持
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

- `runtime_unit_key`
- script固有`input`
- `authority_refs`
- `reference_refs`
- model scriptでは`selection_source`

`upstream_entities`はstale判定用、`static_data_versions`はgeneration条件用なので`input_fingerprint`へ含めません。

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
- `static_data_versions`

`runtime_implementation_fingerprint`は実行した`runtime_contract.py`のUTF-8 file bytes、`generator_implementation_fingerprint`は実行scriptのUTF-8 file bytesをSHA-256した値です。runtime自身が計算し、呼び出し側の申告値を正本にしません。

したがって、同じartifact scriptでも入力・Authority / Reference・runtime contract・generator contract・実装内容・静的参照データのいずれかが変われば`generation_fingerprint`は変わります。

`runtime_contract_version` / `generator_contract_version`は意味契約変更時に更新します。bug fixや内部refactorで意味契約を変えない場合も実装fingerprintが変わるため旧machine evidenceを同一生成条件として再利用しません。探索順、tie-break、Coverage、target key等の契約自体を変える場合は実装fingerprintだけで済ませず対応contract versionも更新します。

generatorが返すtarget集合とCoverage計算は純粋な決定論処理です。target → CI ID等のID維持はstateful materialize処理であり、同じgenerator結果と同じ`previous_target_id_map`から同じmappingを得ることを保証します。
### 4.2 静的参照データ

generator結果に影響する静的データはversionを持ちます。

- `ui-pattern-catalog.json`: file content SHA-256
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

同じIDでも上流Entityの構造化内容は変わり得るため、自由記述versionやMarkdown全文hashではなく、実際に消費したEntityのcanonicalな構造化内容から`content_fingerprint`を計算します。これは意味同値性を推論するhashではなく、正規字段の変更検出用です。

`spec-analysis`のAuthority Entityでは次の字段をcanonical化します。

- 仕様根拠ID
- 種別
- 現在有効な内容
- 適用範囲
- 情報源 / 正本一覧
- 関係
- 関連仕様根拠ID

以降のQA成果物は、下流が実際に利用するEntity単位でfingerprint対象字段を固定します。

- `test-analysis` Product Risk: リスクID、失敗、関連根拠、影響度、発生可能性、level、mapped priority
- `test-analysis` 技法選択: selection key、適用領域、selection source、signals、候補、最終採用技法、状態
- `test-analysis` change graph: node / edge key、type、from / to、Source / Authority
- `test-analysis` 環境要求: requirement key、operator、value / range、Authority
- `test-requirement-design`: TR ID、本文、Authority、Risk、優先度、テストレベル / 観測方法、およびDisposition行
- `test-condition-design`: TCN ID、TR、条件、技法、Coverage基準、Authority / Risk、優先度、model metadata、target → CI mapping、およびDisposition行
- `test-case-design`: TC ID、関連TR / TCN / CI、優先度、前提、データ、手順、期待結果、期待結果Authority、およびDisposition行
- `coverage-analysis`: 対象上流 / 下流ID、Model Key、coverage / stale状態、修正Skill

modelは実際に消費したEntityを`upstream_entities`へ1件ずつ保持し、runtimeがcanonical `content`から`content_fingerprint`を計算します。`skill + entity_ref`が同じEntityの`content_fingerprint`だけを比較し、不一致となったEntityを参照するmodelだけを`要再検証`へ戻します。無関係なEntity変更ではmodelをstaleにしません。

他runtime結果を直接利用したunitは`upstream_runtime_units`も比較します。保存した`generation_fingerprint`と現在の上流runtime unitが一致しなければ下流unitをstaleとし、その下流へも依存関係に従って伝播します。LLMはこのfingerprint比較を手計算しません。
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
- feasibility search node: root assignmentを1とし、backtrackingで新しいpartial assignmentへ入るたびに1加算する。cache hitで再探索しない場合は加算しない
- target / row / candidate総数: stable keyによる重複除去後、Markdown materialize前に数える
- stdout JSON: UTF-8 serialization後のbytesを数える

次を契約値として固定します。

| 対象 | 上限 |
| --- | ---: |
| 入力JSON | 2 MiB |
| JSON / schema / ASTのnesting depth | 64 |
| 1文字列 | 64 KiB |
| Decision Table / Cause-Effectのassignment | 65,536 |
| Pairwise / N-wise / mixed-strengthのCoverage target | 100,000 |
| feasibility search node | 1,000,000 |
| 生成row / test data candidate / Domain point | 10,000 |
| state sequence / flow path | 10,000 |
| grammar生成case | 10,000 |
| Random Testing生成case | 10,000 |
| 1 modelのtarget / row / candidate総数 | 100,000 |
| stdout JSON | 16 MiB |

上限を超えた場合は`limit_exceeded`とし、Coverage基準、strength、path深度等を自動で下げません。item数が上限内でもbyte / depth上限を超える入力・出力は処理しません。上限変更は実装者判断ではなくgenerator contract変更としてPlanを更新します。16 MiBはruntime engineのstdout上限であり、Agentが同量を安全に成果物へ統合できることを意味しません。Step 1の代表smokeで実Agentのstdout取得・strict decode・成果物保存を境界付近まで確認し、16 MiB未満の実用上限が必要ならgenerator実装へ進む前に`runtime-v1`のartifact transport上限としてPlanへ固定します。上限超過時にtruncateや要約でmachine evidenceを欠落させず`limit_exceeded`とします。

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
- hashが同じなのにmodel_key / target_keyが異なる場合は`internal_error`

`materialize_coverage.py`のinputには`previous_target_id_map[]`を明示的に渡します。

```json
[
  {
    "target_ref":"sha256:...",
    "model_key":"bva-001",
    "target_key":"bva:age-lower:AT",
    "ci_id":"TCN-001-CI01"
  }
]
```

- 初回mappingがない場合、同一TCN内のtargetを`model_key`、次に`target_key`のUnicode code point辞書順でsortし、`CI01`から順に採番する
- 既存mappingがある場合、同じ`target_ref`は既存CI IDを維持する
- 新しい`target_ref`は同一TCN内の既存CI最大番号+1から採番する
- 消滅target_refのCIはstaleとし、下流TCを`要再検証`へする
- 削除済みCI番号を再利用せず、既存CI番号の詰め直しを行わない
- previous mappingの`target_ref`をmodel_key / target_keyから再計算し、不一致を拒否する
- 同一`target_ref`が複数CIへ割り当てられる場合、親TCN不一致、merge group外で同一CIへ複数target_refが割り当てられる場合は`invalid_input`
- 同一CIへ複数target_refを割り当てるのは、同一`merge_group`で明示されたtargetだけ許可する。mappingはtarget_refごとに1行保持し、同じ`ci_id`を共有できる
- mergeを解除した場合は、既存CIを辞書順で最初の存続targetへ維持し、残りtargetへ既存CI最大番号+1から新規採番する。旧merge CIの意味が変わるため関連下流TCを`要再検証`へする
- merge targetがすべて消滅した場合だけ旧CIをstaleにする

CI番号は`CI\d{2,}`を許可します。
### 7.3 upsert

再実行はappendではなくstable keyでupsertします。

- 同じ`target_ref`は置換
- 生成されなくなった派生行はstaleとして除去候補にする
- 同一再実行で重複machine evidenceを作らない
- staleな派生成果物が残る状態を完了扱いしない

### 7.4 Coverage targetの成果物上の閉鎖

generatorが返した各`target_ref`は、最終的に次のどちらか一方へ閉じます。

- `materialize_coverage.py`でCIへ割り当てる。複数targetを同じCIへ割り当てる場合は§11の`merge_group`を必須にする
- `target_dispositions[]`で既存`test-condition-design`契約上の扱いへ明示する

`target_dispositions[]`は`{target_ref, handling, reason, authority_refs, covered_by_target_ref}`です。

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

正規化入力JSONはMarkdown table cellへ埋め込まず、次の形式で保存します。

````markdown
### Machine Model: pairwise-001

```json
{...}
```
````

見出しの`model_key`とJSON内metadataの`model_key`が一致しない場合はvalidatorを失敗させます。

人間向け説明文はLLMが生成して構いません。machine evidenceのJSON、key、ID対応、Coverage値をLLMが再計算・改変しません。再利用時のJSON抽出もLLMへ委ねず、`runtime_contract.py`の抽出処理を使用します。

### 8.2 machine evidenceの描画

共通のJSON fence出力、Markdown escape、runtime metadata行の描画は各Skill同梱の`scripts/runtime_contract.py`が担当します。Coverage target → CI materialize、merge group統合、Coverage Item表のmachine row生成は`test-condition-design/scripts/materialize_coverage.py`が担当します。

validatorはfenced JSON blockを抽出してstrict JSON decodeし、canonical化したmodel / fingerprint / machine evidenceが一致することを確認します。

必須round-trip test:

1. canonical modelをMarkdownへ保存
2. `### Machine Model: <model_key>`直下のJSON fenceを抽出
3. strict JSON decode
4. canonical化
5. 元の`model_fingerprint`と一致
6. 抽出したJSONを同じruntime scriptへ再投入し、同一contract / implementation / static data条件なら同じmachine resultを得る

これにより`|`、backslash、改行を含む値をMarkdown table escapeへ依存させません。

## 9. 技法選択とmodelの閉鎖

`test-analysis`の技法選択用signalを機械証拠として保存します。

`選択キー | 適用領域 | Selection Source | Signals JSON | Candidates JSON | Undetermined Signals JSON | 最終採用技法 | 状態`

`Selection Source`は`analysis / user / existing_artifact`のいずれかです。技法modelのmetadataにも`selection_source`を必須で保存します。`test-analysis`を通った場合はその選択行からコピーし、途中工程開始でユーザーが技法を明示した場合は`user`、再利用した既存modelは`existing_artifact`とします。

- `true / false / null`を区別
- `technique_candidates.py`の`complete`は`undetermined_signals`が空かだけを表す診断値であり、`complete=false`だけを理由にworkflowをブロックしない
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
- `schema_cases.py`は`derived.ep_inputs / derived.bva_inputs / derived.combinatorial_constraints / derived.test_data_requirements`を固定schemaで返し、同script内のbuilder処理で各下流script入力へ変換する。別の汎用adapterは作らない
- 各generatorのmachine targetと、LLMがtarget_ref単位で付与した`target_annotations[]`を`materialize_coverage.py`がjoinする。generator target JSONをLLMが再生成しない

意味上の統合だけLLMに残します。CIへmaterializeするtargetの意味情報は`target_annotations[]`へ`{target_ref, priority, expected_result_root, test_data_requirement_refs[]}`として保持します。Disposition済みtargetにはannotationを要求せず、同一targetへannotationとDispositionを同時指定しません。`expected_result_root`は期待結果本文ではなく、同じ期待挙動へまとめてよいかをLLMが判定したstable keyです。複数技法の結果を同じCIへまとめる場合、LLMは`merge_group`を明示し、`materialize_coverage.py`がtarget key、Authority、Reference、優先度、test data requirement参照を決定論的にunionします。

`merge_group` inputは`{"merge_group_key":"MG-001","target_refs":["sha256:...","sha256:..."],"authority_refs":["SPEC-001"]}`です。target refは2件以上、重複不可、同一TCN配下だけを許可します。各targetの`target_annotations.expected_result_root`が一致しない場合は`invalid_input`とします。

## 12. runtime自己検査の処理順

`test-requirement-design`と`test-case-design`では、既存evalのruntime複製で終わらせません。

1. LLMがdraftを作成
2. runtime structure scriptを実行
3. gap / unknown / priority結果を受け取る
4. 意味判断が不要な局所修正は機械結果に合わせる
5. 意味判断が必要なら担当Skillまたは`question-analysis`へ戻す
6. runtime scriptを再実行
7. unresolvedな構造違反がない状態で成果物を確定

## 13. qa-workflow統合

### 13.1 再利用

既存成果物の再利用条件へ次を追加します。

- `runtime_required=true`の新契約成果物はenvelope / runtime / generator contract versionとupstream Entity content fingerprintが現在有効
- `runtime_required=true`ではinput / model / generation fingerprintと派生成果物が一致
- `runtime_required=false`のfallback成果物はfingerprintを決定論的再利用条件に使わず、既存Skill契約と上流Authorityの有効性で再利用可否を判断する
- stale / `要再検証` / unresolvedなmodelが残っていない
- runtime実行対象なのに決定論的generator未実行である場合、その事実を保持する

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
- model issueを`question-analysis`へroutingする場合は`model_key / target_key`を質問一覧・ブロック中範囲・回答後の再開情報へ保持する
- artifact全体scriptのissueは`runtime_unit_key`をBlocker / Issueへ保持し、model keyを捏造しない
- `coverage-analysis`はstale / gapをTCN / CIだけでなく関連`model_key`まで追跡する
### 13.4 上流変更

上流Entityの`content_fingerprint`または直接依存する上流runtime unitの`generation_fingerprint`が変わった場合:

1. 最も早い変更成果物を特定
2. change impact / traceabilityで影響modelを特定
3. 影響modelとその派生成果物だけを`要再検証`
4. 正規化modelを更新
5. generator再実行
6. 下流structure / Coverageを再検査
7. staleが消えた範囲だけ再利用可能に戻す

## 14. 移植性と依存関係

各Skillは単体コピー可能な既存契約を維持します。

strict JSON、canonicalization、fingerprint、envelope処理はruntime対象6 Skillそれぞれの`scripts/runtime_contract.py`へ同じ実装を同梱します。repo rootの共通helperへ依存させません。`runtime_contract_version`をfile内定数として持ち、意味契約を変更した場合にversionを更新します。repository testで6ファイルのSHA-256一致を検証し、Skillごとの実装差を許可しません。実装内容の変更はfile SHA-256を`runtime_implementation_fingerprint`へ反映します。技法固有ロジックはこの共通helperへ入れません。

本Planのruntime dependencyはPython 3.11標準ライブラリだけに固定します。外部PyPI package、外部binary、network serviceをruntime依存へ追加しません。

Planで定義した正確性、hard limit、30秒のCLI test timeoutを標準ライブラリ実装で満たせない場合は、その実装をPlan未達として停止し、暗黙にCoverage基準を下げたり依存関係を変更したりしません。将来用adapterも作りません。
