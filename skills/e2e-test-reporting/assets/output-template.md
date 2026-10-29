# E2Eテスト結果報告 出力テンプレート

## 対象・環境

| 項目                                    | 値 | 参照 / 確認元 |
| --------------------------------------- | -- | ------------- |
| 対象機能 / 範囲                         |    |               |
| テスト環境URL / origin                  |    |               |
| テスト対象version / build ID            |    |               |
| E2Eコードbranch / commit / working tree |    |               |
| 実行日時 / Playwright project           |    |               |

## run全体結果

| 項目                     | 値 | 確認元                      | raw fact / 導出値   |
| ------------------------ | -- | --------------------------- | ------------------- |
| Playwright run全体status |    |                             | raw fact / 確認不能 |
| process exit code        |    | process / 未実施            | raw fact / 確認不能 |
| run-level / global error |    | reporter / process / 未実施 | raw fact / 確認不能 |

必須値を確認できないときは、契約上空欄が指定された欄を除いて値欄に`未提供` / `確認不能` / `未実施`、確認元欄に確認した入力・成果物または「許可された入力内に記録なし」を記載します。表の見出しや確認元を空欄にしたまま未解決情報を隠しません。

## primary対象集計（単位を混同しない）

| 論理的な要求primary対象 | E2E実装参照                   | TC ID（存在時のみ） | resolved primary TestCase数 | 実際に開始したresolved primary TestCase数 | 未実行logical理由 | 未実行resolved理由 |
| ----------------------- | ----------------------------- | ------------------- | --------------------------: | ----------------------------------------: | ----------------- | ------------------ |
| login-flow              | tests/example.spec.ts > login |                     |                           1 |                                         1 |                   |                    |

## resolved primary結果 / attempt結果

| 論理的な要求primary対象 | resolved primary TestCase参照 | 実行開始 | 結果   | 未実行理由 | expectedStatus | outcome  | retry attempt数（別集計） | 初回 / retry履歴 | 実行結果参照 |
| ----------------------- | ----------------------------- | -------- | ------ | ---------- | -------------- | -------- | ------------------------: | ---------------- | ------------ |
| login-flow              | session-test-1                | 開始     | passed |            | passed         | expected |                         1 | passed (retry 0) | result-1     |

開始済みresolved primaryは、`結果`へTestResult.status、`実行結果参照`、expectedStatus、Playwrightから取得したresolved TestCase単位のraw `outcome`、1以上のretry attempt数を記録し、`未実行理由`を空欄にします。retry attempt数がNの場合、`初回 / retry履歴`には`<TestResult.status> (retry <number>)`のcanonical entryをN件、`retry 0`から`retry N-1`の出現順で欠落・重複・範囲外なく保持し、末尾statusを`結果`と一致させます。`outcome = flaky`はこのreportだけで明白な矛盾となる2件未満のattempt数にせず、expected側 / unexpected側のattemptが混在しない履歴をflakyとして記録しません。未開始resolved primaryは、`実行開始`を明示し、`結果`・`実行結果参照`・expectedStatus・outcomeを空欄にし、`未実行理由`を記録し、retry attempt数を0、初回 / retry履歴を空欄にします。resolved primary自体が0件のpreflight blockでは、traceの実行参照欄に架空のresultや未実行理由そのものを識別子として置かず、logical primary識別子を参照し、未実行理由は専用列へ記録します。

## TC・E2E・実行・分析追跡

| TC ID（存在時のみ） | E2E実装参照                   | resolved primary TestCase / 実行結果参照 | 分析結果参照 | 報告上の扱い |
| ------------------- | ----------------------------- | ---------------------------------------- | ------------ | ------------ |
|                     | tests/example.spec.ts > login | result-1                                 |              |              |

`e2e-test-result-analysis`を実施したreportでは、対応する分析成果物の安定参照を空欄にせず、fixtureまたは入力で指定された参照と完全一致させます。分析未実施が明示された正常runでは`分析結果参照`を必ず空欄にします。分析実施状態が未指定の既存経路では一律に空欄を強制しません。resolvedごとに分析成果物が異なる場合はtrace行ごとに対応付け、同じ参照を推測で使い回しません。

primary集計と追跡表のlogical primary識別子、E2E実装参照は同じ値を保持します。resolved primaryがある場合は入力で確認したresolved参照・実行結果参照へ対応付けます。resolved primaryが0件の場合は、追跡表のresolved / execution参照欄に対応するlogical primary識別子をそのまま記録し、説明文で別の参照を作りません。入力に安定参照がない欄は未提供状態を明示し、架空の参照を割り当てません。

追跡表の`resolved primary TestCase / 実行結果参照`欄は、行ごとに参照を1つだけ記録します。開始済みなら`実行結果参照`のみ、未開始なら`resolved primary TestCase参照`のみ、resolved primaryが0件ならlogical primary識別子のみを記録します。複数参照を`/`等で連結しません。

## cleanup・証跡・残存リスク

| 項目                                 | 状態 / 内容                                                     | 安全な参照                       |
| ------------------------------------ | --------------------------------------------------------------- | -------------------------------- |
| cleanup                              | 成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 / 一部失敗 |                                  |
| 残存副作用                           |                                                                 |                                  |
| 証跡                                 |                                                                 | secretを含まないローカル参照のみ |
| ブロック中 / 未解決事項 / 残存リスク |                                                                 |                                  |
