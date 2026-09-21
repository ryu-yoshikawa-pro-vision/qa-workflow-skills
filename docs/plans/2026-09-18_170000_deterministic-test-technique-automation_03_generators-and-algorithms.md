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

完全rule setに対して、1 conditionだけをdon't-care化する候補を次の規則で作ります。

1. 対象conditionを1つ選び、それ以外のcondition assignmentが同一な成立可能known ruleをgroup化する
2. constraint適用後に成立可能な対象conditionの関連value集合を求め、その全valueについてknown ruleが1件ずつ存在することを必須にする
3. group内の全ruleでaction vectorが完全一致する場合だけ候補にする
4. group内のAuthority集合を失わず保持する
5. 生成したdon't-care派生ruleをさらに候補化せず、1回の候補生成で別conditionへ連鎖統合しない

対象conditionが3値以上でも、一部valueだけactionが一致するgroupをdon't-careへ変換しません。例えば`A / B / C`のうち`A / B`だけ同じactionで`C`が異なる場合は統合不可です。3値すべてが同じactionで、他condition assignmentも同一かつ全valueが成立可能known ruleとして揃う場合だけ統合候補にします。

候補をdeterministicに列挙し、各候補へ`merge_key = dm:sha256:<canonical sorted rule_keys hash>`を付与します。`rule_keys`はUnicode code point順でsortした配列をcanonical JSON化してSHA-256します。LLMは意味上統合してよい候補の`merge_key`だけを`accepted_merges[]`へ返し、任意の`rule_keys[]`を新規構成しません。scriptはaccepted `merge_key`が同一実行で生成した候補に存在すること、対象conditionの成立可能な関連valueがすべて候補ruleに含まれること、候補内ruleが同一action vectorであること、統合後のCartesian productが成立可能な既知ruleだけを含み未定義assignmentを追加しないことを再検証してdon't-care ruleを生成します。Boolean minimizationで最小rule数を目的にしません。

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

`classification_tree.py`は先に`factors[] / constraints[]` skeletonを決定論的に生成します。child `comb`の`mode / strength / subsets / base_assignment`が未指定なら、そのskeletonとfactor keyを保持したまま`result_status=unresolved`と`semantic_parameter_requests[]`を返します。LLMは要求された組合せ戦略parameterだけを補います。再実行後は`derived_child_inputs[]`へ`{child_model_key, model_type:"comb", input:{factors, constraints, mode, strength, subsets, base_assignment}}`を返し、その`input`を`combinatorial.py`へ直接渡します。LLMや別builderがfactor / class / constraintを再生成しません。

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

## 続き

[シナリオ・CRUD・schema・Random・Metamorphic等のgenerator](./2026-09-18_170000_deterministic-test-technique-automation_03_additional-generators.md) に続きます。
