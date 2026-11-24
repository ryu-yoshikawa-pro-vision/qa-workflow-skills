---
name: test-reporting
description: 一般TC・E2E・Regression・探索・API/バッチ・静的テスト・欠陥などの元結果を、計画上の母集団と取得完全性に照らして読取専用で集計し、横断報告snapshotを作る。「結果の統合報告・横断集計・取得完全性の確認・終了基準の判定・報告snapshotの鮮度確認」を求められたら、自分で集計する前に必ずこのSkillを読み込む。個別のPlaywright結果報告、結果の再判定、計画更新、リリース可否の判断には使用しない。
---

# Test Reporting

複数のテスト方式の元結果を読取専用で集約し、計画上の母集団と実際に取得した集合を照合した報告snapshotを作ります。元run・原因分析・正式欠陥状態・計画・Product Risk・リリース決定は更新しません。Playwright E2E単体の結果報告は`e2e-test-reporting`です。

## 実行契約

1. 先に`references/guidance.md`を読み、母集団、取得完全性、集計単位、終了基準の契約に従います。
2. 計画上の母集団（承認済み計画版の対象source、build、環境、期間、終了基準）は`test-management`等の正本から参照します。計画がない直接依頼では明示されたscopeと許可された探索rootだけを使い、母集団が不明なら全体率と終了判定を`undetermined`にします。
3. 各source ownerから取得した範囲、source revision、pagination・権限、取得時点、result refを記録します。予定されたsourceが欠けていれば0件ではなく`取得未完了`とし、取得済みの部分集計と不足数・範囲を同時に出します。
4. `logical primary`・`resolved TestCase`・`attempt`・session・TC・テストファイル・suite・個別テスト・review対象・finding・欠陥候補は別単位です。単位をまたいで足さず、retryを分母へ二重加算せず、別build・別環境・対象期間外・旧revisionの結果を混ぜません。終了基準も単一の計測単位のsourceに対してだけ評価し、単位をまたぐ合算で判定しません。
5. 母集団の取得、source参照のcurrentness、元結果の確定、cleanup、各終了基準を独立に判定します。`complete`と終了判定、進捗率とPASS率、報告の生成と承認を混同しません。
6. 元結果のraw値を書き換えません。静的レビューは対象数のレビュー完了がなければ「指摘0件・完了」としません。
7. 計画変更・source更新後は新revisionに対する再集計とし、旧snapshotをcurrentにしません。現在の計画revisionを確認できない場合は、改版済みとは別の未確認として終了判定を確定しません。正式リリース可否の判断はしません。
8. 集計は`scripts/reporting_runtime.py`の決定論的helperで行い、LLMで代替・補完しません。

## 正規対象

- `snapshot`：横断報告snapshotの作成
- `currentness`：保存済みsnapshotの鮮度確認

## リソース

- 手順・責務境界・停止条件: `references/guidance.md`
- 入出力のdata contract: `references/data-contract.md`
- 正規出力形: `assets/output-template.md`
- production helper: `scripts/reporting_runtime.py`（標準ライブラリのみ。他Skillのscriptに依存しない）
- deterministic validator: `evals/deterministic/validator.py`
