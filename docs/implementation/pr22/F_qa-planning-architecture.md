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

## PR #28レビュー指摘修正・最終検証（2026-11-10）

この節は2026-11-09の検証記録を更新する。対象branchは`feat/pr22-f-qa-planning-architecture`、作業開始時HEADはレビュー基準`f86e4bc4f56b95c831997d8ca9088ee7846d8400`で、開始時のworktreeはcleanだった。現在の差分はF担当Skill・F担当文書・F回帰テストだけである。レビュー修正の記録時点ではGitHubへのpush、PR本文更新、commitを行っていない。

### Commit／push確認（2026-11-10）

今回の公開作業開始時は対象branch `feat/pr22-f-qa-planning-architecture`、HEAD `f86e4bc4f56b95c831997d8ca9088ee7846d8400`。worktreeにはこの修正作業で作成した22件のtracked変更があり、未追跡ファイルはなかった。変更pathは3 Skill配下、`tests/skills/evals/deterministic/test_f_planning_contracts.py`、この担当文書に限定され、A所有のREADME・共通runtime・routingや生成物は含まない。

`git fetch origin`は成功し、commit前の`git rev-list --left-right --count HEAD...origin/feat/pr22-f-qa-planning-architecture`は`0 0`。remote-only／local-only commitはなく、履歴同期は不要。秘密情報を含む高信頼形式、意図しないpath、テスト失敗を隠す差分はpush前確認で検出されていない。追記した担当文書はdprint 0.55.2の`dprint fmt`と`dprint check`をPASSした。初回pushはHTTPS認証エラーになったが、その後の通常pushは成功した。

修正commit `be63df06b05970811e966d2f81b589400cc73e34`（`fix(pr28): address planning validator review findings`）と記録commit `ffc1030637f3e65f15c8298bb8ae590a8380f6c3`（`docs(pr28): record push authentication blocker`）はGitHubへpush済み。`git ls-remote --heads origin feat/pr22-f-qa-planning-architecture`とGitHub PR取得でremote／local SHA `ffc1030637f3e65f15c8298bb8ae590a8380f6c3`の一致を確認した。PR #28はopen／Draftのままで、PR本文は更新していない。

### push後Code Quality対応（2026-11-10）

push済みhead `ffc1030637f3e65f15c8298bb8ae590a8380f6c3`のCode Quality run #859が、TMG validatorの未使用`risks`代入（Ruff F841、当時の1150行目）でFAILした。`risks = risk_rows_for_closure`を削除し、同じtracked format checkで示されたTAD/TMG validatorとF回帰テストのRuff format差分も既存formatterで整形した。これらはFの既存変更ファイルに限る。follow-up後の`uv run --with ruff==0.16.8 python scripts/format_tracked.py check`は221 tracked files PASS、F回帰30件も再実行してPASSした。修正はcommit `caa5ed1f80c28bd392bd3daaeca6b3734f7c1ddf`としてpush済みで、remote SHAと一致する。ActionsはAgent Skillsを除く4 workflowがPASSし、Agent Skillsは担当AのREADME登録不足でFAILした。

### 指摘別の修正結果

| 指摘                                 | 原因と修正                                                                                                                                                                                                                                                                            | 結果                                                                                                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| deterministic inputのtemplate参照4件 | QRA case-002、TAD case-002、TMG case-001/002の各`input.md`に`assets/output-template.md`参照を追記した。シナリオ・入力条件・期待・拒否条件は維持。                                                                                                                                     | CIと同じdataset検査で25 Skill／52 caseがPASS。3 Skillの6保存reference fixtureを既存runnerに通して6件PASS。これは実Agent出力ではない。                                                |
| TMG readback欠落時のKeyError         | status表を有効な状態行だけで構成し、欠落・不正・重複IDをD013の証拠に含める。監視件数は全populationに状態がある場合だけ算出し、D015に欠落ID、D018に完了不可を出す。空辞書の状態キー参照を`.get`へ変更。                                                                                | 必須／任意1件欠落、複数欠落、完了snapshotとの同時発生、不正readback行を30件のF回帰で検証。欠落状態を0件・未実行へ補完しない。                                                        |
| 未承認`進行中`計画                   | D023を承認済み・進行中・完了に適用し、scope／artifact ref／revision／主体／証拠refを一致させる。D020で参照するQRA/TAD sourceのowner／ref／revision／scope、取得状態、currentness、必要承認を確認。草案／blockedの読取・分析は維持。                                                   | 未承認・旧revision・scope不一致を拒否し、currentな承認済み計画を維持。validatorの文字列検査は実承認主体の認証と区別。                                                                |
| Risk／action／差異を残す完了         | D017/D022/D024で状態証拠と正式受容・対応不要の主体を要求。D018でsnapshot scopeに該当する未処理項目、根拠不足、未知scope、終了基準未判定を拒否し、snapshot差異summaryと差異IDも照合。ID欠落行をテーブル走査から落とさない。                                                            | 対応中risk、blocked action、open difference、証拠なし、未知scopeを拒否。scope外riskは維持。実行済みFAILおよび証拠付きの正式な終了基準未達は、QA活動の終了と製品release可否から分離。 |
| stale／未取得のQA要求・割当          | QRA-D015/D013とTAD-D015/D016でsource owner／ref／revision／scope／currentness／取得状態／必要承認を確認。fixtureでknown local IDを照合し、表のID/refが空の行も検査対象へ含める。                                                                                                      | 未確定要求・割当はdraft／blockedに保持可能。確定artifactからstale／unknown依存を拒否し、source一覧にない依存も確定扱いしない。                                                       |
| TAD-D011優先順位                     | targetごとに明示指定・承認済み割当・既定system test、競合、全level、実assignmentを比較。優先順位行の欠落・重複、未知level tokenを拒否。dependency stale時は依存するassignmentのみ保留し、同じtarget内の独立current assignmentを保持。承認済みartifactに未解決依存があればD015で拒否。 | target Aの依存だけstaleでcurrentなsystem割当を保持するcase、無関係unknown source混入、競合、複数level、assignment矛盾を追加検証。                                                    |
| TMG-D019 local ID                    | `<artifact_ref>#<QAR/ARCH-local-id>@revision`を解析し、owner・artifact ref・fixtureで確認可能なlocal ID・revision・scopeを照合。実成果物の未取得時はfixtureにない実在性を推測しない。                                                                                                 | 存在しないQAR／ARCH ID、他artifact ID、旧revision、正しいrefを回帰確認。実owner artifact再取得はPR #22で別途検証。                                                                   |

再レビューで追加確認した表行の欠落経路も修正した。`nonempty_rows(table, key)`がID欄空の行を捨て、risk/action/differenceやsource inventoryが完了判定から消える経路があったため、該当表は全データ行を検査して必須ID・scopeを判定する。TADではさらに、assignment targetに対応する優先順位行の欠落を拒否する。変更は既存validatorと既存fixtureに局所適用し、新しい共通frameworkや依存関係は追加していない。

### 回帰検証・実行結果

実行環境はLinux、Python 3.12.3。`python` aliasとsystem `pip`はなく、`python3`を使用した。結果は次のとおり。

- `python3 -m unittest discover -s tests/skills/evals/deterministic -p 'test_f_planning_contracts.py' -v` — PASS 30、FAIL/ERROR 0。
- Code Quality FAIL後に再実行: `uvx --from ruff==0.16.8 ruff format skills/test-architecture-design/evals/deterministic/validator.py skills/test-management/evals/deterministic/validator.py tests/skills/evals/deterministic/test_f_planning_contracts.py` — 3 files reformatted。続く`uv run --with ruff==0.16.8 python scripts/format_tracked.py check` — PASS、221 tracked files。F回帰30件も再実行してPASS。Ruffはephemeral uv environmentで実行し、project dependencyは追加していない。
- `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v` — PASS 12、FAIL/ERROR 0。
- `python3 -m unittest discover -s tests/skills/evals/deterministic -v` — 320件、315件成功、4 FAIL／1 ERROR。Fの30件はPASS。4件は共有SQLite stateの3件とWCAG保存計画1件で、providerが`/tmp/.git`を含むrootをgit worktree内と判定し安全に拒否するためblockedになった。ERROR 1件はstatic serverのloopback bindが`PermissionError: [Errno 1] Operation not permitted`で拒否された。これはこのmanaged sandboxでの実行制約で、Linux GitHub Actionsの結果ではない。共有runtimeの禁止条件は迂回していない。
- `.github/workflows/deterministic-output-evals.yml`の`Validate output eval datasets`と同等の検査 — PASS、25 Skill／52 case。3 Skillの6ケースは既存deterministic runnerで全件PASS（保存reference fixtureを用いた静的評価）。
- `python3 -m compileall -q skills/test-requirements-analysis skills/test-architecture-design skills/test-management tests/skills/evals/deterministic` — PASS。
- `python3 scripts/skills/evals/semantic/validate.py` — PASS、26 Skill／168 case。`python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v` — PASS 27。`python3 -m unittest discover -s tests/skills/evals/semantic -v` — PASS 13。`python3 -m unittest discover -s tests/skills/evals/trigger -v` — PASS 1。
- `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — 496件、477件成功、10 FAIL／9 ERROR。18 SQLite履歴caseは`/tmp/.git`があるためshared providerがgit worktree配下へのDB作成を拒否。残る`test_json_nesting_failure_is_a_structured_input_error`はPython 3.12.3で深い配列をJSON listとしてparseし、期待文字列`nesting`ではなく`JSON document must be an object`になった。A担当の共有runtime／Python-version contractとして引き継ぐ。Windowsで既知の5 failure／14 error／6 skipはこのLinux実行で解消されたものとは扱わない。
- `dprint --version` — 0.55.2。変更・未追跡のMarkdown／JSON等17ファイルを明示した`dprint check --config dprint.json --config-discovery=false --no-gitignore --stdin-files` — PASS。未追跡ファイル0。`dprint fmt`はこの差分内の3 fixtureだけを整列し、意味内容は変えていない。`git diff --check` — PASS。
- 初回の`python3 scripts/format_tracked.py ruff-check`／`check`はRuff実行ファイルがなく終了code 2だった。その後uvで固定版Ruff 0.16.8を一時実行し、上記のfull tracked checkがPASSした。dprintとRuffの結果は個別に記録する。
- 固定revision `69ef37e9424c0a7ea9dd2293b559e43ec8176379`のローカル`skills-ref validate`は当初DNS解決不可で未実施。push済みhead `ffc1030`のCIでは公式`Validate Agent Skills specification` stepがPASSしたが、後続のrepository eval structure stepはREADME登録不足でFAILした。

### GitHub Actionsと共有CIの切分け

push済みhead `ffc1030637f3e65f15c8298bb8ae590a8380f6c3`に対する最新Actionsを確認した。runは次のとおり。

- [Validate Agent Skills #2166](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42727578944) — FAIL。公式Skill仕様validationはPASSしたが、repository eval structure stepでREADMEにない3 Skill (`test-architecture-design`、`test-management`、`test-requirements-analysis`)を指摘。README／共通registryは担当Aのowner範囲。
- [Validate Deterministic Output Evals #2164](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42727578889) — PASS。修正後のdataset検査と後続jobが完了した。
- [Validate Semantic Output Evals #2129](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42727578964) — PASS。
- [Code Quality #859](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42727578929) — FAIL。tracked format/lint stepでRuff F841、未使用`risks`代入を報告。follow-up push後の[Code Quality #862](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728764570)はPASS。
- [Codex Harness #859](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42727578888) — PASS。

follow-up commit `caa5ed1f80c28bd392bd3daaeca6b3734f7c1ddf`の5 workflowを再確認した。

- [Validate Agent Skills #2169](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728767430) — FAIL。公式Skill仕様validationはPASS。repository eval structure stepがREADMEで未登録の3 Skillを検出し、後続stepをSKIP。担当Aへ引継ぎ。
- [Validate Deterministic Output Evals #2167](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728765000)、[Validate Semantic Output Evals #2132](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728764600)、[Code Quality #862](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728764570)、[Codex Harness #862](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42728764604) — PASS。Deterministic workflowはdataset検査、compile、shared/repository deterministic tests、runtime unit/integration testsまで全stepが成功した。

### 担当Aへの変更依頼

共有ownerの最新公開契約`docs/implementation/pr22/A_runtime-integration.md`とbase commit `d38b775e43f7f0a86a834fef4a122f04d30ef724`を確認した。担当Aが既に登録した形跡はなく、README、共通registry、runtime、routingはこのbranchで編集していない。具体的な引継ぎは以下。

1. `README.md`のcanonical Skill rosterへ3 Skillを追加し、CIのREADME整合条件を満たす。
2. `scripts/skills/evals/deterministic/common.py::CANONICAL_SKILLS`へ登録し、`skills/qa-workflow/scripts/workflow_runtime.py::RUNTIME_V2_SKILL_ROOTS`およびqa-workflowのowner verifier／routing入口へ正式接続する。validator入口は各packageの`evals/deterministic/validator.py::validate(text, expected, eval_id)`。未登録範囲をverified／completeにせず`unverified_scopes`として残す。
3. 各owner・scope・artifact ref／revision、依存source ref／revision、local ID、currentness、取得状態、必要承認scope／revision／証拠をAの保存後readbackと照合する。F validatorの静的文字列検査を認証済み承認とみなさない。
4. 正常fixtureはQRA/TAD/TMG各`OUT-001/002`と6保存reference fixture。拒否fixtureはF回帰30件にある未承認／旧revision、stale／未取得、local ID不一致、missing readback、scope内open risk/action/difference、異常priorityをowner verifier gateから呼ぶ。
5. 単独triggerに加えて複合workflow routing、current scopeとの境界、誤発火を検証する。新Skillのruntime verifierが未登録の間は、共通runnerがfixtureを処理できることと業務runtimeの検証済み状態を区別する。
6. 登録後に`Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Code Quality`、`Codex Harness`を新HEADで実行し、後続repository deterministic・runtime testsまで到達した結果を確認する。
7. PR #22では実owner成果物の再取得、保存providerの選定、native CAS／履歴／独立readback、認証済み承認、F source ref／revision／scope接続を行う。fixtureや今回のlocal runner結果を実provider・実Agent証拠へ昇格しない。
8. A範囲の追加確認: `tests/skills/evals/deterministic/test_wcag_runtime_contract.py::test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread`はProject Contextを渡すが、その一時state rootがこのsandboxの`/tmp/.git`検査により拒否される。共有providerの拒否条件を緩めず、隔離されたLinux CIで再実行する。`test_ci_handoff.py::test_json_nesting_failure_is_a_structured_input_error`はPython 3.12.3で別メッセージになったため、Python 3.11／3.12間の境界と明示的depth制限を確認する。

E／Jの実成果物文書はこのcheckoutにはなく、入力公開契約をPlanと共通保存・集計契約に照らした。EにはQAR ref/revision、target／scope単位のlevel・方式、影響する成果物だけの再確認とcurrent成果物保持を渡す。Jには予定populationとsource owner readbackを分けた全identity、plan ref/revision・scope・build・environment単位の件数を渡す。Risk・Regression Run・raw result・reportの正本は複製せず、PR #22で実consumerとの接続を確認する。

### Plan完了判定・再レビュー

- 今回のFレビュー指摘と追加した欠落ID／優先順位負例 — F専用30件と6 fixture runnerはPASS。確認範囲でF validatorの追加修正を要する問題は残っていない。
- deterministic dataset contract — local equivalentは全52 case PASS。GitHub CIで修正後の成功は未確認。
- Ruffのfull tracked format/lint check — follow-up後に221 files PASS。`ffc1030`ではF841でCode QualityがFAILしたが、修正後head `caa5ed1f`のCode QualityはPASS。ローカル固定revision `skills-ref`は未実施だが、同headのCI仕様validation stepはPASS。全deterministic suiteとruntime regressionのローカル実行は前記sandbox制約が残り、担当Fの最終局所受入は**未完了**。
- README／共通registry／routing — Aへ変更要求済み状態。CIのREADME failureはF validatorの不具合ではない。
- E／J実成果物との横断接続、全current Skill同時利用、実Agent trigger／semantic Judge、実provider CAS／履歴／readback、認証済みapproval、保存失敗後復旧、S1〜S17と15＋10条件 — PR #22／外部provider選定待ちで未実施。再開条件はowner成果物とscopeの確定、provider／認証主体の選定、Aの正式runtime登録後に新HEADでCIを完遂すること。
- 文書と実装の差異: root README／`CANONICAL_SKILLS`／`RUNTIME_V2_SKILL_ROOTS`にF 3 Skillがない点は現存し、A担当として未対応。F内ではvalidator、template、data-contract、fixtureの今回変更間に未解決差異を確認していない。E／J実成果物文書がcheckoutにないため実成果物接続は未確認。

### PR #28本文更新案（GitHub未更新）

```markdown
## 目的

PR #22の担当Fとして、QA要求・テストアーキテクチャ・計画／進捗／承認の公開契約とvalidatorを実装し、レビュー指摘とCIデータ契約を修正する。

## 現在の状態

- Draft。F専用回帰30件と6保存fixtureはPASS。全52 deterministic output datasetもローカル契約検査を通過。
- full deterministic／runtime suiteには共有runtimeとsandboxに依存する未解決結果がある。Ruffはfull tracked check PASS。follow-up headではDeterministic／Semantic／Codex Harness／Code QualityがPASS、Agent Skillsは担当AのREADME不足でFAIL。
- README・共通runtime登録は担当Aへ引継ぎ中。実Agent／認証済み承認／保存provider／PR #22横断接続は未実施。
- 詳細・検証証拠・再開条件は[担当F文書](docs/implementation/pr22/F_qa-planning-architecture.md)を参照。
```

この案はPR本文の更新依頼ではなく、現在はGitHub上の本文を変更していない。

## 追加レビュー4件の修正・回帰確認（2026-11-10）

レビュー基準`aa16455ad95971f9a99fbb29363fa5e7fa5d0564`から、対象branch `feat/pr22-f-qa-planning-architecture`で作業した。作業開始時はworktree cleanで、`origin/feat/pr22-f-qa-planning-architecture`とのahead／behindはいずれも0。今回の差分はF担当のQRA／TMG validator、QRA data-contract／guidance、F回帰テスト、本節に限定した。README、共通runtime、qa-workflow routingは変更していない。

### 指摘別の修正

1. **QRA承認placeholder** — `skills/test-requirements-analysis/evals/deterministic/validator.py`の`_has_value()`で大小文字を正規化し、未取得／unknown／未設定／失効／未承認／不要や空値記号を証拠として扱わない。`QRA-D013`は承認行の状態、主体・role、証拠ref、artifact ref、revision、scopeを照合し、確定artifactとsourceのcurrentnessも確認する。検証できるのは記録されたrefと状態の整合までであり、主体認証は行わない。provider未接続は承認完了の証明にならない。
2. **TMG承認主体placeholder** — `skills/test-management/evals/deterministic/validator.py`で既存の`_is_present()`を大小文字非依存にし、`TMG-D023`の承認行内容検査と、同一ref／revision／scopeの有効行検索の両方に使用した。`-`、`unknown`、`未取得`等では有効な承認行を成立させない。草案／blockedは従来どおり許容する。
3. **QA目的・成功条件の欠落** — QRA validatorの`QRA-D001`で正規テーブル、必須5列、各値を検証する。草案／blockedは未取得等の明示状態と理由を保持できる。承認済みでは未確定状態を許容しない。再レビューで、説明文中に`stale`等の単語があるだけで誤拒否することを避け、値全体が状態placeholder、または状態markerと理由区切りで始まる場合だけ未確定と判定するよう修正した。`data-contract.md`と`guidance.md`にも同じ境界を記録した。
4. **未決事項のclosure情報不足** — `QRA-D012`で未解決QA要求ごとに同じQAR IDの未決事項が一意に存在すること、影響scopeが要求scopeを含むこと、担当・許可状態・再開条件が記録されることを検証する。未取得／blocked状態も担当と再開条件があれば保持できる。無関係IDの未決事項は対象判定へ混入させない。未確定の担当者や条件を生成しない契約をdata-contract／guidanceへ反映した。

修正ファイルは上記2 validator、QRA `references/data-contract.md`／`references/guidance.md`、`tests/skills/evals/deterministic/test_f_planning_contracts.py`、本書。templateや共有ownerファイルは変更していない。

### 回帰テスト

既存の30テストを維持し、今回の独立したテスト3件を追加してF回帰を33件にした。承認ref／主体の`unknown`・`未取得`・`-`、artifact／revision／scope mismatch、有効な承認、草案／blocked、目的テーブル欠落・列／値不足、承認済みの未確定値、未決事項行／scope／担当／状態／再開条件の不備と無関係scopeを確認する。承認検索経路も汚染された行で拒否されることをassertion evidenceで確認した。Markdown表編集helperは既存のsection/table構造を利用する。

### 実行した検証

- `python3 -m unittest discover -s tests/skills/evals/deterministic -p 'test_f_planning_contracts.py' -v` — PASS 33／0 FAIL／0 ERROR。正常な6 output reference fixtureを含む。これは実Agent出力ではない。
- `.github/workflows/deterministic-output-evals.yml`の`Validate output eval datasets`と同じ検査 — PASS、25 Skill／52 case。QRA／TAD／TMG各2件の6 fixtureは既存deterministic runnerでPASS（各manifestのreference出力を使用）。
- `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v` — PASS 12。
- `python3 -m unittest discover -s tests/skills/evals/deterministic -v` — 323件中319 PASS、4 FAIL。失敗は共有WCAG／qa-workflowのSQLite providerがsandbox内Project Context state-rootを拒否し`blocked`を返すもの。F変更から独立したA範囲で、`test_sqlite_provider_uses_atomic_revision_compare_and_reread`、`test_wcag_canonical_plan_is_immutable_per_revision_and_context`、`test_wcag_report_requires_persisted_owner_runtime_result`、`test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread`。安全ガードは変更していない。
- `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — 今回のvalidator編集前に同じbranchで実行した全496件は477 PASS、10 FAIL、9 ERROR。SQLite workflow-historyのsandbox cleanup／state-root拒否、およびPython 3.12.3のJSON nesting error message差異。共有runtime owner Aへ引継ぎ、Linux CI結果とWindows既知の5 FAIL／14 ERROR／6 SKIPを混同しない。今回TMG／QRA変更はruntime packageを変更していない。
- `python3 scripts/skills/evals/semantic/validate.py` — PASS、26 Skill／168 case。`python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v` — PASS 27。`python3 -m unittest discover -s tests/skills/evals/semantic -v` — PASS 13。`python3 -m unittest discover -s tests/skills/evals/trigger -v` — PASS 1。実Agent／Judge評価は未実施。
- `python3 -m compileall -q skills/test-requirements-analysis skills/test-management tests/skills/evals/deterministic` — PASS。
- `uv run --with ruff==0.16.8 python scripts/format_tracked.py ruff-check`、`uv run --with ruff==0.16.8 python scripts/format_tracked.py check` — PASS。後者は221 tracked files。dprint 0.55.2も同じtracked check内でPASS。
- CI固定revision `skills-ref@69ef37e9424c0a7ea9dd2293b559e43ec8176379`で3 Skillの`skills-ref validate` — PASS。取得・実行環境は一時領域を使用しrepository依存へ追加していない。
- `git diff --check` — 文書追記後の現在差分でPASS。秘密情報検査、path範囲、stage内容はcommit直前にも再確認する。

### CI、共有登録、受入判定

レビュー基準HEAD `aa16455a`のActionsはDeterministic Output Evals、Semantic Output Evals、Code Quality、Codex HarnessがPASS、Validate Agent SkillsはREADMEにFの3 Skill (`test-requirements-analysis`、`test-architecture-design`、`test-management`)が未登録でFAILした。今回の修正HEADに対するGitHub Actionsはpush後に確認する。ローカルPASSをActions成功とは扱わない。

PR #22統合先`feat/development-qa-traceability`の現行ファイルを読み取り確認した。READMEのSkill roster、`scripts/skills/evals/deterministic/common.py::CANONICAL_SKILLS`、`skills/qa-workflow/scripts/workflow_runtime.py::RUNTIME_V2_SKILL_ROOTS`のいずれにもFの3 Skillは未登録で、今回も共有ファイルは変更していない。担当Aへ、Skill名／責務、validator入口、owner・scope・ref・revision、currentness／approval、正常・拒否fixture、未検証scopeの扱い、routing／trigger条件、登録後CIとPR #22実成果物接続を引き継ぐ。既存の詳細依頼は本書の前節に記載したとおり。

- 4件の今回レビュー指摘 — validatorとfixtureで拒否／保持条件を確認し、F回帰33件はPASS。
- 担当Fローカルの対象修正 — **完了**。承認・目的・未決事項の4契約はPlan/data-contractと整合し、再レビューではsubstring誤検知も修正した。
- 担当Fの全局所受入 — **未完了**。repository deterministic 4件FAILと共有runtime 10 FAIL／9 ERRORが残るため、PR #22の隔離Linux CIで共有state-root／SQLite／Python-version原因を再確認する。
- AのREADME／registry／routing登録 — 未完了、担当A。3 Skill登録後に5 CI workflowと後続deterministic／runtime testsを新HEADで再確認する。
- 実Agent、semantic Judge、認証済みapproval、実保存provider CAS／history／readback、保存失敗後復旧、E／J成果物横断接続、S1〜S17 — PR #22／外部provider・認証主体の選定待ち。fixtureを実接続証拠にしない。
- PR本文は更新していない。Draftを維持する。push後のActions結果を反映したPR本文案は最終報告に示す。

### PR #28本文更新案（GitHub未更新）

```markdown
## 目的

PR #22の担当Fとして、QA要求・architecture・計画の契約とvalidatorを実装し、レビュー指摘と決定論的評価条件を満たす。

## 現在の状態

- Draft。今回の承認placeholder、QA目的・成功条件、未決事項の担当・scope・状態・再開条件を修正し、担当F回帰33件、6 output reference fixture、25 Skill／52 caseのdataset検査はPASS。
- 全repository deterministicは共有runtime sandboxに起因する4 FAIL、runtime suiteは10 FAIL／9 ERRORが残る。push後のGitHub Actions結果は担当F文書に記録する。
- README・共通runtime登録は担当Aへ引継ぎ中。実Agent・認証済み承認・実provider・PR #22横断接続は未実施。
- 詳細と検証証拠は[担当F文書](docs/implementation/pr22/F_qa-planning-architecture.md)を参照。
```
