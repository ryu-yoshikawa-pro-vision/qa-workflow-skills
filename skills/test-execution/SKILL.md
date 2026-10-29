---
name: test-execution
description: 詳細テストケースを実対象上でAIが手動テスト相当の操作により実行し、観測した期待結果との比較と人間向け結果報告を行う。新規のTC実行と合否判断が必要なときに使用する。
---

# テスト実行

## 実行契約

1. 詳細な実行規則が必要な場合は references/guidance.md を読みます。
2. 実操作より前に入力TC snapshotを固定し、全TCをGiven / When / Then構造のYAMLへ意味を変えず整理します。TC本文や再実行元artifactが提供されず、snapshotを復元できない場合は空のGiven / When / Thenや仮の操作を作らず、`snapshot固定方法`欄の正規値を`未生成`として理由を別欄へ記録します。依頼件数だけが分かる場合は件数と不足情報を未実行表へ記録し、必要なら入力順の`input-NNN`を依頼slotのローカル識別子として使います。これはTC本文のsnapshotや元TC IDを意味しません。
3. test_case_ref は入力順の input-001 形式の成果物ローカル参照としてsnapshot内で一意にします。入力元IDは source_test_case_id に値を変えず保持し、なければnullです。独自fingerprintを生成しません。
4. 確定済みTCの再実行は別成果物 / versionとし、前回実行成果物参照と前回TC参照を両方保持します。
5. browser実行基盤はPlaywrightに固定し、Playwright MCP → Playwright CLI → 独立した今回run用Playwright Libraryコード → 未実行 / ブロック中 の順で選びます。前段で契約を満たす場合は下位へ切り替えません。
6. CLI / Library / browser / packageが未導入でも本Skillのためにinstallしません。今回run用Libraryコードはrepo runnerから独立し、repoやrunner設定を変更・読込せず、明示されたpreflightを超えてUI経路を迂回しません。
7. TC実操作は1成果物内で直列です。明示順がなければ入力順にし、preflight、TC操作、後処理、実行時cleanup、副作用回数更新を1件ずつ終えてから次へ進みます。
8. PASS / FAILは実測と根拠がある場合だけ確定します。実行開始前の停止は未実行、開始後に必要な観測を完了できない場合は判定不能です。
9. password / token / cookie / secret / storageState等の実値はYAML・報告・証跡説明へ複製しません。既存の参照方法がある場合だけその参照を記録します。
10. 準備、TC操作、TC事後処理、cleanupの状態変更は副作用scopeごとに回数を共有し、結果不明でも発生可能性があれば1回消費します。必要cleanup未完了や許可されていない残存状態があれば範囲を完了にしません。
11. source_test_case_idは入力で確認できた元TC IDか`null`だけです。ID値が提示されていない理由などの説明文をこの機械欄へ入れず、理由は未実行・判定不能欄へ記載します。実行手段・対象・TC本文・前回artifact等の必須前提が欠ける場合は未実行で閉じ、操作・観測・cleanup・結果のfixtureを作りません。
12. TC本文または再実行元本文がなくsnapshotを復元できない場合、依頼件数から作る`input-NNN`は未解決依頼slotの参照に限ります。TC参照対応表や未実行表へこのslotを記録しても、TC snapshotや実行前YAMLを作ったことにはなりません。YAML fenced block、手順・観測行、副作用scope行、視覚観測、実測値を出力せず、開始状態を`未開始`、結果を`未実行`、実行手段を正規値`未実行`とします。`TC実行条件`と`実行前条件`は依頼slotごとに行を対応付け、未知値を`未提供`、実行可否を`開始不可`として理由を確認結果へ記載します。副作用scopeが未確定の場合、機械欄の値は正規値`未提供`だけを使い、理由は隣接する確認結果欄へ記録します。source ID欄は`未提供`または`なし`だけを使い、説明文は理由欄へ置きます。テンプレートの必須節・表は省略せず、観測・cleanup表はデータ行なしで残します。

## 主な成果物

assets/execution-plan-template.yamlに沿う実行可能なTCの実行前YAMLを最終Markdownにも保持し、assets/output-template.mdを使ってTC参照、run固定条件、TC実行条件、手順・観測、結果、cleanup、集計、ユーザー向け報告を記録します。テンプレートの必須節と表見出しは、データ行がない場合も列名を省略・短縮・変更せず保持します。snapshotの必須入力がない場合はYAMLを出力せず、未生成理由と再開条件を記録します。

## 責務境界

- 詳細TCの作成・期待結果の根拠: test-case-design
- 生きた画面・状態・ふるまい資料の管理: test-target-inspection
- repoへ残すPlaywright E2E: e2e-test-inspection → e2e-test-implementation
- 既存repo E2Eの正式runner実行: e2e-test-execution
- 既存repo E2Eの原因分析: e2e-test-result-analysis
- Playwright runner固有報告: e2e-test-reporting
- workflow routing / 再開: qa-workflow

既存repo E2Eのraw resultを一般TC結果へ再集約しません。TC外の状態変更を伴う診断操作を行わず、原因未確認のFAILを製品不具合と断定しません。
