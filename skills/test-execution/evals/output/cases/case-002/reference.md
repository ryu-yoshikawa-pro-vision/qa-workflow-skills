# テスト実行結果 再実行

## 実行情報

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 | プロフィール設定 | TC入力 |
| テストケース入力元 / 成果物参照 | case-set-10 | ユーザー |
| TC revision / content identity | tcset-r10 | 入力元 |
| snapshot固定方法 | 入力元identity | 入力元 |
| 今回の実行対象 test_case_ref 集合 | input-001 | snapshot |
| 前回実行成果物参照 | execution-v1 | 前回成果物 |
| 実行日時 | 2026-09-26T10:30:00+09:00 | run |
| 使用した実行手段 | Playwright CLI | MCPに必要な能力なし、既存CLI利用可 |
| テスト対象資料参照 | profile-current-v2 | 入力 |

## run固定条件

| 条件 | 値 | 確認元 |
| --- | --- | --- |
| 対象環境 | staging | 案件context |
| 許可origin | https://staging.example.test | 案件context |
| version / build | build-23 | 実対象 |
| その他今回固定する条件 | Chromium、ja-JP | run |

## TC参照対応

| TC参照 | 元TC ID (source_test_case_id) | 入力順 | 前回TC参照 |
| --- | --- | ---: | --- |
| input-001 | TC-044 | 1 | input-001 |

## TC実行条件

| TC参照 | role / アカウント | viewport | locale | feature flag | テストデータ | 開始状態 | 確認結果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| input-001 | editor-test | 1280x800 | ja-JP | profile-v2=on | user-25 | 認証済み設定画面 | 確認済み |

## Given / When / Then構造の実行前YAML

```yaml
test_case_ref: input-001
source_test_case_id: TC-044
title: 表示名を更新できる
scenario:
  given:
    - 認証済みユーザーの設定画面を表示している
    - 既存の認証方法でテストユーザーへログイン済み
  when:
    - step_ref: step-001
      action: 表示名をTest Userへ変更して保存する
  then:
    - after_step_ref: step-001
      expected: 保存後に表示名がTest Userとなる
      observation:
        - accessibility_tree
unresolved: []
cleanup: []
```

## 実行前条件

| TC参照 | 副作用scope | TC事後状態 / 後処理 | 確認結果 |
| --- | --- | --- | --- |
| input-001 | profile-update | 更新後に元の表示名へ戻す | cleanup残数を含めて実施可 |

## 副作用上限・実行時cleanup

| 副作用scope | 1回の定義 | 最大回数 | 準備回数 | TC操作回数 | TC事後処理回数 | 実行時cleanup回数 | 累計実施回数 | 実行時cleanup対象 / 方法 | cleanup結果 | 残存状態 | 残数 / 状態 | 根拠 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| profile-update | 1回はプロフィール値1件の変更操作 | 3 | 1 | 1 | 0 | 1 | 3 | 元の表示名へ戻す | 成功 | 元の表示名へ復元済み | 0 | scope契約 |

## 手順・観測結果

| TC参照 | 手順 / 観測点 (step_ref) | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| input-001 | step-001 | 表示名を入力し保存 | accessibility tree | Test Userが表示 | Test Userを観測 | 一致 |

## 視覚確認

| TC参照 | 手順 / 観測点 | 確認観点 | 画像で観測した事実 | 画像参照 | 判定への利用 |
| --- | --- | --- | --- | --- | --- |

## TC実行結果

| TC参照 | 実行開始 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 証跡参照 |
| --- | --- | --- | --- | --- | --- | --- |
| input-001 | 開始済み | PASS | 表示名がTest User | Test Userを観測 | accessibility treeで保存後を確認 | observation:input-001 |

## 未実行・判定不能

| TC参照 | 状態 | 理由 | 必要な情報 / 対応 | 再開条件 |
| --- | --- | --- | --- | --- |

## 追加観測

| TC参照 | 観測内容 | 確認方法 | TC結果への影響 | 証跡 |
| --- | --- | --- | --- | --- |

## TC事後状態・後処理

| TC参照 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |
| --- | --- | --- | --- | --- |
| input-001 | 元の表示名へ戻す | 成功 | 変更前の値へ復元済み | cleanupを観測 |

## 実行時cleanup・残存状態

| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

## 集計

| 状態 | 件数 |
| --- | ---: |
| PASS | 1 |
| FAIL | 0 |
| 未実行 | 0 |
| 判定不能 | 0 |

## 実行結果報告

- input-001をstagingでPlaywright CLIにより再実行した。
- 結果: PASS 1、FAIL 0、未実行 0、判定不能 0。
- 前回成果物 execution-v1 の input-001 へ追跡できる。
- 表示名変更scopeの準備、TC操作、cleanupを合計3回として記録し、最大3回内で復元を確認した。
- 元入力にあったsecret実値はYAMLと報告へ複製していない。
