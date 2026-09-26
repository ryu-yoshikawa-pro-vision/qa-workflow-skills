# Eval Input
状態は`draft`、`editing`、`published`。有効遷移は`draft --open_editor--> editing`、`editing --publish--> published`、`published --reset--> draft`。round-tripは`draft`開始で開始stateへ戻る上記3遷移、2-switchはそのpathの連続する2遷移ごとに展開する。各2-switch windowもこのpath上で実行し、windowが`editing`から始まる場合は指定開始state `draft`から`editing`へ到達するsetup prefixを含める。3遷移はAuthorityで定義済み。
