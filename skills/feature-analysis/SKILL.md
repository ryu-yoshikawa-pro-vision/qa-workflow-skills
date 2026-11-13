---
name: feature-analysis
description: 製品の機能階層・機能ID・情報源母集団・開発差分・変更履歴（UI/API/バッチ/連携/権限/データ処理）を、初回製品分析・PR更新・merge・release・資料改版のときに調査する。「機能一覧・機能ID・機能差分・source revisionの更新や確認」を求められたら、自分でファイルを調べる前に必ずこのSkillを読み込んで従う。
---

# 製品機能と開発差分の分析

## 実行契約

1. 対象案件の許可された情報源・基準revision・保存先を確認し、references/guidance.mdとreferences/data-contract.mdに従います。
2. Issue、仕様・設計、コード、既存テスト、PR全差分、必要な実対象観測を列挙します。取得できない資料・未完了pagination・未分析領域を隠しません。
3. UI・API・バッチ・外部連携・認可・データ処理を含む機能を安定IDと親子関係で同定します。ファイルpathを機能IDにせず、実装要素は別のrefに保持します。
4. 名称変更、追加、変更、分割、統合、削除、廃止に対し旧機能ID・根拠・revisionを維持します。未知の変更を影響なしに分類しません。
5. Gitの全ファイルとbase→headの差分は許可されたlocal checkoutのfull commit SHAに対しscripts/git_source_inventory.pyで列挙します。renameをold/new pathで記録し、列挙失敗・未対応データをcompleteにしません。Issueや外部設計の取得には許可済みの提供手段を使用します。
6. scripts/feature_registry.pyでsource inventory、feature hierarchy、candidate、変更分類、履歴、旧HEAD、分母0を検証します。結果のcompleteは宣言された情報源境界での機械検証であり、製品全機能の発見保証ではありません。
   Git差分がある場合、scripts/reconcile_git_coverage.pyでGit列挙した全変更pathと機能差分台帳を突き合わせます。未登録変更を分類済みと報告せず、製品CIへはこの照合結果も渡します。gitlink／submodule内部を未取得ならsourceはincompleteです。
7. 明示選択されたローカル保存先ではproject-context/scripts/artifact_store.pyとpersist_snapshotでCAS・履歴・独立readbackを検証します。code sourceを含む台帳の保存には信頼済み呼出し元が指定したgit_inventory_requestsを必須とし、Git全体・差分を再取得して照合します。未取得のsubmoduleや未登録DIFがあれば保存をblockします。未選定の遠隔保存providerの代用にはしません。
8. 案件の保存先がnative CASと履歴・独立readbackを保証できない場合は保存をblockします。認証済みの承認を得る前に対象外へ変更しません。
9. 下流へ機能ID・source refs/revisions・未分類・未知領域・成果物ref/revisionを渡します。仕様Authorityはspec-analysis、Product Riskはtest-analysis、正式TCNはtest-condition-designが正本です。

## リソース

- 分析手順: references/guidance.md
- 機械可読契約: references/data-contract.md
- 出力例: assets/output-template.md
- 解析・履歴検証: scripts/feature_registry.py
- Git全体snapshot・差分列挙: scripts/git_source_inventory.py
- Git差分と機能差分台帳の照合: scripts/reconcile_git_coverage.py

Git管理の機能台帳JSONを正本にする案件では、`project-context/scripts/git_artifact_store.py`を`persist_snapshot`へ明示的に渡すことができます。Git branchのcommit SHAによるnative CASと履歴読戻しを利用し、SQLite・Gitの二重正本を作りません。どちらも選定されていない案件では、保存をblockedとします。
