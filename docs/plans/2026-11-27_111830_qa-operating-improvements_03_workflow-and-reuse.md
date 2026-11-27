# ワークフロー完了・再利用・横断コンテキスト分析の改修

## 目的・対象

OPS-05・15・18、01・04との接続。依頼に必要な工程と根拠だけを選び、意味上の完了・機械的検証・保存・実行完了を区別する。既存成果物を正しく再利用し、#40の横断分析を必要に応じて自律的に利用する。

## 現状と変更境界

`qa-workflow/scripts/workflow_runtime.py` の `_scope_rows`（L445〜）、`_requested_scope_rows`（L869〜）、`_build`（L1049〜）は要求集合と全scopeを扱う。L1132〜でunrequestedを求めるがL1159〜は全scopeを検証し、L1284〜は未検証をblocking issue、L1375は `can_complete = not issues and bool(scopes) and scope_set_declared` とする。`owner_verifiers.py` は9 owner、`runtime_contract.py` はruntime-v2 root 6。残り24 Skillはこの登録外であり個別の品質判断・専用検証を持つものがある。単体Skillの完了と汎用runtime完了を混同しない。

#40の `context_workflow_state.py` の `record_requested_scopes`、`record_signal_attempt`、`record_synthesis_run`、`complete_context_workflow` は開始時の全要求を保存し、最終のA/B実scope・実readback・runを照合する。`complete_context_workflow` の開始/最終要求照合（L1599〜2058）はA/Bを対象とする。`workflow_runtime.py` の `_verify_context_workflow_completion` は独立した `context_workflow_state_root` により最終入力からA/Bが消えた場合も検出する。これを弱めない。

## 実装1 要求集合と完了判定の分離

担当Skillは専門QA判断、必要な成果物・実行・検証を担当する。qa-workflowは依頼と必要な依存工程を確認し、完了・未完了・対象外・再開先を判断する。実行合否、報告、正式承認、リリース可否を混同しない。意味判断、既存Machine Runtime、登録owner validator、WCAG等の専用検証を必要範囲で使う。全Skillを汎用runtimeへ登録しない。

開始要求は依頼・計画・質問回答・成果物から取得する。複数工程や中断で元要求、完了範囲、未解決、次工程が復元できない場合だけ既存workflow_ref単位のJSON stateまたはMarkdownに保持する。機械stateはcreate_workflow_state/read_workflow_stateの既存JSON envelopeを優先し、単一担当の通常更新を可能にする。旧SQLite stateは01の必要資産読取・exportで扱う。SQLite依存・全状態revision履歴・CASを通常経路から削除し、新workflow-runtime-v3、request_start_revision、completion_state_revision、共通書込みgateは追加しない。

同一依頼の途中で必要な工程を発見したら実施前に追加範囲と理由を記録する。stateなしから必要になった場合は元依頼、完了済み成果物、未完了範囲、実行中/結果不明の操作を引き継ぎ、後から記録した時点を初回と偽らない。補助から必須へ変わった工程は既存成果物の範囲・現在性・必要検証を確認し、不足だけ実施する。過去実行を今回実行と偽らない。

縮小・再採用は実際の変更指示または必要な正式承認を元要求に結び付け、対象・理由・影響を記録する。全取消は取消と報告し成功baselineを作らない。未解決副作用・cleanup、正式retirement・下流適用状態を省略しない。downstream_state.pyのscope_removal_resolutions/scope_removal_applied_states、Entity・ownershipを用い、過去結果を無断削除しない。

## 実装2 機械検証・全体完了・baseline

- workflow_runtime.pyの_build、_requested_scope_rows、_verify_context_workflow_completion、owner_verifiers.pyのverify/_stored_owner_artifact、downstream_state.pyの_validate_state_record/_validate_frozen_pair/evaluateを変更する。機械scopeは実成果物と既存検証、意味・専用scopeは担当Skillの必要条件を確認する。機械scope 0でも通常QAを完了可能とし、機械必須scopeの欠落・未実行・不正証拠は未完了。can_completeと利用側を照合し、機械成功を全体完了に読み替えない。旧pairを当時の意味で読む。新schemaは意味変更が避けられない場合だけ追加する。
- 必須A/Bは元要求source・範囲・条件と実batch/run参照を依頼/必要JSON stateに保持し、元要求と実分析済み範囲を照合する。0件と未実施、部分と完了、別root/workflow、split run未実施を区別する。後から判明したsource版やA batchは根拠付きで具体化する。context_workflow_state.pyのSQLite専用更新、全履歴照合、過剰なrevision搬送は削減するが、元要求や実根拠が欠落した完了は認めない。
- context_artifacts.py/context_artifact_store.pyの3 kind、schema・validator・検索を利用する。Bの分析結果と候補の関係、直接根拠・反例・範囲・採否、必要な当時の内容、未完了handoffを保持する。途中保存はrunと実ファイルを照合して再開する。全planned payload、毎更新receipt・revision/hash、関連候補の同時CASは通常必須条件から外す。共通候補は担当を一つにし、統合・分割の途中は必要な関連成果物を確認する。過去結論を最新候補で捏造せず必要な過去版を保全する。外部副作用は04。
- 最後の正常な機械設計・入力・依存は既存Machine Runtime Input/Result/Entity、必要baseline refに保持する。commit_qa_workflow_baseline_localは検証済み成果物の保存と参照更新に縮小し、失敗・中断時は前回正常版を保持する。既存Git履歴やimmutable snapshotで足りれば新履歴を作らない。旧baselineのref/hash/凍結pairは読取可能とする。過去完了と現在採用を分け、現行要求と根拠で再評価する。
- 要求漏れ、誤scope/根拠、未確認機械証拠、過去完了の誤採用、別workflow混線、無断縮小の拒否を維持する。SQLite CAS・全履歴固有の期待値は通常保存・再開・元要求充足へ置換する。旧DBの読取テストは必要な場合に維持する。

## 実装3 発見・再利用と変更影響

`qa-workflow/scripts/input_revision.py` の `_sha256_file` と `_compute_document` はファイル変更の検知として維持する。現行guidance L338〜340の「path変更=依存成果物の要再検証」を意味変化の確認へ置換する。`runtime_contract.py` の `compare_entity_dependencies`、`compare_runtime_dependencies`、`upstream_entity_fingerprints`、`machine_entity_dependency`、`resolve_entity_dependencies`、`input_fingerprint` を利用する。`artifact_graph.py compare_used_context`、`test-analysis/scripts/change_impact.py` と各ownerの `impact`/lookupを再利用する。

入力revision記録は既存の input-revisions.json を用いる。新規の継続workflowで必要なら <root>/state/<workflow-ref>/input-revisions.json、単独の継続成果物ではownerの既存scope領域に置く。既存の一意な記録はそのまま利用し、複数workflowで同一ファイルを上書きしない。共有済み記録の所有範囲が不明なら再利用証拠にせず必要な母集団を再取得する。通常の単発作業に記録ファイルを強制しない。既存 record/compare と原子的置換を利用する。

手順:

1. 01の許可root/direct refと既存ownerで正本を発見する。取得範囲・母集団、必要なsourceの一覧、owner・scope・identity・現在のrevisionを確認する。欠落、重複、読取不能、一覧打切りを区別する。path一致だけで同一意味としない。対象外のartifactの不明を全体の停止に拡大しない。
2. source revision/hash・製品build・利用したContext field・実際に参照したAuthority/Entity・owner成果物のcurrentnessを比較する。入力母集団の変更・外部資料の改版・前回未取得sourceの取得可能化も確認する。未列挙inputの存在を `same` とみなさない。
3. ファイルhashが変わっても、利用した承認済みAuthority/EntityやContext field、入力集合・前提条件が同じなら、関連する既存成果物を再利用する。例: 未承認の別候補・質問の追記、表示だけの変更。変更が当該候補との矛盾・例外・反例を生じる場合は根拠を再評価する。単に候補欄の変更を無条件無視しない。
4. 利用した意味が変わった場合は依存関係から影響scopeだけを要再検証に戻す。spec-analysis→test-analysis→TR→TCN/CI→TCの既存Entity・scope ownership・partial rerun・carry-forward・retirement・coverageを維持する。`downstream_state.py`、`migration_preflight.py`、各runtime generatorの現行経路に従う。全成果物の再生成を既定としない。前回完了したbaseline/過去報告は履歴として保持し、現在の採用可否と区別する。
5. qa-knowledgeの `lookup`、`plan_revalidation`、`update_entry`、`read_entry` 等は既存entry形式で使用する。Knowledgeの利用は追加2 Skillの起動や新規保存を条件としない。#40の軽量projection・既存owner検索・本文の選択取得を利用し、全データの読込や新規全文検索基盤を前提としない。

Entity以外の文書では参照した仕様の節・決定・用語・計画の行ID・Knowledge entryと適用範囲/例外、現行source revisionを既存依存記録で追跡する。hash変更時は担当ownerの既存impactと根拠本文を照合する。計画は06の実際に利用した承認対象・行と根拠、Knowledgeは現行entryのscope・status・根拠、通常仕様文書は実際の該当節と有効Authorityを確認する。意味不変を確認できない場合は該当依存を要再検証とする。一般文書の新規fingerprint schema、全節hash台帳、全文検索サービスは不要。

## 実装4 横断分析の起動条件

`qa-workflow/SKILL.md` 横断コンテキスト分析節、`references/guidance.md` の同節、`context-signal-audit` / `context-rule-synthesis` のdescription・開始/停止条件・reference、routing fixturesを改修する。

<!-- dprint-ignore -->
| 条件 | 動作 |
| --- | --- |
| 明示非保存 | 既存Knowledge・成果物を読取参照し、新規永続batch/candidate/run/Knowledgeは作らない。一時的な分析は許可範囲で行えるが、正式成果物保存が必須なら矛盾を説明し該当範囲のみ未完了 |
| 単発相談・レビュー・調査 | 対話回答を基本とし、再利用価値がある知識だけ許可済み既存ownerへ保存。観察・横断分析が必要ならA/Bを補助起動。保存先不明なら任意蓄積のために依頼を停止しない |
| 利用者が明示無効 | A/Bを起動しない。通常Knowledge・既存仕様の参照は可能。必須目的と矛盾する場合は達成できない範囲を示す |
| 利用者が明示指定 | 指定の対象・必須/補助・範囲に従う |
| 未指定で再利用価値のある単一source観察が必要 | Aを補助として選択。必要な場合にのみ実施 |
| 未指定で複数source/workflowの法則・反例・差異条件の分析が必要 | Bを補助として選択。既存batchやKnowledgeを先に利用し、Aの毎回実行後にBを自動起動しない |
| 分析結果なしに元依頼の必須成果物を成立させられない | 必須として実行前に要求を登録。必要根拠・保存・検証不足は影響scopeを未完了 |
| 有効な過去合意・Knowledgeの直接参照で足りる | A/Bを起動しない |

未指定時の自律起動は現行からの契約変更である。別の設定モードを追加せず、既存の無効・補助・必須・単体利用の意味を利用する。補助の失敗・保存先不明は該当分析の制約として報告し、独立QAを継続する。必須分析は01の許可済みrootの既定 `cross-context/` と必要な要求記録を利用し、追加設定を求めない。必要な許可・保存境界が不足する場合だけ具体的な問題を確認する。

Aの中立観察・不変batch・訂正、Bの独立根拠、反例、候補の適用範囲、7状態・currentnessの区別、別root混在防止を維持する。通常更新は02の単一担当・通常JSON保存、semantic handoff keyは実際の外部反映の重複防止に限定する。候補を正式Authority・Product Risk・期待結果へ自動昇格させない。正式期待への採用はspec-analysis等が有効SPEC/DEC/承認済みASM・適用範囲を照合する。未確定・競合はquestion-analysis、未確認の実装差異はinspection/exploratory-testing、確認済み差異はdefect-management、暫定合意はproject-context/spec-analysis、再利用可能知識はqa-knowledge、リスク候補はtest-analysisへ引継ぐ。仮説の引継ぎと正式採用を区別し、反例・scope外・情報不足を解決済みにしない。実owner一意性が確認できない外部handoffはblockし、read-only調査を継続する。

## 検証・完了条件

- `test_workflow_runtime.py`、`test_qa_workflow_runtime.py`、`test_owner_verifier_gate.py`、`test_owner_verifier_registry.py`、`test_owner_scope_resume.py`、`test_runtime_workflow_integration.py`、`test_qa_workflow_baseline.py`、`test_input_revision.py`、`test_context_workflow_state.py`、`test_context_owner_verifiers.py`、`test_context_runtime_transport.py`、`test_context_artifact_store.py`、`test_sqlite_workflow_history.py`、`test_runtime_portability.py` を関連する変更ごとに個別実行する。9個のruntime_contract.pyの同期テストを維持する。
- routing fixtureの未指定/明示無効/補助/必須/単体、Aのみ・Bのみ・既存Knowledge直接参照、開始後の必須追加、全A/B要求の消去、別root/run、別source/range、補助結果の必須流用、未承認除外、独立補助失敗と依存補助失敗を確認する。
- AT-06/07/08/12〜15/17/19/20/21/22/25。変更なし再依頼、部分改版、未承認候補追記、矛盾追加、未列挙source、stale、実副作用不明、登録外意味scopeを含む複合workflow、機械scope0、必須機械scope未達を対比する。
- 不要な全体停止・全再生成・無条件のA/B起動がなく、必要な専門判断と機械検証、元要求、実行・保存・履歴の保証を維持する。機械gateだけで全体完了と判定する経路を残さない。実Agent評価は05で確認する。
