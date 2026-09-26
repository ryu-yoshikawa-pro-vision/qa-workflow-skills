# Regression / Exploratory Testing 統合Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みのdesign traceability、change impact、execution / result / rerun lineageを再実装せず、継続RegressionとExploratory Testingに残る責務を追加する実装計画です。

PR #13では新規`regression-testing`、`exploratory-testing`、`qa-knowledge`を追加します。加えて、複数workflowの並行実行、共有成果物の競合防止、shared environment / resourceの安全な利用契約を追加します。

「新規・改修」「Regression」「Exploration / Investigation」はQA活動全体を排他的に分類するものではありません。PR #13で責任Skillを持つ主要workflow入口として扱い、同一workflowで複数活動を組み合わせられるようにします。不具合修正では、元の不具合が直ったかを確認する修正確認と、周辺影響を確認するRegression Testingを別目的として扱います。修正確認は独立Skillや独立QA活動として追加せず、既存Skillを使うworkflow intentとして扱います。

Graphの構築自体は目的にしません。成果物・Activity・知識・workflowのprovenanceをdirect ref / revisionで追跡できることを目的とし、主要workflowはrelation indexなしで成立させます。deterministic scanで実需を満たせないことを実測した場合だけ、必要なquery向けの最小indexをその時点で設計します。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ名と既存Planファイル名は旧設計の名称を維持します。実装はPR #11 / #12 merge後の最新`main`へ追従し、両PRの実契約を再確認してから開始します。

## 主要workflow入口と責任Skill

### 新規・改修

既存Skill群がcurrentなQA設計を作ります。

```text
spec-analysis
→ question-analysis
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

既存Skill自身はRegression Suite membership、Run selection、Regression Activityを管理しません。

### Regression

新規`regression-testing`がRegression domainを担当します。

- initial baseline
- Regression Suite membership
- membership再評価
- full / selected
- selection rationale
- required execution route
- TCなし補助testware
- Regression Activity
- Run結果の集約
- Run完了判定
- Regression history

実際のmanual相当操作やE2E実行はPR #12 / E2E Skillへ委譲します。

### Exploration / Investigation

新規`exploratory-testing`が担当します。

- Charter
- Session
- Observation
- Finding
- Evidence
- Follow-up
- 既存責任Skillがない仮説駆動Investigation

### QA Knowledge

新規`qa-knowledge`が、Activity / Finding / Observation等から得た情報について、既存正本へroutingするか、継続利用するQA knowledgeとして有効化・更新・再検証・置換するかを担当します。

- existing owner routing
- residual knowledge validation
- entry create / update / revalidation / replacement
- knowledge lookup / history

仕様Authority、Product Risk、TR / TCN / CI / TC、current実対象情報そのものは既存ownerが正本化します。

### 修正確認のworkflow intent

修正確認専用Skill、専用artifact、専用stateは追加しません。

既存の有効なFAIL / 再現TCがある場合はanalysis / designをやり直さず、`test-execution` / `e2e-test-execution`でそのTCを再実行します。期待結果や再現条件を既存成果物から確定できない場合だけ、`qa-workflow`が必要な最も早い既存analysis / design Skillへ戻してcurrent TCを確定してから実行します。

```text
defect fix
├→ 既存TCで修正確認できる → executionへ直接
├→ 設計不足がある → 必要な既存analysis / design → execution
└→ 周辺影響も確認する → regression-testing
```

修正確認とRegressionは同一workflowで組み合わせられますが、修正確認自体に新しいSkill体系は作りません。

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Cross-artifact query / relation index導入判定](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [決定論的処理・履歴発見](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [QA活動の接続・修正確認・feedback](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・Run・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [regression-testing Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04b_regression-testing-skill.md)
7. [exploratory-testing Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04c_exploratory-testing-skill.md)
8. [継続QA知識・複数workflow・共有環境](./2026-09-22_123900_qa-artifact-graph-harness_04d_continuous-qa-knowledge-and-concurrency.md)
9. [qa-knowledge Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04e_qa-knowledge-skill.md)
10. [既存Skill・PR #11/#12統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
11. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. PR #11をdesign identity / traceability / change impact / freshnessの正本とし、PR #13で第二のdesign graphやcurrentness state machineを作らない。
2. PR #12 / E2Eをexecution / result / evidence / rerun lineageの正本とし、PR #13でexecution schemaを複製しない。
3. 新規・改修Skillはcurrent QA設計を作る責務に留める。Regression固有のmembership / Run selection / Activity管理を追加しない。
4. `test-analysis`は変更影響候補とProduct Risk等を分析する。既存Suiteから今回実行するTCを確定するRegression Run selectionは`regression-testing`が担当する。
5. `qa-workflow`は活動間のrouting、共通workflow state、blocked / resume、複合workflowのオーケストレーションを担当し、Regression固有の意味判断を再実装しない。
6. baseline更新・Run selection・history参照等の単独要求は`regression-testing`から開始できる。manual / E2E実行まで含むend-to-end Regressionは`qa-workflow`が`regression-testing`とexecution Skillを接続する。
7. 修正確認は独立Skill / 独立artifactにせずworkflow intentとして扱う。既存の有効なTCがあればexecution Skillへ直接routingし、設計不足がある場合だけ必要な既存analysis / design Skillへ戻る。周辺影響の確認は別に`regression-testing`が担当する。
8. Regression運用中のprojectでmembership入力が変わった場合、古いbaselineをcurrent扱いしない。変更時handoffに加え、各Run開始前にsource ref / revisionとcurrent stateを照合して必要なreconciliationを行う。
9. initial baselineはauthoritative TC discovery snapshotを固定してからmembershipを処理する。TC数が多い場合はdeterministicに分割・再開でき、全件が閉じるまで`complete=false`とする。
10. TC discoveryの完全性、PR #11 lifecycleへ解決できるか、test basisからのcoverageが閉じるかは別々に判定する。legacy TCを発見しただけでinventory欠落扱いにせず、currentnessを判定できない場合はbaseline completeを成立させない。
11. Regression Suiteは全current TCの保管庫ではなく、current Regression対象範囲を継続的に検証するlogical TCの基準集合とする。current TCとpersistしたmembership判断から再構成できる場合は派生viewを優先する。
12. `coverage-analysis`はRegressionの判断主体にせず、Regression対象範囲→TC、TC→E2E実装等の意味上coverageを検証する。
13. required execution routeは「何を実行する必要があるか」だけを表し、manualと具体的E2E testware refの組合せで構成する。`未実行` / `blocked`はrouteではなく実行状態として分離する。
14. execution artifactの存在だけでexecutedと判断しない。PR #12 / E2Eのsource execution契約上、実際に開始されたことを確認してexecutedを集計する。
15. Suite completeness、Run scope、executed / unexecuted、source resultのPASS / FAIL / 判定不能等を分離する。Regression Activityはsource resultを再判定せずrefと確認済み状態を投影する。
16. `regression-testing`のresidual riskはcurrent Product Risk等を再採点せず、excluded / blocked / unexecuted / coverage gapによって残る既存Riskへの影響を示す。新しいRisk identification / scoringは`test-analysis`へ戻す。
17. Regression中のFAIL / Findingでworkflowを終了しない。証拠に応じて既存責任Skillまたは`exploratory-testing(mode=investigation)`へroutingし、修正後の既知TC再実行による修正確認と、必要なRegression再評価 / rerunへつなぐ。
18. `exploratory-testing`はCharter / Session / Observation / Finding / Follow-up、block / resume / completion、安全・cleanupを明示的な契約として持つ。`investigation`は別Skill / 別runtimeにせず、symptom / hypothesisを起点にする同じSession契約として扱う。
19. Activity stateの正規値は既存`qa-workflow`語彙を再利用する。Regression Activityのdomain stateは`regression-testing`が判断し、`qa-workflow`は独立計算せずworkflow状態へ反映する。
20. relation indexは実装対象ではなく将来gateとする。direct ref + deterministic scanで不足を実測するまでrelation schemaも確定しない。
21. query結果の完全性を保証できない場合は`complete=false`相当を明示し、空集合を「影響なし」「Regression不要」と解釈しない。
22. 新3 Skillの意味品質はdataset構造検証だけで完了扱いにしない。既存semantic runnerと実Judgeを用いた代表caseの評価を実装完了時に別途記録する。
23. QAを続けるほど、テスト対象・関連する仕組み・テスト観点・テスト環境について再利用可能な知見が蓄積され、次のworkflowがscopeに応じて取り出せることを要件にする。既存の仕様・Risk・TC・test-target-inspection等の正本へ入る情報はそちらを更新し、第二の正本を作らない。
24. Activity / Session / executionは履歴の正本とし、Finding / Observationを自動的にcurrent知識へ昇格しない。未検証candidateは元Activity / Finding / Follow-upに残し、検証済みentryだけを知識成果物へ追加する。
25. knowledge entryではprovenance source refs / revisionsとcurrentness dependency refs / revisionsを分離し、entry単位のrevision / content identityを持つ。dependency変更時は一度有効だったentryを`要再検証`へ戻す。
26. `qa-workflow`で継続管理するworkflowは一意な`workflow_ref`を持ち、project contextから一意に発見できるproject-local fixed workflow state root配下で1 workflow = 1 persisted state artifactとする。同じ`workflow_ref`は常に同じstate artifactへ決定論的に解決し、初回保存はcreate-if-absent、更新はそのartifactのexpected revisionを使うatomic conditional writeで行う。standalone Skillにはpersisted stateを強制しない。
27. workflowはproject context全体のref / revisionをprovenance snapshotとして保持し、currentness判定には実際に利用したproject context項目のstable locatorとcontent identityまたは正規化値を別に保持する。cross-workflow currentnessはevent busで即時伝播せず、workflow / Run開始、resume、未開始mutable operation開始直前、current完了直前、current再利用直前のcheckpointで利用済みdependencyだけを再確認する。project context全体のrevisionが変わっても未使用項目だけの変更ではworkflowをstaleにしない。
28. 共有current成果物の自動rebase / partial updateは、owner Skillがdeterministic partial update boundaryを明示するartifactに限定する。scope disjoint、upstream dependency不変、cross-scope invariant維持を確認できない場合はcurrent成果物を再読込し責任Skillで再評価する。
29. shared mutable resourceはisolationを第一選択とし、分離できない場合は既存外部reservation、atomic CAS付きproject-local reservation、blockの順で扱う。project-local reservationでは同じ`resource_ref`が必ず同じreservation targetへ解決され、初回acquireをatomic create-if-absentまたはexpected revision付きstate transitionで競合させる。release / recoveryもcurrent ownerとexpected revisionを確認してCASし、時間経過だけ、owner状態不明、cleanup未確認の状態では自動解放しない。
30. knowledge lifecycleは`qa-knowledge`が担当する。`qa-workflow`はknowledgeのdomain判断を持たず、複数Skillが必要な要求のrouting / workflow stateだけを担当する。
31. knowledge persistenceはproject contextから発見できるfixed root配下の1 entry = 1 independently versioned artifactとする。単一project knowledge artifact、central manifest、global mutable ID counterは採用しない。
32. existing knowledge entryはartifact自身のexpected revisionを使うatomic conditional writeで更新し、same-entry conflictをsemantic auto-mergeしない。new knowledge identityの作成は、identity判定に使用したcompleteなknowledge snapshotとpublishを競合検出可能な形で結び付け、同一semantic identityから複数のcurrent entryを作らない。保存先に応じて、同一identityが同じcreate targetへ収束する方式またはnamespace / branch snapshotへのconditional publishを使用し、snapshot変更時はcurrent rootを再読込してidentity判定からやり直す。
33. このPlanでいうCASは、実際に共有されるmutable storage targetに対するatomic conditional writeを意味する。read → revision比較 → 無条件writeをCASとして扱わない。GitHub Contents API、native Git等でatomic primitiveが異なるため、Step 0で採用する保存経路ごとの条件付き更新方法を既存実装と照合して固定する。
34. workflow分岐、currentness、completeness、安全性、保存可否に使う決定論的な導出値はproduction codeで生成し、LLMに同じ計算を代替させない。PR #11型persisted runtime unitはMachine Evidenceとして下流identity / freshness / completenessがgeneration結果へ依存し、implementation変更時にstale判定が必要な処理だけに限定する。保存済みartifactの独立再検証はdeterministic validator、atomicityは保存先primitive、QA上の意味判断はowner Skillが担当する。
35. project contextのcurrentnessでは、表示label / heading / 行番号と独立したtemplate-defined stable keyをcurrentness対象fieldへ持たせる。workflowは利用したkeyとnormalized valueまたはcontent identity、影響scope / operationだけを保持し、missing / duplicate / ambiguous keyをLLMで推測補完しない。
36. workflow stateのCASだけで同一workflowのmutable operation二重開始を防止済みとは扱わない。PR #12 / E2E等のowner executionにatomic pre-start claim / idempotent startがあれば再利用し、なければStep 0で最小claimを実操作前に確定する。安全にclaimできない場合はsame-workflow concurrent mutable executionをblockする。

## 対象外

- 既存の新規・改修SkillをRegression専用Skillへ拡張すること
- 修正確認専用Skill / 専用artifact / 専用state
- Investigation専用Skill
- Suite maintenance専用Skill
- 汎用reporting Skill / defect-reporting Skill
- Finding / FAILの自動Defect化
- `qa-workflow`へRegression固有の意味判断を追加すること
- QA全体を新しいGraphへ移すこと
- Graph DBを前提としたknowledge management
- 単一の巨大なproject knowledge artifact
- knowledge central manifest / global mutable ID counter
- 汎用knowledge storage adapter
- workflowを1件だけ実行できる中央queue / schedulerの新設
- shared resource向けlock / lease方式の先行固定
- Graph DB / query server / web UI
- 汎用artifact registry
- 新しい共通Feature ID体系 / feature hierarchy
- PR #11 / #12 runtimeの再設計
- PR #13独自freshness / currentness state
- TCなしE2Eの自動TC化
- 全既存E2Eの暗黙Regression加入
- Regression scopeの完全自動決定
- Exploration結果の仕様Authorityへの自動昇格
