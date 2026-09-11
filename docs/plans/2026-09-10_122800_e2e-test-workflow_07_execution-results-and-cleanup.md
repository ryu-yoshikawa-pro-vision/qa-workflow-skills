terminalの人間向け表示だけを実行結果の正本にしません。

優先順位:

1. 対象repoに既存の機械可読reporter / result artifactがあり、そのreporterの外部I/O・ファイル出力等が今回の許可範囲内なら再利用
2. 不足する場合はPlaywright組み込みJSON reporter等の標準機能を実行時に利用
3. 明確な現在要件がない限りcustom reporterを新設しない

既存custom reporterに未許可の外部送信等がある場合はそのまま実行しません。標準reporter等への一時的な変更が既存実行の意味を変えず安全に行える場合だけ変更し、変更した実行条件を記録します。判断できない場合は該当実行をブロックします。

既存configを恒久変更せずに標準reporterを利用できる場合は、その方法を優先します。出力先についても既存ファイルの削除・上書きが起きないことを確認します。

構造化resultの各項目は、利用したreporter / Playwright API / process観測等が実際に提供した情報だけをraw factとして扱います。利用した標準result形式が`FullResult.status`、`repeatEachIndex`等の項目を直接提供しない場合、その値を別情報から推測してPlaywrightのraw fieldとして補完しません。必要ならmachine-readable test result、process exit code、runner終了理由等の複数の確認済み情報源を組み合わせますが、導出値はraw factと区別します。要求された完全性や安全判断に必要な値を合理的に取得できない場合は`確認不能`または`構造化結果不完全`として扱います。Playwright run全体statusを取得できない場合もprocess exit codeとは別項目として`確認不能`を保持します。

構造化resultは今回のrunによって生成または更新されたことを確認します。前回run等の古いartifactを今回の実行結果として再利用しません。resultが未生成、更新されていない、parse不能、または今回runとの対応を合理的に確認できない場合は、構造化結果取得失敗として扱います。独自run ID、hash、manifest等の仕組みは追加しません。

取得した構造化resultは、今回のproject、要求対象、discovery件数、process exit、run-level結果等と明らかに矛盾していないことを必要な範囲で確認します。

### 保持する実行事実

各test / attemptの結果だけでなく、Playwright run全体の結果を分けて保持します。取得可能な範囲で最低限次を保持します。

run全体:

- Playwright run全体のstatus
- CLI process exit code
- testに紐づかないrun-level / global error
- ユーザーが指定した論理的な要求primary対象数
- 各論理的な要求primary対象について、1件以上のresolved primary TestCaseへ解決したか、解決できない場合の未実行 / 解決不能理由
- project / repeatEach等を解決したresolved primary TestCase数
- 実際に開始したresolved primary TestCase数
- 未実行のresolved primary TestCaseと理由
- `globalSetup`、project dependency、`webServer`、global timeout等、run-levelの失敗を判別できる情報

各test / attempt:

- 実行区分: 要求されたprimary test / project dependencyとして付随実行されたtest / project teardownとして付随実行されたtest
- primary testでは論理的な要求primary対象と、対象TC / E2E実装参照
- dependency / teardown testではTC IDを必須にせず、test file / title path / projectで識別
- test file / title path
- Playwright project
- repeatEachIndex等、resolved primary TestCaseの実行variantを識別する情報
- `expectedStatus`
- 各attemptの`status`。Playwright生値として`passed` / `failed` / `timedOut` / `skipped` / `interrupted`等を保持
- retry番号
- 最終`outcome`
- duration
- error / errors
- 実際の実行回数
- 未実行の場合の理由

`timedOut` / `interrupted`は独立した`TestResult`フィールドとして扱わず、`status`の値として保持します。timeout / interruptionを別分類として要約する場合も、Playwright生情報から導出した情報であることを区別します。

`未実行`はPlaywrightの`TestResult.status`ではなく、ワークフロー上の状態として分けます。完全性は二段階で確認します。まず各論理的な要求primary対象について、1件以上のresolved primary TestCaseへ解決したか、解決できなければ対象testへ解決できなかった理由を論理対象側の未実行 / 解決不能理由として残します。次に、解決された各resolved primary TestCaseについて実行結果または未実行理由が存在することを確認します。論理要求primary対象が存在するのにresolved primary TestCaseが0件で理由もない状態を完全実行とみなしません。`--pass-with-no-tests`等によりprocessが成功していても、この完全性判定を省略しません。retryは対象件数へ加算せず、そのresolved primary TestCase配下のattemptとして扱います。dependency / teardown testを要求primary対象数やresolved primary TestCase数へ混ぜません。人間向け報告では論理的なTC / E2E対象単位へ再集計して構いません。

人間向け集計ではPASS / FAIL等に要約して構いませんが、元のPlaywright情報を失いません。

### ローカルリポジトリへの書き込み

Playwright実行がtest `outputDir`以外へ書き込む可能性も考慮します。対象testがsnapshotを利用する場合は、実効的なsnapshot生成・更新条件、snapshot保存先、source側への書き込み可能性を必要な範囲で確認します。snapshot更新を一律に禁止したり、通常runの設定を無断で変更したりしません。

実行前のworking tree状態を基準として記録し、実行後にworking tree差分を再確認します。今回runで新規作成・変更されたrepo内ファイルを識別し、想定外の変更を隠しません。ユーザーが実行前から持っていた既存変更を自動revert / deleteしません。

正式なrunでsnapshot / source更新が必要な場合は、repoの既存方針またはユーザー要求からその更新が許容されることを確認します。許可根拠がなくtestware変更が発生し得る場合は通常runを局所ブロックします。条件を変更した診断runを行う場合は通常runと区別します。

### 実行コードとテスト対象version

次を別々に記録します。

E2Eコード:

- branch
- HEAD commit
- working tree変更有無

テスト対象:

- URL / origin
- version / build ID等。取得できない場合は確認不能

ローカルGitのcommitを指定URLへデプロイされたアプリversionとして扱いません。

### 証跡・機密情報

trace、screenshot、video、HTML report、network情報、stdout / stderr、`storageState`等は機密情報を含み得るものとして扱います。

- 自動的に外部アップロードしない
- `storageState`等の認証状態を通常成果物としてcommitしない
- secret、cookie、token、不要な個人データを報告へ転記しない
- URLにsecret query等がある場合はそのまま記録しない
- 必要なら証跡の種類と安全なローカル参照だけを記録する
- repo / 案件に既存の証跡保存ルールがあれば優先する

### cleanup

cleanup方法も実行主体を分けます。

Playwright runner管理:

- project teardown
- `globalTeardown`
- `globalSetup`が返すteardown callback
- fixture teardown
- `afterAll` / `afterEach`等のhook
- `webServer`でPlaywrightが今回起動したprocessのrunner管理終了処理

これらはPlaywright runの一部として実行されます。runner管理のcleanupが完了している場合、executionが同じcleanupをrunの外側でもう一度実行しません。`reuseExistingServer`等で実行前から存在するprocessを再利用した場合は、executionがそのprocessをcleanup目的で終了させません。

Playwright外で明示実行するcleanup:

- repoで定義されたcleanup script
- APIによる後処理
- その他、inspectionまたは既存repoで確認済みのrun外cleanup

Playwright外cleanupだけ、必要な場合にexecutionが確認済み方法で実行します。executionの責務は「必ず外部cleanupコマンドを実行する」ことではなく、runner管理分とrun外処理を合わせて必要なcleanupが実行されたことを確認し、その結果を記録することです。

最低限次を記録します。

- cleanup成功
- cleanup失敗
- cleanup未確認
- cleanup対象なし
- 意図的に残した状態
- 残存した副作用
- cleanupの実行主体がrunner管理かrun外処理か

process異常終了、通信断、runner interruption等でcleanupの成否を確認できない場合は`cleanup未確認`として扱い、成功・失敗を推測しません。必要なcleanupが失敗または未確認の状態では、現在状態を無視して機械的に再実行しません。安全な完了にcleanup確認が必要な要求では、未確認のままワークフロー完了にしません。「実行結果だけ」の依頼でもcleanup未確認を隠しません。

### 出力

- 実行対象一覧
- 実行条件
- 使用したURL / origin
- Playwright project
- 実際に利用した実行入口と、必要な前後処理を含むcommand chain。secret値は伏せる
- E2Eコードのbranch / commit / working tree状態
- テスト対象version
- Playwright run全体status / process exit code / run-level error。各値の確認元とraw fact / 導出値を区別し、取得元が直接提供しないraw値は推測しない
- 構造化された各test / attemptの実行結果。primary / dependency / teardownを区別
- 各resolved primary TestCaseの結果または未実行理由と、元の論理的な要求primary対象との対応
- reporter / artifactの取得方法、今回runで生成・更新されたことの確認結果、安全確認したoutput先
- 実行前後のworking tree状態と今回runで発生したrepo内変更
- 利用可能な証跡参照
- cleanup結果と実行主体
- 残存副作用
- ブロック中
