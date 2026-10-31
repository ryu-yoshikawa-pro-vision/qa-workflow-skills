# E2Eテスト結果分析 deterministic case 001

`assets/output-template.md`を使い、retry後も初回FAILを消さず、cleanup未確認を保持して分析する。追加証拠が必要なら実行担当を`e2e-test-execution`とする。

このcaseには初回・retryのPlaywright結果、report、trace、cleanup log、実行参照が含まれていません。依頼文にある「初回FAIL」「cleanup未確認」は分析対象の報告内容であり、実行証拠として再解釈しないでください。結果の判定は保留し、不足する実行証拠の回収を`e2e-test-execution`へroutingしてください。分析中にPlaywrightを直接起動しないでください。
