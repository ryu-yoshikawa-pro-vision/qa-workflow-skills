# QA要求分析

## 成果物メタデータ

| 項目                       | 値                                |
| -------------------------- | --------------------------------- |
| owner                      | test-requirements-analysis        |
| artifact_ref               | fixture://qa/requirements/restart |
| revision                   | req-r1                            |
| scope                      | orders-unknown-source             |
| 状態                       | blocked                           |
| 対象build / release / 期間 | 未確認                            |

## QA目的・成功条件

| QA目的                         | 品質目標 | 対象・対象外      | 活動の成功条件                     | 根拠           |
| ------------------------------ | -------- | ----------------- | ---------------------------------- | -------------- |
| source確認後にQA要求を確定する | 未確定   | 対象scopeのみ保留 | 要求元sourceとrevisionを再取得する | sourceが未取得 |

## QA要求

| QA要求ID | QA活動上の要求                   | 要求元 | source_ref      | source_revision | scope                 | 優先度 | 状態   | 根拠・成功条件                          |
| -------- | -------------------------------- | ------ | --------------- | --------------- | --------------------- | ------ | ------ | --------------------------------------- |
| QAR-003  | 要求内容は未確定のため確定しない | 未取得 | REQUEST-MISSING | unknown         | orders-unknown-source | 未確定 | 未解決 | 要求本文とrevisionを取得するまでblocked |

## 情報源・取得範囲

| owner       | source_ref      | revision | scope                 | currentness | 取得状態 | 未取得理由 / evidence     |
| ----------- | --------------- | -------- | --------------------- | ----------- | -------- | ------------------------- |
| stakeholder | REQUEST-MISSING | unknown  | orders-unknown-source | unknown     | 取得不能 | source access unavailable |

## 確認・承認

| 対象scope             | artifact_ref                      | revision | 承認主体・role | 承認証拠ref | 状態   | 失効条件               |
| --------------------- | --------------------------------- | -------- | -------------- | ----------- | ------ | ---------------------- |
| orders-unknown-source | fixture://qa/requirements/restart | req-r1   | -              | -           | 未承認 | source再取得後に再確認 |

## 未決事項

| 項目    | 影響scope             | 担当        | 状態    | 再開条件                                    |
| ------- | --------------------- | ----------- | ------- | ------------------------------------------- |
| QAR-003 | orders-unknown-source | stakeholder | blocked | REQUEST-MISSINGの本文とrevisionを再取得する |

## 下流handoff

| owner                    | artifact_ref | revision | scope                 | 関連するQA要求ID | currentness / 承認 |
| ------------------------ | ------------ | -------- | --------------------- | ---------------- | ------------------ |
| test-architecture-design | 未作成       | 未作成   | orders-unknown-source | QAR-003          | blocked            |

## 履歴

| revision | 置換元ref / revision | 変更理由 | 影響scope             | 再確認する依存  |
| -------- | -------------------- | -------- | --------------------- | --------------- |
| req-r1   | -                    | 初回記録 | orders-unknown-source | REQUEST-MISSING |
