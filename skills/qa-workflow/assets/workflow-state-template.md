# ワークフロー状態 出力テンプレート

必要な場合だけ使用します。ワークフロー状態はSkill実行の前提ではありません。

- ワークフロー全体状態: 未開始 / 実行中 / 部分完了（ブロック中あり） / ブロック中 / 完了
- 開始Skill:
- 開始対象 / 実行範囲: 複数用途Skillの場合は正規値
- 最終Skill:
- 最終対象 / 実行範囲: 複数用途Skillの場合は正規値

| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
| spec-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| question-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-analysis | テスト分析 / E2E対象選定のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-requirement-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-condition-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-case-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| coverage-analysis | テスト設計 / TC → E2E実装 / E2E実装 → 実行結果のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| adversarial-review | テスト設計成果物 / E2E実装のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-implementation |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-result-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-reporting |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-target-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |

## runtime状態（runtime dispatch時だけ表示）

| Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | supported / partial / unsupported / unknown | ready / unresolved / blocked | current / stale | ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run | Yes / No | Yes / No | outside_supported_subset / python_unavailable /  |  |

runtime行は保存されたMachine Runtime Input / ResultとMachine Entityから転記し、`can_complete`や人間向け要約から推測しません。scopeが0件の場合はこの表を表示せず、runtimeをdispatchしない既存経路を維持します。
