# QAワークフロー運用上の改善候補

基準: main 197f1e0e1abe870b0cc793355e7abf73bf241d87（2026-11-25）。全37 QA Skillと主要reference・runtime、[PR #22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)を静的に照合した。以下は未着手の改善候補であり、実装指示・承認済みPlan・既存受入条件の変更ではない。優先度は暫定（P0: 安全・誤完了、P1: 継続性・運用負担、P2: 接続・効率）。案件別保存先という設計自体は欠陥ではない。新Skill・中央台帳・汎用storage frameworkは前提としない。

## 確定前提と適用範囲

[共通原則](../reference/qa-skill-design-principles.md)（PRN-01〜09、Q01〜12）が設計の正本。利用者合意済みであり、再承認不要。OPS-18を先に適用し、Skill・Runtime・validator・Helper・呼出し側の不要な責務・過剰防衛を削減する。以下の「現状」は調査時点の旧契約・制約であり、「改善」「受入」は新方針の候補。現行の未改修契約を文書だけで解消したことにしない。PR #40完了後に実装証拠を確認し、対応済みの再実装や不要になった受入を除く。 PRN-09に従い関連コード・Skill・文書・テスト・設定を同期し、不要な実装・記述・重複だけを除去する。

調査・レビューで使用したG1〜G5、CP01〜10、配置区分等の詳細は、[調査時の共通運用契約](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/7339200bdffd765a9e71091905e0143c144db089/docs/reference/qa-workflow-operating-contract.md)、[調査時の成果物マトリクス](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/7339200bdffd765a9e71091905e0143c144db089/docs/reference/qa-workflow-artifact-matrix.md)、[調査時の利用者ガイド](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/7339200bdffd765a9e71091905e0143c144db089/docs/reference/qa-workflow-user-guide.md)を参照する。これらはレビュー根拠の履歴であり、運用上の正本ではない。保存・承認・配置等の必要な実行条件は担当Skill・Runtimeと適用される契約を確認する。

## A. 質問・承認・checkpoint

### OPS-01 質問前後と工程引継ぎの永続化 (P1)

対象: qa-workflow、question-analysis、agent-answer-form、各設計owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)はstate・再利用・再開を、[question guidance](../../skills/question-analysis/references/guidance.md)はQ ID・回答正規化を規定する。質問提示直後・回答反映後・工程間の保存を全owner横断で自動保証する受入は確認できなかった。

改善: Q09で成果物作成依頼を原則保存対象とし、明示の非保存指示を優先する。Q02の5契機（処理完了、質問前、回答反映後、中断、引継ぎ前）で必要な成果物だけ自動保存する。Q ID、根拠、停止scope、再開先、完了成果物参照は既存成果物から取得できるものを重複保存しない。専用stateは必要情報が復元できない場合だけ利用する。単発相談・レビュー・調査は原則対話回答のみ。調査時のCP01〜10は履歴参照であり、新しい全Skill共通checkpointを実装しない。

受入: 質問提示直後の中断・別session再開、部分回答・保留、保存未設定/失敗、source改版を試験し、解決済み論点・完了済み工程の反復と未保存の成功表示を防ぐ。

追加要件：RV-03/07/09：質問提示前・回答反映後・引継ぎを必要範囲で区別し、Q ID・元質問定義・根拠・回答対応を保持する。HTML利用時は意味が変わった旧フォーム/旧回答を誤適用しない。保存不能でも質問・安全な候補・再開情報を返し、復元保証なしを明示する。通常保存に個別承認不要。未承認変更候補を正式仕様・承認済み決定と区別し、既存の意味を維持する。

### OPS-02 承認要求の集約と進行許可の分離 (P1)

対象: qa-workflow、project-context、question-analysis、計画・保存・実行owner。

現状: continuous/gated、開発連動QA Planの旧Q06配置合意、Git既定承認方式は既存。複数成果物の提示単位・部分承認の横断保証は未確認。ゲートグループ欄は実動作保証ではない。

改善: 許可済み通常保存は都度承認なしとする。候補・回答の記録と内容の正式承認、工程進行、操作認可、破壊的変更を区別する。正式決定・仮定採用・承認済み仕様の意味変更・必要な外部操作は既存の有効な承認単位でまとめる。案件・配置・保存方式の再質問はしない。既存の候補欄・文書構造を優先し、別draftや承認状態管理を一律新設しない。計画等の正式確定・リスク受容が必要な場合は維持する。 Q10に従い通常の内容承認は依頼者の明示判断で成立する。Q11のcontinuousを既定としgatedは明示指定時のみ。案件単位の進行設定を要求しない。

受入: 許可済み通常保存が承認待ちで停止しない、承認済み仕様と未承認変更候補が混在しても前者の意味を保全し後者を正式採用しない、通常の明示承認は追加認証なしで採用、別権限者が必要な判断・外部操作では必要な確認を維持。既定continuousと明示gated、必要承認の拒否・保留・有効性に影響する変更を確認する。

追加要件：RV-03/08/16：Q03を適用。仕様決定、計画承認、進行、書込み許可、内容承認、操作認可、リスク受容を区別。必要承認のscope/ref/revision・差分・権限・失効条件は維持。通常保存には個別承認不要。

## B. 保存・承認・完了証拠

### OPS-03 必要な保存・更新保証の適正化 (P0)

対象: project-context、feature-analysis、test-item-analysis、test-condition-analysis、計画3 Skill、ui-target-analysis、qa-workflow。

現状: [project-context](../../skills/project-context/SKILL.md)には明示選択local/Git provider、候補ownerにはwrite preconditionがあるが全ownerの実保存・履歴・readbackは未確立。

改善: 指定rootで既存ファイル操作・Helperを優先し、通常の単独保存は結果確認、更新は対象・必要内容の保全を基本とする。共有更新・履歴再取得・後続の正本検証・外部操作に実際に必要な場合だけ条件付き保存、一意性、revision/hash、独立readback等を要求する。必要な能力不足は該当操作のみblockし、汎用保存層や全owner接続を目標にしない。

受入: 単独新規/更新の保存・失敗時報告・承認済み内容の保全。実共有更新が必要な経路では同一revisionの競合、create-if-absent、結果不明、必要履歴とreadbackを確認する。外部操作は必要権限・失効・再実行防止を確認。fixtureだけで未検証の遠隔先を保証しない。

追加要件：RV-01/02/15：保存・内容承認・currentnessを分離。結果不明時は実保存先を必要範囲で照合し、旧版のまま・成功済みと断定しない。複数成果物の依存整合が必要な場合は該当refと内容/必要revisionを照合し下流currentを保留。個別CASを一括整合とせず、盲目的再試行・無断rollback・別正本作成をしない。過去対象外は自動解除しない。

### OPS-04 必要な内容承認・操作認可・対象外判定 (P0)

対象: qa-workflow、project-context、計画3 Skill、defect-management、test-evaluation。

現状: [保存・承認契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)には対話同意・通常push・activity照合があるが、excluded_by_approvalの真正性照合が未定義。F 3 Skillのvalidatorは本人性を証明しない。

改善: Q10を適用し、通常の仕様決定・仮定採用・QA方針等は依頼者の明示回答・承認を採用する。決定内容・対象・必要な適用範囲を記録し、別権限者・組織決裁・対象外採用やリスク受容に別の承認契約がある場合・外部操作に必要な権限がある場合だけ既存経路で確認する。通常保存は許可範囲で自動化し、専用認証host・操作別承認/認可発行を一律要求しない。AIの自己申告や依頼者にない権限の推定を認可の証拠にしない。

受入: 通常の明示承認で内容判断が成立し、保留・曖昧回答・AI推定は承認にならない。別権限者・組織決裁・外部操作に必要な主体・対象・有効権限を確認し、承認に影響する変更・失効・権限不明は該当判断/操作をblockする。未承認除外で完了分母を縮小しない。通常保存は個別承認不要。

追加要件：内容承認は対象と明示判断を記録し、追加権限確認が必要な場合だけ該当する権限者・revision/build・失効条件を確認する。低リスクの通常保存へこの契約を拡大しない。必要な承認は形式validatorや編集提出だけで成立させず、未承認除外を必須scopeから外さない。

### OPS-05 QA品質・完了検証契約の適正化 (P0)

対象: qa-workflow/scripts/owner_verifiers.py とproject-context、feature-analysis、ui-target-analysis、defect-management、test-evaluation等。

現状: 登録済み7 Skillはtest-item-analysis、test-condition-analysis、e2e-test-selection、test-reporting、test-requirements-analysis、test-architecture-design、test-management。既存runtime-v2 rootは別経路。未登録scopeはunverified_scopes。計画3 Skillはfixture検証のみ。

改善: owner verifier・Runtime・validator・schema・metadataを利用目的、誤りの影響、再利用・完了証拠の必要性から棚卸しする。既存の意味品質・追跡性・必要検証を維持し、通常の単発分析は適切な出力検証、継続成果物や実行・正式完了の証明は必要な参照/実証を確認する。全owner登録、全成果物のcanonical JSON化、保存証拠一律要求を目標としない。不要な契約は該当Planで明示的に置換し回帰を確認する。

受入: 元依頼の必須scopeと必要な意味・形式・依存検証を満たす。保存が要求されない単発分析を保存証拠不足で誤停止しない。保存・再利用・実行証明が必要な経路では改変、別scope、stale、偽証拠を拒否し、変更したruntime-v2/owner契約の回帰なし。

追加要件：RV-04/05/13：元依頼・要求成果物・必須scope・除外候補の対応を開始/完了時に照合し、入力母集団の完全性、必要な証拠と対象・実行・根拠の対応、信頼境界を確認する。requested_scopes、workflow_ref、owner登録・保存証拠形式等は現行の実現手段であり、改修後に一律維持することを目的としない。必要な保証を維持する代替手段は対象Planで特定し回帰を確認する。受入：必須scope漏れ、入力列挙漏れ、別対象/実行の証拠、必要検証不足、承認不明除外、依存する部分保存。

## C. 実行安全・継続管理

### OPS-06 必要な副作用・共有資源の実行安全 (P0)

対象: qa-workflow、各実行owner。

現状: claimの原子的作成・読戻しはあるがrecover_claimの安全な条件付き解放と外部reservation実readback/releaseは未接続。結果不明時は再実行不可。

改善: 実際に重複実行・共有資源の競合・結果不明が問題となる操作に限り、既存ownerの冪等開始、実開始/結果/cleanup取得、必要予約を利用する。通常の単独文書保存にclaim・予約・排他基盤を追加しない。既存claimは必要性と実運用を評価して維持/削減し、必要保証未確認は該当操作のみblockする。

受入: 実行・副作用が関係する経路で、必要な二重受付防止、開始前中断、結果不明、cleanup、権限、共有時の隔離・解放競合を確認する。結果不明で有害な操作は盲目的に再実行しない。

追加要件：RV-01/12：外部Issue更新や共有資源操作など結果不明・重複が有害な副作用は既存ownerの必要な原子的開始/冪等契約を優先し、元操作・cleanup・必要revisionを照合するまで盲目的に再実行しない。claimを認可・CASの証明としない。実分離/予約が必要な並行実行の既存制約は改修まで維持する。

### OPS-07 実行・証跡・報告の横断受入 (P1)

対象: test-execution、e2e-test-*、testware-*、regression-testing、exploratory-testing、defect-management、test-reporting。

現状: 各ownerはraw結果・分析・報告・cleanupを分離するが実provider経由の横断受入に未達が残る。

改善: 既存経路で実行前条件→raw結果→分析→欠陥候補→統合報告を必要な対象・実行環境で検証。初回FAILや予定母集団を書き換えない。

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

現状: 開発連動QA Planの旧Q06と既存writerはあるが実案件の配置合意・人間編集から正式保存までの横断受入には未達が残る。

改善: QA目的・用語・業務制約・DEC/ASMなどの意味管理と人間編集の受入に集中する。既存template・writerで必要なQA情報の不足確認・有効な判断の再利用を検証。案件初期化・配置決定をSkillから除外し、必要な入力を外部から受ける。通常のMarkdown編集は許可範囲・必要な差分確認を基本とし、特殊な生成領域・ID・正式仕様変更だけ該当ownerの制約を適用する。

受入: 許可済み通常文書の編集・保存、既存正本再利用、正式意味変更/機械生成領域等の必要な制約、正本の競合・不明・アクセス不能時の保全、局所変更伝播。案件探索・配置承認を要求しない。

追加要件：RV-10/14/15/17：配置・発見規則はOPS-14/15、移行はOPS-17を根拠とし、ここではQAコンテキスト・人間編集の横断受入を担当。UI package固有生成領域・draft key・retire・snapshot・writerを他ownerへ無条件流用しない。正式判断が必要な編集に限り提出と採用承認を分離。通常の非破壊的文書編集には専用writer・作業branch・個別承認を一律要求しない。直接改変時は編集案と元revision保全、無断復旧なし。過去対象外（開発連動QA Planの旧Q06等）は維持し再検証は別途合意。

### OPS-10 外部起動・製品CI接続 (P2)

対象: 呼出し側、qa-workflow、feature-analysis、CI handoff。

現状: PR/merge/release/資料改版の起動は呼出し側責務。実成果物取得・承認元未選定なら製品CI統合はblocked。

改善: 呼出し側が起動・入力/結果受渡しを管理し、既存ci_handoff.pyは必要な場合に利用する。Skillに案件運用・監視基盤・CI Agent起動を新設しない。 指定されたrepo・branch・commit・PR差分等のQA情報源の取得・意味分析は必要なSkillの責務とし、Git管理・案件運用とは区別する。

受入: 実際に必要とされる外部起動・資料変更・結果受渡しの経路について、変更元revision/build、未分類差分、必要成果物欠落を確認する。未設定とfailを区別。使用しない起動方式・接続を新設しない。

追加要件：RV-15：過去対象外のrelease通し・実環境/CI接続の再受入は案件選定後に別途合意。source revision・build・母集団を独立確認。sample CIの分類・列挙対象（JSON等）の制約を一般化しない。未設定/未取得をPASSにしない。

### OPS-11 効率と運用負荷の実測 (P2)

対象: qa-workflow、EVALS.md、呼出し側。

現状: PR #22効率比較はunproven、同一入力再依頼等の悪化と安全/品質未達を保持。

改善: 初回、同一入力再依頼、変更、外部資料改版、中断再開の既存比較条件で質問数、不要再生成、保存漏れ、所要時間、費用/token、品質・安全を測る。

受入: 既存比較器、独立試行、同条件・品質/安全PASS、測定不能の明示。介入削減のため承認や品質を弱めない。

追加要件：人間の作業・待ち時間、質問/承認回数、再開時再入力、保存漏れを測定候補に追加。人間レビュー・承認時間は過去比較で対象外承認済みのため、新たに測定する場合は計測法・比較母集団・範囲を別途合意し過去測定値に混入させない。品質・安全合格を前提にする。

## E. 成果物の標準配置・命名・発見

追加調査: 作業branchの 412cabf22710b6b4abccfa6330fc7be538c6dbbf を基準に全37 SkillのSKILL.md、主要reference、関連Plan、一部保存helperを静的確認した。成果物の論理schema、保存先root、物理配置、命名、永続化能力は別々に評価する。既存配置を優先する[開発連動QA Planの旧Q06（配置契約）](../plans/2026-11-07_122247_development-qa-traceability.md)は維持する。以下は指定root配下の標準相対配置案。旧案件別配置判断は撤回し、既存配置への互換対応が必要なら外部境界で行う。現行実装の固定パス仕様ではない。

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

改善: 人間向け正本は読みやすい構造化文書を優先し、機械処理・再現性・検証上の具体的な必要性がある部分だけJSON等を採用する。既存の固定名・安定ID、必要なRun/Attempt・根拠履歴を維持。pathだけで意味同一性を推測せず、必要な参照・revision/hashを用いる。全成果物の二形式化、版番号、履歴複製、Runtime都合だけのmetadataを削減する。

受入: 同一成果物の再依頼は既存正本を解決し、異なるscope・Run・attemptは衝突しない。正本と表示物・draftの誤認を拒否。大文字小文字、禁止文字、path traversal、名前衝突、既存固定名との互換性を実際のファイル操作条件で必要範囲を検証。

追加要件：RV-09：安定正本名・scope識別・Run/Attempt ID・必要なsnapshot・作業領域を分離。日時/版を一律付与しない。HTML利用時のフォーム元定義/必要revisionと回答を対応付け旧HTML/質問履歴を保持。改版後の旧回答自動適用禁止。命名変更で論理ID・履歴・依存を失わない。

### OPS-14 外部指定root・相対ref解決 (P1)

対象: 全成果物owner、決定論的保存Helper、外部入力境界。

現状: Section 16にはqa.workflow_state_root、qa.knowledge_root、qa.feature_artifact_root、qa.reservation_root等がある。その他の成果物は主にSection 14や明示refに依存し、標準配置と案件別設定の横断解決規則が不足する。専用stable keyのないこと自体を欠陥とせず、既存の契約を維持する。

改善: 指定root・許可入力ref・操作可否を呼出し元（ハーネスまたは直接利用時の明示入力）から受け、標準相対pathを既存Helper・標準操作で解決する。既に指定された作業先を利用し、保存が必要で場所が不明な場合だけ確認する。案件探索・配置/Provider選択・専用stable key・初回配置承認は不要。重複・アクセス不能を不存在とみなさず、該当する新規作成・更新だけ停止する。旧配置との互換/移行は必要時に外部側で判断する。

受入: 直接指定/ハーネス経由、既に指定された作業先、保存先未指定の分析継続、必要時のみ場所確認、許可外/重複/アクセス不能/別root同名refの区別。許可済み通常保存は個別承認不要。競合・履歴・外部認可等は該当する経路だけ必要保証を確認する。

追加要件：RV-14：旧Project Context bootstrap案は撤回する。QAに必要なコンテキストは外部指定の入力・相対refから取得し、未取得を不存在とみなさない。案件識別・初回探索入口の決定・Section 12/14/16の運用設定解決はSkillの責務外。入力不足時の分析継続と正式保存停止を分ける。

### OPS-15 保存済み成果物の発見・再利用 (P1)

対象: qa-workflow、project-context、feature-analysis、全成果物owner。

現状: [workflow guidance](../../skills/qa-workflow/references/guidance.md)は既存state・input revisionの再利用、[project-context guidance](../../skills/project-context/references/guidance.md)は許可範囲の列挙と候補判定を定めるが、全ownerの正本発見と重複検出の共通受入は未確認。

改善: 外部指定root/許可direct ref、owner、scope、artifact identity、必要な保存revision・source依存・既存stateを使って発見・currentnessを確認する。必要時の範囲限定探索は既存ownerの許可範囲・完全性・型検証に従い、無制限の再帰探索やpath/ファイル名だけの推定を避ける。重複・一覧取得不全・不明参照は明示し、新規作成や自動選択を止める。

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

現状: 開発連動QA Planの旧Q06は既存配置優先、初回合意、物理分割の必要性判断、無断移動禁止を定める。標準案導入時に既存案件の混在構成・個別overrideを横断検証する必要がある。

改善: 標準化のみを理由に既存正本を移動・改名・分割・再保存しない。移行が必要ならSkill外の作業として対象・旧新ref・依存・履歴・権限・互換読取・条件付き切替・rollback・レビュー範囲を別途合意する。既存writer/schemaを尊重し二重正本を作らない。OPS-09の人間編集受入と接続。

受入: 許可済み既存成果物の無変更再利用、別rootの同名ref分離、未承認移行拒否、必要な外部移行時の競合・失敗、旧revision参照・rollback。標準構造が既存データ消失・二重正本・ID変更を生まないことを示す。

追加要件：RV-10：配置変更と人間編集採用を区別。OPS-09の編集受入を再利用しowner別schema・生成領域・ID・履歴を保全。移行中の新旧参照、部分失敗、旧revision・rollback条件、複数owner参照整合を検証し、条件不成立なら自動切替・自動rollbackなし。

## F. Skill責務の適正化（最優先）

### OPS-18 Skill・Runtime・Helperの責務適正化 (P0)

対象: 全Skill、既存Helper、qa-workflow、project-context、実行環境との境界。

現状: 成果物分類、案件識別・探索、配置合意、保存技術、認証・競合管理が専門QAの判断と混在し、読み込み量・ユーザー確認・重複契約を増やし得る。PR #40の旧kind別branch設計も同じ問題を含む。

改善: 共通原則を最初に適用する。全Skillに加えRuntime・validator・Helper・呼出し側の契約を確認し、維持/既存手段への委譲/必要な外部責務/削除に分類する。QA固有の質問・根拠・結果は担当owner、次工程・再開・完了判断はqa-workflow、実行環境管理は呼出し側。既存成果物で復元可能な情報の重複state、必要性のない保存証拠/validator/metadataを削減する。project-contextの存廃はQA専門責務から判断する。既存保証は必要性を評価し、変更する契約・回帰範囲を対象Planで明示する。不要な管理を別層へ移すだけの変更や汎用基盤新設は行わない。 Q12に従い実装不要・対応済み・外部責務・受入のみ等を再評価し、必要な対応と受入に絞る。

受入: 実際に変更する責務・契約について、(1) 専門外処理・重複の削減理由、(2) 直接利用を含む必要な実行条件でQA品質・根拠追跡・再開が維持されること、(3) 実リスクに応じた必要な保存・権限・履歴・競合・完了検証、(4) 読込・質問・設定・重複処理の削減を既存評価で確認する。全ownerに同一のCAS・保存証拠・state・専用検証基盤を要求しない。未確認は未確認と記録する。

### 責務再評価の扱い

各OPSの改善・受入本文を実装検討の入口とし、別の責務再評価表を正本にしない。共通原則とOPS-18を優先して削減・維持・委譲を判断する。

### PR #40完了後の確認（必要なOPSに適用）

参照: [PR #40](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/40)、[PR #38](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/38)、[PR #39](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/39)、[PR #17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)。PR #40の設計は利用者決定により指定ディレクトリ・責務縮小へ改訂済み。対象PRは参照のみとし変更しない。旧kind別branch案は採用しない。

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
| PRE-13 | 最新mainで全OPSの必要性・残存差分をQ12に従い再評価（対応済み/一部/必要・未対応/不要/外部責務/受入のみ等） | 全18件 |

PR #40完了後に最新mainと最終実装を確認する（PRE-01/13）。他のPREは関連OPSの検討・受入に必要なものだけ適用する。一部の外部接続・計測・受入未確認を理由に独立した文書修正や責務削減まで止めない。PR #40完了前に共通Skillの実装を始めない。未検証の操作は未検証のままとし、必要な安全条件は回避しない。既存資産の移行は別作業であり無断実施しない。 Q12に従い必要な改善と受入が完了して目的を満たすことを終了基準とし、不要・責務外・対応済みの理由を既存Planへ記録する。必要な未対応・未検証を不要扱いしない。新しい管理台帳を作らない。

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

### 再レビューの処置（履歴、追加ゲートではない）

対象commit 064f3c38ac0b8e21b1bd5cce1ba8b09b22b62af1 のRV2-01〜16を次の既存OPS・共通原則に統合した。指摘IDは履歴追跡用であり、新しい改善項目や独立した受入を追加しない。

<!-- dprint-ignore -->
| 指摘 | 対応OPS | 処置 |
| --- | --- | --- |
| RV2-01 | 03/06/14/18 | 通常保存と実共有・外部操作の必要保証を区別 |
| RV2-02 | 01/02/03/04/13 | 承認済み意味を保全、候補保存と正式採用を分離 |
| RV2-03 | 03/05/13/18 | Runtime・validator・schema・metadataの必要性評価 |
| RV2-04 | 01/06/18 | QA状態は既存成果物優先、汎用state移管を回避 |
| RV2-05 | 全18件 | PR #40後の共通確認と関連OPSの個別確認を分離 |
| RV2-06 | 01/02/18 | 現行baselineと新設計の正本を明確化 |
| RV2-07 | 14/18 | 直接利用・明示作業先・必要時だけ確認 |
| RV2-08 | 01/18 | Q02の5契機を基本、旧CPを実装要件にしない |
| RV2-09 | 13/18 | 人間向け正本、必要履歴・機械形式だけ維持 |
| RV2-10 | 01/12/18 | 単発レビュー・調査の保存強制なし |
| RV2-11 | 05/07/18 | 用途・影響・再利用に応じた検証強度 |
| RV2-12 | 09/17 | 通常編集と特殊owner制約の分離 |
| RV2-13 | 18 | 共通原則への参照、重複責務表の削除 |
| RV2-14 | 09/14 | 旧配置契約Q06をPlan名付きで識別 |
| RV2-15 | 全18件 | 実装目的別5領域へ整理 |
| RV2-16 | 全18件 | OPS本文を入口とし、PRE/ATは必要時のみ参照、レビュー表は履歴 |

### 第3回レビューの処置（履歴、追加ゲートではない）

対象commit e226c77c6225b18cfc7d4147490d5c2fe029b938 のRV3-01〜07と利用者が承認したQ09〜12を既存OPS・共通原則・関連文書へ統合した。改善実装・受入完了を意味しない。

<!-- dprint-ignore -->
| 指摘 | 対応OPS/文書 | 処置 |
| --- | --- | --- |
| RV3-01 | 01/12、Q09 | 成果物作成の既定保存と単発回答を区別 |
| RV3-02 | 02/04、Q10 | 通常の明示内容承認と必要な追加権限確認を分離 |
| RV3-03 | 10/14/18、共通原則 | 指定repo/branch/commitの情報源利用と管理を区別 |
| RV3-04 | 05/18 | 意味上の必要保証と現行Runtime実現手段を分離 |
| RV3-05 | README、18 | 現行責務一覧・契約と新規/改修原則を区別 |
| RV3-06 | 02/18、Q11 | continuous既定、明示gatedのみ |
| RV3-07 | マトリクス、12 | 旧G1/G4等を現行baselineの説明に限定 |

### 実装目的別の整理（既存OPSを維持）

PR #40完了後に最新baselineで残存課題を選別し、OPS-18を横断原則として先に適用する。次の5領域は計画の分類であり、新しい管理単位・独立実装・強制順序を作るものではない。

<!-- dprint-ignore -->
| 領域 | 対象OPS | 目的 |
| --- | --- | --- |
| A 責務削減・適正化 | 18 | Skill・Runtime・validator・Helperの不要責務を削減 |
| B 成果物管理 | 09/12/13/14/15/16/17 | 必要な相対配置・形式・命名・発見・人間編集・保護・互換性 |
| C 質問・保存・継続 | 01/02/03/04/06 | 自動保存、必要な内容承認・再開、実リスク相応の安全 |
| D QA品質・完了検証 | 05/07/08 | 意味品質、必要な検証・完了、既存文書との整合 |
| E 外部接続・効率評価 | 10/11 | 必要な接続・改善効果の評価 |

各領域で必要な依存条件だけを確認する。旧Phase全体の完了を後続の一律前提としない。OPS-16の必要な保護と現行の安全制約は全領域で維持し、未改修のblocked条件を回避しない。新Skill・中央DB・中央mutable manifest・全成果物統一schema・全Skill専用key・汎用storage framework・一律配置移行は前提としない。

### 横断受入シナリオ候補

既存Deterministic Test・Semantic Evaluation・実Agent評価を必要範囲で再利用する。以下は各OPSの受入を組み合わせるシナリオ候補であり、独立した追加受入ゲートではない。該当変更・実リスクに応じて既存試験でカバー済みのものは重複実施せず、必要な入力・根拠・結果・未達だけ記録する。

<!-- dprint-ignore -->
| ID | シナリオ | 期待する受入結果 | 関連OPS |
| --- | --- | --- | --- |
| AT-01 | 初回の実行環境 | 外部指定rootから相対配置を解決、Skillによる案件探索・配置再質問なし | 09/12/14/18 |
| AT-02 | 既存成果物利用 | 許可済みroot・ID・有効権限を維持、不要再質問なし | 09/14/17/18 |
| AT-03 | 初回テスト設計 | 必要scopeの分析〜TC、正本・参照・必要保存検証 | 03/05/12/13 |
| AT-04 | 仕様ブロッカー | 許可中間保存または未保存明示、該当scopeだけ停止 | 01/02/16 |
| AT-05 | 部分回答 | 根拠currentな回答scopeのみ再開、旧回答/保留を誤承認しない | 01/02/13 |
| AT-06 | 別Agent再開 | 保存済み成果物・必要時のみstateから再開先取得、未保存候補は復元保証なし | 01/15/18 |
| AT-07 | 変更なし再依頼 | 母集団・依存・currentness確認、有効合意再利用、不要再生成なし | 02/05/15 |
| AT-08 | 一部仕様改版 | 外部資料含む入力完全性、影響scopeのみ再検証 | 05/15 |
| AT-09 | 人間編集 | 通常編集は簡素、正式変更/生成領域のみ必要owner制約、無断上書きなし | 09/17 |
| AT-10 | 並行Workflow・共有資源 | 実際に共有する場合だけ必要な競合/予約保証を確認、未確認操作をblock、混線なし | 06/16 |
| AT-11 | 保存後の結果不明 | 必要な実保存/操作結果を照合、盲目的再試行なし | 03/04/06 |
| AT-12 | 依存する複数成果物の部分保存 | 必要な参照整合確認まで依存する下流current不可 | 03/12/15 |
| AT-13 | 正本重複 | 無断選択・新規作成なし、未解決明示 | 14/15 |
| AT-14 | アクセス不能 | 不存在と区別し正式保存block | 03/14/15 |
| AT-15 | 承認対象の変更・失効 | 承認の対象・意味・有効性に影響する変更では旧承認の誤再利用を拒否 | 02/04 |
| AT-16 | 機密証跡 | 未許可領域書込み/公開なし、任意・必須保存区別 | 16 |
| AT-17 | 必須scope宣言漏れ | 元依頼との照合で不足検出、誤完了なし | 05/07 |
| AT-18 | FAILを含む実行 | 合否・母集団・cleanup・終了基準・workflow完了を独立判定 | 07 |
| AT-19 | 異なるAgentで同一依頼 | 同一正本・配置・命名、別scope/Run衝突なし | 12/13/14/15 |
| AT-20 | 単発読取・レビュー・調査 | 保存依頼/継続利用目的がなければ対話回答、不要な保存・配置承認なし | 01/02/12 |
| AT-21 | 責務境界・移植性 | 異なる外部実行条件で案件/成果物branch/Provider管理なく（指定repo等の情報源分析は可）同一意味成果物、許可外拒否 | 18 |
| AT-22 | 責務削減と回帰 | 専門外判断・読込・不要質問・重複管理削減、既存QA品質・安全・履歴維持 | 11/18 |
| AT-23 | 成果物作成・通常保存・内容承認 | 明示の非保存指示がなければ許可範囲で自動保存、依頼者の明示内容承認を採用、必要時のみ追加権限確認、既存承認済み意味を保全 | 01/02/03/04/18 |
| AT-24 | 直接Skill利用 | 特定ハーネスなし、明示済み作業先利用、必要時のみ保存先確認 | 12/14/18 |
| AT-25 | 最小構成 | 実リスク相応の防御・検証・形式・履歴、不要なCAS/専用基盤/複製/承認なし | 03/05/06/11/13/18 |

上記は未実施の受入候補。具体的な相対path・必要最小の外部契約・実環境・過去対象外の再検証範囲はPR #40後のPlanで確定する。共通原則の再承認は不要。過去のPR #22の未達・対象外・検証結果を上書きしない。 Q11の既定continuous/明示gatedとQ12の必要性・終了判定は関連OPSの既存受入に統合する。
