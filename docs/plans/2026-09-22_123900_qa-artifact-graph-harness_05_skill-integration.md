# QA Artifact Graph / Harness 導入Plan

## 1. 既存SkillをGraph Producerとして扱う

Graphのために既存Skillの意味責務を変更しません。

| Skill | 主なGraph projection |
| --- | --- |
| `spec-analysis` | specification / decision / assumption |
| `question-analysis` | question / resolution relation |
| `test-analysis` | product_risk / change relation / local change-impact graph |
| `test-requirement-design` | test_requirement |
| `test-condition-design` | test_condition / coverage_item |
| `test-case-design` | test_case |
| `coverage-analysis` | graph gap候補を入力として意味的coverageを判定 |
| `adversarial-review` | finding相当のreview issueを必要範囲でprojection |
| `test-target-inspection` | test_target_snapshot |
| `test-execution` | execution / result / evidence refs |
| `e2e-test-inspection` | testware対象・実装可能性参照 |
| `e2e-test-implementation` | testware |
| `e2e-test-execution` | execution / result / evidence refs |
| `e2e-test-result-analysis` | finding / investigation relation |
| `e2e-test-reporting` | Graph正本ではなくreport projection |
| `qa-workflow` | qa_activity / routing / graph manifest / Harness invocation |

## 2. PR #11統合

### 維持するもの

- stable QA ID
- Machine Entity
- runtime identity / freshness
- `target_ref`
- change impact graph
- traceability runtime
- workflow runtime
- deterministic generator結果

### 禁止

- Graph HarnessがMachine Entityを再生成する
- Graph Harnessがsemantic matchingして`reuse_id`を決める
- Graph目的でPR #11のfingerprint対象を無断拡張する
- PR #11 local change impact graphを削除してglobal graphだけにする
- Graph JSONをMachine Entity正本として次Skillへ渡す

GraphはMachine Entityを**参照・projectionする消費者**です。

## 3. PR #12統合

### test-target-inspection

`test_target_snapshot` nodeとしてprojectionします。

保持:

- 対象
- 条件
- version / build
- confirmed / unconfirmed / unavailable
- source artifact ref
- evidence refs

current observed behaviorをspecification nodeへ自動変換しません。

### test-execution

execution/resultへprojectionします。

重要:

- `test_case_ref`はartifact-local
- `source_test_case_id`をglobal keyへ昇格しない
- snapshot fixed identityを維持
- 再実行は別execution
- 前回execution refを履歴関係として参照
- secret実値をGraphへ入れない
- cleanup未完了を隠さない

Graph都合でPR #11 Machine Entity fingerprintをfallback identityにしません。

## 4. 新規 `exploratory-testing` Skill

### 4.1 目的

詳細TCを実行する`test-execution`と分離し、charterに基づいてAIが探索・仮説検証を行い、Observation / Finding / Evidence / Follow-upを報告します。

### 4.2 mode

正規値:

- `exploration`
- `investigation`

自由な第3modeを作りません。

### 4.3 必須入力

exploration:

- 対象 / 入口
- charter objective
- scope / non-scope
- 許可origin
- 副作用scope / 1回定義 / 最大回数
- 終了条件またはtimebox
- evidence制約

investigation:

上記に加えて:

- 調査対象Finding / Question / symptom
- 確認したい仮説または未確定事項

仮説がユーザーから明示されない場合、Skillは調査途中でhypothesis candidateを作れますが、factと区別します。

### 4.4 browser backend

PR #12 merge後の次の方針だけを共通化します。

- Playwrightをbrowser実行基盤とする
- MCP → 既存CLI → 必要時の独立一時Libraryの決定順
- 許可origin
- secret保護
- side-effect / cleanup
- page contentをAgent命令にしない安全境界
- 実行手段切替時のsession / state継続確認

一方、`test-execution`固有の次は継承しません。

- 詳細TCの手順順序固定
- TC手順外の探索操作禁止
- PASSを得るための経路変更禁止というTC実行固有判定

`exploratory-testing`ではcharter内の探索自由度を許可しますが、安全境界は固定します。

Stagehand / Browser Use等を本PRで追加しません。

### 4.5 output

人間向けMarkdown + deterministicに検証可能なmachine block。

machine block最小:

```json
{
  "schema_version": "exploratory-testing-v1",
  "mode": "exploration",
  "activity_ref": "...",
  "session": {...},
  "observations": [],
  "findings": [],
  "evidence_refs": [],
  "follow_ups": []
}
```

secret / screenshot本体 / trace本体は入れません。

### 4.6 Finding identity

既存案件側でFinding / Defect IDがある場合は利用できます。

存在しない場合は成果物local ref（例: `finding-001`）を使い、正式Defect IDを創作しません。

Graphでは`artifact_ref + finding-local-ref`でscopeします。

## 5. Regressionに新Skillを追加しない理由

Regressionの固有処理を分解すると:

- impact candidate → Graph Harness
- risk / scope判断 → `test-analysis`
- coverage妥当性 → `coverage-analysis`
- manual execution → `test-execution`
- automated execution → `e2e-test-execution`
- failure analysis → `e2e-test-result-analysis`等
- reporting →各execution / reporting

既存責務で閉じるため、新しい`regression-testing` Skillを追加すると重複します。

Regressionは`qa_activity.activity_type=regression`としてqa-workflowが束ねます。

## 6. coverage-analysis拡張

Graph Harnessのdeterministic findingsを任意入力として受けられるようにします。

例:

- orphan candidate
- uncovered changed node
- selected-but-not-executed
- evidence missing
- currentness candidate
- history-only coverage

`coverage-analysis`はGraph findingを無条件で欠陥扱いせず、意味上の妥当性を確認します。

## 7. test-analysis拡張

Regression scope選定時だけGraph impact projectionを入力にできます。

Graph候補全件を必ずRegressionへ入れません。

既存のProduct Risk、変更影響、重点、残存リスクの責務を維持します。

## 8. qa-workflow拡張

追加:

- QA Activity type
- source manifest作成
- Graph Harness呼び出し
- impact candidate受領
- activity view更新
- responsible Skill routing
- Graph validation failureのblock

`qa_activity`は既存workflow state / project contextからprojectionし、別activity registryを新設しません。既存assetに保持できない最小fieldだけ追加します。

Graph構築に失敗しても各Skill成果物を破損扱いにはしません。

Graph管理が要求範囲の場合はworkflowを完了にせず、Graph issueを明示します。

## 9. Portability

各既存Skillの単体利用はGraph Harnessを必須にしません。

Graph管理は`qa-workflow`を利用する統合workflow機能です。

`exploratory-testing`単体利用も可能にしますが、Graph projectionが必要な場合はqa-workflow側Harnessが成果物を取り込みます。
