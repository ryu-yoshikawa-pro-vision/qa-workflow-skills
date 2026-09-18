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
└── requirement_structure.py
```

TR本文は生成せず、Authority / Risk → TRの閉鎖、未知参照、Disposition重複、優先度を計算します。

### `test-condition-design`

```text
skills/test-condition-design/scripts/
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
└── case_structure.py
```

具体的な前提、操作、実データ、expected resultは生成せず、TCN / CI → TCの閉鎖、未知参照、優先度、Authority対応を検査します。

### `coverage-analysis`

```text
skills/coverage-analysis/scripts/
└── traceability.py
```

対象はテスト設計のAuthority / Risk → TR → TCN → CI → TC、またはCIを持たない契約でのTCN → TCです。E2E実装・実行結果は既存責務のままです。

### `qa-workflow`

新しい工程固有scriptは追加しません。既存の成果物再利用、上流変更伝播、局所ブロック、完了判定を、以下のversion / fingerprint / runtime状態へ対応させます。

## 3. 共通JSON契約

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

各modelは少なくとも次を持ちます。

```json
{
  "envelope_version": "1",
  "generator_contract_version": "combinatorial-v1",
  "model_key": "pairwise-01",
  "upstream_artifacts": [
    {
      "skill": "test-requirement-design",
      "semantic_fingerprint": "sha256:..."
    }
  ],
  "static_data_versions": {},
  "authority_refs": ["SPEC-001"],
  "reference_refs": []
}
```

- `envelope_version`: runtime共通envelopeの互換性version。全generator共通
- `generator_contract_version`: 各generator固有の入出力・Coverage契約version。互換性を壊す変更でそのgeneratorだけ更新する
- `model_key`: 同一成果物系列のmodel識別
- `upstream_artifacts`: 正規化に使用した上流成果物の意味データfingerprint。Markdown全文hashや自由記述versionを使わない
- `static_data_versions`: 出力へ影響するcatalog / scheme / assetのversionまたはfingerprint
- `authority_refs`: 製品固有expected resultを確定できる現在有効な根拠
- `reference_refs`: 外部標準、一般UI資料、DOM / 実装事実等の補助情報

### 3.3 runtime出力envelope

成功・想定内の未処理状態を含め、stdoutは常に1つのJSON objectにします。

```json
{
  "envelope_version": "1",
  "generator_contract_version": "combinatorial-v1",
  "generator": "combinatorial",
  "model_key": "pairwise-01",
  "model_fingerprint": "sha256:...",
  "generation_fingerprint": "sha256:...",
  "static_data_versions": {},
  "runtime_status": "ok",
  "model_status": "ready",
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
- `unresolved`: 追加情報が必要
- `blocked`: 必須情報不足等で対象modelを継続できない
- `stale`: 上流・model・generator contract・static dataの変更により再生成が必要

`runtime_status=ok`でもblocking issueが存在する場合は`model_status=ready`にしません。

`ok`、`invalid_input`、`unsupported`、`limit_exceeded`は「runtimeが構造化結果を返せた」という意味で終了code 0とします。`internal_error`またはenvelope自体を生成できない障害だけ終了code 1とします。Agent側は終了codeだけでroutingせず、stdout envelopeを必ずparseします。stderrは人間向け診断だけに使い、入力全文、secret、tokenを出しません。

本Planで対応subsetとして定義した入力に対して`unsupported`を返した場合は、LLM fallbackで正常扱いせずruntime契約違反として修正対象にします。本Planの対応subset外の入力だけ、`unsupported`を明示した上で既存LLM経路へ戻せます。

### 3.4 構造化された未解決事項

`issues`は少なくとも次を持てる共通形式にします。

```json
{
  "issue_type": "unspecified_rule",
  "model_key": "decision-01",
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

- `model_fingerprint`
- `generator_contract_version`
- `static_data_versions`

同じmodelでもgenerator contractまたは静的参照データが変われば`generation_fingerprint`は変わり、旧派生成果物をstaleと判定します。

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

同じAuthority IDでも上流成果物versionが変わり得ます。

- modelは利用した上流成果物versionを保持する
- version不一致時は`change_impact.py`またはtraceabilityで関連modelを特定する
- 影響modelだけを`要再検証`へ戻す
- 無関係なmodelを全再生成しない

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

技法固有target keyとCI IDの対応を機械証拠へ保持します。

- 同じtarget keyが再生成された場合は既存CI IDを維持
- 新しいtarget keyだけ新規CI IDを発行
- 消滅targetのCIはstaleとし、下流TCを`要再検証`へする
- 既存CI番号の詰め直しは行わない

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

各scriptのpayloadからmachine evidence行を決定論的に組み立てます。validatorはfenced JSON blockを抽出してstrict JSON decodeし、canonical化したmodel / fingerprint / machine evidenceが一致することを確認します。

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

許可するedge typeは少なくとも次です。

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

意味上の統合だけLLMに残します。複数技法の結果を同じCIへまとめる場合、LLMは`merge_group`を明示し、scriptがtarget key、Authority、優先度を決定論的にunionします。

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

- 新契約成果物はcontract versionとupstream versionが現在有効
- model fingerprintと派生成果物が一致
- stale / `要再検証` / unresolvedなmodelが残っていない
- runtime実行対象なのに決定論的generator未実行である場合、その事実を保持する

### 13.2 legacy成果物

contract versionを持たない既存成果物を一律破棄しません。

- 従来契約を満たす間はlegacy成果物として参照可能
- その成果物を変更・再利用して本Plan対象の決定論的処理へ入る時点で、担当Skillが正規化modelを作成して新契約へ昇格
- legacy成果物を「決定論的生成済み」と表現しない

### 13.3 局所状態

model単位状態の正本は各成果物に保存した`model_status`、fingerprint、構造化issueです。`qa-workflow`の状態表は必要時の集約表示であり、唯一の永続正本にしません。状態表がない場合も、成果物metadataから現在状態を再構築できることを必須とします。

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

strict JSON、canonicalization、fingerprint、envelope処理はruntime対象5 Skillそれぞれの`scripts/runtime_contract.py`へ同じ実装を同梱します。repo rootの共通helperへ依存させません。repository testで5ファイルのSHA-256一致を検証し、Skillごとの実装差を許可しません。技法固有ロジックはこの共通helperへ入れません。

Python 3.11標準ライブラリで正しく実装できる処理は標準ライブラリを優先します。ただし、Domain Testing、mixed-strength、constraint solving等で自前実装より既存の成熟した依存関係を使う方が正確・保守可能な場合は、依存追加を禁止しません。

依存追加時はライセンス、保守状況、CI、Skill単体移植性を確認し、必要なpackageをSkill契約またはrepository依存へ明示します。将来用adapterは作りません。
