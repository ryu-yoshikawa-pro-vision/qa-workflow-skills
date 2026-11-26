# PR #40 実装・受入検証記録

## 対象と実行条件

- 対象branch: feat/context-rule-synthesis、対象PR: [#40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)
- fetch確認時のorigin/mainは`197f1e0e1abe870b0cc793355e7abf73bf241d87`でPR baseと一致。コード・test headは`7a23afdf00dd259f515c11e933d8fb51c98f763f`。後続の検証記録整形head `e154bbc1`、Plan同期head `ce856615`、文書同期head `af7b1615`も全workflow成功を確認した。
- `7a23afdf`ではValidate Agent Skills (2368)、Deterministic Output Evals (2366)、Semantic Output Evals (2331)、Code Quality (1061)、Codex Harness (1061)の5 workflowすべてsuccess。runtime unit/integration suiteは1,504 tests、0 failures、0 errors。`af7b1615`の5 workflowもsuccess（Agent Skills 2376、Deterministic 2374、Semantic 2339、Code Quality 1069、Codex Harness 1069）。
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

| ID | 状態              | 対応・証拠                                                                                                                                                                                                                                                                                                        |
| -- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1 | BLOCKED           | semantic_handoff_keyの再計算と同一artifact_refのcreate-if-absentは検証。別ref・異なるworkflowをまたぐ既存ownerのatomic uniquenessは未接続・未確認。test_context_artifacts.py、test_context_artifact_store.py。                                                                                                    |
| B2 | PARTIAL / BLOCKED | 候補関係とcycleを検証し、対象revision/hashとrelated candidate revision/hashを同じlocal file-lock保存境界で照合。merge/splitのsemantic再確認と実owner保証は未実施。test_context_artifact_store.py、test_context_artifacts.py。                                                                                     |
| B3 | PARTIAL           | planned payload/hash/metadataを保持するrunをin_progressで登録し、候補保存前後・confirmed result記録・pendingからreturnedへのhandoff・readback不足後・run完了前の各地点から保存済みrevisionで再開する。外部owner実反映後の縦断再開は未実施。test_context_workflow_state.py。                                       |
| B4 | PARTIAL           | 3 kindの実create/list/read/history、target/related revision+hashの同一保存境界照合、同じ境界の競合順序、old revision readback、symlink/noncanonical ref拒否を隔離filesystemで確認。workspace 9pでは通常保存継続・conditional update局所blockを実測。本番root/共有writerは未指定。test_context_artifact_store.py。 |
| B5 | PARTIAL           | 通常createに専用host/保存ごとの承認を要求しない。ext4で条件付き更新を確認、9pで能力不足時の更新拒否と通常readbackを確認。実運用rootのOS権限失効や共有writer認可は未確認。                                                                                                                                         |
| B6 | PARTIAL           | QA artifact保存と正式Authority承認を分離。owner verifierはreadback整合を検証するが、外部承認主体・既存owner認可を証明しない。symlink/path境界はlocal storeでテスト。test_context_owner_verifiers.py、test_context_artifact_store.py。                                                                             |

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

| ID | 状態    | 対応・証拠                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| -- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E1 | PARTIAL | requested scope、無効/無指定、補助/必須、単体実行のrouting/state契約を実装。全modeの実Agent workflowは未実施。                                                                                                                                                                                                                                                                                                                                                                            |
| E2 | PARTIAL | owner verifier登録、3 kind readback配列、同一refの複数revision、開始要求/snapshot/target batch対応を確認。workflow final gateで元要求mapping・全current run完了・必要readbackを統合し、別root証拠、in_progress run、handoff readback不足を拒否する回帰を追加。65,535/65,536/65,537 byte境界の既存受入も対象branchの先行検証にあり。外部認可・実owner一意性・全v1/v2実workflow再開は未確認。test_context_workflow_state.py、test_context_runtime_transport.py、9 runtime_contract copies。 |
| E3 | PARTIAL | secret-like text拒否と架空fixture、既存runtime regressionを検証。全metadata/log/historyの機密監査、悪意ある資料に対する実Agent試験、3構成比較は未実施。test_context_artifacts.pyおよびsemantic cases。                                                                                                                                                                                                                                                                                    |

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
| Latest GitHub Actions runtime regression                          | PASS: 1504 tests, 0 failures, 0 errors | Head `7a23afdf`、CI Python 3.11、218.762秒。standalone QA workflowとcontext helper欠落の局所blockを含む最終runtime/integration suite。                                                                     |
| 9p capability実測                                                 | PASS: 通常保存 / BLOCKED: CAS          | workspace下の隔離TemporaryDirectoryでcandidateをcreate/read/list/history。9pと判定されconditional updateだけconditional_update_requires_local_filesystemで拒否。                                           |
| ext4 store実測                                                    | PASS                                   | /tmp isolated rootで3 kind create/list/read/history、candidate/run update、履歴revision readback、stale/conflicting writerをruntime testsで確認。                                                          |
| Ruff 0.16.8                                                       | PASS                                   | `format_tracked.py`で追跡Python 327 filesのlint/formatを確認し、新規common helper 3 filesも個別lint/format check PASS。                                                                                    |
| dprint / tracked format aggregate                                 | PARTIAL                                | `format_tracked.py check`はRuff PASS後、今回対象外の既存tracked files 18件のline-ending差でexit 20。先行head `af7b1615`までのMarkdown/JSON/YAML 17 filesはpinned dprintで個別check PASS。今回の継続再レビューによるMarkdown変更は作業環境にdprint実行ファイルがなく未実施で、push後のCode Quality CIで確認する。既存対象外ファイルは変更していない。 |
| git diff --cached --check                                         | PASS                                   | staged PR #40差分にwhitespace errorなし。                                                                                                                                                                  |
| GitHub Actions CI                                                 | PASS at 7a23afdf                       | Validate Agent Skills (2368)、Deterministic Output Evals (2366)、Semantic Output Evals (2331)、Code Quality (1061)、Codex Harness (1061)の5 workflow。                                                     |
| Code Quality契約tests                                             | PASS: 24 tests                         | formatter 19、patch whitespace 3、CI security configuration 2。                                                                                                                                            |

## 2026-11-26 再レビュー指摘の修正・再検証

| 指摘                                                        | 判定                | 修正と局所証拠                                                                                                                                                                                                                                                                         |
| ----------------------------------------------------------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| in_progress runの空のconfirmed_resultにもreadbackを要求する | must_fix / 修正済み | confirmed resultが未確定なら候補readbackを省き、予定runを既存SQLite stateへ登録する。候補保存後にconfirmed revisionを記録・再readbackして再開する。test_context_workflow_state.py。                                                                                                    |
| 関連候補のrevision/hashが対象保存境界で確認されない         | must_fix / 修正済み | targetのexpected revision/hashとcanonicalなrelated_preconditionsを同じ保存境界で照合し、既存local file-lockの範囲で依存refを保持する。古い前提は拒否、依存更新が後続操作として直列化される順序をtest_context_artifact_store.pyで確認。後続更新を共有一意性や永続lock保証とは扱わない。 |
| workflow stateが成果物rootに束縛されていない                | must_fix / 修正済み | 最初のA/B state記録時にroot bindingを保存し、異なるrootのrun登録を拒否する。test_context_workflow_state.py。                                                                                                                                                                           |
| 元要求・全run完了・readbackの最終workflow統合gateが不足     | must_fix / 追加修正済み | 先行修正はB run群中心で、Aの開始要求全件とruntime最終scope集合の照合、runtimeからB要求group全体が欠落したケースを統合していなかった。今回`completion-check-workflow`をA/B共通gateにし、開始時要求→attempt/group→保存済みartifact→owner record/readback→最終required scope集合をroot/ref/revision/hashで照合。集合の省略・過剰、補助scopeのstate未指定も検証。`test_context_workflow_state.py` 17件。 |
| 補助context scopeのstate未指定が必須workflow gateを止める     | 回帰修正済み | stateのない補助scopeは集約gateから除外し、要求集合上の必須context scopeでstate/evidenceが欠ける場合はblockする。実A必須scope＋B補助scopeの正常系と、必須scopeのstate欠落を`test_context_workflow_state.py`で確認。 |
| history symlink検査前にidentity dirが作成される             | must_fix / 修正済み | 既存path検査後に、対応環境ではdirectory FD/no-follow、未対応環境ではcomponentごとの作成前後検査を用いる。両pathでhistory symlinkの外側に新規ファイル・identity dirを作らず、対象candidateも更新されないことをtest_context_artifact_store.pyで確認。                                    |
| 共通helperのmodule importがQAの単体runtimeを停止させる      | must_fix / 修正済み | completion adapterをcontext synthesis scopeがある場合だけ読み込む。adapter/store/contractの欠落はcontext scopeのみblocking issueとし、通常QA runtimeは単体Skill copyで動作する。`test_context_workflow_state.py`、`test_runtime_portability.py`。                                      |

修正後の関連suiteを個別実行し、`test_context_artifact_store` 12件、`test_context_workflow_state` 12件、`test_context_artifacts` 14件、`test_context_owner_verifiers` 4件、runtime transport 64 KiB境界1件の計43件PASS。`test_context_workflow_state`と`test_runtime_portability`の計15件もPASSし、adapter/store/contractの各欠落と単体QA runtimeの継続を確認した。中断点テストは候補保存前のrun登録、保存成功後readback失敗からの再読取、returned resultのreadback不足からの再開、split run完了gateを含む。初回store suiteで対象revision inode情報の未定義名を検出して修正した。競合testは保存境界後の関連候補更新が直列化されて成功する契約に合わせ、lock保持中は待機し、対象write後の更新となることを確認する期待値へ直した。GitHub Actions `7a23afdf`でruntime 1,504 testsと5 workflowすべてPASS。ローカル全runtimeの重複実行はActions完了後に中断しPASS扱いしていない。

2026-11-26の継続再レビューでは、先行の最終gateがBのみを主に見ており、開始時のA/B全要求、最終required scope集合、全runとowner verifier証拠を一体で照合していなかった点を確認・修正した。runtime入力からB要求group全体が欠落するケース、必須scopeと補助scopeのstate要求分離、最終scope集合の省略・過剰、開始要求scopeの契約不一致、実保存readback後の完了・再開を追加確認した。`test_context_workflow_state` 17件、`test_runtime_portability` 3件、`test_workflow_runtime` 26件、`test_owner_scope_resume` 41件、`test_integration_required_scopes` 24件を各suite個別に実行し、計111件PASS。Ruff check、Ruff format check、`py_compile`もPASS。現変更headのCIは未実行で、直近のリモートCI成功は文書同期head `af7b1615`の5 workflow。外部評価・実Agent受入は本結果に含めない。

先行head `0d789e1f`ではDeterministic Output Evalsがruntime portability test 2件で失敗した。`workflow_runtime.py`の追加adapter importが静的許可リストになく、単体Skill copyで共通helper不足時にも既存QA runtimeが起動できなかった。最初のテスト修正で共有helperをisolated rootへコピーしたが、自己レビューで親Planの単体Skill portability契約を弱めると判断し、そのfixture変更を戻した。最終実装はcontext scopeでのみadapterを遅延importし、adapter/store/contract不足はcontext scopeだけblocking issueにする。ローカル15件とhead `7a23afdf`のruntime全suiteで再検証した。

docs-only head `968629b3`のCode Qualityは検証記録の2行のtable padding不足で失敗した。`dcde957d`でその2行を直した後、新たに追加されたレビュー行106のpaddingが残り、`00e4f06d`と`32a1a084`もCode Qualityで失敗した。CI差分の指定どおり38個の空白に合わせた`e154bbc1`でCode QualityがPASSし、そのheadの5 workflowがすべてsuccess。各修正はverification.mdの表幅だけで、コード/testは`7a23afdf`から変更していない。Plan同期head `ce856615`と後続文書同期head `af7b1615`も5 workflowすべてsuccess。

## 実環境依存・未実施

- 通常root保存・履歴・readback・再開はローカル既存filesystem/SQLiteで接続・検証した。運用rootは指定されていないため、共有writer、複数host、権限外root、外部ownerの一意性・認可・正式承認を実運用環境で受入したとは扱わない。通常保存に専用認証hostを要求しない。
- PR #38の既存owner保存API・semantic_handoff_keyに対応する実保存単位/並行初回作成の一意性は、ローカルcontext artifact storeのcreate-if-absentとは別に確認が必要。外部owner経路を仮定でpassにしない。
- formal trigger全Skill比較、独立Semantic Judge、実Agent縦断、導入前/1 Skill/2 Skillの3構成比較はNOT RUN。評価query、Skill本文、case/rubricをCodex外部サービスへ送る明示許可が未確定のため保留中。Claudeは使用せず、承認要求の範囲を迂回しない。
- 先行Codex CLI smokeは2 positive queryのみ。正式rate、negative query、反復、誤発火を測っていない。repository configがuntrusted扱いでHook/execpolicy無効化を示したため、Codex runtime safety acceptanceも未確認。
- 主な残タスク: 外部評価送信の許可範囲、実運用root/共有writer/owner一意性の確認、Agent/Judge/3構成比較、Plan 03の複合受入完了。

## 設計・実装間の差異と対応

- 古いqa-workflow SKILL.md、semantic rubric/case、verification/Plan statusにあった「通常保存には専用host/認可hostが必要」という前提を、2026-11-25共通原則と最新版Planに合わせて修正した。通常root保存はOS権限と標準filesystem操作、外部/共有/正式仕様変更は既存ownerの認可・承認・履歴・readbackに分けた。
- 共通context contract helperをproject-context Skill配下からrepository common scriptsへ移し、qa-workflow state adapterだけをqa-workflow scriptsに置いた。これはPRN-03/Q06/Q07/Q08の責務に一致する。旧data-contract相対pathも新配置へ修正した。
- completion adapterはcontext synthesis scopeでのみ共有helperを読み込む。単体Skillで共通helperが未配置でも通常qa-workflow runtimeを保ち、context scopeだけを明示的にblockedにする。static import allowlistとsingle-copy regressionの範囲を狭く保った。
- `requested_scopes`の意味が、永続stateに固定する開始時の元要求集合と、最終runtimeへ渡す具体化済みrequired scope集合で異なる点を明記した。前者を変更せず、A/B state mapping・保存readback・owner verificationで対応する後者を作る。runtime入力は`workflow_scopes`とのidentityを保ち、completion gateが集合の不足・余剰を検出する。
- owner verifierはreadback自体を取得せず、callerから受け取った実保存本文/readbackの整合を検証する。専用host認証を意味しない。外部ownerのreadback/承認主体はこのverifierだけでは確立しない。
- qa-workflow guidance.mdに残る共有resource reservation provider未選定時のblockは、複数workflowの外部共有resource排他の契約であり、通常context artifact保存の制限ではないため維持した。
- workflow-state-template.mdのSQLite local-filesystem制約は既存qa.workflow_state_root providerの制約で、context artifactの通常filesystem保存とは別経路。JSON-only legacy stateは自動移行しないが、そのstate更新blockで通常artifact save/独立分析を停止しない。
- Python 3.12.3とCI Python 3.11.18の既存JSON nestingテスト差は、stdlib parserのRecursionError発生有無に依存していた。既存runtime契約と同じ深さ64の明示scannerで拒否するよう修正し、文字列内の括弧を深さと誤認しないtestを追加した。`test_ci_handoff` 28件と全runtime 1495件がPASS。
- formatter契約testとRuffはPASS。dprint集約checkは作業環境の今回対象外の既存tracked file 18件の改行差でexit 20だが、今回変更したMarkdown/JSON/YAML 17 filesはpinned dprintで個別check PASS。既存の対象外ファイルや未stageのuser `.gitattributes` は変更せず、CI formatter/lint checksもPASSした。
