# 人間編集案の差分準備

## 変更案

- `PAGE-003`のlabel変更と`@draft:preferences`の新規PAGEをUI table差分として準備します。
- `PAGE-002`の削除は、提示された理由・承認ref・retirement evidenceを持つ明示retireとしてwriter requestへ変換します。
- 変更行が許可されたUI-owned scope内であることを確認します。scopeやowner境界を確認できない行、またはout-of-scopeの変更はblockedにします。
- 元の`v04` snapshot、current snapshot、isolated edit copy、Q06配置合意、UI owner review、各変更のevidenceを照合します。
- UI構造の変更だけを扱い、ラベルの業務上の意味、期待結果、認可、Authorityを決めません。期待仕様との関係が不明な点は`spec-analysis`へ戻します。
- UI ownerのreview ref、Q06配置合意、変更ごとのsource evidence、retire理由・承認ref・retirement evidenceをそれぞれ確認します。refの存在は承認者の認証を意味しないため、owner verifierが使えないこの実行では正式承認を主張しません。

## 正本更新と証明範囲

差分helperは既存single writerの`ui_target_package.py materialize`用requestを返すだけです。helperはcanonical packageへ書き込まず、作業copyのgenerated/control fileをコピーしません。writer後はreceiptと独立readbackを確認し、stable ID割当、履歴、無関係row、`inspect`／`validate`を再確認します。実provider、authenticated approver、共有runtime、native CASがないので、正式保存・承認認証・共有readbackは未検証です。独立fixtureでwriter、履歴、inspect/validateを通せても、その範囲だけをlocal acceptanceとして報告します。

競合や保存応答消失では編集copy、元snapshot、元request/fingerprintを保全します。responseが失われcommit状態が不明な場合は履歴／receiptを照合し、既存writerが冪等な再送を保証する場合に限り同一request／snapshot／fingerprintを再送して独立readbackします。writerが`stale_snapshot`を返す場合、またはcurrent packageが変わっている場合は旧requestを再送せずblockedにします。fresh `inspect`後、ownerの再レビューを得て再準備し、新しいdraft keyは旧requestが未commitでID未割当と確認できた場合だけ使います。状態・currentnessを確認できない場合はblockedを継続します。
