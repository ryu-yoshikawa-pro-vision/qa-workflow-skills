---
name: e2e-test-reporting
description: 検証済みのPlaywright実行結果と、実施済みの場合は検証済み結果分析を人間が判断できるテスト結果報告へ変換するSkill。原因の再判定、仕様の再解釈、retryによる初回FAILの消去をせず、途中の分析済み結果からも開始できる。
---

# E2Eテスト結果報告

## 実行契約

1. 検証済み実行結果を必須入力とし、`e2e-test-result-analysis`を実施した場合だけ検証済み分析結果を利用します。分析済み結果からの途中開始では、URL、project、実行日時、E2E実装参照等の実行事実へ辿れることを確認します。
2. logical primary対象数、resolved primary TestCase数、実際に開始したresolved primary TestCase数、logical / resolved単位の未実行数・理由を区別します。retry attempt数をresolved件数へ混ぜません。
3. Playwright run全体status、process exit code、run-level error、expected / unexpected / flaky / skipped / timedOut / interrupted等を、確認元と単位を保ったまま報告します。
4. TC IDは存在する場合だけ記載し、TCなし経路のために作成しません。E2E実装参照・実行結果参照・分析結果参照を保持して追跡可能にします。
5. cleanupの成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態と残存副作用、ブロック、残存リスク、未解決事項を隠しません。
6. 原因の再判定、仕様の再解釈、都合のよいPASS / FAIL単純化をしません。証跡からsecret、cookie、token、storageState、不要な個人データを転載しません。

## 出力

`assets/output-template.md`を基本形として、対象範囲、環境、version、E2Eコードrevision、実行日時、run / primary / result集計、追跡、分析、cleanup、証跡、安全状態、残存リスクを報告します。
