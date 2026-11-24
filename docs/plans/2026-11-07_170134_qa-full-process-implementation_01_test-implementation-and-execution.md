# API・バッチ・コンポーネント・非機能テストの実装・実行連携Plan

## 目的と担当

この文書は[QA全工程の実装Plan](./2026-11-07_170134_qa-full-process-implementation.md)の一部であり、製品種別に依存しないテスト設計成果物から、**Playwright E2E以外のテストの実装・実行・結果収集まで**をつなぐ責務を担当する。全工程の目的と文書間の責務は[Planインデックス](./2026-11-07_170134_qa-full-process-implementation_00_index.md)に従う。実行方式・実装前安全確認・assertion品質・runnerの個別テスト識別は[テスト実行と品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)、静的テストは[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)を正本とする。

対象はAPI、バッチ、コンポーネント、イベント・外部連携・データ処理、および性能・セキュリティ・信頼性・互換性等の非機能テスト。案件で利用できる技術別のrunner／CLI／計測ツールを使う。対象SUTの製品実装・正式製品仕様をQA側が改修する責務は持たない。

**作業境界**：本Planの作成は文書変更のみ。実装時に製品repoへテストコード／設定／fixtureを追加・更新する場合は、そのrepoへの明示権限を別途確認する。既存SUTの業務ロジックをテストしやすさのために無断修正しない。

## 現状と依存

- 現行の`test-case-design`はTCの具体的な前提・手順・期待結果を所有する。
- 現行の`test-execution`と`e2e-test-implementation`／`e2e-test-execution`はPlaywrightに限定された実行／実装契約を持つ。
- 現行`test-execution/SKILL.md`はPlaywright MCP→CLI→Libraryの順に実行手段を選択する。案件がCLI限定を要求する場合は既存契約と競合するため、`test-execution` ownerの契約変更と既存回帰テストを別途確認する。新しい非Web Skillによる暗黙のモード切替やPlaywright既存動作の上書きは行わない。
- `regression-testing`はRun選定とActivityを、実行ownerは実測・raw結果・attempt・cleanupを所有する。
- `test-analysis`はProduct Riskとテスト重点、`test-architecture-design`（[親Plan](./2026-11-07_170134_qa-full-process-implementation.md)）はテストレベル／タイプ／方式の全体割当を所有する。
- PR #22の`feature-analysis`、`test-item-analysis`、`test-condition-analysis`等は計画段階。これらがない現在でも、既存TCと明示的な対象scopeから実行できる経路を維持する。

## 担当Skillと既存Skillへの接続

新設する担当Skillは次の2つとする。対象技術ごとにSkillを複製せず、実際のrunner固有処理は必要な接続・設定・安全確認に限定する。

- **`skills/testware-implementation/`（新設）**：既存TC・仕様Authority・有効なテストアーキテクチャの方針を受け、Playwright E2E以外の自動実行可能なテストコード／fixture／設定を作成・更新・検証し、対象repo／testware ref・実装版・参照TCとの対応を所有する。既存`test-case-design`のTCを再採番・再設計せず、製品業務コードを変更しない。Playwright E2Eの実装依頼は既存`e2e-test-implementation`へ送る。
- **`skills/testware-execution/`（新設）**：Playwright E2E以外のrunner実行と、永続testwareを作らない非ブラウザTCの直接操作・観測比較を担当する。Playwright Testを使うAPI専用テストも対象とする。対象build／認証／副作用・data／cleanup、実開始・retry・元runner結果・個別テスト識別・実行証拠を持ち、異常時には原因候補・根拠・反証・不足証拠・次の修正先を診断成果物に記録する。既存`test-execution`のブラウザ直接TC実行、`e2e-test-execution`のブラウザE2E実行、`regression-testing`のRun選定は肩代わりしない。

両Skillは別々に直接開始できる。既存testwareの実行だけなら`testware-execution`へ入り、実装・更新が必要な場合だけ`testware-implementation`へ進む。非ブラウザTCの直接実行ではtestware作成を強制しない。Playwrightの利用有無ではなく、E2E／直接ブラウザTC／非E2E自動／非ブラウザ直接実行の目的と契約に従ってownerを決める。実行結果の正本は`testware-execution`が参照する元runnerの結果と検証済み実行成果物であり、集計・欠陥追跡へ別のraw結果を作り直さない。

新Skillには既存リポジトリの`SKILL.md`、`references/`、`assets/`、必要な`scripts/`と`evals/`を用意する。既存Playwright系との正例・負例trigger、実runner／testwareに合わせた実装・結果契約、portable packaging／既存CIの検証を必須にする。

## 責務を分ける実装経路

### 1. 実装対象の特定

入力は対象TCまたは既存testware、対応する仕様Authority、対象テストレベル・タイプ、SUTのbuild／環境、実装依頼の許可範囲、対象repo／runner情報とする。

- 既存テストがあれば、該当するテストID、ファイル、runner、既存fixture・設定・CIを先に調べ、追加・更新・再利用の別を決める。
- TCから実装が必要な場合は、与えられた期待結果をテスト用の検証・assertionへ対応させる。TCN／CI／TCを実装Skillが第二の正本として再生成しない。
- ステップ・認証・実行データ・テストダブル・外部接続が不明な場合は、必要な仕様・テスト設計ownerへ戻す。実装コードの都合で期待結果を変えない。
- 対象に必要なrunnerが存在しない場合は、対象方式の導入に必要な許可・依存・検証手段を確認し、導入が許可されるまでは該当実行をblockedとする。架空のrunner・テスト結果を作らない。

### 2. テスト実装

技術固有のテスト実装と、その実装に必要な既存テスト設定・fixture・CI連携を担当する。たとえばAPIなら認証・HTTP契約・戻り値と副作用、バッチなら起動条件・終了コード・処理結果・再実行、コンポーネントなら依存の分離・契約・状態、イベントや外部連携なら非同期完了・順序・冪等性・障害時処理を、その案件の仕様と実装基盤に沿って検証する。

実装単位ごとに次を保持する。

- `testware_ref`、入力TC／テストアイテム・仕様根拠refs、対象レベル・タイプ、対象repo revision、実装による変更点、テストデータ・fixtureの前提。実装単位（ファイル／suite／個別test case）とテスト選択条件を分ける
- 利用runner・バージョン・起動方法、静的検証・実行可能性、証拠、実装状態・未実装範囲
- 既存testwareの変更履歴と撤回手順、セキュリティ・環境への影響、正式なコード変更権限

製品コードとテストコードの変更を区別する。編集前のbranch／HEAD／dirty working tree／許可path・既存変更との衝突確認を必須とし、変更後のdiffと副作用のない軽量検証を確認する。テストのassertionと有効なTC／仕様の整合は`adversarial-review`による独立したtestware品質確認を実装し、runner PASSだけで成立としない。必要な権限や品質閾値がない状態では、実装・実測結果を完了としない。

## 実行準備の正本と引継ぎ

IVEC Designerのテスト実装、およびISTQB CTFLの実装活動に含まれるテスト手順・スイート・実行順序・環境／テストデータ準備を、**既存・予定owner間の参照付き成果物**で閉じる。非Regressionのスイート管理を`regression-testing`へ移さず、新しい中央テストデータ管理Skillも無条件に作らない。

| 準備対象                                                       | 正本ownerと引継ぎ                                                                                                                                                                                                                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| テスト方式・レベル・品質特性・必要環境                         | `test-architecture-design`が必要な方式、観測・測定、環境とデータ構成の方針を保持                                                                                                                                                                                                |
| 非Regressionの実行対象・順序・依存関係                         | `test-management`が計画版・必要なTC/testware/run・スイート構成・順序の選定理由、担当・時点・開始／終了基準を保持。特定テスト基盤のsuiteファイルやコマンドは実装ownerが保持                                                                                                      |
| TCごとの前提・データ・期待結果                                 | 既存`test-case-design`のcurrent TCとsource Authorityを使用。TCなしの明示テストなら、正規の既存testware refと有効な仕様根拠を用い、架空のTCを作らない                                                                                                                            |
| データ、テストユーザー、fixture、環境設定、reset/cleanupの実装 | `testware-implementation`（Playwrightの場合は既存`e2e-test-implementation`）が、既存repoのsetup／teardown／fixtureを確認して追加・更新・再利用する。資格情報や個人データ実値を成果物に保存しない                                                                                |
| 今回runの準備・実行結果                                        | `testware-execution`（Playwrightの場合は既存実行Skill）がbuild・testware revision・権限・準備方法・必要な副作用・後処理をpreflightで確認。runner管理のsetup／fixtureが生成する実データは生成後に状態を確認し、準備成功・未確認・blockedを記録。実開始前の停止を実行済みにしない |

**実行準備の受渡し成果物**には`計画scope／対象run・TC／testware refs・revisions／実行順序と依存／環境・build／データとfixture参照／許可された副作用／preflight結果・証拠／未準備項目・担当・再開条件`を残す。データの機密値は格納しない。準備できない項目がある場合、独立対象の実行は続けられても該当runは開始不可とする。今回runのpreflightはplanやテストコードが存在するだけでは完了にしない。実データの生成時点・隔離・再利用・cleanupの詳細は[継続workflowの実行時引継ぎ契約](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md#テストデータの実行時引継ぎ再利用)に従い、runnerが所有するreset／setupをrun外で繰り返さない。

### 3. 実行前の安全確認と実行

- 対象build、環境、認証／権限、データ・前提状態、外部依存、runner、許可されたテスト操作と副作用上限、後処理、共有資源の予約／分離を固定する。
- 禁止された状態変更、秘密情報の露出、データ破壊、実環境への無承認操作を防ぐ。対象repo・runnerからの情報を未信頼データとして扱う。
- 実行開始の証拠と、開始前の未実行、実行途中の判定不能、実測に基づくPASS／FAILを区別する。retryは独立attemptとして保持し、失敗を隠さない。
- 実行結果とcleanupのsource ownerは、実際に使ったrunner／実行Skillとする。実行実績がないのに実装の存在を実行済みとして扱わない。

### 4. 結果と障害分析への引継ぎ

runner固有のraw結果、テスト実行単位と試行、対象TC/testware/item、対象build／環境／revision、開始状態、終了状態、未実行・不明の理由、evidence ref、cleanupと残存状態を読み取り用の成果物として出す。元結果を共通PASS/FAILへ再採点しない。

- **異常分析は`testware-execution`の担当**：実行ownerが確認したraw結果・runnerログ・テストデータ・対象build・環境状態・testware revisionを入力とし、SUT／テストデータ／testware／環境／runner／仕様不明／判定不能の原因候補、根拠・反証・不足証拠・確度、必要な再実行・修正の担当先を記録する。確定していない仮説を製品Defectに昇格しない。必要な追加の専門Skill分離は実装時の技術判断とし、分析ownerと成果物は必須。
- 欠陥候補・外部Issue追跡は[親Planの`defect-management`](./2026-11-07_170134_qa-full-process-implementation.md)に渡す。修正確認そのものは、既存の有効TC／testwareと実行ownerを使った再実行とし、欠陥管理Skillが新たな実行ownerにならない。
- 統合報告への受渡し形式、集計対象の完全性、重複排除は[共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)に従う。

## 静的テストと非機能テスト

- **静的テスト**：製品要求／設計／コードの意味的レビューは既存`adversarial-review`の対象を拡張し、案件で採用・認可されたlint／静的解析ツールの実行は`testware-execution`が扱う。TCを必須とせず単独開始できる。対象revision／適用規則・source／Finding・誤検出判定・修正後の再確認を保存し、`defect-management`と`test-reporting`へ引き継ぐ。完了契約は[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)を正本とする。
- **非機能テスト**：品質特性・対象scope・測定条件・有効な仕様Authority／採用基準・閾値・実測結果の対応を固定する。`test-architecture-design`が特性・レベル・手段・環境、`test-management`が基準・頻度・計画、既存専門Skillまたは確認済みrunnerのownerが実装・測定とraw evidence、`test-reporting`／`test-evaluation`が報告／継続改善を担当する。性能は負荷条件と計測値、セキュリティは許可されたscopeと検証観点、信頼性は障害条件・復旧、互換性は対象環境／版を明示し、実測条件が変わった場合は比較可能性を再判定する。
- **既存のUI/UX・WCAG**：`usability-evaluation`、`usability-inspection`、`wcag-conformance-evaluation`の既存専門判定を保持し、別品質特性の適合証明へ流用しない。
- テスト方式ごとに新Skillを複製しない。採用したrunnerに必要な接続を実装し、非E2E実行の異常分析は`testware-execution`が第一ownerとする。非Web testwareの独立品質レビュー、直接TC実行、実行結果の識別と受入条件は[テスト実行と品質契約](./2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)に従う。

## 実装順序

1. 既存Playwright、`test-execution`、`test-case-design`、`regression-testing`、テスト対象repo／CI／runnerの実契約と呼び出し元・結果ownerを確認する。
2. 対象scopeとtestwareの権限、技術別の検証・実行方式、非機能の有効な閾値、静的テスト方式を確定し、実行できない対象を判別する。
3. 非E2Eのtestware識別／安全な実装／更新を`testware-implementation`、runner実行・非ブラウザ直接TC比較・実行前preflight・元結果・cleanupと原因分析を`testware-execution`へ実装する。Playwright API専用テストとブラウザE2Eのroutingを区別する。
4. 既存TC・E2E・RegressionとのID／revision／履歴整合、非Regressionの実行対象・順序・データ／fixture・preflight引継ぎと、`qa-workflow`の直接開始・部分再開・局所blockを検証する。
5. 非E2E testwareの独立assertionレビュー、run／testware／個別テスト／TCの対応・取得完全性を確認し、`test-reporting`への読取専用投影と責務別trigger／決定論的評価／意味評価／実runner受入を実施する。未検証の実案件をfixture成功で代替しない。

## 検証・受入

- API：認証失敗、権限差、契約違反、状態変更・副作用、timeout・retry、誤ったHTTP成功、実測と仕様不一致。
- バッチ：正常／異常終了、途中失敗、二重起動、実行再開・冪等性、再実行とデータcleanup、外部依存の未完了。
- コンポーネント：境界・契約、fixture準備失敗、依存変更、隔離の失敗、既存testwareへの影響。
- 非同期／外部連携：イベント遅延・重複・順序入替、接続切断、再試行、重複副作用、監査と後処理。
- 非機能：性能の測定条件と閾値、セキュリティの許可範囲、信頼性の障害注入と後処理、互換性の対象環境別判定。測定不能・基準不明なら結果を未検証にする。
- 静的テスト：対象revision、要求からの指摘・根拠、誤検出、既存`adversarial-review`との責務重複、レビュー完了の条件。
- 共通：`testware-implementation`と`testware-execution`の単独起動・連携、非Regressionスイート／環境／データ準備と実行前readyの受渡し、異常診断と修正先、既存Playwrightとの誤発火防止、テストコード生成だけでは未実行のまま。build不一致、旧run、retry、runner失敗、権限不足、secret/PII、異常終了後cleanup、再開と再実行。
- 独立fixtureに加え、各対応技術について実在するrunner・起動・テストコード／設定・raw result・CIまたは同等の受入を示す。実機能を使用できない場合は未検証とし、全完了を宣言しない。

## 完了条件

1. `testware-implementation`が非E2Eテストコードの安全な実装／更新／軽量検証を、`testware-execution`が非E2E runner実行または非ブラウザTC直接比較・結果／cleanupを担当し、両方が単独要求・組合せ要求で機能する。PlaywrightブラウザE2Eとブラウザ直接TC実行は既存Skillを維持し、Playwright API専用テストの担当が空白にならない。
2. API・バッチ・コンポーネント・非同期連携・非機能／静的テストの要求された範囲を全て取り扱い、実行可能な対象で実runnerの受入証拠がある。欠落方式は未対応／blockedとして明示し、完了と誤認しない。
3. 実行ownerごとにテスト準備の対象scope・suite・順序・データ／環境／fixtureのrefと今回runのpreflight、個別テストと元TC／testwareの対応・取得完全性、非E2E testwareの独立assertion品質を検証する。raw結果、対象build／TC／testwareの参照、実開始・retry・判定不能・cleanupと証跡を保持し、非Playwrightの異常には第一分析ownerが診断成果物・必要な追加証拠・再実行先を記録する。統合報告は読み取り専用で投影できる。
4. 既存正本、技術別の権限・副作用、セキュリティ・秘密情報・履歴・再開、異常時のfail-closedと必要な全回帰テストを満たす。
5. この文書だけで完了を宣言せず、親Plan・[継続workflowとE2E受入契約](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)・共通契約の完了条件と合わせて判定する。Agentの起動・監視・通知はSkill外であり、モデルやCLIの種類で責務を固定しない。
