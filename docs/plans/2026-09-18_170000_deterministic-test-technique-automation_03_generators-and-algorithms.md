# テスト分析・テスト技法の決定論的自動化Plan

## 1. プロダクトリスク

### `risk_matrix.py`

入力:

```json
{
  "scheme": "repository-default",
  "impact": 4,
  "likelihood": 2
}
```

出力:

```json
{
  "scheme": "repository-default",
  "impact": 4,
  "likelihood": 2,
  "level": "高"
}
```

`scheme=repository-default`の場合だけ、現在の`test-analysis/references/guidance.md`にある4×4マトリクスを独立実装して使用します。validatorのコードはimportしません。

案件固有のリスク評価方式が存在する場合、このscriptはその方式を解釈・代替しません。`test-analysis`は案件固有方式を維持し、`RISK-D005`側もリポジトリ標準方式を使用するケースだけ4×4再計算を要求するよう整合させます。

scriptは影響度・発生可能性を決めません。標準方式では1〜4以外を入力エラーにします。

## 2. テスト技法候補## 2. テスト技法候補

### `technique_candidates.py`

自然言語ではなく、正規化済みsignalを入力にします。

例:

```json
{
  "ordered_domain": true,
  "explicit_boundaries": true,
  "equivalence_classes": true,
  "multiple_discrete_conditions": false,
  "stateful": false,
  "multiple_factors": false
}
```

出力は既存の正規技法名だけを使用します。

- 同値分割
- 境界値分析
- デシジョンテーブル
- 状態遷移
- Pairwise / 組合せ
- エラー推測
- シナリオ / ユースケース

規則例:

- 明示境界を持つ順序domain → 境界値分析候補
- behaviorally equivalentなclassが明示済み → 同値分割候補
- 複数の離散条件が結果を決める → デシジョンテーブル候補
- 状態・event・guardがある → 状態遷移候補
- 複数因子を横断して相互作用を見る → Pairwise / 組合せ候補
- flow / actor pathが主対象 → シナリオ / ユースケース候補

Error Guessingは構造だけで自動選択しません。過去不具合等の証拠をLLMが確認した場合だけ従来契約で採用します。

## 3. 同値分割

### `equivalence_partitions.py`

同値partitionの「発見」は自動化しません。LLMが次を構造化した後を自動化します。

```json
{
  "partitions": [
    {
      "id": "P1",
      "kind": "valid",
      "domain": {"type": "integer", "minimum": 1, "maximum": 10}
    },
    {
      "id": "P2",
      "kind": "invalid",
      "domain": {"type": "integer", "maximum": 0}
    }
  ]
}
```

機械処理:

- partition ID重複
- 空partition
- 有限範囲で明確な重複がある場合の検出
- enum partitionの重複値
- valid / invalidの同一値重複
- representative valueが入力にある場合の所属検証
- enum、整数範囲等で一意に代表候補を決められる場合の候補生成
- partition coverage計算

整数範囲の代表値を機械生成する場合は、「中央値が業務上代表的」とは扱いません。生成値はCoverage用の候補であり、特定値に意味がある場合はLLMが上書きできます。

文字列意味、業務カテゴリ、自由記述等はscriptがpartitionを発見しません。

## 4. 境界値分析

### `bva.py`

対応domain:

- integer
- decimal
- date
- timezoneを持たないlocal datetime
- length / count

必須入力:

- minimum / maximumのうち対象境界
- inclusive / exclusive
- stepまたは最小単位
- 2-value / 3-value

2-value / 3-valueの定義は`coverage-techniques.md`の現行契約を維持します。

重要事項:

- step不明時に`±1`を仮定しない
- decimalはJSON上では10進文字列として受け取り、binary floatではなく`decimal.Decimal`を使う
- dateは`YYYY-MM-DD`、local datetimeはISO 8601形式で受け取り、最小単位を明示する
- timezone / DSTを含むdatetimeは初回対応から外し、実行環境のlocal timezoneを暗黙に使用しない
- exclusive境界では「境界そのもの」と「最初の有効値」の意味を区別する
- lower / upper両方がある場合は重複値を重複Coverage Itemへしない
- overflowやdomain外値を生成する場合、その値を表現可能か確認する

出力には各値がどの境界・位置に対応するかを含めます。

## 5. デシジョンテーブル

### `decision_table.py`

初回実装では、LLMが各ruleを完全assignmentへ正規化してから渡します。部分ruleやrule priorityは導入しません。

入力:

- conditions
- condition values
- `forbidden_constraints`
- 完全assignmentのknown rules / outcomes
- condition / outcome / rule source references

処理:

1. 条件値のCartesian productを作る
2. `forbidden_constraints`で成立不能assignmentを識別する
3. 成立可能assignmentごとに既知ruleを照合する
4. outcome未定義を`unspecified`として検出する
5. 同一assignmentに複数outcomeが定義されている場合は矛盾として検出する
6. 完全に同一のrule重複を検出する
7. 成立可能rule、成立不能rule、unspecified ruleを分離して返す
8. coverage対象rule数を算出する

成立不能assignmentは捨てず、制約ID / source referenceとともに返し、`test-condition-design`の`カバレッジ候補の扱い`へ`成立不能`として閉じられるようにします。

scriptは未定義assignmentへ製品挙動を補完しません。

初回実装ではdon't care化やBoolean minimizationを行いません。完全rule setの生成、欠落・重複・矛盾の検出を先に正しく固定します。rule最適化は自動化可能な候補として一覧に残しますが、現在の要求を満たすための初回runtimeには含めません。

## 6. 全組合せ・Base Choice・Pairwise・N-wise

### `combinatorial.py`

入力:

- factors
- values
- `forbidden_constraints`
- mode
- N-wiseの場合のstrength
- Base Choiceの場合の各factorのbase value
- source references

対応mode:

- exhaustive
- base-choice
- 2-wise
- t-wise

すべてのmodeで、候補順序とtie-breakを固定し、乱数を使用しません。

### exhaustive

有限domainのCartesian productから禁止assignmentを識別します。

成立不能assignmentは消去だけせず、制約根拠付きの除外候補として返します。

### Base Choice

LLMが各factorのbase valueを意味根拠付きで選択した後に使用します。

1. 全base valueの組合せを1件作る
2. 各factorについて、そのfactorだけを各non-base valueへ置き換える
3. `forbidden_constraints`を適用する
4. base組合せ自体または必須置換組合せが成立不能なら、scriptが別のbase valueを勝手に選ばず入力矛盾として返す

### Pairwise

現行`common.py`の考え方と同じく、成立可能な全値ペアを独立に計算します。

generatorは成立可能assignmentから未Coverageペアを最も多く覆うassignmentを選ぶgreedy方式を初期候補とします。

要件は「最小行数」ではなく「成立可能2-wiseの100% Coverage」です。

同一入力では同一出力にします。factor / value / assignmentのtie-break規則を安定させます。

現行validatorは部分assignment形式の禁止制約だけを独立再計算できるため、初回runtimeも同じ制約表現に限定します。

### N-wise

strength = t として成立可能なt-tupleを計算し、同様にCoverage setを埋めます。

高いinteraction strengthをscriptが自動選択しません。tはユーザー指定、案件コンテキスト、具体的なリスク、過去不具合等の根拠をLLMが確認して入力します。

### 計算量と出力量の上限

因子数・値数・strengthから事前に計算可能なraw Cartesian sizeを確認し、列挙中もassignment数、Coverage tuple数、生成行数、出力件数のhard limitを監視します。

- 上限値は実装時に代表fixtureで検証し、script定数とtestで固定する
- semantic inputとしてLLMに「最大成立可能assignment数」を推測させない
- 上限超過時は`limit_exceeded`として終了する
- exhaustiveをPairwiseへ、N-wiseを低いstrengthへ勝手に変更しない
- 部分生成を100% Coverageとして返さない

PICT / ACTS等の外部engine採用は後述の依存関係判断に従います。

### mixed-strength

自動化自体は可能ですが、初期実装には含めません。

理由は、現行Skill契約がPairwiseを中心にしており、特定因子集合だけ高strengthにする要求が現状確認できないためです。

将来追加する場合も`combinatorial.py`の入力拡張で扱い、新Skillは増やしません。

## 7. Classification Tree## 7. Classification Tree

独立generatorを増やさず、LLMがClassification Treeを次へ正規化します。

```json
{
  "classifications": {
    "Browser": ["Chrome", "Edge"],
    "Role": ["Admin", "Member"]
  },
  "constraints": []
}
```

その後は`combinatorial.py`へ渡します。

対応Coverage:

- exhaustive
- Base Choice
- Pairwise / N-wise

classification / classの意味的分解はLLMに残します。

## 8. 状態遷移

### `state_transition.py`

入力:

- states
- initial states
- terminal states
- transitions
- event
- guard
- next state
- source reference
- optional reset information
- 明示的に採用されたinvalid transition候補
- 要求するCoverage mode

機械処理:

- 未知state参照
- transition重複
- initial stateからのgraph上の到達可能性
- outgoing transitionのない状態の列挙
- 全state Coverage
- 全valid transition Coverage
- transition-pair / n-switch Coverage
- Round-trip Coverage
- 指定Coverage対象のpath候補生成
- 根拠付きで明示されたinvalid transition候補の構造検査

graph上の到達可能性と、guardを含む実行可能性を分けます。scriptがguard条件を評価できない場合は「graph上は到達可能 / 到達不能」までを返し、具体データを含む実行可能性を断定しません。

outgoing transitionがない状態も、scriptは構造事実として返します。入力でterminal stateと明示されている場合は正常終端として区別し、それ以外を自動的に欠陥やdead endとは断定しません。

### n-switch

n-switchはN+1個の連続するvalid transitionとして扱います。

- 0-switch = 1 transition
- 1-switch = 2連続transition
- 2-switch = 3連続transition

2-switch以上を高リスクだけから機械選択せず、具体的なsequence failure risk等の根拠がある場合にLLMがCoverage基準として指定します。

### Round-trip

round tripは、start stateとend stateが同一で、途中のstateを重複しないloopとして構造的に列挙します。

guardを満たすデータや、そのloopが業務上の対象範囲かはLLMに残します。cycle数が上限を超える場合は`limit_exceeded`とし、黙って一部loopだけを100% Coverageとして扱いません。

### invalid transition

現行`coverage-techniques.md`の契約を維持し、有効遷移集合の補集合から全invalid transitionを機械生成しません。

仕様、プロダクトリスク、過去不具合等の根拠をLLMが確認して明示したinvalid transition候補だけを入力し、source referenceとCoverageを検査します。

### path生成

最短1本で全遷移を通すことを必須にしません。

reset可能性が不明な場合、1つの巨大pathへ無理に連結せず複数pathを返します。

既存状態へ到達するためのprefixはgraph上のBFS等で生成できますが、guardを満たす具体データはLLM / 他generator側の責務です。

## 9. 明示flowのpath列挙

### `flow_paths.py`

Use Caseやシナリオに明示的な分岐graphがある場合だけ使用します。

入力:

- nodes
- edges
- start
- terminal
- guard / branch label
- loop bound
- source references
- main / alternative等の分類が仕様で明示されている場合はその分類

処理:

- bounded path候補
- edge Coverage
- node Coverage
- graph上の到達不能node
- terminalへ到達しない構造path
- loopを指定回数に制限したpath列挙

scriptはgraph構造だけからmain / alternativeを推測しません。入力で分類済みの場合だけその分類を保持します。

自然言語の業務フローからgraphを作るのはLLMです。guardを評価できない場合、scriptはgraph上のpathだけを扱います。

cycleがある場合は明示boundなしの全path列挙を拒否します。acyclic graphでもpath数が出力上限を超える場合は`limit_exceeded`とします。

## 10. Cause-Effect Graph## 10. Cause-Effect Graph

### `cause_effect.py`

LLMがcause、effect、論理関係をJSON ASTへ正規化します。

scriptは可能なcause assignmentを列挙し、effectを評価してDecision Table入力へ変換します。

最終的なrule generation / coverageは`decision_table.py`へ委ねます。

任意の自然言語論理式をparseする独自言語は追加しません。

## 11. schema-based test data

### `schema_cases.py`

schema種別とdialectを混同しません。初回入力で`schema_kind`を必須にします。

初回対応候補:

- `json-schema-2020-12`
- `openapi-3.0-schema`
- `html-form-control`

JSON Schema / OpenAPIでは、対応dialectで意味が一意に決まるsubsetだけを処理します。

- type
- required / optional
- enum
- minimum / maximum
- exclusiveMinimum / exclusiveMaximum
- minLength / maxLength
- nullableまたはnull型の扱いはdialectごとに分離
- arrayのminItems / maxItems

HTML form constraintでは`input_type`またはcontrol種別を必須にし、そのtypeへ適用される属性だけを扱います。

- `required`
- `min` / `max`
- `minlength` / `maxlength`
- `step`

HTMLの`minlength`は`required`を意味しないため、`required`がない空値を自動でinvalid partitionへ入れません。

HTMLの`step`はinput typeごとに単位・既定値・step baseが異なるため、type semanticsまたは正規化済みstep情報なしにBVA値を作りません。

`pattern`は初回runtimeでPython `re`へ変換して評価しません。制約が存在する事実とsource referenceだけを保持し、具体的なvalid / invalid値生成や所属判定は行いません。

これらの制約を同値partition / BVA / enum Coverageへ変換します。未対応dialectやkeywordは黙って別仕様として解釈せず`unsupported`として返します。

OpenAPI / JSON Schema全仕様への完全準拠parserを新規実装しません。

## 12. grammar-based testing## 12. grammar-based testing

任意BNF / EBNF parserは初回実装しません。

LLMが次の有限production表現へ正規化できる場合だけ、bounded derivationを生成します。

```json
{
  "start": "expr",
  "productions": {
    "expr": [["number"], ["number", "+", "number"]],
    "number": [["0"], ["1"]]
  },
  "max_depth": 3
}
```

機械処理:

- depth内のvalid derivation
- production rule Coverage
- 1規則を置換 / 欠落させるinvalid候補

invalid候補の期待結果は自動確定しません。

## 13. test data matrix

test data matrixは独立runtime scriptを追加しません。

BVA、partition、schema、enum、組合せの生成結果を`test-condition-design`がCoverage Itemへ統合するときの整理方法として扱います。

- 各generatorは安定した候補keyとsource referenceを返す
- 同じ検証責務を複数generatorが生成した場合は、1つへ統合するか既存の`重複`扱いへ閉じる
- 同じ入力値だからという理由だけで意味上異なるCoverage Itemを統合しない
- 異なるgenerator結果の直積が必要な場合だけ`combinatorial.py`へ明示的に渡す

「共通TestData framework」や新しいID体系は作りません。

## 14. 追跡性

### `coverage-analysis/scripts/traceability.py`

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

の必要edgeを既存契約に従って確認します。

出力:

- missing structural closure
- orphan
- unknown reference
- 構造上のcovered / missing件数
- 構造上の閉鎖率

このscriptが算出するのはID graphの構造事実です。IDが接続されているだけで意味上のCoverageが成立したとは判定しません。

`充足 / 部分充足 / 未充足`、テストケースが上流意図を実際に検証しているか、扱いの意味的妥当性は既存`coverage-analysis`に残します。

修正Skillの判断は、既存の責任分界で一意に決められる構造欠陥だけ機械化します。

## 15. scriptが生成してはいけないもの## 15. scriptが生成してはいけないもの

どのgeneratorでも次は生成しません。

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- リスクscore
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle

generatorの役割は、与えられたモデルを漏れなく・再現可能に展開するところまでです。
