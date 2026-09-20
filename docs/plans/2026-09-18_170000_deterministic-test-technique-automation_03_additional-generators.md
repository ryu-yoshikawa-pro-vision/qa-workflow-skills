# テスト分析・テスト技法の決定論的自動化Plan

このファイルはgenerator契約の後半です。[基本generatorと状態遷移](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md)から続けて参照します。

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

入力は`causes[] / effects[] / constraints[]`です。`constraints[]`は[artifact処理・script別入出力契約](./2026-09-18_170000_deterministic-test-technique-automation_03_artifact-processing-and-script-contracts.md) §25.1の共通partial assignmentをcause keyへ適用し、Authority付きのcause間成立不能条件を表します。constraintをLLMが派生先で作り直しません。

1. cause / effect key、AST参照、constraintのcause key / valueを検証する
2. hard limit内で全cause assignmentを列挙する
3. constraintに一致するassignmentを成立不能として識別し、正式known rule / Coverage母集団へ入れない
4. 成立可能assignmentだけeffect action vectorへ変換する
5. `conditions / actions / known_rules / constraints / accepted_merges=[]`を生成する。conditionはcauseの`cause_key / label`、actionはeffectの`effect_key / label`を失わず、入力`constraints[]`も同じ意味のまま渡す
6. child `decision`のidentityを検証し、`derived_child_inputs[]`へ`{child_model_key, model_type:"decision", input:{conditions, actions, known_rules, constraints, accepted_merges:[]}}`を返す

`derived_child_inputs[].input`は`decision_table.py`のscript固有inputと直接互換にし、Cause-Effect側で意味上のmergeを作りません。cause / effectのlabelを派生先でLLMが再生成しません。

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

正規化後のrange / enum / required等から、選択済みchildごとのmachine skeletonを生成します。`schema_cases.py`自身がTechnique Selectionへ新しい技法を追加したりchild modelを発行したりしません。EPのset / partition、BVA boundary、combinatorial factorにはsource JSON Pointer / property名から決定論的に作る非空`label`を含めます。BVA skeletonは`boundary_key / label / side / threshold / inclusive / step / authority_refs`までを持ち、`mode / coverage_selection_reason`は含めません。combinatorial skeletonはfactor / constraintを持ちます。

selected childに完成inputを作るための意味parameterが不足する場合、`schema_cases.py`はchild model keyとstable machine keyを含む`semantic_parameter_requests[]`を返して`result_status=unresolved`にします。例としてBVAはboundaryごとの`mode / coverage_selection_reason`、combinatorialは`mode / strength / subsets / base_assignment`を要求できます。LLMは要求されたparameterだけを補い、schema由来のset / partition / boundary / factor / constraintを再生成しません。

意味parameter込みで同じ`schema_cases.py`を再実行した後、`derived_child_inputs[]`へ`{child_model_key, model_type, input}`を返します。`input`は`ep / bva / comb`の各child generator script固有inputと直接互換にします。選択済みchildに適用可能なmachine skeletonが0件なら`selected_technique_not_derivable` issueを返し、空Coverage modelとして完了させません。`derived.test_data_requirements`も同じ再実行結果から生成し、別builderでschema outputを再構成しません。

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

## 続き

[artifact処理・script別入出力契約](./2026-09-18_170000_deterministic-test-technique-automation_03_artifact-processing-and-script-contracts.md) に続きます。
