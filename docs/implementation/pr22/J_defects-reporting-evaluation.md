# PR #22 並行実装：J — 欠陥・統合報告・活動評価

## 位置付け

raw結果の正本を保持したまま、欠陥候補・外部Issue追跡、source取得完全性付き統合報告、QA活動改善の実施・再測定を実装する。

- 作業branch：`feat/pr22-j-defects-reporting-evaluation`
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
- [詳細02：承認・取得完全性](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細06：改善の実施・再測定](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)

関連完了条件の主な担当：QA全工程 4・5・6・8・10。開発評価の効率比較はA、QA案件の活動評価はJ。

## このbranchで変更する対象

- 新設`skills/defect-management/**`、`skills/test-reporting/**`、`skills/test-evaluation/**`
- 各Skillの外部Issue参照・raw結果集計・品質／効率評価・改善引継ぎの局所validator／評価

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

- [ ] 外部Issueの権限・source、現在のrun owner単位、計画inventory、source取得契約、既存Knowledge／評価の正本を確認した。
- [ ] F/G/H/I/E/Aとsource ref／raw result／run／retry／承認・source currentnessの受渡しを固定した。

## 作業内容

1. 実行ownerのFAIL／Observation／Findingと確度・証拠から欠陥候補を管理し、外部Issueを参照する。未確認原因で正式登録・closeせず、権限ある明示承認とscope/revisionがある操作だけ更新する。
2. 修正通知は元run ownerへ返し、旧build／不明な変更を誤修正確認扱いしない。外部Issueサービスの現在性・競合・操作済み不明を照合する。
3. Fの予定source inventoryに対し、E2E・一般TC・Regression・探索・API／バッチ・静的テスト／非機能・欠陥の実際の元source refを収集し、取得完全性を独立照合する。
4. 正式TC／retry／attempt／Activity／補助testwareの分母、build／revision／未実行／SKIPを区別し、見かけの100%や誤PASSを拒否する。
5. QA活動5軸（追跡性・品質・効率・プロセス・再利用性。Plan Q08）を評価する。測定不能・悪化・比較不能を成果へ算入しない。（旧記載の「効果・効率・保守／再利用・引継ぎ・改善」は、効果→品質・追跡性、保守／再利用→再利用性、引継ぎ→プロセス、改善→改善の採用・実施・測定の追跡として扱う。2026-11-10にPlanの定義へ統一。）
6. 採用・認可された改善をF/E/実行ownerの正本改版へ返し、実施と次回測定まで検証する。Skill構成そのものの開発時効率比較はAのEVALS評価に残す。

## 依存と引継ぎ

- F→J：QA計画・予定source inventory・品質／終了条件・承認revision。
- G/H/I/E→J：元run／Activity／Finding／TR・coverage等の読み取りref。
- J→G/H：外部修正通知に基づく元runnerの再実行依頼。
- J→F/E/I：採用済み改善の正本改版・Knowledge利用候補。
- A：外部操作の認可・CAS／readbackの共通契約に沿って接続する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 候補→外部Issue参照→修正通知→元実行owner確認が成立し、無許可書込み・重複・誤close・旧build確認を拒否する。
- [ ] 予定母集団と実取得を突合し、欠落・部分取得・旧revision・異なるbuild・retryの偽PASS／偽100%を独立validatorで拒否する。
- [ ] 複数技術のraw結果を元ownerから参照し、正式TC・補助・attempt・Activity・静的結果の計測単位を維持する。
- [ ] 5軸評価と採用／承認→正本改版→実施→次回測定が成立し、未承認・未実施・未測定を完了扱いしない。
- [ ] 新3 Skillの単独・複合発火、負例・権限・監査・deterministic／semantic・既存報告回帰がPASSする。
- [ ] QA全工程Plan 4・5・6と詳細02／06のJ担当範囲について、単独Skillの実Agent・利用可能な実providerの局所受入証拠を記録した。F/G/H/I/Eの実成果物との横断受入はPR #22へ引き継いだ。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装記録と引継ぎ（2026-11-10）

担当Jの実装・局所検証の記録。**担当branch内の完了とPR #22の最終判定は別**であり、横断受入・共有ファイルの登録はPR #22／担当Aへ引き継ぐ。最新HEADのGitHub Actionsは[PR #32のChecks](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32/checks)を正本とする。

### 追加した成果物（担当J所有）

| Skill                       | 入口                                                         | production helper（標準ライブラリのみ・他Skillのscriptに非依存）                                                                                                |
| --------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skills/defect-management/` | `candidate` / `issue-link` / `fix-verification` / `tracking` | `scripts/defect_runtime.py`（`assess-candidate` / `match-issues` / `plan-operation` / `record-outcome` / `fix-request` / `fix-result` / `closure`）             |
| `skills/test-reporting/`    | `snapshot` / `currentness`                                   | `scripts/reporting_runtime.py`（`build-snapshot` / `check-currentness`）                                                                                        |
| `skills/test-evaluation/`   | `evaluation` / `improvement` / `handoff`                     | `scripts/evaluation_runtime.py`（`verify-inputs` / `evaluate-axes` / `advance-improvement` / `summarize-improvements` / `handoff-status` / `propagate-change`） |

各Skillは`SKILL.md`、`references/guidance.md`・`data-contract.md`、`assets/output-template.md`、`evals/`（独立validator、output 5＋5＋4件、semantic 各6件、trigger 各16件×2）を持つ。テストは担当固有のファイルに分けた：`tests/skills/runtime/test_pr32_{defect_management,test_reporting,test_evaluation}.py`、`tests/skills/evals/deterministic/test_pr32_output_contracts.py`。既存Skill・共有runtime・共有評価基盤は変更していない。

### 完了基準との対応

| 完了基準                                                                                  | 実装・検証                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 候補→外部Issue参照→修正通知→元ownerの確認、無許可書込み・重複・誤close・旧build確認の拒否 | `defect_runtime.py`。信頼できる承認サービス由来・認証済み・対象（操作・候補・scope・revision・build・サービス・Issue revision）束縛・期限内の承認だけ`allow`。Issue本文の承認文言、書込み権限なし、重複候補（`reconfirm`）、検索不完全、stale read、同一operation identityの再受付（`already_applied` / `reconcile_first`）、原子的重複防止なしの自動再試行、修正未確認のcloseを拒否。成功は独立readbackがある場合のみ`applied`。修正確認は元ownerへの依頼とし、旧build・同一build・不明な変更・currentでないtestwareを拒否 |
| 予定母集団と実取得の突合、偽PASS・偽100%の拒否                                            | `reporting_runtime.py`と独立validator（helperを使わず成果物から導出を再検証）。欠落source、部分取得・pagination・権限、旧source revision、別build・環境、未確定結果、cleanup未確認、計画外単位、重複・衝突、retry、未承認・改版済み計画を扱う。正当な空集合と取得不能の0件を区別                                                                                                                                                                                                                                            |
| 複数技術のraw結果と計測単位の維持                                                         | `by_unit`で単位別に分母を維持し、`logical primary` / `attempt` / test / review対象 / finding等を合算しない。raw stateは変換しない。静的レビューは全対象のレビュー完了なしに「指摘0件」を主張しない                                                                                                                                                                                                                                                                                                                          |
| 5軸評価と採用→改版→実施→次回測定                                                          | `evaluation_runtime.py`。5軸（追跡性・品質・効率・プロセス・再利用性）を個別に出し総合点を作らない。未測定・比較不能・悪化・改善なしを達成数に含めない。改善は認証済み承認→ownerの新revision→新revision適用後の別活動での測定の順にだけ進み、Knowledge登録は状態を進めない                                                                                                                                                                                                                                                  |
| 新3 Skillの発火・負例・権限・監査・deterministic / semantic・既存報告回帰                 | trigger・semantic・output評価データ、独立validatorの負例（突然変異）テスト、既存`e2e-test-reporting`を含む既存deterministic評価の回帰（下記）                                                                                                                                                                                                                                                                                                                                                                               |
| 変更Skillの`SKILL.md`・入出力・履歴／状態・isolated packaging                             | 3 Skillとも`skills-ref validate`成功。単一Skillコピーでruntime CLIとrepository runnerが動作することをテスト                                                                                                                                                                                                                                                                                                                                                                                                                 |

### 契約

- **source / artifact ref**：`candidate_ref`（`DEFC-`＋元owner・run・result・attempt・scope・正規化症状のhash）、`operation_id`（`DEFOP-`＋候補・操作・Issue ref・expected revision・対象targetのhash）、`snapshot_ref`（`RPT-`＋snapshot本体全体のcontent hash。2026-11-10に、計画・revision・件数のみのhashから変更）。いずれも既存のTR / TCN / CI / TC / Issue IDと衝突しない接頭辞で、グローバルカウンターを持たない。入力の元refは各ownerの`ref`＋`revision`をそのまま保持する。
- **承認**：`source=trusted_approval_service`、`authentication_verified=true`、`authenticated_by`、`principal`、`role`、`policy_revision`、`issued_at` / `expires_at`、対象束縛。承認サービスの実体（認証・policy）は**案件側の決定がなく未接続**。helperは検証だけを行い、承認を作らない。
- **保存**：helperは保存しない。保存が必要な場合は、案件のproviderのcreate-if-absent、expected revisionによる条件付き更新、保存後readbackを必要とし、能力がなければ保存をblockedにする。provider未選定のため**未接続**（仮のproviderを置いていない）。
- **失敗／再開**：外部操作の結果不明は`unknown`とし、自動再試行せず外部サービスの現在状態とreadbackで照合する。報告は計画revisionまたはsource revisionが変わったら`check-currentness`でstaleとし、再集計する。
- **CLI**：stdinはUTF-8固定で、不正なバイト列・重複JSON key・サイズ超過（2 MiB。報告は8 MiB）・非objectは`blocked`（終了コード2）。

### 局所検証の記録

実行環境：Windows 11、Python 3.12.0、ruff 0.16.8（`ruff.toml`の固定版）、dprint 0.55.2（`scripts/format_tracked.py`の固定版）。各コマンドの結果は個別に判定した。

| 検証                                                                                             | 結果                                                                                                 |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| 担当Jのテスト（runtime 82件＋output contract 33件）                                              | 計115件、全件PASS                                                                                    |
| `python scripts/skills/evals/semantic/validate.py`                                               | 26 Skill・183 case                                                                                   |
| `python -m unittest discover -s tests/skills/evals/trigger` / `.../semantic`                     | PASS（semanticは1 skip）                                                                             |
| `python -m unittest discover -s scripts/skills/evals/deterministic/tests` / `.../semantic/tests` | PASS                                                                                                 |
| `skills-ref validate skills/<name>`（3 Skill）                                                   | 成功（Windowsでは`PYTHONUTF8=1`が必要）                                                              |
| `ruff check` / `ruff format --check`（新規Python10件）、`dprint check`（新規md / json）          | PASS（dprint整形済み）                                                                               |
| 既存`python -m unittest discover -s tests/skills/runtime`                                        | 575件中、失敗6・error14・skip6。すべて`test_ci_handoff`と`test_sqlite_workflow_history`（担当A所有） |
| 既存`python -m unittest discover -s tests/skills/evals/deterministic`                            | 323件中、失敗1（`test_pre_start_claim_and_resource_reservation_serialize_mutable_work`、担当A所有）  |

上記の既存テスト失敗は**変更前のbase（`git archive HEAD`のクリーンコピー）でも同数で再現**する。原因はWindowsのファイルロック（WinError 32）、POSIX専用の安全読戻しの非対応、8.3短縮パスの比較で、担当Jの変更とは無関係。Linuxの`ubuntu-latest`で実行されるGitHub Actionsを正本とする。

### 実Agent・実providerの局所受入

- **実Agent（Claudeサブエージェント）の単独経路**：各Skillの`SKILL.md`と参照文書だけを与え、evals・テスト・helper実装は読ませず、独立に用意したfixtureから各2課題を実施させた。結果は独立validatorと独立期待基準で判定した。
  - `defect-management`：原因仮説のFAILを欠陥候補に留め実行ownerへ戻す、Issueのstatus通知だけのcloseを`blocked`にする。validator・期待基準とも一致。
  - `test-reporting`：API未取得のままE2Eのみ完了での「全体100%・完了」の拒否、静的レビュー3/5での「指摘0件・完了」の拒否。判断は正しかった。**ただし1件で、helperが日本語stdinをOSロケール（cp932）で誤デコードし、cleanupが未確認と判定されて独立期待基準と不一致になった**。これは実Agent経由で見つかった担当Jの不具合で、stdinをUTF-8固定にして修正し（回帰テスト追加）、同じfixtureを元のロケールで再実行して期待基準と一致を確認した。
  - `test-evaluation`：作業時間短縮のみでの品質改善主張の棄却、環境違いの品質指標（比較不能）・悪化した追跡性・旧計画revisionでのfinal拒否。validator・期待基準とも一致。
- **発火・routing**：全26 Skillの説明だけを与えた実Agentで、3 Skillの`validation_queries.json`（計48件、順序をシャッフル）を分類させた。46/48一致。不一致2件：`test-evaluation`の「計画改版の影響を受けるアーキテクチャとRiskだけを再確認対象に」→ `none`（対応する`test-management` Skillが未実装）、`test-reporting`の「cleanupが未確認のrunがある場合の報告状態」→ `e2e-test-reporting`（「横断」の語がなく近接）。調整はせず結果を記録。全current Skill同時利用の発火・競合は**PR #22で再評価**。
- **実provider（読取のみ）**：`qa-training-store`の実GitHub Issues 19件を`gh api`で取得し、`match-issues`（revisionに`updated_at`を使用）、`plan-operation`へ接続。重複照合は`human_confirmation_required`（同一欠陥とは断定しない）、書込み権限なし（`push=false`）のためcreateは`read_only`で外部更新なし、検索不完全は`incomplete`。**書込み・CAS・readbackは未実施**（権限・承認主体・案件の合意がない）。

### 未検証・blocked（再開条件）

| 項目                                                                                          | 理由                                                | 再開条件・担当                                                                          |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 外部Issueの書込み、native CAS・条件付き更新・readback、冪等性                                 | 書込み権限・承認主体・案件のIssueサービス選定がない | 案件が提供先と最小権限の資格情報、承認サービスを決定し、A共通契約の保存・承認経路で実証 |
| 承認主体の実認証                                                                              | 認証サービス・policyが未決定（A）                   | 案件の認可サービス決定後に実接続                                                        |
| 報告・評価snapshotの保存（create-if-absent / CAS / readback）                                 | 保存provider未選定                                  | 案件のproviderを決めた上でAの共通契約に接続                                             |
| F／G／H／I／Eの実成果物による横断（計画の`planned_sources`、実run、Activity、TC refとの接続） | 未統合。fixtureによる契約検証のみ                   | PR #22で各ownerが保存した成果物のID・revisionで検証                                     |
| 実Agentでの複合workflow・全Skill同時routing、S1〜S17、人間編集8ケース                         | PR #22の範囲                                        | PR #22                                                                                  |
| `qa-workflow`のworkflow完了判定への登録（owner verifier、`unverified_scopes`の解消）          | 共有`skills/qa-workflow/scripts/**`はA所有          | 下記の登録依頼                                                                          |

### 共有ファイルの登録依頼（A／PR #22）

Jは共有ファイルを変更していない。このため、新3 Skillを加えただけの状態では`Validate Agent Skills`のREADME記載チェック（各Skill名がREADMEに存在すること）が失敗する。**以下の登録をA／PR #22が適用すること**。READMEへの追加だけを適用したクリーンコピー上で、README記載チェック、semantic dataset検証、trigger・semantic・担当Jのテストが成功することを確認済み。

1. `README.md`：ディレクトリ一覧（`qa-knowledge/`の後に`defect-management/`・`test-reporting/`・`test-evaluation/`）、Skill表（`defect-management`：FAIL・Findingの欠陥候補、外部Issue参照・重複照合・認可済み更新、修正確認の再実行依頼／`test-reporting`：複数方式の元結果を計画上の母集団・取得完全性と照合する読取専用の横断報告snapshot／`test-evaluation`：QA活動の5軸評価、改善の採用・改版・実施・次回測定、引継ぎ確認）、責務別ルーティング表。
2. `EVALS.md`：対象Skillの列挙とsemantic表（`DEF-SEM-001`〜`006`、`RPT-SEM-001`〜`006`、`EVL-SEM-001`〜`006`）、output評価（`DEF-OUT-001`〜`005`、`RPT-OUT-001`〜`005`、`EVL-OUT-001`〜`004`）。
3. `scripts/skills/evals/deterministic/common.py`の`CANONICAL_SKILLS`に3 Skill名、`ASSERTIONS.md`に`DEF-D001`〜`018`、`RPT-D001`〜`016`、`EVL-D001`〜`013`。
4. `skills/qa-workflow/**`：routing表・guidance・`workflow-state-template.md`の行、`routing_cases.json`・`routing_candidate_outputs.json`の新Skill分、`workflow_runtime.py`のowner verifier登録。**登録に必要な入口**：各Skillの`scripts/*_runtime.py`、scopeの粒度は`candidate_ref` / `snapshot_ref` / 評価のscope。未登録のままでは、新Skillが検証済み成果物を持つと自己宣言しても完了しない（Aの契約どおり）。

### 担当Jが見つけた文書上の食い違い

- 担当J文書の作業内容5は「効果・効率・保守／再利用・引継ぎ・改善」の5軸としていたが、正本のPlan（Q08）は「追跡性・品質・効率・プロセス・再利用性」。**Planを正本として実装**し、2026-11-10に作業内容5をPlanの定義へ統一した（旧記載は対応付けとして残した：効果→品質・追跡性、保守／再利用→再利用性、引継ぎ→プロセスと`handoff`、改善→改善lifecycle）。
- Plan 02・06は`test-management` / `test-architecture-design`を改善の改版ownerとするが、現branchに両Skillは存在しない。ownerの名称はdata contractの値として扱い、実成果物による接続はPR #22で行う。

### PR #22へ渡す横断検証項目

- 実F／G／H／I／Eの成果物（予定source inventory、元run・attempt・cleanup、Regression Activity、Finding）を`test-reporting`の入力形式へ接続し、source ID・revision・currentnessで再取得できること。
- 外部Issue実接続（権限・承認・CAS・readback・重複防止）と、修正通知→元owner再実行→結果参照の実run。
- 改善の採用→`test-management`等の改版→次回活動での測定を、実ownerの成果物で通すこと。
- 全current Skill同時利用のrouting、S4・S6・S7・S9・S10、詳細02／06の最終照合、Plan詳細07の効率比較。

## レビュー指摘への対応と再検証（2026-11-10 第2回）

[PR #32](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32)の再レビュー指摘6件を、既存実装・Plan・データ契約と照合した。**6件とも問題あり**で、いずれも変更前のコード（commit `0e373f5`）に対する回帰テストで再現し、担当Jの実装として修正した。最新HEADのGitHub Actionsは[PR #32のChecks](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32/checks)を正本とする。過去の記録（上の「実装記録と引継ぎ」）は当時の判断・結果として残し、本節で更新した事項を示す。

### 指摘ごとの結果

| #                        | 確認結果 | 原因（根拠）                                                                                                                                                                                                                               | 修正                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 回帰テスト                                                                                                                                 |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 2.1 `snapshot_ref`       | 問題あり | 旧実装は計画ref・revision、source ID・revision・取得件数だけをhashし、取得完全性・判定・状態・取得内容が違っても同じrefになった（`reporting_runtime.py`の`snapshot_basis`）。保存契約のimmutable・create-if-absentでは別内容が同一視される | refをsnapshot本体全体（件数・完全性・終了判定・各sourceの`records_digest`・期間・計画現在性を含む）のcontent hashにした。入力の並び順には依存しない。validatorは独立にhashを再計算する（`RPT-D017`）                                                                                                                                                                                                                                                           | `SnapshotIdentityTests`：状態・result ref・cleanup・unit ref・現在性だけが異なる入力が別refになる、並び順で変わらない、refが本体hashと一致 |
| 2.2 計画revisionの現在性 | 問題あり | `current_plan_revision`が未指定（`None`）だと`not in (None, revision)`で不一致扱いにならず、改版済みと確認不能が区別されなかった。承認済み・全sourceが完全なら`satisfied`になり得た                                                        | 未指定・空は`plan_currentness_unverified`、不一致は`plan_revision_superseded`、一致は`current`を`plan_currentness`で区別。未確認・改版済み・未承認（失効・取消を含む）・計画ref／revision欠落は終了判定を`undetermined`にする。`check-currentness`も`current` / `stale`（変化）/ `unverified`（現在値を取得できない）に分けた。validatorは承認状態と現在性から終了判定を独立導出（`RPT-D009`・`D019`）                                                         | `PlanCurrentnessTests`                                                                                                                     |
| 2.3 計測単位の合算       | 問題あり | `_evaluate_criterion`が`source_ids`の`planned_total`とPASS件数を単位に関係なく合算していた。既存テストの基準（E2Eのlogical primaryと個別テストを合算）自体がPlanの分母・単位契約に反していた                                               | 基準は単一の計測単位かつ適用可能な方式のsourceだけを対象にし、それ以外は`unknown`（`mixed_units_or_kinds_not_summable` / `metric_not_applicable_to_source_kind`）。logical primaryとattempt、正式TCと個別テスト、補助testware、実行結果と静的レビューを区別。既存テストの基準を単位ごとに分割。validatorは基準の単位・方式を独立に検査（`RPT-D018`）。あわせて`executed_rate`がSKIP・blockedを実行済みに数えていた同種の問題を修正（PASS・FAIL・判定不能のみ） | `MeasurementUnitContractTests`                                                                                                             |
| 2.4 重複source ID        | 問題あり | `retrievals`を辞書化する際、同じ`source_id`は最後の取得結果で上書きされ、並び順だけで完全性が変わった。同種の問題として、同じ`result_ref`で内容が異なるレコードも先勝ち、同じ単位refの衝突でも先のレコードが件数に残った                   | 同じ`source_id`は曖昧な取得として当該sourceを未完了にし（どれも採用しない）、`source_id`のない取得も報告。内容が異なる`result_ref`の再利用と同じ単位refの衝突は、どれも採用せず`conflicting_unit_refs`へ。すべて入力順に依存しない                                                                                                                                                                                                                             | `DuplicateAndConflictOrderTests`（全順列で同じ結果・同じref）                                                                              |
| 2.5 評価軸全体の判定     | 問題あり | `evaluate_axes`は改善した指標が1つあり悪化がなければ、比較不能・未測定・無効な指標が混在していても軸全体を`improved`とし、`improved`の主張を採用した                                                                                       | 軸全体の傾向を全指標から導出（`improved` / `partially_improved` / `mixed` / `worsened` / `invalid` ほか）。軸全体の`improved`は、悪化・比較不能・未測定・無効がない場合だけ。指標単位の主張は`metric_improved`＋`metric_id`。5軸以外の指標は`invalid_metrics`で明示（黙って捨てない）、`invalid_metrics`がある評価は`final`にできない。軸の定義はPlan Q08のまま。validatorも独立に傾向と主張を導出（`EVL-D004`・`D005`・`D014`）                               | `AxisWideJudgementTests`                                                                                                                   |
| 2.6 対象期間             | 問題あり | `period`は文書だけにあり、runtimeは期間を照合しなかった。Plan詳細02の「別build・別環境・別期間のrunは適合するものだけ集計」を満たしていなかった。取得時の`query_filter`は文字列で機械検証できず、保証にならない                            | 計画（またはsource）の`period{from, to}`と、レコードの`executed_at`を照合。期間外は`period_mismatch`、時刻がない・解釈できない場合は`period_unverified`で除外し、不正な期間定義は`plan_period_invalid`。期間未宣言なら絞り込まない。静的レビュー対象にも同じ規則                                                                                                                                                                                               | `PeriodTests`（境界は両端を含む、タイムゾーン、source単位の上書き）                                                                        |

### 周辺・3 Skill全体の再レビューで追加修正した問題

根拠のあるもの（コードとテストで再現）だけを修正した。

- **承認の束縛（`defect-management`・`test-evaluation`）**：束縛値が`None`の項目は照合を飛ばしており、既存Issue向けの承認を新規登録（create）へ流用でき、scope欠落が無条件に通った。承認の対象は完全一致（`None`も一致）とし、候補のscope欠落・改善の提案revision／scope欠落・引継ぎ項目のrevision欠落は拒否する。
- **修正確認と候補の紐付け**：closeが別候補の`fix_confirmed`を受け入れ得た。依頼・結果に`candidate_ref`を持たせ、close／reopenは同一候補の確認だけに限定。依頼した**すべての**TC / testwareを指定revisionで実行した結果（`executed_targets`）がなければ`pending`にし、一部のTCのPASSで修正確認済みにしない。
- **結果の記録**：更新系の成功は、計画したIssueの更新であることと`issue_ref`のreadbackを要求（別Issueの成功を採用しない）。呼出し結果が不正でも例外にならず`unknown`。
- **評価入力**：content hashのない入力は元実績が未改変であることを確認できないため未検証とした。
- **標準入力**：stdinはUTF-8固定で、読取りを上限＋1バイトで打切る。OSロケール（cp932）で日本語を誤デコードして`成功`をcleanup未確認と判定する不具合は第1回で修正済み。
- **状態値**：実行系と静的レビューの状態値域を分け、相互の値を受け入れない。`attempt`単位には整数の`attempt_no`を要求。

指摘どおりで修正不要だった項目はない。「指摘に誤りがある」と判断した項目もない。

### 追加・変更した検証データとテスト

- 追加output ケース：`DEF-OUT-006`・`007`、`RPT-OUT-006`〜`009`、`EVL-OUT-005`・`006`（計22件）。semantic：各Skillに案件境界の追加ケース（`DEF-SEM-007`、`RPT-SEM-007`・`008`、`EVL-SEM-007`、計187 case）。独立validatorに`RPT-D017`〜`D021`、`EVL-D014`、`DEF-D009`・`D013`の強化を追加。
- テストは`test_pr32_*`の4ファイルで合計169件（runtime 124件、output contract 45件）。validatorの負例（突然変異）テストを追加。

### 再検証の記録

固定版のruff 0.16.8・dprint 0.55.2を使用。各コマンドは個別に判定した。

| 検証                                                                               | 結果                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 変更前コード（`0e373f5`）に対する新規回帰テスト                                    | 報告：50件中、失敗38・error4（subTest含む）／評価：34件中、失敗10・error1／欠陥：40件中、失敗7・error2。いずれも修正後は全件PASS（指摘6件すべて再現）                                                                                                                                                                                          |
| 担当Jのテスト（`test_pr32_*` 4ファイル）                                           | 169件、全件PASS                                                                                                                                                                                                                                                                                                                                |
| `ruff check` / `ruff format --check`、`dprint check`（変更・新規のpy / md / json） | PASS                                                                                                                                                                                                                                                                                                                                           |
| `skills-ref validate`（3 Skill）                                                   | 成功                                                                                                                                                                                                                                                                                                                                           |
| `python scripts/skills/evals/semantic/validate.py`                                 | 26 Skill・187 case                                                                                                                                                                                                                                                                                                                             |
| semantic・trigger・`scripts/skills/evals/*/tests`                                  | PASS（semanticは skip 1・2件）                                                                                                                                                                                                                                                                                                                 |
| 既存`tests/skills/runtime`（620件）                                                | 失敗6・error14・skip6。**すべて`test_ci_handoff`・`test_sqlite_workflow_history`（担当A所有）で、第1回と同じWindows固有の失敗**                                                                                                                                                                                                                |
| 既存`tests/skills/evals/deterministic`（335件）                                    | 失敗1（`test_pre_start_claim_and_resource_reservation_serialize_mutable_work`、担当A所有）。第1回と同じ                                                                                                                                                                                                                                        |
| 最新base（`0e99617`）に担当Jを重ねたクリーンコピー                                 | README登録なしでは`Validate Agent Skills`のREADME記載チェックが失敗（新3 Skillが未記載）。**README行だけを共有ownerが登録した状態を模した一時コピー**では、repository structure、semantic（28 Skill・191 case）、trigger、`scripts/*/tests`、担当Jのテスト、既存`test_repository_integration`・`test_workflow_non_e2e_skills`を含む171件がPASS |

Windows固有の既存失敗は、変更前のbase（`git archive`のクリーンコピー）で同数が再現することを第1回に確認済み。今回の変更はこれらのテストに触れていない。

### 実Agent・実providerの局所再受入

修正後の3 Skillで、今回の指摘に直結する課題を独立したfixtureで実Agent（サブエージェント。`SKILL.md`と参照文書だけを与え、evals・テスト・helper実装は読ませない）に実施させ、独立validatorと独立期待基準で判定した。

- `test-reporting`：(A) 異なる単位を合算した終了基準と現在の計画revisionの未確認 → 基準は`unknown`、`plan_currentness=unverified`、終了判定`undetermined`。(B) 期間外のレコードと重複したsource取得 → API・E2Eとも未完了。期待基準と一致。
- `test-evaluation`：品質軸で改善・比較不能・未測定が混在 → 軸の傾向は`partially_improved`、軸全体の「改善」主張は棄却、指標単位の改善だけを`metric_improved`として採用、`final`にしない。一致。
- `defect-management`：依頼した2TCのうち1TCだけのPASS → `pending`（`verification_targets_not_all_executed_at_requested_revision`）で修正確認にもcloseにもしない。一致。
- **実provider（GitHub Issues）**：第1回の読取り専用接続の結果（書込み権限なしでcreateは`read_only`）は、承認束縛・修正確認の変更後も同じ契約で有効。書込み・CAS・readbackは引き続き**未実施**。

### 未解決・blocked

- **README等の共有登録が未適用**：`Validate Agent Skills`のREADME記載チェックは、共有ownerによる登録（担当A／PR #22）が適用されるまで失敗する。**これは担当Jの実装不具合ではない**（共有登録を適用した状態を模した検証で担当Jの検査はすべてPASS）。登録内容は「共有ファイルの登録依頼」のとおり。共有ファイルは変更していない。
- 外部Issueの書込み・CAS・readback、承認主体の実認証、保存providerへのsnapshot保存は、案件側の決定がなく未接続のまま（再開条件は上表のとおり）。
- `test-evaluation`の「計画改版の影響を再確認する」依頼のrouting（`test-management` Skill未実装）と、`test-reporting`と`e2e-test-reporting`の近接した依頼の発火（第1回に記録した2件）は、PR #22の全Skill同時利用評価で再確認する。

### PR #22への追加の引継ぎ

- 計画の`period`と、各ownerの結果の`executed_at`、`current_plan_revision`の取得経路（F／各実行ownerが提供）をPR #22の実成果物で接続する。担当Jのrunnerは、取得できない場合に未確認として扱う。
- 実成果物の終了基準（F）は、計測単位ごとに分割された`source_ids`で書かれている必要がある。単位をまたぐ基準は担当Jでは`unknown`になる。
- 評価入力の`content_hash`、承認の`candidate_ref` / `issue_ref` / `artifact_revision`の束縛を、Aの承認・保存契約の実装で提供する。
- 共有登録（README・EVALS・`ASSERTIONS.md`・`common.py`・`qa-workflow`）に、新設の評価ID（`RPT-D017`〜`D021`、`EVL-D014`、`DEF-OUT-006`・`007`、`RPT-OUT-006`〜`009`、`EVL-OUT-005`・`006`、`DEF-SEM-007`、`RPT-SEM-007`・`008`、`EVL-SEM-007`）を含める。

### 判定

- **担当Jの局所実装**：指摘6件と周辺の同種の問題を修正し、回帰テスト・独立validator・実Agent再受入で確認済み。担当J所有の既知の実装不具合は残っていない。未接続の外部要素（実provider・承認主体・保存先）は、blockedとして上に記録した。
- **PR #32全体のCI・レビュー**：共有ownerによるREADME登録が未適用のため、`Validate Agent Skills`は失敗する状態。登録の適用後に再確認が必要で、現時点では完了と判定しない。PR #22の横断統合・最終受入は担当Jの範囲外。

## 残指摘への対応と再検証（2026-11-10 第3回）

[PR #32](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32)の残指摘（評価軸の誤判定）と、CI失敗の扱いを確認した。最新HEADのGitHub Actionsは[PR #32のChecks](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/32/checks)を正本とする。

### 評価軸の誤判定（`metric_improved`）

- **確認結果：問題あり**。`evaluate_axes`は`metric_improved`を`metric_id`の状態だけで判定し、主張の`axis`と指標の`axis`の一致を見なかった。効率軸の指標`E-time`が改善していれば、`{axis: quality, assertion: metric_improved, metric_id: E-time}`が採用された。同じ`metric_id`が複数の軸にあると、後の指標が先の指標を上書きした。
- **同種の問題（validator）**：独立validatorの`EVL-D005`も`metric_id`だけで判定していた。さらに棄却の突合せが`(axis, assertion)`だけで、同じ軸の支持される指標主張と支持されない指標主張が互いを隠した。
- **修正**：
  - runtime（`evaluation_runtime.py`）：指標を`(axis, metric_id)`で引き、主張の軸に属し、かつその指標のstatusがすべて`improved`のときだけ採用する。
  - validator（`validator.py`）：同じ規則で独立に導出し、指標主張の棄却は`(axis, metric_id)`で突合せる。
  - 文書（`references/data-contract.md`・`guidance.md`）：軸の一致を明記した。
- **回帰テスト**：
  - `AxisWideJudgementTests`に2件。別の軸の指標、軸と指標の取り違え、5軸以外の軸の拒否、正常な主張の維持、同じ`metric_id`が複数の軸にある場合の軸ごとの判定。
  - `ReviewDrivenEvaluationValidatorTests`に1件。不当な採用の検出、正しい棄却と同軸の正常な主張を誤検出しないこと。
  - 変更前のコードでは3件とも失敗し、修正後に全件PASS。既存の正常系（`EVL-OUT-001`〜`006`）は変更なし。

### 検証の記録

固定版のruff 0.16.8・dprint 0.55.2を使用。各コマンドは個別に判定した。

| 検証                                                                           | 結果                                                                                                                                                   |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 担当Jのテスト（`test_pr32_*` 4ファイル）                                       | 172件、全件PASS（第2回の169件＋3件）                                                                                                                   |
| `ruff check` / `ruff format --check`、`python scripts/format_tracked.py check` | PASS（227ファイル）                                                                                                                                    |
| `git diff --check`                                                             | PASS                                                                                                                                                   |
| `skills-ref validate skills/test-evaluation`                                   | 成功                                                                                                                                                   |
| `python scripts/skills/evals/semantic/validate.py`                             | 26 Skill・187 case                                                                                                                                     |
| `tests/skills/evals/semantic`・`scripts/skills/evals/semantic/tests`           | PASS（27件、skip 2）                                                                                                                                   |
| 既存`tests/skills/evals/deterministic`（336件）                                | 失敗1（`test_pre_start_claim_and_resource_reservation_serialize_mutable_work`、担当A所有、Windowsの短縮パス表記による既知の失敗）                      |
| 既存`tests/skills/runtime`                                                     | 622件中、失敗6・error14。第2回と同じ、担当A所有の`test_ci_handoff`・`test_sqlite_workflow_history`のWindows固有の失敗だけ（担当Jのテストの失敗はない） |

### 共有登録の扱い（変更なし）

README・EVALS・`ASSERTIONS.md`・`common.py`・`qa-workflow`は変更していない。`Validate Agent Skills`の失敗は、README記載チェックが新3 Skillを見つけられないことだけが原因で、担当Jの実装不具合ではない。登録内容と新設の評価IDは「共有ファイルの登録依頼」と第2回の「PR #22への追加の引継ぎ」のとおり。今回新設の評価IDはない（`EVL-D005`の強化のみ）。

### 判定

- **担当Jの局所実装**：残指摘を修正し、回帰テストと独立validatorで確認済み。担当J所有の既知の実装不具合は残っていない。
- **PR #32全体のCI**：共有登録が未適用のため`Validate Agent Skills`は失敗する状態で、完了と判定しない。
- **PR #22の横断受入**：担当Jの範囲外で、未実施。
