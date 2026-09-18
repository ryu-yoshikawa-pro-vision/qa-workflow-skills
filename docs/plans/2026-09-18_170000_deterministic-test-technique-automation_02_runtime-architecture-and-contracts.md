# テスト分析・テスト技法の決定論的自動化Plan

## 1. 実行時アーキテクチャ

### 1.1 基本経路

実行経路を次へ変更します。

```text
仕様 / Figma / Q&A / 実装 / 既存成果物
  ↓
LLM
  ├─ 条件
  ├─ domain / partition
  ├─ 境界
  ├─ 状態 / event / guard
  ├─ 因子 / 値
  ├─ 制約
  ├─ flow
  └─ 現在有効な仕様根拠
  ↓
Skill内script
  ├─ 列挙
  ├─ 組合せ生成
  ├─ 成立可能性
  ├─ カバレッジ計算
  └─ 構造矛盾検出
  ↓
LLM
  ├─ テスト条件 / カバレッジ項目へ統合
  ├─ 根拠を付与
  └─ 人間が読める成果物へ整形
  ↓
既存の実行時自己検証
  ↓
開発・回帰時の決定論的 / 意味評価
```

scriptは自然言語の仕様本文を直接解釈しません。LLMがscriptの入力契約まで正規化します。

### 1.2 評価runtimeとの分離

`EVALS.md`の現行契約を維持します。

Skill実行時に次をimportまたは直接呼び出しません。

- `scripts/skills/evals/deterministic/`
- `scripts/skills/evals/semantic/`
- `skills/*/evals/deterministic/validator.py`

理由は次のとおりです。

- 現行`EVALS.md`が実行時自己検証と開発・回帰評価を分離している
- Skill単体利用では`skills/<skill-name>/`だけをコピーできることが既存の移植契約
- generatorとvalidatorが同じ実装を共有すると、同じ不具合で生成と評価が同時に誤る可能性がある

実行時scriptは各Skill package配下へ置き、評価側は独立実装で出力を再計算・照合します。

## 2. 追加する実行時script

### `test-analysis`

```text
skills/test-analysis/
└── scripts/
    ├── risk_matrix.py
    └── technique_candidates.py
```

`risk_matrix.py`は、案件固有のリスク評価方式が採用されていない場合だけ、確定済みの影響度・発生可能性を受け取り、リポジトリ標準の4×4マトリクスからレベルを返します。案件固有方式がある場合はこのscriptで上書きしません。

`technique_candidates.py`は自然言語を読まず、正規化済みの問題構造を受け取ります。例えば`ordered_boundary=true`、`discrete_conditions=true`、`state_model=true`、`multiple_factors=true`等の明示signalから、既存の技法集合の候補を返します。候補を最終採用するかは`test-analysis`が判断します。

### `test-condition-design`

```text
skills/test-condition-design/
└── scripts/
    ├── equivalence_partitions.py
    ├── bva.py
    ├── decision_table.py
    ├── combinatorial.py
    ├── state_transition.py
    ├── flow_paths.py
    ├── cause_effect.py
    ├── schema_cases.py
    └── ui_pattern_candidates.py
```

初回から汎用framework、plugin機構、generator registryは追加しません。各scriptが明確な1責務を持ちます。

複数scriptで同じ有限domain制約評価が重複した場合だけ、実装時に`scripts/_finite_domain.py`等の内部helperへ切り出します。将来利用のためだけには共通化しません。

### `coverage-analysis`

```text
skills/coverage-analysis/
└── scripts/
    └── traceability.py
```

既存validatorにある`compute_graph_gaps()`相当の考え方をSkill runtime側でも利用できるようにします。ただし評価runtimeからのimportは行わず、実行時の入出力契約に合わせて独立実装します。

### 正規技法名の扱い

runtime scriptを追加しても、`test-analysis`の正規技法名は現在のvalidatorが許可する集合を維持します。

N-wise、Base Choice、Classification Tree、Round-trip等は既存技法の内部Coverage modeまたは入力形式として扱い、script追加だけを理由に正規技法名を増やしません。正規技法名自体を増やす場合は、`test-analysis`、`test-condition-design`、trigger / deterministic / semantic evalを別途整合させます。

## 3. 共通の入出力方針

### 3.1 JSONを機械入力とする

scriptへMarkdown表を直接渡しません。

LLMが技法ごとのJSONへ正規化し、scriptはJSONを読み、JSONを返します。Markdown化はSkill側の責務です。

例:

```json
{
  "domain": {
    "type": "integer",
    "minimum": 1,
    "minimum_inclusive": true,
    "maximum": 100,
    "maximum_inclusive": true,
    "step": 1
  },
  "method": "3-value"
}
```

JSON schema用の新規外部依存は入れず、Python標準ライブラリで必須key、型、許可値を検証します。

### 3.2 値の表現

JSON上の値表現を技法ごとに曖昧にしません。

- `integer`: JSON integer
- `boolean`: JSON boolean
- enum / 識別子: JSON string
- `decimal`: `type: "decimal"`を明示し、値は10進文字列として渡して`decimal.Decimal`で解釈する
- `date`: `YYYY-MM-DD`
- 初回対応する日時: timezoneを持たないlocal datetimeだけとし、ISO 8601形式と最小単位を明示する
- Pairwise等の同一factor内では値の型を混在させない

値に`,`、`;`、`=`、`|`等が含まれてもJSON上では通常の値として保持します。Markdown成果物へ変換するときも、delimiter依存の文字列を機械契約にせず、validatorが曖昧なく復元できる表現へ更新します。

### 3.3 CLI契約

scriptは原則として次の形に揃えます。

```bash
python skills/test-condition-design/scripts/bva.py --input path/to/input.json
```

- 成功時: JSONをstdoutへ出力
- 失敗時: 非0終了し、`invalid_input`、`unsupported`、`limit_exceeded`、`internal_error`のいずれかを識別できる診断をstderrへ出力
- 診断へ入力JSON全体や実データ全文をdumpしない。field名、index、制約ID等の特定に必要な情報だけを出す
- 通常実行でリポジトリファイルを変更しない
- networkへアクセスしない
- 乱数を使う技法を将来追加する場合はseedを入力で明示し、同一seedで再現できること
- Pythonの`eval()` / `exec()`で制約式を実行しない

必要性が出るまで`--output`や複数出力formatは追加しません。

### 3.4 仕様根拠をscriptで作らない

LLMが仕様から抽出した境界、partition、rule、transition、constraint等には、現在有効な仕様根拠へ対応付けられる場合は`source_refs`を必須で保持します。scriptは`source_refs`を変更せず、生成した候補へ引き継ぎます。

ただしscriptは次を行いません。

- 一般慣習から`SPEC-xxx`を作る
- UI pattern referenceを製品固有の期待結果へ変換する
- リスクから製品挙動を推測する
- 実装コードの現状を仕様として昇格する

期待結果根拠が不足する生成候補は、`test-condition-design`が完成済みCoverage Itemへ無条件に採用しません。

### 3.5 決定論的な順序と候補識別

同じ入力から同じ候補順序を返すことも決定論性に含めます。

- 入力配列の意味を保つ必要がある場合は入力順を維持する
- 集合計算から得た候補は、技法ごとに定義した安定sortで順序を固定する
- generator出力には成果物IDではない安定した候補keyを持たせ、LLMがMarkdownへ統合するときの並び順と重複判定に使う
- `TCN-xxx-CIxx`等の既存ID形式は変更せず、候補keyを新しい公開ID体系にはしない

## 4. 正規化入力

### 4.1 有限domain

Decision Table、組合せ、Classification Tree等は、次の形へ正規化します。

```json
{
  "factors": [
    {
      "name": "role",
      "values": ["admin", "member"]
    },
    {
      "name": "visibility",
      "values": ["public", "private"]
    }
  ],
  "constraints": []
}
```

値はscriptが意味を推測しないため、文字列として扱える形を基本とします。数値比較が必要な技法では型情報を明示します。

### 4.2 制約

初回実装では、既存Pairwise validatorが独立に再計算できる部分assignment形式の禁止制約だけを共通契約にします。

例:

```json
{
  "forbidden_constraints": [
    {
      "role": "member",
      "visibility": "private"
    }
  ]
}
```

この制約は「assignmentが指定されたすべての因子=値を満たす場合、そのassignmentは成立不能」を意味します。

初回実装では次を共通制約として追加しません。

- `and` / `or` / `not`等の汎用JSON AST
- `lt` / `lte` / `gt` / `gte`等の算術制約
- required constraint
- 独自文字列DSL

数値境界はBVA / schema等の責務で扱います。Decision TableやN-wiseで部分assignmentだけでは表せない具体的要求が確認された場合に、generatorと独立validatorの両方を同時に拡張します。

## 5. LLMとscriptの責務境界

### LLMが担当するもの

- 仕様から条件・因子・状態・境界・制約を抽出する
- 現在有効な仕様根拠へ対応付ける
- 「同じ挙動になる値の集合」を同値partitionとして定義する
- 境界の型、step、包含 / 排他を確定する
- Decision Tableのaction / expected resultを仕様から確定する
- 状態遷移の合法 / 非合法を仕様根拠に基づいて定義する
- riskの影響度・発生可能性を根拠付きで決める
- script出力をテスト条件 / Coverage Itemへ統合する

### scriptが担当するもの

- 同じ入力に対して同じ計算結果を返す
- 組合せ・境界値・rule・transition・pathを列挙する
- 制約を適用する
- カバレッジを計算する
- graph上の到達不能、重複、構造矛盾、欠落を検出する。guardの意味を評価できない場合は実行可能性まで断定しない
- 入力契約不足を明示的に失敗させる

## 6. Skill instructionの変更

### `test-analysis/SKILL.md`

次を追加します。

- 案件固有のリスク評価方式がなく、リポジトリ標準方式を使用すると確定している場合だけ`scripts/risk_matrix.py`でレベルを算出する
- 問題構造が正規化できる場合は`scripts/technique_candidates.py`を補助的に使う
- script結果を根拠なく上書きしない
- script失敗時は`invalid_input`、`unsupported`、`limit_exceeded`、`internal_error`を区別する
- 入力不足が仕様不足に由来する場合は既存停止条件 / ルーティングへ従い、計算量上限ではCoverage方式の判断を`test-condition-design`へ戻す
- scriptを実行できないAgent環境では手計算結果を「scriptで決定論的に生成した結果」と扱わない

### `test-condition-design/SKILL.md`

次を追加します。

- 対応技法にscriptがあり、入力契約を満たす場合はscript生成結果を使用する
- LLMが手計算でscript結果を置き換えない
- scriptに渡す構造化入力と現在有効な仕様根拠の対応を確認する
- scriptが生成した候補の期待結果根拠が不足する場合は完成済みCoverage Itemにしない
- Error GuessingとScenario / Use Caseの意味判断は従来どおりLLMに残す

### `coverage-analysis/SKILL.md`

次を追加します。

- 追跡グラフが構築済みなら`scripts/traceability.py`で機械的なgap / orphan / closureを算出する
- 意味上のedgeそのものはLLMが作る
- script結果と意味評価を混同しない

## 7. 既存成果物との互換性

既存のID体系とSkill責務は維持します。技法固有の機械証拠を曖昧なく保存するため、`test-condition-design/assets/output-template.md`の任意表は必要最小限拡張します。

特に次を固定します。

- Pairwise / N-wise / Base Choiceの因子=値組合せをdelimiter依存の自由文字列だけにしない
- interaction strength、Coverage mode、候補key、成立不能候補とその根拠を追跡できる
- n-switch / Round-trip等の状態Coverage証拠をvalidatorが安定して読める
- generator候補が採用または`カバレッジ候補の扱い`のどちらかへ閉じる

本変更はgeneratorの実行経路を追加するもので、次は変更しません。

- `SPEC-`、`DEC-`、`ASM-`、`RISK-`、`TR-`、`TCN-`、`CI`、`TC-`等の既存ID体系
- `test-analysis`、`test-condition-design`、`coverage-analysis`の責務境界
- 期待結果を現在有効な仕様根拠へ追跡する契約
- 評価runtimeとSkill runtimeの分離
- Skill-only portability

新しいSkillは追加しません。テスト技法は引き続き`test-condition-design`を正本とします。

## 8. 実行環境

初回runtime scriptはPython 3.11標準ライブラリを前提とします。

Agent Skills仕様では`scripts/`は任意の実行可能リソースであり、対応言語はAgent実装に依存します。このためscriptを追加する3 Skillでは、frontmatterの`compatibility`にPython 3.11実行環境が必要であることを明記します。

- Python 3.11を実行できる環境: 対応scriptを通常経路として使用する
- Pythonを実行できない環境: 既存Skill自体の利用可否とは分けて扱い、script由来の決定論的生成・Coverage保証を行ったとは表現しない
- 利用者が決定論的generatorの利用を必須としている場合、runtime unavailableをその計算範囲の制約として明示する

Skill単体コピー後もrepo root、network、外部binaryへ依存しません。
