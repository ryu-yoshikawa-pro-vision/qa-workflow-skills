# テスト分析・テスト技法の決定論的自動化Plan

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
    "1,1": "低"
  }
}
```

- dimension値集合とmatrix keyの完全性を検証
- 入力値がscheme外なら`invalid_input`
- schemeに穴があれば`invalid_input`
- scheme採用理由はLLMへ残す

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

出力payload:

```json
{
  "candidates": ["境界値分析"],
  "undetermined_signals": ["stateful"],
  "complete": false
}
```

候補の最終採用は`test-analysis`が行います。Error Guessingは構造signalだけでは自動採用しません。

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

入力は`boundary_key`、minimum / maximum、包含 / 排他、stepまたは最小単位、2-value / 3-value、Authorityを持ちます。

規則:

- step不明時に`±1`を仮定しない
- decimalは`Decimal`
- fixed-offset datetimeは同一instant比較用にUTC正規化できるが、named timezone / DST ruleを推測しない
- exclusive境界は境界値と最初の有効値を区別
- lower / upperが同じ具体値になってもCoverage positionを別targetとして保持

## 5. Domain Testing

### `domain_testing.py`

多変数数値domainを扱います。一般solverを自然言語式へ適用しません。

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

式は`sum(coeff_i * value_i) + constant relation 0`です。

処理:

1. key / type / coefficientを検証
2. anchorを固定してpivot境界値を計算
3. representableならON pointを生成
4. relation方向と`pivot_step`からIN / OUT pointを生成
5. 各pointがdomain / constraintを満たすか再検証
6. ON / IN / OUT Coverageを計算

境界値が表現不能、pivot coefficientが0、必要step不明の場合は推測せずissueを返します。LLMが明示したoverride pointがある場合は、その所属だけscriptが検証します。

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

候補をdeterministicに列挙し、LLMが意味上統合してよいか判断します。採用されたmergeだけを再入力し、scriptがdon't-care ruleを生成します。Boolean minimizationで最小rule数を目的にしません。

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

独立generatorは追加しません。

LLMがclassification / classの意味を定義し、deterministic adapterがfactor / valueへ変換して`combinatorial.py`へ直接渡します。adapter出力をLLMが再生成しません。

## 9. 状態遷移

### `state_transition.py`

各transitionは`transition_key / from / event / guard / to / authority_refs`を持ちます。

入力:

- states
- initial states
- terminal states
- transitions
- reset options
- guard feasibility
- 根拠付きinvalid transition候補
- Coverage mode

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

入力:

- entities
- functions / operations
- 各cellの`C / R / U / D`期待operation
- Authority
- 対象外cell

処理:

- entity / function key一意性
- cell重複
- unknown entity / function
- 各要求operationのCoverage
- 欠落operation
- 明示されたentity lifecycle sequence候補

空cellを自動で欠陥扱いしません。仕様上operationが必要かはLLMが正規化します。

## 12. Cause-Effect Graph

### `cause_effect.py`

boolean AST:

- `ref`
- `not`
- `and`
- `or`

effectはcauseだけを参照します。循環参照は禁止します。

全cause assignmentをhard limit内で列挙し、effect action vectorへ変換します。出力payloadは`decision_table.py`の入力payloadと直接互換にします。

## 13. grammar-based testing

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

invalid syntaxは補集合から生成しません。明示済みmutation operatorがある場合だけ、そのoperatorを適用してinvalid候補を作ります。

## 14. schema / HTML

### `schema_cases.py`

machine-readableな入力はscriptが直接正規化します。

対応subset:

### JSON Schema 2020-12

- `type`
- `enum`
- `const`
- `required`
- `minimum` / `maximum`
- `exclusiveMinimum` / `exclusiveMaximum`
- `multipleOf`
- `minLength` / `maxLength`
- `minItems` / `maxItems`
- `minProperties` / `maxProperties`

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

`allOf / anyOf / oneOf / not / if / then / else`等、対応subset外でvalidation意味を変えるkeywordは`unsupported`です。annotation keywordだけではschema全体を拒否しません。

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

処理:

- canonical keyによる重複統合
- compatible constraintのintersection
- incompatible constraintの矛盾検出
- requirement → model / target traceability

実際の個人情報・顧客データ・fixture値を自動取得しません。

## 17. Random Testing

### `random_testing.py`

再現可能性のためPRNGを`pcg32-v1`へ固定します。Python `random`の実装versionへ依存しません。

入力:

- uint64 seed
- case count
- domain
- distribution
- Authority / Reference

対応distribution:

- finite valuesのuniform
- integer rangeのuniform
- finite valuesの整数weight付きcategorical

weighted categoricalではmodulo biasを避けるrejection samplingを使用します。同じseed、algorithm version、domain、distributionから同じ列を返します。

Random Testingのoracleは生成しません。

## 18. Metamorphic Testing

### `metamorphic.py`

LLMがmetamorphic relationを定義した後を処理します。

対応input transform:

- `set`
- `add_decimal`
- `multiply_decimal`
- `append`
- `permute`
- `sort`

対応expected relation:

- `equal`
- `not_equal`
- `monotonic_non_decreasing`
- `monotonic_non_increasing`
- `subset`
- `superset`

scriptはsource inputからfollow-up inputを生成し、relationをmachine evidenceへ保持します。relationが製品に妥当か、出力のどのfieldへ適用するかはLLMがAuthorityとともに正規化します。

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

同じkeyの要求を統合し、互換しない値を矛盾として返します。環境を実際に準備・検出しません。

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

## 25. scriptが生成しないもの

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- 新しいrisk score入力
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle
- 意味上の同一性・統合可否

scriptの責務は、対応contractとhard limitの範囲で、与えられたmodelを再現可能に展開し、未解決・非対応・limit超過を隠さないことです。
