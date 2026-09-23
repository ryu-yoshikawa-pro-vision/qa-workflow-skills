# Regression / Exploratory Testing 統合Plan

## 1. 評価方針

### routing / responsibility

- 新規・改修要求は既存設計Skillへroutingされる
- 変更による回帰影響候補 / Product Risk分析は`test-analysis`へroutingされる
- baseline / Run selection / historyの単独要求は`regression-testing`へroutingされる
- executionまで含むRegression要求は`qa-workflow`がオーケストレーションする
- Exploration / Investigationは`exploratory-testing`へ正しくroutingされる
- knowledge lifecycle要求は`qa-knowledge`へroutingされ、既存正本へ属する候補はowner Skillへ戻される
- 既存knowledgeを入力として使うだけのdomain requestは`qa-knowledge`を必須gatewayにしない
- 修正確認を独立Skill化せず既存analysis / design / executionで実施し、必要なRegressionを別目的として組み合わせられる
- `qa-workflow`がRegression固有判断を再実装しない

### deterministic

- project-wide TC discovery completeness
- fixed discovery snapshot / batch resume
- lifecycle resolvabilityとcoverage gapの分離
- initial baseline reconciliation
- Suite / Activity schema
- membership source ref / revision
- Run前currentness
- full / selected snapshot整合
- required execution routeとexecution stateの分離
- actual startに基づくexecuted判定
- TC countとTCなし補助testware countの分離
- source result投影
- Activity lifecycle / immutable条件
- Activity discovery completeness
- direct ref / deterministic scan
- fixed knowledge root discovery completeness
- 1 entry = 1 artifact
- entry ref / storage revision / CAS
- same-entry conflict / create-if-absent
- superseded ref / currentness dependency

### semantic

- membership判断
- scope変更時のmembership再評価
- full / selected selection
- existing Riskに基づくresidual riskの妥当性
- Regression対象範囲のcoverage
- TC→E2E実装coverage
- Finding / Observation / follow-up
- Exploration / Investigationの判断境界
- FAIL後routingの妥当性
- knowledge candidate triage
- residual knowledgeの有効化判断
- existing owner routing
- same-entry update / replacement判断
- environment / version applicability

### runtime smoke

- existing design flow → baseline reconciliation
- 既存TCを持つprojectでinitial baseline
- initial baselineの中断 / resume
- stale baseline → Run前reconciliation
- full / selected Regression
- 修正確認 + Regression
- manual / E2E / partial automation
- FAIL → analysis / investigation → fix → 既存TC再実行による修正確認 → rerun
- Exploration → Finding → design flow → baseline reconciliation
- Activity block / resume / complete / history
- Finding → qa-knowledge → existing owner / residual knowledge
- knowledge revalidation → current evidence取得 → same entry update
- 5 workflowによるentry-level CAS / stale isolation

## 2. 必須評価

### Skill routing

既存positive triggerを維持します。

- 「既存仕様と今回の差分から、回帰影響候補とProduct Riskを整理して」→ `test-analysis`
- 「その影響候補から今回実行するRegression TCを選んで」→ `regression-testing | Run計画`
- 「Regression baselineを更新して」→ `regression-testing | baseline / membership`
- 「過去のRegression結果を確認して」→ `regression-testing | 履歴参照`
- 「Regressionを実施して」→ `qa-workflow`から開始し、`regression-testing`とexecution Skillを利用
- 「探索的テストをして」→ `exploratory-testing | exploration`
- 「この未知症状を仮説検証して」→ 既存ownerがなければ`exploratory-testing | investigation`
- 「現在のUI構造を確認」→ `test-target-inspection`
- 「このFindingを今後のQA知識として残して」→ `qa-knowledge | triage`
- 「この環境知識がまだ有効か確認して」→ `qa-knowledge | revalidation`
- 「過去のQA知識を確認して」→ `qa-knowledge | lookup / history`
- 「このknowledgeを更新して」→ `qa-knowledge | create / update`

negative:

- Regression Run selectionを`test-analysis`へ送らない
- change impact / Product Risk分析を`regression-testing`へ送らない
- current UI情報収集を`exploratory-testing`へ送らない
- 既知TC実行を`exploratory-testing`へ送らない
- specification / Product Risk / current UI factの直接要求を`qa-knowledge`へ送らない
- 既存knowledgeを使ったテスト分析要求をknowledge lifecycleだけの要求と誤判定しない

### 複合workflow

- 「不具合修正が直ったか確認して、周辺Regressionもして」→ currentな既存TCがあればexecutionへ直接。設計不足があれば必要な既存analysis / designを経由し、その後`regression-testing`
- 「今回の変更をRegressionして、追加で探索的にも確認して」→ Regression + Exploration
- baseline / Run planningだけなら`regression-testing`単体利用を許可
- actual executionを含む場合は`qa-workflow`が全体を追跡

### TC discovery / initial baseline

- authoritative discovery rootsからcurrent TC sourceを列挙
- source不足ならdiscovery completeness false
- 発見済みlegacy TCがPR #11 current lifecycleへ解決不能でもdiscovery失敗と混同しない
- lifecycle unresolvedならoverall baseline completeはfalse
- traceability不足はcoverage gapとして区別
- 既存TC A/B/Cがあり今回Cだけ変更でもinitial baselineではA/B/Cを判断
- 大量TCを複数batchに分けても同じdiscovery snapshotを使用
- 未判定TCが残る間は`complete=false`
- source revision変更後に旧snapshotへ新規TCを継ぎ足さない
- resume後に全件閉じればcompleteへ遷移できる

### handoff / Run前currentness

- Regression運用中projectでTC / scope / relevant Risk変更 → `regression-testing | baseline / membership`を`要再検証`
- standalone TC設計だけの要求ではbaseline更新を強制しない
- handoffを意図的に省いたfixtureでも次回Run前currentness checkで差分を検出
- stale baselineのままfull Runを開始しない
- E2E mapping変更だけならmembershipではなくrequired routeを再評価

### Regression membership

- one-off TCを恒常memberにしない
- one-off責務自体がcurrent Regression対象範囲に残る場合はcoverage gapを黙らせない
- stable TC update
- split / mergeはPR #11 lifecycleに従う
- deleted / supersededをcurrent memberにしない
- feature tagなしでも成立
- TC無変更でもscope / relevant Risk変更で再評価
- 影響範囲不明ならcurrent TC全体を再確認

### Full / Selected

- user scope優先
- project policy利用
- full fallbackはcompleteかつcurrent baselineでのみ許可
- fullはsnapshot全TC member
- selectedはsubset
- selectedをSuite全体完了と扱わない
- selection rationaleを保持

### residual risk

- excluded / blocked / unexecuted / coverage gapからexisting Riskへの残存影響を示せる
- Product Riskを`regression-testing`が新規採点しない
- 新規Risk / score変更が必要なら`test-analysis`へrouting

### required route / execution state

- required routeに`未実行` / `blocked`を入れない
- E2E存在だけでmanual不要としない
- partial E2Eでmanual + E2Eを要求できる
- preflight blockでexecution artifactが作られてもexecutedにしない
- PR #12の`実行開始=未開始` + `状態=未実行`をexecutedにしない
- 1 TC → 2 E2Eで片方未開始ならlogical TCをexecutedにしない
- manual + E2Eで片方未開始ならlogical TCをexecutedにしない
- FAIL / 判定不能とexecutedを分離
- 2 TC → 1 E2Eでexecutionを重複起動しない
- 全required routeでactual start確認後だけlogical TCをexecutedにする

### source result / Activity

- Activityからrouteごとのexecution ref / source開始状態 / source resultを追える
- source resultをRegression独自taxonomyへ再判定しない
- PASS / FAIL / 判定不能等をhistory上確認できる
- project context / baseline / selection input revisionsを保持
- scope / snapshot不変のblock → resume
- scope / snapshot変更時は別Activity
- completed Activity immutable
- `regression-testing`のdomain stateを`qa-workflow`が独立再計算しない

### TCなしE2E

- TC IDを創作しない
- user明示またはproject policyだけで参加
- fullでも暗黙加入しない
- auxiliary countをTC countと分離
- TC-based coverageへ算入しない

### 修正確認 intent

- currentなknown failing manual TCがある → analysis / designを再実行せず`test-execution`
- currentなknown failing E2Eがある → analysis / designを再実行せず`e2e-test-execution`
- 期待結果 / 再現条件 / current TCが不足する → 必要な最も早い既存analysis / design Skillで不足分だけ更新してからexecution
- 修正確認専用Skill / artifact / stateを生成しない
- 修正確認PASSだけでRegression不要としない

### Regression FAIL feedback

- E2E FAIL → `e2e-test-result-analysis`
- manual FAILで仕様不明 → `question-analysis`
- current実対象情報不足 → `test-target-inspection`
- TC問題 → `test-case-design`
- owner不明の仮説調査 → `exploratory-testing | investigation`
- fix後 → currentな既存TC再実行による修正確認
- QA成果物 / baseline入力変更 → membership / Run scope再評価
- FAIL / Findingを自動Defect化しない

### Exploration / Investigation

- Charter必須項目
- ObservationとFindingの区別
- evidence ref
- Follow-up
- interrupted / blocked / resume
- cleanup / side-effect / secret保護
- current UI確認は`test-target-inspection`
- 既知TC実行はexecution Skill
- ownerなし仮説駆動だけInvestigation
- Investigationで別runtime / schemaを作らない


### 継続QA知識

- Finding / Observationを無条件にcurrent knowledgeへ昇格しない
- 未検証candidateをknowledge artifactへ保存せず元Activity / Finding / Follow-upに残す
- specification候補 → `spec-analysis`
- Product Risk / test focus候補 → `test-analysis`
- current UI fact → `test-target-inspection`
- formal Test Condition等へ昇格すべき候補 → design Skill
- 既存正本へ自然に置けない再利用knowledgeだけ`qa-knowledge`がentry化する
- knowledge entryはstable refを持つ
- fixed root配下で1 entry = 1 independently versioned artifact
- existing entry updateはentry artifact自身のexpected revisionを使うatomic conditional write
- new entryのidentity判定とpublishを同じcompleteなknowledge snapshotへ結び付ける
- 同じsemantic identityを2 workflowが同時createしてもcurrent entryは1件に収束する
- identity判定後にsnapshotが変わった場合はcurrent rootを再読込してidentity判定からやり直す
- 異なるsemantic identityの並行createは再評価後に両方保存できる
- global mutable counter / central manifestを要求しない
- provenance source refs / revisionsとcurrentness dependency refs / revisionsを分離する
- 適用scope、environment / version条件を持つ
- currentness dependency変更時はcurrent利用しない
- same identityの再検証 / 更新はsame entryのnew revision
- semantic identity変更時だけreplacementを使う
- same-entry CAS conflictをsemantic auto-mergeしない
- 別entry更新だけで無関係entry利用workflowをstaleにしない
- `要再検証` / `置換済み`entryをcurrentな判断へ使わない
- workflow / Activityから実際に利用したentry ref / revisionを追える
- knowledge更新後も過去Activity / Sessionのinput revisionを書き換えない
- scopeに無関係なknowledgeを全件LLMへ投入しない
- secret実値をknowledge artifactへ保存しない

### 複数workflow

- 同一projectで2つ以上のworkflowが異なる`workflow_ref`を持って同時進行できる
- qa-workflowが継続管理するworkflowはfixed workflow state root配下で1 workflow = 1 persisted state artifact
- 同じ`workflow_ref`の同時初回保存が1つのcanonical state artifactへ収束する
- workflow state自身がrevision / content identityを持ちatomic conditional writeで更新される
- 同じworkflowを2 sessionが同時resumeしてもstateの後勝ち上書きが起きない
- 各workflowがstarted source refs / revisions、knowledge refs / revisions、project context全体revision、利用したproject context項目のstable locator + content identityまたは正規化値、resource条件を保持する
- workflow Aの進行中にBがAの依存Entityを更新してもAのhistorical resultは保持する
- currentnessをworkflow / Run開始、resume、未開始mutable operation開始直前、current完了直前、current再利用直前で確認する
- BがAの利用中project context項目を変更した場合だけ該当scopeを`要再検証`へ戻す
- BがAの未使用project context項目だけを変更した場合はAをstaleにしない
- Bの変更がAへ無関係ならA全体を再実行しない
- event bus / repo-wide coordinatorなしでcheckpoint検出できる

### 共有成果物の競合

- 同じscopeを同じbase revisionから更新した場合、後勝ち上書きをしない
- scope overlapを判定できない場合にLLMが自動mergeしない
- revision / SHA / ETag等の競合検出に失敗した更新を保存済み扱いしない
- read → revision比較 → 無条件writeをCASとして扱わず、保存先のatomic conditional writeを検証する
- owner Skillがdeterministic partial update boundaryを定義していないartifactは自動rebaseしない
- owner contractがあるartifactでもupdate scope disjoint + upstream dependency不変を確認する
- stable IDが異なるだけではdisjoint updateとみなさない
- safe partial updateではcurrent成果物を再読込してscope外current内容を保持する

### shared environment / resource

- workflow別に分離されたtest user / dataでは並行実行できる
- 既存の外部reservation / exclusive ownershipがある場合は再利用する
- 外部機構がない場合、atomic CASを提供できる保存先だけproject-local reservationを許可する
- 同じresource refが同じcanonical reservation targetへ解決される
- project-local reservationの同時acquireで1 workflowだけが成功する
- CASで排他を保証できないshared mutable resourceは並行実行をblockする
- read-only / parallel-safe resourceはreservation不要
- cleanupが別workflowのresourceを削除しない
- environment / resource条件が途中で変わった場合、結果のcurrentnessを再確認する
- workflow異常終了時にreservationを自動expiryで別workflowへ譲渡しない
- stale reservation revisionからのrelease / recoveryを拒否する
- owner active状態またはcleanup状態を確認できないrecoveryをblockする
- 安全なrecoveryだけがexpected revision付きCASでreleaseできる

### relation index不要

- TC → past Activityをfixed root scanで回答できる場合はindex不要
- scanで要件を満たす限りrelation schemaを確定しない

## 3. workflow state / CI更新

実装開始時のPR #11 / #12 merge後CIを正本として、少なくとも次を更新します。

- Skill一覧へ`regression-testing` / `exploratory-testing` / `qa-knowledge`
- `skills/qa-workflow/assets/workflow-state-template.md`
- `scripts/skills/evals/deterministic/common.py`
  - `CANONICAL_SKILLS`
  - `MULTI_USE_SKILL_TARGETS`
- `skills/qa-workflow/evals/deterministic/validator.py`への影響確認
- qa-workflow routing fixtures / candidate outputs
- `.github/workflows/validate-skills.yml`のexpected Skill一覧 / 件数
- trigger dataset
- deterministic output eval
- semantic dataset / rubric
- Regression Suite / Activity validator
- qa-knowledge entry validator / discovery / CAS contract test
- knowledge routing / lifecycle fixtures
- current TC discovery / baseline progress test
- Activity discovery
- execution route closure
- project context schema / docs
- README / EVALS / ASSERTIONS
- `skills-ref validate`

Skill総数や評価件数は実装開始時のlatest mainから再計算し、現在の14 Skill前提をコピーしません。

## 4. semantic実評価

repository CIでは既存方針どおり外部LLM APIを呼びません。

ただし次はdataset / rubric構造検証だけで意味品質PASSと扱いません。

- Regression membership
- selected Regression
- residual risk
- Exploration Charter解釈
- Observation / Finding分類
- Follow-up
- 複合workflow routing
- knowledge candidate triage / owner routing
- knowledge applicability / revalidation / replacement

実装完了前に代表caseの実Agent candidate outputを保存し、

```text
candidate output
→ scripts/skills/evals/semantic/run.py
→ 実Judge command
→ pass / needs_review / fail
```

を実行し、結果をPRの検証記録へ残します。

CIへ外部APIを追加しません。

## 5. 実装順序

### Step 0: PR #11 / #12 merge後の再判定

- merge済み実装を確認
- current TC identity / lifecycle / impact
- project-wide discovery capability
- PR #12 execution start / result / rerun契約
- E2E execution start / result契約
- Activity保存規約
- workflow state / knowledge entry / reservationをpersistする実際の保存経路
- 保存経路ごとのatomic conditional write primitiveと、historical revisionから当時artifactを再取得できること
- fixed rootを使用するAPI / filesystemで完全列挙でき、truncation時に`complete=true`を返さないこと
- same-workflow concurrent resume時、state保存より先に同じmutable operationを二重開始しないsource contractが存在するか
- PR #11 / #12だけで解けるものを除外

### Step 1: Skill / workflow vocabulary

- `regression-testing` / `exploratory-testing` / `qa-knowledge` skeleton
- `CANONICAL_SKILLS`
- `MULTI_USE_SKILL_TARGETS`
- workflow state template
- trigger境界
- qa-workflow routing

### Step 2: qa-knowledge / 継続QA知識 / workflow concurrency

- `qa-knowledge` trigger / non-trigger / input / output
- candidate triage / existing owner routing
- fixed knowledge root discovery
- 1 entry = 1 independently versioned artifact
- stable entry ref / create-if-absent
- new knowledge identityのsnapshot-bound create / concurrent duplicate防止
- entry storage revision / backend atomic conditional write
- provenance sourceとcurrentness dependencyの分離
- same-entry update / revalidation / replacement
- root / repository HEAD変更だけで無関係entryをstaleにしない
- knowledge candidateをActivity / Finding / Follow-upに留める契約
- workflow_ref
- fixed workflow state root / 1 workflow_ref = 1 persisted state artifact
- workflow state初回create-if-absent / revision / backend atomic conditional write
- started source refs / revisions
- project context whole revision + used item dependency identity
- currentness checkpoint
- owner Skillが保証するpartial update boundary
- shared artifact revision conflict
- cross-workflow staleのcheckpoint検出
- shared environment / resource policy入口
- isolation → existing reservation → canonical target + CAS付きproject-local reservation → block
- reservation recoveryのowner / cleanup確認とCAS release

### Step 3: initial baseline / currentness

- discovery snapshot
- batch / resume
- lifecycle resolvability
- membership
- coverage gap分離
- Run前currentness

### Step 4: Regression Run計画

- full / selected
- `test-analysis`とのimpact境界
- residual risk
- required execution route

### Step 5: execution / Activity

- manual / E2E
- route vs state分離
- actual start判定
- TCなしE2E
- source result投影
- Activity lifecycle / history

### Step 6: 修正確認routing / FAIL feedback

- 既存TC再利用とanalysis / design省略条件
- E2E failure analysis
- manual FAIL owner routing
- fix → 修正確認 → rerun / baseline再評価

### Step 7: exploratory-testing

- dedicated Skill contract
- Charter / Session
- Observation / Finding
- side-effect / cleanup
- block / resume / completion
- Follow-up routing

### Step 8: end-to-end QA cycle

```text
新規・改修
→ current QA成果物
→ baseline reconciliation
→ Regression
→ FAIL / Finding
→ analysis / investigation
→ fix
→ 既存TC再実行による修正確認
→ 必要なRegression
```

Regression + Exploration等の複合workflowも確認します。

### Step 9: semantic実評価

保存candidate outputを既存semantic runner + 実Judgeで評価します。

### Step 10: relation index gate

direct ref + deterministic scanで不足を実測した場合だけ、必要queryに対するindexをその時点で設計します。

不足がなければ何も実装せず完了します。

### Step 11: 全体回帰

既存Skill、PR #11 / #12、新規3 Skill、routing、runtime smoke、CI、実Judge記録を確認します。

## 6. 実装時に避けること

- 主要workflow入口を排他的なQA taxonomyとして扱う
- 修正確認を独立Skill / 独立artifactとして実装する
- 修正確認をRegressionと同一視する
- `test-analysis`の既存回帰影響候補triggerを`regression-testing`へ移す
- `qa-workflow`へRegression固有意味判断を追加する
- standalone設計依頼でRegression baseline構築を強制する
- baseline運用中なのにmembership入力変更を無視する
- Run前currentness確認なしに古いbaselineを使う
- initial baselineを1回で全件処理できる前提にする
- legacy TCを`regression-testing`が独自修復する
- required routeへ`未実行` / `blocked`を混ぜる
- execution artifact存在だけでexecuted扱いする
- Product Riskを`regression-testing`で再採点する
- FAIL / Findingでworkflowを終了する
- Investigation専用Skill / runtimeを増やす
- Findingを自動Defect化する
- generic reporting frameworkを追加する
- relation index schemaを必要性実証前に固定する
- workflow stateをproject全体で1件だけ持つ
- shared current artifactをrevision確認なしで上書きする
- concurrent workflowのsemantic conflictを後勝ちまたは無条件自動mergeで解決する
- Activity / Findingを自動でcurrent知識へ昇格する
- project contextへ知識本文を無制限に詰め込む
- shared mutable resourceを安全性確認なしで並行利用する
- reservation / lock方式を必要性検証前に固定する
- provenance sourceだけでknowledgeのcurrentnessを判断する
- 未検証Finding / Observationをknowledge成果物へ蓄積する
- knowledge artifact全体のrevisionだけを全entryのrevisionとして扱う
- 全knowledge entryを単一artifactへ集約する
- knowledge central manifest / global mutable ID counterを追加する
- `qa-knowledge`へ仕様 / Risk / TC / current実対象情報のdomain判断を移す
- 既存knowledgeを利用するだけの全domain requestを`qa-knowledge`経由にする
- workflow stateをCASなしで更新する
- currentnessをworkflow完了時だけ確認する
- owner Skillがpartial updateを保証していないartifactをscope推測でauto-rebaseする
- project policyの記述だけをshared mutable resourceの排他保証として扱う
- CASできないreservation fileの存在だけをlockとして扱う
- blob / revisionを事前比較しただけの無条件writeをCASと呼ぶ
- 同一semantic knowledgeを別refで複数current entryとして残す
- project context全体revision差だけで無関係workflowまでstaleにする
- abandoned reservationを時間経過や未確認cleanupのままreleaseする

## 7. 完了条件

- 主要workflow入口を組み合わせてQAを実施できる
- 修正確認がworkflow intentとして既存Skillで実施され、専用Skill / artifact / stateを作らずRegressionと区別されている
- `test-analysis` impact分析と`regression-testing` Run selectionが競合しない
- `regression-testing`単体要求とend-to-end Regressionが区別される
- 新規・改修後のhandoffとRun前currentnessの両方で古いbaseline利用を防げる
- initial baselineを同一snapshotで中断 / 再開できる
- discovery / lifecycle / membership / coverage completenessを混同しない
- full fallbackはcomplete current baselineでだけ成立する
- required routeとexecution stateが分離されている
- actual startに基づきexecutedを判定できる
- source resultをActivity historyから確認できる
- residual riskがexisting Riskを再採点しない
- Regression FAIL → analysis / investigation → fix → 既存TC再実行による修正確認 → rerunが閉じる
- `exploratory-testing`の入力 / lifecycle / output / safety契約が実装可能な粒度で固定されている
- workflow state validatorが新3 Skill / multi-use targetを扱える
- relation indexなしで主workflowが成立する
- deterministic / semantic dataset / runtime smoke / 既存CIがPASSする
- 代表semantic caseを実Judgeで評価し、実装完了記録に残せる
- 継続利用するQA知識を`qa-knowledge`でtriage / 有効化 / 再検証 / 更新 / 置換 / lookupできる
- fixed knowledge root + 1 entry = 1 artifactで保存・検索・再利用できる
- same-entry updateをentry-level atomic conditional writeで保護できる
- 同一semantic identityの並行createを1 current entryへ収束できる
- unrelated entry更新で無関係workflowをstaleにしない
- 既存正本へ属する知識を第二の正本として複製しない
- 複数workflowが独立したworkflow_ref / state / input snapshotで同時進行できる
- 同じworkflow_refの初回state作成と更新が1つのcanonical state artifactへ収束する
- shared current artifactの競合で後勝ち上書きが起きない
- project contextの未使用項目変更で誤staleにせず、利用項目変更だけ必要scopeを要再検証へ戻せる
- cross-workflow変更をdependency / revisionから必要scopeだけ要再検証へ戻せる
- shared environment / resourceの安全な並行利用可否を判断でき、不明時にblockできる
- knowledge entryのprovenanceとcurrentness dependencyを分離できる
- 未検証candidateをcurrent knowledgeとして利用しない
- workflow state自身のCASで同一workflowのlost updateを防げる
- currentness checkpointで別workflowの変更をmutable operation開始前にも検出できる
- partial auto-rebaseをowner Skillが保証するartifactへ限定できる
- shared mutable resourceをisolation → existing reservation → canonical target + CAS付きlocal reservation → blockの順で安全に扱える
- abandoned reservationをowner / cleanup状態確認なしに再利用せず、安全なrecoveryだけをCASで解放できる
