# テスト分析・テスト技法の決定論的自動化Plan

## 1. 評価方針

評価を次の4層へ分けます。

1. runtime script unit test
2. 独立した決定論的validator
3. semantic eval
4. qa-workflow統合評価

generatorとvalidatorは実装helperを共有しません。expected fixtureをgenerator出力から自動生成しません。

## 2. runtime script unit test

`tests/skills/runtime/`直下へ配置し、Python 3.11の`unittest discover`で実行します。

対象:

```text
test_test_analysis_risk_matrix.py
test_test_analysis_technique_candidates.py
test_test_analysis_change_impact.py
test_test_analysis_environment_requirements.py
test_test_requirement_structure.py
test_test_condition_equivalence_partitions.py
test_test_condition_bva.py
test_test_condition_domain_testing.py
test_test_condition_decision_table.py
test_test_condition_combinatorial.py
test_test_condition_classification_tree.py
test_test_condition_state_transition.py
test_test_condition_flow_paths.py
test_test_condition_crud_matrix.py
test_test_condition_cause_effect.py
test_test_condition_grammar_cases.py
test_test_condition_schema_cases.py
test_test_condition_ui_pattern_candidates.py
test_test_condition_test_data_requirements.py
test_test_condition_random_testing.py
test_test_condition_metamorphic.py
test_test_condition_materialize_coverage.py
test_test_case_structure.py
test_coverage_analysis_traceability.py
test_runtime_contract.py
test_runtime_markdown_roundtrip.py
test_runtime_determinism.py
test_runtime_workflow_integration.py
```

実行test数が0件ならCIを失敗させます。

各runtime scriptには`tests/skills/runtime/fixtures/<script-name>/valid_minimal.json`を1件必須とし、これをPlan `_03`のrequired input schemaの実行例とします。fixtureは手書きし、generator出力から生成しません。unknown field拒否、required field欠落、型不一致は各scriptのunit testで確認します。

CLI integration testは各代表fixtureをsubprocessで`python <script-path>`起動し、stdinへJSONを渡してstdout envelopeを読む経路を使用します。1 subprocessのtimeoutは30秒です。

## 3. 共通契約の必須回帰

### strict JSON

- duplicate key拒否
- `NaN` / `Infinity`拒否
- 不正top-level type拒否
- decimalの型保持
- nullと欠落の区別

### runtime envelope

- `envelope_version / runtime_contract_version / generator_contract_version / generator / model_key / model_fingerprint / generation_fingerprint / static_data_versions / runtime_status / model_status / deterministic_generated / payload / issues`
- artifact全体scriptでは`model_key`を禁止し、技法model scriptだけ`<slug>-\d{3,}`を要求
- `ok / invalid_input / unsupported / limit_exceeded`は構造化結果を返せた扱いで終了code 0
- `internal_error`は可能ならenvelopeを返して終了code 1、envelope生成不能も1
- Agent側は終了codeだけで判断せずstdout envelopeをparseする
- supported subsetへの`unsupported`を正常fallback扱いしない
- Python unavailable / runtime未実行は成果物metadataで`runtime_status=not_run / deterministic_generated=false`
- status対応表どおりの`model_status`とblocking issueを要求
- staleはruntime statusではなく`freshness_status`としてworkflowが付与
- stderrへ入力全文・secretを出さない
- unknown `route_to` / `resume_skill`を拒否

### canonicalization / fingerprint

- object key順が違ってもcanonical結果は同じ
- `authority_refs` / `reference_refs`の順序差でfingerprintが変わらない
- 順序に意味があるfactor / value / transition配列の順序変更はfingerprintへ反映
- decimal / date / fixed-offset datetimeの正規化
- 人間向け説明文だけを変えてもmodel fingerprintが変わらない
- upstream Entityの正規字段変更でその`content_fingerprint`だけが変わる
- 無関係なupstream Entity変更では対象modelをstaleにしない
- generator、runtime contract、generator contract、static data version変更で`generation_fingerprint`が変わる
- machine outputへ影響するbug fix / tie-break変更でgenerator contract versionを更新する
- fenced JSONの保存→抽出→strict decode→canonical化でmodel fingerprintが一致する

### 決定論性

同一fixtureを少なくとも`PYTHONHASHSEED=1`と`PYTHONHASHSEED=999`で実行し、machine outputが一致することを確認します。

locale依存sort、set iteration順、dict insertion偶然性に依存する出力を禁止します。

### hard limit

`_02`の固定上限について境界値をテストします。

- item数、入力byte、nesting depth、1文字列、stdout byteの各上限ちょうどは処理可能
- feasibility search nodeはroot=1、visited partial assignment単位で数える
- target / row / candidateはstable key重複除去後に数える
- 1件または1 byte超過で`limit_exceeded`
- Coverage基準を自動で下げない
- 部分結果を100%としない

## 4. 技法・構造処理の必須回帰

### risk matrix

- repository-default 4×4
- project-specific matrix完全性
- matrix levelごとの`priority_map`完全性
- mapped priorityが`高 / 中 / 低`のいずれか
- scheme外値拒否
- project-specificを標準方式で上書きしない
- mapped priorityが`test-requirement-design`の最低優先度判定へ渡る

### technique candidates

- 全signal key
- `true / false / null`
- `_03`のsignal → candidate mapping
- 複数`true`時のunionと安定順
- `undetermined_signals`
- `complete=false`だけではworkflowをブロックしない
- `Selection Source = analysis / user / existing_artifact`
- ユーザー明示 / 既存成果物由来の技法をcandidate scriptが却下しない
- 新規正規技法名
- 選択技法のmodel / disposition閉鎖

### change impact

- node / edge type
- `depends_on / traces_to / derived_from`の探索方向
- unknown node / dangling edge
- 名称類似だけでedge追加しない
- upstream content fingerprint変更時の影響model限定

### test environment requirement

- 同一requirement統合
- compatible value統合
- incompatible value矛盾
- 実環境を勝手に推測しない

### test requirement structure

- Authority / Risk → TR closure
- linked + disposed重複
- unknown upstream ID
- 最低優先度
- draft → runtime検査 → 再検査の処理順

### 同値分割 / Each Choice

- partition重複 / 衝突
- representative所属
- 成果物閉鎖とCoverageの分離
- DispositionをCoverage済みと数えない
- Authority付き成立不能だけを母集団から除外

### BVA

- inclusive / exclusive
- 2-value / 3-value
- integer / Decimal / date / local datetime / fixed-offset datetime
- step不明時に隣接値を創作しない
- 同一具体値でもCoverage positionを区別

### Domain Testing

- Reliable Domain Coverageだけを実装
- linear border
- pivot / anchor / positive step
- `< / <= / > / >= / = / !=`
- closed `<= / >=`: ON=border、OFF=outside最隣接、IN=inside最隣接、OUT=さらにoutside
- open `< / >`: OFF=border、ON=inside最隣接、IN=さらにinside、OUT=outside最隣接
- `=`: ON + OFF_NEG + OFF_POS
- `!=`: OFF + ON_NEG + ON_POS
- `_03`で定義したrelation別target key
- representable / unrepresentable boundary
- coefficient 0 / anchor不足
- constraintとの整合
- override point所属・距離検証

### Decision Table

- 任意condition数
- action key完全性
- forbidden constraint
- unspecified
- duplicate / conflict
- don't-care merge candidate
- merge後に未定義assignmentを増やさない
- Authority保持

### 組合せ

- exhaustive
- constraint付きBase Choice
- Pairwise / N-wise
- mixed-strength
- `SAT / UNSAT / limit_exceeded`
- target union
- tie-break
- full Cartesian productの事前materializeを前提にしない

### 状態遷移

- transition identity
- all state / all transition
- n-switch
- Round-trip
- guard feasibility
- initial / reset
- setup prefix
- shortest path tie-break
- 実行開始不能sequenceを正式Coverageにしない

### flow

- node / edge / path
- `max_path_length=1..1000`
- max path length超過を列挙しない
- simple loop
- fork / join branch Coverage
- `region_key`によるfork / join対応
- nested region
- 同一region複数fork / join、crossing regionは`unsupported`
- scheduler interleavingを勝手に生成しない
- edge証拠とpath証拠の分離

### CRUD

- completeness / consistencyを別Coverage summaryで返す
- matrix operation target
- lifecycle sequence
- Authority付きnegative sequence
- matrixに存在しないsequence stepを拒否
- consistency未正規化ではCRUD全体をcompleteにしない
- 空cellを自動欠陥化しない

### Cause-Effect

- boolean AST
- unknown cause
- cycle禁止
- assignment hard limit
- Decision Tableとの直接互換payload

### Syntax-Based Testing

- production_key一意性
- undefined nonterminal
- unreachable production
- recursion / max depth
- shortest derivation
- production Coverage
- `delete_terminal / replace_terminal / insert_terminal`だけをmutationとして許可
- mutation結果を自動で製品上invalidと断定しない

### schema / HTML

raw machine-readable入力をfixtureにします。

- JSON Schema 2020-12対応keyword
- `properties / items` traversal
- local JSON Pointer `$ref`
- cyclic local `$ref` subtreeは`unsupported`
- external `$ref`は事前dereference要求
- OpenAPI 3.0 `nullable` / boolean exclusive boundary
- HTML constraint validation
- unsupported applicator
- unsupported keywordが意味へ影響するsubtreeだけを局所`unsupported`
- 親validation意味を左右する場合は親subtree全体を`unsupported`
- annotationだけでは拒否しない
- HTML `pattern`をPython `re`で評価しない
- 正規化constraintをEP / BVA / test data requirementへ直接渡す

### UI pattern

- pattern / alias一意性
- catalog SHA-256
- catalog変更で旧結果stale
- external referenceをAuthorityへ昇格しない
- 未知patternを自動登録しない

### test data requirement

- scalar equality / enum set / numeric・date・datetime range / version range / boolean
- operatorごとのintersection
- incompatible constraint
- unsupported operator
- model / target traceability
- 実データを自動取得しない

### Random Testing

- `pcg32-v1`のstate / seeding / XSH RR / rejection sampling
- seed=42固定test vector
- 同seedで同列
- seed差
- `uniform_finite`: non-empty / duplicate拒否
- `uniform_integer`: inclusive min/max
- `categorical`: positive integer weightのみ、value重複拒否
- case count limit
- 一般Coverage 100%を作らない
- `required_case_count / generated_case_count / complete`による終了条件

### Metamorphic Testing

- `set / add_decimal / multiply_decimal / append / permute / sort`のrequired parameter
- JSON pathはobject key / array indexだけ
- `permute` indicesが完全bijection
- `equal / not_equal`、numeric monotonic、unique scalar array subset / supersetの型制約
- unsupported transform / path / relation
- source → follow-up traceability
- relationごとのrequired source数 / follow-up数
- 一般Coverage 100%を作らない
- 各MRを1回扱っただけで十分と判定しない
- relation自体をscriptが創作しない

### test case structure

- TCN / CI → TC closure
- linked + disposed重複
- unknown upstream
- highest priority
- numbered expected result / Authority
- runtime検査後の再検査

### traceability

- Authority / Risk → TR → TCN → CI → TC
- CIなしTCN → TC
- missing / orphan / unknown
- stale downstream
- 技法Coverageを再計算しない

## 5. stable identity・再実行の回帰

- 同じmodel改訂で`model_key`維持
- 新modelは同slug最大番号+1、新系列は001
- 削除keyを同系列で再利用しない
- qa-workflowの再利用元有無で成果物系列を一意に判定
- TR / TCN / TCは意味上同一の既存Entityを再利用できる場合だけID維持し、runtimeがsemantic matchingしない
- TR / TCN / TCの新規IDは最大番号+1、999到達後は`id_space_exhausted`
- 初回mappingはcanonical target順でCI01から採番
- existing mappingは同一TCN内で維持し、新targetだけ最大番号+1
- duplicate mapping / parent mismatchを拒否
- 消滅targetで下流`要再検証`
- 同じ実行を2回行ってmachine evidenceが重複しない
- stale rowを完了扱いしない

## 6. 既存validatorの更新

### 共通ID

`CI\d{2,}`を許可します。ただし`TCN-\d{3}-CI\d{2,}`だけをCIとして認識し、`SPEC-001-CI01`等を誤認しません。

### `test-analysis`

- risk scheme分岐
- technique selection machine evidence
- change graph
- environment requirement

### `test-requirement-design`

既存`TR-D001`〜を維持し、runtimeと同じfixtureで独立照合します。

### `test-condition-design`

自由文検索依存を減らし、技法固有key、model、target、Coverage、runtime metadataを検査します。

正規化model fingerprintと保存済みmachine evidenceの不一致を検出します。

### `test-case-design`

既存構造契約を維持し、runtimeと独立にclosure / priority / Authority mappingを検証します。

### `coverage-analysis`

`assets/output-template.md`を次のように更新します。

- `カバレッジ基準確認`へ`Model Key`列を追加
- `カバレッジ項目の扱い`へ`Model Key`列を追加
- `陳腐化 / 孤立分析`へ`Model Key`列を追加
- modelを持たないlegacy / E2E経路では空欄を許可

validatorはruntime traceabilityと独立にmissing / orphan / unknown / staleを検出し、stale / gapをTCN / CIだけでなく関連`model_key`まで追跡します。

### `question-analysis`

`assets/output-template.md`の`不明点 / 質問一覧`と`ブロック中範囲`へ、既存の`再開対象 / 実行範囲`とは別に`Model Key`と`Target Key`列を追加します。

- `再開対象 / 実行範囲`は既存`QUESTION-D017`のSkill用途判定だけに使用する
- `Model Key` / `Target Key`はruntime issueの局所識別専用とし、単一用途Skillでも値を許可する
- 同じブロッカーIDについて質問一覧とブロック中範囲のModel / Targetが一致することをvalidatorで確認する
- runtime issue由来でない質問では両列を空欄にできる

### `qa-workflow`

既存Skill状態表は`qa-workflow`出力時に引き続き必須とし、`WF-D009`は維持します。ただし永続正本にはせず、成果物metadataから再構築可能にします。

`assets/workflow-state-template.md`へ別表`モデル状態`を追加します。

`Skill | Model Key | Model Status | Freshness | Runtime Status | Deterministic Generated | Blocker / Issue`

- `Model Key`は同一Skill内一意
- `Freshness`は`current / stale`
- `Runtime Status`は`ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Deterministic Generated`は`Yes / No`
- Skill状態表の`WF-D012`は従来どおりSkill + 対象にだけ適用し、モデル状態表へ流用しない
- ワークフロー全体`完了`では必須modelに`stale / unresolved / blocked`または`Deterministic Generated=No`の未処置が残らないことを追加検査する

完了条件・再利用条件へ次を追加します。

- envelope / runtime / generator contract version
- upstream Entity別content fingerprint
- model / generation fingerprint
- stale派生成果物
- model単位の`要再検証` / ブロック中
- runtime未実行 / unsupportedとQA成果物状態の分離
- legacy成果物の昇格

## 7. semantic eval

維持・追加する主な確認:

- 正規化modelがAuthority / Risk / TRの意味を必要十分に表している
- partition / boundary / Domain borderの意味
- Decision Table condition / action / constraint
- factor / strength / mixed-strength選択
- state / guard / reset / flow / fork-joinの意味
- CRUD completeness / consistency model
- Syntax-Based Testingのgrammar / production / mutation意味
- operational profile / Random Testing採用
- metamorphic relation
- UI pattern分類
- test data / environment requirement
- merge groupの意味上の妥当性
- model内100%を対象仕様全体100%と誤認しない
- scriptがexpected resultを創作していない

semantic referenceをgenerator outputから自動生成しません。

### semantic dataset件数

現行`tests/skills/evals/semantic/test_semantic_datasets.py`の「各Skillちょうど2件 / 合計28件」は本変更で撤廃します。

- 各Skillは2件以上
- case IDはSkill内一意
- repository全体は28件以上
- `test-analysis` / `test-condition-design`は新規正規技法5種を少なくとも1件ずつsemantic評価できるcaseを持つ。1 caseで複数技法を評価してよいが、各技法のcriteriaが明示されること
- `adversarial-review`は下記代表誤用をそれぞれcriteriaまたはcaseとして評価する
- 既存Skillのcaseを減らして最低件数だけ満たす変更は行わない

`adversarial-review`には技法アルゴリズムを複製せず、次を評価します。

- Random Testingを一般的な「100% Coverage」と記載する
- Metamorphic TestingでMRを1回だけ扱ったことを十分なCoverageと断定する
- Domain Testingでrelation別required pointを欠落させる
- CRUD completenessだけでconsistencyも完了したと断定する
- Syntax-Based Testingのmutation candidateをAuthorityなしで製品上invalidと断定する
- 新規技法のexpected resultをAuthorityなしで創作する

### 発火評価

新規技法追加により、現行`.github/workflows/validate-skills.yml`の固定件数契約を次へ変更します。

- 全Skill: train 12件以上、validation 8件以上
- 各datasetはpositive / negative同数
- train / validation queryはSkill内で重複しない
- repository全体のtrigger query総数は280件以上
- `test-analysis` / `test-condition-design`は既存queryを削らず、新規技法境界を追加する

`test-analysis` / `test-condition-design`では、Domain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testingの各技法についてtrainとvalidationの双方で次を持ちます。

1. `test-analysis` positive: 技法を採用すべきか判断する依頼
2. `test-analysis` negative: その技法で具体的なCoverage / 条件を設計する依頼
3. `test-condition-design` positive: 技法を使って具体的なCoverage / 条件を設計する依頼
4. `test-condition-design` negative: 技法の採用可否だけを判断する依頼

さらに各Skillのtrainまたはvalidationに「技法とは何か説明して」という説明依頼negativeを少なくとも1件含めます。これらのscenarioとdataset case IDの対応表を`EVALS.md`へ記録し、train / validation未使用queryを最終holdoutとして残します。
## 8. qa-workflow統合評価

少なくとも次をE2E fixture化します。

1. 新規設計
   - test-analysisで技法選択
   - model作成
   - runtime生成
   - CI / TC
   - coverage-analysis
   - workflow完了

2. 上流Authority変更
   - upstream content fingerprint変更
   - 人間向け説明文だけの変更ではfingerprint不変
   - 影響modelだけ`要再検証`
   - stale派生物を拒否
   - 再生成後に再利用可能

3. model / generator変更
   - model意味変更で`model_fingerprint`変更
   - generator contract / static data変更で`generation_fingerprint`変更
   - 旧machine evidence拒否

4. 局所ブロック
   - 1 modelだけ未解決
   - `question-analysis`往復で`model_key / target_key`維持
   - 独立modelは継続
   - workflow状態表がなくても成果物metadataから状態再構築
   - workflowは部分完了

5. runtime unsupported
   - QA成果物状態と分離
   - 「決定論的生成済み」と誤表示しない

6. legacy成果物
   - 旧成果物を参照
   - 変更時に新modelへ昇格
   - 以後version / fingerprint契約で再利用

7. runtime利用確認
   - script適用可能fixtureでruntime result metadataが存在
   - supported subsetが`unsupported`になった場合は失敗
   - LLM手計算だけの成果物を決定論的生成済みと判定しない

8. 途中工程開始
   - ユーザーが技法を明示したTRから`test-condition-design`を開始
   - `Selection Source=user`を保持
   - `test-analysis`の技法選択行を作るためだけに上流へ戻らない

## 9. CI

既存`.github/workflows/deterministic-output-evals.yml`へ追加します。

```bash
python -m compileall -q skills/test-analysis/scripts
python -m compileall -q skills/test-requirement-design/scripts
python -m compileall -q skills/test-condition-design/scripts
python -m compileall -q skills/test-case-design/scripts
python -m compileall -q skills/coverage-analysis/scripts
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v
```

既存のdeterministic eval、semantic dataset validation、Skill validationも維持します。

`validate-skills.yml`へruntime unit testを重複追加しません。

## 10. Skill単体移植性

次の5 Skillを単体コピーして代表scriptをCLI実行します。

- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`

確認:

- repo rootのeval helperをimportしない
- 5 Skillの`scripts/runtime_contract.py`がSHA-256一致
- network不要
- 必要依存が`compatibility`またはSkillと一緒に移植可能なmanifestへ明示
- Skill rootからscriptを解決
- stdout envelopeを読める
- Python unavailable時にSkill全体を利用不能と誤判定しない
- runtime未実行を決定論的生成済みと表現しない

## 11. ドキュメント更新

### README

- LLM / runtime責務境界
- contract / static data version
- stale / legacy / 再利用
- Python要件
- Skill package内script

### `test-analysis`

- `SKILL.md` / `references/guidance.md`へ新規正規技法と選択条件を追加
- `assets/output-template.md`へ`Selection Source`と技法選択machine evidenceを追加
- risk scheme / priority mapping
- change graph
- environment requirement
- deterministic / semantic / trigger evalを更新

### `test-requirement-design`

- runtime structure検査の処理順

### `test-condition-design`

- `SKILL.md`の対象技法を更新
- `references/coverage-techniques.md`へ全実装技法の適用条件、Coverageまたは終了条件を追加
- `assets/output-template.md`へ正規化model metadata、fenced JSON machine model、stable target / CI mappingを追加
- Random / Metamorphicは一般Coverage 100%を定義しない
- runtime metadata
- test data requirement
- deterministic / semantic / trigger evalを更新

### `test-case-design`

- runtime structure検査の処理順
- stable ID / stale

### `coverage-analysis`

- stale / fingerprint / test-design traceability
- model_key単位のgap / stale参照

### `question-analysis`

- runtime issueの`model_key / target_key`を質問・ブロック・再開まで保持

### `qa-workflow`

- model単位状態を成果物metadataから再構築
- legacy昇格
- upstream content fingerprint / stale伝播
- 完了条件

### `EVALS.md` / `ASSERTIONS.md`

新契約と独立評価を記録します。

## 12. 実装順序

### Step 0: 基準再確認

- main最新
- 関連Skill / validator / CI
- branch差分

### Step 1: 共通runtime契約

- strict JSON
- output envelope
- canonicalization
- envelope / generator contract version
- static data version
- model / generation fingerprint
- content fingerprint
- hard limit
- tie-break
- structured issue

### Step 2: identity / workflow基盤

- stable model key
- 既存TR / TCN / TCのID再利用規則と999上限
- target → CI mapping
- upsert / stale
- upstream content fingerprint
- qa-workflow model単位状態
- legacy昇格

### Step 3: test-analysis

- risk scheme / priority mapping
- technique candidates / Selection Source
- 新規正規技法のSkill契約
- trigger eval更新
- change graph / impact
- environment requirement

### Step 4: test-requirement-design

- requirement structure
- runtime再検査

### Step 5: condition design 基本技法

- EP / Each Choice
- BVA
- Domain Testing ON / OFF / IN / OUT
- schema / HTML parser
- test data requirement
- 新規技法のSkill / reference / template / eval契約

### Step 6: rule / model技法

- Decision Table / don't-care候補
- Cause-Effect
- CRUD
- grammar

### Step 7: 組合せ

- exhaustive
- constraint付きBase Choice
- Pairwise / N-wise
- mixed-strength
- `classification_tree.py` adapter

### Step 8: state / scenario

- state / transition
- setup prefix / reset
- n-switch / Round-trip
- simple loop
- fork / join

### Step 9: Random / Metamorphic / UI

- `pcg32-v1`固定test vector
- Random completion criterion
- Metamorphic relation / completion criterion
- UI catalog / static version

### Step 10: test-case / traceability

- case structure
- merge group
- traceability
- stale downstream

### Step 11: workflow統合

- end-to-end path
- upstream変更
- model変更
- local block
- unsupported
- legacy
- runtime利用確認

### Step 12: 全体検証・文書同期

- unit / deterministic / semantic / workflow
- CI
- portability
- README / references / templates / EVALS / ASSERTIONS

## 13. リスク

### LLMの正規化誤り

semantic evalとAuthority traceで検出し、scriptが意味を補完しません。

### 計算量

固定hard limitを使用し、超過時にCoverage基準を下げません。

### generator / validator同時誤り

helperとexpected fixtureを共有しません。

### stale成果物

model / upstream / static data versionを保持し、qa-workflowで`要再検証`へ戻します。

### runtime非対応環境

runtime状態とQA成果物状態を分離します。

### 依存関係

標準ライブラリを優先しますが、正確性を犠牲にして依存を避けません。必要な依存追加はPlan更新と互換性確認を経ます。

## 14. 完了条件

Plan完了には次をすべて満たす必要があります。

- `_01`で実装対象にした処理がruntimeまたは既存機械処理へ割り当てられている
- 目的内の技法・構造処理が本Plan外へ先送りされていない
- strict JSON / envelope / canonicalization / envelope version / generator contract versionが実装済み
- upstream content fingerprint、static data version、model / generation fingerprintが再現可能
- 正規化modelのMarkdown fenced JSON round-tripが成立する
- stable model key / 既存Entity ID再利用 / CI mappingが契約どおり
- 再実行がupsertされ重複machine evidenceを作らない
- stale派生成果物を完了扱いしない
- 選択技法がmodelまたは明示的な扱いへ閉じる
- machine-readable schema / HTMLをLLMが手変換せず対応scriptが処理する
- script間の機械変換でLLMを再介在させない
- 全技法generatorと構造scriptにunit testがある
- item数 / byte / depthを含むhard limitとtie-breakが契約どおり
- runtime出力と保存machine evidenceの一致をvalidatorが確認する
- supported subsetを`unsupported`でLLM fallbackしない
- model内Coverageと仕様全体Coverageを混同しない
- qa-workflowがupstream意味変更、generation変更、stale、局所ブロック、legacyを処理できる
- question-analysis往復でmodel / targetが失われない
- 途中工程開始と`Selection Source`が既存workflowを壊さない
- runtime適用可能な代表fixtureでruntime使用が統合評価から確認できる
- 5 Skillの単体移植性が成立し、共通runtime helperの内容一致を検証できる
- test-analysis / test-condition-designのtrigger train / validation件数とpositive / negative比率を維持する
- adversarial-reviewの新規技法代表semantic fixtureがPASSする
- Python 3.11 compile / runtime unit / deterministic eval / semantic validation / workflow統合評価がPASS
- `skills-ref validate`がPASS
- README、Skill、reference、template、EVALS、ASSERTIONSが実装と一致
- Error Guessing、Exploratory Testing、risk発見、expected result等の意味判断をscriptへ移していない

## 15. 実装時に避けること

- eval helperをruntimeからimportする
- generator outputをexpected fixtureへ使う
- 任意Python式を`eval()` / `exec()`で実行する
- 将来用plugin / adapterを作る
- Coverage基準をlimit都合で下げる
- stale派生成果物を再利用する
- runtime `unsupported`をQA成果物の`対象外`と同一視する
- `null` signalを`false`へ変換する
- model内100%を仕様全体100%と表現する
- Random Testing / Metamorphic Testingへ一般的な100% Coverageを作る
- external referenceを製品Authorityへ昇格する
- 意味判断なしにinvalid behavior / expected result / riskを創作する
- machine evidenceをLLMに手計算させる
- machine-readable入力を対応scriptがあるのにLLMへ再変換させる
