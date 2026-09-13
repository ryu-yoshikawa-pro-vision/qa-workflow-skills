## `e2e-test-inspection`

### 責務

Playwright実装前に、対象リポジトリ / ワークスペース、既存E2E、必要な場合は指定された実対象を調査し、次を確定します。

- E2E対象。詳細TCが存在する場合は対象TCも保持
- 実装に必要な事実
- 実装可否
- 実行上の安全条件
- 既存E2Eとの関係

コード変更は行いません。

### 入力

必須:

- 次のいずれか
  - 対象詳細テストケース
  - ユーザーが明示したE2E対象
  - 更新対象となる既存E2E実装参照
- 対象リポジトリ / ワークスペース

期待結果の妥当性まで確定する場合は、現在有効な仕様根拠を利用します。仕様根拠が不足していても、repo構造、既存E2E、locator候補、認証、データ準備、副作用、技術的実装可能性等の調査まで一律停止しません。仕様根拠が必要なoracle・期待結果確認だけを`未確認`または該当範囲の`ブロック中`として扱います。

未指定時に具体的なE2E対象を決める場合は、利用可能な`test-analysis`成果物や既存追跡情報も使います。詳細TCが存在しない経路のためだけにTCまたはTC IDを生成しません。

テスト環境URLは実UI・実状態の確認が必要な範囲では必須です。ただし、URL不足を理由にrepo構造、既存E2E、設定の確認まで一律停止しません。

### 調査対象

必要な範囲で次を確認します。

#### リポジトリ / Playwright構成

- Playwright導入状況
- `playwright.config.*`
- package manager
- 既存実行コマンド
- 既存spec
- fixture。対象testへ適用され得るautomatic fixture、worker-scoped automatic fixtureを含む
- helper
- Page Object
- locator方針
- 認証方法
- `storageState`等の認証状態管理
- テストデータ・状態準備方法
- setup / cleanupがPlaywright runner管理か、run外で明示実行する処理か
- cleanup方法
- reporter
- trace / screenshot / video等の既存設定
- `baseURL`
- Playwright projectとproject固有上書き
- `test.use()`等のテスト単位上書き
- 絶対URLを利用する既存navigation
- `webServer`
- `retries`
- `repeatEach`
- `workers`
- `fullyParallel`
- serial設定
- 共有アカウント / 共有サーバー側データへの依存

inspectionでは設定を新規設計するのではなく、既存の実効設定を事実として確認します。

#### 実対象

必要で、かつ操作能力とURLが利用可能な場合は次を確認します。

- 指定URLへ到達できるか
- 対象画面・対象機能へ到達できるか
- 詳細TCが存在する場合はその開始状態を成立させられるか。TCなしの場合は明示E2E対象に必要な開始状態を成立させられるか
- 実際のUI構造と操作対象
- locatorとして利用可能な実在情報
- 非同期処理や状態遷移
- 期待結果を観測できるか
- 必要なロール・権限
- 必要なテストデータを準備できるか
- テスト対象version / build ID等を確認できるか

実対象を操作する手段が利用できない場合は`未確認`または該当範囲の`ブロック中`とし、確認済みとして推測補完しません。

### 確認元と鮮度

inspection成果物へ最低限次を残します。

- リポジトリ確認時のbranch / commit
- working tree変更有無
- 実対象URL / origin
- 実対象確認日時
- 取得できる場合はversion / build ID
- 主要な事実が「repo」「実対象」「ユーザー提供情報」のどこから確認されたか

implementation開始時に、対象repoの関連ファイルや実対象がinspection時点から実質的に変わっていないか軽量確認します。差分が実装判断へ影響する場合だけ該当範囲を再inspectionします。

### URL・外部遷移・副作用

指定URLは主たるテスト対象を識別する基準であり、副作用の包括許可ではありません。

確認可能な範囲で次を区別します。

- 主たるテスト対象URL / origin
- 認証等で意図して利用する外部origin
- 外部API等、状態変更を伴う依存先
- 指定されていない別テスト環境

OAuth / SSO等の必要な外部遷移は、案件コンテキストまたは既存構成から利用が確認できる場合に扱えます。指定されていない別テスト環境への切替は許可しません。

次の操作が対象となる場合は、ユーザー指示または案件コンテキストから実行許可と許可範囲を確認します。

- データ削除
- 大量データ作成
- メール送信
- Slack等の外部通知
- 決済
- 外部サービスへの状態変更
- 権限変更
- アカウントロックにつながる操作
- その他、不可逆または環境外へ影響する操作

許可を確認できない場合は該当TCだけをブロックします。許可確認前の調査は原則として読み取り・非破壊操作に留めます。

### 証跡・認証情報

次を確認します。

- `storageState`等の認証状態ファイルの保護
- 認証状態やsecretをcommitしない構成
- `.gitignore`等の既存保護設定
- trace / screenshot / video / HTML report / network情報に機密情報や個人データが含まれ得るか
- 証跡の永続化・共有に案件固有制約があるか

secret、cookie、token値を通常成果物へ転記しません。

### 既存E2Eとの重複

各対象TC、ユーザーが明示したE2E対象、または更新対象となる既存E2E実装参照を次のいずれかへ閉じます。

- 既存E2Eで十分にカバー済み
- 既存E2Eの拡張で対応可能
- 新規E2E実装が必要
- 新事実によりE2E自動化価値の再判断が必要
- 実装ブロック中

### Playwright未導入の場合

ユーザーがPlaywrightでの実装を明示的に要求しており、対象packageが明確で、既存package managerと構成に沿った最小限の依存関係・config追加だけで成立する場合は、`e2e-test-implementation`で最小構成を追加できます。

次のような大きな設計判断が必要な場合は該当範囲をブロックします。

- どのpackageへ導入すべきか確定できない
- 既存test frameworkとの置換・競合判断が必要
- モノレポ全体のE2E基盤選定が必要
- 大規模な共通fixture / 認証基盤が必要
- 権限を伴うsystem dependency導入が必要
- CI構築まで必要

新たなE2E基盤構築Skillは追加しません。

### 出力

対象ごとに最低限次を記録します。

- TC ID。詳細TCを入力として持つ場合、または既存のTC ↔ E2E対応がある場合は必須。TCなしの明示E2E対象や既存E2Eから開始する場合は必須にせず、対象説明またはrepo-relative test path + title path等で識別する
- E2E対象の決定根拠
- repo / workspace
- inspection時のbranch / commit / working tree状態
- テスト環境URL / origin。不要・未指定ならその状態
- 実対象確認日時 / version情報
- 対象画面 / 経路
- 必要な開始状態
- 状態・データ準備方法
- setup / cleanupの実行主体。Playwright runner管理かrun外処理か
- 実際の操作対象
- locator候補または既存抽象化
- 期待結果の観測方法
- 再利用できる既存spec / fixture / helper / Page Object
- 実装・実行へ影響するPlaywright設定
- 副作用
- 実行許可の根拠または未許可状態
- cleanup方法 / 制約
- 証跡・認証状態の取扱い制約
- 既存E2Eとの関係
- 実装可否
- ブロック理由 / 未確認事項
- 実装時に守る既存パターン
- 主要事実の確認元

存在を確認できないlocator、fixture、Page Object、API、URL、データ準備方法等を推測で補完しません。
