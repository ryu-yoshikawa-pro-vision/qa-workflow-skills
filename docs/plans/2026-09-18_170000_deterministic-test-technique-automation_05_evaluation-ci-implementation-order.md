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
test_test_case_structure.py
test_coverage_analysis_traceability.py
test_runtime_contract.py
test_runtime_markdown_roundtrip.py
test_runtime_determinism.py
test_runtime_workflow_integration.py
```

実行test数が0件ならCIを失敗させます。

## 3. 共通契約の必須回帰

### strict JSON

- duplicate key拒否
- `NaN` / `Infinity`拒否
- 不正top-level type拒否
- decimalの型保持
- nullと欠落の区別

### runtime envelope

- `envelope_version / generator_contract_version / generator / model_key / model_fingerprint / generation_fingerprint / static_data_versions / runtime_status / model_status / payload / issues`
- `ok / invalid_input / unsupported / limit_exceeded`は構造化結果を返せた扱いで終了code 0
- `internal_error`またはenvelope生成不能だけ終了code 1
- Agent側は終了codeだけで判断せずstdout envelopeをparseする
- supported subsetへの`unsupported`を正常fallback扱いしない
- stderrへ入力全文・secretを出さない
- unknown `route_to` / `resume_skill`を拒否

### canonicalization / fingerprint

- object key順が違ってもcanonical結果は同じ
- `authority_refs` / `reference_refs`の順序差でfingerprintが変わらない
- 順序に意味があるfactor / value / transition配列の順序変更はfingerprintへ反映
- decimal / date / fixed-offset datetimeの正規化
- 人間向け説明文だけを変えてもsemantic / model fingerprintが変わらない
- upstream意味データ変更でsemantic fingerprintが変わる
- generator contractまたはstatic data version変更で`generation_fingerprint`が変わる
- fenced JSONの保存→抽出→strict decode→canonical化でmodel fingerprintが一致する

### 決定論性

同一fixtureを少なくとも`PYTHONHASHSEED=1`と`PYTHONHASHSEED=999`で実行し、machine outputが一致することを確認します。

locale依存sort、set iteration順、dict insertion偶然性に依存する出力を禁止します。

### hard limit

`_02`の固定上限について境界値をテストします。

- item数、入力byte、nesting depth、1文字列、stdout byteの各上限ちょうどは処理可能
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
- upstream version変更時の影響model限定

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

- linear border
- pivot / anchor
- closed / open border
- ON / OFF / IN / OUT
- closed borderではON=inside / OFF=outside
- open borderではON=outside / OFF=inside
- `<border_key>:ON|OFF|IN|OUT` target key
- representable / unrepresentable boundary
- coefficient 0
- constraintとの整合
- override point所属検証

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
- simple loop
- fork / join branch Coverage
- `region_key`によるfork / join対応
- nested region
- 同一region複数fork / join、crossing regionは`unsupported`
- scheduler interleavingを勝手に生成しない
- edge証拠とpath証拠の分離

### CRUD

- matrix key
- operation Coverage
- 欠落operation
- 空cellを自動欠陥化しない

### Cause-Effect

- boolean AST
- unknown cause
- cycle禁止
- assignment hard limit
- Decision Tableとの直接互換payload

### grammar

- undefined nonterminal
- unreachable production
- recursion / max depth
- shortest derivation
- production Coverage
- 明示mutationだけinvalid候補へ使う

### schema / HTML

raw machine-readable入力をfixtureにします。

- JSON Schema 2020-12対応keyword
- `properties / items` traversal
- local JSON Pointer `$ref`
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
- uniform finite
- uniform integer
- weighted categorical
- case count limit
- 一般Coverage 100%を作らない
- `required_case_count / generated_case_count / complete`による終了条件

### Metamorphic Testing

- 各input transform
- 各expected relation
- unsupported transform
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
- 新modelだけ新key
- 削除keyを再利用しない
- 既存TR / TCN / CI / TC IDを意味変更なしで維持
- 新規項目だけ新番号
- target key → CI ID mapping維持
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

runtime traceabilityと既存validatorが同じfixtureに対して独立にmissing / orphan / unknown / staleを検出できることを確認します。

### `qa-workflow`

次を完了条件・再利用条件へ追加します。

- contract version
- upstream artifact version
- model fingerprint
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
- CRUD model
- grammar
- operational profile / Random Testing採用
- metamorphic relation
- UI pattern分類
- test data / environment requirement
- merge groupの意味上の妥当性
- model内100%を対象仕様全体100%と誤認しない
- scriptがexpected resultを創作していない

semantic referenceをgenerator outputから自動生成しません。

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
   - upstream version変更
   - 影響modelだけ`要再検証`
   - stale派生物を拒否
   - 再生成後に再利用可能

3. modelだけ変更
   - fingerprint変更
   - 旧machine evidence拒否

4. 局所ブロック
   - 1 modelだけ未解決
   - 独立modelは継続
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
   - LLM手計算だけの成果物を決定論的生成済みと判定しない

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
- network不要
- 必要依存が`compatibility`またはrepository依存へ明示
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

- risk scheme
- technique signal machine evidence
- change graph
- environment requirement

### `test-requirement-design`

- runtime structure検査の処理順

### `test-condition-design`

- 全実装技法のCoverage契約
- 正規化model表
- stable target / CI mapping
- runtime metadata
- test data requirement
- machine evidence

### `test-case-design`

- runtime structure検査の処理順
- stable ID / stale

### `coverage-analysis`

- stale / fingerprint / test-design traceability

### `qa-workflow`

- model単位状態
- legacy昇格
- upstream version / stale伝播
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
- contract version
- static data version
- model fingerprint
- hard limit
- tie-break
- structured issue

### Step 2: identity / workflow基盤

- stable model key
- stable QA ID
- target → CI mapping
- upsert / stale
- upstream artifact version
- qa-workflow model単位状態
- legacy昇格

### Step 3: test-analysis

- risk scheme
- technique candidates
- change graph / impact
- environment requirement

### Step 4: test-requirement-design

- requirement structure
- runtime再検査

### Step 5: condition design 基本技法

- EP / Each Choice
- BVA
- Domain Testing
- schema / HTML parser
- test data requirement

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
- Classification Tree adapter

### Step 8: state / scenario

- state / transition
- setup prefix / reset
- n-switch / Round-trip
- simple loop
- fork / join

### Step 9: Random / Metamorphic / UI

- `pcg32-v1`
- metamorphic relation
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
- strict JSON / envelope / canonicalization / contract versionが実装済み
- static data versionとmodel fingerprintが再現可能
- stable model key / QA ID / CI mappingが維持される
- 再実行がupsertされ重複machine evidenceを作らない
- stale派生成果物を完了扱いしない
- 選択技法がmodelまたは明示的な扱いへ閉じる
- machine-readable schema / HTMLをLLMが手変換せず対応scriptが処理する
- script間の機械変換でLLMを再介在させない
- 全技法generatorと構造scriptにunit testがある
- hard limit / tie-breakが契約どおり
- runtime出力と保存machine evidenceの一致をvalidatorが確認する
- model内Coverageと仕様全体Coverageを混同しない
- qa-workflowがupstream変更、model変更、stale、局所ブロック、legacyを処理できる
- runtime適用可能な代表fixtureでruntime使用が統合評価から確認できる
- 5 Skillの単体移植性が成立
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
- external referenceを製品Authorityへ昇格する
- 意味判断なしにinvalid behavior / expected result / riskを創作する
- machine evidenceをLLMに手計算させる
- machine-readable入力を対応scriptがあるのにLLMへ再変換させる
