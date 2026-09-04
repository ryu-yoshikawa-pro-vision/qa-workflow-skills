# 仕様・不明点レビュー Probes

このreferenceは、仕様分析 / Current Effective Authority / 不明点 / Assumptionを反証レビューする場合だけ読みます。

詳細なAuthority解決アルゴリズムは`spec-analysis`、未解決事項分類・回答正規化は`question-analysis`をSingle Source of Truthとします。

## 仕様分析 / Current Effective Authority

主に次を疑います。

- 仕様・Decision・Inference・Unknownの分類が混ざっていないか
- 分類とIDが一致しているか
- Canonical Registryの同じDecision / Assumptionを別IDで重複管理していないか
- 対象スコープの有効Authorityが正規化ビューから欠落していないか
- 古い / 撤回済み / 置換済みの根拠を現在有効として扱っていないか
- 実装や既存Test Caseを、根拠なく仕様Authorityへ昇格していないか
- Authority競合を未解決のまま下流へ流していないか
- 対象範囲外の周辺仕様を無根拠に追加していないか

Authorityの優先関係・version・Decision / ASM詳細判断が必要なら、`spec-analysis`の契約に照らし、ここで別アルゴリズムを作りません。

## 不明点 / Assumption

主に次を疑います。

- 本来下流の正しさを成立させない論点を非Blocker扱いしていないか
- 逆に、局所論点を必要以上に全体Blockerへ広げていないか
- 未承認Assumptionが完成済み期待結果 / PASS条件へ混入していないか
- AI自身がAssumptionを承認済みにしていないか
- 回答済み論点が適切なAuthorityへ正規化されず、生の会話情報のまま下流へ流れていないか
- 解決済み事項を再質問していないか
- 実装差分だけを理由に不要な仕様質問へ戻していないか

Blocker / 要確認 / 仮定可能 / 提案・任意の詳細分類は`question-analysis`を正本とします。
