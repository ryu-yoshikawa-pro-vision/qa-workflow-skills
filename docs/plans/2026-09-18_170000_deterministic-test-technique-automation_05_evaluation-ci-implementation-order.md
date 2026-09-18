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

- `envelope_version / runtime_contract_version / generator_contract_version / generator / runtime_unit_key / model_key / input_fingerprint / model_fingerprint / generation_fingerprint / static_data_versions / runtime_status / result_status / runtime_required / deterministic_generated / fallback_reason / payload / issues`
- model scriptは`runtime_unit_key=model:<model_key>`、artifact全体scriptは`runtime_unit_key=artifact:<generator>:<scope_key>`を要求し、artifact全体scriptの`model_key`はnull
- `ok / invalid_input / unsupported / limit_exceeded`は構造化結果を返せた扱いで終了code 0
- `internal_error`は可能ならenvelopeを返して終了code 1、envelope生成不能も1
- Agent側は終了codeだけで判断せずstdout envelopeをparseする
- `runtime_required=false`の対応subset外は`not_run` fallbackとし、実行済みscriptの`unsupported`を正常fallback扱いしない
- supported inputで`runtime_required=false`を拒否する
- artifact scriptのscope keyがscript別固定値 / input由来値と一致する
- Python unavailable / runtime未実行は成果物metadataで`runtime_status=not_run / deterministic_generated=false`とし、fingerprintをnull、`fallback_reason`を許可値で保持する
- status対応表どおりの`result_status / runtime_required / deterministic_generated`を要求
- model scriptでは`model_status=result_status`、artifact全体scriptでは`artifact_status=result_status`
- staleはruntime statusではなく`freshness_status`としてworkflowが付与
- stderrへ入力全文・secretを出さない
- unknown `route_to` / `resume_skill`を拒否

### canonicalization / fingerprint

- object key順が違ってもcanonical結果は同じ
- `authority_refs` / `reference_refs`の順序差でfingerprintが変わらない
- 順序に意味があるfactor / value / transition配列の順序変更はfingerprintへ反映
- decimal / date / fixed-offset datetimeの正規化
- 人間向け説明文だけを変えてもinput / model fingerprintが変わらない
- script固有input、`authority_refs`、`reference_refs`、modelの`selection_source`変更で`input_fingerprint`が変わる
- artifact全体scriptでもinput変更で`input_fingerprint / generation_fingerprint`が変わる
- upstream Entityの正規字段変更でその`content_fingerprint`だけが変わる
- 無関係なupstream Entity変更では対象runtime unitをstaleにしない
- envelope version、generator、runtime contract、generator contract、static data version変更で`generation_fingerprint`が変わる
- machine outputへ影響するbug fix / tie-break変更でgenerator contract versionを更新する
- fenced JSONの保存→抽出→strict decode→canonical化でmodel fingerprintが一致する

### 決定論性

同一fixtureを`PYTHONHASHSEED=1`と`PYTHONHASHSEED=999`の2条件で実行し、machine outputが一致することを確認します。

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
- upstream Entity content fingerprint変更時の影響model限定

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
- 低い指定優先度 + 空の`priority_override_reason`をviolation
- 低い指定優先度 + 非空override reasonは値を保持し、自動補正しない
- draft → runtime検査 → 再検査の処理順

### 同値分割 / Each Choice

- partition重複 / 衝突
- representative所属
- 成果物閉鎖とCoverageの分離
- DispositionをCoverage済みと数えない
- Authority付き成立不能だけを母集団から除外

### BVA

- `threshold / side / inclusive`から2-valueの`OTHER`を一意に決定
- 3-valueの`BELOW / AT / ABOVE`
- integer / Decimal / date / local datetime / fixed-offset datetime
- domain別step objectの型・正値検証
- fixed-offset datetime算術でoffsetを保持
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
- `_03`で定義したpartition + border + relation別target key
- partition expressionの`and / or / border_ref`検証
- ON / INがpartition全体true、OFF / OUTがfalseになること
- 対象border以外の条件によりrequired pointを作れない場合のblocking
- representable / unrepresentable boundary
- coefficient 0 / anchor不足
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
- n-switchは`N+1`個の連続valid transition全sequence
- `switch_count=0..10`
- Round-tripは開始終了stateのみ重複するsimple cycle、self-loop含む
- cycle rotationのcanonicalizationとstable target
- guard feasibility
- initial / reset
- setup prefix
- shortest path tie-break
- 実行開始不能sequenceを正式Coverageにしない

### flow

- `initial_node_keys[]`必須
- node / edge / initial→terminal bounded path
- `max_path_length=1..1000`
- explicit `loop_specs[]`の0 / 1 / typical / max iteration target
- `maximum_iterations=null` / typical重複時のtarget dedupe
- explicit `regions[] / branches[]`の連続path検証
- nested region
- crossing regionは`unsupported`
- scheduler interleavingを勝手に生成しない
- edge証拠とpath証拠の分離

### CRUD

- completeness / consistencyを別Coverage summaryで返す
- matrix operation target
- entity単位でC/R/U/D欠落を`crud:missing:*` anomalyとして列挙
- Authority付き`not_applicable` dispositionでのみmissing operationを閉じる
- lifecycle sequence
- Authority付きnegative sequence
- matrixに存在しないsequence stepを拒否
- consistency未正規化または未処置missing operationではCRUD全体をcompleteにしない
- 個々の空cellを自動欠陥化しない

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
- production適用回数最小 + production key列辞書順tie-breakのshortest derivation
- production Coverage
- `symbol_index`境界とterminal item検証
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
- annotation allowlistだけをvalidation非影響として許可
- unsupported keywordが意味へ影響するsubtreeだけを局所`unsupported`
- 親validation意味を左右する場合は親subtree全体を`unsupported`
- HTML `pattern`を保持するがPython `re`で評価しない
- JSON Schema `multipleOf` → `grid(base=0, step=m)`
- HTML数値`step`は`min`ありの場合だけgrid化し、minなし / date-time系は`unsupported`
- range / enum / requiredはEP / BVA / combinatorial / test dataへ、gridはschema Coverage / BVA / combinatorialだけへ渡す

### UI pattern

- `pattern_key / name / alias`のcatalog全体一意性と相互衝突
- pattern内`candidate_key`一意性とcategory許可値
- `ui:<pattern_key>:<candidate_key>` stable target
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
- `uniform_finite`: typed value、non-empty / duplicate拒否、宣言順sample mapping
- `uniform_integer`: inclusive min/max
- `categorical`: typed value、positive integer weightのみ、value重複拒否、宣言順累積区間
- case count limit
- 一般Coverage 100%を作らない
- `required_case_count / generated_case_count / complete`による終了条件

### Metamorphic Testing

- `follow_ups[]`の`follow_up_key`一意性と1..10,000件
- 各follow-upの`transforms[]`を宣言順に逐次適用
- `set / add_decimal / multiply_decimal / append / permute / sort`のrequired parameter
- JSON pathはobject key / array indexだけ
- `permute` indicesが完全bijection
- `expected_relation.output_kind`必須
- `equal / not_equal`、numeric monotonic、unique scalar array subset / supersetの`op × output_kind`互換性
- unsupported transform / path / relation
- source → follow-up traceability
- `required_pairs = source数 × follow_up数`
- 一般Coverage 100%を作らない
- 各MRを1回扱っただけで十分と判定しない
- relation自体をscriptが創作しない

### test case structure

- TCN / CI → TC closure
- linked + disposed重複
- unknown upstream
- highest priority
- 低い指定優先度 + 空の`priority_override_reason`をviolation
- 低い指定優先度 + 非空override reasonは値を保持し、自動補正しない
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
- `target_ref = sha256({model_key,target_key})`を独立再計算
- 同じTCN内に同名target keyを持つ複数modelがあってもtarget_refが衝突しない
- 初回mappingは`model_key → target_key`順でCI01から採番
- existing mappingは同一target_refで維持し、新target_refだけ最大番号+1
- target_ref内容不一致、duplicate mapping、parent mismatchを拒否
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

`assets/output-template.md`の`不明点 / 質問一覧`と`ブロック中範囲`へ、既存の`再開対象 / 実行範囲`とは別に`Runtime Unit Key`、`Model Key`、`Target Key`列を追加します。

- `再開対象 / 実行範囲`は既存`QUESTION-D017`のSkill用途判定だけに使用する
- `Runtime Unit Key`はruntime issue由来の質問で必須
- model issueでは`Model Key`を必須、artifact全体script issueでは空欄
- target固有issueだけ`Target Key`を必須
- 同じブロッカーIDについて質問一覧とブロック中範囲のRuntime Unit / Model / Targetが一致することをvalidatorで確認する
- runtime issue由来でない質問では3列を空欄にできる
### `qa-workflow`

既存Skill状態表は`qa-workflow`出力時に引き続き必須とし、`WF-D009`は維持します。ただし永続正本にはせず、成果物metadataから再構築可能にします。

`assets/workflow-state-template.md`へ別表`runtime状態`を追加します。

`Skill | Runtime Unit Key | Model Key | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue`

- `Runtime Unit Key`は同一Skill内一意
- model scriptではModel Key必須、artifact全体scriptでは空欄
- `Result Status = ready / unresolved / blocked`
- `Freshness = current / stale`
- `Runtime Status = ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Runtime Required / Deterministic Generated = Yes / No`
- `Fallback Reason`は空欄 / `outside_supported_subset` / `python_unavailable`
- Skill状態表の`WF-D012`は従来どおりSkill + 対象にだけ適用し、runtime状態表へ流用しない
- ワークフロー全体`完了`では全runtime unitが`Result Status=ready / Freshness=current`であることを追加検査する
- `Runtime Required=Yes`のunitでは、さらに`Deterministic Generated=Yes`を要求する
- `Runtime Required=No`のfallback unitも`Result Status != ready`なら完了を妨げる

完了条件・再利用条件へ次を追加します。

- envelope / runtime / generator contract version
- upstream Entity別content fingerprint
- input / model / generation fingerprint
- stale派生成果物
- runtime unit単位の`要再検証` / ブロック中
- runtime未実行 / unsupportedとQA成果物状態の分離
- legacy成果物の昇格
### output eval fixture schema

runtime対応Skillの`evals/output/cases/*/expected.json`では、既存fieldに加えて必要なcaseだけ次の`runtime_contract` objectを持てるようにします。

```json
{
  "runtime_contract": {
    "expected_runtime_unit_key": "model:pairwise-001",
    "upstream_entities": [
      {"skill":"spec-analysis","entity_ref":"SPEC-001","content_fingerprint":"sha256:..."}
    ],
    "expected_target_keys": [],
    "expected_runtime_status": "ok",
    "expected_result_status": "ready",
    "expected_runtime_required": true,
    "expected_deterministic_generated": true,
    "expected_fallback_reason": null,
    "expected_freshness_status": "current",
    "expected_target_id_map": []
  }
}
```

- expected target / Coverageは手書きfixtureから独立計算または明示し、generator出力をexpectedへコピーしない
- `expected_target_id_map`はstateful materialize caseだけ使用し、`{target_ref, model_key, target_key, ci_id}`配列で保持する
- validatorは保存済みruntime inputから`input_fingerprint`、model scriptでは`model_fingerprint`、全scriptで`generation_fingerprint`を独立再計算し、fixtureに書いたhash文字列を盲信しない
- upstream Entity差分caseでは無関係Entityの変更が対象modelをstaleにしないことを確認する
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
- merge groupの意味上の妥当性と`target_refs[]`の同一TCN制約
- model内100%を対象仕様全体100%と誤認しない
- scriptがexpected resultを創作していない

semantic referenceをgenerator outputから自動生成しません。

### semantic dataset件数

semantic dataset件数は次で固定します。

| Skill | case数 |
| --- | ---: |
| `test-analysis` | 7 |
| `test-condition-design` | 7 |
| `adversarial-review` | 8 |
| その他11 Skill | 各2 |
| repository合計 | 44 |

- `test-analysis`: 既存2 caseを維持し、Domain / CRUD / Random / Metamorphic / Syntax-Basedを主対象とする5 caseを追加する
- `test-condition-design`: 既存2 caseを維持し、同5技法を主対象とする5 caseを追加する
- `adversarial-review`: 既存2 caseを維持し、下記6誤用を主対象とする6 caseを追加する
- case IDはSkill内一意
- `tests/skills/evals/semantic/test_semantic_datasets.py`はSkill別expected count mapと合計44を検証する

`adversarial-review`には技法アルゴリズムを複製せず、次の6 caseを追加します。

- Random Testingを一般的な「100% Coverage」と記載する
- Metamorphic TestingでMRを1回だけ扱ったことを十分なCoverageと断定する
- Domain Testingでrelation別required pointを欠落させる
- CRUD completenessだけでconsistencyも完了したと断定する
- Syntax-Based Testingのmutation candidateをAuthorityなしで製品上invalidと断定する
- 新規技法のexpected resultをAuthorityなしで創作する
### 発火評価

既存queryは削除せず、新規技法5種の責務境界を追加します。件数は次で固定します。

| Skill | train | validation |
| --- | ---: | ---: |
| `test-analysis` | 24（positive 12 / negative 12） | 20（positive 10 / negative 10） |
| `test-condition-design` | 24（positive 12 / negative 12） | 20（positive 10 / negative 10） |
| その他12 Skill | 各12（6 / 6） | 各8（4 / 4） |
| repository合計 | 192 | 136 |

repository全体は328 queryです。

`test-analysis` / `test-condition-design`では、Domain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testingの各技法についてtrainとvalidationの双方に次の10 queryを追加します。

1. `test-analysis` positive: 技法を採用すべきか判断する依頼 × 5技法
2. `test-analysis` negative: その技法で具体的なCoverage / 条件を設計する依頼 × 5技法
3. `test-condition-design` positive: 技法を使って具体的なCoverage / 条件を設計する依頼 × 5技法
4. `test-condition-design` negative: 技法の採用可否だけを判断する依頼 × 5技法

さらに各datasetへ、各Skillについて「技法とは何か説明して」という説明依頼negativeを1件と、既存責務の一般positiveを1件追加してbalanceを維持します。train / validation間のquery重複は禁止します。

`.github/workflows/validate-skills.yml`は上表のSkill別exact count、positive / negative exact count、repository合計328を検証します。`EVALS.md`へ新規query IDと責務境界の対応を記録します。
## 8. qa-workflow統合評価

次の9シナリオをE2E fixture / smokeとして検証します。

1. 新規設計
   - test-analysisで技法選択
   - model作成
   - runtime生成
   - CI / TC
   - coverage-analysis
   - workflow完了

2. 上流Authority変更
   - upstream Entity content fingerprint変更
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
   - `question-analysis`往復で`runtime_unit_key / model_key / target_key`維持
   - 独立modelは継続
   - 成果物metadataから状態を再構築し、qa-workflow出力時は既存Skill状態表と新しいruntime状態表へ反映
   - workflowは部分完了

5. runtime fallback / unavailable
   - 対応subset外は`runtime_required=false / runtime_status=not_run / result_status=ready / deterministic_generated=false / fallback_reason=outside_supported_subset`でLLM fallbackし、既存Skill契約を満たせば完了可能
   - supported inputで`runtime_required=false`にした成果物はvalidator失敗
   - supported inputでPython unavailableなら`runtime_required=true / runtime_status=not_run / deterministic_generated=false`を保持し、workflowを完了にしない
   - QA成果物状態とruntime状態を分離
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
   - `Selection Source=user`をmodel metadataへ保持
   - `test-analysis`の技法選択行を作るためだけに上流へ戻らない

9. 実Agent runtime smoke
   - CIだけではLLMが実際にscriptを起動したことまでは証明しない
   - 実装完了前にAgent環境で`test-analysis`と`test-condition-design`の代表promptを各1件実行する
   - command / script path、return code、stdout envelopeが確認できる実行logをPRの検証記録へ残す
   - runtime適用可能なpromptで`deterministic_generated=true`になることを確認する

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

`.github/workflows/validate-skills.yml`のrepository eval structureは次へ変更します。

- trigger dataset: 上記Skill別exact countとpositive / negative exact countを検証
- total trigger query: 328
- train / validation disjointを維持
- semantic dataset: `test-analysis=7 / test-condition-design=7 / adversarial-review=8 / その他=2`、repository合計44を検証

`validate-skills.yml`へruntime unit testを重複追加しません。runtime testは`deterministic-output-evals.yml`だけで実行します。

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
- runtime dependencyがPython 3.11標準ライブラリだけで、外部package manifestを必要としない
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

- `assets/output-template.md`のカバレッジ基準確認・カバレッジ項目の扱い・陳腐化 / 孤立分析へ`Model Key`列を追加
- stale / fingerprint / test-design traceability
- model_key単位のgap / stale参照
- deterministic validatorでModel Keyの既知model照合を追加

### `question-analysis`

- `不明点 / 質問一覧`と`ブロック中範囲`へ`Model Key / Target Key`列を追加
- runtime issueの`runtime_unit_key / model_key / target_key`を質問・ブロック・再開まで保持
- `再開対象 / 実行範囲`へmodel keyを流用せず、既存`QUESTION-D017`契約を維持

### `qa-workflow`

- 既存Skill状態表を維持し、別表`runtime状態`を追加
- model単位状態を成果物metadataから再構築
- legacy昇格
- upstream Entity別content fingerprint / stale伝播
- 完了条件

### `EVALS.md` / `ASSERTIONS.md`

新契約と独立評価を記録します。

## 12. 実装順序

### Step 0: 基準再確認

- main最新
- 関連Skill / validator / CI
- branch差分

### Step 1: 共通runtime契約

- stdin / stdout / cwd非依存のCLI契約
- strict JSON
- output envelope / status対応表
- canonicalization
- envelope / runtime / generator contract version
- static data versions
- input / model / generation fingerprint
- upstream Entity content fingerprint
- item / byte / depth / search node hard limit
- tie-break
- structured issue / blocking
- 5 Skillの`runtime_contract.py`同一実装

### Step 2: identity / workflow基盤

- technique slugとstable model key採番
- qa-workflow再利用元による成果物系列判定
- 既存TR / TCN / TCのID再利用規則と999上限
- previous target_ref mappingを入力にしたtarget_ref → CI materialize
- upsert / stale / freshness status
- upstream Entity別content fingerprint
- question-analysisのModel / Target保持
- coverage-analysisのModel Key追跡
- qa-workflowのSkill状態表 + runtime状態表（model / artifact両runtime unit）
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
- BVA 2-value / 3-value target
- Domain Testing Reliable Domain Coverage（`< <= > >= = !=`）
- schema / HTML parser / local `$ref`
- test data requirement
- 新規技法のSkill / reference / template / eval契約

### Step 6: rule / model技法

- Decision Table / don't-care候補
- Cause-Effect
- CRUD
- Syntax-Based Testing

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

### Step 10: materialize / test-case / traceability

- `materialize_coverage.py`
- target_ref → CI mapping / upsert
- merge group union
- machine evidence描画
- case structure
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

- runtime unit / CLI integration / deterministic / semantic / workflow
- trigger datasetのSkill別exact count（repository合計328）・正負件数・境界scenario
- semantic datasetのSkill別exact count（repository合計44）と新技法case
- CI
- portability
- 実Agent runtime smoke
- README / references / templates / EVALS / ASSERTIONS

## 13. リスク

### LLMの正規化誤り

semantic evalとAuthority traceで検出し、scriptが意味を補完しません。

### 計算量

固定hard limitを使用し、超過時にCoverage基準を下げません。

### generator / validator同時誤り

helperとexpected fixtureを共有しません。

### stale成果物

model / upstream Entity content fingerprint / runtime・generator contract / static data versionsを保持し、qa-workflowで`要再検証`へ戻します。

### runtime非対応環境

runtime状態とQA成果物状態を分離します。

### 依存関係

runtime dependencyはPython 3.11標準ライブラリだけとし、実装中の外部dependency追加を認めません。正確性・hard limit・30秒timeoutを満たせない場合はPlan未達として停止します。

## 14. 完了条件

Plan完了には次をすべて満たす必要があります。

- `_01`で実装対象にした処理がruntimeまたは既存機械処理へ割り当てられている
- 目的内の技法・構造処理が本Plan外へ先送りされていない
- CLI / strict JSON / envelope / canonicalization / envelope・runtime・generator contract versionが実装済み
- upstream Entity別content fingerprint、static data versions、input / model / generation fingerprintが再現可能
- 正規化modelのMarkdown fenced JSON round-tripが成立する
- stable model key / target_ref / 成果物系列 / 既存Entity ID再利用 / previous mappingを含むCI materializeが契約どおり
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
- qa-workflowがmodel / artifact両方のruntime unit、upstream Entity内容変更、generation変更、stale、局所ブロック、runtime fallback、legacyを処理できる
- question-analysis往復でmodel / targetが失われない
- 途中工程開始と`Selection Source`が既存workflowを壊さない
- CIではruntime metadata整合を確認し、実Agent smokeで代表promptが実際にscriptを起動したことを確認できる
- 5 Skillの単体移植性が成立し、共通runtime helperの内容一致を検証できる
- trigger datasetがSkill別exact count（repository合計328）を満たし、新規技法5種のselection / design境界をtrain・validation双方で検証する
- semantic datasetがSkill別exact count（repository合計44）を満たし、test-analysis / test-condition-design / adversarial-reviewの新規技法caseがPASSする
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
