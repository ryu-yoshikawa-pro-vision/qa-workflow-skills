# テストアイテム候補

## Scope and source snapshot

| Field                                   | Value                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Project scope                           | project:shop                                                                                     |
| Candidate artifact ref                  | item-candidates:shop                                                                             |
| Candidate update / analysis status      | candidate_ready_unpersisted / complete                                                           |
| Feature inventory ref / revision / hash | feature-analysis / feature-r1 / aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| Confirmed source boundary               | complete                                                                                         |
| Candidate model fingerprint             | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb                                 |
| Provider revision / readback            | 未保存 / 未確認                                                                                  |

## Feature population

| Feature ID | Feature status | Candidate item refs | Candidate state |
| ---------- | -------------- | ------------------- | --------------- |
| FEAT-001   | implemented    | ITEM-001, ITEM-002  | candidate       |
| FEAT-002   | planned        | ITEM-002            | candidate       |

## Item candidates

| Item ID  | Name          | Kind  | Parent item IDs | Feature refs       | Status      | Evidence refs                                 | Currentness |
| -------- | ------------- | ----- | --------------- | ------------------ | ----------- | --------------------------------------------- | ----------- |
| ITEM-001 | 注文検索API   | api   | なし            | FEAT-001           | implemented | feature-analysis@feature-r1, SPEC-001@spec-r1 | current     |
| ITEM-002 | 注文CSVバッチ | batch | ITEM-001        | FEAT-001, FEAT-002 | planned     | feature-analysis@feature-r1                   | current     |

## Stable ID history

| Item ID  | Change  | Reason                         | Related item IDs | Evidence refs               |
| -------- | ------- | ------------------------------ | ---------------- | --------------------------- |
| ITEM-001 | created | APIを独立に確認するため        | なし             | feature-analysis@feature-r1 |
| ITEM-002 | created | バッチ経路を親子で追跡するため | ITEM-001         | feature-analysis@feature-r1 |

## Candidate identification metrics

| Metric                                             | Status   | Numerator | Denominator | Rate | Basis                          |
| -------------------------------------------------- | -------- | --------- | ----------- | ---- | ------------------------------ |
| Confirmed feature-to-item candidate identification | measured | 2         | 2           | 100% | confirmed active features only |
| Unrepresented known feature candidates             | none     | 0         | 2           | N/A  | source boundary complete       |

## Separate owner metrics

| Separate owner metric                    | State                                 | Value             |
| ---------------------------------------- | ------------------------------------- | ----------------- |
| Item-condition applicability decision    | E / `test-condition-design` owns this | Not provided by D |
| Formal TCN / CI / expected-result design | E / `test-condition-design` owns this | Not provided by D |
| Test execution                           | Execution owner                       | Not provided by D |

## Unknown, stale, blocked, or resume conditions

| Scope or item | State   | Evidence or missing input           | Resume owner / condition                 |
| ------------- | ------- | ----------------------------------- | ---------------------------------------- |
| item artifact | blocked | provider CAS/readback not connected | A / select provider and confirm revision |

## Handoff

Send ITEM-001 and ITEM-002 refs, source revisions, candidate fingerprint, history, and local validation evidence to `test-condition-analysis` and E. The helper output is an unpersisted candidate payload; no provider revision or approval is asserted.
