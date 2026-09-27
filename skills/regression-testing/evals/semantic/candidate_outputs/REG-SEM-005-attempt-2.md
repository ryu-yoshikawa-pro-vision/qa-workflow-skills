## 対応ルート

1. **原因調査:** `question-analysis`へ送り、FAIL時の期待結果に必要な条件と仕様authorityを確認する。既存仕様の解釈やauthorityの確定が必要なら、`spec-analysis`へ引き継ぐ。原因の確定とFAILの再判定は担当ownerに委ねる。
2. **FAILの記録:** 既存のmanual実行結果と証拠をActivityへ参照・投影し、結果を再解釈しない。実行開始はPR #12の契約に沿って確認する。TC-401は有効なcurrent TCとして維持する。
3. **修正確認:** 修正後、同じcurrent TC-401を`test-execution`で再実行する。専用のfix confirmation artifactやstateは作らない。
4. **周辺Regression:** 修正確認とは別目的のRunとして扱う。開始前にsourceとbaselineのcurrentnessを確認し、current Riskや過去Findingなどから候補・選択・除外理由を記録する。TCとRiskのtraceabilityが確認できない場合は推測せず未解決とする。
