---
name: feature-analysis
description: 初回製品分析・PR更新・merge・release・資料改版のUI/API/バッチ/連携/権限/データ処理について、機能ID・情報源母集団・開発差分・変更履歴を調査するときに使用する。
---

# 製品機能と開発差分の分析

## 実行契約

1. 対象案件の許可された情報源・基準revision・保存先を確認し、references/guidance.mdとreferences/data-contract.mdに従います。
2. Issue、仕様・設計、コード、既存テスト、PR全差分、必要な実対象観測を列挙します。取得できない資料・未完了pagination・未分析領域を隠しません。
3. UI・API・バッチ・外部連携・認可・データ処理を含む機能を安定IDと親子関係で同定します。ファイルpathを機能IDにせず、実装要素は別のrefに保持します。
4. 名称変更、追加、変更、分割、統合、削除、廃止に対し旧機能ID・根拠・revisionを維持します。未知の変更を影響なしに分類しません。
5. scripts/feature_registry.pyでsource inventory、feature hierarchy、candidate、変更分類、履歴、旧HEAD、分母0を検証します。結果のcompleteは宣言された情報源境界での機械検証であり、製品全機能の発見保証ではありません。
6. 案件の保存先がnative CASと履歴・独立readbackを保証できない場合は保存をblockします。認証済みの承認を得る前に対象外へ変更しません。
7. 下流へ機能ID・source refs/revisions・未分類・未知領域・成果物ref/revisionを渡します。仕様Authorityはspec-analysis、Product Riskはtest-analysis、正式TCNはtest-condition-designが正本です。

## リソース

- 分析手順: references/guidance.md
- 機械可読契約: references/data-contract.md
- 出力例: assets/output-template.md
- 解析・履歴検証: scripts/feature_registry.py
