# 非E2E実行評価

Vitestの同名testがあり、部分選択された一件はskip、run前の共有fixture予約とcleanupが未確認。runnerのraw PASSだけで全TC PASSとせず、開始・未取得・診断・再開を分離する。
