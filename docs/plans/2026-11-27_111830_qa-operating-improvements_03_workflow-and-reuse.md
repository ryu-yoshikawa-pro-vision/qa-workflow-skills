# ワークフロー完了・再利用・横断コンテキスト分析の改修

## 目的・対象

OPS-05・15・18、01・04との接続。依頼に必要な工程と根拠だけを選び、意味上の完了・機械的検証・保存・実行完了を区別する。既存成果物を正しく再利用し、#40の横断分析を必要に応じて自律的に利用する。

## 現状と変更境界

`qa-workflow/scripts/workflow_runtime.py` の `_scope_rows`（L445〜）、`_requested_scope_rows`（L869〜）、`_build`（L1049〜）は要求集合と全scopeを扱う。L1132〜でunrequestedを求めるがL1159〜は全scopeを検証し、L1284〜は未検証をblocking issue、L1375は `can_complete = not issues and bool(scopes) and scope_set_declared` とする。`owner_verifiers.py` は9 owner、`runtime_contract.py` はruntime-v2 root 6。残り24 Skillはこの登録外であり個別の品質判断・専用検証を持つものがある。単体Skillの完了と汎用runtime完了を混同しない。

#40の `context_workflow_state.py` の `record_requested_scopes`、`record_signal_attempt`、`record_synthesis_run`、`complete_context_workflow` は開始時の全要求を保存し、最終のA/B実scope・実readback・runを照合する。`complete_context_workflow` の開始/最終要求照合（L1599〜2058）はA/Bを対象とする。`workflow_runtime.py` の `_verify_context_workflow_completion` は独立した `context_workflow_state_root` により最終入力からA/Bが消えた場合も検出する。これを弱めない。

## 実装1 要求集合と完了判定の分離

`qa-workflow/SKILL.md`、`references/guidance.md`、`assets/workflow-state-template.md` を以下の契約に置換する。各依頼の目的・対象・求められた成果物を起点とし、最短の必要な担当Skillから開始する。開始時に必要な成果物/工程とその依存を確認する。新しい固定工程表を作らない。

- 単発相談・調査・レビュー: 担当Skillの意味品質と必要な形式確認で終了できる。永続state、機械runtime、保存証拠は依頼が要求する時だけ利用する。
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

### 開始後の要求追加

context_workflow_state.py の record_requested_scopes（register-requested-scopes）を既存集合を保全する追加と単調具体化に限定して拡張する。初回の全要求をstateへ保存し、以後は既存集合と追加分の和集合を同じSQLite CAS内で保存する。初回登録と、既存identityを維持した明示的な追加を区別する。追加は既存stateのexpected revisionと追加行・contractを入力とする（全集合の置換ではない）。完全同一追加の再送・既に保存した旧追加要求は現行集合を維持してreused。既存identityの契約変更・削除・縮小・別root・別workflowは拒否。最終要求照合は現行集合を基準にし、旧集合の再送を完了要求の縮小に使わない。新規contractは当該要求の実開始前のみ登録可とし、別要求にattempt/runがあるだけで拒否しない。実行済み別要求のstart_contract・mappingは不変。現在の追加要求集合を全て読戻してから実行する。必要なA/Bは同じworkflow_ref、artifact_root bindingで初回/追加とも登録し、既存source/range/条件、B batch追加、分割・readbackの単調具体化を維持する。既存補助成果物を利用する場合も必須要求として現行根拠・scope・完了証拠を確認し、過去補助runを今回実行済みと偽らない。CAS競合は最新stateを再取得し同じ追加を再照合する。

complete_context_workflow はstateの全必須A/B（開始時と後続追加）を起点に実batch/run・owner検証・最終A/B scopeの完全一致を維持する。workflow_runtime.py の独立context_workflow_state_rootを必須A/Bが一件でも存在するworkflowで維持し、stateのアンカーと最終入力からA/Bを落とした場合をbaseline保存側でも検出する。別root/run、要求置換、未登録contract、後続追加直前/直後の中断、旧集合再送を回帰にする。

### 開始後のscope除外

要求を減らす明示変更は別workflow_refの変更後依頼として扱い、元workflowは当初scopeで未完了/中断のまま履歴を残す。02の実回答と担当QA要求・計画に旧ref、除外scope、理由、依存影響、必要承認を記録し、新workflowで改訂済み要求を登録する。現在有効な成果物・実行結果は通常の再利用条件で引継げるが、旧A/B runを新workflowの今回runへ偽装しない。残る実副作用・必要cleanup・外部操作結果不明は変更後にも未解決として保持し、対象除外で消さない。通常の依頼変更は依頼者の明示回答で成立する。組織の正式品質保証範囲・決裁が関係する場合は既存正式承認を担当ownerで確認し、未確認なら縮小した正式完了を主張しない。全対象取消は取消として報告し完了baselineを作らない。

_exclusion_confirmed は現行v1/v2と汎用機械gateではFalseを維持する。新規の別workflowでは合意済み変更後要求を開始集合とするため、機械入力に excluded_by_approval を混入させない。新認証サービス・汎用承認schemaを作らない。正式承認の真正性をapproval_ref文字列だけから推定しない。承認済み除外の目的は元要求を消さず変更後依頼を進めることで達成する。

### 機械gate、全体完了、baselineの保存・再開

1. workflow_runtime.py _build/_requested_scope_rows は必要機械scopeと依存の集合、expected unit/entity、currentness、owner readback、context completionを従来どおりstrictに照合する。unrequested/unverified/不足のissueを無条件無視しない。新規workflowの can_complete は当該機械対象の結果であり全体完了ではない。
2. 新規凍結pairには generator_contract_version=workflow-runtime-v3 を使用しv1/v2を新解釈で読まない。入力は既存機械projectionを使い、全必須要求と各結果の対応は既存workflow成果物の完了表に保持する。表は元の Skill/target/execution_range、実scope（A/B分割対応含む）、担当成果物ref/revision、検証経路、結果、必要証拠ref、未完了理由を一行ずつ持つ。継続workflowでは開始要求・依存追加・最終要求をstateに保持し表が全件に対応することを機械的に照合する。意味判断は担当Skillとqa-workflowが実際の根拠を読んで行い、表の完了文字列だけで独立品質を証明しない。
3. 機械baselineが必要なworkflowに限り、artifact_graph.py commit_qa_workflow_baseline_local の保存入口で全必須要求の対応、必要機械pair（既存verify_runtime_evidence、owner/context closure）、専用検証結果と実保存refを確認してから immutable Markdownを公開し last_completed_qa_workflow_artifact を進める。任意の完了boolや機械gate単独で進めない。機械scope0のworkflowは機械pairを作らず既存成果物/必要stateから再開する。
4. 既存JSON stateのv1/v2 workflowは現行local baselineの原子的保存・state更新・読取互換を維持する。新規のstateを必要とするworkflowは既存SQLite envelopeを唯一のstateとし、同じroot内の既存immutable baseline artifact保存/readbackを再利用後、conditional_write_sqlite_workflow_state で検証したstate revisionに対しbindingだけ更新する。CAS失敗は旧bindingを維持して最新stateと全要求を再確認する。未参照artifactは完了証拠にしない。別JSON stateへ二重書込みしない。legacy JSON-onlyでv3の継続や必須A/Bを必要とする場合は元stateを移行せず新workflowへ引継ぎ、元の全必須要求・未解決の副作用・再利用範囲を記録する。旧workflowの完了履歴は変更しない。
5. downstream_state.py の _validate_frozen_pair/_WORKFLOW_CONTRACTS/_validate_owner_verification_records/evaluate、artifact_graph.py のbaseline読取、runtime_contract.py verify_runtime_evidence、関連handoff/reporting/fixtureを同時更新する。v3は凍結pairのidentity/hash/必要機械scope、実保存baseline binding、完了表の全要求との対応を検証してから利用する。過去完了を現在採用可とみなさない。v1/v2は現行の厳密な読取・対象外拒否・履歴契約を維持する。SQLite使用時は同じworkflow_refのstateからbindingを取得し、JSONだけを探して欠落と判定しない。新旧が同時に存在する曖昧なstateを推測選択しない。
6. test_integration_required_scopes.py、test_downstream_state.py、test_qa_workflow_baseline.py、test_context_workflow_state.py に機械scope0正常/欠落、必須専用検証未達、機械gate成功だが意味要求欠落、旧凍結pair、新v3、SQLite/JSON binding、CAS競合、追加要求・旧集合再送、変更後の別workflow・旧未完了保持を追加または既存fixtureで確認する。

## 実装3 発見・再利用と変更影響

`qa-workflow/scripts/input_revision.py` の `_sha256_file` と `_compute_document` はファイル変更の検知として維持する。現行guidance L338〜340の「path変更=依存成果物の要再検証」を意味変化の確認へ置換する。`runtime_contract.py` の `compare_entity_dependencies`、`compare_runtime_dependencies`、`upstream_entity_fingerprints`、`machine_entity_dependency`、`resolve_entity_dependencies`、`input_fingerprint` を利用する。`artifact_graph.py compare_used_context`、`test-analysis/scripts/change_impact.py` と各ownerの `impact`/lookupを再利用する。

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
| 明示非保存または単発読取・相談で永続化の要求なし | 既存Knowledge・成果物を読取参照し、新規永続batch/candidate/runは作らない。正式A/Bが必須で保存不可なら矛盾を説明し該当範囲のみ未完了 |
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
