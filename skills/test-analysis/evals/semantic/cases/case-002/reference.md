# 判定根拠
## Source of Truth
- 注文履歴は利用者の主要業務経路で、変更時の回帰を繰り返し確認する価値がある。
- E2E対象候補は注文履歴の表示・主要遷移など、利用者価値と観測可能な業務結果で表す。
- 技術的なlocator、fixture、Playwright構成、実装可否はinspectionへ渡す。

## 禁止される推測
- locator、fixture、webServer、URL、実装コストをtest-analysisで決めない。
