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

`risk_matrix.py`は確定済みの影響度・発生可能性だけを受け取り、現在の4×4マトリクスからレベルを返します。

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

### 3.2 CLI契約

scriptは原則として次の形に揃えます。

```bash
python skills/test-condition-design/scripts/bva.py --input path/to/input.json
```

- 成功時: JSONをstdoutへ出力
- 入力契約違反: 非0終了し、原因をstderrへ出力
- 通常実行でリポジトリファイルを変更しない
- networkへアクセスしない
- 乱数を使う場合はseedを入力で明示し、同一seedで再現できること
- Pythonの`eval()` / `exec()`で制約式を実行しない

必要性が出るまで`--output`や複数出力formatは追加しません。

### 3.3 仕様根拠をscriptで作らない

generator入力に現在有効な仕様根拠IDを渡せる場合は、出力へそのまま引き継ぎます。

ただしscriptは次を行いません。

- 一般慣習から`SPEC-xxx`を作る
- UI pattern referenceを製品固有の期待結果へ変換する
- リスクから製品挙動を推測する
- 実装コードの現状を仕様として昇格する

期待結果根拠が不足する生成候補は、`test-condition-design`が完成済みCoverage Itemへ無条件に採用しません。

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

初期実装では任意のPython式や独自DSLを作りません。

制約はJSON ASTまたは部分assignmentとして表現します。

単純な禁止条件:

```json
{
  "forbidden": {
    "role": "member",
    "visibility": "private"
  }
}
```

複合条件が必要な場合:

```json
{
  "op": "and",
  "args": [
    {"op": "eq", "factor": "role", "value": "member"},
    {"op": "eq", "factor": "visibility", "value": "private"}
  ]
}
```

初期許可演算子は実際に必要な最小集合に限定します。

候補:

- `and`
- `or`
- `not`
- `eq`
- `neq`
- `in`
- 数値domainで必要なら`lt`、`lte`、`gt`、`gte`

文字列式を独自parserで解釈する実装は行いません。

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
- 到達不能、重複、矛盾、欠落を検出する
- 入力契約不足を明示的に失敗させる

## 6. Skill instructionの変更

### `test-analysis/SKILL.md`

次を追加します。

- 影響度・発生可能性が確定している場合は`scripts/risk_matrix.py`でレベルを算出する
- 問題構造が正規化できる場合は`scripts/technique_candidates.py`を補助的に使う
- script結果を根拠なく上書きしない
- scriptが必要入力不足で失敗した場合はLLMで数値や条件を捏造せず既存停止条件へ従う

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

既存Markdown成果物の主要な表形式、ID体系、Skill責務は維持します。

本変更はgeneratorの実行経路を追加するもので、次は変更しません。

- `SPEC-`、`DEC-`、`ASM-`、`RISK-`、`TR-`、`TCN-`、`CI`、`TC-`等の既存ID体系
- `test-analysis`、`test-condition-design`、`coverage-analysis`の責務境界
- 期待結果を現在有効な仕様根拠へ追跡する契約
- 評価runtimeとSkill runtimeの分離
- Skill-only portability

新しいSkillは追加しません。テスト技法は引き続き`test-condition-design`を正本とします。
