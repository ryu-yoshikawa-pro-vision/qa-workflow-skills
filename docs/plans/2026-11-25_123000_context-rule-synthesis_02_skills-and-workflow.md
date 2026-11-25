# Skill・workflow・既存owner連携

親: [実装Plan](2026-11-25_123000_context-rule-synthesis.md)。保存契約は[01](2026-11-25_123000_context-rule-synthesis_01_storage-and-contracts.md)。

## 1. 実装配置と責務

- skills/context-signal-audit/{SKILL.md,assets/,references/,scripts/,evals/}、skills/context-rule-synthesis/{SKILL.md,assets/,references/,scripts/,evals/}を追加。SKILL.mdは選択条件・責務・入出力・短い手順、詳細のdata-contract/guidanceとサンプルJSONはreferences/assetsに置く。必要時だけ読み込む。通常出力には人が確認できる短い要約を付け、保存JSONと重複する第二の正本を作らない。
- production helperの候補: Aのbatch identity/validate、Bのcandidate/run identity/validate/impact/completion_checkを各Skill scriptsに置く。共通のcanonical処理が必要なら既存のSkill-local copy同期規約を使うか、保存ownerの共通helperを明示依存として利用する。単体Skillで参照先がない場合は分析案作成を続け、保存・完了のみ未確認とする。全共通runtime複製やeval validatorの本番利用は不要。関数/CLIの分割は実際の処理量に従う。
- qa-workflow/SKILL.md、references/guidance.md、assets/workflow-state-template.mdへ起動・試行state・局所停止・再利用を追加。owner_verifiers.py、runtime_contract.py（Skill-localコピー同期）、READMEのcatalog、EVALS、必要な固定registry/fixtureを更新。workflow_runtime.pyやdownstream_state.pyは既存共通処理で成立するなら変更しない。
- runtimeの機械検証とAIの意味判断を分離。意味的な抽出漏れ、表現ゆれ、仮説の比較、反例分類、owner選択のために固定語彙・固定スコア・全資料の再取得を要求しない。

## 2. A: context-signal-audit

入力: project_ref/許可root、workflow_ref/scope、environment/version、source ref/revision/hash、requested/actual inspected range、取得完全性、本文。任意: 関連candidate metadata。既存の成果物（仕様、回答、実装確認、探索等）を読むだけで、深い横断探索・裁定・正本更新はしない。

1. workflowの決定論的判定から未処理入力だけを受け取る。取得範囲とsource hashを確認し、観察条件が意味を変える場合だけidentityに含める。
2. 同一成果物から他機能にも適用し得る中立的観察を抽出。共通構造だけでなく差異の発生条件、未承認回答の区別を保持。関連候補がなければ支持/反例を強制しない。候補metadataがあれば潜在反例/競合を照合する。取得不能/未提供はnot_checked、確認済み反例なしとは区別する。
3. helperによる構造検証後、実取得範囲確定・正常抽出時のみimmutable batchを保存。正常0件も記録。取得失敗/partial/抽出失敗/保存失敗は既存workflow stateへ反映し正常再実行を可能にする。
4. Bへの優先起動理由は既存候補・正式根拠との重大競合を主とする。通常観察やnot_checkedは蓄積して次の適切な契機へ。固定件数の閾値をコードに強制しない（案件の負荷・論点に応じてまとめる）。

## 3. B: context-rule-synthesis

入力: project_ref/許可root/workflow_ref、requested scope・分析観点・横断属性・環境/version、対象batch・候補・前回run、既存Authority/回答/Knowledge/調査成果物、検索条件と完全性。

### 分析手順

1. 許可rootの候補・batch・過去回答・仕様/DEC/ASM・Knowledge等を軽量発見する。provider listと既存ownerのread/scanを使い、scopeだけで除外しない。横断属性、同義概念、対象操作、条件等で絞り、必要な本文だけを取得。qa-knowledge.lookupの正式適用scopeを緩めず、read_root_entries/scan_knowledge_rootの発見後、既存lookup/compare_currentness等で適用可能性を確認する。中央indexは作らない。導入前の既存根拠も対象。
2. 直接参照全ソースと検索条件、取得完全性をsnapshotへ記録。completeは指定した列挙・検索・確認手順が終わったことを表す。未知の根拠が絶対に存在しないとは主張しない。取得失敗を空検索としない。
3. 同一コンポーネント、同一仕様書、改訂再取得による同一観察をindependence_groupでまとめる。観察件数だけで根拠の強度を決めない。
4. 共通法則と差異条件を比較。例: 「管理者」対「復元不能な削除」など相関する複数仮説は独立候補にし、competing_hypothesis/alternativeを関係づけ、必要な判別調査を特定。1候補1独立仮説、関係数・候補数の固定上限は設けない。
5. 候補ごとに支持、反例、未観察、判定不能、対象外を区別。未観察を反証にしない。反例原因6分類（01参照）で根拠不足はunclassified。governing_conditionsへ意味条件を構造化しapplicabilityと整合させる。
6. 有効なSPEC/DEC/承認済みASMと照合。spec-analysis/references/authority-resolution.mdの適用範囲、補足/上書き/置換、失効・現在性の契約に従う。観察多数で有効仕様を上書きしない。未承認ユーザー回答は正式決定にも確定却下にも昇格させない。
7. 過去の候補・回答・却下範囲を照合し、同義重複は01の並行安全な手順で統合する。安全に統合できない場合は独立候補として保持し他分析を続ける。
8. 追加調査の必要性を判断し、既存ownerへ局所handoff。既に確認した同じsource hash/条件でno_new_infoなら再調査せず質問/保留へ。一時障害は認証/権限/環境/安全承認の解消でrevision不変でも再開可能。必要な調査を回数だけで打切らない。実観測はexploratory-testingのinvestigationと既存成果物を使い、exploratory_runtime.pyの既存handoff先制約は変更しない。
9. 予定集合をrunへ保存し候補更新/readback、必要handoffの到達確認、run完了。候補0件もrunを保存。候補の未解決自体は分析失敗ではない。調査/質問handoffが成立していれば分析工程は完了できる。

### 既存ownerの振り分けと冪等照合

- 業務規則/UI/データ不変条件/状態/権限 → spec-analysis。有効SPEC/DECが全範囲を裏付けるならresolved（実装未観測はunverified）。確認済みFAIL/Findingによる不一致はdefect-management、コード推論のみなら担当調査/探索へ。部分裏付けはcoverage=partialでinvestigating、必要なら分割。有効Authorityと局所適用を維持する。
- 仕様不明 → spec-analysisで正式UNKNOWNを生成・確認してからquestion-analysisへ。question_ids.pyの現行UNKNOWN参照検査を保持し、候補IDをUNKに偽装しない。仕様UNKNOWNでない任意確認はunknown_ref=nullで既存4分類を使う。回答受領と意味解決は別。質問前に既存Q/revision/scope/正規化意図/現行Authorityを照合し、却下候補を理由に未解決の個別仕様を省略しない。
- 共通実装構造 → test-target-inspection/ui-target-analysisの保存済みinspectionを照合してINSPECTIONとしてresolved。実装構造を仕様へ昇格しない。
- 不具合傾向/正式Product Risk → test-analysis、確定QA知識/手順 → qa-knowledge、環境制約 → project-context。qa-knowledgeのentry identity/scope/依存/currentness、plan_create/update/replacementを再利用し未検証FindingをKnowledgeへ書かない。承認済みASM/PROJECT_CONTEXT/PRODUCT_RISK/KNOWLEDGEを正式SPECと誤認しない。
- spec-analysisはAuthority/UNKNOWNのref、question-analysisはQと正規化回答/現行UNKNOWN、project-contextは有効DEC/ASM/配置、qa-knowledgeはcanonical_entry_ref、test-analysisは正式Risk/Machine Entity、inspectionはscope/environment/build/ref、defect-managementは確認済みFinding/FAILと既存defect refを既存照合点とする。これらは意味的冪等照合の候補であり、各ownerの正式保存とCASの実入口を実装着手時に確認。PR #38の3 owner保存契約と整合させる。既存ownerのread/lookup→意味的重複判定→既存承認経路→native CAS→readbackを使う。未提供ownerの保存を新Skillが肩代わりせず、必要時のみ最小接続を追加する。安全に反映済みか確認できないhandoffはblocked_unverifiable、別候補は進める。

## 4. workflow起動・再利用・モード

起動判定の純粋helperは既存state、入力hash、保存batch、完了run、要求範囲を比較し、Aの未実行/失敗/変更を判断する。BはAごとの自動起動をしない。重大な反例/競合、新機能QA開始時、下流テスト設計/仕様根拠確定の直前、案件に適した蓄積契機、明示指示で起動する。complete 0件のみではBを起動しない。未処理not_checkedを下流直前まで放置しない。Bの対象バッチ集合は要求scope・観点・環境が一致する最新完了runのtarget_batch_refsと比較する。別観点では過去batchも再利用可能。最新runだけで処理済み集合が失われるなら対象集合を累積して保存し、毎回全本文を再読しない。処理済みnot_checkedの無限起動を防ぐ。

再利用は要求範囲/観点/環境/入力内容hash不変、関連未処理batchなし、候補・全直接参照ソース・Authority有効性/Entity fingerprint不変、取得可能化や新規反例なしの全条件で判断する。Git HEAD単独では判定しない。候補更新のみでは既存テスト設計をstaleにしない。正式SPEC/DEC/ASM/PROJECT_CONTEXT/Knowledge/Riskが変化したとき既存artifact_graph.compare_used_context・Machine Entity dependencyで影響範囲のみ再検証する。

新機能開始時: 対象決定→横断発見→hashとAuthority鮮度確認→spec-analysisのAuthority解決→残存不明点をquestion-analysis→下流へ。未承認仮説は探索/調査/観点候補として渡し、PASS/FAIL期待値には使わない。未評価反例が出た場合は当該判断のみ再評価する。

モード:
- 無効/無指定: A/Bを起動せず既存state、要求集合、処理負荷を変えない。
- 補助: requested_scopes/workflow_scopesに含めない。未設定not_configured、失敗/partialは補助未完了と記録し既存工程の完了を破壊しない。利用できる候補や根拠を表示する。
- 必須: 明示要求または案件必須設定を開始時requested_scopesに記録。未設定・不完全・認可不足でも要求から除外しない。該当scopeを未完了/blocked、他scopeは継続。
- 単体: 指定Skillだけを起動、read-only分析案は可能、正式保存/完了に必要な設定がない場合はその操作を停止。同じverifierを利用。

A試行stateは既存workflow_refごとのstate envelopeに必要時のみ追加（例: state.context_signal_attempts）。operation ID/入力ref/hash、要求/実取得範囲、batch ref/revision、candidate_check、status=unexecuted|fetch_failed|partial|extract_failed|persist_failed|completed、失敗理由、再開条件。補助not_configuredは設定状態として別記録。既存native CAS state providerで更新。exact-content tokenをCASと誤認せず、未設定ならセッション内の試行結果を保存済みと称さない。Bのrun refと再開先を既存stateに参照として保持。第4成果物storeは作らない。

## 5. owner verifierと完了

runtime-v2 rootを新設せず、owner_verifiers.VERIFIERSおよびruntime_contract.OWNER_VERIFIED_SKILLSへ2 Skillを登録、全同一runtimeコピーを同期。既存 _stored_owner_artifact のvalidate/validate_readbackを利用。Aは要求入力全件を一件ずつscopeとして宣言（targetは完全取得時の決定論的batch ref、execution_rangeは要求範囲のcanonical表現）。開始時に入力ref/hashと要求範囲を確定できない場合は要求scopeを未完了として保持し、特定後に既存の要求集合記録を更新する。scopeの消失で完了させない。全要求入力が網羅されていることをhostとverifierで検証し、1 batchだけで全件完了にしない。B targetはrun ref。Bの候補全件のreadback・予定hash・snapshot・必要handoffを実providerからhostが取得し、owner helperのcompletion_checkへ渡す。候補単体もvalidate/validate_readbackを提供。

normalized_input.owner_verificationは保存本文のcanonical JSON文字列、expected_revision、readback（content_hash等）、要求入力集合/根拠/候補/handoffの照合に必要な実readbackを受ける。正確なフィールドは既存verifierのkeysと再開記録のverified_artifactに合わせる。owner CLIは保存本文・identity/ref/path・project・hash/範囲・完全性・0件理由・予定集合・currentness/引継ぎを確認する。hostが実readbackを供給し、AIによる同形JSONの自己申告では正式完了しない。既存runtimeが信頼済みhost入力と任意CLI入力を区別できない点は、host内で完了検証を実行し証拠受渡しを管理する。独立readbackを取得しない任意CLI呼出しの結果を正式完了として採用しない。

partial/failed、必須handoff pending/blocked_unverifiableは未完了。質問成果物/調査依頼の保存・到達が確認できれば未回答でも分析完了可能。完了記録と最新結果の採用を分離し、外部変更で旧runを再利用できなくても保存された実行履歴を消さない。current_structure_state=null、verified_owner_scopesの既存記録形式と保存済みv2再開を維持。workflow_runtimeの汎用gateで足りなければ共通原因の最小修正だけ行い、新たな専用workflowエンジンは作らない。
