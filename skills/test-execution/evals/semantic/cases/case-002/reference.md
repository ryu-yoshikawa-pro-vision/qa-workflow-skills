# Reference
- 再実行は別成果物 / versionとし、前回成果物参照と前回TC参照を両方記録する。
- MCPが利用不可なら既存CLIを次に評価する。CLIで必要能力を満たせるならLibraryへ切り替えない。
- CLIからLibraryへ切り替える場合、開始済みTCの状態継続を確認する。確認できない場合は判定不能で閉じ、同一成果物で同じTCを再実行しない。
- dummy secretは実行前YAML、報告、証跡説明へ複製しない。既存secret参照がない場合に名前を創作しない。
- 同scopeの準備・TC操作・後処理・cleanupは1回の定義と上限を共有し、結果不明も消費とする。TCは直列に進め、cleanup未完了なら対応範囲を完了にしない。
- UIを確かめる操作をAPI / DB / storage等で置き換えない。repo runnerや永続E2E責務を取り込まない。
