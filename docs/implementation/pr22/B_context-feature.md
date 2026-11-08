# PR #22 並行実装：B — Project Context・機能分析

## 位置付け

初回案件のProject Context作成・更新、開発情報源の母集団、製品機能IDと差分の正本を作る。

- 作業branch：`feat/pr22-b-context-feature`
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

- [ ] Project Contextの既存parser、`artifact_graph.py`、`project_context_ids.py`、template、呼び出し元と回帰テストを確認した。
- [ ] AとSection 12／14、source revision、機能ID、provider・承認refの契約と共有ファイルの編集ownerを確認した。
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

- [ ] `project-context`が初回作成・有効既存文書再利用・差分更新・競合拒否・読戻し・履歴を扱う。既存16節・DEC/ASM・過去成果物が維持される。
- [ ] 配置方針が必要時のみ合意され、未承認の正本移動・二重正本化がない。機能別の正本参照ができる。
- [ ] `feature-analysis`が非UIを含む機能全体・安定ID・階層・差分・source inventoryを保持し、PR／merge／release／外部資料変更の現在性を判定できる。
- [ ] 機能の分割／統合／削除・partial discovery・source取得不能・0分母・旧HEAD・競合・二重受付の負例を検証した。
- [ ] C・D・Eへ実際の機能参照とrevisionを渡し、AへCI照合用のinventory・hash・未分類を渡せる。
- [ ] 新SkillのSKILL／契約／template・局所unit・意味・発火テスト、既存Project Context回帰を実行して証拠を記録した。

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
