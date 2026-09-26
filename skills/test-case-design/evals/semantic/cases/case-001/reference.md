# 判定根拠
## 入力の正本
- Coverage Item表を再解釈せず、`TCN-001-CI01` Machine Entityの`content.execution`を実行意味の正本として使う。
- `precondition`で既存設定「週次レポート」を確認し、`input.name`の「年次レポート」を入力して保存する。
- `test_data_requirement_refs`の`data:setting-name-valid`を満たす具体値を使う。
- `ENV-CHROME-EDITOR`のChrome・更新権限の前提を手順開始時に確認する。

## Source of Truth
- 編集者でログインし、既存設定「週次レポート」を編集開始できる前提が必要。
- 1〜50文字の有効名称を具体値として入力し保存する操作が必要。
- 保存後、設定一覧でその新名称が表示されることが観測可能なOracle。
- トーストは仕様にないためOracleへ要求しない。
- Coverage Itemの意図は「正常保存 + 一覧反映」。
- Machine Entityにない操作・期待結果を追加せず、`execution`に含まれる観測だけを具体的な手順とOracleへ展開する。

## 許容される解釈
- 具体的な新名称は1〜50文字なら任意。
