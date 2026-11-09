# PR #22 並行実装：F — QA要求・アーキテクチャ・管理

## 位置付け

QA活動の要求・レベル／方式／環境の全体割当・計画と監視／是正を、既存製品仕様・設計・workflow状態から独立した正本として実装する。

- 作業branch：`feat/pr22-f-qa-planning-architecture`
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

関連完了条件の主な担当：QA全工程 1・2・3・5・8。報告・評価本体はJ。

## このbranchで変更する対象

- 新設`skills/test-requirements-analysis/**`、`skills/test-architecture-design/**`、`skills/test-management/**`
- QA要求・レベル割当・計画改版・project risk・source inventoryのデータ契約・局所テスト

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

- [x] 既存Project Context・TR・Risk・test-analysis・qa-workflow・Regressionの正本、計画source ref、承認要件を確認した。
- [ ] Aと保存／承認、Eとレベル優先順、Jと計画母集団を合意した。

## 作業内容

1. QA活動の要求元・目標・対象／非対象・品質条件・承認根拠・未決定を記録する。製品要求・TRの第二の正本を作らない。
2. テストレベル・タイプ・方式・環境・データ・非機能品質特性の割当を管理し、明示指定＞承認済みarchitecture＞既定値の優先と改版影響を扱う。
3. suite・実行時点・対象build・担当・工数／資源・入口／終了基準・監視・project risk・是正を管理し、`qa-workflow`のrouting stateとRegression Runを二重管理しない。
4. 予定source inventoryと必要実行の母集団をJへ渡し、未取得結果・未実行・取消しの区別を維持する。
5. 承認済み計画の改版・失効、承認前の計画を現行扱いしない負例、environment／architecture変更の局所再評価を検証する。
6. 既存成果物からの管理／報告だけの直接開始と、新設B/D未実装時の単独受入を可能にする。

## 依存と引継ぎ

- B→F：配置・Project Context参照。
- F→E：承認済みレベル／方式・環境割当。`test-analysis`編集はEへ依頼する。
- F→G/H/J：実行計画・source inventory・終了条件・承認revision。
- A：承認／保存／workflow runtimeの共有変更依頼。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 3 Skillが単独・複合で正しく発火し、QA要求・architecture・計画を製品仕様や個別TRと区別できる。
- [x] QA要求→レベル／方式割当→計画／進捗・是正・終了基準への正規refが成立した（担当fixtureでrevision chainを検証）。
- [x] 変更前後の承認・revision・currentness、環境・方式変更、未取得sourceを扱い、未承認計画を現行にしない（担当fixtureの静的受入まで）。
- [x] レベル変更が必要なRisk・正式設計・testware準備にだけ伝わり、無関係なcurrent成果物を保持した（担当fixtureで影響scopeと保持対象を照合）。
- [x] Jが集計に利用できる正式な実行母集団・取得範囲の出力契約とfixtureを本書に記録し、既存Regressionとの重複正本を作らない。Jの実成果物との照合はPR #22へ引き継いだ。
- [ ] isolated/trigger/semantic・決定論的・統合評価と保存／承認の負例を実行した。

- [x] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、isolated packaging・決定論的テスト・semantic／trigger datasetを揃えた。Judgeと実Agentによるsemantic／trigger評価は別途未実施。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 担当branch内の全局所受入は未完了。外部provider／実Agentに依存する項目はblockedとして条件を記録し、Windows runtimeで失敗した共有テストはAへ引き継ぐ。PR #22のみで行う横断検証と15＋10条件の最終判定は、担当branchの受入と区別して引き継ぐ。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## PR #28レビュー指摘対応・追加検証記録（2026-11-09）

### 実装・修正内容

既存の3 Skillを維持し、担当Fのテスト管理契約にあったsource inventoryと完了判定の不足を修正した。

- 予定するsource／実行母集団と、source ownerから取得したreadback台帳を別表にした。readbackには実際のowner、ref、revision、scope、取得範囲、実行単位、build、environmentを記録する。
- 取得済み・部分取得・未取得・取得不能・確認済み0件・不明と、実行済み・実行中・未実行・取消・実行失敗・結果不明・対象なしを区別する。取得不能の行に架空の実refを入れない。
- readbackの識別情報を予定母集団と比較し、revision、scope、範囲、実行単位、build、environmentが異なる結果を集計しない。monitoring件数はplan revision、scope、build、environmentごとに照合する。
- 実行基盤の失敗は「実行失敗／判定不能」として記録し、テスト結果のFAILと混同しない。
- 必須populationに実行結果またはreadback根拠付きの確認済み0件がなく、または終了基準に最終判定がない場合は完了扱いしない。plan全体を完了にする際は、必須グループごとの完了snapshotを要求する。
- 原因は、旧契約が予定母集団と実取得結果を同じ行で扱い、実体の識別照合と必須実行結果の欠落検査を十分に持たなかったこと。変更はF担当内のtemplate、運用・データ契約、validator、fixture、テストに限定した。
- test_f_planning_contracts.pyを11テストへ拡張した。readback revision/build不一致、未実行runの偽完了、確認済み0件と未取得の区別、実行基盤失敗とテストFAILの区別を回帰確認する。
- dprintがMarkdown tableを整列するため、担当テストはtable cellを正規化して評価する。fixtureの意味内容は変更していない。

変更対象はこの担当文書、skills/test-requirements-analysis/**、skills/test-architecture-design/**、skills/test-management/**、tests/skills/evals/deterministic/test_f_planning_contracts.py。shared README、Aのruntime／registry／routing、E・J担当ファイルは変更していない。新しい実行依存関係は追加していない。

### 担当Fの公開契約・fixture引渡し

| Skill / package                                                 | 入力・責務と出力                                                                                                                                                                                                                                       | 決定論的validator・基準fixture                                                                                                                                                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| test-requirements-analysis (skills/test-requirements-analysis/) | QA活動の目的、要求元、品質目標、対象／非対象、制約、未決事項を整理する。製品仕様・個別TRの正本を作らず、要求元ref／revision／scope／currentness、要求ID、状態、同一scope・artifact ref・revisionに結び付く承認参照を出力する。                         | evals/deterministic/validator.pyのvalidate(text, expected, eval_id)。QRA-OUT-001は承認済みQA要求、QRA-OUT-002はblocked／未承認要求。                                                                            |
| test-architecture-design (skills/test-architecture-design/)     | QA要求のartifact ref・要求ID・revisionを入力し、targetごとの複数level、test type／方式、environment／data、runner、選択根拠、準備状態、変更影響、保持するcurrent成果物を出力する。優先順位は明示指定 ＞ 承認済みarchitecture ＞ system test既定値。    | evals/deterministic/validator.pyのvalidate(text, expected, eval_id)。TAD-OUT-001はcurrentな複数level割当、TAD-OUT-002はconflict／unknownを保留するケース。                                                      |
| test-management (skills/test-management/)                       | currentなQA要求・architectureを入力し、suite／schedule／build／owner／工数・資源、入口・終了基準、project risk、改版・承認、予定population、実取得readback、monitoringを出力する。Regression Run、raw result、workflow routing stateの正本は作らない。 | evals/deterministic/validator.pyのvalidate(text, expected, eval_id)。TMG-OUT-001は実取得／実行済み、TMG-OUT-002はsource未取得・旧revision承認。両fixtureで取得0件と未取得、実行失敗とテストFAIL等の回帰を追加。 |

各packageのevals/output/evals.jsonがoutput manifest、assets/output-template.mdとreference fixtureのMarkdown tableが現在の局所入出力契約である。独立したJSON Schemaは定義していない。共通決定論的runnerはmanifestからFのvalidatorを読み込め、6 fixtureをrunner経由でもPASSした。これはAのowner verifier登録やqa-workflow routingの完了を意味しない。

Aに渡す共通handoffでは、owner skill、scope、artifact ref／revision、source refs／revisions、validatorと評価結果ref、承認・依存、状態、未解決・resumeをそろえる。Fのartifact本文は自身のcontent hashを生成しない。保存後の正確なcontent hashはA runtimeが取得し、artifact ref／revisionと一緒に結び付ける。Fのsource currentnessはcurrent / stale / unknown、処理状態はartifact statusおよびblocked／再開欄に保持する。A runtimeは、能力のないproviderを成功にせずunsupportedとして外へ返す契約を維持する。Fの静的validatorは参照文字列を検査するだけで、承認者の認証、署名、provider-native CAS、独立readbackを実証しない。

### 検証環境・実施結果

使用環境はWindows、Python 3.11.9のプロジェクト専用.venv。事前のpython -m pip show PyYAMLはsystem Pythonに未導入だった。以下を.venvに導入し、repository dependency fileは変更していない。

- python -m pip install "PyYAML==6.0.3"
- python -m pip install "ruff==0.16.8"
- python -m pip install "git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref"

使用versionはpython --version = 3.11.9、PyYAML = 6.0.3、Ruff = 0.16.8、dprint = 0.55.2、公式skills-ref = 0.1.0（CI固定revision 69ef37e9424c0a7ea9dd2293b559e43ec8176379）。dprint executableは一時領域に置いた。

- python -m unittest discover -s tests/skills/evals/deterministic -p 'test_f_planning_contracts.py' -v — PASS 11、FAIL／ERROR 0。
- python -m unittest discover -s scripts/skills/evals/deterministic/tests -v — PASS 12、FAIL／ERROR 0。
- python -m unittest discover -s tests/skills/evals/deterministic -v — PyYAML導入後、PASS 301、FAIL／ERROR 0。導入前は214件実行で1 failure／24 errors。tracebackは共通loaderが既存test-execution validatorをimportする際のModuleNotFoundError: yamlで、残る1 failureも同じ依存不足によるdeterministic CLI load失敗だった。導入後に全301件が通り、Fの不具合ではないことを確認した。
- python scripts/skills/evals/deterministic/run.py --help — PASS。各output manifestから6件（QRA-OUT-001/002、TAD-OUT-001/002、TMG-OUT-001/002）をrunnerで個別実行し、PASS 6、assertion合計107、ERROR／WARNING 0。
- python -m compileall -q scripts/skills/evals/deterministic、python -m compileall -q skills/test-requirements-analysis、python -m compileall -q skills/test-architecture-design、python -m compileall -q skills/test-management、python -m compileall -q tests/skills/evals/deterministic — 各PASS。
- python scripts/skills/evals/semantic/validate.py — PASS、26 Skill／168 case。Fの3 semantic caseは実Agent出力から期待値を作らず、各inputに独立referenceとrubricを持つ。
- python -m unittest discover -s scripts/skills/evals/semantic/tests -v — PASS 25、SKIP 2（Windows symlink privilege；計27件）。python -m unittest discover -s tests/skills/evals/semantic -v — PASS 12、SKIP 1（同権限；計13件）。
- python -m unittest discover -s tests/skills/evals/trigger -v — PASS 1。Fのtrain／validationは各Skill 12／8件、各split内でpositive／negative均衡、split間で重複なし。QA要求、level／方式／environment、計画・進捗・終了条件の単独発火と、製品仕様／TR／Risk／Regression／result reportingの誤発火例を含む。実Agentでの単独・複合発火と全current Skill同時利用は未実施。
- semantic Judgeによる実採点、実Agentのsemantic出力、実Agent triggerは未実施。ローカルにQA Agent／Judge runnerがなく、codex CLIも見つからなかった。dataset形式・独立期待基準の検証と意味採点を区別する。
- skills-ref validate skills/test-requirements-analysis、skills-ref validate skills/test-architecture-design、skills-ref validate skills/test-management — 固定revisionで3件ともPASS。
- ruff --version — ruff 0.16.8。python scripts/format_tracked.py ruff-check、ruff check --config ruff.tomlとruff format --check --config ruff.tomlを4つのF担当Pythonファイルへ明示指定 — PASS。
- dprint --version — dprint 0.55.2。python scripts/format_tracked.py checkはtracked filesを検査し、F package内の51 Markdown／JSONはdprint check --config dprint.json --config-discovery=false --no-gitignoreで別途明示指定した。tracked-only scriptから漏れる新規fileも検査対象に含め、すべてPASS。
- validate-skills workflowのrepository eval structureと同一の静的検査 — frontmatter、Skill名、trigger形式・均衡・分割は通過。README rosterだけFAILし、不足はtest-architecture-design、test-management、test-requirements-analysisの3名。root READMEはA担当のため変更しない。
- python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v — Windowsで496件、PASS 471、FAIL 5、ERROR 14、SKIP 6。5 failuresはtest_ci_handoffで安全なartifact readbackがWindowsでartifact_readback_unavailableを返し、POSIX readback前提のテストがPASSを期待したもの。14 errorsは既存test_sqlite_workflow_history群の一時SQLite DB削除時にPermissionError [WinError 32]となるcleanup失敗。Linux実行で切り分ける必要がある。SKIP 6件はPOSIX専用FIFOまたはsymlink作成権限不足で、実装PASSを意味しない。
- Linux再実行は未実施。WSL distro照会はE_ACCESSDENIED、Docker daemonは接続不能だった。PR #23 A契約上、Windowsのsafe readbackはunsupported/blockedと扱われる。runtime failures／SQLite cleanupのownerはshared QA workflow/runtimeのA。F Skillコード変更が原因とは確認されていないが、Linux CI相当でPASSを確認するまでruntime回帰は未解消として扱う。
- GitHub Actions自体は起動していない。

### 承認・revision・保存に関する判定

担当validator／fixtureで、未承認QA要求、artifact revisionに結び付かない承認、旧plan承認、stale／未取得source、QA要求revision mismatch、readback未取得、readback ref／revision／build不一致、scope内の未実行必須run、確認済み0件と未取得の混同、実行失敗とtest FAILの混同、monitoring件数不一致、偽の完了を拒否・未完了分類する。これらは独立fixtureを使った文字列／表契約検証であり、外部artifactの存在や承認主体の認証を証明しない。

実provider、認証主体、provider-native CAS、独立した保存先readbackは未選定／未接続。以下はblockedで、fixture応答を成功証拠にしない。

- blocked owner: A（共有runtime/provider契約と接続主体）、PR #22でproviderと実成果物の統合確認。
- 必要条件: providerと認証方式の選定、読み書き主体・承認主体の権限、実artifact source、native CAS／履歴、独立readbackが利用可能であること。
- 再開手順: A runtimeからreadbackしたowner／ref／revision／scope／content hash／approvalをFの計画sourceと照合し、成功・権限拒否・未取得・更新競合・revision変更・不正／未信頼入力を実providerで再試験する。
- unsupported capabilityはblockedの成功に読み替えない。Aの正式runtimeがunsupported状態を返し、承認／保存／計画完了を閉じないことを確認する。

### Plan完了条件と判定

- QA要求→architecture→planのref／revision chain — PASS（F fixtureと6 output eval）。実owner成果物同士の接続はPR #22。
- 承認・revision・currentnessと変更影響 — F validatorの負例はPASS。実認証・provider読戻しはA接続待ちでblocked。
- 計画母集団・取得範囲のJ handoff — F側の予定populationと実取得readbackの契約・validator・fixtureを本書とpackageに記録済み。Jの実consumerとの照合はPR #22。
- 正式Skill仕様・isolated package — 3 Skillともskills-ref PASS。F output evaluatorの6件PASS。
- deterministic／syntax／format/lint — 担当11件、共通deterministic 12件、全301件、compileall、Ruff、dprintはPASS。PyYAMLの24 errorsと1 failureは解消。
- semantic／trigger — data形式、独立reference／rubric、train／validation分割はPASS。実Agent／Judgeは未実施なので完了扱いしない。
- 旧consumer／runtime回帰 — legacy output suiteはPASS。共有runtime suiteはWindowsのFAIL／ERRORが残り、Linux再確認が必要。
- Skill登録・routing — README rosterは3 Skill不足。AのCANONICAL_SKILLS／owner verifier registryおよびqa-workflowのRUNTIME_V2_SKILL_ROOTSにもF 3 Skillが未登録。Fは共有fileを編集せずAへ契約を渡す。
- 保存／承認／CAS／readback — 実provider未選定のためblocked。成功・完了とは扱わない。
- PR #22横断受入 — 全current Skillの同時利用、Fを含むrouting、実owner成果物接続、実Agent／Judge、実provider／runner、S1〜S17、人間編集8ケース、15＋10完了条件と詳細Plan 01〜08の最終照合を実施する。

### ownerへの引継ぎ

**A（PR #23／共有runtime）**

- root README.mdに3 Skill名を登録。shared evalのCANONICAL_SKILLS、F validatorを正式owner verifierとして読み込むregistry、qa-workflowのRUNTIME_V2_SKILL_ROOTS／routingへ登録する。
- F packagesの入口は上記3つのSKILL.md、output templates、evals/output/evals.json。validator入口は各evals/deterministic/validator.pyのvalidate(text, expected, eval_id)。fixture IDsはQRA-OUT-001/002、TAD-OUT-001/002、TMG-OUT-001/002。F固有の追加負例はtests/skills/evals/deterministic/test_f_planning_contracts.py。
- A統合テストで正式registry／loaderから6 output evalと3 owner verifierを呼び、単独／複合routing、source ref・revision・scope・hash、approval scope／revision、missing artifact、readback unavailable、権限拒否、CAS conflict、partial source、未信頼入力、unsupported capabilityを確認する。共通runnerが6 fixtureを呼べることは確認済みだが、owner verifier登録は別作業。
- Windows runtime 5 failureとSQLite cleanup 14 errorをPOSIX/Linux CI相当で再実行し、Windowsのunsupported contract・SQLite file handle cleanupの扱いを判定する。

**E（PR #27／正式設計）**

- architecture出力のQA要求 artifact_ref#QAR-ID@revision、source owner／scope／revision／currentness、明示指定 ＞ 承認済みarchitecture ＞ 既定system test、複数level、影響scope・保持するcurrent成果物を入力契約として利用する。
- Fはtest-analysisやformal designの正本を編集していない。level変更からRisk／正式設計／testware準備への影響再評価はE ownerの実成果物で確認する。

**J（PR #32／reporting）**

- planned populationとactual source owner readbackを別入力として利用する。readback fields: population ID、source owner/ref/revision/scope、取得範囲、execution unit、build、environment、currentness、取得／実行／結果状態、readback ref、未取得／未実行理由。
- monitoring件数はplan ref/revision・scope・build・environment単位。未取得、部分取得、取得不能、確認済み0件、未実行、取消、実行失敗、結果不明、test FAILを統合しない。実行結果・reportはJ側の正本で、Fは複製しない。
- FのfixtureとvalidatorはJの実source owner readbackの証拠ではない。実集計はPR #22で照合する。

### PR #22への引継ぎ

PR #22ではA〜Jの実artifactを保存・readback後に接続し、Fが保持したowner・scope・revision・approval・population identityと比較する。全current Skill同時利用の複合trigger／routing、実Agentでの意味出力とJudge、実provider／runnerのCAS・履歴・readback、未取得／失敗／再開、S1〜S17、人間編集8ケース、15＋10条件・詳細Plan 01〜08の最終判定を行う。担当Fの局所deterministic PASSをこれらの代替にしない。

### 再レビュー・文書と実装の差異

- **共有README差異**: README.mdに新設3 Skillが未掲載。validate-skills workflowのREADME roster assertionを再現し、3名不足でFAILした。責任ownerはA。Fでは変更していない。
- **共有runtime差異**: Fはgeneric deterministic output runnerで利用でき、manifest経由の6 fixtureはPASS。一方、shared CANONICAL_SKILLS、正式owner verifier registry、qa-workflow routingにはFが未登録。責任ownerはA。これは共通eval runnerのfixture実行と業務runtime登録を区別する。
- **state／hash契約境界**: F本文はsource currentnessをcurrent / stale / unknown、処理失敗をblockedとして表現する。unsupportedと自己artifactのcontent hashはA runtime層の判定／計算とし、F validatorでは代替しない。Aのruntime結果とF artifactの対応はPR #22で確認する。
- **Fの内部整合**: 予定inventory、実readback、template、validator、fixtureは今回の修正で照合し、追加の内部文書／コード差異は確認していない。
- **PR #17／#10互換性**: 両PRの公開範囲・正本契約を再確認した。Fはlegacy Skill・共通runtime・既存consumerを編集していない。deterministic legacy suiteはPASS。共有runtime全体は上記Windows failureのため、互換性全体をPASSとは判定しない。

変更一覧・実行証拠はこの担当文書およびworktreeの差分で確認できる。commit／push／merge・PR本文更新は行っていない。
