# QA全工程の責務・成果物契約とPR #22の整合調査

調査日：2026-11-07  
対象：`ryu-yoshikawa-pro-vision/qa-workflow-skills`  
調査基準：`main` `329cd8ad75ecde9d21c2e60f791214ca27fa2602`、PR #22の調査開始時HEAD `2d275923c339cf6efcfa06923d624fc8964ee744`  
作業種別：調査・設計・提案。**Skill、runtime、CI、製品コードの実装は行っていない。既存PR #22のPlanも変更していない。**

## 1. 結論と位置付け

本リポジトリの到達目標は、**QAの全工程に対する再利用可能なAgent Skills、成果物、検証手段を提供すること**とする。全工程を常時実行すること、全製品種別でテストを自動実行できること、全工程の意思決定をAgentへ移譲することは意味しない。

現行`main`の23 Skillは、仕様・テスト分析、TR/TCN/CI/TC、PlaywrightによるWeb実装・実行、Regression、Exploration、UI/UX・WCAG、QA Knowledge、workflow routing等を支援する。一方、QA要求の合意、テスト計画・アーキテクチャ、全体モニタリング、非Webの実装・実行、欠陥の継続管理、テスト全体報告、QA活動そのものの評価は、現行Skillの単一の正本・完了条件に閉じていない。

PR #22は**開発情報源→製品機能→仕様・UI→テストアイテム／共通条件候補→Risk→TR→正式TCN/CI→TC**の追跡と変更追従を補うPlanである。上記の全工程における未対応を、PR #22の6つの予定Skillで解消したと見なさない。

**この文書は、リポジトリ全体の方向性・設計判断・未解決課題の報告書である。PR #22の実装Planおよび完了条件の変更、別工程の実装着手、案件固有の承認を意味しない。**

## 2. 確定した利用者の方針（Q01〜Q08）

| 質問 | 確定事項 | 設計上の帰結 |
|---|---|---|
| Q01 | QAの全工程を支援対象とする。自動実行は必要性と実行可能性で判断 | 工程の対応表は全工程を対象にし、実装済みと未対応を表示 |
| Q02 | 計画・戦略・進捗管理・終了評価を正式な責務に含める | `qa-workflow`のroutingだけをテストマネジメントと呼ばない |
| Q03 | 分析・管理は製品種別非依存。実装・実行の制約は明示 | 現行Playwright実装を非Webにも対応済みと表現しない |
| Q04 | 性能・セキュリティ・信頼性等の非機能テストも分析・設計・実行・評価の支援対象 | 品質特性ごとに対応可能な活動・実行手段を明示 |
| Q05 | UI・API・バッチ・コンポーネント等は技術別既存手段と連携 | 実装／実行への接続方法を案件のrunner・環境と分離して設計 |
| Q06 | 欠陥候補の報告、追跡、修正確認まで支援。製品改修は対象外 | FAILを自動で正式欠陥にせず、外部欠陥管理の正本・権限を尊重 |
| Q07 | QA担当者・設計者、QAリーダー／テストマネージャー、自律的QA Agentが主な利用者 | 人間のレビュー・承認とAgentの生成・検証・提案を分ける |
| Q08 | 追跡性、品質、効率、プロセスの再現性・監査性、他案件への再利用性の5軸で評価 | 単一の総合点ではなく、独立した指標と検証証拠を用意 |

未確定のまま維持する事項：案件ごとの承認者・品質基準・対象runner・保存先・権限・予算、組織レベルの人事／教育まで対象とするか。PR #22のQ06・Q20・Q24の未回答／任意扱いを、この報告で回答済みにしない。

## 3. 根拠・確認方法と制限

- `main`の再帰treeで**23個の`skills/*/SKILL.md`**を確認し、各Skillの責務と主要出力テンプレート、`skills/qa-workflow/references/guidance.md`、`EVALS.md`、`PLANS.md`を照合した。
- PR #22の`docs/plans/2026-11-07_122247_development-qa-traceability.md`の責務表、成果物正本、工程、開発イベント、保存・CI・セキュリティ、完了条件を照合した。調査開始時は**Plan 1ファイルだけを変更した未マージPR**。
- 前回までの会話で確認した、IVEC Assistant/Tester/Designer/Architect/Evangelist、JSTQB/ISTQB CTFL/TA/TTA/TAE/TM/Expert TMの計11シラバス、テストプロセス横断分析、目的・工程対応の調査、ステップ2の工程別成果物整理を統合した。IVECの7工程とISTQBの活動は名称・粒度が一致しない。
- このレポートでは、**確認済み実装**、**PR #22で計画中**、**新たな設計提案**を分ける。現行の全runtime・テストを実行したわけではなく、実製品での網羅性・品質の実証を含まない。

主要参照先：

- [README](../../README.md)（現行目的とSkill一覧。末尾の「全プロセス再現は目的ではない」はQ01・Q02の新方針と整合見直しが必要）
- [`qa-workflow` guidance](../../skills/qa-workflow/references/guidance.md)
- [Project Context template](../../skills/qa-workflow/assets/project-context-template.md)
- [`test-analysis` guidance](../../skills/test-analysis/references/guidance.md)
- [`regression-testing`](../../skills/regression-testing/SKILL.md)
- [`test-execution`](../../skills/test-execution/SKILL.md)
- [`qa-knowledge`](../../skills/qa-knowledge/SKILL.md)
- [Skill評価方針](../../EVALS.md)
- [PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)、[PR #22の既存Plan](../plans/2026-11-07_122247_development-qa-traceability.md)

## 4. テスト工程・管理活動と現行Skillの対応

以下の「部分対応」は、現行の正式な成果物責務が工程全体を覆っていないという意味であり、既存機能が使えないという意味ではない。

| 工程・活動 | 現行Skill・既存の出力 | 確認できる不足 | 現段階の設計方針 |
|---|---|---|---|
| IVEC 1. テスト要求分析 | `spec-analysis`、`question-analysis`、`test-analysis`。仕様根拠、UNKNOWN、Risk、重点 | QA活動への要求、品質目標・要求元・制約・対象外の合意の正本 | 製品仕様Authorityと個別のTRを複製せず、テスト要求分析として独立管理 |
| IVEC 2. テストアーキテクチャ設計 | `test-analysis`、`regression-testing`、E2E系。レベル、重点、既存Run | レベル／タイプの組立て、環境・データ・方式と全体終了基準 | テスト全体のアーキテクチャと計画の正本・参照関係を定義 |
| IVEC 3. テスト詳細設計 | `test-requirement-design`、`test-condition-design`、`coverage-analysis`、`adversarial-review` | 機能／アイテム／共通条件候補の上流識別 | PR #22の`feature-analysis`、`test-item-analysis`、`test-condition-analysis`を接続 |
| IVEC 4. テスト実装 | `test-case-design`、`e2e-test-inspection`、`e2e-test-implementation`。TC、Playwright E2E | 非Playwrightの実装経路、環境・データ連携 | 共通TCの正本を維持し、技術別の実装方式を連携 |
| IVEC 5. テスト実行 | `test-execution`、`e2e-test-execution`、`exploratory-testing`、`regression-testing`。実測、run、Finding | 非Web実行・欠陥の正式追跡・修正確認の統合 | runのsource resultを正本として維持し、欠陥管理の引継ぎを追加 |
| IVEC 6. テスト報告 | `test-execution`の個別報告、`e2e-test-reporting`のPlaywright報告 | テスト全レベル・タイプと欠陥・進捗・終了基準の統合 | 元の実行結果の参照のみを使う横断報告 |
| IVEC 7. テスト評価 | `qa-knowledge`の知識管理、`qa-workflow`の活動状態 | QA活動の有効性・効率・改善実績、完了・引継ぎの正本 | Agent Skills自体を評価する`EVALS.md`とは分離 |
| ISTQB 横断：テスト計画 | Project Contextの一部、`test-analysis`の重点 | 予算・要員・日程・計画承認・改版 | テストマネジメントの独立した判断責務 |
| ISTQB 横断：モニタリングとコントロール | `qa-workflow`のルーティング、`regression-testing`のActivity | 計画対実績、プロジェクトリスク、是正処置の管理 | テスト計画と連動する管理責務 |
| 横断：レビュー・静的テスト | `adversarial-review`のQA成果物／E2E実装の反証レビュー | 製品の要件・設計・コード等の静的テスト実行範囲は要調査 | 仕様正本と独立レビューを混同せず、既存reviewを優先 |
| 横断：非機能品質特性 | `usability-evaluation`、`usability-inspection`、`wcag-conformance-evaluation` | 性能・セキュリティ・信頼性等の技術固有実装・実行 | 品質特性別の分析／設計／実行／評価の対応表を維持 |

## 5. 共通の成果物契約（新設・拡張する責務に適用する設計案）

既存のMarkdown、Machine Entity、`runtime-v2`、`entity-state-v2`、revision/CAS、Scope ownershipに合わせて実装時に検討する**論理項目**である。全Skillの現行schemaを一括置換する指示ではない。

| 項目 | 必要な意味・検証 |
|---|---|
| 識別・版 | 成果物種別、安定参照、対象範囲、成果物revision、schema versionがある場合はその版。採番規則は既存ownerと衝突しないよう実装時確定 |
| 正本・参照 | 作成・更新ownerを一意にし、元の仕様・Risk・TR/TCN/CI/TC・run・外部Issueは参照する。再保存して第二の正本を作らない |
| 情報源 | source ref・source revision・取得範囲・確認時点・取得不能範囲。実測、仕様、推論、案件の決定を区別 |
| 状態 | 作業中、確認中、確定済み、保留などの意味はownerの契約と案件の承認規則で定義。全成果物へ未確認の共通列挙値を強制しない |
| 承認 | 必要な対象scope、内容revision、決定主体、承認証拠、失効条件。文書に「承認済み」と書かれただけで外部承認を証明しない |
| 依存・変更 | 依存元参照、現在性比較に必要なsource revision、影響範囲、再検証先、履歴。無関係な成果物を一律staleにしない |
| 保存・競合 | 保存先のnative atomic create-if-absent / conditional writeを確認する。read-compare-unconditional-writeをCASと呼ばない。必要能力がなければ該当操作をblock |
| 検証 | 意味判断のレビュー、schema・ID・参照・版の機械検証、欠落・部分完了・未実施の区別。fixtureのPASSだけで実案件の受入完了としない |
| 保護 | 機密・個人情報・認証情報を本文や公開artifactに無断複製しない。必要最小限の証拠refと保持条件を使用 |

**識別子設計**：新しい横断成果物に対して独自の固定prefixや共有の連番カウンターをここで採用しない。実装Planでownerとstorage provider、競合条件、外部Issueとの対応を確認してから決める。`DEC/ASM`、`TR/TCN/CI/TC`、PR #22の機能・アイテム・条件IDの既存／予定契約を変更しない。

**状態・履歴**：草案作成、レビュー、承認、部分完了、失効、再検証、保管は業務上の概念として整理する。元のruntimeや外部Issueの状態を勝手に再定義せず、必要な変換は参照付きで行う。承認は対象revisionが変わった際の失効判断を必須とする。

## 6. 未対応工程の成果物契約

### 6.1 テスト要求分析（IVEC工程1）

| 区分 | 契約案 |
|---|---|
| 入力 | 業務目的・品質要求・関係者・テストベース、対象システム／リリース、開発情報源、制約、既存仕様分析、既知リスク |
| owner | QA活動に対する要求の整理・合意を担う**独立責務**。`spec-analysis`は製品期待仕様、`test-requirement-design`は個別検証責務TRのまま |
| 保存情報 | テスト目的、要求元／関係者、品質目標、対象・対象外と理由、重要度、制約、情報源、未解決事項、意思決定・承認の参照 |
| 出力・接続 | テストアーキテクチャ・計画へ渡す要求と対応付け。仕様競合は`question-analysis`、仕様Authorityは`spec-analysis`へ戻す |
| 完了条件 | 要求と根拠・対象範囲・対象外・確認者が追跡でき、必須な未回答は影響範囲と次の担当が分かる。未承認の提案を合意済みにしない |

**判断**：新しい独立Skillの候補とする。`spec-analysis`や`test-analysis`へ追加すると、製品仕様の確定・Product RiskとQA活動への要求の合意が混在する。Skillの名称・実装単位は実装Planで確定する。

### 6.2 テストアーキテクチャ設計（IVEC工程2）

| 区分 | 契約案 |
|---|---|
| 入力 | 確認済みのテスト要求分析、機能／アイテム構造、Product Risk、品質特性、テストレベル、技術構成、環境・データ・既存資産 |
| owner | テストレベル・タイプ・方式の**全体設計責務**。局所的なRisk・重点は`test-analysis`、具体的なCIは`test-condition-design`が正本 |
| 保存情報 | レベル／タイプ別の検証分担、対象アイテムとリスク、テストモデル・設計技法の方針、環境・テストデータ・実行方式、依存関係、制約、代替／未対応方式、設計判断とrevision |
| 出力・接続 | テスト計画へ提供する構成・見積り前提、TR/TCN/CI・E2E/Regressionへの設計方針。正式TCNとTCを自身で生成しない |
| 完了条件 | 要求・リスクと各テストレベル／タイプの割当が説明でき、抜け・重複・技術的制約を確認できる。実施不能を解決済みと扱わない |

**判断**：独立Skill候補。`qa-workflow`のrouting、`test-analysis`のRisk、`e2e-test-inspection`のPlaywright構成調査を再実装しない。テスト計画との重複項目は**アーキテクチャが方式の正本、計画が資源・日程・実行承認の正本**として参照で接続する。

### 6.3 テスト計画・モニタリング／コントロール（工程横断）

| 区分 | 契約案 |
|---|---|
| 入力 | テスト要求分析・アーキテクチャ、Project Contextの案件設定、対象リリース／baseline、資源、期日、費用、環境・依存先、実行・欠陥・報告の現在状態 |
| owner | テスト計画・予実・是正・プロジェクトリスクの管理責務。**`qa-workflow`はSkillの起動・再開・完了状態のみ**を保持 |
| 保存情報 | テスト計画のscope、レベル／タイプ、担当・役割、見積り、日程、環境・データ、開始／終了基準、計画前提、承認・版。モニタリング時点別の計画対実績、進捗、阻害事項、プロジェクトリスク、是正処置・責任者・期限 |
| 出力・接続 | QA担当の実行依頼、テスト報告の計画比較基準、変更時の再計画。Product RiskとRegression Activityは既存ownerを参照する |
| 完了条件 | 必要な計画項目、承認状態、測定基準が明示され、各監視時点の分母・集計元・実績が追跡できる。差異と是正の未完了を隠さない |

**判断**：テストマネジメントの独立Skill候補。計画と監視は同じ管理ライフサイクルなので、用途別に直ちに2 Skillへ分割しない。Project Contextには案件固有設定と計画正本への参照を持たせ、計画全体を複製しない。**プロジェクトリスク**と`test-analysis`の**Product Risk**を混ぜない。

### 6.4 不具合管理と修正確認（工程横断）

| 区分 | 契約案 |
|---|---|
| 入力 | `test-execution`、`e2e-test-execution`、`e2e-test-result-analysis`、`exploratory-testing`、Regressionの実行結果／Observation／Finding、仕様根拠、対象build・環境 |
| owner | QA側の欠陥候補の整理、正式な欠陥管理への引継ぎ、追跡、修正通知に対する確認依頼と結果の接続。正式Issue・欠陥の状態の正本は**案件の既存管理システム** |
| 保存情報 | 発見元・観測・再現手順と条件・実際結果・期待結果のAuthority・証跡・影響範囲・既知問題照合、登録有無と外部Issue参照、外部状態取得時点・revision、QAの修正確認対象・依頼・結果ref、未解決事項 |
| 出力・接続 | 根拠付き欠陥候補／引継ぎ、外部Issueと元runのリンク、必要な修正確認用TC/runへのrouting。コード修正・仕様変更・欠陥の受容をQA Agentが代行しない |
| 完了条件 | 候補ごとの扱い・未登録理由、正式登録先／引継ぎ先、追跡可否、修正確認の結果または未実施理由が分かる。FAILだけでDefect登録済みとしない |

**状態設計**：`Finding`、`FAIL`、`Observation`、外部Issueの`open/closed`等は異なる概念。管理システムの正式状態はそのまま保持し、QA側の未登録・追跡中・再検証待ち等の判断を参照として持つ。複数Issue管理システムの状態名を共通の単一enumに無理に統一しない。

**判断**：独立した欠陥管理責務／Skill候補。`regression-testing`のRun選定・Activity、`qa-knowledge`の知識、`e2e-test-result-analysis`の原因判断を重複作成しない。外部への新規Issue登録・状態変更は**案件の明示権限を得た場合に限る**。

### 6.5 複数テスト方式の統合報告（IVEC工程6、ISTQBの進捗報告）

| 区分 | 契約案 |
|---|---|
| 入力 | 計画と終了基準、一般TC、E2E、Regression、Exploration、使用性／WCAG、非Web／非機能run、欠陥・Risk・coverageと各正本revision |
| owner | 対象範囲・期間・SUT版を固定して、元の実行・監視情報を**読取専用で集約する報告責務** |
| 保存情報 | 報告対象scope／baseline／build・環境、各テスト方式の結果と単位・分母、計画対実績、未実行・判定不能、欠陥・未検証・ブロッカー、終了基準の充足と未達、残存Risk参照、作成時点と元データrevision |
| 出力・接続 | QAリーダー向け進捗・完了報告、判断材料。元runのPASS/FAIL、Product Risk評価、正式欠陥状態、リリース判断を更新しない |
| 完了条件 | 全数値がsource run／TC／test item／欠陥へ遡れる。`logical primary`、`resolved TestCase`、`attempt`など単位差を保存し、retryをTC件数へ重複計上しない |

**判断**：独立Skill候補。既存`e2e-test-reporting`と`test-execution`の報告を置き換えず、それらを参照する。未取得のrunや未実施技術を0件PASSとして加算しない。正式な終了判定は終了基準と権限に従い、報告書の存在だけでリリース可としない。

### 6.6 テスト評価・完了／改善（IVEC工程7）

| 区分 | 契約案 |
|---|---|
| 入力 | テスト要求と目標、計画・監視・統合報告、工数・期間・費用、欠陥／リスク、前回改善とフォロー結果、保管・引継ぎ要件 |
| owner | QA活動・プロセスの有効性、効率性、計画達成、改善内容、完了・保管・引継ぎを評価する責務 |
| 保存情報 | 評価対象・期間、計画と実績の比較、評価指標・計算条件・根拠、達成／未達／未測定、要因分析と制約、改善項目・責任者・期限・検証方法、引継ぎと保管状況、確認／承認記録 |
| 出力・接続 | QA活動評価報告、改善計画、未完了引継ぎ一覧。汎用的な再利用知識だけを`qa-knowledge`へrouting |
| 完了条件 | 評価結果の測定元と制限が追跡でき、改善責任・期限・効果確認方法が指定済み。改善効果が未測定なら「未測定」と記録する |

**判断**：独立Skill候補。`EVALS.md`はAgent Skills自身の発火・出力品質・統合評価、`qa-knowledge`は継続利用知識、`qa-workflow`はroutingであり、案件のQA活動評価の正本ではない。

### 6.7 API・バッチ・コンポーネント・非機能の実装／実行（IVEC工程4・5）

新しい実行経路は必要だが、**技術名の数だけSkillを先に増やさない**。対象案件の既存runner、CLI、フレームワーク、CI、計測工具を確認し、共通の入力・結果参照と、技術固有のpreflight／cleanupを分離する。

| 項目 | 契約案 |
|---|---|
| 入口 | 既存TC／対象アイテム、実行目的、test level/type、現在有効な期待結果、対象buildと実行許可 |
| 実装・実行方式 | 実際に確認した対象repo、runner、config、試験対象操作の許可、環境・ロール、データ、外部依存、副作用上限、cleanup |
| 結果 | runner固有のraw outcomeと集計単位、TC等との対応、実開始／未開始、再試行、環境／build、証跡ref、判定不能理由、後処理と残存状態 |
| 連携 | `qa-workflow`が適切な既存実行ownerへroutingし、結果はそのownerを正本として`coverage-analysis`／統合報告が参照 |
| 受入 | 正常系・異常系・権限不足・runner失敗・途中停止・cleanup失敗で、無根拠なPASSや安全完了を出さない |

現行`test-execution`はbrowser実行手段をPlaywrightに固定し、`e2e-test-implementation`と`e2e-test-execution`もPlaywright固有。既存実装を無断で「全テスト共通runner」に変更しない。品質特性については、性能、セキュリティ、信頼性、互換性等の**分析／設計／実装／実行／評価**それぞれの実対応を記録し、測定閾値がない場合はPASSを捏造しない。

## 7. 既存Skillの拡張・新規独立責務の判断

| 対象 | 推奨判断 | 理由・重複回避 |
|---|---|---|
| 製品仕様・UNKNOWN | `spec-analysis`／`question-analysis`を維持 | 仕様Authority・不明点の既存正本 |
| Product Risk・テスト重点 | `test-analysis`を維持 | プロジェクトリスクと分離 |
| TR／正式TCN・CI／TC | 各既存Skillを維持し、PR #22計画の候補参照を追加 | 正式設計と上流候補を重複作成しない |
| QA要求分析 | **新規独立責務を推奨** | テストサービス目的・要求元・合意は製品仕様／TRと別 |
| テストアーキテクチャ | **新規独立責務を推奨** | テスト構成・方式・環境の全体設計は局所RiskやCIと別 |
| テスト計画・監視・是正 | **独立した管理責務を推奨**。計画と監視を直ちに分割しない | `qa-workflow`の技術routingと混同しない |
| 欠陥管理 | **新規独立責務を推奨** | 外部Issueを正本とした追跡・修正確認は実行・Regressionと別 |
| 統合報告 | **新規独立責務を推奨** | 元のrunとPlaywright専門報告を再判定しない |
| テスト評価 | **新規独立責務を推奨** | `EVALS.md`や`qa-knowledge`とは目的・正本が異なる |
| 技術別テスト実装／実行 | **既存runner連携を先に設計し、足りない技術固有のSkill／adapterを追加** | Playwright固有の安全・retry・cleanup契約を無理に汎用化しない |
| 静的レビュー・非機能の専門領域 | 既存`adversarial-review`、使用性・WCAGを調査後、足りない責務だけ拡張／追加 | 同じ基準や実行事実の第二の正本を作らない |
| Skill選択、保存・評価 | `qa-workflow`、既存runtime／`EVALS.md`を再利用・必要なrouting／fixtureだけ拡張 | 新しい中央オーケストレーター・独自評価基盤を追加しない |

ここで推奨するのは**責務の分離**である。Skill名、ファイル数、schema、実装順、案件適用の詳細は、既存helper・consumer・テスト・CIと照合した実装Planで確定する。新Skillの増加自体を目的にしない。

## 8. PR #22に関する過去レビューの未解決事項

### 優先度高：Plan・実装前に検証する項目

1. **ローカルAgent成果物→製品CIの受渡し（Plan 280〜302、329〜356行）**：CI runnerがローカル`qa.feature_artifact_root`を直接読めるとは限らない。保存先、権限、artifact provenance、source revision／PR head一致、hash照合、再取得失敗時の判定を設計する。
2. **Project Contextのnative atomic CAS provider（Plan 74〜90、322〜327行）**：`artifact_graph.py`の局所的なrevision比較は保存先のCASそのものではない。実際のstorage操作、expected revision、競合処置、履歴取得、単体配布時の依存を検証する。
3. **並行PRでの安定IDと複数成果物の整合（Plan 161〜168、193〜201、247〜278行）**：同じbaseからの並行採番、分割・統合、itemとconditionの相互参照、遅延更新、部分再実行と復旧の整合を定義する。
4. **「影響なし」「対象外」と承認の信頼境界（Plan 152〜159、280〜312行）**：署名や認可できる主体、根拠、scope、commit/revisionに紐付けた承認を検証する。CIが文字列の存在だけで内容の正しさを承認しない。
5. **実行起動・運用契約（Plan 280〜303行）**：PR作成・更新、merge、releaseの各時点で、誰がAgentを起動し、成果物を保存・公開し、CIがいつ参照するかを明示。外部仕様資料の未観測変更は未確認として残す。

### 優先度中：完了基準と導入時の精度確認

6. **機能抽出の分母（Plan 205〜245行）**：発見済み候補への対応率と、独立母集団を使った発見の十分性を分ける。「未知の全機能まで100%」と主張しない。
7. **受入製品・独立基準データ（Plan 170〜172、384〜404、421〜439行）**：候補`qa-training-store`のrevision、実対象の対応範囲を検証し、不足する種類はfixtureで別評価。誤検出・見逃し・重複・変更追従の基準を定める。
8. **Skill単体配布の依存関係（README、Plan 74〜90行）**：`project-context`が既存`qa-workflow/scripts/artifact_graph.py`等へ依存する場合、単体配布の説明と実際の起動条件を一致させる。
9. **既存Skillとの工程対応**：UI package／Authorityの移管、共通条件候補／正式TCNの分離、Risk一次評価と局所再評価、E2E対象選定の分離を、既存consumer・runtime・historyと合わせて検証する。
10. **実Agent受入**：形式やfixtureのPASSは意味的な抽出精度・実Agent統合の保証ではない。実Agentの発火・routing・成果物・復旧を独立して評価する。

**変更しない既存合意**：`project-context`と`qa-workflow`の境界、`feature-analysis`と`spec-analysis`の境界、UI構造とAuthorityの区別、テストアイテムと共通条件候補の並行識別、正式TCNは`test-condition-design`、Product Riskは`test-analysis`、CIで新しい意味判断を行わない、PR #22はPlan-onlyであること。今回のレポート追加はユーザーの明示依頼による記録であり、Skill実装着手ではない。

## 9. 完了条件・品質評価の設計案

### 9.1 新たな責務の受入で要求すること

- **正本とトレーサビリティ**：入力参照・owner・revisionと下流参照が一致し、重複正本がないこと。
- **意味品質**：独立した仕様・正解・レビュー根拠との照合。Agentの説明や自身が生成した成果物だけを正解にしないこと。
- **安全**：認可・最小権限、untrusted source、secret/個人情報、データ破壊、副作用、cleanupを適切に扱うこと。
- **変更追従**：変更なし、仕様変更、PR並行更新、source取得失敗、保存競合、再開、履歴・schema移行を検証すること。
- **既存互換**：現在の`qa-workflow`、`TR/TCN/CI/TC`、Machine Entity、Regression、E2E、QA Knowledgeの正本・呼び出し元・CIを壊さないこと。
- **正しい結果表現**：workflow完了／対象製品のPASS／リスク受容／リリース承認を別に扱い、未実行・判定不能・未測定をPASSに含めないこと。

### 9.2 Q08の評価軸と指標候補

| 評価軸 | 指標・根拠の候補 | 取り扱い上の注意 |
|---|---|---|
| 追跡性・網羅性 | 対象とした独立母集団に対する機能分類・仕様・TR/TCN/CI/TCの対応、未分類・未確認数 | 分母、版、対象外理由を固定。発見済み候補の対応率と全機能発見を混同しない |
| 設計・実行品質 | 独立レビューで検出した誤り、期待結果の根拠欠落、実行誤判定、再現可能な欠陥検出 | 不具合件数の多寡だけでテスト品質を決めない |
| 効率 | 同一範囲の人手時間、Agent処理・レビュー時間、差戻し・再作業、変更後の再検証時間 | 環境・対象条件・品質を揃えて比較し、未測定なら明示 |
| プロセス | 必要成果物の現在性、承認・変更履歴、blocked・再開、完了条件の再現性、監査証拠 | CI PASSだけで全工程完了とはしない |
| 再利用・導入 | 案件間で変更せず利用できたSkill、共通helper依存、導入作業、実Agent／OS／CLIの受入結果 | Web/Playwright限定の範囲を他製品へ拡大表記しない |

既存`EVALS.md`の仕様適合・発火・決定論的出力・意味評価・workflow統合評価を活用し、**案件QA活動の効果測定**は別の成果物として設計する。評価条件、case分割、実Agent実行、判断不能の扱いを記録する。

## 10. 進め方と実装境界

1. **目的・対応表を正本化**：READMEの目的・工程対応・技術制約を更新する計画を別途作る。現行23 Skill／PR #22の計画6 Skill／新規候補を混同しない。
2. **新たな成果物契約を審査**：本レポート第5〜7節を基に、既存owner・保存先・承認者・schema・呼び出し元と照合し、Skill拡張か新設かを実装Planへ落とす。
3. **PR #22の実装前提を確定**：第8節の優先度高5点を先に解き、既存の実装Planで定めた機能全体、例外、検証、移行を省略しない。
4. **設計・実装・統合受入**：独立した成果物のownerを確定し、Skill／runtime／CI／評価データ／Project Contextとの接続、実Agent経路を検証する。
5. **QA全工程の連結を確認**：要求→計画・アーキテクチャ→設計→実装・実行→欠陥追跡・報告→評価・改善まで、条件付き実行・部分実行・直接開始・復旧を対象にする。

**今回実施したこと**：既存資料・PRの読み取り、過去のレビュー結果と確定方針の統合、工程別の責務・成果物契約とSkill新設／拡張の判断案の作成。  
**未実施**：Skill/runtimes/CIの変更、実行テスト、実Agent受入、案件ごとの承認・保存先の決定、製品改修、PR #22のPlan更新・完了宣言。
