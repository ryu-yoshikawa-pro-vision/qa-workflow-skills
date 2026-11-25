# QAワークフロー運用上の改善候補

基準: main 197f1e0e1abe870b0cc793355e7abf73bf241d87（2026-11-25）。全37 QA Skillと主要reference・runtime、[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)を静的に照合した。以下は未着手の改善候補であり、実装指示・承認済みPlan・既存受入条件の変更ではない。優先度は暫定（P0: 安全・誤完了、P1: 継続性・運用負担、P2: 接続・効率）。案件別保存先という設計自体は欠陥ではない。新Skill・中央台帳・汎用storage frameworkは前提としない。

## 最上位の確定方針

2026-11-25 利用者決定（今後の設計に適用）：成果物は指定root配下のディレクトリで統一管理する。案件識別・探索・切替、ブランチ管理、保存技術/Provider・認証方式の選択、配置の都度決定はSkillの責務外。必要な環境条件・許可root・権限をハーネスが提供し、不要な管理は移管せず削除する。Skillは専門的なQAの意味判断、成果物の内容・形式・相対配置、質問・引継ぎに集中し、Helperは決定論的な採番・計算・検証・保存を担当する。案件管理や特定ハーネスの実装、新たな保存基盤を改善の必須要件にしない。

OPS-01〜17の従来提案は調査時点の課題・受入候補として保持する。実装範囲は以下OPS-18および責務再評価表で上書きする。旧案件単位・kind別branch・配置承認・Provider拡張をそのまま実装しない。現行の安全制約は改修完了まで維持する。PR #40の改訂設計・最終実装を先に確認し、既に対応された課題の再実装を避ける。

### 追加の確定前提（Q01〜08）

[QA Skill設計・開発の共通原則](../reference/qa-skill-design-principles.md)をプロジェクト全体の設計前提とする。Q01〜08は利用者合意済みであり、再承認を求めない。OPS-18を適用する際に通常保存の都度承認、専用認証hostの一律要求、不要な状態管理・履歴複製を削減する。保存と内容承認・必要な外部操作を区別する。直接利用を維持し既存手段の具体的不足が確認できない限り新規管理機構や追加防御を作らない。既存の開発用Git保護・未改修の安全制約は維持する。

## A. 質問・承認・checkpoint

### OPS-01 質問前後と工程引継ぎの永続化 (P1)

対象: qa-workflow、question-analysis、agent-answer-form、各設計owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)はstate・再利用・再開を、[question guidance](../../skills/question-analysis/references/guidance.md)はQ ID・回答正規化を規定する。質問提示直後・回答反映後・工程間の保存を全owner横断で自動保証する受入は確認できなかった。

改善: [共通運用契約](../reference/qa-workflow-operating-contract.md)のCP03/04/05/08を既存stateと各ownerの保存入口で検証する。Q ID、停止scope、完了済みartifact ref/revision、候補、未保存理由、再開ownerを保持。単発読取へ永続化を強制しない。 Q02の処理完了・質問前・回答反映後・中断・引継ぎで必要分を自動保存し、同一時点の重複保存を避ける。

受入: 質問提示直後の中断・別session再開、部分回答・保留、保存未設定/失敗、source改版を試験し、解決済み論点・完了済み工程の反復と未保存の成功表示を防ぐ。

追加要件：RV-03/07/09：正式保存と許可済み中間保存を分離し、質問提示前・回答受領後・owner引継ぎを区別。Q ID、元質問定義/revision・根拠、回答対応、旧HTML、未保存範囲を保持し、意味が変わった旧回答を自動採用しない。許可済み通常保存は自動。候補保存を内容承認とせず、質問のために未承認の正式仕様変更を行わない。中間保存不能時は質問・安全な候補・再開情報を返し復元保証なしを明示。受入：未設定/権限拒否、承認待ちでも質問提示、質問改版・旧回答再送、部分回答、別session復元。

### OPS-02 承認要求の集約と進行許可の分離 (P1)

対象: qa-workflow、project-context、question-analysis、計画・保存・実行owner。

現状: continuous/gated、Q06配置合意、Git既定承認方式は既存。複数成果物の提示単位・部分承認の横断保証は未確認。ゲートグループ欄は実動作保証ではない。

改善: 許可済み通常保存は都度承認なしとする。候補・回答の記録と内容の正式承認、工程進行、操作認可、破壊的変更を区別する。正式決定・仮定採用・承認済み仕様の意味変更・必要な外部操作は既存の有効な承認単位でまとめる。案件・配置・保存方式の再質問はしない。

受入: 許可済み通常保存が承認待ちで停止しない、未承認候補を正式仕様として採用しない、必要承認の拒否・保留・revision変更・権限不足・gated停止を維持する。

追加要件：RV-03/08/16：Q03を適用。仕様決定、計画承認、進行、書込み許可、内容承認、操作認可、リスク受容を区別。必要承認のscope/ref/revision・差分・権限・失効条件は維持。通常保存には個別承認不要。

## B. 保存・承認・完了証拠

### OPS-03 Owner別保存接続 (P0)

対象: project-context、feature-analysis、test-item-analysis、test-condition-analysis、計画3 Skill、ui-target-analysis、qa-workflow。

現状: [project-context](../../skills/project-context/SKILL.md)には明示選択local/Git provider、候補ownerにはwrite preconditionがあるが全ownerの実保存・履歴・readbackは未確立。

改善: 指定rootと必要な保存能力を外部から受け、既存の決定論的保存helperを必要なownerから接続。候補→正式保存→current引継ぎのref/revision/hashを実証する。案件・Provider・承認方式をSkillが選ばない。特定storeの全ownerへの拡張は必須としない。

受入: 同一revisionの並行更新、create-if-absent、履歴、readback不一致、権限失効、応答消失、中断復帰を実providerで確認。fixtureだけで遠隔先を保証しない。

追加要件：RV-01/02/15：保存・認証済み承認・currentnessを分離。応答消失・readback不一致で旧外部revision保持を断定せず、実ref/revision/hash/操作結果を独立取得。個別CASで一括整合を宣言せずcommit/snapshot境界・依存ref/revisionを照合するまで下流currentをblock。過去対象外を自動解除しない。受入：書込み成功＋応答消失、部分保存、readback不能、別owner revision変更、二重更新・無断rollback・別正本拒否。

### OPS-04 認証済み承認・対象外判定 (P0)

対象: qa-workflow、project-context、計画3 Skill、defect-management、test-evaluation。

現状: [保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)には対話同意・通常push・activity照合があるが、excluded_by_approvalの真正性照合が未定義。F 3 Skillのvalidatorは本人性を証明しない。

改善: 外部から供給される信頼境界・操作認可によりscope/revision/actor/権限/期限を実照合し、必要ownerと既存exclusion判定へ接続。認証方式をSkillが選ばない。 通常の許可済み保存には専用認証host・個別承認を要求せず、実際の認可リスクがある外部操作・正式判断等に限定する。

受入: 正しい主体・操作・scope・revisionのみ許可、別主体・scope・revision・失効・認可結果不明をblock。未承認除外で完了分母を縮小しない。

追加要件：承認対象に操作種別、scope/ref/revision、差分、build/source、役割、理由、有効期間・失効条件を束縛。直前のrevision・権限確認、認可確認遅延中の未確定状態、独立readbackを検証。対話同意・編集提出・形式validatorだけで正式承認にしない。未接続excluded_by_approvalは必須scopeのまま。

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

改善: 外部で保証される共有資源・操作境界と元ownerの実開始・結果・cleanup取得を接続。旧claim/予約を無断削除・移行しない。必要な場合に限り既存helperを用いる。複数writer/hostの能力未確認は局所blockし、新しい汎用排他基盤を作らない。

受入: 二重受付、開始前中断、応答消失、cleanup失敗、権限失効、並行workflow隔離、解放競合。状態不明では再実行しない。

追加要件：RV-01/12：正式保存・外部Issue更新等のmutable operationも対象。既存ownerの原子的claim/冪等開始を優先。応答消失時は実開始・実保存・cleanup・claim revisionを独立取得し結果不明なら再実行しない。外部CAS/認可をclaimで代用しない。実分離/予約・解放確認まで同一資源を共有する並列運用は既存制約を維持。

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

### OPS-09 QAコンテキスト・人間編集の受入 (P1)

対象: project-context、feature-analysis、ui-target-analysis、spec-analysis、qa-workflow。

現状: Q06と既存writerはあるが実案件の配置合意・人間編集から正式保存までの横断受入には未達が残る。

改善: QA目的・用語・業務制約・DEC/ASMなどの意味管理と人間編集の受入に集中する。既存template・writerで必要なQA情報の不足確認・有効な判断の再利用を検証。案件初期化・配置決定をSkillから除外し、必要な入力を外部から受ける。

受入: 指定rootの既存正本再利用、候補重複・アクセス不能、正本直接改変、手動ID・行削除、競合、承認済み採用、局所変更伝播。案件探索・配置承認の再質問なし。

追加要件：RV-10/14/15/17：配置・発見規則はOPS-14/15、移行はOPS-17を根拠とし、ここではQAコンテキスト・人間編集の横断受入を担当。UI package固有生成領域・draft key・retire・snapshot・writerを他ownerへ無条件流用しない。編集提出と正式反映承認を分離。直接改変時は編集案と元revision保全、無断復旧なし。過去対象外（実Q06等）は維持し再検証は別途合意。

### OPS-10 外部起動・製品CI接続 (P2)

対象: 呼出し側、qa-workflow、feature-analysis、CI handoff。

現状: PR/merge/release/資料改版の起動は呼出し側責務。実成果物取得・承認元未選定なら製品CI統合はblocked。

改善: 呼出し側が起動・入力/結果受渡しを管理し、既存ci_handoff.pyは必要な場合に利用する。Skillに案件運用・監視基盤・CI Agent起動を新設しない。

受入: PR追加commit、merge、release、外部資料改版、旧build結果、未分類差分、必須artifact欠落。未設定とfailを区別。

追加要件：RV-15：過去対象外のrelease通し・実環境/CI接続の再受入は案件選定後に別途合意。source revision・build・母集団を独立確認。sample CIの分類・列挙対象（JSON等）の制約を一般化しない。未設定/未取得をPASSにしない。

### OPS-11 効率と運用負荷の実測 (P2)

対象: qa-workflow、EVALS.md、呼出し側。

現状: PR #22効率比較はunproven、同一入力再依頼等の悪化と安全/品質未達を保持。

改善: 初回、同一入力再依頼、変更、外部資料改版、中断再開の既存比較条件で質問数、不要再生成、保存漏れ、所要時間、費用/token、品質・安全を測る。

受入: 既存比較器、独立試行、同条件・品質/安全PASS、測定不能の明示。介入削減のため承認や品質を弱めない。

追加要件：人間の作業・待ち時間、質問/承認回数、再開時再入力、保存漏れを測定候補に追加。人間レビュー・承認時間は過去比較で対象外承認済みのため、新たに測定する場合は計測法・比較母集団・範囲を別途合意し過去測定値に混入させない。品質・安全合格を前提にする。

## E. 成果物の標準配置・命名・発見

追加調査: 作業branchの 412cabf22710b6b4abccfa6330fc7be538c6dbbf を基準に全37 SkillのSKILL.md、主要reference、関連Plan、一部保存helperを静的確認した。成果物の論理schema、保存先root、物理配置、命名、永続化能力は別々に評価する。既存配置を優先する[Q06](../plans/2026-11-07_122247_development-qa-traceability.md)は維持する。以下は指定root配下の標準相対配置案。旧案件別配置判断は撤回し、既存配置への互換対応が必要なら外部境界で行う。現行実装の固定パス仕様ではない。

### OPS-12 標準ディレクトリ構造と保存粒度 (P1)

対象: 全成果物owner、既存Helper、ハーネスとの入力境界。

現状: [Project Context template](../../skills/qa-workflow/assets/project-context-template.md)のSection 14は既存成果物の場所・範囲・鮮度を記録し、Section 16には一部rootのstable keyがある。新規案件全体の標準配置と案件・機能・scope・Run単位の保存粒度は未統一。特に計画、設計、質問、レビュー、報告は内容の形式と物理配置が別である。

改善: 指定root配下の標準相対配置を定義する。最終Skill構成の成果物についてowner、正本形式、保存要否、論理scope、保存粒度、標準相対path、例外、既存writerとの対応を明確にする。共通条件や機能横断成果物を機能別に複製しない。rootは外部入力とし、案件別の配置決定・初回配置承認をSkillに要求しない。以下は相対配置の検討案であり、必要なディレクトリだけ作る。

```text
<指定成果物root>/
├── context/          # QA前提 / DEC / ASM
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
├── cross-context/    # PR #40の指定rootとして利用する配置案
│   ├── context-signal-batch/
│   ├── context-rule-candidate/
│   └── context-synthesis-run/
├── defects/          # 欠陥候補 / 外部Issue参照
├── usability/        # 評価 / 観測 / WCAG
├── reports/          # 報告 / QA活動評価
└── state/            # 必要な永続stateのみ。ハーネス側で別rootに分離可
```

実テストコードは対象repoの既存構成、機密raw証跡・高頻度state・一時作業物は外部指定の安全な領域を利用できる。管理対象の正式成果物はディレクトリで分類・発見する。保存技術による別論理配置をSkillに設計させない。物理rootや案件名を意味identityにしない。

受入: 外部指定rootから同一相対配置を解決し、別session/agentでも一致。最終Skill構成について保存対象・非対象・粒度・例外を説明可能。既存ui-target-v1、knowledge entry、state、runnerの必要な形式・安全契約を維持し、必要な場所だけ生成する。

追加要件：RV-02/18：root内の共通成果物、機能/scope、共通条件、論点、Workflow、Run、Attempt、Entry、Snapshotの論理粒度を区別。論点単位のID管理は1論点1ファイルを意味しない。正本・派生表示物・raw・履歴と参照整合/一体更新境界をowner別に明示。最終Skill構成の標準配置/既存固定名/例外/保存不要/未接続を一覧化。標準path採用は別途合意。

### OPS-13 成果物の命名規則と正本・表示物の識別 (P1)

対象: 全成果物owner、qa-workflow、project-context。

現状: [ui-target-v1](../../skills/spec-analysis/references/ui-test-target-analysis.md)は標準file群、[knowledge](../../skills/qa-knowledge/references/data-contract.md)はentry-ref.md、[artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)はUUID.json・digestによるsnapshot等、[testware runner](../../skills/testware-execution/scripts/runner.py)はmanifest.json・attempt log等を規定する。一方、多くの計画・設計・報告ownerのテンプレートは出力内容を規定するが、共通の保存ファイル名は確認できない。

改善: ownerごとにcanonical名、表示用Markdown等の派生物、draft・一時物、履歴、Run/attemptの命名と拡張子・schemaの対応を定める。既存の固定名・writer・安定IDを優先する。論理artifact refとprovider revisionを正本識別に使い、pathや日時だけを識別・currentnessの根拠にしない。単なる再出力で正本を複製せず、Run/attemptの証跡は独立したidentityで保持する。 Q04/05に従い人間向けの読みやすい形式を優先し必要な機械処理だけ構造化。履歴複製・全成果物の二形式化を強制しない。

受入: 同一成果物の再依頼は既存正本を解決し、異なるscope・Run・attemptは衝突しない。正本と表示物・draftの誤認を拒否。大文字小文字、禁止文字、path traversal、名前衝突、既存固定名との互換性を対象providerで検証。

追加要件：RV-09：安定正本名・scope識別・Run/Attempt ID・immutable snapshot・作業領域を分離。日時/版を一律付与しない。フォーム元定義/revisionと回答を対応付け旧HTML/質問履歴を保持。改版後の旧回答自動適用禁止。命名変更で論理ID・履歴・依存を失わない。

### OPS-14 外部指定root・相対ref解決 (P1)

対象: 全成果物owner、決定論的保存Helper、外部入力境界。

現状: Section 16にはqa.workflow_state_root、qa.knowledge_root、qa.feature_artifact_root、qa.reservation_root等がある。その他の成果物は主にSection 14や明示refに依存し、標準配置と案件別設定の横断解決規則が不足する。専用stable keyのないこと自体を欠陥とせず、既存の契約を維持する。

改善: 指定root・許可入力ref・操作可否をハーネスから受け、標準相対pathを決定論的に解決する。Skillに案件探索・既存配置policy選択・Provider選択・初回配置合意・専用stable key追加を要求しない。既存正本との矛盾、重複、アクセス不能、root未設定を不存在と区別し正式保存をblock。旧配置との互換・移行は必要な場合だけ外部側で別途判断する。

受入: 指定root、root未設定、相対ref違反、異なるrootの同名ref、重複、アクセス不能を区別。別sessionで同一入力・同一rootの解決結果が一致。案件/配置/保存方式の再質問なし。条件付き保存、権限、承認、readbackが不足すれば正式保存しない。

追加要件：RV-14：旧Project Context bootstrap案は撤回する。QAに必要なコンテキストは外部指定の入力・相対refから取得し、未取得を不存在とみなさない。案件識別・初回探索入口の決定・Section 12/14/16の運用設定解決はSkillの責務外。入力不足時の分析継続と正式保存停止を分ける。

### OPS-15 保存済み成果物の発見・再利用 (P1)

対象: qa-workflow、project-context、feature-analysis、全成果物owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)は既存state・input revisionの再利用、[project-context guidance](../../skills/project-context/references/guidance.md)は許可範囲の列挙と候補判定を定めるが、全ownerの正本発見と重複検出の共通受入は未確認。

改善: 外部指定root/許可direct ref、owner、scope、artifact identity、保存revision、source依存、既存stateを使って発見・currentnessを確認する。固定root scanは既存ownerの許可範囲・完全性・型検証に従い、無制限の再帰探索やpath/ファイル名だけの推定を避ける。重複・一覧取得不全・不明参照は明示し、新規作成や自動選択を止める。

受入: 別agent/sessionから同一正本を発見、変更なしの再依頼で不要再生成なし、部分改版では影響scopeのみ再検証。重複・欠落・stale・読取不能・列挙打切りを区別し、既存正本を保全する。OPS-01/03/05と接続する。

追加要件：RV-02/05/14：入力revision一致に加え入力母集団完全性、利用Context field、依存source/ownerのcurrentness・scope・意味契約を確認。input_revision.pyのsameだけで再利用しない。root入力・ref解決はOPS-14、部分保存整合はOPS-03。受入：未列挙入力改版、外部資料改版、未使用Context変更、重複・一覧不全・別workflow混在。

### OPS-16 永続成果物・一時作業物・機密証跡の分離 (P0)

対象: qa-workflow、project-context、agent-answer-form、test-target-inspection、各実行・評価owner。

現状: [test-target-inspection](../../skills/test-target-inspection/references/guidance.md)は指定先・秘密情報の保存制約、[testware-execution](../../skills/testware-execution/references/guidance.md)はrepo外の保護された成果物先を定める。agent-answer-formはSkill外作業dirを使用する。全owner横断の保存区分・保持・cleanup・共有範囲は未統一。

改善: 正本、再生成可能な派生物、再開に必要なdraft、短期一時物、raw実行証跡、機密証跡を区別する。保存可否、許可root、アクセス範囲、保持・cleanup方針、参照の有効期限と非保存理由を外部から提供された保存・実行条件で確認する。rawの無断保存・共有を禁止し、安全な要約/参照のみを渡す場合も元証跡の取得可能性を偽らない。保存不能なら未保存と完了条件への影響を明示する。

受入: secretを含む証跡、安全な保存先なし、誤ったroot、別Runの証跡、保持期限切れ、一時物cleanup失敗、再開に必要な候補の保全を確認する。既存runnerの保護領域と安全契約を維持し、正式履歴をcleanupで削除しない。

追加要件：RV-03/06/11：正式成果物、継続作業、保護証跡、テストコードを論理区分し物理root/provider追加を強制しない。Skill指示とsandbox/hook/OS/provider権限を分離し最小権限・機密非保存・cleanupを検証。PR #22の指定領域外補助script書込み事例を維持し隔離環境で確認。必要境界未確認はblock。ARIA snapshotは安全な任意保存で、保存自体を要求した場合だけ完了条件。中間保存は正式承認を代替しない。受入：root外書込み・symlink等の逸脱、secret、未許可作業領域、任意/必須証跡の差、正式履歴保全。

### OPS-17 既存配置との互換性・変更管理 (P1)

対象: project-context、qa-workflow、全成果物owner。

現状: Q06は既存配置優先、初回合意、物理分割の必要性判断、無断移動禁止を定める。標準案導入時に既存案件の混在構成・個別overrideを横断検証する必要がある。

改善: 標準化のみを理由に既存正本を移動・改名・分割・再保存しない。移行が必要ならSkill外の作業として対象・旧新ref・依存・履歴・権限・互換読取・条件付き切替・rollback・レビュー範囲を別途合意する。既存writer/schemaを尊重し二重正本を作らない。OPS-09の人間編集受入と接続。

受入: 許可済み既存成果物の無変更再利用、別rootの同名ref分離、未承認移行拒否、必要な外部移行時の競合・失敗、旧revision参照・rollback。標準構造が既存データ消失・二重正本・ID変更を生まないことを示す。

追加要件：RV-10：配置変更と人間編集採用を区別。OPS-09の編集受入を再利用しowner別schema・生成領域・ID・履歴を保全。移行中の新旧参照、部分失敗、旧revision・rollback条件、複数owner参照整合を検証し、条件不成立なら自動切替・自動rollbackなし。

## F. Skill責務の適正化（最優先）

### OPS-18 Skillの責務適正化・ハーネスとの責務分離 (P0)

対象: 全Skill、既存Helper、qa-workflow、project-context、実行環境との境界。

現状: 成果物分類、案件識別・探索、配置合意、保存技術、認証・競合管理が専門QAの判断と混在し、読み込み量・ユーザー確認・重複契約を増やし得る。PR #40の旧kind別branch設計も同じ問題を含む。

改善: 確定方針を最初に適用し、各責務を「Skillに残す」「既存Helperへ委譲」「必要な場合だけハーネスへ委譲」「不要なので削除」に分類する。Skillの案件識別・切替、branch管理、Provider選択、認証方式選択、配置の再決定を除外する。意味的なQA scopeや制約・DEC/ASM・正式な仕様回答は維持する。project-contextのQAコンテキスト管理と案件管理を分離し、独立Skillとしての必要性は残存責務・他ownerとの重複に基づき評価する（廃止は未決定）。汎用ハーネス、中央台帳、保存基盤を新設しない。既存の保存・履歴・認可・scope・依存・完了判定の保証は削除しない。技術的に保証できない処理は局所blockする。旧案件/branch管理を名前だけ変えて他層へ丸ごと移管しない。 PRN-01〜08・Q01〜08を判断基準とし過剰防衛を含む追加機構に具体的必要性を求める。qa-workflowはQAのrouting・依存・引継ぎ・局所再開・完了確認に集中する。

受入: (1) 全Skillの責務/読込reference/入出力を棚卸し、削除・委譲・維持の理由を記録、(2) 同一のQA入力を異なる実行環境で用いて案件/branch/Provider判断なしに同じ意味成果物を生成、(3) 許可root内の固定相対配置・異なるrootの同名refの隔離・権限外拒否・履歴・CAS・readback・再開を確認、(4) 既存品質・安全・traceabilityの回帰なし、(5) 専門外判断、読込量、不要質問、設定/重複helper・管理契約の削減を測定、(6) 保存失敗を成功扱いしない。具体的な実装境界・必要最小の外部契約はPR #40後のbaselineで決める。

### 既存17件の責務再評価（実装境界の正本）

<!-- dprint-ignore -->
| ID | 残す・再利用するもの | 削除・外部化するもの |
| --- | --- | --- |
| OPS-01 | Q・根拠・候補・再開情報の意味、PR #40のhandoff契約 | 各Skillの保存先決定、状態管理の重複 |
| OPS-02 | 仕様判断・必要な承認内容、質問省略の根拠 | 配置・Provider・認証方式の再質問。実認可は外部 |
| OPS-03 | 実保存・依存整合・readback | 全ownerのProvider選択・拡張を必須化しない。既存Helper優先 |
| OPS-04 | 正式仕様判断と操作認可の区別、対象/根拠 | 認証方式選択、案件権限管理は外部。自己申告を認証しない |
| OPS-05 | owner意味検証・要求scope完全性・採用可否 | 実証済み共通verifierの重複、保存技術判断 |
| OPS-06 | 副作用の必要性・結果不明・cleanup判断 | 排他/予約・冪等保存は実行/保存層。不要な管理機構を作らない |
| OPS-07 | QA品質・実行/報告/完了の横断受入 | 特定案件管理・特定Providerの受入を一律強制しない |
| OPS-08 | WCAG文書整合の局所修正 | 別管理機構の追加なし |
| OPS-09 | QA前提・人間編集・正本反映の意味品質 | 案件初期化・配置決定をSkillから除外。必要なら外部 |
| OPS-10 | QAへの入力・必要な結果 | CI・外部起動は呼出し側。案件運用をSkillへ追加しない |
| OPS-11 | 品質・安全・効率・利用者負担の測定 | 専門外判断・読込・設定・重複処理を削減対象とする |
| OPS-12 | 指定root配下の固定相対配置・成果物粒度 | 案件単位配置提案・kind別branch・全root事前作成 |
| OPS-13 | 安定命名・identity・正本と派生物の区別 | branch/案件名を新規意味identityに混ぜない |
| OPS-14 | 外部指定rootと決定論的相対ref解決 | 案件探索・配置/Provider選択・新規stable keyの一律追加 |
| OPS-15 | 許可root内の発見・依存/鮮度・適用判断 | 案件横断探索、重複検索基盤、PR #40との二重実装 |
| OPS-16 | 正本・作業・機密証跡・コードの必要な境界 | 技術的強制をSkillの文章で代用しない。不要なroot/設定の新設 |
| OPS-17 | 既存資産・ID・履歴・互換性の保全 | 一括移行やbranch変換をSkillの責務としない |

### PR #40完了後の着手条件

参照: [PR #40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)、[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)、[PR #39](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/39)、[PR #17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)。PR #40の設計は利用者決定により指定ディレクトリ・責務縮小へ改訂する。旧kind別branch案は採用しない。

<!-- dprint-ignore -->
| ID | 着手前の確認 | OPS |
| --- | --- | --- |
| PRE-01 | 最終Skill構成・総数・登録を実装証拠で確認 | 05/12/18 |
| PRE-02 | PR #38/#40の実保存・承認/認可境界、自己申告と認証の区別 | 02/03/04 |
| PRE-03 | 指定rootのディレクトリ配置に統一、旧kind別branch案を撤回 | 12/13/14/18 |
| PRE-04 | 3 kindの固定相対配置・不変batch・候補・runの履歴を維持 | 12/13/17 |
| PRE-05 | 質問前の自己解決、対話提示と永続的質問発行を区別 | 01/02 |
| PRE-06 | 横断検索・既存成果物発見を再利用、重複基盤なし | 15 |
| PRE-07 | 無効・補助・必須・単体と要求scope完全性 | 05/07 |
| PRE-08 | 過去実行の完了証明と現在の採用可否を分離 | 05/15 |
| PRE-09 | semantic handoff keyと実owner一意性・結果不明からの再開 | 01/06 |
| PRE-10 | 64 KiB等の本文搬送制約、集約サイズ、根拠切捨て禁止 | 03/05/12/15 |
| PRE-11 | PR #40の品質・構成比較・効率baselineと責務削減指標 | 11/18 |
| PRE-12 | 実評価ランナー・CIの最新統合状況、旧未達/対象外 | 07/10/11 |
| PRE-13 | 最新mainで全OPSを対応済み/一部/未対応/受入のみへ再分類 | 全18件 |

上記は着手条件であり確認済みの受入結果ではない。PR #40が完了していない間は共通Skillの実装を始めない。既存の案件/branch管理を移行する必要性と方法は外部側の別判断とし、無断移行しない。

## レビュー反映と実装順序の候補

2026-11-25の文書レビュー（対象commit 351e4e925e74fb52f7a9ddcf777f3828ca3c2cc7）のRV-01〜18を既存OPS-01〜17に統合した。このレビューの処置では追加OPS IDを作らなかった。後続の利用者決定に基づくOPS-18は別途追加した。文書上の処置であり、Skill/runtime改善・実provider受入の完了を意味しない。

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
| 0 責務適正化・仕様整合 | 18/08 | PR #40後のbaseline再確認、全Skillの不要責務削減、WCAG旧guidanceの局所修正 |
| 1 成果物管理基盤 | 09/12/13/14/15/16/17 | 配置・命名・粒度・発見・保護・互換性、最終Skill構成の相対配置契約案 |
| 2 質問・承認・再開 | 01/02 | 中間保存許可、質問revision、内容承認と自動保存、局所停止・再開 |
| 3 正式保存・実行安全 | 03/04/06 | 外部から供給される保存能力・権限、独立readback、claim/予約/回復 |
| 4 完了検証・横断受入 | 05/07 | owner verifier、元依頼・scope・currentness、保存・実行・報告独立検証 |
| 5 案件接続・効率評価 | 10/11 | CI接続、品質/安全と効率・利用者負担測定 |

OPS-18を最初に適用し、不要な処理を削除してからPhase 1/2を並行検討する。Phase 3は必要最小の外部保存能力を確認する。OPS-16と現行安全制約は全Phaseで維持する。既存blocked操作をPhase順序で許可しない。独立作業の並行検討は可だが共有resourceの並列実行は既存制約に従う。既存owner/helperを優先し、新Skill・中央DB・中央mutable manifest・全成果物統一schema・全Skill専用key・汎用storage framework・一律配置移行は前提としない。

### 横断受入シナリオ候補

既存Deterministic Test・Semantic Evaluation・実Agent評価を再利用する。各シナリオで元依頼・scope・入力/保存revision・必要承認・実測または拒否証拠・再開条件を確認し未検証は未検証のまま記録する。

<!-- dprint-ignore -->
| ID | シナリオ | 期待する受入結果 | 関連OPS |
| --- | --- | --- | --- |
| AT-01 | 初回の実行環境 | 外部指定rootから相対配置を解決、Skillによる案件探索・配置再質問なし | 09/12/14/18 |
| AT-02 | 既存成果物利用 | 許可済みroot・ID・有効権限を維持、不要再質問なし | 09/14/17/18 |
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
| AT-21 | 責務境界・移植性 | 異なる外部実行条件で案件/branch/Provider判断なく同一意味成果物、許可外拒否 | 18 |
| AT-22 | 責務削減と回帰 | 専門外判断・読込・不要質問・重複管理削減、既存QA品質・安全・履歴維持 | 11/18 |
| AT-23 | 許可済み通常保存 | 個別承認なしで保存・readback、未承認候補はAuthority化しない | 01/02/03/04/18 |
| AT-24 | 直接Skill利用 | 特定ハーネスなしで必要入力から分析、必要時のみ保存先確認 | 12/14/18 |
| AT-25 | 最小構成 | 実リスクに比例した防御・形式・履歴、不要な専用基盤・複製・承認なし | 03/06/11/13/18 |

全て未実施の受入候補。ディレクトリ管理・責務適正化は確定済み。具体的な実装Plan、相対path、最小外部契約、実環境・過去対象外の再検証範囲は別途合意する。既存PR #22の未達・対象外・検証結果を上書きしない。
