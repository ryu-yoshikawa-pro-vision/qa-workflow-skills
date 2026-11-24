# テスト計画・モニタリング

## 成果物メタデータ

| 項目                           | 値              |
| ------------------------------ | --------------- |
| owner                          | test-management |
| artifact_ref                   |                 |
| revision                       |                 |
| scope                          |                 |
| plan_version                   |                 |
| 状態                           | 草案            |
| 対象build / environment / 期間 |                 |

## 入力source

| owner | source_ref | revision | scope | currentness | 取得状態 | 承認状態 | 承認証拠ref |
| ----- | ---------- | -------- | ----- | ----------- | -------- | -------- | ----------- |

## 計画・資源

| 計画ID | QA要求ref / revision | architecture ref / revision | 対象scope | level / type | suite・順序 | 担当 | 見積工数 | resource / 準備条件 |
| ------ | -------------------- | --------------------------- | --------- | ------------ | ----------- | ---- | -------- | ------------------- |

## 開始・終了基準

| 種別 | 基準 | 対象scope | evidence source / revision | 判定状態 |
| ---- | ---- | --------- | -------------------------- | -------- |

## 予定source inventory・必要実行母集団

| population ID | source owner | planned source_ref | planned revision | scope | query / acquisition range | execution unit | target build | environment | 必須 / 任意 |
| ------------- | ------------ | ------------------ | ---------------- | ----- | ------------------------- | -------------- | ------------ | ----------- | ----------- |

## source owner readback・取得／実行状態

| population ID | actual source owner | actual source_ref | actual revision | actual scope | acquired range | actual execution unit | actual build | actual environment | currentness | 取得状態 | 実行状態 | 結果状態 | source owner readback ref | 未取得 / 未実行理由 |
| ------------- | ------------------- | ----------------- | --------------- | ------------ | -------------- | --------------------- | ------------ | ------------------ | ----------- | -------- | -------- | -------- | ------------------------- | ------------------- |

## Monitoring snapshot

| snapshot_ref | plan_ref / revision | scope | target build | environment | 測定時点 | 計画population数 | 取得済数 | 部分取得数 | 未取得数 | 取得不能数 | 0件確認済み数 | 取得不明数 | 実行済み数 | 実行中数 | 未実行数 | 取消数 | 実行失敗数 | 結果不明数 | PASS数 | FAIL数 | 判定不能数 | 未判定数 | 対象なし数 | 全体判定 | 見積工数 | 実績工数 | 差異・未確定 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Project risk

| project risk ID | 計画遂行上のrisk | 影響scope | 根拠ref / revision | 対応 | owner | 状態 | 状態証拠ref | 承認主体・role |
| --------------- | ---------------- | --------- | ------------------ | ---- | ----- | ---- | ----------- | -------------- |

## 是正処置

| action ID | 差異 / risk ref | 影響scope | action | owner | 期限 / 状態 | 結果ref | 承認主体・role |
| --------- | --------------- | --------- | ------ | ----- | ----------- | ------- | -------------- |

## 差異・未処理事項

| 差異ID | 影響scope | 差異 | 根拠ref / revision | 対応 | owner | 状態 | 状態証拠ref | 承認主体・role |
| ------ | --------- | ---- | ------------------ | ---- | ----- | ---- | ----------- | -------------- |

## 承認

| 対象scope | artifact_ref | revision | 承認主体・role | 承認証拠ref | 状態 | 失効条件 |
| --------- | ------------ | -------- | -------------- | ----------- | ---- | -------- |

## 未取得・blocked・再開

| 対象source / population | 状態 | 影響 | 担当owner | 再開条件 |
| ----------------------- | ---- | ---- | --------- | -------- |

## 改版履歴

| revision | 置換元ref / revision | 変更理由 | 影響scope | 失効した承認 / 依存 |
| -------- | -------------------- | -------- | --------- | ------------------- |
