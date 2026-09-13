# 判定根拠
## Source of Truth
- inspection相当のrepo / E2E事実がないため、開始は`qa-workflow → e2e-test-inspection`とする。
- inspectionで対象、確認済み期待挙動、既存構造、URL / origin、認証・データ・cleanup、安全な証跡を確認した後、`e2e-test-implementation`へ進める。
- TCなし経路ではTC / TC IDを生成せず、明示E2E対象とinspectionで確認した期待挙動を直接引き継ぐ。
- 対象選定要求がないため`test-analysis`、TC作成要求がないため`test-case-design`を必須化しない。

## 禁止される推測
- inspectionを省略して実装を開始しない。
- 未確認のlocator、fixture、URL、データ準備、期待挙動を補わない。
