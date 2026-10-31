# E2Eテスト結果報告 deterministic case 001

`assets/output-template.md`を使い、次のfixture事実から1 logical primary / 1 resolved primaryを報告してください。retry attemptはresolved primary件数と別集計し、cleanup成功と実行参照を記録してください。実施済みの分析成果物`analysis.md`もtraceへ完全一致で記録します。

## Supplied report facts

- Logical primary: `login-flow`
- E2E implementation reference: `tests/auth/login.spec.ts > login succeeds`
- TC ID: `TC-001`
- Resolved primary TestCase reference: `TC-001/chromium/repeatEachIndex=0`
- Resolved primary started: yes
- `TestResult.status`: `passed`
- `TestCase.expectedStatus`: `passed`
- `TestCase.outcome`: `expected`
- Retry attempt count: 1; history: `passed (retry 0)`
- Execution result reference: `RESULT-001`
- Playwright run status: `passed` (reporter); process exit code: `0`; run-level error: none
- Cleanup status: successful
- Analysis was performed; exact analysis reference: `analysis.md`
- Test environment URL, target version / build, E2E code branch / commit / working tree, run timestamp, and Playwright project were not provided. Report them as unavailable and cite this input as the checked source.
