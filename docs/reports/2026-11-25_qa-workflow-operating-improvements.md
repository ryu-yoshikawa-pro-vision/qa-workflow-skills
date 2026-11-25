# QAワークフロー運用上の改善候補

基準: main 197f1e0e1abe870b0cc793355e7abf73bf241d87（2026-11-25）。全37 QA Skillと主要reference・runtime、[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)を静的に照合した。以下は未着手の改善候補であり、実装指示・承認済みPlan・既存受入条件の変更ではない。優先度は暫定（P0: 安全・誤完了、P1: 継続性・運用負担、P2: 接続・効率）。案件別保存先という設計自体は欠陥ではない。新Skill・中央台帳・汎用storage frameworkは前提としない。

## A. 質問・承認・checkpoint

### OPS-01 質問前後と工程引継ぎの永続化 (P1)

対象: qa-workflow、question-analysis、agent-answer-form、各設計owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)はstate・再利用・再開を、[question guidance](../../skills/question-analysis/references/guidance.md)はQ ID・回答正規化を規定する。質問提示直後・回答反映後・工程間の保存を全owner横断で自動保証する受入は確認できなかった。

改善: [共通運用契約](../reference/qa-workflow-operating-contract.md)のCP03/04/05/08を既存stateと各ownerの保存入口で検証する。Q ID、停止scope、完了済みartifact ref/revision、候補、未保存理由、再開ownerを保持。単発読取へ永続化を強制しない。

受入: 質問提示直後の中断・別session再開、部分回答・保留、保存未設定/失敗、source改版を試験し、解決済み論点・完了済み工程の反復と未保存の成功表示を防ぐ。

### OPS-02 承認要求の集約と進行許可の分離 (P1)

対象: qa-workflow、project-context、question-analysis、計画・保存・実行owner。

現状: continuous/gated、Q06配置合意、Git既定承認方式は既存。複数成果物の提示単位・部分承認の横断保証は未確認。ゲートグループ欄は実動作保証ではない。

改善: 既存approval refs、scope/revision、失効条件で独立承認可能な項目をまとめる。回答、進行、配置、保存、外部副作用を区別し承認条件を緩めない。

受入: 部分承認・拒否・保留・revision変更・権限不足・有効合意再利用・モード変更で未承認操作を拒否し、重複質問を抑える。承認単位の変更は別途合意。

## B. 保存・承認・完了証拠

### OPS-03 Owner別保存接続 (P0)

対象: project-context、feature-analysis、test-item-analysis、test-condition-analysis、計画3 Skill、ui-target-analysis、qa-workflow。

現状: [project-context](../../skills/project-context/SKILL.md)には明示選択local/Git provider、候補ownerにはwrite preconditionがあるが全ownerの実保存・履歴・readbackは未確立。

改善: 案件の正本・provider・承認方式を先に選び、既存adapterを利用可能なownerから接続。候補→正式保存→current引継ぎのref/revision/hashを実証する。

受入: 同一revisionの並行更新、create-if-absent、履歴、readback不一致、権限失効、応答消失、中断復帰を実providerで確認。fixtureだけで遠隔先を保証しない。

### OPS-04 認証済み承認・対象外判定 (P0)

対象: qa-workflow、project-context、計画3 Skill、defect-management、test-evaluation。

現状: [保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)には対話同意・通常push・activity照合があるが、excluded_by_approvalの真正性照合が未定義。F 3 Skillのvalidatorは本人性を証明しない。

改善: 案件の承認元・信頼境界を選び、scope/revision/actor/権限/期限を実照合して必要ownerと既存exclusion判定へ接続。

受入: 正しいactor/before/afterのみ許可、別actor・scope・revision・失効・activity遅延・取得不能をblock。未承認除外で完了分母を縮小しない。

### OPS-05 Owner verifier未登録scope (P0)

対象: qa-workflow/scripts/owner_verifiers.py とproject-context、feature-analysis、ui-target-analysis、defect-management、test-evaluation等。

現状: 登録済み7 Skillはtest-item-analysis、test-condition-analysis、e2e-test-selection、test-reporting、test-requirements-analysis、test-architecture-design、test-management。既存runtime-v2 rootは別経路。未登録scopeはunverified_scopes。計画3 Skillはfixture検証のみ。

改善: 各ownerの実保存正本・検証入口・currentnessを接続。OPS-03/04の必要条件を満たす。単なる登録で完了としない。

受入: current実成果物だけ完了、改変本文・別scope・stale/欠落revision・偽readbackを拒否。再開時に独立読戻しし、既存runtime-v2の回帰なし。

## C. 実行安全・継続管理

### OPS-06 Claim回復と共有resource予約・解放 (P0)

対象: qa-workflow、各実行owner。

現状: claimの原子的作成・読戻しはあるがrecover_claimの安全な条件付き解放と外部reservation実readback/releaseは未接続。結果不明時は再実行不可。

改善: 案件選定providerと元ownerの実開始・結果・cleanup取得を接続。旧claim/予約を無断削除・移行しない。複数host/network filesystemは個別実証。

受入: 二重受付、開始前中断、応答消失、cleanup失敗、権限失効、並行workflow隔離、解放競合。状態不明では再実行しない。

### OPS-07 実行・証跡・報告の横断受入 (P1)

対象: test-execution、e2e-test-*、testware-*、regression-testing、exploratory-testing、defect-management、test-reporting。

現状: 各ownerはraw結果・分析・報告・cleanupを分離するが実provider経由の横断受入に未達が残る。

改善: 既存経路で実行前条件→raw結果→分析→欠陥候補→統合報告を実案件接続。初回FAILや予定母集団を書き換えない。

受入: 未実行、判定不能、FAIL、retry、収集不全、cleanup未確認、修正確認と別目的Regression、証跡保護、外部Issue未認可拒否。

## D. 文書整合・接続・効率

### OPS-08 WCAG closureガイダンスの旧記述 (P1)

対象: skills/qa-workflow/references/guidance.md §WCAG formal evaluation state（基準revision L252）、skills/qa-workflow/SKILL.md、skills/qa-workflow/scripts/workflow_runtime.py の _execute_and_finalize_wcag_report（L245以降）。

確認した差異: guidanceは現行finalize-wcag-reportがcaller提供dependency metadataとcandidateを照合するだけでcurrent rowを独立取得しないと記載。一方SKILL.mdはQA runtimeでcurrent stateを取得し公式WCAG close-reportを内部実行・CAS保存・独立readback後に完了する契約。コードもread-wcag-evaluation-stateを内部実行し、取得結果からWCAG runtimeを実行、_record_wcag_report_runtime_execution、finalize_wcag_reportを呼ぶ。旧説明は少なくとも現行owner内部実行経路と一致しない。

改善: 現行コード・schema・否定試験と照合してguidance更新。特権DB writer、複数host、認可や意味判断まで保証すると解釈しない。今回の静的確認は攻撃経路全体の実証ではない。

受入: 偽造candidate/metadata拒否、owner内部実行、CAS conflict、履歴欠損、closure不完全、独立readbackを確認し文書とコード・テストを一致させる。

### OPS-09 案件初期化・配置・人間編集の受入 (P1)

対象: project-context、feature-analysis、ui-target-analysis、spec-analysis、qa-workflow。

現状: Q06と既存writerはあるが実案件の配置合意・人間編集から正式保存までの横断受入には未達が残る。

改善: 既存template・writerを用い、必要時の不足field確認・既存合意再利用を実案件で検証。機能別物理分割を強制しない。

受入: 既存配置維持、候補重複・アクセス不能、新規配置未承認、正本直接改変、手動ID・行削除、競合、承認済み採用、局所変更伝播。

### OPS-10 外部起動・製品CI接続 (P2)

対象: 呼出し側、qa-workflow、feature-analysis、CI handoff。

現状: PR/merge/release/資料改版の起動は呼出し側責務。実成果物取得・承認元未選定なら製品CI統合はblocked。

改善: 案件の起動・受渡し方式を合意し既存ci_handoff.pyを接続。Skillに監視基盤やCI Agent起動を新設しない。

受入: PR追加commit、merge、release、外部資料改版、旧build結果、未分類差分、必須artifact欠落。未設定とfailを区別。

### OPS-11 効率と運用負荷の実測 (P2)

対象: qa-workflow、EVALS.md、呼出し側。

現状: PR #22効率比較はunproven、同一入力再依頼等の悪化と安全/品質未達を保持。

改善: 初回、同一入力再依頼、変更、外部資料改版、中断再開の既存比較条件で質問数、不要再生成、保存漏れ、所要時間、費用/token、品質・安全を測る。

受入: 既存比較器、独立試行、同条件・品質/安全PASS、測定不能の明示。介入削減のため承認や品質を弱めない。

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

### OPS-13 成果物の命名規則と正本・表示物の識別 (P1)

対象: 全成果物owner、qa-workflow、project-context。

現状: [ui-target-v1](../../skills/spec-analysis/references/ui-test-target-analysis.md)は標準file群、[knowledge](../../skills/qa-knowledge/references/data-contract.md)はentry-ref.md、[artifact_graph.py](../../skills/qa-workflow/scripts/artifact_graph.py)はUUID.json・digestによるsnapshot等、[testware runner](../../skills/testware-execution/scripts/runner.py)はmanifest.json・attempt log等を規定する。一方、多くの計画・設計・報告ownerのテンプレートは出力内容を規定するが、共通の保存ファイル名は確認できない。

改善: ownerごとにcanonical名、表示用Markdown等の派生物、draft・一時物、履歴、Run/attemptの命名と拡張子・schemaの対応を定める。既存の固定名・writer・安定IDを優先する。論理artifact refとprovider revisionを正本識別に使い、pathや日時だけを識別・currentnessの根拠にしない。単なる再出力で正本を複製せず、Run/attemptの証跡は独立したidentityで保持する。

受入: 同一成果物の再依頼は既存正本を解決し、異なるscope・Run・attemptは衝突しない。正本と表示物・draftの誤認を拒否。大文字小文字、禁止文字、path traversal、名前衝突、既存固定名との互換性を対象providerで検証。

### OPS-14 保存先解決と案件設定 (P1)

対象: project-context、qa-workflow、各保存owner。

現状: Section 16にはqa.workflow_state_root、qa.knowledge_root、qa.feature_artifact_root、qa.reservation_root等がある。その他の成果物は主にSection 14や明示refに依存し、標準配置と案件別設定の横断解決規則が不足する。専用stable keyのないこと自体を欠陥とせず、既存の契約を維持する。

改善: 明示された依頼scope・操作許可を確認し、既存正本と有効な配置合意を優先する。矛盾する明示指定は配置変更候補として扱い、無断上書きしない。既存がないと確認できた場合は承認済み案件設定を適用し、なければ標準案を提示して初回合意を得る。未解決・重複・アクセス不能は不存在と区別し、正式保存をblockする。Section 14/16と既存prepare-placementを再利用し、全Skill専用keyや新中央台帳は必須としない。

受入: 明示指定、既存配置、案件override、標準案、設定なし、矛盾、重複、アクセス不能を個別に確認。別sessionで解決結果が一致し、有効な合意が変わらなければ再質問しない。保存先が解決してもnative CAS、権限、承認、readbackが不足すれば正式保存しない。

### OPS-15 保存済み成果物の発見・再利用 (P1)

対象: qa-workflow、project-context、feature-analysis、全成果物owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)は既存state・input revisionの再利用、[project-context guidance](../../skills/project-context/references/guidance.md)は許可範囲の列挙と候補判定を定めるが、全ownerの正本発見と重複検出の共通受入は未確認。

改善: 承認済みroot/direct ref、owner、scope、artifact identity、provider revision、source依存、既存stateを使って発見・currentnessを確認する。固定root scanは既存ownerの許可範囲・完全性・型検証に従い、無制限の再帰探索やpath/ファイル名だけの推定を避ける。重複・一覧取得不全・不明参照は明示し、新規作成や自動選択を止める。

受入: 別agent/sessionから同一正本を発見、変更なしの再依頼で不要再生成なし、部分改版では影響scopeのみ再検証。重複・欠落・stale・読取不能・列挙打切りを区別し、既存正本を保全する。OPS-01/03/05と接続する。

### OPS-16 永続成果物・一時作業物・機密証跡の分離 (P0)

対象: qa-workflow、project-context、agent-answer-form、test-target-inspection、各実行・評価owner。

現状: [test-target-inspection](../../skills/test-target-inspection/references/guidance.md)は指定先・秘密情報の保存制約、[testware-execution](../../skills/testware-execution/references/guidance.md)はrepo外の保護された成果物先を定める。agent-answer-formはSkill外作業dirを使用する。全owner横断の保存区分・保持・cleanup・共有範囲は未統一。

改善: 正本、再生成可能な派生物、再開に必要なdraft、短期一時物、raw実行証跡、機密証跡を区別する。保存可否、許可root、アクセス範囲、保持・cleanup方針、参照の有効期限と非保存理由を案件条件で明確にする。rawの無断commit・共有を禁止し、安全な要約/参照のみを渡す場合も元証跡の取得可能性を偽らない。保存不能なら未保存と完了条件への影響を明示する。

受入: secretを含む証跡、安全な保存先なし、誤ったroot、別Runの証跡、保持期限切れ、一時物cleanup失敗、再開に必要な候補の保全を確認する。既存runnerの保護領域と安全契約を維持し、正式履歴をcleanupで削除しない。

### OPS-17 既存配置との互換性・変更管理 (P1)

対象: project-context、qa-workflow、全成果物owner。

現状: Q06は既存配置優先、初回合意、物理分割の必要性判断、無断移動禁止を定める。標準案導入時に既存案件の混在構成・個別overrideを横断検証する必要がある。

改善: 有効な既存配置を優先し、標準化のみを理由とする移動・改名・分割・再保存を行わない。変更が必要な場合だけ、移行対象・旧新ref・依存関係・履歴・権限・互換読取・条件付き切替・rollback・レビュー範囲を明示して別途合意する。現行writer/schemaを尊重し、二重正本を作らない。OPS-09の案件初期化・人間編集受入と接続する。

受入: 既存案件の無変更再利用、異なるprovider/配置の混在、部分override、変更未承認、移行途中の競合・失敗、旧revisionの参照、rollbackを確認。標準構造が既存データの消失・二重正本・ID変更を生まないことを示す。

## 進め方の候補

OPS-12〜17を一つの配置・発見契約グループとして詳細化し、OPS-08の文書整合確認、OPS-01/02の運用受入と並行して検討する。配置・命名・正本識別・保護境界を決めてから実provider接続（OPS-03）を具体化する。OPS-16の安全制約は先行して維持し、実provider・承認者が決まり次第OPS-03/04/06を優先、OPS-05/07/09へ接続する。OPS-10/11は案件接続と品質確保後に評価。正式な実装Plan・優先順位・標準pathの採用は別途合意する。
