# テスト分析・テスト技法の決定論的自動化Plan

## 共通payload契約

generator系scriptの`payload`は次を基本形とします。

```json
{
  "targets": [],
  "coverage_summary": {
    "criterion": "",
    "required": 0,
    "covered": 0,
    "complete": false
  },
  "derived": {},
  "metadata": {}
}
```

- `targets`: 技法固有のstable `target_key`を持つ機械生成対象。model generatorは共通post-processで`model_key + target_key`から`target_ref`も付与する。CIへmaterialize可能なtargetは、具体的な値・assignment・setup + sequence・path・生成input等、そのCoverageを1回実行するmachine表現を`execution`へ必須で持たせ、共通post-processで`execution_fingerprint`を計算する。診断・adapter専用targetは`execution`を持たず直接CI化しない
- `coverage_summary`: EP / BVA / Domain / Decision Table / combinatorial / state / flow / grammar等の通常Coverage modelでは`{criterion, required, covered, complete}`を返す。CRUDでは`coverage_summary={completeness:{criterion,required,covered,complete}, consistency:{criterion,required,covered,complete}, complete}`を返し、2要素ともcompleteのときだけ全体をcompleteにする
- `completion_summary`: Random Testing / Metamorphic Testingだけが使用する。Randomは`required_case_count / generated_case_count / complete`、Metamorphicは`required_pairs / generated_pairs / complete`を返す
- model typeごとに上記の許可fieldを固定し、Random / Metamorphicへ`coverage_summary`を捏造したり、通常Coverage modelへ`completion_summary`を追加したりしない
- `derived`: 次scriptへ直接渡す機械変換結果
- `metadata`: target以外の再現可能な補助情報

構造検査scriptは`violations`と`derived_values`をpayloadへ返します。全scriptのrequired input、stable key、payloadは「## 25. script別入出力契約」で固定します。各技法節では技法固有アルゴリズムだけを定義し、実装者が別形式を追加しません。

### materialize対象と`execution`

model generatorはtargetごとに`materializable=true|false`を返します。`materializable=true`では`execution`必須、`false`では`execution=null / execution_fingerprint=null`です。

| generator | materialize | canonical `execution` |
| --- | --- | --- |
| `equivalence_partitions.py` | yes | `{set:{key,label}, partition:{key,label}, representative}` |
| `bva.py` | yes | `{boundary:{key,label}, position, value}` |
| `domain_testing.py` | yes | `{partition:{key,label}, border:{key,label}, point_kind, coordinates:[{dimension_key,label,value}]}` |
| `decision_table.py` | yes | `{conditions:[{condition_key,label,value}], actions:[{action_key,label,value}]}` |
| `combinatorial.py` | yes | `{row_ref, assignments:[{factor_key,label,value}]}` |
| `classification_tree.py` | no | adapter専用。child `comb` modelだけをCI化 |
| `state_transition.py` | yes | `{initial_state_key, initial_state_label, reset_key, reset_execution, setup_prefix, coverage_sequence, attempted_transition}`。state / transition / resetの実行意味を内包する |
| `flow_paths.py` | mode依存 | node / edge / bounded-path / simple-loopは`{initial_node_key, initial_node_label, target_node, edge_sequence}`。node / edgeの実行意味を内包する。fork-join branchはsemantic Coverage Itemへ閉じる |
| `crud_matrix.py` | yes | operation=`{entity_key, entity_label, function_key, function_label, operation}`、sequence=`{entity_key, entity_label, sequence_key, steps}`。stepsへfunction labelを含める |
| `cause_effect.py` | no | adapter専用。child `decision` modelだけをCI化 |
| `grammar_cases.py` | yes | `{input_label, input_text, production_key_sequence, mutation_key}` |
| `schema_cases.py` | no | adapter専用 |
| `ui_pattern_candidates.py` | no | 一般確認候補であり直接CI化しない |
| `random_testing.py` | yes | `{input_label, case_index, generated_value}` |
| `metamorphic.py` | yes | `{relation_key, relation_label, source_id, source_input, follow_up_key, follow_up_input, expected_relation}` |

`materializable=false`でも正規Coverage基準上必要なtargetは、current target versionを保持したsemantic Coverage Itemまたは既存Skillで許可されたDispositionへ閉じるまで完了させません。adapter / diagnostic専用targetはこのclosure対象外です。`execution`はstable keyの解決を下流へ要求せず、`test-case-design`がgenerator内部modelを読み直さなくても入力対象・条件・操作・期待関係を理解できるmachine meaningを持たせます。

エラー推測も同じsemantic Coverage Item経路を使い、偽のmachine target / executionを作りません。

## 1. プロダクトリスク

### `test-analysis/scripts/risk_matrix.py`

入力は採用済みschemeと確定済み評価値です。scriptはリスクを発見・採点しません。

`repository-default`:

- impact: 1〜4
- likelihood: 1〜4
- 現行4×4 matrixを正本としてlevelを返す

`project-specific`:

```json
{
  "scheme_key": "customer-risk-v1",
  "dimensions": {
    "impact": [1,2,3,4,5],
    "likelihood": [1,2,3]
  },
  "matrix": {
    "1,1": "L1"
  },
  "priority_map": {
    "L1": "低",
    "L2": "中",
    "L3": "高"
  }
}
```

- dimension値集合とmatrix keyの完全性を検証
- matrixが返すすべてのlevelに`priority_map`を必須にする
- `priority_map`の値は既存契約の`高 / 中 / 低`だけを許可する
- 入力値がscheme外、matrixに穴がある、priority mappingがない場合は`invalid_input`
- scheme採用理由はLLMへ残す
- `test-requirement-design`以降の最低優先度判定にはmapped priorityを渡し、案件固有level文字列を既存`RISK_LEVEL_ORDER`へ直接渡さない
- output payloadは`risks[]: {risk_id, level, mapped_priority}`を`risk_id`順で返す。入力にないrisk、欠落risk、重複risk rowを作らない

## 2. テスト技法候補

### `test-analysis/scripts/technique_candidates.py`

signal:

- `ordered_domain`
- `explicit_boundaries`
- `equivalence_classes`
- `multiple_discrete_conditions`
- `stateful`
- `multiple_factors`
- `explicit_flow`
- `multi_variable_domain`
- `crud_model`
- `operational_profile`
- `metamorphic_relation`
- `grammar_model`

各signalは`true / false / null`です。key欠落は`invalid_input`、`null`は未確認であり`false`ではありません。

signalから候補技法へのmappingは次で固定します。

| signal | `true`時の候補 |
| --- | --- |
| `ordered_domain` | `境界値分析` |
| `explicit_boundaries` | `境界値分析` |
| `equivalence_classes` | `同値分割` |
| `multiple_discrete_conditions` | `デシジョンテーブル` |
| `stateful` | `状態遷移` |
| `multiple_factors` | `Pairwise / 組合せ` |
| `explicit_flow` | `シナリオ / ユースケース` |
| `multi_variable_domain` | `Domain Testing` |
| `crud_model` | `CRUD Testing` |
| `operational_profile` | `Random Testing` |
| `metamorphic_relation` | `Metamorphic Testing` |
| `grammar_model` | `Syntax-Based Testing` |

複数signalが`true`の場合は候補集合のunionを返し、上表の順で安定sortします。`false`は候補を追加せず、`null`は`undetermined_signals`へ入れます。

出力payload:

```json
{
  "selection_key": "selection-001",
  "candidates": ["境界値分析"],
  "undetermined_signals": ["stateful"],
  "complete": false
}
```

outputの`selection_key`はinput値をそのまま返します。`complete`は`undetermined_signals`が空かだけを表す診断値であり、`false`だけを理由にworkflowをブロックしません。候補の最終採用は`test-analysis`が行います。Error Guessingは構造signalだけでは自動採用しません。

## 3. 同値分割 / Each Choice

### `equivalence_partitions.py`

LLMがpartition setとpartitionの意味を正規化した後を処理します。

機械処理:

- `set_key` / `partition_key`一意性
- 空partition拒否
- 同一set内のenum / finite range重複
- valid / invalidの同一値衝突
- representative value所属検証
- representativeが明示済みならpartition所属を検証してその値を使用
- representative=nullの場合、enumは宣言順の先頭値を使用
- integer rangeはfiniteなminimum / maximumを必須とし、minimum inclusiveならminimum、exclusiveならminimum+1を使用。maximumを超える場合は`invalid_input`
- decimal / date / datetime rangeでrepresentative=nullの場合はstepを勝手に仮定せず`result_status=unresolved`
- 成果物上の閉鎖
- Each Choice Coverage

成果物上の閉鎖とCoverageは分離します。`対象外`、`別テストレベル`、`残存リスク`、`ブロック中`へ閉じただけではCoverage済みと数えません。

成立不能partitionをCoverage母集団から外す場合はAuthority付きconstraintを必須にします。

## 4. 境界値分析

### `bva.py`

対応domain:

- integer
- decimal
- date
- local datetime
- fixed-offset datetime
- length / count

入力の`threshold`は仕様に明示された境界値そのものです。`side`は対象partitionがthresholdより上側か下側か、`inclusive`はthresholdを対象partitionへ含むかを表します。

`step`はdomainごとに次で固定します。

- integer / length / count: `{"unit":"integer","amount":<positive integer>}`
- decimal: `{"unit":"decimal","amount":"<positive decimal>"}`
- date: `{"unit":"day","amount":<positive integer>}`
- local / fixed-offset datetime: `{"unit":"second","amount":<positive integer>}`

規則:

- step不明時に`±1`を仮定しない
- decimalは共通exact helperの`integer coefficient + base-10 scale`表現で加減算し、Python `Decimal` context precisionへ依存しない
- fixed-offset datetimeの加減算は入力thresholdのoffsetを保持して行い、named timezone / DST ruleを推測しない
- `AT = threshold`
- 2-valueの`OTHER`は、ATが対象partition内なら反対側の最隣接値、ATが対象partition外なら対象partition側の最隣接値
- lower inclusive: `OTHER = threshold - step`
- lower exclusive: `OTHER = threshold + step`
- upper inclusive: `OTHER = threshold + step`
- upper exclusive: `OTHER = threshold - step`
- 3-valueは`BELOW = threshold - step / AT = threshold / ABOVE = threshold + step`
- lower / upperが同じ具体値になってもCoverage positionを別targetとして保持
- target keyは`bva:<boundary_key>:AT|OTHER|BELOW|ABOVE`。modeで不要なpositionは生成しない

生成値がdomainで表現不能、date/datetime演算がoverflow、stepが0以下の場合は`invalid_input`とし、別のstepを推測しません。
## 5. Domain Testing

### `domain_testing.py`

本PlanではISTQB CTAL-TA v4.0の**Reliable Domain Coverage**を実装します。Simplified Domain Coverageは別modeとして実装しません。

多変数の線形borderと、そのborderで囲まれるpartition全体を扱います。各borderの`relation`は、そのborderについて対象partitionの内側で`true`になる向きで正規化します。

入力は`partitions[]`と`borders[]`です。

partition:

```json
{
  "partition_key": "P1",
  "label": "購入金額と保有ポイントの有効領域",
  "dimensions": [
    {"dimension_key":"x","label":"購入金額"},
    {"dimension_key":"y","label":"保有ポイント"}
  ],
  "expression": {
    "op": "and",
    "args": [
      {"op":"border_ref","border_key":"B1"},
      {"op":"border_ref","border_key":"B2"}
    ]
  },
  "authority_refs": ["SPEC-001"]
}
```

partition expressionは`border_ref / and / or`だけを許可します。`not`は使用せず、補集合側を対象にする場合はrelationを反転した別borderとして正規化します。

border:

```json
{
  "border_key": "B1",
  "label": "購入金額 + 2×保有ポイント <= 10",
  "partition_key": "P1",
  "relation": "<=",
  "coefficients": {"x": "1", "y": "2"},
  "constant": "-10",
  "pivot_key": "x",
  "anchor": {"y": {"type":"decimal","value":"3"}},
  "pivot_step": "1",
  "authority_refs": ["SPEC-001"]
}
```

式は`sum(coeff_i * value_i) + constant relation 0`です。`relation`は`< / <= / > / >= / = / !=`だけを許可し、`pivot_step`は正のdecimal文字列です。

`< / <= / > / >=`のReliable Domain Coverage:

- closed border（`<= / >=`）: ON = border上、OFF = raw relationがfalseになる最隣接点、IN = raw relationがtrueになる最隣接点、OUT = OFFよりさらに1 step外側
- open border（`< / >`）: OFF = border上、ON = raw relationがtrueになる最隣接点、IN = ONよりさらに1 step内側、OUT = raw relationがfalseになる最隣接点
- target keyは`domain:<partition_key>:<border_key>:ON|OFF|IN|OUT`

`=`:

- ON = border上
- OFF_NEG / OFF_POS = borderの両側の最隣接点
- target keyは`domain:<partition_key>:<border_key>:ON|OFF_NEG|OFF_POS`

`!=`: 

- OFF = border上
- ON_NEG / ON_POS = borderの両側の最隣接点
- target keyは`domain:<partition_key>:<border_key>:OFF|ON_NEG|ON_POS`

処理:

1. partition / border key、partition参照、型、coefficient、positive stepを検証
2. partition expressionが同partitionの既知borderだけを参照することを検証
3. anchorを固定してpivot border valueを求める
4. relation別規則でcoverage pointを生成
5. 各pointを**partition expression全体**へ再代入する
6. ON / INはpartition expressionがtrue、OFF / OUTはfalseであることを検証する。`=` / `!=`も上記定義に従ってpartition所属を検証する
7. 対象borderのON pointは、同じpartitionを構成する他borderについてborder上ではなくpartition内部にあることを必須にする。対象border以外でON/OFF相当になるpointはReliable Domain Coverageの対象pointとして採用しない
8. IN pointは対象borderだけでなく同じpartitionの他borderについてもpartition内部にあることを検証する。対象border以外を意図せず跨ぐ、または他border上に乗る場合はblocking issueを返す
9. OFF / OUT pointは対象borderを跨いだ結果としてpartition外になることを確認し、別borderだけを跨いでpartition外になったpointを対象borderのrequired pointとして採用しない
10. relation別required targetがすべて生成できたときだけCoverage completeとする

coefficient、constant、anchor、pivot stepは有限decimalをexact rationalへ変換し、border座標計算はPython `fractions.Fraction`相当の有理数演算で行います。pivot border valueを求める途中でbinary floatや`Decimal` context roundingを使用しません。最終値がintegerまたは有限decimalとしてexactに表現できる場合だけtyped valueへ変換します。既約分母が2と5以外の素因数を持つ等、対応typed valueへexact変換できないrequired pointは`unrepresentable_point`としてunsupported itemへ出し、丸めたON / OFF pointを生成しません。

border valueまたは必要な隣接点がrepresentableでない、pivot coefficientが0、anchor不足、step不明、partition全体の所属条件を満たせない場合は推測しません。LLMがoverride pointを明示する場合も、scriptがpartition全体の所属とstep距離をexact arithmeticで検証し、規則に一致しなければ`invalid_input`とします。
## 6. Decision Table

### `decision_table.py`

condition / action / ruleは任意数を許可します。known ruleのaction vectorは宣言済みaction key集合と完全一致させます。

完全rule処理:

1. condition / action / rule keyと値集合を検証
2. known ruleとconstraintの直接矛盾を検出
3. hard limit内でrule spaceを列挙
4. constraintで成立不能なassignmentを識別
5. known ruleを照合
6. 未定義assignmentを`unspecified`
7. 同一assignmentの同一actionは重複、異なるactionは矛盾
8. 成立可能rule Coverageを算出

`unspecified` / 矛盾はCoverage済みとせず、構造化issueとして`question-analysis`へ送ります。

### 6.1 don't-care統合候補

完全rule setに対して、次を満たす2 ruleだけを統合候補にします。

- action vectorが完全一致
- assignmentが1 conditionだけ異なる
- 統合後に新しい未定義assignmentを包含しない
- Authority集合を保持できる

候補をdeterministicに列挙し、各候補へ`merge_key = dm:sha256:<canonical sorted rule_keys hash>`を付与します。`rule_keys`はUnicode code point順でsortした配列をcanonical JSON化してSHA-256します。LLMは意味上統合してよい候補の`merge_key`だけを`accepted_merges[]`へ返し、任意の`rule_keys[]`を新規構成しません。scriptはaccepted `merge_key`が同一実行で生成した候補に存在すること、候補内ruleが同一action vectorであること、統合後のCartesian productが成立可能な既知ruleだけを含み未定義assignmentを追加しないことを再検証してdon't-care ruleを生成します。Boolean minimizationで最小rule数を目的にしません。

`accepted_merges[]`はDecision Tableの派生表示・レビュー用のdon't-care ruleを作るためだけに使用します。元の成立可能assignment targetは削除せず、`coverage_summary.required / covered`も変更しません。異なるassignmentは`execution_fingerprint`が異なるため、accepted don't-care mergeを`materialize_coverage.py`の`merge_group`へ変換せず、元assignmentごとに別CIを維持します。TCへ複数CIを対応付ける必要がある場合は、don't-care表示を根拠に自動統合せず、`test-case-design`が具体的な前提・データ・手順・期待結果を意味判断したうえで既存の`ci_refs[]`契約を使用します。

## 7. 組合せ

### `combinatorial.py`

mode:

- `exhaustive`
- `base-choice`
- `t-wise`
- `mixed-strength`

### 7.1 exhaustive

有限domainのCartesian productをhard limit内で列挙します。成立不能assignmentはAuthority付きconstraintとともに保持します。

### 7.2 Base Choice

入力base assignment全体がSATであることを必須にします。

各factorについて、そのfactorだけをnon-base valueへ置換したassignmentを評価します。

- SATならCoverage row
- 完全探索でUNSATなら成立不能target
- 他factorまで変更して成立させる補正は行わない

これによりconstraint付きでもBase Choiceの意味を変えません。

### 7.3 Pairwise / N-wise

1. factor subsetとvalueからt-tuple候補を列挙
2. deterministic backtrackingでcompletion可能性を調べる
3. `SAT / UNSAT / limit_exceeded`を区別
4. SAT targetだけをCoverage母集団とする
5. uncovered targetをcanonical順で選ぶ
6. completion候補のうち新規Coverage target数最大を選ぶ
7. tieはvalue index辞書順
8. 100%になるまで繰り返す

最小row数は保証しません。

### 7.4 mixed-strength

入力:

```json
{
  "global_strength": 2,
  "subsets": [
    {"factor_keys": ["role","plan","region"], "strength": 3}
  ]
}
```

Coverage targetはglobal strength targetとsubset追加targetの和集合です。同一targetはcanonical keyで重複除去します。feasibility、greedy、limit規則はN-wiseと同じです。

## 8. Classification Tree

### `classification_tree.py`

LLMがclassification / classの意味を定義した後、`classification_tree.py`がdeterministic adapterとしてfactor / valueへ変換し、`combinatorial.py`へ直接渡します。adapter出力をLLMが再生成しません。

入力required key:

- `classifications[]`
- 各classificationの`classification_key / label`
- `classes[]`
- 各classの`class_key`
- Authority / constraint refs

出力`derived.combinatorial_input`は`factors[] / constraints[]`を持ち、`combinatorial.py`の同名fieldと直接互換にします。`mode / strength / mixed-strength subsets / base_assignment`は組合せ戦略の意味判断なのでLLMが別fieldとして決め、固定builderが`derived.combinatorial_input`へjoinします。LLMがfactor / class / constraintを再生成しません。

## 9. 状態遷移

### `state_transition.py`

各stateは`state_key / label / authority_refs`、各transitionは`transition_key / from / event / guard_status / guard_refs / to / authority_refs`を持ちます。`label`は下流でstable keyを再解釈せず状態の意味を扱うための非空文字列です。

入力:

- `states[]`
- `initial_states[]`
- `terminal_states[]`
- `transitions[]`
- `reset_options[]`
- `invalid_transition_candidates[]`
- `coverage_mode`
- `switch_count`（`coverage_mode=n-switch`だけ必須）

`guard_status=true|false|null`と`guard_refs[]`を使います。`false`をCoverage母集団から外すには`guard_refs`にAuthorityを1件以上必須とします。initial stateから`true` edgeだけで到達可能なstateをsourceに持つ`guard_status=null` transitionがある場合はCoverage母集団が確定しないため`result_status=unresolved`とし、100% Coverageを返しません。`null`を含むsequenceは正式Coverage targetにしません。

Coverage定義:

- `all-states`: model内の全state。initial stateから`guard_status=true` transitionだけでsetupできないstateが1件でもあればrequired集合から黙って除外せず`result_status=unresolved`とする
- `valid-transitions`: model内で`guard_status=true`と確定した全valid transition。source stateへsetupできないtransitionが1件でもあればrequired集合から黙って除外せず`result_status=unresolved`とする
- `n-switch`: `switch_count=N`として、到達可能なN+1個の連続するvalid transitionの全sequence。Nは0..10。N>=2は高いfailure risk、ユーザー明示、案件固有基準等の具体的理由を`coverage_selection_reason`へ必須で残す
- `round-trip`: 到達可能なsimple cycle。開始stateと終了stateは同一で、それ以外のstateをsequence内で重複させない。self-loopも1 transitionのround-tripとして含める。開始stateが異なるround tripは別Coverage targetとして扱う
- `invalid-transitions`: 明示されたinvalid transition candidateだけ

stable target:

- state: `state:node:<state_key>`
- transition: `state:transition:<transition_key>`
- n-switch: `state:n-switch:<N>:sha256:<transition_key_sequence_hash>`
- round-trip: `state:round-trip:<start_state_key>:sha256:<transition_key_sequence_hash>`
- invalid: `state:invalid:<candidate_key>`

round-tripは開始stateをCoverage identityの一部とし、transition key列をrotationして同一化しません。同じ閉路でも開始stateが異なる場合は別targetです。同じ開始stateかつ同じtransition key列だけを重複として除去し、逆方向はtransition列が異なるため別cycleです。

invalid transition candidateは`{"candidate_key":"INV-001","from":"draft","event":"publish","authority_refs":["SPEC-010"]}`形式です。

reset:

```json
{
  "reset_key": "RESET-1",
  "from_states": ["*"],
  "to_state": "draft",
  "action": "下書き状態へ戻す",
  "authority_refs": ["SPEC-010"]
}
```

### 9.1 setup prefixとcanonical execution

各materializable targetについてCoverage開始stateへの実行contextを次で一意に決めます。

1. 各`initial_states[]`から`guard_status=true`だけを使うshortest pathを探索する
2. direct候補は`(path長, initial_state_key, transition key列)`で昇順
3. direct候補がなければ、各initial stateで適用可能なresetごとにreset後stateから`guard_status=true`だけのshortest pathを探索する
4. reset候補は`(path長, initial_state_key, reset_key, transition key列)`で昇順
5. `guard_status=null`を含むpathは構造候補に留め、正式executionにしない
6. setupが得られないtargetをCoverage済みにしない

canonical execution:

```json
{
  "initial_state_key": "draft",
  "initial_state_label": "下書き",
  "reset_key": null,
  "reset_execution": null,
  "setup_prefix": [],
  "coverage_sequence": [
    {
      "transition_key":"T-001",
      "from":{"state_key":"draft","label":"下書き"},
      "event":"publish",
      "to":{"state_key":"published","label":"公開済み"}
    }
  ],
  "attempted_transition": null
}
```

- resetなしでは選択した`initial_state_key`を保存する
- resetありではresetを実行する起点の`initial_state_key`と`reset_key`を保存し、`reset_execution={reset_key, action, from_state_key, to_state:{state_key,label}}`を持たせる。reset後のtransitionだけを`setup_prefix`へ入れる
- `initial_state_label`、`reset_execution`、`setup_prefix / coverage_sequence`のstate labelと`event`を含め、stable keyだけでなく下流が実行手順を作るための自己完結machine meaningを持つ
- valid targetでは`coverage_sequence`を使用する
- invalid transitionでは`coverage_sequence=[]`、`attempted_transition={candidate_key, from, event}`
- initial stateそのものをCoverageする場合も`initial_state_key`をexecution identityへ含める

## 10. Use Case / シナリオ

### `flow_paths.py`

入力は`nodes[] / edges[] / initial_node_keys[] / regions[] / loop_specs[] / coverage_mode / max_path_length`です。

node kind:

- `normal`
- `fork`
- `join`
- `terminal`

`nodes[]`の各nodeは`node_key / label / kind / authority_refs`を持ち、`label`は非空文字列です。`initial_node_keys[]`は1件以上必須で、すべて既知nodeを参照します。terminal到達を要求するpath criterionでは`kind=terminal`のnodeを終点にします。

edgeは`edge_key / from / to / guard_status / guard_refs / label / authority_refs`を持ち、`guard_status=true`だけを正式Coverage対象へ使います。`guard_status=false`をCoverage母集団から外すには`guard_refs`にAuthorityを1件以上必須とします。initial nodeから`true` edgeだけで到達可能なnodeをsourceに持つ`guard_status=null` edgeがある場合は`result_status=unresolved`とし、node / edge / path / loop / fork-joinの100% Coverageを返しません。

fork / join regionは曖昧に導出せず、次を正規化入力として明示します。

```json
{
  "region_key":"RG-001",
  "fork_node_key":"F1",
  "join_node_key":"J1",
  "branches":[
    {"branch_key":"BR-001","edge_keys":["E1","E2"]},
    {"branch_key":"BR-002","edge_keys":["E3"]}
  ]
}
```

- branchの`edge_keys`はforkからmatching joinまで連続するpathであることをscriptが検証する
- 同一regionのbranch keyは一意
- nested regionはbranch path内に含めてよい
- region同士がcrossingする場合は`unsupported`
- scheduler interleavingは仕様なしに生成しない
- fork-join targetは直接linear executionへ落とさずsemantic Coverage Itemへ閉じる

simple loopは次を明示します。

```json
{
  "loop_key":"LP-001",
  "entry_node_key":"N1",
  "edge_keys":["E10","E11"],
  "exit_edge_keys":["E12"],
  "typical_iterations":3,
  "maximum_iterations":10,
  "authority_refs":["SPEC-020"]
}
```

- `edge_keys`はentryへ戻るsimple cycleで、途中node重複を禁止する
- `exit_edge_keys[]`は1件以上で、すべてentryから出る`guard_status=true` edge、cycleの最初のedgeとは別key
- `typical_iterations`は2以上のinteger必須
- `maximum_iterations`はnullまたは`typical_iterations`以上のinteger
- Coverage targetは0回、1回、typical回、maximum回。maximumがnullまたはtypicalと同値なら重複targetを作らない
- executionは`prefix + cycle×N + canonical exit`とし、exitは`exit_edge_keys[]`のUnicode code point辞書順先頭を使う
- 0回targetでもexitを実行し、空sequenceで代用しない
- canonical exitを実行できないloop specは`invalid_input`

`max_path_length`は1〜1000 edgeのintegerです。

Coverage mode:

- `node`: initialから到達可能な全node
- `edge`: initialから到達可能な全feasible edge
- `bounded-path`: initialからterminalへ到達する、長さ`<= max_path_length`の全feasible path
- `simple-loop`: `loop_specs[]`で明示したloop iteration target
- `fork-join`: `regions[]`の各branchを少なくとも1回含むtarget

stable target:

- node: `flow:node:<node_key>`
- edge: `flow:edge:<edge_key>`
- bounded path: `flow:path:sha256:<edge_key_sequence_hash>`
- simple loop: `flow:loop:<loop_key>:<iterations>`
- fork / join: `flow:branch:<region_key>:<branch_key>`

node / edge / bounded-path / simple-loopのmaterializable targetは各initial nodeからCoverage開始点まで`guard_status=true`だけのshortest prefixを求め、同長は`(initial_node_key, edge key列)`で辞書順に固定します。bounded-pathはterminal到達を必須とし、terminalへ到達しない候補は正式targetにせず診断metadataへ保持します。

canonical executionは選択した`initial_node_key / initial_node_label`、Coverage対象の`target_node={node_key,label}`、各edgeについて`edge_key / from:{node_key,label} / label / to:{node_key,label}`を持つ`edge_sequence`を保存します。node targetがinitial node自身で`edge_sequence=[]`でも`target_node`から意味を解決でき、stable key列だけを渡して下流にmodel再解決させません。

## 11. CRUD Testing

### `crud_matrix.py`

ISTQB CTAL-TA v4.0に合わせ、CRUD Testingは**completeness**と**consistency**を分けて扱います。

入力:

- `entities[]`（`entity_key / label / authority_refs`）
- `functions[]`（`function_key / label / authority_refs`）
- `cells[]`
- `consistency_sequences[]`
- `operation_dispositions[]`

completeness:

- entity / function / operation key一意性
- cell重複、unknown entity / function / operationを拒否
- matrixに明示された各operationをCoverage targetとする
- target keyは`crud:op:<entity_key>:<function_key>:<C|R|U|D>`
- entityごとにC/R/U/Dの各operationがmatrix全体で1回も存在しない場合、`crud:missing:<entity_key>:<C|R|U|D>` anomalyを生成する
- missing operationは即欠陥とは断定せず、`operation_dispositions[]`にAuthority付きの`not_applicable`がなければ`result_status=unresolved`として`question-analysis`へ送る
- `operation_dispositions[]`: `{entity_key, operation, handling, reason, authority_refs}`。`handling`は`not_applicable`だけを許可し、Authority 1件以上を必須とする
- 個々の空cellだけを理由に欠陥扱いしない

consistency:

`consistency_sequences[]`はLLMが業務意味を正規化した後のsequenceです。generatorはentity / function keyを現在inputへ解決し、materializable executionには対応する`entity_label / function_label`も複製します。下流はCRUD keyだけを見て意味を推測しません。

```json
{
  "sequence_key": "SEQ-001",
  "entity_key": "customer",
  "kind": "lifecycle",
  "steps": [
    {"function_key":"create_customer","operation":"C"},
    {"function_key":"read_customer","operation":"R"},
    {"function_key":"delete_customer","operation":"D"}
  ],
  "authority_refs": ["SPEC-001"]
}
```

- `kind`は`lifecycle / negative`
- 各stepがCRUD matrixに存在するoperationを参照することを検証
- lifecycle sequenceでは、そのentityの適用対象operationを全体として1回以上Coverageすることを要求
- `not_applicable` disposition済みoperationはlifecycle Coverage母集団から除外する
- negative sequenceはAuthorityで明示された「未作成のR/U/D」「削除後のR/U/D」等だけを入力し、scriptが業務上の禁止操作を創作しない
- sequence target keyは`crud:seq:<sequence_key>`

`coverage_summary`は`completeness`と`consistency`を別々に返し、両方completeでのみCRUD modelをcompleteとします。未処置missing operationまたはconsistency sequence未正規化があれば`result_status=unresolved`とし、completenessだけで「CRUD Testing完了」と表現しません。
## 12. Cause-Effect Graph

### `cause_effect.py`

boolean AST:

- `ref`
- `not`
- `and`
- `or`

effectはcauseだけを参照します。循環参照は禁止します。

入力は`causes[] / effects[] / constraints[]`です。`constraints[]`は§25.1の共通partial assignmentをcause keyへ適用し、Authority付きのcause間成立不能条件を表します。constraintをLLMが派生先で作り直しません。

1. cause / effect key、AST参照、constraintのcause key / valueを検証する
2. hard limit内で全cause assignmentを列挙する
3. constraintに一致するassignmentを成立不能として識別し、正式known rule / Coverage母集団へ入れない
4. 成立可能assignmentだけeffect action vectorへ変換する
5. `derived.decision_table.conditions / actions / known_rules / constraints / accepted_merges=[]`を生成する。conditionはcauseの`cause_key / label`、actionはeffectの`effect_key / label`を失わずDecision Table互換schemaへ渡し、入力`constraints[]`も同じ意味のまま渡す

`derived.decision_table`は`decision_table.py`のscript固有inputと直接互換にし、Cause-Effect側で意味上のmergeを作りません。cause / effectのlabelを派生先でLLMが再生成しません。

## 13. Syntax-Based Testing

### `grammar_cases.py`

自然言語grammarをparseせず、正規化済みproductionを受けます。`input_label`には生成文字列を適用する入力対象を非空文字列で渡し、全materializable targetの`execution`へそのまま保持します。

derivationは**leftmost derivation**で固定します。sentential formに複数nonterminalがある場合、常に最左のnonterminal occurrenceだけへ次productionを適用します。

`max_depth`はparse tree depthで、start symbolを0、productionで生成したchildをparent + 1と数えます。生成childが`max_depth`を超えるproduction適用は探索しません。`rhs=[]`はepsilon productionとして許可します。

production Coverage targetごとに、対象productionを1回以上含むleftmost derivationのうちproduction適用回数最小を選び、同数ならproduction key列のUnicode code point辞書順で決めます。leftmost規則により同じproduction key列から異なる文字列を生成しません。

valid case集合は各production Coverage targetのshortest derivationのunionとし、生成文字列とproduction key列が同一のcaseを重複除去します。production Coverage達成に不要な追加grammar列挙は行いません。

invalid syntaxは補集合から生成しません。明示mutationは`delete_terminal / replace_terminal / insert_terminal`だけを許可します。

- `delete_terminal`: `symbol_index`が指すterminal itemを削除する
- `replace_terminal`: `symbol_index`が指すterminal itemを明示replacement文字列へ置換する
- `insert_terminal`: RHS配列の`symbol_index`位置へ明示terminal文字列を挿入し、0..len(rhs)を許可する
- delete / replaceで対象itemがnonterminalなら`invalid_input`

mutationは指定productionのRHSを1回だけ変換した一時grammarへ適用します。その一時grammarで変換したproductionを1回以上使うleftmost derivationのうちproduction適用回数最小を探索し、同数ならproduction key列のUnicode code point辞書順で決めます。`max_depth`内で導出不能なら`unreachable_mutation` issueを返します。

stable targetはproduction Coverageを`syntax:prod:<production_key>`、mutation候補を`syntax:mutation:<mutation_key>`とします。mutation結果は`invalid_candidate`であり、scriptだけで製品上invalidと断定しません。製品上invalidであることをexpected resultへ昇格するにはAuthorityまたはLLMの意味判断を必須にします。

## 14. schema / HTML

### `schema_cases.py`

machine-readableな入力はscriptが直接正規化します。JSON Schema 2020-12、OpenAPI 3.0、HTML form constraintは別semanticsとして扱い、同じkeyword名だけを理由に意味を共通化しません。

### JSON Schema 2020-12

runtime-v1の対応subset:

- `type`
- `$defs`（対応可能なlocal referenceの参照先container）
- `$ref`
- `properties`
- `items`
- `enum`
- `const`
- `required`
- `minimum / maximum`
- `exclusiveMinimum / exclusiveMaximum`
- `multipleOf`
- `minLength / maxLength`
- `minItems / maxItems`
- `minProperties / maxProperties`

`$ref`はruntime内でnetwork解決しません。runtime-v1で対応するreferenceは同一schema resource内の`#/...` JSON Pointerだけです。root schemaの`$id`はmetadataとして保持できますが、subschemaに`$id`があり別schema resource / base URIを形成するdocument、plain-name fragment、`$anchor / $dynamicAnchor / $dynamicRef`、外部URI referenceは`unsupported`です。これによりnested `$id`を無視してdocument rootへ誤解決しません。

JSON Schema 2020-12では`$ref`のsibling keywordも評価対象です。したがって`$ref`と並ぶ対応subset keywordは通常どおり評価し、未知またはruntime-v1非対応keywordがvalidation意味へ影響する場合はそのsubtreeを`unsupported`にします。`$ref`があるという理由でsiblingを捨てません。

`type`は単一type文字列、または`[<non-null type>, "null"] / ["null", <non-null type>]`の2要素だけを対応し、2要素形式は`allows_null=true`へ正規化します。それ以外のunion typeは`unsupported`です。

`$schema`とroot `$id`はdocument metadataとして保持します。validationへ影響しないannotationとして無視してよいkeywordは`title / description / $comment / default / examples`だけです。その他の未知keywordを「制約なし」として扱いません。

JSON numberは`_02` §3.1の専用number tokenとしてstring値と区別してdecodeし、token長・grammar検証後にcanonical integerまたは`integer coefficient + base-10 scale`へexact正規化します。binary floatやPython `Decimal` context precisionへ意味を依存させません。

`enum / const`のruntime-v1対応範囲はscalar / nullだけです。string、boolean、integer、finite decimal、nullは対応し、object / arrayを値として持つsubtreeは`unsupported`です。

### OpenAPI 3.0 Schema

OpenAPI 3.0はJSON Schema 2020-12として解釈しません。runtime-v1ではPlanで列挙したSchema Object subsetだけをOpenAPI 3.0 semanticsで処理します。

- `nullable`はOpenAPI 3.0固有semanticsとしてsingle base typeにnull許容を加える
- `exclusiveMinimum / exclusiveMaximum`はOpenAPI 3.0のboolean形式として扱う
- `context=request|response`を必須にし、`readOnly=true` propertyはrequest側required / test data母集団から除外し、`writeOnly=true` propertyはresponse側required / expected response母集団から除外する
- 同一propertyで`readOnly=true`かつ`writeOnly=true`は`invalid_input`
- `title / description / default / example / deprecated`はannotationとして保持してもvalidation Coverageへ使用しない
- Reference Objectは`$ref`だけを意味fieldとして扱う。OpenAPI 3.0のReference Objectへ追加されたpropertyは仕様どおり無視し、参照先schemaのsibling assertionとして解釈しない
- runtime-v1で対応するreferenceは同一OpenAPI document内のlocal JSON Pointerだけ。外部document referenceは事前dereference済み入力を要求する
- JSON Schema 2020-12だけのkeywordをOpenAPI 3.0へ暗黙適用しない

### HTML form control

runtime-v1でconstraint生成対象とする`type`は`text / number / date / datetime-local`だけです。それ以外のnative control typeはUI pattern候補として扱えても`schema_cases.py`ではcontrol subtreeを`unsupported`にします。

受け取る属性:

- `type`
- `required`
- `min / max`
- `minlength / maxlength`
- `step`
- `value`
- `pattern`
- `disabled`
- `readonly`
- `multiple`

type別の扱い:

- `text`: `required / minlength / maxlength`
- `number`: `required / min / max / step / value`
- `date / datetime-local`: `required / min / max`。runtime-v1ではdate/time系`step`を対応しない
- 対応typeでHTML Standard上そのattributeが適用されない場合はvalidation constraintへ変換せずmetadataとして保持する
- `disabled=true`、または対応typeで`readonly=true`の場合はconstraint validation対象外としてvalidation targetを生成しない
- `pattern`がvalidationへ適用されるcontrolはECMAScript RegExpをPython `re`で代用せず、そのcontrol validationを`unsupported`にする
- `multiple`がvalidation意味を持つtypeはruntime-v1の対応type外なので`unsupported`とする

HTML `number`のstepはHTML Standardのstep semanticsへ合わせます。

- `step`省略時はdefault step = 1
- `step="any"`ではallowed value stepなしとし、grid constraintを生成しない
- positive finite `step=s`ではallowed step = s
- step baseは有効な`min`、次に有効な`value`、それもなければ0の順で決める
- invalid / zero / negative step tokenはHTML semanticsどおりdefault step=1へfallbackする。制約なしとして扱わない
- numberのdefault stepもstep mismatchへ影響するため、`step`属性がないことを「gridなし」と解釈しない

`multipleOf`と対応可能なnumber stepは`grid` constraintへ正規化します。

```json
{
  "operator":"grid",
  "base":{"type":"decimal","value":"0"},
  "step":{"type":"decimal","value":"0.5"}
}
```

`grid`はschema Coverage候補とBVA / combinatorial入力へ渡しますが、`test_data_requirements.py`のintersection対象にはしません。

`allOf / anyOf / oneOf / not / if / then / else`等、対応subset外でvalidation意味を変えるkeywordは`unsupported`です。unsupported keywordがvalidation意味へ影響するsubtreeだけを切り離し、独立して評価できる別property / itemは継続できます。親schemaのvalidation意味をunsupported keywordが左右する場合は、その親subtree全体を`unsupported`にします。

正規化後のrange / enum / required等は`derived.ep_inputs / derived.bva_boundary_skeletons / derived.combinatorial_constraints / derived.test_data_requirements`へ固定schemaで出力します。EPのset / partition、BVA boundary、combinatorial factorにはsource JSON Pointer / property名から決定論的に作る非空`label`を含めます。`derived.bva_boundary_skeletons`は`boundary_key / label / side / threshold / inclusive / step / authority_refs`までを持ち、`mode / coverage_selection_reason`は含めません。LLMがその2 fieldだけを追加し、固定builderが`bva.py` inputへ変換します。

## 15. UI pattern

### `ui_pattern_candidates.py`

入力は正規pattern名またはaliasと、対象から確認済みの属性です。

出力は一般確認候補であり、製品expected resultではありません。

- alias解決はcatalogだけで行う
- 未知patternを推測登録しない
- catalog versionを出力へ記録
- HTML / ARIA / APG referenceは`reference_refs`
- 製品Authorityと矛盾した候補は採用しない

## 16. テストデータ要求

### `test_data_requirements.py`

入力はEP / BVA / Domain / Decision Table / combinatorial / state / CRUD / schema等の構造化要求です。

要求key例:

- role
- entity state
- partition / boundary
- field constraint
- relation
- required fixture property

対応constraint operator:

- scalar equality
- finite enum set
- integer / decimal / date / datetime range
- version range（dot-separated non-negative integer componentだけ。各componentは`0`または先頭0なし。比較時は短い側へ0を補い、`1.2 == 1.2.0`とする）
- boolean requirement

処理:

- canonical keyによる重複統合
- 同一dimensionで型互換な`eq × eq`、`eq × enum`、`eq × range`、`enum × enum`、`enum × range`、`range × range`、`version_range × version_range`をintersectionする
- `boolean`は同一dimensionのboolean同士、または型互換な`eq`との一致を検証する
- 空intersection、異なるscalar equality、range外eq等を矛盾として検出する
- 型またはoperator組合せを安全にintersectionできない場合は別要求として黙って残さず`unsupported`
- requirement → model / source target traceability。test data要求では各source targetを`{target_ref, target_content_fingerprint, generation_fingerprint}`として保持し、stable IDだけへ結び付けない

実際の個人情報・顧客データ・fixture値を自動取得しません。

## 17. Random Testing

### `random_testing.py`

再現可能性のためPRNGを`pcg32-v1`へ固定します。Python `random`の実装versionへ依存しません。

`pcg32-v1`はPCG XSH RR 64/32として次を固定します。

- multiplier: `6364136223846793005`
- 64-bit unsigned state
- init sequence: `54`
- increment: `(54 << 1) | 1 = 109`
- seeding: state=0 → 1回advance → seed加算 → 1回advance
- output permutation: XSH RR 64/32
- bounded integer: rejection samplingでmodulo biasを避ける

seed=`42`の最初の6 outputは`2707161783, 2068313097, 3122475824, 2211639955, 3215226955, 3421331566`とし、固定test vectorに使用します。bounded integerはraw output vectorだけでなく、少なくとも1つのnon-power-of-two bound（例: bound=10）についてrejection発生を含む固定vectorを契約testへ持ち、単純modulo実装への回帰を検出します。

入力:

- 非空`input_label`
- uint64 `seed`
- `case_count`（1〜10,000）
- `distribution`
- Authority / Reference

対応distribution schema:

```json
{
  "type":"uniform_finite",
  "values":[
    {"type":"integer","value":1},
    {"type":"integer","value":2},
    {"type":"integer","value":3}
  ]
}
```

- `values`は1件以上、canonical typed valueとして重複不可

```json
{"type":"uniform_integer","minimum":0,"maximum":10}
```

- minimum / maximumはinclusive integer、`minimum <= maximum`、domain size `maximum - minimum + 1 <= 2^32`

```json
{
  "type":"categorical",
  "entries":[
    {"value":{"type":"string","value":"A"},"weight":3},
    {"value":{"type":"string","value":"B"},"weight":1}
  ]
}
```

- valueはcanonical typed valueで重複不可
- weightは1〜2,147,483,647のinteger。0 / 負値 / decimalは禁止
- weight合計は1..`2^32`

uniform finite / categoricalでは宣言順をsample indexへ使います。weighted categoricalではweight累積区間を宣言順で構築し、rejection sampling後の整数をその区間へ写像します。

3 distributionはいずれも**復元抽出**とし、caseごとに独立して次の乱数を消費します。同じ値が複数caseに現れることを許可します。

同じseed、generator contract version、distributionから同じ列を返します。

Random Testingには一般的なCoverage 100%を定義しません。`completion_summary`は`required_case_count = case_count`、`generated_case_count`、`complete = generated_case_count == required_case_count`を返します。本Planのruntimeでは時間依存の終了条件を使わず、件数で正規化された場合だけ機械生成します。

Random Testingのoracleは生成しません。
## 18. Metamorphic Testing

### `metamorphic.py`

LLMがmetamorphic relationを定義した後を処理します。複数follow-upは件数だけで暗黙生成せず、各follow-upとtransform列を明示します。

各relation:

```json
{
  "relation_key": "MR-001",
  "relation_label": "金額を増やしても合計は減少しない",
  "source_inputs": [
    {"source_id":"SRC-001","value":{"amount":{"type":"decimal","value":"10"}}}
  ],
  "follow_ups": [
    {
      "follow_up_key":"FU-001",
      "transforms":[
        {"op":"add_decimal","path":"$.amount","operand":"1"}
      ]
    }
  ],
  "expected_relation": {"op":"monotonic_non_decreasing","output_path":"$.total","output_kind":"decimal"},
  "authority_refs": ["SPEC-001"]
}
```

`follow_ups[]`は1〜10,000件で`follow_up_key`をrelation内一意にします。各follow-upの`transforms[]`は1件以上で宣言順に逐次適用します。

対応input transform:

- `set`: `path`とtyped `value`
- `add_decimal`: decimal fieldの`path`とdecimal文字列`operand`
- `multiply_decimal`: decimal fieldの`path`とdecimal文字列`operand`
- `append`: arrayまたはstringの`path`と型互換な`value`
- `permute`: arrayの`path`と0..n-1の完全なbijectionである`indices`
- `sort`: homogeneous scalar arrayの`path`と`order=asc|desc`。runtime-v1で許可する要素型はnumber同士またはstring同士に限定し、numberはexact numeric order、stringはUnicode code point順で比較する。boolean / null / enumを含むsort、異種型混在は`unsupported`

JSON pathはroot `$`からobject key / array indexだけを辿る簡易pathとし、wildcard、filter、recursive descentは`unsupported`です。

対応expected relation:

- `output_kind`は`integer / decimal / scalar / unique_scalar_array / canonical_json`
- `equal / not_equal`: すべての`output_kind`
- `monotonic_non_decreasing / monotonic_non_increasing`: `integer / decimal`だけ
- `subset / superset`: `unique_scalar_array`だけ

各expected relationは`output_path / output_kind`を必須にします。scriptは実際の製品出力をまだ持たないため、実値の型検証は行わず、`op`と正規化済み`output_kind`の互換性だけを検証します。実行時に観測した出力型が異なる場合はテスト実行側で失敗として扱います。

scriptは各source inputへ各follow-upのtransform列を適用します。target keyは`mr:<relation_key>:<source_id>:<follow_up_key>`です。

Metamorphic Testingには一般的なCoverage 100%を定義しません。`completion_summary`は`required_pairs = source_inputs数 × follow_ups数`、`generated_pairs`、`complete = generated_pairs == required_pairs`を返します。各MRを1回実行したことを「十分なCoverage」と表現しません。

relationが製品に妥当か、source input集合、follow-up transform、出力のどのfieldへ期待関係を適用するかはLLMがAuthorityとともに正規化します。
## 19. テスト環境要求

### `test-analysis/scripts/environment_requirements.py`

構造化済み要求例:

- browser / version range
- OS / device class
- role / permission
- feature flag
- external integration
- locale / timezone requirement
- network / storage等の前提

対応constraint operatorは`test_data_requirements.py`と同じく、scalar equality、finite enum set、numeric / date / datetime range、version range、boolean requirementです。同じdimensionの要求は`test_data_requirements.py`と同じcross-operator intersection規則で統合し、互換しない値を矛盾として返します。未対応operatorまたは安全にintersectionできない型組合せは`unsupported`とし、環境を実際に準備・検出しません。

## 20. 変更影響分析

### `change_impact.py`

`_02`で定義したnode / edge契約だけを使用します。

- changed nodeから許可edgeを探索する
- Authority / TR / TCN / CI / TC候補を重複除去する
- dangling edge / unknown nodeを検出する
- 意味上のedgeを新規推測しない

payloadの`paths[]`は各impacted nodeに対する**shortest impact pathを1本**だけ返します。探索中のvisitedはgraph全体で「一度見たnodeを永久に捨てる」集合にせず、shortest distanceとcanonical predecessorを管理します。同じ最短距離の候補が複数ある場合はedge key列、次にnode key列のUnicode code point辞書順で1本へ固定します。cycleはshortest distanceを改善しない再訪として打ち切ります。

出力はimpacted nodeをnode key順、pathを終点node key順でcanonical sortします。all simple pathsの列挙は行いません。

## 21. テスト要求の構造処理

### `requirement_structure.py`

LLMはTRの本文、テストレベル / 観測方法と、既存TRを再利用するか新規TRにするかを判断します。これらの意味fieldもruntime inputへそのまま渡し、structure scriptは内容を生成・要約せずschemaと構造だけを検査します。Dispositionのmachine schemaはstructure / traceabilityで共通して`{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`とし、`covered_by_entity`は不要なhandlingではnullです。既存ID再利用時は`reuse_id`、新規時は`new`を指定し、runtimeが最終TR IDを割り当てます。

LLM draft後に次を計算します。

- Authority / RiskがTRまたはDispositionのどちらか一方へ閉じるか
- unknown upstream ID
- linked + disposed重複
- 関連Product Riskからの最低優先度
- TRの指定優先度が最低優先度以上ならそのまま保持
- 指定優先度が最低優先度より低く`priority_override_reason`が空ならviolation
- 指定優先度が低くても`priority_override_reason`が非空ならoverrideとして保持し、runtimeが自動で優先度を書き換えない
- reuse指定のTR IDが直前成果物系列に存在し、同じIDを複数draftへ割り当てていないことを検証する
- new指定だけ既存最大TR番号+1から採番し、削除済みTR番号を再利用しない
- outputへactive / deletedを含む`tr_id_state[]`を返し、次回の`previous_tr_ids[]`の正本にする

TR本文、テストレベル / 観測方法、粒度、既存TRとの意味上の同一性は変更・推論しません。runtime outputと入力meaning fieldを固定builderでjoinし、`_02` §4.4のTR Machine Entityを作ります。

## 22. テストケースの構造処理

### `case_structure.py`

LLMはTCのタイトル / 目的、前提・手順・データ・expected result・事後状態 / 後処理と、既存TCを再利用するか新規TCにするかを判断します。これらの意味fieldもruntime inputへそのまま渡し、structure scriptは内容を生成せず構造・参照・優先度・expected result番号とAuthority対応を検査します。Dispositionは`requirement_structure.py`と同じ共通schemaを使用します。既存ID再利用時は`reuse_id`、新規時は`new`を指定し、runtimeが最終TC IDを割り当てます。

LLM draft後に次を計算します。

- TCN / CIがTCまたはDispositionへ閉じるか
- unknown upstream ID
- linked + disposed重複
- Coverage Itemから要求される最高優先度
- TCの指定優先度が要求優先度以上ならそのまま保持
- 指定優先度が要求より低く`priority_override_reason`が空ならviolation
- 指定優先度が低くても`priority_override_reason`が非空ならoverrideとして保持し、runtimeが自動で優先度を書き換えない
- 番号付きexpected resultとAuthority対応
- reuse指定のTC IDが直前成果物系列に存在し、同じIDを複数draftへ割り当てていないことを検証する
- new指定だけ既存最大TC番号+1から採番し、削除済みTC番号を再利用しない
- outputへactive / deletedを含む`tc_id_state[]`を返し、次回の`previous_tc_ids[]`の正本にする

具体的なタイトル / 目的、前提・操作・データ・expected result・事後状態 / 後処理、既存TCとの意味上の同一性は生成・推論しません。runtime outputと入力meaning fieldを固定builderでjoinし、`_02` §4.4のTC Machine Entityを作ります。

## 23. traceability

### `coverage-analysis/scripts/traceability.py`

対象はテスト設計です。

- Authority / Risk → TRまたはDisposition
- TR → TCNまたはDisposition
- TCN → CI → TC、または各層の既存Skill契約で許可されたDisposition
- CIなし契約のTCN → TCまたはDispositionは、そのTCNにactiveなCoverage所有modelが存在せず、既存Skill契約が明示的にCIなしを許可する場合だけ認める
- missing edge
- orphan
- unknown reference
- stale downstream

許可する直接edgeは`Authority→TR`、`Risk→TR`、`TR→TCN`、`TCN→CI`、`CI→TC`、条件付きのCIなし`TCN→TC`だけです。CIなし`TCN→TC`は当該TCNにactiveなCoverage所有modelが0件で、既存Skill契約が明示的に許可する場合だけ有効です。Coverage所有modelが1件でもあるTCNでは、current materialize runtime unitの`model_completion[]`とcurrent unsupported closureから各modelの完了を先に検査し、直接edgeをCoverage closureの代替にしません。別層を飛び越えるedgeや逆向きedgeをclosure根拠として数えません。Dispositionは既存各Skillのhandling集合と必要なreason / Authority条件を検証し、正常なDispositionをmissing扱いしません。

技法別Coverage数値は各技法scriptを正本とし、traceabilityで再計算しません。

## 24. 複数Coverage targetの扱い

CI単位の`merge_group`と、TCが複数CIを参照する意味判断を分離します。

`materialize_coverage.py`の`merge_group`は、同一TCN・同一`model_key`・同一`execution_fingerprint`・同一`expected_result_root`のtargetだけを対象にします。LLMはその範囲で`merge_group`を明示し、scriptは次を機械統合します。

- Covered Target Refs
- Authority refs
- Reference refs
- 優先度は既存規則の最高値
- 追加test data requirements

異なるmodel / 技法、異なるexecution、異なるexpected resultを同一CIへ統合しません。異なるCIを1つの詳細TCで検証できるかは`test-case-design`の意味判断に残し、成立する場合だけ1つのTC draftの`ci_refs[]`へ複数CIを明示します。runtimeはこのTC判断を`merge_group`へ逆変換しません。

## 25. script別入出力契約

次のkeyを全実装で固定します。hash targetは、指定したcanonical objectをSHA-256し`sha256:<64 lowercase hex>`で表します。

| script | required input | stable result / target key | 主payload |
| --- | --- | --- | --- |
| `risk_matrix.py` | `scheme, risks[]` | `risk_id` | level、mapped priority |
| `technique_candidates.py` | 全signal、selection key | `selection_key` | candidates、undetermined、complete |
| `change_impact.py` | changed node、nodes、edges | `impact:<node_key>` | impacted nodes / paths |
| `environment_requirements.py` | requirements[] | `env:<requirement_key>` | merged requirements / conflicts |
| `analysis_entities.py` | test-analysis意味field + current runtime result | `(entity_type, entity_ref)` | Machine Entity / expected identity |
| `requirement_structure.py` | authorities、risks、TR、Disposition、previous ID state | `violation:<type>:<entity_id>` | violations / derived priority / TR ID mapping |
| `condition_structure.py` | TCN、models、previous ID state | `violation:<type>:<entity_id>` | violations / TCN・model key mapping |
| `equivalence_partitions.py` | sets[] / partitions[] | `ep:<set_key>:<partition_key>` | representative / Coverage |
| `bva.py` | boundaries[] | `bva:<boundary_key>:<position>` | typed value / Coverage |
| `domain_testing.py` | partitions[] / borders[] | §5のpartition + border + relation別key | point / Coverage |
| `decision_table.py` | conditions、actions、known rules、constraints、accepted merges | `dt:sha256:<assignment_hash>` | rule assignment / action vector / Coverage |
| `combinatorial.py` | mode、factors、constraints、strength | `comb:<mode>:sha256:<target_hash>` | target tuple / rows / Coverage |
| `classification_tree.py` | classifications[] / classes[] / constraints[] | `class:<classification_key>:<class_key>` | `derived.combinatorial_input` |
| `state_transition.py` | states、transitions、reset、coverage mode、n-switch時switch_count | §9のstate / transition / n-switch / round-trip / invalid key | setup / sequence / Coverage |
| `flow_paths.py` | nodes、edges、initial nodes、regions、loop specs、max path length、coverage mode | §10のnode / edge / path / loop / branch key | paths / loops / branch Coverage |
| `crud_matrix.py` | matrix、consistency sequences、operation dispositions | §11のoperation / missing / sequence key | completeness / consistency / anomalies |
| `cause_effect.py` | causes、effects、constraints、AST | `ce:sha256:<cause_assignment_hash>` | Decision Table互換rules |
| `grammar_cases.py` | start、key付きproductions、max depth、mutations | `syntax:prod:<production_key>`、mutationは`syntax:mutation:<mutation_key>` | derivations / production Coverage |
| `schema_cases.py` | `schema_kind, document, schema_pointer, context` | `schema:sha256:<source_hash>` | normalized constraints / downstream inputs / unsupported subtrees |
| `ui_pattern_candidates.py` | pattern / alias、attributes | `ui:<pattern_key>:<candidate_key>` | candidate / references |
| `test_data_requirements.py` | requirements[] | `data:<requirement_key>` | merged requirements / conflicts |
| `random_testing.py` | seed、case count、distribution | `random:case:<1-based zero-padded 6 digits>` | generated input / completion |
| `metamorphic.py` | relations[] | §18 key | follow-up input / completion |
| `case_structure.py` | TCN / CI / TC / Disposition | `violation:<type>:<entity_id>` | violations / derived priority |
| `traceability.py` | nodes / edges / dispositions / runtime units / Machine Entity state | `gap:<type>:<entity_id>` | gaps / orphan / stale / closed dispositions |
| `materialize_coverage.py` | TCN、generator targets、target annotations、previous mapping、merge groups | target ref → CI ID | CI mapping / stale / machine rows |
| `workflow_runtime.py` | runtime units、current Machine Entities / runtime units、unsupported item closure | `runtime_unit_key` | runtime / Entity freshness、stale propagation、completion blockers |

assignment / tuple / sequence / pathのhash対象はIDや表示文ではなく、そのtargetを定義するcanonical key/value構造だけです。hash collisionを検出した場合は`internal_error`として停止し、別targetを同一keyへ統合しません。

### 25.1 共通値schema

技法model内の業務値は、Pythonの型同一視へ依存しないよう次のtyped valueを使用します。

```json
{"type":"integer","value":1}
{"type":"boolean","value":true}
{"type":"string","value":"A"}
{"type":"enum","value":"admin"}
{"type":"decimal","value":"0.10"}
{"type":"null","value":null}
{"type":"date","value":"2026-09-19"}
{"type":"local_datetime","value":"2026-09-19T12:30:00"}
{"type":"fixed_offset_datetime","value":"2026-09-19T12:30:00+09:00"}
```

- integerはstrict JSON decodeで取得した専用number tokenをgrammar / raw length検証してからcanonical integerへ変換する。JSON stringの`"1"`と混同しない
- decimalはtyped valueでは符号付き10進文字列で指数表記を禁止し、共通exact helperで`integer coefficient + base-10 scale`へ正規化する。Python `Decimal` context precisionやbinary floatへ結果を依存させない
- raw numeric tokenとcanonical numeric representationはいずれも4096 chars上限。超過時は`limit_exceeded`とし、丸めない
- date / datetimeは`_02`のISO 8601契約へ従う
- enumとstringは同じ文字列でも別型として扱う
- nullは`value:null`だけを許可する
- assignmentのvalueはすべてtyped value

共通constraint:

```json
{
  "constraint_key":"C1",
  "assignment":{"role":{"type":"enum","value":"guest"}},
  "authority_refs":["SPEC-001"]
}
```

`assignment`は1件以上のfactor / condition keyを持つpartial assignmentです。

### 25.2 script固有input schema

以下で`required`に記載したfieldは必須、`optional`に記載したfieldだけ省略可能です。未知fieldは`invalid_input`です。配列内の`*_key` / IDは各配列内一意です。

#### `risk_matrix.py`

- required: `scheme`, `risks[]`
- `scheme.kind = repository-default | project-specific`
- repository-default: `scheme_key="risk-scheme-v1"`
- project-specific: `_03` §1の`scheme_key / dimensions / matrix / priority_map`を必須
- `risks[]`: `{risk_id, impact, likelihood}`。impact / likelihoodはschemeで宣言したinteger value

#### `technique_candidates.py`

- required: `selection_key`, `signals`
- `selection_key`はstable result keyとして`_02` §3.2と同じ`^[A-Za-z][A-Za-z0-9._-]{0,64}$`を使用し、`:`を許可しない
- `signals`は§2で列挙した12 keyをすべて持ち、値は`true / false / null`
- signal以外の技法選択、`selection_source`、最終採用技法はこのscript入力に含めない

#### `change_impact.py`

- required: `changed_node_keys[]`, `nodes[]`, `edges[]`
- node: `{node_key, node_type, source_ref, change_kind, expected_impact}`。`change_kind / expected_impact`は非空文字列またはnullで、探索順・到達判定には使わずMachine Entityへそのまま保持する
- `node_type = Authority | Risk | TR | TCN | CI | TC`
- edge: `{edge_key, from, to, edge_type, evidence_refs[]}`
- `edge_type = depends_on | traces_to | derived_from`
- changed nodeはnodesに存在必須

#### `environment_requirements.py` / `test_data_requirements.py`

- environment required: `requirements[]`
- test data required: `requirements[]`, `current_source_targets[]`
- `current_source_targets[]`: `{source_model_key, target_ref, target_content_fingerprint, generation_fingerprint}`。同一target identityの重複を拒否し、current generator resultから固定builderが作る
- requirement: `{requirement_key, dimension_key, operator, authority_refs, source_model_key, source_target_versions}`。environmentでは`source_model_key=null`。test dataではcurrent model keyを必須とし、model-wide requirementではcurrent adapter modelを許可、target-specific requirementではCoverage所有modelを必須にする
- `operator=eq`: `value` typed value必須
- `operator=enum`: `values[]` typed valueを1件以上、重複不可
- `operator=range`: `minimum / maximum` typed value、`minimum_inclusive / maximum_inclusive` boolean必須
- `operator=version_range`: `minimum / maximum` version文字列、inclusive boolean必須
- `operator=boolean`: `value` boolean必須
- `source_target_versions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint}`。environmentとmodel-wide test dataでは空配列を許可する。target-specific test dataでは1件以上必須とし、全rowが`current_source_targets[]`の同じ`source_model_key`へ完全一致しなければ`invalid_input`とする。model-wide test dataでは`current_source_targets[]`照合を要求せず、`source_model_key`のcurrent model metadata一致だけを必須にする。別modelのtargetや古いversionを受理せず、modelを跨ぐtraceabilityへ`target_key`単独を使用しない
- `test_data_requirements.py`の各正規化済み要求は`data_ref=data:<requirement_key>`を返し、`materialize_coverage.py`の`test_data_requirement_refs[]`はこの`data_ref`だけを参照する

#### `analysis_entities.py`

- required: `test_analysis_context`, `product_risks[]`, `technique_selections[]`, `change_nodes[]`, `change_edges[]`, `environment_requirements[]`, `risk_matrix_results[]`, `technique_candidate_results[]`
- `test_analysis_context`は`_02` §4.4のcontext contentと同じ意味fieldを持つ
- `risk_matrix_results[]`はcurrent `risk_matrix.py` payloadの`risks[]`を固定抽出した`{risk_id, level, mapped_priority}`だけを受ける。Product Risk draftは`{risk_id, failure, source_refs[], authority_refs[], impact, likelihood, assessment_reason, confidence_note}`。各`risk_id`は入力内一意で、result rowと1対1でjoinする。missing / duplicate / unknown resultを`invalid_input`にする
- `technique_candidate_results[]`はcurrent `technique_candidates.py` payloadから固定抽出した`{selection_key, candidates[], undetermined_signals[]}`だけを受ける。Technique Selection draftは`{selection_key, applicability_scope, selection_source, signals, selected_techniques[], selection_reason, risk_refs[], authority_refs[], condition_design_focus[], undetermined_signal_closures[], status}`。result rowと1対1でjoinし、closure対象signal集合を一致させる
- `status=active`では全`undetermined_signals[]`が`resolved / selection_not_affected / question`のいずれかへ1回だけ閉じ、`selected_techniques[]`はcanonical technique slugだけを許可する
- change node / edgeは`_02` §4.4の`change_kind / expected_impact / evidence_refs[]`を含むcontent schemaをそのまま使う
- `environment_requirements[]`はcurrent `environment_requirements.py` resultから固定builderが渡す正規化済み要求で、同runtime unitを`upstream_runtime_units[]`へ保持する
- Product Riskはcurrent `risk_matrix.py`、Technique Selectionはcurrent `technique_candidates.py`の対応resultを必要な場合だけ`upstream_runtime_units[]`へ保持する。change impact resultはchange graph contentの正本にはせず、別runtime resultとして保存する
- 同一invocation内のEntity生成順は、(1) change graph / environment requirement、(2) Product Risk、(3) Technique Selection / test-analysis contextで固定する。後段Entityが前段Entityをsemantic dependencyとして参照する場合は、同じ実行で確定した前段Entityのcanonical content fingerprintを使用する
- change graph内のRisk / TR / TCN / CI / TC nodeは構造参照であり、それら下流QA Entityへのdependencyを自動追加しない。これによりProduct Riskがchange graphを参照してもdependency cycleを作らない
- outputはcanonical sort済み`machine_entities[]`と`expected_entity_identities[]`。expected identityはdraft / normalized resultのidentity sourceから導出し、生成済み`machine_entities[]`の存在から逆算しない
- Machine Entity wrapper / content fingerprint / dependencyは`runtime_contract.py`の共通builderで生成し、LLMがJSONを再構築しない

#### `requirement_structure.py`

- required: `authorities[]`, `risks[]`, `test_requirements[]`, `dispositions[]`, `previous_tr_ids[]`
- TR draft: `{draft_key, identity_action, reuse_id, text, authority_refs[], risk_refs[], priority, priority_override_reason, test_level, observation_method}`
- `draft_key`は入力内一意、`identity_action=reuse|new`。reuse時だけactiveな既存`TR-\d{3}`を`reuse_id`へ指定し、new時は`reuse_id=null`
- `previous_tr_ids[]`: `{tr_id, status}`、`status=active|deleted`
- canonicalized `test_requirements[]`を`draft_key`順で処理し、複数new TRへその順で採番する
- reuse対象の不存在 / deleted / 同一IDのduplicate reuseを`invalid_input`にする。new採番はdeletedを含む過去最大番号+1。999超過は`id_space_exhausted`
- previous active TRのうちcurrentでreuseされないIDは`deleted`へ遷移し、deleted rowを保持する
- `priority_override_reason`は関連Riskから導出した最低優先度より低くする場合だけ非空必須で、runtimeが意味判断として優先度を自動補正しない
- dispositionは`{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`を使う
- outputは`tr_id_map[]: {draft_key, tr_id, identity_action}`とactive / deleted全行を含むfull snapshotの`tr_id_state[]`

#### `condition_structure.py`

- required: `test_requirements[]`, `technique_selections[]`, `test_conditions[]`, `requirement_dispositions[]`, `models[]`, `previous_tcn_ids[]`, `previous_model_keys[]`
- TR: `{tr_id, priority, authority_refs[], risk_refs[]}`。各`tr_id`は入力内一意
- Technique Selection: `{selection_key, selected_techniques[], undetermined_signal_closures[], status}`。`selection_key`は入力内一意、`selected_techniques[]`はcanonical technique slugで重複不可。`status=active`だけmodel閉鎖の対象にし、activeではundetermined signalが全件閉じていることを必須にする
- TCN draft: `{draft_key, identity_action, reuse_id, tr_refs[], condition, category, technique_slugs[], coverage_criterion, authority_refs[], risk_refs[], priority, priority_override_reason}`。`draft_key`は入力内一意、`condition / coverage_criterion`は非空文字列、`category`は文字列またはnull、`technique_slugs[]`は`_02` §4.3のcanonical technique slugだけを許可し重複不可。意味上の同一性はLLMが`identity_action=reuse|new`で決め、reuse時だけactiveな既存`TCN-\d{3}`を`reuse_id`へ指定する
- requirement dispositionは`_02`の共通Disposition schemaを使用する
- 各current TRはTCNの`tr_refs[]`またはrequirement dispositionのどちらか一方へ閉じる。unknown TR、linked + disposed重複、未閉鎖TRをviolationにする
- TCNの既定priorityは関連TRの最高優先度。より低いpriorityを指定する場合だけ非空`priority_override_reason`を必須にし、runtimeが自動補正しない
- model draft: `{draft_key, model_type, technique_slug, selection_source, selection_key, derived_from_model_draft_key, identity_action, reuse_model_key, parent_tcn_draft_key}`。`model_type`は`_02` §4.3の内部model type。adapterでは`technique_slug / selection_source / selection_key=null`、Coverage所有modelではcanonical `technique_slug`と`selection_source=analysis|condition_design|user`を必須とする。`selection_source=analysis`だけ`selection_key`必須、その他はnull
- `previous_tcn_ids[]`: `{tcn_id, status}`、`previous_model_keys[]`: `{model_key, model_type, technique_slug, parent_tcn_id, selection_source, selection_key, derived_from_model_key, status}`。`status=active|deleted`。reuseはactiveだけ許可し、新規採番の最大番号にはdeletedも含める
- runtimeはreuse対象の存在、status、duplicate reuse、`model_type / technique_slug / selection_source / selection_key / derived_from_model_key`、最終親TCN一致を検証する。reuse modelを別TCNへ移さない。`derived_from_model_draft_key`は同じTCN draft配下のadapter draftだけを許可し、確定後の`derived_from_model_key`へ一意変換する
- TCN draftはcanonical `draft_key`順、model draftは`(parent_tcn_draft_key, model_type, draft_key)`順でnew IDを割り当てる。raw入力順を採番へ使わない
- 1つのmodel keyは同時に1つのTCNだけへ所属する。previous active TCN / modelでcurrentにreuseされないものはdeletedへ遷移し、deleted rowをfull snapshotから消さない
- 各TCN draftの`technique_slugs[]`は、そのTCNを`parent_tcn_draft_key`に持つcurrent Coverage所有model draftの非null `technique_slug`集合と完全一致させる。`model_type`を集合へ入れずadapterはTCNの適用技法を増やさない
- Classification Tree / Cause-Effect / schema / UI等のadapterはcanonical techniqueを所有しない。Coverageを実際に所有するchild modelが`technique_slug / selection_source / selection_key`を持つ
- `selection_source=analysis`のCoverage所有modelは参照Technique Selectionに同じ`technique_slug`が存在必須。1つの`selection_key + technique_slug`から複数TCN / modelへ展開してよい
- active Technique Selectionの`selected_techniques[]`に残る各技法は、少なくとも1件のcurrent Coverage所有modelへ到達必須。後から不適用 / 未解決と判断した場合はTechnique Selection Entity自体を更新してselected listから外すか既存block / unresolvedへ戻し、未定義のselection closureで閉じない
- `model_type=error-guessing / technique_slug=error-guessing`はmodel metadataを作るがgenerator runtime unitを期待集合へ追加しない。semantic Coverage Itemを1件以上のcurrent CIへmaterializeするまで完了不可
- outputは`tcn_id_map[]: {draft_key, tcn_id, identity_action}`、`model_key_map[]: {draft_key, model_key, model_type, technique_slug, parent_tcn_id, derived_from_model_key, identity_action}`、full snapshotの`tcn_id_state[]`、`model_key_state[]`を返す
- 固定builderはTCN draftの意味field（`priority_override_reason`を含む）と最終TCN IDをjoinしてTCN Machine Entityを、model draftの`model_type / technique_slug / selection_source / selection_key / derived_from_model_draft_key`と最終model key / parent TCN / `derived_from_model_key`をjoinしてmodel metadata Entityを生成する。LLMがMachine Entity JSONを再生成しない
- TCN / modelは同一`condition_structure.py` invocationで生成するため、model metadataの親TCNと`derived_from_model_key`のadapter modelは入力`upstream_entities[]`へ事前要求しない。TCN Entityを先に、adapter modelをchild modelより先に固定生成し、そのcurrent content fingerprintをmodel Entityの`upstream_entity_dependencies[]`へ設定する
- 999到達後の新規TCNは`id_space_exhausted`。model keyは3桁以上を許可し999上限を設けない

#### `equivalence_partitions.py`

- required: `sets[]`
- set: `{set_key, label, partitions[]}`。`label`は非空文字列
- partition: `{partition_key, label, validity, definition, representative, authority_refs}`。`label`は非空文字列
- `validity = valid | invalid`
- `definition.type=enum`: `values[]` typed valueを1件以上
- `definition.type=range`: `minimum / maximum / minimum_inclusive / maximum_inclusive`
- `representative`はtyped valueまたはnull。nullならscriptが一意に選べるenum / numeric rangeだけ自動生成

#### `bva.py`

- required: `boundaries[]`
- boundary: `{boundary_key, label, side, threshold, inclusive, step, mode, coverage_selection_reason, authority_refs}`。`label`は非空文字列
- `side=lower|upper`, `mode=2-value|3-value`。`mode=3-value`では境界リスク、過去不具合、ユーザー明示等の具体的な`coverage_selection_reason`を非空必須とし、2-valueでは空文字を許可する
- `threshold`はtyped integer / decimal / date / local_datetime / fixed_offset_datetime
- `step`は§4のdomain別object形式だけを許可し、threshold型と互換であることを必須にする

#### `domain_testing.py`

- required: `partitions[]`, `borders[]`
- partition: `{partition_key, label, dimensions[], expression, authority_refs}`。`label`は非空文字列、`dimensions[]`は`{dimension_key,label}`を1件以上持ち、expressionは§5の`border_ref / and / or` ASTだけ
- borderは§5の`border_key / label / partition_key / relation / coefficients / constant / pivot_key / anchor / pivot_step / authority_refs`だけ。`label`は非空文字列、coefficient / anchorのdimension keyは同partitionの`dimensions[]`へ解決必須
- coefficient / constant / pivot_stepはdecimal文字列
- anchor valueはtyped integer / decimalだけ
- 各borderは同じ`partition_key`のpartition expressionから1回以上参照されること

#### `decision_table.py`

- required: `conditions[]`, `actions[]`, `known_rules[]`, `constraints[]`, `accepted_merges[]`
- condition: `{condition_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- action: `{action_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- known rule: `{rule_key, when, then, authority_refs}`。`when`は全condition keyを1回ずつ、`then`は全action keyを1回ずつ持つ
- constraintsは共通partial assignment
- accepted mergeは§6.1形式

#### `combinatorial.py`

- required: `mode`, `factors[]`, `constraints[]`
- factor: `{factor_key, label, values[], authority_refs}`。`label`は非空文字列、valuesはtyped valueを1件以上
- `mode=exhaustive`: 追加fieldなし
- `mode=base-choice`: `base_assignment`を全factorについて必須
- `mode=t-wise`: `strength` integerを2..factor数で必須。`strength>2`では`coverage_selection_reason`を非空必須
- `mode=mixed-strength`: `global_strength` integerを2..factor数、`subsets[]`を1件以上必須。subsetは`factor_keys[]`と`strength`を持ち、strengthは2..subset factor数。globalまたはsubsetのいずれかがstrength>2なら`coverage_selection_reason`を非空必須

#### `classification_tree.py`

- required: `classifications[]`, `constraints[]`
- classification: `{classification_key, label, classes[], authority_refs}`。`label`は非空文字列
- class: `{class_key, value, authority_refs}`。valueはtyped value
- 同一classificationのclass valueは重複不可

#### `state_transition.py`

- required: `states[]`, `initial_states[]`, `terminal_states[]`, `transitions[]`, `reset_options[]`, `invalid_transition_candidates[]`, `coverage_mode`
- optional: `switch_count`, `coverage_selection_reason`。`coverage_mode=n-switch`だけ`switch_count`必須、`switch_count>=2`では`coverage_selection_reason`を非空必須
- state: `{state_key, label, authority_refs}`。`label`は非空文字列
- transition: `{transition_key, from, event, guard_status, guard_refs, to, authority_refs}`
- `guard_status=true|false|null`
- resetは§9形式で`action`を非空文字列必須とする
- coverage mode: `all-states | valid-transitions | n-switch | round-trip | invalid-transitions`
- `switch_count`はinteger 0..10
- n-switch / round-tripのtarget定義とcanonicalizationは§9を正本とする
- invalid candidateは§9形式

#### `flow_paths.py`

- required: `nodes[]`, `edges[]`, `initial_node_keys[]`, `regions[]`, `loop_specs[]`, `coverage_mode`, `max_path_length`
- node: `{node_key, label, kind, authority_refs}`。`label`は非空文字列、kindは`normal / fork / join / terminal`
- edge: `{edge_key, from, to, guard_status, guard_refs, label, authority_refs}`
- region: `{region_key, fork_node_key, join_node_key, branches[]}`。branchは`{branch_key, edge_keys[]}`
- loop spec: `{loop_key, entry_node_key, edge_keys[], exit_edge_keys[], typical_iterations, maximum_iterations, authority_refs}`
- `initial_node_keys[]`は1件以上
- `coverage_mode = node | edge | bounded-path | simple-loop | fork-join`
- `max_path_length`は1..1000
- region / loopの連続性・nest・iteration規則は§10を正本とする

#### `crud_matrix.py`

- required: `entities[]`, `functions[]`, `cells[]`, `consistency_sequences[]`, `operation_dispositions[]`
- entity: `{entity_key, label, authority_refs}`。`label`は非空文字列
- function: `{function_key, label, authority_refs}`。`label`は非空文字列
- cell: `{entity_key, function_key, operations[], authority_refs}`。operationsは`C/R/U/D`の重複なし集合
- consistency sequenceは§11形式
- 個々の空cellは欠陥・N/Aを意味しないため専用`excluded_cells[]`を持たない。entity全体でoperationが存在しない場合だけ`operation_dispositions[]`で扱う
- operation disposition: `{entity_key, operation, handling, reason, authority_refs}`。`handling=not_applicable`、Authority 1件以上

#### `cause_effect.py`

- required: `causes[]`, `effects[]`, `constraints[]`
- cause: `{cause_key, label, authority_refs}`。`label`は非空文字列
- effect: `{effect_key, label, expression, true_value, false_value, authority_refs}`。`label`は非空文字列
- expression ASTは`{"op":"ref","key":"C1"}`、`{"op":"not","arg":...}`、`{"op":"and|or","args":[...,...]}`だけ
- refはcause keyだけを許可し、effect参照は禁止
- true / false valueはtyped value
- constraintは§25.1の共通partial assignmentで、assignment keyはcause keyだけを許可し、`derived.decision_table.constraints`へそのまま渡す

#### `grammar_cases.py`

- required: `input_label`, `start`, `productions[]`, `max_depth`, `mutations[]`
- `input_label`は生成文字列を適用する入力対象を第三者が識別できる非空文字列
- productionは`{production_key,lhs,rhs[]}`。RHS itemは`{"terminal":"..."}`または`{"nonterminal":"..."}`のどちらか一方で、`rhs=[]`をepsilonとして許可する
- `max_depth`は1..64のparse tree depth上限でroot start symbolをdepth 0とする
- derivationはleftmost固定。各production targetは対象productionを1回以上含むproduction適用回数最小のderivation、同数ならproduction key列辞書順
- valid case集合は各production shortest derivationのunionで、生成文字列 + production key列が同一なら重複除去
- mutation: `{mutation_key, op, production_key, symbol_index, value}`。opは`delete_terminal / replace_terminal / insert_terminal`
- deleteではvalue禁止、replace / insertではvalue string必須
- delete / replaceは`symbol_index`がterminal itemを指すこと、insertは0..len(rhs)を許可
- mutation後もleftmost / depth / shortest tie-breakを適用し、対象productionを含む導出がなければ`unreachable_mutation`
- stable targetはproduction `syntax:prod:<production_key>`、mutation `syntax:mutation:<mutation_key>`

#### `schema_cases.py`

- required: `schema_kind`, `document`, `schema_pointer`, `context`
- arbitrary JSON Pointerやproperty名をstable component keyへ直接埋め込まない。`source_digest`は`canonical JSON({schema_kind,schema_pointer,keyword,role})`のSHA-256 64桁lowercase hexとし、schema targetは`schema:sha256:<source_digest>`を使う。下流へ渡す`set_key / partition_key / boundary_key / factor_key / requirement_key`は同じsource objectへ用途`role`を加えたfull digestから`_02` §3.2の`h` + 64 hex component keyを固定生成する。元pointer / keyword / full digestもpayloadへ保持する
- `schema_kind = json-schema-2020-12 | openapi-3.0 | html-control`
- numberは共通strict JSONの専用number tokenからcanonical integer / exact `coefficient + scale`へ正規化し、binary float / `Decimal` contextへ依存しない
- JSON Schema 2020-12ではroot `$id`だけmetadataとして許可し、nested `$id`、`$anchor / $dynamicAnchor / $dynamicRef`、外部URI referenceはruntime-v1 `unsupported`。対応`$ref`は同一schema resource内の`#/...`だけ
- JSON Schema 2020-12の`$ref` siblingは対応keywordなら通常どおり評価し、`$ref`だけを見てsiblingsを捨てない
- OpenAPI 3.0はJSON Schema 2020-12と別semanticsで、`nullable`、boolean exclusive boundary、`readOnly / writeOnly`、Reference Objectを§14どおり処理する
- OpenAPI Reference Objectは`$ref`以外の追加propertyを仕様どおり無視し、sibling Schema assertionとして解釈しない
- `enum / const`はscalar / nullだけruntime-v1対応。object / array値を含むsubtreeはunsupported itemへ出す
- `context`はJSON Schemaでは`validation`、OpenAPIでは`request|response`、HTMLでは`form-control`
- html-control `document`は`{type, required, min, max, minlength, maxlength, step, value, pattern, disabled, readonly, multiple}`。numberのdefault step=1、`step=any`、step base=min→value→0を§14どおり扱う
- `pattern`等の未対応constraintを無視してcompleteにせず、validation意味へ影響するsubtreeを`unsupported`
- `multipleOf`と対応可能なnumber `step`は§14の`grid` constraintへ正規化する
- annotation allowlistとunsupported subtree規則は§14を正本とする

#### `ui_pattern_candidates.py`

- required: `pattern`, `attributes`
- `pattern`はcatalog正規名またはalias
- `attributes`は`type / role / required / min / max / minlength / maxlength / step / disabled / readonly / multiple`だけを許可
- catalogにないpatternは`unsupported`

#### `random_testing.py`

- required: `input_label`, `seed`, `case_count`, `distribution`
- `input_label`は生成値を適用する入力対象を第三者が識別できる非空文字列
- distributionは§17の3 schemaのいずれか一つ

#### `metamorphic.py`

- required: `relations[]`
- relationは§18形式に`relation_label`を加え、`relation_label`を非空必須とする。`expected_relation.output_path / output_kind`も必須
- `source_id`はrelation内一意
- `follow_ups[]`は1..10,000件で`follow_up_key`をrelation内一意
- 各follow-upの`transforms[]`は1件以上で宣言順に適用する

#### `case_structure.py`

- required: `test_conditions[]`, `coverage_items[]`, `environment_requirements[]`, `test_data_requirements[]`, `test_cases[]`, `dispositions[]`, `previous_tc_ids[]`
- TCN: `{tcn_id, tr_refs[], priority}`
- CI: `{ci_id, tcn_id, model_key, priority, authority_refs[], source_kind, execution, semantic_item_key, semantic_item_text, semantic_source_targets[], test_data_requirement_refs[]}`
- environment / test data requirementはcurrent Machine Entityのcanonical contentとcontent fingerprintを渡す
- TC draft: `{draft_key, identity_action, reuse_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], environment_requirement_refs[], test_data_requirement_refs[], priority, priority_override_reason, preconditions[], test_data[], steps[], expected_results[], postconditions_or_cleanup[]}`
- stepは`{number,text}`で1から連番。expected resultは`{number,text,authority_refs[]}`で1から連番
- `previous_tc_ids[]`は`{tc_id,status}`のfull snapshot。reuseはactiveだけ、duplicate reuse禁止、newはdeletedを含む過去最大番号+1、999超過は`id_space_exhausted`
- 各`ci_ref`の親TCNは`tcn_refs[]`に必須。TCの`tr_refs[]`は参照TCNのTR unionと一致させる
- CIのtest data requirement refsはTCのrefsへ含め、environment / test data requirementの存在とcontent fingerprintを検証する
- `priority_override_reason`はCoverage Itemから要求される優先度より低くする場合だけ非空必須
- LLMはCIの自己完結canonical `execution`または`semantic_item_text`とcurrent requirementsを使い、Markdown Coverage Item表やgenerator内部modelからmachine meaningを再抽出しない
- canonicalized TC draftを`draft_key`順で採番し、previous activeでreuseされないTCはdeletedへ遷移する
- dispositionは完全Machine Entity参照schemaを使う
- outputは`tc_id_map[]: {draft_key,tc_id,identity_action}`とactive / deleted全行を含む`tc_id_state[]`

#### `traceability.py`

- required: `nodes[]`, `edges[]`, `dispositions[]`, `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`, `expected_runtime_units[]`, `expected_entities[]`, `unsupported_item_closures[]`
- node: `{node_key, node_type}`。node_typeは`Authority / Risk / TR / TCN / CI / TC`
- edge: `{from, to}`。from / toは既知nodeで、§23の許可直接edgeだけを認める
- disposition: `{upstream_entity:{skill, entity_type, entity_ref, content_fingerprint}, handling, reason, authority_refs[], covered_by_entity}`。handlingは対象上流型に対して既存担当Skillが許可するDisposition集合だけを認め、必要なreason / Authority / covered_by_entityを検証する
- `runtime_units / current_entities / current_runtime_units / expected_runtime_units / expected_entities / unsupported_item_closures`は`workflow_runtime.py`と同じschemaを使用し、materialize runtime unitの`model_completion[] / target_mappings[] / target_dispositions[]`も同じcurrent resultから受け取る
- `coverage-analysis::artifact:traceability:all`自身と`qa-workflow::artifact:workflow_runtime:all`は`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`のすべてから除外する。いずれかが含まれていた場合は`invalid_input`とし、traceability → workflow_runtime → traceabilityのcycleを作らない
- `traceability.py`は各Skillの同一内容`runtime_contract.py`にある共通freshness評価関数を呼び、`runtime_freshness[] / entity_freshness[]`を決定論的に算出する。workflow_runtime resultを入力へ渡さず、self/cycle dependencyを作らない
- stale分析では`entity_freshness[]: {skill, entity_type, entity_ref, model_key, freshness_status, stale_reasons[]}`を正本にし、stale Entityがcurrentな下流で閉鎖済みと誤判定しない

#### `materialize_coverage.py`

- required: `tcn_id`, `active_model_metadata[]`, `models[]`, `semantic_coverage_items[]`, `target_annotations[]`, `target_dispositions[]`, `test_data_requirements[]`, `previous_target_id_map[]`, `previous_semantic_ci_map[]`, `previous_ci_ids[]`, `previous_expected_result_roots[]`, `merge_groups[]`
- `tcn_id`は`TCN-\d{3}`
- `active_model_metadata[]`: `{model_key, model_type, technique_slug, parent_tcn_id, content_fingerprint}`。TCN配下の全current modelを渡し、`parent_tcn_id`はinputの`tcn_id`と一致必須
- `models[]`の各model resultは共通metadata `{model_key, model_type, technique_slug, skill, runtime_unit_key, input_fingerprint, model_fingerprint, generation_fingerprint, generator_contract_version, support_status, runtime_status, result_status, deterministic_generated, freshness_status, targets[], unsupported_items[]}`に、model type別summaryを加える。通常Coverage modelは`coverage_summary={criterion,required,covered,complete}`、CRUDは`coverage_summary={completeness:{criterion,required,covered,complete},consistency:{criterion,required,covered,complete},complete}`、Random / Metamorphicは各節の`completion_summary`を必須とし、他形式を拒否する
- materialize対象model resultは`runtime_status=ok / result_status=ready / deterministic_generated=true / freshness_status=current`を必須にする。加えて通常Coverage modelは`coverage_summary.complete=true`、CRUDは`coverage_summary.completeness.complete=true / consistency.complete=true / complete=true`、Random / Metamorphicは`completion_summary.complete=true`を必須にする。`support_status=supported`または、unsupported itemと対応可能targetが分離済みの`partial`だけ許可し、partialではsupported範囲のsummaryだけをcompleteにできる。runtimeなしsemantic modelやwhole-model unsupportedを成功resultとして`models[]`へ偽装しない
- `freshness_status=current`は現在のMachine Entity / normalized inputをpreflight確認した後、現在scriptを再実行して正常生成したresultだけに付与する。保存済みgenerator resultをmaterialize入力のcurrent cacheとして直接再利用しない
- semantic item draft: `{draft_key, model_key, identity_action, reuse_semantic_item_key, reuse_ci_id, source_target_versions[], item_text, authority_refs[], reference_refs[], priority, priority_override_reason, expected_result_root, test_data_requirement_refs[]}`。`draft_key`は入力内一意、`item_text`は非空。runtime generatorへ移さないsemantic model、fork-join等の直接linear executionへ落とさないCoverage Item、またはpartial / whole-model unsupportedの`llm_fallback`だけに使用する
- new semantic itemは`reuse_semantic_item_key / reuse_ci_id=null`とし、canonical `(model_key, draft_key)`順でCIを採番した後にruntimeが`semantic_item_key=semantic:<ci_id>`を発行する。reuseではactive / inactiveのprevious rowにある同じsemantic item key / model / CIをすべて指定し、別item・別model・runtime target CIへの横取りを拒否する
- `semantic_content_fingerprint`は`model_key / source_target_versions[] / item_text / authority_refs[] / reference_refs[] / priority / priority_override_reason / expected_result_root / test_data_requirement_refs[]`をcanonical JSON化してSHA-256する。identity_action / reuse fieldはfingerprintへ含めない
- `source_target_versions[]`は`{target_ref, target_content_fingerprint, generation_fingerprint}`。machine targetを意味判断へ渡す場合は現在targetと完全一致し、全targetがsemantic item自身の`model_key`に所属することを必須にする。エラー推測またはwhole-model unsupported fallbackのように元machine targetがないsemantic itemでは空配列を許可する。machine target / execution / generation fingerprintを捏造しない
- machine target: `{target_ref, target_content_fingerprint, materializable, execution_fingerprint, target_key, execution, authority_refs, reference_refs, ...技法固有machine fields}`。`materializable=true`では自己完結`execution`と`execution_fingerprint`必須、falseでは両方null。fingerprintは`_02` §7.2の式をruntimeが再計算する
- target annotation: `{target_ref, target_content_fingerprint, generation_fingerprint, priority, priority_override_reason, expected_result_root, test_data_requirement_refs[]}`。Dispositionされないmaterializable targetにちょうど1件対応し、unknown / duplicate target_refを拒否する。target / generation versionは現在model resultと一致必須
- `expected_result_root`は同一TCN内の内部用local keyでstable component key形式を使う。同じkeyはLLMがAuthorityに基づき同じ期待挙動へ統合可能と判断したtargetだけへ付与し、製品Authorityそのものとして扱わない。意味上同じgroupをreuseする場合だけactiveなprevious keyを維持し、新規groupは未使用keyを追加する
- target disposition: `{target_ref, target_content_fingerprint, generation_fingerprint, handling, reason, authority_refs[], covered_by_target_version}`。`covered_by_target_version`はnullまたは`{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint}`。source targetの現在target / generationは完全一致必須で、同一targetへannotationとDispositionを同時指定しない。`handling=重複`では完全`covered_by_target_version`必須かつself参照禁止。参照先`materializable=true`ではcurrent `execution_fingerprint`を必須、semantic Coverage Itemへ閉じる`materializable=false` targetでは`execution_fingerprint=null`を必須にする。同一input内の参照先targetは即時にcurrent version照合し、local input外の参照先は最終`traceability.py / workflow_runtime.py`で全materialize unit横断照合する
- `target_ref`は`_02` §7.2の式を再計算して一致必須
- `test_data_requirements[]`: `{data_ref, requirement_key, dimension_key, operator, ...}`。`data_ref=data:<requirement_key>`を一意にし、annotation / semantic itemの全`test_data_requirement_refs[]`はcurrent集合に存在必須
- `previous_target_id_map[]`: `{target_ref, model_key, target_key, target_content_fingerprint, ci_id, mapping_status}`。`mapping_status=active|inactive`。Disposition中targetの直近CIもinactiveとして保持し、同じtarget_refでcontent fingerprintが変わればCI IDを維持しても`stale_ci_ids[]`へ追加する
- `previous_semantic_ci_map[]`: `{semantic_item_key, model_key, ci_id, mapping_status, semantic_content_fingerprint}`。`mapping_status=active|inactive`
- `previous_ci_ids[]`: `{ci_id, status}`。`status=active|deleted`で削除済み番号も保持する
- `previous_expected_result_roots[]`: `{expected_result_root, status}`。`status=active|deleted`。same-meaning groupのreuse可否はLLMが判断し、runtimeはunknown / duplicate / deleted keyの不正reuseを検査する
- previous active target / semantic mappingがcurrentでreuseされなければinactiveへ遷移する。共有targetのないruntime CIまたは消滅したsemantic CIはdeletedへ移し、inactive / deleted rowをfull snapshotから消さない
- inactive target / semantic itemの復帰は同じidentityへの明示reuseかつ過去CIが別identityへ再利用されていない場合だけ同じCIを復帰できる。deleted CI / semantic item keyを別identityへ再利用しない
- semantic itemのmodel変更はreuse不可。同じsemantic item keyをreuseしてもcontent fingerprintが変わればCI content fingerprintを変え、既存TCをstaleにする
- merge groupは`_02` §7.4の`{merge_group_key, model_key, target_refs[], target_versions[]}`を使う。Dispositionされていない同一TCN・同一model内targetだけを許可し、全target versionを現在model resultへ一致させる。`execution_fingerprint`と`expected_result_root`が全件一致する場合だけ同一CIへ統合し、異なるmodel / 技法 / execution / expected resultを統合しない
- merge group内の追加test data requirementは§16と同じintersection規則で統合し、conflict / unsupportedならmergeを拒否する。異なるCIを1つのTCへまとめる意味判断は`case_structure.py`の`ci_refs[]`で行い、merge groupへ逆変換しない
- `materializable=false`のadapter / diagnostic専用targetはCI採番、annotation、Dispositionの対象外。正規Coverage基準上必要だがlinear executionへ落とせないtargetはcurrent target versionを持つsemantic Coverage Itemまたは既存Skillで許可されたtarget Dispositionへ1回だけ閉じる
- `target_dispositions[]`にあるmaterializable targetはCI採番対象から除外するが、generator固有の`coverage_summary`または`completion_summary`自体は変更しない
- new CI候補はcanonical `(model_key, source_kind, source_key)`順で採番する。`runtime_target < semantic_item`、runtime targetのsource keyは`target_ref`、semantic itemはnewなら`draft_key`、reuseなら`reuse_semantic_item_key`。raw入力順で採番しない
- runtime target mapping、semantic reuse、mergeの全経路で同一CIを別identityへ不正reuseするduplicateを拒否する。new CIはdeletedを含む同一TCNの過去最大番号+1で割り当てる。CIは`CI\d{2,}`で上限を設けない
- outputは`target_id_map[]`、`target_mapping_state[]`、`semantic_ci_mapping_state[]`、`ci_id_state[]`、`expected_result_root_state[]`、`disposed_target_refs[]`、`coverage_item_rows[]`、`stale_ci_ids[]`、`model_completion[]`、`issues[]`
- `target_id_map[]`: `{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`。`generation_fingerprint`はsource model resultのcurrent generationを固定転記する。active mappingだけを返し、1 target_refから複数CIへのmappingを禁止する
- `target_mapping_state[] / semantic_ci_mapping_state[] / ci_id_state[] / expected_result_root_state[]`はactive / inactive / deletedを含む必要なfull snapshotを返し、次回previous stateの正本にする
- 固定builderはactive CIごとに`_02`のCI Machine Entityを生成する。machine target由来は`source_kind=runtime_target`として`covered_targets[]`をtarget_ref順で集約しcanonical `execution`を保存する。semantic item由来は`source_kind=semantic_item / covered_targets=[] / execution=null / semantic_item_key / semantic_item_text / semantic_source_targets[]`を保存する
- CI Machine Entityの`runtime_dependencies[]`にはcurrent `materialize_coverage.py` generationを、`upstream_entity_dependencies[]`には親TCN、model metadata、current test data requirement Entityを保存する。priority / expected result root / Authority / Reference / test data requirementは現在annotation / target / semantic itemから固定joinし、LLMがCI Entity JSONを再生成しない
- `disposed_target_refs[]`: `{target_ref, target_content_fingerprint, generation_fingerprint, handling, covered_by_target_version}`。`covered_by_target_version`は`_02` §7.4と同じ4 fieldを保持し、Coverage済みtarget数の計算には使用しない
- `model_completion[]`: `{model_key, required_target_refs[], closed_target_refs[], active_ci_ids[], semantic_item_keys[], materialize_complete}`。supported / partial runtime modelとruntimeなしsemantic modelを対象にする。adapter / diagnosticをrequired targetへ数えない
- runtime targetを持つmodelは`required_target_refs[]`が非空かつ全件`closed_target_refs[]`に含まれる場合だけ`materialize_complete=true`。target disposition、current CI mapping、target version一致済みsemantic itemだけをclosureへ数える
- エラー推測等のtargetなしsemantic modelは1件以上のactive semantic CIがある場合だけtrue。partial modelのunsupported item closureはここで完了扱いせず`workflow_runtime.py`が別途検査する。whole-model unsupportedはLLM fallback CIのmaterialize自体は許可するが`model_completion[]`へ成功rowを捏造せず、workflow側のcurrent whole-model closureを最終条件にする
- `conditions=[] / actions=[] / factors=[] / relations=[] / source_inputs=[] / states=[]`等、Coverage所有modelの意味母集団が空でrequired target / pair / caseが0件になる入力をvacuous completeにしない。model契約に応じて`invalid_input`または`unresolved`へ落とす

#### `workflow_runtime.py`

- required: `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`, `expected_runtime_units[]`, `expected_entities[]`, `unsupported_item_closures[]`
- `qa-workflow::artifact:workflow_runtime:all`自身は`runtime_units[] / current_runtime_units[] / expected_runtime_units[]`の3集合すべてから除外する。いずれかに自身が含まれていた場合は`invalid_input`とし、self dependencyも禁止する
- runtime unit: `{skill, runtime_unit_key, model_key, support_status, result_status, runtime_status, runtime_required, deterministic_generated, generation_fingerprint, upstream_entities[], upstream_runtime_units[], unsupported_items[], model_completion[], target_mappings[], target_dispositions[]}`。`model_completion[] / target_mappings[] / target_dispositions[]`は`artifact:materialize_coverage:<tcn_id>`だけ非空を許可し、current materialize resultから固定builderで転記する。他unitは3配列とも空固定
- `current_entities[]`: `{skill, entity_type, entity_ref, model_key, content, content_fingerprint, upstream_entity_dependencies[], runtime_dependencies[]}`。`content`は`_02` §4.4のMachine Entityと同一で、共通関数が`content_fingerprint`を再計算して保存値と一致確認する
- `current_runtime_units[]`: `{skill, runtime_unit_key, generation_fingerprint}`。`(skill, runtime_unit_key)`を一意keyとして保存済み`upstream_runtime_units[]`と比較する
- `expected_runtime_units[]`: `{skill, runtime_unit_key}`。各Skillは`_02` §2.1のdispatch表、現在の対象 / 実行範囲、active TCN / model metadata、条件付き入力の有無から固定builderで期待集合を作り、`qa-workflow`はそれを連結して`workflow_runtime.py`自身を除外する
- `expected_entities[]`: `{skill, entity_type, entity_ref}`。actual `current_entities[]`や保存済みMachine Entity blockから逆算せず、actual集合と独立したsourceから固定導出する
  - `spec-analysis`: Authority表 / canonical source inventory
  - `test-analysis`: 人間向け正本とnormalized inputからcontext / Product Risk / Technique Selection / change graph / environment requirement
  - `test-requirement-design`: `requirement_structure.py`のinput draft + ID mapping / full stateからTR / Disposition
  - `test-condition-design`: `condition_structure.py`のinput draft + ID mapping / full state、current generator dispatch、`materialize_coverage.py` mappingからTCN / model / CI / test data requirement / Disposition
  - `test-case-design`: `case_structure.py`のinput draft + ID mapping / full stateからTC / Disposition
- 禁止: `current_entities[]`を読んでexpectedを作る、保存済みMachine Entity blockを期待集合の正本にする、missing actual Entityの存在を前提にexpected identityを作る
- `expected_runtime_units[]`もactual `runtime_units[] / current_runtime_units[]`から逆算せず、固定dispatch条件、対象 / 実行範囲、active structure state、normalized inputから導出する
- `runtime_units[]`のidentity集合は`expected_runtime_units[]`と完全一致、`current_entities[]`のidentity集合は`expected_entities[]`と完全一致を必須にする。期待item欠落はblocker、未知の余分なcurrent itemは`invalid_input`とする
- completionでは各active Coverage所有modelをmodel単位で検査する。supported / partial / runtimeなしsemantic modelはcurrent materialize runtime unitの対応`model_completion[]` rowを必須とし、`materialize_complete=true`かつrow内`active_ci_ids[]`がcurrent CI Machine Entityと一致することを検証する。partialではさらにcurrent unsupported item closureを全件必須とする。whole-model unsupportedは対応generationのwhole-model `unsupported_item_closures[]`を必須とする。親TCNに別modelのCIがあるだけで当該modelを完了扱いしない
- 各Skillの同一内容`runtime_contract.py`にruntime dependency graphとMachine Entity dependency graphを評価する共通関数を置く。missing dependencyはstale + blocker、duplicateまたはcycleは`invalid_input`
- `unsupported_item_closures[]`: `{skill, runtime_unit_key, generation_fingerprint, item_key, reason_code, handling, reason, authority_refs, covered_by_entity}`。`covered_by_entity`は`null`または`{skill, entity_type, entity_ref, content_fingerprint}`の完全Machine Entity参照。`handling`は`llm_fallback / 対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複 / ブロック中`だけを許可する。closureの`generation_fingerprint`は対象runtime unitの現在値と一致必須。`support_status=partial`では`item_key`をunsupported itemのstable keyで必須とし、`reason_code`も現在unsupported itemと一致必須。whole-model `unsupported`では`item_key=null / reason_code=null`を許可するが`generation_fingerprint`一致は必須とする。世代またはreasonが変わった以前のclosureを自動再利用しない
- `llm_fallback`と`重複`は`covered_by_entity`必須で、currentなMachine Entityへ解決できることを検証する。`llm_fallback`は同じ`model_key`に属するcurrent CI Machine Entityを必須とし、親TCNやmodel metadataだけをfallback Coverage evidenceにしない。`対象外 / 別テストレベル / 残存リスク / 成立不能`は既存`test-condition-design`のDisposition条件をそのまま適用し、不要な`covered_by_entity`はnullとする。`ブロック中`はclosure rowとして保持しても閉鎖済みには数えず`can_complete=false`とする
- runtimeは意味上の再利用可否、開始Skill、仕様Authorityの優先関係を再判断しない
- outputは`freshness[]: {skill, runtime_unit_key, generation_fingerprint, freshness_status, stale_reasons[]}`、`entity_freshness[]: {skill, entity_type, entity_ref, model_key, freshness_status, stale_reasons[]}`、`completion: {can_complete, blockers[]}`、runtime状態表用の正規化rowを返す
- `can_complete=true`には、expected runtime / Entity集合が完全一致し、全runtime unitと対象Machine Entityがcurrent、全unitの`result_status=ready`、runtime required unitが`deterministic_generated=true`であることに加え、partial / unsupportedの各itemが上記closure契約を満たし、`ブロック中`closure、missing / stale / fingerprint不一致な`covered_by_entity`、既存Disposition条件違反が0件であることを必須にする

### unsupported item共通schema

`support_status=partial`で返す`payload.unsupported_items[]`は`{item_key, item_type, source_key, reason_code, authority_refs[]}`で固定します。`reason_code`は機械的な非対応理由であり、workflow完了可否は`unsupported_item_closures[]`の`handling / covered_by_entity`を別途検査して決めます。

- `item_key`は`unsupported:<generator>:sha256:<canonical identity hash>`で、generator、`item_type`、`source_key`をcanonical JSON化して作る
- `source_key`は対応できないsubtree / region / operator等のstable component keyまたはJSON Pointer
- `reason_code`はscriptごとにPlan / Skill referenceで列挙した固定値だけを使用し、自由文をidentityに含めない
- 再実行で同じunsupported箇所は同じ`item_key`を維持し、`workflow_runtime.py`のclosure再利用に使う

`valid_minimal.json`は上記schemaの実行例であり正本ではありません。optional fieldは上記で明記したものだけとし、Skill referenceはこのPlanのschemaをそのまま説明します。

### stable component key

target / result keyへ文字列連結する`set_key / partition_key / boundary_key / border_key / condition_key / action_key / rule_key / factor_key / classification_key / class_key / state_key / transition_key / candidate_key / region_key / branch_key / loop_key / entity_key / function_key / sequence_key / cause_key / effect_key / production_key / mutation_key / relation_key / source_id / follow_up_key / requirement_key / dimension_key`は`_02` §3.2のstable component key形式に従い、`:`を含めません。

### grammar production key

`grammar_cases.py`のproductionは配列indexへ依存せず、各productionを`{"production_key":"P-001","lhs":"expr","rhs":[...]}`形式で与えます。`production_key`はmodel内一意で、並べ替えではtarget keyを変えません。

## 26. scriptが生成しないもの

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- 新しいrisk score入力
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle
- 意味上の同一性・統合可否

scriptの責務は、対応contractとhard limitの範囲で、与えられたmodelを再現可能に展開し、未解決・非対応・limit超過を隠さないことです。
