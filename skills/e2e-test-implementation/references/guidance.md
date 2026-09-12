# E2Eテスト実装 詳細判断基準

## 実装前

inspection時点のbranch / commit / working treeと現在状態を比較します。今回編集するファイルと既存変更が競合する場合は停止し、競合しない変更は保持します。

## 実装

対象repoの既存実行入口・設定・fixture・helperを再利用します。locatorは既存方針を優先し、方針がない場合だけPlaywright公式推奨に沿います。固定時間待機、テスト間依存、共有状態依存を既定手段にしません。

TCなし経路では、明示E2E対象と確認済み期待挙動を直接実装します。TCを作る目的だけで`test-case-design`へ戻りません。期待挙動が確定できない範囲だけブロックします。

## 軽量検証

package script / task / wrapperのchainを確認して、実E2E、外部I/O、状態変更、破壊的操作を含まないものだけを実行します。`playwright test --list`も設定読み込みに副作用がないと確認できる場合だけ使います。指定環境への本実行は`e2e-test-execution`へ委譲します。

## 参照

`repo-relative test file + title path`を基本参照とし、TC IDが存在する場合だけ対応を保持します。架空のE2E IDを必須化しません。
