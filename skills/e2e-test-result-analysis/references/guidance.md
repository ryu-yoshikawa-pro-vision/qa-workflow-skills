# E2Eテスト結果分析 詳細判断基準

## 分析対象

分析へ進めるのは、最終outcomeがunexpected / flaky、期待外skip、要求対象未実行、run全体failed / timedout / interrupted、run-level error、cleanup失敗 / 未確認、または明示分析要求がある場合です。`expectedStatus = failed`かつ期待どおりの結果は異常扱いしません。

## 原因と判定状態

原因候補はプロダクト挙動と仕様根拠の不一致、E2E実装、TC、条件 / 対象選定、データ / 開始状態、指定環境、ローカルruntime、仕様根拠不足です。証拠が不足する場合は`判定不能`を判定状態として残します。version不明が原因判定へ影響する場合は環境未確定 / 証拠不足として扱います。

再現性は`再現`、`再現せず`、`断続的`、`未確認`で別管理します。retry PASSは初回FAILを消さず、flaky等の事実と推論を分離します。

## 追加実行とrouting

追加実行の出力は、目的・仮説・必要範囲・実行担当`e2e-test-execution`を含みます。分析Skillはcommand、Playwright API、ブラウザ操作を実行しません。
