# Eval Input
分類木factorは`browser={Chrome, Firefox}`、`os={Windows, Linux, macOS}`、`auth={password, SAML}`。Authority `SPEC-CTD-008`により`Firefox + macOS + SAML`は成立不能。全factor pairwiseと、subset `{browser, os, auth}`の3-wiseを採用し、classification adapterから既存comb childへ展開する。
