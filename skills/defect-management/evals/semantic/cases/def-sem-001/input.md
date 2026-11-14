# Semantic eval input

原因が仮説のFAILを欠陥候補として扱う

E2E実行（run:e2e-101、build:41）でTC-007がFAILした。実行ownerの分析では原因は「決済APIの一時的な不具合かテストデータの不整合かは未確定（確度: 低）」。期待結果の根拠はSPEC-012 r5。QA担当は「今のうちに正式なIssueとして登録してclose条件も設定してほしい」と依頼している。どう扱うか。
