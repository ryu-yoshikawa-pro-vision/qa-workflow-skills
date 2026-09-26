# 判定根拠
## Source of Truth
- 1は生きた実対象で今回範囲を確認するため`test-target-inspection`へ進める。既存資料やrepo情報だけでcurrentと判定せず、通常の設計workflowへ無条件挿入もしない。
- 2はAIが詳細TCを今回runとして操作・観測するため`test-execution`へ進める。repoにPlaywright E2Eがあることだけで既存runnerへ移さない。
- `e2e-test-inspection` / `e2e-test-implementation` / `e2e-test-execution`はrepoへ残すPlaywright E2E資産のinspection・実装・正式runner実行を担当し、今回runだけの手動TC実行と責務を混ぜない。

## 禁止される推測
- repo情報や古いテスト対象資料だけで1をcurrent扱いしない。
- 詳細TCの実行をe2e-test-executionへ誤routeしない。
- 今回runのためだけに永続Playwright実装を追加しない。
