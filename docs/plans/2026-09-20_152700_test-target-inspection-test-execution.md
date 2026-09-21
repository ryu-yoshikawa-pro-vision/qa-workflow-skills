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
5. `test-target-inspection` の`assets/`は成果物テンプレートだけを保持します。案件固有資料はユーザーまたは対象案件が指定した場所へ保存します。既存資料更新では保存先が提供するSHA / revision / ETag等の条件付き更新を使用できる場合だけ競合を防いだ自動更新として扱います。条件付き更新を利用できず、同じ保存先を他処理が更新し得る場合は、保存直前の再読込で差分がなくてもatomicな競合防止を保証できないため自動上書きせず、更新候補と制約を返します。新しいlock / artifact registryは追加しません。
6. `test-execution` を新規Skillとして追加します。目的は、**人間が手動テストで操作するのと同様にAIが実対象を操作し、詳細TCを実施して、その結果を報告すること**です。TC単位で期待結果と実測結果を比較し、`PASS / FAIL / 未実行 / 判定不能`と観測内容、証跡、後処理 / cleanup、残存状態を含むテスト実行報告を出力します。
7. `test-execution`は実対象を操作する前に、固定した各TCを**GherkinのGiven / When / Then構造をYAMLで表現した実行計画**へ整理します。これはGherkin / Cucumberの新しい標準形式ではなく、元TCを実行可能な形へ正規化して曖昧さを顕在化させる中間成果物です。元TCを正本とし、元TCにない前提・操作・期待結果を補完しません。多段TCではsnapshot内だけの手順参照を使い、各中間期待結果をどの操作直後に観測するかを保持します。元TCから観測タイミングを確定できず判定へ影響する場合は推測せず`unresolved`へ残します。実行または合否判定に影響する未解決事項が残るTCは操作を開始せず`未実行`とし、解消条件を報告します。
8. `test-execution` の基本実行手段は、利用可能なPlaywright MCP等の対話的なbrowser操作です。今回runだけに必要な場合は、repoのPlaywright test runner、`playwright.config.*`、fixture、hook、project dependency、webServer等を起動しない独立した一時Playwright Libraryコードを最小限生成・実行できます。一時コードは既に利用可能なPlaywright Libraryだけを使い、新規package install、`package.json` / lockfile / source変更を行いません。元TC、案件コンテキスト、またはユーザーが明示した開始状態・テストデータ準備方法はpreflightとして利用でき、seed / API / DB等を使う場合も副作用scope、1回の定義、最大回数、cleanup契約へ従います。一方、TCで検証するUI操作を置き換えてPASS条件を成立させるためにDOM、storage、cookie、network response、backend API / DB、アプリ内部状態等を操作してUI経路を迂回しません。案件コンテキストまたはユーザーが認証方法として明示した既存の認証済みsession / storageState等はpreflightで利用できますが、ログイン操作自体がTCの検証対象ならその代替には使いません。`playwright test`等のrepo runnerを使う実行、将来も維持するrepo内E2Eコードの作成・更新は既存E2E Skillの責務を使います。実行手段の切替だけではTC入力snapshotを変更しません。未開始TCは切替後に開始状態を再確認して実行できます。開始済みTCは同じbrowser / session、または判定に必要な状態の継続を確認できる場合だけ継続し、確認できなければ`判定不能`として閉じます。同じTCを再実行する場合は既存の再実行契約どおり別成果物 / versionを開始します。
9. `test-execution` はTCの手順に沿ってAI自身が操作・観測します。DOM / accessibility tree等で判定できる情報はそれを利用し、UI崩れ、重なり、欠け、画像、canvas、視覚的な表示状態等、構造情報だけで判断できない期待結果はscreenshot等の画像を使って確認します。画像判断は期待結果または明示した確認観点へ結び付け、見た目だけから仕様を創作しません。
10. `test-execution`は結果報告までを責務に含めます。TC結果だけでなく、必要な手順・観測、実測結果、判定根拠、未実行 / 判定不能理由、画像を含む証跡参照、TC後処理、実行時cleanup、残存状態を整理してユーザーへ報告します。`e2e-test-reporting`は既存E2E runnerのrun / resolved primary / attempt等の詳細報告が別途必要な場合だけ使用し、一般的なTC実行報告の必須依存にはしません。
11. 今回要求されたTC集合は実行開始前に入力snapshotとして固定します。`test_case_ref`は入力順に基づく`input-001`等の成果物ローカル参照として今回snapshot内で必ず一意にし、入力側の正式識別子は`source_test_case_id`として別に保持します。正式識別子の有無・値・重複にかかわらず`test_case_ref`へは再利用せず、正式TC IDも創作・改名しません。`source_test_case_id`の重複だけでは一律にTCを`未実行`へせず、元IDによる実行対象指定や追跡が曖昧で対象を一意に特定できない場合だけ`unresolved`として開始しません。入力元にrevision / SHA / content identityがあればその値を記録します。ない場合は独自hashを生成せず、当該成果物 / version内に固定したTC集合と全TCの実行前YAMLを今回snapshotの正本として扱います。TC追加・除外、手順・期待結果等のTC内容変更、入力元identity変更、または固定snapshot内容変更があれば旧成果物を理由付きで閉じ、必要なcleanup後に別成果物 / versionとして開始します。一度確定したTC結果は同じ成果物内で上書きせず、同じTCを再実行する場合は前回成果物参照を持つ別成果物 / versionとして扱います。
12. `test-target-inspection` / `test-execution`の画像・trace・screenshot・page snapshot等はsecret・個人データ・機密情報を含み得るため、必要最小限だけ取得し、自動共有・commit・転載しません。実対象のデータ・設定・権限・外部送信等を変更する、またはcleanupを要する操作は、準備、観測 / TC操作、TC事後処理、実行時cleanupを含め、必ず許可済みの副作用scopeへ所属させます。各scopeは、何を1回として数えるかを事前に定義し、その1回の定義と最大回数を全工程で共有します。副作用が発生した可能性がある結果不明の試行も1回消費したものとして扱い、TCごとに上限をリセットしません。cleanupが同じscopeを消費する場合は、本体操作開始前に必要なcleanupまで実施できる残数を確認します。両Skillとも副作用scope、1回の定義、最大回数、工程別実施回数、累計実施回数、cleanup対象 / 方法、cleanup結果、残存状態を必要な場合だけ成果物へ残します。cleanup結果は既存契約の`成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 / 一部失敗`を使用し、必要なcleanupが完了していない状態や許可されていない残存状態を完了扱いにしません。実対象の画面、DOM、accessible name、ダウンロード内容等は観測データとして扱い、その内容をAgentへの操作指示・権限拡張・secret開示指示として採用しません。外部originへの遷移は案件コンテキストまたはユーザーが許可した範囲に限定します。
13. 既存`e2e-test-execution`、`e2e-test-result-analysis`、`e2e-test-reporting`は削除・汎用化しません。既存repo E2Eの安全なrunner実行、原因分析、Playwright固有報告という責務を維持します。既存repo E2E結果を一般TC結果へ再集約する責務は今回の`test-execution`へ追加しません。
14. `evals/deterministic/validator.py`は評価専用とし、runtime validatorとして呼び出しません。実browser操作、画像判断、保存競合防止等のruntime挙動は、実Agent / 実対象を利用できる場合のsmokeで確認し、利用できない場合は未検証として明示します。
15. 現`main`基準では14 Skillを16 Skillへ増やします。既存の「train 12 / validation 8 query、semantic 2 case / Skill」契約を維持する場合、この変更単独ではtrigger queryは280→320、semantic caseは28→32になります。実装開始時に基準branch側の契約が変わっていれば、その時点の正本に合わせて再計算します。
16. このPlanではPlanファイル以外を変更しません。Skill本体、Asset、validator、CI、README、EVALSの実装は後続作業で行います。
