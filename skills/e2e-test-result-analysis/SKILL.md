---
name: e2e-test-result-analysis
description: 検証済みPlaywright実行結果、E2E対象・実装参照、証跡から異常・未実行・cleanup問題の原因を判定可能な範囲で分析し、追加証拠と最も早い責任Skillへの修正routingを示すSkill。Playwrightを直接再実行しない。
---

# E2Eテスト結果分析

## 実行契約

1. 詳細判断が必要な場合は最初に`references/guidance.md`を読み、raw factと原因推論、追加実行routingの契約に従います。
2. 検証済みの実行結果、識別可能なE2E対象 / E2E実装参照、利用可能な証跡を最低入力にします。TCと仕様根拠は存在し判定に必要な場合だけ利用します。
3. Playwrightのraw status / outcome / expectedStatus、run全体結果、未実行、run-level error、cleanup状態、ユーザー要求を分離して読みます。raw attemptの`failed`だけで自動的に原因分析したり、FAILをプロダクト不具合と断定したりしません。
4. TCなしの既存E2E結果を分析するためにTC / TC IDを新規作成しません。assertionコード自体を製品仕様の正本にしません。
5. version / deployment差異、データ・開始状態、実行条件、実装、仕様根拠不足を区別し、判定不能は原因と混同しません。再現性は原因とは別軸で保持します。
6. 「実行結果だけ」と明示された場合は原因分析を追加しません。ただしcleanup未確認・残存副作用など安全上の状態は隠さず伝えます。
7. 追加実行が必要でもPlaywrightを直接起動しません。必要証拠、検証する仮説、必要範囲を出力して`qa-workflow`経由で`e2e-test-execution`へroutingします。
8. 修正先は仕様根拠、question-analysis、test-analysis、test-case-design、inspection、implementation、execution等の最も早い責任Skillへ戻します。プロダクトの仕様不一致をE2Eコード変更でPASSへ変えません。
9. cleanup未確認は未確認のまま保持し、追加実行や完了判定を安全状態の確認なしに進めません。

10. 必須の実行事実は項目名だけで完了扱いにせず、各行の`値`と`参照`を確認します。判定と追加実行判断も最低1行必要です。追加実行が不要なら`不要`を明示し、必要 / ブロック中の場合だけ証拠・仮説・範囲・担当を記録します。

## 出力

`assets/output-template.md`を基本形として、値と参照を伴う実行事実、判定状態、原因（複数可）、再現性、根拠、不足証拠、追加実行依頼、修正先、`要再検証`、検出事項を記録します。原因を確定できない場合は`原因未確定`等の明示状態を使います。
