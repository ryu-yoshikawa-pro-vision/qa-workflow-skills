# PR #22 並行実装：A — 共通runtime・保存・CI基盤

## 位置付け

共通の検証・routing・保存／承認・製品CI受渡しの機構を実装・局所検証する。**全Skillの横断受入と統合作業はPR #22**に限定し、A担当branchでは実施しない。個々の意味判断や成果物正本は各Skillに残す。

- 作業branch：`feat/pr22-a-runtime-integration`
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
- [詳細02：保存・承認・集計](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細03：workflow・受入](../../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)
- [詳細04：runtime・Regression](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)
- [詳細07：効率比較](../../plans/2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)

関連完了条件の主な担当：開発連動QA 2・3・7・11・15、QA全工程 8・9・10のうち、共通runtime・保存・CI・評価基盤を実装する。全体受入の実施・判定はPR #22。

## このbranchで変更する対象

- `skills/qa-workflow/scripts/**` と必要な `skills/qa-workflow/` の契約
- `skills/qa-workflow/assets/project-context-template.md` の互換調整（Bの必要条件を受付）
- 共有評価基盤、`EVALS.md`、共通CI・READMEのA担当実装部分（横断受入記録はPR #22）
- 製品CI向けの成果物検証と案件別受渡し接続（接続先／認可の決定を含む）

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

## 共通契約の確定と共有（後続実装の前提）

- [ ] 実装開始時点の既存runtime／正本schema・呼び出し元／下流・CI・PR #17／#10を確認し、既存契約の再利用と変更が必要な契約を区別した。
- [ ] B〜Jで共通利用するsource／artifact ID、revision／currentness、scope、owner、保存先のnative CAS・履歴／readback、承認主体・対象revision、blocked／resume、証拠・実行結果・cleanupの**公開引継ぎ条件**を、各正本ownerの責務を保って担当Markdownまたは検証レポートへ記録し、PR #23から参照できるようにした。
- [ ] 契約ごとのschema・固定fixture・正常例／拒否例、既存資産・legacyの互換性、共有ファイルの編集ownerをB〜Jへ伝達した。
- [ ] 保存provider・製品CI受渡し・承認者等の案件固有の未決定事項は仮の既定値にせず、未決定／blockedの範囲、決定元、再開条件を記録した。
- [ ] 共通契約を確認しただけでA〜Jの実成果物の横断接続を完了扱いしていない。実成果物による統合受入はPR #22へ引き継ぐ。

この文書のチェックリストは**共通契約の確定完了を宣言するものではない**。証拠と契約がPR #23に保存されるまで、B〜Jの依存実装へ確定済みと通知しない。

## 着手基準

- [ ] PR #22の固定HEAD、既存CIと対象Skill・テスト・PR #17／#10の変更範囲を読んだ。
- [ ] A〜Jの編集owner表、保存先・承認・ID／revision／状態／evidenceの最小引継ぎ契約を各担当と共有した。
- [ ] 実保存先、対象製品repoのCI権限、比較測定方法の可否を確認し、不足はblockedで記録した。

## 作業内容

1. PR #17・#10を含むbase/関連実装、既存23 Skill、runtime・評価runner・CIの差分／呼び出し元・先を確認し、A〜Jの正本owner・入力出力・依存revisionを固定する。
2. `_default_expected_runtime_units()`等の未登録Skill・未検証scope・空evidenceの完了判定を修正し、新設14 Skillの検証／routing／partial rerun／別セッション再開を維持する。
3. provider-native create-if-absent／update-if-revision(CAS)・履歴・readback・操作開始前記録・保存失敗／重複時の再照合を、ownerごとの既存保存経路へ接続する。単なるread-compare-writeをCAS扱いしない。
4. 対象scope・revisionに紐付く認証済み承認主体を検証し、未承認／期限切れ／権限不足／未信頼資料内指示を拒否する。外部Issueの意味処理はJに残す。
5. source inventory／差分分類／正規成果物を製品CIへ渡す方式を案件で選定し、接続可能な環境で旧HEAD・欠落・未分類・hash不一致をfailさせる。未設定なら実接続をblockedで保持する。
6. S1〜S17に必要な共通検証器・評価形式・fixture・CI契約を実装し、A担当経路を局所検証する。A〜Jの実成果物をつなぐ総合受入、全current Skill同時利用と実Agent発火・実provider横断検証はPR #22で実施する。
7. Plan詳細07の5条件（初回・変更なし・局所コード変更・外部仕様改版・中断再開）を測定する共通基盤と独立品質判定を実装・局所検証する。全体の同条件実Agent比較・改善判定・再測定はPR #22で実施する。

## 依存と引継ぎ

- B→A：source inventory・機能／変更差分と製品CIが検証すべき参照。
- C／D／E／F／G／H／I／J→A：正本ref・revision・validator・required route・独立fixture・negative case。
- A→全担当：runtime登録・save/approval/handoff契約。共通ファイル編集はAのみ。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 未登録Skill・空evidence・旧revision・scopeの食違いを完了扱いしないruntime／routingと、既存経路の互換性が自動テストで確認された。
- [ ] native CAS・履歴・readback・承認・操作状態不明・二重受付・局所再開の正常／拒否／失敗テストが実providerを含めて成立した。
- [ ] 製品CI受渡し機構・決定論的照合・artifact欠落／旧版のfail条件をA担当の独立経路とfixtureで検証した。担当の実接続が可能なら実証し、未接続は記録した。全owner成果物を通す実製品CI総合受入はPR #22へ引き継いだ。
- [ ] S1〜S17・別セッション再開に必要なA担当の共通契約と独立fixtureで局所検証した。各担当の実成果物を用いたS1〜S17総合受入はPR #22へ引き継いだ。
- [ ] Plan詳細07の5比較の計測・独立品質判定・未測定区分を実装し、局所試験を記録した。5条件の横断実測・比較・悪化時再測定はPR #22へ引き継いだ。
- [ ] A担当のruntime／共有評価基盤・Skill登録・局所routingと関連GitHub Actions／formatter／docsを検証した。全current Skill同時発火・全体CIの統合評価はPR #22へ引き継いだ。
- [ ] 15＋10条件および詳細01〜08の**A担当部分**の実装証拠と、PR #22へ渡す未完了の統合条件を整理した。全条件の最終照合はPR #22のみで行う。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をA担当の共通契約として実装・局所検証し、PR #22で再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 現行実装の公開契約と担当別引継ぎ（2026-11-08）

以下はPR #23の実装と固定fixtureで確認できる契約。担当B〜Jの未統合成果物、未選定の外部provider、製品CIの本番接続を確定済みとは扱わない。

### 実装した共通経路

- **workflowの完了判定**：`skills/qa-workflow/scripts/workflow_runtime.py`では既存のruntime-v2 rootを持つ6 Skill（`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`）だけを既存verifier経路へ通す。未登録Skillは`unsupported_skill_verifier`をblocking issueに追加し、対象`skill`・`target`・`execution_range`を`payload.unverified_scopes[]`へ保持する。既存対応Skillの`runtime_units`／Entityのcurrent結果は捨てない。新設14 Skillをこの6 SkillのMachine Entity契約へ無条件に移行しない。
- **既存のverified state**：対応済みSkillは`verify_runtime_evidence`が返した`current_structure_state`の`runtime_results`／`carry_forward_entities`／`previous_ci_id_state`を既存`validate_current_structure_state`で検証する。入力は`workflow_ref`（canonical UUID）、`workflow_scopes[]`の`skill`・`target`・`execution_range`・`normalized_input`、`runtime_units[]`、`current_runtime_units[]`、`current_entities[]`、`unsupported_item_closures[]`。保存済みの旧versionや他workflowの検証済みという文面だけをcurrent証拠として受理しない。
- **履歴・native更新**：既存`artifact_graph.py`の`create_workflow_state`、`commit_qa_workflow_baseline_local`、`read_qa_workflow_artifact_revision_local`、SQLite conditional write、操作claim／復旧の既存経路を再利用する。SQLiteのworkflow stateはcurrent更新と旧／新revisionのsnapshotを同じtransactionで保存し、`read_sqlite_workflow_state_revision`で過去revisionを取得する。履歴のない旧DBでは過去記録を捏造せず、履歴連続性がないことを`historical_revision_available=false`で示す。ローカルの単一hostに限る原子性・exact historical readbackであり、遠隔providerにも保証があるとは扱わない。
- **shared resourceの予約・解放**：`reserve_shared_resource`のlocal経路は`reserve_sqlite_shared_resource`へ統一し、`read_sqlite_shared_resource`でowner／provider revisionを取得する。`release_shared_resource(..., reservation_root=..., resource_ref=...)`がowner状態・cleanup・expected revisionを検証し、SQLite transactionでstatusとrevisionを条件付き更新する。旧JSON予約があれば移行をblockし、旧版file予約と同時運用しない。これは単一hostのlocal providerだけの実装であり、承認事実の認証や複数hostの排他性を証明しない。
- **操作開始前の記録**：`claim_mutable_operation(..., operation_details=...)`はowner／scope／操作種類／対象ref／source・artifact revision／期待revision／承認ref／必要権限／resume ownerを、既存workflowのclaim rootに原子的作成・独立読戻しします。同一operation identityの再受付、権限不足で読戻し不能、metadata不正、symlink先への作成をblockし、未実施の副作用を再実行しません。これは実ownerの認可を証明する機能ではありません。
  - `read_mutable_operation_claim(..., expected_claim_revision=...)`で後続セッションが同じclaimとrevisionを再取得し、履歴不一致・欠落・非正規化内容を拒否。読戻しでは`may_start`を返さず、副作用の二重実行を許可しない。
- **製品CI受渡し**：`skills/qa-workflow/scripts/ci_handoff.py`は`qa-ci-handoff-v1`形式の信頼済み`expected`、候補`manifest`、読戻し済みartifactを比較する。必要なbase／head SHA・build ref、source inventoryのref／revision、変更パスの全件、許容分類、owner／scope／artifact ref／revision／SHA-256、source依存を照合する。結果`pass`は機械的受渡し整合のみ。外部保存先から信頼済み`expected`を生成する経路、認可・承認、実製品CIでの実行はまだ接続していない。承認必須の入力は`approval_provider_unconfigured`で`blocked`。詳細は`skills/qa-workflow/references/ci-handoff.md`。
  - artifactはsource ref／revisionが必須。POSIX CIでのsymlink経由読戻しとサイズ超過を拒否し、承認未接続とrevision不一致が同時にある場合は不一致を`fail`として残す。
- **効率比較**：`scripts/skills/evals/workflow_efficiency.py`はPlan詳細07の5シナリオについて、比較元／変更後各2回以上の試行ref・source revision・scope・独立期待基準・品質／安全の判定ref・実測取得元を比較する。測定不能はnullと理由で表し、必要指標不足・品質未PASS・条件不一致では効率改善と判定しない。実Agentを起動せず、実測値や意味評価は作成しない。形式は`EVALS.md`を参照。
  - 同じrunを複数回の独立試行として数えることを禁止し、重複`trial_ref`／`run_ref`、JSON重複キー、入力サイズ超過を拒否する。

### B〜Jが引き渡す入力・owner責務

- **B**：Project Contextが指定した有効なsource snapshot、source inventoryの完全性と各source ref／revision、base／headと変更パスの全件、差分分類の正規成果物。機能分析の識別と意味判断はBの正本に残す。
- **C／D／E／F／G／H／I／J**：各担当が所有する成果物の`owner skill`、scope、artifact refと保存revision／content hash、入力source refs／revisions、利用したvalidator／runtimeと実際の検証結果ref、必要な承認、依存するownerのref／revision、現状態（current・stale・blocked・unsupported）、未解決・再開先を提供する。既存の成果物形式・stable ID・正本ownerを上書きせず、担当内の正常／拒否fixtureを添える。
- **G／H／Jの実行／報告**：元run／attempt ref、runの開始証拠、結果の最終確定、必要cleanupの実施と保存readback、部分取得・未実行を区別する。共通runtimeは実測を再採点しない。実行や集計の判定は各担当Skillの責務。
- **共通契約変更の窓口**：`skills/qa-workflow/scripts/**`、`EVALS.md`、Project Context templateおよび共通CIはAが編集する。他担当から新Skillの正式validator入口、scopeの粒度、正本参照形式と検証fixtureを受け取ってから登録を追加する。現時点で未登録の新Skillは、検証済みの成果物があると自己宣言しても完了できない。

### 保存・承認と失敗／再開の条件

新規保存はprovider-native create-if-absent、更新は提供側が原子的に保証するexpected revisionによるCASを必要とする。旧revisionの履歴取得と書込み後の独立readbackがない操作はblocked。複数ownerの個別CASだけで横断commitが成立したとは扱わない。

承認対象の操作／scope／成果物revision／source buildと、信頼できるサービスで認証した主体・ロール・有効期間・policy revisionが一致する場合だけ副作用を許可する。文書やIssueに書かれた`approved`は単独の証拠にならない。状態不明の副作用を再実行せず、開始前operation identityと元ownerの実保存状態から復旧する。実provider・承認主体・操作対象repoの権限は案件側の決定がなく未接続。決定元は案件Project Context／正式な認可サービスと製品CI管理者。受入再開には提供先と資格情報を安全に用意し、native CAS／履歴／readbackと権限を実証する必要がある。

### PR #22で再取得する証拠

- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`：既存runtime・履歴互換・新たなowner gate／CI受渡し／効率比較の回帰。
- `python scripts/format_tracked.py check`：共有フォーマット・lint。GitHub Actionsの`Code Quality`で確認する。
- `Validate Deterministic Output Evals`、`Validate Agent Skills`、`Validate Semantic Output Evals`、`Codex Harness`：各HEADの完了結果をPR #23のChecksで確認する。途中HEADの失敗を最新HEADの成功に読み替えない。
- 独立fixtureの検証は他ownerの実成果物を使った統合証拠ではない。**未実施**：新設14 Skillの各owner validator正式登録、実providerの競合・履歴・認可受入、実製品CI受渡し、実Agentの5シナリオ測定、A〜J横断S1〜S17／全条件の最終受入（PR #22担当）。

## 2026-11-08 担当Aの局所検証記録

検証対象の実装commitは[`5c848c48a59ea87d62b5c4c2531cf68132b161df`](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/5c848c48a59ea87d62b5c4c2531cf68132b161df)。共通helper、SQLite保存履歴、CI受渡し、効率評価処理と既存runtimeの回帰を、リポジトリのGitHub Actionsで検証した。fixtureの結果は他担当の実成果物や遠隔providerの検証を意味しない。

- 共有runtime単体テスト：`python -m unittest discover -s scripts/skills/evals/deterministic/tests -v`、12件PASS。
- repository決定論的評価：`python -m unittest discover -s tests/skills/evals/deterministic -v`、290件PASS。
- runtime／統合テスト：`python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`、461件PASS。
- 既存意味評価runtimeテスト：27件＋13件PASS。

上記の元ログは[Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42465992406)に保存している。[Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42465992453)、[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42465995075)、[Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42465994895)はSUCCESS。Codex Harnessは同一commitの[実行記録](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42465992421)を確認する（本文更新時点でWindows job実行中）。

特に`test_qa_operation_claim.py`は同一操作の並行claim、pre-start metadataの保存と別セッション読戻し、旧claim revision、改ざん、symlink、サイズ超過、既存3引数claim互換を検証した。`test_ci_handoff.py`は旧HEAD、未分類差分、source未対応、成果物hash／revision不一致、symlink経由読取り、承認provider未設定と不一致の同時発生を検証した。`test_workflow_efficiency.py`は5条件の比較、独立run重複、品質未PASS、条件不一致、未測定、悪化、JSON重複キー・サイズ制限を検証した。

SQLite予約の追加テスト`test_sqlite_shared_reservation.py`は、並行予約の単一取得、owner不一致・旧revision、cleanup未確認、解放の二重要求、再取得、旧JSON予約との共存拒否、DB障害・symlinkを検証する。既存`test_qa_artifact_graph_skills.py`の公開helper回帰もSQLite readbackへ更新した。

SQLite履歴の追加テスト`test_sqlite_workflow_history.py`は、create／CAS更新での旧・新revision保存、履歴のworkflow分離、同一revisionの並行更新、履歴保存失敗時の原子的ロールバック、直接変更された履歴の拒否、旧DBの欠落revision、旧形式JSON、未来revision、過大なrevision tokenを検証した。SQLiteへの実接続はGitHub Actionsの単一host環境に限り、network filesystemや複数hostを検証していない。

製品CIの現状を[qa-training-storeのWeb CI](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/main/.github/workflows/ci.yml)で確認した。既存CIはbuild成果物・テスト証跡の`actions/upload-artifact`／`actions/download-artifact`を利用しているが、確認したWeb CI workflowには`qa-ci-handoff-v1`の信頼済み`expected`、候補`manifest`と正本のrevisionを取得・照合するジョブはない。既存のbuild成果物をQA解析成果物の受渡しとして認定せず、転送方式と正本取得の決定をblockedとして残す。

予約保存の移行条件：既存の`qa.reservation_root`内に同一resourceの旧`<identity>.json`がある場合、新SQLite予約をblockする。既存ownerの実行／cleanupを調査せずにJSONを削除しない。旧版file-based予約と新版SQLite予約の同時運用は対象外とし、切替前に既存予約をすべて解消してから適用する。rollback時もSQLite上の予約を解放／照合するまでは旧版file-based経路を再開しない。

**未検証／blocked**：新設Skillの正式owner結果が未提供のためowner verifier登録と単独完了経路は未完成。遠隔保存providerのnative CAS／履歴／独立readback、承認主体の実認証、製品CIの実成果物取得、実Agentの5条件比較は未実施。複数host・遠隔providerへの安全性をローカル単一hostのclaimから推定しない。PR #22の全体受入に転用する際は、source・artifact revision・承認・cleanupを各ownerの正本から再取得する。
