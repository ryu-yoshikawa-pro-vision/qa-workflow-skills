# ワークフロー完了・再利用・横断コンテキスト分析の改修

## 目的・対象

OPS-05・15・18、01・04との接続。依頼に必要な工程と根拠だけを選び、意味上の完了・機械的検証・保存・実行完了を区別する。既存成果物を正しく再利用し、#40の横断分析を必要に応じて自律的に利用する。

## 現状と変更境界

`qa-workflow/scripts/workflow_runtime.py` の `_scope_rows`（L445〜）、`_requested_scope_rows`（L869〜）、`_build`（L1049〜）は要求集合と全scopeを扱う。L1132〜でunrequestedを求めるがL1159〜は全scopeを検証し、L1284〜は未検証をblocking issue、L1375は `can_complete = not issues and bool(scopes) and scope_set_declared` とする。`owner_verifiers.py` は9 owner、`runtime_contract.py` はruntime-v2 root 6。runtime-v2 rootにはqa-workflow自身も含まれる。未登録の担当Skillには個別の品質判断・専用検証を持つものがある。単体Skillの完了と汎用runtime完了を混同しない。

#40の `context_workflow_state.py` の `record_requested_scopes`、`record_signal_attempt`、`record_synthesis_run`、`complete_context_workflow` は開始時の全要求を保存し、最終のA/B実scope・実readback・runを照合する。`complete_context_workflow` の開始/最終要求照合（L1599〜2058）はA/Bを対象とする。`workflow_runtime.py` の `_verify_context_workflow_completion` は独立した `context_workflow_state_root` により最終入力からA/Bが消えた場合も検出する。元要求の欠落を検出する目的は維持し、SQLiteへの依存は本Planで置換する。

## 実装1 要求集合と完了判定の分離

担当Skillは専門QA判断、必要な成果物・実行・検証を担当する。qa-workflowは依頼と必要な依存工程を確認し、完了・未完了・対象外・再開先を判断する。実行合否、報告、正式承認、リリース可否を混同しない。意味判断、既存Machine Runtime、登録owner validator、WCAG等の専用検証を必要範囲で使う。全Skillを汎用runtimeへ登録しない。

開始要求は元依頼・計画・質問回答を参照する。最終成果物の自己申告だけから元要求を再構成しない。単独の処理では元依頼と実入力、計画に基づくworkflowでは既存計画・要求成果物を照合元とする。複数工程の機械的完了検証では単一sessionでも、実行前に確定した必須要求集合を最終入力とは別に参照できるようにする。既存の依頼・計画等を機械照合元として利用できない場合だけ、既存requested_scopes形式の通常JSONに必要な要求を記録する。中断・再開に必要な未完了情報も既存成果物から復元できない場合だけ保持する。機械stateは既存workflow_refのJSON envelopeを優先する。SQLite専用の初期化・読取・履歴・条件付き更新と設定・呼出しを削除する。全状態revision履歴、新workflow-runtime-v3、request_start_revision、completion_state_revision、共通書込みgateは追加しない。

同一依頼の途中で必要な工程を発見したら実施前に追加範囲と理由を記録する。stateなしから必要になった場合は元依頼、完了済み成果物、未完了範囲、実行中/結果不明の操作を引き継ぎ、後から記録した時点を初回と偽らない。補助から必須へ変わった工程は既存成果物の範囲・現在性・必要検証を確認し、不足だけ実施する。過去実行を今回実行と偽らない。

縮小・再採用は実際の変更指示または必要な正式承認を元要求に結び付け、対象・理由・影響を記録する。全取消は取消と報告し成功baselineを作らない。未解決副作用・cleanup、正式retirement・下流適用状態を省略しない。downstream_state.pyのscope_removal_resolutions/scope_removal_applied_states、Entity・ownershipを用い、過去結果を無断削除しない。

## 実装2 機械検証・全体完了・baseline

- 機械検証不要の依頼はworkflow_runtime.pyを呼ばず、担当Skillとqa-workflowが元依頼に必要な成果物・検証から完了を判断する。必要な検証は元依頼・要求成果物・担当Skillの既存契約・使用するruntimeと依存から判断し、機械検証の対象は実行前または追加工程の判明時に確定する。決定論的技法、機械schema、結果集計、正式WCAGなど既存契約で必須の検証をAgentの任意判断で省略しない。通常のMarkdown相談・分析には不要な機械検証を要求しない。成果物の有無だけで必須scopeを決めない。最終入力のrequested_scopesとworkflow_scopesの両方を欠落させても、実行前に確定した独立の要求集合と照合して未完了を検出する。最終結果から要求集合を作り直さない。正当な追加・除外は元依頼と変更指示に基づいて反映する。この照合は要求漏れ検出であり、Agentによる記録の意図的な改変まで防ぐ仕組みではない。単独処理に一律state生成を課さない。混合workflowでは機械必須scopeのみ既存runtime/owner verifierへ渡し、その結果と意味・専用scopeの実成果物をqa-workflowが照合する。機械scope 0を空の機械runtimeで成功させない。機械必須scopeの欠落・未実行・不正証拠は未完了。_build/_requested_scope_rows/_verify_context_workflow_completion、owner_verifiers.verify/_stored_owner_artifact、downstream_state._validate_state_record/_validate_frozen_pair/evaluateと呼出し元を変更する。can_completeは機械対象の完了として扱い、全体完了へ読み替えない。旧v1/v2の固定キー・fingerprint・凍結pairは当時の意味で検証し、機械出力の意味変更が必要な場合だけ版を区別する。
- 必須A/Bは最初の実行前に元要求source・範囲・条件を既存依頼/計画または必要なJSONに記録する。最終run入力とは独立してその記録を読み、実batch/runの参照・分析範囲と照合する。途中追加・除外・再採用は実際の変更を反映する。最終入力からA/B scope・参照が全部落ちても元要求を読み欠落を検出する。0件と未実施、部分と完了、別root/workflow、split run未実施を区別する。後から判明したsource版やbatchは根拠付きで具体化する。context_workflow_state.pyのSQLite更新・全履歴照合・過剰なrevision搬送を通常ファイルへ置換する。
- scripts/context_artifacts.pyの_validate_runはplanned_candidate_opsの固定fields（base_content_hash、expected_revision、related_preconditions、operation_id、planned_content_hash、planned_payload、write_request_meta、confirmed_result等）を要求する。保存方式だけ変えて旧schema用のダミー値を作らない。3 kindの意味・identity・source・観察・反例・範囲・候補採否・根拠・run完了を維持し、run/candidate schema・validator・projection・store・workflow adapter・owner verifier・fixtureを一体改訂する。runは要求/分析範囲、実候補ref、必要な予定作業・未完了、結果・根拠を持つ。全予定payload・毎更新receipt・関連候補同時CASは必須にしない。中断は実ファイルと残作業を照合し、必要な過去根拠を保全する。旧JSON fixtureは旧契約で読む。候補統合・分割は関連成果物の参照・採用整合を確認し、外部副作用は04。
- 最後の正常な機械設計・入力・依存は既存Machine Runtime Input/Result/Entity、必要baseline refに保持する。commit_qa_workflow_baseline_localは検証済み成果物の保存と参照更新に縮小し、失敗・中断時は前回正常版を保持する。既存Git履歴やimmutable snapshotで足りれば新履歴を作らない。旧baselineのref/hash/凍結pairは読取可能とする。過去完了と現在採用を分け、現行要求と根拠で再評価する。
- 要求漏れ、誤scope/根拠、未確認機械証拠、過去完了の誤採用、別workflow混線、無断縮小の拒否を維持する。SQLite CAS・全履歴固有テストを削除し、通常保存・再開・元要求充足の検証へ置換する。外部旧DB読取テストは追加しない。

## 実装3 発見・再利用と変更影響

`qa-workflow/scripts/input_revision.py` の `_sha256_file` と `_compute_document` はファイル変更の検知として維持する。現行guidance L338〜340の「path変更=依存成果物の要再検証」を意味変化の確認へ置換する。`runtime_contract.py` の `compare_entity_dependencies`、`compare_runtime_dependencies`、`upstream_entity_fingerprints`、`machine_entity_dependency`、`resolve_entity_dependencies`、`input_fingerprint` を利用する。`artifact_graph.py compare_used_context`、`test-analysis/scripts/change_impact.py` と各ownerの `impact`/lookupを再利用する。

入力revision記録は既存の input-revisions.json を用いる。新規の継続workflowで必要なら <root>/state/<workflow-ref>/input-revisions.json、単独の継続成果物ではownerの既存scope領域に置く。既存の一意な記録はそのまま利用し、複数workflowで同一ファイルを上書きしない。共有済み記録の所有範囲が不明なら再利用証拠にせず必要な母集団を再取得する。通常の単発作業に記録ファイルを強制しない。既存 record/compare と原子的置換を利用する。

手順:

1. 01の許可root/direct refと既存ownerで正本を発見する。取得範囲・母集団、必要なsourceの一覧、owner・scope・identity・現在のrevisionを確認する。欠落、重複、読取不能、一覧打切りを区別する。path一致だけで同一意味としない。対象外のartifactの不明を全体の停止に拡大しない。
2. source revision/hash・製品build・利用したContext field・実際に参照したAuthority/Entity・owner成果物のcurrentnessを比較する。入力母集団の変更・外部資料の改版・前回未取得sourceの取得可能化も確認する。未列挙inputの存在を `same` とみなさない。
3. ファイルhashが変わっても、利用した承認済みAuthority/EntityやContext field、入力集合・前提条件が同じなら、関連する既存成果物を再利用する。例: 未承認の別候補・質問の追記、表示だけの変更。変更が当該候補との矛盾・例外・反例を生じる場合は根拠を再評価する。単に候補欄の変更を無条件無視しない。
4. 利用した意味が変わった場合は依存関係から影響scopeだけを要再検証に戻す。spec-analysis→test-analysis→TR→TCN/CI→TCの既存Entity・scope ownership・partial rerun・carry-forward・retirement・coverageを維持する。`downstream_state.py`、`migration_preflight.py`、各runtime generatorの現行経路に従う。全成果物の再生成を既定としない。前回完了したbaseline/過去報告は履歴として保持し、現在の採用可否と区別する。
5. qa-knowledgeの `lookup`、`plan_revalidation`、`update_entry`、`read_entry` 等は既存entry形式で使用する。Knowledgeの利用は追加2 Skillの起動や新規保存を条件としない。#40の軽量projection・既存owner検索・本文の選択取得を利用し、全データの読込や新規全文検索基盤を前提としない。

Entity以外の文書では参照した仕様の節・決定・用語・計画の行ID・Knowledge entryと適用範囲/例外、現行source revisionを既存依存記録で追跡する。hash変更時は担当ownerの既存impactと根拠本文を照合する。計画は06の実際に利用した承認対象・行と根拠、Knowledgeは現行entryのscope・status・根拠、通常仕様文書は実際の該当節と有効Authorityを確認する。物理的な入力revision/hashの変化と、実際に参照した意味の変化を分離する。ownerのimpactが旧版hashの変化を検出したときは該当根拠の差分を担当ownerで確認し、意味不変と判断できた範囲のみ再利用する。必要な当時の内容が取得できず意味不変を確認できない場合は該当依存を要再検証とする。要再検証は白紙再生成を意味しない。担当Skillが現行の根拠と既存成果物を再照合し、妥当ならその成果物を再利用して必要な依存・現在性を更新する。実際に意味が変わる部分だけ修正・再生成する。機械Entityの変更は既存downstream_state.py等で検証し、通常Markdownの意味判断は担当Skillが行う。参照IDのない共通制約、例外、文書全体の適用範囲も意味判断に含める。IDブロックのhash一致だけで再利用を決めない。一般文書の新規fingerprint schema、全節hash台帳、全文検索サービスは不要。

Contextを後から作成・更新した場合、qa-workflowと担当Skillは許可範囲で新たに利用可能になったContextを確認し、既存のsource・対象範囲・判断理由・未確定事項・前提と、新たに有効になったDEC/ASM・制約を照合する。既存成果物にContext refがなくても、実際に影響する成果物を担当Skillで再評価し、必要な根拠refを更新する。artifact_graph.pyのcompare_used_contextは既に利用したfieldの比較であり、used_fieldsが空でcurrentを返すことを新規Contextの適用確認の代用にしない。新規Context・DEC/ASM・共通制約の影響判断は既存の入力発見・変更影響評価から行う。意味不変の範囲は再利用し、過去成果物への一律ID付与や再登録は行わない。

## 実装4 横断分析の起動条件

`qa-workflow/SKILL.md` 横断コンテキスト分析節、`references/guidance.md` の同節、`context-signal-audit` / `context-rule-synthesis` のdescription・開始/停止条件・reference、routing fixturesを改修する。

<!-- dprint-ignore -->
| 条件 | 動作 |
| --- | --- |
| 明示非保存 | 既存Knowledge・成果物を読取参照し、新規永続batch/candidate/run/Knowledgeは作らない。一時的な分析は許可範囲で行えるが、正式成果物保存が必須なら矛盾を説明し該当範囲のみ未完了 |
| 単発相談・レビュー・調査 | 対話回答を基本とし、再利用価値がある知識だけ許可済み既存ownerへ保存。観察・横断分析が必要ならA/Bを補助起動。保存先不明なら任意蓄積のために依頼を停止しない |
| 利用者が明示無効 | A/Bを起動しない。通常Knowledge・既存仕様の参照は可能。必須目的と矛盾する場合は達成できない範囲を示す |
| 利用者が明示指定 | 指定の対象・必須/補助・範囲に従う |
| 未指定で再利用価値のある単一source観察が必要 | Aを補助として選択。通常の資料読取だけでは起動しない |
| 未指定で複数source/workflowの法則・反例・差異条件の分析が必要 | Bを補助として選択。通常の複数資料参照や一機能の仕様整理だけでは起動しない。既存batchやKnowledgeを先に利用し、Aの毎回実行後にBを自動起動しない |
| 分析結果なしに元依頼の必須成果物を成立させられない | 必須として実行前に要求を登録。必要根拠・保存・検証不足は影響scopeを未完了 |
| 有効な過去合意・Knowledgeの直接参照で足りる | A/Bを起動しない |

未指定時の自律起動は現行からの契約変更である。別の設定モードを追加せず、既存の無効・補助・必須・単体利用の意味を利用する。補助の失敗・保存先不明は該当分析の制約として報告し、独立QAを継続する。必須分析は01の許可済みrootの既定 `cross-context/` と必要な要求記録を利用し、追加設定を求めない。必要な許可・保存境界が不足する場合だけ具体的な問題を確認する。

Aの中立観察・不変batch・訂正、Bの独立根拠、反例、候補の適用範囲、7状態・currentnessの区別、別root混在防止を維持する。通常更新は02の単一担当・通常JSON保存、semantic handoff keyは実際の外部反映の重複防止に限定する。候補を正式Authority・Product Risk・期待結果へ自動昇格させない。正式期待への採用はspec-analysis等が有効SPEC/DEC/承認済みASM・適用範囲を照合する。未確定・競合はquestion-analysis、未確認の実装差異はinspection/exploratory-testing、確認済み差異はdefect-management、暫定合意はproject-context/spec-analysis、再利用可能知識はqa-knowledge、リスク候補はtest-analysisへ引継ぐ。仮説の引継ぎと正式採用を区別し、反例・scope外・情報不足を解決済みにしない。実owner一意性が確認できない外部handoffはblockし、read-only調査を継続する。

## 検証・完了条件

- `test_workflow_runtime.py`、`test_qa_workflow_runtime.py`、`test_owner_verifier_gate.py`、`test_owner_verifier_registry.py`、`test_owner_scope_resume.py`、`test_runtime_workflow_integration.py`、`test_qa_workflow_baseline.py`、`test_input_revision.py`、`test_context_workflow_state.py`、`test_context_owner_verifiers.py`、`test_context_runtime_transport.py`、`test_context_artifact_store.py`、`test_runtime_portability.py` を関連する変更ごとに個別実行する。9個のruntime_contract.pyの同期テストを維持する。
- routing fixtureの未指定/明示無効/補助/必須/単体、Aのみ・Bのみ・既存Knowledge直接参照、開始後の必須追加、全A/B要求の消去、別root/run、別source/range、補助結果の必須流用、未承認除外、独立補助失敗と依存補助失敗を確認する。複数仕様書を使う通常の仕様整理・既存ルールの直接適用を負例、共通欠陥傾向・反例・差異条件の分析を必要とする依頼を正例として確認する。
- AT-06/07/08/12〜15/17/19/20/21/22/25。変更なし再依頼、部分改版、未承認候補追記、矛盾追加、未列挙source、stale、実副作用不明、登録外意味scopeを含む複合workflow、機械scope0、必須機械scope未達を対比する。元依頼に含まれる必須機械scopeをAgentの最終入力から除外した場合、機械検証を不要扱いした場合、Context後発生成による関連成果物の再評価、IDのない共通制約・例外の変更も確認する。要求集合と実行結果の両方から同じ必須scopeを除外した場合、単一sessionの複数工程、Context未作成時の空used_fieldsから関連/無関係のContextが後発生成された場合、未コミット旧Markdownを取得できない場合の再検証と再利用を確認する。
- 不要な全体停止・全再生成・無条件のA/B起動がなく、必要な専門判断と機械検証、元要求、実行・保存・履歴の保証を維持する。機械gateだけで全体完了と判定する経路を残さない。実Agent評価は05で確認する。
