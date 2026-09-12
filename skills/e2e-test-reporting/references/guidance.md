# E2Eテスト結果報告 詳細判断基準

## 集計単位

論理的な要求primary対象、Playwrightが解決したresolved primary TestCase、各attemptを別の単位で保持します。project / repeatEach等でresolved件数が増え、retryでattemptが増えます。dependency / teardown testは要求primary集計へ混ぜません。

logical primaryがresolved 0件の場合は、未実行 / 解決不能理由をlogical単位で示します。resolved primaryごとに結果または未実行理由がない場合も完全実行としません。resolved primaryを開始していない場合は、`結果`と`実行結果参照`を空欄にし、`未実行理由`へworkflow側の理由を記録します。`expectedStatus` / `outcome`へ`未実行`などの擬似値を入れません。preflight blockでresolved自体がない場合は、logical primaryの識別子・理由へ追跡し、架空のresolved result参照を作りません。

## 追跡参照の完全性

`TC・E2E・実行・分析追跡`の`E2E実装参照`はprimary対象集計の安定参照と完全一致させます。開始済みresolved primaryは、その行の`実行結果参照`と完全一致させ、未開始resolved primaryはresolved TestCase参照、resolved自体が0件ならlogical primary識別子を使います。未実行理由そのものは識別子・参照にしません。trace行を1件置くだけでは不十分で、全対象の対応行が必要です。存在しないresult参照や別E2E実装参照は記録しません。分析未実施が明示された正常runでは`分析結果参照`を空欄にし、架空の参照を残しません。分析実施状態が未指定の既存経路では一律に空欄を強制しません。分析を実施した場合は、安定した分析成果物参照をtrace行ごとに記録し、指定された参照と完全一致させます。

## 結果と分析

raw status、run-level結果、process exit code、導出したoutcome / 集計を区別します。`TestResult.status`は`passed` / `failed` / `timedOut` / `skipped` / `interrupted`、`TestCase.expectedStatus`も同じ値域、`TestCase.outcome()`は`skipped` / `expected` / `unexpected` / `flaky`、FullResultのrun全体statusは`passed` / `failed` / `timedout` / `interrupted`です。`未実行`や`確認不能`をPlaywright raw値へ混ぜません。分析を実施していない場合は「分析なし」と明記し、結果から原因を推測しません。分析済みの場合も入力の判定・原因・再現性を再解釈せず引用可能な範囲で伝えます。

## 安全な共有

trace / screenshot / video / HTML report / network / stdout / storageStateは機密情報を含み得ます。安全なローカル参照だけを示し、secret query、cookie、token、不要な個人データを転載しません。
