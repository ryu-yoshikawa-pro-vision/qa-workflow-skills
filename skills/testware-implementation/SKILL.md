---
name: testware-implementation
description: API-only Playwright、Vitest、component、batch、event、非機能など、ブラウザE2E以外の保存可能な自動testware・fixture・設定を安全に実装・更新するSkill。TCまたは明示対象と変更権限・仕様根拠があるときに使用する。
---

# 非E2E testware実装

## 実行契約

1. 先にreferences/guidance.md、対象repoの既存testware・fixture・実行入口・関連テスト・CI、参照元の仕様Authority・TC revision・変更権限を確認する。
2. Playwright TestによるAPI-onlyテストは対象とするが、PlaywrightブラウザE2Eはe2e-test-implementation、ブラウザTC直接操作はtest-executionへ渡す。runnerの製品実行はtestware-executionが担当する。
3. TCがなくても明示testware、対象scope、根拠となる期待挙動・採用基準があれば実装可能とする。TC IDを創作しない。期待値・非機能閾値が不明なら該当範囲をblockする。
4. 変更前にbranch・HEAD・dirty状態・対象path、既存assertion、fixture・認証・cleanupとscript chainを確認し、隔離worktree/copyで作業する。対象外pathやSUT製品実装・正式仕様を変更しない。
5. scripts/snapshot_guard.pyによる内容照合は補助検査であり、原子的な反映ではない。共有先への適用は最新HEADと対象内容を再取得し、native expected-HEAD CASなどの条件付き確定ができる場合だけ行う。同じpathの競合では旧内容で上書きしない。
6. 隔離できない共有workspaceは関係者共通の有効な排他予約が必要である。qa-workflowのreserve_shared_resource()がblockedなら編集を開始しない。claim_mutable_operation()はpath排他の代用ではない。
7. 生成コードのassertionを仕様根拠にしない。既存setup/teardownを再利用し、secret・PIIをtestware・レポート・Git差分に残さない。危険なpackage script・外部I/O・本テスト実行を軽量検証として起動しない。
8. 反映後は実際の変更先でHEAD・内容・許可差分を再確認する。readback不能・cleanup未確認・CI失敗は完了扱いせず、独立assertionレビューをadversarial-reviewへ渡す。

## 出力と境界

assets/output-template.mdで作業対象、元TCまたは明示対象、source/testware revision、変更ファイル、競合・権限・preflight、軽量検証、未実施／blocked、実testware参照、cleanup、次の担当を保存する。実runner PASSやTCの合否は主張しない。

## リソース

- 判断・変更安全性: references/guidance.md
- 読取専用snapshot照合: scripts/snapshot_guard.py
- 既定出力: assets/output-template.md
