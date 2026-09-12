# E2Eテスト実行 詳細判断基準

## 実効設定と副作用

config → project → file / describe / test → CLIの上書きを、今回対象へ影響する範囲だけ追います。absolute URL、webServer、project dependency / teardown、globalSetup / globalTeardown、返却teardown callback、automatic fixture、worker-scoped fixture、hooks、対象testから到達するAPI / helperまで副作用に関係する経路を確認します。

1件の論理TCがproject、repeatEach、retry、parallel worker再生成で複数回操作され得ることを踏まえ、メール・削除・共有データ更新等の最大回数を決めます。対象URL / origin、実行入口、project、必要な認証・開始状態、副作用の許可範囲と最大回数、必須cleanup方法をrunner開始前に確定できない場合は、その範囲をブロックします。テスト対象version / build IDは、実行自体が安全に成立する情報と分け、取得できない場合は`未確認`として結果解釈上の制約へ残せます。

## 準備とcleanup

runnerが管理するsetup / teardownをrun外で二重実行しません。`setup / dependency / webServer / teardown`欄はraw設定の記録に限定し、serverごとのownership・再利用・cleanupの正本は`webServer process ownership`表に置きます。`webServer`は、なし、未確認 / 確認不能、確認済みの設定ありを分けます。確認済みの設定ありでは期待される全serverをownership表へprocessごとに1行で対応付け、ownership・既存 / 再利用・cleanup対象・根拠を個別に記録します。既存 / 再利用processは今回runが所有せず終了対象にしません。webServer未確認 / 確認不能ではrunnerを開始せず、架空のserver識別子やownership行を作りません。run外処理はrepoで定義されinspection等で確認済みのseed / API / cleanupだけを使い、新しい方式を作りません。run外cleanupを成功と記録する場合は、実行条件の`run外準備`を`実施`または`実施（詳細）`として独立したraw factで記録します。setup自由記述の`run外`、`seed`、`API`等の部分一致や、`run外なし`等の否定表現だけでは準備実施とみなしません。process interruptionや通信断でcleanup結果が確認できない場合は`未確認`です。

## Playwright値域とworkflow状態

Playwrightの値域をworkflow状態と混在させません。公式APIが提供する契約は次のとおりです。

| 情報 | 許可されるraw値 |
| --- | --- |
| `TestResult.status` | `passed` / `failed` / `timedOut` / `skipped` / `interrupted` |
| `TestCase.expectedStatus` | `passed` / `failed` / `timedOut` / `skipped` / `interrupted` |
| `TestCase.outcome()` | `skipped` / `expected` / `unexpected` / `flaky` |
| `FullResult.status` / reporterのrun全体status | `passed` / `failed` / `timedout` / `interrupted` |

`未実行`、`未確認`、`確認不能`、`構造化結果不完全`はPlaywright raw status / outcomeではなく、workflow上の状態または取得不能状態として別列へ保持します。利用したreporter / APIが直接提供していないraw値をprocess exit codeから作りません。

## 構造化結果

各logical primary対象がresolved primary TestCaseへ1件以上解決したかを先に確認し、解決できなければ理由を残します。次に各resolved primary TestCaseの結果または未実行理由を確認します。dependency / teardown testは要求primary数へ混ぜません。`timedOut` / `interrupted`はPlaywright statusとして保持し、`outcome`は別の導出結果として扱います。

`FullResult.status`や`repeatEachIndex`を利用したresult形式が直接提供しないなら、process exit codeや別ログからraw fieldへ推測転記しません。必要な値は`確認不能`または`構造化結果不完全`にし、導出値と分けます。

runnerを開始していないpreflight blockでは、`FullResult.status`の成功値、数値のprocess exit code、reporter由来のrun結果、resolved / attempt result、runner管理cleanupの`成功`を記録しません。run-level / global errorも`未実施`、`未確認`、`確認不能`、`対象なし`等のworkflow状態だけを許容し、`browser crashed`や`timeout`等のPlaywright由来raw factを置きません。Playwright raw欄へ`未実施`を代入するのではなく、run全体status等は`未確認` / `確認不能`、process exit codeとrun-level errorは`未実施`等のworkflow上の明示状態へ分け、ブロック理由を記録します。runner未開始でも、runner開始前に実施したrun外準備に対応するrun外cleanupの`成功`は記録できます。logical primaryは最低1件残し、resolved / attemptが0件である理由を示します。

## 変更と証跡

実行前後のworking treeを比較し、snapshot / source / outputDir以外のrepo内変更も隠しません。output / reportの削除・上書き、custom reporterの外部I/O、storageStateの機密性を確認します。
