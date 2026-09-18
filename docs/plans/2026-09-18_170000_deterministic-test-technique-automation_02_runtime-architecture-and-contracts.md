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

`risk_matrix.py`は、案件固有のリスク評価方式が採用されていない場合だけ、確定済みの影響度・発生可能性からリポジトリ標準4×4マトリクスのレベルを返します。案件固有方式を解釈・上書きしません。

`technique_candidates.py`は自然言語を読まず、次のsignalをすべて明示したJSONを入力にします。

- `ordered_domain`
- `explicit_boundaries`
- `equivalence_classes`
- `multiple_discrete_conditions`
- `stateful`
- `multiple_factors`
- `explicit_flow`

各signalは`true / false / null`のいずれかとし、key欠落は入力エラーにします。`null`は未確認を意味し、`false`と同一視しません。出力は現行の正規技法名だけとし、最終採用は`test-analysis`が判断します。

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

初回から汎用framework、plugin機構、generator registryは追加しません。複数scriptで同じ有限domain判定が重複した場合だけ、Skill内の小さいhelperへ切り出します。

grammar-based testingは初回実装から外すため、grammar用scriptは追加しません。

### `coverage-analysis`

```text
skills/coverage-analysis/
└── scripts/
    └── traceability.py
```

`traceability.py`は初回は`対象 / 実行範囲 = テスト設計`だけを扱います。Authority / Risk → TR → TCN → CI / TC → TCのmissing edge、orphan、unknown referenceを算出し、E2E実装参照や実行結果の意味判断は既存`coverage-analysis`に残します。

### 正規技法名の扱い

runtime scriptを追加しても、`test-analysis`の正規技法名は現在のvalidatorが許可する集合を維持します。

- Each Choiceは`同値分割`のCoverage基準
- Base Choice / Pairwise / N-wise / Classification Tree由来の組合せは`Pairwise / 組合せ`の内部Coverage modeまたは入力形式
- transition-pair / n-switch / Round-tripは`状態遷移`の内部Coverage mode
- Cause-Effect GraphはDecision Table入力への変換
- schema / HTML / UI属性は既存技法の候補生成元

## 3. 共通の入出力方針

### 3.1 JSONを機械入力とする

scriptへMarkdown表を直接渡しません。LLMが技法ごとのJSONへ正規化し、scriptはJSONを読み、JSONを返します。Markdown化はSkill側の責務です。

各generator invocationは、少なくとも次を持ちます。

- `model_key`: 同一成果物内で技法インスタンスを区別する局所キー
- 技法固有入力
- `authority_refs`: 現在有効な製品仕様根拠。`SPEC-` / `DEC-` / `ASM-`等
- `reference_refs`: HTML / APG等の外部資料、DOM・実装事実等。製品固有expected resultのAuthorityには使わない

`model_key`は既存QA IDではなく、成果物内で同じ技法を複数回使用したときの機械的な関連付けにだけ使います。

### 3.2 値の表現

- `integer`: JSON integer
- `boolean`: JSON boolean
- enum / 識別子: JSON string
- `decimal`: `type: "decimal"`を明示し、値は10進文字列として渡して`decimal.Decimal`で解釈する
- `date`: `YYYY-MM-DD`
- 初回対応する日時: timezoneを持たないlocal datetimeだけとし、ISO 8601形式と最小単位を明示する
- Pairwise等の同一factor内では値の型を混在させない

runtimeのtyped valueとMarkdown成果物の文字列表現を混同しません。技法固有の機械証拠では型を復元できる表現を使用します。

### 3.3 CLI契約

Skill instructionからはSkill rootを基準に`scripts/<name>.py`を参照します。repo root固定pathを契約にしません。

```bash
python scripts/bva.py --input path/to/input.json
```

- 成功時: JSONをstdoutへ出力
- stdoutのmachine-readable JSONはWindowsのlegacy code pageに依存しないよう`ensure_ascii=True`相当で出力する
- 失敗時: 非0終了し、`invalid_input`、`unsupported`、`limit_exceeded`、`internal_error`を識別できる診断をstderrへ出力
- 診断へ入力JSON全体や実データ全文をdumpしない
- 通常実行でリポジトリファイルを変更しない
- networkへアクセスしない
- Pythonの`eval()` / `exec()`で制約式を実行しない

### 3.4 根拠の扱い

`authority_refs`と`reference_refs`を分けます。

- `authority_refs`: 製品固有expected resultを確定できる現在有効な仕様根拠
- `reference_refs`: 外部標準、一般UI資料、DOM・実装事実等の補助情報

scriptはこれらを作成・置換せず、入力から生成候補へ引き継ぎます。UI catalogやHTML / APGのURLだけをCoverage Itemの`期待挙動の根拠`へ昇格しません。

### 3.5 決定論的な順序と識別

- 入力順を意味として使う場合は入力順を維持する
- 集合計算結果は技法ごとの安定sortで固定する
- `candidate_key`は`model_key`内で一意な局所キーとし、別model間の重複判定にはそのまま使わない
- `candidate_key`へ`authority_refs`を埋め込まず、同じCoverage対象に複数Authorityがある場合はrefsを統合できるようにする
- generatorがCoverage対象と生成行を別に持つ技法では両者を1対1と仮定しない

特にPairwise / N-wiseではt-tupleがCoverage母集団であり、1つの生成組合せが複数tupleをCoverageできます。

## 4. 正規化入力

### 4.1 有限domain

Decision Table、組合せ、Classification Tree等ではfactor / conditionのkeyを一意にし、値集合を空にしません。

```json
{
  "model_key": "pairwise-01",
  "factors": [
    {"key": "role", "values": ["admin", "member"]},
    {"key": "visibility", "values": ["public", "private"]}
  ],
  "forbidden_constraints": []
}
```

入力検証では次を必須にします。

- factor / condition keyが一意
- 各値集合が1件以上で重複なし
- constraintが空assignmentでない
- constraintが参照するfactor / valueが実在する
- Pairwiseは2因子以上
- N-wiseは`2 <= strength <= factor数`

### 4.2 禁止制約

初回実装では、部分assignment形式の禁止制約だけを共通契約にします。

```json
{
  "forbidden_constraints": [
    {
      "constraint_key": "FC-01",
      "assignment": {"role": "member", "visibility": "private"},
      "authority_refs": ["SPEC-001"]
    }
  ]
}
```

`constraint_key`は局所キーで、既存QA ID体系へ追加しません。constraintの`assignment`が指定したすべてのfactor=valueを満たすfull assignmentは成立不能です。

全assignmentが禁止される場合は正常な100% Coverageとはせず、UNSATとして明示的に返します。

初回実装では汎用constraint AST、算術constraint、required constraint、独自文字列DSLを追加しません。必要性が確認された場合にgeneratorと独立validatorを同時に拡張します。

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

- 案件固有方式がなく`repository-default`と確定した場合だけ`scripts/risk_matrix.py`を使う
- `technique_candidates.py`は補助候補に使い、最終技法選択はLLMが行う
- scriptで対応可能な入力はscriptを優先する
- script対象外・`unsupported`・Python unavailableの場合は既存LLM経路を利用できるが、その結果を「scriptで決定論的に生成・検証した」と表現しない

### `test-condition-design/SKILL.md`

- 対応技法にscriptがあり入力契約を満たす場合はscriptを使用する
- Coverage母集団は技法ごとの`coverage-techniques.md`契約を正本とし、共通candidate規則へ無理に変換しない
- `invalid_input`: 構造化入力を修正できるか確認し、仕様不足なら既存停止条件へ従う
- `unsupported`: 対応範囲外として既存LLM経路で設計可能か判断する
- `limit_exceeded`: Coverage基準を無断で下げず、方式・scopeを再判断する
- `internal_error`: script異常として扱い、結果を完成済みCoverageとして使わない
- Python unavailable時も従来の意味判断は可能だが、決定論的generator利用済みとは扱わない
- 仕様根拠のある同一partition内の値へ代表値を変更する場合は、所属をscriptで再検証する

### `coverage-analysis/SKILL.md`

- 初回の`traceability.py`は`対象 / 実行範囲 = テスト設計`だけで使用する
- scriptはmissing edge / orphan / unknown reference等の構造事実を返す
- 技法別Coverage値は`test-condition-design`成果物を利用し、本Skillで再計算しない
- 意味上のCoverage充足、Disposition妥当性、E2E実装・実行結果の分析は従来どおりLLMに残す

## 7. 既存成果物との互換性

既存のQA ID prefixとSkill責務は維持します。ただし、自動生成で1 TCNあたり100件以上のCoverage Itemが発生し得るため、CI番号だけ後方互換で拡張します。

- 現行: `TCN-001-CI01`
- 変更後: `TCN-001-CI01`、`TCN-001-CI100`等を許可する`CI\d{2,}`

`ID_PATTERNS["CI"]`、`ALL_ID_RE`、`test-condition-design`、`test-case-design`、`coverage-analysis`等のCI ID consumerを同時に更新します。既存2桁IDはそのまま有効です。

`test-analysis/assets/output-template.md`には分析単位の`リスク評価方式`を追加します。

- `repository-default`: 影響度・発生可能性は1〜4で、`RISK-D004` / `RISK-D005`が標準方式を検証する
- `project-specific:<name>`: 標準1〜4と4×4を強制せず、fixtureで明示できる契約または意味評価で確認する

`test-condition-design/assets/output-template.md`は、同じ技法を複数回使っても独立validatorが区別できるよう、技法固有の機械証拠へ`モデルキー`または`観点ID`を持たせます。

最低限、次を保持できる形式へ更新します。

- 同値分割: モデルキー、partition set、partition key、valid / invalid、代表値、対応CI / Disposition
- BVA: モデルキー、境界key、lower / upper、inclusive、位置、typed value、対応CI
- Decision Table: モデルキー、rule key、完全condition assignment、action vector、対応CI / Disposition
- Pairwise / N-wise / Base Choice: モデルキー、Coverage mode、strength、因子・typed value、生成組合せ、Coverage対象tupleとの対応
- 状態遷移: モデルキー、transition key、from / event / guard / to、sequence / Round-trip、対応CI
- flow: モデルキー、edge key、from / to / guard / label、path

delimiter依存の`Factor=Value; ...`だけを機械契約にしません。

技法ごとのCoverage母集団と生成CIの関係は1対1とは限りません。Pairwise / N-wiseではt-tuple、BVAでは境界位置、状態遷移ではtransition / sequenceをCoverage対象として独立に保持します。

新しいSkillは追加しません。

## 8. 実行環境

初回runtime scriptはPython 3.11標準ライブラリを前提とします。

Agent Skills仕様では`scripts/`は任意の実行可能リソースであり、対応言語はAgent実装に依存します。このためscriptを追加する3 Skillでは、frontmatterの`compatibility`を「Skill全体がPython必須」と読める表現にせず、`Deterministic generator scripts require Python 3.11`相当の要件として記載します。

- Python 3.11を実行できる環境: 対応scriptを通常経路として使用する
- Pythonを実行できない環境: 既存Skillの意味判断は利用できるが、script由来の決定論的生成・Coverage保証を行ったとは表現しない
- 利用者が決定論的generatorの使用自体を必須としている場合: runtime unavailableをその範囲の制約として明示する

Skill単体コピー後もrepo root、network、外部binaryへ依存しません。

