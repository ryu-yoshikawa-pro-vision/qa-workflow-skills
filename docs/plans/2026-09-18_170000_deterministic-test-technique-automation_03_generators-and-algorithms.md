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

- `targets`: 技法固有のstable target keyを持つ機械生成対象
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
- enum / integer range等で一意に作れる代表値候補
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

入力は`boundary_key`、`side=lower|upper`、boundary value、包含 / 排他、正の`step`または最小単位、`mode=2-value|3-value`、Authorityを持ちます。

規則:

- step不明時に`±1`を仮定しない
- decimalは`Decimal`
- fixed-offset datetimeは同一instant比較用にUTC正規化できるが、named timezone / DST ruleを推測しない
- exclusive境界は境界値と最初の有効値を区別
- 2-valueは`AT`と隣接partition側の`OTHER`の2 targetを作る
- 3-valueは`BELOW / AT / ABOVE`の3 targetを作る
- lower / upperが同じ具体値になってもCoverage positionを別targetとして保持
- target keyは`bva:<boundary_key>:AT|OTHER|BELOW|ABOVE`。modeで不要なpositionは生成しない

## 5. Domain Testing

### `domain_testing.py`

本PlanではISTQB CTAL-TA v4.0の**Reliable Domain Coverage**を実装します。Simplified Domain Coverageは別modeとして実装せず、Reliableのsubsetとして別名出力もしません。

多変数の線形borderを扱います。一般solverを自然言語式へ適用しません。

各borderは次を持ちます。

```json
{
  "border_key": "B1",
  "relation": "<=",
  "coefficients": {"x": "1", "y": "2"},
  "constant": "-10",
  "pivot_key": "x",
  "anchor": {"y": "3"},
  "pivot_step": "1",
  "authority_refs": ["SPEC-001"]
}
```

式は`sum(coeff_i * value_i) + constant relation 0`です。`relation`は`< / <= / > / >= / = / !=`だけを許可し、`pivot_step`は正のrepresentable単位を必須にします。

`< / <= / > / >=`のReliable Domain Coverage:

- closed border（`<= / >=`）: ON = border上、OFF = outside側の最隣接点、IN = inside側の最隣接点、OUT = OFFよりさらに1 step外側
- open border（`< / >`）: OFF = border上、ON = inside側の最隣接点、IN = ONよりさらに1 step内側、OUT = outside側の最隣接点
- target keyは`domain:<border_key>:ON|OFF|IN|OUT`

`=`:

- ON = border上
- OFF_NEG / OFF_POS = borderの両側の最隣接点
- target keyは`domain:<border_key>:ON|OFF_NEG|OFF_POS`

`!=`:

- OFF = border上
- ON_NEG / ON_POS = borderの両側の最隣接点
- target keyは`domain:<border_key>:OFF|ON_NEG|ON_POS`

処理:

1. key / type / coefficient / positive stepを検証
2. anchorを固定してpivot border valueを求める
3. 上記relation別規則でcoverage pointを生成
4. 各pointを元のborder式へ再代入し、意図したinside / outside / border所属を検証
5. Authority付きconstraintと矛盾しないことを検証
6. relation別required targetがすべて生成できたときだけCoverage completeとする

border valueまたは必要な隣接点がrepresentableでない、pivot coefficientが0、anchor不足、step不明の場合は推測せずblocking issueを返します。LLMがoverride pointを明示する場合も、scriptが所属とstep距離を検証し、規則に一致しなければ`invalid_input`とします。

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

候補をdeterministicに列挙し、LLMが意味上統合してよいか判断します。採用されたmergeは`accepted_merges[]`として`{"merge_key":"DM-001","rule_keys":["R1","R2"]}`を再入力します。`rule_keys`は2件以上、重複不可、すべて同一action vectorであることをscriptが再検証し、don't-care ruleを生成します。Boolean minimizationで最小rule数を目的にしません。

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

出力`derived.factors`は`combinatorial.py`のfactor入力と直接互換にします。

## 9. 状態遷移

### `state_transition.py`

各transitionは`transition_key / from / event / guard / to / authority_refs`を持ちます。

入力:

- `states[]`
- `initial_states[]`
- `terminal_states[]`
- `transitions[]`
- `reset_options[]`
- `invalid_transition_candidates[]`
- `coverage_mode`

transitionの`guard`は説明用文字列ではなく`guard_status=true|false|null`と`guard_refs[]`を持ちます。`true`は成立可能、`false`はAuthorityにより成立不能、`null`は未解決です。`false`をCoverage母集団から外すには`guard_refs`にAuthorityを1件以上必須とします。

invalid transition candidateは`{"candidate_key":"INV-001","from":"draft","event":"publish","authority_refs":["SPEC-010"]}`形式とし、target keyは`state:invalid:<candidate_key>`です。

reset:

```json
{
  "reset_key": "RESET-1",
  "from_states": ["*"],
  "to_state": "draft",
  "authority_refs": ["SPEC-010"]
}
```

機械処理:

- state / transition key整合
- 到達可能性
- all states / all transitions
- 0-switch / 1-switch / 2-switch /任意n-switch
- Round-trip
- invalid transition候補検証
- 各Coverage sequenceの実行開始条件

### 9.1 setup prefix

sequence開始stateへ直接開始できない場合:

1. initial stateからのfeasible shortest pathを探す
2. なければ適用可能reset後のshortest pathを探す
3. 同長ならtransition key列の辞書順
4. guard feasibility不明を含むpathは「構造候補」とし正式実行sequenceにしない

出力は`setup_prefix`と`coverage_sequence`を分離します。実行可能setupがないsequenceを正式Coverage済みにしません。

## 10. Use Case / シナリオ

### `flow_paths.py`

edgeは`edge_key / from / to / guard / label / authority_refs`を持ちます。

node kind:

- `normal`
- `fork`
- `join`
- `terminal`

fork / joinを使う場合は`region_key`を必須にし、同じ`region_key`を持つ1つのforkと1つのjoinだけを対応pairとします。regionのnestは許可しますが、同一region内の複数fork / join、crossing regionは`unsupported`です。

入力に`max_path_length`を必須とし、1〜1000 edgeの整数だけを許可します。すべてのpath列挙はこの長さ以下に制限します。cycleを含まないgraphでも同じ契約を使用します。

処理:

- bounded path
- node / edge Coverage
- unreachable node
- terminalへ到達しないpath
- simple loop Coverage
- fork / join branch Coverage

fork / joinでは、matching forkからjoinまでの各branchを少なくとも1回Coverageする組合せを生成します。scheduler interleavingを仕様なしに列挙しません。順序依存を検証する場合は、順序を明示したstate / event modelを別modelとして入力します。

loop回数は0、1、仕様で明示した代表回数、仕様上の最大回数をCoverage targetにします。typical / maxをscriptが推測しません。

edge証拠とpath証拠は分離します。

## 11. CRUD Testing

### `crud_matrix.py`

ISTQB CTAL-TA v4.0に合わせ、CRUD Testingは**completeness**と**consistency**を分けて扱います。

入力:

- `entities[]`
- `functions[]`
- 各cellの`C / R / U / D` operation集合
- cellごとのAuthority
- `consistency_sequences[]`
- 対象外cell

completeness:

- entity / function / operation key一意性
- cell重複、unknown entity / function / operationを拒否
- matrixに明示された各operationをCoverage targetとする
- target keyは`crud:op:<entity_key>:<function_key>:<C|R|U|D>`
- 仕様上必要なoperationが欠落しているかはLLMがAuthorityからmatrixへ正規化し、空cellだけを理由にscriptが欠陥扱いしない

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
- lifecycle sequenceでは、そのentityのmatrix operationを全体として少なくとも1回Coverageすることを要求
- negative sequenceはAuthorityで明示された「未作成のR/U/D」「削除後のR/U/D」等だけを入力し、scriptが業務上の禁止操作を創作しない
- sequence target keyは`crud:seq:<sequence_key>`

`coverage_summary`は`completeness`と`consistency`を別々に返し、両方completeでのみCRUD modelをcompleteとします。consistency sequenceが未正規化なら`model_status=unresolved`とし、completenessだけで「CRUD Testing完了」と表現しません。

## 12. Cause-Effect Graph

### `cause_effect.py`

boolean AST:

- `ref`
- `not`
- `and`
- `or`

effectはcauseだけを参照します。循環参照は禁止します。

全cause assignmentをhard limit内で列挙し、effect action vectorへ変換します。出力payloadは`decision_table.py`の入力payloadと直接互換にします。

## 13. Syntax-Based Testing

### `grammar_cases.py`

自然言語grammarをparseしません。正規化済みproductionを受けます。

```json
{
  "start": "expr",
  "productions": {
    "expr": [
      [{"terminal":"a"}],
      [{"nonterminal":"expr"},{"terminal":"+"},{"terminal":"a"}]
    ]
  },
  "max_depth": 4
}
```

処理:

- undefined nonterminal / unreachable production
- left recursion等によるdepth超過
- 各productionを少なくとも1回使うshortest valid derivation
- bounded valid case生成
- production Coverage

invalid syntaxは補集合から生成しません。明示mutationは`delete_terminal / replace_terminal / insert_terminal`だけを許可します。

- `delete_terminal`: production内の指定terminal indexを削除
- `replace_terminal`: 指定terminal indexを明示replacement文字列へ置換
- `insert_terminal`: 指定位置へ明示terminal文字列を挿入

mutation結果は`invalid_candidate`であり、scriptだけで「必ずinvalid」と断定しません。製品上invalidであることをexpected resultへ昇格するにはAuthorityまたはLLMの意味判断を必須にします。

## 14. schema / HTML

### `schema_cases.py`

machine-readableな入力はscriptが直接正規化します。

対応subset:

### JSON Schema 2020-12

- `type`
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

`$ref`はruntime内でnetwork解決しません。同一入力document内のlocal JSON Pointerだけ対応し、外部URI referenceは事前dereference済み入力を要求します。local `$ref`の循環参照はこのPlanでは展開せず、その循環subtreeを`unsupported`とします。

### OpenAPI 3.0 Schema

- 上記相当keyword
- boolean `exclusiveMinimum` / `exclusiveMaximum`
- `nullable`

### HTML form control

- type
- required
- min / max
- minlength / maxlength
- step
- disabled
- readonly
- multiple

`pattern`は存在を検出しreferenceへ残しますが、ECMAScript RegExpとPython `re`を同一視して具体値生成しません。

`allOf / anyOf / oneOf / not / if / then / else`等、対応subset外でvalidation意味を変えるkeywordは`unsupported`です。unsupported keywordがvalidation意味へ影響するsubtreeだけを`unsupported`として切り離し、独立して評価できる別property / itemは継続できます。親schemaのvalidation意味をunsupported keywordが左右する場合は、その親subtree全体を`unsupported`にします。annotation keywordだけではschema全体を拒否しません。

正規化後のconstraintはEP / BVA / combinatorial / test data requirementへ直接渡します。

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
- equality一致、enum集合intersection、range intersection、version range intersection
- 空intersectionまたは異なるscalar equalityを矛盾として検出
- 対応operator外は推測せず`unsupported`
- requirement → model / target traceability

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
{"type":"uniform_finite","values":[1,2,3]}
```

- `values`は1件以上、canonical typed valueとして重複不可

```json
{"type":"uniform_integer","minimum":0,"maximum":10}
```

- minimum / maximumはinclusive integer、`minimum <= maximum`

```json
{"type":"categorical","entries":[{"value":"A","weight":3},{"value":"B","weight":1}]}
```

- valueは重複不可
- weightは1〜2,147,483,647のinteger。0 / 負値 / decimalは禁止

weighted categoricalではmodulo biasを避けるrejection samplingを使用します。同じseed、algorithm version、domain、distributionから同じ列を返します。

Random Testingには一般的なCoverage 100%を定義しません。`completion_summary`は`required_case_count = case_count`、`generated_case_count`、`complete = generated_case_count == required_case_count`を返します。case count、時間等の終了条件をLLMが勝手に補いません。本Planのruntimeでは時間依存の終了条件を再現性保証へ含めず、件数で正規化された場合だけ機械生成します。

Random Testingのoracleは生成しません。

## 18. Metamorphic Testing

### `metamorphic.py`

LLMがmetamorphic relationを定義した後を処理します。

各relation:

```json
{
  "relation_key": "MR-001",
  "source_inputs": [{"id":"SRC-001","value":{"amount":"10.0"}}],
  "follow_up_count": 1,
  "transform": {"op":"add_decimal","path":"$.amount","operand":"1.0"},
  "expected_relation": {"op":"monotonic_non_decreasing","output_path":"$.total"},
  "authority_refs": ["SPEC-001"]
}
```

対応input transform:

- `set`: `path`とtyped `value`
- `add_decimal`: decimal fieldの`path`とdecimal文字列`operand`
- `multiply_decimal`: decimal fieldの`path`とdecimal文字列`operand`
- `append`: arrayまたはstringの`path`と型互換な`value`
- `permute`: arrayの`path`と0..n-1の完全なbijectionである`indices`
- `sort`: homogeneous scalar arrayの`path`と`order=asc|desc`

JSON pathはroot `$`からobject key / array indexだけを辿る簡易pathとし、wildcard、filter、recursive descentは`unsupported`です。

対応expected relation:

- `equal / not_equal`: canonical typed valueなら使用可
- `monotonic_non_decreasing / monotonic_non_increasing`: integer / decimalだけ
- `subset / superset`: 重複を持たないcanonical scalar arrayだけ

各expected relationは`output_path`を必須にし、型不一致は`invalid_input`です。

scriptはsource inputから指定件数のfollow-up inputを生成し、relationをmachine evidenceへ保持します。target keyは`mr:<relation_key>:<source_id>:<followup_index>`です。

Metamorphic Testingには一般的なCoverage 100%を定義しません。`completion_summary`は各`relation_key`について要求されたsource数とfollow-up数をすべて生成できたかだけを判定します。各MRを1回実行したことを「十分なCoverage」と表現しません。

relationが製品に妥当か、必要なsource test数、出力のどのfieldへ適用するかはLLMがAuthorityとともに正規化します。

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

対応constraint operatorは`test_data_requirements.py`と同じく、scalar equality、finite enum set、numeric / date / datetime range、version range、boolean requirementです。同じkeyの要求をoperatorごとのintersectionで統合し、互換しない値を矛盾として返します。未対応operatorは`unsupported`とし、環境を実際に準備・検出しません。

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

LLM draft後に次を計算します。

- Authority / RiskがTRまたはDispositionのどちらか一方へ閉じるか
- unknown upstream ID
- linked + disposed重複
- 関連Product Riskからの最低優先度

TR本文や粒度は変更しません。

## 22. テストケースの構造処理

### `case_structure.py`

LLM draft後に次を計算します。

- TCN / CIがTCまたはDispositionへ閉じるか
- unknown upstream ID
- linked + disposed重複
- Coverage Itemからの最高優先度
- 番号付きexpected resultとAuthority対応

具体的な前提・操作・データ・expected resultは生成しません。

## 23. traceability

### `coverage-analysis/scripts/traceability.py`

対象はテスト設計です。

- Authority / Risk → TR
- TR → TCN
- TCN → CI → TC
- CIなし契約ではTCN → TC
- missing edge
- orphan
- unknown reference
- stale downstream

技法別Coverage数値は各技法scriptを正本とし、traceabilityで再計算しません。

## 24. 複数技法の統合

同じ具体的テストへ複数Coverage targetをまとめる意味判断はLLMに残します。

LLMは`merge_group`だけを明示します。scriptは同じgroupについて次を機械統合します。

- Covered Target Keys
- Authority refs
- Reference refs
- 優先度は既存規則の最高値
- test data requirements

異なるexpected resultを持つ候補を同一groupへ統合しません。

## 25. script別入出力契約

次のkeyを全実装で固定します。hash targetは、指定したcanonical objectをSHA-256し`sha256:<64 lowercase hex>`で表します。

| script | required input | stable result / target key | 主payload |
| --- | --- | --- | --- |
| `risk_matrix.py` | `scheme, risks[]` | `risk_id` | level、mapped priority |
| `technique_candidates.py` | 全signal、selection key | `selection_key` | candidates、undetermined、complete |
| `change_impact.py` | changed node、nodes、edges | `impact:<node_key>` | impacted nodes / paths |
| `environment_requirements.py` | requirements[] | `env:<requirement_key>` | merged requirements / conflicts |
| `requirement_structure.py` | authorities、risks、TR、Disposition | `violation:<type>:<entity_id>` | violations / derived priority |
| `equivalence_partitions.py` | sets[] / partitions[] | `ep:<set_key>:<partition_key>` | representative / Coverage |
| `bva.py` | boundaries[] | `bva:<boundary_key>:<position>` | typed value / Coverage |
| `domain_testing.py` | borders[] | §5のrelation別key | point / Coverage |
| `decision_table.py` | conditions、actions、known rules、constraints、accepted merges | `dt:sha256:<assignment_hash>` | rule assignment / action vector / Coverage |
| `combinatorial.py` | mode、factors、constraints、strength | `comb:<mode>:sha256:<target_hash>` | target tuple / rows / Coverage |
| `classification_tree.py` | classifications[] / classes[] | `class:<classification_key>:<class_key>` | `derived.factors` |
| `state_transition.py` | states、transitions、reset、coverage mode | `state:<mode>:sha256:<sequence_hash>`、invalidは§9 key | setup / sequence / Coverage |
| `flow_paths.py` | nodes、edges、region、max path length、coverage mode | `flow:<criterion>:sha256:<path_or_item_hash>` | paths / loops / branch Coverage |
| `crud_matrix.py` | matrix、consistency sequences | §11のoperation / sequence key | completeness / consistency |
| `cause_effect.py` | causes、effects、AST | `ce:sha256:<cause_assignment_hash>` | Decision Table互換rules |
| `grammar_cases.py` | start、key付きproductions、max depth、mutations | `syntax:prod:<production_key>`、mutationは`syntax:mutation:<mutation_key>` | derivations / production Coverage |
| `schema_cases.py` | `schema_kind, schema` | `schema:<json_pointer>:<keyword>` | normalized constraints / unsupported subtrees |
| `ui_pattern_candidates.py` | pattern / alias、attributes | `ui:<pattern_key>:<candidate_key>` | candidate / references |
| `test_data_requirements.py` | requirements[] | `data:<requirement_key>` | merged requirements / conflicts |
| `random_testing.py` | seed、case count、distribution | `random:case:<1-based zero-padded 6 digits>` | generated input / completion |
| `metamorphic.py` | relations[] | §18 key | follow-up input / completion |
| `case_structure.py` | TCN / CI / TC / Disposition | `violation:<type>:<entity_id>` | violations / derived priority |
| `traceability.py` | nodes / edges / stale metadata | `gap:<type>:<entity_id>` | gaps / orphan / stale |

assignment / tuple / sequence / pathのhash対象はIDや表示文ではなく、そのtargetを定義するcanonical key/value構造だけです。hash collisionを検出した場合は`internal_error`として停止し、別targetを同一keyへ統合しません。

script固有inputの詳細schemaは同名unit fixtureの`valid_minimal.json`を正本例として1件ずつ置き、Planと異なるfieldを追加しません。optional fieldは各scriptのSkill referenceへ列挙し、未知fieldは`invalid_input`です。

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
