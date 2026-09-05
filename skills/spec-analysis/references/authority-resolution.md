# Current Effective Authority 詳細解決

このreferenceは、単一で明確なAuthorityだけでは判断できない場合に読みます。

対象例:

- 複数情報源が同じ挙動を記述している
- version / scopeが複数ある
- Canonical Decisionが既存SPEC / Decisionと重なる
- Decisionの補足 / 上書き / 置換関係を判定する
- 承認済みASMの適用範囲を判断する
- 有効Authority間の競合を解消する

Current Effective Authorityの具体的解決アルゴリズムは`spec-analysis`がSingle Source of Truthです。他Skillへこの手順を複製しません。

## 解決順序

対象スコープごとに次の順で解決します。

1. Canonical Decision Registryから、状態が`有効`で対象スコープに適用される`DECISION`をすべてAuthority候補として識別する。既存`SPEC` / 旧`DECISION`を上書きしていない補足Decisionも候補に含める
2. 有効`DECISION`が既存`SPEC` / 旧`DECISION`と同じ挙動領域に重なる場合は、補足 / 上書き / 置換関係、関連Authority、影響範囲から現在有効な内容を解決する。未定義領域を補足するDecisionは既存Authorityと共存できる
3. `SPEC`は、まず各情報源内で対象Version / Scopeに適用される現行版を版・更新時点から特定する
4. 現行版の`SPEC`候補間では案件固有の情報源優先順位を適用する。鮮度だけを理由に低優先度情報源を高優先度情報源より優先しない
5. `承認済み ASM`は、有効な`SPEC` / `DECISION`で未定義の隙間だけを暫定的に補える
6. `ASM`が有効な`SPEC` / `DECISION`と競合する場合、`ASM`を優先せず、正式な仕様更新または`DECISION`として解決する
7. 同一スコープで複数の有効Authorityが競合し、Decision関係・情報源優先順位等で解決できない場合は`question-analysis`へ送る

## Decision状態

- `有効`の`DEC-xxx`だけをCurrent Effective Authority候補にする
- `撤回` / `置換済み`Decisionを現在の根拠に使わない
- 補足Decisionは既存Authorityを置換しなくても同一スコープで共存できる
- 上書き / 置換する場合は関連Authorityと影響範囲をCanonical Registryで追跡する

## SPECのversion / 情報源

- 鮮度はまず同一情報源内で対象Version / Scopeに適用される現行版を特定するために使う
- 複数情報源間では案件固有の情報源優先順位を適用する
- 鮮度だけを理由に、低優先度情報源で高優先度情報源を上書きしない
- 競合証拠は消さず、採用したAuthorityと合わせて追跡可能に残す

## Assumption

- `承認済み ASM`だけが未定義の隙間を暫定的に補える
- AI自身の判断でAssumptionを承認済みにしない
- 有効な`SPEC` / `DECISION`をASMで上書きしない
- 正式挙動として確定した内容は、仕様更新または`DECISION`へ正規化する

## 正規化ビュー

解決後は、対象範囲のCurrent Effective Authorityを次の情報とともに明示します。

- Authority ID
- type（`SPEC` / `DECISION` / `承認済み ASM`）
- 現在有効な内容
- 適用範囲
- 情報源 / Canonical Registry
- 関係（独立 / 補足 / 上書き / 置換 / 未定義部分の補完）
- 関連Authority ID

## Blocker

次の場合は`question-analysis`へ送り、解決不能な影響範囲をBlockedとします。

- 同一スコープの有効Authorityが相互排他的
- Decision関係が不足して採用内容を決められない
- 案件固有情報源優先順位が必要だが未定義
- version / scopeを特定できず複数SPECのどれが現行か決められない

解決可能な他範囲は継続します。
