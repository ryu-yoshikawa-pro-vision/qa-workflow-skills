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
- `coverage_summary`: Coverage基準を持つ技法だけが使用する。Random Testing / Metamorphic Testingのように一般的なCoverage基準を持たない技法では、技法固有の終了条件を`completion_summary`として返す
- `derived`: 次scriptへ直接渡す機械変換結果
- `metadata`: target以外の再現可能な補助情報

構造検査scriptは`violations`と`derived_values`をpayloadへ返します。全scriptのrequired input、stable key、payloadは「## 25. script別入出力契約」で固定します。各技法節では技法固有アルゴリズムだけを定義し、実装者が別形式を追加しません。

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
  "candidates": ["境界値分析"],
  "undetermined_signals": ["stateful"],
  "complete": false
}
```

`complete`は`undetermined_signals`が空かだけを表す診断値であり、`false`だけを理由にworkflowをブロックしません。候補の最終採用は`test-analysis`が行います。Error Guessingは構造signalだけでは自動採用しません。

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
- decimalは`Decimal`
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
- 各classificationの`classification_key`
- `classes[]`
- 各classの`class_key`
- Authority / constraint refs

出力`derived.combinatorial_input`は`factors[] / constraints[]`を持ち、`combinatorial.py`の同名fieldと直接互換にします。`mode / strength / mixed-strength subsets / base_assignment`は組合せ戦略の意味判断なのでLLMが別fieldとして決め、固定builderが`derived.combinatorial_input`へjoinします。LLMがfactor / class / constraintを再生成しません。

## 9. 状態遷移

### `state_transition.py`

各transitionは`transition_key / from / event / guard_status / guard_refs / to / authority_refs`を持ちます。

入力:

- `states[]`
- `initial_states[]`
- `terminal_states[]`
- `transitions[]`
- `reset_options[]`
- `invalid_transition_candidates[]`
- `coverage_mode`
- `switch_count`（`coverage_mode=n-switch`だけ必須）

`guard_status=true|false|null`と`guard_refs[]`を使います。`false`をCoverage母集団から外すには`guard_refs`にAuthorityを1件以上必須とします。initial stateから`true` edgeだけで到達可能なstateをsourceに持つ`guard_status=null` transitionがある場合は、Coverage母集団が確定しないため`result_status=unresolved`とし、100% Coverageを返しません。`null`を含むsequenceは正式Coverage targetにしません。

Coverage定義:

- `all-states`: initial stateからfeasible transitionだけで到達可能な全state
- `all-transitions`: initial stateから到達可能で`guard_status=true`の全transition
- `n-switch`: `switch_count=N`として、到達可能な**N+1個の連続するvalid transition**の全sequence。Nは0..10。`N>=2`は高いfailure risk、ユーザー明示、案件固有基準等の具体的理由を`coverage_selection_reason`へ必須で残す
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
  "authority_refs": ["SPEC-010"]
}
```

### 9.1 setup prefix

Coverage sequence開始stateへ直接開始できない場合:

1. initial stateから`guard_status=true`だけを使うshortest pathを探す
2. なければ適用可能reset後のshortest pathを探す
3. path長が同じ場合はtransition key列のUnicode code point辞書順
4. `guard_status=null`を含むpathは構造候補に留め、正式実行sequenceにしない

出力は`setup_prefix`と`coverage_sequence`を分離します。実行可能setupがないtargetをCoverage済みにしません。
## 10. Use Case / シナリオ

### `flow_paths.py`

入力は`nodes[] / edges[] / initial_node_keys[] / regions[] / loop_specs[] / coverage_mode / max_path_length`です。

node kind:

- `normal`
- `fork`
- `join`
- `terminal`

`initial_node_keys[]`は1件以上必須で、すべて既知nodeを参照します。terminal到達を要求するpath criterionでは`kind=terminal`のnodeを終点にします。

edgeは`edge_key / from / to / guard_status / guard_refs / label / authority_refs`を持ち、`guard_status=true`だけを正式Coverage対象へ使います。

`guard_status=false`をCoverage母集団から外すには`guard_refs`にAuthorityを1件以上必須とします。initial nodeから`true` edgeだけで到達可能なnodeをsourceに持つ`guard_status=null` edgeがある場合は`result_status=unresolved`とし、node / edge / path / loop / fork-joinの100% Coverageを返しません。

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

- branchの`edge_keys`はforkからmatching joinまで連続するpathであることをscriptが検証
- 同一regionのbranch keyは一意
- nested regionはbranch path内に含めてよい
- region同士がcrossingする場合は`unsupported`
- scheduler interleavingは仕様なしに生成しない

simple loopは次を明示します。

```json
{
  "loop_key":"LP-001",
  "entry_node_key":"N1",
  "edge_keys":["E10","E11"],
  "typical_iterations":3,
  "maximum_iterations":10,
  "authority_refs":["SPEC-020"]
}
```

- `edge_keys`はentryへ戻るsimple cycleで、途中node重複を禁止
- `typical_iterations`は2以上のinteger必須
- `maximum_iterations`はnullまたは`typical_iterations`以上のinteger
- Coverage targetは0回、1回、typical回、maximum回。maximumがnullまたはtypicalと同値なら重複targetを作らない

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

terminalへ到達しないbounded path候補は正式Coverage targetにせず、診断metadataへ保持します。
## 11. CRUD Testing

### `crud_matrix.py`

ISTQB CTAL-TA v4.0に合わせ、CRUD Testingは**completeness**と**consistency**を分けて扱います。

入力:

- `entities[]`
- `functions[]`
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

`consistency_sequences[]`はLLMが業務意味を正規化した後のsequenceです。

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
5. `derived.decision_table.conditions / actions / known_rules / constraints / accepted_merges=[]`を生成する。入力`constraints[]`は同じ意味のままDecision Table互換schemaへ渡す

`derived.decision_table`は`decision_table.py`のscript固有inputと直接互換にし、Cause-Effect側で意味上のmergeを作りません。

## 13. Syntax-Based Testing

### `grammar_cases.py`

自然言語grammarをparseしません。正規化済みproductionを受けます。

```json
{
  "start": "expr",
  "productions": [
    {"production_key":"P-001","lhs":"expr","rhs":[{"terminal":"a"}]},
    {"production_key":"P-002","lhs":"expr","rhs":[{"nonterminal":"expr"},{"terminal":"+"},{"terminal":"a"}]}
  ],
  "max_depth": 4,
  "mutations": []
}
```

処理:

- undefined nonterminal / unreachable production
- recursionによるdepth超過
- 各productionを少なくとも1回使うvalid derivation
- bounded valid case生成
- production Coverage

production Coverage targetごとに、対象productionを1回以上含むderivationのうち**production適用回数が最小**のものを選びます。同じ適用回数なら、適用した`production_key`列のUnicode code point辞書順で最小のderivationを選びます。

valid case集合は各production targetの上記shortest derivationのunionとし、生成文字列とproduction key列が同一のcaseを重複除去します。production Coverage達成に不要な追加grammar列挙は行いません。

invalid syntaxは補集合から生成しません。明示mutationは`delete_terminal / replace_terminal / insert_terminal`だけを許可します。

- `delete_terminal`: `symbol_index`が指すterminal itemを削除
- `replace_terminal`: `symbol_index`が指すterminal itemを明示replacement文字列へ置換
- `insert_terminal`: RHS配列の`symbol_index`位置へ明示terminal文字列を挿入。0..len(rhs)を許可
- delete / replaceで対象itemがnonterminalなら`invalid_input`

mutationは指定productionのRHSを1回だけ変換した一時grammarへ適用します。その一時grammarで、変換したproductionを1回以上使うproduction適用回数最小のderivationを探索し、同数ならproduction key列辞書順で選びます。`max_depth`内で導出不能なら`unreachable_mutation` issueを返します。

mutation結果は`invalid_candidate`であり、scriptだけで製品上invalidと断定しません。製品上invalidであることをexpected resultへ昇格するにはAuthorityまたはLLMの意味判断を必須にします。
## 14. schema / HTML

### `schema_cases.py`

machine-readableな入力はscriptが直接正規化します。

対応subset:

### JSON Schema 2020-12

- `type`
- `$defs`（local JSON Pointer `$ref`の参照先containerとしてのみ使用）
- `properties`
- `items`
- `enum`
- `const`
- `required`
- `minimum` / `maximum`
- `exclusiveMinimum` / `exclusiveMaximum`
- `multipleOf`
- `minLength` / `maxLength`
- `minItems` / `maxItems`
- `minProperties` / `maxProperties`

`$ref`はruntime内でnetwork解決しません。JSON Schema / OpenAPIでは`document`をrootとして同一document内のlocal JSON Pointerだけ解決し、`schema_pointer`でCoverage対象subtreeを指定します。外部URI referenceは事前dereference済み入力を要求します。local `$ref`の循環参照はその循環subtreeを`unsupported`とします。

`type`は単一type文字列、または`[<non-null type>, "null"]` / `["null", <non-null type>]`の2要素だけを対応します。2要素形式は`allows_null=true`へ正規化し、それ以外のunion typeは`unsupported`です。

`$schema / $id`はdocument metadataとして保持しますがvalidation Coverageへ使用しません。validationへ影響しないannotationとして無視してよいkeywordは`title / description / $comment / default / examples`だけです。その他の未知keywordは黙って無視せず`unsupported`とします。

JSON Schema / OpenAPI document内のJSON numberは`_02` §3.1に従ってintegerを`int`、非integerを`Decimal`としてparseし、`minimum / maximum / exclusiveMinimum / exclusiveMaximum / multipleOf / enum / const`をbinary floatへ変換しません。

`enum / const`のruntime-v1対応範囲はscalar / nullだけです。string、boolean、integer、finite decimal、nullは対応し、object / arrayを値として持つ`enum / const`はそのsubtreeを`unsupported`とします。JSON Schema自体をinvalidとは扱いません。

### OpenAPI 3.0 Schema

- 上記相当keyword
- boolean `exclusiveMinimum` / `exclusiveMaximum`
- `nullable`
- `nullable=true`はsingle base type + nullの`allows_null=true`へ正規化する
- `context=request|response`を必須にし、`readOnly=true` propertyはrequest側required / test data母集団から除外し、`writeOnly=true` propertyはresponse側required / expected response母集団から除外する
- 同一propertyで`readOnly=true`かつ`writeOnly=true`は`invalid_input`
- `title / description / default / example / deprecated`はannotationとして保持してもvalidation Coverageへ使用しない

### HTML form control

runtime-v1でconstraint生成対象とする`type`は`text / number / date / datetime-local`だけです。それ以外のnative control typeはUI pattern候補として扱えても、`schema_cases.py`ではcontrol subtreeを`unsupported`にします。

受け取る属性:

- type
- required
- min / max
- minlength / maxlength
- step
- pattern
- disabled
- readonly
- multiple

type別の扱い:

- `text`: `required / minlength / maxlength`
- `number`: `required / min / max / step`
- `date / datetime-local`: `required / min / max`。本Planではdate/time系`step`を対応しない
- 対応typeでHTML Standard上そのattributeが適用されない場合はvalidation constraintへ変換せずmetadataとして保持する
- `disabled=true`、または対応typeで`readonly=true`の場合はconstraint validation対象外としてvalidation targetを生成しない。readonly / disabled自体のUI挙動はUI pattern側で扱う
- `pattern`がvalidationへ適用されるcontrolはECMAScript RegExpをPython `re`で代用せず、そのcontrol validationを`unsupported`にする。pattern制約を無視したまま他constraintだけでcompleteにしない
- `multiple`がvalidation意味を持つtypeはruntime-v1の対応type外なので`unsupported`とする。対応type上で意味を持たない場合はmetadataだけ保持する

`multipleOf`と数値系HTML `step`は`grid` constraintへ正規化します。

```json
{
  "operator":"grid",
  "base":{"type":"decimal","value":"0"},
  "step":{"type":"decimal","value":"0.5"}
}
```

- JSON Schema `multipleOf=m`: `base=0 / step=m`
- HTML `step=s`: `type=number`かつ`min`が存在するcontrolだけ`base=min / step=s`として対応
- `type=number`で`step`が存在して`min`がない場合、またはdate / datetime-local系stepは本Planの対応subset外としてそのcontrol subtreeを`unsupported`
- `grid`はschema Coverage候補とBVA / combinatorial入力へ渡すが、`test_data_requirements.py`のintersection対象にはしない

`allOf / anyOf / oneOf / not / if / then / else`等、対応subset外でvalidation意味を変えるkeywordは`unsupported`です。unsupported keywordがvalidation意味へ影響するsubtreeだけを切り離し、独立して評価できる別property / itemは継続できます。親schemaのvalidation意味をunsupported keywordが左右する場合は、その親subtree全体を`unsupported`にします。

正規化後のrange / enum / required等は`derived.ep_inputs / derived.bva_boundary_skeletons / derived.combinatorial_constraints / derived.test_data_requirements`へ固定schemaで出力します。`derived.bva_boundary_skeletons`は`boundary_key / side / threshold / inclusive / step / authority_refs`までを持ち、`mode / coverage_selection_reason`は含めません。LLMがその2 fieldだけを追加し、固定builderが`bva.py` inputへ変換します。EP / combinatorial / test dataは対応下流scriptのinput fieldと直接互換です。`grid`は上記限定経路で扱います。
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
- requirement → model / `source_target_refs[]` traceability

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

seed=`42`の最初の6 outputは`2707161783, 2068313097, 3122475824, 2211639955, 3215226955, 3421331566`とし、固定test vectorに使用します。

入力:

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
- `sort`: homogeneous scalar arrayの`path`と`order=asc|desc`

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

- changed nodeから許可edgeを探索
- Authority / TR / TCN / CI / TC候補を重複除去
- dangling edge / unknown nodeを検出
- canonical順で出力

意味上のedgeを新規推測しません。

## 21. テスト要求の構造処理

### `requirement_structure.py`

LLMはTRの本文、テストレベル / 観測方法と、既存TRを再利用するか新規TRにするかを判断します。これらの意味fieldもruntime inputへそのまま渡し、structure scriptは内容を生成・要約せずschemaと構造だけを検査します。Dispositionのmachine schemaはstructure / traceabilityで共通して`{upstream_id, handling, reason, authority_refs[], covered_by_ref}`とし、不要な`covered_by_ref`はnullです。既存ID再利用時は`reuse_id`、新規時は`new`を指定し、runtimeが最終TR IDを割り当てます。

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
- CIなし契約ではTCN → TCまたはDisposition
- missing edge
- orphan
- unknown reference
- stale downstream

許可する直接edgeは`Authority→TR`、`Risk→TR`、`TR→TCN`、`TCN→CI`、`CI→TC`、CIなし契約の`TCN→TC`だけです。別層を飛び越えるedgeや逆向きedgeをclosure根拠として数えません。Dispositionは既存各Skillのhandling集合と必要なreason / Authority条件を検証し、正常なDispositionをmissing扱いしません。

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
| `schema_cases.py` | `schema_kind, document, schema_pointer, context` | `schema:<json_pointer>:<keyword>` | normalized constraints / downstream inputs / unsupported subtrees |
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

- integerはJSON integer
- decimalは符号付き10進文字列で指数表記を禁止し、`Decimal`でcanonical化する
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
- `selection_key`は`^[A-Za-z][A-Za-z0-9._:-]{0,63}$`
- `signals`は§2で列挙した12 keyをすべて持ち、値は`true / false / null`
- signal以外の技法選択、`selection_source`、最終採用技法はこのscript入力に含めない

#### `change_impact.py`

- required: `changed_node_keys[]`, `nodes[]`, `edges[]`
- node: `{node_key, node_type, source_ref}`
- `node_type = Authority | Risk | TR | TCN | CI | TC`
- edge: `{edge_key, from, to, edge_type, evidence_refs[]}`
- `edge_type = depends_on | traces_to | derived_from`
- changed nodeはnodesに存在必須

#### `environment_requirements.py` / `test_data_requirements.py`

- required: `requirements[]`
- requirement: `{requirement_key, dimension_key, operator, authority_refs, source_target_refs}`
- `operator=eq`: `value` typed value必須
- `operator=enum`: `values[]` typed valueを1件以上、重複不可
- `operator=range`: `minimum / maximum` typed value、`minimum_inclusive / maximum_inclusive` boolean必須
- `operator=version_range`: `minimum / maximum` version文字列、inclusive boolean必須
- `operator=boolean`: `value` boolean必須
- `source_target_refs`は`sha256:<64 lowercase hex>`の`target_ref`だけを許可し、test dataでは1件以上、environmentでは空配列を許可する。modelを跨ぐtraceabilityへ`target_key`単独を使用しない
- `test_data_requirements.py`の各正規化済み要求は`data_ref=data:<requirement_key>`を返し、`materialize_coverage.py`の`test_data_requirement_refs[]`はこの`data_ref`だけを参照する

#### `requirement_structure.py`

- required: `authorities[]`, `risks[]`, `test_requirements[]`, `dispositions[]`, `previous_tr_ids[]`
- `authorities[]`: Authority ID文字列
- risk: `{risk_id, priority}`、priorityは`高 / 中 / 低`
- TR draft: `{draft_key, identity_action, reuse_id, text, authority_refs[], risk_refs[], priority, priority_override_reason, test_level, observation_method}`。`draft_key`は入力内一意、`identity_action=reuse|new`。`text`は非空文字列、`test_level / observation_method`は文字列またはnull。reuse時だけ既存`TR-\d{3}`を`reuse_id`へ指定し、new時は`reuse_id=null`
- `previous_tr_ids[]`: `{tr_id, status}`。`status=active|deleted`。reuseは`active`だけ許可し、new採番の最大番号計算にはactive / deletedの両方を含めて削除済み番号を再利用しない
- runtimeはreuse対象の存在・status・重複を検証し、newだけ最大番号+1で採番する。999到達後のnewは`id_space_exhausted`
- `priority_override_reason`は空文字を許可。関連risk最高優先度より低い場合だけ非空必須
- disposition: `{upstream_id, handling, reason, authority_refs[], covered_by_ref}`。handlingは既存TR Disposition集合、`covered_by_ref`は必要なhandlingだけ使用しその他はnull
- outputに`tr_id_map[]: {draft_key, tr_id, identity_action}`と`tr_id_state[]: {tr_id, status}`を返す。固定builderは最終TR IDと入力`text / authority_refs / risk_refs / priority / test_level / observation_method`をjoinし、TR Machine Entityを生成する

#### `condition_structure.py`

- required: `test_requirements[]`, `test_conditions[]`, `requirement_dispositions[]`, `models[]`, `previous_tcn_ids[]`, `previous_model_keys[]`
- TR: `{tr_id, priority, authority_refs[], risk_refs[]}`
- TCN draft: `{draft_key, identity_action, reuse_id, tr_refs[], condition, category, technique, coverage_criterion, authority_refs[], risk_refs[], priority, priority_override_reason}`。`draft_key`は入力内一意。condition / technique / coverage_criterionは非空文字列、categoryは文字列またはnull。意味上の同一性はLLMが`identity_action=reuse|new`として決め、reuse時だけ既存`TCN-\d{3}`を指定する
- requirement dispositionは共通Disposition schemaを使用する
- 各TRはTCNの`tr_refs[]`またはrequirement dispositionのどちらか一方へ閉じ、unknown TR、linked + disposed重複、未閉鎖TRをviolationにする
- TCNの既定priorityは関連TRの最高優先度。より低いpriorityを指定する場合だけ非空`priority_override_reason`を必須にし、runtimeが自動補正しない
- model draft: `{draft_key, technique_slug, selection_source, identity_action, reuse_model_key, parent_tcn_draft_key}`。`draft_key`はmodel内一意、`selection_source=analysis|user|existing_artifact|derived`、`parent_tcn_draft_key`は同じ入力のTCN draftを参照する。reuse時だけ既存`<slug>-\d{3,}`を指定する
- `previous_tcn_ids[]`: `{tcn_id, status}`、`previous_model_keys[]`: `{model_key, technique_slug, parent_tcn_id, status}`。`status=active|deleted`。reuseはactiveだけ許可し、新規採番の最大番号にはdeletedも含める
- runtimeはreuse対象の存在、status、重複、slug一致、最終親TCN一致を検証し、新規TCN / modelだけ既存最大番号+1で採番する
- 1つのmodel keyは同時に1つのTCNだけへ所属する。別TCNへ同じmodel keyを割り当てない
- outputに`tcn_id_map[]: {draft_key, tcn_id, identity_action}`、`model_key_map[]: {draft_key, model_key, parent_tcn_id, identity_action}`、`tcn_id_state[]`、`model_key_state[]`を返す。固定builderはTCN draftの意味fieldと最終TCN IDをjoinしてTCN Machine Entityを、model draftの`technique_slug / selection_source`と最終model key / parent TCNをjoinしてmodel metadata Entityを生成する
- 999到達後の新規TCNは`id_space_exhausted`。model keyは3桁以上を許可し999上限を設けない

#### `equivalence_partitions.py`

- required: `sets[]`
- set: `{set_key, partitions[]}`
- partition: `{partition_key, validity, definition, representative, authority_refs}`
- `validity = valid | invalid`
- `definition.type=enum`: `values[]` typed valueを1件以上
- `definition.type=range`: `minimum / maximum / minimum_inclusive / maximum_inclusive`
- `representative`はtyped valueまたはnull。nullならscriptが一意に選べるenum / numeric rangeだけ自動生成

#### `bva.py`

- required: `boundaries[]`
- boundary: `{boundary_key, side, threshold, inclusive, step, mode, coverage_selection_reason, authority_refs}`
- `side=lower|upper`, `mode=2-value|3-value`。`mode=3-value`では境界リスク、過去不具合、ユーザー明示等の具体的な`coverage_selection_reason`を非空必須とし、2-valueでは空文字を許可する
- `threshold`はtyped integer / decimal / date / local_datetime / fixed_offset_datetime
- `step`は§4のdomain別object形式だけを許可し、threshold型と互換であることを必須にする

#### `domain_testing.py`

- required: `partitions[]`, `borders[]`
- partition: `{partition_key, expression, authority_refs}`。expressionは§5の`border_ref / and / or` ASTだけ
- borderは§5の`border_key / partition_key / relation / coefficients / constant / pivot_key / anchor / pivot_step / authority_refs`だけ
- coefficient / constant / pivot_stepはdecimal文字列
- anchor valueはtyped integer / decimalだけ
- 各borderは同じ`partition_key`のpartition expressionから1回以上参照されること

#### `decision_table.py`

- required: `conditions[]`, `actions[]`, `known_rules[]`, `constraints[]`, `accepted_merges[]`
- condition: `{condition_key, values[], authority_refs}`。valuesはtyped valueを1件以上
- action: `{action_key, values[], authority_refs}`。valuesはtyped valueを1件以上
- known rule: `{rule_key, when, then, authority_refs}`。`when`は全condition keyを1回ずつ、`then`は全action keyを1回ずつ持つ
- constraintsは共通partial assignment
- accepted mergeは§6.1形式

#### `combinatorial.py`

- required: `mode`, `factors[]`, `constraints[]`
- factor: `{factor_key, values[], authority_refs}`。valuesはtyped valueを1件以上
- `mode=exhaustive`: 追加fieldなし
- `mode=base-choice`: `base_assignment`を全factorについて必須
- `mode=t-wise`: `strength` integerを2..factor数で必須。`strength>2`では`coverage_selection_reason`を非空必須
- `mode=mixed-strength`: `global_strength` integerを2..factor数、`subsets[]`を1件以上必須。subsetは`factor_keys[]`と`strength`を持ち、strengthは2..subset factor数。globalまたはsubsetのいずれかがstrength>2なら`coverage_selection_reason`を非空必須

#### `classification_tree.py`

- required: `classifications[]`, `constraints[]`
- classification: `{classification_key, classes[], authority_refs}`
- class: `{class_key, value, authority_refs}`。valueはtyped value
- 同一classificationのclass valueは重複不可

#### `state_transition.py`

- required: `states[]`, `initial_states[]`, `terminal_states[]`, `transitions[]`, `reset_options[]`, `invalid_transition_candidates[]`, `coverage_mode`
- optional: `switch_count`, `coverage_selection_reason`。`coverage_mode=n-switch`だけ`switch_count`必須、`switch_count>=2`では`coverage_selection_reason`を非空必須
- state: `{state_key, authority_refs}`
- transition: `{transition_key, from, event, guard_status, guard_refs, to, authority_refs}`
- `guard_status=true|false|null`
- resetは§9形式
- coverage mode: `all-states | all-transitions | n-switch | round-trip | invalid-transitions`
- `switch_count`はinteger 0..10
- n-switch / round-tripのtarget定義とcanonicalizationは§9を正本とする
- invalid candidateは§9形式

#### `flow_paths.py`

- required: `nodes[]`, `edges[]`, `initial_node_keys[]`, `regions[]`, `loop_specs[]`, `coverage_mode`, `max_path_length`
- node: `{node_key, kind, authority_refs}`。kindは`normal / fork / join / terminal`
- edge: `{edge_key, from, to, guard_status, guard_refs, label, authority_refs}`
- region: `{region_key, fork_node_key, join_node_key, branches[]}`。branchは`{branch_key, edge_keys[]}`
- loop spec: `{loop_key, entry_node_key, edge_keys[], typical_iterations, maximum_iterations, authority_refs}`
- `initial_node_keys[]`は1件以上
- `coverage_mode = node | edge | bounded-path | simple-loop | fork-join`
- `max_path_length`は1..1000
- region / loopの連続性・nest・iteration規則は§10を正本とする

#### `crud_matrix.py`

- required: `entities[]`, `functions[]`, `cells[]`, `consistency_sequences[]`, `operation_dispositions[]`
- entity: `{entity_key, authority_refs}`
- function: `{function_key, authority_refs}`
- cell: `{entity_key, function_key, operations[], authority_refs}`。operationsは`C/R/U/D`の重複なし集合
- consistency sequenceは§11形式
- 個々の空cellは欠陥・N/Aを意味しないため専用`excluded_cells[]`を持たない。entity全体でoperationが存在しない場合だけ`operation_dispositions[]`で扱う
- operation disposition: `{entity_key, operation, handling, reason, authority_refs}`。`handling=not_applicable`、Authority 1件以上

#### `cause_effect.py`

- required: `causes[]`, `effects[]`, `constraints[]`
- cause: `{cause_key, authority_refs}`
- effect: `{effect_key, expression, true_value, false_value, authority_refs}`
- expression ASTは`{"op":"ref","key":"C1"}`、`{"op":"not","arg":...}`、`{"op":"and|or","args":[...,...]}`だけ
- refはcause keyだけを許可し、effect参照は禁止
- true / false valueはtyped value
- constraintは§25.1の共通partial assignmentで、assignment keyはcause keyだけを許可し、`derived.decision_table.constraints`へそのまま渡す

#### `grammar_cases.py`

- required: `start`, `productions[]`, `max_depth`, `mutations[]`
- productionは§25 grammar production key形式
- RHS itemは`{"terminal":"..."}`または`{"nonterminal":"..."}`のどちらか一方
- `max_depth`は1..64
- mutation: `{mutation_key, op, production_key, symbol_index, value}`。opは§13の3種
- deleteではvalue禁止、replace/insertではvalue string必須
- delete / replaceは`symbol_index`がterminal itemを指すこと、insertは0..len(rhs)を許可

#### `schema_cases.py`

- required: `schema_kind`, `document`, `schema_pointer`, `context`
- JSON / OpenAPI documentの非integer JSON numberは`Decimal`としてexactにparseし、binary floatを使用しない
- `enum / const`はscalar / nullだけruntime-v1対応。object / array値を含むsubtreeはunsupported itemへ出す
- `schema_kind = json-schema-2020-12 | openapi-3.0 | html-control`
- json/openapiでは`document`はroot document object、`schema_pointer`はそのdocument内のCoverage対象Schema Objectを指すlocal JSON Pointer。local `$ref`は常に同じ`document`をrootとして解決する
- `context`はJSON Schemaでは`validation`、OpenAPIでは`request|response`、HTMLでは`form-control`
- html-controlでは`document`は`{type, required, min, max, minlength, maxlength, step, pattern, disabled, readonly, multiple}`の対応属性だけを持つobject、`schema_pointer`は空文字列を固定。存在しない属性は省略可能
- OpenAPIでは`readOnly / writeOnly`を§14のrequest / response規則でrequired母集団へ反映する
- html-controlは§14のruntime-v1 type / attribute matrixを正本とする。`type=text`でvalidationへ適用される`pattern`は無視せずcontrol validationを`unsupported`にし、`disabled / readonly`でconstraint validation対象外となるcontrolからinvalid候補を生成しない
- `multipleOf`と対応可能な数値HTML `step`は§14の`grid` constraintへ正規化
- annotation allowlistとunsupported subtree規則は§14を正本とする

#### `ui_pattern_candidates.py`

- required: `pattern`, `attributes`
- `pattern`はcatalog正規名またはalias
- `attributes`は`type / role / required / min / max / minlength / maxlength / step / disabled / readonly / multiple`だけを許可
- catalogにないpatternは`unsupported`

#### `random_testing.py`

- required: `seed`, `case_count`, `distribution`
- distributionは§17の3 schemaのいずれか一つ

#### `metamorphic.py`

- required: `relations[]`
- relationは§18形式のみ。`expected_relation.output_path / output_kind`を必須とする
- `source_id`はrelation内一意
- `follow_ups[]`は1..10,000件で`follow_up_key`をrelation内一意
- 各follow-upの`transforms[]`は1件以上で宣言順に適用する

#### `case_structure.py`

- required: `test_conditions[]`, `coverage_items[]`, `test_cases[]`, `dispositions[]`, `previous_tc_ids[]`
- TCN: `{tcn_id, priority}`
- CI: `{ci_id, tcn_id, priority, authority_refs}`
- TC draft: `{draft_key, identity_action, reuse_id, title_or_purpose, tr_refs[], tcn_refs[], ci_refs[], priority, priority_override_reason, preconditions[], test_data[], steps[], expected_results[], postconditions_or_cleanup[]}`。`draft_key`は入力内一意、`identity_action=reuse|new`。`title_or_purpose`は非空文字列、preconditions / test_data / postconditions_or_cleanupは文字列配列、stepは`{number, text}`で1から連番。reuse時だけ既存`TC-\d{3}`を`reuse_id`へ指定し、new時は`reuse_id=null`
- `previous_tc_ids[]`: `{tc_id, status}`。`status=active|deleted`。reuseはactiveだけ許可し、new採番の最大番号にはdeletedも含めて削除済み番号を再利用しない
- runtimeはreuse対象の存在・status・重複を検証し、newだけ最大番号+1で採番する。999到達後のnewは`id_space_exhausted`
- expected result: `{number, text, authority_refs[]}`。numberは1から連番
- priority_override_reasonは低い優先度へoverrideする場合だけ非空必須
- disposition: `{upstream_id, handling, reason, authority_refs[], covered_by_ref}`
- outputに`tc_id_map[]: {draft_key, tc_id, identity_action}`と`tc_id_state[]: {tc_id, status}`を返す。固定builderは最終TC IDと入力`title_or_purpose / tr_refs / tcn_refs / ci_refs / priority / preconditions / test_data / steps / expected_results / postconditions_or_cleanup`をjoinしてTC Machine Entityを生成する

#### `traceability.py`

- required: `nodes[]`, `edges[]`, `dispositions[]`, `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`
- node: `{node_key, node_type}`。node_typeは`Authority / Risk / TR / TCN / CI / TC`
- edge: `{from, to}`。from / toは既知nodeで、§23の許可直接edgeだけを認める
- disposition: `{upstream_id, handling, reason, authority_refs[], covered_by_ref}`。handlingは対象上流型に対して既存担当Skillが許可するDisposition集合だけを認め、必要なreason / Authority / covered_by_refを検証する
- `runtime_units / current_entities / current_runtime_units`は`workflow_runtime.py`と同じschemaを使用する
- `traceability.py`は各Skillの同一内容`runtime_contract.py`にある共通freshness評価関数を呼び、`runtime_freshness[] / entity_freshness[]`を決定論的に算出する。workflow_runtime resultを入力へ渡さず、self/cycle dependencyを作らない
- stale分析では`entity_freshness[]: {skill, entity_ref, model_key, freshness_status, stale_reasons[]}`を正本にし、stale Entityがcurrentな下流で閉鎖済みと誤判定しない

#### `materialize_coverage.py`

- required: `tcn_id`, `models[]`, `target_annotations[]`, `target_dispositions[]`, `test_data_requirements[]`, `previous_target_id_map[]`, `previous_ci_ids[]`, `previous_expected_result_roots[]`, `merge_groups[]`
- `tcn_id`は`TCN-\d{3}`
- model: `{model_key, skill, runtime_unit_key, input_fingerprint, model_fingerprint, generation_fingerprint, generator_contract_version, support_status, runtime_status, result_status, deterministic_generated, freshness_status, targets[]}`。全modelは`condition_structure.py`で同じ`tcn_id`への1対1所属を検証済みであること
- materialize対象modelは`runtime_status=ok / result_status=ready / deterministic_generated=true / freshness_status=current`を必須にする。`support_status=supported`または、unsupported itemとtarget集合が分離済みの`partial`だけ許可する
- `freshness_status=current`は、現在のMachine Entity / 正規化済み意味入力をpreflight確認した後、現在scriptを再実行して正常生成したresultだけに付与する。保存済みresultをmaterialize入力として直接再利用しない。`materialize_coverage.py`自身はupstream semantic freshnessを再判定しない
- machine target: `{target_ref, target_content_fingerprint, execution_fingerprint, target_key, execution, authority_refs, reference_refs, ...技法固有machine fields}`。`target_content_fingerprint / execution_fingerprint`は`_02` §7.2の式をruntimeが計算する。CI化するtargetでは`execution`必須。priority、expected result、test data要求をLLMに埋め戻させない
- target annotation: `{target_ref, target_content_fingerprint, generation_fingerprint, priority, expected_result_root, test_data_requirement_refs[]}`。Dispositionされないmachine targetにちょうど1件対応し、unknown / duplicate target_refを拒否する。`target_content_fingerprint`と`generation_fingerprint`は現在machine target / modelと一致必須で、以前のtarget内容・上流Entity内容・runtime世代に対するannotationを再利用しない。`expected_result_root`は同一TCN内の内部用local keyで`^[A-Za-z][A-Za-z0-9._:-]{0,63}$`、同じkeyはLLMがAuthorityに基づき同じ期待挙動へ統合可能と判断したtargetだけへ付与する。前回同じ期待挙動groupを再利用すると意味判断した場合は`previous_expected_result_roots[]`の既存keyを維持し、新規groupだけ未使用keyを追加する。製品Authorityそのものとして扱わない
- target disposition: `{target_ref, target_content_fingerprint, generation_fingerprint, handling, reason, authority_refs, covered_by_target_ref}`。`target_content_fingerprint`と`generation_fingerprint`は現在machine target / modelと一致必須。`_02` §7.4のhandlingだけを許可し、同一target_refへannotationとDispositionを同時指定しない。`重複`では`covered_by_target_ref`必須
- `target_ref`は`_02` §7.2の式を再計算して一致必須
- `test_data_requirements[]`は`{data_ref, requirement_key, dimension_key, operator, ...}`で、`data_ref=data:<requirement_key>`を一意にする。annotationの全`test_data_requirement_refs[]`はこの集合に存在必須
- `previous_target_id_map[]`: `{target_ref, model_key, target_key, target_content_fingerprint, ci_id, mapping_status}`。`mapping_status=active|inactive`で、Disposition中targetの直近CIもinactiveとして保持する。同じ`target_ref`でcontent fingerprintが変わった場合はCI IDを維持しても`stale_ci_ids`へ追加する
- `previous_ci_ids[]`: `{ci_id, status}`。`status=active|deleted`で削除済み番号も保持する
- `previous_expected_result_roots[]`: `{expected_result_root, status}`。`status=active|deleted`。同じ意味groupのkey再利用可否はLLMが判断し、runtimeはduplicate / deleted keyの不正reuseを検査する
- merge groupは`_02` §11形式の`model_key / target_refs[] / target_versions[]`で、Dispositionされていない同一TCN・同一model内targetだけを許可する。全target versionは現在machine target / modelと一致必須で、`execution_fingerprint`と`expected_result_root`が全件一致する場合だけ同一CIへ統合する。異なるmodel / 技法はCIを分け、必要なら`case_structure.py`の1 TC draftで複数`ci_refs[]`を参照する。group内の追加test data requirementは§16と同じintersection規則で統合し、conflict / unsupportedならmergeを拒否する
- `target_dispositions[]`にあるtargetはCI採番対象から除外し、generatorの`coverage_summary`自体は変更しない
- outputは`target_id_map[]`、`target_mapping_state[]`、`ci_id_state[]`、`expected_result_root_state[]`、`disposed_target_refs[]`、`coverage_item_rows`、`stale_ci_ids`、`issues`
- `target_id_map[]`: `{target_ref, target_content_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`。active mappingだけを返し、1 target_refから複数CIへのmappingは禁止する
- `target_mapping_state[]`はactive / inactiveと直近`target_content_fingerprint`を保持し、`ci_id_state[]`はactive / deletedを保持する。次回のprevious stateはこれらを正本にする
- 固定builderはactive CIごとに`_02` §4.4のCI Machine Entityを生成する。`covered_targets[]`は同じ`ci_id`へactive mappingされたtargetを`target_ref`順で集約し、各`target_ref / target_key / target_content_fingerprint / execution_fingerprint`を保持する。priority / expected_result_root / Authority / Reference / test data requirementは現在annotation / targetから機械joinし、LLMがCI Entity JSONを再生成しない
- CI Machine Entityの`runtime_dependencies[]`には現在の`materialize_coverage.py` generationを、`upstream_entity_dependencies[]`には親TCNとmodel metadataを保存する。stable target_refのままtarget内容が変わればCI content fingerprintも変わる
- `disposed_target_refs[]`: `{target_ref, handling, covered_by_target_ref}`。Coverage済みtarget数の計算には使用しない

#### `workflow_runtime.py`

- required: `runtime_units[]`, `current_entities[]`, `current_runtime_units[]`, `unsupported_item_closures[]`
- `runtime_units[]`は評価対象unitだけを含み、`qa-workflow::artifact:workflow_runtime:all`自身を含めない。self dependencyも禁止する
- runtime unit: `{skill, runtime_unit_key, model_key, support_status, result_status, runtime_status, runtime_required, deterministic_generated, generation_fingerprint, upstream_entities[], upstream_runtime_units[], unsupported_items[]}`
- `current_entities[]`: `{skill, entity_ref, model_key, content, upstream_entity_dependencies[], runtime_dependencies[]}`。`content`は§4.4のMachine Entityと同一で、共通関数が現在`content_fingerprint`を計算する
- `current_runtime_units[]`: `{skill, runtime_unit_key, generation_fingerprint}`。`(skill, runtime_unit_key)`を一意keyとして保存済み`upstream_runtime_units[]`と比較する
- 各Skillの同一内容`runtime_contract.py`にruntime dependency graphとMachine Entity dependency graphを評価する共通関数を置く。missing dependencyはstale + blocker、duplicateまたはcycleは`invalid_input`
- `unsupported_item_closures[]`: `{skill, runtime_unit_key, generation_fingerprint, item_key, reason_code, handling, reason, authority_refs}`。closureの`generation_fingerprint`は対象runtime unitの現在値と一致必須。`support_status=partial`では`item_key`をunsupported itemのstable keyで必須とし、`reason_code`も現在unsupported itemと一致必須。whole-model `unsupported`では`item_key=null / reason_code=null`を許可するが`generation_fingerprint`一致は必須とする。世代またはreasonが変わった以前のclosureを自動再利用しない
- runtimeは意味上の再利用可否、開始Skill、仕様Authorityの優先関係を再判断しない
- outputは`freshness[]: {skill, runtime_unit_key, generation_fingerprint, freshness_status, stale_reasons[]}`、`entity_freshness[]: {skill, entity_ref, model_key, freshness_status, stale_reasons[]}`、`completion: {can_complete, blockers[]}`、runtime状態表用の正規化rowを返す
- `can_complete=true`には、全runtime unitと対象Machine Entityがcurrent、全unitの`result_status=ready`、runtime required unitが`deterministic_generated=true`、partial / unsupportedの未閉鎖itemが0件であることを必須にする

### unsupported item共通schema

`support_status=partial`で返す`payload.unsupported_items[]`は`{item_key, item_type, source_key, reason_code, authority_refs[]}`で固定します。

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
