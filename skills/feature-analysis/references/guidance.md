# 情報源・機能階層・変更の判断

許可された案件root・source境界だけを調べます。Issue・仕様・設計・製品実装・既存テスト・PR差分のrevision、対象範囲、pagination、権限拒否、解析不能な場所をsource別に保持します。情報源取得完全性と製品全機能の発見完全性を混同しません。

初回には全対象候補を根拠付きで列挙し、PR更新・rebase・merge・release・資料改版の際には前回正本と現時点のsource revisionを比較します。変更ファイル件数は機能件数ではありません。

製品→領域→機能→サブ機能の必要な階層を持ち、UI・API・バッチ・認可・データ処理・外部連携を含めます。複数の実装要素が一機能を構成できます。semantic identityを変更しないpath移動では同じ機能IDを使用します。分割・統合・廃止では元IDを残し、履歴のfrom_ids/to_idsで旧機能との対応を保持します。

差分は根拠に基づいてimpact / no_impact / out_of_scope / unclassified / unresolvedを判定します。対象外とするなら承認refを持たせますが、その文字列の実認証は承認ownerの責務です。specificationの期待動作は実装の観測事実から推測して確定しません。

実providerのnative create-if-absent／CAS・過去revision・readbackが未確認なら、更新案と分析結果だけを残します。同じoperation_idの再受付、旧HEAD、競合、停止再開は上流正本を再読込し、無条件再書込みを避けます。

## Git情報源の取得

`scripts/git_source_inventory.py`に許可されたcheckout rootをrepository_root・authorized_rootとして同一の正本pathで渡し、base_sha／head_shaは完全なcommit SHAで指定します。初回はbase_sha=nullです。Gitファイル一覧とrename/moveのbefore/after pathを証拠として受取り、各ファイルを自動的に別機能と数えません。Gitの出力が大きすぎる・権限不足・HEAD不一致ならcompleteとせず再取得します。Git以外のIssue／仕様・設計情報源は権限のある提供経路で列挙し、未接続ならpartial／unavailableを保持します。
