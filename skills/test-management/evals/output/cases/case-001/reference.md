# テスト計画・モニタリング

## 成果物メタデータ

| 項目                           | 値                               |
| ------------------------------ | -------------------------------- |
| owner                          | test-management                  |
| artifact_ref                   | fixture://qa/plan/orders-q4      |
| revision                       | plan-r8                          |
| scope                          | orders-release-q4                |
| plan_version                   | 8                                |
| 状態                           | 進行中                           |
| 対象build / environment / 期間 | build-110 / staging / release-q4 |

## 入力source

| owner                      | source_ref                          | revision | scope             | currentness | 取得状態 | 承認状態 | 承認証拠ref     |
| -------------------------- | ----------------------------------- | -------- | ----------------- | ----------- | -------- | -------- | --------------- |
| test-requirements-analysis | fixture://qa/requirements/orders-q4 | req-r3   | orders-release-q4 | current     | 取得済   | 承認済み | APPROVAL-4      |
| test-architecture-design   | fixture://qa/architecture/orders-r1 | arch-r1  | orders-release-q4 | current     | 取得済   | 承認済み | APPROVAL-ARCH-1 |

## 計画・資源

| 計画ID   | QA要求ref / revision                               | architecture ref / revision                          | 対象scope         | level / type | suite・順序  | 担当    | 見積工数 | resource / 準備条件       |
| -------- | -------------------------------------------------- | ---------------------------------------------------- | ----------------- | ------------ | ------------ | ------- | -------- | ------------------------- |
| PLAN-001 | fixture://qa/requirements/orders-q4#QAR-001@req-r3 | fixture://qa/architecture/orders-r1#ARCH-001@arch-r1 | orders-release-q4 | API / system | E2E then API | QA team | 4h       | staging, test data loaded |

## 開始・終了基準

| 種別 | 基準                                     | 対象scope         | evidence source / revision   | 判定状態 |
| ---- | ---------------------------------------- | ----------------- | ---------------------------- | -------- |
| 開始 | stagingとtest dataが利用可能             | orders-release-q4 | ENV-READY@env-r2             | 満たす   |
| 終了 | 必須populationを取得し、未処理差異を記録 | orders-release-q4 | E2E-16@run-r1, API-21@run-r2 | 未判定   |

## 予定source inventory・必要実行母集団

| population ID | source owner       | planned source_ref | planned revision | scope             | query / acquisition range          | execution unit  | target build | environment | 必須 / 任意 |
| ------------- | ------------------ | ------------------ | ---------------- | ----------------- | ---------------------------------- | --------------- | ------------ | ----------- | ----------- |
| POP-001       | e2e-test-execution | E2E-16             | run-r1           | orders-release-q4 | logical primary run for release-q4 | logical E2E run | build-110    | staging     | 必須        |
| POP-002       | testware-execution | API-21             | run-r2           | orders-release-q4 | API logical run at build-110       | API logical run | build-110    | staging     | 必須        |

## source owner readback・取得／実行状態

| population ID | actual source owner | actual source_ref | actual revision | actual scope      | acquired range                     | actual execution unit | actual build | actual environment | currentness | 取得状態 | 実行状態 | 結果状態 | source owner readback ref | 未取得 / 未実行理由            |
| ------------- | ------------------- | ----------------- | --------------- | ----------------- | ---------------------------------- | --------------------- | ------------ | ------------------ | ----------- | -------- | -------- | -------- | ------------------------- | ------------------------------ |
| POP-001       | e2e-test-execution  | E2E-16            | run-r1          | orders-release-q4 | logical primary run for release-q4 | logical E2E run       | build-110    | staging            | current     | 取得済   | 実行済み | PASS     | READBACK://e2e/16@run-r1  | -                              |
| POP-002       | testware-execution  | API-21            | run-r2          | orders-release-q4 | API logical run at build-110       | API logical run       | build-110    | staging            | current     | 取得済   | 実行済み | FAIL     | READBACK://api/21@run-r2  | source ownerのraw resultを参照 |

## Monitoring snapshot

| snapshot_ref | plan_ref / revision                 | scope             | target build | environment | 測定時点    | 計画population数 | 取得済数 | 部分取得数 | 未取得数 | 取得不能数 | 0件確認済み数 | 取得不明数 | 実行済み数 | 実行中数 | 未実行数 | 取消数 | 実行失敗数 | 結果不明数 | PASS数 | FAIL数 | 判定不能数 | 未判定数 | 対象なし数 | 全体判定 | 見積工数 | 実績工数 | 差異・未確定                                                |
| ------------ | ----------------------------------- | ----------------- | ------------ | ----------- | ----------- | ---------------- | -------- | ---------- | -------- | ---------- | ------------- | ---------- | ---------- | -------- | -------- | ------ | ---------- | ---------- | ------ | ------ | ---------- | -------- | ---------- | -------- | -------- | -------- | ----------------------------------------------------------- |
| MON-8        | fixture://qa/plan/orders-q4@plan-r8 | orders-release-q4 | build-110    | staging     | after-run-2 | 2                | 2        | 0          | 0        | 0          | 0             | 0          | 2          | 0        | 0        | 0      | 0          | 0          | 1      | 1      | 0          | 0        | 0          | 進行中   | 4h       | 3h       | API-21のFAILは実行ownerのraw resultを参照。終了基準は未判定 |

## Project risk

| project risk ID | 計画遂行上のrisk                        | 影響scope         | 根拠ref / revision | 対応                         | owner   | 状態   | 状態証拠ref | 承認主体・role |
| --------------- | --------------------------------------- | ----------------- | ------------------ | ---------------------------- | ------- | ------ | ----------- | -------------- |
| PROJ-RISK-001   | API failure diagnosis may delay closure | orders-release-q4 | API-21@run-r2      | source ownerへ原因分析を依頼 | QA lead | 対応中 | -           | -              |

## 是正処置

| action ID | 差異 / risk ref | 影響scope         | action                                | owner              | 期限 / 状態     | 結果ref | 承認主体・role |
| --------- | --------------- | ----------------- | ------------------------------------- | ------------------ | --------------- | ------- | -------------- |
| CA-001    | PROJ-RISK-001   | orders-release-q4 | API failure diagnosis and retest plan | testware-execution | 未設定 / 対応中 | 未取得  | -              |

## 差異・未処理事項

| 差異ID | 影響scope | 差異 | 根拠ref / revision | 対応 | owner | 状態 | 状態証拠ref | 承認主体・role |
| ------ | --------- | ---- | ------------------ | ---- | ----- | ---- | ----------- | -------------- |

## 承認

| 対象scope         | artifact_ref                | revision | 承認主体・role | 承認証拠ref     | 状態     | 失効条件                     |
| ----------------- | --------------------------- | -------- | -------------- | --------------- | -------- | ---------------------------- |
| orders-release-q4 | fixture://qa/plan/orders-q4 | plan-r8  | QA manager     | APPROVAL-PLAN-8 | 承認済み | plan revision / scope change |

## 未取得・blocked・再開

| 対象source / population | 状態 | 影響 | 担当owner | 再開条件 |
| ----------------------- | ---- | ---- | --------- | -------- |

## 改版履歴

| revision | 置換元ref / revision | 変更理由           | 影響scope         | 失効した承認 / 依存 |
| -------- | -------------------- | ------------------ | ----------------- | ------------------- |
| plan-r8  | plan-r7              | run evidenceを反映 | orders-release-q4 | approval refreshed  |
