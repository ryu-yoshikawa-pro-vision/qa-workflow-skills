# PR #22 並行実装：B — Project Context・機能分析

## 位置付け

初回案件のProject Context作成・更新、開発情報源の母集団、製品機能IDと差分の正本を作る。

- 作業branch：`feat/pr22-b-context-feature`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRは**実装準備のDraft**から始め、以下の完了条件を満たしてレビューできる状態にする。**実装完了・merge済みを意味しない**。
- 2026-11-08の利用者指示で、最終統合先はPR #22に変更された。既存Plan索引の「PR #22は文書変更PR」という作成時点の記載より、この統合指示を優先する。
- このファイルは担当別の作業ガイド。要件・完了条件の正本は以下のPlan。**15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケースを削減しない**。全体の最終完了判定はPR #22で行う。
- **2026-11-09の利用者指示：このPR #24は実装のみを対象とする。実案件での接続・操作・受入検証は実施しない。** 既存の実環境検証要件に優先し、未実施であることを理由に担当Bの実装完了を妨げない。ただし、必要な機能・安全な失敗処理・入力出力契約・自動テストを省略する意味ではない。PR #22や他担当PRの対象変更はこの文書では行わない。

## 参照するPlan

- [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細02：保存・承認](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細08：人間編集](../../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)

関連完了条件の主な担当：開発連動QA 1・2・4・6・9・10。全体の保存・CI・互換条件はA・Cと共同検証する。

## このbranchで変更する対象

- 新設`skills/project-context/**` と `skills/feature-analysis/**`
- 両Skill固有のhelper・fixture・unit／意味／発火テスト
- Project ContextのSection 12／14・既存16節への出力契約（共有template・parserの編集はAが実施）

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 担当branchで実施する作業とPR #22で実施する作業

### このbranchで実施・検証する

- 本書の担当対象のSkill・runtime・helper・データ契約・既存consumerとの局所接続を実装し、担当範囲の既存テスト・回帰・負例・権限／保存・履歴互換性を検証する。
- **実環境検証は行わない。** 実runner・実保存先・実Agent・案件の製品CIを使用する受入と実際の承認操作を要求しない。コード実装、単体テスト、隔離fixture、一時Git repositoryを使った結合テスト、GitHub Actionsの既定CIを対象にする。実際に選定されていない保存providerや承認主体の権限を捏造せず、未接続時の拒否・引継ぎ契約を実装する。
- 他branchの未統合実装は合意した契約と独立fixtureで代替して局所検証する。fixtureは他ownerの実成果物を統合した証拠にはしない。
- 担当が所有する実装不具合、局所結合・回帰不具合は**このbranchで修正**し、対応したテスト・実施証拠を残す。

### PR #22だけで実施・判定する

- A〜Jの実装PRの取り込み、競合解消・全体再検証、**各ownerが実際に保存した成果物同士**のID／revision／currentness／承認・run参照による横断接続。
- 全current Skill同時利用時の発火／routing、工程をまたぐ実Agent・実runner・実provider・製品CIの一連の受入、S1〜S17の総合試験、人間編集8ケースの**全体経路としての再検証**。
- 開発連動QAの15条件、QA全工程の10条件と詳細Plan 01〜08の最終照合、Plan詳細07の5シナリオの**変更前後の横断実測・効率化判定**、統合後の全CI・回帰評価。
- 横断試験で見つかった問題はownerを特定し、分割可能な実装・修正は対象branchに戻す。統合固有の接続・設定・複数owner間の確認作業だけをPR #22で実施する。

### PR #22へ引き渡す証拠

- 担当の変更ファイル、公開入出力契約、参照するowner／source／artifact IDとrevision、schema／fixture、保存・承認・失敗／再開条件。
- 自動テスト／CIのコマンドと結果、隔離fixture・回帰・負例、実装上の既知制約と他ownerへの引継ぎ。実runner／実providerの実環境実行証拠は作成しない。
- 他担当の実成果物が必要な横断検証項目。**これらの未実施は担当branchの局所検証を失敗扱いする理由にはしないが、PR #22の最終受入完了には必ず必要**とする。

## 共通契約が未確定の場合の着手範囲

- A（[PR #23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23)）のsource／artifact ID・revision・scope、runtime登録、保存・承認・CAS／readback、blocked／再開、評価・CI引継ぎ契約を**実コード・既存契約と照合し、PR #23で共有された内容**に従う。
- 上記に依存しない既存実装調査、担当Skill固有ロジック、独立fixture、局所テストは先行可能。Aによる確定・共有前に、未確定の共通schema・保存形式・承認・runtimeの接続方法を推測して確定しない。
- 契約未確定で停止する対象処理と理由・解決責任者・再開条件を記録し、独立して実施できる作業を止めない。Aが共有した契約を使う局所検証の後、他ownerの**実成果物を使う横断検証はPR #22**へ引き継ぐ。

## 着手基準

- [x] Project Contextの既存parser、`artifact_graph.py`、`project_context_ids.py`、template、呼び出し元と回帰テストを確認した。
- [x] AとSection 12／14、source revision、機能ID、provider・承認refの契約と共有ファイルの編集ownerを確認した。
- [ ] 対象案件の探索範囲・認証・保存先を列挙し、未確認は明示的にblockedとした。

## 作業内容

1. 既存Project Contextの発見／候補重複／初期化／更新／readback、16節・stable key・DEC/ASM ID・parserの互換を実装する。
2. Q06の配置・編集可否・機能別参照の初回確認、承認記録と有効な合意の再利用を実装する。未承認の移動・保存を拒否し、読取分析は止めない。
3. 製品コード・Issue・仕様・設計・テストのsource inventory、権限不足・取得漏れの表示、PR／rebase／merge／releaseと資料改版の取得完全性を実装する。
4. UI以外を含む製品機能の階層・安定ID・根拠・追加／変更／分割／統合／削除／廃止履歴を管理する。ファイルpathを機能IDにしない。
5. 差分未分類・未知領域・partial discovery／分母0を区別し、分類率・機能網羅率・仕様対応率へ参照を渡す。仕様Authority／Product Risk／正式TCNは担当しない。
6. 同じsource再送・旧HEAD到着・権限不足・並行更新の負例と、保存先native CAS／readbackの受入を実施する。

## 依存と引継ぎ

- A：Project Context共通templateとruntime登録、保存・承認／source入力契約の共有変更を依頼する。
- C・D・E：feature ref・機能階層・source revisionを渡す。
- F：承認済み配置・案件QA用の基本情報を渡す。
- A：製品CIの差分分類／未分類／情報源完全性・artifact hashを渡す。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [x] `project-context`が初回作成・有効既存文書再利用・差分更新・競合拒否・読戻し・履歴を扱う。既存16節・DEC/ASM・過去成果物が維持される。
- [x] 配置方針が必要時のみ合意され、未承認の正本移動・二重正本化がない。機能別の正本参照ができる。
- [x] `feature-analysis`が非UIを含む機能全体・安定ID・階層・差分・source inventoryを保持し、PR／merge／release／外部資料変更の現在性を判定できる。
- [x] 機能の分割／統合／削除・partial discovery・source取得不能・0分母・旧HEAD・競合・二重受付の負例を検証した。
- [ ] C・D・Eへ実際の機能参照とrevisionを渡し、AへCI照合用のinventory・hash・未分類を渡せる。
- [x] 新SkillのSKILL／契約／template・局所unit・意味・発火テスト、既存Project Context回帰を実行して証拠を記録した。

- [x] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [x] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [x] source ref・artifact ref・revision・承認・保存readback・失敗／再開の**コード上の接続契約と自動テスト**をAへ引き渡した。実providerの読戻し・実承認は本PRでは実施しない。
- [x] 担当branch内の実装・自動テストを完了し、実環境検証とPR #22の横断検証・15＋10条件の最終判定を**本PRの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装・受入記録（2026-11-08）

- 担当Bの新設ファイル：skills/project-context/、skills/feature-analysis/。共通parser・DEC/ASM helperを再利用し、共有templateとruntimeを変更しない。
- Project Context：候補のreadable/absent/denied/unavailable、16節・stable key・DEC/ASM検証、未設定required key、未承認配置の再利用候補、既存fieldの差分更新draftを扱う。draftとreuse_candidateは保存・承認成功ではない。
- feature-analysis：source inventory・対象revision・機能IDの意味上の同一性と親子循環・差分分類・候補対応・history追記・旧HEAD・operation重複を決定論的に検証する。全製品機能が発見されたという機械的保証は返さない。
- 独立unit：tests/skills/runtime/test_project_context_owner.py、test_feature_registry.py。trigger train/validationとsemantic independent reference caseを追加した。CI結果は対象branchの最新HEADを参照し、未実行をPASSとしない。
- 共通契約との差：qa-workflow/assets/project-context-template.mdのSection 12/13のID列separatorは2本のhyphenだが、qa-workflow/scripts/project_context_ids.pyは3本以上を要求する。担当Bでは検証時だけread-only copyを正規化し、旧文書の本文・DEC/ASM IDを変更せず扱う。新規draftは3本で生成する。共有template自体の変更はA担当へ依頼する。
- 依存：A担当のProject Context追加key（qa.feature_source_refs、qa.feature_artifact_root、qa.feature_base_ref、qa.feature_approval_policy_ref）はこのbranchの共通templateへ書かない。未登録keyの更新はblocked。provider-native CAS／履歴readback／認証済み承認元／案件のsource取得元が未選定なら、永続更新および実受入はblocked。別pathへの無許可保存で代用しない。
- 未接続：正式なsource列挙adapter、案件ごとの保存providerと権限、実Agent発火・実providerへのcreate/update/readback、owner間の実成果物接続、製品CI受渡し。準備済みのfixture検証をこれらの証拠として使わない。
- 局所の検証コマンド：python -m unittest tests.skills.runtime.test_feature_registry tests.skills.runtime.test_project_context_owner（module import環境によってはdiscoverで個別path指定）。CI：Code Quality / Validate Agent Skills / Validate Deterministic Output Evals / Validate Semantic Output Evals。結果は各workflowの実施結果を確認後に記載する。

## 担当Bの追加実装・局所検証（2026-11-08）

- Project Contextの`prepare-ids`：Section 12/13がこの案件のDEC/ASM正本である場合のみ、既存`project_context_ids.py materialize`に採番を委譲する。過去ID・16節・table前後の自由記述とSection 14/16を保持し、正本owner不一致・過去ID消失・expected revision不在を拒否する。これは保存前のdraft生成であり、providerによる原子的保存の証明ではない。
- Project Contextの`prepare-update`：元artifact refとexpected revision、source ref/revision、変更理由を必須にした。既存stable key以外を無断更新せず、元の表・DEC/ASMを保持する。保存結果は`draft`と区別する。
- `feature-analysis/scripts/git_source_inventory.py`：許可された単一のlocal Git checkoutとfull commit SHAを用い、全file snapshot・base→head差分・rename/moveをNUL区切りで列挙する。ファイル件数を機能件数としない。外部Issue／設計資料の列挙や保存は実providerに依存する。
- `feature_registry.py`：未分類・source不完全・未知領域・分母0・旧HEAD・機能階層循環・機能ID意味再利用・履歴書換えを拒否またはincompleteにする。候補の対象外は機能ID対応率の分子へ含めない。繰返しのoperation IDでもschemaと履歴検証を省略しない。
- 両Skillの`evals/deterministic/validator.py`、出力fixture、trigger、semantic caseを追加した。決定論的出力validatorはMarkdownの契約・ID・判定状態を調べる。独立した意味判断・外部sourceの真偽・provider承認の真正性を検証したことにはならない。

### 確認済みCI結果と未解決の共有側の失敗

[実装commit `5aceb2ae7f2da107768383182c588ef95a9c9739`](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/5aceb2ae7f2da107768383182c588ef95a9c9739) のGitHub Actions結果：

- [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42489982093)：SUCCESS。新規Python・Markdown・JSONのformatterとlintを確認した。
- [Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42489982071)：SUCCESS。共有決定論的runtime 12件、repository決定論的評価292件、runtime／統合528件、意味評価runtimeの27件と13件がPASS。実Agentの意味判定を実行した証拠ではない。
- [Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42489982055)：SUCCESS。dataset／参照の構造検証であり、実Agentの応答を評価したものではない。
- [Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42489982060)：FAIL。両新Skillの正式形式検証は通過したが、共有`README.md`に`project-context`と`feature-analysis`の記載がないためrepository一覧整合が失敗。共有READMEは担当A／PR #22の編集範囲。
- [Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42489982070)：この記録時点では実行中。先行commitのLinux／Windowsでは、共有`tests/codex/test_development_skills.py:85`のSkill数`23`固定と新Skill25件との不一致によりFAILした。現HEADでも修正未統合のため残存する問題。

共有README・Codexテスト・Section 16追加key・B ownerのruntime登録は[PR #22へ対応依頼](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22#issuecomment-6722581724)済み。これらを担当Bで独自変更して競合させない。実案件のsource API接続、Project Context・機能一覧のprovider-native create/CAS、過去revisionの独立readback、実認証承認、実Agent／実製品CIの担当単独受入は未接続／blocked。局所fixtureとGitHub Actionsの成功を、保存・統合や製品全機能発見の完了として報告しない。

## 追加の安全性修正（2026-11-09）

- `prepare-update`：path型の相対配置を検証し、絶対path・`..`・URIとscalar/pathへの改行・16節外の数値見出しの混入を拒否する。既存文書は自動書換えしない。
- `feature_registry`：実際に変更されたartifactのrevision使回しを拒否し、split/mergedの履歴要件を確認する。handoffにcanonical snapshot SHA-256と取得source別状態・revision・未取得範囲を追加する。これらはproviderによる保存履歴・readbackの代替ではない。
- `git_source_inventory`：Gitの大量出力を一時ファイルへ退避してから容量を判定し、巨大repoの出力によるプロセスメモリ消費を抑える。既存のGit差分と改名判定は維持する。
- 上記の負例を担当unitへ追加。最新HEADのCI結果は実行後に確認し、未完了は未検証と記載する。

## 差分母集団の照合追加（2026-11-09）

- `reconcile_git_coverage.py`を追加。実際に列挙したGit差分の各変更pathと、feature inventoryに登録された差分locatorを照合し、漏れたpath／根拠のない差分IDを`incomplete`にする。旧HEAD／取得不完全は成功へ変換しない。
- `test_git_change_coverage.py`は一時GitリポジトリでbaseとHEADの変更2件を作り、台帳に1件しか登録していない場合の漏れ、2件分類したときの整合、未分類・旧revision・存在しないpathの負例を検証する。
- この照合はコードの変更path単位であり、意味上の全製品機能・全差分hunk・外部資料の列挙を保証しない。製品CI接続はA・PR #22に引き継ぐ。

## 最新HEADの担当B局所検証（2026-11-09）

対象：[コミット `4f1177c6000441cbd3e76a11c467b68a7576288d`](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/4f1177c6000441cbd3e76a11c467b68a7576288d)。

- [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42538056128)：SUCCESS。追加・変更したPython／Markdown等の書式・lint確認。
- [Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42538056146)：SUCCESS。追加したProject Context／feature registry／実Git差分照合のunit／結合とrepository既存回帰を含む。fixture・実行中に作る一時Git repositoryの受入であり、実製品CIの受入ではない。
- [Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42538056160)：SUCCESS。dataset構造・参照の検証で、実Agentによる意味判断を示さない。
- [Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42538056138)：FAIL。2 Skillの形式チェックは通るが共有`README.md`に`feature-analysis`・`project-context`がない。PR #22の共有ownerに依頼済み。
- [Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42538056127)：FAIL。`tests/codex/test_development_skills.py:85`の`len(qa_skills) == 23`が新規2 Skill追加後の25件と一致しない。共有ownerに依頼済み。
- PRのbaseは`feat/development-qa-traceability`、担当branchの差分は担当BのSkill、専用unit／eval、担当記録のみ。mergeや共有ファイル修正は実施しない。

### PR #22への未完了の受入引継ぎ

- 共有`README.md`、Codex固定件数、共有Project Context templateのSection 12/13 separator・Section 16追加stable key、共通runtimeへのB owner登録を統合branchの担当者が修正して再検証する。
- 実案件の認証・情報源／保存root・正本を決め、対象providerのnative create-if-absent／CAS・history・独立readback、実認証承認、同時更新と再試行の受入を行う。現helperは準備済みdraft／検証結果であって永続書込み済みの正本ではない。
- 実AgentでのSkill発火・意味評価、実製品情報源からの全対象列挙、製品CIへの差分／分類／hash受渡し、他ownerの実成果物との現在性と承認・再開を検証する。これらの経路は未接続のため未実施であり、PR #24の局所fixture成功を完了証拠としない。

## 実装のみとする範囲の確定（2026-11-09）

利用者から**「実環境検証はしない。PRは実装のみ」**と明示されたため、担当Bの作業の判定を次のとおり修正する。

- 対象：`project-context`と`feature-analysis`のコード・契約・fixture・単体／結合テスト、既存回帰、formatter／lint・GitHub Actions。既存のID・revision・承認・CAS／履歴readback・未取得sourceの安全な扱いを実装する。正式な外部providerの選定が必要な部分は無断で決定しない。
- 対象外：実案件の対象製品／保存provider／承認サービスへの接続、実Agentの発火・実runnerの動作、実製品CIでの成果物受渡し、実案件データによる網羅率・効率比較。**これらを実行できないことはPR #24の実装完了の阻害条件ではない。**
- 残るコード側の統合事項：共有`README.md`とCodexのSkill件数、共通templateの修正、共通runtimeへのB owner登録およびB成果物のCI契約との結合はA／PR #22側の実装範囲。PR #24では共有ファイルを二重編集せず、必要な契約・自動テスト・変更点を引き継ぐ。
- 状態の区別：CIが成功しても実環境で動作を確認したとは記載しない。一方で実環境検証を実施しないこと自体を`blocked`として本PRの完了条件に加えない。未接続でも安全に拒否するコード上の仕様と、実際の保存・承認済みの状態は区別する。

## 追加の履歴・既存文書検証（2026-11-09）

- `project-context discover`でreadable候補の16節とstable keyだけでなく、DEC/ASMテーブルとID構造も確認する。破損候補を既存の有効正本として自動採用しない。
- `feature_registry`でsource/candidate/changeの既存IDを別の対象へ再利用する変更を拒否する。新artifact revisionで同じIDの意味を変える操作は履歴の整合性を損なうためblockedとする。

## 担当Bの実装完了記録（2026-11-09）

利用者の指示により、対象は**コード実装と自動テストのみ**とし、実案件のprovider・承認サービス・実Agent・実製品CIへの接続検証は実施しない。前節までの実環境検証を担当Bの完了必須条件とする記述は、この指示で更新された。旧コミットに対するCIの失敗は当時の履歴として保持し、以下の最新結果を現在の判定とする。

- 担当Bの最終コード変更：[コミット `1835fed2e4d19e338d335cdca1d96922c543f4a1`](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/1835fed2e4d19e338d335cdca1d96922c543f4a1)。既存正本候補のDEC/ASM構造検証、source／候補／差分IDの意味上の再利用拒否、4つのfeature用stable keyの更新・再読込まで担当Bの回帰テストを追加した。
- [Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42540774400)：SUCCESS。
- [Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42540774457)：SUCCESS。
- [Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42540774484)：SUCCESS。共有12件、決定論的292件、runtime／結合543件、意味評価runtime27件・13件のすべてがPASS。
- [Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42540774490)：SUCCESS。意味評価datasetの構造検証であり実Agent判定ではない。
- [Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42540774428)：SUCCESS。Linux／Windowsの両jobがPASS。
- 上記のCIはPR #22のbaseを統合したGitHub ActionsのPR検証。共有README／Codexテスト／Project Context templateの対応は、担当Bの編集範囲に混ぜず、[PR #22側のコミット `7cc8ac8`](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/7cc8ac8bcebdacd6ac35aede3bed8555c73f276c)に分離した。配置・認可・CAS等は案件ごとの契約が確定しなければ安全に拒否する。

**判定**：担当Bで所有する実装・単体／結合テスト・CI検証は完了。実環境検証は依頼対象外であり未実施。A〜J横断のruntime／provider実装・PR #22統合、15＋10条件の全体判定は本PRで完了を宣言しない。PR #24のmerge、force push、base変更は実施しない。

## Plan再レビュー後の実装追補（2026-11-09）

利用者の指示に従い、PR #24の担当Bが所有するコード・契約・自動テストだけを変更した。PR #22／他担当branch／共有runtimeへの変更は行っていない。以前の「draftのみ／provider-native保存がない」という制約は、この節の**明示選択ローカルprovider**について更新する。ただし実案件が利用する遠隔providerと認証済み承認サービスは選定されていないため、実接続済みとは扱わない。

### Project Context・配置合意

- `skills/project-context/scripts/artifact_store.py`に、明示された許可root内のprivate SQLiteを用いるB担当の保存経路を実装した。トランザクションによるcreate-if-absent、expected revisionを条件にした更新、過去revisionの不変保存、独立readback、内容hash照合、operation_id冪等性、並行更新競合の拒否に対応する。
- `project_context.persist_prepared`は`prepare-create`／`prepare-update`／`prepare-ids`／`prepare-placement`／`prepare-sections`で生成した候補を、保存済み前revision・本文と照合した後、保存providerに引き渡す。外部から渡された単なる承認refでの無条件保存はできず、信頼済み呼出し元が渡す`authorize` callbackで承認・権限・対象revisionを検証する。
- `prepare-placement`は同一方針の再利用を判定し、新規・変更時にはDEC正本とSection 14の参照行を同一draftに記録する。`prepare-sections`はSection 1〜11・15のみを変更し、DEC/ASM（12/13）、配置参照（14）、stable key（16）の正本を直接改変しない。初回作成時は`section_updates`で既知情報のみ記録できる。

### 機能分析・変更追跡

- `feature_registry.py`で、既存機能の名称・状態・親・実装／仕様／QA参照を更新する場合の追記履歴を必須にした。意味上のID再利用・旧revision・履歴改変を拒否する。
- `no_impact`／`out_of_scope`を分類済みとする前に理由と承認refを必須にした。承認refだけでは真正性を保証できないため、保存時に信頼済み承認確認を行う。
- `event_basis`でPR更新・rebase・merge・release・外部文書のみの改版の必要な旧／新revisionを検証する。`reconcile_git_coverage.py`はPR base→headに加え、前回PR head→現在headのGit差分の和集合を照合し、片方が未取得ならcompleteを返さない。
- `git_source_inventory.py`のCLIは信頼済み起動環境の`QA_FEATURE_AUTHORIZED_ROOT`を必須として、入力JSONの自己宣言だけによるGit root認可を拒否する。
- 下流向けに機能階層・source／実装／仕様／QA refs、影響機能IDs、承認確認が必要な差分IDs、未知領域とsource inventoryをhandoffへ出力する。

### 自動テスト・完了条件の境界

- 保存provider単体とowner接続を`tests/skills/runtime/test_pr24_artifact_store.py`で検証する。原子的な同時更新、旧revision保全、操作ID再送、改変readback、権限拒否、承認providerエラー、Project Context／Feature Inventoryのcreate/update、配置合意、Section編集を含む。
- source・イベント・履歴・Git二重差分の正常系／負例は`test_feature_registry.py`、`test_git_source_inventory.py`、`test_git_change_coverage.py`、`test_project_context_owner.py`へ追加した。
- **実案件での保存先選択・認証サービス接続・実Agent・製品CIは対象外**。ローカルproviderの成功を、未選定のGitHub／Drive等のproviderのnative CAS・承認・readback成功へ一般化しない。
- PR #22側の共通runtime owner登録・他ownerとの成果物受渡しはPR #24の編集範囲外。担当Bは必要な入出力契約とhandoff projectionを用意したが、PR #22の統合完了は宣言しない。
- 最終実装コードの先頭commitは[dd5b7f5](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/commit/dd5b7f5c2327b295a0b139c50fc82189d286e6b4)。CI最終判定は最新PR headに紐付くActionsで確認する。

## PR #24 追加レビュー6件の修正（2026-11-09）

レビュー時点のHEAD `0ddbf4a` で指摘された6件を、担当Bの保存・ID・差分契約と回帰テストに反映した。

1. **不存在確認済みrefの限定**：`prepare-create`の保存先refが列挙済みの`absent`候補と一致することを確認する。別refへのredirectは`prepare_create`と`persist_prepared`で拒否する。
2. **既存Markdown正本の保存**：Git管理文書の正本は`git_artifact_store.py`で対象branchの元pathを更新する。Git commit SHAをexpected revisionにした`git update-ref`によるnative CAS、Git履歴からの旧版読戻し、独立内容照合、同一operationの再送を実装した。未選択の遠隔providerに保存できるとは主張しない。SQLiteを正本とする案件だけ従来の`LocalArtifactStore`を使用する。
3. **配置変更時の既存DEC失効**：現在有効なDECとSection 14の正本参照、`existing_policy.decision_id`を照合する。変更時は旧DECの状態を`置換済み`、`置換先ID`を新DECに設定し、新DECのみ有効にする。同時に既存DEC／ASMのセルが以前の保存文書と一致することを検証し、別の決定内容の無断編集を拒否する。文書に裏付けがない方針の再利用はblockedにする。
4. **変更イベントの初回扱い**：前回snapshotが存在する更新で`event=initial`を指定すると拒否する（同一snapshotの冪等再送のみ許容）。source revisionに変化がない手動の内容修正は`analysis_update`と明示的なsource revision・根拠refを要求する。PR更新・merge等のイベント根拠を初回処理へ偽装できないようにした。
5. **2基準差分の旧revision**：PR base→HEADと前回HEAD→現在HEADを、それぞれ旧SHA・path・今回HEADの組として照合する。両基準に同じpathがあって旧SHAが異なる場合も二つの差分を保持する。一方だけの分類を両方の100%として報告せず、`missing_git_revision_pairs`に未確認を残す。
6. **保存先の読取権限**：SQLiteの`read_current`／`read_revision`にも信頼済みhostの`authorize`callbackを必須とし、案件・成果物refと操作種別を渡す。writeのoperation ID再送時もアクセス権を再評価する。Git保存先も読取／書込で同じ認可境界を適用する。

検証はB専用の独立テスト・一時Git repository・GitHub Actionsで実施する。新規fixtureには正本pathの維持、競合、旧revision保全、認可取消、複数revision基準、DEC置換・二重有効防止と未承認refの負例を含めた。**実案件の認証元、遠隔provider、実Agent／製品CIへの接続は今回の依頼から除外**し、隔離テスト成功を実環境受入済みとは扱わない。PR #22側の共通runtime／他owner統合とmergeも対象外。

## 担当Bチェックリストの判定（PR #34再確認）

上記のチェック項目は、担当Bのコード・契約・隔離テスト・GitHub Actionsで確認済みのものだけをチェック済みにした。次は未チェックのまま維持する。

- **着手基準：実案件の探索範囲・認証・保存先の列挙**：案件固有の情報源・認証・保存先の選定は指示された実環境検証対象外。未選定の場合は未接続・保存拒否として扱う。
- **C・D・Eへの実成果物接続、Aへの製品CI受渡し**：担当Bは構造・ID・revision・handoffを提供済み。別ownerの実成果物との照合・CI接続は親PR #22で確認する。
- **旧artifact／legacy・既存consumer・全体CIの横断回帰**：担当B単独の既存回帰と局所fixtureは実施済み。担当外の統合後経路についてはPR #22の受入が必要。

## PR #24 merge後の追加レビュー4件（2026-11-09、修正PR #34）

PR #24は2026-11-09 14:01 JSTにPR #22へmergeされ、元branchも削除された。以後の追加修正はPR #22のbranchへ直接commitせず、担当Bだけの[PR #34](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/34)で行う。

1. `prepare-placement`は保存済みSection 12の有効DECとSection 14の参照から、決定ID、owner、scope、保存先、方針revision、決定根拠、承認revision、編集可能範囲、機能別参照を復元・相互照合する。入力`existing_policy`を承認済みとみなさず、両入力の承認revisionだけを変えても再利用不可。旧記録に承認revisionがなければ推測しない。
2. Gitの`GitArtifactStore.write`では`authorize`へ承認revision・source ref/revision・operation ID・理由・hashを渡し、信頼済み承認元が不一致を拒否できるようにした。承認refだけの検証では通さない。
3. `git_source_inventory.py`はgitlink／submoduleの内部を未取得の場合に`incomplete`、`complete_file_listing=false`、`unretrieved=[gitlink:path@revision]`とする。親treeの列挙成功をsubmodule内部の取得成功として扱わず、別sourceとして検証する必要がある。
4. `feature_registry.py`は今回新規のDIFの`after_revision`をsourceの現在revisionへ照合し、PR更新／rebaseの`before_revision`を正当な旧SHAへ制限する。過去に登録したDIFは旧revisionのまま保持する。`persist_snapshot`ではcode sourceごとに信頼済み呼出し元が指定したGit root・base/head refを`git_inventory_requests`で受け、保存前に実際のGit tree／diffを再列挙し、`reconcile_git_coverage`を再実行する。未登録差分・submodule未取得・HEAD不一致・必要な差分未列挙ならblocked。code sourceを含まない台帳は既存の保存経路を保持する。

自動テストには保存済み方針と呼出し元の承認revision不一致、Git承認revision不一致、gitlinkの未取得、偽ったDIF revision、未登録Git差分、保存前のGit再列挙と旧DIF履歴維持を追加した。実案件の遠隔保存provider・承認認証元・実Agent・製品CIの実環境検証は利用者指示どおり実施しない。全工程・他owner横断の統合はPR #22で別に判定する。

## PR #34 再レビュー指摘3件の修正（2026-11-09）

担当Bの再レビューで確認した3件を追加修正した。

1. **過去DIFと今回差分の分離**：保存済みDIF IDとその全フィールドをappend-onlyに維持する。PR更新・rebaseのGit差分照合では現在イベントで追加したDIFのみを計上し、過去行の`after_revision`を現HEADへ書き換えない。base→今回HEADと前回HEAD→今回HEADの両方の必要な差分は新IDで登録する。同一HEADの分析修正は既存の有効DIFを再利用する。
2. **複数repositoryのrevision**：主イベントの`source_revision`と、個別`sources[].revision`を分離する。各code sourceに独立したGit root・base/head SHA・前回HEADがあり、独立してGit tree/diffを取得・照合する。主repoと異なるHEADであることを理由に拒否しない。
3. **DIF分類変更の履歴・承認**：既存DIFの分類・理由・承認refなどの上書き・削除を拒否する。見直しでは新DIFに`supersedes_id`、別の根拠、承認ref・revisionを付け、保存前に信頼済み承認元で検証する。旧DIFは履歴として維持し、置換済みの旧分類を現在の未分類・分類率に重複計上しない。

検証は単体・一時Git repository・GitHub Actionsで実施する。連続2回のPR更新、2つのGit repositoryでの異なるHEADとその更新、古いDIFの改変拒否、承認されない再分類、未分類から承認済み分類への変化を回帰テストに追加した。実環境provider・Agent・製品CIは利用者の従来指示どおり未実施。PR #22の横断統合とmergeは本PRの対象外。

## PR #34追加レビューの対応（2026-11-09）

前回レビューの4件をコードと回帰テストへ反映した。

- **現在の影響と履歴の分離**：保存済みDIFを残しながら、今回イベントの変更分類率・影響機能ID・承認対象IDを新規有効DIFから算出する。初回・同一revisionの`analysis_update`は別の集計条件とした。連続PRで旧影響機能が混入しない回帰テストを追加した。
- **再分類の承認範囲**：`persist_snapshot`が保存前認可へ旧・新feature IDs、source ID/ref/scope、旧・新revision、locator、旧・新根拠を渡す。承認revisionが同じでも機能IDを改変した場合は拒否し、旧正本を維持する。
- **同一Git差分の矛盾分類**：source／旧SHA／新SHA／locatorが同じ複数の有効DIFを拒否する。正規の再分類は`supersedes_id`で旧DIFを履歴として保存する。
- **主source IDの明示**：複数repositoryが同じHEADを共有するときは`event_basis.primary_source_id`を要求する。実Gitで同一コミット・異なるbaseを指定した2 repositoryの保存／拒否をテストした。既存の主sourceが一意な場合の入力は互換維持。

担当範囲のGitHub Actions 5系統と決定論的テストを最新HEADで再確認する。実provider／実Agent／製品CIの受入は従来の利用者指示に従い対象外とし、PR #22の横断統合はここでは完了判定しない。

## PR #34 再点検：checkoutのHEAD現在性

`git_source_inventory.analyze`で`cat-file`による指定コミットの存在確認に加え、許可されたcheckoutの`git rev-parse HEAD`と`head_sha`が一致することを検証する。過去コミット自体が存在してもcheckoutが進んでいれば`git_head_changed`として保存を拒否する。`test_git_source_inventory.py`に古い実在SHAの列挙拒否、`test_pr24_git_artifact_store.py`に旧SHAを使った保存拒否と正本不変を追加した。現行SHAを信頼済み呼出し元で取り直すまで保存を再試行しない。GitHub Actionsの実行結果はPR #34の最新HEADに紐付くworkflowを正とする。

## PR #34最終レビュー追加2件への対応（2026-11-09）

担当Bの再点検で判明した次の2件を修正した。

1. **merge／releaseのGit差分基準**：`reconcile_git_coverage`が各code sourceの保存済み`previous_snapshot.sources[].revision`と、今回Git列挙の`base_sha`を照合する。途中のcommit→今回HEADだけの差分では全変更を拾えないため`stale`にする。`persist_snapshot`もmerge／releaseに`base_sha`を必須とし、再列挙・照合で不一致なら書込みを拒否する。初回分析やPR更新の既存仕様は維持する。
2. **過去DIF訂正と今回影響の分離**：`supersedes_id`で過去revisionのDIFを訂正しても、PR更新・rebase・merge・releaseなどのイベントの変更分類率・影響機能・承認対象へ計上しない。同一revisionの`analysis_update`では現行revisionの訂正のみ計上する。`reconcile_git_coverage`の差分照合でも同条件で過去訂正を除外する。訂正履歴・保存前承認の条件は維持する。

回帰テストは`test_feature_registry.py`の旧DIF再分類2通り、`test_git_change_coverage.py`の実Git merge／releaseの途中commit base拒否、`test_pr24_git_artifact_store.py`の実Gitでの未列挙ファイルを含む途中commit base保存拒否・保存済み正本維持・正しい旧SHAからの正常保存を含む。検証はPR #34最新HEADのGitHub Actionsを正とする。

実案件の外部provider・実承認サービス・実Agent・実製品CIおよびPR #22のA〜J統合受入は、従来の対象範囲どおり本PRの完了判定に含めない。外部レビューの依頼とPRのmergeは本対応では実施しない。

## PR #34 履歴互換・多source・submoduleの再点検（2026-11-09）

担当Bの保存・差分管理・Project Contextについて、レビューで確認した問題を修正した。

- 旧重複DIFは変更せず履歴として保持し、未統合ならincompleteとする。新規重複はblockedとし、supersedes_idsに旧ID群を明示した訂正では旧行それぞれの承認を確認する。同分類の根拠・機能ID訂正を許可する。
- analysis_updateはすべてのsourceのrevisionを比較し、直前PRの二つのGit差分基準を照合する。主sourceの旧SHAをsource IDで確認し、新規副次sourceは初回基準で処理する。
- 削除・置換前のgitlinkも未取得として記録し、検証済みの子sourceのSHAと対応付けてから親sourceを保存する。Git取得失敗の理由も保存結果へ伝える。
- Git検証と成果物保存の間はHEADとbranch refのGitロックを保持する。通常のGit ref更新との競合では保存しない。
- 配置方針の参照URL内の=を許容し、前後空白を拒否する。承認revisionのない旧DECは再利用せず、新たな承認による置換を許可する。承認revisionだけを変更する場合も新DECを作成する。

回帰テストは担当Bのテストへ追加し、最新コミットでGitHub Actionsを確認する。実案件provider・実Agent・製品CIやPR #22の他担当統合は従来どおり対象外とし、レビュー依頼とmergeは行わない。
