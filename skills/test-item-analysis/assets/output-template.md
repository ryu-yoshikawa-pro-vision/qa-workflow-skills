# テストアイテム候補

## Scope and source snapshot

| Field                                   | Value           |
| --------------------------------------- | --------------- |
| Project scope                           |                 |
| Candidate artifact ref                  |                 |
| Feature inventory ref / revision / hash |                 |
| Confirmed source boundary               |                 |
| Candidate model fingerprint             |                 |
| Provider revision / readback            | 未保存 / 未確認 |

## Feature population

| Feature ID | Feature status | Candidate item refs | Candidate state |
| ---------- | -------------- | ------------------- | --------------- |

## Item candidates

| Item ID | Name | Kind | Parent item IDs | Feature refs | Status | Evidence refs | Currentness |
| ------- | ---- | ---- | --------------- | ------------ | ------ | ------------- | ----------- |

## Stable ID history

| Item ID | Change | Reason | Related item IDs | Evidence refs |
| ------- | ------ | ------ | ---------------- | ------------- |

## Candidate identification metrics

| Metric                                             | Status | Numerator | Denominator | Rate | Basis |
| -------------------------------------------------- | ------ | --------- | ----------- | ---- | ----- |
| Confirmed feature-to-item candidate identification |        |           |             |      |       |
| Unrepresented known feature candidates             |        |           |             | N/A  |       |

## Separate owner metrics

| Separate owner metric                    | State                                 | Value             |
| ---------------------------------------- | ------------------------------------- | ----------------- |
| Item-condition applicability decision    | E / `test-condition-design` owns this | Not provided by D |
| Formal TCN / CI / expected-result design | E / `test-condition-design` owns this | Not provided by D |
| Test execution                           | Execution owner                       | Not provided by D |

## Unknown, stale, blocked, or resume conditions

| Scope or item | State | Evidence or missing input | Resume owner / condition |
| ------------- | ----- | ------------------------- | ------------------------ |

## Handoff

Provide stable `ITEM-*` refs, candidate fingerprint, source refs/revisions, validator result, history, unrepresented feature candidates, unknowns, and provider persistence status to `test-condition-analysis`, E, and A as applicable.
