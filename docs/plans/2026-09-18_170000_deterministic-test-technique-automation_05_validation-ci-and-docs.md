# テスト分析・テスト技法の決定論的自動化Plan

このファイルはvalidator、semantic eval、CI、文書更新をまとめます。[unit test・必須回帰](./2026-09-18_170000_deterministic-test-technique-automation_05_evaluation-ci-implementation-order.md)から続けて参照します。

## 6. 既存validatorの更新

### 共通ID

CIの完全IDは`TCN-\d{3}-CI\d{2,}`だけを認識します。suffix `CI\d{2,}`は同一TCN内の採番比較にだけ使用し、state / mapping / Machine Entity / legacy inputへsuffix単独を保存しません。`SPEC-001-CI01`等を誤認しません。

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

`assets/output-template.md`の`不明点 / 質問一覧`と`ブロック中範囲`へ、既存の`再開対象 / 実行範囲`とは別に`Runtime Skill`、`Runtime Unit Key`、`Model Key`、`Target Key`、`Generation Fingerprint`列を追加します。

- `再開対象 / 実行範囲`は既存`QUESTION-D017`のSkill用途判定だけに使用する
- `Runtime Skill`と`Runtime Unit Key`はruntime issue由来の質問で必須で、組を一意identityとして扱う
- model issueでは`Model Key`を必須、artifact全体script issueでは空欄
- target固有issueだけ`Target Key`を必須
- canonical input確定後のruntime issueでは`Generation Fingerprint`を必須にする。pre-parse error / timeout等でgenerationを確定できないissueだけ空欄を許可する。`question-analysis`自身はgenerationを計算せず、回答を再開先へ渡す前に`qa-workflow`の再開preflightで現在generationとの一致を確認する
- 同じブロッカーIDについて質問一覧とブロック中範囲のRuntime Skill / Runtime Unit / Model / Target / Generation Fingerprintが一致することをvalidatorで確認する
- runtime issue由来でない質問では5列を空欄にできる

runtime issueへの回答を再開する場合は、回答を正規化modelへ適用する前に次の順序を固定します。

1. 保存済み回答をまだ適用せず、現在のMachine Entity / semantic dependencyと、質問発生時点の未解決inputから対象runtime unitを再実行する
2. 再実行したcurrent `generation_fingerprint`と質問行の`Generation Fingerprint`を比較する
3. 一致する場合だけ保存済み回答を担当Skillの意味入力へ適用し、その回答を含む正規化inputでruntimeを再実行する
4. 不一致なら旧回答を自動適用せず、現在世代でissueが残るかを再評価して質問 / block状態を更新する
5. pre-parse error / timeout由来でfingerprintが空欄の場合は世代一致による回答再利用をせず、現在inputからissueを再評価する

### `qa-workflow`

既存Skill契約どおり、Skill状態表はワークフロー状態を明示する必要がある場合だけ表示します。通常出力の必須要件には変更しません。既存canonical deterministic evalでは状態表を検証するfixtureに対する`WF-D009`を維持しますが、一般のSkill出力へ拡張しません。状態表は永続正本にせず、成果物metadataから再構築可能にします。

`assets/workflow-state-template.md`へ、状態表示を行う場合に既存Skill状態表と併記する別表`runtime状態`を追加します。これは人間向け表示だけです。`workflow_runtime.py`がdispatchされた場合の`Machine Runtime Input / Result`は`qa-workflow`の最終出力契約として状態表と独立に必須保存し、状態表を省略した正常出力でもmachine evidenceを残します。

`Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue`

- `Runtime Unit Key`は同一Skill内一意
- model scriptではModel Key必須、artifact全体scriptでは空欄
- `Support Status = supported / partial / unsupported / unknown`
- `Result Status = ready / unresolved / blocked`
- `Freshness = current / stale`
- `Runtime Status = ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run`
- `Runtime Required / Deterministic Generated = Yes / No`
- `Fallback Reason`は空欄 / `outside_supported_subset` / `python_unavailable`
- Skill状態表を表示するfixtureでは`WF-D012`を従来どおりSkill + 対象にだけ適用し、runtime状態表へ流用しない
- `workflow_runtime.py`をdispatchするfixtureでは、Skill状態表 / runtime状態表を省略しても`Machine Runtime Input / Result`が存在すればvalidとし、同じfixtureからworkflow runtime evidenceだけを削除した場合はinvalidとする
- ワークフロー全体`完了`では全runtime unitが`Result Status=ready / Freshness=current`であることを追加検査する
- `Runtime Required=Yes`のunitでは、さらに`Deterministic Generated=Yes`を要求する
- `Runtime Required=No`のfallback unitも`Result Status != ready`なら完了を妨げる
- `Support Status=partial`では`unsupported_items[]`が許可されたhandling、必要なcurrent`covered_by_entity`、既存Disposition条件を満たすclosureへすべて閉じていることを要求する。closure行の存在だけでは完了条件を満たさない
- `workflow_runtime.py`が上流Entity fingerprint、`upstream_runtime_units`、runtime metadata、materialize runtime unitの`model_completion[] / target_mappings[] / target_dispositions[]`、`unsupported_item_closures[]`からstale / 完了可否を計算し、LLMが表を手計算しない
- partial supportは全unsupported item keyにclosureがあり、closureの`generation_fingerprint / reason_code`が現在unsupported itemと一致することに加え、`handling`が許可集合内であることを要求する。同じ`(skill,runtime_unit_key,generation_fingerprint,item_key)`のclosureはちょうど1件とし、duplicateを拒否する。通常Coverage modelの`llm_fallback`は同じ`model_key`に属するcurrent CI Machine Entityを必須にする。internal adapterのpartialではunsupported itemの`affected_technique_slug`と同じtechniqueの直接定義Coverage model / current CIだけを許可し、同じsourceが複数techniqueへ影響する場合はitemがtechnique単位に分かれていることを要求する。adapter自身・無関係TCN / technique・stale CIを拒否する。`重複`はcurrentな`covered_by_entity`を必須にし、`ブロック中`は完了不可、その他Dispositionは既存Skill条件を満たすことを検証する。whole-model unsupportedは同じ`(skill,runtime_unit_key,generation_fingerprint)`でclosureをちょうど1件とし、activeのまま残る各selected child techniqueがcurrent direct Coverage model / CIまたは既存Disposition closureへ到達することを必須にする。target Dispositionの`重複`は全materialize unitを跨いでcycleがなく、current CI / semantic CIへ到達する場合だけ閉鎖済みに数える

完了条件・再利用条件へ次を追加します。

- envelope / runtime / generator contract version
- upstream Entity別content fingerprint
- input / model / generation fingerprint
- stale派生成果物
- runtime unit単位の`要再検証` / ブロック中
- runtime未実行 / unsupportedとQA成果物状態の分離
- legacy成果物の昇格
### output eval fixture schema

runtime対応Skillの`evals/output/cases/*/expected.json`では、既存fieldに加えて必要なcaseだけ次の`runtime_contract` objectを持てるようにします。Machine Entityを持つSkillではruntime有無にかかわらず`machine_entities` objectも使用できます。

```json
{
  "machine_entities": {
    "expected_entities": [
      {"skill":"test-condition-design","entity_type":"tcn","entity_ref":"TCN-001"},
      {"skill":"test-condition-design","entity_type":"ci","entity_ref":"TCN-001-CI01"}
    ],
    "expected_stale_entities": []
  },
  "runtime_contract": {
    "expected_runtime_units": [
      {"skill":"test-condition-design","runtime_unit_key":"artifact:condition_structure:all"},
      {"skill":"test-condition-design","runtime_unit_key":"model:comb-001"},
      {"skill":"test-condition-design","runtime_unit_key":"artifact:materialize_coverage:TCN-001"}
    ],
    "expected_skill": "test-condition-design",
    "expected_runtime_unit_key": "model:comb-001",
    "upstream_entities": [
      {"skill":"spec-analysis","entity_type":"authority","entity_ref":"SPEC-001","content_fingerprint":"sha256:..."}
    ],
    "expected_target_keys": [],
    "expected_support_status": "supported",
    "expected_runtime_status": "ok",
    "expected_result_status": "ready",
    "expected_runtime_required": true,
    "expected_deterministic_generated": true,
    "expected_fallback_reason": null,
    "expected_freshness_status": "current",
    "expected_target_id_map": [],
    "expected_model_completion": []
  }
}
```

- `machine_entities.expected_entities[]`は各Skillの固定builderがnormalized source / structure stateから導出した`(skill, entity_type, entity_ref)`をfixtureへ明示し、actual成果物のMachine Entity集合から逆算しない。validatorはactual identity集合とのmissing / extraと、各contentのentity type別canonical schema・人間向け表主要fieldを独立照合する
- `runtime_contract.expected_runtime_units[]`はvalidator fixtureではstandalone Skillのcanonical normalized inputと検証済みstructure / adapter parent resultから固定builderが段階的に導出した`(skill, runtime_unit_key)`を明示する。productionの`verify_runtime_evidence`も完成済みexpected集合を入力せず同じ導出順を使用する。validatorは成果物中の`Machine Runtime Input / Result` block identity集合と完全一致を要求し、必須runtime blockの丸ごと欠落と未知の余分なblockを検出する。actual runtime block集合からexpectedを逆算しない
- standalone direct fixtureで必須runtime blockを1件削除したnegative caseを各代表Skillに置き、`qa-workflow`を通さなくても成果物を完成扱いしないことを確認する
- 同じcandidate artifactへproduction側`runtime_contract.py`の`verify_runtime_evidence` operationを実行し、validatorとは独立にruntime blockのmissing / extra / incomplete pair / duplicateとMachine Entityのmissing / extra / duplicateを検出できることを確認する。partial rerunでは検証済みprevious Machine Entityからscope外expected identityを導出し、actual candidate集合からexpectedを逆算しない。deterministic validatorがPASS判定の唯一の省略検出経路にならない。operationは集約stdin 16 MiB上限を使い、JSON escape後の実UTF-8 bytesで境界値と1 byte超過を検証する
- `spec-analysis`では`runtime_contract.py`のcanonical / Machine Entity helperと`authority_entities.py`を使うfixtureを用意し、runtime unitを作らずAuthority表とcanonical Authority content / expected identityの一致を検証する
- expected target / Coverageは手書きfixtureから独立計算または明示し、generator出力をexpectedへコピーしない
- `expected_target_id_map`はstateful materialize caseだけ使用し、`{target_ref, target_content_fingerprint, generation_fingerprint, execution_fingerprint, model_key, target_key, ci_id}`配列で保持する
- `expected_model_completion`はmaterialize / workflow integration caseで使用し、modelごとの`required_target_refs / closed_target_refs / active_ci_ids / semantic_item_keys / materialize_complete`を手書きfixtureから明示する。runtime出力をexpectedへコピーしない
- validatorは全runtime unitの保存済み`Machine Runtime Input / Result`から`input_fingerprint`、model scriptでは`model_fingerprint`、全scriptで`generation_fingerprint`を独立再計算し、fixtureに書いたhash文字列を盲信しない
- upstream Entity差分caseでは無関係Entityの変更が対象modelをstaleにしないことを確認する
- upstream runtime差分caseでは直接依存unitだけがstaleになり、依存していないmodelへ伝播しないことを確認する
- implementation fingerprintはruntime / generator sourceから独立再計算し、fixtureの文字列を盲信しない
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
- `test-case-design`がCI Machine Entityのcanonical `execution`または`semantic_item_text`を入力として具体TCへ展開し、generator内部modelやMarkdown Coverage Item表を再解釈せず、Authorityにないexpected resultを追加していない

semantic referenceをgenerator outputから自動生成しません。

CIの`Validate Semantic Output Evals`は既存契約どおり外部LLM APIを呼ばず、dataset / rubric / semantic runtime / fake judge contractを検証します。このCI成功だけをsemantic case PASSとは扱いません。

Plan完了時は、`test-analysis / test-condition-design / test-case-design / adversarial-review`の本Planで追加・更新したsemantic caseについて、保存済みcandidate outputを用意し、既存`scripts/skills/evals/semantic/run.py`へそのprotocolに適合する外部Judge commandを接続して実評価します。特定provider用の新しいJudge adapterは本Planの実装対象にしません。candidate output生成、Judge実行command、Judge結果をPRの検証記録へ残します。Judgeを利用できない場合はsemantic dataset validationまでは実施できますが、semantic case PASSの完了条件は未達としてPRをDraftのままにします。CIへ外部LLM secretやJudge実行を追加しません。

### semantic dataset件数

semantic dataset件数は次で固定します。

| Skill | case数 |
| --- | ---: |
| `test-analysis` | 7 |
| `test-condition-design` | 14 |
| `adversarial-review` | 8 |
| その他11 Skill（`test-case-design`を含む） | 各2 |
| repository合計 | 51 |

- `test-analysis`: 既存2 caseを維持し、Domain / CRUD / Random / Metamorphic / Syntax-Basedの採用判断を主対象とする5 caseを追加する
- `test-condition-design`: 既存2 caseを維持し、Domain / CRUD / Random / Metamorphic / Syntax-Basedに加え、Decision Table / Cause-Effect、Classification Tree / combinatorial strength、Round-trip / n-switch、flow、schema / OpenAPI、UI pattern、test data / environment、merge / Coverage範囲の意味判断を各caseで最低1回検証できるよう合計14 caseへする。1 caseで複数責務を検証してよいが、各責務とcase IDの対応表を`EVALS.md`へ記録する
- `test-case-design`: case数は既存2件のまま維持し、そのうち1件を本PlanのCI Machine Entity入力へ更新する。入力にはcanonical `execution`または`semantic_item_text`、Authority、current environment / test data requirementを含め、具体的な前提・データ・手順・期待結果へ正しく展開できること、generator内部modelを再解釈しないこと、Authorityにないexpected resultを追加しないことを評価する
- `adversarial-review`: 既存2 caseを維持し、下記6誤用を主対象とする6 caseを追加する
- case IDはSkill内一意
- `tests/skills/evals/semantic/test_semantic_datasets.py`はSkill別expected count mapと合計51を検証し、`EVALS.md`の意味判断責務→case対応が空になっていないこともrepository testで確認する

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

さらに`test-analysis` / `test-condition-design`の各datasetへ、それぞれ「技法とは何か説明して」という説明依頼negativeを1件と、既存責務の一般positiveを1件追加してbalanceを維持します。その他12 Skillの件数は変更しません。train / validation間のquery重複は禁止します。

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

2. 上流Authority / runtime変更
   - upstream Entity content fingerprint変更
   - runtime `generation_fingerprint`へupstream Entity fingerprintが含まれ、同じAuthority IDでも内容変更で別generationになる
   - 保存済みsemantic model / draftの`upstream_entity_dependencies[]`不一致をruntime再実行前に検出し、担当Skillで意味再確認するまで古い入力を再投入しない
   - Machine Entityのupstream / runtime dependencyからEntity freshnessがstaleになり、`traceability.py`と`workflow_runtime.py`で同じ結果になる
   - 人間向け説明文だけの変更ではfingerprint不変
   - 直接依存する上流runtime unitのgeneration fingerprint変更
   - 影響modelと依存下流unitだけ`要再検証`
   - 無関係modelへstaleを伝播しない
   - stale派生物を拒否
   - 再生成後に再利用可能

3. model / generator変更
   - model意味変更で`model_fingerprint`変更
   - generator contract / static data / generator implementation変更で`generation_fingerprint`変更
   - contractを変えないbug fixでもimplementation fingerprint差で旧machine evidenceを再利用しない
   - 旧machine evidence拒否

4. 局所ブロック
   - 1 modelだけ未解決
   - `question-analysis`往復で`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`維持
   - 質問後にgenerationが変わった場合は以前の回答を自動適用せず、現在世代でissueが残るか再評価する
   - 独立modelは継続
   - 成果物metadataから状態を再構築し、qa-workflowが状態表示を行う場合だけ既存Skill状態表と新しいruntime状態表へ反映する。表を省略しても完了判定は変わらない
   - workflowは部分完了

5. runtime support / fallback / unavailable
   - model全体が対応subset外ならscript自身が`support_status=unsupported / runtime_status=unsupported / runtime_required=false / deterministic_generated=false / fallback_reason=outside_supported_subset`を返し、既存Skill契約を満たすLLM fallbackで完了可能
   - 既存fallback成果物を再利用するときも現在runtimeでsupport判定を再実行し、runtime更新でsupportedになったfixtureを古いfallbackへ固定しない
   - 一部subset外なら`support_status=partial`でsupported部分を生成し、unsupported itemをfallback / Dispositionへ閉じるまで完了不可
   - `runtime_required`をcaller inputから与えず、runtimeのsupport判定出力として検証する
   - Python unavailableなら`support_status=unknown / runtime_required=true / runtime_status=not_run / result_status=blocked / deterministic_generated=false`を保持し、workflowを完了にしない
   - QA成果物状態とruntime状態を分離
   - 「決定論的生成済み」と誤表示しない

6. legacy成果物
   - 旧成果物を参照
   - 初回昇格時は`input_mode=direct`かつnormal previous stateが空の場合だけ、`legacy_tr_ids[] / legacy_tcn_ids[] / legacy_tc_ids[]`を各structure script自身がactive previous stateへseedする。Agent / LLMがprevious stateを手組みしない
   - 現在観測できるTR / TCN / CI / TCだけをactive seedとして取り込み、未知の過去deleted履歴を捏造しない
   - TR / TCN / TCは意味上同一なら既存IDをreuseし、model keyがlegacyに存在しなければ新規採番する
   - CIは各TCNの全既存IDをそのTCNの`legacy_ci_ids[]`でprevious stateへseedし、そのsubsetの`legacy_ci_seed[]`だけをcurrent target / semantic itemへ対応付ける。対応不能CIも同TCNの番号rowをfull snapshotへ残して別CIへ再利用せず、参照TCは`要再検証`へする
   - normal previous state生成後のlegacy入力再投入、legacy / normal state併用、unknown / duplicate / 別TCN / 別model seedを拒否する
   - 前工程Machine Entityが存在しないdirect由来境界は新契約保存後もdirectで再利用でき、必要な外部Machine Entityがすべて揃った時点だけartifactへ切り替える
   - 以後version / fingerprint / normal previous state契約で再利用

7. runtime利用確認
   - 正規化済み`input / model_type / 対象 / 実行範囲`からscript選択表へ入った後のdispatchはunit fixtureで全runtime scriptを網羅し、期待script path・必須/条件付き・実行順とCLI実行結果metadataを検証する
   - 自然言語promptからSkill責務・意味入力を決める部分はPython dispatch testへ実装せず、既存trigger eval / semantic evalと代表Agent smokeで検証する。dispatch検証専用のprompt parserや重複manifestを新設しない
   - `test-analysis: E2E対象選定`と`coverage-analysis: TC → E2E実装 / E2E実装 → 実行結果`では本Planruntimeをdispatchしない
   - canonical workflow scopeに本Planruntime対象scopeが0件のE2E-only `qa-workflow`では`workflow_runtime.py`をdispatchせず、Python unavailableでも本Plan追加を理由に`blocked`へ変更しない。既存`qa-workflow`の開始・完了条件だけで判定する回帰fixtureを追加する
   - テスト設計runtimeとE2E実装・実行を同時に要求する混在workflowでは、`workflow_runtime.py`の`can_complete=true`でもE2E側の既存完了条件が未達ならworkflow全体を`完了`にしない。逆に既存workflow条件を満たしても`workflow_runtime.py`がdispatch済みで`can_complete=false`なら完了にしない
   - supported inputが`unsupported`になる、またはsupport判定前にAgentがscriptを省略する場合は失敗
   - 保存済み`Machine Runtime Input / Result`を決定論的に抽出してround-trip検証できるが、workflow再利用では保存済みresultをcurrent cacheにせず現在scriptを再実行する
   - LLM手計算だけの成果物を決定論的生成済みと判定しない
   - internal adapterがpartialになり`llm_fallback`を選ぶfixtureでは、同じsourceがEP / BVA等の複数child techniqueへ影響するcaseを含め、`affected_technique_slug`ごとにunsupported itemを分割し、各itemを同techniqueの直接定義Coverage model / current CIへ閉じる。whole-model unsupportedではactiveのまま残すselected child techniqueすべてにdirect Coverage model / CIまたは既存Disposition closureがあることを要求する。adapter自身のCI、無関係TCN / technique、stale CI、selected technique欠落を拒否する

8. 途中工程開始
   - 前工程のMachine Entityがない直接入力では`input_mode=direct`を使用し、ユーザーが技法を明示したTRから`test-condition-design`を開始して`Selection Source=user`をmodel metadataへ保持する。存在しない`test-analysis / test-requirement-design` Machine Entityを捏造しない
   - 同じfixtureを`test-condition-design` Skill directory単体でも実行し、repo root helperや前工程Skill directoryなしで正規化input → runtime → Machine Entity保存まで成立することを確認する
   - ユーザー明示がなくても`test-condition-design`自身が問題構造から技法を選べる正常経路を`Selection Source=condition_design`で検証する
   - 既存Machine Entity付き成果物を再利用する経路では`input_mode=artifact`を使用し、元のSelection Source / selection keyを維持する。reuseを別のSelection Sourceへ置き換えない
   - legacy昇格は初回`input_mode=direct`とし、新契約のMachine Entity保存後も必要な前工程Machine Entityが存在しない境界はdirectで再利用する。必要な外部Machine Entityがすべてcurrentになった場合だけartifactへ切り替える
   - `test-analysis`の技法選択行を作るためだけに上流へ戻らない

9. 実Agent runtime smoke
   - 全scriptのdispatch網羅はCIで保証し、実Agent smokeを全script分へ重複させない
   - 実装完了前にAgent環境で`test-analysis`と`test-condition-design`の代表promptを各1件実行し、Python runtime起動、stdout envelope parse、machine result採用、Markdown保存・再読込まで確認する
   - 1件は可能な範囲で大きいmachine outputも扱い、artifact transport上限がruntime 16 MiBより低くないか確認する
   - command / script path、return code、stdout envelopeが確認できる実行logをPRの検証記録へ残す
   - runtime適用可能なpromptで`deterministic_generated=true`になることを確認する

## 9. CI

既存`.github/workflows/deterministic-output-evals.yml`へ追加します。

```bash
python -m compileall -q skills/spec-analysis/scripts
python -m compileall -q skills/test-analysis/scripts
python -m compileall -q skills/test-requirement-design/scripts
python -m compileall -q skills/test-condition-design/scripts
python -m compileall -q skills/test-case-design/scripts
python -m compileall -q skills/coverage-analysis/scripts
python -m compileall -q skills/qa-workflow/scripts
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v
```

既存のdeterministic eval、semantic dataset validation、Skill validationも維持します。

`.github/workflows/validate-skills.yml`のrepository eval structureは次へ変更します。

- trigger dataset: 上記Skill別exact countとpositive / negative exact countを検証
- total trigger query: 328
- train / validation disjointを維持
- semantic dataset: `test-analysis=7 / test-condition-design=14 / adversarial-review=8 / その他=2`、repository合計51を検証

`validate-skills.yml`へruntime unit testを重複追加しません。runtime testは`deterministic-output-evals.yml`だけで実行します。

## 10. Skill単体移植性

runtime対象の次の6 Skillを単体コピーして代表scriptを実行します。CIではsetup済みPython 3.11 interpreterを使用し、Skill側が`python`というcommand名へ依存しないことを確認します。加えて`spec-analysis`も単体コピーし、`authority_entities.py`によるAuthority Machine Entity生成と`runtime_contract.py`のcanonical / Machine Entity helperが外部repository helperなしで動作することを検証します。

- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `qa-workflow`

確認:

- repo rootのeval helperをimportしない
- `spec-analysis`を含む7 Skillの`scripts/runtime_contract.py`がLF正規化後のSHA-256で一致
- network不要
- runtime dependencyがPython 3.11標準ライブラリだけで、外部package manifestを必要としない
- 本Planで追加するmodel generator / artifact runtimeの全scriptがSkill-local Python moduleとしてimportできるのは`runtime_contract.py`だけで、fingerprint対象外helperへ実行ロジックを逃がさない
- Skill rootからscriptを解決
- stdinへUTF-8 JSONを渡しstdout envelopeを読める。interpreterのcommand名やtimeout APIをSkill code / Skill契約へ埋め込まない
- `test-condition-design`と`test-case-design`は`input_mode=direct`の代表fixtureを前工程Skill directory / Machine Entityなしで実行できる
- runtime対象6 Skillの単体コピーで`runtime_contract.py`の`verify_runtime_evidence` operationを実行でき、repo root validator / helperなしでcandidate artifactのruntime block pairを検査できる
- `input_mode=artifact`では必要なMachine Entity missing / extraを拒否し、`direct`と`artifact`を黙って相互fallbackしない
- `authority_entities.py`が失敗またはPython unavailableの場合、Authority Machine Entity / fingerprintをLLMや別builderで代替生成せず対象範囲をblockedにする
- Python unavailable時にSkill全体を利用不能と誤判定しない
- runtime未実行を決定論的生成済みと表現しない

## 11. ドキュメント更新

### README

- LLM / runtime責務境界
- contract / static data version
- stale / legacy / 再利用
- Python 3.11要件と、interpreter command名 / timeout APIをSkill共通契約へ固定しない実行境界
- `input_mode=artifact|direct`による成果物再利用 / 途中工程開始
- Skill package内script

### `spec-analysis`

- runtime unitは追加しない
- `scripts/runtime_contract.py`と`scripts/authority_entities.py`を追加し、Authority Machine Entity / expected identityを決定論的に生成する
- `assets/output-template.md`へAuthorityの`Machine Entities` canonical JSON blockを追加する
- Authority表とMachine EntityのID / 種別 / 現在有効な内容 / 適用範囲 / 情報源 / 関係 / 関連Authorityの一致をvalidatorで確認する

### `test-analysis`

- `SKILL.md` / `references/guidance.md`へ新規正規技法と選択条件を追加
- `assets/output-template.md`へ`Machine Entities`、`Machine Runtime Input / Result`、`Selection Source`、技法選択machine evidence、current undetermined signalの`selection_not_affected / question`閉鎖状態を追加する。signal解決時は`signals`更新・candidate runtime再実行でundetermined集合から外す
- `analysis_entities.py`がtest-analysis context / Product Risk / Technique Selection / change graph / environment requirementのLLM意味fieldとcurrent runtime resultをjoinし、Machine Entity / dependency / expected Entity identityを固定生成する。Product Riskは`assessment_reason / confidence_note`も保持する
- `analysis_entities.py`はchange graph / environment → Product Risk → Technique Selection / contextの順で同一invocation内dependencyを解決し、change graph上のRisk / TR / TCN / CI / TC参照を逆向きdependencyにしてcycleを作らない
- risk scheme / priority mapping
- change graph
- environment requirement。`environment_key`ごとの代替実行環境とrequirementを人間向け出力でも追跡できるよう、key / dimension / constraint / Authorityを表示する
- deterministic / semantic / trigger evalを更新

### `test-requirement-design`

- runtime structure検査の処理順
- `assets/output-template.md`へTRの`Machine Entities`、`Machine Runtime Input / Result`、TR active / deleted ID stateとpartial rerunの`update_scope_tr_ids[]` evidenceを追加

### `test-condition-design`

- `SKILL.md`の対象技法を更新
- `references/coverage-techniques.md`へ全実装技法の適用条件、Coverageまたは終了条件を追加
- `assets/output-template.md`へTCN / model metadata / CI mappingの`Machine Entities`、`Machine Runtime Input / Result`、active / deleted ID state、`update_scope_tcn_ids[] / update_scope_model_keys[]`、stable target / CI mappingを追加
- Random / Metamorphicは一般Coverage 100%を定義しない
- runtime metadata
- test data requirement。model-wide / target-specificの適用範囲と元`requirement_key` identityを保持し、別target間の要求を早期に誤intersectionしない
- deterministic / semantic / trigger evalを更新

### `test-case-design`

- runtime structure検査の処理順
- `assets/output-template.md`へTCの`Machine Entities`、`Machine Runtime Input / Result`、TC active / deleted ID stateと`update_scope_tc_ids[]` evidenceを追加
- stable ID / active・deleted ID state / stale
- 既存semantic case 2件のうち1件をCI Machine Entityのcanonical `execution` / `semantic_item_text`入力へ更新し、generator内部modelを再読解せず具体TCへ展開する経路を評価する
- TCのmachine evidenceへpassword、token、cookie、secret値そのものを保存せず、認証方式・取得方法・環境変数名等の非secret参照だけを残す

### `coverage-analysis`

- `assets/output-template.md`へ`Machine Runtime Input / Result`を追加
- `assets/output-template.md`のカバレッジ基準確認・カバレッジ項目の扱い・陳腐化 / 孤立分析へ`Model Key`列を追加
- stale / fingerprint / test-design traceability
- model_key単位のgap / stale参照
- deterministic validatorでModel Keyの既知model照合を追加

### `question-analysis`

- `不明点 / 質問一覧`と`ブロック中範囲`へ`Runtime Skill / Runtime Unit Key / Model Key / Target Key / Generation Fingerprint`列を追加
- runtime issueの`skill / runtime_unit_key / model_key / target_key / generation_fingerprint`を質問・ブロック・再開まで保持
- `再開対象 / 実行範囲`へmodel keyを流用せず、既存`QUESTION-D017`契約を維持

### `qa-workflow`

- `qa-workflow/SKILL.md`へ、`workflow_runtime.py`をdispatchした場合は状態表示の有無にかかわらず`Machine Runtime Input / Result`を最終成果物へ保存する契約を追加する。`assets/workflow-state-template.md`は既存どおり任意の人間向け状態表示と`runtime状態`表だけを扱い、machine evidenceの唯一の保存先にしない
- `scripts/workflow_runtime.py`を追加し、runtime metadata集約、Machine Entityのupstream / runtime dependency、runtime unit fingerprint比較、runtime / Entity freshness、stale伝播、機械的完了判定をLLMから分離
- runtime dependency identityは`(skill, runtime_unit_key)`で固定する
- `workflow_runtime.py`自身を評価対象`runtime_units[]`から除外し、self dependencyを禁止する
- missing dependencyはstale + blocker、duplicate / cycleは`invalid_input`
- 既存Skill状態表の「必要な場合だけ使用」を維持し、状態表示時だけ別表`runtime状態`を追加
- model単位状態を成果物metadataから再構築
- legacy昇格。structure / materialize scriptの初回legacy seed入力とnormal previous stateへの移行まで含む
- standalone最終出力では`runtime_contract.py verify_runtime_evidence`へcurrent Skillのcanonical normalized inputとcandidate artifactだけを渡し、必須root runtimeを先に、current parent resultから条件付きdownstream runtimeを後に導出して必須runtime block pairをproduction側から検査する。完成済みexpected集合やdispatch stateをAgent / LLMから受けない。Skill / 対象 / 条件 / `model_type → generator`のdispatch metadataは同一`runtime_contract.py`内の固定dataを正本にし、別manifest / registryを追加しない
- upstream Entity別content fingerprint / Machine Entityの`upstream_entity_dependencies[] / runtime_dependencies[]` / upstream runtime dependency / stale伝播
- `traceability.py`と同じ`runtime_contract.py` freshness関数を使用し、workflow_runtime resultをtraceabilityの依存入力にしない
- `workflow_runtime.py`の`can_complete`は本Planruntime範囲の必要条件として扱い、既存`qa-workflow`全体の完了条件を置換しない
- 完了条件

### `EVALS.md` / `ASSERTIONS.md`

新契約と独立評価を記録します。

## 続き

[実装順序・リスク・完了条件](./2026-09-18_170000_deterministic-test-technique-automation_05_implementation-order-and-completion.md) に続きます。
