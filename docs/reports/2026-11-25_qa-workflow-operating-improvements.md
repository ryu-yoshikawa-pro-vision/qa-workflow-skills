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

## 進め方の候補

OPS-08の文書整合確認とOPS-01/02の運用受入から開始。実provider・承認者が決まり次第OPS-03/04/06を優先し、OPS-05/07/09へ接続する。OPS-10/11は案件接続と品質確保後に評価。正式な実装Plan・優先順位は別途合意する。
