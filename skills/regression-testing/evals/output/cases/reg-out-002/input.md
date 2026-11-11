# Eval Input

正規形は`assets/output-template.md`を使います。

TC-001にmanualとE2Eの2 routeが必要。manualはFAILで実開始、E2Eはpreflight blockで未開始。

この入力にはActivity identity、固定snapshot、Regression scope identity、各routeのsource execution ref、route ref、結果確定状態、cleanup状態がありません。これらの値は推測・採番せず、正規Activityをmaterializeできない場合は理由を示してblockしてください。
