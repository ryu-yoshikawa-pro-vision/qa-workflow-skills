# テストアーキテクチャ設計

## 成果物メタデータ

| 項目         | 値                                         |
| ------------ | ------------------------------------------ |
| owner        | test-architecture-design                   |
| artifact_ref | fixture://qa/architecture/billing-conflict |
| revision     | arch-r2                                    |
| scope        | billing.authorization                      |
| 状態         | 要再確認                                   |

## 入力source・依存

| owner                      | source_ref                                 | revision | scope                 | currentness | 取得状態 |
| -------------------------- | ------------------------------------------ | -------- | --------------------- | ----------- | -------- |
| stakeholder                | REQUEST-UNKNOWN@unknown                    | unknown  | billing.authorization | unknown     | 取得不能 |
| test-requirements-analysis | fixture://qa/requirements/billing-conflict | unknown  | billing.authorization | unknown     | 取得不能 |
| architecture owner         | ARCH-OLD@rev-1                             | rev-1    | billing.authorization | stale       | 取得済   |

## テストアーキテクチャ割当

| 割当ID   | target_ref            | target種別 | QA要求ref / revision                                           | level  | type       | 方式・検証分担             | environment / data | runner / tool | 選択根拠 | 根拠ref / revision      | 状態・準備条件 | owner                    |
| -------- | --------------------- | ---------- | -------------------------------------------------------------- | ------ | ---------- | -------------------------- | ------------------ | ------------- | -------- | ----------------------- | -------------- | ------------------------ |
| ARCH-004 | billing.authorization | API target | fixture://qa/requirements/billing-conflict#QAR-UNKNOWN@unknown | 未確定 | functional | 指定の解決後に分担を決める | 未確定             | 未確定        | 未確定   | REQUEST-UNKNOWN@unknown | 判断保留       | test-architecture-design |

## レベル優先・競合

| target_ref            | 明示指定 | 承認済み割当 | 既定値   | 適用判断           | 競合・判断元                                |
| --------------------- | -------- | ------------ | -------- | ------------------ | ------------------------------------------- |
| billing.authorization | API      | システム     | システム | 未確定、採用しない | scopeとrevisionが一致する判断元を再取得する |

## 非機能・環境制約

| 品質特性      | 対象ref               | 測定方式 | 閾値source / revision   | environment / data | 準備状態 | 残る制約           |
| ------------- | --------------------- | -------- | ----------------------- | ------------------ | -------- | ------------------ |
| authorization | billing.authorization | 未確定   | REQUEST-UNKNOWN@unknown | 未確定             | blocked  | sourceを再取得する |

## 承認

| 対象scope             | artifact_ref                               | revision | 承認主体・role | 承認証拠ref | 状態   | 失効条件                 |
| --------------------- | ------------------------------------------ | -------- | -------------- | ----------- | ------ | ------------------------ |
| billing.authorization | fixture://qa/architecture/billing-conflict | arch-r2  | -              | -           | 未承認 | sourceと指定が解決した後 |

## 変更影響・handoff

| 変更ref / revision      | 影響scope             | 要再確認のowner / ref             | 保持するcurrent成果物             | resume owner             | 理由                   |
| ----------------------- | --------------------- | --------------------------------- | --------------------------------- | ------------------------ | ---------------------- |
| REQUEST-UNKNOWN@unknown | billing.authorization | test-architecture-design/ARCH-004 | 無関係なorders scopeのcurrent割当 | test-architecture-design | 指定元と承認割当の競合 |

## 未解決・blocked

| 項目      | scope                 | 担当        | 状態    | 再開条件                                   |
| --------- | --------------------- | ----------- | ------- | ------------------------------------------ |
| level競合 | billing.authorization | stakeholder | blocked | 明示指定と承認済み割当を同じrevisionで確認 |

## 履歴

| revision | 置換元ref / revision | 変更理由                    | 影響scope             | 再確認する依存            |
| -------- | -------------------- | --------------------------- | --------------------- | ------------------------- |
| arch-r2  | arch-r1              | conflicting source detected | billing.authorization | REQUEST-UNKNOWN、ARCH-OLD |
