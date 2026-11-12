# PR #22 統合修正・最終受入の検証記録（2026-11-12）

## 対象と前提

- 対象branch：`feat/development-qa-traceability`。作業開始時のHEADは`21cbdc5aea30b5748b33913f643b3f36cef60352`（A〜J統合済み）。この記録の修正commitは本ファイルを含むcommitとその親`5d5cf409`。
- 実行環境：WSL2 Linux 6.6.87.2、Python 3.12.3（CIは3.11）、Node v24.22.2、ruff 0.16.8、dprint 0.55.2、skills-ref `69ef37e`（CIと同じ固定版をscratchpadへ導入）、Codex CLI 0.167.1（記録のみ。Codex実runtime受入は実施していない）。
- サブエージェントは`claude-haiku-5-5`（Haiku 5.5）で、読取専用の調査だけに使用した。変更・判定はメインAgentが行った。
- 判定語：**PASS**＝条件の全範囲を証拠で確認。**FAIL**＝実装・接続の欠落または不一致を確認。**blocked**＝必要な外部入力（provider、承認主体、実案件source、製品CI、外部Issue等）が無く検証できない。**未実施**＝実施可能だが今回は実施していない。部分的に確認できた範囲は「確認済み範囲」に書き、総合判定をPASSにしない。

## 1. 実施した修正

| 対象                                                                                                     | 原因                                                                                                                                                                                                                                                                           | 修正                                                                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md`                                                                                              | 7 Skill（test-requirements-analysis、test-architecture-design、test-management、e2e-test-selection、defect-management、test-reporting、test-evaluation）が未登録で、Validate Agent Skillsの構造検証が失敗し後続stepがSKIP                                                      | Skill一覧・責務表・工程正本表・routing説明へ追加                                                                                                                                                                                                                                                             |
| `scripts/skills/evals/deterministic/common.py`                                                           | `CANONICAL_SKILLS`に新13 Skillが無く、qa-workflowの状態行・修正先・再開先として新Skillを使うとWF-D002で拒否される                                                                                                                                                              | 新13 Skillを登録。`agent-answer-form`は補助Skillとして従来どおり除外                                                                                                                                                                                                                                         |
| `scripts/skills/evals/deterministic/ASSERTIONS.md`                                                       | 新14 SkillのAssertionと`E2E-SEL-D001`〜`D006`が未掲載                                                                                                                                                                                                                          | 追加。`RISK-D016/D017`は削除せず旧`test-analysis`表のlegacy互換と明記                                                                                                                                                                                                                                        |
| `skills/qa-workflow/**`                                                                                  | 担当表・routing・状態テンプレートに新Skill 9件が無い。E2E選定の新規判断が旧`test-analysis`へ向く。UI package作成のrouting fixtureが`spec-analysis`開始のまま                                                                                                                   | 担当表・開始点・修正routing・完了条件・状態テンプレートを更新。`WF-UI-TARGET-001/002/003/005`を`ui-target-analysis`開始へ修正し、`WF-PROCESS-001`〜`014`を追加                                                                                                                                               |
| `tests/skills/runtime/test_owner_verifier_gate.py`                                                       | routing登録とowner verifier登録の混同を防ぐ回帰が無い                                                                                                                                                                                                                          | `RUNTIME_V2_SKILL_ROOTS`が既存6 Skillのままであること、owner verifier未登録の全workflow Skillが`unverified_scopes`で完了不可になることを固定                                                                                                                                                                 |
| `skills/testware-execution/scripts/contract.py`、`skills/regression-testing/references/data-contract.md` | Gのrunner manifest（`testware_revision`・`run_ref`・`collection_verified`・`cleanup_state`）とHのsource execution契約（`implementation_revision`・`attempt_ref`・`raw_capture_complete`・`cleanup_status`等）の項目名が異なり、実runの結果がRegression routeで未開始扱いになる | `regression_source_execution()`で投影。revisionはrunnerが検証したcheckout（`repo_revision`）を使い、申告の`testware_revision`は別項目に残す。fixture証拠・未確認cleanup・未終了process・raw未取得は確定させない。`test_testware_regression_handoff.py`（11件）で実runner起動→投影→`project_activity()`を検証 |

owner verifierの正式登録（Plan 04 §1）は実装していない。新Skillの本番validateは正本保存のreadbackを検証せず（例：`item_candidates.py validate`は`provider_readback="not_verified_by_this_validator"`）、eval validatorはfixture固有の`expected`無しで判定できない。保存providerが未選定の現状で登録すると、名前追加と同等の誤完了経路になるため、未登録scopeを完了不可とする既存gateを維持した。

## 2. 実装後の独立レビュー

Haiku 5.5による読取専用レビューの指摘と対応：

| 指摘                                                                                                                                                                              | 対応                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 投影が申告値`testware_revision`を`implementation_revision`に使い、別checkoutの実行を対象revisionとして数え得る（高）                                                              | `repo_revision`へ変更し、申告値と実行値が異なるテストを追加                                                                                                                                                                     |
| `attempt_ref`が生の証拠の場所を指さない（中）                                                                                                                                     | 試行ディレクトリのpathへ変更し、reporterへ辿れることをテスト                                                                                                                                                                    |
| fixture証拠でも結果確定になる（中）                                                                                                                                               | `evidence_is_fixture`がfalseと確認できる場合だけ確定。テスト追加                                                                                                                                                                |
| `measurement_FAIL`が未確定扱い（低）                                                                                                                                              | 確定outcomeへ追加                                                                                                                                                                                                               |
| cleanup成功／失敗の分岐が未テスト                                                                                                                                                 | 両方のテストを追加                                                                                                                                                                                                              |
| `provider_readback`を無視                                                                                                                                                         | 保存readbackは実行結果の確定とは別のgateとして転記（Activity保存時にblocked）                                                                                                                                                   |
| `CANONICAL_SKILLS`の拡張により、eval validator（question-analysisの`Runtime Skill`、qa-workflowのruntime行、adversarial-reviewの修正先）がowner verifier未登録のSkill名も受理する | **未対応**。本番の`workflow_runtime.py`は未登録scopeを完了不可にするため、誤完了は本番では起きない。eval側でruntime行をRUNTIME_V2の6 Skillに限定するかは各owner（question-analysis、qa-workflow、adversarial-review）の契約判断 |

## 3. CI相当の個別実行（LFのクリーン展開先）

`git archive HEAD`に変更を重ねた展開先で、5 workflowの各`run`stepを個別に実行した（`local-ci-steps.json`）。Windows jobは未実行。

| workflow                       | 結果                                                                                                                                                                                                                                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code Quality                   | 全step rc=0。`Check patch whitespace`はGitHub eventが無いとrc=2になるため、base＝作業開始HEAD、head＝変更commitのpull_request eventを与えて別途rc=0                                                                                                                                   |
| Validate Agent Skills          | 全step rc=0（skills-ref 37 Skill、構造検証37 Skill／836 query、回答フォーム、semantic件数、trigger契約）。以前SKIPされたstepも実行                                                                                                                                                    |
| Deterministic Output Evals     | `Run runtime unit and integration tests`だけrc=1（最終展開先で976件中1 FAIL）。`test_ci_handoff.test_json_nesting_failure_is_a_structured_input_error`で、作業開始HEADでも同じく失敗。Python 3.12は深さ1100のJSONを解析できるため（3.11はRecursionError）の**環境起因**。他stepはrc=0 |
| Validate Semantic Output Evals | 全step rc=0                                                                                                                                                                                                                                                                           |
| Codex Harness（Linux job）     | 全step rc=0。Windows jobは未実行                                                                                                                                                                                                                                                      |

push後のHEAD `822b19f5`では、GitHub Actionsの[Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/43219591978)、[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/43219592035)、[Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/43219592180)、[Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/43219592124)、[Codex Harness（Linux・Windows）](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/43219592380)がすべてPASSした。Validate Agent Skillsは全stepがsuccessで、SKIPは無い。Deterministic Output Evals（Python 3.11）では`test_ci_handoff`もPASSしており、ローカルの1件が環境起因であることと整合する。

## 4. 実runner受入（qa-training-store `2a8bcf57ff091e84a8b3bf7b123568e967000d88`）

固定SHAをscratchpadへclone（元repoは読取のみ）し、固定lockfileから`pnpm@10.34.5 install --frozen-lockfile --ignore-scripts`で依存を導入した。選択集合は実行と別に`vitest list --json`または静的source確認で取得した。`skills/testware-execution/scripts/runner.py`をLinuxのchild subreaper＋procfs監督ありで実行した。証拠は`runner/`（JSONはrepoのformatterで整形し、scratchpadの絶対pathを`<scratchpad>`へ置換した。値は変更していない）。

| 経路                     | 対象                                                     | 結果                                                                                                                                                                   | 判定                                                        |
| ------------------------ | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Vitest unit              | `tests/unit/pricing.test.ts` 3件                         | `runner_pass`、選択3件＝収集3件、reporter整合、process tree `terminated`、workspace clean                                                                              | PASS（runner契約。正式TCの期待値Authority照合はしていない） |
| timeout・retry・cleanup  | 同上をtimeout 1秒・attempts 2                            | rc=-9でkill、`blocked_cleanup_or_timeout`、2回目は起動しない、残存process無し、workspace clean                                                                         | PASS                                                        |
| Web component（Vitest）  | `tests/component/cart-page.test.tsx` 3件                 | `runner_pass`、収集完全                                                                                                                                                | PASS（runner契約）                                          |
| Native component（Jest） | `tests/component/native/native-cart-screen.test.tsx` 4件 | 初回：1件がJestの5秒test timeoutで`runner_fail`（収集完全）。別operationの再実行：4件PASS（同testは395ms）。cold transformの時間超過という仮説は未確定。初回結果は保持 | FAIL記録を保持（製品不具合とは断定しない）                  |
| G→H接続（実run）         | 上記5 runのmanifest                                      | `regression_source_execution()`→`project_activity()`：PASS／FAILは結果確定・`完了`、timeoutは`実行中`（`g-to-h-real.json`）                                            | PASS（ローカル。Activityの保存readbackはblocked）           |
| Playwright Test API-only | —                                                        | 固定SHAにAPI専用specが無い（`e2e/web/*`はブラウザspec）                                                                                                                | blocked（製品側testware無し）                               |
| 静的解析                 | ESLint 9.39.2                                            | runnerは正規化済み静的report（`analyzed_paths`・`findings_count`等）をstdoutに要求し、ESLint出力からのadapterが無い                                                    | blocked（G ownerのadapter未提供）                           |
| batch／event             | —                                                        | 固定SHAに該当testwareを特定できない                                                                                                                                    | blocked                                                     |
| 非機能計測               | —                                                        | 閾値Authorityと計測条件の正本が無い                                                                                                                                    | blocked                                                     |
| 非ブラウザ直接TC         | —                                                        | 承認済み正式TCと期待値Authorityが無い                                                                                                                                  | blocked                                                     |
| Windows実行保証          | —                                                        | runnerはWindowsで`process_supervision_unavailable`として開始前に拒否する契約。Windows実行は未実施                                                                      | 未実施                                                      |
| 製品CI                   | —                                                        | 製品CIへの成果物受渡し方式が未決定。製品CIの既存成功は本受入に使わない                                                                                                 | blocked                                                     |

## 5. 横断接続

Haiku 5.5の静的調査と、メインAgentの原文確認を組み合わせた。

| 経路                             | 状態                                                                                                                                                                                                                                   | 判定                                      |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| B → D                            | Dは`{snapshot, analysis}`と`feature_ref{owner, scope, artifact_ref, revision, content_hash}`を検証するが、Bの`persist_snapshot()`はこの組を返さず、store戻り値は`sha256`・store revisionで名前と意味が異なる。組み立てる実コードが無い | FAIL                                      |
| B → C                            | `human_editing.py`はfeature ref／revisionの非空だけを確認し、B成果物を読まない                                                                                                                                                         | FAIL                                      |
| D → E                            | D data-contract L55自身が「D→E adapterは無い」と記録。Eは`TI-*`・`{ref, revision, currentness}`、Dは`ITEM-*`・`{owner, scope, artifact_ref, revision, content_hash}`                                                                   | FAIL                                      |
| F 要求→方式→計画                 | 3 Skillに実行コードが無く、Markdown参照をvalidatorがfixtureの既知refと照合するだけ。実成果物の受渡しは未実施                                                                                                                           | blocked                                   |
| E 正式設計 → coverage            | `test_coverage_analysis_traceability.py`がEの実CLI出力をcoverageへ渡す。E入力自体は手書き                                                                                                                                              | PASS（ローカル。上流D/F実成果物は未接続） |
| E2E選定 → inspection／実装／実行 | 下流3 Skillに`e2e-test-selection`の読み手が無い。routingはこの修正で接続                                                                                                                                                               | FAIL                                      |
| G → H                            | 今回の投影で接続し、実runnerと実製品runで確認                                                                                                                                                                                          | PASS（ローカル）                          |
| I → 他owner                      | `exploratory_runtime.py`のhandoffを読むconsumerが無い。Jの欠陥候補が要求する`source_kind`・`run_ref`・`symptom`等をIのhandoffは持たない                                                                                                | FAIL                                      |
| F/G/H/I/E → J                    | Jのruntimeは手書きpayloadでのみ検証。runnerの`outcome`→Jの`FINAL_STATES`、HのActivity状態→Jの集計単位の投影が無い                                                                                                                      | FAIL                                      |
| provider・承認・外部Issue        | 案件provider、認証済み承認者、外部Issue管理先がどの文書でも未選定                                                                                                                                                                      | blocked                                   |

## 6. 実Agent・意味評価

- **Semantic Judge（PR #27の既存証拠）**：31件中PASS 20／needs_review 8／FAIL 3。未解決11件（RISK-SEM-002、RISK-SEM-005、E2E-SEL-SEM-003、TCN-SEM-004、TCN-SEM-008、TCN-SEM-012、TCN-SEM-013、TCN-SEM-014、TC-SEM-001、TC-SEM-002、COV-SEM-002）はすべてE ownerの判断待ちのまま。rubric・reference・期待結果は変更していない。再評価は**未実施**。
- **trigger評価**：利用者の停止指示（E記録L1140「切りのよいところで中断」）を維持し、長時間評価は再開していない。repoに正規trigger runnerが無く（`scripts/skills/evals/`にtrigger実装なし）、Eの一時driverは`codex exec`を1 query 900秒上限で逐次実行していた。query 4は900秒で2回打ち切られ、意味評価の候補生成も312〜1388秒かかっていることから、900秒は観測された所要時間の範囲内の壁時計上限と推定される（原因は未検証）。**再開条件**：repo管理のtrigger runnerを用意し、query単位のtimeoutと失敗試行の除外規則を定め、全Skillを含む最新HEADのsnapshotで実行することを利用者が改めて承認すること。
- 新14 Skillで実Judge結果があるのはe2e-test-selection、ui-target-analysis、test-item-analysis、test-condition-analysisだけ。他は**未実施**。

## 7. GitHub操作

- commit `5d5cf409`（共有登録・routing）と`822b19f5`（G→H投影・本記録）を、利用者の指示によりrepository ownerのアカウント`ryu-yoshikawa-pro-vision`（`gh`に保存済みの認証）で通常pushした。最初に試した`ryu-yoshikawa`（pull権限のみ）ではHTTP 403だった。force pushはしていない。
- PR #22の本文を、運用規則に従って目的と現在の状態へ置き換えた。

## 8. 完了条件の判定

### 開発連動QA Plan（15条件）

| #  | 確認済み範囲                                                                                        | 判定    | 再開条件                                          |
| -- | --------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------- |
| 1  | feature-analysisの契約・runtime・差分分類のローカルテスト                                           | blocked | 実案件sourceと保存provider                        |
| 2  | revision照合のローカル契約                                                                          | blocked | 実PR／merge／release入力と製品CI受渡し方式        |
| 3  | `ci_handoff.py`のローカル契約                                                                       | blocked | 製品CI受渡し方式の決定                            |
| 4  | 分類率等を分けて計算するローカル契約                                                                | blocked | 実案件データでの算出                              |
| 5  | 既存成果物の参照は、B→D、D→Eで欠落                                                                  | FAIL    | B→D組み立てとD→E adapterの契約決定・実装（B/D/E） |
| 6  | 機能ID・履歴は維持。下流への局所再検証伝播はD→Eで切断                                               | FAIL    | 同上                                              |
| 7  | ローカルSQLite／Git fixtureのCAS                                                                    | blocked | 遠隔providerのnative CAS・履歴・readback          |
| 8  | UI package・migration・legacy（RISK-D016/D017）・routing fixtureの回帰がローカルでPASS              | PASS    | —                                                 |
| 9  | project-contextの判定・配置提案のローカル契約                                                       | blocked | 承認済み保存先と承認主体                          |
| 10 | Project Context 16節・stable key・DEC／ASMの互換テストPASS                                          | PASS    | —                                                 |
| 11 | 文書・CI登録を更新し、`822b19f5`のGitHub Actions 5 workflowはすべてPASS。実製品相当の統合受入は未完 | blocked | 実製品相当の統合受入                              |
| 12 | 4 Skillは存在し、局所テスト・routingはPASS。機能別参照から正本へ辿る経路はB実成果物が無い           | blocked | B実成果物とprovider                               |
| 13 | itemとconditionの別ID・履歴はPASS。正式設計への採用経路はD→Eで切断                                  | FAIL    | D→E adapter                                       |
| 14 | 正式設計の意味評価に未解決FAIL／needs_reviewが残り、D→Eも切断                                       | FAIL    | Semantic 11件のowner判断と再評価、D→E adapter     |
| 15 | 不足時にblockedへ倒す契約、CIが意味判断をしないことはローカルで確認                                 | PASS    | —                                                 |

### QA全工程Plan（10条件）

| #  | 確認済み範囲                                                               | 判定    | 再開条件                                                       |
| -- | -------------------------------------------------------------------------- | ------- | -------------------------------------------------------------- |
| 1  | routing fixtureで単独・複合の開始・停止を固定。実Agentの発火は未測定       | 未実施  | trigger runnerと利用者の再開承認                               |
| 2  | F連鎖は文書参照のみ。J入力は手書き                                         | blocked | F実成果物と保存provider                                        |
| 3  | F validatorのローカル契約                                                  | blocked | 承認主体とprovider                                             |
| 4  | Jの欠陥候補・外部操作計画のローカル契約                                    | blocked | 外部Issue管理先と認証済み承認                                  |
| 5  | Jの集計契約はPASS。G／H／I出力からJへの投影が無い                          | FAIL    | runner `outcome`・H Activity・I handoff→Jの投影契約（G/H/I/J） |
| 6  | Jの評価runtimeのローカル契約                                               | blocked | 改善採用の承認と正本改版の実接続                               |
| 7  | Vitest unit／Web component／Native Jestを実runnerで確認。他の方式はblocked | blocked | 3節の各再開条件                                                |
| 8  | 共通契約・runtime・Regressionのローカル契約。G→Hは接続済み                 | blocked | provider・承認・readback                                       |
| 9  | 人間編集8ケースのローカルPASS                                              | blocked | 承認済み配置と実provider                                       |
| 10 | 実Agent受入・効率比較は未実施                                              | 未実施  | trigger runnerと利用者の再開承認                               |

### 詳細Plan 01〜08

| 詳細 | 確認済み範囲                                                                                                   | 判定    |
| ---- | -------------------------------------------------------------------------------------------------------------- | ------- |
| 01   | 実runner（Vitest、Web component、Native Jest、timeout）。API-only、batch、非機能、静的はblocked                | blocked |
| 02   | native CAS・履歴・readback・承認・外部Issueはprovider未選定                                                    | blocked |
| 03   | S1〜S17とCI受渡しは下表                                                                                        | blocked |
| 04   | 未登録Skillを完了にしない契約はPASS。ownerの検証済み成果物による単独完了経路は未実装（保存readback契約が前提） | FAIL    |
| 05   | owner振り分けとVitest個別結果の照合は実runnerでPASS。API-only・直接TCはblocked                                 | blocked |
| 06   | 静的解析のadapterが無い。探索・Knowledgeはローカル契約のみ                                                     | blocked |
| 07   | 5シナリオの実測が無い                                                                                          | 未実施  |
| 08   | 人間編集8ケースのローカルPASS。実providerと承認は未接続                                                        | blocked |

### S1〜S17

| S   | 判定    | 根拠・再開条件                                                                          |
| --- | ------- | --------------------------------------------------------------------------------------- |
| S1  | blocked | 実案件のProject Contextと配置合意の保存先が無い                                         |
| S2  | FAIL    | feature→item／condition→正式設計の経路がB→D、D→Eで切断                                  |
| S3  | FAIL    | E2E選定の結果を下流が読まない。実E2Eは未実施                                            |
| S4  | blocked | runner→raw→cleanup→Activityは実runで確認。統合報告（J）への投影が無い                   |
| S5  | blocked | F実成果物とprovider                                                                     |
| S6  | blocked | 遠隔providerのCAS競合・承認失効                                                         |
| S7  | blocked | 外部Issue管理先と承認                                                                   |
| S8  | blocked | 実外部資料の改版入力                                                                    |
| S9  | blocked | merge commit・実buildと製品CI                                                           |
| S10 | blocked | 改善採用の承認と正本改版                                                                |
| S11 | FAIL    | 未登録Skillを完了にしない点はPASS。新Skillの検証済み成果物による完了経路が無い          |
| S12 | blocked | Vitest→route→実runner→Activityはローカル・実製品runでPASS。Activityの保存readbackが無い |
| S13 | blocked | API-only・直接TCの製品testwareとAuthorityが無い                                         |
| S14 | blocked | 静的解析adapterと、2セッションの共有予約provider                                        |
| S15 | blocked | 改善の承認・計画改版の実接続                                                            |
| S16 | blocked | 遠隔providerでの中断・別セッション復旧                                                  |
| S17 | 未実施  | 効率比較5シナリオを未測定                                                               |

### 人間編集8ケース

`tests/skills/runtime/test_ui_human_editing.py`のHE-1〜HE-8は、runtime suite（970件中、環境起因の1件以外PASS）でローカルPASS。B実feature artifact、承認主体の認証、遠隔providerのCAS・readbackを含む全体経路は**blocked**。

### 効率比較5シナリオ

初回QA、変更なし再依頼、局所コード変更、仕様資料だけの改版、中断後の再開のいずれも、変更前後の実Agent測定をしていないため**未実施**。比較器（`scripts/skills/evals/workflow_efficiency.py`）のローカル契約だけがある。

## 9. 総合判定

**PR #22の最終受入は未完了**。FAILは横断接続の欠落（B→D、B→C、D→E、E2E選定→下流、I→J、G/H/I→J）とPlan 04の単独完了経路。blockedは、provider・承認主体・外部Issue・製品CI・実案件sourceが未選定であること。このためmainへのmerge条件は満たさない。
