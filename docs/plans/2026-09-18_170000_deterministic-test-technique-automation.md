# テスト分析・テスト技法の決定論的自動化Plan

このPlanは長文化するため、内容を見出し境界で分割しています。レビュー・実装時は以下5ファイルを順に読み、全体を1つのPlanとして扱ってください。

## 対象ブランチ

`feat/deterministic-test-technique-automation`

## 基準

- 基準branch: `main`
- 基準commit: `3510e6ffce87ba8c025ebde22f9947dbb6074f9c`
- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`

## 構成

1. [目的・現状・自動化対象の全体一覧](./2026-09-18_170000_deterministic-test-technique-automation_01_scope-and-inventory.md)
2. [実行時アーキテクチャ・入力出力契約](./2026-09-18_170000_deterministic-test-technique-automation_02_runtime-architecture-and-contracts.md)
3. [各テスト技法のgenerator・検査ロジック](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md)
4. [UIパターン・外部標準・既存プロジェクトの扱い](./2026-09-18_170000_deterministic-test-technique-automation_04_ui-patterns-and-external-references.md)
5. [評価・CI・実装順序・完了条件](./2026-09-18_170000_deterministic-test-technique-automation_05_evaluation-ci-implementation-order.md)

## このPlanの基本方針

自然言語の仕様、Figma、Q&A、実装等から「何が条件・境界・状態・因子・制約・期待結果の根拠になるか」を判断する処理はLLMに残します。

一方、構造化済みの入力から一意または機械的に導出できる次の処理は、可能な限りSkill内のscriptへ移します。

- 値・組合せ・ルール・遷移・経路の列挙
- 成立不能条件の判定とCoverage母集団からの除外。候補と根拠は保持する
- カバレッジ計算
- 欠落・重複・矛盾・到達不能の検出
- 確定済み数値からのリスクレベル算出
- 変更済み要素からの構造的な影響範囲抽出
- Authority / Risk → TR → TCN → CI → TCの構造的な閉鎖・優先度継承
- 追跡グラフの閉鎖性・孤立確認
- UI要素種別から一般的な確認候補を引く処理

このPlanでいう決定論性は、**同じ正規化済みモデルと同じscript versionから同じ機械処理結果を得ること**です。自然言語資料から正規化済みモデルを作るLLM判断まで「同じ入力なら常に同じ結果」と保証するものではありません。正規化の意味妥当性・漏れはsemantic evalと既存の上流閉鎖で確認します。

scriptは仕様根拠や業務ルールを創作しません。期待結果が現在有効な仕様根拠へ追跡できない場合は、生成結果を完成済みテストとして扱わず、既存の停止条件・ブロック中・質問ルーティングへ戻します。
