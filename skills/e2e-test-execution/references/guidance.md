# E2Eテスト実行 詳細判断基準

## 実効設定と副作用

config → project → file / describe / test → CLIの上書きを、今回対象へ影響する範囲だけ追います。absolute URL、webServer、project dependency / teardown、globalSetup / globalTeardown、返却teardown callback、automatic fixture、worker-scoped fixture、hooks、対象testから到達するAPI / helperまで副作用に関係する経路を確認します。

1件の論理TCがproject、repeatEach、retry、parallel worker再生成で複数回操作され得ることを踏まえ、メール・削除・共有データ更新等の最大回数を決めます。上限が不明なら該当範囲をブロックします。

## 準備とcleanup

runnerが管理するsetup / teardownをrun外で二重実行しません。run外処理はrepoで定義されinspection等で確認済みのseed / API / cleanupだけを使い、新しい方式を作りません。process interruptionや通信断でcleanup結果が確認できない場合は`未確認`です。

## 構造化結果

各logical primary対象がresolved primary TestCaseへ1件以上解決したかを先に確認し、解決できなければ理由を残します。次に各resolved primary TestCaseの結果または未実行理由を確認します。dependency / teardown testは要求primary数へ混ぜません。`timedOut` / `interrupted`はPlaywright statusとして保持し、`outcome`は別の導出結果として扱います。

`FullResult.status`や`repeatEachIndex`を利用したresult形式が直接提供しないなら、process exit codeや別ログからraw fieldへ推測転記しません。必要な値は`確認不能`または`構造化結果不完全`にし、導出値と分けます。

## 変更と証跡

実行前後のworking treeを比較し、snapshot / source / outputDir以外のrepo内変更も隠しません。output / reportの削除・上書き、custom reporterの外部I/O、storageStateの機密性を確認します。
