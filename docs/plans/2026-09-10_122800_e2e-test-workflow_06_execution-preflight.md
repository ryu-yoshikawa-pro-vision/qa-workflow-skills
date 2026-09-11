## `e2e-test-execution`

### 責務

実装済みまたは既存のPlaywright E2Eを、指定されたテスト環境URLへローカルから安全に実行します。

次を担当します。

```text
実行対象確認
↓
最小限の実行安全確認
↓
Playwright外で必要な確認済み準備だけ実行
↓
Playwright実行
  └ dependency / setup / fixture / hook / teardown等、runner管理処理を含む
↓
構造化された生の実行結果・証跡取得
↓
Playwright外で必要な確認済みcleanupだけ実行
↓
runner管理分も含むcleanup結果・残存副作用の記録
```

Playwright runnerが管理するsetup / cleanupと、executionがrunの外側で明示実行する準備 / cleanupを区別し、同じ処理を二重実行しません。

失敗原因の推論は行いません。

### 直接開始

既存E2Eの実行要求では`e2e-test-execution`から直接開始できます。inspection成果物を必須依存にしません。

ただし直接開始時でも、今回の実行に必要な安全確認を本Skill自身が行います。安全性または実行範囲を確認できない場合だけinspectionへ戻します。

### 実行前に確認する範囲

今回の実行へ実際に影響する範囲で次を確認します。

- 指定テスト環境URL
- 主たる対象origin
- 実行対象テスト
- 今回利用する実際の実行入口と、そこからPlaywright起動・必要な前後処理までに到達するpackage script / task / wrapper / pre-post処理
- Playwright project
- project固有の`use` / `baseURL`等
- `test.use()`等によるfile / describe / test単位の`baseURL`、`storageState`等の上書き
- `test.describe.configure()`等によるretries、mode、timeout等の上書き
- project dependencies
- project teardown
- `globalSetup`
- `globalTeardown`
- 対象テストへ適用されるfixture / hooksのうち副作用へ関係するもの。明示利用fixtureだけでなく`auto: true`のautomatic fixture、worker-scoped automatic fixtureも含む
- 実行対象test本体と、そこから到達するhelper / Page Object / API呼び出し等のうち、対象URL、外部I/O、副作用、安全判断へ影響する経路
- `webServer`
- 絶対URL navigation
- reporter。custom reporterの場合は外部送信、ファイル出力、test選択・status変更等の副作用
- test `outputDir`、reporterのoutput file / output directoryと既存ファイルへの影響
- 対象testがsnapshotを利用する場合のsnapshot生成・更新設定、snapshot保存先、source側への書き込み可能性、`ignoreSnapshots`等によりsnapshot assertion自体が無効化されていないか
- 実行前のworking tree状態と、repo内への既知の書き込み先が既存ユーザー変更と衝突しないか
- retries
- repeatEach
- workers
- fullyParallel / serial設定
- 今回の実行集合・途中停止へ影響する`maxFailures`、`globalTimeout`、grep / grepInvert、focusされたtest等
- retryの実効挙動が今回の安全性・結果解釈へ影響する場合は、その設定と挙動
- 共有アカウント
- 共有サーバー側データ
- 必要な認証
- テストデータ / 開始状態
- 副作用の許可範囲
- cleanup方法
- 証跡取扱い制約
- ローカルPlaywright runtimeが実際に利用可能か

全repoを再監査せず、今回の実行経路から到達する設定・setup・teardown・fixture等へ確認範囲を限定します。今回対象testへ最終的に適用される実効設定を、安全性、実行回数、期待結果へ影響する範囲で確認し、config → project → file / describe / test → CLI等の上書きを必要なところだけ追います。Playwrightの機能や設定の対応状況・挙動に不確実性がある場合だけ、その時点で対象repoの実効設定とPlaywright公式仕様を確認します。Playwrightのversion確認を毎回の必須手順にはしません。

repoに既存の実行入口がある場合は、安全性と実行意味を確認できるならそれを優先します。安全確認を避ける目的で`npm run e2e`等を直接`playwright test`へ置き換えません。別の起動方法へ変更する場合は、必要な環境変数、準備、cleanup、reporter等を失わず実行意味が同じと確認できる場合だけ行います。wrapper等に含まれる準備・cleanupは、既存のrunner管理 / run外処理の契約へ統合して二重実行を防ぎます。安全性を確認できない実行入口は推測で実行しません。

`--no-deps`等によって副作用を安易に回避しません。dependencyやteardownを無効化すると本来必要なsetup / cleanupまで失う可能性があるため、実行意味と安全性を確認して判断します。

### 実行回数と副作用

project、repeatEach、retry、parallel worker等により、1件のTCに見える操作が複数回実行される可能性を考慮します。automatic fixtureやworker-scoped automatic fixtureも対象testへ適用される場合は副作用回数の判断に含め、workerの再生成等でsetupが再実行され得る場合も安全側に確認します。

メール、外部通知、削除、決済、権限変更、共有レコード更新等については、設定値を確認するだけでなく「今回最大何回副作用が発生し得るか」を合理的に判断します。setup、fixture、hook、project dependency、retry等が組み合わさり上限を確定できない場合は`不明`として扱います。

高リスク副作用について、回数上限が安全判断に必要なのに合理的に確定できない場合は、推測で上限を置かず該当範囲をブロックします。

通常の正式な検証runでは`retries`と`repeatEach`を原則として対象repoの実効設定のまま利用します。これらを変更するとflaky等の観測結果や実行意味が変わり得るため、安全上その設定で実行できない場合は通常runとしてブロックするか、明示的な診断目的の実行として分離します。診断目的で条件を変更した実行を通常の正式実行結果と同一視しません。

安全のためにCLI上で実行範囲やworkers等を一時的に狭める場合は、次を満たす必要があります。

- テストの意味を変えない
- ユーザー要求と矛盾しない
- repoの既存意図を壊さない
- 何を変更して実行したか記録する

repoのconfigをPASS目的で勝手に恒久変更しません。

### テストデータ・開始状態準備

準備方法を次の2種類に分けます。

Playwright runner管理:

- project dependency
- `globalSetup`
- fixture setup。明示fixtureだけでなく対象testへ適用されるautomatic fixture、worker-scoped automatic fixtureを含む
- `beforeAll` / `beforeEach`等のhook
- `webServer`でPlaywrightが今回起動するprocess

これらはPlaywright run自体によって起動します。executionが同じ準備処理をrunの外側で重複実行しません。`reuseExistingServer`等で実行前から存在するprocessを再利用する場合は、Playwrightが今回起動したprocessとして扱いません。複数`webServer`がある場合も各processの所有関係を区別します。

Playwright外で明示実行する準備:

- repoで定義された外部seed command
- APIによる事前データ作成
- その他、inspectionまたは既存repoで確認済みのrun外準備

Playwright外の準備だけ、必要な場合にexecutionが確認済み方法で実行します。execution自身が新しい準備方式を創作しません。方法が未確認ならinspectionへ戻します。

準備操作自体が副作用を持つ場合も、テスト本体と同じ許可基準を適用します。

### 構造化結果の取得
