# E2Eテスト実行 出力テンプレート

## 実行条件

| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| 対象URL / origin |  |  | raw fact |
| 実行入口 / command chain |  |  | raw fact |
| Playwright project |  |  | raw fact |
| retries / repeatEach / workers / parallel |  |  | raw fact |
| setup / dependency / webServer / teardown |  |  | raw fact |
| run外準備 | 実施 / 対象なし / 未確認 / 確認不能 |  | raw fact |
| 必要な認証 / テストデータ / 開始状態 |  |  | raw fact / 確認不能 |
| 副作用の許可範囲 / 最大回数 |  |  | raw fact / 確認不能 |
| cleanup方法 |  |  | raw fact / 確認不能 |
| branch / HEAD / working tree |  |  | raw fact |
| テスト対象version / build ID |  |  | raw fact / 確認不能 |

## Playwright run結果

| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| Playwright run全体status |  | reporter / API / 確認不能 | raw fact / 確認不能 |
| CLI process exit code |  | process / 未実施 | raw fact / 確認不能 |
| run-level / global error |  | reporter / process / 未実施 | raw fact / 確認不能 |
| runner開始 |  | execution | raw fact |
| result artifactの今回run生成・更新 |  | filesystem / reporter | raw fact |

## webServer process ownership（webServerがある場合）

実行条件の`run外準備`行は、準備の有無を問わず必ず記録します。`setup / dependency / webServer / teardown`欄は実効設定のraw factを記録し、serverごとの所有・再利用・cleanupの導出結果はこの表を正本にします。`reuseExistingServer=true`だけからactual reuseを導出せず、実行前から存在して再利用したprocessと今回runが新規起動したprocessを実測事実として区別します。setup欄へownershipの結論を重複記載させません。webServerなしならownership行は不要です。webServerが未確認 / 確認不能ならrunnerを開始せず、架空のserver識別子を作らずownership行を0件にできます。確認済みのwebServerが複数ある場合も1 process 1行とし、自由記述1セルへまとめません。実効設定で期待される全serverを記録し、既存 / 再利用processは今回run非所有・cleanup対象外、今回runが起動したprocessは所有とcleanup対象の扱いを明示します。

| server識別子 | 起動状態 | 今回run所有か | 既存 / 再利用か | cleanup対象か | 根拠 |
| --- | --- | --- | --- | --- | --- |
| frontend | 今回runが起動 / 実行前から存在 | 今回runが所有 / 今回runは所有しない | 新規起動 / 既存process再利用 | 対象 / 対象外 |  |

## logical primary対象の解決

| 論理的な要求primary対象 | E2E実装参照 / TC ID（存在時のみ） | resolved primary TestCase数 | 未実行 / 解決不能理由 |
| --- | --- | ---: | --- |
| login-flow | tests/example.spec.ts > login | 1 |  |

## resolved primary TestCase結果

| resolved primary TestCase参照 | 論理要求primary対象 | test file / title path | project | repeatEachIndex | 実行開始 | 結果 / 未実行理由 |
| --- | --- | --- | --- | --- | --- | --- |
| session-test-1 | login-flow | tests/example.spec.ts > login | chromium | 0 | 開始 |  |

## attempt結果（retryをresolved件数へ加算しない）

| resolved primary TestCase参照 | attempt番号 | 実行区分 | status | expectedStatus | outcome | retry番号 | duration | error / errors |
| --- | ---: | --- | --- | --- | --- | ---: | --- | --- |
| session-test-1 | 1 | 要求primary test | passed / failed / timedOut / skipped / interrupted | passed / failed / timedOut / skipped / interrupted | skipped / expected / unexpected / flaky | 0 |  |  |

## working tree・証跡

| 項目 | 実行前 | 実行後 | 今回runの変更 / 安全確認 |
| --- | --- | --- | --- |
| working tree |  |  |  |
| output / report / snapshot / source |  |  |  |
| trace / screenshot / video / HTML report / network / storageState |  |  |  |
| stale artifactの今回結果利用 |  |  | 未利用 / 利用していないことを確認 |

## cleanup・残存副作用

| cleanup対象 / 実行主体 | 状態 | 結果 / 残存副作用 | 確認元 |
| --- | --- | --- | --- |
| runner管理 | 成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 |  |  |
| run外処理 | 成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 |  |  |

- 実行成果物状態: 完了 / ブロック中 / 要再確認
- ブロック中: preflight blockの場合はrunner未開始・artifact未生成の理由
- run外cleanupを成功と記録する場合は、実行条件の`run外準備`を`実施`または`実施（詳細）`として構造化して記録します。`run外なし`、`外部準備なし`、`seedなし`等の否定表現は準備実施の根拠になりません。
