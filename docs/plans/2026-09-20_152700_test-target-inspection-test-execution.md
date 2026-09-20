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

1. `test-target-inspection` を新規Skillとして追加します。通常のテスト分析・設計フローの必須工程にはせず、実対象の構造・操作・状態等を確認して再利用可能なテスト対象資料を作成・更新する必要がある場合だけ使用します。通常は実対象確認を正本とし、repo / workspaceは補助情報源として使用します。ユーザーがrepoだけの調査を明示した場合は、その限定範囲の成果物として扱います。
2. `test-target-inspection` の成果物はPOMそのものに限定しません。画面、領域、UI要素、状態、遷移、権限、データ依存、非同期状態、観測方法を中心に、テスト設計・実装・実行で参照可能な資料とします。既存Page Object / fixture / helper等のrepo対応は、確認済みで後続作業に有用な場合だけ任意で記録し、必須の正規表や鮮度管理対象へ広げません。
3. 実対象で観測した現在の挙動は実装事実として扱い、製品の期待結果や現在有効な仕様根拠へ昇格させません。`test-case-design`はこのworkflow内で詳細TC・期待結果を設計・変更する責任Skillです。外部成果物やユーザー直接入力で既に明示された詳細TCの期待結果は今回の`test-execution`の実行契約として利用できますが、`SPEC`や製品期待挙動の正本へ自動昇格しません。
4. `test-target-inspection` の`assets/`は成果物テンプレートだけを保持します。案件固有のテスト対象資料を`qa-workflow-skills`リポジトリへ自動保存しません。永続化先はユーザーまたは対象案件が指定したパス / リポジトリを使用し、指定・書込能力がない場合は永続更新を実施済みと扱いません。既存資料の更新では保存先が提供するSHA / revision / ETag等の条件付き更新を優先し、利用できない場合だけ保存直前の再読込・比較で古い候補の上書きを避けます。永続保存・更新自体がユーザー要求に含まれる場合、保存成功またはユーザーによる保存不要への要求変更までは完了扱いにしません。`qa-workflow`利用時の案件コンテキスト`既存QA成果物`欄の更新は`qa-workflow`が担当し、`test-target-inspection`は保存済み成果物参照・範囲・鮮度を返します。新しいlock / artifact registryは追加しません。
5. `test-execution` を新規Skillとして追加し、詳細テストケースを実行して期待結果と実測結果を比較し、TC単位の結果を確定する責務を持たせます。自動化対象かどうかを入力条件にしません。詳細TCは`qa-workflow`成果物だけに限定せず、外部成果物やユーザー直接入力も受け付けます。ただし今回実行する各TCは入力側で一意に識別できる必要があり、既存TC IDや外部システムの一意識別子をそのまま使用します。`test-execution`自身が正式TC IDを創作しません。今回の`TC識別子`は実行入力上の識別子として扱い、外部IDを既存E2E成果物の`TC ID`へ書き換えて流用しません。既存`TC → E2E実装`対応が`TC ID`を持つ場合は、今回識別子と既存TC IDが同一TCを指すことを別途確認します。
6. 現スコープの実行方式は`AI直接操作`と`自動実行`です。`AI直接操作`は利用可能なbrowser / computer操作能力で実対象UIを操作・観測できるTC、`自動実行`は既存Playwright E2Eの検証済み実行成果物をTC判定へ利用する方式です。API / DB等の専用実行方法やrunnerを本変更で新設しません。実行方式はTC単位で決め、同一成果物内で混在可能とします。`test-execution`は固定TC集合、方式、TCと既存E2E実装参照の対応、最終TC結果を所有しますが、Skill間routing、Playwrightのlogical primary解決、preflight、run分割、runner実行は所有しません。自動実行に新しいrunが必要な場合は`qa-workflow`が既存`e2e-test-execution`へroutingし、Playwright固有判断は同Skillの既存契約へ委ねます。方式未指定時は、currentなE2E対応が存在するだけで`自動実行`を選ばず、そのE2EがTC判定に必要な期待結果を十分検証できることを実行前に確認できる場合だけ自動実行候補とします。今回新しい実行を要求されている場合は過去結果だけで代替しません。新しい汎用browser framework、runner、run registryは追加しません。
7. 既存`e2e-test-execution`は削除・汎用化しません。Playwright固有のproject、retry、repeat、reporter、raw result、artifact、process ownership、cleanup等の契約を維持し、`test-execution`へ移しません。
8. `test-execution` のTC結果状態は`PASS / FAIL / 未実行 / 判定不能`を基本とします。`ブロック中`はTC結果ではなくSkill / workflow状態として扱います。実行基盤・認証・環境・準備の失敗を製品の`FAIL`へ変換せず、実測できない期待結果を推測でPASSにしません。TC結果、TCに定義された事後状態 / 後処理、実行時cleanup、Playwright runner管理cleanupを混同しません。
9. 既存E2Eをraw runner結果だけ取得する要求は、従来どおり`e2e-test-execution`から直接開始可能とします。TCの実行結果判定を要求された場合だけ`test-execution`へ接続します。異常、未実行、run-level error、cleanup失敗 / 未確認は現行E2E契約どおり`e2e-test-result-analysis`を経由し、その分析後に必要なTC判定を`test-execution`で行います。`e2e-test-result-analysis`が要求する診断runは正式TC実行と分離し、診断runだけを新しいPASS根拠として正式結果へ置き換えません。
10. 今回要求されたTC集合と`test-execution`結果集合の完全性は、`test-execution`の`SKILL.md` / guidanceで定義する最終出力自己検証で確認します。`evals/deterministic/validator.py`は評価専用とし、runtime validatorとして呼び出しません。範囲指定で依頼された場合も、実行開始前に入力上の既存一意識別子から今回の具体的なTC集合へ解決して母集団を固定します。1つの`test-execution`成果物は1つのTC入力元 / snapshotを対象とし、異なる入力元を同時に扱う場合は別成果物 / versionへ分けます。実行開始後は固定集合を変更せず、ユーザーがTC追加・除外や方式変更を求めた場合は、旧成果物の未開始TCを`未実行`、開始済みだが判定前のTCを必要に応じて`判定不能`としてcleanup後に履歴として閉じ、変更後要求を別成果物 / versionとして開始します。複数TCを一意に識別できない場合は実行開始前に該当範囲をブロックします。内部QA成果物TCで既存`TC → E2E実装`対応の欠落・陳腐化が問題なら既存`coverage-analysis`（対象: `TC → E2E実装`）へ戻します。外部 / ユーザー直接入力TCは内部QA成果物へ自動変換せず、必要な対応や期待結果を入力元・ユーザーから解消できない場合はその範囲をブロックします。内部QA workflowへの取込が明示された場合だけ既存設計Skillへroutingします。`coverage-analysis`へ新しい`TC → テスト実行結果`用途は追加しません。
11. `test-target-inspection`で今回確認すべき範囲に`未確認`または`確認不能`が残る場合は、repo情報だけで実対象確認済みとせず、要求成果物を完成できない範囲をworkflow上`ブロック中`として扱います。`未確認`は今回確認対象だがまだ確認していない状態、`確認不能`は今回確認対象だがアクセス・権限・環境等により確認できない状態とし、要求範囲外を`未確認`へ混ぜません。成果物の観測事実とSkill完了状態を分離します。
12. 現`main`基準では14 Skillを16 Skillへ増やします。既存の「train 12 / validation 8 query、semantic 2 case / Skill」契約を維持する場合、この変更単独ではtrigger queryは280→320、semantic caseは28→32になります。実装開始時に基準branch側の契約が変わっていれば、当時の正本に合わせて再計算します。
13. `test-target-inspection`は対象製品コード、Page Object、fixture、helper、既存テストコードを変更しません。永続書込を行う場合も、ユーザーまたは案件が指定したテスト対象資料だけを更新します。`test-target-inspection` / `test-execution`が取得するscreenshot、page snapshot等の証跡は必要最小限とし、secret・個人データ・機密情報を含む可能性がある証跡を自動共有・commit・転載しません。AI直接操作の副作用上限は許可された操作scope全体で累計し、TCごとに上限をリセットしません。
14. このPlanではPlanファイル以外を変更しません。Skill本体、Asset、validator、CI、README、EVALSの実装は後続作業で行います。
