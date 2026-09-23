# Regression / Exploratory Testing 統合Plan

## 1. Skill構成

PR #13ではuser-facing Skillを3件追加します。

- `regression-testing`
- `exploratory-testing`
- `qa-knowledge`

既存の新規・改修Skillは責務を維持します。

| Skill / runtime | PR #13での位置づけ |
| --- | --- |
| PR #11 Machine Entity / traceability | identity / lifecycle / impact / freshnessの正本 |
| `test-analysis` | 新規・改修の変更影響候補 / Product Risk / test objective / test scope |
| `test-case-design` | current logical TC |
| `coverage-analysis` | 指定された成果物の意味上coverage検証 |
| `regression-testing` | Regression baseline / membership / Run計画 / Activity / history |
| `test-target-inspection` | currentな実対象情報 / UI / 既知範囲のふるまい収集 |
| `test-execution` | manual相当execution / result / evidence。既存TCの修正確認にも再利用 |
| `e2e-test-implementation` | E2E testware |
| `e2e-test-execution` | E2E execution / result / evidence。既存E2Eの修正確認にも再利用 |
| `e2e-test-result-analysis` | E2E failure分析 |
| `exploratory-testing` | Exploration / 仮説駆動Investigation |
| `qa-knowledge` | 継続QA knowledgeのtriage / lifecycle / lookup |
| `qa-workflow` | 複合workflowのrouting / common workflow state / blocked / resume |

## 2. 既存の新規・改修Skill

`test-analysis`等へRegression固有責務を追加しません。

新規・改修側は次を作ります。

- current仕様
- Product Risk
- test objective / test scope
- TR / TCN / CI / TC
- current TC→E2E mapping
- PR #11によるchange impact / freshness

「変更による回帰影響候補とProduct Riskを整理する」は`test-analysis`の既存責務として維持します。

「その影響候補等を使って、既存baselineから今回実行するRegression TCを確定する」は`regression-testing`です。

この境界をtrigger / semantic evalで固定します。

## 3. regression-testing

詳細契約は`_04b_regression-testing-skill.md`を正本とします。

正規の`対象 / 実行範囲`:

- `baseline / membership`
- `Run計画`
- `Run結果更新`
- `履歴参照`

`regression-testing`単体で完結できる要求と、`qa-workflow`がexecutionまでオーケストレーションする要求を分離します。

## 4. exploratory-testing

詳細契約は`_04c_exploratory-testing-skill.md`を正本とします。

正規の`対象 / 実行範囲`:

- `exploration`
- `investigation`

Investigation専用Skill / 別runtimeは追加しません。

## 5. qa-knowledge

詳細契約は`_04e_qa-knowledge-skill.md`を正本とします。

正規の`対象 / 実行範囲`:

- `triage`
- `create / update`
- `revalidation`
- `lookup / history`

担当:

- knowledge candidateの分類
- 既存正本ownerへのrouting
- residual knowledgeの有効化
- entry create / update / revalidation / replacement
- explicit knowledge lookup / history

担当しない:

- specification Authority確定
- Product Risk / test focusの採点
- TR / TCN / CI / TC設計
- current実対象情報の観測そのもの
- test execution
- Regression / Explorationのdomain判断
- workflow orchestration

既存の有効knowledgeを入力として使うだけのdomain requestでは、`qa-knowledge`を中央gatewayとして必須化しません。

## 6. 修正確認のrouting

修正確認は独立Skill、独立artifact、独立stateとして追加しません。`qa-workflow`が要求を修正確認として解釈し、必要な既存Skillへroutingします。

- currentな既存FAIL / 再現TCがある → analysis / designを省略し、manual相当は`test-execution`、repo E2Eは`e2e-test-execution`
- 期待結果、再現条件、current TCが不足する → 必要な最も早い既存analysis / design Skillで不足分だけ更新し、その後execution
- 周辺影響も確認する → `regression-testing`を別目的として追加

修正確認専用のテスト設計体系は作りません。既存のanalysis / design成果物を再利用できる場合は再利用します。

## 7. project context

既存`skills/qa-workflow/assets/project-context-template.md`を拡張します。

既存欄を再利用:

- §3 テスト範囲
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

必要な案件だけ追加:

- Regression既定Run方針
- TCなしE2E等の補助Regression testware refs

対象機能、role、業務フローをRegression専用欄へ複製しません。

## 8. coverage-analysis

Regression専用Skillにはしません。

`regression-testing`または`qa-workflow`から指定された対象に対し、既存責務の範囲で確認します。

- current Regression対象範囲 → TC
- selected scope → selected TC
- TC → E2E実装

Regression membership / Run selectionを`coverage-analysis`自身で決定しません。

## 9. PR #11

正本:

- stable QA ID
- Machine Entity
- design dependency / traceability
- change impact
- freshness / stale / `要再検証`
- partial update lifecycle

`regression-testing`は入力として利用し、独自freshnessを作りません。

PR #11がproject-wide artifact discoveryを保証するとは仮定しません。

## 10. PR #12 / E2E

### test-target-inspection

currentな実対象情報 / UI / 既知範囲のふるまい確認を担当します。

### test-execution

- TC snapshot
- manual相当execution
- source execution start / result / evidence / cleanup

修正確認でも同じexecution契約をそのまま再利用します。

を正本とします。

PR #12 Planでは最初の`scenario.when`操作開始がTCの開始済み境界です。`regression-testing`はこのsource contractを参照します。

### E2E

既存repo E2Eのexecution / rerun / raw result契約を正本とします。

TCなしE2EへTCを創作しません。

## 11. qa-workflow

`qa-workflow`は活動間routingだけでなく、複数Skillが必要なend-to-end QA要求をオーケストレーションします。

代表例:

- 新規・改修 + Regression asset reconciliation
- 修正確認 + Regression
- Regression Run planning + manual / E2E execution + Activity update
- Regression FAIL → analysis / investigation → fix → 既存TCの修正確認 → rerun
- Regression + Exploration

`qa-workflow`自身は次を独立再判定しません。

- Regression membership
- full / selected
- candidate / selected / excluded
- required execution route
- source result
- Regression Activity domain state
- knowledge candidate分類 / entry有効化 / update / replacement判断

## 12. workflow state / canonical Skill更新

PR #11 / #12 merge後の最新実装を確認し、少なくとも次をPR #13実装対象へ含めます。

- `skills/qa-workflow/assets/workflow-state-template.md`
- `scripts/skills/evals/deterministic/common.py`の`CANONICAL_SKILLS`
- 同ファイルの`MULTI_USE_SKILL_TARGETS`
- `skills/qa-workflow/evals/deterministic/validator.py`への影響確認
- qa-workflow routing fixtures / candidate outputs
- `.github/workflows/validate-skills.yml`のSkill一覧 / 件数
- README / EVALS / ASSERTIONS等のSkill一覧と件数

`MULTI_USE_SKILL_TARGETS`へ少なくとも次を追加します。

```text
regression-testing:
- baseline / membership
- Run計画
- Run結果更新
- 履歴参照

exploratory-testing:
- exploration
- investigation

qa-knowledge:
- triage
- create / update
- revalidation
- lookup / history
```

最新mainのSkill数を実装時に再取得し、古い14 Skill前提をハードコードしません。

## 13. FAIL / Finding feedback

Regression中のFAIL / 判定不能は`regression-testing`が原因確定しません。

`qa-workflow`が証拠に応じて、

- E2E異常 → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- current実対象情報不足 → `test-target-inspection`
- TC問題 → `test-case-design`
- coverage gap → `coverage-analysis`
- ownerなしの仮説駆動調査 → `exploratory-testing | investigation`

へroutingします。

修正後はcurrentな既存TCが使えるなら直接再実行して修正確認し、設計不足がある場合だけ既存analysis / designへ戻します。必要ならbaseline / Run scopeを再評価します。

## 14. reporting / Defect Management

PR #13では汎用reporting Skillや`defect-reporting`を追加しません。

Finding / FAILを自動Defect化しません。

実装後に報告形式の重複や運用上の必要性が確認された場合は別課題として検討します。

## 15. Portability

既存Skillは単体利用時にRegression Suite / Activityを必須にしません。

`regression-testing`、`exploratory-testing`、`qa-knowledge`もGraph / relation indexなしで主要機能を利用できることを必須にします。

## 16. 継続QA知識

継続利用する知識の共通契約は`_04d_continuous-qa-knowledge-and-concurrency.md`、Skill固有契約は`_04e_qa-knowledge-skill.md`を正本とします。

既存正本へ属する知識は`qa-knowledge`がそのownerへroutingします。

- 仕様・期待挙動 → `spec-analysis`
- Product Risk / test focus → `test-analysis`
- currentな実対象情報 → `test-target-inspection`
- TR / TCN / CI / TC → 各design Skill
- execution / result → PR #12 / E2E

既存正本へ自然に置けず、複数workflowで継続再利用する価値があるテスト対象・仕組み・観点・環境の知識だけを`qa-knowledge`がproject-local knowledge entryとして管理します。

保存形式はproject contextから発見するfixed root + 1 entry = 1 independently versioned artifactです。

new knowledge identityの作成では、identity判定に使ったcompleteなknowledge snapshotとpublishを競合検出可能な形で結び付け、同一semantic identityのcurrent entryを複数作りません。同一identityが同じcreate targetへ収束する場合はatomic create-if-absent、そうでない場合はnamespace / branch snapshotのexpected revision付きpublishを使い、snapshot変更時はidentity判定からやり直します。

`qa-workflow`はknowledgeの意味内容やentry lifecycleを独自に確定しません。複数Skillが必要な要求のrouting / workflow state / handoffだけを担当します。

## 17. project contextの追加入口

project contextへ知識本文やworkflow state本文を直接埋め込みません。

既存の「既存QA成果物」または最小追加欄から、少なくとも次の入口を発見できるようにします。

- fixed knowledge root
- workflow history root
- Activity / Session history root
- shared environment / resource policy

既存の実施環境、test user、test data、cleanup等の案件固有値は引き続きproject contextへ保持します。

workflowはproject context全体のref / revisionをprovenance snapshotとして保持します。一方、currentness判定では実際に利用した項目のstable locator + content identityまたは正規化値を保存し、whole revisionが変わった場合も利用項目だけを比較します。未使用項目だけの変更ではworkflowをstaleにしません。

project context自体を汎用artifact registryにしません。

## 18. workflow state

`skills/qa-workflow/assets/workflow-state-template.md`は「1 project = 1 workflow」の形にしません。

`qa-workflow`が複数sessionへ跨いで継続管理するworkflowは、project-local fixed workflow state root配下で1 workflow = 1 persisted state artifactとします。

同じ`workflow_ref`は常に同じstate artifactへ決定論的に解決します。初回保存はatomic create-if-absentとし、同じworkflowを別session / Agentが別state artifactへ分岐させません。

各workflow stateへ最低限次を追加します。

- workflow_ref
- workflow objective / requested outcome
- workflow scope
- started source refs / revisions
- 利用したknowledge refs / revisions
- project context ref / revision（provenance snapshot）
- currentness判定に利用したproject context項目のstable locator + content identityまたは正規化値
- 利用したenvironment / shared resource refs
- produced artifact / Activity / Session refs
- optional related workflow refs
- state revision / content identity

state更新はそのartifactのexpected revisionを保存先のatomic conditional writeへ渡し、同じworkflowを複数session / Agentが同時resumeしても古いstateで後勝ち上書きしません。

Skill状態表はそのworkflow内だけを表します。

単発のstandalone Skill利用にまでpersisted workflow stateを強制しません。

## 19. 共有成果物の並行更新

PR #12の`test-target-inspection`にあるrevision / SHA / ETagベースの競合防止を、共有current QA成果物更新時の共通原則として再利用します。

- 読み込み時revisionを保持
- 保存時は実際のshared mutable storage targetへatomic conditional writeする
- read → revision比較 → 無条件writeをCASとして扱わない
- 保存先ごとの条件付き更新primitiveを使用する
- 競合検出時に古いbaseで上書きしない
- overlapping / unknown scopeでは責任Skillへ戻して再評価

自動rebase / partial updateを許可するのは、owner Skillがdeterministic partial update boundaryを明示的に定義しているartifactだけです。

その場合も、update scopeがdisjoint、upstream dependency revision / fingerprintが不変、cross-scope invariantを壊さないことを確認し、current成果物を再読込してからscope外current内容を保持します。

stable IDが異なることだけを理由に安全mergeと判断しません。

汎用merge engineは追加しません。

## 20. shared environment / resource

`test-execution` / `exploratory-testing` / E2E等の実操作では、同時に利用するtest user、tenant、test data、external account等が他workflowへ影響し得ます。

優先順位を固定します。

1. workflowごとにresourceを分離する。
2. 分離できず既存の外部reservation / exclusive ownership機構がある場合は利用する。
3. 外部機構がなく、保存先がatomic CASを保証できる場合だけproject-local reservation recordを利用する。
4. 排他を保証できず相互影響も否定できない場合は自動並行実行をblockする。

project-local reservationは必要なprojectだけで使用し、同じ`resource_ref`が全workflowから同じcanonical reservation targetへ解決されるようにします。resource ref、workflow ref、関連Activity / Session ref、予約状態、reservation revisionを持たせます。

未予約をabsenceで表す場合はacquireをatomic create-if-absent、persistent recordを使う場合はexpected revision付き`available → reserved` CASとします。releaseはcurrent owner / workflowとexpected reservation revisionが一致する場合だけ成功します。

read-only / parallel-safe用途にはreservationを要求しません。

cleanupは自workflowが所有または予約したresource範囲だけを対象にします。

異常終了時はreservationを自動expiryしません。recoveryではcurrent reservation revision、owner workflow / Activity / Session、必要cleanupを再確認し、owner状態不明またはcleanup未確認では自動releaseせず明示的確認へblockします。recoveryのstate更新もCASします。

自動expiry付きlease、distributed lock service、environment managerは追加しません。

