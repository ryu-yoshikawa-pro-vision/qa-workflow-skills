# E2Eテスト実行 詳細判断基準

## 実効設定と副作用

config → project → file / describe / test → CLIの上書きを、今回対象へ影響する範囲だけ追います。absolute URL、webServer、project dependency / teardown、globalSetup / globalTeardown、返却teardown callback、automatic fixture、worker-scoped fixture、hooks、対象testから到達するAPI / helperまで副作用に関係する経路を確認します。

1件の論理TCがproject、repeatEach、retry、parallel worker再生成で複数回操作され得ることを踏まえ、メール・削除・共有データ更新等の最大回数を決めます。副作用の許可範囲と最大回数は、自然言語から推測せず、`<許可範囲> / <最大回数>`の構造で両方を記録します。対象URL / origin、実行入口、project、必要な認証・開始状態、許可範囲 / 最大回数、runner管理cleanup対象 / 方法、run外cleanup対象 / 方法をrunner開始前に確定できない場合は、その範囲をブロックします。テスト対象version / build IDは、実行自体が安全に成立する情報と分け、取得できない場合は`未確認`として結果解釈上の制約へ残せます。

## 準備とcleanup

runnerが管理するsetup / teardownをrun外で二重実行しません。実行条件には`run外準備`行を必ず記録します。`setup / dependency / webServer / teardown`欄は4要素のraw設定として記録し、4番目が`none` / `なし` / `対象なし` / `未使用`等でなければ明示的なrunner管理cleanup対象として扱います。serverごとのownership・再利用・cleanupの正本は`webServer process ownership`表に置きます。`reuseExistingServer=true`は設定値であり、実行前からserverが存在して実際に再利用されたことを意味しません。actual reuseなら今回run非所有・cleanup対象外、actual新規起動なら今回run所有・cleanup対象としてownership表に記録します。`起動状態`は`実行前から存在`または`今回runが起動`、`既存 / 再利用か`は`既存process再利用`または`新規起動`としてactual stateを明示します。`根拠`には実行前のURL / port疎通確認、実行前process確認、今回runでの起動確認など、実際の状態観測を記録し、`reuseExistingServer=true`やconfig上の`reuseExistingServer`だけを単独の根拠にしません。`webServer`は、なし、未確認 / 確認不能、確認済みの設定ありを分けます。確認済みの設定ありでは期待される全serverをownership表へprocessごとに1行で対応付け、ownership・既存 / 再利用・cleanup対象・根拠を個別に記録します。既存 / 再利用processは今回runが所有せず終了対象にしません。webServer未確認 / 確認不能ではrunnerを開始せず、架空のserver識別子やownership行を作りません。run外処理はrepoで定義されinspection等で確認済みのseed / API / cleanupだけを使い、新しい方式を作りません。runner管理cleanup対象 / 方法とrun外cleanup対象 / 方法は、対象と確認済み方法、または明示的な`対象なし`を記録します。run外cleanupの成功 / 失敗 / 未確認 / 一部失敗 / 意図的に残した状態は、run外準備の有無ではなく事前cleanup契約と照合します。run外準備を実施した場合はcleanupの扱いを必ず記録し、対象なしなら不要の根拠を残します。setup自由記述の`run外`、`seed`、`API`等の部分一致や、`run外なし`等の否定表現だけでは準備実施とみなしません。process interruptionや通信断でcleanup結果が確認できない場合は`未確認`です。

## Playwright値域とworkflow状態

Playwrightの値域をworkflow状態と混在させません。公式APIが提供する契約は次のとおりです。

| 情報 | 許可されるraw値 |
| --- | --- |
| `TestResult.status` | `passed` / `failed` / `timedOut` / `skipped` / `interrupted` |
| `TestCase.expectedStatus` | `passed` / `failed` / `timedOut` / `skipped` / `interrupted` |
| `TestCase.outcome()` | `skipped` / `expected` / `unexpected` / `flaky` |
| `FullResult.status` / reporterのrun全体status | `passed` / `failed` / `timedout` / `interrupted` |

`未実行`、`未確認`、`確認不能`、`構造化結果不完全`はPlaywright raw status / outcomeではなく、workflow上の状態または取得不能状態として別列へ保持します。`TestCase.outcome()`はPlaywrightから取得したresolved TestCase単位のraw factです。validatorの補助計算はそのraw factとの整合確認だけに使用し、成果物のoutcomeを生成・置換しません。利用したreporter / APIが直接提供していないraw値をprocess exit codeから作りません。

## 構造化結果

各logical primary対象がresolved primary TestCaseへ1件以上解決したかを先に確認し、解決できなければ理由を残します。次に各resolved primary TestCaseの結果または未実行理由を確認します。resolved primaryの`実行開始`は空欄にせず、開始済みまたは明示的な未開始markerで記録します。dependency / teardown testは要求primary数へ混ぜず、実行区分・test file / title path・project・repeatEachIndexのTestCase identityごとにattempt番号`1..N`、retry番号`0..N-1`を検証します。`timedOut` / `interrupted`はPlaywright statusとして保持し、`outcome`はPlaywrightから取得したTestCase単位の値として別に扱います。

`FullResult.status`や`repeatEachIndex`を利用したresult形式が直接提供しないなら、process exit codeや別ログからraw fieldへ推測転記しません。必要な値は`確認不能`または`構造化結果不完全`にし、導出値と分けます。

runnerを開始していないpreflight blockでは、`FullResult.status`の成功値、数値のprocess exit code、reporter由来のrun結果、resolved / attempt result、runner管理cleanupの`成功`を記録しません。run-level / global errorも`未実施`、`未確認`、`確認不能`、`対象なし`等のworkflow状態だけを許容し、`browser crashed`や`timeout`等のPlaywright由来raw factを置きません。Playwright raw欄へ`未実施`を代入するのではなく、run全体status等は`未確認` / `確認不能`、process exit codeとrun-level errorは`未実施`等のworkflow上の明示状態へ分け、ブロック理由を記録します。runner未開始でも、事前cleanup契約に対応するrun外cleanupの実績は、run外準備の有無だけを理由に拒否せず、契約との対応と結果を記録します。logical primaryは最低1件残し、resolved / attemptが0件である理由を示します。

## 変更と証跡

実行前後のworking treeを比較し、snapshot / source / outputDir以外のrepo内変更も隠しません。output / reportの削除・上書き、custom reporterの外部I/O、storageStateの機密性を確認します。
