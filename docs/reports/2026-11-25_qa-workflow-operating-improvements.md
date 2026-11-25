# QAワークフロー運用上の改善候補

基準: main 197f1e0e1abe870b0cc793355e7abf73bf241d87（2026-11-25）。全37 QA Skillと主要reference・runtime、[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)を静的に照合した。以下は未着手の改善候補であり、実装指示・承認済みPlan・既存受入条件の変更ではない。優先度は暫定（P0: 安全・誤完了、P1: 継続性・運用負担、P2: 接続・効率）。案件別保存先という設計自体は欠陥ではない。新Skill・中央台帳・汎用storage frameworkは前提としない。

## A. 質問・承認・checkpoint

### OPS-01 質問前後と工程引継ぎの永続化 (P1)

対象: qa-workflow、question-analysis、agent-answer-form、各設計owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)はstate・再利用・再開を、[question guidance](../../skills/question-analysis/references/guidance.md)はQ ID・回答正規化を規定する。質問提示直後・回答反映後・工程間の保存を全owner横断で自動保証する受入は確認できなかった。

改善: [共通運用契約](../reference/qa-workflow-operating-contract.md)のCP03/04/05/08を既存stateと各ownerの保存入口で検証する。Q ID、停止scope、完了済みartifact ref/revision、候補、未保存理由、再開ownerを保持。単発読取へ永続化を強制しない。

受入: 質問提示直後の中断・別session再開、部分回答・保留、保存未設定/失敗、source改版を試験し、解決済み論点・完了済み工程の反復と未保存の成功表示を防ぐ。

追加要件：RV-03/07/09：正式保存と許可済み中間保存を分離し、質問提示前・回答受領後・owner引継ぎを区別。Q ID、元質問定義/revision・根拠、回答対応、旧HTML、未保存範囲を保持し、意味が変わった旧回答を自動採用しない。質問のために未承認の正式保存を行わない。中間保存不能時は質問・安全な候補・再開情報を返し復元保証なしを明示。受入：未設定/権限拒否、承認待ちでも質問提示、質問改版・旧回答再送、部分回答、別session復元。

### OPS-02 承認要求の集約と進行許可の分離 (P1)

対象: qa-workflow、project-context、question-analysis、計画・保存・実行owner。

現状: continuous/gated、Q06配置合意、Git既定承認方式は既存。複数成果物の提示単位・部分承認の横断保証は未確認。ゲートグループ欄は実動作保証ではない。

改善: 既存approval refs、scope/revision、失効条件で独立承認可能な項目をまとめる。回答、進行、配置、保存、外部副作用を区別し承認条件を緩めない。

受入: 部分承認・拒否・保留・revision変更・権限不足・有効合意再利用・モード変更で未承認操作を拒否し、重複質問を抑える。承認単位の変更は別途合意。

追加要件：RV-03/08/16：配置合意、仕様決定、計画承認、進行、正式保存、作業領域許可、操作認可、リスク受容を区別。Git既定方式・対象scope/ref/revision・差分・actor・失効条件を維持。中間保存の初回許可範囲は別途合意し正式保存を包括許可しない。受入：gated停止、continuousの不要介入削減、設計工程の必要正式保存承認、承認後revision変更、部分拒否。

## B. 保存・承認・完了証拠

### OPS-03 Owner別保存接続 (P0)

対象: project-context、feature-analysis、test-item-analysis、test-condition-analysis、計画3 Skill、ui-target-analysis、qa-workflow。

現状: [project-context](../../skills/project-context/SKILL.md)には明示選択local/Git provider、候補ownerにはwrite preconditionがあるが全ownerの実保存・履歴・readbackは未確立。

改善: 案件の正本・provider・承認方式を先に選び、既存adapterを利用可能なownerから接続。候補→正式保存→current引継ぎのref/revision/hashを実証する。

受入: 同一revisionの並行更新、create-if-absent、履歴、readback不一致、権限失効、応答消失、中断復帰を実providerで確認。fixtureだけで遠隔先を保証しない。

追加要件：RV-01/02/15：保存・認証済み承認・currentnessを分離。応答消失・readback不一致で旧外部revision保持を断定せず、実ref/revision/hash/操作結果を独立取得。個別CASで一括整合を宣言せずcommit/snapshot境界・依存ref/revisionを照合するまで下流currentをblock。過去対象外を自動解除しない。受入：書込み成功＋応答消失、部分保存、readback不能、別owner revision変更、二重更新・無断rollback・別正本拒否。

### OPS-04 認証済み承認・対象外判定 (P0)

対象: qa-workflow、project-context、計画3 Skill、defect-management、test-evaluation。

現状: [保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)には対話同意・通常push・activity照合があるが、excluded_by_approvalの真正性照合が未定義。F 3 Skillのvalidatorは本人性を証明しない。

改善: 案件の承認元・信頼境界を選び、scope/revision/actor/権限/期限を実照合して必要ownerと既存exclusion判定へ接続。

受入: 正しいactor/before/afterのみ許可、別actor・scope・revision・失効・activity遅延・取得不能をblock。未承認除外で完了分母を縮小しない。

追加要件：承認対象に操作種別、scope/ref/revision、差分、build/source、役割、理由、有効期間・失効条件を束縛。直前のrevision・権限確認、activity遅延中の未確定状態、独立readbackを検証。対話同意・作業branch push・形式validatorだけで正式承認にしない。未接続excluded_by_approvalは必須scopeのまま。

### OPS-05 Owner verifier未登録scope (P0)

対象: qa-workflow/scripts/owner_verifiers.py とproject-context、feature-analysis、ui-target-analysis、defect-management、test-evaluation等。

現状: 登録済み7 Skillはtest-item-analysis、test-condition-analysis、e2e-test-selection、test-reporting、test-requirements-analysis、test-architecture-design、test-management。既存runtime-v2 rootは別経路。未登録scopeはunverified_scopes。計画3 Skillはfixture検証のみ。

改善: 各ownerの実保存正本・検証入口・currentnessを接続。OPS-03/04の必要条件を満たす。単なる登録で完了としない。

受入: current実成果物だけ完了、改変本文・別scope・stale/欠落revision・偽readbackを拒否。再開時に独立読戻しし、既存runtime-v2の回帰なし。

追加要件：RV-04/05/13：元依頼・要求成果物・必須scope・除外候補とrequested_scopesの対応を開始/完了時に照合。宣言集合・入力列挙完全性、workflow_refと保存証拠の束縛、信頼境界を明示。保存本文・記録・証拠一式の偽造や別workflow混在は実providerから独立取得可能な範囲で検証する。受入：必須scope未宣言、入力列挙漏れ、別workflow証拠、未登録owner、承認不明除外、部分保存。

## C. 実行安全・継続管理

### OPS-06 Claim回復と共有resource予約・解放 (P0)

対象: qa-workflow、各実行owner。

現状: claimの原子的作成・読戻しはあるがrecover_claimの安全な条件付き解放と外部reservation実readback/releaseは未接続。結果不明時は再実行不可。

改善: 案件選定providerと元ownerの実開始・結果・cleanup取得を接続。旧claim/予約を無断削除・移行しない。複数host/network filesystemは個別実証。

受入: 二重受付、開始前中断、応答消失、cleanup失敗、権限失効、並行workflow隔離、解放競合。状態不明では再実行しない。

追加要件：RV-01/12：正式保存・外部Issue更新等のmutable operationも対象。既存ownerの原子的claim/冪等開始を優先。応答消失時は実開始・実保存・cleanup・claim revisionを独立取得し結果不明なら再実行しない。外部CAS/認可をclaimで代用しない。実分離/予約・解放確認まで同一案件の並列運用は既存制約を維持。

### OPS-07 実行・証跡・報告の横断受入 (P1)

対象: test-execution、e2e-test-*、testware-*、regression-testing、exploratory-testing、defect-management、test-reporting。

現状: 各ownerはraw結果・分析・報告・cleanupを分離するが実provider経由の横断受入に未達が残る。

改善: 既存経路で実行前条件→raw結果→分析→欠陥候補→統合報告を実案件接続。初回FAILや予定母集団を書き換えない。

受入: 未実行、判定不能、FAIL、retry、収集不全、cleanup未確認、修正確認と別目的Regression、証跡保護、外部Issue未認可拒否。

追加要件：RV-04/13/15：成果物完成、正式保存・承認、実行完了、合否、取得完全性、終了基準、Workflow完了、リリース承認を独立判定。元依頼と予定母集団・宣言scopeを対応付け、欠落sourceを0件にしない。母集団不明の直接報告は全体率・終了判定undetermined。新実環境の範囲は別途合意。受入：FAILを含む完了、scope漏れ、計画なし、未実行/判定不能、cleanup不明、部分保存。

## D. 文書整合・接続・効率

### OPS-08 WCAG closureガイダンスの旧記述 (P1)

対象: skills/qa-workflow/references/guidance.md §WCAG formal evaluation state（基準revision L252）、skills/qa-workflow/SKILL.md、skills/qa-workflow/scripts/workflow_runtime.py の _execute_and_finalize_wcag_report（L245以降）。

確認した差異: guidanceは現行finalize-wcag-reportがcaller提供dependency metadataとcandidateを照合するだけでcurrent rowを独立取得しないと記載。一方SKILL.mdはQA runtimeでcurrent stateを取得し公式WCAG close-reportを内部実行・CAS保存・独立readback後に完了する契約。コードもread-wcag-evaluation-stateを内部実行し、取得結果からWCAG runtimeを実行、_record_wcag_report_runtime_execution、finalize_wcag_reportを呼ぶ。旧説明は少なくとも現行owner内部実行経路と一致しない。

改善: 現行コード・schema・否定試験と照合してguidance更新。特権DB writer、複数host、認可や意味判断まで保証すると解釈しない。今回の静的確認は攻撃経路全体の実証ではない。

受入: 偽造candidate/metadata拒否、owner内部実行、CAS conflict、履歴欠損、closure不完全、独立readbackを確認し文書とコード・テストを一致させる。

追加要件：現行文書・コード・schema・否定試験を再取得し正規owner内部実行経路に合わせ局所修正する。今回の運用文書改訂ではSkill本体・guidance修正や実runtime試験は行わず、OPS-08は未着手。

### OPS-09 案件初期化・配置・人間編集の受入 (P1)

対象: project-context、feature-analysis、ui-target-analysis、spec-analysis、qa-workflow。

現状: Q06と既存writerはあるが実案件の配置合意・人間編集から正式保存までの横断受入には未達が残る。

改善: 既存template・writerを用い、必要時の不足field確認・既存合意再利用を実案件で検証。機能別物理分割を強制しない。

受入: 既存配置維持、候補重複・アクセス不能、新規配置未承認、正本直接改変、手動ID・行削除、競合、承認済み採用、局所変更伝播。

追加要件：RV-10/14/15/17：配置・発見規則はOPS-14/15、移行はOPS-17を根拠とし、ここでは初期化・人間編集の横断受入を担当。UI package固有生成領域・draft key・retire・snapshot・writerを他ownerへ無条件流用しない。作業branch pushと正式反映承認を分離。直接改変時は編集案と元revision保全、無断復旧なし。過去対象外（実Q06等）は維持し再検証は別途合意。

### OPS-10 外部起動・製品CI接続 (P2)

対象: 呼出し側、qa-workflow、feature-analysis、CI handoff。

現状: PR/merge/release/資料改版の起動は呼出し側責務。実成果物取得・承認元未選定なら製品CI統合はblocked。

改善: 案件の起動・受渡し方式を合意し既存ci_handoff.pyを接続。Skillに監視基盤やCI Agent起動を新設しない。

受入: PR追加commit、merge、release、外部資料改版、旧build結果、未分類差分、必須artifact欠落。未設定とfailを区別。

追加要件：RV-15：過去対象外のrelease通し・実環境/CI接続の再受入は案件選定後に別途合意。source revision・build・母集団を独立確認。sample CIの分類・列挙対象（JSON等）の制約を一般化しない。未設定/未取得をPASSにしない。

### OPS-11 効率と運用負荷の実測 (P2)

対象: qa-workflow、EVALS.md、呼出し側。

現状: PR #22効率比較はunproven、同一入力再依頼等の悪化と安全/品質未達を保持。

改善: 初回、同一入力再依頼、変更、外部資料改版、中断再開の既存比較条件で質問数、不要再生成、保存漏れ、所要時間、費用/token、品質・安全を測る。

受入: 既存比較器、独立試行、同条件・品質/安全PASS、測定不能の明示。介入削減のため承認や品質を弱めない。

追加要件：人間の作業・待ち時間、質問/承認回数、再開時再入力、保存漏れを測定候補に追加。人間レビュー・承認時間は過去比較で対象外承認済みのため、新たに測定する場合は計測法・比較母集団・範囲を別途合意し過去測定値に混入させない。品質・安全合格を前提にする。

## E. 成果物の標準配置・命名・発見

追加調査: 作業branchの 412cabf22710b6b4abccfa6330fc7be538c6dbbf を基準に全37 SkillのSKILL.md、主要reference、関連Plan、一部保存helperを静的確認した。成果物の論理schema、保存先root、物理配置、命名、永続化能力は別々に評価する。既存配置を優先する[Q06](../plans/2026-11-07_122247_development-qa-traceability.md)は維持する。以下は新規案件の既定案と解決規則の不足に対する改善候補であり、現行の固定パス仕様ではない。

### OPS-12 標準ディレクトリ構造と保存粒度 (P1)

対象: project-context、qa-workflow、全成果物owner。

現状: [Project Context template](../../skills/qa-workflow/assets/project-context-template.md)のSection 14は既存成果物の場所・範囲・鮮度を記録し、Section 16には一部rootのstable keyがある。新規案件全体の標準配置と案件・機能・scope・Run単位の保存粒度は未統一。特に計画、設計、質問、レビュー、報告は内容の形式と物理配置が別である。

改善: 既存配置がないと確認された場合に提示する標準構成を定義し、案件別overrideを許す。全37 Skillの成果物についてowner、正本形式、保存要否、論理scope、保存粒度、標準相対path、例外、既存writerとの対応を明確にする。案件単位の共通条件や機能横断成果物を機能別に重複保存しない。次のqa/構成は検討用であり、全ディレクトリの事前作成や採用を強制しない。

```text
qa/
├── context/          # Project Context / DEC / ASM
├── features/         # 機能台帳
├── specifications/   # 仕様分析 / ui-target/
├── questions/        # Q / 回答履歴 / 必要時のform参照
├── planning/         # QA要求 / 方式 / 計画
├── analysis/         # Risk / ITEM / COND候補
├── design/           # TR / TCN・CI / TC
├── reviews/          # coverage / adversarial review
├── automation/       # E2E選定 / inspection / 実装参照
├── execution/        # 直接TC / E2E / 非E2EのRunと結果参照
├── regression/       # baseline / run / activity
├── exploration/      # charter / session / finding
├── knowledge/        # 既存entry形式
├── defects/          # 欠陥候補 / 外部Issue参照
├── usability/        # 評価 / 観測 / WCAG
├── reports/          # 報告 / QA活動評価
└── state/            # 既存workflow state / claim / baseline
```

実テストコードは対象repoの既存構成、機密raw証跡や一時作業物は別の許可済み保護領域を優先する。providerがディレクトリを持たない場合は同等の論理refを定義し、物理pathをIDにしない。

受入: 新規案件で一度の配置合意後に必要な成果物を同じ規則で配置、別session/agentでも一致、全37 Skillについて保存対象と非対象・粒度・例外を説明可能。既存ui-target-v1の構造、knowledge entry、state、runnerの保存契約を変更せず、必要な場所だけ生成する。

追加要件：RV-02/18：案件、機能/scope、共通条件、論点、Workflow、Run、Attempt、Entry、Snapshotの論理粒度を区別。論点単位のID管理は1論点1ファイルを意味しない。正本・派生表示物・raw・履歴と参照整合/一体更新境界をowner別に明示。全37 Skillの標準配置/既存固定名/例外/保存不要/未接続を一覧化。標準path採用は別途合意。

### OPS-13 成果物の命名規則と正本・表示物の識別 (P1)

対象: 全成果物owner、qa-workflow、project-context。

現状: [ui-target-v1](../../skills/spec-analysis/references/ui-test-target-analysis.md)は標準file群、[knowledge](../../skills/qa-knowledge/references/data-contract.md)はentry-ref.md、[artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)はUUID.json・digestによるsnapshot等、[testware runner](../../skills/testware-execution/scripts/runner.py)はmanifest.json・attempt log等を規定する。一方、多くの計画・設計・報告ownerのテンプレートは出力内容を規定するが、共通の保存ファイル名は確認できない。

改善: ownerごとにcanonical名、表示用Markdown等の派生物、draft・一時物、履歴、Run/attemptの命名と拡張子・schemaの対応を定める。既存の固定名・writer・安定IDを優先する。論理artifact refとprovider revisionを正本識別に使い、pathや日時だけを識別・currentnessの根拠にしない。単なる再出力で正本を複製せず、Run/attemptの証跡は独立したidentityで保持する。

受入: 同一成果物の再依頼は既存正本を解決し、異なるscope・Run・attemptは衝突しない。正本と表示物・draftの誤認を拒否。大文字小文字、禁止文字、path traversal、名前衝突、既存固定名との互換性を対象providerで検証。

追加要件：RV-09：安定正本名・scope識別・Run/Attempt ID・immutable snapshot・作業領域を分離。日時/版を一律付与しない。フォーム元定義/revisionと回答を対応付け旧HTML/質問履歴を保持。改版後の旧回答自動適用禁止。命名変更で論理ID・履歴・依存を失わない。

### OPS-14 保存先解決と案件設定 (P1)

対象: project-context、qa-workflow、各保存owner。

現状: Section 16にはqa.workflow_state_root、qa.knowledge_root、qa.feature_artifact_root、qa.reservation_root等がある。その他の成果物は主にSection 14や明示refに依存し、標準配置と案件別設定の横断解決規則が不足する。専用stable keyのないこと自体を欠陥とせず、既存の契約を維持する。

改善: 明示された依頼scope・操作許可を確認し、既存正本と有効な配置合意を優先する。矛盾する明示指定は配置変更候補として扱い、無断上書きしない。既存がないと確認できた場合は承認済み案件設定を適用し、なければ標準案を提示して初回合意を得る。未解決・重複・アクセス不能は不存在と区別し、正式保存をblockする。Section 14/16と既存prepare-placementを再利用し、全Skill専用keyや新中央台帳は必須としない。

受入: 明示指定、既存配置、案件override、標準案、設定なし、矛盾、重複、アクセス不能を個別に確認。別sessionで解決結果が一致し、有効な合意が変わらなければ再質問しない。保存先が解決してもnative CAS、権限、承認、readbackが不足すれば正式保存しない。

追加要件：RV-14：Project Context自身の初回発見をbootstrapとし、案件、許可探索入口、候補ref、権限、案件一致、列挙完全性を確認。未取得を不存在とみなさない。既存Context取得後にSection 12/14/16を利用。矛盾する明示指定は変更候補。未設定時の読取継続と正式保存停止を分ける。

### OPS-15 保存済み成果物の発見・再利用 (P1)

対象: qa-workflow、project-context、feature-analysis、全成果物owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)は既存state・input revisionの再利用、[project-context guidance](../../skills/project-context/references/guidance.md)は許可範囲の列挙と候補判定を定めるが、全ownerの正本発見と重複検出の共通受入は未確認。

改善: 承認済みroot/direct ref、owner、scope、artifact identity、provider revision、source依存、既存stateを使って発見・currentnessを確認する。固定root scanは既存ownerの許可範囲・完全性・型検証に従い、無制限の再帰探索やpath/ファイル名だけの推定を避ける。重複・一覧取得不全・不明参照は明示し、新規作成や自動選択を止める。

受入: 別agent/sessionから同一正本を発見、変更なしの再依頼で不要再生成なし、部分改版では影響scopeのみ再検証。重複・欠落・stale・読取不能・列挙打切りを区別し、既存正本を保全する。OPS-01/03/05と接続する。

追加要件：RV-02/05/14：入力revision一致に加え入力母集団完全性、利用Context field、依存source/ownerのcurrentness・scope・意味契約を確認。input_revision.pyのsameだけで再利用しない。bootstrapはOPS-14、部分保存整合はOPS-03。受入：未列挙入力改版、外部資料改版、未使用Context変更、重複・一覧不全・別workflow混在。

### OPS-16 永続成果物・一時作業物・機密証跡の分離 (P0)

対象: qa-workflow、project-context、agent-answer-form、test-target-inspection、各実行・評価owner。

現状: [test-target-inspection](../../skills/test-target-inspection/references/guidance.md)は指定先・秘密情報の保存制約、[testware-execution](../../skills/testware-execution/references/guidance.md)はrepo外の保護された成果物先を定める。agent-answer-formはSkill外作業dirを使用する。全owner横断の保存区分・保持・cleanup・共有範囲は未統一。

改善: 正本、再生成可能な派生物、再開に必要なdraft、短期一時物、raw実行証跡、機密証跡を区別する。保存可否、許可root、アクセス範囲、保持・cleanup方針、参照の有効期限と非保存理由を案件条件で明確にする。rawの無断commit・共有を禁止し、安全な要約/参照のみを渡す場合も元証跡の取得可能性を偽らない。保存不能なら未保存と完了条件への影響を明示する。

受入: secretを含む証跡、安全な保存先なし、誤ったroot、別Runの証跡、保持期限切れ、一時物cleanup失敗、再開に必要な候補の保全を確認する。既存runnerの保護領域と安全契約を維持し、正式履歴をcleanupで削除しない。

追加要件：RV-03/06/11：正式成果物、継続作業、保護証跡、テストコードを論理区分し物理root/provider追加を強制しない。Skill指示とsandbox/hook/OS/provider権限を分離し最小権限・機密非保存・cleanupを検証。PR #22の指定領域外補助script書込み事例を維持し隔離環境で確認。必要境界未確認はblock。ARIA snapshotは安全な任意保存で、保存自体を要求した場合だけ完了条件。中間保存は正式承認を代替しない。受入：root外書込み・symlink等の逸脱、secret、未許可作業領域、任意/必須証跡の差、正式履歴保全。

### OPS-17 既存配置との互換性・変更管理 (P1)

対象: project-context、qa-workflow、全成果物owner。

現状: Q06は既存配置優先、初回合意、物理分割の必要性判断、無断移動禁止を定める。標準案導入時に既存案件の混在構成・個別overrideを横断検証する必要がある。

改善: 有効な既存配置を優先し、標準化のみを理由とする移動・改名・分割・再保存を行わない。変更が必要な場合だけ、移行対象・旧新ref・依存関係・履歴・権限・互換読取・条件付き切替・rollback・レビュー範囲を明示して別途合意する。現行writer/schemaを尊重し、二重正本を作らない。OPS-09の案件初期化・人間編集受入と接続する。

受入: 既存案件の無変更再利用、異なるprovider/配置の混在、部分override、変更未承認、移行途中の競合・失敗、旧revisionの参照、rollbackを確認。標準構造が既存データの消失・二重正本・ID変更を生まないことを示す。

追加要件：RV-10：配置変更と人間編集採用を区別。OPS-09の編集受入を再利用しowner別schema・生成領域・ID・履歴を保全。移行中の新旧参照、部分失敗、旧revision・rollback条件、複数owner参照整合を検証し、条件不成立なら自動切替・自動rollbackなし。

## レビュー反映と実装順序の候補

2026-11-25の文書レビュー（対象commit 351e4e925e74fb52f7a9ddcf777f3828ca3c2cc7）のRV-01〜18を既存OPS-01〜17に統合した。追加OPS IDは作らない。文書上の処置であり、Skill/runtime改善・実provider受入の完了を意味しない。

<!-- dprint-ignore -->
| 指摘 | 重大度 | 対応OPS | 文書反映 |
| --- | --- | --- | --- |
| RV-01 保存結果不明 | 高 | 03/06 | 保存・承認・currentness分離、独立再取得 |
| RV-02 部分保存 | 高 | 03/12/15 | snapshot境界・依存revision・下流current停止 |
| RV-03 質問前保存 | 高 | 01/02/16 | 許可済み中間保存・正式別承認・未保存時質問提示 |
| RV-04 要求scope完全性 | 高 | 05/07 | 元依頼と宣言scope照合、Runtime限界 |
| RV-05 入力列挙完全性 | 高 | 05/15 | 母集団・依存・used fields・currentness |
| RV-06 書込み制限 | 高 | 16 | 運用指示と技術境界分離、隔離・最小権限 |
| RV-07 Checkpoint混在 | 中 | 01 | 現行/部分/指針/改善を区別 |
| RV-08 設計系介入 | 中 | 02 | 固有進行承認とG1/G4/gatedを区別 |
| RV-09 フォーム改版 | 中 | 01/13 | Q/元定義・旧HTML・旧回答再確認 |
| RV-10 UI固有編集制約 | 中 | 09/17 | 共通編集方針とui-target-v1固有制約 |
| RV-11 snapshot任意性 | 中 | 16 | 任意保存・要求時完了条件 |
| RV-12 claim適用先 | 中 | 06 | mutable operation全般、owner契約優先 |
| RV-13 完了判定 | 中 | 05/07 | 成果物・保存・承認・実行・合否・終了・リリース区別 |
| RV-14 Context初回発見 | 中 | 14/15 | bootstrap、許可探索・不存在と不明の区別 |
| RV-15 過去対象外 | 中 | 03/07/09/10 | 過去判定維持、新受入範囲別途合意 |
| RV-16 利用者対応区分 | 低 | 02 | 必須・条件付き・任意・AI担当 |
| RV-17 利用シナリオ | 低 | 09/01 | 初回・変更・回答・再開・実行・読取例 |
| RV-18 保存root具体性 | 低 | 12/13/14 | 全37 Skillの固定・部分・未統一・例外 |

### Phase（実装単位の提案）

<!-- dprint-ignore -->
| Phase | 対象OPS | 成果物・依存条件 |
| --- | --- | --- |
| 0 仕様整合 | 08 | WCAG旧guidanceの照合・局所修正・既存試験確認 |
| 1 成果物管理基盤 | 09/12/13/14/15/16/17 | 配置・命名・粒度・発見・保護・互換性、全37 Skill配置契約案 |
| 2 質問・承認・再開 | 01/02 | 中間保存許可、質問revision、正式承認、局所停止・再開 |
| 3 正式保存・実行安全 | 03/04/06 | 選定済み実provider/認可元、独立readback、claim/予約/回復 |
| 4 完了検証・横断受入 | 05/07 | owner verifier、元依頼・scope・currentness、保存・実行・報告独立検証 |
| 5 案件接続・効率評価 | 10/11 | CI接続、品質/安全と効率・利用者負担測定 |

Phase 1/2の契約は並行検討しPhase 3の実provider能力に応じ調整する。OPS-16と現行安全制約は全Phaseで維持する。既存blocked操作をPhase順序で許可しない。独立作業の並行検討は可だが共有resourceの並列実行は既存制約に従う。既存owner/helperを優先し、新Skill・中央DB・中央mutable manifest・全成果物統一schema・全Skill専用key・汎用storage framework・一律配置移行は前提としない。

### 横断受入シナリオ候補

既存Deterministic Test・Semantic Evaluation・実Agent評価を再利用する。各シナリオで元依頼・scope・入力/保存revision・必要承認・実測または拒否証拠・再開条件を確認し未検証は未検証のまま記録する。

<!-- dprint-ignore -->
| ID | シナリオ | 期待する受入結果 | 関連OPS |
| --- | --- | --- | --- |
| AT-01 | 新規案件初期化 | 探索完全性確認後、一度の配置合意で必要先解決 | 09/12/14 |
| AT-02 | 既存案件利用 | 配置・ID・有効合意維持、不要再質問なし | 09/14/17 |
| AT-03 | 初回テスト設計 | 必要scopeの分析〜TC、正本・参照・必要保存検証 | 03/05/12/13 |
| AT-04 | 仕様ブロッカー | 許可中間保存または未保存明示、該当scopeだけ停止 | 01/02/16 |
| AT-05 | 部分回答 | 根拠currentな回答scopeのみ再開、旧回答/保留を誤承認しない | 01/02/13 |
| AT-06 | 別Agent再開 | 実保存state/正本から再開先取得、未保存候補は復元保証なし | 01/15 |
| AT-07 | 変更なし再依頼 | 母集団・依存・currentness確認、有効合意再利用、不要再生成なし | 02/05/15 |
| AT-08 | 一部仕様改版 | 外部資料含む入力完全性、影響scopeのみ再検証 | 05/15 |
| AT-09 | 人間編集 | owner固有writer、差分/承認、競合拒否、無断上書きなし | 09/17 |
| AT-10 | 並行Workflow | 実分離/予約確認、未接続block、混線なし | 06/16 |
| AT-11 | 保存後通信障害 | 実保存・承認独立再取得、二重更新なし | 03/04/06 |
| AT-12 | 複数成果物部分保存 | snapshot/依存整合確認まで下流current不可 | 03/12/15 |
| AT-13 | 正本重複 | 無断選択・新規作成なし、未解決明示 | 14/15 |
| AT-14 | アクセス不能 | 不存在と区別し正式保存block | 03/14/15 |
| AT-15 | 承認後revision変更 | 旧承認再利用拒否 | 02/04 |
| AT-16 | 機密証跡 | 未許可領域書込み/公開なし、任意・必須保存区別 | 16 |
| AT-17 | 必須scope宣言漏れ | 元依頼との照合で不足検出、誤完了なし | 05/07 |
| AT-18 | FAILを含む実行 | 合否・母集団・cleanup・終了基準・workflow完了を独立判定 | 07 |
| AT-19 | 異なるAgentで同一依頼 | 同一正本・配置・命名、別scope/Run衝突なし | 12/13/14/15 |
| AT-20 | 単発読取 | 不要な永続保存・配置承認を要求しない | 01/02/12 |

全て未実施の受入候補。正式な実装Plan、Phase採用、標準path、provider、承認元、優先度、実環境・過去対象外の再検証範囲は別途合意する。既存PR #22の未達・対象外・検証結果を上書きしない。
