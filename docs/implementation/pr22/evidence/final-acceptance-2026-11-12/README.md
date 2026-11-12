# PR #22 統合修正・最終受入の検証記録

最終更新：2026-11-13。作業開始時のHEADは`21cbdc5aea30b5748b33913f643b3f36cef60352`（A〜J統合済み）。

## 判定語

- **PASS**：条件の全範囲を証拠で確認した。
- **部分**：担当間の接続を実装し、実producerの出力を使うテストでPASSした。ただし実案件・実Agent・実provider等の証拠が一部足りない。残りを「残件」に書く。PASSとは扱わない。
- **FAIL**：実装・接続の欠落、または実Agentの評価で基準を満たさなかった。
- **blocked**：必要な外部入力（権限、承認、実案件source等）が無く検証できない。
- **未実施**：実施できるが今回は実施していない。

## 実行環境と前提

- WSL2 Linux 6.6.87.2、Python 3.12.3（CIは3.11）、Node v24.22.2、ruff 0.16.8、dprint 0.55.2、skills-ref `69ef37e`（CIと同じ固定版）。
- 実Agentの評価（意味評価の候補生成・Judge、trigger runner）は**Claude CodeのHaiku 5.5（`claude-haiku-5-5`）**で行った。候補生成とJudgeは別session・別contextだが同じモデルで、独立性は限定的である。AGENTS.mdが前提とするCodex（`codex --no-daemon --strict-config`）での受入は**未検証**。
- 保存先・承認・外部Issue・製品CIの方式は利用者が決定した（[判断の記録](./approval-packet.md)）。

## 1. 実施した修正と実装

| 区分            | 内容                                                                                                                                                                                                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 共有登録        | READMEの7 Skill未登録（Validate Agent Skillsの失敗原因）、`CANONICAL_SKILLS`、`ASSERTIONS.md`（`E2E-SEL-D001`〜`D006`ほか。`RISK-D016/D017`はlegacy互換と明記）、`qa-workflow`のrouting（担当表・開始点・修正routing・状態テンプレート）、routing fixture（`WF-UI-TARGET-*`の訂正と`WF-PROCESS-001`〜`014`） |
| owner verifier  | `qa-workflow/scripts/owner_verifiers.py`。登録は`test-item-analysis`、`test-condition-analysis`、`e2e-test-selection`、`test-reporting`。ownerの本番CLIを実行し、保存本文のhash・owner validator・source currentness（報告は再計算との一致）がそろう場合だけ完了対象にする。未登録は完了不可のまま           |
| 担当間接続      | B→D（`candidate_handoff`）、B→C（feature-indexが保存snapshotを検証）、D→E（`formal_design_sources`）、E2E選定→inspection（`inspection_handoff`と`E2E-INSP-D017`）、探索→欠陥候補（`defect_candidate_source`）、G／H／I→統合報告（各`reporting_records`）、G→H（`regression_source_execution`）               |
| 規則変更        | CRUD lifecycle sequenceに必須のoperationを状態を変えるC／U／Dに限定、`version_range`の片側境界を許可（利用者承認済み）                                                                                                                                                                                       |
| eval            | runtime行・`Runtime Skill`に使える名前を、完了検証が登録されたSkill・runtime unit生成Skillに限定                                                                                                                                                                                                             |
| Project Context | `qa.defect_issue_tracker_ref`を追加。未設定の案件は欠陥候補の整理までで完了                                                                                                                                                                                                                                  |
| Plan            | 承認方式（対話での同意＋認証済みpush＋activity APIによる実行者と前後SHAの読み戻し）を詳細02・08へ追加                                                                                                                                                                                                        |
| trigger runner  | `scripts/skills/evals/trigger/run.py`（Claude Code headless、隔離config、`Skill`ツール呼出しの観測、timeoutは無効試行として集計から除外）                                                                                                                                                                    |
| 意味評価データ  | 評価入力・参照解答を現行の正本に合わせて修正（rubricは変更しない）                                                                                                                                                                                                                                           |

担当間接続の証拠テスト：`tests/skills/runtime/test_cross_owner_*.py`（実Git store、実runner起動、実materialize、実選定packet、実Session）、`test_owner_verifier_registry.py`（12件）、`test_testware_regression_handoff.py`（11件）。

owner verifierを**登録していない**Skill：Markdownのみで検証入口を持たない`test-requirements-analysis`・`test-architecture-design`・`test-management`、保存成果物のreadback検証を持たない`defect-management`・`test-evaluation`・`feature-analysis`・`project-context`・`ui-target-analysis`等。未登録scopeは`unverified_scopes`として完了不可のまま残る。

## 2. CI

GitHub Actions（最終HEADの結果は§11）。ローカルのCI相当実行（LFのクリーン展開先で各stepを個別に実行）では、`test_ci_handoff`のJSON nesting失敗（ローカルPython 3.12起因。作業開始HEADでも同じ。CIの3.11ではPASS）以外はすべてPASS。

## 3. 実runner（qa-training-store 固定SHA `2a8bcf57ff091e84a8b3bf7b123568e967000d88`）

固定SHAをscratchpadへclone、`pnpm@10.34.5 install --frozen-lockfile --ignore-scripts`で依存を導入。選択集合は実行と別に取得。`skills/testware-execution/scripts/runner.py`をLinuxのchild subreaper＋procfs監督ありで実行。証拠は`runner/`（絶対pathは`<scratchpad>`へ置換）。

| 経路                         | 結果                                                                                                                                                                                                                  | 判定                              |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| Vitest unit 3件              | `runner_pass`。選択3件＝収集3件、process終了、workspace clean                                                                                                                                                         | PASS（runner契約）                |
| timeout・retry・cleanup      | 強制終了して`blocked_cleanup_or_timeout`。再試行せず、残存processなし                                                                                                                                                 | PASS                              |
| Web component（Vitest）3件   | `runner_pass`                                                                                                                                                                                                         | PASS（runner契約）                |
| Native component（Jest）4件  | cold実行（cacheを消す）は3回とも先頭テストが約9〜11秒でJestの既定5秒test timeoutとなり`runner_fail`、warm実行は3回とも0.7〜1.1秒で4件PASS（`runner/jest-repro.jsonl`）。jest-expoの初回変換コスト。製品不具合ではない | FAIL（cold実行で再現）            |
| G→H（実run）                 | 上記の実runをHへ投影。PASS／FAILは`完了`、timeoutは`実行中`                                                                                                                                                           | PASS（ローカル）                  |
| G→J（実run）                 | `reporting_records`で個別testを集計。timeout・fixtureはPASS／FAILにならない                                                                                                                                           | PASS（ローカル）                  |
| Playwright API-only          | 固定SHAにAPI専用specが無い                                                                                                                                                                                            | blocked（製品側testware無し）     |
| 静的解析                     | runnerは正規化済みreportをstdoutに要求。ESLint出力からのadapterが無い                                                                                                                                                 | blocked（G ownerのadapter未提供） |
| batch／event、非機能、直接TC | 対象testware、閾値と期待値の正本、承認済み正式TCが無い                                                                                                                                                                | blocked                           |
| Windows実行保証              | runnerはWindowsで`process_supervision_unavailable`として開始前に拒否する契約                                                                                                                                          | 未実施                            |

## 4. 実provider（Git）

承認済みの範囲（qa-training-storeの専用orphan branch `qa/artifacts`への通常push）。証拠：`provider/result.json`、実行script`provider/run_git_provider_acceptance.py`。

| 検証             | 結果                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| create-if-absent | 初回作成後の再作成を`create_if_absent_conflict`で拒否                                                        |
| revision履歴     | 3 revisionを保存し、それぞれ前revisionへつながる                                                             |
| 遠隔CAS          | 古い書き手のpushが非fast-forwardで拒否され、遠隔headは先行した書き手のまま。古い書込みは遠隔の履歴に入らない |
| 未承認書込み     | `access_denied`でblocked、ref不変                                                                            |
| 独立readback     | 新規cloneから3 revisionの内容hashが書込み時と一致。currentは最後に受理されたrevision                         |
| 承認主体         | GitHub activity APIの実行者`ryu-yoshikawa-pro-vision`と前後SHAの連鎖を確認（commitのauthorは使わない）       |
| activityの遅延   | push直後はactivityが取得できず、後から取得できた。承認の手順を再試行つきに改訂（詳細02）                     |

判定：**PASS**（Git providerのこの範囲）。権限取消・複数ホスト同時書込み・中断後の復旧は未検証。

## 5. 製品CI（保存先branchのref参照）

qa-training-storeの検証用Draft PR #221（mergeしない、branch `ci/qa-artifact-handoff-verification`）。workflowは保存先branchの固定commitと`qa-workflow-skills`の固定commitをcheckoutし、期待値を製品CI自身のGit objects（変更範囲、成果物のcommitとtrailer、内容hash）から導いて`ci_handoff.py`を実行する。証拠：`product-ci/`。

- 製品CI上で`QA artifact handoff verification`が成功（通常系`pass`、承認されたpusherの確認、負例3件：改ざん成果物は`fail`、分類が欠けた変更は不一致、未承認pusherは拒否）。
- 製品の既存`Web CI`は`Vitest (contracts)`の1件が失敗するが、mainでも同じテスト（Windows向け`codex-task-native-command`）が失敗しており本変更と無関係。初回は私のworkflowが製品repoの「remote actionを40文字のSHAで固定する」契約に違反して失敗したため、SHA固定へ直した。

判定：**PASS**（保存先branchのref参照による受渡し）。承認が必要な更新を`ci_handoff.py`が受理するprovider接続は、承認方式がGitHubのactivity APIのため`required_approvals`を空にして別stepで検証している。

## 6. 横断接続

| 経路                 | 判定   | 根拠・残件                                                                                                                                                  |
| -------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B → D                | 部分   | 実Git store保存→読み戻し→Dの実materializeを通す。残：実案件のfeature inventory                                                                              |
| B → C                | 部分   | feature-indexが保存snapshotの存在・retired・hash・revisionを検証。残：実案件の通し                                                                          |
| D → E                | 部分   | Dの実候補→`formal_design_sources`→Eの実validate。staleは要再検証。EのTI-*はEが採番し候補は自動採用しない。残：実案件、Eの意味評価                           |
| E2E選定 → inspection | 部分   | `inspection_handoff`と`E2E-INSP-D017`。実装・実行は引継ぎ対象をinspectionから受ける。残：実Playwright実行                                                   |
| 探索 → 欠陥候補      | 部分   | 実Session→`defect_candidate_source`→Jの実`assess_candidate`。対象buildと環境はCharter identityのhashを再現した値だけ。残：外部Issue（案件設定なしは対象外） |
| G／H／I → 統合報告   | 部分   | 実runner結果・Activity・Sessionから`reporting_records`→Jの実`build_snapshot`。残：実案件のsource inventory                                                  |
| F 要求→方式→計画     | 未実施 | 3 Skillに実行コードが無く（Markdownのみ）、owner verifierは未登録。実成果物の受渡しは未実装                                                                 |
| 保存先provider・承認 | PASS   | §4                                                                                                                                                          |

## 7. 実Agent・意味評価

### 7.1 意味評価の再実行（Haiku 5.5、評価データ修正後、11件）

PR #27で未解決だった11件を、現行HEADの評価データで再実行した（candidate：Haiku 5.5が`evals`を除いたSkillスナップショットだけを読んで生成、Judge：別sessionのHaiku 5.5、判定：repoの`run.py`）。証拠：`semantic/`（candidateのMarkdown出力は、repoのformatterでtableの空白だけを整えた。内容は変えていない。`prepare_semantic_run.py`が準備・Judge prompt作成・判定を行う）。

| Case            | 結果         | 内容                                                                                                                                                                                        |
| --------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E2E-SEL-SEM-003 | pass         | TI-003にrevisionを追加した入力で、候補は選定を適切に扱った                                                                                                                                  |
| COV-SEM-002     | pass         | 上流が無い監査で孤立と判定せず判定不能とした                                                                                                                                                |
| TC-SEM-001      | pass         | 修正した入力で成立                                                                                                                                                                          |
| TC-SEM-002      | pass         | 修正した入力で成立                                                                                                                                                                          |
| TCN-SEM-004     | needs_review | 候補が実際に`crud_matrix.py`を実行し`ready`（consistency 1/1）。4基準中3基準がpass、残る1基準（3つのpostconditionを1項目にまとめた点）がneeds_review                                        |
| TCN-SEM-012     | needs_review | 候補が全面blockedで、全4基準がnot_evaluable（referenceがblocked時の期待を持たない）。Judgeの応答は1回目が契約違反（`evaluable=false`のevidenceが空でない）で、記録して別sessionでやり直した |
| RISK-SEM-002    | fail         | 候補が仕様根拠の不足を理由に全面blockedとし、Product Riskと重点を出さなかった                                                                                                               |
| RISK-SEM-005    | fail         | 同上。定性的なLikelihood判断と技法選択を出さなかった                                                                                                                                        |
| TCN-SEM-008     | fail         | 候補がruntime入力の不足を理由に実行せず、Coverage Itemを1件も出さなかった                                                                                                                   |
| TCN-SEM-013     | fail         | 同上。merge groupの判定とconflict拒否をCoverage Itemにしなかった                                                                                                                            |
| TCN-SEM-014     | fail         | 閉鎖結果を条件・Coverage Itemへ展開せずblockedとした                                                                                                                                        |

pass 4／needs_review 2／fail 5。failの共通点は、**候補（Haiku 5.5）が仕様根拠・runtime入力の不足を理由に全面停止し、referenceが求める部分成果物を出さなかった**こと。`test-analysis`のguidanceは「根拠が不足しても低信頼度で評価し全体停止しない」としている一方、`test-condition-design`は入力契約が不足すると停止する。Skillの停止条件と部分成果物の期待の関係は、Eのownerが判断する事項として残す（rubricは変更していない）。この結果は、PR #27のCodex実行（pass 20 ／needs_review 8 ／fail 3）とは別の条件（モデル・評価データ）なので比較しない。

### 7.2 trigger評価

- 停止指示（E記録「切りのよいところで中断」）は、長時間評価について維持している。
- repo管理のrunnerを作成し、動作確認（1 Skill、各class 1 query、2回、4実行、約27秒）を行った。37 Skillを同時に利用可能にし、`Skill`ツール呼出しを観測できた。`defect-management`の肯定queryは2回とも発火せず（原因は未調査）、否定queryは`test-reporting`を2回読み込んだ（想定外発火）。
- **本実行は未実施**。新14 Skillのvalidation queryを各Skillの肯定・否定2件ずつ、3回、並列3で実行すると、56 query・168実行・約9分の見積もり。実行には利用者の承認を待つ。
- 以前の900秒timeoutの原因は未検証のまま。新runnerはquery単位のtimeoutを持ち、timeoutした試行を無効として記録し、発火率の集計から除外する（「発火しなかった」とは数えない）。

## 8. 完了条件の判定

### 開発連動QA Plan（15条件）

| #  | 判定   | 確認済み範囲・残件                                                                                      |
| -- | ------ | ------------------------------------------------------------------------------------------------------- |
| 1  | 未実施 | feature-analysisの契約・実Git store。残：実製品（qa-training-store）の全機能抽出                        |
| 2  | 未実施 | 残：実PR・merge・releaseの入力                                                                          |
| 3  | 部分   | 製品CI上で未分類・改ざん・未承認pusherの負例がPASS。残：Riskを踏まえたfail／warning／blockedの分類      |
| 4  | 部分   | ローカル契約。残：実案件データでの算出                                                                  |
| 5  | 部分   | B→D→E接続。残：§6の残件                                                                                 |
| 6  | 部分   | 機能ID・履歴の維持とstale伝播（D→E）。残：実案件                                                        |
| 7  | 部分   | 実GitHubの遠隔CAS・履歴・readback・承認主体。残：rebase・merge・release、権限取消、中断復旧             |
| 8  | PASS   | UI package・migration・legacy・routing fixtureの回帰                                                    |
| 9  | 部分   | Project Contextを実GitHubへ保存・承認・readback。残：実Q06の配置合意                                    |
| 10 | PASS   | 16節・stable key・DEC／ASM・互換テスト                                                                  |
| 11 | 部分   | 文書・CI登録・GitHub Actions全PASS。残：実製品相当の統合受入                                            |
| 12 | 部分   | 4 Skillの存在・routing・接続。残：実案件の通し                                                          |
| 13 | 部分   | itemとconditionの別ID・履歴、D→E採用経路。残：Eの意味評価                                               |
| 14 | FAIL   | 意味評価の実Agent再実行でRISK-SEM-002／005、TCN-SEM-008／013／014がfail、TCN-SEM-004／012がneeds_review |
| 15 | PASS   | 不足時にblockedへ倒す契約、CIが意味判断をしないこと                                                     |

### QA全工程Plan（10条件）

| #  | 判定    | 確認済み範囲・残件                                                                                     |
| -- | ------- | ------------------------------------------------------------------------------------------------------ |
| 1  | 未実施  | routing fixtureは固定。実Agentの発火は動作確認のみ（本実行は承認待ち）                                 |
| 2  | 部分    | E→coverage、D→E、G→H→J接続。残：F実成果物                                                              |
| 3  | blocked | F 3 Skillに実行コードが無く、owner verifier未登録（完了不可）                                          |
| 4  | 部分    | 探索→欠陥候補は接続。外部Issueは案件設定なしのため対象外。残：修正確認の実接続                         |
| 5  | 部分    | G／H／I→J投影とowner verifier（test-reporting）。残：実案件のsource inventory                          |
| 6  | 部分    | Jの評価runtimeのローカル契約。残：改善採用の承認と正本改版                                             |
| 7  | 部分    | Vitest・Web component・Native Jestを実runnerで確認。API-only・batch・静的解析・非機能・直接TCはblocked |
| 8  | 部分    | 共通契約・runtime・Regression、実Git provider。残：Activityの保存readback                              |
| 9  | 部分    | 人間編集8ケースのローカルPASSと実Git provider。残：承認済み配置の実運用                                |
| 10 | FAIL    | 実Agent評価にfailが残る。効率比較は未実施                                                              |

### 詳細Plan 01〜08

| 詳細 | 判定   | 理由                                                                                            |
| ---- | ------ | ----------------------------------------------------------------------------------------------- |
| 01   | 部分   | 実runner（Vitest・Web component・Native Jest・timeout）。API-only・batch・非機能・静的はblocked |
| 02   | 部分   | 実Git provider（CAS・履歴・readback・承認主体）。外部Issueは案件設定なしのため対象外            |
| 03   | 部分   | S1〜S17は下表                                                                                   |
| 04   | 部分   | owner verifierを4 Skillで登録。F 3 Skillなどは登録できず完了不可のまま                          |
| 05   | 部分   | owner振り分けとVitest個別結果の照合は実runnerでPASS。API-only・直接TCはblocked                  |
| 06   | 部分   | 静的解析のadapterが無い。探索・Knowledgeはローカル契約                                          |
| 07   | 未実施 | 5シナリオの実測が無い                                                                           |
| 08   | 部分   | 人間編集8ケースのローカルPASSと実Git provider                                                   |

### S1〜S17

| S   | 判定    | 根拠・残件                                                                      |
| --- | ------- | ------------------------------------------------------------------------------- |
| S1  | 部分    | Project Contextの保存・承認・readbackは実GitHubでPASS。残：実案件の配置合意     |
| S2  | 部分    | feature→item／condition→正式設計が接続済み。残：実PR／rebase                    |
| S3  | 部分    | E2E選定→inspectionが接続済み。残：実Playwright                                  |
| S4  | 部分    | runner→raw→cleanup→Activity→統合報告が実runで接続。残：非機能・直接TC           |
| S5  | blocked | F実成果物                                                                       |
| S6  | 部分    | 実Gitの遠隔CAS競合。残：承認失効・実行中断・取得失敗                            |
| S7  | 部分    | 探索→欠陥候補。外部Issueは対象外。残：修正通知と周辺Regression                  |
| S8  | 未実施  | 実外部資料の改版入力                                                            |
| S9  | 未実施  | merge commit・実build                                                           |
| S10 | blocked | 改善採用の承認と正本改版                                                        |
| S11 | 部分    | 未登録Skillは完了不可。登録済み4 Skillは検証済み成果物で完了。残：その他のSkill |
| S12 | 部分    | Vitest→route→実runner→Activityを実製品runでPASS                                 |
| S13 | blocked | API-only・直接TCの製品testwareとAuthority                                       |
| S14 | blocked | 静的解析adapter、2セッションの共有予約provider                                  |
| S15 | blocked | 改善の承認・計画改版                                                            |
| S16 | 部分    | 実Gitでのreadback。残：中断後の別セッション復旧                                 |
| S17 | 未実施  | 効率比較5シナリオ                                                               |

### 人間編集8ケース・効率比較

- 人間編集8ケース：ローカルのテストはPASS（B由来の機能ID検証を含めて18件）。全体経路は**部分**（残：承認済み配置の実運用）。
- 効率比較5シナリオ：変更前後の実Agent測定をしておらず**未実施**。手順と見積もりを提示し、承認後に実施する。

## 9. 総合判定

**PR #22の最終受入は未完了**。mainへのmerge条件は満たさない。残る主な条件は次のとおり。

1. 意味評価のfail 5件・needs_review 2件（Skillの停止条件と部分成果物の期待の関係をEのownerが判断）。
2. trigger評価の本実行（承認待ち）と効率比較5シナリオ。
3. F 3 Skillを含む、owner verifier未登録Skillの完了経路。
4. 実案件（実PR・merge・release、実Q06の配置合意、実Issue管理先の設定）での通し。
5. API-only・batch・静的解析・非機能・直接TC・Windowsの実行保証。
6. Codex（AGENTS.mdの前提runtime）での受入。

## 10. GitHub操作

- `ryu-yoshikawa-pro-vision`（repository ownerのアカウント）で通常push。force pushはしていない。mainへのmerge、PR close、release、tag操作はしていない。
- 製品repo qa-training-storeには、`qa/artifacts`（QA成果物のorphan branch）と、検証用Draft PR #221のbranchだけを作成した。製品コードは変更していない。

## 11. 最終HEADのGitHub Actions

最終HEADのCIはこの記録のcommit後に確認し、PR #22の本文に反映する。
