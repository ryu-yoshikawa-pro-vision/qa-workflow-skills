# Eval Input

TC-401の required route は manual と、非E2E の testware（Vitest `tests/unit/password-hasher.test.ts`、実行ownerは`testware-execution`、実装revision `rev-2026-11-09`）の2つです。

利用者は今回のRunで、TCを持たない Vitest `tests/unit/app-config.test.ts` を補助testwareとして**実行するよう明示**しました。`tests/unit/native-stores.test.ts` は「参照候補として記録するだけ」で、今回は実行不要と指示されています。

owner execution contract の返却値は次のとおりです。

- TC-401 manual：開始済み、result finalized=true、raw result=PASS。
- TC-401 testware：開始済み（attempt ref `attempt-t401-1`）、実装revision `rev-2026-11-09`、result finalized=true、raw result=PASS、raw取得完了、cleanup 対象なし。
- `app-config.test.ts` 補助：runnerの起動前preflightでblockedとなり、actual attempt は未開始、result finalized=false。
- `native-stores.test.ts` 補助：未開始（実行対象外）。

このRunのRun artifactとActivity artifactを正規形で作成し、Activityの状態とその理由を示してください。
