# 人間編集案の差分準備

## 変更案

- `PAGE-003`のlabel変更と`@draft:preferences`の新規PAGEをUI table差分として準備します。
- `PAGE-002`の削除は、提示された理由・承認ref・retirement evidenceを持つ明示retireとしてwriter requestへ変換します。
- 元の`v04` snapshot、current snapshot、isolated edit copy、Q06配置合意、UI owner review、各変更のevidenceを照合します。

## 正本更新と証明範囲

差分helperは`ui_target_package.py materialize`用requestを返すだけです。canonical packageをこの準備段階で書き込みません。実provider、authenticated approver、共有runtime、native CASがないので、正式保存・承認認証・共有readbackは未検証です。独立fixtureでwriter、履歴、inspect/validateを通せても、その範囲だけをlocal acceptanceとして報告します。
