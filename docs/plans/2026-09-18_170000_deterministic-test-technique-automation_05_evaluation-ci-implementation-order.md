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

Python 3.11の`unittest discover`で確実に検出できるよう、初回は`tests/skills/runtime/`直下へflatに配置します。

```text
tests/skills/runtime/
├── test_test_analysis_risk_matrix.py
├── test_test_analysis_technique_candidates.py
├── test_test_analysis_change_impact.py
├── test_test_requirement_structure.py
├── test_test_condition_equivalence_partitions.py
├── test_test_condition_bva.py
├── test_test_condition_decision_table.py
├── test_test_condition_combinatorial.py
├── test_test_condition_state_transition.py
├── test_test_condition_flow_paths.py
├── test_test_condition_cause_effect.py
├── test_test_condition_schema_cases.py
├── test_test_condition_ui_pattern_candidates.py
├── test_test_case_structure.py
└── test_coverage_analysis_traceability.py
```

CIでは実行test数が0件でないことも確認します。

### 必須回帰ケース

#### risk matrix

- `repository-default`の4×4全16組合せ
- 0 / 5 / 非数値の拒否
- `project-specific:*`を標準4×4で上書きしない

#### technique candidates

- 全signal keyが必須
- `true / false / null`の区別
- key欠落 / 不正値の拒否
- `null`を`false`扱いして候補を落とさない
- `candidates / undetermined_signals / complete`の出力
- 未確認signalが残る場合にcomplete扱いしない

#### change impact

- changed nodeから明示edgeだけを辿る
- Authority / TR / TCN / CI / TCの重複除去
- unknown node / dangling edge
- 名称類似だけではimpactを追加しない
- 同一入力で順序が安定する

#### test requirement structure

- Authority / Risk → TR closure
- linked + disposed重複
- unknown upstream ID
- 関連Product Riskからの最低優先度
- TR本文をscriptが変更しない

#### 同値分割 / Each Choice

- 複数partition set
- 同じset内のenum / range重複
- 異なるset間の値重複を誤検出しない
- inclusive / exclusive端点
- representative value所属
- valid / invalid衝突
- 成果物上のpartition閉鎖とEach Choice Coverageを別に判定
- `対象外` / `残存リスク`等のDispositionをCoverage済みと数えない
- Authority付き成立不能だけをCoverage母集団から除外
- unresolved / unsupportedが残るmodelで100%としない

#### BVA

- lower / upper
- `minimum_inclusive` / `maximum_inclusive`
- 2-value / 3-value
- decimal + step
- date
- step不明時に`±1`を作らない
- lower / upperが同じ具体値を生成しても境界位置を区別
- model / boundary keyとtyped valueの対応

#### Decision Table

- 任意数condition
- 複数actionのaction vector
- action key完全一致、未知key / 欠落key / 非boolean拒否
- all actions falseのknown ruleを`unspecified`にしない
- forbidden constraint
- known ruleとconstraintの矛盾
- unspecified ruleをCoverage済みにせず未解決として返す
- action矛盾ruleを自動採用しない
- 同一assignment + 同一action vectorの重複
- 同一assignment + 異なるaction vectorの矛盾
- 部分rule / don't-careを初回入力として拒否
- 自動最適化を行わない
- 同一成果物に2つのDecision Table model

#### Pairwise / N-wise

- factor / valueの一意性と空集合拒否
- 空constraint拒否
- unknown factor / value in constraint
- Pairwiseは2因子以上
- N-wise strength範囲
- 全assignment UNSATを100% Coverage扱いしない
- constraintなしBase Choice
- constraint付きBase Choiceは`unsupported`
- 成立可能2-wise / 3-wise tupleの100% Coverage
- feasibilityの`SAT / UNSAT / limit_exceeded`区別
- 探索上限到達をUNSAT扱いしない
- 成立不能t-tupleのAuthority根拠
- 全Cartesian productを事前materializeしない経路
- deterministic ordering / tie-break
- feasibility search / tuple / row / output hard limit
- `limit_exceeded`時にCoverage基準を下げない
- typed valueと`,` / `;` / `=`等を含む文字列値
- 同一成果物に2つの独立Pairwise model

#### 状態遷移

- `transition_key`一意性
- 同じfrom / event / toでguardだけ異なる遷移を区別
- all states / all transitions
- 0-switch / 1-switch / 2-switch
- guard feasibility不明時は構造候補と正式Coverageを区別
- Round-trip
- unreachable state
- terminal state
- 根拠付きinvalid transition候補
- 全invalid transition補集合を生成しない
- resetなしで巨大pathへ無理に連結しない
- sequence / cycle hard limit
- 同一成果物に2つの状態model

#### flow path

- `edge_key`一意性
- 同じfrom / toでguard / labelが異なるedgeを区別
- 複数`terminal_nodes`
- node / edge Coverage
- edge証拠とpath証拠の分離
- 1 edgeが複数pathへ所属可能
- main / alternativeを入力なしに推測しない
- simple loopの0回 / 1回 / 指定代表回数 / 指定最大回数
- fork / join / 並行flowを`unsupported`にする
- loop boundのedge通過定義
- boundなしcycle拒否
- path hard limit

#### Cause-Effect

- `ref` / `not` / `and` / `or`
- unknown cause参照
- 重複key
- 空`and / or`
- 複数effectを完全なaction vectorへ変換
- cause数 / assignment数hard limit
- limit超過時に部分列挙を完全table扱いしない
- Decision Tableへの変換

#### schema / HTML

runtime unit testでは正規化済みfield constraintだけを入力にします。

- 正規化済みminimum / maximum / inclusive / allows_null / length等から正しいCoverage targetを生成
- schema_kindごとのlength semantics
- 未対応正規化constraintを`unsupported`にする
- HTML required / min / max / minlength / maxlength / step
- `constraint_validation_applicable=false`
- disabled / readonly
- HTML `pattern`をPython `re`で評価しない
- length semanticsをschema_kind間で混同しない

raw JSON Schema 2020-12 / OpenAPI 3.0からこの正規化形式へ変換する際の`exclusiveMinimum`、`exclusiveMaximum`、`nullable`、annotation / applicator差はsemantic fixtureで確認します。runtime unit testへraw dialect parser責務を持ち込みません。

#### test case structure

- TCN / CI → TC closure
- linked + disposed重複
- unknown upstream ID
- Coverage Itemからの最高優先度
- 番号付き期待結果とAuthority対応
- 具体的な期待結果をscriptが補完しない

#### UI pattern

- 正規pattern名一意
- alias一意
- aliasと別pattern正規名の衝突禁止
- 未知patternでもcatalogを実行中に変更しない
- 一般候補を製品Authorityへ昇格しない
- 低リスク領域へ一般edge caseを無条件全展開しない

#### traceability

- `対象 / 実行範囲 = テスト設計`
- 正常な構造閉鎖
- Authority / Risk / TR / TCN / CIのmissing edge
- orphan
- unknown reference
- disposition済みnode
- E2E部分分析をscript対象と誤認しない

## 3. 既存決定論的validatorの更新

### 共通ID

`ID_PATTERNS["CI"]`と`ALL_ID_RE`を`CI\d{2,}`へ後方互換で拡張し、`test-condition-design`、`test-case-design`、`coverage-analysis`等のCI参照検査を同時に更新します。

`ALL_ID_RE`は`TCN-\d{3}-CI\d{2,}`だけをCIとして認識し、`SPEC-001-CI01`、`TR-001-CI01`等を誤認しないfixtureを追加します。

### `test-analysis`

`リスク評価方式`をfixture / 成果物から判定できるようにします。

- `repository-default`: `RISK-D004`で1〜4、`RISK-D005`で標準4×4を独立再計算
- `project-specific:*`: `RISK-D004` / `RISK-D005`で標準方式を強制しない
- 案件固有方式の決定論的契約をfixtureへ持てる場合だけその期待値を検査し、それ以外は意味評価へ残す

runtime generatorとvalidatorで同じhelperを共有しません。

### `test-requirement-design`

既存`TR-D001`〜`TR-D015`を正本として、runtimeの`requirement_structure.py`と同じfixtureを独立に照合します。runtimeとvalidatorでhelper実装を共有しません。

### `test-condition-design`

既存Assertionを不要に弱めず、自由文検索や「最初の1表だけ」を前提とする箇所を技法固有の機械証拠へ置き換えます。

- 同値分割: model / partition set / partition key / CIまたはDisposition
- BVA: model / boundary key / position / typed value / CI。現行`TCN-D017`の全CI自由文検索だけには依存しない
- Decision Table: model / rule key / complete assignment / action vector / CIまたはDisposition
- Pairwise / N-wise: modelごとのfactor / tuple母集団 / generated rows / tuple Coverage
- 状態遷移: `transition_key`、guardを含むidentity、modelごとのsequence Coverage
- flow: `edge_key`とmodelごとのpath証拠

同一成果物に同種技法modelが複数存在するfixtureを追加し、2つ目以降を無視するfalse-passを防ぎます。

Coverage母集団の閉鎖は技法ごとに検査します。全generatorへ「candidate 1件 = CI 1件」の共通Assertionは追加しません。

`期待挙動の根拠`についてfixtureがknown Authorityを持つ場合、Coverage Itemに少なくとも1件の有効な`SPEC-` / `DEC-` / `ASM-`参照があることを検査します。外部URL等の`reference_refs`だけでは満たした扱いにしません。

### `test-case-design`

既存`TC-D001`〜`TC-D014`の構造契約を維持し、`case_structure.py`と同じfixtureでclosure、優先度、Authority mappingを独立照合します。期待結果本文の妥当性はsemantic evalへ残します。

### `coverage-analysis`

`traceability.py`と既存validatorが、`対象 / 実行範囲 = テスト設計`の同じfixtureに対して独立にmissing edge / orphan / unknown referenceを検出できることを確認します。

数値の構造閉鎖率は新設しません。既存`COV-D001`〜`COV-D012`の意味を不要に変更しません。

## 4. 意味評価

generatorが正しくても入力モデルが誤っていれば結果も誤るため、意味評価は維持します。

主な確認対象:

- partition setと各partitionの意味
- boundary / step / inclusivity
- Decision Tableのcondition / action / constraint
- Cause-Effectのcause / effect式
- state / event / guardと実行可能性
- Pairwise因子・値・strength
- schema / HTML constraintの正規化
- UI pattern分類
- `authority_refs`と`reference_refs`の区別
- script出力を成果物化する過程でCoverage対象や根拠が欠落・改変されていないこと
- 正規化済みモデルが元のAuthority / Risk / TR / TCNの意味を必要十分に表していること
- generatorの100% Coverageを対象仕様全体100%と誤解していないこと
- raw JSON Schema / OpenAPIから正規化constraintへのdialect解釈が正しいこと

semantic fixtureのreferenceをruntime generator出力から自動生成しません。

## 5. 発火評価

新Skillは追加しません。

既存Skillの責務も変えないため、発火評価280 queryを機械的に増やしません。

`description`を変更する必要が生じた場合だけ、対象Skillのtrain / validation datasetを現行比率に従って更新します。

「scriptを追加したから」という理由だけで発火queryを変更しません。

## 6. CI

新しいworkflowを増やす前に、既存`.github/workflows/deterministic-output-evals.yml`へ追加します。

```bash
python -m compileall -q skills/test-analysis/scripts
python -m compileall -q skills/test-requirement-design/scripts
python -m compileall -q skills/test-condition-design/scripts
python -m compileall -q skills/test-case-design/scripts
python -m compileall -q skills/coverage-analysis/scripts
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v
```

`tests/skills/runtime/`はflat構成とし、Python 3.11のdiscoverで子directory package要件に依存しません。

テスト実行結果から実行test数が0件でないことを確認します。

`validate-skills.yml`はAgent Skills仕様・repository構造の検証責務を維持し、generator unit testを重複実行させません。

## 7. Skill単体移植性の検証

既存READMEの「利用時は`skills/<skill-name>/`だけをコピーできる」契約を維持します。

次の5 Skillをそれぞれ別のtemporary directoryへ単体コピーし、最低1つの代表scriptをCLI実行します。

- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`

検証項目:

- repo rootの`scripts/` / `tests/`へimportしない
- network不要
- 外部binary不要
- Python 3.11標準ライブラリで実行可能
- Skill rootから`scripts/<name>.py`を解決できる
- stdout JSONをlegacy code pageへ依存せず読める
- `compatibility`に「deterministic generator scripts require Python 3.11」相当の要件が明示される
- Python unavailable時にSkill全体を誤って利用不能扱いせず、決定論的generator利用済みとも表現しない

## 8. ドキュメント更新

### README

- 機械生成できる部分はSkill内scriptを使用する
- LLMとscriptの責務境界
- Python 3.11要件はdeterministic generator scriptの要件であること
- Skill package内`scripts/`の配置例

### `test-analysis`

- `assets/output-template.md`へ`リスク評価方式`を追加
- repository-defaultとproject-specificのvalidator分岐を成果物から判断可能にする
- `SKILL.md`へ構造的な変更影響候補抽出と意味上の影響判断の境界を追加

### `test-requirement-design`

- `SKILL.md`へ`requirement_structure.py`の利用条件と責務境界を追加
- 既存output templateのTR / Disposition形式は維持する

### `test-condition-design/references/coverage-techniques.md`

- Each Choice
- Base Choice / N-wiseを`Pairwise / 組合せ`内のCoverage modeとして説明
- n-switch / Round-tripを`状態遷移`内のCoverage modeとして説明
- scriptを使える入力条件と意味判断の境界

### `test-condition-design/assets/output-template.md`

同じ技法modelを複数保持できる単一の機械表を技法ごとに用意し、各表へ`モデルキー` / `観点ID`を含めます。

- 同値partition表
- BVA境界証拠表
- 任意condition数・複数actionを表現できるDecision Table表
- typed valueとCoverage tupleを曖昧なく保存できる組合せ表
- `transition_key`を含む状態遷移表 / sequence表
- `edge_key`を含むflow証拠表

既存QA ID prefixは維持し、CI番号だけ`CI\d{2,}`へ拡張します。

### `test-case-design`

- `SKILL.md`へ`case_structure.py`の利用条件と責務境界を追加
- 既存output templateのTC / Disposition形式は維持する

### `coverage-analysis`

`traceability.py`の初回対象がテスト設計の構造追跡だけであることを`SKILL.md` / referenceへ明記します。

### `EVALS.md` / `ASSERTIONS.md`

- Skill runtime scriptと評価runtimeを分離する
- 新しい技法固有機械証拠と独立Assertionを記録する
- runtime generator outputをexpected fixtureの生成元にしない

## 9. 実装順序

### Step 0: 現状固定

- main最新commit、関連Skill、validator、fixture、CIを再確認
- branch作成後にmainへ入った変更との差分を確認

### Step 1: 共通契約

- 決定論性の保証単位を「同じ正規化済みモデル」に固定
- 正規化済みモデルを成果物から再構築できる機械表現
- `model_key`一意性、typed value、`authority_refs` / `reference_refs`継承
- `forbidden_constraints`の`constraint_key / assignment / authority_refs`
- factor / value / strength / `SAT / UNSAT / limit_exceeded`入力検証
- 安定sortと技法固有key
- CLI error分類とstdout encoding
- CI ID `\d{2,}`とTCN限定regex
- Skill-only portability

### Step 2: test-analysis / test-requirement-design

- `risk_matrix.py`
- `technique_candidates.py`の`undetermined_signals`
- `change_impact.py`
- `RISK-D004` / `RISK-D005`のscheme分岐
- `requirement_structure.py`
- Authority / Risk → TR closureと優先度
- deterministic / semantic fixture

### Step 3: 同値分割 / BVA

- partition set / Each Choice
- 成果物上の閉鎖とCoverage達成の分離
- `equivalence_partitions.py`
- structured BVA evidence / `bva.py`

成果物形式と独立validatorを同じStepで更新し、generatorだけ先に入れません。

### Step 4: Decision Table / Cause-Effect

- action vector形式のDecision Table成果物
- action key完全性
- `unspecified` / 矛盾の質問ルーティング
- `decision_table.py`
- constraintとknown ruleの矛盾
- boolean subsetの`cause_effect.py`
- assignment hard limit
- Decision Table validator / semantic fixture

### Step 5: 組合せ

- constraintなしBase Choice
- Pairwise / N-wiseのtuple feasibility
- `SAT / UNSAT / limit_exceeded`
- full Cartesian productをmaterializeしない生成
- model別成果物 / validator

### Step 6: 状態 / flow

- `transition_key` / `edge_key`
- guard feasibility境界
- n-switch / Round-trip
- `terminal_nodes` / loop bound
- simple loop Coverage
- fork / join / 並行flowの`unsupported`
- edge証拠とpath証拠の分離
- state / flow validator

### Step 7: schema / UI

- 正規化済みfield constraint形式
- raw dialect解釈はsemantic eval、runtimeは正規化後だけを扱う
- HTML constraint validation対象判定
- UI catalog alias / reference / low-risk深度

### Step 8: test-case-design / traceability

- `case_structure.py`
- TCN / CI → TC closure、優先度、Authority mapping
- `対象 / 実行範囲 = テスト設計`に限定した`traceability.py`
- missing edge / orphan / unknown reference
- 既存validatorとの独立照合

### Step 9: 全体統合

- 5 Skillのinstruction / compatibility
- normalized model再構築と再実行fixture
- deterministic / semantic fixtures
- CI / portability
- README / `EVALS.md` / `ASSERTIONS.md`

grammar-based testing、CRUD Testing、Domain Testing、Metamorphic Testing等の後続候補はこの実装順序に含めません。

## 10. 実装を分ける場合

複数PRへ分ける場合、runtime scriptだけを先にmergeして未使用コードを残す横割りにはしません。

各PRは可能な限り次を一緒に含む縦の単位にします。

- runtime script
- Skill instruction / reference
- output template
- deterministic validator / fixture
- unit test
- 必要なsemantic fixture

例:

1. 共通契約 + risk / 同値分割 / BVA
2. Decision Table + Cause-Effect
3. Base Choice / Pairwise / N-wise
4. 状態遷移 + flow
5. schema / UI + traceability + 全体統合

実際のPR分割は実装時の差分量で決め、Plan段階でbranchを増やしません。

## 11. リスク

### LLMが誤ったモデルを作る

- `authority_refs`を正規化入力へ保持する
- semantic evalを維持する
- 未確定値をscriptが補完しない

### 組合せ・pathの計算量

- tuple / feasibility search / row / path / cycle / outputのhard limit
- full Cartesian productをPairwise / N-wiseの前提にしない
- `limit_exceeded`時にCoverage基準を勝手に下げない
- 部分結果を100% Coverageと表現しない

### generatorとvalidatorの同時誤り

- helper実装を共有しない
- expected fixtureをgeneratorから自動生成しない
- small fixtureの期待値を人手で固定
- false-pass regressionを追加

### 成果物形式の曖昧さ

- model keyで同種技法を区別し、衝突modelを拒否
- 正規化済み入力を成果物から再構築可能にする
- typed valueと自由文を分離
- Coverage母集団と生成CIを1対1と仮定しない
- model内Coverageと対象仕様全体のCoverageを混同しない

### UI / 外部標準からの仕様創作

- `authority_refs`と`reference_refs`を分離
- catalogは候補に限定
- semantic evalで回帰確認

### runtime非対応環境

- Python unavailableとSkill自体の利用可否を分離
- deterministic generator未実行を明示

### 依存関係増加

初回はPython標準ライブラリを使用します。PICT / ACTS / GraphWalker / Z3は、標準ライブラリ実装で具体的な性能・正確性問題を再現した場合だけ再評価します。

## 12. 完了条件

- 実装対象の各処理が対応Skillのscriptまたは既存機械処理へ割り当てられている
- grammar-based testingが初回実装scopeから外れている
- LLMとscriptの責務境界、`authority_refs` / `reference_refs`が文書化されている
- risk schemeが成果物へ残り、`RISK-D004` / `RISK-D005`が正しく分岐する
- risk / technique candidates / change impact / test requirement structure / 同値分割 / Each Choice / BVA / Decision Table / Base Choice / Pairwise / N-wise / 状態遷移 / n-switch / Round-trip / flow / schema / UI / test case structure / traceabilityにruntime unit testがある
- Decision Tableが任意condition数と複数actionを表現できる
- 同一成果物で同種技法modelを複数保持・独立評価でき、同一`(技法, model_key)`の矛盾定義を拒否できる
- 成果物の正規化入力JSONから同じgeneratorを再実行できる
- generatorの100% Coverageを対象仕様全体100%と誤認しない
- BVA / 同値分割 / Pairwise / 状態遷移を自由文検索だけに頼らず機械評価できる
- CI IDが100件以上でも既存下流Skillを含め追跡できる
- Pairwise / N-wiseが全Cartesian productの事前materializeを前提にしない
- SAT / UNSAT / unsupported / limit_exceededを区別し、探索上限到達をUNSATまたは100% Coverageとして扱わない
- state guard feasibility不明時に構造候補と正式Coverageを混同しない
- raw schema full parserを追加せず、正規化済みconstraint契約でdialect差を保持する
- `traceability.py`をテスト設計の構造追跡に限定する
- 5 SkillそれぞれのSkill-only portability testがPASSする
- Python 3.11でcompile / unit test / deterministic eval / semantic dataset validationがPASSする
- runtime unit testが0件ではない
- `skills-ref validate`が全SkillでPASSする
- README、`EVALS.md`、`ASSERTIONS.md`、関連referenceが実装と一致する
- 外部referenceだけから製品固有expected resultを創作する回帰がない
- Error Guessing、Exploratory Testing、リスク発見等の意味判断を決定論的generatorへ移していない

## 13. 実装時に避けること

- eval用helperをruntimeからimportする
- generator outputをそのままexpected fixtureへ使う
- 任意Python式を`eval()`で制約として実行する
- 汎用plugin frameworkを先に作る
- 全テスト技法を別Skillへ分割する
- grammar runtimeを今回追加する
- PICT / GraphWalker / Z3 adapterを将来用に先行実装する
- Pairwise / N-wiseで全Cartesian productを必ずmaterializeする
- 空Coverage母集団を100% CoverageとしてPASSさせる
- Coverage対象と生成CIを全技法で1対1と仮定する
- model内100% Coverageを対象仕様全体100%と表現する
- `null`のtechnique signalを`false`へ暗黙変換する
- exploration limit到達をUNSATと判定する
- Decision Tableを単一outcomeモデルへ固定する
- UI / HTML / APGのreferenceを製品Authorityとして扱う
- 有効遷移集合の補集合から全invalid transitionを機械生成する
- guard未評価のsequenceを実行可能Coverageと断定する
- HTML `pattern`をPython `re`で同等とみなす
- project-specific risk方式を標準1〜4 / 4×4へ強制する
- 構造上のedge存在だけで意味上のCoverage充足と判定する
- `limit_exceeded`時にCoverage基準を無断で下げる
- Python unavailableだけを理由に従来の意味判断まで禁止する

