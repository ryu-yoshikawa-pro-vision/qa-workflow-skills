---
name: e2e-test-execution
description: 既存または実装済みのPlaywright E2Eを指定されたテスト環境へ安全にローカル実行し、run・logical primary・resolved primary TestCase・attempt・証跡・cleanupを構造化して収集するSkill。既存E2Eの実行だけを要求された場合にも直接開始できる。
---

# E2Eテスト実行

## 実行契約

1. 実行前に`references/guidance.md`を読み、Playwrightのraw値域、preflight block、webServer ownership、結果・cleanup契約に従います。
2. 既存E2E実行のみなら直接開始できます。inspectionを利用できる場合は再利用しますが、本Skill自身が今回の実行に必要な安全確認を行います。
3. 指定URL、対象origin、実際のpackage script / task / wrapper / pre-post chain、Playwright project、対象testへ効く実効設定、依存、setup / teardown、fixture / hook、必要な認証・開始状態、副作用の許可範囲と最大回数、cleanup方法、reporter、output、snapshot、cleanupを確認します。これらの実行開始前必須情報を確定できない場合はrunnerを開始せずブロックします。
4. runner管理のdependency / globalSetup / fixture / hook / webServer / teardownと、run外で確認済みの準備 / cleanupを区別し、二重実行しません。webServerなし、未確認 / 確認不能、確認済みの設定ありを区別し、設定ありならserver集合全件をownership表へ記録します。webServer未確認 / 確認不能ではrunnerを開始せず、今回runが所有していないprocessをcleanup目的で終了しません。automatic fixture、worker-scoped automatic fixture、worker再生成も副作用回数へ含めます。
5. retries、repeatEach、workers、parallel / serial、maxFailures、globalTimeout、filter、focus、project dependenciesを確認します。通常runの実効設定をPASS目的で変更せず、診断runは正式結果と分離します。
6. 高リスク副作用の最大回数が合理的に確定できない場合は推測せず該当範囲をブロックします。productionの可能性、削除、メール、通知、決済、権限変更、共有データ更新等は許可範囲を確認します。
7. terminal表示だけを正本にせず、既存machine-readable reporterまたは標準JSON等を安全に取得します。reporter / Playwright API / process観測が直接提供したraw factと、process exit code / 導出値を区別し、提供されないraw値を推測補完しません。preflightでブロックした場合はrunner未開始・artifact未生成を正当な結果として記録し、FullResult.status、成功exit code、reporter由来の具体的run-level error、resolved / attempt、runner管理cleanup成功を残しません。run外準備のcleanupだけは実行主体を明示して記録できます。stale artifactを今回結果として利用しません。
8. logical primary対象、resolved primary TestCase、各attempt、dependency / teardown testを分けます。execution成果物を開始した以上、logical primaryは最低1件記録します。retryはresolved件数へ加算しません。logical primaryがresolved 0件なら未実行 / 解決不能理由を残します。
9. runnerを開始した場合だけ、今回runで生成・更新されたresult artifactを確認し、古いartifactを再利用しません。trace、storageState、HTML report、network、stdout等は機密情報を含み得るため自動共有・commit・転載をしません。
10. runner管理分とrun外処理を行単位で分け、cleanupの成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態と残存副作用を記録します。runner未開始時のrunner管理cleanup成功は矛盾として扱い、run外cleanup成功は対応するrun外準備がある場合に許容します。必要cleanupが未確認のまま安全な完了や機械的再実行へ進みません。
11. 原因分析は行いません。異常、未実行、cleanup問題、明示分析要求は検証済み結果を`e2e-test-result-analysis`へ渡します。

## 出力

`assets/output-template.md`を基本形として、実行入口chain、実効条件、webServerごとのownership、run全体status / process exit / run-level error、logical primary / resolved primary / attempt、artifact鮮度、working tree差分、証跡、cleanup、残存副作用、ブロックを記録します。preflight blockでもlogical primaryを0件にせず、未実行理由で閉じます。
