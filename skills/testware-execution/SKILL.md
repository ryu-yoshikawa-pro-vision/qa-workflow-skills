---
name: testware-execution
description: 非E2EのVitest・API-only Playwright・component・batch・event・非機能testwareの実runner実行、非ブラウザTCの直接観測、許可された静的解析ツール実行とraw結果・cleanup・診断を担当するSkill。「非E2Eテストの実行、raw結果の取得、静的解析の実行」を求められたら、コマンドを自分で組み立てる前に必ずこのSkillを読み込む。実行のみ・TCなしでも直接開始できる。
---

# 非E2E testware実行

## 実行契約

1. 実行前にreferences/guidance.mdを読む。activity、ブラウザ操作の有無、保存するtestwareの有無でownerを選び、runner名だけでPlaywright E2Eへroutingしない。
2. 正式TCがなくても既存testware refと採用基準・scopeから直接実行できる。自動testwareを作成しない非ブラウザTCの直接操作・期待結果比較も担当する。ブラウザTCはtest-execution、ブラウザE2E runnerはe2e-test-executionに戻す。
3. source/build/testware/TC revision、対象scope・選択集合、runner version・script chain、環境・認証・fixture、許可副作用と回数上限、共有資源予約、cleanupをpreflightで固定する。scripts/contract.pyのpreflightは補助であり承認・reservation・実開始を証明しない。
4. 実行前の停止は未実行とする。開始後の収集不全・必須観測欠落は判定不能／取得不完全、期待結果不一致の実測はFAIL。HTTP成功・exit 0・test file成功のみで正式TCをPASSにしない。
5. runnerが提供するraw結果、実開始、attempt・retry、個別test identity、skip/todo/timeout、未収集・未選択、実効filter、後処理と残存状態を分ける。Vitestの個別照合ではscripts/contract.pyを使用できる。runner内部の一時IDを永続識別子にしない。
6. 静的解析は許可された実ツールのraw出力と解析対象revisionを記録する。Agentの意味的静的レビューはadversarial-reviewへ渡す。静的解析exit 0をFinding 0件と同義にしない。
7. 実行異常の第一分析ownerとして元runを変更せず、原因候補・確度・根拠・反証・不足証拠と修正／再実行先を独立記録する。確定していない製品欠陥をIssueへ自動登録しない。
8. 共有状態の予約やcleanupが未確認なら自動再実行を拒否し、元の証跡を保持する。raw log・trace・認証情報は機密資料として扱い、無断commit・共有・転載しない。

## 出力

assets/output-template.mdを使い、runの固定条件、実開始・未開始、raw参照、個別testとTC/testware対応、母集団／収集完全性、attempt、直接観測、静的解析、診断、cleanupと再開条件を記録する。raw結果と分析は別の成果物とする。

## リソース

- 非E2E実行手順・安全判断: references/guidance.md
- 決定論的な結果照合: scripts/contract.py
- 正規出力: assets/output-template.md

- 実runnerの単独実行: `scripts/runner.py`（承認済みの隔離checkoutのみ。コマンド・fixture・副作用を確認する前に実行しない）
