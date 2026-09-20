# テスト対象資料管理・テスト実行Skill追加Plan

このPlanは、`test-target-inspection` と `test-execution` を既存のQAワークフローへ追加する実装計画です。内容を責務境界ごとに分割し、以下5ファイルを順に読み、全体を1つのPlanとして扱います。

## 対象ブランチ

`feat/test-target-inspection-test-execution`

## 基準

- 基準branch: `main`
- 基準commit: `3510e6ffce87ba8c025ebde22f9947dbb6074f9c`
- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- Plan作成時点の正規Skill数: 14

実装開始前に最新`main`との差分を確認します。特にDraft PR #11 `feat/deterministic-test-technique-automation` が先にmergeされた場合は、同PRが変更したSkill・評価・CI契約をこのPlanの基準より優先し、本Planで固定した14 Skill / 280 trigger query / semantic 28 case等の基準値をそのまま上書きしません。PR #11でTCの`content_fingerprint`等、今回の追跡性に利用できる既存契約が導入済みなら再利用します。一方、本変更だけを理由に`test-target-inspection` / `test-execution`をPR #11のMachine Entity / runtime対象へ追加しません。

## 構成

1. [目的・責務境界・対象範囲](./2026-09-20_152700_test-target-inspection-test-execution_01_scope-and-responsibilities.md)
2. [`test-target-inspection` のSkill・Asset・成果物契約](./2026-09-20_152700_test-target-inspection-test-execution_02_test-target-inspection.md)
3. [`test-execution` のSkill・実行・結果契約](./2026-09-20_152700_test-target-inspection-test-execution_03_test-execution.md)
4. [既存workflow・E2E Skillとの統合](./2026-09-20_152700_test-target-inspection-test-execution_04_workflow-integration.md)
5. [評価・CI・実装順序・完了条件](./2026-09-20_152700_test-target-inspection-test-execution_05_evaluation-ci-implementation-order.md)

## 固定方針

1. `test-target-inspection` を新規Skillとして追加します。目的は、**生きたテスト対象から現在のUI情報とふるまいを収集し、再利用可能なテスト対象資料として管理すること**です。Skillを実行するたびに今回対象範囲の実対象を確認し、既存資料がある場合は現在も正しいかを照合します。変更がある箇所だけ更新し、変更がない箇所も今回確認済みであることを残します。実対象へ到達できない範囲はcurrentと扱いません。repo / workspaceは補助情報源です。
2. `test-target-inspection` は画面、領域、UI要素、表示状態、操作可能性、操作に対する反応、画面遷移、非同期状態、権限、データ依存等を記録します。DOM / accessibility tree等の構造情報だけでは視覚状態を確認できない場合、またはレイアウト、重なり、欠け、画像、canvas等の視覚情報が確認対象の場合は、screenshot等の画像も観測元として使用します。画像だけでroleやaccessible name等を推測せず、構造情報と視覚情報を必要に応じて併用します。
3. POM / Page Object / fixture / helperの作成・更新は`test-target-inspection`の目的にしません。対象プロジェクトに既存POM等があり、テスト対象資料との対応が後続作業に有用な場合だけ任意で参照を記録します。POMを採用していないプロジェクトでもSkillを成立させます。
4. 実対象で観測した現在の挙動は実装事実として扱い、製品の期待結果や現在有効な仕様根拠へ昇格させません。`test-case-design`はworkflow内で詳細TC・期待結果を設計・変更する責任Skillです。外部成果物やユーザー直接入力で既に明示された詳細TCの期待結果は今回の`test-execution`の実行契約として利用できますが、`SPEC`や製品期待挙動の正本へ自動昇格しません。
5. `test-target-inspection` の`assets/`は成果物テンプレートだけを保持します。案件固有資料はユーザーまたは対象案件が指定した場所へ保存します。既存資料更新では保存先が提供するSHA / revision / ETag等の条件付き更新を優先し、利用できない場合だけ保存直前の再読込・比較で古い候補の上書きを避けます。新しいlock / artifact registryは追加しません。
6. `test-execution` を新規Skillとして追加します。目的は、**人間が手動テストで操作するのと同様にAIが実対象を操作し、詳細TCを実施して、その結果を報告すること**です。TC単位で期待結果と実測結果を比較し、`PASS / FAIL / 未実行 / 判定不能`と観測内容、証跡、後処理 / cleanup、残存状態を含むテスト実行報告を出力します。
7. `test-execution` の基本実行手段は、利用可能なPlaywright MCP等の対話的なbrowser操作です。対象環境や作業内容に応じてPlaywright CLIやPlaywrightコード実行も使用できます。今回の実行だけに必要な一時的なPlaywrightコードは`test-execution`内で最小限生成・実行できますが、将来も維持するrepo内E2Eコードとして保存・更新する場合は既存`e2e-test-inspection` / `e2e-test-implementation`の責務を使います。既存repo E2Eを正式なrunner契約で実行する場合は既存`e2e-test-execution`を再利用します。
8. `test-execution` はTCの手順に沿ってAI自身が操作・観測します。DOM / accessibility tree等で判定できる情報はそれを利用し、UI崩れ、重なり、欠け、画像、canvas、視覚的な表示状態等、構造情報だけで判断できない期待結果はscreenshot等の画像を使って確認します。画像判断は期待結果または明示した確認観点へ結び付け、見た目だけから仕様を創作しません。
9. `test-execution`は結果報告までを責務に含めます。TC結果だけでなく、必要な手順・観測、実測結果、判定根拠、未実行 / 判定不能理由、画像を含む証跡参照、TC後処理、実行時cleanup、残存状態を整理してユーザーへ報告します。`e2e-test-reporting`は既存E2E runnerのrun / resolved primary / attempt等の詳細報告が別途必要な場合だけ使用し、一般的なTC実行報告の必須依存にはしません。
10. 今回要求されたTC集合は実行開始前に入力側の既存一意識別子から固定します。1つの`test-execution`成果物は1つのTC入力元 / snapshotを対象とします。実行開始後にTC追加・除外または実行手段変更があった場合は旧成果物を理由付きで閉じ、必要なcleanup後に別成果物 / versionとして開始します。外部 / ユーザー直接入力TCへ正式TC IDを創作しません。
11. `test-target-inspection` / `test-execution`の画像・trace・screenshot・page snapshot等はsecret・個人データ・機密情報を含み得るため、必要最小限だけ取得し、自動共有・commit・転載しません。副作用の最大回数は許可された操作scope全体で累計し、TCごとにリセットしません。
12. 既存`e2e-test-execution`、`e2e-test-result-analysis`、`e2e-test-reporting`は削除・汎用化しません。既存repo E2Eの安全なrunner実行、原因分析、Playwright固有報告という責務を維持します。
13. `evals/deterministic/validator.py`は評価専用とし、runtime validatorとして呼び出しません。実browser操作、画像判断、保存競合防止等のruntime挙動は、実Agent / 実対象を利用できる場合のsmokeで確認し、利用できない場合は未検証として明示します。
14. 現`main`基準では14 Skillを16 Skillへ増やします。既存の「train 12 / validation 8 query、semantic 2 case / Skill」契約を維持する場合、この変更単独ではtrigger queryは280→320、semantic caseは28→32になります。実装開始時に基準branch側の契約が変わっていれば、その時点の正本に合わせて再計算します。
15. このPlanではPlanファイル以外を変更しません。Skill本体、Asset、validator、CI、README、EVALSの実装は後続作業で行います。
