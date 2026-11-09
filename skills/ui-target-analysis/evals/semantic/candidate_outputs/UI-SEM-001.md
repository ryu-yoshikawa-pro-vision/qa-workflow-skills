# UI分析

## 入力とcurrentness

| 対象 | ref | revision | 確認結果 |
| --- | --- | --- | --- |
| 画面capture | `artifact://design/checkout` | `design-r7` | 静止画像から確認できる要素・表示だけを記録 |
| 要件 | `doc://checkout/requirement` | `req-12` | 住所入力と支払画面への遷移intentを確認 |

## UI構造・操作の観測

| UI要素 | 観測 |
| --- | --- |
| 配送先住所フォーム | 画面上に表示 |
| Continueボタン | disabled表示 |
| 郵便番号欄 | 不正値入力後にinline messageが表示 |

`design-r7`だけからは、messageの発火条件、Continueのenable条件、invalid input時のsubmit可否、実際の遷移成功を確定できません。

## Authority境界

`req-12`が示す期待は「利用者が配送先住所を入力し、支払へ進める」です。郵便番号のvalidation規則と操作時の期待結果は指定されていないため、`spec-analysis`でUNKNOWNとして解決してください。capture上のdisabled表示やmessageを期待仕様の根拠にしません。
