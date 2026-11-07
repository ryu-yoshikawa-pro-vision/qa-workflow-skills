# QA全工程のAgent Skills・成果物・管理機能の実装Plan

## 目的

QAの全工程を支援するリポジトリとして、現行23 SkillとPR #22の計画中6 Skillに不足する、QA要求分析、テストアーキテクチャ設計、テストマネジメント、欠陥管理、統合テスト報告、テスト評価の責務を実装する。API・バッチ・コンポーネント等のテスト実装／実行と非機能テスト、静的テストの接続も対象とする。

ユーザー確定方針Q01〜Q08：全工程支援、テスト計画・管理、製品種別非依存の分析、非機能品質特性、技術別実行連携、欠陥追跡・修正確認（**製品改修は対象外**）、QA担当／管理者／Agentの利用、追跡性・品質・効率・プロセス・案件再利用の5軸での評価。

全工程支援は、全工程の強制実行、あらゆるrunnerの自前実装、AIによる仕様確定／リスク受容／リリース承認を意味しない。依頼された成果物からの直接開始、既存current成果物の再利用、部分再実行、blockedと再開を維持する。

**Planの位置付け**：この文書はQA要求・テストアーキテクチャ・管理・欠陥追跡・統合報告・活動評価という6つの追加責務を担当し、PR #22の機能抽出／設計Planを変更・置換しない。[Planインデックス](./2026-11-07_170134_qa-full-process-implementation_00_index.md)を入口とし、[非Webテスト実装・実行](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)、[保存・承認・集計の共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)、[workflow runtime・Regression契約](./2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)、[テスト実行・品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)、[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)、[QA遂行効率の比較受入契約](./2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)を詳細文書とする。PR #22のQ06は初回の成果物配置・人間編集方針を合意する契約として確定済み。Q20・Q24の未確定／任意事項は推測で確定しない。今回の文書修正ではSkill・runtime・CIや製品コードの実装は行わない。

**Skillの実行境界**：Agent起動の指示・常時監視・通知・定期実行、使用モデル・CLI・ハーネスの選定はSkill外。Skillは渡された依頼とsource revisionに対する分析・成果物・handoff・局所停止・再開を担当する。工程間の契約は[継続workflow・受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)を正本とする。

## 現状と根拠

調査基準：`main` commit `329cd8ad75ecde9d21c2e60f791214ca27fa2602`、PR #22の既存Planと2026-11-07付[工程別責務・成果物契約の調査レポート](../reports/2026-11-07_qa-process-responsibility-and-artifact-contract-review.md)。着手時には`main`、本Planのbranch、PR #22、未マージPR #17（Agent評価ランナー）・#10（Skill同期）のHEAD・差分・CI・関連Issueを再確認する。

- `skills/qa-workflow/SKILL.md`と`references/guidance.md`は開始・停止・再開・現在性・修正routingとworkflow完了を担当。案件のテスト計画や予実・プロジェクトリスクを所有しない。
- `skills/qa-workflow/assets/project-context-template.md`は既存16節と`qa.regression_scope`、`qa.regression_policy`、`qa.knowledge_root`、`qa.workflow_state_root`、`qa.reservation_root`、`qa.auxiliary_testware_refs`の6 stable keyを保持する。案件設定と成果物参照を持つが、テスト計画そのものの正本にはしない。
- `skills/spec-analysis/`は現在有効な製品仕様Authority、`skills/question-analysis/`は仕様の不明点・仮定、`skills/test-analysis/`はProduct Risk・重点、`skills/test-requirement-design/`は個別TR、`skills/test-condition-design/`は正式TCN・CI、`skills/test-case-design/`はTC、`skills/coverage-analysis/`は追跡性・閉鎖性を担当する。
- `skills/test-execution/`はPlaywrightを使う詳細TCの手動相当操作と結果報告、`skills/e2e-test-*/`はPlaywright E2E、`skills/regression-testing/`はbaseline・membership・Run・Activity、`skills/exploratory-testing/`はCharter/Observation/Finding、`skills/qa-knowledge/`は継続知識を担当する。
- `skills/usability-evaluation/`、`skills/usability-inspection/`、`skills/wcag-conformance-evaluation/`はUI/UX・アクセシビリティの専門経路。全非機能品質特性や非Webの実行を実装済みとは扱わない。
- `skills/adversarial-review/`は仕様分析・QA設計成果物・E2E testware等を反証レビューする。コード／設計書等の一般的な静的テスト全体への適用可否は、既存guidanceとfixtureの確認が必要。
- `skills/qa-workflow/scripts/artifact_graph.py`、`workflow_runtime.py`、`project_context_ids.py`、`skills/regression-testing/scripts/regression_runtime.py`、`skills/qa-knowledge/scripts/knowledge_runtime.py`、`skills/exploratory-testing/scripts/exploratory_runtime.py`に既存の参照・状態・並行更新・履歴契約がある。単純な先読み比較をnative CASと呼ばない。
- `EVALS.md`はSkillの仕様適合、発火、決定論的出力、意味品質、workflow統合評価を定義。案件のQAプロセス評価とは別の正本。
- 現行`README.md`末尾の「完全準拠やテストプロセス全体の再現は目的としない」は、Q01・Q02で定めた**全工程の支援**との関係を修正する。ただし規格への完全準拠を自動的に宣言しない。
- 既存CI：`.github/workflows/validate-skills.yml`、`deterministic-output-evals.yml`、`semantic-output-evals.yml`、`code-quality.yml`、`codex-harness.yml`。GitHub Actionsの成功だけで実Agent・実製品での品質を保証しない。

## 既存契約と変更禁止事項

1. 正本の一意性：製品仕様は`spec-analysis`、Product Riskは`test-analysis`、個別TRは`test-requirement-design`、正式TCN/CIは`test-condition-design`、TCは`test-case-design`、実行結果は実行owner、Regressionは`regression-testing`、QA Knowledgeは`qa-knowledge`。新しいSkillがこれらを再定義・再採番しない。
2. PR #22の新しい正本：`project-context`が案件設定と成果物配置・人間編集方針の合意記録、`feature-analysis`が製品機能、`ui-target-analysis`がUI構造、`test-item-analysis`がアイテム、`test-condition-analysis`が共通条件候補、`e2e-test-selection`が技術非依存のE2E選定を所有する予定。**未実装の予定機能を現行の依存必須として扱わない**。
3. 実行結果のraw値（PASS/FAIL/未実行/判定不能、Playwright `logical primary`／`resolved TestCase`／`attempt`など）を集約側で変換して元記録を上書きしない。結果数・分母の単位とprovenanceを保持する。
4. workflowの`完了`は対象製品の`PASS`やリスク受容・リリース承認と別。最終の案件承認・製品仕様の決定・製品コードの変更は権限者の責務。`qa-workflow`は工程固有の判断・承認を肩代わりしない。
5. 案件設定／成果物保存先／認証／承認者／環境はProject Contextまたは案件の権威ある資料から取得する。secret値を文書・PR・公開artifactへ複製しない。保存にnative conditional writeが必要だが能力がない場合は、その保存操作をblockedとする。
6. Skillは`SKILL.md`、`references/`、`assets/`、必要な`scripts/`、`evals/`の既存構造を踏襲。Skillが単体配布可能と宣言する場合はsibling Skill scriptを暗黙要求しない。共通runtimeに依存する場合は依存形態・起動条件を明記し、単独コピー実行を回帰検証する。
7. 既存のdirect/artifact入力、`runtime-v2`、`entity-state-v2`、Machine Entity、部分再実行、`ui-target-v1`、PR #22の移行・rollback・CAS、`qa-workflow`のroutingを壊さない。
8. 既存テスト・Plan・PRに記載された完了条件を、新Planの都合で省略・変更しない。

## 対象範囲

### 実装するもの

- 6つの独立責務とそれぞれの成果物、検証・review・currentness・履歴・案件による承認条件。命名と実装入口を`skills/test-requirements-analysis/`、`skills/test-architecture-design/`、`skills/test-management/`、`skills/defect-management/`、`skills/test-reporting/`、`skills/test-evaluation/`とする。各名称は既存の`test-requirement-design`等と誤発火しないよう実装・評価する。
- `qa-workflow`の必要時routing、Project Context・PR #22の成果物・既存TR/TCN/CI/TC・実行結果との参照連携。適切な成果物がない経路も、可能な範囲だけ局所的にblockedにする。
- UI以外のテストコード実装・更新を新規`testware-implementation`、技術別runnerの実行・raw結果・cleanupを新規`testware-execution`が担当する。性能・セキュリティ・信頼性等の非機能検証、静的テストの既存専門tool/runnerへの安全な接続と未対応能力の管理も対象とする。既存Playwright系の正本は維持し、利用不能なrunnerや未測定の品質特性をPASSとしない。
- 変更時の影響再評価、承認失効、並行処理・部分再実行・履歴、最終報告・活動評価への追跡性。
- Skill仕様、正規出力、決定論的runtime／validator、trigger・deterministic・semanticの評価データ、workflow integration test、README・EVALS・導入資料・CIの変更。

### 実装しないもの

- 仕様Authorityの作成・改変、製品コードの修正・commit・merge、正式なリリース承認の自動化。
- 外部欠陥管理サービスの正式状態をリポジトリで複製管理すること。外部システムへの登録・更新は案件で許可されたときのみ、明示した権限／監査契約に従う。
- 既存Playwright固有コードの理由のない全面汎用化、テスト設計／Product Riskの二重計算、全技術向けの自作統合runner、中央mutable manifestや共有連番カウンターの追加。
- PR #22の機能抽出・UI package移行・item/condition ID発行、独自CI接続の実装そのもの（PR #22のPlanが正本）。これらの成果物を使うための**このPlan固有の連携**は対象とする。
- 組織人事・教育など、案件QA活動から切り離された組織運営の自動化。

## 責務別の変更対象と成果物契約

### 1. QA活動に対する要求分析 — `skills/test-requirements-analysis/`

- **入力**：案件のQA目的・ステークホルダー要求、品質目標、対象範囲・対象外、現行`spec-analysis`の製品仕様、既知のProduct Risk・プロジェクト制約、Project Contextの承認済み情報。
- **正本**：QA活動に求められる目標・成果物・制約・合意・未決事項。`test-requirement-design`の個別`TR`と製品仕様の`Authority`は保存・再判定しない。
- **成果物**：対象scope・build/期間、要求元、テスト目的／品質要求／成功条件、優先度、対象・対象外と理由、情報源・revision、制約、未解決事項と担当、確認／承認参照、履歴、テスト計画／アーキテクチャへの対応表。
- **動作**：既存要求と新規要求を重複判定し、要求元に根拠がない提案を`承認済み`にしない。仕様不明は`question-analysis`、仕様Authorityは`spec-analysis`へ戻す。新たなProduct Risk評価は`test-analysis`へ委譲する。
- **完了条件**：全必須要求が有効根拠または未確認／対象外の扱いへ閉じ、要求元・revision・未回答に伴う影響・承認の有無が区別できる。承認が必要な利用先では未承認の要求を確定入力にしない。
- **変更・検証**：新SkillのSKILL/guidance/data-contract/output-template／必要helper/evals、`qa-workflow`の開始・修正routingと`README.md`。`test-requirement-design`との負例trigger、要求元不在・競合仕様・変更後の局所再確認を評価。

### 2. テストアーキテクチャ — `skills/test-architecture-design/`

- **入力**：QA要求、現行仕様・Product Risk、機能・アイテム・条件候補がある場合はその有効参照、テストレベル／タイプ、製品構成、環境・データ・既存testware、非機能の品質特性。
- **正本**：対象アイテム・品質特性・リスクをどのテストレベル／タイプ／技法・テスト方式で担保するかという全体構成・依存と、制約付きの代替方式。局所技法の採否や正式CIは`test-condition-design`が正本。
- **成果物**：テストレベル／タイプ別の対象と根拠、検証分担、データ／環境構成・接続点、テストモデル・観測方法、手動／自動、runner・道具・実装要否、非機能の測定可能性、制約・リスク、依存・revision、判断・承認参照。
- **動作**：`test-analysis`がProduct Risk／深度、`e2e-test-selection`がE2E価値判断、`e2e-test-inspection`がPlaywright固有の実装可能性を担当する。テストレベルの優先順位は①案件・ユーザーの明示指定、②有効なアーキテクチャのアイテム／品質特性別割当、③いずれもない場合に限る`test-analysis`既定のシステムテストとする。①と②の矛盾を無断で上書きせず、該当範囲の判断元に戻す。複数レベルの割当は一つに丸めない。初期構成とProduct Risk評価の相互再確認は入力revisionの変化がある影響範囲だけで行い、同じ条件で再実行し続けない。 **管理からの差戻し**：資源・日程・環境・品質特性・終了基準が変わったら、影響するレベル／方式だけ再評価し、Risk・正式設計・実行準備に必要な変更を返す。
- **完了条件**：各要求・重要リスク・品質特性のレベル／方式と、対象外・未実装・別レベル・技術的ブロッカーが検証できる。先に`test-analysis`がシステムテストを既定とした後、アーキテクチャで別レベルが確定した場合は、その割当に依存するProduct Risk・TR/TCN/CI/TCのみ要再検証に戻す。無関係なcurrent成果物を維持し、環境欠落を実行可能と報告しない。
- **変更・検証**：新Skill一式、`test-analysis`と`qa-workflow`の参照契約、必要時に`test-requirement-design`、`test-condition-design`の既存入力へ構成refを追加する。E2E選定との責任分離、非UIのみ・レベル重複・依存環境不足のfixtureを評価。

### 3. テスト計画・モニタリング／コントロール — `skills/test-management/`

- **入力**：QA要求・アーキテクチャ・Project Context、対象release／版、担当・要員・工数・予算・日程・環境、各run/Regression Activity／欠陥・未実行・Riskの実績。
- **正本**：テスト計画、開始／終了基準、計画の承認・改版、プロジェクトリスク、進捗監視、差異、是正処置。Product Riskは`test-analysis`、workflow実行stateは`qa-workflow`、Regression membership/Runは`regression-testing`のまま。
- **成果物**：計画版・対象範囲・期間、担当・資源・日程・予算・レベル／タイプ、環境／データ、開始／終了基準、承認。要求される実行方式・TC／testware／run・source owner・対象build／環境を集計母集団として明記する。監視時点の分母／実績・差異・プロジェクトリスク・是正処置と担当／期限／結果／履歴を保持する。 **非Regressionの実行準備**として対象TC／testware・スイート／順序・依存・データ／環境準備担当を記録する。Regression Runの正本は既存`regression-testing`。
- **動作**：`計画作成／改版`、`進捗参照`、`差異・是正管理`を同じ責務のmodeとする。`test-evaluation`で採用された改善事項を受け取った場合は、必要な承認と旧／新計画revision・実施担当・実施結果を記録し、改善の効果測定は評価ownerへ返す。期限・予算・担当を捏造せず、必要な範囲のみblockedにする。承認済みの計画版と変更案を区別し、予定sourceと取得結果の差を[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)で照合する。欠落した実績を0件実施とせず未測定とする。 計画改版時は`test-architecture-design`へ関連するレベル・方式・環境の再評価を依頼し、必要なRisk／設計／実行予定だけ再検証・再承認する。
- **完了条件**：計画の範囲・終了基準・責任者・承認状態が明示され、各進捗値が元データと測定単位へ遡れる。見積りと実績を混同せず、未処理の差異／プロジェクトリスクを隠さない。
- **変更・検証**：新Skill一式、`qa-workflow`、Project Context Section 14の正本参照方法、`regression-testing`のActivity、実行ownerの結果を読取参照する契約。複数version計画、承認失効、部分runと全体進捗、工数不足、並行更新を評価。

### 4. 欠陥管理と修正確認 — `skills/defect-management/`

- **入力**：`test-execution`／`e2e-test-execution`／`e2e-test-result-analysis`／`exploratory-testing`／Regressionのsource結果・Observation・Finding、`spec-analysis`の期待仕様根拠、build／環境、案件の正式欠陥管理先。
- **正本**：QAによる欠陥候補の整理、証拠・重複照合、正式な報告先への引継ぎ、外部Issueとの対応、修正確認計画と結果参照。正式欠陥の状態・優先度決定・修正実施は案件の外部正本・権限者。
- **成果物**：候補のscope・provenance・症状／再現条件／実際結果、仕様に基づく期待結果、証拠参照・機密扱い、判定可能性、類似／既知Issueの対応、未登録理由・引継ぎ履歴、外部Issue参照・取得時点とrevision、修正確認TC/runと結果／未実施理由。
- **動作**：`FAIL`／`Finding`／`Observation`を自動的に正式Defectにしない。原因未確定は実行分析ownerへ戻す。外部サービスの登録・更新は、[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)に従い認証された主体・権限、操作対象scope・revision・承認と重複防止を確認した場合だけ実行する。未認可なら読取・報告のみ。外部Issue変更時は修正対象build・TCを検証して既存`test-execution`／`e2e-test-execution`へ再実行を依頼し、`regression-testing`のRun選定と混同しない。修正確認の実操作と合否判定は実行ownerで行う。 非E2E実行の第一分析ownerは`testware-execution`、ブラウザ直接TCは`test-execution`、既存E2Eは`e2e-test-result-analysis`。各ownerが元結果を維持して観測・原因仮説／確度・追加証拠・再実行先を記録し、正式欠陥候補に引き継ぐ。
- **完了条件**：候補ごとの提出先・未登録／保留の根拠・追跡可否・外部Issue確認状態・修正確認結果が閉じている。欠陥解決や製品修正の完了をQA Skillが無根拠に確定しない。
- **変更・検証**：新Skill一式と読み取り専用の外部Issue入力契約、必要なtool接続手順、`qa-workflow`のhandoff。二重登録、権限不足、staleな外部状態、誤ったFAIL分類、修正確認対象の誤version、cleanup未完了を評価。

### 5. テスト全体の統合報告 — `skills/test-reporting/`

- **入力**：承認済みまたは状態が明示された計画・終了基準、TC一般実行、E2E、Regression、Exploration、非E2E・非機能run、静的レビュー／静的解析、UI/UX・WCAG、coverage、Product Risk、欠陥候補／外部Issueのcurrent projection。各ref・revision・対象build/環境を含む。
- **正本**：対象時点の**横断的な報告snapshot**だけ。元の実行結果、原因分析、正式欠陥状態、計画、Risk、リリース決定を更新しない。
- **成果物**：報告scope・期間・build・レベル／タイプ、**計画上要求されるsource owner・run・対象TC／testwareと実際に取得した集合の差**、取得範囲・source revision・完全性、TC／run／attempt等の分母・単位、未開始／未実行／判定不能／FAIL／PASS／blocked／cleanup、欠陥・残存リスク、終了基準の充足／未達／不明、報告時点・次の判断先。
- **動作**：各ownerから読み取り専用で集計。`logical primary`、`resolved TestCase`、`attempt`、Exploration session、TCを同じ件数に足さない。計画で要求するsource inventory・対象build／期間・scopeと取得した結果を照合する。Reportだけ直接開始した場合は明示scopeと許可された探索範囲を固定し、母集団が未知なら全体率を未確定とする。source列挙の失敗を0件PASSにせず、正式リリース可否の判断は行わない。詳細は[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)。
- **完了条件**：全数値が元run・baseline・計画へ追跡でき、集計単位・重複排除・不完全分母・報告時点のrevisionが機械検証できる。意思決定に影響する欠落があれば完了ではなく影響範囲と再取得条件を示す。
- **変更・検証**：新Skill一式、実行owner／Regression／QA Knowledge等の読取projectionと`qa-workflow`のreport routing。retry増加だけでTC件数不変、部分run／結果遅延／build混在／欠陥更新による鮮度変化を検証。

### 6. QA活動評価・引継ぎ・改善 — `skills/test-evaluation/`

- **入力**：QA要求・品質目標、計画と予実、統合報告、欠陥・リスク・coverage、工数・期間・再作業、前回改善・引継ぎ・成果物保存状態。
- **正本**：案件のQA活動の有効性・効率・再現性・改善効果の評価、完了／保管／引継ぎの確認と改善項目。`EVALS.md`はSkill品質評価、`qa-knowledge`は継続QA知識の正本のまま。
- **成果物**：評価scope・時点・入力revision、評価対象目標・指標／計算条件、計画／実績、達成／未達／未測定と根拠、原因候補と判定不能範囲、改善項目・対象の正式owner・採用に必要な承認・計画／設計変更依頼ref・担当・期限・実施状態・確認方法、前回改善の効果測定、保管・引継ぎの状況・承認記録。
- **動作**：Q08の5評価軸（追跡性、品質、効率、プロセス、再利用性）を測定可能な情報に基づいて扱う。複数指標を独自の根拠なき総合点にしない。比較条件が違えば注記する。リリース承認・プロジェクト終了決定を代行しない。採用された改善は`test-management`・`test-architecture-design`または元設計ownerへ正式な改版依頼として引き継ぎ、実施後の効果を再測定する。再利用知識の候補だけを`qa-knowledge`へルーティングし、Knowledge登録を計画変更・実施とみなさない。
- **完了条件**：すべての指標に測定元、対象・分母、結果または未測定理由がある。改善と未完了事項は責任・期限・検証方法または未確定状態を持ち、引継ぎ・保管・権限者の確認が追跡できる。**Skill構成の効率比較は本Skillの責務に含めず**、[QA遂行効率の比較受入契約](./2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)に従う。
- **変更・検証**：新Skill一式、`test-reporting`／`test-management`からの参照、`qa-knowledge`への候補連携。時間短縮だけで品質改善を主張する例、未測定・非比較条件・改善未実施・複数案件再利用を評価。

## 共通データ・保存・承認契約

### 既存体系との関係

保存・承認・集計完全性・独立受入の実行契約は[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)を正本とする。以下はSkill間の論理項目であり、共通mutable storageを作る指示ではない。

- 正規の人間向け出力は既存の`assets/output-template.md`によるMarkdownに合わせ、`scripts/`の決定論的helper／`evals/deterministic/`のvalidatorで機械検証できる項目を限定する。既存`TR/TCN/CI/TC`を新成果物へ統合しない。
- 新成果物ごとにowner、scope、安定した識別、source refsとrevisions、現在性を判断する依存、作成／改版、過去結果参照、block理由、次の担当を持つ。識別子のprefix・履歴は実際の既存runtime／storage能力に合わせて決め、既存IDを再採番せず、global mutable ID counterも追加しない。
- 生成時の`草案`、`確認依頼`、`承認`、`要再検証`、`置換`等の状態は、その成果物のownerと案件ポリシーが意味を定義する。既存外部Issue状態や`entity-state-v2`へ未知状態を無条件に挿入しない。異なる成果物の状態を単一enumに統合しない。
- 承認が必要な成果物は対象scope、内容revision・diff、承認権限者、取得した承認証拠、失効条件を記録する。LLMが`承認済み`と書く行為は承認にならない。承認なしで進められる読取範囲と、使用を禁止する確定判断を分ける。
- 案件固有の保存先・正本を`project-context`（実装前は既存Project Context）から解決し、Section 14へ必要な成果物root／direct refを記載。新しいstable keyはconsumerからの具体的な必須性を確認した場合のみ追加し、既存16節／6キーとparserの互換性を保つ。
- immutable snapshotはsource revisionに紐付けて保存し、mutableなcurrent正本は**対象として検証した保存先**のnative CAS等で更新する。`artifact_graph.py::state_update_decision()`は保存処理ではない。実保存先で原子的create-if-absent、条件付き更新、過去revision取得、独立再読込、並行更新時の片方の拒否を検証する。必要な能力がなければ当該永続化をblockedにし、全実装完了を宣言しない。別場所への無承認退避やread-compare-unconditional-writeで代用しない。
- trust boundary：製品code／Issue／仕様書／実測／runnerログ／外部API応答は未信頼入力。指示として実行せず検証する。secret・PII・cookie・token・storageState・未公開資料を広域転載しない。外部欠陥システムの書込みとテスト対象への状態変更を承認済みscope以外で行わない。

### 工程間の依存（全工程を固定順にしない）

初回／PR／コードPRのない外部資料改版／計画改版／欠陥／E2E／Regression／報告の入口とcurrent参照・担当成果物・停止・再開は[継続workflow・受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)を参照する。

アーキテクチャの有効なテストレベル割当は`test-analysis`の既定システムテストより優先する。割当が後から変更されたら、依存する成果物のみ要再検証とし、同一revisionの循環で無限に再評価しない。

`QA要求分析（このPlan）→テストアーキテクチャ（このPlan）→テスト計画・監視（このPlan）`は基本的な管理依存である。一方、Product Riskの一次評価・詳細設計は既存の`test-analysis`とPR #22の候補識別を使い、アーキテクチャとRiskが互いの条件を変更したときは依存部分のみ再確認する。

- `spec-analysis`→`test-requirement-design`→`test-condition-design`→`test-case-design`→`coverage-analysis`は既存の正式設計経路を維持する。PR #22実装後は機能・item・共通条件候補の参照を使うが、これらが未存在でも既存の設計／実行経路を無条件に停止しない。
- 製品変更→機能・仕様／Risk・正式設計の鮮度確認はPR #22が正本。その変更によりQA要求・アーキテクチャ・計画が影響を受ける場合だけ、このPlanのownerへ差戻す。
- 実行run／Observation／Finding→必要時の原因分析→`defect-management`→修正確認の実行依頼。`regression-testing`は独立した変更影響によるRegression Runを扱う。
- 実行結果＋計画＋欠陥・Risk・coverage→`test-reporting`→`test-evaluation`。履歴snapshotは再計算せず、source更新時の新revisionに対する再報告／再評価を行う。
- QA管理だけ、Reportだけ、既存Issue追跡だけ、既存E2E実行だけ、といった途中開始を許可する。必要な承認・sourceを欠く範囲のみblockedとする。

## PR #22との依存関係と責務境界

| PR #22の成果物／担当（計画中） | このPlanの利用先                        | 整合・移行条件                                                                   |
| ------------------------------ | --------------------------------------- | -------------------------------------------------------------------------------- |
| `project-context`              | 6領域すべて                             | 案件設定と参照を読む。計画本文／実行結果／正式IssueをProject Contextに複製しない |
| `feature-analysis`             | 要求分析、アーキテクチャ、管理、報告    | 機能ID・source完全性を参照し、未発見機能を独自に再採番しない                     |
| `ui-target-analysis`           | アーキテクチャ、実装／実行連携          | UI事実は観測／構造の正本を参照。期待仕様は`spec-analysis`                        |
| `test-item-analysis`           | アーキテクチャ、計画、report            | itemの階層・機能参照とtest level/typeの扱いを保つ                                |
| `test-condition-analysis`      | アーキテクチャ、report                  | 共通条件候補を正式TCN、正式coverage、実行済みと誤認しない                        |
| `e2e-test-selection`           | アーキテクチャ、計画、実行接続          | 自動化価値の選定を重複採点せず、Playwright固有の実装可否は既存E2E owner          |
| `qa-workflow`／既存runtime     | 全6領域のrouting・部分再開・currentness | 工程固有logicの重複、state正本の二重化、既存直接開始経路の破壊を防ぐ             |

**検証の段階**：PR #22の6 Skillが未実装の間は既存refを使う経路の動作と計画中schemaの静的整合だけを検証する。実装後には新しいfeature/item/condition成果物を実際に読ませ、source currentness、ID、legacy、partial rerunの統合受入を必ず追加する。両者を同じPASSにしない。

**移行規則**：PR #22の未マージheadのschemaを実装済みとして参照しない。PR #22のmerge／実装完了前は現行のsource ref・scopeを使う。実装後は参照追加・currentness比較・legacy読取の移行と回帰を実行し、既存成果物の情報が不足する場合は局所的に未確認／blocked。ID自動再採番、全成果物の無条件stale化はしない。

**PR分担**：本Planの実装はPR #22の実装Planとは別に管理できるよう、6責務の変更・検証を一組の実装計画として保持する。PR #22の15完了条件をこのPlanの完了で代替しない。実装時のPR数や順序はユーザーの作業指示を優先し、工程の必要機能・検証を無断で省略しない。

## API・バッチ・非機能・静的テストとの接続

[非Webテストの実装・実行Plan](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)を正本とする。API・バッチ・コンポーネント等では**実行結果の取込だけでなく、新規・既存テストコード／fixture／設定の実装・更新・検証・起動・実測・後処理まで**を対象にする。既存PlaywrightやRegressionの正本を再実装しない。

製品要求・設計・コードの静的レビューは既存`adversarial-review`を拡張し、許可された静的解析ツール実行は`testware-execution`に追加する。正式TCなしの直接入口、Finding・誤検出・再レビュー・統合報告を[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)に従って実装する。案件で有効なrunner／権限／測定閾値が不足する対象は該当実装・実行の受入を未検証として残し、全体完了としない。製品業務ロジックの改修は対象外であり、利用先repoのテストコード変更も別途権限を確認する。

## リスク・前提・未確定事項

### 確認済みの前提

- 現行Skillの責務は上記のとおり。PR #22はPlanと調査報告のみで、6新Skillは未実装。
- 案件レベルの承認者、外部Issue管理システム、保存先、使用可能runner、非機能の基準値、予算・日程は一般化できない。これらは実案件のProject Context等から解決し、技術や案件ごとの固定値を導入しない。
- `EVALS.md`の評価対象はAgent Skillsそのものであり、案件のQA活動評価と区別する。

### 案件固有情報の取得と完了条件

- 保存先のnative conditional write・過去revision参照を[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)に従い実証する。providerが未確定なら永続更新は未完成であり全体完了を宣言しない。
- 外部欠陥管理の読み取り／書込み権限・監査証跡。未許可の外部更新を自動実行しない。
- 非Web実行および各非機能測定に使う具体的runner。実在する対象案件・依存・CIを調査し、未検証範囲を記録する。
- 作業中のPR #22／PR #17／PR #10と同じファイル・runtime・評価データに触れるときは、merge状態・base差分・正本を再確認する。
- 公式シラバスの版・該当節と本リポジトリ独自の追加要求を[調査レポート](../reports/2026-11-07_qa-process-responsibility-and-artifact-contract-review.md)で区別する。原本の特定節を未照合のままシラバス適合済みと扱わない。

### 主な失敗条件

承認証拠の偽造、情報源の不足を0件とする集計、暫定QA要求から期待仕様を自動生成、Product Riskとプロジェクトリスクの混合、複数runnerの件数二重計上、正式Issue状態の二重管理、並行更新の上書き、旧revisionの報告をcurrent扱い、機密証跡の転載、未実施をPASSにする処理。

## 実装順序

1. **base・責務・成果物一覧の再確認**：`main`とPR #22、他open PR、全23既存Skill・helper・consumer、source artifact、CI/testを確認。全工程の対象範囲と直接開始／部分再開を固定し、重複正本の有無を整理する。
2. **Skillの正式な入出力・現在性・承認契約**：各6責務の`SKILL.md`／`references/guidance.md`／`references/data-contract.md`／`assets/output-template.md`を定義。新たな識別子・revision・失効・保存条件・rootとread-only参照形式を既存runtimeと照合する。必要時だけproduction helperを追加する。
3. **QA要求分析とアーキテクチャ**：QA目標・要求元→レベル／タイプ／環境／方式の引継ぎを実装。`spec-analysis`／`test-analysis`／`test-requirement-design`との責務分離、PR #22のfeature/item/condition候補への条件付き参照を検証する。
4. **テストマネジメント**：計画・改版・承認、モニタリング・差異・是正・プロジェクトリスクを実装。`qa-workflow`の状態やRegression Activityを第二の正本にせず、計画対実績を対応付ける。
5. **欠陥管理**：現行の実行／原因分析／Exploration・Regressionのsource結果から候補→外部Issue参照→修正確認の引継ぎを実装。読み取りを先に成立させ、書込みを必要とする経路には認可・監査・競合条件を設ける。
6. **非E2E／非機能／静的テストの実装・実行**：[詳細Plan](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)と[実行方式・品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)に従い既存TCからAPI／バッチ／コンポーネント等のテストコード・fixture・設定を実装／更新／検証し、技術別runnerで安全に実行する。非機能測定・静的テストも専門ownerを維持し、raw result／証跡／cleanupを記録する。
7. **統合報告**：一般TC・Playwright・Regression・Exploration・非Web／非機能・欠陥・計画をsource refsで集計する。計画上のsource inventoryと取得範囲を[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)で突き合わせ、欠落・分母・版と終了条件を独立に判定する。
8. **テスト評価**：報告・計画・工数・履歴から5軸の評価・改善・完了／引継ぎを実装する。採用改善は計画／アーキテクチャ／設計ownerへ変更依頼し、実施状態と次回効果測定を照合する。未測定・比較不能・未承認の判断を保持する。
9. **workflow／既存契約へ統合**：[workflow runtime・Regression契約](./2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)に従い未登録Skillと未検証成果物を完了にせず、TCに紐付く非E2E required routeと別セッション再開を追加する。`qa-workflow`のrouting・状態・開始点／停止／再開、Project Context参照、`coverage-analysis`／`adversarial-review`、PR #22実装後のfeature/item/condition ref、legacyとpartial rerunの回帰を確認する。大規模な中央orchestratorを新設しない。 ユーザー側のAgent起動や監視ではなく、外部資料改版も含む受付後のSkill routingと局所停止・再開を対象とする。
10. **評価・CI・READMEの更新**：各Skillのtrigger、出力契約、決定論的・意味評価、実Agent統合、ポータビリティを追加。READMEの目的・工程一覧・対応／未対応技術・導入手順と`EVALS.md`を更新し、全テスト・CIを確認する。

## 検証

### 責務境界・構造

- 6新Skillの`skills-ref validate`、frontmatter、`SKILL.md`での起動条件・非起動条件、正規の`references/`／`assets/`／`scripts/`／`evals/`を検証。 全current Skillを同一Agentで利用可能にし、モデル・CLIを固定せず近接Skillの誤発火・途中開始・E2E直接実行・再開を評価する。
- `spec-analysis`、`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`qa-workflow`との負例を含む発火評価。直接開始、途中開始、既存成果物再利用、局所blocked／再開のrouting fixtureを追加。
- Skill別のdeterministic・semantic評価で、定義した成果物の必要項目、根拠・版・参照整合、意味品質・重複正本・誤分類、未承認・未測定・不完全情報の扱いを検証。新しい評価用runnerを重複実装しない。

### QA要求・計画・アーキテクチャ

- 要求元の異なる品質要求、変更で失効した要求、仕様AuthorityとQA目標の衝突、要求不明時の部分継続。
- 1アイテムを複数レベル／タイプで確認する構成、案件明示指定／アーキテクチャ割当／`test-analysis`既定値の優先順位、後からの割当変更による局所再検証。E2Eに不適な対象、非UIのみ、非機能の閾値不明、既存testware再利用、環境不足。
- 承認前／承認後の計画revision、計画日程と実績の差、部分run／Regression selected Run、Product Riskとプロジェクトリスクの分離、是正処置の未完了。

### 欠陥・実行・報告・評価

- `PASS`／`FAIL`／`Finding`／`Observation`／`判定不能`の区別、原因未確定、既知Issue照合・重複検出、外部Issueの権限不足／stale read、未登録時の引継ぎ、修正確認で旧buildを誤使用しない。
- 一般TC／E2E／Regression／探索／API／バッチ／コンポーネントのsource結果のraw値保持、実開始前停止、retry、cleanup失敗、異なるreporter、重複run、複数環境／buildの混在。 非Regressionの実行スイート・順序・データ／環境・fixture／preflightの引継ぎ、非Web異常診断のownerと修正先も評価する。
- 対象集計：計画で必要とされたsource owner／runと実際に取得した集合を照合する。pagination失敗、権限不足、件数0／分母0、未実行、部分完了、旧revisionを`PASS 100%`へ誤投影しない。
- 評価：品質基準不足、監視実績不足、時間削減のみ、未測定／改善未実施、比較条件不一致、案件を跨ぐ再利用時の制約を適切に表示すること。

### 保存・変更追従・安全性

- 対象とする実保存先のAPI／transactionでcreate-if-absent・native CASの競合を検証する。同時更新、保存後再読込不一致、履歴欠落、旧revision、source部分変更と局所staleを評価する。
- 外部Issue／runner／製品repoの未信頼文字列、secret／PII／未公開資料、権限不足、副作用、cleanup未確認。承認対象scope・revisionと認証済みの権限主体を検証し、無許可のIssue更新・二重登録・製品改修・リリース操作を起こさない。
- PR #22が未実装／実装済みの両経路で、既存source refだけを使う開始と新たなfeature/item/condition参照を使う開始を区別して検証。旧仕様・UI package・TC・Regression・Knowledgeを失わない。

### 実Agent・対象案件受入

[継続workflow・受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)のS1〜S17を対象とする。`qa-training-store`の受入開始時に固定したcommitを用い、既存PlaywrightのTCあり／TCなし／既存E2Eのみの経路とVitestの実runnerを確認する。足りない技術は独立fixtureで補うが実製品受入と区別する。

[共通契約の受入項目](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)を用い、要求見落とし・欠陥の誤登録・二重計上・未確認事項の誤承認・競合更新について独立の正解／拒否条件を設定する。

- [共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)の独立した期待結果と拒否例を用い、QA要求→アーキテクチャ→計画→仕様／Risk／設計→テスト実装→実runner→欠陥追跡→統合報告→活動評価を検証する。未測定、blocked、修正確認、rollbackも対象とする。
- 案件や外部サービスの接続が必要な経路は権限・環境・source revisionを固定し、実Agentと実runnerで確認。利用不能な範囲は「未検証」と記録し、fixture成功で実案件受入を代替しない。
- 性能・セキュリティ・信頼性等の対象品質特性は、それぞれ有効な受入基準、測定method、runner、evidenceを確認し、実行可能な場合は実測と独立した検証を行う。環境のない特性に合格を付けない。

### 既存テストとCI

- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`
- `python -m unittest discover -s tests/skills/evals/deterministic -v`
- `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v`
- `python scripts/skills/evals/semantic/validate.py`
- `python -m unittest discover -s tests/skills/evals/semantic -v`
- `python -m unittest discover -s scripts/skills/evals/semantic/tests -v`
- `python -m unittest discover -s tests/skills/evals/trigger -v`
- `python scripts/format_tracked.py check`
- `python .github/check_patch_whitespace.py`、`git diff --check`、公式`skills-ref validate skills/<name>`（全current Skill）。
- GitHub Actionsの`Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Code Quality`、`Codex Harness`。各job／stepの未実行・FAIL・SKIPを個別に記録する。
- 変更したSkillのisolated packaging、README/EVALSとtrigger dataset数の同期、実Agentの実発火・routingを別々に確認する。

## 完了条件

すべてを満たした場合だけ実装完了とする。

1. 6つの責務が既存ownerを侵害せず、入力・正本・出力・状態・変更／承認・完了基準を持つSkillとして利用できる。各Skillは単独要求と複合workflowの両方で適切に発火・停止する。
2. QA要求・製品仕様・Product Risk・TR／TCN／CI／TC、QA計画・アーキテクチャを混同せず、上下流の不足・承認・残存リスクへ辿れる。
3. テスト計画・監視・是正・プロジェクトリスク・終了基準を管理でき、`qa-workflow`のrouting／Regression Runの第二の正本を作らない。
4. FAIL／Finding／Observationから欠陥候補・外部Issue参照・修正確認へ接続できる。正式欠陥状態は外部正本を保持し、製品コード修正を行わない。
5. 一般TC、E2E、Regression、Exploration、非Web／非機能の結果を技術別単位・対象versionのまま集約し、**計画のsource inventoryと取得完全性**を確認する。未実行・部分取得・retry・旧revisionにより偽の100%やPASSが発生しない。
6. QA活動を5軸で評価し、計画比較・根拠・未測定・改善と引継ぎを追跡できる。採用・承認された改善が適切な計画／設計正本の改版と実施・次回測定へつながる。`EVALS.md`のSkill評価とは分離する。Skill構成自体の効率化は[比較受入契約](./2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)の同条件実測で独立判定する。
7. [非Webの実装・実行Plan](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)、[テスト実行と品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)、[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)の全完了条件を満たす。API／バッチ／コンポーネント等でテスト実装・更新からrunner実行・結果まで接続し、非機能品質特性と静的テストの対応・未対応範囲を証拠付きで示す。
8. [共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)、[継続workflow・受入Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)、[workflow runtime・Regression契約](./2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)の全完了条件を満たす。対象保存先のnative CAS・履歴、承認主体の認証と対象scope／revision、変更影響、セキュリティ・cleanup、並行更新・再開を実証する。
9. 現行23 SkillとPR #22の計画中6 Skillの責務・正本・既存ID・直接開始・履歴との整合を保つ。人間が正本QA成果物を直接編集・レビューする場合、承認済み配置と機能別参照・編集可能範囲を確認し、変更後にownerの検証・履歴・変更影響判定へ反映できることを確かめる。**PR #22実装前は単独受入と参照仕様の照合、実装後は実成果物との統合・ID・migration・回帰受入**を別々に実施する。後者が未検証ならQA全工程の最終実装完了を宣言しない。PR #22の15完了条件と確定済みQ06、未確定のQ20／任意のQ24を維持する。
10. 新Skillの仕様適合・発火・決定論的出力・意味評価・workflow統合・実Agent受入・[QA遂行効率の比較受入](./2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)について、**Agentの候補から独立した期待成果物・誤判定拒否例**で検証する。関連回帰テスト・CI・README・EVALS・導入文書を更新し、未実施・SKIP・実案件未接続をPASS扱いしない。 特定のモデル・CLI・ハーネスを固定せず、全current Skillの同時利用と実Agentでの発火・成果物検証、別セッションの成果物readback・停止／再開を必須にする。

**Skill構成の効率化ゲート**：既存構成または実際の人手手順と同じQA目的・品質条件で、初回、変更なし、局所コード変更、外部仕様改版、中断・再開の実測を比較する。品質劣化・誤PASS・欠落した証拠を短時間化の成果に含めない。比較元がない範囲や費用などの未測定項目は独立して明示し、機能の受入成功を効率化実証へ転用しない。

## 次の作業で確認する事項

- 実装着手時の`main`、PR #22、PR #17、PR #10の差分とCI。プランニング時点の推奨Skill名・構成を、既存ownerとの最新衝突があれば根拠付きで更新する。
- 案件のstorage providerとCAS・履歴の実能力、外部Issue管理サービスと認証された承認主体・対象操作・revision、技術別runnerと非機能基準を確認する。未確定部分だけblockedにし、独立した読取・設計まで停止しない。 **CI受渡し方式は未決定**。案件ごとの選定まで実製品CI連携の受入はblockedとする。
- 実装時には各工程の計画・テスト・CI実績と、実Agent・実案件の受入結果を独立に記録する。未検証の工程を削って完了宣言しない。
