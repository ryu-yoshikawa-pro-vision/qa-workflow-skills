# テスト実行結果

## 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 | 注文検索 | TC入力 |
| テストケース入力元 / 成果物参照 | user-input-set-A | ユーザー |
| TC revision / content identity | なし | 入力に存在しない |
| snapshot固定方法 | 成果物内TC集合・実行前YAML | 成果物v1 |
| 今回の実行対象 test_case_ref 集合 | input-001, input-002 | snapshot |
| 前回実行成果物参照 | なし | 初回実行 |
| 実行日時 | 2026-09-26T10:00:00+09:00 | run |
| 使用した実行手段 | Playwright MCP | 現在利用可能なMCP |
| テスト対象資料参照 | orders-current-v3 | 入力 |

## run固定条件

| 条件 | 値 | 確認元 |
| --- | --- | --- |
| 対象環境 | staging | 案件context |
| 許可origin | https://staging.example.test | 案件context |
| version / build | build-23 | 実対象 |
| その他今回固定する条件 | ja-JP | 案件context |

## TC参照対応

| TC参照 | 元TC ID (source_test_case_id) | 入力順 | 前回TC参照 |
| --- | --- | ---: | --- |
| input-001 | EXT-17 | 1 | なし |
| input-002 | EXT-17 | 2 | なし |

## TC実行条件

| TC参照 | role / アカウント | viewport | locale | feature flag | テストデータ | 開始状態 | 確認結果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| input-001 | viewer-test | 1440x900 | ja-JP | orders-v2=on | order-42あり | 未ログイン | 確認済み |
| input-002 | viewer-test | 1440x900 | ja-JP | orders-v2=on | order-42あり | 注文一覧 | 確認済み |

## Given / When / Then構造の実行前YAML

```yaml
test_case_ref: input-001
source_test_case_id: EXT-17
title: 注文を検索できる
scenario:
  given:
    - 注文一覧が表示されている
  when:
    - step_ref: step-001
      action: 注文番号42を検索欄へ入力する
  then:
    - after_step_ref: step-001
      expected: 注文番号42が一覧に表示される
      observation:
        - accessibility_tree
unresolved: []
cleanup: []
```

```yaml
test_case_ref: input-002
source_test_case_id: EXT-17
title: 注文詳細へ移動する
scenario:
  given:
    - 注文一覧に注文番号42が表示されている
  when:
    - step_ref: step-002
      action: 注文番号42のリンクを選択する
  then:
    - after_step_ref: step-002
      expected: 注文詳細画面が表示される
      observation:
        - accessibility_tree
unresolved: []
cleanup: []
```

## 実行前条件

| TC参照 | 副作用scope | TC事後状態 / 後処理 | 確認結果 |
| --- | --- | --- | --- |
| input-001 | なし | なし | 条件確認済み |
| input-002 | なし | なし | 条件確認済み |

## 副作用上限・実行時cleanup

| 副作用scope | 1回の定義 | 最大回数 | 準備回数 | TC操作回数 | TC事後処理回数 | 実行時cleanup回数 | 累計実施回数 | 実行時cleanup対象 / 方法 | cleanup結果 | 残存状態 | 残数 / 状態 | 根拠 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |

## 手順・観測結果

| TC参照 | 手順 / 観測点 (step_ref) | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| input-001 | step-001 | 注文番号42を検索欄へ入力 | accessibility tree | 注文番号42が表示 | 注文番号42を観測 | 一致 |
| input-002 | step-002 | 注文番号42のリンクを選択 | accessibility tree | 注文詳細画面 | 注文詳細画面を観測 | 一致 |

## 視覚確認

| TC参照 | 手順 / 観測点 | 確認観点 | 画像で観測した事実 | 画像参照 | 判定への利用 |
| --- | --- | --- | --- | --- | --- |
| input-002 | step-002 | 詳細画面の表示崩れ | 見出しと明細が重ならない | screenshot:input-002-step-002 | 視覚期待結果の確認 |

## TC実行結果

| TC参照 | 実行開始 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 証跡参照 |
| --- | --- | --- | --- | --- | --- | --- |
| input-001 | 開始済み | PASS | 注文番号42が表示 | 注文番号42を観測 | accessibility treeで確認 | observation:input-001 |
| input-002 | 開始済み | PASS | 注文詳細画面 | 注文詳細画面を観測 | accessibility treeと画像で確認 | observation:input-002 |

## 未実行・判定不能

| TC参照 | 状態 | 理由 | 必要な情報 / 対応 | 再開条件 |
| --- | --- | --- | --- | --- |

## 追加観測

| TC参照 | 観測内容 | 確認方法 | TC結果への影響 | 証跡 |
| --- | --- | --- | --- | --- |

## TC事後状態・後処理

| TC参照 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |
| --- | --- | --- | --- | --- |

## 実行時cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

## 集計

| 状態 | 件数 |
| --- | ---: |
| PASS | 2 |
| FAIL | 0 |
| 未実行 | 0 |
| 判定不能 | 0 |

## 実行結果報告

- 実行対象と環境: input-001、input-002 / staging / build-23
- 結果: PASS 2、FAIL 0、未実行 0、判定不能 0
- 2 TCをPlaywright MCPで入力順に実行し、各期待結果を観測した。
- 副作用はなく、cleanup対象と残存状態はない。
- 詳細は各TCの観測表と判定根拠を参照。
