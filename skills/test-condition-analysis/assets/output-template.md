# 共通テスト条件候補

## Scope and source snapshot

| Field                                   | Value           |
| --------------------------------------- | --------------- |
| Project scope                           |                 |
| Candidate artifact ref                  |                 |
| Candidate update / analysis status      |                 |
| Feature inventory ref / revision / hash |                 |
| Authority refs / revisions              |                 |
| Confirmed source boundary               |                 |
| Candidate model fingerprint             |                 |
| Provider revision / readback            | 未保存 / 未確認 |

## Condition candidates

| Condition ID | Name | Intent | Kind | Applicable item kinds | Feature refs | Known item refs | Candidate state | Authority refs | Evidence refs | Currentness | Unknowns |
| ------------ | ---- | ------ | ---- | --------------------- | ------------ | --------------- | --------------- | -------------- | ------------- | ----------- | -------- |

## Advisory item-condition candidate pairs

| Item ID | Condition ID | Candidate state | Rationale | Evidence refs |
| ------- | ------------ | --------------- | --------- | ------------- |

## Candidate gaps and source boundary

| Finding | State | Refs | Evidence / recheck condition |
| ------- | ----- | ---- | ---------------------------- |

## Separate owner metrics

| Metric                                        | Owner                         | State             | Count |
| --------------------------------------------- | ----------------------------- | ----------------- | ----- |
| Common condition candidates                   | D / `test-condition-analysis` |                   |       |
| Explicit item-condition candidate pairs       | D / `test-condition-analysis` |                   |       |
| Formal applicability / adoption / disposition | E / `test-condition-design`   | Not provided to D | N/A   |
| Formal TCN / CI / expected-result design      | E / `test-condition-design`   | Not provided to D | N/A   |
| Test execution                                | Execution owner               | Not provided to D | N/A   |

## ID history and resume

| Condition ID | Change | Reason | Related condition IDs | Evidence refs |
| ------------ | ------ | ------ | --------------------- | ------------- |

| Scope | State | Missing evidence or blocker | Resume owner / condition |
| ----- | ----- | --------------------------- | ------------------------ |

## Handoff

Provide stable `COND-*` refs, candidate fingerprint, source/Authority refs and revisions, history, explicit advisory pairs, unrepresented feature candidates, unknowns, and provider persistence status to E. Formal applicability remains pending E.
