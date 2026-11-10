# PR #22 並行実装：E — 正式テスト設計・E2E選定

## 位置付け

既存Product Risk→TR→TCN／CI→TCを保ち、機能・item・共通条件候補と技術非依存のE2E選定をつなぐ。

- 作業branch：`feat/pr22-e-formal-design-e2e-selection`
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
- [詳細03：E2E・直接開始](../../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)

関連完了条件の主な担当：開発連動QA 5・8・12・13・14、QA全工程 2・9の正式設計部分。

## このbranchで変更する対象

- 新設`skills/e2e-test-selection/**`
- 既存`skills/test-analysis/**`、`skills/test-requirement-design/**`、`skills/test-condition-design/**`、`skills/test-case-design/**`、`skills/coverage-analysis/**`の必要な接続
- それらの既存runtime／validator／fixture／migrationテスト（共有runtimeの改変はAへ）

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

- [x] Risk・TR・TCN・CI・TC・coverageの実装、schema、呼び出し元・先、CI・テストと既存IDを確認した。
- [x] B／C／D／Fの受渡し契約と`test-analysis`のE単一編集ownerを確認した。

## 作業内容

1. B/D/C/Fから渡るsource、機能、item、共通条件候補、Authority、アーキテクチャ割当を既存Product Risk・TR・TCN・CI・TCに接続する。
2. 一次RiskをTRより前に扱い、新証拠や条件候補による局所再評価を行い、製品仕様・QA計画・Riskの正本を混ぜない。
3. item×conditionの採否／正当な不採用／未確認、アイテムごとの正式TCN ID、複数期待結果候補のAuthority・観測・副作用の根拠を保持する。
4. 既存CIのpartition／boundary／rule等の局所技法候補と共通condition IDを区別し、TCの個別期待結果が現在有効なAuthorityを持つか検証する。
5. テストレベルは明示指定＞承認済みarchitecture＞既存既定の優先で反映し、変更されたレベル・仕様・Riskに依存する範囲だけ再検証する。
6. 技術非依存のE2E候補・選定理由・履歴・source参照を新設し、既存Playwright E2E Skillによる検査／実装／実行を複製しない。
7. 既存ID・artifact graph・正規成果物・legacy・partial rerun・direct TC/E2Eでの利用を回帰する。

## 依存と引継ぎ

- B/C/D/F→E：機能・UI・item・condition・仕様Authority・QAレベル割当のref。
- E→G/H/J：正式TCとE2E選定ref・coverage評価。
- A：共有runtime登録依頼。Fが必要とする既存`test-analysis`変更はEが実施する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

最新の担当受入状態は末尾の「レビュー指摘対応・最終再検証」を参照する。以前の受入記録は作業履歴として保持する。

- [x] 各正本・Authorityを守り、feature/item/condition/architectureの契約fixtureから既存設計までID・revision付きで局所検証した。B/C/D/Fの正規実成果物との横断追跡はPR #22へ引き継いだ。
- [x] 採否・不採用・blocked・複数expected result・別レベル・既存技法CIが互いに混同されない。
- [ ] 技術非依存のE2E選定がE2E実装・実行とは独立して発火し、既存E2E直接利用を妨げない。
- [x] Risk・TR・TCN・CI・TC・coverageのlegacy／migration／partial rerun回帰と、authorityなし期待結果・誤100%等の負例がPASSする。
- [x] 既存ID・証拠・既存設計／executionの直接入口が保たれ、Aによる統合検証へ渡せる。
- [ ] 新Skillと改訂既存Skillのisolated/trigger/semantic・決定論的評価を実行した。

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

## PR #27 実装・局所検証記録（2026-11-09）

### 実装範囲

- `skills/e2e-test-selection/`を追加。技術非依存のE2E候補、採否、根拠、source currentness、revision履歴、retirementを検証する単独Skill・schema runtime・output／semantic／trigger評価データを実装した。runtimeはUTF-8 JSON envelopeで完全な選定recordを返し、永続化・承認・CAS・readbackを仮定しない。
- `test-analysis`から新規選定依頼を新Skillへrouteし、直接TC、既存selection参照、既存E2Eの直接利用は維持した。既存selection validatorはlegacy入力の読取りを維持した。
- `test-condition-design`にitem×condition全組合せの明示採否・未確認・別レベル・blocked、item単位TCN ID、複数Authority付き期待結果候補、履歴を追加し、採用pairだけ既存TCNへ投影する。テストレベルは明示指定＞承認済architecture＞既定の順に扱う。
- `test-requirement-design`にテストレベル根拠を追加。`test-case-design`は期待結果ごとにcurrent Authorityを要求し、formal candidateとの一致を確認する。`coverage-analysis`はformal candidate coverageをCI／QA artifact graphと分離し、分母0・不完全な母集団を100%扱いしない。
- owner-local runtime・fixture・決定論的テストを追加し、Authority付きTC fixtureをlegacy cutover／vertical integrationにも補った。共通README、root EVALS、共有runtime登録、共有assertion registryは変更していない。

### 担当範囲の受入確認

以下は個別実行でPASSした。

- `python -m unittest tests.skills.runtime.test_e2e_selection_contract -v` — 10 tests。
- `python -m unittest tests.skills.runtime.test_formal_design_contract -v` — 12 tests。
- `python -m unittest tests.skills.runtime.test_test_condition_structure -v` — 11 tests（複数itemの固有TCN ID、revision時のID再利用、未採用判断と履歴の保持を含む）。
- `python -m unittest tests.skills.runtime.test_test_requirement_structure -v` — 11 tests。
- `python -m unittest tests.skills.runtime.test_case_structure -v` — 10 tests（Authorityなし／stale Authority拒否を含む）。
- `python -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v` — 16 tests（誤100%拒否を含む）。
- `python -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v` — 2 tests。
- `python -m unittest tests.skills.runtime.test_ep_vertical_integration.EpVerticalIntegrationTests.test_standalone_evidence_and_qa_workflow_integration -v` — 1 test。
- `python -m unittest tests.skills.runtime.test_runtime_portability -v` — 3 tests（Skill単独copy実行、未承認repo-local importなし）。
- `python -m unittest tests.skills.runtime.test_test_analysis_entities -v` — 17 tests。
- `python -m unittest tests.skills.runtime.test_test_analysis_risk_matrix -v` — 3 tests。
- `python -m unittest tests.skills.runtime.test_test_analysis_change_impact -v` — 2 tests。
- `python -m unittest tests.skills.runtime.test_test_analysis_technique_candidates -v` — 3 tests。
- `python -m unittest tests.skills.evals.deterministic.test_new_skill_contracts.E2ESelectionDeterministicContractTests -v` — 4 tests（新Skill output／triggerと旧`test-analysis` selection assertion RISK-D016／D017の互換を含む）。
- `python -m unittest discover -s tests/skills/evals/trigger -v` — 1 test。`python scripts/skills/evals/semantic/validate.py` — 24 Skills／168 cases。`python -m unittest discover -s scripts/skills/evals/semantic/tests -v` — 27 passed／2 Windows symlink skip。`python -m unittest discover -s tests/skills/evals/semantic -v` — 13 passed／1 Windows symlink skip。
- deterministic output manifest CI blockと同じ検査 — 23 Skills／48 cases PASS。変更対象のcompileallと`git diff --check`もPASS。

### 未完了・blocked

- `python -m unittest discover -s tests/skills/runtime -p "test_*.py" -v`は525 testsでFAILED（5 failures／14 errors／6 skipped）。担当外の`test_ci_handoff` 5件はWindowsでsecure artifact readbackが`artifact_readback_unavailable`となり、`test_sqlite_workflow_history` 14件はWindowsの一時SQLite fileがopenのままcleanup時に`WinError 32`となる。各suite単独の再実行でも同じ失敗を再現した。PR #27起因の失敗は再検証で解消済み。
- `python -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v`はE2E固有4 testsがPASSした一方、全38 testsは既存`test-execution` validatorのimport時にPyYAML未導入で16 errors。`python -m unittest tests.skills.evals.deterministic.test_e2e_contracts -v`も共有loaderが全validatorを先読みするため同じPyYAML欠落で開始できない（旧selection validator自体は上記owner-local testで直接検証済み）。`.github/workflows/deterministic-output-evals.yml`はPyYAML 6.0.3をinstallするが、この環境にはない。共通runner全体の決定論的評価は未完了。
- `python scripts/format_tracked.py check`はruff起動時に`WinError 2`で停止。`ruff`／`dprint`／`skills-ref`はいずれもこの環境にないため、formatterと公式Agent Skills validatorは未検証。semantic judge/providerによる意味評価も未実施。
- `validate-skills.yml`のrepository eval structure検査はcanonical Skill 24件中、新設`e2e-test-selection`が共有`README.md`にないため失敗する。READMEはA ownerの共有ファイルなので本branchでは変更していない。Aが登録後に再実行する。
- `scripts/skills/evals/deterministic/ASSERTIONS.md`には旧`test-analysis`のE2E選定assertion RISK-D016／D017が現行契約として残る。legacy validator対応は維持したが、共有registryの移管・現行化はA／PR #22で行う。
- 実B/C/D/F成果物、A runtime登録、保存先・承認・CAS・readbackがこのbranchでは利用できない。固定fixtureによる局所検証に留め、実artifact間のID／revision／currentness、保存後readback、必要承認は未検証。

### 文書・コード契約の不一致と対応

- `test-case-design`でAuthorityなし期待結果を許容していた実装がPlanのcurrent Authority必須条件と不一致だったため、current Authority必須化と欠落／stale負例を追加した。
- `test-analysis`の既存文書・出力templateがE2E選定の現行ownerを同Skillとしていたため、新規選定は新Skillへrouteし、旧validatorのselection形式はlegacy読取り用途として明示した。
- `test-condition-design/SKILL.md`のformal validator helper参照とruntime packaging契約が不一致だったため、validatorを既存`condition_structure.py`に内包し、文書参照も合わせた。
- 共有`README.md`の新Skill登録漏れと共有`ASSERTIONS.md`の旧selection assertion記述は、いずれもA ownerの共有ファイルに属するため未修正。上記の通りPR #22へ引き継ぐ。

### PR #22への引継ぎ

1. Aがroot `README.md`のcanonical Skill一覧・責務表・E2E workflow routingに`e2e-test-selection`を登録し、直接TC／既存E2E経路を保持したまま`validate-skills.yml`を再実行する。
2. Aが共有`ASSERTIONS.md`のRISK-D016／D017をlegacy `test-analysis`表の互換Assertionとして明記し、新SkillのE2E-SEL-D001〜D006を追加・参照する。既存Assertionは移行根拠なしに削除・無効化しない。
3. PR #22でB/C/D/Fの実成果物を使い、source/artifact ID・revision・currentness・Authority・scopeの実接続を確認する。
4. Aの共有保存・承認・CAS・readback契約と実runtime登録を利用して保存失敗／再開／再取得を検証する。現在のlocal validatorは意図的に永続化を行わない。
5. Linux CIまたは必要ツール導入済み環境でPyYAML付きdeterministic suite、全runtime suite、ruff/dprint、`skills-ref validate`を再実行する。semantic judge/providerを使った意味評価を実施する。
6. 他owner実成果物を用いる横断試験、S1〜S17、人間編集8ケース、15＋10条件の最終判定はPR #22だけで行う。

## レビュー指摘対応・最終再検証（2026-11-09）

> この節を現在の状態とする。上の「PR #27 実装・局所検証記録」は初回実行時点の履歴として保持する。初回のPyYAML不足・ツール不足・525件runtime結果は後続検証で更新し、同節の既存証拠は削除しない。

### 3.1 新Skill登録・README・CI

- `skills/e2e-test-selection/`の名称・frontmatter・resource参照・output／semantic／trigger評価一式を確認した。canonical Skillは24件、trigger queryは526件で、各datasetは非空・正負同数・train／validation重複なし。新Skillのoutput manifestは3 cases。
- `.github/workflows/validate-skills.yml`のrepository structure step相当を再実行した。24 Skillのname・description・trigger dataの検査は通り、最後のREADME照合だけが`README.md`に`` `e2e-test-selection` ``がないため失敗する。これはSkill packageの仕様違反ではない。
- Plan索引の共有README／CI owner Aを確認し、本branchでは`README.md`と`.github/workflows/validate-skills.yml`を変更していない。Aはcanonical Skill一覧、責務表、`test-analysis`から新Skillを経て既存inspectionへ至るE2E flowを追記し、直接TC・既存E2E実行の入口を保った状態で同workflowを再実行する。
- 公式`skills-ref`（workflow固定commit `69ef37e9424c0a7ea9dd2293b559e43ec8176379`）は新設／変更した6 Skill（`coverage-analysis`、`test-analysis`、`test-case-design`、`test-condition-design`、`test-requirement-design`、`e2e-test-selection`）すべてPASS。

### 3.2 RISK-D016／D017・新旧selection契約

- 共有`ASSERTIONS.md`のRISK-D016／D017は旧`test-analysis`出力の「E2E対象選定」表に適用される。E2E選定表がない場合のD016、表の必須field欠落時のD017は今も必要であり、旧Assertionだけが残っていることは単独では不具合ではない。
- `skills/test-analysis/evals/deterministic/validator.py`は旧tableを引き続き検証する。追加したpositive／negative testで、旧tableと技術非依存fieldが揃えば両AssertionがPASSし、table欠落ではD016／D017がFAILし、field欠落ではD017がFAILすることを確認した。新規selection依頼は`e2e-test-selection`へrouteする。
- 新Skillの新形式は`E2E-SEL-D001`〜`D006`でselection ID／revision／履歴・retirement、候補集合・decision、source revision/currentness、status投影を検証する。旧表を新形式のcurrent selectionへ自動昇格・mergeせず、旧表はlegacy履歴として維持し、新形式recordのcurrentness・readbackが確認できない場合はcurrent扱いしない方針をSkill guidanceへ明記した。旧形式から同一IDの改訂を安全に再開できない場合はmigrationをblockedにする。
- 既存E2Eの直接実行およびTC直接開始は新Skillを必須としない。共有`ASSERTIONS.md`はA ownerのため未変更。AはD016／D017をlegacy互換Assertionとして明記し、新SkillのD001〜D006を追加・参照する。既存Assertionを移行根拠なしに削除・無効化しない。

### 3.3 全runtime suite失敗の原因・owner

実行環境はWindows 10.0.19045、Python 3.11.9。最終実行は535件、5 failures／14 errors／6 skipped、exit 1。全tracebackは`%TEMP%\pr27-runtime-final-rerun.log`に保存した。

| 失敗群                             | 失敗名                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 例外・実条件                                                                                                                                                                                                                                                                                                                                                                                                                                                       | PR #27との関係／処置                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CI artifact readback（5 failures） | `test_artifact_hash_mismatch_is_rejected`、`test_artifact_read_enforces_limit`、`test_backslash_in_posix_changed_filename_is_a_valid_comparison_key`、`test_cli_output_and_fail_closed_exit_code`、`test_complete_integrity_transport_passes`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `skills/qa-workflow/scripts/ci_handoff.py::_read_artifact`がWindows（`os.name != "posix"`）または`O_NOFOLLOW`／`O_DIRECTORY`／`O_NONBLOCK`不足時に`_SecureReadbackUnavailable`を送出し、consumerが`artifact_readback_unavailable`へfail closedする。期待するreadback testへ到達する前に起きる。                                                                                                                                                                    | A所有の共有runtimeで、PR #27差分に含まれない。PR #23の安全契約どおり。readback安全性を弱める変更はしない。POSIX descriptor-bound readback可能な環境での再実行が必要。                                                                                                                                                                                      |
| SQLite cleanup（14 errors）        | `test_cannot_refetch_future_revision_even_if_table_is_tampered`、`test_corrupt_old_snapshot_blocks_current_read_and_future_write`、`test_divergent_history_blocks_read_and_update`、`test_dropped_tracked_history_table_blocks_current_read`、`test_history_with_invalid_json_is_not_reused`、`test_history_write_failure_rolls_back_current_update`、`test_legacy_database_does_not_fabricate_missing_earlier_revisions`、`test_legacy_pretty_json_snapshot_can_be_refetched_after_update`、`test_missing_latest_tracked_snapshot_blocks_earlier_history_read`、`test_missing_latest_tracked_snapshot_blocks_prior_to_backfill`、`test_missing_tracked_revision_cannot_be_silently_recreated`、`test_sqlite_revision_max_is_blocked_without_an_overflow_write`、`test_unmarked_complete_database_can_adopt_history_origin`、`test_unmarked_partial_history_is_ambiguous_and_blocks_updates` | 最初の例外は各test終了時の`TemporaryDirectory.cleanup()`→`shutil.rmtree()`→`os.unlink()`での`PermissionError: [WinError 32]`。Windowsが使用中の`workflow-state.sqlite3`の削除を拒否した。A所有fixtureは`with sqlite3.connect(...) as connection:`を使うがConnection context managerはcommit／rollbackを行うだけでcloseしない。fixture内connectionをcontext exit時に明示closeする診断wrapperを一時実行したところ、同class 20 tests全件PASSしcleanup errorは消えた。 | E担当コード・呼出元ではなくA所有の`tests/skills/runtime/test_sqlite_workflow_history.py`／共通runtime領域。productionの`artifact_graph.py`は4箇所を`contextlib.closing(_sqlite_connection(...))`でcloseする。Aはtest fixtureを`closing()`または明示`close()`へ修正し、通常suiteをLinux／Windowsで再実行する。データ削除・cleanup強制成功化は行っていない。 |

WSLは`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`、Docker serviceはStopped、Docker engine pipeがなくLinux実行環境を利用できなかった。上記cleanup診断はfixture connectionの明示closeで全20件PASSした補助検証であり、Linuxで同じbranch全体を再実行した結果の代替ではない。現在の確定できる根拠はWindows file-lock APIの`WinError 32`とclose前後の差であり、同branchのLinux全suiteは未実施。

PR #23の最新公開head `2c2dcab1968c32ae59f3919a04d7176d10737e0c`では、Aの公開報告にruntime／integration 496 tests PASSがある。これは前提runtimeのLinux CI証拠として参照するが、今回のPR #27変更を含む535件suiteの再実行ではないため、current local suiteのPASSやLinux再実行済みとは扱わない。

### 3.4 PyYAML評価依存

- グローバルPythonへ実装依存を追加せず、隔離評価venv `%TEMP%\pr27-eval-venv` に`PyYAML==6.0.3`を導入した。runtime依存定義は変更していない。
- `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v` — 12 PASS。
- `python -m unittest discover -s tests/skills/evals/deterministic -v` — 299 PASS（最終ログ `%TEMP%\pr27-deterministic-final-after-fix.log`）。初回のPyYAML import errorは解消。E2E-selection固有の`E2ESelectionDeterministicContractTests`は9 PASS（`%TEMP%\pr27-owner-runtime-final\e2e_deterministic.log`）。
- CI output manifest相当の構造検査は23 Skill／49 cases PASS。実Agentが生成した保存済み文章を使う決定論的CLI評価は、Agent出力がなく未実施。manifest／validator／負例をunitで検証した結果と区別する。

### 3.5 formatter／lint／compile

| 対象・command                                                                                                                     | 環境／result                                                                        | 証拠        |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------- |
| `ruff --version`、`dprint --version`                                                                                              | Ruff 0.16.8、dprint 0.55.2                                                          | tool output |
| `python scripts/format_tracked.py check`                                                                                          | PASS、217 tracked files already formatted。`PYTHONUTF8=1`とpinned tool PATHを使用。 | tool output |
| `ruff check`および`ruff format --check`（`selection_contract.py`、E2E deterministic validator、E2E runtime／formal runtime test） | PASS、4 Python files。                                                              | tool output |
| `dprint check`（`skills/e2e-test-selection/`の新規Markdown／JSON全件）                                                            | PASS。fixture値・期待値の意味は決定論的suite／manifest検査でも再確認。              | tool output |
| `python -m compileall -q`（変更したSkill runtime／validatorとruntime test）                                                       | PASS。                                                                              | tool output |

### 3.6 Agent Skills公式仕様検証

`.github/workflows/validate-skills.yml`のpinned `skills-ref`手順で、上記6 Skillを個別に`skills-ref validate <skill path>`し、すべてPASS。frontmatter、Skill名／directory、description、参照ファイルを確認した。README登録漏れは3.1に分離しており、Skill自体の仕様適合と混同していない。

### 3.7 semantic／trigger評価

| 検証層                    | command／result                                                                           | 判定上の制限                                                                                                                                                                                                                      |
| ------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| semantic data structure   | `python scripts/skills/evals/semantic/validate.py` — 24 Skills／168 cases PASS            | dataset構造検証。LLM Judge評価ではない。                                                                                                                                                                                          |
| semantic runtime tests    | `python -m unittest discover -s scripts/skills/evals/semantic/tests -v` — 27 PASS／2 SKIP | Windows symlink作成権限`WinError 1314`で2件skip。                                                                                                                                                                                 |
| repository semantic tests | `python -m unittest discover -s tests/skills/evals/semantic -v` — 13 PASS／1 SKIP         | Windows symlink作成権限`WinError 1314`で1件skip。                                                                                                                                                                                 |
| trigger dataset contract  | `python -m unittest discover -s tests/skills/evals/trigger -v` — 1 PASS                   | dataset・balance・disjoint検証。実Agent発火の証拠ではない。                                                                                                                                                                       |
| 実semantic Judge          | 未実施                                                                                    | EVALSのJudge AdapterとAgent生成outputが必要だが、この環境にadapter／provider設定がない。Judge接続済み環境でE2E selectionと変更Skillのcaseを実行し、保存済み結果を追加する。                                                       |
| 実Agent trigger           | 未実施／blocked                                                                           | `codex` executableがなく、この環境ではSkill load logを観測できる実Agent runtimeがない。Codex CLI等を使える承認済み環境で、E2E新規依頼・legacy参照・直接TC／既存E2E実行・無関係依頼・`test-analysis`近接負例を実際に発火観測する。 |

構造検証PASSは意味評価／実Agent発火PASSへ読み替えていない。SKILL改訂・output／semantic fixtureは揃っているが、実JudgeとAgent評価が未完了のため該当完了基準は未チェックのまま。

### 3.8 正式設計／E2E選定重点回帰

- Product Risk→TR→TCN／CI→TCのtyped identity・revision、item×condition採否／不採用／未確認、正当な不採用と未確認の区別、stable TCN ID、複数expected resultと個別Authority、stale／撤回／未承認Authorityは、formal design・requirement・condition・caseの独立fixtureで検証した。
- テストレベル優先順位、既存CIのpartition／boundary／ruleと共通condition ID、分母0・不完全母集団・blocked項目の誤100%、source currentness・履歴・retirement、legacy・migration・partial rerunは該当runtime／負例で検証した。具体的な証拠suiteと件数は3.4／次節の受入表に記録する。
- 保存、readback、承認、失敗後再開、他ownerの下流consumerに対する実成果物接続はA runtimeとB/C/D/F実成果物が必要なため未検証。これはPR #22統合とAの共有runtime接続に引き継ぐ。

### E担当runtime・回帰テスト（各commandを独立実行）

環境はPython 3.11.9／Windows 10.0.19045。各ログは`%TEMP%\pr27-owner-runtime-final\`。

| command（すべて末尾に`-v`）                                                                                                                               | result                                                                   |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `python -m unittest tests.skills.runtime.test_e2e_selection_contract -v`                                                                                  | 12 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_formal_design_contract -v`                                                                                  | 15 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_test_condition_structure -v`                                                                                | 11 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_test_requirement_structure -v`                                                                              | 11 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_case_structure -v`                                                                                          | 11 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v`                                                                          | 16 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v`                                                                                 | 2 PASS                                                                   |
| `python -m unittest tests.skills.runtime.test_ep_vertical_integration.EpVerticalIntegrationTests.test_standalone_evidence_and_qa_workflow_integration -v` | 1 PASS                                                                   |
| `python -m unittest tests.skills.runtime.test_runtime_portability -v`                                                                                     | 3 PASS                                                                   |
| `python -m unittest tests.skills.runtime.test_test_analysis_entities -v`                                                                                  | 17 PASS                                                                  |
| `python -m unittest tests.skills.runtime.test_test_analysis_risk_matrix -v`                                                                               | 3 PASS                                                                   |
| `python -m unittest tests.skills.runtime.test_test_analysis_change_impact -v`                                                                             | 2 PASS                                                                   |
| `python -m unittest tests.skills.runtime.test_test_analysis_technique_candidates -v`                                                                      | 3 PASS                                                                   |
| `python -m unittest tests.skills.evals.deterministic.test_new_skill_contracts.E2ESelectionDeterministicContractTests -v`                                  | 9 PASS（legacy RISK-D016／D017、new output／negative／trigger contract） |

上記E担当runtimeは合計107 PASS。新しい追加レビュー修正は`skills/test-case-design/scripts/case_structure.py`で、formal TCNがcandidate refのみを渡しcandidate payloadを欠くと`StopIteration`内部エラーになっていた。明示的な`invalid_input`として拒否し、`test_formal_candidate_refs_require_candidate_payloads`を追加した。該当negativeと正常candidate対応の2 test、および`test_case_structure`全11 testsがPASS。担当範囲内のfalse-pass／fail-openは追加確認で見つからなかった。

### formatter・CI・Actionsの実行対象

- PR #27のGitHub上の公開headは`688cacf9514dd63ccbe93641f4f86fad340d3580`。そのheadに紐づく`Codex Harness`、`Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Code Quality`はすべてsuccessだが、これはlocal uncommitted worktreeを含まない公開commitの結果である。
- PR #23の最新公開head `2c2dcab1968c32ae59f3919a04d7176d10737e0c`はclosedで、同headの上記5 workflowはsuccess。Aの安全readback blocked方針とSQLite履歴runtimeの共有契約確認に使用した。PR #23の結果もPR #27 local差分のCI結果として扱わない。
- 今回のlocal変更に対するGitHub Actionsは未実行。no pushの制約下で未commit worktreeをActionsへ渡せないため。公開headのsuccessで代替していない。

### 2026-11-09時点の完了基準状態（当時の記録）

この時点の状態表は履歴として保持する。2026-11-10の再検証結果は末尾の「担当E残作業の再検証・外部blocked記録」を参照する。

- [x] 各正本・Authority、ID／revisionの局所fixture、採否／不採用／blocked、複数expected result、level priority、legacy／partial rerun、誤100%負例を担当runtimeで確認した。
- [ ] 実Agentによる新Skill trigger、非発火近接例、実semantic Judge評価が未実施。
- [ ] full runtime suiteはA所有共有コード起因の5 failures／14 cleanup errorsがあり、Linuxでの同branch再実行も未実施。
- [ ] README未登録によりrepository-wide Skill validationの最終stepが失敗。Aの修正後に再実行が必要。
- [ ] 変更済みlocal worktreeに対するGitHub Actions未実施。
- [ ] 保存／readback／承認／再開と他owner成果物を用いたsource ID・revision・currentness横断接続は未実施。
- [ ] 以上から「担当branch内の実装・局所検証完了」はまだ宣言しない。E担当runtime・formatter・Skill仕様・構造評価は実施済みだが、未完了項目が残る。

### owner別の再開・引継ぎ条件

**Aへ**

1. `README.md`のcanonical Skill一覧・責務表・新E2E routingを更新し、`validate-skills.yml`の全stepを再実行する。README omissionは `e2e-test-selection`、ownerはA。
2. 共有`ASSERTIONS.md`のRISK-D016／D017をlegacy `test-analysis`表の互換対象として明記し、new SkillのE2E-SEL-D001〜D006を登録・参照する。現行positive／negative結果を維持し、既存Assertionを削除／無効化しない。
3. `tests/skills/runtime/test_sqlite_workflow_history.py`でConnection contextをcloseする修正（`closing()`または明示close）を行い、通常のruntime suiteをLinux／Windowsで再実行する。現状の14件はすべてcleanup時WinError 32で、各testのassertion失敗とは別。
4. `ci_handoff.py::_read_artifact`はPOSIX descriptor-bound readback不可能時の`artifact_readback_unavailable` blockedを維持する。Windowsでreadbackのnegative/positive testsをPASSさせる場合もsymlink／race安全性を保持する実装が必要。再開条件はLinux等の安全なPOSIX環境で5 testsを通すか、Aが同等の安全性を持つ別platform readerを共有すること。

**PR #22へ**

1. B/C/D/Fの実成果物とAの登録runtimeを用い、Product Risk→TR→TCN／CI→TC→coverageおよびE2E選定の実ref・revision・Authority・currentnessを照合する。
2. Aの承認済み保存／CAS／readbackを接続し、保存失敗・retry／再開・保存後再取得、source変更時のstale伝播と下流consumerを検証する。
3. Judge Adapterと実Agentが利用できる環境で今回未実施の意味評価・Skill読み込み／trigger評価を行い、TCあり・TCなし、既存E2E直接実行、legacy参照、無関係依頼を観測する。
4. 全current Skill、S1〜S17、人間編集8ケース、開発連動QA15条件／QA全工程10条件、詳細Plan01〜08と統合後Actionsの横断最終受入を行う。このbranchでは実施しない。

### 文書・コード不一致の棚卸し

- `README.md`が新Skillを欠き、`.github/workflows/validate-skills.yml`のcanonical list照合で落ちる。仕様違反ではなくA ownerの共有文書未登録。未変更・引継ぎ済み。
- 共有`ASSERTIONS.md`は旧tableを対象とするが旧artifactのvalidator互換も必要なため、旧契約の存在だけを不具合扱いしない。RISK-D016／D017のscope更新とnew Skill assertionの追加はA ownerへ引継ぎ済み。
- 正式設計Authority revisionとsource revisionの照合、candidate removal／retirement履歴、current `change_reason`は旧runtime検証と文書条件に不足があったため、E担当runtime・fixture・Skill docs・negative testを更新した。
- 正式TCNのcandidate IDのみを渡すと`test-case-design`で内部`StopIteration`となるschema不一致を今回の追加レビューで発見し、明示入力拒否と回帰testを追加した。
- 上記以外に今回の差分範囲で把握した文書・コード契約の不一致はない。

## PR #27 最新コードレビュー対応・最終再検証（2026-11-10）

> 本節を今回のレビューに関する現在状態とする。2026-11-09以前の検証記録は当時の履歴として保持し、本節で更新する。

### 対象HEAD・作業状態・最新CI

- レビュー対象HEAD `54e54262768ed256aacdc811875e4a02b7d08fd7` は作業開始時のHEADと一致した。作業branchは`feat/pr22-e-formal-design-e2e-selection`。開始時worktreeはcleanで、差分・差分checkとも空／PASSだった。
- PR #27は引き続きDraft、head `54e54262768ed256aacdc811875e4a02b7d08fd7`、base／最終統合先`feat/development-qa-traceability`。GitHub上の本文は文書のみ追加済み・実装未実施という古い状態だったが、依頼どおり本文・commentは変更していない。
- このHEADに対応するActionsはsynthetic merge commit `59cf21f755b0ca62eef6f78062473cb971d8904a`で実行されている。`Validate Deterministic Output Evals` run 2153、`Codex Harness` run 848、`Validate Semantic Output Evals` run 2118、`Code Quality` run 848はsuccess。`Validate Agent Skills` run 2155はfailure。公式`skills-ref`によるSkill単体検証は通過し、最後のrepository structure照合が`README.md`に`e2e-test-selection`がないため失敗した。いずれもレビュー対象HEADの結果であり、本節の未commit worktreeのCI証拠ではない。
- 今回の変更はすべて未commit。変更後worktreeに対するGitHub Actionsは実施していない。

### 6件の指摘への対応

#### 1. 正式設計coverage完了判定 — 修正

- 原因は`formal_design_summaries`が任意入力なのに、内部整合したsummaryだけで正式設計coverageを完了扱いできたこと。`formal_design_record`の生成元は`test-condition-design`の`validate_formal_design()`で、そのrecordとsummaryは`payload`へ出力される。`coverage-analysis`への本番受け渡し元・Aの登録済みreadback callerはこのbranchに存在せず、runtime unit test以外に接続済みcallerは確認できなかった。
- `coverage-analysis/scripts/traceability.py`の`_formal_design_summary_rows()`／新設`_formal_record_metrics()`／`_build()`でsummary値をrecordから再計算するよう変更した。design ref／revision、item・condition scope、候補母集団、全pair判断、Authorityとsource revision/currentness、revision履歴、候補ID割当・retirementを検証する。record欠落・不一致、stale／unknown依存、未割当stale source、分母0、不完全な母集団、unconfirmed／blockedが残る場合は完了しない。CI artifact graphは別分母のまま維持し、formal summaryを渡さない既存CI経路も変更していない。
- 再現・回帰は`tests/skills/runtime/test_coverage_analysis_traceability.py`に追加した。自己整合する2/2 summaryだけ、record内にunconfirmed pairがあるのに2/2と偽るsummary、design ref／revision不一致、stale source、未割当stale source、分母0・不完全母集団を負例にした。生成したcurrent recordの正常1/1 fixtureは完了し、CI graphにはCOND nodeが混ざらない。最終22 tests PASS。
- 未完了の境界：recordは局所構造検証済みの入力であり、悪意ある呼出元がrecordとsummary双方を捏造した場合の真正性、実providerのcurrent revision、承認、保存・CAS・readbackは証明しない。共通runtime契約が必要なためA／PR #22へ引き継ぐ。

#### 2. stale sourceによる正式設計全体の拒否 — 修正

- 原因は`condition_structure.py::validate_formal_design()`がsource行のcurrentnessだけでpacket全体を停止していたこと。item、condition、itemごとのtest-level evidence、採用expected-resultのAuthority refsからpair依存を作り、stale sourceが影響するpairを特定できる場合は該当pairだけblockedにした。duplicate pairは採用対象への依存を伝播する。pairに割り当てられないstale sourceは影響範囲不明として全pairをblockedにする。stale Authorityに依存する期待結果はTCNへprojectしない。
- partial rerunではstale pairのcurrent TCN Entityを再生成せず、既存ID・revision履歴を保持する。影響しないpairは以前のIDを維持し、scope外current Entityを再生成しない。`tests/skills/runtime/test_test_condition_structure.py::test_formal_stale_pair_partial_rerun_preserves_unrelated_artifacts`でTI-001 stale、TI-002 unaffected、TCN-001／TCN-002 identity stateとrevision 1 history維持、scope外Entity非生成を確認した。stale Authority／unmapped stale依存は`test_formal_design_contract.py`で個別確認した。最終condition 13 tests、formal 17 tests PASS。
- A共通runtime上の保存Entity freshness・stale伝播・別session再開は局所fixtureでは証明できずPR #22へ引き継ぐ。共有state名・provider契約は追加していない。

#### 3. 複数itemのtest level — 修正

- 原因はformal packet全体で単一の`test_level_evidence`を解決していたこと。`test-condition-design/scripts/condition_structure.py`の`resolve_item_test_levels()`でitemごとに対応TR由来evidenceを解決し、明示user／project指定、承認済みarchitecture、system defaultの優先順位を保持する。採用pairと対応TRのlevel／source refが一致しない場合は拒否する。`requirement_structure.py`には変更不要で、既存のTR単位割当とprovenanceを利用した。
- TI-001 integration／TI-002 system、明示指定優先、未承認architectureはsystemへfallback、TR不一致拒否、`other_test_level`非生成、同一レベル既存fixture・TCN ID維持を回帰確認した。`test_condition_structure` 13 tests、`test_requirement_structure` 11 tests PASS。

#### 4. E2E選定のrevision履歴 — 修正

- 旧`e2e-selection-v1`はcandidate ID/key・change reason・retirementを持つ一方、過去revisionのdecision、rationale、source revision/currentnessを再構成できなかった。`selection_contract.py`でrevisionごとの`selection_snapshot`とsnapshot・decision・rationale・source・retirement・change reasonを結ぶ`revision_digest`を追加し、現在revisionの`current_revision_digest`を返す。digestなしの旧snapshot履歴は読めるがblockedにする。過去snapshotの整合性値を欠損時に推測しない。legacy rowにsnapshot自体がない旧形式も解析可能なままblockedにする。versionはv1のままとし、旧形式を読む後方互換readerを維持した。
- decision／rationale／source revision変更をdigestと照合し、不一致を検出する独立負例を追加した。revision 1→2→3、selected→not_selected→selected、source revision更新、retirement reason累積、candidate ID再利用拒否、履歴欠落・digest欠落、legacy読取を`tests/skills/runtime/test_e2e_selection_contract.py`で確認し、26 tests PASS。`E2ESelectionDeterministicContractTests` 9 testsもPASS。
- Skill、guidance、output template、deterministic validatorとcase 001〜003のreference／expectedを同じ契約へ更新した。SHA-256値は内容整合性の検査であって署名ではない。digestとsnapshotを一緒に変更する攻撃や、provider上のcurrentness／readbackはAの保存・Machine Entity fingerprint・CAS契約が必要であり、PR #22へ引き継ぐ。

#### 5. E2E選定CLI JSON入力保護 — 修正

- 既存`coverage-analysis/scripts/runtime_contract.py`／`qa-workflow/scripts/runtime_contract.py`の通常runtime境界を調査した。通常stdin 2 MiB、stdout 16 MiB、depth 64、1文字列64 KiB、JSON number token／展開値4096文字。duplicate key、strict UTF-8、非有限数、surrogate拒否も一致させた。aggregate入力だけの16 MiB上限は通常CLIには適用しない。Skill単独copy portabilityを保つため外部／repository-local importは増やさずPython標準ライブラリで実装した。
- `main()`は上限内読込、schema検証、structured error envelope、正常CLI互換を維持し、不正入力でtracebackを出さない。26 E2E runtime testsにoversized、duplicate key、過深、NaN／Infinity、UTF-8、surrogate、top-level schema、stdout limit、正常入力とisolated Skill copyを含めPASS。入力拒否は既存のCLI status code契約どおりstructured resultで返す。

#### 6. PR本文・Planの古い状態 — ローカルPlan更新

- PR本文が文書のみ・実装未実施として古いことを確認した。GitHub本文は変更せず、置換案は最終報告に提示する。本節と過去節の区別を記録した。

### 追加レビューで見つけた問題

- `_formal_record_metrics()`がpairに割り当てられないstale sourceを無視できた。別のcurrent pairへ誤って影響を与えない一方、scope不明sourceを無関係と推測するため不安全だった。condition validatorと同じく、未割当stale sourceが1件でもあれば全pairをblockedに変更し、`test_unmapped_stale_formal_source_blocks_all_pairs`を追加した。coverage suite 22 tests PASS。
- E2E snapshotにdecision／rationale／source revisionは追加されたが、snapshot単体の改変検出値がなかった。4件目の対応としてrevision digestを加え、decision・rationale・source revision改変を別々に検出した。
- `test-analysis`のrouting、`test-requirement-design`のTR割当、`test-condition-design`のpair projection、`test-case-design`のAuthority／formal candidate消費、既存CI coverage graphを追加確認し、上記以外の担当内不具合は確認しなかった。固定fixtureは接続済みprovider証拠として扱わない。

### 最終検証結果

環境はWSL2 / Linux、Python 3.12。`python` commandがないためPython検証は`python3`で実行した。

| 検証                                                                                                                      | 実行結果                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python3 -m unittest tests.skills.runtime.test_e2e_selection_contract -v`                                                 | PASS 26 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_formal_design_contract -v`                                                 | PASS 17 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_test_condition_structure -v`                                               | PASS 13 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_test_requirement_structure -v`                                             | PASS 11 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_case_structure -v`                                                         | PASS 11 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v`                                         | PASS 22 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v`                                                | PASS 2 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts.E2ESelectionDeterministicContractTests -v` | PASS 9 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python3 -m unittest discover -s tests/skills/evals/deterministic -v`                                                     | FAIL 299 tests中4 failures／1 error。3件はA所有WCAG SQLite provider登録が`blocked`になるtests、1件はcurrent Project Context state-root source不足のWCAG runtime test、1 errorはsandbox内localhost TCP bindの`PermissionError`。E2E selection evalは上の独立suiteで9/9 PASS。                                                                                                                                                                                                                  |
| `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v`                                             | PASS 12 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`                                                  | FAIL 559 tests中10 failures／9 errors。1 failureはA所有`test_ci_handoff.CiHandoffTests.test_json_nesting_failure_is_a_structured_input_error`が期待`nesting`に対して`JSON document must be an object`を返す。SQLite履歴provider suiteは9 failures／9 errors。9 errorsは全て`sqlite3.OperationalError: unable to open database file`、9 failuresはproviderが`workflow_state_provider_unavailable`／`workflow_state_unreadable`でblockedするケース、書込みblocked、競合更新の期待status不一致。 |
| `python3 scripts/skills/evals/semantic/validate.py`                                                                       | PASS 24 Skills／168 cases                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v`                                                  | PASS 27 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest discover -s tests/skills/evals/semantic -v`                                                          | PASS 13 tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m unittest discover -s tests/skills/evals/trigger -v`                                                           | PASS 1 test。dataset契約検証であり、実Agent発火評価ではない。                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `python3 -m compileall -q`（変更Python runtime・validator・tests）                                                        | PASS。本節更新後の最終実行。                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python3 scripts/format_tracked.py check`                                                                                 | ERROR。tracked formatterが`ruff`を起動できず`No such file or directory`。Ruffは環境未導入のため変更していない。                                                                                                                                                                                                                                                                                                                                                                               |
| `dprint check`（tracked dprint対象全体）                                                                                  | PASS。本節とcase 003 tableをrepo指定dprint 0.55.2でformat後に確認。                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `git diff --check`                                                                                                        | PASS。本節追記後に確認。                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| local `skills-ref validate`                                                                                               | SKIP。`skills-ref` executableなし。review HEAD CIではSkill単体検証PASS、repository README照合はFAIL。local未commit変更の公式検証としては扱わない。                                                                                                                                                                                                                                                                                                                                            |
| 実Agent trigger／実semantic Judge                                                                                         | 未実施。実Agent runtime受入には`codex --no-daemon --strict-config` embedded/non-shared session、project trust、対象tool-mode Hook／execpolicy確認が必要。CLI `codex-cli 0.167.0`の存在だけでは条件を満たさず、現在環境の`NoNewPrivs=1`／`Seccomp=2`下でtrigger実行を開始していない。Judge Adapter／providerもなく意味評価は未開始。                                                                                                                                                           |
| 変更後worktreeに対するGitHub Actions                                                                                      | 未実施。変更をpushしない制約による。review HEAD CIは代替証拠にしない。                                                                                                                                                                                                                                                                                                                                                                                                                        |

### 現在の完了状態と残件

- E担当で修正可能なcoverage入力検証、pair-level stale判定、item単位test level、revision履歴、CLI JSON境界は実装し、指摘ごとの回帰を追加した。各担当runtime suiteとE2E deterministic suiteはPASS。固定fixtureの結果は実provider成果物の証拠ではない。
- PR #27全体の受入は未完了。full deterministic／runtime suiteの共有A owner失敗、README未登録、local Ruff／skills-ref不足、実provider保存・approval・CAS・readback、source stale propagation、実Agent／実Judge、変更後GitHub Actionsが残る。
- `formal_design_record`の実保存／approval／CAS／readback currentness、E2E selection Machine Entity登録とdigest保存readback、source refとcurrent revisionのtrusted照合はE branchで独自契約を作らずAへ渡す。

### A担当への引継ぎ

1. 対象：root `README.md`と`.github/workflows/validate-skills.yml`のcanonical Skill一覧・責務・routing。現状：`e2e-test-selection`未登録でValidate Agent Skills run 2155が最後のrepository照合に失敗。期待：Skill一覧と`test-analysis`→E2E selection→既存inspectionへのroutingを載せ、TC直接指定・既存E2E直接実行入口を維持。検証：`Validate Agent Skills`全stepと公式`skills-ref validate skills/e2e-test-selection`。
2. 対象：共有`ASSERTIONS.md`。現状：RISK-D016／D017がlegacy `test-analysis` E2E table契約として残る一方、E2E-SEL-D001〜D006は新Skillのowner assertion。期待：旧Assertionのlegacy適用範囲を明記し、新Skill assertionをregistryに追加・参照する。既存legacy assertionを移行根拠なく削除しない。検証：deterministic output suite全体とAssertion参照／正負例。
3. 対象：A共有runtimeのartifact／source registrationとMachine Entity保存契約。現状：正式設計recordとE2E selection recordはE runtime output/input fixtureの範囲で、trusted durable provider/readback callerなし。期待：登録済みartifact ref、revision、scope、Authority・source currentness、承認、create-if-absent/CAS、保存後readback、stale伝播と再開を共通契約で提供する。E2Eの`current_revision_digest`／history `revision_digest`をMachine Entity content fingerprint・readbackへ結び、digest単体を署名と扱わない。検証：実provider保存・競合CAS・失敗後readback・別session再開・source変更から下流へのcurrentness suite。
4. 対象：A所有`ci_handoff`／SQLite workflow history providerとそのtests。再現：`python3 -m unittest tests.skills.runtime.test_ci_handoff -v`でnesting negativeのerror期待不一致、`python3 -m unittest tests.skills.runtime.test_sqlite_workflow_history -v`で9 errors／9 failures。unable-to-open-database-file／provider-unavailable/unreadableの根因は本検証で特定していない。期待：安全なartifact readback／CAS境界を保って環境別provider状態・JSON nesting処理を調査し、WSL2/LinuxとWindowsでsuiteを再実行する。

### PR #22への横断統合引継ぎ

1. B/C/D/F実成果物からProduct Risk→TR→TCN／CI→TCおよびE2E選定へ実ref、revision、Authority、scope、currentnessを照合する。Eの固定fixtureのPASSで代替しない。
2. Aのruntime登録・実providerを用い、formal design／E2E選定のsave、approval、CAS、readback、source変更stale伝播、失敗後・別session再開を実証し、G/H/J consumerの受け渡しを検証する。
3. 全current Skill routing／発火、実Agent trigger、実semantic Judgeを実行可能な承認済みruntimeで評価する。未実施のS1〜S17、人間編集8ケース、開発連動QA15条件／QA全工程10条件、詳細Plan 01〜08を最終判定し、統合後Actionsを確認する。

### 今回の文書・コード不一致一覧

- `coverage-analysis`はsummaryだけで完了できた実装と、正式設計成果物・候補coverageを根拠にする要件が不一致だった。record再計算と負例で修正した。
- `test-condition-design`はsource一件のstaleでpacket全体を拒否し、formal packet単一test levelを全itemに要求した。pair依存範囲とitem/TR単位levelへ修正した。
- E2E output templateがrevisionごとのsource snapshotを要求する一方、実装履歴はID/key中心だった。snapshot・digestと対応するJSON／Markdown／eval fixtureを追加した。
- `README.md`に新canonical Skill登録がなく、CIのrepository structure checkが失敗する。共有A ownerのため未変更、上記へ引継ぎ。
- 共有`ASSERTIONS.md`のRISK-D016／D017はlegacy `test-analysis` table用で、新Skill assertionsの移管記述が未反映。A ownerへ引継ぎ、legacy compatibilityは維持した。
- A共有`ci_handoff`のnesting負例は期待するJSON depth errorと実際のtop-level object errorが異なる。担当外なので未変更、Aへ再現条件を引継ぎ。
- 以上以外、今回追加レビュー対象のtest-analysis、test-requirement-design、test-case-design、既存CI coverage graphとの局所契約不一致は確認していない。

## push試行・remote確認（2026-11-10）

- 実装commitは`9c663401c932b803651cc4fbddc33a69c8611a75`、その時点のPlan記録commitは`ae4a45529c64594737a19cc35ba86d54cffed144`。指定の`HEAD:refs/heads/...`形式はrepository PreToolUse Hookが宛先を現在branchとして認識できず拒否した。Safety harness文書に沿う同一宛先の`HEAD:feat/pr22-e-formal-design-e2e-selection`形式で通常pushを試したが、GitHub HTTPSがusernameを取得できず`could not read Username ... No such device or address`で失敗した。force、別credential経路、ref更新APIは使っていない。
- push後に予定していた`git status -sb`／`git ls-remote`での一致確認はできていない。read-only GitHub PR metadataではPR #27はopen／Draft、base `feat/development-qa-traceability`、remote headは引き続き`54e54262768ed256aacdc811875e4a02b7d08fd7`だった。したがってlocalの2 commitは未pushで、local／remote HEADは不一致。PR本文は未変更。
- GitHub Actionsはremote head `54e54262768ed256aacdc811875e4a02b7d08fd7`に対する結果のみ確認した。Code Quality run 848、Validate Deterministic Output Evals run 2153、Validate Semantic Output Evals run 2118、Codex Harness run 848はsuccess。Validate Agent Skills run 2155は`validate` jobの`Validate repository eval structure` stepでfailure。原因は共有`README.md`に`e2e-test-selection`登録がないことで、owner A。これらはlocal未push commitsの検証ではない。
- local再開条件：通常のGitHub HTTPS認証がこの実行環境から利用可能になった後、先に`git fetch origin`と`git status -sb`でremote先行を再確認し、remoteがlocal履歴のancestorの場合だけ指定branchへ通常pushする。remoteが進んでいた場合はpushを停止し、force／無断rebaseをせず調整する。認証情報の表示・コピー・別経路利用はしない。

## push完了・追加CI修正（2026-11-10）

- 実行環境更新後の`git fetch origin`で対象remote branchの先行変更がないことを確認し、通常pushが成功した。local／remote HEADは`e1b700915c98a89bbe958ef808844d0bdcba66af`で一致し、作業treeはclean。前項の認証失敗は解消済みとして履歴に残す。PR #27は引き続きopen／Draft。
- このHEADのActions：Validate Deterministic Output Evals run 2163 PASS、Validate Semantic Output Evals run 2128 PASS、Code Quality run 858 FAIL、Validate Agent Skills run 2165 FAIL、Codex Harness run 858 実行中（最後の確認時点）。Code Qualityのstep `Check tracked Python, Markdown, JSON, YAML, TOML, and JavaScript`は担当テスト2ファイルのRuff I001 import order違反で失敗した。`test_coverage_analysis_traceability.py`では同一test moduleのimport順、`test_e2e_selection_contract.py`では`copy`と`importlib.util`の順を修正する。local Ruff executableがないためRuffの独立実行は未実施、対象runtime 22件＋26件、compileall、dprint check、`git diff --check`は修正後PASS。
- Validate Agent Skills run 2165はrepository eval structure stepで`README.md`に`e2e-test-selection`がないためFAIL。Skill単体spec stepはPASS。READMEは共有A ownerのためEでは変更せず、Aへ引継ぎを継続する。
- 上記import order修正と本Plan記録を担当branchへ次の通常commit／push対象とする。修正後HEADのActionsはpush後に別途確認し、run 858のCodex Harnessが実行中だった結果は完了と扱わない。

## lint追修正とe2 commit Actions（2026-11-10）

- `468eee6a9034269b8b7f8c3248dbf26b1d219a84`は通常push済みでlocal／remote一致を確認した。Actions完了後の結果：Validate Deterministic Output Evals run 2165 PASS、Validate Semantic Output Evals run 2130 PASS、Codex Harness run 860 PASS、Validate Agent Skills run 2167 FAIL、Code Quality run 860 FAIL。
- Code Quality run 860では最初の修正で`test_e2e_selection_contract.py`のI001は解消したが、`test_coverage_analysis_traceability.py`でalias付きimportを同じ括弧内にまとめた形がRuff I001として残った。Ruffの自動修正提案に合わせ、`contract`／`drafts`／`packet`をそれぞれ独立した`from` importに変更した。local Ruff executableは未導入のため直接lintは未実施。追修正後、coverage suite 22件とE2E selection suite 26件はPASSし、対象compileall、dprint check、`git diff --check`もPASS。
- Validate Agent Skills run 2167の失敗はREADME canonical listに`e2e-test-selection`がないこと。Skill specification validationはPASS。共有READMEはA ownerであり未変更。新しい追修正のCode Quality再判定は次のpush後に確認する。

## Ruff format追修正とe3 Actions（2026-11-10）

- `2172b8a1ee1aa012c8a1fe39a97a703e86b00847`は通常push済みでremoteと一致。Code Quality run 861はRuff formatにより8ファイルが未整形と判定されFAILした。CI固定版`ruff 0.16.8`を`uv tool run`で使って以下を整形した：`skills/coverage-analysis/scripts/traceability.py`、`skills/e2e-test-selection/evals/deterministic/validator.py`、`skills/e2e-test-selection/scripts/selection_contract.py`、`skills/test-condition-design/scripts/condition_structure.py`、`tests/skills/runtime/test_coverage_analysis_traceability.py`、`tests/skills/runtime/test_e2e_selection_contract.py`、`tests/skills/runtime/test_formal_design_contract.py`、`tests/skills/runtime/test_test_condition_structure.py`。
- この8ファイルに対する`ruff format --check`と`ruff check`はPASS。coverage suite 22件、E2E selection suite 26件、compileall、dprint check、`git diff --check`もPASS。新しい整形差分とこのPlan記録を次のcommit／通常pushに含め、Code Qualityを再確認する。
- e3 ActionsはValidate Deterministic Output Evals run 2166 PASS、Validate Semantic Output Evals run 2131 PASS、Code Quality run 861 FAIL（上記format）、Validate Agent Skills run 2168 FAIL（READMEの新Skill登録漏れ、A owner）。Codex Harness run 861は最後の確認時点で実行中であり、PASS扱いしない。

## Ruff整形commitのpush結果（2026-11-10）

- Ruff 0.16.8で整形した8ファイルとこのPlan追記をcommit `ad89a52d5b962ecbc2d77788f00ef68cff5d3b59`（`style: format PR #27 implementation changes`）として通常pushした。`git status -sb`はclean、`git ls-remote --heads origin feat/pr22-e-formal-design-e2e-selection`も同じSHAを返し、local／remote一致を確認した。
- ad89 HEADのActions：Code Quality run 863 PASS、Validate Semantic Output Evals run 2133 PASS、Validate Agent Skills run 2170 FAIL、Validate Deterministic Output Evals run 2168 実行中、Codex Harness run 863 実行中（最後の確認時点）。Code Quality passはCI pinned RuffによるI001／format検査を含む。Validate Agent Skillsは`Validate repository eval structure`で`README.md`に`e2e-test-selection`がないため失敗、owner A。残る実行中workflowは完了扱いしない。
- PR #27はopen／Draftを維持し、PR本文は変更していない。担当内変更は保存済みだが、A ownerのREADME登録、共有ASSERTIONS／provider連携、実成果物を用いるPR #22横断検証、実Agent／Judge評価は未完了。

## 進捗保存（2026-11-10）

- 上記レビュー修正23ファイルをcommit `9c663401c932b803651cc4fbddc33a69c8611a75`（`fix: address PR #27 follow-up review findings`）として記録した。commit前にremoteをfetchし、branchはremoteと一致していた。commit直後はlocalが1 commit aheadで、pushとActions確認は未実施。
- commit前の`git diff --check`と`git diff --cached --check`はPASS。cached path一覧・statは予定した23ファイルと一致し、未追跡ファイルはなかった。テスト／formatter／評価結果は本節の上にある2026-11-10レビュー検証表を参照し、そこに記録したFAIL／ERROR／SKIP／未実施は未解消のまま保持する。
- review HEADの過去Actions結果をこのcommitの結果として扱わない。push後にCode Quality、Validate Agent Skills、Validate Deterministic Output Evals、Validate Semantic Output Evals、Codex Harnessの状態を最新branch HEADと照合して記録する。
- 次の作業：この担当branchへの通常push後、remote HEAD一致とPR #27のDraft状態を確認し、該当commit SHAごとのActions成功／失敗／実行中／未実行を追記する。README／ASSERTIONS、A provider連携、実Agent／Judge、PR #22横断統合は未完了のまま各owner引継ぎを維持する。

## 追加レビュー3件の修正・検証（2026-11-10）

### 対象HEAD・再現結果

- 対象branchは`feat/pr22-e-formal-design-e2e-selection`。レビュー対象／修正前HEADは`30289c915bcc64e6cdc4479c34189ab2c7740eee`。修正開始時のworktreeはcleanで、`git fetch origin`後もlocal／remote HEADは一致し、remote先行変更はなかった。
- stale TCN/model：`test_formal_stale_pair_partial_rerun_preserves_unrelated_artifacts`の更新scopeへstaleになった`TCN-001`／`ep-001`自身を含めた再現では、現行実装が`TCN-001: deleted`を返した。共有condition staleで複数pairを止める再現でも、scope内IDがdeletedとなった。失敗はID lifecycleと生成保留を同じ未再利用条件で扱う経路にあった。
- `other_test_level`：正式設計validatorはTI-002の別レベルpairを受理したが、返却recordとsummaryをcoverageへ渡すと`invalid_input`となり、割当レベルとの差をdecision別に扱っていなかった。
- E2E候補0件：不完全な候補母集団・具体的blockerありのrevision 1でsnapshot構築が`ContractError`となり、runtime結果／CLI envelopeを生成できなかった。revision履歴上の空snapshotも同じ経路で拒否された。

### 修正と再レビュー

- `skills/test-condition-design/scripts/condition_structure.py::_build()`は、formal source staleによって保留したTCN/model draftと、scope内でreuse指定された既存IDを区別する。reuse対象・scope・previous state・model parent／metadataの対応を検証し、対象IDをactive/inactiveのlifecycle履歴に保持する一方、stale pairに対するcurrent TCN/model Entityは出力しない。blocked pairは既存のformal issue／runtime unresolvedで示す。明示scope omissionのdeleted遷移と`zero_scope_terminal`は維持する。sourceがcurrentへ戻った再実行では既存TCN/model IDを再利用する。
- `skills/coverage-analysis/scripts/traceability.py::_formal_record_metrics()`をformal validatorのdecision契約に合わせた。`adopted`はitem割当レベル一致、`other_test_level`は割当レベルと異なることを検証する。別レベルpairの閉鎖は正式recordで確認するが、TCN／CIを生成せず、CI artifact graphのcoverage母集団も変更しない。
- `skills/e2e-test-selection/scripts/selection_contract.py::_selection_snapshot()`と`validate()`は、候補0件を「母集団不完全かつblockerあり」の未完了状態に限って記録可能にした。候補0件でblockerなし、または母集団completeは引き続き拒否する。decision／revision履歴、legacy互換性、CLI envelopeを変更していない。
- 関連仕様を`skills/test-condition-design/SKILL.md`、`skills/coverage-analysis/references/guidance.md`、`skills/e2e-test-selection/references/guidance.md`、`skills/e2e-test-selection/assets/output-template.md`へ反映した。再レビューでcurrent Entityの誤出力、明示削除の抑止、部分更新scope外の変更、formal/coverage判定不一致、履歴喪失、candidate 0の誤readyを確認する追加確定不具合は見つからなかった。

### 追加回帰テストと検証

再現時のnegative testは修正前に失敗することを確認し、以下の修正後テストはPASSした。古いrevisionのActions結果を今回のworktree検証とは扱わない。

| 検証                                                                                                                                                                                            | 結果                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `python3 -m unittest tests.skills.runtime.test_test_condition_structure -v`                                                                                                                     | PASS 16 tests。scope内stale TCN/model、共有condition stale、scope外artifact維持、source回復後のID再利用、明示削除、zero-scope terminal、inactive reuseを含む。                                                                                                                 |
| `python3 -m unittest tests.skills.runtime.test_formal_design_contract -v`                                                                                                                       | PASS 17 tests。decisionごとのtest level、other-level非採用TCN、既存Authority／source currentness負例を含む。                                                                                                                                                                   |
| `python3 -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v`                                                                                                               | PASS 25 tests。formal→coverageのother-level正常系、採用レベル不一致、other-levelが割当と同じ場合、CI graph分離を含む。                                                                                                                                                         |
| `python3 -m unittest tests.skills.runtime.test_e2e_selection_contract -v`                                                                                                                       | PASS 30 tests。空候補＋blockerのCLI envelope、blockerなし／complete空母集団の拒否、revision 1空snapshotからrevision 2候補追加、digest／legacy／single-Skill copyを含む。                                                                                                       |
| `python3 -m unittest tests.skills.runtime.test_test_requirement_structure -v`                                                                                                                   | PASS 11 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest tests.skills.runtime.test_case_structure -v`                                                                                                                               | PASS 11 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v`                                                                                                                      | PASS 2 tests。                                                                                                                                                                                                                                                                 |
| `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v`                                                                                                              | PASS 43 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v`                                                                                                                   | PASS 12 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest discover -s tests/skills/evals/deterministic -v`                                                                                                                           | FAIL 299 tests中4 failures。3件のWCAG SQLite provider testがexpected `created`／`registered`に対して`blocked`、1件のWCAG runtime testがcurrent Project Context state-root source不足でblocked。E担当差分外のA/shared provider経路。                                            |
| `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`                                                                                                                        | FAIL 569 tests中10 failures／9 errors。1 failureはA所有`test_ci_handoff.CiHandoffTests.test_json_nesting_failure_is_a_structured_input_error`で、期待`nesting`に対し`JSON document must be an object`。残る9 failures／9 errorsはA所有SQLite workflow history provider suite。 |
| `python3 -m unittest tests.skills.runtime.test_ci_handoff -v`                                                                                                                                   | FAIL 27 tests中1 failure、26 PASS。上記nesting負例。                                                                                                                                                                                                                           |
| `python3 -m unittest tests.skills.runtime.test_sqlite_workflow_history -v`                                                                                                                      | FAIL 20 tests中9 failures／9 errors、2 PASS。複数ケースでproviderが`workflow_state_unreadable`等を返すかDB操作がerrorとなる。原因はこの検証では特定していない。                                                                                                                |
| `python3 scripts/skills/evals/semantic/validate.py`                                                                                                                                             | PASS 24 Skills／168 dataset cases。これはdataset構造検証であり、実LLM Judge評価ではない。                                                                                                                                                                                      |
| `python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v`                                                                                                                        | PASS 27 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest discover -s tests/skills/evals/semantic -v`                                                                                                                                | PASS 13 tests。                                                                                                                                                                                                                                                                |
| `python3 -m unittest discover -s tests/skills/evals/trigger -v`                                                                                                                                 | PASS 1 test。実Agent trigger評価は未実施。                                                                                                                                                                                                                                     |
| `uv run --no-project --with ruff==0.16.8 python3 scripts/format_tracked.py check`                                                                                                               | PASS。221 tracked files formatted。                                                                                                                                                                                                                                            |
| `uv tool run --from ruff==0.16.8 ruff check <変更7 Python files>`                                                                                                                               | PASS。                                                                                                                                                                                                                                                                         |
| `uv tool run --from ruff==0.16.8 ruff format --check <変更7 Python files>`                                                                                                                      | PASS。7 files already formatted。                                                                                                                                                                                                                                              |
| `python3 -m compileall -q skills/coverage-analysis/scripts/traceability.py skills/e2e-test-selection/scripts/selection_contract.py skills/test-condition-design/scripts/condition_structure.py` | PASS。                                                                                                                                                                                                                                                                         |
| `git diff --check`                                                                                                                                                                              | PASS。                                                                                                                                                                                                                                                                         |

PR #27レビュー時点の`30289c915bcc64e6cdc4479c34189ab2c7740eee` ActionsはCode Quality run 864 PASS、Validate Deterministic Output Evals run 2169 PASS、Validate Semantic Output Evals run 2134 PASS、Codex Harness run 864 PASS、Validate Agent Skills run 2171 FAIL。最後の失敗はrepository structure validationで`README.md`に`e2e-test-selection`が登録されていないため。これらは未commit worktreeの結果ではない。

### 未完了事項と引継ぎ

- E担当の今回の3件は局所実装修正・回帰test・formatterがPASSした。担当内変更のcommit／pushとpush後Actions確認はこれから行う。実provider・承認・CAS・readback・別session再開、実Agent／実Judgeは未検証のまま。
- A担当：READMEのcanonical Skill登録・routing、共有ASSERTIONS更新、formal/E2E artifact registrationとMachine Entity保存・承認・CAS・readback契約を引き続き担当する。追加で、`test_ci_handoff`のnesting error契約、およびSQLite history suiteの9 failures／9 errorsとprovider unreadable状態を安全なreadback境界を維持して調査し、Linux／Windows両環境で再検証する。README変更後はValidate Agent Skillsを再実行する。
- PR #22統合：B/C/D/Fの実成果物を用いたformal design／E2E selectionのID・revision・Authority・scope・currentness照合、source変更時stale伝播、G/H/J下流consumerとの接続、実provider save／approval／CAS／readback、別session再開、全Skill routing、S1〜S17と人間編集8ケース、開発連動QA15条件／QA全工程10条件の最終判定を行う。
- 本追記時点の対象commit SHAとpush後Actionsは未確定のため、push後に別記する。PR #27本文は更新しない。README未登録、共有runtime、実provider、実Agent／Judge、PR #22統合が残るためPR #27全体の受入完了とはしない。

### commit・push・Actions結果（2026-11-10）

- 上記12ファイルをcommit `c0e7b801123ef590d3f25c5beaad67ff38153e81`（`fix: preserve formal design state and align selection contracts`）として記録し、対象branchへ通常pushした。push直前に`git fetch origin`と`git merge-base --is-ancestor origin/feat/pr22-e-formal-design-e2e-selection HEAD`を実行し、ancestor判定は終了code 0。push後のlocal HEADと`git ls-remote`のremote HEADは同じ`c0e7b801123ef590d3f25c5beaad67ff38153e81`、worktreeはclean。
- このcommitのGitHub Actions：Code Quality run 869 PASS、Validate Deterministic Output Evals run 2174 PASS、Validate Semantic Output Evals run 2139 PASS、Codex Harness run 869 PASS、Validate Agent Skills run 2176 FAIL。失敗jobは`validate`、失敗stepは`Validate repository eval structure`。`Validate Agent Skills specification`はPASSしており、repository eval structure failureは共有`README.md`のcanonical Skill一覧に`e2e-test-selection`がないため。owner A。過去HEADのActions結果と区別し、他4 workflowのPASSはこのcommit SHAに紐づく。
- このActions確認とcommit SHAを記録するPlan更新はdocumentation-only follow-upとして別commit／pushする。PR #27はopen／Draftを維持し、GitHub上のPR本文は変更していない。PR本文には「実装コードの追加と担当内の実受入は未実施」と古い状態が残っているため更新が必要だが、本作業では更新しない。

## 追加レビュー2件の修正・検証（2026-11-10）

### 対象HEADと修正前の再現

- レビュー対象・作業開始HEADは`eb1bd2a47a3aaaf44071099bab5d580145c293bc`。対象branchは`feat/pr22-e-formal-design-e2e-selection`で、開始時のworktreeはclean。`git fetch origin`後にlocal／remote HEADは一致し、remote先行commitはなかった。
- TCN Authority依存：TI-001だけのTCN draftが追加参照するSPEC-002をstaleにしたformal packetを`validate_formal_design()`へ渡し、返却された実`formal_design_record`／`formal_design_summary`をcoverageへ接続した。修正前はrecordにpair固有参照がなく、coverageの未割当stale source fail-closed処理がTI-002も止め、formalとcoverageのclosed pair数が一致しなかった。
- E2E過去snapshot：revision 1に`population_complete=false`、候補1件、blockerなしのsnapshotを置き、既存`_revision_digest()`で履歴digestを再計算したrevision 2 fixtureを作成した。修正前は現行revisionと異なり、過去snapshotの検証がblocker欠落を拒否しなかった。

### 原因と修正

- `skills/test-condition-design/scripts/condition_structure.py::validate_formal_design()`はadopted pairの`tcn_authority_refs`を検証し、対応draftの`authority_refs`がある場合は集合一致を要求する。packetに値がなければ検証済みdraftからcanonicalに導出し、入力・draft双方がなければ依存不明として該当pairをblockedにする。登録Authority／source、revision、currentness検証を通った参照をpair stale dependencyとformal recordの両方に同じく反映する。非採用pairはこのfieldを受理しない。
- `skills/coverage-analysis/scripts/traceability.py::_formal_record_metrics()`はpair別TCN Authority参照をsource dependencyに含め、formal validatorと同様に影響pairだけをblockedにする。unknown／不正参照は拒否し、古いrecordで参照集合が欠落しているadopted pairはunresolved・`record_verified=false`としてcompleteへ昇格させない。既存のunmapped stale sourceの全pair fail-closedは維持し、formal candidate coverageとCI graphを混同しない。
- `skills/e2e-test-selection/scripts/selection_contract.py::_selection_snapshot()`に、現行revisionと同じ`population_complete=false`かつblocker必須条件を加えた。候補数にかかわらず、過去snapshotの入力契約違反をdigest再計算で通せない。schema version、history形式、digest方式は変更していない。digestは内容整合性確認であり、保存先の真正性証明ではない。
- 旧形式formal packetは読める状態を保つが、adopted pairの依存関係を復元できない旧recordは完了扱いしない。partial rerunでdraftがない場合も明示されたpair参照だけを使い、ない依存は推測しない。CI graph、scope外artifact、ID／revision履歴を変更せず、共通runtime／providerにも変更を加えていない。
- 仕様を`skills/test-condition-design/SKILL.md`、同output template、`skills/coverage-analysis/references/guidance.md`、`skills/e2e-test-selection/references/guidance.md`および同output templateへ反映した。E担当deterministic fixtureに新契約を必要とする更新はなかった。

### 回帰テストとローカル検証

修正前の再現テストは両方とも期待した不具合を検出し、修正後は次の対象テストがすべてPASSした。

- `python3 -m unittest tests.skills.runtime.test_test_condition_structure -v` — PASS 16 tests。
- `python3 -m unittest tests.skills.runtime.test_formal_design_contract -v` — PASS 22 tests。draft由来Authorityのrecord保持、TI-001だけのstale、draftとの不一致、unknown/currentness不正、draftなしの未解決を含む。
- `python3 -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v` — PASS 28 tests。formal runtimeの実record／summaryをそのままcoverageへ渡すケースで、SPEC-002 stale時は1/2・TI-001だけunresolved、current回復後は2/2となる。
- `python3 -m unittest tests.skills.runtime.test_e2e_selection_contract -v` — PASS 32 tests。不完全母集団・候補あり・blockerなしのdigest整合過去snapshotを拒否し、blocker追加時は受理する。
- `python3 -m unittest tests.skills.runtime.test_test_requirement_structure -v` — PASS 11 tests。
- `python3 -m unittest tests.skills.runtime.test_case_structure -v` — PASS 11 tests。
- `python3 -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v` — PASS 2 tests。
- `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v` — PASS 43 tests。
- `python3 -m unittest tests.skills.runtime.test_runtime_portability -v` — PASS 3 tests。E2E selectionのSkill単独copy実行は対象runtimeでも確認済み。
- `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v` — PASS 12 tests。
- `python3 -m unittest discover -s tests/skills/evals/deterministic -v` — FAIL 299 tests中4 failures。WCAGの`test_sqlite_provider_uses_atomic_revision_compare_and_reread`、`test_wcag_canonical_plan_is_immutable_per_revision_and_context`、`test_wcag_report_requires_persisted_owner_runtime_result`はproviderが`blocked`を返し、`test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread`はcurrent Project Context state-root source不足でblocked。これらは変更差分外。
- `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — FAIL 579 tests中10 failures／9 errors。直前の記録済みruntime全体（569 tests、同10 failures／9 errors）から10 tests増え、今回の対象テストはすべてPASS。失敗集合はA担当`test_ci_handoff`の`test_json_nesting_failure_is_a_structured_input_error` 1件と、A担当`test_sqlite_workflow_history`の9 failures／9 errorsで、修正前に記録した同じ失敗群が継続する。
- `python3 -m unittest tests.skills.runtime.test_ci_handoff -v` — FAIL 27 tests中1 failure／26 PASS。JSON nesting不正時に期待する`nesting`ではなく`JSON document must be an object`が返る。E差分外のA担当契約。
- `python3 -m unittest tests.skills.runtime.test_sqlite_workflow_history -v` — FAIL 20 tests中9 failures／9 errors／2 PASS。failuresは作成／CAS、競合、legacy履歴readback等がprovider-unavailable／unreadableまたはblockedになるもの。errorsはSQLite DB作成時の`sqlite3.OperationalError: unable to open database file`。この実行では原因の追加特定に至らず、E差分外のA担当調査事項。
- `python3 scripts/skills/evals/semantic/validate.py` — PASS 24 Skills／168 dataset cases。dataset検証のみであり、実LLM Judge評価は未実施。
- `python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v` — PASS 27 tests。
- `python3 -m unittest discover -s tests/skills/evals/semantic -v` — PASS 13 tests。
- `python3 -m unittest discover -s tests/skills/evals/trigger -v` — PASS 1 test。dataset契約検証のみであり、実Agent発火評価は未実施。
- `uv run --no-project --with ruff==0.16.8 python3 scripts/format_tracked.py check` — PASS、221 tracked files。最初はoutput templateのtable alignment 1件を検出したためdprintで整形し、再実行PASS。
- `uv tool run --from ruff==0.16.8 ruff check <変更6 Python files>`と`ruff format --check <変更6 Python files>` — PASS。6 files。
- `python3 -m compileall -q <変更6 Python files>` — PASS。
- `git diff --check` — PASS。

### 残件・引継ぎ・CI

- E担当の2件は再現・局所修正・回帰検証済み。変更後のprovider保存／承認／CAS／readback、source変更時の別session stale propagation、実Agent／実Judge、PR #22横断実成果物確認は未実施。
- A担当／PR #22統合owner：共有README・ASSERTIONSとcanonical Skill routingの更新、正式設計／E2E artifact registrationおよびprovider保存・承認・CAS・readbackの公開契約を担当する。加えて既存`test_ci_handoff` nesting errorとSQLite historyの9 failures／9 errorsを、安全なreadback境界を維持した状態で調査する。
- PR #22では、実TCN draft／Machine Entity／Authorityを用いてpair依存を照合し、正式設計recordとcoverage再計算が一致すること、旧recordとpartial rerunがunresolvedを保つこと、source変更時のstale伝播を別sessionまで検証する。E2E過去snapshotの実保存readbackもproviderで検証する。
- PR #27はDraftを維持し、GitHub上のPR本文は変更しない。PR本文に古い「実装コードの追加と担当内の実受入は未実施」という記載が残るため、実装状況・局所test PASS・残存するActions／provider／横断受入を反映する更新案を最終報告へ示す。

### commit・push・GitHub Actions（2026-11-10）

- 12担当ファイルをcommit `37432d93c9e4edf67a9e9b296de9c10401dd99a5`（`fix: align formal authority dependencies and E2E history validation`）へ記録。push前の`git fetch origin`後、`git merge-base --is-ancestor origin/feat/pr22-e-formal-design-e2e-selection HEAD`は終了code 0。通常push成功。
- push後のbranchは`feat/pr22-e-formal-design-e2e-selection`。local HEADとremote `ls-remote`のHEADはともに`37432d93c9e4edf67a9e9b296de9c10401dd99a5`、worktreeはclean。
- commit SHAに関連付いた最新Actions：Code Quality run 879 PASS、Validate Deterministic Output Evals run 2184 PASS、Validate Semantic Output Evals run 2149 PASS、Codex Harness run 879 PASS、Validate Agent Skills run 2186 FAIL。各runの`head_sha`は本commit SHA。Validate Agent Skillsでは仕様検証PASS、job `validate`の`Validate repository eval structure` stepがFAILし、ログは共有`README.md`に`e2e-test-selection`がないことを示す。README変更は今回の権限外で、PR #22統合ownerへ引継ぎ済み。
- Validate Agent Skillsのjob logでは実行checkoutがsynthetic merge commit `a248c792122f73a086d5e494179d2dea8bb95fe5`だった。GitHubは上記runを本branch HEADへ関連付けているが、merge結果の実行とbranch単体HEADの検証を同一視しない。CI結果はPR連動Actionsの現状として報告し、source-only実行証拠とはしない。
- PR APIで確認：PR #27はopen／Draft、head `37432d93c9e4edf67a9e9b296de9c10401dd99a5`、base `feat/development-qa-traceability`。PR本文は変更していない。全体受入にはREADME登録、実provider契約、実Agent／Judge、PR #22横断検証が残る。

## 担当E残作業の再検証・外部blocked記録（2026-11-10）

### 対象HEAD・GitHub状態

- 対象HEADは`870c911ab76dab915a06c3b1e92b6771a1bd1d3b`。`git fetch origin`後、`git status -sb`は`feat/pr22-e-formal-design-e2e-selection...origin/feat/pr22-e-formal-design-e2e-selection`、`git log -1 --oneline`は`870c911a docs: record PR #27 authority and snapshot CI results`、localと`origin/feat/pr22-e-formal-design-e2e-selection`の`git rev-parse`は同一SHAだった。作業開始時とPlan追記前の`git status --short`、`git diff --stat`、`git diff --check`、`git ls-files --others --exclude-standard`はいずれも差分なし。
- PR APIではPR #27はopen／Draft、baseは`feat/development-qa-traceability`、headは上記SHA。GitHub上のPR本文は未変更だが、「実装コードの追加と担当内の実受入は未実施」という記述が現状と食い違う。

### 完了基準の最新照合

| 担当Planの完了基準                                                  | 最新状態                   | 対象HEADの証拠・残件                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 各正本・Authorityと既存設計の局所検証                               | PASS                       | 正式設計record／coverage／E2E selectionのfixture・runtime確認は既往記録にあり、今回のHEADでも対象回帰suiteを再実行した。B/C/D/F実成果物の横断照合はPR #22へ引継ぎ。                                                                                                                                                                                                                                     |
| 採否・blocked・別レベル・期待結果・CIの区別                         | PASS                       | `test_test_condition_structure` 16件、`test_formal_design_contract` 22件、`test_coverage_analysis_traceability` 28件がPASS。                                                                                                                                                                                                                                                                            |
| E2E選定の実Agent発火と直接実行経路の分離                            | BLOCKED／未実施            | `codex --version`は`codex-cli 0.167.0`、`codex --no-daemon --strict-config exec --help`は成功。repositoryのQA Skillは`skills/*/SKILL.md`配下に24件ある一方、`.agents/skills/`にはCodex用の3 Skillだけで、QA Skillを同時にdiscoverして発火ログを取る正規harnessは見つからなかった。`tests/skills/evals/trigger` 1件PASSはdataset構造検査のみ。train／validation／holdoutを実Agentで各3回実行していない。 |
| 新旧Skillのisolated packaging、trigger、semantic、deterministic評価 | 部分PASS／未完了           | Python 3.11.17で`test_e2e_selection_contract` 32件と`test_runtime_portability` 3件がPASS。Python 3.12.3でも全E担当runtimeとportable-copyテストがPASS。変更6 Skillへの公式`skills-ref validate`は全PASS、deterministic出力契約テスト43件もPASS。実Agent triggerと実semantic Judgeは未実施のため基準全体は未完了。                                                                                        |
| 正常系・負例・legacy・下流consumer・CI回帰                          | 部分PASS／未完了           | 対象runtimeはPASS。全deterministic suiteは299件中295 PASS／4 FAIL、全runtime suiteは579件中560 PASS／10 FAIL／9 ERROR。既知の失敗群は以下に記録し、PR #22／A担当へ引継ぎ。最新CIのValidate Agent SkillsもREADME登録欠落でFAIL。                                                                                                                                                                         |
| 実runner・実保存先・承認・CAS・readback・別session再開              | BLOCKED／未実施            | Eの`selection_contract.py`は保存を仮定しないvalidator、formal runtimeも局所record／Entity生成までで、E成果物を登録する共有provider APIはこのbranchにない。既存`qa-workflow`のSQLite保存経路はWCAG専用。実provider・承認権限・E artifact registrationがなく、fixtureやWCAG providerで代替していない。A／PR #22で契約と保存先が接続後、save／readback／CAS競合／stale／別session resumeを再開する。       |
| source変更時のstale伝播・失敗後再開                                 | 部分PASS／未完了           | fixture runtimeではsource／Authority currentness、影響pair限定のstale、履歴維持と再評価を確認済み。実保存後のsource変更、provider stale伝播、別session readbackを示す証拠はないため、実provider条件としてPR #22へ引継ぎ。                                                                                                                                                                               |
| repository-wide Validate Agent Skills                               | FAIL／owner引継ぎ          | run 2188はjob `validate`、step `Validate repository eval structure`でFAIL。先行する公式Agent Skills specification stepはPASS。ログは`README.md`に`e2e-test-selection`が欠落と明示。README変更は共有owner範囲のため本branchでは行わない。                                                                                                                                                                |
| Plan・PR本文・実装・CIの整合                                        | Plan更新済み／PR本文未更新 | 本追記は対象HEADの現状を記録する。GitHub PR本文は今回変更しない。更新案は最終報告に提示する。                                                                                                                                                                                                                                                                                                           |
| PR #22へ証拠・依存条件を引継ぎ                                      | 更新済み                   | 下記「残件・引継ぎと再開条件」にPR #22 owner、必要なartifact、保存契約、workflow、再検証を記録。横断完了条件を担当EのPASSへ繰り上げていない。                                                                                                                                                                                                                                                           |

### 対象HEADでのローカル検証

以下は2026-11-10にlocal HEAD `870c911ab76dab915a06c3b1e92b6771a1bd1d3b`で個別実行した結果。

- `python3 -m unittest tests.skills.runtime.test_test_condition_structure -v` — PASS 16 tests。
- `python3 -m unittest tests.skills.runtime.test_formal_design_contract -v` — PASS 22 tests。
- `python3 -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v` — PASS 28 tests。
- `python3 -m unittest tests.skills.runtime.test_e2e_selection_contract -v` — PASS 32 tests。
- `python3 -m unittest tests.skills.runtime.test_test_requirement_structure -v` — PASS 11 tests。
- `python3 -m unittest tests.skills.runtime.test_case_structure -v` — PASS 11 tests。
- `python3 -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v` — PASS 2 tests。
- `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v` — PASS 43 tests。
- `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v` — PASS 12 tests。
- `python3 -m unittest discover -s tests/skills/evals/deterministic -v` — FAIL 299 tests中295 PASS／4 FAIL。失敗は`test_sqlite_provider_uses_atomic_revision_compare_and_reread`、`test_wcag_canonical_plan_is_immutable_per_revision_and_context`、`test_wcag_report_requires_persisted_owner_runtime_result`（いずれもproviderが`blocked`）、`test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread`（Project Context state-root source不足）。すべて既往検証と同じA/shared WCAG provider系で、E差分外。
- `python3 -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — FAIL 579 tests中560 PASS／10 FAIL／9 ERROR。失敗は`test_ci_handoff.CiHandoffTests.test_json_nesting_failure_is_a_structured_input_error` 1件（期待するnesting errorと実際のtop-level object errorの不一致）と、`test_sqlite_workflow_history`の9 FAIL／9 ERROR（provider blocked／unreadable、SQLite `unable to open database file`）。対象HEADのE担当runtime suiteはすべてPASS。変更前記録と同じ失敗集合。
- `python3.11 -m unittest tests.skills.runtime.test_e2e_selection_contract -v` — PASS 32 tests。
- `python3.11 -m unittest tests.skills.runtime.test_test_condition_structure -v` — PASS 16 tests。
- `python3.11 -m unittest tests.skills.runtime.test_formal_design_contract -v` — PASS 22 tests。
- `python3.11 -m unittest tests.skills.runtime.test_coverage_analysis_traceability -v` — PASS 28 tests。
- `python3.11 -m unittest tests.skills.runtime.test_runtime_portability -v`および`python3 -m unittest tests.skills.runtime.test_runtime_portability -v` — 両方PASS 3 tests。single-copy runtimeとSkill-local helper import条件を確認。
- `python3 scripts/skills/evals/semantic/validate.py` — PASS 24 Skills／168 cases。dataset検証のみで、Judge実評価ではない。
- `python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v` — PASS 27 tests。
- `python3 -m unittest discover -s tests/skills/evals/semantic -v` — PASS 13 tests。
- `python3 -m unittest discover -s tests/skills/evals/trigger -v` — PASS 1 test。trigger dataset検証のみ。
- 対象Python 16 filesへ`uv tool run --from ruff==0.16.8 ruff check ...` — PASS。`ruff format --check ...` — PASS 16 files。
- `uv run --no-project --with ruff==0.16.8 python3 scripts/format_tracked.py check` — PASS 221 tracked files。
- 対象Python 16 filesへの`python3.11 -m compileall -q ...` — PASS。
- `uv tool run --from 'git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref' skills-ref validate skills/<name>` — coverage-analysis、e2e-test-selection、test-analysis、test-case-design、test-condition-design、test-requirement-designの6 SkillすべてPASS。
- Plan追記前に行った`git status --short`、`git diff --stat`、`git diff --check`、`git ls-files --others --exclude-standard` — いずれも差分なし。その後のPlan追記で本Markdownだけが変更された。追記後は固定Ruff 0.16.8を使う`format_tracked.py check`（221 files）と`git diff --check`がPASS。

### 最新GitHub Actions（PR head `870c911ab76dab915a06c3b1e92b6771a1bd1d3b`関連）

| Workflow                            |  run | 結果 | 詳細                                                                                                                          |
| ----------------------------------- | ---: | ---- | ----------------------------------------------------------------------------------------------------------------------------- |
| Code Quality                        |  881 | PASS | tracked formatter／lint／差分検査を含むjob完了。                                                                              |
| Validate Agent Skills               | 2188 | FAIL | `Validate Agent Skills specification` PASS。`Validate repository eval structure` FAILし、READMEに`e2e-test-selection`未登録。 |
| Validate Deterministic Output Evals | 2186 | PASS | deterministic dataset／compile／shared・repository test／runtime／semantic dataset検査を含むjob完了。                         |
| Validate Semantic Output Evals      | 2151 | PASS | semantic datasetとshared/repository runtime tests。実LLM Judge評価ではない。                                                  |
| Codex Harness                       |  881 | PASS | Hook/config/execpolicyと公式validatorのcontract job。実Agent発火・fresh session受入とは別。                                   |

runはPR head `870c911...`に関連付いているが、Validate Agent Skillsのjob logで実際にcheckoutしたrefはPR synthetic merge commit `40ce0fec6b79049f3979bd7450b17b349869a1ed`（base `0e996171918cd9b2b7b0e0bc2b2de5bc3f98066c`とhead `870c911...`のmerge）だった。したがってPR Actionsをbranch単体HEADでの直接実行と同一視しない。CIの失敗原因はREADMEのみとログで確定しており、E担当branchでは共有READMEを変更しない。

### 実Agent／Judge／providerを実施していない理由と再開条件

- Codex CLIは`codex-cli 0.167.0`。repositoryの`.agents/skills/`にE評価対象のQA Skillsは登録されておらず、`codex exec --json`のSkill発火traceを取る正規trigger runnerもない。現在の`skills/*/evals/trigger`はdatasetのみ。2026-11-10に`codex --no-daemon --strict-config --sandbox read-only`でinteractive sessionの起動を試みたが、この実行端末は`TERM=dumb`かつstdin/stderrがTTYではないため、Codexは確認promptの前に終了した。fresh sessionの`/hooks`、実際のSkill load log、既存CLI認証状態は未確認で、Agent試行・発火結果は未実施として扱い、PASS／FAILを付けない。認証情報は読まず、起動・認証の迂回もしていない。
- 変更対象のsemantic manifestは、e2e-test-selection 3件、test-analysis 7件、test-requirement-design 3件、test-condition-design 14件、test-case-design 2件、coverage-analysis 2件（合計31 cases）。`scripts/skills/evals/semantic/run.py`は既に生成済みcandidate outputを要求し、repositoryには実外部Judge adapterがない。現在のreference文章をcandidate outputに転用せず、実Judge結果は未実施。
- Python `test-condition-design`／coverageとE2E selectionのlocal runtime結果は保存・readback・approval・CASを行わない。E artifactsを登録する共有runtime/provider契約と認証済み保存先が用意されていないため、実provider・別session再開は未実施。SQLite/WCAG fixture providerをE formal/E2E persistenceの証拠に流用しない。
- 再開条件：①PR #22/A ownerが正式design／E2E selectionの登録済みsource/artifact参照、Machine Entity、承認、native create/CAS/readbackを公開、②TTYを備えた承認済み実Agent環境で`codex --no-daemon --strict-config --sandbox read-only`をrepo rootから起動し、fresh sessionの`/hooks`でrepository-owned hookを確認、全current Skillを同時利用できるowner-approved trigger harnessとskill-load traceを用意、③実際のcandidate generationを行うLLM Judge adapterと独立rubric実行先を接続。開始後はE2E trigger train／validation各3回と未使用holdout、semantic 31 candidate outputs、provider失敗・競合・stale後再開を実測して結果を追記する。`codex exec --json`単独は現状Skill登録・発火traceを満たさないため、正規harnessなしで評価済みにしない。

### 残件・PR #22への引継ぎ

- PR #22統合owner：共有READMEのcanonical Skill一覧・routingへ`e2e-test-selection`を登録し、他canonical一覧と件数／名前を合わせる。shared ASSERTIONSでRISK-D016／D017とE2E-SEL-D001〜D006の正本・重複を整理し、legacy `test-analysis`のE2E表／既存E2E直接入口を残す。修正後にValidate Agent Skillsの全stepを再実行し、READMEチェックを含めPASSを確認する。
- A／共有runtime owner：formal-design recordとE2E selection recordのsource/artifact ref、revision、scope、currentness、Machine Entity登録、承認、native create-if-absent／CAS、exact historical readback契約を公開し、認証済み保存先を接続する。共有README／providerはE branchで変更しない。
- PR #22統合後：B/C/D/F正規成果物を用いたID／revision／Authority／scope照合、stale伝播と別session再開、E formal→coverageおよびE2E selection→G/H/J接続を行う。S1〜S17、人間編集8ケース、開発連動QA15条件、QA全工程10条件は全体統合で判定し、今回のfixture/local PASSで代替しない。
- PR #27全体はREADME失敗、実Agent/Judge/provider、横断接続が残るため受入未完了。PRはDraftのままとし、この作業でGitHub PR本文を変更しない。

### push後の最新commit・Actions

- 2026-11-10に担当Planのみをcommit `37a4f63d6f621b683cc44a3529433b2bd65b3175`（`docs: record PR #27 remaining acceptance blockers`）へ記録し、branch `feat/pr22-e-formal-design-e2e-selection`へ通常pushした。push後のlocal HEAD、`git ls-remote`のremote HEADは同一SHAで、worktreeはclean。実装コードは変更していない。
- 対象commitに紐づく最新PR Actions：Code Quality run 885 PASS、Validate Deterministic Output Evals run 2190 PASS、Validate Semantic Output Evals run 2155 PASS、Codex Harness run 885 PASS（Linux `codex-contract`／Windows `windows-launcher`ともPASS）、Validate Agent Skills run 2192 FAIL。
- Validate Agent Skillsのjob `validate`では`Validate Agent Skills specification` PASS、`Validate repository eval structure` FAIL。実行logはPR synthetic merge `2822986b98fb229f6d6eed1a954e5f95e0fb954c`をcheckoutし、READMEのcanonical一覧に`e2e-test-selection`がないため停止した。PR ActionsのPASSは実Agent発火・semantic Judge・実providerの受入を示さない。
- PR APIで再確認：PR #27はopen／Draft、base `feat/development-qa-traceability`、head `37a4f63d6f621b683cc44a3529433b2bd65b3175`。PR本文は旧状態のままで、この作業では変更していない。次回はREADMEをPR #22統合ownerが修正した後にValidate Agent Skillsを再実行し、本Plan記載の実Agent／Judge／provider条件は別途owner-approved環境が接続した後に再開する。

### 2026-11-10の最新Plan commit・Actions確認

- 上記Actions確認を記録したPlan-only commit `c24be2f3c6e1f26d56d73523a8544257169cd4e6`（`docs: record PR #27 post-push checks`）を同branchへ通常pushした。push後のlocal HEADとremote HEADは一致した。
- このcommitに紐づくActions：Code Quality run 887 PASS、Validate Deterministic Output Evals run 2192 PASS、Validate Semantic Output Evals run 2157 PASS、Codex Harness run 887 PASS（`codex-contract`と`windows-launcher`）、Validate Agent Skills run 2194 FAIL。
- Validate Agent Skillsはjob `validate`の`Validate repository eval structure`でFAILし、ログの不一致はREADME canonical一覧に`e2e-test-selection`がないこと。公式Skill仕様検証はPASS。実際のcheckoutはsynthetic merge `e464fcf373aac894f7b31db89ecd09b2975b647e`（head `c24be2f...`とbase `0e996171918cd9b2b7b0e0bc2b2de5bc3f98066c`）で、branch-only検証ではない。
- 現時点のPR API状態：PR #27はopen／Draft、base `feat/development-qa-traceability`、head `c24be2f3c6e1f26d56d73523a8544257169cd4e6`。PR本文は未変更。次のPlan-only同期commit自体のCIはpush後に別途確認し、完了扱いせず最終報告へ記録する。

### 2026-11-10の最新HEAD確認

- 担当Planの前回同期後に作成したdocs-only commit `794f6bcb8f1b6842c420df50ff589d1dceef5cf6`を通常pushし、local／remote HEADが一致した。実装コードに差分はない。
- 対象HEADに紐づくPR Actions：Code Quality run 888 PASS、Validate Deterministic Output Evals run 2193 PASS、Validate Semantic Output Evals run 2158 PASS、Codex Harness run 888 PASS（`codex-contract`／`windows-launcher`）、Validate Agent Skills run 2195 FAIL。
- Validate Agent Skillsは`Validate Agent Skills specification` PASS、`Validate repository eval structure` FAIL。job logの実checkoutはsynthetic merge `763a899989296439bb3c88f970c4c0bc43c0b93e`で、READMEのcanonical一覧に`e2e-test-selection`がないという同じ原因を確認した。
- この追記を含む次のPlan-only commitのCI状態は、push後に別途確認して最終報告へ記録する。GitHub PR本文は変更しない。PR #27はDraft／受入未完了を維持する。

## 2026-11-10 実Agent・Judge評価の最新進捗

### 対象HEADと実Agent起動

- 評価開始時のbranch HEADは`bda79aabad951dc5a1550b64685c92b5a03aed4b`。評価データ・deterministic contract test・本Planをcommitした`6c3e9f1e8c1e848fdec716e7f17395a75d42bda6`（`test: complete E2E semantic and trigger fixtures`）を通常push済み。PR #27はopen／Draft、base `feat/development-qa-traceability`、head `6c3e9f1...`。PR本文は旧状態だが変更していない。
- `codex --version`は`codex-cli 0.167.0`。`codex exec --help`、`codex login --help`、`codex login status`を確認し、状態表示は`Logged in using ChatGPT`。token、`auth.json`、API keyは読まず、ログへ出していない。
- `codex --no-daemon --strict-config exec --json --sandbox read-only --ephemeral -C <repository> "このリポジトリの構成を確認し、利用可能なSkillを説明してください。ファイルは変更しないでください。"`を実行し、exit 0、`turn.completed`、42 JSONL events、36 command eventsを確認した。traceにskill-load eventはなく、QA Skillを読み込むcommandも観測しなかった。このsmokeはCLI起動の証拠で、trigger判定には数えない。
- `skills/*/SKILL.md`からcurrent Skillは24件。作業rootの`.agents/skills/`には`code-review`、`feature-plan`、`repair-loop`のみがあり、QA Skillを利用できる評価環境を作る必要がある。`git worktree add --detach /tmp/pr27-e-formal-agent-eval-bda79a HEAD`はPreToolUseに`approval required by policy, but AskForApproval is set to Never`で拒否された。Hook／sandbox／execpolicyの迂回はしていない。
- このため、train／validation各queryをfresh Agent sessionで3回ずつ、未使用holdout、legacy selection参照、Skill load観測まで満たすtrigger実評価は未実施。発火率をPASS／FAILとしていない。再開条件はapproval-capable environmentで隔離worktreeを作成し、全24 current Skillを同時登録してskill-load traceを取得できること。

### Trigger datasetの規定件数と検証

- `e2e-test-selection`のtrigger trainは12件（positive 6／negative 6）、validationは8件（positive 4／negative 4）に確定した。既存queryの文言・期待値は変更せず、未使用queryを重複なく追加した。`test_new_skill_contracts`に件数・balance・一意性・split間非重複の回帰テストがある。
- train追加は技術非依存のE2E価値、TC直接指定、Playwright実装可否、validation追加はcurrent selection再利用と`test-analysis` Product Risk専用依頼との区別を扱う。既存E2E実行queryは従来fixtureで維持する。
- `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v` — 43 tests PASS。`python3 -m unittest discover -s tests/skills/evals/trigger -v` — 1 test PASS。これはdataset契約の検証で実Agent発火率ではない。

### 実candidate生成・独立Judge

- 対象はsemantic manifestの6 Skill／31 cases（E2E selection 3、test-analysis 7、test-requirement-design 3、test-condition-design 14、test-case-design 2、coverage-analysis 2）。現在の入力で16／31件について実Agent candidate生成とJudgeを完了した：`E2E-SEL-SEM-001..003`、`RISK-SEM-001..007`、`TR-SEM-001..003`、`TCN-SEM-001..003`。その他15件は未生成／未Judgeであり、完了扱いしない。
- Candidate generationはCodex CLI 0.167.0のfresh `codex exec --json --sandbox workspace-write --ephemeral`をcaseごとに起動し、実際のSkill文書、guidance、template、評価inputを使った。reference文章やJudge結果をcandidate outputとして流用していない。E2Eの3件はfixture更新後に再生成し、reference／rubricは変更していない。最初のTCN-SEM-002 runは20分timeoutでcandidateとして数えず、isolated packageによる再試行がexit 0、turn.completed、候補出力ありで完了した。
- 16件のJudgeはそれぞれ別のCodex `exec` sessionで実行し、既存`scripts/skills/evals/semantic/run.py --judge-command ...`と`normalize_judge_response()`を使用した。Codex `--output-schema`でcriterion JSONを要求し、Judge実行エラーを正常結果へ変換していない。生成とJudgeは同じ既定Codex設定／model familyのため、独立sessionではあるがmodel独立性はない。model IDはJSONLから取得できなかった。
- 実Judge結果16件：pass 12、needs_review 4、fail 0、not_evaluable 0、Judge実行エラー0。criterion単位はpass 52、needs_review 4。詳細入力・candidate・raw response・Agent/Judge JSONL・criterion根拠は[semantic証拠index](evidence/semantic-2026-11-10/evidence-index.json)と`semantic-evidence-v1.tar.gz`に保存する。
- v2の6件（RISK 5件、TR 1件）は6c3 commit前に生成されたが、評価input byte hashとSKILL/guidance/templateは現在のsourceと一致した。これらのpackage copyにはeval filesも存在した。Agent traceにはreference／rubricの内容を読むcommandが見つからず、`rg --files`によるfile名一覧だけを確認した。ただしfilesystem isolationはv5/v6より弱いため、証拠bundleで区別した。v4/v5/v6の生成は6c3 sourceで、E2EとTCN-SEM-002のpackage copyから`evals/`、tests、pycacheを除外した。

#### needs_reviewの確認

- `RISK-SEM-002`：主要利用者経路のリスクは示すが、入力に表示内容・具体遷移がないためテスト重点をこれ以上具体化できていないとのJudge評価。技術固有の経路を推測しない既存契約とreferenceの意図の照合が必要で、実装不具合とは断定していない。
- `RISK-SEM-005`：発生可能性を統計確率でなく複雑性・新規性等のproxyで評価するguidanceに対し、Judgeが実分布・発生率の数値を要求した。出力は低信頼を明記するが、rubricとguidanceの期待差を確認するまで仕様変更しない。
- `TCN-SEM-001`：許可境界1／50文字のcoverage itemは境界内であることを示すが、保存成功／一覧反映は別TCNのitemで扱われ、境界値と成功結果の組合せがないとのJudge評価。境界判定と状態遷移を別pairで扱う既存契約との関係を要確認。実装validatorの不具合とは断定していない。
- `E2E-SEL-SEM-003`：selection ID／revision履歴は維持し、新しいTI-003 candidate IDも追加したが、TI-003のimmutable revision tokenがinputにないためAgentはblockedにした。inputはTI-003をcurrentなREQ-ORDER-TRACKING revisionに基づくと述べる一方、正式設計ではTI-003自体のrevision/currentness値がない。referenceは候補追加を期待するため、revision tokenを推測してinputを変更せず、fixtureまたはsource identity契約の確認事項として保留する。

### 現在のHEADで再実行した局所検証

| コマンド／検証                                                                                                                                       | 結果                                         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `python3 -m unittest tests.skills.runtime.test_test_condition_structure -v`                                                                          | PASS 16                                      |
| `python3 -m unittest tests.skills.runtime.test_formal_design_contract -v`                                                                            | PASS 22                                      |
| `python3 -m unittest tests.skills.runtime.test_coverage_analysis_traceability`                                                                       | PASS 28                                      |
| `python3 -m unittest tests.skills.runtime.test_e2e_selection_contract -v`                                                                            | PASS 32                                      |
| `python3 -m unittest tests.skills.runtime.test_test_requirement_structure -v`                                                                        | PASS 11                                      |
| `python3 -m unittest tests.skills.runtime.test_case_structure -v`                                                                                    | PASS 11                                      |
| `python3 -m unittest tests.skills.runtime.test_case_runtime_v1_cutover -v`                                                                           | PASS 2                                       |
| `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v`                                                                   | PASS 43                                      |
| `python3 scripts/skills/evals/semantic/validate.py`                                                                                                  | PASS 24 Skills／168 cases（dataset構造検証） |
| `python3 -m unittest discover -s tests/skills/evals/semantic -v`                                                                                     | PASS 13                                      |
| `python3 -m unittest discover -s tests/skills/evals/trigger -v`                                                                                      | PASS 1（dataset契約のみ）                    |
| `python3.11 -m unittest tests.skills.runtime.test_e2e_selection_contract.E2ESelectionContractTests.test_runtime_runs_from_an_isolated_skill_copy -v` | PASS 1、Python 3.11.17                       |

- 6c3 HEADでの前回repository-wide deterministic testsは299件中295 PASS／4 FAIL。失敗はSQLite/WCAG providerのatomic reread、WCAG canonical-planのrevision/context、persisted owner runtime result、saved current WCAG planのQA workflow CAS/read reread。最後はProject Context state-root source欠落。今回の変更はtrigger dataとeval fixtureで、これら共有経路への変更はない。
- 6c3 HEADでの前回全runtime suiteは579件中560 PASS／10 FAIL／9 ERROR。FAILにはshared `ci_handoff` JSON nesting error 1件とSQLite history provider関連9件、ERROR 9件はSQLite `unable to open database file`。共有owner処理を変更せず、E担当branchで再現した担当runtimeは上表どおりPASS。
- `python3 -m unittest discover -s scripts/skills/evals/deterministic/tests -v`はPASS 12、`python3 -m unittest discover -s tests/skills/evals/deterministic -v`は前記FAIL 4件、`python3 -m unittest discover -s scripts/skills/evals/semantic/tests -v`はPASS 27。`python3 scripts/format_tracked.py check`はdprint 0.55.2で221 files PASS、変更testに対するRuff 0.16.8 check／format checkもPASS。Planと新証拠indexの追加後はformatterを再実行する。

### PR #22／provider／Actionsの現状

- PR #22はopen、head `0e996171918cd9b2b7b0e0bc2b2de5bc3f98066c`。branch READMEは`e2e-test-selection`をcanonical listへ登録していない（blob `f2d255f32c644114cb77005970a36b0ee20ad771`）。ASSERTIONS blob `6f2e078ae548bcaac4c51c11a8f87aec33419bbf`にはlegacy RISK-D016／D017があり、E2E-SEL-D001..D006は未登録。A runtime plan blob `9a09ff37980a7f12ebc83f4c506299c9fe2b5401`にE formal/E2E artifact registrationはない。共有ファイルとproviderは変更しない。
- 6c3 HEADに紐づくActions：Code Quality run 905 PASS、Validate Deterministic Output Evals run 2210 PASS、Validate Semantic Output Evals run 2175 PASS、Codex Harness run 905 PASS、Validate Agent Skills run 2212 FAIL。後者の`Validate Agent Skills specification`はPASS、`Validate repository eval structure`はREADMEのcanonical listにE2E skillがないためFAIL。Actionsは現在のuncommitted評価結果や実Agent/Judgeを評価しない。
- local runtimeは実provider保存・approval・CAS・独立readback・historical read・別session再開を実施しない。共有providerが現PR #22にないため未実施であり、fixtureやSQLite/WCAG providerをE artifact保存証拠へ転用しない。

### 現在の受入と次の作業

- E担当局所受入は未完了。trigger実Agent発火評価はworktree作成がHookに拒否され未実施。semantic 16／31件は実生成・Judge済みだが15件が残る。4 needs_reviewは記録どおり保持し、実装不具合・rubric誤り・入力不足を未確定のままにしない。provider保存・readbackは共有契約未接続で未実施。
- 現在`agent-v7`でTCN-SEM-004のcandidate generationを試行中。まだturn.completedなしで、Judge対象・PASSへ数えていない。完了またはtimeoutを記録後に残りのTCN／TC／coverage casesを続け、各完成candidateへ既存`run.py`の独立Judgeを適用する。
- A担当／PR #22統合ownerへ、E artifact registration、承認済みprovider、CAS/readback/historical read/stale propagation/別session再開を引き継ぐ。PR #22統合ownerへはREADME canonical list登録、ASSERTIONS D016/D017とE2E-SEL-D001..D006整理、legacy `test-analysis`互換性、Validate Agent Skills再実行を引き継ぐ。
- 受入判断のため人間に確認が必要：`E2E-SEL-SEM-003`でTI-003のimmutable revision/currentnessをどの上流成果物から得るか、またはこのfixtureの期待candidateをどう扱うか。未承認の推測でrevisionを作成しない。
- この節の根拠はsource HEAD 6c3で取得した検証とsemantic evidence v1。次のPlan/evidence commit SHAと、そのHEADの最新Actions結果はpush後に追記する。PR #27はDraftのままとし、本文は変更しない。

### 2026-11-10 semantic evidence v2追記

- source HEADは引き続き`6c3e9f1e8c1e848fdec716e7f17395a75d42bda6`。TCN-SEM-004のcandidate生成がCodex CLI 0.167.0で完了し、`turn.completed`、exit 0、候補出力、73 JSONL events、32 command eventsを確認した。所要1102.4秒。生成packageは`evals/`、tests、pycacheを含まない。
- Judgeは別のCodex `exec` sessionで既存semantic runnerと`normalize_judge_response()`を通し、TCN-SEM-004はpass（4/4 criteria、Judge errorなし）。raw response、Judge JSONL/stderr、normalized resultを保存した。生成とJudgeは同じ既定model familyで、model IDは取得できない。
- semantic評価は17／31 cases完了、pass 13、needs_review 4、fail 0、not_evaluable 0、Judge error 0。criterion集計はpass 55、needs_review 4。残り14件を完了扱いしない。v2 evidence archiveとindexは`evidence/semantic-2026-11-10/semantic-evidence-v2.tar.gz`、`evidence-index-v2.json`、`README.md`。16件版のarchive、index、READMEはv1履歴として保持した。
- TCN-SEM-004追加後も評価入力・reference・rubricを変更していない。4件のneeds_reviewと、E2E-SEL-SEM-003のsource revision確認事項は未解決のまま維持する。
- 実Agent trigger評価は、全current Skillを一時worktreeへ配置する`git worktree add`がHookに`approval required by policy, but AskForApproval is set to Never`で拒否されたため未実施。Hook/execpolicyを迂回しない。実provider、保存・承認・CAS・readbackも共有契約未接続で未実施。E担当局所受入は未完了。
- 6c3に対応するGitHub ActionsはCode Quality PASS、Validate Deterministic Output Evals PASS、Validate Semantic Output Evals PASS、Codex Harness PASS、Validate Agent Skills FAIL（repository eval structureがREADME canonical listのE2E登録不足で失敗）。PR #27はopen／Draft。PR本文は未変更。
- 今回の文書・証拠のcommit／pushは未完了。作業環境からの直接Git branch確認がHookに拒否されたため状態を再確認中。変更は担当Planとsemantic evidenceのみで、追加コード変更はない。次はformatter／差分・secret scan、branch/remote再確認、許可された場合の明示ファイルstage・commit・通常push、push後Actions再取得を行う。

### 2026-11-10 commit・push後の状態（69ab542）

- Planとsemantic evidence v1/v2をcommit `69ab5429a274e93c5e9648de1489f6fb3247eb89`（`eval: record PR #27 agent and judge evidence`）として担当branchへ通常pushした。push前に`git fetch origin`と`git merge-base --is-ancestor origin/feat/pr22-e-formal-design-e2e-selection HEAD`が成功。localとremote branch headは同SHA、`git status -sb`はclean。
- commit 69ab542に対するActionsはCode Quality PASS（run 906）、Validate Deterministic Output Evals PASS（run 2211）、Validate Semantic Output Evals PASS（run 2176）、Codex Harness PASS（run 906）、Validate Agent Skills FAIL（run 2213）。これらPR workflowはsynthetic merge commit `32300054c722c76abbb28fbb8bf67dd920f86e2c`をcheckoutした。Agent Skillsの`Validate Agent Skills specification`はPASS、`Validate repository eval structure`はFAIL。job logはREADME.mdに`e2e-test-selection`が欠けると明記。共有README/ASSERTIONSは変更しない。
- PR #27はopen／Draftで維持、GitHub本文は未変更。commit 69ab542時点のsemantic実評価は17／31、pass 13、needs_review 4、fail/not_evaluable/Judge error 0。trigger実評価は未実施、provider・保存・承認・CAS・readbackも未実施。
- 全current Skillのtrigger環境用worktree作成を、canonical quoted root形式の`git worktree add --detach /tmp/pr27-e-formal-agent-eval-69ab HEAD`で再試行した。Hookは`approval required by policy, but AskForApproval is set to Never`で拒否。Hook/execpolicy回避はしない。read-only Codex smokeはskill load traceを持たず、trigger評価の代替にはならない。
- 次の独立semantic generation run `agent-v8`を開始し、TCN-SEM-005を生成中。TCN-SEM-004を含め17件のみがJudge完了済みで、残り14件は未評価。起動中Agentが完了またはtimeoutした各caseを記録し、candidate完了後に別Judge sessionで判定してから継続する。
- GitHub Actions結果、remote一致、worktree拒否の証拠は2026-11-10の実行結果。新たなcommit後は、そのcommitに紐づくActionsを改めて取得する。

### 2026-11-10 commit bca5e9aeのCI

- PlanのCI追記commit `bca5e9ae9ced61a22ecaeca6ed027ced73e9083f`は担当branchへ通常push済み。local／remote head一致、working tree clean。PR #27はopen／Draft。
- このHEADのworkflowはsynthetic merge commit `858fbf1916c4c1e2d5f244f1d5bf3372f7c14f18`をcheckout。Code Quality run 907 PASS、Validate Deterministic Output Evals run 2212 PASS、Validate Semantic Output Evals run 2177 PASS、Codex Harness run 907 PASS、Validate Agent Skills run 2214 FAIL。
- Agent Skillsのvalidator jobでは`Validate Agent Skills specification` PASS、`Validate repository eval structure` FAIL。失敗点はPR #22のREADME canonical Skill catalogに`e2e-test-selection`が欠けていること。共有README／ASSERTIONSは変更せず、PR #22統合ownerへ引き継ぐ。
- semantic Agent-v8はこのPlan追記前からTCN-SEM-005を生成中。生成完了／timeoutと別Judgeを確認後、次の結果を証拠化して保存する。今は17／31件が実生成・Judge済みで、残14件は未完了。

### 2026-11-10 semantic evidence v3追記

- `agent-v8`が`TCN-SEM-005`を生成し、exit 0／`turn.completed`／candidateありを確認。elapsed 744.4秒、115 JSONL events、54 command events。eval packageから`evals/`、tests、pycacheは除外した。実行時のbranch source HEADは`69ab5429a274e93c5e9648de1489f6fb3247eb89`。後続の文書だけのcommitでSkill/input内容は変わっていない。
- 既存`run.py --judge-command`と独立Codex Judge sessionで判定し、`normalize_judge_response()`を通した結果はpass、4／4 criteria、Judge errorなし。raw Judge応答・JSONL・stderrと正規化結果を保存した。
- semanticの実生成・Judge累計は18／31件、pass 14、needs_review 4、fail／not_evaluable／Judge error 0、criterion statusはpass 59／needs_review 4。新しいarchive/indexは`evidence/semantic-2026-11-10/semantic-evidence-v3.tar.gz`、`evidence-index-v3.json`、`README.md`。v1・v2のbundleとindexは変更せず保持。
- `agent-v8`はTCN-SEM-005判定後に停止。remaining 13 casesは未評価で、実施可能なため引き続き生成・Judgeを続ける。4 needs_reviewとE2E-SEL-SEM-003のTI-003 revision/currentness確認事項は未解決。
- commit `d5a91582563d2784a9f68888bfeef55448e890c7`に紐づく最新ActionsはCode Quality run 908 PASS、Validate Deterministic Output Evals run 2213 PASS、Validate Semantic Output Evals run 2178 PASS、Codex Harness run 908 PASS、Validate Agent Skills run 2215 FAIL。PR jobはsynthetic merge `227fd6ae2e505b76aa7b6785c710b6288a380cd4`をcheckout。失敗job `validate`の`Validate repository eval structure`はREADME canonical listに`e2e-test-selection`がないと報告し、`Validate Agent Skills specification`はPASS。
- このPlan更新とv3 evidence fileは未commit。次は明示したPlan／README／v3 index／archiveだけをstageし、差分・formatter・秘密情報scan後にcommit・通常pushする。local/remote一致とそのcommitに紐づくActionsを再確認する。

## 実Agent・semantic評価の再実施（2026-11-10、進行中）

### 対象状態とE2E trigger dataset

- 開始時のPR #27 branch HEADは`bda79aabad951dc5a1550b64685c92b5a03aed4b`。PR #27はopen／Draft、baseは`feat/development-qa-traceability`。PR本文は「実装コード未追加」とする古い本文のままで、この作業では変更しない。
- `EVALS.md`の通常Skill件数に対し、`e2e-test-selection`のtrainは8件（4 positive／4 negative）、validationは6件（3／3）だった。既存queryと既存期待値を変更せず、trainへ2 positive（技術非依存の価値選定）と2 negative（TC直接指定、Playwright実装可否だけの依頼）、validationへ1 positive（候補の価値順位付け）と1 negative（`test-analysis`のProduct Riskだけの依頼）を追加した。current selection再利用と既存E2E実行は既存queryで維持する。
- `tests/skills/evals/deterministic/test_new_skill_contracts.py`の`test_e2e_selection_trigger_examples_are_well_formed_and_disjoint`はtrain 12件／6:6、validation 8件／4:4、各分割内一意性・train/validation非重複を固定する。Agent trigger評価より前にdatasetを確定した。query／期待値はAgent結果を見て変更していない。
- `python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts -v` — 43 tests PASS。datasetを最終確定した後のrepository-wide deterministic runでも本moduleのE2E trigger contractはPASSした。`python3 -m unittest tests.skills.evals.deterministic.test_new_skill_contracts.E2ESelectionDeterministicContractTests.test_e2e_selection_trigger_examples_are_well_formed_and_disjoint -v` — 最終datasetでPASS。`python3 -m unittest discover -s tests/skills/evals/trigger -v` — 1 test PASS。

### 非対話Codexの実行とtrigger評価のblocker

- `codex --version` — `codex-cli 0.167.0`。`codex exec --help`で`--json`、`--sandbox`、`--ephemeral`、`--output-schema`を確認。`codex login --help`と`codex login status`を実行し、状態表示は`Logged in using ChatGPT`。credential file、token、API keyは読んでいない。
- 次のread-only smokeを実行した：`codex --no-daemon --strict-config exec --json --sandbox read-only --ephemeral -C <repository> "このリポジトリの構成を確認し、利用可能なSkillを説明してください。ファイルは変更しないでください。"`。exit 0、JSONL 42 events、`turn.completed`あり、`command_execution` 36件。イベント型に明示的なSkill load eventはなく、10件のSkill文書参照commandも`e2e-test-selection/SKILL.md`を読んでいない。これはCLI起動確認であり、trigger評価結果ではない。生JSONLは`/tmp/pr27-agent-smoke.HN1gmt/events.jsonl`に保存した。
- repositoryには`skills/*/SKILL.md`でcurrent Skillが24件ある一方、実行rootの`.agents/skills/`は`code-review`、`feature-plan`、`repair-loop`の3件だけで、QA Skill 24件すべてが未登録。全current Skillを置く評価worktreeを作るため`git worktree add --detach /tmp/pr27-e-formal-agent-eval-bda79a HEAD`を試したが、PreToolUseが`approval required by policy, but AskForApproval is set to Never`で拒否した。承認要求、Hook、sandbox、execpolicyの迂回はしていない。
- そのため、元query・全Skill同時登録・queryごとの独立session・3回反復・Skill load観測を満たす正規trigger測定は未実施。train／validation発火率、未使用holdout、legacy selection参照の測定をPASS／FAILと扱わない。再開には承認可能な環境で同branch HEADの一時worktreeを作り、24 current Skillを`.agents/skills/`へ複製し、fresh `codex --no-daemon --strict-config` sessionでHook dispatchとSkill load traceを観測してから、各queryを3回ずつ実行する必要がある。

### semantic candidate生成・Judgeの進捗

- 対象manifestは6 Skill、31 cases（E2E selection 3、test-analysis 7、test-requirement-design 3、test-condition-design 14、test-case-design 2、coverage-analysis 2）。候補生成は`codex-cli 0.167.0`のfresh `codex exec --json --sandbox read-only --ephemeral`をcaseごとに起動し、各caseの`SKILL.md`、guidance、output template、`input.md`だけを入力した。`reference.md`、`rubric.json`、採点結果は生成側へ渡していない。生成中の出力・event JSONLは`/tmp/pr27-semantic-20261110/`へ保存している。
- このPlan追記時点で13／31 casesの実candidateが生成済み。13件すべてCLI exit 0、`turn.completed`あり、candidateファイルあり。これはsemantic Judge結果ではなく、全case完了にも達していない。CLI JSONLはmodel名を返さないため、model識別子は未確認。生成・Judgeで同じ既定Codex設定を使う場合は同一modelの可能性と限界を評価結果に記録する。
- Judgeは未実行。既存`run.py`の`--judge-command`を使う一時Codex CLI adapterを用意し、Judgeごとに別のread-only `codex exec` sessionを起動する。rubric responseは`--output-schema`でJSON構造化し、最終判定は既存`normalize_judge_response()`に通す。候補生成が31件完了後、31件の実判定とcriterion evidenceを保存し、終了・失敗・timeoutを個別に集計する。

### 現在HEADでの関連検証

- E担当runtime: E2E selection 32 PASS、formal design 22 PASS、test-condition 16 PASS、coverage analysis 28 PASS、test-requirement 11 PASS、test-case 11 PASS、case runtime v1 cutover 2 PASS。deterministic new-skill contracts 43 PASS。計165 PASS。
- semantic dataset validator: 24 Skills／168 cases PASS（dataset構造のみ）。semantic runtime tests 27 PASS、repository semantic tests 13 PASS。
- `python3 -m unittest discover -s tests/skills/evals/deterministic -v` — 299 tests中295 PASS／4 FAIL。失敗は`test_sqlite_provider_uses_atomic_revision_compare_and_reread`、`test_wcag_canonical_plan_is_immutable_per_revision_and_context`、`test_wcag_report_requires_persisted_owner_runtime_result`、`test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread`。前三件はSQLite/WCAG providerが`blocked`を返す既知共有経路、最後はProject Contextのstate-root source欠落。E担当の変更箇所とは独立した共有条件で、修正していない。
- Formatterはdprint 0.55.2で最終datasetを整形後に実行し、`python3 scripts/format_tracked.py check` — 221 files PASS。変更したPython testはRuff 0.16.8 `check`／`format --check`ともPASS。

### PR #22とproviderの現行確認

- PR #22はopen、head `feat/development-qa-traceability`／`0e996171918cd9b2b7b0e0bc2b2de5bc3f98066c`。このheadのREADMEに`e2e-test-selection`登録はなく、`scripts/skills/evals/deterministic/ASSERTIONS.md`（blob `6f2e078ae548bcaac4c51c11a8f87aec33419bbf`）にはlegacy `RISK-D016`／`RISK-D017`がある一方、`E2E-SEL-D001`〜`D006`の登録はない。共有ファイルは変更せずPR #22統合ownerへ引き継ぐ。
- 同headの`docs/implementation/pr22/A_runtime-integration.md`（blob `9a09ff37980a7f12ebc83f4c506299c9fe2b5401`）はworkflow verifier対象を6 Skillとし、未登録Skillを`unsupported_skill_verifier`でblockingにする。ローカルSQLiteのCAS／履歴／readbackは記載されるが、remote provider、承認主体、新設E Skillの正式登録・owner結果は未接続。E成果物の実provider保存・承認・CAS・historical read・independent readback・stale伝播・別session再開は実施できず、PR #22/A ownerの契約・provider接続後に再開する。
- bda79aabに対応する既存ActionsはCode Quality 890 PASS、Validate Deterministic Output Evals 2195 PASS、Validate Semantic Output Evals 2160 PASS、Codex Harness 890 PASS、Validate Agent Skills 2197 FAIL（README canonical listに`e2e-test-selection`がない）。今回の未commit dataset／test変更を含むCI結果ではない。pushできた場合は新HEADごとに再取得する。

### 受入状態

- E担当の局所受入は未完了。dataset件数、関連runtime、dataset validator、formatterはPASS。実trigger評価、31件のJudge評価、実provider保存・approval/CAS/readback、全runtime suite、今回変更後のGitHub Actionsは未完了または実行中のため完了扱いしない。
- 既知のPR #22引継ぎ（README／ASSERTIONS登録、E owner verifier／artifact registration、remote provider、横断source freshness・失敗後再開、実成果物、S1〜S17／人間編集8／15＋10条件）を維持する。PR #27はDraft、GitHub PR本文は変更しない。

### 2026-11-10 評価データ修正と実生成の追記

- E2E semantic case 001の最初のruntime-enabled candidateは、入力にTI-001／TI-002・TC-001・E2E-01のsource revision/currentnessがなく、両候補をblockedにした。referenceだけがcurrent sourceを要求していたため、`EVALS.md`のhidden requirement禁止に照らし、reference／rubricを変えずinputへfixtureのcurrent source・revisionとcomplete populationを追加した。
- E2E semantic case 002のinputへ「owner未割当」を追加した。依頼の不完全状態は維持し、ownerを架空の人物へ割り当てず、再開条件でowner割当を明示できるようにした。
- E2E semantic case 003のinputへrevision 1のcandidate ID/key・decision・rationale・source currentness・scope・population・retirementなし・runtime算出digestを追加した。digestはfixture整合性用で、provider真正性の証明としていない。reference／rubricは変更していない。これら3件は変更後inputで実Agent再生成とJudge再評価が必要で、まだ結果を付けていない。
- `python3 scripts/skills/evals/semantic/validate.py` — PASS、24 Skill／168 cases。変更後のcase入力を含むdataset構造検証である。
- runtimeを実際に許可した候補生成で、現行inputのRISK-SEM-001、003、004、005、006、RISK-SEM-002、007、およびTR-SEM-001の8/31件がCLI exit 0・`turn.completed`・candidate fileありで生成済み。以前の禁止runtime生成はdiagnostic扱いで、ここへ数えていない。`RISK-SEM-002`は739.2秒／15 command events、`RISK-SEM-007`は603.0秒／12 command events。候補は一時保存先`/tmp/pr27-semantic-20261110/agent-v{2,4}/`にあり、Judgeはまだ実行していない。model IDはCodex JSONLに出ず未確認。
- 現在は`TR-SEM-002`のruntime-enabled Codex turnを実行中であり、完了扱いしていない。生成timeoutの再試行を継続する。生成AgentとJudgeのCodex sessionは同時起動せず、後続Judgeは生成終了後に独立sessionで実行する。
- 次の作業：変更後E2E semantic 3件を再生成し、完了candidateへ既存`run.py`＋独立Codex Judge adapterを順次実行する。全31件を完了できない場合も、各caseをgenerated／timeout／Judge error／not evaluatedに区別して証拠を残す。
