# テスト計画・モニタリング

## 成果物メタデータ

| 項目                           | 値                               |
| ------------------------------ | -------------------------------- |
| owner                          | test-management                  |
| artifact_ref                   | fixture://qa/plan/orders-q4      |
| revision                       | plan-r2                          |
| scope                          | orders-release-q4                |
| plan_version                   | 2                                |
| 状態                           | 草案                             |
| 対象build / environment / 期間 | build-111 / staging / release-q4 |

## 入力source

| owner                      | source_ref       | revision | scope             | currentness | 取得状態 |
| -------------------------- | ---------------- | -------- | ----------------- | ----------- | -------- |
| test-requirements-analysis | QA-REQ-ARTIFACT  | req-r3   | orders-release-q4 | current     | 取得済   |
| test-architecture-design   | QA-ARCH-ARTIFACT | arch-r5  | orders-release-q4 | stale       | 取得済   |

## 計画・資源

| 計画ID   | QA要求ref / revision   | architecture ref / revision | 対象scope         | level / type | suite・順序 | 担当    | 見積工数 | resource / 準備条件  |
| -------- | ---------------------- | --------------------------- | ----------------- | ------------ | ----------- | ------- | -------- | -------------------- |
| PLAN-002 | QA-REQ-ARTIFACT@req-r3 | QA-ARCH-ARTIFACT@arch-r5    | orders-release-q4 | API          | API suite   | QA team | 未見積   | API source確認が必要 |

## 開始・終了基準

| 種別 | 基準                                       | 対象scope         | evidence source / revision | 判定状態 |
| ---- | ------------------------------------------ | ----------------- | -------------------------- | -------- |
| 開始 | current architectureとAPI sourceを取得する | orders-release-q4 | QA-ARCH-ARTIFACT@arch-r5   | 未判定   |
| 終了 | 必須runの取得と終了基準を確認する          | orders-release-q4 | API-SOURCE-V2@unknown      | 未設定   |

## 予定source inventory・必要実行母集団

| population ID | source owner       | planned source_ref | planned revision | scope             | query / acquisition range          | execution unit  | target build | environment | 必須 / 任意 |
| ------------- | ------------------ | ------------------ | ---------------- | ----------------- | ---------------------------------- | --------------- | ------------ | ----------- | ----------- |
| POP-101       | testware-execution | API-SOURCE-V2      | unknown          | orders-release-q4 | API inventory lookup for build-111 | API logical run | build-111    | staging     | 必須        |

## source owner readback・取得／実行状態

| population ID | actual source owner | actual source_ref | actual revision | actual scope | acquired range | actual execution unit | actual build | actual environment | currentness | 取得状態 | 実行状態 | 結果状態 | source owner readback ref | 未取得 / 未実行理由          |
| ------------- | ------------------- | ----------------- | --------------- | ------------ | -------------- | --------------------- | ------------ | ------------------ | ----------- | -------- | -------- | -------- | ------------------------- | ---------------------------- |
| POP-101       | -                   | -                 | -               | -            | -              | -                     | -            | -                  | unknown     | 未取得   | 未実行   | 未判定   | -                         | API source inventoryが未取得 |

## Monitoring snapshot

| snapshot_ref | plan_ref / revision                 | scope             | target build | environment | 測定時点 | 計画population数 | 取得済数 | 部分取得数 | 未取得数 | 取得不能数 | 0件確認済み数 | 取得不明数 | 実行済み数 | 実行中数 | 未実行数 | 取消数 | 実行失敗数 | 結果不明数 | PASS数 | FAIL数 | 判定不能数 | 未判定数 | 対象なし数 | 全体判定 | 見積工数 | 実績工数 | 差異・未確定                              |
| ------------ | ----------------------------------- | ----------------- | ------------ | ----------- | -------- | ---------------- | -------- | ---------- | -------- | ---------- | ------------- | ---------- | ---------- | -------- | -------- | ------ | ---------- | ---------- | ------ | ------ | ---------- | -------- | ---------- | -------- | -------- | -------- | ----------------------------------------- |
| MON-2        | fixture://qa/plan/orders-q4@plan-r2 | orders-release-q4 | build-111    | staging     | initial  | 1                | 0        | 0          | 1        | 0          | 0             | 0          | 0          | 0        | 1        | 0      | 0          | 0          | 0      | 0      | 0          | 1        | 0          | blocked  | 未見積   | 未測定   | API source unavailable; no run is counted |

## Project risk

| project risk ID | 計画遂行上のrisk                 | 影響scope         | 根拠ref / revision    | 対応                     | owner   | 状態    |
| --------------- | -------------------------------- | ----------------- | --------------------- | ------------------------ | ------- | ------- |
| PROJ-RISK-002   | API source access is unavailable | orders-release-q4 | API-SOURCE-V2@unknown | source ownerへ取得を依頼 | QA lead | blocked |

## 是正処置

| action ID | 差異 / risk ref | action                             | owner   | 期限 / 状態      | 結果ref |
| --------- | --------------- | ---------------------------------- | ------- | ---------------- | ------- |
| CA-002    | PROJ-RISK-002   | request API inventory and revision | QA lead | 未設定 / blocked | 未取得  |

## 承認

| 対象scope         | artifact_ref                | revision | 承認主体・role | 承認証拠ref     | 状態 | 失効条件                   |
| ----------------- | --------------------------- | -------- | -------------- | --------------- | ---- | -------------------------- |
| orders-release-q4 | fixture://qa/plan/orders-q4 | plan-r1  | QA manager     | APPROVAL-PLAN-1 | 失効 | revision 2 is not approved |

## 未取得・blocked・再開

| 対象source / population | 状態   | 影響                      | 担当owner          | 再開条件                      |
| ----------------------- | ------ | ------------------------- | ------------------ | ----------------------------- |
| API-SOURCE-V2 / POP-101 | 未取得 | API実行の全体進捗は未確定 | testware-execution | source listとrevisionを読戻す |

## 改版履歴

| revision | 置換元ref / revision | 変更理由             | 影響scope         | 失効した承認 / 依存         |
| -------- | -------------------- | -------------------- | ----------------- | --------------------------- |
| plan-r2  | plan-r1              | API populationを追加 | orders-release-q4 | APPROVAL-PLAN-1は旧revision |
