# Regression Run Plan

- **種別:** selected Run。complete baselineの3 member全体を実行するfull Runではありません。
- **選択:** TC-201。checkout変更に関連するTCとして明示されています。
- **除外:** TC-202。ユーザー指定による除外です。Riskの検証済み根拠には数えません。
- **残るbaseline member:** 1件のrefが提示されていないため、このRunでの候補・選択・除外を確認できません。

## Risk R-8

- 既存Risk「決済二重計上」のscoreは変更しません。
- TCとR-8のtraceabilityが提示されていないため、R-8に関連するTCと、このRunで残る未検証影響は未解決です。TC-202の除外をR-8の検証完了とは扱いません。

## 実行状態

**開始前にブロック。** TC-201のrequired routeと、R-8に関連するTCのtraceabilityを確認できていません。routeが確定するまで実行開始・executed計上はできません。
