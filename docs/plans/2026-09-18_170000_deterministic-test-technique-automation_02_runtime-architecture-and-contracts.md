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
└── metamorphic.py
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

新しい工程固有scriptは追加しません。既存の成果物再利用、上流変更伝播、局所ブロック、完了判定を、以下のversion / fingerprint / runtime状態へ対応させます。

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
    "model_key": "pairwise-001",
    "upstream_entities": [
      {
        "skill": "test-requirement-design",
        "entity_ref": "TR-001",
        "content_fingerprint": "sha256:..."
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
- `model_key`: 技法modelを処理するscriptだけ必須。形式は`<technique-slug>-\d{3,}`。同じ技法modelの改訂では維持し、新規modelは同じ技法slug内の最大番号+1とする
- artifact全体を処理する`risk_matrix.py`、`technique_candidates.py`、`change_impact.py`、`environment_requirements.py`、`requirement_structure.py`、`case_structure.py`、`traceability.py`では`model_key`を禁止し、対象Entityはscript固有inputのIDで識別する
- `upstream_entities`: 実際に消費した上流Entity単位で保持する。`skill + entity_ref`を一意keyとし、そのEntityのcanonicalな構造化内容から`content_fingerprint`を計算する
- `static_data_versions`: keyは`^[a-z][a-z0-9_]*# テスト分析・テスト技法の決定論的自動化Plan

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
└── metamorphic.py
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

新しい工程固有scriptは追加しません。既存の成果物再利用、上流変更伝播、局所ブロック、完了判定を、以下のversion / fingerprint / runtime状態へ対応させます。

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

、valueは`sha256:<64 lowercase hex>`または明示的なcontract version文字列`^[A-Za-z0-9][A-Za-z0-9._-]*# テスト分析・テスト技法の決定論的自動化Plan

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
└── metamorphic.py
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

新しい工程固有scriptは追加しません。既存の成果物再利用、上流変更伝播、局所ブロック、完了判定を、以下のversion / fingerprint / runtime状態へ対応させます。

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


- `authority_refs`: 製品固有expected resultを確定できる現在有効な根拠
- `reference_refs`: 外部標準、一般UI資料、DOM / 実装事実等の補助情報
- script固有入力は必ず`input`配下に置き、metadataと同じkeyを再定義しない

### 3.3 runtime出力envelope

成功・想定内の未処理状態を含め、stdoutは常に1つのJSON objectにします。

```json
{
  "envelope_version": "1",
  "runtime_contract_version": "runtime-v1",
  "generator_contract_version": "combinatorial-v1",
  "generator": "combinatorial",
  "model_key": "pairwise-001",
  "model_fingerprint": "sha256:...",
  "generation_fingerprint": "sha256:...",
  "static_data_versions": {},
  "runtime_status": "ok",
  "model_status": "ready",
  "deterministic_generated": true,
  "payload": {},
  "issues": []
}
```

`runtime_status`:

- `ok`: script責務を完了
- `invalid_input`: 入力契約違反
- `unsupported`: 入力は妥当だが本Planの対応契約外
- `limit_exceeded`: 契約上限を超過
- `internal_error`: 想定外障害

`model_status`:

- `ready`: 下流へ利用可能
- `unresolved`: 追加情報またはLLM fallbackが必要
- `blocked`: 入力違反、上限超過、runtime障害等で継続不可

scriptが返す組合せは次で固定します。

| runtime_status | model_status | blocking issue | 扱い |
| --- | --- | --- | --- |
| `ok` | `ready` | なし | runtime結果を利用可能 |
| `ok` | `unresolved` | あり | 質問・意味判断後に再実行 |
| `invalid_input` | `blocked` | あり | 入力契約を修正 |
| `unsupported` | `unresolved` | あり | 本Planの対応subset外だけLLM fallback可 |
| `limit_exceeded` | `blocked` | あり | model分割またはcontract変更が必要 |
| `internal_error` | `blocked` | あり | runtime不具合として扱う |

`stale`はscriptが返す`model_status`ではありません。成果物保存時の`freshness_status = current / stale`として`qa-workflow`がfingerprint比較から付与します。

scriptが正常実行されたenvelopeでは`deterministic_generated=true`です。Python unavailable、runtime未実行、対応subset外のLLM fallbackでは、成果物metadataを`runtime_status=not_run`または直前の`unsupported`、`deterministic_generated=false`として保存します。LLM fallback後にQA成果物自体が利用可能なら`model_status=ready`にできますが、「決定論的生成済み」とは扱いません。

`ok`、`invalid_input`、`unsupported`、`limit_exceeded`は「runtimeが構造化結果を返せた」という意味で終了code 0とします。`internal_error`は可能なら構造化envelopeを返して終了code 1、envelope自体を生成できない障害も終了code 1とします。Agent側は終了codeだけでroutingせず、stdout envelopeをparseします。stderrは人間向け診断だけに使い、入力全文、secret、tokenを出しません。

本Planで対応subsetとして定義した入力に対して`unsupported`を返した場合は、LLM fallbackで正常扱いせずruntime契約違反として修正対象にします。本Planの対応subset外の入力だけ、`unsupported`を明示した上で既存LLM経路へ戻せます。

### 3.4 構造化された未解決事項

`issues`は少なくとも次を持てる共通形式にします。

```json
{
  "issue_type": "unspecified_rule",
  "blocking": true,
  "model_key": "decision-001",
  "target_key": "R4",
  "authority_refs": ["SPEC-001"],
  "required_information": "条件組合せに対する期待action",
  "route_to": "question-analysis",
  "resume_skill": "test-condition-design"
}
```

自由文stderrを再解釈してroutingしません。`route_to` / `resume_skill`は既存Skill名だけを許可します。`question-analysis`へ送る場合は`model_key` / `target_key`を質問・ブロック・回答後の再開まで保持し、同じSkill内の無関係なmodelをブロックしません。

## 4. canonicalization・version・fingerprint

### 4.1 canonical model

model fingerprintはSHA-256で計算します。入力はUTF-8のcanonical JSONです。

- object keyはUnicode code point順
- `authority_refs` / `reference_refs`等の集合扱い配列は重複除去してsort
- factor、condition、action、state、transition、edge、grammar production等、tie-breakや意味に入力順を使う配列は宣言順を保持
- assignment objectのkeyはsort
- decimal / date / datetimeは共通表現へ正規化
- JSON whitespaceは除去
- 非有限数は不可

`model_fingerprint`はcanonical modelの意味データだけから計算し、Markdownの説明文、表示順だけの装飾、生成結果を含めません。

`generation_fingerprint`は次をcanonical JSON化してSHA-256を計算します。

- `generator`
- `model_fingerprint`
- `runtime_contract_version`
- `generator_contract_version`
- `static_data_versions`

同じmodelでも共通runtime、generator contract、静的参照データが変われば`generation_fingerprint`は変わり、旧派生成果物をstaleと判定します。generator実装のbug fix、探索順、tie-break等、machine outputへ影響する変更はschema互換でも必ず`generator_contract_version`を更新します。

generatorが返すtarget集合とCoverage計算は純粋な決定論処理です。一方、target → CI ID等の既存ID維持はstateful処理であり、再現条件に前回のmappingを含みます。同じgenerator結果と同じprevious mappingからは同じmaterialized ID mappingを得るものとし、generatorの決定論性とID維持を混同しません。

### 4.2 静的参照データ

generator結果に影響する静的データはversionを持ちます。

- `ui-pattern-catalog.json`: file content SHA-256
- repository-default risk scheme: `risk-scheme-v1`
- project-specific scheme: 正規化schemeのfingerprint
- grammar / distribution / metamorphic relation等が外部assetの場合: そのasset versionまたはfingerprint

同じscriptでも静的データversionが異なる場合は同じ再現条件とは扱いません。

### 4.3 model_keyの安定性

- 同じ技法・同じ検証責務のmodelを改訂する場合は既存`model_key`を維持する
- 意味上別modelと判断した場合だけ新しいkeyを発行する
- 削除済みkeyは同じ成果物系列で再利用しない
- 同じ`(技法, model_key)`に異なる同時定義を置かない

意味上同じmodelかどうかの判断はLLMに残します。keyの維持・新規発行規則は機械契約として固定します。

### 4.4 上流変更

同じIDでも上流成果物の構造化内容は変わり得るため、自由記述のversionやMarkdown全文hashではなく、実際に消費したEntityのcanonicalな構造化内容から`content_fingerprint`を計算します。`content_fingerprint`は意味同値性を推論するものではなく、正規字段の内容変更を検出するためのfingerprintです。

最初のAuthority入力では、`spec-analysis`成果物のうち実際に利用した「現在有効な仕様根拠」行について、少なくとも次をcanonical化します。

- 仕様根拠ID
- 種別
- 現在有効な内容
- 適用範囲
- 情報源 / 正本一覧
- 関係
- 関連仕様根拠ID

人間向け説明文、見出し、表記だけの変更はfingerprint対象にしません。`spec-analysis`へfingerprint字段を必須追加せず、最初に消費するruntime側で上記意味データから算出できます。

以降のQA成果物は、下流が実際に利用する正規テーブル / machine evidence / model metadataだけをcontent fingerprint対象とします。

- `test-analysis`: Product Risk、技法選択machine evidence、change graph、環境要求
- `test-requirement-design`: TRと上流Disposition
- `test-condition-design`: TCN、正規化model、target → CI mapping、Disposition
- `test-case-design`: TCとDisposition
- `coverage-analysis`: coverage / stale判定のmachine evidence

modelは利用した上流Entityを`upstream_entities`へ1件ずつ保持します。`skill + entity_ref`が同じEntityの`content_fingerprint`だけを比較し、不一致となったEntityを参照するmodelだけを`要再検証`へ戻します。成果物全体のfingerprint差だけを理由に無関係なmodelを全再生成しません。

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

上限の計測規則は次で固定します。

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

上限を超えた場合は`limit_exceeded`とし、Coverage基準、strength、path深度等を自動で下げません。item数が上限内でもbyte / depth上限を超える入力・出力は処理しません。上限変更は実装者判断ではなくgenerator contract変更としてPlanを更新します。

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

より強いsolver表現が必要なDomain Testing等は、その技法の明示ASTへ限定します。

## 7. stable ID・upsert・stale

### 7.1 QA ID

既存prefixは維持します。

- `TR-`
- `TCN-`
- `TCN-xxx-CIyy`
- `TC-`

同じ意味の既存項目を再利用できる場合は既存IDを維持します。TR / TCN / TCの意味上の同一性判断は担当SkillのLLM責務であり、runtimeがsemantic matchingして再採番しません。新規項目だけ現在の最大番号より後ろへ採番し、削除済みIDを同じ成果物系列で再利用しません。

TR / TCN / TCは既存の3桁形式をこのPlanで変更しません。最大番号が999に達した成果物系列で新規IDが必要な場合は削除済みIDを再利用せず、`id_space_exhausted` issueとしてブロックします。CIは`CI\d{2,}`のため同じ上限を持ちません。

### 7.2 Coverage targetとCI

技法固有target keyとCI IDの対応を機械証拠へ保持します。materialize時のinputには`previous_target_id_map`を明示的に渡します。

- 初回でmappingがない場合、同一TCN内のtarget keyをcanonical sortし、`CI01`から順に採番する
- 既存mappingがある場合、同じtarget keyは既存CI IDを維持する
- 新しいtarget keyは**同一TCN内**の既存CI最大番号+1から採番する
- 消滅targetのCIはstaleとし、下流TCを`要再検証`へする
- 削除済みCI番号を再利用せず、既存CI番号の詰め直しを行わない
- previous mappingに同一targetの重複、同一CIの複数target、親TCN不一致があれば`invalid_input`

CI番号は`CI\d{2,}`を許可します。

### 7.3 upsert

再実行はappendではなくstable keyでupsertします。

- 同じ`model_key + target key`は置換
- 生成されなくなった派生行はstaleとして除去候補にする
- 同一再実行で重複machine evidenceを作らない
- staleな派生成果物が残る状態を完了扱いしない

## 8. machine evidenceとMarkdown

### 8.1 正規化済みモデル

`test-condition-design`を中心に、scriptへ再投入できる正規化済みJSONを成果物へ保持します。

一覧表には次だけを置きます。

`モデルキー | 観点ID | 技法 | generator contract version | model fingerprint | generation fingerprint | upstream fingerprint | static data version | runtime status | model status`

正規化入力JSONそのものはMarkdown table cellへ埋め込まず、`model_key`ごとのfenced `json` blockへ保存します。JSONはstrict JSONで、表示用のindentや改行が変わってもcanonical化後の意味が同じなら同じ`model_fingerprint`になります。

人間向け説明文はLLMが生成して構いません。machine evidenceのJSON、key、ID対応、Coverage値をLLMが再計算・改変しません。

### 8.2 machine evidenceの描画

共通のJSON fence出力、Markdown escape、runtime metadata行の描画は各Skill同梱の`scripts/runtime_contract.py`が担当します。Coverage target → CI materialize、merge group統合、Coverage Item表のmachine row生成は`test-condition-design/scripts/materialize_coverage.py`が担当し、generatorへ混在させません。

正規化modelの保存形式は次で固定します。

```markdown
### Machine Model: pairwise-001

```json
{...}
```
```

見出しの`model_key`とJSON内metadataの`model_key`が一致しない場合はvalidatorを失敗させます。

validatorはfenced JSON blockを抽出してstrict JSON decodeし、canonical化したmodel / fingerprint / machine evidenceが一致することを確認します。

必須round-trip testは次です。

1. canonical modelをMarkdownへ保存
2. parserで同じ`model_key`のJSON blockを抽出
3. strict JSON decode
4. canonical化
5. 元の`model_fingerprint`と一致

これにより`|`、backslash、改行を含む値をMarkdown table escapeへ依存させません。

## 9. 技法選択とmodelの閉鎖

`test-analysis`の技法選択用signalを機械証拠として保存します。

`選択キー | 適用領域 | Selection Source | Signals JSON | Candidates JSON | Undetermined Signals JSON | 最終採用技法 | 状態`

`Selection Source`は`analysis / user / existing_artifact`のいずれかです。

- `true / false / null`を区別
- `technique_candidates.py`の`complete`は`undetermined_signals`が空かだけを表す診断値であり、`complete=false`だけを理由にworkflowをブロックしない
- ユーザー明示または有効な既存成果物由来の技法をcandidate scriptが勝手に却下しない
- 選択した技法は`test-condition-design`のmodel、対象外、未解決、runtime未対応のいずれかへ必ず閉じる
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

直接互換payloadまたは小さいdeterministic adapterを使用します。

意味上の統合だけLLMに残します。複数技法の結果を同じCIへまとめる場合、LLMは`merge_group`を明示し、`materialize_coverage.py`が同一groupのtarget key、Authority、Reference、優先度、test data requirementを決定論的にunionします。

`merge_group`入力は`{"merge_group_key":"MG-001","target_keys":["..."],"authority_refs":["..."]}`とし、target keyは2件以上、重複不可、同一TCN配下だけを許可します。異なるexpected result rootを持つtargetは`invalid_input`とします。

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

- 新契約成果物はenvelope / generator contract versionとupstream content fingerprintが現在有効
- model / generation fingerprintと派生成果物が一致
- stale / `要再検証` / unresolvedなmodelが残っていない
- runtime実行対象なのに決定論的generator未実行である場合、その事実を保持する

### 13.2 legacy成果物

contract versionを持たない既存成果物を一律破棄しません。

- 従来契約を満たす間はlegacy成果物として参照可能
- その成果物を変更・再利用して本Plan対象の決定論的処理へ入る時点で、担当Skillが正規化modelを作成して新契約へ昇格
- legacy成果物を「決定論的生成済み」と表現しない

### 13.3 局所状態

model単位状態の正本は各成果物に保存した`model_status`、`freshness_status`、fingerprint、構造化issueです。`qa-workflow`を出力する場合は既存のSkill状態表を必須で維持しますが、この表は集約表示であり唯一の永続正本ではありません。他Skillを実行する前提としてworkflow状態表の存在は要求せず、必要な場合は成果物metadataから現在状態を再構築します。

`qa-workflow`には既存Skill状態表とは別に次のmodel状態表を追加します。

`Skill | Model Key | Model Status | Freshness | Runtime Status | Deterministic Generated | Blocker / Issue`

同じSkillで複数model行を許可し、`WF-D012`のSkill + 対象重複契約は既存Skill状態表だけへ適用します。

- 1 modelだけ`ブロック中` / `要再検証`でも、独立した他modelは継続可能
- 対象scopeにstale / unresolvedな必須modelが残る場合はworkflow全体を完了にしない
- runtime `unsupported`とQA成果物の意味上の`ブロック中`を分離する
- `question-analysis`へroutingする場合は`model_key` / `target_key`を質問一覧・ブロック中範囲・回答後の再開情報へ保持する
- `coverage-analysis`はstale / gapをTCN / CIだけでなく関連`model_key`まで追跡できるようにする

### 13.4 上流変更

上流成果物versionが変わった場合:

1. 最も早い変更成果物を特定
2. change impact / traceabilityで影響modelを特定
3. 影響modelとその派生成果物だけを`要再検証`
4. 正規化modelを更新
5. generator再実行
6. 下流structure / Coverageを再検査
7. staleが消えた範囲だけ再利用可能に戻す

## 14. 移植性と依存関係

各Skillは単体コピー可能な既存契約を維持します。

strict JSON、canonicalization、fingerprint、envelope処理はruntime対象5 Skillそれぞれの`scripts/runtime_contract.py`へ同じ実装を同梱します。repo rootの共通helperへ依存させません。`runtime_contract_version`をfile内定数として持ち、内容変更では必ずversionを更新します。repository testで5ファイルのSHA-256一致を検証し、Skillごとの実装差を許可しません。技法固有ロジックはこの共通helperへ入れません。

Python 3.11標準ライブラリで正しく実装できる処理は標準ライブラリを優先します。ただし、Domain Testing、mixed-strength、constraint solving等で自前実装より既存の成熟した依存関係を使う方が正確・保守可能な場合は、依存追加を禁止しません。

依存追加時はライセンス、保守状況、CI、Skill単体移植性を確認し、必要なpackageをSkill契約またはrepository依存へ明示します。将来用adapterは作りません。
