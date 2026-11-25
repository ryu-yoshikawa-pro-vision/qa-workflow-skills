# PR #40 実装・受入検証記録

## 対象と実行条件

- 対象branch: feat/context-rule-synthesis、対象PR: [#40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)
- 最新fetch時点: origin/main = 197f1e0e1abe870b0cc793355e7abf73bf241d87、origin/feat/context-rule-synthesis = 21134c966ca0dfaac68fdd7efd71530a9fbffef7。local branchはremoteと一致し、mainはbranchの祖先。fetchでmain・PR branchに更新はなく、別の文書branchだけ更新された。
- PR #40の現head 21134c96では、Validate Agent Skills、Validate Deterministic Output Evals、Validate Semantic Output Evals、Code Quality、Codex Harnessの5 workflowがsuccess。これは以下の追加作業より前のCI結果。追加commit後のCIはpush後に再確認する。
- 作業環境はPython 3.12.3。CI指定Python 3.11.18はローカルにない。Ruff 0.16.8、dprint 0.55.2、skills-ref pinned packageを/tmpで利用。
- 実運用rootは未指定。これは通常保存に専用認証hostが必要という意味ではない。隔離ローカルrootで保存経路を実測した。/tmpのext4では条件付き更新を実測し、workspaceの9p filesystemでは通常create/read/list/historyは成功、条件付き更新だけを能力不足としてblockした。
- shared writer、外部ownerの一意性保証、正式仕様の承認・認可、実運用rootの権限はローカルfilesystem試験から推定しない。
- Claudeは使用していない。Codex CLIの先行target-only positive smokeは各Skill 1 queryのみで、正式trigger評価ではない。Codex等の認証済み外部サービスへ比較用Skill/query/caseを送る許可は未確定のため、今回の正式外部評価は行っていない。

状態: PARTIALは局所実装・検証済みでも設計項目全体に未確認条件が残る状態。BLOCKEDは実運用の共有/owner接続または外部送信承認が必要な状態。NOT RUNは実Agent/Judge/比較測定を行っていない状態。いずれも複合受入のPASSを意味しない。

## 基本設計13.2全項目と証拠

以下の30行は設計13.2 A〜Eの全チェック項目に対応する。局所テストが通っても、行の受入条件に外部owner・意味評価・本番接続が含まれる場合はPASSにしない。

### A. 不変ログ・データ契約・識別・状態遷移

| ID | 状態    | 対応・証拠                                                                                                                                                                                                                                           |
| -- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1 | PARTIAL | Batch identity、範囲/観測条件、訂正identity、immutable save/readback、再利用のcontract testあり。実Agent抽出失敗からの再実行と保存後readback失敗の縦断受入は未実施。tests/skills/runtime/test_context_artifacts.py、test_context_artifact_store.py。 |
| A2 | PARTIAL | A attempt stateを既存SQLite workflow-state providerへ保存し、再読込・再送を確認。全失敗状態の実Agentでの遷移・復旧は未確認。tests/skills/runtime/test_context_workflow_state.py。                                                                    |
| A3 | PARTIAL | Directory storeの実保存readbackを両登録owner verifierへ渡す統合テストあり。実運用rootと外部owner readback境界は未指定。tests/skills/runtime/test_context_workflow_state.py、test_context_artifacts.py。                                              |
| A4 | PARTIAL | Candidate schemaは7 resolution stateと鮮度/完全性軸を分離。全状態と下流変更伝播の実運用組合せは未確認。tests/skills/runtime/test_context_artifacts.py。                                                                                              |
| A5 | PARTIAL | transition helper・鮮度条件・再開条件の決定論テストあり。一時障害後の実Agent再評価は未実施。test_context_artifacts.py、両Skillのreferences/guidance.md。                                                                                             |
| A6 | PARTIAL | candidate/batch/run/operation/handoff identityの再計算、scope・source/hash・条件差を確認。root bindingと実storeもテストしたが、複数運用root間のowner一意性は未確認。test_context_artifacts.py、test_context_artifact_store.py。                      |
| A7 | PARTIAL | competing/alternative相互参照、successor自己参照/cycle拒否の決定論テストあり。統合/分割の実保存競合は未確認。test_context_artifacts.py。                                                                                                             |
| A8 | PARTIAL | 0変更runを正確なsource/run revision readbackで完了判定し、未実行と区別する。複数仮説の意味的な一部解決は独立Semantic Judge未実施。test_context_artifacts.py、tests/skills/evals/deterministic/test_context_rule_contracts.py。                       |

### B. 並行実行・永続化・認可・再開

| ID | 状態              | 対応・証拠                                                                                                                                                                                                                                                                                   |
| -- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1 | BLOCKED           | semantic_handoff_keyの再計算と同一artifact_refのcreate-if-absentは検証。別ref・異なるworkflowをまたぐ既存ownerのatomic uniquenessは未接続・未確認。test_context_artifacts.py、test_context_artifact_store.py。                                                                               |
| B2 | PARTIAL / BLOCKED | 候補関係とcycleを検証し、同一candidate revisionのCAS競合はローカル実filesystemで確認。merge/splitの関連候補一体更新と実owner保証は未実施。                                                                                                                                                   |
| B3 | PARTIAL           | planned payload/hash/metadataを保持するrun contract、SQLite stateへのrun ref保存、再読込、stale state conflictをテスト。候補更新・handoff各中断点からの実provider再開は未実施。test_context_workflow_state.py、test_context_artifact_store.py。                                              |
| B4 | PARTIAL           | 3 kindの実create/list/read/history、candidate/run conditional update、old revision readback、同revisionの並行writer、symlink/noncanonical ref拒否を隔離filesystemで確認。workspace 9pでは通常保存継続・conditional update局所blockを実測。本番rootは未指定。test_context_artifact_store.py。 |
| B5 | PARTIAL           | 通常createに専用host/保存ごとの承認を要求しない。ext4で条件付き更新を確認、9pで能力不足時の更新拒否と通常readbackを確認。実運用rootのOS権限失効や共有writer認可は未確認。                                                                                                                    |
| B6 | PARTIAL           | QA artifact保存と正式Authority承認を分離。owner verifierはreadback整合を検証するが、外部承認主体・既存owner認可を証明しない。symlink/path境界はlocal storeでテスト。test_context_owner_verifiers.py、test_context_artifact_store.py。                                                        |

### C. 横断検索・起動制御・鮮度・再評価

| ID | 状態    | 対応・証拠                                                                                                                                                                                                                                                                                            |
| -- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1 | PARTIAL | QA routing/guidanceはcomplete 0件、not_checked、重大反例、必須/補助モードを区別。実Agentの発火・ループなし再評価は未実施。                                                                                                                                                                            |
| C2 | PARTIAL | Skillはscope一致に限らない過去batch/candidate/Authority/Knowledge/Qの横断検索を指示。実データを用いる複数workflow検索・reuseは未実施。                                                                                                                                                                |
| C3 | PARTIAL | snapshot inputとtarget_batch_refsを開始要求・source revision・hash・readbackで照合。start input/snapshot/target batchの整合とexact revisionはcontract/runtime testsで検証。外部source/owner接続は未実施。test_context_artifacts.py、test_context_owner_verifiers.py、test_context_workflow_state.py。 |
| C4 | PARTIAL | impact/currentness helperがsource addition、authority変更、hash/revision変化を検出。実分析中の外部変更を受けたrun採用gateは未受入。test_context_artifacts.py。                                                                                                                                        |
| C5 | NOT RUN | 独立support、Authority失効/置換、重複観察の過大評価防止はrubric/caseに定義。実Agent/Judge評価は未実施。                                                                                                                                                                                               |
| C6 | NOT RUN | scope-bound rejectionと必要質問維持はSkill/caseに定義。実Agentから既存question/exploration ownerへのhandoff受入は未実施。                                                                                                                                                                             |

### D. 帰納的推論・Authority・既存owner連携・変更伝播

| ID | 状態    | 対応・証拠                                                                                                               |
| -- | ------- | ------------------------------------------------------------------------------------------------------------------------ |
| D1 | NOT RUN | 共通法則・差異条件・競合仮説/not_checkedのrubricとcaseは登録済み。実Agentの出力評価・独立Judge未実施。                   |
| D2 | NOT RUN | 5分類・反例分類・unclassified・同一観察の複数候補対応を評価セットへ記述。意味品質測定未実施。                            |
| D3 | NOT RUN | independence_group・provenanceと局所仕様の過一般化防止をSkill/rubricへ記述。実Agent評価未実施。                          |
| D4 | NOT RUN | SPECの有効性と実装適合/不一致/未確認の分離をSkill/rubricへ記述。元設計9.2全判定の実Agent受入未実施。                     |
| D5 | NOT RUN | PRODUCT_RISK、ASM、PROJECT_CONTEXT、承認回答をAuthorityと分離する契約・caseを登録。実owner readback/approval試験未実施。 |
| D6 | NOT RUN | UNKNOWN/Q、exploratory investigation、no_new_info終了・再開をroutingへ記述。既存ownerの実handoffは未実施。               |
| D7 | NOT RUN | 正式Authority等の変更伝播は既存dependency契約へ接続する設計。Machine Entity経路での実下流再検証は未実施。                |

### E. workflow完了判定・セキュリティ・効率・回帰

| ID | 状態    | 対応・証拠                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| -- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E1 | PARTIAL | requested scope、無効/無指定、補助/必須、単体実行のrouting/state契約を実装。全modeの実Agent workflowは未実施。                                                                                                                                                                                                                                                                                                                                |
| E2 | PARTIAL | owner verifier登録、3 kind readback配列、同一refの複数revision、開始要求/snapshot/target batch対応を確認。65,535/65,536/65,537 byteの各kindを実storeへ保存し、独立readback、登録owner、workflow_runtime完了、凍結input/resultの検証とdownstream_state再開まで通した。外部認可・全v1/v2実workflow再開は未確認。test_context_owner_verifiers.py、test_context_runtime_transport.py、test_context_workflow_state.py、9 runtime_contract copies。 |
| E3 | PARTIAL | secret-like text拒否と架空fixture、既存runtime regressionを検証。全metadata/log/historyの機密監査、悪意ある資料に対する実Agent試験、3構成比較は未実施。test_context_artifacts.pyおよびsemantic cases。                                                                                                                                                                                                                                        |

## ローカル検証記録

| 検証                                                              | 結果                                   | 条件・制約                                                                                                                                                                                                 |
| ----------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Context store/contracts/owner/state/transport/runtime portability | PASS: 62 tests                         | 7 targeted modules。実store CLI、owner verifierへの実readback、SQLite state restart、競合・履歴・9p capability refusal、3 kindの64 KiB境界におけるruntime完了・凍結結果再開を含む。                        |
| Deterministic repository eval suite                               | PASS: 675 tests                        | Full repository suite。新規 fixtureは開始sourceとrun双方のexact readbackを含めて更新。                                                                                                                     |
| Deterministic runner tests                                        | PASS: 12 tests                         | runner/loader/validator契約。Agent生成出力の評価ではない。                                                                                                                                                 |
| Deterministic output runner                                       | PASS: 2 evals / 6 assertions           | 新規2 Skillのcanonical example outputを各1 eval実行。各3 assertions PASS。Agent生成出力の意味評価ではない。                                                                                                |
| Semantic validator                                                | PASS: 39 skills / 227 cases            | Dataset構造の検査。意味品質をJudgeした結果ではない。                                                                                                                                                       |
| Semantic runtime tests                                            | PASS: 14 tests                         | semantic dataset/runner契約。実Agent candidate/Judge評価ではない。                                                                                                                                         |
| Trigger contract tests                                            | PASS: 17 tests                         | query balance、重複、train/validation分離等。実発火率ではない。                                                                                                                                            |
| Trigger runner CLI                                                | HELP確認のみ                           | `--help`はClaude Code headless runnerと確認。Claudeは実行せず、Codex CLI実Agent評価は送信承認待ち。                                                                                                        |
| skills-ref                                                        | PASS: 2 new Skills                     | 両Skillをpinned packageで個別validate。全39 Skillは追加変更後CIで確認する。                                                                                                                                |
| Full runtime regression                                           | PASS: 1495 tests, 0 failures, 0 errors | Python 3.12.3、1119.725秒。明示的JSON nesting上限の修正、64 KiB境界統合、localhost fixtureを含む全runtime suite。                                                                                          |
| 9p capability実測                                                 | PASS: 通常保存 / BLOCKED: CAS          | workspace下の隔離TemporaryDirectoryでcandidateをcreate/read/list/history。9pと判定されconditional updateだけconditional_update_requires_local_filesystemで拒否。                                           |
| ext4 store実測                                                    | PASS                                   | /tmp isolated rootで3 kind create/list/read/history、candidate/run update、履歴revision readback、stale/conflicting writerをruntime testsで確認。                                                          |
| Ruff 0.16.8                                                       | PASS                                   | `format_tracked.py`で追跡Python 327 filesのlint/formatを確認し、新規common helper 3 filesも個別lint/format check PASS。                                                                                    |
| dprint / tracked format aggregate                                 | PARTIAL                                | `format_tracked.py check`はRuff PASS後、今回対象外の既存tracked files 18件のline-ending差でexit 20。今回変更したMarkdown/JSON/YAML 17 filesはpinned dprintで個別check PASS。既存ファイルは変更していない。 |
| git diff --cached --check                                         | PASS                                   | staged PR #40差分にwhitespace errorなし。                                                                                                                                                                  |
| GitHub Actions CI                                                 | PASS at 21134c96, before local changes | Validate Agent Skills、Deterministic Output Evals、Semantic Output Evals、Code Quality、Codex Harnessの5 workflow。new local diff後のCIはpush後に確認。                                                    |
| Code Quality契約tests                                             | PASS: 24 tests                         | formatter 19、patch whitespace 3、CI security configuration 2。                                                                                                                                            |

## 実環境依存・未実施

- 通常root保存・履歴・readback・再開はローカル既存filesystem/SQLiteで接続・検証した。運用rootは指定されていないため、共有writer、複数host、権限外root、外部ownerの一意性・認可・正式承認を実運用環境で受入したとは扱わない。通常保存に専用認証hostを要求しない。
- PR #38の既存owner保存API・semantic_handoff_keyに対応する実保存単位/並行初回作成の一意性は、ローカルcontext artifact storeのcreate-if-absentとは別に確認が必要。外部owner経路を仮定でpassにしない。
- formal trigger全Skill比較、独立Semantic Judge、実Agent縦断、導入前/1 Skill/2 Skillの3構成比較はNOT RUN。評価query、Skill本文、case/rubricをCodex外部サービスへ送る明示許可が未確定のため保留中。Claudeは使用せず、承認要求の範囲を迂回しない。
- 先行Codex CLI smokeは2 positive queryのみ。正式rate、negative query、反復、誤発火を測っていない。repository configがuntrusted扱いでHook/execpolicy無効化を示したため、Codex runtime safety acceptanceも未確認。
- 主な残タスク: 外部評価送信の可否、実運用root/共有writer/owner一意性の確認、Agent/Judge/3構成比較、追加差分後のCI、完了条件の再評価。

## 設計・実装間の差異と対応

- 古いqa-workflow SKILL.md、semantic rubric/case、verification/Plan statusにあった「通常保存には専用host/認可hostが必要」という前提を、2026-11-25共通原則と最新版Planに合わせて修正した。通常root保存はOS権限と標準filesystem操作、外部/共有/正式仕様変更は既存ownerの認可・承認・履歴・readbackに分けた。
- 共通context contract helperをproject-context Skill配下からrepository common scriptsへ移し、qa-workflow state adapterだけをqa-workflow scriptsに置いた。これはPRN-03/Q06/Q07/Q08の責務に一致する。旧data-contract相対pathも新配置へ修正した。
- owner verifierはreadback自体を取得せず、callerから受け取った実保存本文/readbackの整合を検証する。専用host認証を意味しない。外部ownerのreadback/承認主体はこのverifierだけでは確立しない。
- qa-workflow guidance.mdに残る共有resource reservation provider未選定時のblockは、複数workflowの外部共有resource排他の契約であり、通常context artifact保存の制限ではないため維持した。
- workflow-state-template.mdのSQLite local-filesystem制約は既存qa.workflow_state_root providerの制約で、context artifactの通常filesystem保存とは別経路。JSON-only legacy stateは自動移行しないが、そのstate更新blockで通常artifact save/独立分析を停止しない。
- Python 3.12.3とCI Python 3.11.18の既存JSON nestingテスト差は、stdlib parserのRecursionError発生有無に依存していた。既存runtime契約と同じ深さ64の明示scannerで拒否するよう修正し、文字列内の括弧を深さと誤認しないtestを追加した。`test_ci_handoff` 28件と全runtime 1495件がPASS。
- formatter契約testはPASS。全tracked checkのRuffはPASSだが、dprint集約checkは作業環境の今回対象外の既存tracked file 18件の改行差でexit 20となった。今回変更したMarkdown/JSON/YAML 17 filesはpinned dprintで個別checkし、既存の対象外ファイルや未stageのuser `.gitattributes` を変更していない。clean GitHub Actions後の結果も確認する。
