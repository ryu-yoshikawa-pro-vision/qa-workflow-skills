# ワークフロー完了・再利用・横断コンテキスト分析の改修

## 目的・対象

OPS-05・15・18、01・04との接続。依頼に必要な工程と根拠だけを選び、意味上の完了・機械的検証・保存・実行完了を区別する。既存成果物を正しく再利用し、#40の横断分析を必要に応じて自律的に利用する。

## 現状と変更境界

`qa-workflow/scripts/workflow_runtime.py` の `_scope_rows`（L445〜）、`_requested_scope_rows`（L869〜）、`_build`（L1049〜）は要求集合と全scopeを扱う。L1132〜でunrequestedを求めるがL1159〜は全scopeを検証し、L1284〜は未検証をblocking issue、L1375は `can_complete = not issues and bool(scopes) and scope_set_declared` とする。`owner_verifiers.py` は9 owner、`runtime_contract.py` はruntime-v2 root 6。残り24 Skillはこの登録外であり個別の品質判断・専用検証を持つものがある。単体Skillの完了と汎用runtime完了を混同しない。

#40の `context_workflow_state.py` の `record_requested_scopes`、`record_signal_attempt`、`record_synthesis_run`、`complete_context_workflow` は開始時の全要求を保存し、最終のA/B実scope・実readback・runを照合する。`complete_context_workflow` の開始/最終要求照合（L1599〜2058）はA/Bを対象とする。`workflow_runtime.py` の `_verify_context_workflow_completion` は独立した `context_workflow_state_root` により最終入力からA/Bが消えた場合も検出する。これを弱めない。

## 実装1 要求集合と完了判定の分離

`qa-workflow/SKILL.md`、`references/guidance.md`、`assets/workflow-state-template.md` を以下の契約に置換する。各依頼の目的・対象・求められた成果物を起点とし、最短の必要な担当Skillから開始する。開始時に必要な成果物/工程とその依存を確認する。新しい固定工程表を作らない。

- 単発相談・調査・レビュー: 担当Skillの意味品質と必要な形式確認で終了できる。永続state、機械runtime、保存証拠は依頼または必要な知識蓄積の実契約に応じて利用する。通常の回答全体は保存しない。再利用価値のある知識だけ02の条件で自律保存できる。
- 成果物作成: 担当Skillの意味/形式・根拠と02の必要保存。機械処理を必要とする成果物にはその既存検証を適用する。
- 複合workflow: 元依頼の必須scope、依存する補助工程、独立した補助工程を区別する。前二者を必要な完了範囲とする。独立補助工程は制約を報告するが、必須範囲の完了を妨げない。補助工程の結果を必須成果物の根拠に採用した時は依存範囲に昇格し、該当する検証を実施する。未検証・必要な副作用残存を隠す目的で補助へ変更しない。
- 機械検証: runtime-v2の生成・Entity・coverage、登録済みownerの正式成果物、専用WCAG検証、実行・承認・cleanup等に必要な実証拠を保持する。自己申告の `complete`、`valid`、保存先文字列だけで成立させない。

既存workflow stateの requested_scopes に開始時の全必須scope（依存必須を含む）を保持する。単発の完結した依頼は対話・成果物を要求記録とし専用stateを作らない。継続workflowでは既存stateまたは成果物の要求記録を使う。新規の機械baseline・正式WCAG・必須A/B・副作用からの継続などstateが必要なworkflowは、初回要求登録から既存SQLite envelopeを使用する。後続にA/Bを必要とする場合も同じstateを利用できる。通常の文書継続にSQLiteを強制しない。scope identityは既存の Skill + target + execution_range と workflow_ref。

## 実装2 汎用runtimeと全体完了

機械対象はAgentの任意選択にしない。開始要求と依存を以下の既存契約で分類し、実行後に全要求と証拠の対応を確認する。単なる相談と正式成果物作成を区別する。

<!-- dprint-ignore -->
| 要求の種類 | 必要な検証 |
| --- | --- |
| test-analysis、test-requirement-design、test-condition-design、test-case-design、coverage-analysis のruntime対象 | RUNTIME_V2_SKILL_ROOTSに従いruntime unit/Entity/Disposition/必要coverageをverify_runtime_evidenceとworkflow_runtimeで検証 |
| test-item-analysis、test-condition-analysis、e2e-test-selection、test-reporting、test-requirements-analysis、test-architecture-design、test-management、context-signal-audit、context-rule-synthesis の正式成果物 | OWNER_VERIFIED_SKILLSと既存owner_verifiersの検証・必要保存/読戻し |
| WCAG正式評価、test-execution、E2E・testware実行、Regression/Explorationの実行等 | 専用ownerの実開始・raw・結果・対象母集団・必要cleanup・正式closure。汎用登録外でも省略不可 |
| その他の相談、分析、質問、レビュー、非機械成果物 | 担当Skillの意味/形式契約、根拠・必要保存。機械証拠を必要とする下流へ渡す場合はその契約も適用 |

qa-workflow自身はscopeに含めない。元要求・依存必須から必要機械対象のidentity集合を抽出しruntime入力と照合する。必要な機械scopeが一つでも欠けたら未完了。機械対象0は元要求のすべてが担当/専用検証だけで成立する場合に限りdispatch不要。依存不明は必要範囲に残す。独立補助scopeは最終報告に結果・制約を示すが機械gateに入れない。補助結果を必須成果物に採用する場合は事前に必須依存へ追加して検証する。

### 開始要求・追加・範囲変更

同一依頼を同じworkflow_refで扱う。stateが必要な新規workflowでは既存SQLite履歴を正本とし、初回要求登録のstate revisionを request_start_revision に記録する。SQLite createまたは登録transactionで実際に保存するrevision tokenを設定し、そのsnapshotに同じ値が含まれることを独立readbackで確認する。初回要求は空でない全必要scope（依存必須を含む）。既存 requested_scopes の行（skill, target, execution_range, requirement, approval_ref）のidentityを使う。開始時/追加時の登録行を削除せず、現在の除外と再採用はstate内の履歴付き変更記録から導出する。初回登録以降のSQLite historyは欠落・不整合を拒否する。状態を必要としない通常文書では同じ意味を既存依頼・回答・成果物で保全し、DBを強制しない。

- context_workflow_state.py の record_requested_scopes は一般要求登録とA/B固有の処理を分離する。一般要求の登録/変更ではDirectoryArtifactStoreを生成せず、A/Bを必要とする時に限り許可済みartifact_rootを必要なら作成し、既存root bindingとstart_contractを設定する。通常要求の初回登録でcross-context/を作らない。既存A/Bのinitialize・register-requested-scopes・attempt/runは互換を維持する。
- 新規登録入口では初回全要求を保存し、以後の追加はexpected state revisionと追加行、必要なA/B start_contractだけを渡す。既存要求との和集合を同一CASで保存する。完全同一追加再送はreused、異なる契約で同じidentityを置換しない。新規A/B contractは当該要求の開始前に登録し、他要求のattempt/runを理由に拒否しない。既存start_contract、source/range、B batch、単調具体化・分割対応・readbackは維持する。
- 範囲の縮小・再採用は同じworkflow内の明示された内容変更とする。既存stateに scope_removal_resolutions 等の既存下流契約で利用する解決・適用記録を結び付ける。要求の変更自体は state.request_scope_changes の追記行で保持する。行は skill/target/execution_range（既存要求identity）、base_state_revision、operation（exclude または restore）、approval_ref、approval_revision、reason、affected_scope_refs を持つ。実回答または正式承認の既存正本へのref/revisionを利用する。通常の回答に外部provider revisionを新規要求せず、保存済み回答のexact-content token等を使う。変更前stateの有効集合、対象・根拠・依存影響と照合し、一度除外された範囲の再送は重複適用しない。承認済み要求集合を直接置換しない。既存承認済み対象外を再採用するには現行の依頼・決定と適用範囲を確認する。通常の依頼変更は依頼者の明示回答、組織の正式品質保証scopeの縮小・リスク受容は既存担当ownerの必要な認可で成立する。権限や根拠不明、対象の曖昧さは該当変更を拒否する。現在必須集合は初回＋追加から有効な除外を差し引き、再採用を反映したもの。実副作用、結果不明、必要cleanupはscope除外で消さない。全取消は取消と報告し完了baselineを生成しない。
- 変更は新規の汎用承認サービスではなく02の実回答/正式承認記録を担当ownerが読取り、必要な内容・権限・現在の対象を確認する。scope変更の記録を承認そのものとしない。approval_ref単独・AI自己申告は不可。v1/v2の _exclusion_confirmed はFalseのまま。v3の機械projectionには現行必須scopeだけを required として渡し、全登録・有効除外・再採用はstate履歴と完了表で照合する。
- state書込みの共通入口 conditional_write_sqlite_workflow_state でv3管理workflowの要求集合・変更記録・context start_contract・履歴アンカーの変更を確認する。一般の状態更新ではこれらのfieldを変更できない。登録/変更入口からも、共通書込み境界で取得した現在stateと差分を照合し、対象の正規化・承認証拠の取得結果・旧履歴との整合を検証する。専用入口の呼出しやcallerのフラグだけを信頼しない。登録/変更の差分のみ同一transactionで適用し、失敗時はstateを進めない。保護対象の新設は要求変更に必要なfieldに限る。元のhistory revisionと後続snapshotの差分を検証し、未登録の削除、縮小、変更記録改変、初回アンカー変更、別root、古いstateでの上書きを拒否する。低レベルDBの特権改竄に対する保証は主張しない。
- complete_context_workflow は同じstateから有効な現在必須A/B集合を取得し、当該要求の実batch/run・owner readback・最終scope分割の完全一致を維持する。有効除外の旧contract・attempt/runは履歴として残し、現行完了へ数えない。開始時または追加の全A/Bを最終入力から落としてもstateを根拠に検出する。A/Bの過去補助runは現行根拠・scopeと必要証拠を確認して再利用し、今回の実行と偽らない。旧完了の証明と現在採用は分離する。

downstream_state.py evaluate/_scope_impact の既存 scope_removal_resolutions / scope_removal_applied_states の入力を利用し、同じworkflowの過去baselineに対する対象外TR/TCN/CI/TCの影響・必要なretirement/materializationを担当ownerで適用する。新しい要求変更を理由に既存ID・過去結果・過去報告を削除しない。正式承認済み要求縮小だけでは下流への適用済みを主張せず、既存の適用証拠を確認する。独立した別依頼だけ新workflow_refを発行する。

### 機械gate、全体完了、baselineの保存・再開

1. workflow_runtime.py _build/_requested_scope_rows はstateの現在必須要求・依存と実機械projectionを照合する。登録外の意味scopeを機械対象から分け、必要な専用検証を省略しない。機械結果の can_complete は当該機械対象だけの判定。機械scope0は元要求と担当/専用結果が実際に成立した場合だけdispatch不要。unrequested/unverified/不足を無条件無視しない。
2. 機械対象の意味を変えるため新規pairは generator_contract_version=workflow-runtime-v3 とする（共通runtime-v2 envelopeは維持）。既存workflow成果物に完了表を保持し、全登録要求のidentity、現在必須/有効除外、対応する実scope、担当成果物ref/revision、検証経路、結果、必要証拠ref、未完了理由を一行ずつ記載。A/B分割は既存mappingを用いる。v3 inputの許可キーはv2の必須キーに workflow_state_root と completion_state_revision を追加し、既存の任意 context_workflow_state_root はA/B必須時だけ同じ実rootとして照合する。workflow_state_root は実際に許可された絶対rootを呼出し側から独立取得し、input内の文字列だけを信頼しない。既存stateの初回・追加・変更履歴と完了時snapshotから必須集合を復元し、表の自己申告だけで全体を完了としない。意味判断は実根拠を読んだ担当Skill/qa-workflow、専用検証は実ownerに残す。
3. artifact_graph.py commit_qa_workflow_baseline_local はv1/v2の既存JSON経路を保持し、v3ではSQLiteのexpected revisionを受ける分岐とする。保存入口で現在stateを独立取得、初回からの要求変更の妥当性、全要求への証拠対応、機械pair・専用検証・必要な副作用解決・実保存refを確認する。検証したstateから変更を作り、callerの任意desired_stateで要求履歴を置換しない。機械baselineが不要なら既存成果物/必要stateだけで完了・再開する。
4. 既存immutable artifactの path/sha/readbackを使用し、v3のlast_completed_qa_workflow_artifact に従来の3 fieldに加え completion_state_revision（binding更新直前に検証したSQLite revision）を保存する。凍結inputの同fieldと一致させる。artifact公開/readback後にそのrevisionでbinding更新をCASし、独立再読込で一致確認する。CAS失敗・readback不明は状態を読み直す。既に同一bindingが保存済みなら再利用、未参照artifactだけでは完了不可。最新要求が変化していれば再照合・再検証し、古いpairでbindingを進めない。別JSON stateへ二重書込みしない。
5. downstream_state.py の _validate_state_record/_validate_frozen_pair/_WORKFLOW_CONTRACTS/_validate_owner_verification_records/evaluate、artifact_graph.py のbaseline読取、runtime_contract.py verify_runtime_evidence、関連handoff/reporting/fixtureを同時更新する。v3は保存先を扱う既存呼出し側でbindingのcompletion_state_revisionに対応する実SQLite historyを read_sqlite_workflow_state_revision で取得し、downstream_stateの検証入力にそのexact snapshotと取得metadataを渡す（純粋な意味検証処理に独自providerを持たせない）。当時の要求集合・完了表・凍結pair・hash/identityと照合する。現在のstateの要求追加・除外は過去完了を無効にせず、現在採用可否は現行要求と依存で別途判定する。過去snapshot欠落・hash不一致・別workflow/別rootを拒否。v1/v2は旧3 field binding・旧凍結pair・当時の対象外拒否を維持する。旧pairを新意味で読まない。
6. legacy JSON-only workflowは旧経路を維持する。v3継続にSQLiteが必要な場合だけ新workflowへ明示的に引継ぐ。旧workflowの実ref・state revision・baseline binding/hashを独立取得し、元要求・未解決副作用・既存scope ownership・inactive Entity履歴・対象外適用記録を参照する。downstream_stateは旧workflow_refで旧pairを検証して影響を計算し、新workflowの現在採用と分ける。旧baselineのworkflow_refを書換えたり新workflowの完了bindingとして直接登録しない。旧参照が取得不能なら影響範囲の再利用を保留し、必要な元資産を破壊せず調査する。無断の一括移行は行わない。
7. test_integration_required_scopes.py、test_downstream_state.py、test_qa_workflow_baseline.py、test_context_workflow_state.py、test_sqlite_workflow_history.py で機械scope0正常/欠落、専用検証未達、意味要求欠落、未認可のstate変更、開始時要求削除、追加・再送、承認済み除外/再採用、scope縮小とinactive履歴、過去完了後の要求追加、旧凍結pair、新v3、過去snapshot欠落、SQLite/JSON binding・旧参照引継ぎ、CAS競合・結果不明・再開を確認する。

## 実装3 発見・再利用と変更影響

`qa-workflow/scripts/input_revision.py` の `_sha256_file` と `_compute_document` はファイル変更の検知として維持する。現行guidance L338〜340の「path変更=依存成果物の要再検証」を意味変化の確認へ置換する。`runtime_contract.py` の `compare_entity_dependencies`、`compare_runtime_dependencies`、`upstream_entity_fingerprints`、`machine_entity_dependency`、`resolve_entity_dependencies`、`input_fingerprint` を利用する。`artifact_graph.py compare_used_context`、`test-analysis/scripts/change_impact.py` と各ownerの `impact`/lookupを再利用する。

入力revision記録は既存の input-revisions.json を用いる。新規の継続workflowで必要なら <root>/state/<workflow-ref>/input-revisions.json、単独の継続成果物ではownerの既存scope領域に置く。既存の一意な記録はそのまま利用し、複数workflowで同一ファイルを上書きしない。共有済み記録の所有範囲が不明なら再利用証拠にせず必要な母集団を再取得する。通常の単発作業に記録ファイルを強制しない。既存 record/compare と原子的置換を利用する。

手順:

1. 01の許可root/direct refと既存ownerで正本を発見する。取得範囲・母集団、必要なsourceの一覧、owner・scope・identity・現在のrevisionを確認する。欠落、重複、読取不能、一覧打切りを区別する。path一致だけで同一意味としない。対象外のartifactの不明を全体の停止に拡大しない。
2. source revision/hash・製品build・利用したContext field・実際に参照したAuthority/Entity・owner成果物のcurrentnessを比較する。入力母集団の変更・外部資料の改版・前回未取得sourceの取得可能化も確認する。未列挙inputの存在を `same` とみなさない。
3. ファイルhashが変わっても、利用した承認済みAuthority/EntityやContext field、入力集合・前提条件が同じなら、関連する既存成果物を再利用する。例: 未承認の別候補・質問の追記、表示だけの変更。変更が当該候補との矛盾・例外・反例を生じる場合は根拠を再評価する。単に候補欄の変更を無条件無視しない。
4. 利用した意味が変わった場合は依存関係から影響scopeだけを要再検証に戻す。spec-analysis→test-analysis→TR→TCN/CI→TCの既存Entity・scope ownership・partial rerun・carry-forward・retirement・coverageを維持する。`downstream_state.py`、`migration_preflight.py`、各runtime generatorの現行経路に従う。全成果物の再生成を既定としない。前回完了したbaseline/過去報告は履歴として保持し、現在の採用可否と区別する。
5. qa-knowledgeの `lookup`、`plan_revalidation`、`update_entry`、`read_entry` 等は既存entry形式で使用する。Knowledgeの利用は追加2 Skillの起動や新規保存を条件としない。#40の軽量projection・既存owner検索・本文の選択取得を利用し、全データの読込や新規全文検索基盤を前提としない。

Entity以外の文書では参照した仕様の節・決定・用語・計画の行ID・Knowledge entryと適用範囲/例外、現行source revisionを既存依存記録で追跡する。hash変更時は担当ownerの既存impactと根拠本文を照合する。構造化計画は01のprojection、Knowledgeは現行entryのscope・status・根拠、通常仕様文書は実際の該当節と有効Authorityを確認する。意味不変を確認できない場合は該当依存を要再検証とする。一般文書の新規fingerprint schema、全節hash台帳、全文検索サービスは不要。

## 実装4 横断分析の起動条件

`qa-workflow/SKILL.md` 横断コンテキスト分析節、`references/guidance.md` の同節、`context-signal-audit` / `context-rule-synthesis` のdescription・開始/停止条件・reference、routing fixturesを改修する。

<!-- dprint-ignore -->
| 条件 | 動作 |
| --- | --- |
| 明示非保存 | 既存Knowledge・成果物を読取参照し、新規永続batch/candidate/run/Knowledgeは作らない。正式A/Bが必須で保存不可なら矛盾を説明し該当範囲のみ未完了 |
| 単発相談・レビュー・調査 | 対話回答を基本とし、再利用価値がある知識だけ許可済み既存ownerへ保存。観察・横断分析が必要ならA/Bを補助起動。保存先不明なら任意蓄積のために依頼を停止しない |
| 利用者が明示無効 | A/Bを起動しない。通常Knowledge・既存仕様の参照は可能。必須目的と矛盾する場合は達成できない範囲を示す |
| 利用者が明示指定 | 指定の対象・必須/補助・範囲に従う |
| 未指定で再利用価値のある単一source観察が必要 | Aを補助として選択。必要な場合にのみ実施 |
| 未指定で複数source/workflowの法則・反例・差異条件の分析が必要 | Bを補助として選択。既存batchやKnowledgeを先に利用し、Aの毎回実行後にBを自動起動しない |
| 分析結果なしに元依頼の必須成果物を成立させられない | 必須として実行前に要求を登録。必要根拠・保存・検証不足は影響scopeを未完了 |
| 有効な過去合意・Knowledgeの直接参照で足りる | A/Bを起動しない |

未指定時の自律起動は現行からの契約変更である。別の設定モードを追加せず、既存の無効・補助・必須・単体利用の意味を利用する。補助の失敗・保存先不明は該当分析の制約として報告し、独立QAを継続する。必須分析は01の許可済みrootの既定 `cross-context/` と既存stateを利用できる場合は追加設定を求めない。必要な許可・保存境界が不足する場合だけ具体的な問題を確認する。

Aの中立観察・不変batch・訂正、Bの独立根拠、反例、候補の適用範囲、7状態・currentnessの区別、root binding、関係候補の条件付き更新、semantic handoff keyを維持する。候補を正式Authority・Product Risk・期待結果へ自動昇格させない。正式期待への採用はspec-analysis等が有効SPEC/DEC/承認済みASM・適用範囲を照合する。未確定・競合はquestion-analysis、未確認の実装差異はinspection/exploratory-testing、確認済み差異はdefect-management、暫定合意はproject-context/spec-analysis、再利用可能知識はqa-knowledge、リスク候補はtest-analysisへ引継ぐ。仮説の引継ぎと正式採用を区別し、反例・scope外・情報不足を解決済みにしない。実owner一意性が確認できない外部handoffはblockし、read-only調査を継続する。

## 検証・完了条件

- `test_workflow_runtime.py`、`test_qa_workflow_runtime.py`、`test_owner_verifier_gate.py`、`test_owner_verifier_registry.py`、`test_owner_scope_resume.py`、`test_runtime_workflow_integration.py`、`test_qa_workflow_baseline.py`、`test_input_revision.py`、`test_context_workflow_state.py`、`test_context_owner_verifiers.py`、`test_context_runtime_transport.py`、`test_context_artifact_store.py`、`test_sqlite_workflow_history.py`、`test_runtime_portability.py` を関連する変更ごとに個別実行する。9個のruntime_contract.pyの同期テストを維持する。
- routing fixtureの未指定/明示無効/補助/必須/単体、Aのみ・Bのみ・既存Knowledge直接参照、開始後の必須追加、全A/B要求の消去、別root/run、別source/range、補助結果の必須流用、未承認除外、独立補助失敗と依存補助失敗を確認する。
- AT-06/07/08/12〜15/17/19/20/21/22/25。変更なし再依頼、部分改版、未承認候補追記、矛盾追加、未列挙source、stale、実副作用不明、登録外意味scopeを含む複合workflow、機械scope0、必須機械scope未達を対比する。
- 不要な全体停止・全再生成・無条件のA/B起動がなく、必要な専門判断と機械検証、元要求、実行・保存・履歴の保証を維持する。機械gateだけで全体完了と判定する経路を残さない。実Agent評価は05で確認する。
