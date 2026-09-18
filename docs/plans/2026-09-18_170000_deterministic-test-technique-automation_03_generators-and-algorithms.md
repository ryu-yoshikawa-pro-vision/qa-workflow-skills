# テスト分析・テスト技法の決定論的自動化Plan

## 1. プロダクトリスク

### `risk_matrix.py`

入力は`scheme`、`impact`、`likelihood`です。

- `scheme = repository-default`: 現在の`test-analysis/references/guidance.md`にある4×4マトリクスを独立実装し、impact / likelihoodは1〜4だけを許可する
- `scheme = project-specific:*`: 本scriptの計算対象外とし、標準4×4へ変換・補正しない

`test-analysis`成果物には分析単位の`リスク評価方式`を残します。`RISK-D004`と`RISK-D005`は`repository-default`の場合だけ1〜4と標準4×4を要求します。案件固有方式ではfixtureが明示する契約または意味評価を使います。

scriptは影響度・発生可能性を決めず、validator実装をimportしません。

## 2. テスト技法候補

### `technique_candidates.py`

自然言語ではなく、次のsignalをすべて持つ正規化入力を受け取ります。

```json
{
  "ordered_domain": true,
  "explicit_boundaries": true,
  "equivalence_classes": true,
  "multiple_discrete_conditions": false,
  "stateful": false,
  "multiple_factors": false,
  "explicit_flow": null
}
```

`true`は確認済み、`false`は明示的に該当しない、`null`は未確認です。key欠落は`invalid_input`とします。

出力は現行の正規技法名だけを使います。

- 同値分割
- 境界値分析
- デシジョンテーブル
- 状態遷移
- Pairwise / 組合せ
- エラー推測
- シナリオ / ユースケース

scriptは`true`の構造signalから候補を返し、`candidates`、`undetermined_signals`、`complete`を返します。`null`を`false`として候補除外せず、未確認signalが残る場合は最終候補集合を確定済みとは扱いません。Error Guessingは過去不具合等の意味根拠が必要なため自動選択しません。

## 3. 同値分割

### `equivalence_partitions.py`

同値partitionの発見は自動化しません。LLMがpartition setと各partitionを正規化した後を自動化します。

```json
{
  "model_key": "ep-01",
  "partition_sets": [
    {
      "set_key": "age",
      "partitions": [
        {
          "partition_key": "age-valid",
          "kind": "valid",
          "domain": {
            "type": "integer",
            "minimum": 18,
            "minimum_inclusive": true,
            "maximum": 64,
            "maximum_inclusive": true
          },
          "authority_refs": ["SPEC-001"]
        }
      ]
    }
  ]
}
```

機械処理:

- `set_key` / `partition_key`の重複
- 空partition
- 同じpartition set内の有限range / enumの重複
- valid / invalidの同一値衝突
- representative valueが入力にある場合の所属検証
- enum、整数範囲等で一意に候補を作れる場合の代表値候補生成
- partition Coverage
- 成果物上の閉鎖: 各partitionがCoverage Itemまたは妥当なDispositionのどちらか一方へ位置づいていること
- Each Choice Coverage: 対象内かつ成立可能な各partitionが、実際に1件以上のCoverage ItemでCoverageされていること

異なるpartition set間のdomainは重複していてよく、相互排他検査をしません。

整数rangeの代表値を機械生成しても「業務上代表的」とは扱いません。仕様根拠のある同一partition内の別値へ変更する場合は、変更後の所属をscriptで再検証します。

複数partition set間の具体的な値組合せ最適化は同値分割scriptの責務にせず、必要な場合だけ明示的に`combinatorial.py`へ渡します。

`対象外`、`別テストレベル`、`残存リスク`、`ブロック中`へ閉じたpartitionを「Coverage済み」とは数えません。`成立不能`としてCoverage母集団から外す場合は、成立不能を示すAuthority根拠を必須にします。`unresolved` / `unsupported`が残るmodelではEach Choice 100%を宣言しません。

## 4. 境界値分析

### `bva.py`

対応domain:

- integer
- decimal
- date
- timezoneを持たないlocal datetime
- length / count

境界ごとに次を明示します。

- `boundary_key`
- `minimum` / `maximum`
- `minimum_inclusive` / `maximum_inclusive`
- stepまたは最小単位
- `2-value` / `3-value`
- `authority_refs`

重要事項:

- step不明時に`±1`を仮定しない
- decimalは10進文字列で受け取り`decimal.Decimal`を使う
- dateは`YYYY-MM-DD`、local datetimeはISO 8601形式で受け取る
- timezone / DSTを含むdatetimeは初回対象外
- exclusive境界では境界そのものと最初の有効値を区別する
- lower / upperが近接して同じ具体値になる場合でも、値とCoverage上の境界位置を分けて保持する

出力は自由文中の数値ではなく、`boundary_key`、`position`、typed value、対応Coverage Itemを機械的に追跡できる形へします。

## 5. デシジョンテーブル

### `decision_table.py`

初回実装ではcondition assignmentを完全展開したruleだけを扱います。don't-careを含むminimized table、rule priorityは初回非対応です。

入力例:

```json
{
  "model_key": "dt-01",
  "conditions": [
    {"key": "role", "values": ["admin", "member"]},
    {"key": "locked", "values": [true, false]}
  ],
  "actions": [
    {"key": "allow_save"},
    {"key": "show_error"}
  ],
  "known_rules": [
    {
      "rule_key": "R1",
      "assignment": {"role": "admin", "locked": false},
      "actions": {"allow_save": true, "show_error": false},
      "authority_refs": ["SPEC-001"]
    }
  ],
  "forbidden_constraints": []
}
```

actionは複数同時に成立できます。`actions`がすべて`false`のknown ruleも有効なruleであり、rule未定義とは区別します。

各known ruleのaction vectorは、宣言済みaction keyの集合と完全一致させます。

- action key欠落を暗黙の`false`へ変換しない
- 未知action keyを拒否する
- 初回boolean subsetでは各action値をbooleanに限定する
- key欠落、未知key、型不一致は`invalid_input`とする

処理順:

1. condition / action / rule keyと値集合を検証する
2. known ruleと`forbidden_constraints`が直接衝突していないか検出する
3. 条件値のCartesian productを、hard limit内でrule spaceとして列挙する
4. 成立不能assignmentを制約根拠付きで識別する
5. 成立可能assignmentへknown ruleを照合する
6. known ruleが存在しないassignmentを`unspecified`として返す
7. 同一assignmentに複数known ruleがある場合、action vectorが一致すれば重複、異なれば矛盾として返す
8. 成立可能rule Coverageを算出する

成立不能rule、unspecified ruleを無言で捨てません。未定義assignmentへscriptがactionを補完しません。

`unspecified`が残る場合は、そのassignmentをCoverage済みruleへ数えず、期待挙動不足として既存`question-analysis` / ブロック中の経路へ戻します。同一assignmentへ異なるaction vectorが定義された矛盾も同様に未解決として返し、scriptがどちらかを採用しません。

初回実装ではdon't-care化やBoolean minimizationを行いません。

## 6. 全組合せ・Base Choice・Pairwise・N-wise

### `combinatorial.py`

共通入力:

- `model_key`
- factors / values
- `forbidden_constraints`
- mode
- N-wiseの場合のstrength
- Base Choiceの場合の各factorのbase value
- `authority_refs` / `reference_refs`

対応mode:

- exhaustive
- base-choice
- 2-wise
- t-wise

共通入力検証:

- factor key一意
- 各値集合1件以上・重複なし
- constraintのassignmentが空でない
- constraint参照factor / valueが存在する
- 成立可能full assignmentが0件ならUNSAT
- Pairwiseは2因子以上
- N-wiseは`2 <= strength <= factor数`

### exhaustive

hard limit内で有限domainのCartesian productを列挙します。成立不能assignmentは制約根拠付きで識別し、単純に消去しません。

### Base Choice

初回は`forbidden_constraints`なしのdomainだけを対象にします。

1. 全base valueの組合せを1件作る
2. 各factorについて、そのfactorだけを各non-base valueへ置き換える
3. 同一入力で安定した順序を返す

constraint付きBase Choiceは、base再選択規則をこのbranchで新設せず`unsupported`とします。

### Pairwise / N-wise

全full assignmentを事前にmaterializeしてからgreedy選択しません。

1. factor組合せと値からt-tuple候補を列挙する
2. 各tupleについて、部分assignment禁止制約を使った決定論的backtrackingで少なくとも1つのfull assignmentへcompletion可能か確認する
3. feasibility結果を`SAT / UNSAT / limit_exceeded`へ分ける。探索空間を完全に調べ切った場合だけ`UNSAT`とする
4. `SAT`のtupleだけをCoverage母集団とし、`UNSAT`はAuthority付き制約根拠とともに成立不能として保持する
5. `limit_exceeded`が1件でも残る場合はCoverage母集団が確定していないため100% Coverageを宣言しない
6. 未Coverage tupleを安定順で選び、そのtupleを含むfull assignmentを決定論的にcompletionする
7. completion時は未Coverage tupleを多く含む値を優先し、tie-breakを固定する
8. 生成したfull assignmentがCoverageするtupleを集合から除き、0件になるまで繰り返す

最小行数は保証しません。要件は成立可能t-tupleの100% Coverageです。

Pairwise / N-wiseのDisposition対象は全禁止full assignmentではなく、Coverage母集団として評価したt-tupleです。constraintで成立不能なt-tupleは、根拠を追跡できる形で`成立不能`へ閉じられるようにします。

### 計算量と出力量の上限

- tuple候補数
- feasibility search node数
- 生成row数
- 出力件数

をruntimeのhard limitで制御します。上限値は実装時のfixtureで固定し、LLM入力にはしません。

`limit_exceeded`時にexhaustiveをPairwiseへ、N-wiseを低strengthへ勝手に変更せず、部分結果を100% Coverageと表現しません。

mixed-strengthは初回対象外です。

## 7. Classification Tree

独立generatorは追加しません。

LLMがclassification / classをfactor / valueへ正規化し、同じ`forbidden_constraints`契約で`combinatorial.py`へ渡します。

対応Coverageはexhaustive、Base Choice、Pairwise / N-wiseです。Classification Treeを新しい正規技法名にはしません。

## 8. 状態遷移

### `state_transition.py`

各transitionは一意な`transition_key`を持ちます。

```json
{
  "transition_key": "T1",
  "from": "draft",
  "event": "publish",
  "guard": "owner",
  "to": "published",
  "authority_refs": ["SPEC-001"]
}
```

`from + event + to`だけではidentityとせず、guard違いのtransitionを別遷移として保持します。

入力:

- `model_key`
- states
- initial states
- terminal states
- transitions
- optional reset information
- 根拠付きで明示されたinvalid transition候補
- 要求するCoverage mode

機械処理:

- 未知state参照
- transition key重複
- graph上の到達可能性
- outgoing transitionのない状態
- all states / all valid transitions
- transition-pair / n-switch
- Round-trip
- 根拠付きinvalid transition候補の構造検査

### guardと実行可能性

guardをscriptが評価できない場合、graph上の連続sequenceと実行可能sequenceを区別します。

- guardなし、またはsequence feasibilityが正規化済み: n-switch / Round-tripの正式Coverage母集団として扱える
- guard feasibilityが不明: 構造上のsequence候補として返し、100%実行可能Coverageとは表現しない

### n-switch

- 0-switch = 1 transition
- 1-switch = 2連続transition
- 2-switch = 3連続transition

2-switch以上を高リスクという理由だけで自動選択せず、sequence failure risk等の根拠を必要とします。

### Round-trip

start stateとend stateが同一で、途中stateを重複しないloopを構造的に列挙します。guardを満たす実行可能性と業務上のscopeは別に判断します。

### invalid transition

有効遷移集合の補集合から全invalid transitionを生成しません。仕様、プロダクトリスク、過去不具合等の根拠がある候補だけを入力します。

## 9. 明示flowのpath列挙

### `flow_paths.py`

各edgeは一意な`edge_key`を持ち、同じfrom / toでもguardやbranch labelが異なるedgeを区別します。

入力:

- `model_key`
- nodes
- edges: `edge_key / from / to / guard / label / authority_refs`
- start node
- `terminal_nodes`
- loop bound
- main / alternative等の分類が仕様で明示されている場合はその分類

処理:

- bounded path候補
- node Coverage
- edge Coverage
- graph上のunreachable node
- terminalへ到達しない構造path
- inputでloop対象・代表回数・最大回数が明示された場合のsimple loop Coverage

scriptはgraph構造からmain / alternative、typical loop回数、最大loop回数を推測しません。

初回対応はsingle-threaded flow graphに限定します。fork / join、並行branch、interleaving semanticsを含むflowは`unsupported`とし、通常のpath列挙で直列化しません。

loop boundは「同じedgeを追加で通過できる最大回数」として固定し、boundなしcycleを拒否します。simple loop Coverageを要求する場合は、0回、1回、仕様で明示された代表回数、仕様上の最大回数のうち入力で定義されたものをCoverage対象として保持します。acyclic graphでもpath数がhard limitを超える場合は`limit_exceeded`とします。

edge証拠とpath証拠は分離し、1つのedgeが複数pathへ含まれることを許可します。

## 10. Cause-Effect Graph

### `cause_effect.py`

初回はboolean cause / effect subsetだけを扱います。

effect式で許可するAST node:

- `{"op":"ref","cause_key":"C1"}`
- `{"op":"not","arg": ...}`
- `{"op":"and","args":[...]}`
- `{"op":"or","args":[...]}`

effect式はcauseだけを参照し、effect同士の参照は初回非対応とします。これにより循環参照を持ち込みません。

入力例:

```json
{
  "model_key": "ce-01",
  "causes": [{"cause_key": "C1"}, {"cause_key": "C2"}],
  "effects": [
    {
      "effect_key": "E1",
      "expr": {"op": "and", "args": [
        {"op": "ref", "cause_key": "C1"},
        {"op": "ref", "cause_key": "C2"}
      ]}
    }
  ]
}
```

scriptはcause assignmentを列挙して各effectをboolean評価し、`effect_key -> boolean`の完全なaction vectorとして`decision_table.py`へ渡します。

cause数と最大assignment数にhard limitを設けます。全assignmentは最大`2^n`件になるため、上限を超えた場合は`limit_exceeded`とし、部分列挙を完全なDecision Tableへ渡しません。

未知cause参照、重複key、空`and / or`を`invalid_input`とします。自然言語論理式をparseするDSLは追加しません。

## 11. schema-based test data

### `schema_cases.py`

初回はraw JSON Schema / OpenAPI documentを完全parseしません。LLMまたは対象調査がdialectの意味を解釈し、fieldごとの正規化済みconstraintへ変換した後をscriptで処理します。

入力例:

```json
{
  "model_key": "schema-01",
  "schema_kind": "json-schema-2020-12",
  "fields": [
    {
      "field_key": "name",
      "type": "string",
      "required": true,
      "allows_null": false,
      "constraints": {"min_length": 3, "max_length": 20},
      "length_semantics": "json-schema-string",
      "authority_refs": ["SPEC-001"]
    }
  ]
}
```

初回`schema_kind`:

- `json-schema-2020-12`
- `openapi-3.0-schema`
- `html-form-control`

normalization側でdialect差を保持します。raw JSON Schema / OpenAPI documentからこの正規化形式へ変換する意味判断はLLM / 対象調査の責務で、`schema_cases.py`の責務ではありません。

- JSON Schema 2020-12の`exclusiveMinimum` / `exclusiveMaximum`は数値境界として正規化する
- OpenAPI 3.0のboolean `exclusiveMinimum` / `exclusiveMaximum`は`minimum` / `maximum`と組み合わせて正規化する
- OpenAPI 3.0の`nullable: true`はtype等の成立条件を確認した上で`allows_null`へ正規化する
- `title`、`description`等のannotation keywordはvalidation constraintとして扱わない
- 未対応validation / applicator keywordがfieldの意味を変える場合は`unsupported`とし、annotationだけを理由にschema全体を拒否しない

HTML form controlでは次を追加で明示します。

- `input_type` / control種別
- `constraint_validation_applicable`
- `disabled` / `readonly`等の適用判断
- `length_semantics = html-control-value`

`constraint_validation_applicable=false`のcontrolからrequired / min / max等のinvalid候補を生成しません。

初回に生成するのはtype、required、enum、数値境界、length、item count等のCoverage targetです。`pattern`の正規表現評価や、別constraintも満たす任意dummy文字列生成は行いません。

具体値を生成できる場合も、その値が未評価の別constraintを満たすとは表現しません。

## 12. grammar-based testing

自動化可能性はありますが、初回実装から外します。

terminal / nonterminal表現、epsilon、depth定義、membership、mutation候補のinvalid証明まで契約が増え、現在のテスト分析・条件設計の決定論化を完了するために必須ではありません。

将来対応する場合は別Issue / Planで扱い、このbranchではscript、成果物形式、validatorを追加しません。

## 13. test data matrix

独立runtime scriptは追加しません。

BVA、partition、schema、enum、組合せの生成結果を`test-condition-design`がCoverage Itemへ統合するときの整理方法として扱います。

- 同じ検証責務を複数generatorが導出した場合は1つへ統合するか`重複`へ閉じる
- 同じ具体値でもCoverage対象が異なる場合は統合しない
- 異なるgenerator結果の直積が必要な場合だけ`combinatorial.py`へ明示的に渡す

汎用TestData frameworkや新しい公開ID体系は追加しません。

## 14. 追跡性

### `coverage-analysis/scripts/traceability.py`

初回対象は`対象 / 実行範囲 = テスト設計`です。

入力:

- node id
- node type
- edges
- disposition
- analysis target

機械処理:

- Authority / Risk → TR
- TR → TCN
- TCN → CIまたはTC
- CI → TC

出力:

- missing edge / structural gap
- orphan
- unknown reference

数値の「構造上の閉鎖率」は新設しません。既存成果物とvalidatorが使うgap集合を正本にします。

IDが接続されているだけで意味上のCoverageが成立したとは判定しません。`充足 / 部分充足 / 未充足`、Disposition妥当性、E2E実装・実行結果の分析は既存`coverage-analysis`に残します。

## 15. 変更影響分析

### `test-analysis/scripts/change_impact.py`

入力:

- changed node IDs
- node type
- 明示済みdependency / traceability edges
- 対象とする下流node type

処理:

- 変更nodeから明示edgeを辿った構造的な影響候補抽出
- impacted Authority / TR / TCN / CI / TCの重複除去
- unknown node / dangling edgeの検出
- deterministic ordering

scriptは名称類似、同一画面、一般的な実装知識等から新しいimpact edgeを作りません。「構造上接続されていないが意味上影響する可能性」は`test-analysis`のLLM判断に残します。

## 16. テスト要求の構造処理

### `test-requirement-design/scripts/requirement_structure.py`

LLMが作成したTRとDispositionを入力にし、既存validatorと独立実装で次を計算します。

- Authority / RiskがTRまたはDispositionのどちらか一方へ閉じているか
- unknown upstream ID
- linked + disposed重複
- 関連する最高Product Riskからの最低優先度

TR本文、TRの分割 / 統合、検証責務の意味は変更しません。

## 17. テストケースの構造処理

### `test-case-design/scripts/case_structure.py`

LLMが作成したTCとDispositionを入力にし、既存validatorと独立実装で次を計算します。

- TCN / CIがTCまたはDispositionのどちらか一方へ閉じているか
- unknown upstream ID
- linked + disposed重複
- 関連Coverage Itemからの最高優先度
- 番号付き期待結果とAuthority対応の構造

具体的な前提条件、操作、テストデータ、期待結果、Oracleは生成・修正しません。

## 18. scriptが生成してはいけないもの

どのgeneratorでも次は生成しません。

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- リスクscore
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle

generatorの役割は、対応scopeとhard limitの範囲で、与えられたモデルを再現可能に展開し、未処理・unsupported・limit超過を隠さないところまでです。
