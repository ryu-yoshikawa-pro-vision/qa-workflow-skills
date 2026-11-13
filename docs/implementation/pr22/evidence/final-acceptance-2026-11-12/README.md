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

| 経路                         | 結果                                                                                                                                                                                                                                                                          | 判定                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Vitest unit 3件              | `runner_pass`。選択3件＝収集3件、process終了、workspace clean                                                                                                                                                                                                                 | PASS（runner契約）                                              |
| timeout・retry・cleanup      | 強制終了して`blocked_cleanup_or_timeout`。再試行せず、残存processなし                                                                                                                                                                                                         | PASS                                                            |
| Web component（Vitest）3件   | `runner_pass`                                                                                                                                                                                                                                                                 | PASS（runner契約）                                              |
| Native component（Jest）4件  | cold実行（cacheを消す）は3回とも先頭テストが約9〜11秒でJestの既定5秒test timeoutとなり`runner_fail`、warm実行は3回とも0.7〜1.1秒で4件PASS（`runner/jest-repro.jsonl`）。jest-expoの初回変換コスト。製品不具合ではない                                                         | FAIL（cold実行で再現）                                          |
| G→H（実run）                 | 上記の実runをHへ投影。PASS／FAILは`完了`、timeoutは`実行中`                                                                                                                                                                                                                   | PASS（ローカル）                                                |
| G→J（実run）                 | `reporting_records`で個別testを集計。timeout・fixtureはPASS／FAILにならない                                                                                                                                                                                                   | PASS（ローカル）                                                |
| Playwright API-only          | 固定SHAにAPI専用specが無い                                                                                                                                                                                                                                                    | blocked（製品側testware無し）                                   |
| 静的解析                     | ESLint（v9.39.2）のJSONを正規化するadapter（`static/eslint_adapter.py`）でrunnerを実行。対象2ファイルは`runner_pass`（実行済み・findings 0・対象完全）。存在しないpathを含む負例は`incomplete`（取得不完全）で、「指摘なし」にならない                                        | PASS（runner契約。adapterは受入用で製品repoには追加していない） |
| batch／event、非機能、直接TC | 対象testware、閾値と期待値の正本、承認済み正式TCが無い                                                                                                                                                                                                                        | blocked                                                         |
| Windows実行保証              | Windows 11のPython 3.12.0で`test_non_e2e_runner`を実行：44件中28件が失敗、4件skip。失敗は、runnerが`process_supervision_unavailable`でexit 2として開始前に拒否するため（子孫processを監督できない環境で実行しない契約どおり）。runnerはLinux専用で、Windowsでの実行保証はない | blocked（設計上Windows非対応。実行保証は作らない）              |

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

#### 7.1.1 評価データ補完後の再実行（2026-11-13、7件）

fail 5件・needs_review 2件は、評価入力にテスト要求ID・現在有効な仕様根拠・テストレベル・coverage_selection_reasonがなく、Skillが入力契約どおりに全面停止したことが原因だった。前回承認された方針（rubricは変えず評価データ側を直す）に従い、`RISK-SEM-002`／`005`、`TCN-SEM-008`／`012`／`013`／`014`の入力へ、不足していた要求ID・承認済みAuthority・テストレベルを補った（Skillの停止条件は変更していない）。`TCN-SEM-004`は入力を変えずに再実行した。candidateはHaiku 5.5、Judgeは別sessionのHaiku 5.5、判定は`scripts/skills/evals/semantic/run.py`。証拠：`semantic/rerun2/`。

| Case         | 結果 | 備考                                                                                  |
| ------------ | ---- | ------------------------------------------------------------------------------------- |
| RISK-SEM-002 | pass | 全4基準pass                                                                           |
| RISK-SEM-005 | pass | 全3基準pass                                                                           |
| TCN-SEM-004  | pass | 前回needs_reviewだった基準が今回はpass（同一入力の再実行。Judgeの揺らぎがありうる）   |
| TCN-SEM-008  | pass | 全5基準pass                                                                           |
| TCN-SEM-012  | pass | 全4基準pass                                                                           |
| TCN-SEM-013  | pass | 候補はBash権限の拒否でruntimeを実行できず未完成と明記したが、Judgeはpass（評価点は3） |
| TCN-SEM-014  | pass | 全4基準pass                                                                           |

11件すべてがpassになった。ただし、入力を補ったことで通っており、**元の（不足のある）入力でSkillが全面停止する挙動は変えていない**。この結果は、候補とJudgeが同じモデル（Haiku 5.5）である限定条件の証拠である。

### 7.2 trigger評価

- 停止指示（E記録「切りのよいところで中断」）は、長時間評価について維持している。利用者の再承認後に、repo管理のrunner（`scripts/skills/evals/trigger/run.py`）で実施した。Haiku 5.5、新14 Skill、各Skillの肯定・否定2件ずつ、3回、並列3、`--max-turns 6`。
- **観測方法の修正**：最初のSkill読込で停止する。`Skill`ツール呼出しに加えて、`.claude/skills/<name>/SKILL.md`の直接Readも読込として観測し、方式を`load_methods`に分けて記録する（EVALS.mdは「Skillの読み込みを観測できるログ」を求める）。最初の実行（`--max-turns 1`、`trigger/superseded-maxturns1.json`）は、Skill呼出し前に打ち切られる偏りがあり採用しない。
- **変更前（同じvalidation、168実行、全て有効）**：肯定queryは31／84試行で発火（28 queryのうち10がpass）、否定は1／84。失敗した肯定の試行は、別Skillも読まず直接回答していた。
- **較正（既存7 Skill、同じ条件）**：肯定は15／42試行（14 queryのうち7がpass）。新14 Skillだけの問題ではなく、ヘッドレスのHaiku 5.5が直接回答しやすい傾向であることを示す。
- **改善**：新14 Skillのうち13件のdescriptionに、「〜を求められたら、自分で答える前に必ずこのSkillを読み込む」という依頼文型を追記し、既存の適用範囲・除外は維持した（`defect-management`は変更なし）。trainで調整し、validationで確認した。

| データ                       | 肯定の発火試行 | 肯定queryのpass | 否定の発火試行 | 否定queryのpass |
| ---------------------------- | -------------- | --------------- | -------------- | --------------- |
| train（変更前）              | 48／82         | 17／28          | 0／84          | 28／28          |
| train（採用した変更後）      | 72／84         | 24／28          | 2／84          | 27／28          |
| validation（変更前）         | 31／84         | 10／28          | 1／84          | 28／28          |
| validation（採用した変更後） | 63／84         | 20／28          | 2／84          | 27／28          |

- 2回目の調整（判断・確認の相談文型を追記）はtrainの肯定が23／28、validationの肯定が20／28（変化なし）で否定が26／28へ悪化したため**採用せず**、1回目の記述へ戻した（`trigger/*-iter2-not-adopted.json`）。
- **判定は部分**：validationの肯定は10／28から20／28へ改善したが、**肯定8 queryと否定1 query（`ui-target-analysis`の「承認者と証拠の所在だけを監査して」）が不合格のまま**。残りのfailは、description調整だけでは直せなかったか、queryが「判断・確認の相談」型で直接回答になりやすいもの。単一モデル（Haiku 5.5）・各Skill肯定2件・各query3回の部分評価で、全37 Skillの網羅ではない。validationは、train中心の調整後の確認に1回使い、2回目の調整でもう1回見ている（完全な未使用データではない）。
- 以前の900秒timeoutの原因は未検証のまま。新runnerはquery単位のtimeoutを持ち、timeoutした試行を無効として記録する。証拠：`trigger/`。

### 7.3 実PRでの通し（qa-training-store PR #220）

実際にmerge済みのPR #220（`2a8bcf57`、`package.json`と`pnpm-lock.yaml`のみを変更する依存同期）を入力に、Haiku 5.5のClaude Codeがqa-workflow（PR #22のSkill一式）に従って、変更の分析・QA影響の判断・影響するテスト項目候補の特定までを1 sessionで実行した（製品はGit履歴つきのclone、remoteは外し、読み取り専用のgitのみ許可）。証拠：`efficiency/real-pr-220/`。

- 結果：functional／quality／traceabilityはpass、**safetyはfail**。成果物は変更ファイルを依存・lockfileとして正しく分類し、機能のソースが変わっていないと判断し、依存更新に固有の回帰確認項目（`expo install --check`、Web／Native build、既存テスト）を根拠つきで挙げ、機能網羅は主張しなかった。
- safetyのfailは、Agentが補助script（`pr220_evidence.py`）を`qa-state/`の外（作業用scratchpad内）へ書いた機械検査の違反による。製品の作業ツリーは変更されていない。headlessの`dontAsk`では`Write`の書込み先がworkspaceに限られないため、Skillではなく実行環境の制約として残す。
- 1回目の実行（`realpr-attempt1`）は、Agentがgitを使えず差分を取得できずに停止した。実行環境の設定（読み取りgit許可）を直して再実行したもので、1回目は採用しない。
- 範囲：1 PR・1 sessionで、release・Q06・外部Issueは含まない。判定は**部分**。

## 8. 完了条件の判定

### 開発連動QA Plan（15条件）

| #  | 判定   | 確認済み範囲・残件                                                                                                                                |
| -- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | 未実施 | feature-analysisの契約・実Git store。残：実製品（qa-training-store）の全機能抽出                                                                  |
| 2  | 未実施 | 残：実PR・merge・releaseの入力                                                                                                                    |
| 3  | 部分   | 製品CI上で未分類・改ざん・未承認pusherの負例がPASS。残：Riskを踏まえたfail／warning／blockedの分類                                                |
| 4  | 部分   | ローカル契約。残：実案件データでの算出                                                                                                            |
| 5  | 部分   | B→D→E接続。残：§6の残件                                                                                                                           |
| 6  | 部分   | 機能ID・履歴の維持とstale伝播（D→E）。残：実案件                                                                                                  |
| 7  | 部分   | 実GitHubの遠隔CAS・履歴・readback・承認主体。残：rebase・merge・release、権限取消、中断復旧                                                       |
| 8  | PASS   | UI package・migration・legacy・routing fixtureの回帰                                                                                              |
| 9  | 部分   | Project Contextを実GitHubへ保存・承認・readback。残：実Q06の配置合意                                                                              |
| 10 | PASS   | 16節・stable key・DEC／ASM・互換テスト                                                                                                            |
| 11 | 部分   | 文書・CI登録・GitHub Actions全PASS。残：実製品相当の統合受入                                                                                      |
| 12 | 部分   | 4 Skillの存在・routing・接続。残：実案件の通し                                                                                                    |
| 13 | 部分   | itemとconditionの別ID・履歴、D→E採用経路。残：Eの意味評価                                                                                         |
| 14 | PASS   | 評価データを補完して再実行した意味評価11件がすべてpass（候補・JudgeともHaiku 5.5。§7.1.1）。元の不足入力でSkillが全面停止する挙動は変更していない |
| 15 | PASS   | 不足時にblockedへ倒す契約、CIが意味判断をしないこと                                                                                               |

### QA全工程Plan（10条件）

| #  | 判定    | 確認済み範囲・残件                                                                                                                                                      |
| -- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | 部分    | routing fixtureは固定。実Agentの発火は新14 Skillのvalidationで肯定20／28 query・否定27／28 queryがpass（変更前は10／28）。残：肯定8・否定1がfail（§7.2）                |
| 2  | 部分    | E→coverage、D→E、G→H→J接続。残：F実成果物                                                                                                                               |
| 3  | blocked | F 3 Skillに実行コードが無く、owner verifier未登録（完了不可）                                                                                                           |
| 4  | 部分    | 探索→欠陥候補は接続。外部Issueは案件設定なしのため対象外。残：修正確認の実接続                                                                                          |
| 5  | 部分    | G／H／I→J投影とowner verifier（test-reporting）。残：実案件のsource inventory                                                                                           |
| 6  | 部分    | Jの評価runtimeのローカル契約。残：改善採用の承認と正本改版                                                                                                              |
| 7  | 部分    | Vitest・Web component・Native Jest・静的解析（ESLint）を実runnerで確認。API-only・batch・非機能・直接TCは製品側testware／承認済みTCが無くblocked、Windowsは設計上非対応 |
| 8  | 部分    | 共通契約・runtime・Regression、実Git provider。残：Activityの保存readback                                                                                               |
| 9  | 部分    | 人間編集8ケースのローカルPASSと実Git provider。残：承認済み配置の実運用                                                                                                 |
| 10 | 部分    | 実Agentの意味評価は11件pass。効率比較は5シナリオを実測したが、人間の確認・承認時間が未測定で「未実証」（悪化が残る範囲あり。§8）                                        |

### 詳細Plan 01〜08

| 詳細 | 判定 | 理由                                                                                                                       |
| ---- | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| 01   | 部分 | 実runner（Vitest・Web component・Native Jest・timeout・静的解析）。API-only・batch・非機能はblocked、Windowsは設計上非対応 |
| 02   | 部分 | 実Git provider（CAS・履歴・readback・承認主体）。外部Issueは案件設定なしのため対象外                                       |
| 03   | 部分 | S1〜S17は下表                                                                                                              |
| 04   | 部分 | owner verifierを4 Skillで登録。F 3 Skillなどは登録できず完了不可のまま                                                     |
| 05   | 部分 | owner振り分けとVitest個別結果の照合は実runnerでPASS。API-only・直接TCはblocked                                             |
| 06   | 部分 | 静的解析は受入用adapterで実行済み（製品・Skillへのadapter組込みは未実施）。探索・Knowledgeはローカル契約                   |
| 07   | 部分 | 5シナリオを実測。人間時間が未測定で効率は未実証、悪化範囲あり                                                              |
| 08   | 部分 | 人間編集8ケースのローカルPASSと実Git provider                                                                              |

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
| S14 | blocked | 2セッションの共有予約provider（静的解析のadapterは受入用に実行済み）            |
| S15 | blocked | 改善の承認・計画改版                                                            |
| S16 | 部分    | 実Gitでのreadback。残：中断後の別セッション復旧                                 |
| S17 | 部分    | 5シナリオを実測。人間時間が未測定で効率は未実証                                 |

### 人間編集8ケース・効率比較

- 人間編集8ケース：ローカルのテストはPASS（B由来の機能ID検証を含めて18件）。全体経路は**部分**（残：承認済み配置の実運用）。
- 効率比較5シナリオ（詳細07・S17）：**実測した。効率向上は未実証**。証拠：`efficiency/`（`harness.py`、`checklists.json`、各trialの`trial.json`・成果物・実行ログ）。
  - 方法：同じ製品commit（`2a8bcf57`）・同じQA依頼（カート機能、テスト分析からテスト観点設計まで）・同じ期待基準で、変更前＝`main`（78d8d394、23 Skill）と変更後＝PR #22（37 Skill）のSkill一式を、Haiku 5.5のClaude Code（`claude -p`、各trialは新しいworkspace）で実行した。5シナリオ（初回／変更なし再依頼／局所コード変更＝`maxCartQuantity` 99→100／外部仕様改版＝BR-CART-001の上限99→50／中断再開＝qa-stateへ3回書いた時点でsessionを終了して再開）、各2回、合計20 trial（変更後はSkill改訂後に10 trial追加）。
  - 指標はログ・操作・ファイルhashから機械的に取得した（所要時間、Skill読込数、再読込数、再利用・再生成した成果物数、書き直し回数、token・request・費用）。品質は、実行Agentとは別sessionのJudge（Haiku 5.5）が事前に書いた基準で判定し、操作ログの機械検査（`qa-state/`外への書込み、外部通信、製品変更）を安全に反映した。
  - **人間のレビュー・承認時間は無人実行では測れないため「未測定」とした**。比較器は両者を必須測定とするため、全シナリオが`not_comparable`、総合は`unproven`（未実証）になる。
  - 品質：全trialがpassではなく（Judgeが「機械証拠の未取得」「成果物内の件数の不一致」などを指摘）、`unchanged_request`と`interrupted_resume`は品質のfailを含む。品質・安全がpassでない試行があるシナリオは、比較器の規則で比較不能になる。
  - エージェント側の指標（median、変更前→変更後、初回実行のSkill）：初回QAは所要時間446→342秒、費用$0.46→$0.28、token 3.3M→2.3Mで改善、Skill読込は4.5→5回で増加。外部仕様改版は557→317秒、書き直し25→17回で改善。**変更なし再依頼は悪化**（所要150→548秒、費用$0.09→$0.34、再利用成果物2→0.5件）。局所コード変更は所要は同程度で費用・tokenが増加。中断再開は所要910→627秒で改善、Skill再読込は4→3回。
  - **悪化範囲の是正と再測定**：変更なし再依頼で、変更後のSkillは既存のqa-stateを読まず全体を再生成していた。`qa-workflow`の実行契約2へ「開始時に既存のworkflow stateと成果物を読み、記録された入力revisionが同一なら再利用し、変更した範囲だけ再実行し、再利用・再実行と中断・再開をworkflow stateへ記録する」を追記して、変更後のSkillだけを再測定した（`efficiency/run2-candidate-v2`）。結果は、初回QA（342秒、費用$0.22）と外部仕様改版（140秒、費用$0.09）は大きく改善したが、**変更なし再依頼（再利用1件、費用$0.14）と局所コード変更では悪化が残った**。試行が各2回でAgentの揺らぎが大きく、追記の効果は確認できていない。
  - 測定の限界：各2回、単一モデル、候補とJudgeが同じモデル、Judgeの厳しさに揺らぎがある。最初の実行（`efficiency/superseded`）はharnessの不具合（相対pathの扱い、中断の時点が早すぎて再開すべき成果物がない、runtime検証を許可していない）で採用せず、2回目はアカウントの利用上限（HTTP 429）で中断したため採用しない。

## 9. 総合判定

**PR #22の最終受入は未完了**。mainへのmerge条件は満たさない。今回（2026-11-13）、利用者の指示で、Codexでの受入は必須とせず、「何らかのAgentで実施したこと」（今回はClaude Code／Haiku 5.5）を要件とした。残る条件は次のとおり。

1. 意味評価は11件がpassしたが、入力の補完で通ったもので、元の不足入力でSkillが全面停止する挙動は変えていない。必要なら、Skillの停止条件と部分成果物の関係をEのownerが判断する。
2. trigger評価の肯定8 queryと否定1 queryが不合格（§7.2）。description調整は1回採用・1回不採用で、追加の調整はownerの判断が必要。
3. 効率比較は実測したが、人間のレビュー・承認時間を測れず**未実証**。変更なし再依頼・局所コード変更・中断再開に悪化または品質failが残る。
4. F 3 Skill（`test-requirements-analysis`・`test-architecture-design`・`test-management`）はMarkdownのみで、保存・readback・currentnessを検証する本番入口がない。owner verifierを登録すると形式検査を「完了」と偽るため、登録しない（完了は引き続き不可）。実行可能な検証入口の追加はFのownerの設計判断で、今回は実装していない。
5. 実案件：実PR（#220）の通しは実施した（§7.3）。ただしrelease、実Q06の配置合意、実Issue管理先の設定は入力が無く未実施。
6. runner経路：Vitest・Web component・Native Jest・静的解析は実runnerで確認した。API-only（製品に対象spec無し）・batch・非機能・直接TC（対象testwareと承認済みTC・閾値が無い）はblocked、Windowsは設計上非対応。
7. Codex：必須ではない（利用者の指示）。`codex --no-daemon --strict-config`での受入は未検証のまま。

## 10. GitHub操作

- `ryu-yoshikawa-pro-vision`（repository ownerのアカウント）で通常push。force pushはしていない。mainへのmerge、PR close、release、tag操作はしていない。
- 製品repo qa-training-storeには、`qa/artifacts`（QA成果物のorphan branch）と、検証用Draft PR #221のbranchだけを作成した。製品コードは変更していない。

## 11. 最終HEADのGitHub Actions

最終HEADのCIはこの記録のcommit後に確認し、PR #22の本文に反映する。
