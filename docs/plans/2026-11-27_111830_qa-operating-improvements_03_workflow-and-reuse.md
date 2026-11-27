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

既存workflow stateの `requested_scopes` は開始時の必要範囲を保持する。単発の完結した依頼では対話・成果物が要求記録となり、専用stateを強制しない。継続workflowでは、元の必要scopeを既存stateまたは既存成果物の要求記録として保存し、明示の依頼変更履歴を保持する。現在の要求は元要求と承認済み変更から導く。既存 `workflow_ref` と `Skill + target + execution_range` を使う。

## 実装2 汎用runtimeの変更方法

現在の機械完了契約を全QA活動へ拡張しない。既存 `workflow_runtime.py` を必要な機械scopeの検証に利用し、qa-workflowの最終報告は機械検証・専用検証・意味品質の結果を元依頼と照合する。全39 Skillに機械verifierを追加しない。

1. qa-workflowは元の全要求を保持し、実際に必要なruntime-v2/owner検証scopeを選ぶ。必要な機械検証の依存scopeも含める。独立補助scopeは別の担当結果として報告し、機械scope入力に不要な証拠を混ぜない。登録外で意味検証により成立するscope（例: 単発レビュー、質問分類）は担当成果物・根拠・必要な保存確認を最終報告に記載する。機械検証を要する実行や正式保存の不足を、登録外の意味検証として代替しない。
2. `_build` の `unrequested_scopes` とissueの扱いを見直す。元要求に必要な依存を入力から除外しない。独立補助scopeは機械gateへ渡さず、既存の最終報告で結果・制約を記載する。機械gateに渡されたscopeについては従来のstrictな検証を維持し、未検証scopeのissueを無条件に非blockingへ変えない。互換入力に独立補助scopeが混入した場合は呼出し側で機械対象を再構成し、必要な依存を除外していないことを確認してから再検証する。判断不能な依存は必須側に残す。`can_complete` を単純に全issue無視・`unverified_scopes`無視へ変更しない。機械入力は必要な範囲の全証拠を照合し、必須scope不足・stale・偽証拠・閉鎖性違反を拒否する。
3. `_requested_scope_rows` は機械検証対象を表す既存入力として維持する。全要求を保持する既存state/最終報告から機械対象への対応を確認する。登録外の意味scopeと専用検証scopeは機械完了と別に結果を保持し、元要求に対し必要な結果が不足していればworkflow全体を完了にしない。機械scopeが0なら従来どおりdispatchしない。必要な機械scopeが1以上の場合、既存の `verify_runtime_evidence` と `workflow_runtime.py` の両方を実行する。
4. `can_complete` はその機械検証要求についての結果と明記し、全体完了の単独根拠にしない。最終のqa-workflow成果物には元の全要求の結果を記載し、意味検証の結果と実保存/実行証明の根拠、独立補助制約を区別する。既存 `last_completed_qa_workflow_artifact` の更新は機械gate成功だけでなく、必須全範囲の確認後に限定する。`artifact_graph.py commit_qa_workflow_baseline_local` のstate更新入口、`downstream_state.py _validate_frozen_pair` の凍結済みruntime対と `_validate_owner_verification_records`、`runtime_contract.py verify_runtime_evidence`、reporting/owner verifierと関連fixtureにおける `can_complete` 消費経路を修正する。既存のbaseline本文とstateの元要求に対し、全必須scopeの結果・実成果物ref・必要検証が対応することを保存前に照合する。機械scopeの結果は機械root pairから確認し、意味scopeは担当成果物・必要な根拠の確認結果と区別する。利用者やLLMが作る任意の完了boolのみでbaselineを進めない。旧版の凍結pairは旧契約で読み戻し、旧機械scopeを新たな意味scopeへ読み替えない。過去のbaselineの完了を現在の未達で改変しない。
5. #40の必須A/Bは既存 `context_workflow_state.py register-requested-scopes` に全開始要求を登録する。機械入力の `requested_scopes` に最終A/B実scopeを必ず含め、`context_workflow_state_root` を独立して渡す。`complete_context_workflow` のA/B mapping、source/range/条件、開始時root、state revision、実readback検証を維持する。普通の意味scopeを機械projectionから外しても、元全要求はstateから除かない。A/B消去・別run・補助からの流用を拒否する。開始後に必要性を発見したA/Bは実行前に追加要求を記録する。既存 `record_requested_scopes` のset-onceを無条件に上書きしない。必要な追加に限り既存stateのCAS内で元集合を保全したappend/具体化を行う。既存contract・実行済みmapping・要求範囲の置換/縮小は禁止。追加できない場合は新たな必要scopeを未完了として扱う。要求追加・再送・途中中断の否定試験を作る。
6. 完了の意味判断に必要な成果物、登録範囲、実際の証拠が現在有効かを確認する。全体の意味判断はqa-workflowで行うが、機械的に証明できる対象・状態・根拠の整合は既存validatorで扱う。機械的な `valid` を人間の内容承認や専門品質の証明にしない。新しい全Skill共通の保存証明schemaや汎用validatorは作らない。

### 開始後のscope除外

02で保持した通常の依頼範囲変更・正式対象外判断を用いる。通常の利用者による新しい依頼scopeの合意は、元要求と変更後要求を分けて扱い、元の未完了範囲を明示する。変更後の必要範囲で機械検証と意味完了を行う。開始時の要求から黙って消すことはしない。

正式な必須scope除外で `excluded_by_approval` を利用する場合、`_exclusion_confirmed()` の現状（常にFalse）を無条件に緩めない。対象ownerの既存正式な決定記録を、当該scope・元要求・必要な決裁権限・承認対象revision・失効条件と照合できる経路だけ確定可能とする。通常内容承認は依頼者の実回答を根拠に担当成果物/質問回答へ記録する。機械CLIに渡された `approval_ref` やAgent自己申告のみでは真正性を主張しない。正式な権限者照合経路が必要で未接続なら該当scopeの除外は未確定を維持する。A/Bの開始要求を除外する場合も旧stateを削らず、明示変更後の要求・履歴・未完了範囲が対応することを#40契約と照合する。変更後の依頼が別workflowとして扱われる場合は元workflowを完了扱いにしない。

## 実装3 発見・再利用と変更影響

`qa-workflow/scripts/input_revision.py` の `_sha256_file` と `_compute_document` はファイル変更の検知として維持する。現行guidance L338〜340の「path変更=依存成果物の要再検証」を意味変化の確認へ置換する。`runtime_contract.py` の `compare_entity_dependencies`、`compare_runtime_dependencies`、`upstream_entity_fingerprints`、`machine_entity_dependency`、`resolve_entity_dependencies`、`input_fingerprint` を利用する。`artifact_graph.py compare_used_context`、`test-analysis/scripts/change_impact.py` と各ownerの `impact`/lookupを再利用する。

手順:

1. 01の許可root/direct refと既存ownerで正本を発見する。取得範囲・母集団、必要なsourceの一覧、owner・scope・identity・現在のrevisionを確認する。欠落、重複、読取不能、一覧打切りを区別する。path一致だけで同一意味としない。対象外のartifactの不明を全体の停止に拡大しない。
2. source revision/hash・製品build・利用したContext field・実際に参照したAuthority/Entity・owner成果物のcurrentnessを比較する。入力母集団の変更・外部資料の改版・前回未取得sourceの取得可能化も確認する。未列挙inputの存在を `same` とみなさない。
3. ファイルhashが変わっても、利用した承認済みAuthority/EntityやContext field、入力集合・前提条件が同じなら、関連する既存成果物を再利用する。例: 未承認の別候補・質問の追記、表示だけの変更。変更が当該候補との矛盾・例外・反例を生じる場合は根拠を再評価する。単に候補欄の変更を無条件無視しない。
4. 利用した意味が変わった場合は依存関係から影響scopeだけを要再検証に戻す。spec-analysis→test-analysis→TR→TCN/CI→TCの既存Entity・scope ownership・partial rerun・carry-forward・retirement・coverageを維持する。`downstream_state.py`、`migration_preflight.py`、各runtime generatorの現行経路に従う。全成果物の再生成を既定としない。前回完了したbaseline/過去報告は履歴として保持し、現在の採用可否と区別する。
5. qa-knowledgeの `lookup`、`plan_revalidation`、`update_entry`、`read_entry` 等は既存entry形式で使用する。Knowledgeの利用は追加2 Skillの起動や新規保存を条件としない。#40の軽量projection・既存owner検索・本文の選択取得を利用し、全データの読込や新規全文検索基盤を前提としない。

## 実装4 横断分析の起動条件

`qa-workflow/SKILL.md` 横断コンテキスト分析節、`references/guidance.md` の同節、`context-signal-audit` / `context-rule-synthesis` のdescription・開始/停止条件・reference、routing fixturesを改修する。

<!-- dprint-ignore -->
| 条件 | 動作 |
| --- | --- |
| 利用者が明示無効 | A/Bを起動しない。通常Knowledge・既存仕様の参照は可能。必須目的と矛盾する場合は達成できない範囲を示す |
| 利用者が明示指定 | 指定の対象・必須/補助・範囲に従う |
| 未指定で再利用価値のある単一source観察が必要 | Aを補助として選択。必要な場合にのみ実施 |
| 未指定で複数source/workflowの法則・反例・差異条件の分析が必要 | Bを補助として選択。既存batchやKnowledgeを先に利用し、Aの毎回実行後にBを自動起動しない |
| 分析結果なしに元依頼の必須成果物を成立させられない | 必須として実行前に要求を登録。必要根拠・保存・検証不足は影響scopeを未完了 |
| 有効な過去合意・Knowledgeの直接参照で足りる | A/Bを起動しない |

未指定時の自律起動は現行からの契約変更である。別の設定モードを追加せず、既存の無効・補助・必須・単体利用の意味を利用する。補助の失敗・保存先不明は該当分析の制約として報告し、独立QAを継続する。必須分析は01の許可済みrootの既定 `cross-context/` と既存stateを利用できる場合は追加設定を求めない。必要な許可・保存境界が不足する場合だけ具体的な問題を確認する。

Aの中立観察・不変batch・訂正、Bの独立根拠、反例、候補の適用範囲、7状態・currentnessの区別、root binding、関係候補の条件付き更新、semantic handoff keyを維持する。候補を正式Authority・Product Risk・期待結果へ自動昇格させない。既存SPEC/DECが裏付ける場合のみ担当ownerへ反映し、反例・scope外・情報不足は候補のままとする。実owner一意性が確認できない外部handoffはblockし、read-only調査を継続する。

## 検証・完了条件

- `test_workflow_runtime.py`、`test_qa_workflow_runtime.py`、`test_owner_verifier_gate.py`、`test_owner_verifier_registry.py`、`test_owner_scope_resume.py`、`test_runtime_workflow_integration.py`、`test_qa_workflow_baseline.py`、`test_input_revision.py`、`test_context_workflow_state.py`、`test_context_owner_verifiers.py`、`test_context_runtime_transport.py`、`test_context_artifact_store.py`、`test_sqlite_workflow_history.py`、`test_runtime_portability.py` を関連する変更ごとに個別実行する。9個のruntime_contract.pyの同期テストを維持する。
- routing fixtureの未指定/明示無効/補助/必須/単体、Aのみ・Bのみ・既存Knowledge直接参照、開始後の必須追加、全A/B要求の消去、別root/run、別source/range、補助結果の必須流用、未承認除外、独立補助失敗と依存補助失敗を確認する。
- AT-06/07/08/12〜15/17/19/20/21/22/25。変更なし再依頼、部分改版、未承認候補追記、矛盾追加、未列挙source、stale、実副作用不明、登録外意味scopeを含む複合workflow、機械scope0、必須機械scope未達を対比する。
- 不要な全体停止・全再生成・無条件のA/B起動がなく、必要な専門判断と機械検証、元要求、実行・保存・履歴の保証を維持する。機械gateだけで全体完了と判定する経路を残さない。実Agent評価は05で確認する。
