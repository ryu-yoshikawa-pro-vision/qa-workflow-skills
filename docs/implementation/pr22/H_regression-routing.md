# PR #22 並行実装：H — Regression・Activity

## 位置付け

正式TCに紐付く非E2E required routeとTCなし必須補助testwareの実施義務をRegression Run・Activityへ正しく反映する。

- 作業branch：`feat/pr22-h-regression-routing`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRは**実装準備のDraft**から始め、以下の完了条件を満たしてレビューできる状態にする。**実装完了・merge済みを意味しない**。
- 2026-11-08の利用者指示で、最終統合先はPR #22に変更された。既存Plan索引の「PR #22は文書変更PR」という作成時点の記載より、この統合指示を優先する。
- このファイルは担当別の作業ガイド。要件・完了条件の正本は以下のPlan。**15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケースを削減しない**。全体の最終完了判定はPR #22で行う。

## 参照するPlan

- [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細04：runtimeとRegression](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)

関連完了条件の主な担当：QA全工程 8・9のRegression route／Activity部分。

## このbranchで変更する対象

- 既存`skills/regression-testing/**`、特に`scripts/regression_runtime.py`
- `evals/deterministic/validator.py`のREG-D011／REG-D015、Run・Activity契約／template・回帰fixture

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 担当branchで実施する作業とPR #22で実施する作業

### このbranchで実施・検証する

- 本書の担当対象のSkill・runtime・helper・データ契約・既存consumerとの局所接続を実装し、担当範囲の既存テスト・回帰・負例・権限／保存・履歴互換性を検証する。
- 担当機能の受入に必要な実runner・実保存先・実Agentの**単独経路**は、利用可能な環境で実施する。外部権限・実接続が不足する場合はその条件を未検証／blockedと明示し、独立に検証できる部分は完成させる。
- 他branchの未統合実装は合意した契約と独立fixtureで代替して局所検証する。fixtureは他ownerの実成果物を統合した証拠にはしない。
- 担当が所有する実装不具合、局所結合・回帰不具合は**このbranchで修正**し、対応したテスト・実施証拠を残す。

### PR #22だけで実施・判定する

- A〜Jの実装PRの取り込み、競合解消・全体再検証、**各ownerが実際に保存した成果物同士**のID／revision／currentness／承認・run参照による横断接続。
- 全current Skill同時利用時の発火／routing、工程をまたぐ実Agent・実runner・実provider・製品CIの一連の受入、S1〜S17の総合試験、人間編集8ケースの**全体経路としての再検証**。
- 開発連動QAの15条件、QA全工程の10条件と詳細Plan 01〜08の最終照合、Plan詳細07の5シナリオの**変更前後の横断実測・効率化判定**、統合後の全CI・回帰評価。
- 横断試験で見つかった問題はownerを特定し、分割可能な実装・修正は対象branchに戻す。統合固有の接続・設定・複数owner間の確認作業だけをPR #22で実施する。

### PR #22へ引き渡す証拠

- 担当の変更ファイル、公開入出力契約、参照するowner／source／artifact IDとrevision、schema／fixture、保存・承認・失敗／再開条件。
- 局所検証のコマンドと結果、実runner／実providerの担当経路の証拠、回帰・負例、未実行／SKIP／blockedと再開条件。
- 他担当の実成果物が必要な横断検証項目。**これらの未実施は担当branchの局所検証を失敗扱いする理由にはしないが、PR #22の最終受入完了には必ず必要**とする。

## 共通契約が未確定の場合の着手範囲

- A（[PR #23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23)）のsource／artifact ID・revision・scope、runtime登録、保存・承認・CAS／readback、blocked／再開、評価・CI引継ぎ契約を**実コード・既存契約と照合し、PR #23で共有された内容**に従う。
- 上記に依存しない既存実装調査、担当Skill固有ロジック、独立fixture、局所テストは先行可能。Aによる確定・共有前に、未確定の共通schema・保存形式・承認・runtimeの接続方法を推測して確定しない。
- 契約未確定で停止する対象処理と理由・解決責任者・再開条件を記録し、独立して実施できる作業を止めない。Aが共有した契約を使う局所検証の後、他ownerの**実成果物を使う横断検証はPR #22**へ引き継ぐ。

## 着手基準

- [x] `regression_runtime.py`、REG-D011／D015、旧Run・Activityと全呼び出し元を確認した。
- [ ] Gとtestware実行結果、Eと正式TC参照、Fと管理計画の分離を合意した。

## 作業内容

1. `validate_required_routes()`がmanual/e2e以外を拒否する現契約へ非E2E `testware`を追加し、Gの実行ownerに引継ぐ。
2. 正式TCのrequired routesと、TCなしauxiliary testwareを別の集合・カウンタ・結果参照で扱う。
3. auxiliary routeごとの`completion_required`選定根拠・実run／attempt・result finalized・raw取得完全性・cleanupを扱い、補助必須未実行をActivity完了にしない。
4. 補助のみのRunも実開始・blocked・確定結果に応じて既存Activity状態へ反映し、正式TCのexecution／coverage分子を汚染しない。
5. 旧Run／Activityの読取・再開・履歴の不変性、required義務が不明な旧Runのblocked、新revisionでの復旧を扱う。
6. REG-D011／REG-D015を元sourceから独立再計算し、timeout・skip・部分Run・cleanup不全・retry・旧buildを検証する。

## 依存と引継ぎ

- E/F→H：正式TC・selection・Run計画。
- G→H：実runner／attempt／cleanup・testware revision・source result。
- H→J：TC route・補助route別のActivity実測と未取得範囲。
- A：workflow runtimeに必要な統合状態を渡すが、Regressionの状態はHが正本。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [x] manual/e2e/testwareの正式route選定と実行ownerへの引継ぎが成立する。
- [x] 必須補助が未実行ならActivity完了拒否、補助だけのRunでも未開始に固定されない状態導出がPASSする。
- [x] 正式TCと補助testwareの母集団・結果・件数が混同されない。
- [x] legacy／old RunとActivity、partial Run、unknown obligation、timeout／retry／cleanup不全を含む決定論的validatorと履歴互換がPASSする。
- [x] 固定qa-training-storeで確認したVitestの形式と独立fixtureを用い、H担当のRun→Activity判定・既存互換を検証した。Gが生成した正本runとの実参照・統合受入はPR #22へ引き継いだ。
- [x] Regression既存のtrigger／決定論的／意味評価と関係テストの回帰がPASSする。

- [x] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [x] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [x] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [x] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [x] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装・検証記録（担当H、2026-11-09時点）

### 変更ファイルと公開契約

| 対象                                                                                                        | 内容                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `skills/regression-testing/scripts/regression_runtime.py`                                                   | `testware` required route、補助`completion_required`、`validate_auxiliary_routes()`、`resolve_auxiliary_obligations()`、`project_activity()`の完了・状態導出 |
| `skills/regression-testing/evals/deterministic/validator.py`                                                | REG-D008／D009（Run）、REG-D010／D011／D015（Activity）をowner sourceから独立再計算。旧形式は従来規則                                                        |
| `references/data-contract.md`・`guidance.md`・`SKILL.md`・`assets/output-template.md`                       | route・義務・完了判定・旧形式互換の契約                                                                                                                      |
| `scripts/skills/evals/deterministic/ASSERTIONS.md`                                                          | REG-D008／D009／D011／D015の説明                                                                                                                             |
| `evals/output/cases/reg-out-003`〜`005`、`evals.json`                                                       | Run（manual＋testware＋補助）、Activity完了、必須補助未開始の負例                                                                                            |
| `tests/skills/evals/deterministic/test_regression_routing.py`、`tests/skills/fixtures/regression-testware/` | 担当固有の局所テスト111件と、固定`qa-training-store`のVitest JSON形式fixture                                                                                 |
| `tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`                                         | 出力評価manifestのcase一覧にREG-OUT-003〜005を追加（既存テストの変更はこの1箇所のみ）                                                                        |

公開契約の要点（詳細は`data-contract.md`）：

- `required_routes[].route_type`に`testware`を追加。`testware_ref`・`executor_owner=testware-execution`・`implementation_revision`・`selection_basis`が必須。`manual`／`e2e`の正規化形は変更なし。
- Run／Activityに`route_contract_version: "2"`。未設定は旧形式で、読取互換・従来規則のまま。
- `testware` routeのsourceは`attempt_ref`・`raw_capture_complete`・`cleanup_status`を返す前提で、cleanup欠落は`未確認`として`完了`にしない（manual／e2eの旧既定値は変更しない）。
- ActivityのRun照合：`REG-D018`／`validate_activity_against_run()`／`verify_activity_against_run()`が、保存済みRunを正本にRun自体の妥当性・route集合・実施義務（`completion_required`等）・TC付きtestwareの選定情報（`testware_ref`・`executor_owner`・`selection_basis`）・sourceから再計算した状態・件数を照合する。Runを渡せない経路ではv2 Activityの`完了`を拒否する。
- 補助`auxiliary_routes[]`は`completion_required`・選定根拠・実行owner・実装revisionを持つ。source executionは`attempt_ref`・`raw_capture_complete`・`cleanup_status`・`implementation_revision`を返す。
- Activity `完了`はrequired TC routeと`completion_required=true`の補助routeの全確定時のみ。両集合が空・義務不明・旧build結果・TC／補助間の`execution_ref`共有は完了にしない。補助の件数・結果はTCのexecution／coverage分子へ加算しない。

### 局所検証（個別に実行・判定）

実行環境: Python 3.12.0、ruff 0.16.8（`ruff.toml`の固定versionに合わせて隔離venvへ導入）、dprint 0.55.2、Node v22.20.0、Codex CLI 0.164.0。

| 検証                                                                                                                                                                         | 結果                                                                                                                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `unittest discover tests/skills/evals/deterministic`（401件）                                                                                                                | PASS（短縮形のTEMPで1件が環境要因で失敗するため、TEMPを長いパスにして実行）                                                                                                                |
| `test_regression_routing.py`（111件）、`test_qa_artifact_graph_skills.py`（40件、Regression 18件を含む）                                                                     | PASS                                                                                                                                                                                       |
| `scripts/skills/evals/deterministic/tests`（12件）、`tests/skills/evals/semantic`（13件、1 skip）、`tests/skills/evals/trigger`、`scripts/skills/evals/semantic/validate.py` | PASS                                                                                                                                                                                       |
| `ruff format --check`／`ruff check`（変更したPython）、`dprint check`（変更したmd／json）、`git diff --check`                                                                | PASS                                                                                                                                                                                       |
| `unittest discover tests/skills/runtime`（496件）                                                                                                                            | `test_ci_handoff`（6 FAIL）と`test_sqlite_workflow_history`（14 ERROR）が失敗。変更前HEAD（`git archive`）でも同数が失敗するためH差分と無関係（Windows環境起因）。Regression関連の失敗なし |

### 固定`qa-training-store`のVitest形式

固定commit `2a8bcf57ff091e84a8b3bf7b123568e967000d88`（`origin/main`）をexportし、`tests/unit/password-hasher.test.ts`と`tests/unit/app-config.test.ts`を`vitest run --reporter=json`で実行して得た形式（`ancestorTitles`・`title`・`fullName`・`status`）を`tests/skills/fixtures/regression-testware/vitest-qa-training-store-2a8bcf5.json`に保存した。永続識別はrepo revision・file・test名／階層とし、runner内部IDは使わない。このfixtureでTC紐付きtestware route→実開始→結果確定→Activity、旧build（別revision）の不採用、TCなしVitestの必須補助化を検証した。Gが保存した正本runではない。

### 未実施・blocked・PR #22へ引き継ぐ項目

- **Gの実runner・実attempt／cleanupとの実参照**：未実施。`attempt_ref`・`raw_capture_complete`・`cleanup_status`・`implementation_revision`をsource executionが返す前提の契約とfixtureで検証した。Gが保存した実成果物でのID／revision／currentness接続はPR #22。
- **意味評価（モデルを使うJudge）**：`REG-SEM-007`の新規追加と、影響する`REG-SEM-004`・`REG-SEM-006`の再評価を実施済み（下記「意味評価・Skill validationの追加検証」）。単一Judge・単一試行で、統計的な再現性は未確認。
- **A（PR #23）の共通runtime・保存・CAS／readback・承認との接続**：契約と実コードの照合と、`regression-testing`のverifier登録に必要な入力の引渡しは上記「Aの共通契約との照合と登録依頼」に記録した。登録（`skills/qa-workflow/scripts/**`・`EVALS.md`）はAの編集範囲。新revisionのRun／Activityの実保存・承認、Aが登録したverifierを通すworkflow完了判定は、各ownerの実成果物が必要なためPR #22で結合確認する。
- **実Agent経路・S1〜S17・人間編集8ケース・15＋10条件の最終判定**：PR #22。

### 旧Run／Activityの互換・移行・rollback

- `route_contract_version`が無い保存物は旧形式。読取・検証は従来規則で、完了済みActivityを遡って変更しない（`reg-out-002`は無変更で通る）。
- 旧Runの補助義務が不明な範囲は`project_activity()`が`auxiliary_obligation_unknown:<ref>`を残して`blocked`系の状態にする。`resolve_auxiliary_obligations()`は入力Runを変更せず、現在の利用者指示・policy・選定証拠で解決できた場合だけ新revisionのRunを返す。
- rollbackは本変更のrevertで足りる。保存済み旧形式は書き換えていない。

### 発見したドキュメントと既存コードの食い違い

- `references/data-contract.md`の「Run routeは`manual`またはconcrete `e2e_ref`」は、コード・validator・fixtureの`e2e_testware_ref`と不一致だった。コードに合わせて「E2E testware ref」へ修正した。
- `REG-D008`の旧実装はRunの`required_routes`の`execution_ref`型・重複を検査せず、`project_activity()`と判定が乖離していた。`_required_route_issues()`で規則を揃えた（対象：`validator.py`、`regression_runtime.py::validate_required_routes()`と同一規則）。
- Plan 04は補助routeを`auxiliary_routes`と記載するが、既存のdata contractとtemplateは`auxiliary_testware_refs`のみを定義し、`project_activity()`だけが`auxiliary_routes`を読んでいた。`auxiliary_routes`をdata contractへ追記し、refsだけの旧Runは義務不明として扱う。

### A（PR #23）の共通契約との照合と登録依頼

[A担当文書](./A_runtime-integration.md)の公開契約を実コードと照合した。

- `skills/qa-workflow/scripts/**`にRegression固有の参照は無く、`workflow_runtime.py`は未登録Skillを`unsupported_skill_verifier`で`blocked`にする。`regression-testing`は現在この未登録Skillに当たる。H差分はこの経路を変更していない（`skills/qa-workflow/scripts/**`・`EVALS.md`・共通CIはAのみ編集のため、Hでは触れていない）。
- 保存・承認・CAS／readbackはAの契約に従う。Regressionは保存先・条件付き更新を新設しない。Activity／Runの更新は既存どおり、提供先のnative条件付き保存を確認できない場合に`blocked`、新revisionのRun（`resolve_auxiliary_obligations()`の`new_revision_required`）と新Activityの保存は、Aの`claim_mutable_operation`（operation identity・期待revision・承認ref・resume owner）経由でPR #22に結合確認する。

Aが`regression-testing`をworkflowのverifierへ登録するための入力（A文書「他担当から…正式validator入口、scopeの粒度、正本参照形式と検証fixtureを受け取ってから登録を追加する」への引渡し）：

| 項目                      | 内容                                                                                                                                                                                                                                                                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| owner skill / 検証入口    | `regression-testing`。`skills/regression-testing/evals/deterministic/validator.py::validate(text, expected, eval_id)`（REG-D001〜D017）と`scripts/regression_runtime.py`（`validate_required_routes`・`validate_auxiliary_routes`・`project_activity`・`resolve_auxiliary_obligations`） |
| scopeの粒度               | Baseline／Run／Activity artifact単位。identityは`baseline_ref`／`activity_ref`＋`snapshot_ref`＋`scope_identity`                                                                                                                                                                         |
| 参照形式                  | `source_executions`のkey（`execution_ref`）、`attempt_ref`、`implementation_revision`、`testware_ref`、`route_contract_version`（無ければ旧形式）                                                                                                                                        |
| 状態→workflow状態の投影案 | `完了`＝全義務確定でcurrent相当、`実行中`／`部分完了（ブロック中あり）`／`ブロック中`＝未完了（blocked）、`未開始`＝未着手。`unresolved`に`auxiliary_obligation_unknown:*`・`implementation_revision_mismatch:*`がある間は完了にしない。ownerの内部状態とworkflow全体の状態は別          |
| 固定fixture               | 正常：`reg-out-003`（Run）・`reg-out-004`（Activity完了）。拒否：`reg-out-005`（必須補助未開始）、`tests/skills/evals/deterministic/test_regression_routing.py`の負例、旧形式`reg-out-002`                                                                                               |
| 意味評価                  | `REG-SEM-007`（candidate・Judge結果は`evals/semantic/candidate_outputs/`）                                                                                                                                                                                                               |
| `EVALS.md`の更新依頼      | Regression意味評価の行（現在`REG-SEM-001` ～ `REG-SEM-006`）を`REG-SEM-007`まで、決定論出力評価の件数を`REG-OUT-005`までへ更新（共通ファイルのためHでは未編集）                                                                                                                          |

### 意味評価・Skill validationの追加検証（2026-11-09）

- `REG-SEM-007`（testware route・補助testwareの実施義務）を新規追加した。評価対象Agent（subagent）がSKILL.md・references・templateと`input.md`だけを読んで候補を生成し、別の独立Judge（subagent）が既存runnerの`build_judge_prompt`のプロンプトで評価した。応答は既存runner（`scripts/skills/evals/semantic/run.py`）で正規化した。結果：**pass、rating 3**（Judge所見：入力に無い補助routeのimplementation_revisionとcleanup_status=unconfirmedを補完している軽微な指摘。状態判断・件数には影響なし）。候補は`candidate_outputs/REG-SEM-007.md`、結果は`candidate_outputs/results/REG-SEM-007.json`。
- SKILL.md・guidanceの変更で影響を受ける既存caseを更新後のSkillで再評価した。`REG-SEM-004`（route・actual start）は**pass、rating 4**（`REG-SEM-004-recheck`）、`REG-SEM-006`（補助testware境界）は**pass、rating 4**（`REG-SEM-006`、従来は保存済み候補が無かった）。旧`REG-SEM-004`の保存済み結果は変更していない。
- Judgeは候補生成Agentと別contextで実行し、`reference.md`は生成側に渡していない。評価は単一Judge・単一試行であり、再現性の統計的保証ではない。
- `REG-SEM-007`はPR #30のレビュー指摘（入力に無い補助testwareの`implementation_revision`を候補が補完していた）を受けて、rubricの基準（入力に無い補助revision・cleanup結果を推測せず未解決として扱う）と`reference.md`を追加し、候補を別のAgentで再生成して別Judgeで再評価した。再評価の結果は**pass、rating 3**で、補助revisionは空・`implementation_revision_missing`として未解決に、cleanupは`未確認`として扱われた。Judgeの軽微な指摘は、未解決値を`null`でなく空文字で表した点と、入力に無い補助のexecutor ownerを注記付きで`testware-execution`にした点。`REG-SEM-006`の候補はこのレビュー対応より前に生成した結果で、再生成していない（`REG-SEM-007`・`REG-SEM-004-recheck`は後続の「追加修正」で正規形に合わせて再生成した）。`REG-SEM-006`は補助testwareの境界（TCへ混ぜない）を評価する通常caseで、今回のcleanup既定値・revision必須化・Run照合・testware owner契約は評価基準の範囲外のため、再生成していない。
- `skills-ref validate`（CI `validate-skills.yml`と同じ固定commit）：`skills/*`の23 Skill全てPASS（Windowsでは`PYTHONUTF8=1`が必要）。

### GitHub Actions（HEAD `af127e2`）

Run検証2件の修正commit `af127e2`で、`Code Quality`・`Codex Harness`（codex-contract・windows-launcher）・`Validate Deterministic Output Evals`・`Validate Semantic Output Evals`・`Validate Agent Skills`の5本を個別に確認し、全てPASS（CodeRabbitはDraftのためスキップ）。この記録を追加するcommitは文書のみの変更で、そのHEADの結果はPR #30のChecksで確認する。履歴：`52de5b9`・`c0e170b`・`f25fb16`・`c13f82f`・`aea50bf`・`15bfae7`でも同じ5本がPASS。

PR本文の更新とCodeRabbit threadへの返信・解決は、`gh`の認証アカウントが読み取り専用（`push: false`）のため`UpdatePullRequest`が拒否され実施できていない（権限の迂回はしていない）。更新後の本文は作業用のファイルに用意済みで、書込権限のあるアカウントでの反映が必要。

#### 履歴（HEAD `e134412`、`aea50bf`で同じ5本がPASS）

`Code Quality`、`Codex Harness`（codex-contract・windows-launcher）、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Validate Agent Skills`の全てがPASS。初回HEAD（`82efb1b`）では`Code Quality`が、`REG-SEM-007`候補出力内のJSONのdprint整形差で失敗したため整形して再pushし、最新HEADでPASSを確認した（途中HEADの失敗を最新HEADの成功で読み替えていない）。ローカルのdprintはパス引数指定だと未整形を検出しなかったため、以後はリポジトリ全体の`dprint check`で確認する。

### レビュー指摘（CodeRabbit、16件）の再確認と追加修正

最新HEADに対し、16件の指摘を現行コードとテストで再確認した（古い差分上の指摘もoutdatedを理由に解消済みとしていない）。分類は「解消」（コードとテストで有効性を確認）、「追加修正」（前回の修正に不足があり今回直した）、「該当しない」。

| #  | 対象                                                  | 分類     | 現行コード上の根拠                                                                                                                                                                                            |
| -- | ----------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | validator：不正な`testware_ref`でset操作が例外        | 解消     | `validator.py::_auxiliary_run_issues`が型検証後にsetへ追加。`REG-D007`の`selected_tc_refs`・`member_tc_refs`も`_ref_set()`で検証（実際のLLM候補で`member_tc_refs: null`による例外を確認し今回追加修正）       |
| 2  | 未対応の`route_contract_version`を旧形式として受理    | 解消     | `unsupported_version`で`REG-D009`／`D011`／`D015`が拒否。旧形式はfield自体が無い場合のみ                                                                                                                      |
| 3  | `auxiliary_route_results`が非listだと空listに置換     | 解消     | `_object_list()`が型不正を失敗にする。`route_results`・`source_executions`・`tc_execution_state`・`counts`も同様                                                                                              |
| 4  | Activityから必須補助を削除しても通る                  | 追加修正 | 前回は`REG-D014`のfixture照合だけで、実際のRun検証の代替にならなかった。保存済みRunを正本とする`REG-D018`・`validate_activity_against_run()`・`verify_activity_against_run()`を追加（下記）                   |
| 5  | 補助の完了数・義務不明数を再計算していない            | 解消     | `REG-D015`の`expected_counts`が全件数を独立に再計算                                                                                                                                                           |
| 6  | `executed_tc_count`の水増し                           | 解消     | routeごとの再計算と`state_without_route`検出                                                                                                                                                                  |
| 7  | `reg-out-005`の期待状態                               | 解消     | `expected.json`に`activity_state`・`required_auxiliary_refs`・`run`を指定し、`REG-D014`／`D018`で照合                                                                                                         |
| 8  | `REG-SEM-007`が入力に無い補助revisionを補完           | 解消     | 基準追加・再生成・再判定済み（`REG-SEM-007`の再生成でも未解決として扱われ、rating 4）                                                                                                                         |
| 9  | 候補の`source_executions`・`tc_execution_state`が配列 | 追加修正 | 前回は候補を書き換えずvalidator側を堅牢化するのみだった。今回、契約に正規形（key付きobject）を明記して`REG-SEM-007`・`REG-SEM-004-recheck`を再生成・再判定し、旧候補・旧結果は`*-pre-keyed`として保持（下記） |
| 10 | `select_auxiliary_testware()`の`execution_ready`      | 解消     | `testware_details`省略時は`execution_ready: false`でownerとrevisionを含めない                                                                                                                                 |
| 11 | `execution_ref`の正規化・引継ぎ                       | 解消     | `validate_required_routes()`が有効な`execution_ref`を全route種別で保持。不正値は`invalid_execution_ref:<ref>`                                                                                                 |
| 12 | 必須補助のrevision欠落                                | 解消     | `_revision_confirmed(required=True)`と`implementation_revision_missing:<ref>`。testware routeも同様                                                                                                           |
| 13 | versionなし旧Runの`completion_required`               | 解消     | `project_activity()`の`run_is_v2`と`resolve_auxiliary_obligations()`の`is_v2`                                                                                                                                 |
| 14 | 補助のcleanup欠落                                     | 解消     | 補助の既定値は`未確認`。同じ規則を`testware` routeにも適用（追加修正、下記）                                                                                                                                  |
| 15 | 補助完了数にcleanup終了が必要                         | 解消     | `aux_completed()`が`CLEANUP_CLOSED`を要求                                                                                                                                                                     |
| 16 | route単位の部分完了判定                               | 解消     | `started_units`がroute単位                                                                                                                                                                                    |

新規のインライン指摘は無い（`@coderabbitai full review`後も16件のまま）。

### 追加修正（Run照合・testwareのowner契約・件数・入力検証・候補形式）

| 項目                    | 原因                                                                                                                                                                                         | 修正                                                                                                                                                                                                                                                                                                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Runとの照合             | `REG-D011`はActivity内のrouteだけを見るため、Activity側で必須補助を削除し`completion_required`と件数を整合させる改ざんを通した。`REG-D014`のexpectedはfixture用で実Run検証の代替ではなかった | 保存済みRunを正本として、required route・補助routeの欠落／追加／重複と、`completion_required`・選定根拠・owner・revision・`execution_ref`の変更を検出する`REG-D018`を追加。`validate(..., run=)`の引数または`expected.json`の`run`で渡す。Runを渡せない経路ではv2 Activityの`完了`を失敗にし、それ以外は警告（Run照合済みとは扱わない）。旧形式は対象外。runtimeには`verify_activity_against_run()`を追加 |
| testware routeのcleanup | 新規`testware` routeでも`cleanup_status`欠落が`対象なし`になり完了できた                                                                                                                     | `testware` routeは欠落を`未確認`、`未確認`／`失敗`／`進行中`等は完了不可。`attempt_ref`・`raw_capture_complete`も要求して`実行中`に留める。runtimeとvalidatorで同じ判定。manual／e2eの旧既定値は不変                                                                                                                                                                                                      |
| 件数の再計算            | `unexecuted_tc_count`・`blocked_tc_count`・`auxiliary_source_result_counts`を検証していなかった                                                                                              | 公開される全件数をroute・sourceから再計算して照合                                                                                                                                                                                                                                                                                                                                                         |
| 不正入力                | route配列の要素・`execution_ref`・`route_type`・`cleanup_status`・source等が配列・objectだと集合照会で`TypeError`になる経路があった                                                          | `validate_required_routes()`／`validate_auxiliary_routes()`は`valid: false`、`project_activity()`は`invalid_execution_ref:*`等を`unresolved`へ、`select_auxiliary_testware()`は`invalid_refs`付き`unresolved`、validatorは失敗として扱い、例外で中断しない                                                                                                                                                |
| 意味評価の候補形式      | 候補の`source_executions`・`tc_execution_state`が配列で、runtime・validatorのkey付きobject形と不整合                                                                                         | data-contractに正規形を明記し、`REG-SEM-007`・`REG-SEM-004-recheck`を別Agentで再生成、別Judgeで再評価（いずれもpass、rating 4）。旧候補・旧結果は`*-pre-keyed.md`／`results/*-pre-keyed.json`として保持。形の回帰テストを追加                                                                                                                                                                             |

意味評価のPASSは、machine artifactの正規契約への適合を意味しない。再生成した候補をvalidatorへ通した結果、keyed object形には整合したが、完全適合ではない（Runで補助revisionを`null`とした`REG-D009`、`REG-D013`のidentity、件数・投影項目の不足・不一致）。これは、入力に無い値を推測せず未解決とする評価の性質上、完全なv2 artifactを構成できない例を含む。意味評価は意味の正しさだけを根拠とし、正規契約への適合は`REG-OUT-*`のfixtureと`REG-D*`で別に確認する。

契約の変更は`references/data-contract.md`・`scripts/skills/evals/deterministic/ASSERTIONS.md`へ反映した。次の入力は今回の変更で`完了`にならなくなる（意図した厳格化）：補助sourceが`cleanup_status`を返さない入力、`testware` route sourceがcleanup・attempt・rawを返さない入力、`route_contract_version`なしで`completion_required`を使うRun、Runを渡さずv2 Activityの`完了`を検証する経路。

### 追加レビュー指摘4件（PR #30再レビュー、前回確認HEAD `15bfae7`）への対応

最新HEAD（`15bfae7`）で4件を再確認し、再現テストを先に作成した。4件とも前回HEADで成立しており、新規テスト（`InvalidRunTests`・`TestwareSelectionIdentityTests`・`ActivityStateVerificationTests`・`RunAuxiliaryRefInputTests`、23件）は修正前のコードで全て失敗する（2.4は`TypeError`も再現）ことを確認した。

| # | 指摘                                            | 再現と原因                                                                                                                                                                                                              | 修正（ファイル・関数）                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| - | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | 不正なrequired routeでActivityが完了する        | `route_type: "unknown"`等のrouteを含むRunでも、sourceがPASSなら`project_activity()`が`完了`を導いた。`REG-D018`はRunの集合照会だけでRun自体の妥当性を見なかった                                                         | `regression_runtime.py::_run_contract_issues()`を追加。既存の`validate_required_routes()`／`validate_auxiliary_routes()`を再利用し、`project_activity()`が不正を`unresolved`へ追加して`完了`にしない。`verify_activity_against_run()`は不正なRunを`run_contract_invalid`で`valid: false`にする。`validator.py::_required_route_issues()`をREG-D008とREG-D018で共有し、`_run_contract_issues()`でREG-D018がRun自体を検査。旧Runは版に関する検査だけを免除 |
| 2 | TC付きtestwareの選定情報がRun照合から抜けている | `_ROUTE_IDENTITY`が`testware_ref`・`executor_owner`・`selection_basis`を含まず、`route_ref`・`execution_ref`・revisionを維持した選定情報の変更を検出できなかった。そもそも`route_results`にこれらが投影されていなかった | `project_activity()`がtestware routeに限り3項目を`route_results`へ投影（`manual`／`e2e`は追加なし）。`_ROUTE_IDENTITY`へ追加し、REG-D010が欠落を検出。`reg-out-004`／`005`の`output.md`をruntimeから再生成（各3行の追加のみ）                                                                                                                                                                                                                            |
| 3 | REG-D018がActivity状態の不一致を検出しない      | 全route完了後に`activity_state`を`実行中`へ変えても、REG-D011は`完了`の主張だけを検査するため通過した。routeの`blocked`申告もsourceと照合していなかった                                                                 | `validator.py::_derive_activity_state()`を追加し、識別子（route種別・`execution_ref`・revision・実施義務）とowner sourceだけから状態を独立に再計算。REG-D011（Activity内のrouteから）とREG-D018（Runから）が申告状態と照合する。REG-D010／D015でrouteと補助の`blocked`をsourceから照合。runtimeの`verify_activity_against_run()`は従来から`project_activity()`の再計算と状態を比較している                                                               |
| 4 | REG-D018の不正入力による例外                    | `run.auxiliary_routes[].testware_ref`がlist・dictだと`covered`の集合生成で`TypeError`。比較関数も異常値で例外になり得た                                                                                                 | 集合へ入れる前に`_text()`で型を確認し、不正値は`run_contract_invalid`（`missing_or_invalid_auxiliary_testware_ref`・`invalid_auxiliary_testware_ref:<i>`）として失敗にする（黙って除去しない）。`_identity_key()`は比較不能な値を`repr`にして例外にしない                                                                                                                                                                                                |

runtimeとvalidatorの判定の一致は、14種のscenario（完了・実行中の各原因・部分完了・未開始・blocked・revision不一致・cleanup失敗・execution_ref共有等）で、runtimeが導いた状態をvalidatorが申告値を使わず同じに導出すること、および5状態のそれぞれを別状態へ改ざんするとREG-D011・REG-D018・`verify_activity_against_run()`の全てが拒否することで確認した。同じ不具合を両方が同時に見逃さないよう、validatorはActivityの`executed`・`blocked`・件数・状態を再計算に使わない。

出力形式への影響：`route_results`の`testware` routeに3項目（`testware_ref`・`executor_owner`・`selection_basis`）が増えた。v2形式は未mergeのため保存済みの運用データは無く、影響するのはPR内の`reg-out-004`／`005`（再生成済み）だけ。この3項目を持たないv2 Activityは、Run照合で不一致として扱う（`test_old_v2_activity_without_selection_fields_is_not_silently_accepted`）。旧形式（`route_contract_version`なし）の読取・検証、完了済みActivityの不変性は変更していない。下流consumerを検索した結果、`project_activity()`／`route_results`を読むのはvalidator・`reg-out-*`のfixture・テスト・文書・意味評価の保存済み候補（自由形式で機械検証の対象外）だけで、Aのverifierは未登録のため影響しない。

追加した厳格化の境界：`auxiliary_testware_refs`を宣言したv2 Runは補助routeの集合と一致する必要がある（宣言が無いRunは検査しない。REG-D009の件数検査は従来どおり別）。

### 残存不具合3件（再々レビュー、前回確認HEAD `c13f82f`）への対応

最新HEAD（`c13f82f`、前回から変更なし）で3件とも成立することを再現してから修正した。再現結果（修正前）と修正後の結果は次のとおり。新規テスト（`AuxiliaryOwnerAndBasisInputTests`・`E2ETestwareRefTests`・`AuxiliaryCountTests`、17件）は修正前のコードで失敗またはエラーになることを確認した。

| # | 指摘                                                                | 修正前の再現                                                                                                                                                                                                                              | 修正（ファイル・関数）                                                                                                                                                                                                                                                                                                                                                                                |
| - | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | 補助の`executor_owner`・`selection_basis`が不正型で例外             | 補助routeの`executor_owner: []`／`selection_basis: {"b": 1}`で、`REG-D009`・`REG-D018`が`TypeError: unhashable type`で中断した（runtimeは`valid: false`）                                                                                 | `validator.py::_auxiliary_run_issues()`の集合照会を既存の型安全な`_in()`へ変更。`completion_required`と選定根拠の整合判定は維持し、不正値は正規化せず`invalid_auxiliary_obligation`で失敗にする。同じ責務の`artifact_type`（`REG-D002`）と`decision`（`REG-D016`）の集合照会も`_in()`へ統一した                                                                                                       |
| 2 | E2Eの`e2e_testware_ref`がRun照合から漏れている                      | Runの`e2e_testware_ref`だけを別の参照へ変更しても、`REG-D018`は`pass`、`verify_activity_against_run()`は`valid: true`だった。`["x"]`・`{"a": 1}`・`5`・空白のみの値は`REG-D008`・`validate_required_routes()`が受理した（空文字だけ拒否） | `validate_required_routes()`と`_required_route_issues()`は`e2e_testware_ref`を空でない文字列に限定。`project_activity()`はe2e routeに限り`route_results`へ`e2e_testware_ref`を投影。`_ROUTE_IDENTITY`へ追加し、REG-D010がv2 e2e routeの参照欠落を検出。`manual`の出力は変更なし、E2E実行ownerの処理は変更なし                                                                                         |
| 3 | `auxiliary_testware_count`の不一致を`REG-D018`・runtimeが検出しない | 補助route 1件のv2 Runで、count が`0`・`99`・`-1`・`"1"`・`True`・`1.0`・欠落のいずれでも`REG-D018`は`pass`、runtimeは`valid: true`だった。`REG-D009`も`True`と`1.0`を受理した（`True == 1`）                                              | `validator.py::_auxiliary_count_issues()`を追加し、`REG-D009`と`_run_contract_issues()`（`REG-D018`）が共有する。型は`int`（真偽値を除く）かつ0以上で、`auxiliary_routes`の件数（refs宣言時はその件数も）と一致が必要。runtimeの`_run_contract_issues()`も同じ規則で、`project_activity()`は不正な件数を`unresolved`へ入れ`完了`にせず、`verify_activity_against_run()`は`run_contract_invalid`にする |

契約上の扱い：`auxiliary_testware_count`はdata-contractのRun項目で、`REG-D009`が従来から全Runで必須としていたため、v2 Runでは必須とした（欠落は失敗）。`route_contract_version`が無い旧Runでは、runtime・`REG-D018`とも件数を検査しない（`REG-D009`の従来の規則は維持。ただし真偽値・小数は件数として受理しなくなった）。

修正後の結果：新規17件を含む`test_regression_routing.py`101件、`tests/skills/evals/deterministic`全体391件がPASS。既存テストは弱体化していない（v2 Runの件数が必須になったため、既存テスト内のv2 Runに`auxiliary_testware_count`を追記したのみ）。`reg-out-003`〜`005`のfixtureは件数・e2e参照ともに影響を受けず再生成は不要（e2e routeを含むv2 fixtureは無い。e2e routeの投影はテストで検証）。runtimeとvalidatorの判定一致は、ランダム6000件の比較とActivity・Runへ不正型を注入する8000件の変異ファジング（`validate`・`verify_activity_against_run`・`project_activity`で例外ゼロ）で再確認した（いずれもコミットしない確認）。

互換性：旧形式（`route_contract_version`なし）のRun・Activityの読取・検証、保存済みの`完了`、manual・testwareのroute形式は変更していない。`route_results`のe2e routeに`e2e_testware_ref`が増えた。v2は未mergeで、保存済みの運用データは無い。この項目を持たないv2 Activityは、e2e routeがある場合にRun照合で不一致となる。PR #22への引継ぎ事項に変更はない。

### Run検証の不整合2件（前回確認HEAD `c0e170b`）への対応

最新HEAD（`c0e170b`、前回から変更なし）で2件とも再現してから修正した。新規テスト（`AuxiliaryRefsPresenceTests`・`RunArtifactTypeVerificationTests`、10件）は修正前のコードで失敗する（refs省略の正常系とartifact_type拒否の計13件のsubTest）ことを確認した。

| # | 指摘                                                         | 修正前の再現                                                                                                                                                           | 原因と修正（関数）                                                                                                                                                                                                                                                                                                                                                            |
| - | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `auxiliary_testware_refs`省略時にREG-D009と他経路が不一致    | 補助route 1件・count 1・refs省略のv2 Runで、`REG-D009`は`fail`、`REG-D018`は`pass`、`verify_activity_against_run()`は`valid: true`、`project_activity()`は`完了`だった | `_auxiliary_run_issues()`と`_auxiliary_count_issues()`がrefs省略を空配列として扱い集合・件数を比較していた。`validator.py`の2関数で、v2 Runはフィールドが存在する場合だけrefs一覧との集合・件数比較を行うよう変更し、`_run_contract_issues()`の個別処理（refs未宣言時の差し替えと`REG-D009`の問題の選別）を削除して規則を1か所に集約した。runtime側は既に同じ規則で、変更なし |
| 2 | `verify_activity_against_run()`が`artifact_type`を検査しない | 正常なRunの`artifact_type`だけを`activity`・`baseline`・空文字・`None`・list・dict・未指定へ変えても`valid: true`だった（`REG-D018`は拒否）                            | runtimeのRun検証が`artifact_type`を見ていなかった。`regression_runtime.py::verify_activity_against_run()`に`run_artifact_required`を追加し、`valid: false`・`run_contract_invalid`を返す。`project_activity()`と`_run_contract_issues()`は変更せず、`artifact_type`を省略した簡略Runの投影は従来どおり                                                                        |

refsの契約確認：`references/data-contract.md`とtemplateはrefs一覧を「必須」と明記しておらず、fixtureと`resolve_auxiliary_obligations()`は常にrefsを出力する。runtimeと`REG-D018`の実装・担当文書の既存規則（宣言しない場合は集合比較を行わない）が省略を許容しているため、仕様は変更せず`REG-D009`をこれに揃えた（`data-contract.md`へ明記）。省略と空配列は区別し、`[]`・`["B"]`・重複・`null`・文字列は失敗、省略時のcount `0`・`True`は失敗、補助route 0件・count 0は成功。この仕様は`REG-D009`・`REG-D018`・`verify_activity_against_run()`・`project_activity()`の4経路で同じ結果になる。旧形式（版なし）のRunは従来どおりrefsだけが根拠で、省略は空一覧として扱う。

互換性：v2 Runでrefsを省略した入力は`REG-D009`でも通るようになる（緩和）。`artifact_type`が`run`でないRunを`verify_activity_against_run()`へ渡す呼び出しは拒否される（厳格化。保存済みRunは`artifact_type: "run"`を持つ。fixtureの`expected.json`のrunも該当）。旧形式のRun・Activity、`project_activity()`の簡略入力、完了済みActivityの不変性、fixtureの出力は変更していない。

### CodeRabbit 16スレッドの再確認（HEAD `c0e170b`）

16件すべてを、最新HEADのコードに対する挙動の再実行（コミットしない確認スクリプト）で確認し、いずれも成立しないことを確認した（16項目すべてOK）。上の対応表のコード根拠・テストと対応する。16スレッドはGitHub上ですべて未解決（`isResolved: false`）で、うち9件はoutdated。outdatedであることは解消の根拠にしていない。レビュー状態は`CHANGES_REQUESTED`のままで、これは現行コードの不具合の有無とは別の状態である。

### E／F／Gとの合意の状況

担当文書の着手基準「Gとtestware実行結果、Eと正式TC参照、Fと管理計画の分離を合意した」は**未了のまま**とする。他担当のbranchを読取専用で確認した結果は次のとおりで、いずれも合意の証拠にはならない。

| 相手                   | 確認できたこと                                                                                                                                                                                          | 確認できていないこと／owner／PR #22での再開条件                                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G（PR #29、`42d7834`） | `skills/testware-execution/scripts/contract.py`はcleanup未確認を既定値`未確認`で返し、H契約の「欠落は`未確認`」と整合する。出力templateは「attempt／raw status」「取得完全性」「cleanup状態」を記録する | `attempt_ref`・`raw_capture_complete`・`implementation_revision`のmachine-readableな返却項目名はGに無い。ownerはG。G実成果物（run ref・attempt・raw ref）をHのsource execution形へ対応付け、PR #22の結合でfixtureとして照合できた時点で再開する |
| E（PR #27）            | E担当文書にRegressionへの言及が無い。Hは`tc_ref`を論理TC identityとして受け取り、正式TCの検証・保存形式を持たない                                                                                       | Eの正式TC参照形式とHの`tc_ref`の対応。ownerはE。PR #22でEの正式TC成果物のrefをRunの`required_routes[].tc_ref`へ接続できた時点で再開する                                                                                                         |
| F（PR #28）            | F担当文書は「`qa-workflow`のrouting stateとRegression Runを二重管理しない」と明記している（`F_qa-planning-architecture.md`）。HはRun／Activityを管理計画の正本にせず、suite・工数等を持たない           | 管理計画側のrefからRegression Runを参照する形式の合意。ownerはF。PR #22でFの計画成果物がRun／Activity refを参照する結合を確認できた時点で再開する                                                                                               |

### 移行・rollback・PR #22への引継ぎ（追記）

- 互換性：`route_contract_version`が無い旧Run／Activity、保存済みの`完了`、旧manual／e2eのcleanup既定値は変更していない。`validate()`の`run`引数は省略可能で既存の呼び出し形は変わらない。rollbackは本PRの差分を戻すだけでよく、保存データの移行は無い。
- PR #22へ：①Gの正式な`testware-execution`の返却項目（`attempt_ref`・`raw_capture_complete`・`cleanup_status`・`implementation_revision`）とこの契約の照合、②Aの保存・承認・CASでRunを取得して`REG-D018`／`verify_activity_against_run()`へ渡す結合（Hでは保存済みRunの実取得を行わない）、③Aによる`regression-testing`のverifier登録、④S1〜S17と15＋10条件。
- 完了していない項目：E／F／Gとの分離の合意（上のチェックボックスのとおり未了。内容・owner・再開条件は「E／F／Gとの合意の状況」）。他担当の正本・共有runtimeは変更していない。
