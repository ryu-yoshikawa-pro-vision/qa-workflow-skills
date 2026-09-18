# テスト分析・テスト技法の決定論的自動化Plan

## 1. 評価方針

generatorを追加しても、LLMが正しいモデルを作れたことまではgenerator自身では保証できません。

評価を次へ分けます。

1. runtime script unit test
2. 既存の決定論的出力評価
3. 既存の意味評価
4. 必要なworkflow統合評価

同じアルゴリズムで生成と評価を行い、同じ不具合を見逃す構造にはしません。

## 2. runtime scriptのunit test

追加候補:

```text
tests/skills/runtime/
├── test_analysis/
│   ├── test_risk_matrix.py
│   └── test_technique_candidates.py
├── test_condition_design/
│   ├── test_equivalence_partitions.py
│   ├── test_bva.py
│   ├── test_decision_table.py
│   ├── test_combinatorial.py
│   ├── test_state_transition.py
│   ├── test_flow_paths.py
│   ├── test_cause_effect.py
│   ├── test_schema_cases.py
│   └── test_ui_pattern_candidates.py
└── coverage_analysis/
    └── test_traceability.py
```

実装時に既存テスト構成と比較し、より自然な配置がある場合は既存側へ合わせます。

### 必須回帰ケース

#### risk matrix

- repository-default方式の4×4全16組合せ
- 0 / 5 / 非数値の拒否
- 案件固有方式を`risk_matrix.py`で上書きしない
- validator側もrepository-defaultケースだけ4×4を要求する

#### BVA#### BVA

- integer lower / upper
- inclusive / exclusive
- 2-value / 3-value
- decimal + step
- date
- step不明時に`±1`を作らない
- lower / upperが近接する場合の重複排除

#### 同値分割

- enum partition
- 有限range
- 重複partition
- representative valueの所属
- valid / invalidの衝突

#### Decision Table

- 2条件booleanの全rule
- 多値条件
- forbidden constraint
- 成立不能ruleを除外だけせず扱い候補として返す
- unspecified outcome
- 同一完全assignmentへの矛盾outcome
- 重複rule
- 部分ruleを初回入力として受け付けない
- 自動don't care最適化を初回runtimeで行わない

#### Pairwise / N-wise

- 既存Pairwise fixture相当
- forbidden constraint
- 成立不能assignmentを根拠付きで返す
- Base Choice
- 100%成立可能pair Coverage
- 3-wiseの小規模fixture
- 同一入力で同一順序・同一結果
- assignment / tuple / output件数上限
- 上限超過時にCoverage基準を勝手に下げない
- 未知factor / 未知value
- factor / valueに`,`、`;`、`=`等を含んでも機械表現が壊れない

#### 状態遷移

- all states
- all transitions
- 0-switch = 1 transition
- 1-switch = 2連続transition
- 2-switch = 3連続transition
- Round-trip
- graph上のunreachable state
- terminal stateとoutgoing transitionなしの状態を区別
- guard未評価時に実行可能性まで断定しない
- 根拠付きで明示されたinvalid transition候補の検査
- 有効遷移の補集合から全invalid transitionを生成しない
- cycle
- resetなしで無理に1path化しない
- path / cycle件数上限

#### flow path

- bounded path
- node / edge Coverage
- main / alternative分類を入力なしに推測しない
- unreachable node
- bounded loop
- boundなしcycleの拒否
- acyclicでもpath数上限を超える場合の`limit_exceeded`

#### Cause-Effect#### Cause-Effect

- and / or / not
- Decision Tableへの変換
- effect矛盾

#### schema

- `json-schema-2020-12`
- `openapi-3.0-schema`
- `html-form-control`
- required
- enum
- min / max
- exclusive boundary
- minLength / maxLength
- nullable / null型のdialect差
- HTMLの`minlength`が`required`を暗黙に意味しない
- HTMLのinput typeごとの`step`
- HTML `pattern`をPython `re`で評価しない
- 未対応dialect / keywordを黙って解釈しない

#### UI pattern#### UI pattern

- 正規pattern
- alias
- 未知pattern
- pattern候補が製品固有expected resultとして返らない
- BVAへ渡せる属性抽出

#### traceability

- 正常な構造閉鎖
- Authority未閉鎖
- TR未閉鎖
- TCN / CI未閉鎖
- orphan
- unknown reference
- disposition済み項目
- 構造上の閉鎖率と意味上のCoverage判定を混同しない

## 3. 既存決定論的validatorの更新## 3. 既存決定論的validatorの更新

### `test-analysis`

現在の`RISK-D005`は常にリポジトリ標準4×4マトリクスを再計算しますが、`test-analysis/references/guidance.md`は案件固有方式を許可しています。

runtime側`risk_matrix.py`追加前にこの不整合を解消します。

- repository-default方式のfixtureでは、`RISK-D005`が4×4を独立再計算する
- project-specific方式のfixtureでは、標準4×4へ強制しない
- project-specific方式の正しさは、そのcaseで独立に定義できる期待値または意味評価で確認する
- runtime generatorとvalidatorで同じhelperを共有しない

script利用後も既存Assertionの意味を不要に弱めません。

### `test-condition-design`

既存Assertionを維持します。

特にPairwiseは現在の次の検査をgeneratorから独立して残します。

- `TCN-D014`: 因子 / 値集合
- `TCN-D015`: 成立可能pair 100% Coverage
- `TCN-D018`〜`TCN-D021`: 未知factor / value、constraint、欠落factor
- `TCN-D026`〜`TCN-D028`: Coverage Item参照、一意性、token構造
- `TCN-D016`: 状態遷移
- `TCN-D017`: BVA

追加する決定論的評価候補:

- generatorが識別した候補母集団の各候補が、Coverage Itemまたは`カバレッジ候補の扱い`のどちらかへ閉じること
- 同値partition Coverage
- Decision Tableの成立可能rule Coverage、成立不能ruleの扱い、unspecified / contradictory ruleの表現
- Base Choice / N-wise Coverage
- state / transition / n-switch / Round-trip Coverage
- schema由来boundary / enum候補
- UI pattern候補が仕様根拠なしにexpected resultへ昇格していないこと
- generator候補のsource referenceが成果物化の途中で失われていないこと

Assertion IDは既存`ASSERTIONS.md`を確認し、未使用番号を割り当てます。Plan時点で番号を先に固定しません。

### `coverage-analysis`

runtime`traceability.py`と既存validatorが独立に同じgap / orphanを検出できるfixtureを追加します。

既存`COV-D001`〜`COV-D012`の意味を不要に変更しません。

## 4. 意味評価

決定論的scriptを追加すると、LLMの品質評価で重要になる箇所が変わります。

意味評価では主に次を確認します。

- 仕様から抽出したboundaryが正しいか
- partitionの意味が妥当か
- Decision Tableのcondition / outcome / constraintが仕様を正しく表しているか
- state / event / guardを誤って作っていないか
- Pairwise因子・値が問題構造を適切に表しているか
- UI要素のpattern分類が妥当か
- 一般候補を製品固有expected resultへ昇格していないか
- scriptが出した組合せを、LLMが成果物化する過程で欠落・改変していないか

generatorが正しくても入力モデルが誤っていればテスト設計は誤るため、この意味評価は削減しません。

## 5. 発火評価

新Skillは追加しません。

既存Skillの責務も変えないため、発火評価280 queryを機械的に増やしません。

`description`を変更する必要が生じた場合だけ、対象Skillのtrain / validation datasetを現行比率に従って更新します。

「scriptを追加したから」という理由だけで発火queryを変更しません。

## 6. CI

新しいworkflowを増やす前に、既存`.github/workflows/deterministic-output-evals.yml`へ次を追加します。

- `skills/test-analysis/scripts`のcompile
- `skills/test-condition-design/scripts`のcompile
- `skills/coverage-analysis/scripts`のcompile
- `tests/skills/runtime`のunit test

例:

```bash
python -m compileall -q skills/test-analysis/scripts
python -m compileall -q skills/test-condition-design/scripts
python -m compileall -q skills/coverage-analysis/scripts
python -m unittest discover -s tests/skills/runtime -v
```

実際のtest package構成に合わせてdiscover pathは調整します。

`validate-skills.yml`はAgent Skills仕様・repository構造の検証責務を維持し、generatorの全unit testを重複実行させません。

## 7. Skill単体移植性の検証

既存READMEは、利用時に`skills/<skill-name>/`だけをコピーできることを契約にしています。

script追加後も次を満たします。

- `test-condition-design`等、対象Skillを単体コピーしてgeneratorが動く
- repo rootの`scripts/`へimportしない
- `tests/`へimportしない
- networkを必要としない
- 外部binaryを必須にしない
- Python 3.11標準ライブラリで動く
- runtime scriptを持つSkillの`compatibility`にPython 3.11要件が記載されている
- Pythonを実行できないAgent環境で、手計算結果をscript由来の決定論的結果として扱わない

テストではtemporary directoryへSkill packageをコピーし、代表scriptを実行する移植性回帰を追加します。

## 8. ドキュメント更新

### README

次を最小限追加します。

- テスト技法のうち機械的に生成できる部分はSkill内scriptを使用すること
- LLMとscriptの責務境界
- Skill packageに`scripts/`が実際に存在する例

READMEへ個々の技法アルゴリズムを複製しません。

### `coverage-techniques.md` / `output-template.md`

各技法について次を追記します。

- scriptを使える入力条件
- scriptへ渡す前にLLMが確定すべき情報
- scriptで自動化する範囲
- 自動化しない意味判断

具体的なPythonアルゴリズム説明はreferenceへ大量に書かず、scriptとtestを正本とします。

`output-template.md`は、既存ID体系を変えずに次を機械的に保持できる最小拡張を行います。

- Base Choice / Pairwise / N-wiseのCoverage modeとinteraction strength
- delimiterに依存しない因子=値の表現
- state sequence / Round-tripの対応Coverage Item
- generator候補key
- 成立不能候補と制約根拠

### `EVALS.md`

Skill runtime scriptと評価runtimeの違いを明記します。

特に「実行時自己検証はeval runtimeを呼ばない」という既存契約と、「Skill自身のruntime scriptを使う」ことが矛盾しないよう説明します。

## 9. 実装順序

### Step 0: 現状固定

- main最新commitを再確認
- 関連Skill、validator、fixture、CIを再検索
- Plan作成後にmainへ入った変更があれば差分を確認
- 新依存が追加されていないか確認

### Step 1: 共通境界

- JSON入力契約
- 値の型・decimal / date / local datetime表現
- 部分assignment形式の`forbidden_constraints`
- 安定した出力順序と候補key
- CLIエラー分類
- 計算量 / 出力量のhard limit
- source referenceの引き継ぎ
- Skill frontmatterのPython 3.11 `compatibility`
- Skill-only portability test
- `EVALS.md`のruntime / eval境界更新

この段階では汎用constraint ASTやplugin frameworkを作らず、最初のscript実装に必要な契約だけ固定します。

### Step 2: 小さく完全に決められる処理### Step 2: 小さく完全に決められる処理

- 案件固有リスク方式と`RISK-D005`の既存不整合を先に解消
- `risk_matrix.py`
- `bva.py`
- `equivalence_partitions.py`

repository-default方式では既存validatorと独立unit testで一致を確認し、project-specific方式を標準4×4で上書きしないことも回帰確認します。

### Step 3: rule / 組合せ

- 完全assignment契約の`decision_table.py`
- `combinatorial.py`のexhaustive / Base Choice / Pairwise / N-wise
- Classification Treeから組合せ入力への正規化
- `cause_effect.py`

ここでPairwise generatorと既存Pairwise validatorの独立性を重点確認します。

### Step 4: graph

- `state_transition.py`
- `flow_paths.py`

state / transition / n-switch / Round-trip Coverage、graph上の到達可能性、terminal state、guardを含む意味判断との境界を固定します。有効遷移の補集合から全invalid transitionは生成しません。

### Step 5: schema / UI候補

- dialect別の`schema_cases.py`
- HTML control typeごとのconstraint handling
- `ui-pattern-catalog.json`
- `ui-patterns.md`
- `ui_pattern_candidates.py`

HTML `pattern`をPython `re`で代替せず、外部標準を製品仕様へ昇格しない回帰ケースを必須にします。

### Step 6: 追跡性

- `coverage-analysis/scripts/traceability.py`
- 構造上の閉鎖率
- gap / orphan / unknown reference計算
- 既存`coverage-analysis` validatorとの独立照合

意味上のCoverage充足はscriptへ移しません。

### Step 7: Skill統合

- `test-analysis/SKILL.md`
- `test-condition-design/SKILL.md`
- `coverage-analysis/SKILL.md`
- Python 3.11 `compatibility`
- references / output templateの必要最小限更新
- generator候補をCoverage Itemまたは明示した扱いへ閉じる統合規則
- 重複候補とCI ID割当の安定順序

generatorを呼ぶ条件と、入力不足時にLLMが手計算・推測で埋めない条件を固定します。

### Step 8: 評価・CI・README

- runtime unit tests
- deterministic fixtures
- semantic fixtures
- portability regression
- CI
- README
- `ASSERTIONS.md` / `EVALS.md`

## 10. 実装を分ける場合

変更量が大きいため、1 PRへ無理に詰め込まない方が安全です。

実装時の分割候補:

1. runtime基盤 + risk / BVA / 同値分割
2. Decision Table + Pairwise / N-wise + Cause-Effect
3. State Transition + flow paths
4. schema + UI pattern
5. traceability + Skill統合 + 全体評価

ただしbranchやPR分割は実装開始時の差分量を見て決めます。Plan段階で複数branchを先に作りません。

## 11. リスク

### LLMが誤ったモデルを作る

generatorは誤った入力を忠実に展開するため、結果が大量に誤る可能性があります。

対策:

- source referenceを構造入力に含める
- 意味評価を維持する
- generator前の必須入力検査
- 未確定値をscriptが補完しない

### 計算量・出力量の増加

N-wise、Decision Table、state sequence、Round-trip、flow path、grammar generationで増加します。

対策:

- assignment / tuple / path / cycle / derivation / output件数のhard limit
- bounded traversal
- exhaustiveからPairwiseへ勝手に変更しない
- 上限超過を`limit_exceeded`として明示し、部分結果を100% Coverage扱いしない
- Coverage方式の判断を`test-condition-design`へ戻す

### generatorとvalidatorの同時誤り

同一helper共有で起きやすくなります。

対策:

- eval runtimeをimportしない
- fixtureの期待値をgeneratorから自動生成しない
- 小規模ケースは期待結果を手で固定する
- Pairwise等は数学的Coverageをvalidatorで独立再計算する

### UI一般論による仕様創作

対策:

- catalogは確認候補に限定
- source種別を明示
- 製品仕様がない候補からexpected resultを作らない
- semantic evalで回帰確認

### 依存関係増加

対策:

- 初期実装はPython標準ライブラリ
- PICT / ACTS / GraphWalker / Z3は具体的な不足が出るまで依存にしない

## 12. 完了条件

次をすべて満たしたとき完了とします。

- 実装対象として列挙した決定論的処理が、対応Skillのscriptまたは既存の明示的な機械処理へ割り当てられている
- LLMとscriptの責務境界が`SKILL.md` / referenceで説明されている
- BVA、同値分割、Decision Table、Base Choice / Pairwise / N-wise、状態遷移 / n-switch / Round-trip、flow、schema、UI pattern、追跡性にruntime unit testがある
- 現行Pairwise / BVA / 状態遷移 / risk / traceability validatorが独立評価として維持され、案件固有risk方式・新Coverage mode・候補閉鎖に必要な評価が追加されている
- 新規機械処理に必要な決定論的fixtureが追加されている
- 入力モデルの意味品質を確認するsemantic fixtureがある
- Skill-only portability testがPASSする
- runtime scriptを持つSkillの`compatibility`にPython 3.11要件が明示されている
- Python 3.11でcompile / unit test / deterministic eval / semantic dataset validationがPASSする
- `skills-ref validate`が全SkillでPASSする
- 外部依存を追加していない、または追加した場合は必要性・license・platform影響が別途確認済み
- README、`EVALS.md`、`ASSERTIONS.md`、関連referenceが実装と一致する
- 一般UI候補や外部標準から製品固有expected resultを創作する回帰がない
- generatorが除外した成立不能候補を無言で捨てず、採用または明示した扱いへ閉じている
- traceability scriptの構造上の閉鎖率を意味上のCoverage充足として扱っていない
- 同じ入力から候補順序と機械表現が安定している
- Error Guessing、Exploratory Testing、リスク発見等の意味判断を無理に決定論的generatorへ移していない

## 13. 実装時に避けること

- eval用helperをruntimeからimportする
- generator outputをそのままexpected fixtureへ使う
- 任意Python式を`eval()`で制約として実行する
- 汎用plugin frameworkを先に作る
- 全テスト技法を別Skillへ分割する
- PICT / GraphWalker / Z3 adapterを将来用に先行実装する
- 未定義挙動をUI標準から補完する
- N-wiseの最小ケース数を保証すると宣言する
- 組合せ上限超過時に無断でCoverage基準を下げる
- 有効遷移集合の補集合から全invalid transitionを機械生成する
- HTML `pattern`をPython `re`で同等とみなす
- project-specific risk方式を標準4×4で上書きする
- 構造上のedge存在だけで意味上のCoverage充足と判定する
- エラー推測・探索的テストを固定チェックリストだけで置き換える
