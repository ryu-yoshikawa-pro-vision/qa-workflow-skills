# 判定根拠

## Source of Truth

- 注文履歴は利用者の主要業務経路で、変更時の回帰を繰り返し確認する価値がある。Product Riskとテスト重点は、この主要経路で利用者が注文履歴を確認できるという業務結果に置く。
- E2E自動化の対象選定（候補範囲、選定理由、選定結論）は`e2e-test-selection`の責務である。test-analysisは選定結論を作らず、Product Riskと重点を示したうえで選定を`e2e-test-selection`へroutingする（`skills/test-analysis/SKILL.md`の実行契約）。
- 入力に表示内容や遷移の仕様がない場合、それらを推測して重点や期待結果へ追加しない。不足する仕様根拠は確認事項として残す。
- 技術的なlocator、fixture、Playwright構成、実装可否はinspectionへ渡す。

## 禁止される推測

- locator、fixture、webServer、URL、実装コストをtest-analysisで決めない。
- 入力にない表示項目・遷移・期待結果を創作しない。
