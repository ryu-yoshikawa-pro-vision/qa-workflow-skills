# QA全工程の責務・成果物契約とPR #22の整合調査

調査日：2026-11-07\
対象：`ryu-yoshikawa-pro-vision/qa-workflow-skills`\
調査基準：`main` `329cd8ad75ecde9d21c2e60f791214ca27fa2602`、PR #22の調査開始時HEAD `2d275923c339cf6efcfa06923d624fc8964ee744`\
作業種別：調査・設計・提案。**Skill、runtime、CI、製品コードの実装は行っていない。既存PR #22のPlanも変更していない。**

## 1. 結論と位置付け

本リポジトリの到達目標は、**QAの全工程に対する再利用可能なAgent Skills、成果物、検証手段を提供すること**とする。全工程を常時実行すること、全製品種別でテストを自動実行できること、全工程の意思決定をAgentへ移譲することは意味しない。

現行`main`の23 Skillは、仕様・テスト分析、TR/TCN/CI/TC、PlaywrightによるWeb実装・実行、Regression、Exploration、UI/UX・WCAG、QA Knowledge、workflow routing等を支援する。一方、QA要求の合意、テスト計画・アーキテクチャ、全体モニタリング、非Webの実装・実行、欠陥の継続管理、テスト全体報告、QA活動そのものの評価は、現行Skillの単一の正本・完了条件に閉じていない。

PR #22は**開発情報源→製品機能→仕様・UI→テストアイテム／共通条件候補→Risk→TR→正式TCN/CI→TC**の追跡と変更追従を補うPlanである。上記の全工程における未対応を、PR #22の6つの予定Skillで解消したと見なさない。

**この文書は、リポジトリ全体の方向性・設計判断・未解決課題の報告書である。PR #22の実装Planおよび完了条件の変更、別工程の実装着手、案件固有の承認を意味しない。**

## 2. 確定した利用者の方針（Q01〜Q08）

| 質問 | 確定事項                                                                     | 設計上の帰結                                               |
| ---- | ---------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Q01  | QAの全工程を支援対象とする。自動実行は必要性と実行可能性で判断               | 工程の対応表は全工程を対象にし、実装済みと未対応を表示     |
| Q02  | 計画・戦略・進捗管理・終了評価を正式な責務に含める                           | `qa-workflow`のroutingだけをテストマネジメントと呼ばない   |
| Q03  | 分析・管理は製品種別非依存。実装・実行の制約は明示                           | 現行Playwright実装を非Webにも対応済みと表現しない          |
| Q04  | 性能・セキュリティ・信頼性等の非機能テストも分析・設計・実行・評価の支援対象 | 品質特性ごとに対応可能な活動・実行手段を明示               |
| Q05  | UI・API・バッチ・コンポーネント等は技術別既存手段と連携                      | 実装／実行への接続方法を案件のrunner・環境と分離して設計   |
| Q06  | 欠陥候補の報告、追跡、修正確認まで支援。製品改修は対象外                     | FAILを自動で正式欠陥にせず、外部欠陥管理の正本・権限を尊重 |
| Q07  | QA担当者・設計者、QAリーダー／テストマネージャー、自律的QA Agentが主な利用者 | 人間のレビュー・承認とAgentの生成・検証・提案を分ける      |
| Q08  | 追跡性、品質、効率、プロセスの再現性・監査性、他案件への再利用性の5軸で評価  | 単一の総合点ではなく、独立した指標と検証証拠を用意         |

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

| 工程・活動                             | 現行Skill・既存の出力                                                                                   | 確認できる不足                                             | 現段階の設計方針                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| IVEC 1. テスト要求分析                 | `spec-analysis`、`question-analysis`、`test-analysis`。仕様根拠、UNKNOWN、Risk、重点                    | QA活動への要求、品質目標・要求元・制約・対象外の合意の正本 | 製品仕様Authorityと個別のTRを複製せず、テスト要求分析として独立管理               |
| IVEC 2. テストアーキテクチャ設計       | `test-analysis`、`regression-testing`、E2E系。レベル、重点、既存Run                                     | レベル／タイプの組立て、環境・データ・方式と全体終了基準   | テスト全体のアーキテクチャと計画の正本・参照関係を定義                            |
| IVEC 3. テスト詳細設計                 | `test-requirement-design`、`test-condition-design`、`coverage-analysis`、`adversarial-review`           | 機能／アイテム／共通条件候補の上流識別                     | PR #22の`feature-analysis`、`test-item-analysis`、`test-condition-analysis`を接続 |
| IVEC 4. テスト実装                     | `test-case-design`、`e2e-test-inspection`、`e2e-test-implementation`。TC、Playwright E2E                | 非Playwrightの実装経路、環境・データ連携                   | 共通TCの正本を維持し、技術別の実装方式を連携                                      |
| IVEC 5. テスト実行                     | `test-execution`、`e2e-test-execution`、`exploratory-testing`、`regression-testing`。実測、run、Finding | 非Web実行・欠陥の正式追跡・修正確認の統合                  | runのsource resultを正本として維持し、欠陥管理の引継ぎを追加                      |
| IVEC 6. テスト報告                     | `test-execution`の個別報告、`e2e-test-reporting`のPlaywright報告                                        | テスト全レベル・タイプと欠陥・進捗・終了基準の統合         | 元の実行結果の参照のみを使う横断報告                                              |
| IVEC 7. テスト評価                     | `qa-knowledge`の知識管理、`qa-workflow`の活動状態                                                       | QA活動の有効性・効率・改善実績、完了・引継ぎの正本         | Agent Skills自体を評価する`EVALS.md`とは分離                                      |
| ISTQB 横断：テスト計画                 | Project Contextの一部、`test-analysis`の重点                                                            | 予算・要員・日程・計画承認・改版                           | テストマネジメントの独立した判断責務                                              |
| ISTQB 横断：モニタリングとコントロール | `qa-workflow`のルーティング、`regression-testing`のActivity                                             | 計画対実績、プロジェクトリスク、是正処置の管理             | テスト計画と連動する管理責務                                                      |
| 横断：レビュー・静的テスト             | `adversarial-review`のQA成果物／E2E実装の反証レビュー                                                   | 製品の要件・設計・コード等の静的テスト実行範囲は要調査     | 仕様正本と独立レビューを混同せず、既存reviewを優先                                |
| 横断：非機能品質特性                   | `usability-evaluation`、`usability-inspection`、`wcag-conformance-evaluation`                           | 性能・セキュリティ・信頼性等の技術固有実装・実行           | 品質特性別の分析／設計／実行／評価の対応表を維持                                  |

## 5. 共通の成果物契約（新設・拡張する責務に適用する設計案）

既存のMarkdown、Machine Entity、`runtime-v2`、`entity-state-v2`、revision/CAS、Scope ownershipに合わせて実装時に検討する**論理項目**である。全Skillの現行schemaを一括置換する指示ではない。

| 項目       | 必要な意味・検証                                                                                                                                         |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 識別・版   | 成果物種別、安定参照、対象範囲、成果物revision、schema versionがある場合はその版。採番規則は既存ownerと衝突しないよう実装時確定                          |
| 正本・参照 | 作成・更新ownerを一意にし、元の仕様・Risk・TR/TCN/CI/TC・run・外部Issueは参照する。再保存して第二の正本を作らない                                        |
| 情報源     | source ref・source revision・取得範囲・確認時点・取得不能範囲。実測、仕様、推論、案件の決定を区別                                                        |
| 状態       | 作業中、確認中、確定済み、保留などの意味はownerの契約と案件の承認規則で定義。全成果物へ未確認の共通列挙値を強制しない                                    |
| 承認       | 必要な対象scope、内容revision、決定主体、承認証拠、失効条件。文書に「承認済み」と書かれただけで外部承認を証明しない                                      |
| 依存・変更 | 依存元参照、現在性比較に必要なsource revision、影響範囲、再検証先、履歴。無関係な成果物を一律staleにしない                                               |
| 保存・競合 | 保存先のnative atomic create-if-absent / conditional writeを確認する。read-compare-unconditional-writeをCASと呼ばない。必要能力がなければ該当操作をblock |
| 検証       | 意味判断のレビュー、schema・ID・参照・版の機械検証、欠落・部分完了・未実施の区別。fixtureのPASSだけで実案件の受入完了としない                            |
| 保護       | 機密・個人情報・認証情報を本文や公開artifactに無断複製しない。必要最小限の証拠refと保持条件を使用                                                        |

**識別子設計**：新しい横断成果物に対して独自の固定prefixや共有の連番カウンターをここで採用しない。実装Planでownerとstorage provider、競合条件、外部Issueとの対応を確認してから決める。`DEC/ASM`、`TR/TCN/CI/TC`、PR #22の機能・アイテム・条件IDの既存／予定契約を変更しない。

**状態・履歴**：草案作成、レビュー、承認、部分完了、失効、再検証、保管は業務上の概念として整理する。元のruntimeや外部Issueの状態を勝手に再定義せず、必要な変換は参照付きで行う。承認は対象revisionが変わった際の失効判断を必須とする。

## 6. 未対応工程の成果物契約

### 6.1 テスト要求分析（IVEC工程1）

| 区分       | 契約案                                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 入力       | 業務目的・品質要求・関係者・テストベース、対象システム／リリース、開発情報源、制約、既存仕様分析、既知リスク                     |
| owner      | QA活動に対する要求の整理・合意を担う**独立責務**。`spec-analysis`は製品期待仕様、`test-requirement-design`は個別検証責務TRのまま |
| 保存情報   | テスト目的、要求元／関係者、品質目標、対象・対象外と理由、重要度、制約、情報源、未解決事項、意思決定・承認の参照                 |
| 出力・接続 | テストアーキテクチャ・計画へ渡す要求と対応付け。仕様競合は`question-analysis`、仕様Authorityは`spec-analysis`へ戻す              |
| 完了条件   | 要求と根拠・対象範囲・対象外・確認者が追跡でき、必須な未回答は影響範囲と次の担当が分かる。未承認の提案を合意済みにしない         |

**判断**：新しい独立Skillの候補とする。`spec-analysis`や`test-analysis`へ追加すると、製品仕様の確定・Product RiskとQA活動への要求の合意が混在する。Skillの名称・実装単位は実装Planで確定する。

### 6.2 テストアーキテクチャ設計（IVEC工程2）

| 区分       | 契約案                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 入力       | 確認済みのテスト要求分析、機能／アイテム構造、Product Risk、品質特性、テストレベル、技術構成、環境・データ・既存資産                                               |
| owner      | テストレベル・タイプ・方式の**全体設計責務**。局所的なRisk・重点は`test-analysis`、具体的なCIは`test-condition-design`が正本                                       |
| 保存情報   | レベル／タイプ別の検証分担、対象アイテムとリスク、テストモデル・設計技法の方針、環境・テストデータ・実行方式、依存関係、制約、代替／未対応方式、設計判断とrevision |
| 出力・接続 | テスト計画へ提供する構成・見積り前提、TR/TCN/CI・E2E/Regressionへの設計方針。正式TCNとTCを自身で生成しない                                                         |
| 完了条件   | 要求・リスクと各テストレベル／タイプの割当が説明でき、抜け・重複・技術的制約を確認できる。実施不能を解決済みと扱わない                                             |

**判断**：独立Skill候補。`qa-workflow`のrouting、`test-analysis`のRisk、`e2e-test-inspection`のPlaywright構成調査を再実装しない。テスト計画との重複項目は**アーキテクチャが方式の正本、計画が資源・日程・実行承認の正本**として参照で接続する。

### 6.3 テスト計画・モニタリング／コントロール（工程横断）

| 区分       | 契約案                                                                                                                                                                                                    |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 入力       | テスト要求分析・アーキテクチャ、Project Contextの案件設定、対象リリース／baseline、資源、期日、費用、環境・依存先、実行・欠陥・報告の現在状態                                                             |
| owner      | テスト計画・予実・是正・プロジェクトリスクの管理責務。**`qa-workflow`はSkillの起動・再開・完了状態のみ**を保持                                                                                            |
| 保存情報   | テスト計画のscope、レベル／タイプ、担当・役割、見積り、日程、環境・データ、開始／終了基準、計画前提、承認・版。モニタリング時点別の計画対実績、進捗、阻害事項、プロジェクトリスク、是正処置・責任者・期限 |
| 出力・接続 | QA担当の実行依頼、テスト報告の計画比較基準、変更時の再計画。Product RiskとRegression Activityは既存ownerを参照する                                                                                        |
| 完了条件   | 必要な計画項目、承認状態、測定基準が明示され、各監視時点の分母・集計元・実績が追跡できる。差異と是正の未完了を隠さない                                                                                    |

**判断**：テストマネジメントの独立Skill候補。計画と監視は同じ管理ライフサイクルなので、用途別に直ちに2 Skillへ分割しない。Project Contextには案件固有設定と計画正本への参照を持たせ、計画全体を複製しない。**プロジェクトリスク**と`test-analysis`の**Product Risk**を混ぜない。

### 6.4 不具合管理と修正確認（工程横断）

| 区分       | 契約案                                                                                                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 入力       | `test-execution`、`e2e-test-execution`、`e2e-test-result-analysis`、`exploratory-testing`、Regressionの実行結果／Observation／Finding、仕様根拠、対象build・環境                            |
| owner      | QA側の欠陥候補の整理、正式な欠陥管理への引継ぎ、追跡、修正通知に対する確認依頼と結果の接続。正式Issue・欠陥の状態の正本は**案件の既存管理システム**                                         |
| 保存情報   | 発見元・観測・再現手順と条件・実際結果・期待結果のAuthority・証跡・影響範囲・既知問題照合、登録有無と外部Issue参照、外部状態取得時点・revision、QAの修正確認対象・依頼・結果ref、未解決事項 |
| 出力・接続 | 根拠付き欠陥候補／引継ぎ、外部Issueと元runのリンク、必要な修正確認用TC/runへのrouting。コード修正・仕様変更・欠陥の受容をQA Agentが代行しない                                               |
| 完了条件   | 候補ごとの扱い・未登録理由、正式登録先／引継ぎ先、追跡可否、修正確認の結果または未実施理由が分かる。FAILだけでDefect登録済みとしない                                                        |

**状態設計**：`Finding`、`FAIL`、`Observation`、外部Issueの`open/closed`等は異なる概念。管理システムの正式状態はそのまま保持し、QA側の未登録・追跡中・再検証待ち等の判断を参照として持つ。複数Issue管理システムの状態名を共通の単一enumに無理に統一しない。

**判断**：独立した欠陥管理責務／Skill候補。`regression-testing`のRun選定・Activity、`qa-knowledge`の知識、`e2e-test-result-analysis`の原因判断を重複作成しない。外部への新規Issue登録・状態変更は**案件の明示権限を得た場合に限る**。

### 6.5 複数テスト方式の統合報告（IVEC工程6、ISTQBの進捗報告）

| 区分       | 契約案                                                                                                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 入力       | 計画と終了基準、一般TC、E2E、Regression、Exploration、使用性／WCAG、非Web／非機能run、欠陥・Risk・coverageと各正本revision                                                                   |
| owner      | 対象範囲・期間・SUT版を固定して、元の実行・監視情報を**読取専用で集約する報告責務**                                                                                                          |
| 保存情報   | 報告対象scope／baseline／build・環境、各テスト方式の結果と単位・分母、計画対実績、未実行・判定不能、欠陥・未検証・ブロッカー、終了基準の充足と未達、残存Risk参照、作成時点と元データrevision |
| 出力・接続 | QAリーダー向け進捗・完了報告、判断材料。元runのPASS/FAIL、Product Risk評価、正式欠陥状態、リリース判断を更新しない                                                                           |
| 完了条件   | 全数値がsource run／TC／test item／欠陥へ遡れる。`logical primary`、`resolved TestCase`、`attempt`など単位差を保存し、retryをTC件数へ重複計上しない                                          |

**判断**：独立Skill候補。既存`e2e-test-reporting`と`test-execution`の報告を置き換えず、それらを参照する。未取得のrunや未実施技術を0件PASSとして加算しない。正式な終了判定は終了基準と権限に従い、報告書の存在だけでリリース可としない。

### 6.6 テスト評価・完了／改善（IVEC工程7）

| 区分       | 契約案                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 入力       | テスト要求と目標、計画・監視・統合報告、工数・期間・費用、欠陥／リスク、前回改善とフォロー結果、保管・引継ぎ要件                                                   |
| owner      | QA活動・プロセスの有効性、効率性、計画達成、改善内容、完了・保管・引継ぎを評価する責務                                                                             |
| 保存情報   | 評価対象・期間、計画と実績の比較、評価指標・計算条件・根拠、達成／未達／未測定、要因分析と制約、改善項目・責任者・期限・検証方法、引継ぎと保管状況、確認／承認記録 |
| 出力・接続 | QA活動評価報告、改善計画、未完了引継ぎ一覧。汎用的な再利用知識だけを`qa-knowledge`へrouting                                                                        |
| 完了条件   | 評価結果の測定元と制限が追跡でき、改善責任・期限・効果確認方法が指定済み。改善効果が未測定なら「未測定」と記録する                                                 |

**判断**：独立Skill候補。`EVALS.md`はAgent Skills自身の発火・出力品質・統合評価、`qa-knowledge`は継続利用知識、`qa-workflow`はroutingであり、案件のQA活動評価の正本ではない。

### 6.7 API・バッチ・コンポーネント・非機能の実装／実行（IVEC工程4・5）

新しい実行経路は必要だが、**技術名の数だけSkillを先に増やさない**。対象案件の既存runner、CLI、フレームワーク、CI、計測工具を確認し、共通の入力・結果参照と、技術固有のpreflight／cleanupを分離する。

| 項目           | 契約案                                                                                                                        |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 入口           | 既存TC／対象アイテム、実行目的、test level/type、現在有効な期待結果、対象buildと実行許可                                      |
| 実装・実行方式 | 実際に確認した対象repo、runner、config、試験対象操作の許可、環境・ロール、データ、外部依存、副作用上限、cleanup               |
| 結果           | runner固有のraw outcomeと集計単位、TC等との対応、実開始／未開始、再試行、環境／build、証跡ref、判定不能理由、後処理と残存状態 |
| 連携           | `qa-workflow`が適切な既存実行ownerへroutingし、結果はそのownerを正本として`coverage-analysis`／統合報告が参照                 |
| 受入           | 正常系・異常系・権限不足・runner失敗・途中停止・cleanup失敗で、無根拠なPASSや安全完了を出さない                               |

現行`test-execution`はbrowser実行手段をPlaywrightに固定し、`e2e-test-implementation`と`e2e-test-execution`もPlaywright固有。既存実装を無断で「全テスト共通runner」に変更しない。品質特性については、性能、セキュリティ、信頼性、互換性等の**分析／設計／実装／実行／評価**それぞれの実対応を記録し、測定閾値がない場合はPASSを捏造しない。

## 7. 既存Skillの拡張・新規独立責務の判断

| 対象                           | 推奨判断                                                                       | 理由・重複回避                                               |
| ------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| 製品仕様・UNKNOWN              | `spec-analysis`／`question-analysis`を維持                                     | 仕様Authority・不明点の既存正本                              |
| Product Risk・テスト重点       | `test-analysis`を維持                                                          | プロジェクトリスクと分離                                     |
| TR／正式TCN・CI／TC            | 各既存Skillを維持し、PR #22計画の候補参照を追加                                | 正式設計と上流候補を重複作成しない                           |
| QA要求分析                     | **新規独立責務を推奨**                                                         | テストサービス目的・要求元・合意は製品仕様／TRと別           |
| テストアーキテクチャ           | **新規独立責務を推奨**                                                         | テスト構成・方式・環境の全体設計は局所RiskやCIと別           |
| テスト計画・監視・是正         | **独立した管理責務を推奨**。計画と監視を直ちに分割しない                       | `qa-workflow`の技術routingと混同しない                       |
| 欠陥管理                       | **新規独立責務を推奨**                                                         | 外部Issueを正本とした追跡・修正確認は実行・Regressionと別    |
| 統合報告                       | **新規独立責務を推奨**                                                         | 元のrunとPlaywright専門報告を再判定しない                    |
| テスト評価                     | **新規独立責務を推奨**                                                         | `EVALS.md`や`qa-knowledge`とは目的・正本が異なる             |
| 技術別テスト実装／実行         | **既存runner連携を先に設計し、足りない技術固有のSkill／adapterを追加**         | Playwright固有の安全・retry・cleanup契約を無理に汎用化しない |
| 静的レビュー・非機能の専門領域 | 既存`adversarial-review`、使用性・WCAGを調査後、足りない責務だけ拡張／追加     | 同じ基準や実行事実の第二の正本を作らない                     |
| Skill選択、保存・評価          | `qa-workflow`、既存runtime／`EVALS.md`を再利用・必要なrouting／fixtureだけ拡張 | 新しい中央オーケストレーター・独自評価基盤を追加しない       |

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

| 評価軸         | 指標・根拠の候補                                                                      | 取り扱い上の注意                                                         |
| -------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 追跡性・網羅性 | 対象とした独立母集団に対する機能分類・仕様・TR/TCN/CI/TCの対応、未分類・未確認数      | 分母、版、対象外理由を固定。発見済み候補の対応率と全機能発見を混同しない |
| 設計・実行品質 | 独立レビューで検出した誤り、期待結果の根拠欠落、実行誤判定、再現可能な欠陥検出        | 不具合件数の多寡だけでテスト品質を決めない                               |
| 効率           | 同一範囲の人手時間、Agent処理・レビュー時間、差戻し・再作業、変更後の再検証時間       | 環境・対象条件・品質を揃えて比較し、未測定なら明示                       |
| プロセス       | 必要成果物の現在性、承認・変更履歴、blocked・再開、完了条件の再現性、監査証拠         | CI PASSだけで全工程完了とはしない                                        |
| 再利用・導入   | 案件間で変更せず利用できたSkill、共通helper依存、導入作業、実Agent／OS／CLIの受入結果 | Web/Playwright限定の範囲を他製品へ拡大表記しない                         |

既存`EVALS.md`の仕様適合・発火・決定論的出力・意味評価・workflow統合評価を活用し、**案件QA活動の効果測定**は別の成果物として設計する。評価条件、case分割、実Agent実行、判断不能の扱いを記録する。

## 10. 進め方と実装境界

1. **目的・対応表を正本化**：READMEの目的・工程対応・技術制約を更新する計画を別途作る。現行23 Skill／PR #22の計画6 Skill／新規候補を混同しない。
2. **新たな成果物契約を審査**：本レポート第5〜7節を基に、既存owner・保存先・承認者・schema・呼び出し元と照合し、Skill拡張か新設かを実装Planへ落とす。
3. **PR #22の実装前提を確定**：第8節の優先度高5点を先に解き、既存の実装Planで定めた機能全体、例外、検証、移行を省略しない。
4. **設計・実装・統合受入**：独立した成果物のownerを確定し、Skill／runtime／CI／評価データ／Project Contextとの接続、実Agent経路を検証する。
5. **QA全工程の連結を確認**：要求→計画・アーキテクチャ→設計→実装・実行→欠陥追跡・報告→評価・改善まで、条件付き実行・部分実行・直接開始・復旧を対象にする。

**今回実施したこと**：既存資料・PRの読み取り、過去のレビュー結果と確定方針の統合、工程別の責務・成果物契約とSkill新設／拡張の判断案の作成。\
**未実施**：Skill/runtimes/CIの変更、実行テスト、実Agent受入、案件ごとの承認・保存先の決定、製品改修、PR #22のPlan更新・完了宣言。

## 11. 追加レビュー10件と利用者回答の反映（2026-11-07）

この節は、本レポート作成後の再レビューと利用者の確定回答を追記したもの。上記1〜10節は調査時点の事実・提案として保持する。実装契約の最新の正本は[Planインデックス](../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)および参照先Planであり、この報告をSkillやruntimeの実装済み証拠として扱わない。

### 利用者が確定した作業範囲と境界

| 確認                           | 回答・影響                                                                                                                                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q01 今回の変更                 | PR #22のPlan・索引・調査レポート・PR本文に限る。Skill／runtime／CI実装は明示依頼まで実施しない                                                                                                 |
| Q02 Agent起動                  | 外部の担当者等がCLIなどで起動する。指示・常時監視・通知・定期実行はSkillの責務外。Skillが入力後の分析・成果物・handoff・局所停止・再開を担当                                                   |
| Q03 CI受渡し                   | ローカル成果物の製品CIへの受渡し方式は未決定。実装時に案件ごとに選び、選定まで実CI受入はblocked。設定済み経路で必須成果物が欠落した場合はfail                                                  |
| Q04 コードPRなしの外部資料改版 | Issue・仕様書・設計資料のrevision変更を独立した分析入力にする。通知／定期照合の切替は案件側で行い、その実装をSkillへ含めない                                                                   |
| Q05 受入対象                   | `qa-training-store`の受入開始時に固定したcommitを中心にPlaywright・Vitestで検証。バッチ・非機能等の不足は独立fixtureで補う                                                                     |
| Q06 特定CLI／モデル            | 指定・固定しない。利用先のAgent製品・起動方式に依存しないSkillの正本・引継ぎ・検証を重視                                                                                                       |
| Q07 非Web原因分析              | Skill数は固定しない。ただし第一分析ownerと、観測／仮説／確度／不足証拠／再実行先の成果物を必須にする。現Planでは`testware-execution`が第一owner。独立Skillへ分けるかは実装・評価を確認して判断 |

Q02とQ04は矛盾しない。**外部資料の変更を入力として扱うこと**はSkillの責務、**通知や定期照合で入力を生成しAgentを起動すること**はSkill外の責務とする。受渡し方式・案件の保存先や承認主体を推測して確定しない。

### 再レビューP1・P2の反映先

| 指摘                            | Planで補った責務／成果物                                                                                                                                                                                                                                                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1-1 開発イベント→Agent→CI      | [開発連動QA Plan](../plans/2026-11-07_122247_development-qa-traceability.md)に受付入力と意味判断・結果の責務境界を追加。[継続workflow・受入Plan](../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)でsource snapshot、artifact ref/hash、保存・CI検証・blocked再開を定義。Agent起動はSkill外 |
| P1-2 2つのPlanの工程間接続      | [Planインデックス](../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)と継続workflow・受入Planに、初回・PR・外部資料改版・計画改版・欠陥・E2E等の入口別owner・currentness・戻り先を追加                                                                                                                         |
| P1-3 テスト実行準備             | [非Web実装・実行Plan](../plans/2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)に、非Regressionスイート／順序、テストデータ・fixture・環境、今回runのpreflightの各正本と実行準備handoffを定義                                                                                             |
| P1-4 非Web実行の原因分析        | `testware-execution`を第一分析ownerとし、診断成果物・証拠・確度・再実行／修正の戻り先を必須にする。独立Skill新設は前提にしない                                                                                                                                                                                                     |
| P1-5 E2Eまでの受入              | `qa-training-store`固定commitで、新しいfeature/item/condition・正式TR/TCN/CI/TCから**既存E2E Skill**へ接続。TCあり／なし／既存E2Eだけの経路と実run／cleanup／報告を区別                                                                                                                                                            |
| P2-1 アーキテクチャと管理の改版 | [QA全工程Plan](../plans/2026-11-07_170134_qa-full-process-implementation.md)と継続workflow・受入Planで、日程・資源・品質特性・環境の変更を関連構成→Risk／設計へ差戻す                                                                                                                                                              |
| P2-2 コードPRなし外部資料改版   | 外部から渡された資料revisionの独立入力と局所再評価を明記し、外部監視・通知の実装を除外                                                                                                                                                                                                                                             |
| P2-3 静的／非機能テスト         | 専門owner、採用基準Authority、ツール／測定、Finding・raw evidence、再検証と報告の分離を非WebPlanへ明記                                                                                                                                                                                                                             |
| P2-4 複数成果物途中失敗         | [保存・承認・集計の共通契約](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)でowner別の保存確定・状態不明・未開始、再読込と局所再開を定義                                                                                                                                              |
| P2-5 全Skill発火・競合          | 全current Skill同時利用、近接Skillの負例、複合・途中開始・再開、観測可能な実Agent証拠を継続workflow・受入Planに追加。Skill数・モデル・CLIを固定しない                                                                                                                                                                              |

### 未検証・実装時の確認事項

- 今回は**Plan文書の修正のみ**。新規予定Skill、runtime、保存provider、外部Issue更新、製品CI接続、Playwright／Vitest実受入は未実装・未実行。
- 製品CIの受渡し先が未決定であるため、方式決定・権限・実保存・内容hash／source revision照合・CIのfail検証を終えるまで、その完了条件を満たしたとは扱わない。
- Agentが複合Skillを実際に発火・停止・再開し、既存E2Eへ接続できるかは独立fixtureと実受入で検証する。PR #17の開発用Agent評価経路を運用時のAgent起動装置とみなさない。

## 12. 複数モデルの指摘統合と採用根拠（2026-11-07）

この節は複数モデルが提出した計22件の指摘について、実コード・既存Planと照合して重複を整理した記録である。**実装要件の正本は[Planインデックス](../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)とその詳細Planに置く。** このレポートの優先度・評価理由をそのまま実装上の分岐にしない。

### 実装コードで確認した制限と採用した設計

1. **新設Skillの完了検証**：`skills/qa-workflow/scripts/runtime_contract.py::_default_expected_runtime_units()`のroot unitは既存6 Skillに基づく。一方、`workflow_runtime.py::_scope_rows()`はその6件への限定ではない。未登録scopeや検証結果空を完了扱いしないこと、管理のみ／報告のみ等で検証済みowner成果物を使えることを[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)へ記載した。全Skillを同じMachine Entityへ移すことは要求しない。
2. **Regressionの非E2E経路**：`regression_runtime.py::validate_required_routes()`の正式routeは`manual`と`e2e`のみ。`auxiliary_testware_refs`はTCなしの補助経路として既に存在する。TCに紐付く`testware` required routeを追加し、旧manual／e2e／補助を回帰させない契約を[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)に追加した。
3. **実行方式の分類軸**：従来Planの「Playwright E2E以外の実装」「非Playwright runner実行」は分類が一致していなかった。Playwright Test製APIテスト、Vitest、非ブラウザTC単発実行を区別し、実行目的・既存実行ownerでrouteする契約に変更した。詳細は[05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)。
4. **静的テストの実施空白**：`adversarial-review`の既存主対象はQA成果物とE2E testware。製品要求・設計・コードの意味的レビューを同Skillに拡張し、採用したツールによる静的解析は`testware-execution`で扱うと決めた。新設Skillを増やさず、Finding・再確認・集計まで[詳細06](../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)で閉じる。
5. **非E2E testware編集の安全性**：`e2e-test-implementation/references/guidance.md`にはinspection後のbranch／commit／working tree比較と副作用確認がある。新設testware実装へ同じ技術非依存のpreflightを適用し、上書き・未許可パス・危険な検証scriptを拒否する[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)を追加した。
6. **実行結果と品質の区別**：Vitest等のrunnerがPASSした事実だけではTCの期待結果がassertionで実証されたことにならない。`adversarial-review`の非E2E testwareレビューを要求し、TC／仕様／assertion・実観測の対応と、重要検証の欠落を独立判定する[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)を追加した。
7. **runnerテスト単位の追跡**：file／suite／個別testとTC／testware／attemptの単位を分離し、部分選択・skip／todo・改名・未取得結果が全体PASSに化けない契約を[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)に追加した。
8. **複数ownerの部分保存からの再開**：`artifact_graph.py::claim_mutable_operation()`は存在するが、複数owner成果物の保存を横断的に確定する台帳ではない。既存workflow state／owner保存先に操作開始前のidentityと期待revisionを永続化し、実保存結果・run・cleanupを独立再読込する契約を[詳細02](../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)へ補足した。第二の中央graphは要求しない。

### 既存能力を維持したうえで補完した事項

9. **一般TC失敗の診断**：`test-execution`は実測と期待結果比較・FAIL／判定不能を既に持つ。欠けていた原因仮説・反証・不足証拠・修正先を既存`test-execution`へ拡張する契約とし、新分析Skillは作らない（[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)）。
10. **別セッションへの引継ぎ**：同一Agentの全Skill同時利用評価を維持し、別セッションが保存済みsource／成果物・未完了範囲から再開する受入を追加した。外部のAgent自動切替は要求しない（[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)）。
11. **改善の循環**：`test-evaluation`は改善項目・効果測定を既に所有する。採用・承認後に`test-management`／`test-architecture-design`／設計ownerへ正式に戻し、実施と次回測定を確認する契約を[詳細06](../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)へ追加した。
12. **探索とKnowledgeの直接開始**：`exploratory-testing`のCharterとinvestigation、`qa-knowledge`のlookup／revalidationは既存の直接開始経路。全体フロー図と[継続workflow受入S11〜S16](../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)に独立入口を明記した。
13. **実行後の永続化確認**：保存・再開の基本契約は既存Plan本文に存在していたため独立の新機能とは扱わない。Mermaid図にrun結果／cleanupの保存・readback・状態不明の復旧を加えた。
14. **受入証拠の分類**：`qa-training-store`の固定SHA `2a8bcf57ff091e84a8b3bf7b123568e967000d88`にある`tests/contracts/test-api.test.ts`はテスト制御APIの公開境界を検証する。一般HTTP APIの要求・応答・副作用の受入とは区別し、独立fixtureの証拠を製品受入と合算しない（[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)）。

### シラバス照合の位置付け

- **IVEC Designer V3.2**：公式配布の参照先は[IT検証産業協会](https://www.ivia.or.jp/item43/item38)。テスト詳細設計、テスト実装、実行・報告等の工程をSkillに一対一で変換しない。原本で確認した活動と、個別のSkill実装を検証した事実を分ける。
- **ISTQB CTFL v4.0.1**：[公式PDF](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf)の§1.4.1（テストの実装・実行）と第3章（静的テスト）を参照する。これらが特定のSkill名・Agent起動方式・保存形式を要求しているとは扱わない。
- **ISTQB CTAL-TA v4.0／CTAL-TM v3.0／CTAL-TAE v2.0**：各公式版の対象活動・成果物を、既存責務と設計判断の照合材料とする。日本語JSTQB版と国際版は版番号・公開状態・試験適用を区別する。
- **照合記録の原則**：公式名称・版・節、明示された活動と成果物、確認したコード証拠、当repo固有の設計要件、未検証事項を区別する。各活動の全シラバス節について原本への照合が終わっていない部分を「全体適合済み」と表示しない。

### 反映の範囲と未実装の区別

本レビューは**Planに必要な契約を確定する作業**であり、`qa-workflow`／Regression／新設Skill／静的レビューのコード変更や実Agent・実runnerでの受入を実施した記録ではない。実装時は[継続workflow S1〜S16](../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)と各詳細Planの負例を用い、結果を独立に記録する。

## 13. QA Knowledge・補助Regression・並行編集・効率化の追加レビュー（2026-11-07）

この節はPR #22 HEAD `5f1f032613f466475c5178292ac6f25866098219`を基準に、複数モデルが提示した11件の指摘をコード・validator・既存Planへ照合した記録。重複を6論点に統合した。**確定した実装契約は各詳細Planに置き、レビューの判断理由は本節に記録する**。今回の変更は文書のみ。

### Plan契約を追加した4論点

1. **QA Knowledgeのidentity・適用対象・現在性（P1）**：`skills/qa-knowledge/scripts/knowledge_runtime.py::validate_entry()`は`entry_ref`と`identity`を照合するが、`identity.kind/scope_refs`と直下の`kind/scope_refs`の一致を検証しない。`lookup()`は直下の値でscopeを選び、適用判定前に全entryを検証するため、異なるscopeへの誤適用と、無関係なentryの依存不明による全体停止の両方が成立する。`read_entry()`の`entry_revision`はentry本文の外に返るためlookupへの受渡しも必要。[詳細06](../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)で識別不変条件・適用範囲確定後の現在性確認・root不完全時の停止・revision引継ぎ・部分再検証を定義した。新Knowledge台帳は作らない。
2. **testware編集後の競合（P1）**：`e2e-test-implementation/references/guidance.md`と以前の[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)は編集前HEAD／working tree検査を要求している。しかし`artifact_graph.py::claim_mutable_operation()`はworkflow／operation単位のclaimで、別operation IDによる同じpathへの編集を排他しない。同ファイルの並行更新では編集確定時にも競合確認が必要。[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)で隔離worktreeの条件付き反映と、共有workspaceの資源予約・原子的な確定を使い分け、競合・再試行・復旧を検証する契約にした。新lock基盤は設けない。
3. **Regressionの補助routeとActivity完了（P1）**：`regression_runtime.py::project_activity()`は補助結果・件数を投影するが、Activity stateをrequired TC routeだけで導出する。そのため必須補助routeが未開始でもTC側が完了していればActivityは完了し得る一方、補助routeだけ実行したActivityは`未開始`となる。`REG-D011`／`REG-D015`も補助routeの実施義務を検証していない。[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)で今回実行必須か否かの区別、必須補助の結果・cleanupとActivity stateの一致、正式TC件数との分離、旧Run／Activity互換を確定した。
4. **Skill構成の効率化比較（P2）**：`test-evaluation`は案件のQA活動の評価を担い、`EVALS.md`はSkillの開発評価を担う。これらを一つのSkillへ統合しない。[詳細07](../plans/2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)では初回・変更なし・局所コード変更・仕様のみ改版・中断後再開を同一QA目的で比較し、Agent／人間の処理負担と独立品質基準を測る。比較不成立、重要指標の未測定、品質低下による時間短縮を効率化成功にしない。実案件ごとの課金・工数閾値をシラバスの要求として創作しない。

### 以前のPlanで対応済みだった2論点

- **未登録Skillの未検証完了（P1）**：`workflow_runtime.py::_scope_rows()`は任意Skill名を受理し、`runtime_contract.py::_default_expected_runtime_units()`の既定rootは既存6 Skillを主対象とする。`_build()`の`can_complete`で期待集合が空なら空証拠による誤完了の危険がある。現行実装は未変更だが、[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)は検証結果のないSkillの完了禁止・owner validatorの引継ぎ・単独開始・回帰をすでに要求しているため、契約を重複して増やさない。
- **TC対応非E2E実行のRegression route（P1）**：`regression_runtime.py::validate_required_routes()`は`manual`／`e2e`だけを許す。非E2Eの正式`testware` route追加・元実行結果の証拠・旧履歴の維持は[詳細04](../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)と[詳細05](../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)にある。今回の追加点は**TCなし補助routeの完了義務**であり、TC対応route不足と重複させない。

### 実装・検証との区別

- コード、Skill、評価基盤、製品CIは今回変更していない。追加した修正契約・S17等が成立した実測証拠ではない。
- QA Knowledgeの異常検索・Regression補助のみのActivity・並行testware編集・Agent効率の比較を実行再現したわけではない。既存コード・Planの処理経路を根拠とする。
- QA遂行効率は、機能として成立したことと、同じ品質で処理負担を減らせたことを区別する。従来経路が機能を持たなかった範囲は機能追加として記録し、比較不能を「効率改善」と数えない。
