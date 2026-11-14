# QA要求分析

## 成果物メタデータ

| 項目                       | 値                                  |
| -------------------------- | ----------------------------------- |
| owner                      | test-requirements-analysis          |
| artifact_ref               | fixture://qa/requirements/orders-q4 |
| revision                   | req-r3                              |
| scope                      | orders-release-q4                   |
| 状態                       | 承認済み                            |
| 対象build / release / 期間 | release-2026-q4 / 対象build未確定   |

## QA目的・成功条件

| QA目的                       | 品質目標                        | 対象・対象外                    | 活動の成功条件                                   | 根拠             |
| ---------------------------- | ------------------------------- | ------------------------------- | ------------------------------------------------ | ---------------- |
| Ordersの品質ゲートを準備する | 注文更新を必要なlevelで確認する | Orders release / 対象外は未合意 | 承認済みQA要求と必要なsourceが計画へ引き継がれる | REQUEST-01@doc-7 |

## QA要求

| QA要求ID | QA活動上の要求                               | 要求元      | source_ref | source_revision | scope             | 優先度 | 状態     | 根拠・成功条件                                |
| -------- | -------------------------------------------- | ----------- | ---------- | --------------- | ----------------- | ------ | -------- | --------------------------------------------- |
| QAR-001  | 注文更新の品質ゲートと必要な証拠を明確にする | stakeholder | REQUEST-01 | doc-7           | orders-release-q4 | 高     | 合意済み | APPROVAL-4の参照がこのartifact revisionを指す |
| QAR-002  | APIとsystemの両levelで結果を確認する         | 利用者提案  | REQUEST-01 | doc-7           | orders-release-q4 | 中     | 提案     | 計画へ確定入力する前に承認が必要              |

## 情報源・取得範囲

| owner         | source_ref | revision | scope             | currentness | 取得状態 | 未取得理由 / evidence  |
| ------------- | ---------- | -------- | ----------------- | ----------- | -------- | ---------------------- |
| stakeholder   | REQUEST-01 | doc-7    | orders-release-q4 | current     | 取得済   | approval recordを確認  |
| test-analysis | RISK-001   | risk-5   | order-update      | current     | 取得済   | source ownerのrevision |

## 確認・承認

| 対象scope         | artifact_ref                        | revision | 承認主体・role | 承認証拠ref | 状態     | 失効条件                  |
| ----------------- | ----------------------------------- | -------- | -------------- | ----------- | -------- | ------------------------- |
| orders-release-q4 | fixture://qa/requirements/orders-q4 | req-r3   | QA lead        | APPROVAL-4  | 承認済み | scope・内容revisionの変更 |

## 未決事項

| 項目 | 影響scope | 担当 | 状態 | 再開条件 |
| ---- | --------- | ---- | ---- | -------- |

## 下流handoff

| owner                    | artifact_ref                        | revision | scope             | 関連するQA要求ID | currentness / 承認 |
| ------------------------ | ----------------------------------- | -------- | ----------------- | ---------------- | ------------------ |
| test-architecture-design | fixture://qa/architecture/orders-r1 | arch-r1  | orders-release-q4 | QAR-001          | current / 承認済み |

## 履歴

| revision | 置換元ref / revision | 変更理由     | 影響scope         | 再確認する依存                              |
| -------- | -------------------- | ------------ | ----------------- | ------------------------------------------- |
| req-r3   | req-r2               | QA要求の整理 | orders-release-q4 | fixture://qa/architecture/orders-r1@arch-r1 |
