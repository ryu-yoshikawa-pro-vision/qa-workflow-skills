# テスト実装・実行方式・品質確認の実装契約

## 対象と責務

本書は[非Webテスト実装・実行Plan](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)の実行方式、testware変更前確認、テスト結果の対応付け、独立レビューの詳細契約を定める。**Playwrightを使用しているかだけでは実行ownerを決定しない**。

- `e2e-test-implementation`／`e2e-test-execution`／`e2e-test-result-analysis`：既存のリポジトリE2Eテスト。
- `test-execution`：既存の詳細TCをブラウザで手動テスト相当の方法により操作・観測する実行。
- 新設予定`testware-implementation`：**E2E以外**の保存可能な自動テストコード・fixture・設定の作成・更新。Playwright Test製のAPIテストもここに含める。
- 新設予定`testware-execution`：**E2E以外**の自動テストrunner／実ツールの実行、またはTCに基づく非ブラウザ直接操作・観測比較。Playwright TestのAPIテストもここに含める。
- `adversarial-review`：自動生成・更新した非E2E testwareの期待結果・assertionの独立レビューを拡張する。正式TC／CIのcoverage判定は`coverage-analysis`の正本を使用する。
- `regression-testing`：選定とActivity参照のみ。非E2Eの実行ownerにはならない。
- 元run結果は実行owner、欠陥候補・外部Issueは`defect-management`。診断によって元結果のPASS／FAILを再採点しない。

## 1. 実行方式と担当ownerの決定

依頼内容を、テスト目的・元となるTC／testware・実行操作・runnerの実能力・保存の要否で分類する。

1. リポジトリへ残すPlaywrightブラウザE2E：既存E2Eのinspection→implementation→execution→result analysis／reporting。
2. 詳細TCのブラウザ直接操作（repoへE2E実装を残さない）：既存`test-execution`。
3. 保存する非E2E自動テスト（Vitest、API、component、batch、イベント、**Playwright Testを使うAPI専用テスト**等）：必要時に`testware-implementation`、実行時に`testware-execution`。
4. **自動テストコードを作成しない非ブラウザTC直接実行**：`testware-execution`の直接観測・期待結果比較で扱う。必要な外部操作と検証能力がない場合は実行前にblocked。テストコードの新規作成を完了の前提にしない。
5. TCなしの既存testware実行：有効なtestware参照・採用基準・対象scopeを明示して実行し、正式TCを創作しない。
6. 専門的な静的解析ツール実行と人間／Agentによる意味的レビューは[静的テスト・改善契約](./2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)で区別する。レビューを「実行できるtestwareがある」と偽らない。

一つの対象が複数方式に該当する場合は、**依頼された活動の正本を持つowner**が担当する。同じrunnerの使用を理由にraw結果を別ownerへ再保存・二重集計しない。所有関係が確定できない範囲はblockedとし、適当なE2E扱いへ格下げしない。

### 直接観測・比較の成果物

非ブラウザの単発TC実行では、実開始前に`TC revision／仕様Authority／対象build／環境・認証／許可された副作用・cleanup／観測方法／必要な証跡`を固定する。各期待結果に対して、実際のレスポンス、データ変化、出力、イベント等から得た観測値、比較結果と根拠、観測不能項目を記録する。

- 実開始前の停止は未実行。実開始後に必要な観測が不足すれば判定不能。実測で期待結果と相違すればFAIL。
- HTTP 200、終了コード0、runner自体の成功だけで、本文・永続化データ・副作用の期待結果をPASSにしない。
- 操作やcleanupが状態不明なら再試行前に元操作の状態・残存状態を照合する。実行を再開できないときも、確認済み実測を消さない。
- 出力はTC実行結果と診断成果物を分ける。元resultのownerと修正・再実行先を明示する。

## 2. testware変更前・変更後の安全確認

新設`testware-implementation`は、既存`e2e-test-implementation/references/guidance.md`の技術非依存部分を再利用する。安全確認を別の共通frameworkに複製しない。

### 書込み前

1. 対象repo・branch・HEAD／base、検証用workspaceの作業ツリー状態と権限、許可対象パス／ファイルを取得する。inspection時点のsnapshotと現在状態を比較する。
2. 対象ファイル・fixture・設定・lockfileの未commit変更、他Agentの更新、重複する編集・競合を検査する。**競合する変更は上書きしない**。独立した利用者変更は保存する。
3. 既存テスト用のsetup、helper、データ・認証、テスト実行入口・CIを確認する。製品の業務コードと正式仕様を実装都合で変更しない。
4. 実行予定のlint／typecheck／テスト列挙／検証コマンドについて、script連鎖と副作用・外部I/O・本実行・cleanupの要否を調べる。軽量検証の名目で危険なscriptを実行しない。
5. 対象リポジトリに書込権限がない、競合がある、変更後の復元条件が確保できない、必要な環境・secretの取得条件が満たせないときは**対象の編集をblocked**にする。

### 書込み後

1. 変更差分が許可されたテスト対象・fixture・設定に限定され、元のユーザー変更を消していないことを確認する。
2. source／TC／testwareの参照と版、assertion、runner設定の変更点、前提データ・cleanupと再実行条件を記録する。
3. 安全が確認できた静的・軽量検証で実装の構文／起動可能性を確認し、**実runner未開始なら「実行済み」にしない**。
4. 検証失敗や中断では、対象diffと元の状態を照合し、ユーザーの編集を破棄せず、未確定の変更・復旧先を記録する。強制reset、無断上書き、破壊的cleanを禁止する。

### 同時編集と変更確定時の競合防止

書込み前のHEAD・working tree確認、operation単位のclaim、成果物保存のCASは、**testwareファイルへの変更確定時の競合検出を代替しない**。共有ファイルの変更は、事前検査から実際の反映まで整合性を保証する。

**変更対象**：`skills/testware-implementation/`（新設予定）、既存`e2e-test-implementation/references/guidance.md`の共通安全条件、`skills/qa-workflow/scripts/artifact_graph.py::reserve_shared_resource()`を使う呼出し元、変更記録と回帰fixture。既存の排他手段を再利用し、新しい汎用lock managerは作らない。

1. **変更単位の固定**：作業開始時に対象repo・branch／HEAD、対象path、変更前ファイル内容hash、既存dirty状態、許可された差分・operation refを記録する。作業中に追加された依存ファイル・設定も変更対象として再確定する。ユーザー／他Agentの変更を今回の差分と混同しない。
2. **隔離workspaceでの編集**：各Agentは独立worktreeまたは隔離作業コピーで生成・検証する。共有branchへの反映直前に対象branchのHEADと対象ファイルの最新内容を再取得し、記録した前提との一致を確認する。競合時は反映せず、先行変更を取り込むか再計画して再検証する。非fast-forward更新、force push、強制resetによる上書きは行わない。
3. **共有workspaceの直接編集**：隔離できず同一repo／pathを共有する場合は、**関係する書込主体が同じ予約機構を守ること**を確認したうえで、対象資源に対する排他予約を編集前に取得し、編集完了／中断まで維持する。`reserve_shared_resource()`等で予約を取得できない場合は対象scopeをblockedとする。予約は変更前内容の照合を省略する理由にならない。予約の安全な解放は既存native conditional releaseに従う。
4. **第三者更新の検出**：予約を使わない外部書込主体が存在する場合、予約だけで完全な競合防止を保証しない。保存・commit時の期待HEAD／期待内容に基づく条件付き確定を必須とし、条件を満たせない共有更新経路は使用しない。ローカルファイルのwriteとGitのcommit／pushで保証される原子性を混同しない。
5. **操作の重複と復旧**：`claim_mutable_operation()`の`workflow_ref`・`operation_ref`は同一操作の重複防止に使用する。**別operation IDの同一path編集は競合し得る**ため、資源予約または反映時の競合検出を別途行う。中断後はclaim・予約・作業差分・変更先HEAD・ファイル内容を再読込し、内容不明のまま再編集・再反映しない。
6. **確定後の検証**：実際の反映先からHEAD・対象ファイル・変更差分を再読込し、意図したassertion／fixture／設定と他者変更の保持を確認する。保存されたtestware ref・source revision・変更証拠を下流へ渡す。反映は成功してもreadbackできない場合、確定済みと推測せず、元のoperation refから調査する。
7. **権限境界**：作業用copy／branchの使用許可と共有branchへの変更反映許可を区別する。製品本体・正式仕様の変更権限はこのSkillに含めない。

**必須受入**：

- 同一ファイルに対する2セッションが同じpreflightを通過した後、交互に編集・反映する。先に確定した差分を保持し、後続の古い前提による確定は競合として拒否する。
- 異なるファイルへの独立変更は不要にブロックしない。ただし共通設定・lockfileへ双方が触れた場合は競合とする。
- shared workspaceで予約の競合・取得失敗・異常終了・別operationによる更新を検証する。隔離worktreeでは並行commit・branch更新・共有先反映直前のHEAD変化を検証する。
- dirty working tree、既存の未commit変更、検証中断、確定応答消失、対象外pathを組み合わせ、ユーザー変更の欠落・二重編集・無断上書きがないことを確認する。
- 既存E2E testware実装の安全条件にも同じ競合保証が適用され、新設非E2E側だけ安全になって既存経路が未保護のまま残らないことを確認する。

## 3. 非E2E testwareの独立品質確認

runnerのPASSとテスト目的の検証成立を分ける。生成・更新したtestwareをテスト完了の根拠とする前に、**実装ownerとは独立した反証レビュー**を行う。

1. `adversarial-review`に非E2E testwareレビュー入力を追加し、`TC／TCN／CI／期待結果／仕様Authority／testware refとrevision／assertion／必要なfixture`を受け取る。TCなしなら明示対象・採用基準と根拠を受ける。
2. 各期待結果と実コードの実際のassertion／観測・検証処理を対応付ける。常に真となる検証、assertion欠落、誤った期待値、重要な分岐未検証、テストデータが必ず期待値を満たすだけの誤陽性を検出する。
3. 既存`coverage-analysis`が保持するTR／TCN／CI／TCの閉鎖性と、**testwareがTCを正しく実装したこと**の確認を混同しない。前者は既存正本、後者は独立testwareレビュー成果物として引き継ぐ。
4. レビュー不能・重大な不整合・現在性未確認が残る場合、runnerのraw PASSはそのまま保持し、**テスト設計を検証したとする品質ゲートは未完了**とする。元runnerのPASSを書き換えない。
5. E2E review／coverageの既存経路と非E2Eの新経路を互いに回帰させず、同じ対象を複数ownerが重複レビューして正本を増やさない。

## 4. runner単位・TC・実行結果の対応と完全性

`testware_ref`と`TC ref`、実行単位、runnerが返す個別結果を別の識別対象として保持する。ファイル単位の成功から、その中の個別テストの完了を推測しない。

### 取得する情報

- 計画上のテスト集合：`test-management`のscope、対象TC/testware、テスト実行方式、runner選択条件と必要run。
- testwareの識別：repo／source commit、repo相対パス、suite／title path、テスト用fixtureの参照。ファイルのみ・テストケース単位・suite単位を明示する。
- runnerの選択集合：実コマンド／filter／環境、実際に選択・列挙されたテスト集合、runner version、実run／attempt、取得完全性とraw結果。
- 個別対応：選択されたテストごとに元TCまたは明示testware、実測・skip／todo／timeout・retry／診断・cleanupと証拠を関連付ける。

### 固定commitでのVitest受入

主要受入対象は`qa-training-store`の実施開始時に固定したSHAと実在するVitestテストとする。新しいテスト参照の汎用フレームワークは先行実装せず、**Vitestで実際に取得できる結果形式と選択条件**を使って対応付ける。runner内部の一時的IDだけで永続識別せず、repo revision、ファイル、テスト名／階層、選択条件を確認する。

- 一つのファイルに複数のテスト、同名テスト、パラメータ化テスト、部分選択、skip／todo、timeout、retry、ファイル移動／改名を検証する。
- 計画された個別テストの一部が未実行・結果未取得であれば、全件実行・全PASS・100%としない。旧commitの結果を現行テストに自動対応させない。
- Vitestのtest-control API境界のテスト（`tests/contracts/test-api.test.ts`）は**一般的なHTTP APIテストの受入証拠ではない**。実HTTPの認証・レスポンス本文・副作用・timeoutを検証する独立fixtureを用意し、実製品の受入結果とは別に記録する。
- 必要な技術（バッチ、イベント、非機能等）が固定製品にない場合も独立fixtureを利用し、fixture成功を製品側の実機能受入に加算しない。

## 5. 実行異常の分析と報告

- 非E2Eの実行・直接観測：`testware-execution`が第一分析owner。元runの実測、raw結果、対象build、testware／TC revision、データ、環境／runnerを確認し、原因候補・確度・不足証拠・修正先を診断成果物に保持する。
- ブラウザ直接TC実行：`test-execution`が第一分析owner。元PASS／FAIL／判定不能を維持し、仕様Authority、期待結果、開始状態・データ、環境・操作、追加の許可された観測から、原因仮説・反証・追加確認先を記録する。TC外の状態変更を診断のために無断実行しない。
- 既存E2E：`e2e-test-result-analysis`が原因分析。Playwright以外の結果をE2Eの報告正本へ転記しない。
- 製品欠陥が確定していない結果は`defect-management`で正式欠陥へ自動昇格しない。元実行ownerで原因確認できない仮説の追加調査だけを既存`exploratory-testing`のinvestigationへ引き継ぐ。
- 統合報告は各sourceの取得範囲・元結果・判定不能・cleanup・診断・未処理を**読取専用で集約**する。

## 必須受入ケース

1. Playwright TestのAPI専用テスト、既存ブラウザE2E、Vitest component／integrationが別の実行ownerへ一意にroutingされる。
2. 永続testwareなしでHTTP 200＋本文不一致、バッチ終了コード0＋出力不一致、観測不能の副作用を判定し、PASS・FAIL・判定不能を区別する。
3. 非E2E testwareにassertion欠落・常に真となるassertion・誤期待値・必要分岐の欠落を混入し、実行raw PASSとは独立して品質不適合を検出する。
4. dirty working tree・同一ファイルの並行変更・対象外パス・危険なpackage script・編集途中中断で、上書きや不要な実行を拒否する。隔離worktree／共有workspaceの各反映経路で、preflight直後に他セッションが変更したファイルの更新競合を拒否できる。
5. Vitestの部分実行、skip／todo、同名・移動・改名、結果欠落・重複attemptの下で計画上の母集団と実績を正しく照合する。
6. 一般TC・非E2E・E2Eの失敗について、元runを変更せず、担当ownerが原因仮説・追加証拠・次の修正先を残す。
7. 新実装側の直接開始と既存E2EのTCあり／なし／実行のみの経路が互いに誤発火・回帰しない。
