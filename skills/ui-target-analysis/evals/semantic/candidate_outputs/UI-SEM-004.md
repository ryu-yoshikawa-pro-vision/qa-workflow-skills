# 安全な再開判断

## 現在の状態

Manifest mismatchがあるcanonical bytes、`v09` baseline、編集copyを別々に保全します。正本のManifestを手で修正せず、不正なcanonicalをcurrentとして採用しません。提示情報だけでは、直前のrequestがcommit済みか判断できません。

## 再開条件

まず許可された保存先の履歴またはwrite receiptで、`v09`がcurrentか、同一fingerprintのrequestがすでにcommitされたかを確認します。commit済みなら、その正式revisionを取得して独立readbackします。未commitと確認でき、`v09`が有効なcanonical baselineと確認できた場合だけ、同じsnapshot・同じrequestを用います。状態を確認できない場合はblockedを継続し、baselineからの復元や再適用をしません。

旧packageの`PAGE-002`、`UIOP-004`、conditional file applicability、Manifest、retired `PAGE-001`のchangelog履歴は維持します。package-local lockはremote CASや複数workspaceの履歴証明ではありません。
