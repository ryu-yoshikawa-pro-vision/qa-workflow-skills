# 意味上の期待

- plan revisionとapproval revisionを一致させる。
- planned population、source取得状態、実行状態、raw result、build／environmentを別々に保つ。
- 未取得sourceを未実行／0件確認済みと混同せず、全体終了判定を未完了またはblockedにする。
- 進捗数の単位を明記し、別run／retryを重複計上しない。
- project riskをProduct Riskから分け、Regression Runや実行結果・報告を再所有しない。
