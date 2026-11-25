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

判定は元の基本設計9.2の全行を維持する。業務規則・UI仕様・データ不変条件・状態遷移・権限制御のAuthorityはspec-analysisの責務。以下は意味判断のガイドであり、固定語彙による自動裁定ではない。

- 有効SPEC/DECが全範囲を裏付け、実装一致を確認した場合: `resolved`、SPEC/DEC参照、`conforms`。spec-analysisのAuthorityを維持。
- 全範囲を裏付け、実装未確認の場合: `resolved`、SPEC/DEC参照、`unverified`。実装確認は別管理。
- 全範囲を裏付け、既存FAIL/Findingで不一致確認済みの場合: `resolved`、SPEC/DEC参照、`confirmed_mismatch`。defect-managementへ渡し、仕様質問には戻さない。
- 全範囲を裏付けるがコード推論のみで不一致を疑う場合: `resolved`、SPEC/DEC参照、`unverified` と調査ref。担当調査Skillまたはexploratory-testingへ渡し、確定FAIL扱いしない。
- 一部範囲のみ裏付ける場合: `investigating` と `coverage: partial` を維持、または独立管理が必要なら01の手順で分割して旧候補をsuperseded。spec-analysisと残余範囲の調査・質問へ。
- 承認済みASMによる暫定解決、環境・実施条件確定: `resolved`、ASMまたはPROJECT_CONTEXTの参照。project-context/spec-analysisへ。正式SPECとは区別する。
- 実装観察のみで正式仕様なし: `investigating`、INFERENCE扱い。追加調査後、未解決ならspec-analysisでUNKNOWN化してquestion-analysisへ。
- 共通コンポーネント等の実装共通構造: `resolved`、INSPECTION。test-target-inspection/ui-target-analysisの保存済みinspectionを照合する。仕様へ昇格しない。
- 有効SPEC同士の競合、適用範囲・例外・合否根拠不明: `investigating`、question_refs。spec-analysisで正規UNKNOWNを生成・確認してquestion-analysisへ。`question_ids.py` の現行UNKNOWN参照検査と既存4分類を保持し、候補IDをUNKに偽装しない。回答受領≠意味解決。
- 仕様UNKNOWNでない任意確認・調査相談: `investigating` または `deferred`、`unknown_ref: null`。question-analysisへ。
- 不具合傾向・リスク候補、環境制約、テスト実施手順: test-analysis/qa-knowledge/project-contextへ。既存知識で解決済みなら既存refを再利用し、新規反映のreadback後は `resolved`（PRODUCT_RISK/KNOWLEDGE/PROJECT_CONTEXT）。未検証FindingをKnowledgeへ書かず、正式SPECとも区別する。

追加調査は基本設計9.1に従う。仕様書・決定事項・過去回答はspec-analysis、画面・実装構造・共通コンポーネントはtest-target-inspection、UI構造・画面遷移・状態の継続分析はui-target-analysis、実操作による仮説・反例検証はexploratory-testingのinvestigationへ。手順8の終了・再開条件を全経路へ適用する。

既存ownerの意味的冪等照合は次の対象・根拠・revisionを使用する。現行mainに全owner共通の正式保存APIが存在するとはみなさない。実際のowner保存・CASは既存経路を使い、未対応箇所だけ最小接続を行う。

- spec-analysis: `references/authority-resolution.md` の有効Authorityとscope、SPEC/DEC/ASM/UNKNOWNのref・revision・content hash。現行根拠が同じ意味を既に確定している場合は再発行しない。
- question-analysis: `scripts/question_ids.py` の `validate_links` と既存Q履歴、question ref/revision、現行UNKNOWN、正規化された質問意図・回答scope・承認状態。過去回答の適用可能性を確認してから質問を再利用し、未解決の個別仕様質問を却下候補だけで省略しない。
- project-context: `scripts/project_context.py` の `prepare_ids`、`prepare_placement`、`persist_prepared`（project-context専用）、有効DEC/ASMのscope・ref・revision・承認。既存正本に同一内容がある場合はreuse。
- qa-knowledge: `scripts/knowledge_runtime.py` の `canonical_entry_ref`、`lookup`/`lookup_root`、`compare_currentness`、`plan_create`/`plan_update`/`plan_replacement`、entryのidentity・scope・依存・現行revision。正式適用scopeは維持。
- test-analysis: 正式Product Risk・テスト重点の既存ref、scope、依存するMachine Entity fingerprint。`scripts/analysis_entities.py` のentity依存と既存成果物を照合し、既採用のリスク・重点を重複登録しない。
- test-target-inspection: `references/guidance.md` の対象/要素/状態キー、確認条件、build、保存ref/revision、immutable証跡。ui-target-analysis: `scripts/human_editing.py` のcurrent package・stable IDと既存scope、source ref/revision。正本の同一構造を再利用する。
- defect-management: `scripts/defect_runtime.py` の `candidate_ref`、`operation_id`、`assess_candidate`、`plan_external_operation` と既存FAIL/Finding・defect ref/revision。既存外部課題の反映結果を確認し、同じ不一致を再登録しない。

各handoffで、既存ownerのread/lookup→意味的重複判定→既存承認経路→native CAS→readbackを使用する。CAS競合後は必ず再読取して同一意図の反映済みを再確認する。PR #38の3 owner保存契約が統合された場合はその正式経路と照合する。各ownerの具体的な保存API・実host/外部providerのCAS・承認接続は着手前に確認し、未確認の経路を既存APIとして扱わない。新Skillは既存ownerを肩代わりしない。結果不明で冪等性が保証できないhandoffのみblocked_unverifiableとし、他候補を継続する。

## 4. workflow起動・再利用・モード

起動判定の純粋helperは既存state、入力hash、保存batch、完了run、要求範囲を比較し、Aの未実行/失敗/変更を判断する。BはAごとの自動起動をしない。重大な反例/競合、新機能QA開始時、下流テスト設計/仕様根拠確定の直前、案件に適した蓄積契機、明示指示で起動する。complete 0件のみではBを起動しない。未処理not_checkedを下流直前まで放置しない。Bの対象バッチ集合は要求scope・観点・環境が一致する最新完了runのtarget_batch_refsと比較する。別観点では過去batchも再利用可能。最新runだけで処理済み集合が失われるなら対象集合を累積して保存し、毎回全本文を再読しない。処理済みnot_checkedの無限起動を防ぐ。

再利用は要求範囲/観点/調査条件/環境/入力内容hash不変、関連未処理batchなし、候補・全直接参照ソース・Authority有効性/Entity fingerprint不変、取得可能化や新規反例・独立支持根拠なしの全条件で判断する。Git HEAD単独では判定しない。本文hashが同じでも上位DECによる上書き、ASM失効、Knowledge置換、build・環境・権限変更、過去回答のscope/revision/承認状態の変化、Machine Entity fingerprint変化を再評価する。新規反例や独立支持は軽量一覧の差分から検知し、同一観察の再取得は独立支持に数えない。deferredの論点が後続QAで合否必須化された場合、一時障害が解消した場合もrevision不変でinvestigatingへ戻す。候補更新のみでは既存テスト設計をstaleにしない。正式SPEC/DEC/承認済みASM/PROJECT_CONTEXT/Knowledge、test-analysisの正式Product Risk・テスト重点が変化した場合のみ既存artifact_graph.compare_used_context・Machine Entity dependencyで影響範囲を再検証する。

新機能開始時: 対象決定→横断発見→hashとAuthority鮮度確認→spec-analysisのAuthority解決→残存不明点をquestion-analysis→下流へ。未承認仮説は探索/調査/観点候補として渡し、PASS/FAIL期待値には使わない。未評価反例が出た場合は当該判断のみ再評価する。

モード:
- 無効/無指定: A/Bを起動せず既存state、要求集合、処理負荷を変えない。
- 補助: requested_scopes/workflow_scopesに含めない。未設定not_configured、失敗/partialは補助未完了と記録し既存工程の完了を破壊しない。利用できる候補や根拠を表示する。
- 必須: 明示要求または案件必須設定を開始時requested_scopesに記録。未設定・不完全・認可不足でも要求から除外しない。該当scopeを未完了/blocked、他scopeは継続。
- 単体: 指定Skillだけを起動。保存先・認可等の実行条件不足時は正式な単体実行を停止し、同じverifierを利用する。利用者が別途読み取り・分析案を求める場合は可能な範囲で対応し、正式保存・正式完了とは区別する。

A試行stateは既存workflow_refごとのstate envelopeに必要時のみ追加（例: state.context_signal_attempts）。operation ID/入力ref/hash、要求/実取得範囲、batch ref/revision、candidate_check、status=unexecuted|fetch_failed|partial|extract_failed|persist_failed|completed、失敗理由、再開条件。補助not_configuredは設定状態として別記録。既存native CAS state providerで更新。exact-content tokenをCASと誤認せず、未設定ならセッション内の試行結果を保存済みと称さない。Bのrun refと再開先を既存stateに参照として保持。第4成果物storeは作らない。

## 5. owner verifierと完了

runtime-v2 rootを新設せず、owner_verifiers.VERIFIERSおよびruntime_contract.OWNER_VERIFIED_SKILLSへ2 Skillを登録し、全同一runtimeコピーを同期する。既存 `_stored_owner_artifact` のvalidate/validate_readbackを利用する。現行 `_scope_identity` は(skill, target, execution_range)で、`_scope_rows` と `_requested_scope_rows` は重複を拒否する。targetは最終的に実保存成果物の `artifact_ref` と一致させる。

### 開始時の要求と保存成果物の対応

- Aは開始時に要求された全入力を一件ずつ、Bは要求された分析範囲・観点・調査条件ごとに記録する。要求入力の元refまたは明示された対象識別、要求範囲、観測/分析条件、workflow_refを保存し、内容hash確定前でも要求を区別する。識別できない集合は未確定要求として残し、空集合として完了させない。
- 開始時点で実成果物refが確定している要求は既存のrequested_scopesへ直接記録する。未確定の場合は、同じworkflow内の要求識別から決定論的に作る一意の仮target（例: `request:<sha256>`）をrequiredとして記録し、既存workflow stateの要求記録に対応する元入力・範囲を保持する。仮targetは成果物refではなく、owner verifierの完了証拠にはしない。未確定scopeはworkflow_scopesへ完了scopeとして渡さず、既存のrequired_scope_missingで未完了にする。
- 入力hashと実取得範囲・観測条件が決まったらAの保存batch ref（過去の広いbatchを再利用する場合も実際のref）またはBのrun refに対応付け、元の要求と現在の実行範囲を維持したrequested_scopesへ具体化する。Aのexecution_rangeは今回要求した範囲のcanonical表現とする。Bは今回要求した分析範囲・観点・条件を区別する。内容hashを得ただけで要求範囲を狭めない。複数要求が同一batchを参照する場合は個別の要求範囲・条件を全件照合し、同一の最終scope identityになる本当に同じ要求のみ重複排除する。
- 元の要求集合と確定後scopeの対応、未確定・未取得・失敗の要求を既存workflow stateに保持する。stateの既存native CASで対応付けと要求集合を更新し、競合時は再読取。要求追加・変更とref具体化を区別し、具体化で元要求を削除しない。条件変更は新しいoperationとして扱う。元要求との対応が欠ける場合は該当要求をrequiredのまま残す。新しい要求管理ストアは作らない。
- hostはruntimeへ渡すrequested_scopes/normalized_input.owner_verificationが元要求を全件網羅し、確定ref・範囲と実readbackが対応することを確認する。owner verifierは当該scopeの範囲、元入力、観測条件、実readbackを検証し、既存runtimeは最終scope集合の全件完了を検証する。再開時も保存済みの元要求と対応、凍結済みruntime証拠・verified_owner_scopesを照合する。現在の共通処理で元要求の消失を検知できない場合のみ、共通gate/再開処理を必要範囲で修正する。新runtime-v2 rootや別workflowエンジンは作らない。

### 完了証拠

Aは全要求入力について、保存本文の初回 `scan_completeness` と今回の取得完全性を区別し、01 §3の範囲包含・source hash・観測条件・正常抽出・実readbackで今回のcompleteを再計算する。過去partialでも今回の要求全域を満たす場合は完了可能。逆に初回completeだけを根拠に今回の広い要求を完了としない。必要に応じて既存バッチの再利用を優先し、不足分を取得する。単一バッチで全件完了を自己申告しない。

Bのtargetはrun ref。候補全件のreadback・予定hash・snapshot・必要handoffを実providerからhostが取得し、owner helperのcompletion_checkへ渡す。候補単体もvalidate/validate_readbackを提供。

normalized_input.owner_verificationは保存本文のcanonical JSON文字列、expected_revision、readback（content_hash等）、要求入力集合/根拠/候補/handoffの照合に必要な実readbackを受ける。正確なフィールドは既存verifierのkeysと再開記録のverified_artifactに合わせる。owner CLIは保存本文・identity/ref/path・project・hash/範囲・完全性・0件理由・予定集合・currentness/引継ぎを確認する。hostが実readbackを供給し、AIによる同形JSONの自己申告では正式完了しない。既存runtimeが信頼済みhost入力と任意CLI入力を区別できない点は、host内で完了検証を実行し証拠受渡しを管理する。独立readbackを取得しない任意CLI呼出しの結果を正式完了として採用しない。

今回の要求に対して取得不完全なpartial/failed、抽出失敗、必須handoff pending/blocked_unverifiableは未完了。Aの過去partialの再利用は上記の現在の要求範囲の照合で判定する。Bのpartial/failed runは未完了。質問成果物/調査依頼の保存・到達が確認できれば未回答でも分析完了可能。完了記録と最新結果の採用を分離し、外部変更で旧runを再利用できなくても保存された実行履歴を消さない。current_structure_state=null、verified_owner_scopesの既存記録形式と保存済みv2再開を維持。workflow_runtimeの汎用gateで足りなければ共通原因の最小修正だけ行い、新たな専用workflowエンジンは作らない。
