# Semantic評価証拠（2026-11-10、latest v4）

- Skill/input source baseline: `6c3e9f1e8c1e848fdec716e7f17395a75d42bda6`; evidence packaging HEAD: `7c76ed379b3d7210585d29e8a72956302f38faf5`
- manifest: 31 cases; actual candidate generation and independent-session Judge completed: 19/31
- verdicts: pass 15, needs_review 4, fail 0, not_evaluable 0, Judge errors 0
- criterion statuses: pass 64, needs_review 4
- Generator and Judge used independent Codex sessions per case, using the same default configured model family; model ID was not exposed, so model independence is not established.
- v4 adds current-input `TCN-SEM-006`; its actual candidate, Agent JSONL, Judge raw response/events, normalized result, and source hashes are in the v4 archive. The v4 archive also corrects a prior packaging error in v2/v3 for the normalized `TCN-SEM-002` Judge result.
- Some earlier generated cases used packages that contained eval files. Their command traces were audited for reference/rubric reads, but filesystem isolation was weaker; v5/v6/v7/v8/v9 excluded eval files, tests, and pycache.
- Evaluation evidence is not repository-wide acceptance and does not cover real Agent trigger rates, a real artifact provider, or the remaining 12 semantic cases.

| Skill                     | Eval ID           |    Agent | Judge        |
| ------------------------- | ----------------- | -------: | ------------ |
| `test-analysis`           | `RISK-SEM-001`    |  595.5 s | pass         |
| `test-analysis`           | `RISK-SEM-003`    |  407.5 s | pass         |
| `test-analysis`           | `RISK-SEM-004`    |  498.3 s | pass         |
| `test-analysis`           | `RISK-SEM-005`    |  574.4 s | needs_review |
| `test-analysis`           | `RISK-SEM-006`    |  487.5 s | pass         |
| `test-requirement-design` | `TR-SEM-001`      |  502.6 s | pass         |
| `test-analysis`           | `RISK-SEM-002`    |  739.2 s | needs_review |
| `test-analysis`           | `RISK-SEM-007`    |  603.0 s | pass         |
| `test-requirement-design` | `TR-SEM-002`      |  710.9 s | pass         |
| `test-requirement-design` | `TR-SEM-003`      |  554.9 s | pass         |
| `test-condition-design`   | `TCN-SEM-001`     |  889.0 s | needs_review |
| `test-condition-design`   | `TCN-SEM-003`     |  911.5 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-001` |  312.3 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-002` |  179.1 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-003` |  643.3 s | needs_review |
| `test-condition-design`   | `TCN-SEM-002`     | 1189.9 s | pass         |
| `test-condition-design`   | `TCN-SEM-004`     | 1102.4 s | pass         |
| `test-condition-design`   | `TCN-SEM-005`     |  744.4 s | pass         |
| `test-condition-design`   | `TCN-SEM-006`     |  897.8 s | pass         |

Current detail index: `evidence-index-v4.json`. Full v4 archive: `semantic-evidence-v4.tar.gz`. The v2/v3 archives have an incorrect normalized `TCN-SEM-002/judge-result.json` copied from a later case; their raw Judge data remains, and v4 contains the correct normalization from the TCN-002 runner output. The v1 archive has the correct 16-case TCN-002 record; prior versions are preserved with this limitation recorded in `README-v2.md` and `README-v3.md`.
