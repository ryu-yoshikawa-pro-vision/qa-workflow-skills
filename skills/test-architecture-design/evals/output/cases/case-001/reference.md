# テストアーキテクチャ設計

## 成果物メタデータ

| 項目         | 値                                  |
| ------------ | ----------------------------------- |
| owner        | test-architecture-design            |
| artifact_ref | fixture://qa/architecture/orders-r1 |
| revision     | arch-r1                             |
| scope        | orders-release-q4                   |
| 状態         | 承認済み                            |

## 入力source・依存

| owner                      | source_ref                          | revision | scope              | currentness | 取得状態 |
| -------------------------- | ----------------------------------- | -------- | ------------------ | ----------- | -------- |
| test-requirements-analysis | REQUEST-01@doc-7                    | doc-7    | orders-release-q4  | current     | 取得済   |
| test-requirements-analysis | fixture://qa/requirements/orders-q4 | req-r3   | orders-release-q4  | current     | 取得済   |
| test-analysis              | RISK-001@risk-5                     | risk-5   | orders.update      | current     | 取得済   |
| architecture owner         | ARCH-SOURCE@arch-4                  | arch-4   | orders.persistence | current     | 取得済   |

## テストアーキテクチャ割当

| 割当ID   | target_ref         | target種別    | QA要求ref / revision                               | level          | type        | 方式・検証分担                        | environment / data             | runner / tool          | 選択根拠             | 根拠ref / revision | 状態・準備条件        | owner               |
| -------- | ------------------ | ------------- | -------------------------------------------------- | -------------- | ----------- | ------------------------------------- | ------------------------------ | ---------------------- | -------------------- | ------------------ | --------------------- | ------------------- |
| ARCH-001 | orders.update      | API target    | fixture://qa/requirements/orders-q4#QAR-001@req-r3 | API            | functional  | API contractと応答を検証              | staging-api / synthetic-orders | API runner未接続       | 明示指定             | REQUEST-01@doc-7   | 準備未確認            | testware-execution  |
| ARCH-002 | orders.update      | business flow | fixture://qa/requirements/orders-q4#QAR-001@req-r3 | システム       | functional  | system levelの別分担を保持            | staging / synthetic-orders     | Playwright候補         | 承認済みarchitecture | ARCH-SOURCE@arch-4 | 実装可否は別owner確認 | e2e-test-inspection |
| ARCH-003 | orders.persistence | component     | fixture://qa/requirements/orders-q4#QAR-002@req-r3 | コンポーネント | reliability | persistence componentの異常応答を検証 | component-env / fixture未確認  | component runner未接続 | 承認済みarchitecture | ARCH-SOURCE@arch-4 | data準備が必要        | testware-execution  |

## レベル優先・競合

| target_ref         | 明示指定 | 承認済み割当   | 既定値   | 適用判断                                            | 競合・判断元            |
| ------------------ | -------- | -------------- | -------- | --------------------------------------------------- | ----------------------- |
| orders.update      | API      | API・システム  | システム | APIを明示指定で採用しsystem levelも別分担として保持 | levelを単一値に丸めない |
| orders.persistence | -        | コンポーネント | システム | コンポーネントを承認済みarchitectureから採用        | 既定値は未使用          |

## 非機能・環境制約

| 品質特性    | 対象ref            | 測定方式                    | 閾値source / revision | environment / data | 準備状態 | 残る制約                   |
| ----------- | ------------------ | --------------------------- | --------------------- | ------------------ | -------- | -------------------------- |
| reliability | orders.persistence | component failure injection | RISK-001@risk-5       | component-env      | 未準備   | tool ownerと準備条件を確認 |

## 承認

| 対象scope         | artifact_ref                        | revision | 承認主体・role        | 承認証拠ref     | 状態     | 失効条件                       |
| ----------------- | ----------------------------------- | -------- | --------------------- | --------------- | -------- | ------------------------------ |
| orders-release-q4 | fixture://qa/architecture/orders-r1 | arch-r1  | QA architecture owner | APPROVAL-ARCH-1 | 承認済み | sourceまたは割当revisionの変更 |

## 変更影響・handoff

| 変更ref / revision | 影響scope          | 要再確認のowner / ref                                  | 保持するcurrent成果物      | resume owner             | 理由                        |
| ------------------ | ------------------ | ------------------------------------------------------ | -------------------------- | ------------------------ | --------------------------- |
| ARCH-SOURCE@arch-4 | orders.persistence | test-analysis/RISK-001、test-requirement-design/TR-001 | orders.updateのcurrent割当 | test-architecture-design | persistence level割当の改版 |

## 未解決・blocked

| 項目          | scope              | 担当               | 状態    | 再開条件                    |
| ------------- | ------------------ | ------------------ | ------- | --------------------------- |
| component環境 | orders.persistence | testware-execution | blocked | environmentとdata準備を確認 |

## 履歴

| revision | 置換元ref / revision | 変更理由 | 影響scope         | 再確認する依存                    |
| -------- | -------------------- | -------- | ----------------- | --------------------------------- |
| arch-r1  | -                    | 初回割当 | orders-release-q4 | REQUEST-01、RISK-001、ARCH-SOURCE |
