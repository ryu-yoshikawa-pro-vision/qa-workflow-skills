# E2Eテスト実行 出力テンプレート

## 実行条件

| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| 対象URL / origin |  |  | raw fact |
| 実行入口 / command chain |  |  | raw fact |
| Playwright project |  |  | raw fact |
| retries / repeatEach / workers / parallel |  |  | raw fact |
| setup / dependency / webServer / teardown |  |  | raw fact |
| branch / HEAD / working tree |  |  | raw fact |
| テスト対象version / build ID |  |  | raw fact / 確認不能 |

## Playwright run結果

| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| Playwright run全体status |  | reporter / API / 確認不能 | raw fact / 確認不能 |
| CLI process exit code |  | process | raw fact |
| run-level / global error |  | reporter / process | raw fact |
| runner開始 |  | execution | raw fact |
| result artifactの今回run生成・更新 |  | filesystem / reporter | raw fact |

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
| runner管理 / run外処理 | 成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 |  |  |

- 実行成果物状態: 完了 / ブロック中 / 要再確認
- ブロック中: preflight blockの場合はrunner未開始・artifact未生成の理由
