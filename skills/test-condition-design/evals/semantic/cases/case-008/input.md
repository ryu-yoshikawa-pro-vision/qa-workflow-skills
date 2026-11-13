# Eval Input

分類木factorは`browser={Chrome, Firefox}`、`os={Windows, Linux, macOS}`、`auth={password, SAML}`。Authority `SPEC-CTD-008`により`Firefox + macOS + SAML`は成立不能。全factor pairwiseと、subset `{browser, os, auth}`の3-wiseを採用し、classification adapterから既存comb childへ展開する。再利用する既存comb childのstable model keyは`comb-008`（current Machine Entityで確認済み）。

テスト要求`TR-CTD-008`（システムテスト）は「browser・os・authの組合せを制約付きで確認すること」を求める。採用理由（coverage_selection_reason）は、承認済みでcurrentな`SPEC-CTD-008`が定める「設定依存の組合せ欠陥を、全factorはpairwise、subset `{browser, os, auth}`は3-wiseで確認する」ことである。current modelのMachine Entityは確認済み。
