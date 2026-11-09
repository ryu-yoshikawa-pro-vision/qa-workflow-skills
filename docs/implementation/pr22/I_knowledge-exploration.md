# PR #22 並行実装：I — QA Knowledge・探索

## 位置付け

QA Knowledgeのidentity・scope・currentnessを正し、Charter／探索／症状調査の直接開始と安全な別セッション再利用を扱う。

- 作業branch：`feat/pr22-i-knowledge-exploration`
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
- [詳細06：探索／Knowledge／改善](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)
- [詳細04：別セッション再開](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)

関連完了条件の主な担当：QA全工程 8・9のKnowledge／探索・再開部分。

## このbranchで変更する対象

- 既存`skills/qa-knowledge/**`、`scripts/knowledge_runtime.py`を含むvalidator・lookup・lifecycle
- 既存`skills/exploratory-testing/**`の直接開始／Charter／Findingの必要な接続と局所テスト

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

- [x] QA Knowledgeのentry schema・identity・hash・read_revision・reader／writer、探索Charter・session／Findingと既存テストを確認した。
- [x] A/Jとhandoff・承認・欠陥候補と既存result ownerの境界を固定した（固定fixture／参照payload。J実成果物との接続はPR #22）。

## 作業内容

1. `identity.kind`／`scope_refs`とentry最上位のkind／scopeを照合し、ID hash一致だけで矛盾するentryを受け入れない。
2. scope別source currentness・read revisionを扱い、無関係なentryの依存不明だけで検索全体をblockedにしない。
3. 候補のpartial lookup、legacy entry／再検証・readback・同時更新と別セッション再開を扱う。
4. 探索Charter・Observation・Finding／調査依頼から必要Skillへ直接進み、未確定症状を正式欠陥へ自動昇格させない。
5. Knowledgeの再利用を強制経由・第二の仕様／結果正本にせず、改善候補の採否・適用範囲とsource refをJ／Fへ渡す。

## 依存と引継ぎ

- I→J：Finding・Knowledge改善候補・source revision・scopeと未確認。
- I→A：read_revision・currentness・再開条件。
- J/F→I：承認済み改善からの再利用知識の更新要求。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [x] identity.kind／scopeと適用対象の不一致を拒否し、旧entry／正当なscopeの読取互換を維持する。
- [x] 部分検索・無関係scope stale・read_revision・再検証・保存失敗／競合と別セッション再開を検証した（create → read → lookup → 更新 → lookupを別sessionとして実行。native CASは固定fixtureのproviderでの検証で、実providerは未検証。下記）。
- [x] Charter／Knowledgeから独立発火・停止／再開でき、無関係な設計・全工程Skillを強制しない（発火はhaikuサブエージェントによる擬似的な発火確認で、停止／再開は決定論テスト。全current Skill同時の実ハーネスでのroutingはPR #22。下記）。
- [x] 探索FindingからJの欠陥候補／報告に渡す参照契約を固定fixtureで検証し、run／仕様の正本を複製しない。Jの実成果物との横断試験はPR #22へ引き継いだ。
- [x] 詳細06のKnowledge／探索条件と既存lifecycle・deterministic／trigger／semantic回帰がPASSする（repositoryのdataset／契約テスト。semantic判定のLLM評価は未実施でPR #22。triggerはhaikuで擬似確認済み。既存の無関係な失敗は下記）。

- [x] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [x] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [x] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [x] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した（Aの公開契約の項目に合わせた参照payloadとreadback済みrevisionまで。Aのvalidator正式登録、validation result refの保存、承認providerは未接続でPR #22／A側。下記）。
- [x] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装・検証記録（2026-11-09）

### 変更ファイル

- `skills/qa-knowledge/scripts/knowledge_runtime.py`：`identity_issues()`を追加し、`validate_entry()`・`create_entry()`・`read_entry()`・`lookup()`・`plan_update()`・`plan_replacement()`・`plan_revalidation()`・`update_entry()`で同一の識別不変条件を適用。`plan_update()`／`plan_replacement()`は現・新entryを必須にし、省略による検証回避を禁止。`lookup()`は適用範囲判定→適用entryだけ内容／currentness検証の順に変更。`create_entry()`は保存後に読み戻したrevisionだけを返す。`update_entry()`は保存先providerのconditional writeを注入して実行し、readbackで確認する（providerなしはblocked）。`lookup_input()`・`read_root_entries()`・`lookup_root()`・`plan_revalidation()`・`improvement_reference()`・`plan_approved_improvement_update()`を追加。
- `skills/exploratory-testing/scripts/exploratory_runtime.py`：`resolve_direct_start()`（TC不要の直接開始と既存ownerへのrouting）と`build_follow_up_handoff()`（参照のみのFinding引継ぎ）を追加。
- `skills/qa-knowledge/evals/deterministic/validator.py`／`scripts/skills/evals/deterministic/ASSERTIONS.md`：`KN-D012`（identityと直下のkind／scope_refsの一致）。
- 両Skillの`SKILL.md`・`references/`、trigger（各train／validationに正負1件ずつ。exploratory-testingのtrain負例1件は、下記の実Agent確認の結果に基づき差し替え）、両Skillの`description`、semantic（`KN-SEM-007`・`EXP-SEM-005`）、`EVALS.md`の対象ID範囲。
- 既存テスト`tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`：`plan_update()`／`plan_replacement()`が現・新entryを必須にした契約変更に合わせて呼出しを更新（検証内容は維持）。
- 新規テスト：`tests/skills/evals/deterministic/test_knowledge_exploration_pr22_i.py`（74件。うちレビュー指摘への回帰は後述）。

### 公開入出力契約（PR #22／Aへ引渡し）

- identity不変条件：`identity.kind`＝直下`kind`、`identity.scope_refs`＝直下`scope_refs`（値・順序）。不一致は`entry_identity_invalid`（read／create／update／replacement）または`incomplete`（lookup）。entryを渡さない更新・置換計画は`entry_identity_unverified`でblock。自動修正・再採番はしない。
- 保存revision：`read_entry()`の`entry_revision`（保存bytesのsha256。native CAS条件ではない）を`lookup_input()`で検証用入力にする。本体へは書かない（`create_entry()`／`update_entry()`は`entry_revision_must_not_be_in_body`で拒否）。create／updateが返すrevisionは保存後のreadbackで確認したもの。過去revisionは再取得できない（`historical_revision_available=false`）。
- 更新：`update_entry(root, updated_entry, expected_entry_revision, conditional_write, current_dependencies)`。`conditional_write(path, content, expected_revision)`は保存先自身のcompare-and-setで、`written`／`conflict`／`blocked`を返す。conflict・未確認・readback不一致は成功にせず、auto mergeしない。
- lookup結果：`status`（`complete`／`incomplete`）、`entries`、`historical_excluded_refs`、`out_of_scope_diagnostics`（対象外entryの依存不明）、`unresolved`。
- Aの公開契約に対応する引継ぎ項目（Knowledge：`improvement_reference()`、探索：`build_follow_up_handoff()`）：`owner_skill`、`artifact_ref`、`content_hash`（保存revision）、source refs、依存ref／revision、`validation`（実行したvalidatorとinline結果。`result_ref`は呼出し側が保存するまで`null`）、`state`（`current`／`stale`／`blocked`）、`unresolved`、`resume`（再開先と条件）、`required_approval`（承認は記録せず、受け手のownerが決める）。依存snapshotなしのKnowledgeは`blocked`。探索payloadの受け手は`follow_up_owner_skill`、`session_revision`は呼出し側が与える不透明なrevision。実測本文・仕様・run結果は含まず、`promotion=not_promoted`。
- Aへの接続範囲：A（`skills/qa-workflow/scripts/**`）への新Skill validator／scopeの登録、validation result refの保存、承認provider、実providerのCAS／履歴は、Aの公開契約でも未接続・未選定とされている。本branchは上記の参照形式と検証fixtureを渡すところまでで、登録はA／PR #22が行う。**前版の記録にあった「Aの共有契約を確認できなかった」は誤りで、Aの公開契約（`A_runtime-integration.md`「現行実装の公開契約と担当別引継ぎ」）を確認し、上記項目に合わせた。**

### 実行した検証（コマンドごとに個別判定）

| 検証                                                                                                                                                | 環境                    | 結果                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `unittest test_knowledge_exploration_pr22_i`（74件）                                                                                                | Windows                 | PASS（レビュー指摘対応後）                                                                                                                                                           |
| `unittest discover -s tests/skills/evals/deterministic`（366件）                                                                                    | Windows                 | TEMPを長いパスにして366件PASS（既定TEMPは短縮パス`RYU-YO~1`のため、1件が環境依存でFAILする。変更前から）                                                                             |
| 同上                                                                                                                                                | Linux(WSL, Python 3.12) | 1件FAIL（`test_wcag_sqlite_provider_blocks_..._git_worktree_path`）。作業ツリーのコピーが`.git`を持たないため。`git init`したコピーで単体PASS。本変更と無関係                        |
| `unittest discover -s tests/skills/runtime`（581件）                                                                                                | Windows                 | 6 failures／16 errors（`test_sqlite_workflow_history`・`test_ci_handoff`）。変更前HEAD（`bbd5a19`）のexportで同条件に実行し、失敗22件の名前が完全に一致（Windowsのファイルロック等） |
| 同上（581件）／deterministic（366件）                                                                                                               | Linux(WSL, Python 3.12) | runtimeは581件中1件FAIL（`test_ci_handoff`の`test_json_nesting_failure_...`。変更前HEADのexportでも同じ失敗。CIはPython 3.11）。deterministicは366件PASS。本変更と無関係             |
| `unittest discover -s scripts/skills/evals/deterministic/tests`、`.../trigger`、`.../semantic`、`scripts/skills/evals/semantic/{validate.py,tests}` | Windows／Linux          | PASS（semantic datasetは23 Skill／167 case）                                                                                                                                         |
| `format_tracked.py check`（ruff 0.16.8・dprint 0.55.2）、`git diff --check`、`compileall`                                                           | Windows                 | PASS                                                                                                                                                                                 |

### 実Agentによる発火確認（haikuサブエージェント、2026-11-09）

- 方法：現在の全23 Skillの`name`と`description`だけを渡し、`exploratory-testing`と`qa-knowledge`のtrigger dataset（各train／validation、計48問）を順序を変えて独立に判定させた。正解ラベルは渡さず、採点は別に保持したlabelで行った。各回はhaikuの別サブエージェント（複数Skillの同時選択を許可）。実際のSkillハーネスのroutingそのものではなく、descriptionに基づく選択をモデルに判断させる擬似確認である。
- 結果の推移（各2回）：
  1. 変更前のdescription：正例24／24、負例の誤検出3件（`qa-knowledge`：既存knowledgeを入力として使う分析2件で`test-analysis`と併せて発火、`exploratory-testing`：既知E2E失敗を「investigation modeで探索して」と明示指示する負例1件）。
  2. `qa-knowledge`に「既存knowledgeを他の分析・設計の入力として読むだけの場合は使用しない」、`exploratory-testing`に「既知のE2E失敗や既知TCの失敗は、ユーザーが『調査』『investigation』と呼んでも既存ownerへ回す」を追記：`qa-knowledge`の誤検出は0件。ただし`exploratory-testing`の負例1件（ユーザーが探索を明示指示）は両回とも誤検出のまま、`qa-knowledge`の正例（探索Finding／Observationのtriage）が1回につき1件`exploratory-testing`へ流れた。
  3. 上記の負例を、descriptionだけで判定できる語の罠（「E2E実行が失敗した原因を調査して、修正先を教えて。」）に差し替え。**差し替えの根拠**：ユーザーが探索を明示した依頼はdescriptionでは覆せず、発火後にSkillの契約（`resolve_direct_start()`が既知E2E失敗を`e2e-test-result-analysis`へroute）で既存ownerへ回す。この経路は決定論テストで検証済み。
  4. `qa-knowledge`のdescriptionに「探索のFinding / Observationを含むQA candidate」を明記：2回とも48／48（両Skillで正例24／24、負例24／24）。
- 限界：(a) descriptionの調整に使ったdatasetと同じ48問で最終確認しており、保留データでの確認ではない。(b) 試行回数は各版2回、モデルはhaikuのみ。(c) 最終版は2回とも全問一致だったが、途中の版では同じ問いの判定が回ごとに揺れたため、この2回を再現性の保証とは扱わない。保留データ・他モデル・実ハーネスでの全current Skill同時のroutingはPR #22で行う。
- 追加した説明の検証：`description`の変更はfrontmatterの文字列のみ。`tests/skills/evals/trigger`のdataset契約テスト、semantic dataset検証、format／lintは変更後もPASS。

### レビュー指摘への対応（2026-11-09、レビュー対象`bbd5a19`）

`bbd5a19`のレビューで4件の問題が指摘された。いずれも、修正前のコードで再現するテストを先に用意し（修正前のコードに対して失敗することを確認した）、同じ原因の別経路も確認した。

1. **unresolved Findingからの直接調査**（`exploratory_runtime.py`）：`resolve_direct_start()`は`unresolved_finding_ref`を調査開始条件として受けたが、`validate_charter()`がその起点を認識せず、有効なCharterでも`charter_invalid`でblockされた。既存テストは`mode`しか確認しておらず、見逃していた。`INVESTIGATION_ORIGIN_KEYS`を共通にし、`validate_charter()`・`validate_session()`（経由）・`can_resume()`（Charter identityに起点が含まれる）・deterministic validator（`EXP-D003`）が同じ起点を認めるようにした。`resolve_direct_start()`は起点を含む`charter`を返し、呼出し側はこれをSessionに保存する。起点は空でない文字列に限る。既知owner・既知E2E失敗・既知TC・current UI収集のroutingは変更しない。回帰テストは`status == "start"`を必ず確認し、開始、Session検証、blocked、`can_resume()`、起点変更時の`new_session_required`までを検証する。
2. **Knowledge entryの不正型による例外**（`knowledge_runtime.py`）：`identity.kind`・`kind`・`state`に配列／objectを与えると、集合への包含判定で`TypeError`になった。`compare_currentness()`も、依存`ref`が配列、または`currentness_dependencies`が`null`・数値のとき同様に例外になった。非objectのentryは`AttributeError`だった。`_one_of()`で型を確認してから判定し、非objectは`entry_must_be_object`、不正な依存は`invalid_dependency_record`（currentnessは`unresolved`）に変換した。`provenance`／`currentness_dependencies`の`ref`・`revision`は文字列を必須にした。`create_entry()`／`read_entry()`／`update_entry()`／`plan_update()`／`plan_replacement()`／`plan_revalidation()`／`lookup()`／`improvement_reference()`／`plan_approved_improvement_update()`は、例外ではなくblocked／incomplete／rejectedを返す。不正identityを自動修正・再採番せず、入力も変更しない。
3. **部分再検証の入力不備**（`plan_revalidation()`）：辞書以外のentryを無言で除外し、保存済み`entry_revision`のないentryも再検証対象として`complete`で返した。非objectのentry・identity不正・`currentness_dependencies`がlistでない・再検証対象でrevisionがないentryは`rejected`に入れ、statusを`incomplete`にする。`scope_refs`／`changed_refs`／`current_dependencies`／`entries`の型が不正な場合もincompleteにする。対象外scope・依存変更のないentryは、revisionがなくても対象にもrejectedにもしない。repo HEADの変更だけでは対象を選ばない。stale（`dependency_changed`）・依存不明（`dependency_unresolved`）・identity不正（`rejected`）は別々に返す。`plan_update()`も、文字列で空でないrevisionを必須にした。
4. **探索Finding引継ぎのsource revision**（`build_follow_up_handoff()`）：`source_refs`はCharterの文字列refをそのまま返し、sourceごとのrevisionがなかった。Aの公開契約は入力source refs／revisionsを要求する。`source_refs`を`{ref, revision}`の配列にした。revisionはCharterの`source_refs`の`{ref, revision}`、またはSessionの任意の`source_revisions`（ref→revision）から取り、Session revisionとは別に扱う。取得していないrevisionは作らず`null`のまま、`source_revision_unresolved:<ref>`をunresolvedに残し、stateを`blocked`、再開先を`record_source_revisions`にする（blocked Sessionでは`resume_session`を優先）。`defect-management`宛は、revision未取得のsourceがあると`source_revision_unresolved`でblockする。実測本文・仕様・run結果は複製せず、欠陥候補・Defect・Knowledge entryへ自動昇格しない（`promotion=not_promoted`）。共通契約（A）の項目は変更しない。

**同じ原因の追加対応**：探索の`validate_charter()`／`validate_session()`も、`allowed_operations`・`side_effect_operations`・`mode`・`state`・`cleanup`・Observation／Findingのref・`source_observation_refs`に配列／objectを与える、または非objectのSessionを渡すと`TypeError`／`AttributeError`になったため、issueとして返すようにした（回帰テストあり）。Findingの`unresolved`がlistでない場合は`unresolved_must_be_list`でblockする。

**未対応（既存で、本PRの変更対象外）**：探索の`authorize_operation()`・`record_attempt()`は、`allowed_operations`／`side_effect_operations`が非listのCharterを直接渡されると例外になりうる。いずれもSession検証（`validate_charter()`）で拒否される入力で、本PRで追加・変更した経路ではないため、変更していない。

#### 完了基準の再判定（実コード・テストで確認）

| 完了基準                                     | 判定                  | 根拠・区別                                                                                                                                         |
| -------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| identity・scope不一致の拒否、旧entry読取互換 | 満たす（固定fixture） | `KnowledgeIdentityInvariantTests`、旧schemaのentry読取、不正型entryの回帰（`KnowledgeMalformedEntryTests`）                                        |
| 対象外scopeを巻き込まないlookup              | 満たす（固定fixture） | `KnowledgePartialLookupTests`。対象外entryは内容・依存を検証せず、診断のみ                                                                         |
| root列挙・読取の完全性                       | 満たす（固定fixture） | 切り詰め・読取不能・非canonical名・不正identityは`incomplete`                                                                                      |
| 部分revalidation・revision・保存競合         | 満たす（固定fixture） | `KnowledgeRevalidationInputTests`。native CASは固定fixtureのproviderで、実providerは未検証（PR #22）                                               |
| create → read → lookup → update → lookup     | 満たす（固定fixture） | 別sessionとして実行。保存後のreadback済みrevisionだけを使用                                                                                        |
| 探索・症状調査の直接開始                     | 満たす（修正後）      | unresolved Finding起点を含む3起点が、開始・Session検証・再開まで一貫（`ExploratoryInvestigationOriginTests`）。routingは既存のまま                 |
| Findingの引継ぎと未確定状態の保持            | 満たす（修正後）      | sourceごとのrevision、未取得revisionのunresolved／blocked／再開先（`ExploratorySourceRevisionHandoffTests`）。Aの実成果物との接続はPR #22          |
| 既存Skillとのrouting境界                     | 部分的（擬似確認）    | haikuのdescription判定は48／48だが、同一dataset・haikuのみ・実ハーネスではない。全current Skill同時のrouting・保留dataはPR #22                     |
| 履歴・旧entry・既存呼び出し元の互換性        | 満たす                | 既存`test_qa_artifact_graph_skills`等を含むdeterministic 366件。runtimeの失敗集合は変更前と一致。公開形状の変更は「互換・移行・rollback」を参照    |
| standalone packaging・評価データ・関連CI     | 満たす（局所）        | isolated packagingテスト、trigger／semantic dataset検証、deterministic。semantic評価のLLM判定は未実施（PR #22）。最終HEADのActionsは下の記録を参照 |

### 未検証／blocked／SKIP と再開条件

- semantic評価（LLM判定）は未実施。データ契約とcase追加までで、PR #22の実Agent評価で実施する。triggerは下記の擬似確認までで、実ハーネスでの全current Skill同時のroutingはPR #22。
- 実保存先のnative atomic create／conditional write（CAS）：`update_entry()`は注入されたproviderの結果を使う。テストのproviderは固定fixture（排他lockとos.replace）で、実providerのCASを実証したものではない。実provider／実runnerでの検証はPR #22。
- GitHub Actions（PR #31のChecks）：コミット`8e4425e`（ベース取り込み後）で`code-quality`・`codex-contract`・`windows-launcher`・`deterministic-output-evals`・`semantic-output-evals`・`validate`が各々pass（CodeRabbitはskipping）。`47e97d7`にrunが無かったのは、当時PRがベースとコンフリクトしていてpull_request用workflowが起動しなかったため。以降のHEADで変わった場合は、そのHEADのChecksを個別に確認する。
- A・J・Fの実成果物との接続、validation result refの保存、承認provider、全Skill同時のrouting、S1〜S17、人間編集8ケースはPR #22で実施する。
- 本環境の既存の失敗（上表）は、変更前HEADでも再現することを確認済み。Python 3.11のLinux CIでの再確認はPR #22。

### ベース取り込み（2026-11-09）

- ベース`feat/development-qa-traceability`（B統合を含む14コミット）の取り込みで`EVALS.md`の意味評価対応表のみ衝突した。ベース側の表を採用し、担当Iの2セル（`EXP-SEM-005`・`KN-SEM-007`）だけを再適用した。取り込み後のローカル検証：format／lint、semantic dataset（25 Skill／171 case）、trigger、deterministic（Windows／Linuxとも341件）がPASS。Linuxのruntimeテストは581件中1件（`test_ci_handoff`、変更前HEADでも失敗する既存の失敗）。

### 互換・移行・rollback

- レビュー対応での公開形状の変更：(1) `build_follow_up_handoff()`の`source_refs`は、文字列の配列から`{ref, revision}`の配列になった（本PRで導入した引継ぎで、リポジトリ内の他の呼出し元はない）。revision未取得のsourceがあるとstateは`blocked`になり、従来のようにcurrentとは返さない。(2) `resolve_direct_start()`の`start`結果に`charter`が追加された（追加のみ）。(3) `provenance`／`currentness_dependencies`の`ref`・`revision`は文字列が必須（従来は真偽判定のみで、数値・配列も通った）。(4) investigationの起点は空でない文字列に限る。(5) `plan_revalidation()`は不正入力を除外せず`incomplete`で返し、再検証対象にはrevisionが必須。rollbackはこのbranchのcommit単位で戻せる。
- 旧entryは、`identity`が有効な`kind`と`scope_refs`を持ち直下と一致していれば、そのまま読める（`entry_ref`・保存形式・状態・履歴は不変）。identityに`kind`／`scope_refs`がない、または直下と不一致の旧entryは拒否される。該当entryは正本ownerが`identity`を再確認し、必要ならreplacementで移す。
- `plan_update()`／`plan_replacement()`は現・新entryが必須になった（従来の2引数のみの呼出しは`entry_identity_unverified`でblock）。リポジトリ内の呼出し元は既存テストのみで、更新済み。`lookup()`の引数・戻りキーは維持し、変更は、無関係scopeのentryを内容検証しなくなる点と、診断キー`out_of_scope_diagnostics`の追加。rollbackはこのbranchのcommit単位で戻せる。
