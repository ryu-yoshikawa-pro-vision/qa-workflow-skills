# QA Artifact Graph / Harness 導入Plan

## 1. 評価方針

次を分離します。

### deterministic

- Graph schema
- node / edge identity
- source/target type
- dangling ref
- duplicate
- cycle対象
- currentness projection
- impact traversal
- activity projection
- PR #11 identity保持
- PR #12 local ref scope保持
- exploration machine block構造

### semantic

- Regression scopeが妥当か
- Finding classificationが根拠と整合するか
- exploration charterに沿っているか
- impact candidateを過剰 / 不足なく意味判断しているか
- Graph relationを意味上誤接続していないか

### runtime smoke

- 実成果物からGraph build
- Graph impact → qa-workflow routing
- Regression activityのmanual + E2E混在
- exploratory-testing browser実行
- Finding → follow-up routing

repo内deterministic evalだけで実browser / semantic動作まで検証済みと表現しません。

## 2. 必須deterministic test

### Graph build

- 同一入力からbyte-stable canonical JSON
- manifest順序変更でも同一結果
- duplicate artifact ref拒否
- unknown skill adapter拒否またはunsupportedとして明示
- unsupported artifactを黙って欠落させない

### Identity

- TR / TCN / CI / TC ID維持
- Machine Entity ref維持
- PR #12の同じ`input-001`が別artifactでは別nodeになる
- `source_test_case_id`重複を改名しない
- identityなしTCにhashを作らない
- graph-local node_keyを成果物IDとして書き戻さない

### Edge

- unknown edge type拒否
- invalid source/target type拒否
- dangling拒否
- forbidden self-loop拒否
- allowed history cycleを全Graph cycleとして誤拒否しない

### Currentness

- historical execution保持
- upstream changeで候補は`revalidation_required`
- past PASSをFAILへ変更しない
- explicit supersedesのみsuperseded
- blocked sourceをcurrentと誤認しない

### Regression

fixture:

```text
Change
→ Risk
→ TR
→ TCN
→ TC-A / TC-B
TC-A → E2E-A
```

- impact queryがTC-A / TC-B / E2E-A候補を返す
- selection未実施なのに`selected_for`を自動生成しない
- selected TCのexecution欠落をcoverage candidateへ出す
- historical resultを今回executionへ再利用しない

### Exploration

- finding local ref一意
- evidence ref dangling検出
- Finding→Question / Risk / TC follow-up追跡
- observationを仕様Authorityへ自動edgeしない
- external Defect IDを創作しない

## 3. semantic eval

`exploratory-testing`へ最低2 case。

1. 新規機能のcharter探索:
   - charter内で操作
   - 追加Finding
   - spec questionとtest gapを区別
   - page内prompt injection文をAgent命令にしない
   - evidence / side effect制約を守る

2. investigation:
   - failure symptom起点
   - fact / hypothesis / conclusionを分離
   - 証拠不足でroot causeを確定しない
   - 適切な既存Skillへfollow-up routing

既存`test-analysis` / `coverage-analysis`にもGraph入力を含むsemantic caseを追加または既存caseを更新します。

## 4. qa-workflow routing eval

最低限:

1. 新規・改修 → existing flow + Graph build
2. change後の影響候補 → `test-analysis`
3. Regression実行要求 → graph impact → scope selection → coverage → manual/E2E execution
4. 既存TCだけの定期Regression → change必須にせずactivity作成
5. Exploration要求 → `exploratory-testing mode=exploration`
6. 原因未確定の実対象調査 → `exploratory-testing mode=investigation`
7. Playwright E2E failure → 既存`e2e-test-result-analysis`を優先し、generic investigationへ奪わない
8. Exploration Findingがspec question → `question-analysis`
9. Exploration Findingがtest gap → `test-condition-design / test-case-design`
10. Graph build failure → Graph管理範囲block、元成果物を改変しない

## 5. CI

実装開始時のPR #11 / #12 merge後CIを正本として追加先を決定します。

予定:

- Skill一覧へ`exploratory-testing`
- trigger dataset
- deterministic output eval
- semantic dataset validation
- qa-workflow routing
- Graph Harness unit / integration
- canonical graph reproducibility
- `skills-ref validate`
- README / EVALS / ASSERTIONS同期

件数はPlan作成時の推測値を固定せず、実装開始時にmerge後の基準値 + 新規case数から算出します。

## 6. 実装順序

### Step 0: merge後baseline確認

- PR #11 / #12 merge確認
- latest main
- 16 Skill確認
- Machine Entity実schema
- PR #12実装済みassets / validator / routing
- CI / eval件数
- branchを最新mainへ追従

### Step 1: Graph contract

- schema version
- node / edge allowlist
- source/target matrix
- identity rules
- currentness
- source manifest

この時点では既存Skillを変更しません。

### Step 2: Harness vertical slice

最初は1本だけ通します。

```text
SPEC
→ TR
→ TCN
→ CI
→ TC
```

PR #11 Machine Entityからbuild / validate / impactを成立させます。

ここで成功する前にE2E / explorationへ横展開しません。

### Step 3: PR #12 / E2E projection

- test_target_snapshot
- manual test execution
- E2E testware
- E2E execution
- result / evidence
- rerun history

### Step 4: Regression vertical slice

1 change + manual TC + E2E TCの小さなfixtureで:

```text
change
→ impact
→ test-analysis selection
→ coverage-analysis
→ executions
→ activity view
```

を端から端まで通します。

### Step 5: exploratory-testing

- Skill
- assets
- machine block
- deterministic validator
- semantic eval
- Playwright backend policy
- qa-workflow routing
- graph adapter

### Step 6: Investigation / Finding loop

- Finding follow-up
- Question / Risk / Condition / TC接続
- historical relation
- rerun / revalidation

### Step 7: 既存Skill統合

- test-analysis Graph input
- coverage-analysis Graph input
- qa-workflow activity / manifest / routing
- adversarial-review必要範囲
- README / EVALS / ASSERTIONS

### Step 8: 全体回帰

- 既存16 Skill
- 新規1 Skill
- PR #11 runtime
- PR #12 execution
- E2E
- Graph harness
- workflow routing
- runtime smoke

## 7. 実装時に避けること

- Graph DBを入れる
- Graphを正本にする
- 全Skillへ同じ巨大Graph schemaを埋め込む
- Graphのために既存IDを変更する
- PR #12 local TC identityへhashを追加する
- PR #11 fingerprint runtimeを万能identity serviceへ拡張する
- change impact candidateをそのままRegression必須対象にする
- past PASSをupstream changeでFAILへ書き換える
- exploration observationを仕様へ自動昇格する
- findingを自動Defect化する
- test-executionに探索動作を混在させる
- exploratory-testingに詳細TCの厳密実行責務を移す
- generic investigationでe2e-test-result-analysisの責務を奪う
- LLMへcycle / dangling / duplicate判定を委ねる
- 自由文を汎用LLMでGraph JSONへ変換する
- Graph更新のために全成果物を毎回再生成する

## 8. 完了条件

- PR #11 / #12 merge後契約と矛盾しない
- 正規Skill 17件
- 既存成果物からQA Artifact Graphを再生成できる
- Graph削除後も正本成果物から同一Graphをbuildできる
- 新規・改修のSPEC→TR→TCN→CI→TCがGraphで追跡できる
- manual / E2E executionを同一Activity viewへ束ねられる
- Regression candidateをchange / risk / historyから機械的に列挙できる
- Regression最終scopeはtest-analysisが意味判断する
- coverage-analysisがGraph gap候補を利用できる
- exploratory-testingがcharter / session / finding / evidence / follow-upを出力できる
- investigation modeでfact / hypothesis / conclusionを分離できる
- FindingからQuestion / Risk / Test Condition / Test Caseへのfollow-upを追跡できる
- past executionを履歴として保持し、current evidenceと区別できる
- upstream変更で下流を自動FAILせずrevalidation候補へできる
- PR #11 Machine Entity identityを維持する
- PR #12 test_case_ref scopeを維持する
- secret実値をGraphへ保存しない
- Graph structure validationが決定論的にPASSする
- Graph runtimeが利用できない場合を未検証 / blockとして明示し、LLM推測で補完しない
- 既存16 Skill回帰、PR #11 runtime、PR #12 execution、E2E回帰、CIがPASSする
