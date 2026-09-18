# テスト分析・テスト技法の決定論的自動化Plan

## 1. プロダクトリスク

### `risk_matrix.py`

入力:

```json
{
  "impact": 4,
  "likelihood": 2
}
```

出力:

```json
{
  "impact": 4,
  "likelihood": 2,
  "level": "高"
}
```

実装は現在の`skills/test-analysis/evals/deterministic/validator.py`にある4×4マトリクスと同じ契約にします。ただしvalidatorのコードはimportしません。

scriptは影響度・発生可能性を決めません。1〜4以外は入力エラーです。

## 2. テスト技法候補

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
- datetime
- length / count

必須入力:

- minimum / maximumのうち対象境界
- inclusive / exclusive
- stepまたは最小単位
- 2-value / 3-value

2-value / 3-valueの定義は`coverage-techniques.md`の現行契約を維持します。

重要事項:

- step不明時に`±1`を仮定しない
- decimalはbinary floatではなく`decimal.Decimal`を使う
- date / datetimeは単位を明示する
- exclusive境界では「境界そのもの」と「最初の有効値」の意味を区別する
- lower / upper両方がある場合は重複値を重複Coverage Itemへしない
- overflowやdomain外値を生成する場合、その値を表現可能か確認する

出力には各値がどの境界・位置に対応するかを含めます。

## 5. デシジョンテーブル

### `decision_table.py`

入力:

- conditions
- condition values
- constraints
- known rules / outcomes
- rule source references

処理:

1. 条件値のCartesian productを作る
2. constraintsで成立不能assignmentを除外する
3. 成立可能assignmentごとに既知ruleを照合する
4. outcome未定義を`unspecified`として検出する
5. 同一assignmentに複数outcomeが一致した場合は矛盾として検出する
6. 完全に同一のrule重複を検出する
7. coverage対象rule数を算出する
8. 必要に応じて安全なrule統合候補を出す

scriptは未定義assignmentへ製品挙動を補完しません。

### rule最適化

最適化前の完全rule setを必ず保持します。

don't care化は、差分となる条件値以外が同じで、outcomeとoracle根拠が同一である場合だけ候補にします。

最適化後だけを保存して元ruleを失う実装にはしません。

Boolean minimizationのためだけに外部依存を追加しません。初期実装は隣接ruleの安全な統合までとし、複雑な最小化が必要になった場合に別途評価します。

## 6. 全組合せ・Pairwise・N-wise

### `combinatorial.py`

入力:

- factors
- values
- forbidden / required constraints
- strength
- optional seed

対応mode:

- exhaustive
- 2-wise
- t-wise

### exhaustive

有限domainのCartesian productから禁止assignmentを除外します。

組合せ数が設定上限を超える場合は処理を拒否し、LLMへPairwise / N-wise等の縮約判断を返します。scriptが勝手にCoverage基準を下げません。

### Pairwise

現行`common.py`の考え方と同じく、成立可能な全値ペアをまず計算します。

generatorは成立可能assignmentから未Coverageペアを最も多く覆うassignmentを選ぶgreedy方式を初期候補とします。

要件は「最小行数」ではなく「成立可能2-wiseの100% Coverage」です。

同一入力・同一seedでは同一出力にします。tie-breakはfactor/valueの安定sort等で固定します。

既存validatorの`TCN-D014`、`TCN-D015`、`TCN-D018`〜`TCN-D021`、`TCN-D026`〜`TCN-D028`で独立に検証できるようにします。

### N-wise

strength = t として成立可能なt-tupleを計算し、同様にCoverage setを埋めます。

ただし全assignment × 全t-tupleの計算量が急増するため、次を入力契約にします。

- 因子数
- 各因子の値数
- strength
- 最大成立可能assignment数

上限超過時に無制限計算しません。

PICT / ACTS等の外部engine採用は後述の依存関係判断に従います。

### mixed-strength

自動化自体は可能ですが、初期実装には含めません。

理由は、現行Skill契約がPairwiseを中心にしており、特定因子集合だけ高strengthにする要求が現状確認できないためです。

将来追加する場合も`combinatorial.py`の入力拡張で扱い、新Skillは増やしません。

## 7. Classification Tree

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

- each-choice / minimum criterion
- exhaustive
- Pairwise / N-wise

classification / classの意味的分解はLLMに残します。

## 8. 状態遷移

### `state_transition.py`

入力:

- states
- initial states
- transitions
- event
- guard
- next state
- source reference
- optional reset information

機械処理:

- 未知state参照
- transition重複
- 到達不能state
- initial stateから到達不能なtransition
- outgoing transitionのないdead end候補
- 全state Coverage
- 全valid transition Coverage
- transition-pair Coverage
- n-switch Coverage
- 指定Coverage対象のpath候補生成

invalid transitionは「仕様で許可されたevent集合と有効遷移が十分明示されている」場合だけ補集合候補を出します。

「定義がないから拒否される」とは推論しません。

### path生成

最短1本で全遷移を通すことを必須にしません。

reset可能性が不明な場合、1つの巨大pathへ無理に連結せず複数pathを返します。

既存状態へ到達するためのprefixはBFS等で生成できますが、guardを満たす具体データはLLM / 他generator側の責務です。

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

処理:

- main / alternative path候補
- edge Coverage
- node Coverage
- 到達不能node
- terminalへ到達しないpath
- loopを指定回数に制限したpath列挙

自然言語の業務フローからgraphを作るのはLLMです。

無限loopを防ぐため、cycleがある場合は明示boundなしの全path列挙を拒否します。

## 10. Cause-Effect Graph

### `cause_effect.py`

LLMがcause、effect、論理関係をJSON ASTへ正規化します。

scriptは可能なcause assignmentを列挙し、effectを評価してDecision Table入力へ変換します。

最終的なrule generation / coverageは`decision_table.py`へ委ねます。

任意の自然言語論理式をparseする独自言語は追加しません。

## 11. schema-based test data

### `schema_cases.py`

初期対応対象は、一般的で一意に解釈できる制約に限定します。

候補:

- type
- required / optional
- enum
- minimum / maximum
- exclusiveMinimum / exclusiveMaximum
- minLength / maxLength
- nullable
- arrayのminItems / maxItems
- HTML相当のmin / max / minlength / maxlength / required

これらを同値partition / BVA / enum Coverageへ変換します。

`pattern`や`format`は「制約あり」という候補は作れますが、任意regexやメールアドレス等の有効・無効具体値を標準ライブラリだけで完全生成しません。仕様またはLLMが具体値を与えた場合に所属検証へ使います。

OpenAPI / JSON Schema全仕様への完全準拠parserを新規実装しません。必要なsubsetだけを対象にします。

## 12. grammar-based testing

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

BVA、partition、schema、enum、組合せの生成結果を、Coverage Itemへ利用しやすい共通の候補行へ整形できます。

ただし「共通TestData framework」は作りません。各generatorは自分のJSON出力を返し、`test-condition-design`が成果物へ統合します。

異なるgenerator結果の直積が必要な場合だけ`combinatorial.py`へ明示的に渡します。

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

- missing closure
- orphan
- unknown reference
- covered / partial / missingの計数
- Coverage率

修正Skillの判断は、既存の責任分界で一意に決められる構造欠陥だけ機械化します。意味上の原因判断は`coverage-analysis`に残します。

## 15. scriptが生成してはいけないもの

どのgeneratorでも次は生成しません。

- 新しい仕様根拠
- 未定義のexpected result
- 根拠のないinvalid behavior
- リスクscore
- E2E実装コード
- 「一般的にはこう」という理由だけの製品固有oracle

generatorの役割は、与えられたモデルを漏れなく・再現可能に展開するところまでです。
