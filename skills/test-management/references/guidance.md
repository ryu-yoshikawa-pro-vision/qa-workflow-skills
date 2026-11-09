# テスト計画・モニタリングの判断基準

## 正本の境界

| 管理対象                                                 | owner                        |
| -------------------------------------------------------- | ---------------------------- |
| QA活動の目的・scope・成功条件                            | `test-requirements-analysis` |
| level／type／方式／環境の全体割当                        | `test-architecture-design`   |
| Product Risk・設計深度                                   | `test-analysis`              |
| project plan・source inventory・進捗・project risk・是正 | `test-management`            |
| workflow routing・停止・再開状態                         | `qa-workflow`                |
| Regression baseline・membership・Run・Activity           | `regression-testing`         |
| raw execution／attempt／cleanup                          | 実行owner                    |
| 統合result snapshot・全体closure                         | `test-reporting`             |

## 計画と承認

1. currentなQA要求・architectureをowner ref／revisionで読みます。未提供の要求を作り足しません。
2. 対象scope・build／環境・期間、suite・順序・担当、見積工数・resource、開始／終了基準を記録します。見積と実績は別項目です。
3. plan versionの変更ごとに旧版参照・diff・影響scope・失効する承認を残します。承認refは対象plan artifact ref・revision・scopeと一致しなければなりません。
4. 承認主体は信頼できる認証元の証拠で確認します。LLMの`approved`や利用者が書いた自由文だけで承認済みにしません。
5. 承認provider／native CAS／履歴／readbackが未接続なら計画を正式保存しません。草案作成は続行し、永続化だけをblockedにします。

## source inventoryと母集団

承認済み計画revisionは、Jのreportingが照合できるよう、予定source owner・source ref／revision・scope・対象build／環境・必要実行単位を明示します。例: logical TC、E2E run、Regression selected run、Exploration session、API／batch suite、静的レビュー対象。テストファイル数から個別TC数を推定しません。

予定母集団とsource ownerが返した取得readbackは別表で保持し、population IDで結びます。readbackのsource owner／ref／revision／scope／取得範囲／unit／build／environmentを予定値と照合します。完全取得・0件確認は期待identityと一致するreadbackが必要です。部分取得は取得できた範囲と不足理由を示し、別build／旧revisionの結果を予定値へ結び替えません。

各sourceについて次を区別します:

- **取得状態**: 取得済、部分取得、未取得、取得不能、0件を確認済み
- **実行状態**: 実行済み、実行中、未実行、取消、実行失敗、結果不明、対象なし
- **判定状態**: 未判定、PASS、FAIL、判定不能（source ownerのraw resultを維持）

`0件を確認済み`はscope・query／pagination・取得時点が分かるsource ownerの明示確認がある場合だけです。該当populationの実行状態は`対象なし`とし、`未実行`や取消と混同しません。`実行失敗`は確認済みのrunner／環境失敗で、結果は`判定不能`、理由とsource owner readbackが必要です。これはテスト結果の`FAIL`でも`結果不明`でもありません。source未取得を0件や完了としません。runの再試行はattemptとlogical unitを分け、異なるbuild・期間・環境を混ぜません。

計画上の母集団と実取得範囲を同じ単位で照合します。取得が一部でも計画全体の比率や終了判定を確定しません。`test-reporting`が実結果のPASS率・横断closureを所有します。

## 進捗・差異・リスク・是正

- monitoring snapshotは1つの計画revision・target build・environment内の母集団だけを集計し、取得済／部分取得／未取得／取得不能／0件確認／取得不明、実行済／実行中／未実行／取消／実行失敗／結果不明、判定別の各件数をplannedとreadback ledgerから再計算できるようにします。
- 見積工数と実績時間、planned sourceと取得source、実行開始と判定結果を別々に記録します。
- Project riskは日程、資源、要員、環境準備、権限、外部依存などQA計画遂行上の不確実性です。`test-analysis`のProduct Riskをコピー・再採点しません。
- 是正処置は原因・action・責任者・期限（不明なら未設定）・状態・結果・source refを追跡します。未完了actionや未処理差異を隠しません。
- 外部Issue・実行ownerの副作用を再試行する場合は同一operation identityと実保存状態をowner側で照合し、結果不明の副作用を自動再実行しません。

## 改版と部分再評価

計画・resource・環境・方式・品質目標が変わった場合は`test-architecture-design`へ影響する割当だけ再評価を依頼します。下流Risk・正式設計・実行準備は変更根拠があるscopeだけ再確認します。依存が分からない場合は未確認を残し、無関係なcurrent成果物を失効させません。

## 品質ゲート

- 承認済み計画は正確なscope／ref／revisionと認証済みapproval evidenceに紐付く。
- planned source inventoryと必要実行母集団をowner／source ref／revision／build／環境／単位で取得できる。
- 未取得、取得不能、実行0件、正当な0件確認、取消、未判定を区別する。
- 進捗の分母・実績・見積・raw結果が再取得可能で、報告側の全体PASSを作らない。
- Product Riskとproject risk、workflow stateとRegression Runが分離されている。
- 未処理の差異・risk・是正、block理由・resume ownerが残る。
