# 共通テスト条件候補

## Scope and source snapshot

| Field                                   | Value                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Project scope                           | project:shop                                                                                     |
| Candidate artifact ref                  | condition-candidates:shop                                                                        |
| Candidate update / analysis status      | candidate_ready_unpersisted / complete                                                           |
| Feature inventory ref / revision / hash | feature-analysis / feature-r1 / aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| Authority refs / revisions              | AUTH-001 / spec-r1                                                                               |
| Confirmed source boundary               | complete                                                                                         |
| Candidate model fingerprint             | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb                                 |
| Provider revision / readback            | 未保存 / 未確認                                                                                  |

## Condition candidates

| Condition ID | Name                     | Intent                                                  | Kind          | Applicable item kinds | Feature refs | Known item refs | Candidate state | Authority refs   | Evidence refs         | Currentness | Unknowns |
| ------------ | ------------------------ | ------------------------------------------------------- | ------------- | --------------------- | ------------ | --------------- | --------------- | ---------------- | --------------------- | ----------- | -------- |
| COND-001     | 連続認証失敗とロック復旧 | 5回の連続失敗後のロックと設定時間後の復旧を確認する候補 | authorization | api, ui               | FEAT-001     | 未確定          | candidate       | AUTH-001@spec-r1 | spec-analysis@spec-r1 | current     | なし     |

## Advisory item-condition candidate pairs

| Item ID | Condition ID | Candidate state | Rationale                         | Evidence refs    |
| ------- | ------------ | --------------- | --------------------------------- | ---------------- |
| 未確定  | COND-001     | unconfirmed     | item candidates are not finalized | AUTH-001@spec-r1 |

## Candidate gaps and source boundary

| Finding            | State       | Refs     | Evidence / recheck condition      |
| ------------------ | ----------- | -------- | --------------------------------- |
| item applicability | unconfirmed | COND-001 | wait for item candidate inventory |

## Separate owner metrics

| Metric                                        | Owner                         | State              | Count |
| --------------------------------------------- | ----------------------------- | ------------------ | ----- |
| Common condition candidates                   | D / `test-condition-analysis` | current candidates | 1     |
| Explicit item-condition candidate pairs       | D / `test-condition-analysis` | advisory only      | 0     |
| Formal applicability / adoption / disposition | E / `test-condition-design`   | Not provided to D  | N/A   |
| Formal TCN / CI / expected-result design      | E / `test-condition-design`   | Not provided to D  | N/A   |
| Test execution                                | Execution owner               | Not provided to D  | N/A   |

## ID history and resume

| Condition ID | Change  | Reason                                    | Related condition IDs | Evidence refs    |
| ------------ | ------- | ----------------------------------------- | --------------------- | ---------------- |
| COND-001     | created | common authentication condition candidate | none                  | AUTH-001@spec-r1 |

| Scope              | State   | Missing evidence or blocker         | Resume owner / condition                 |
| ------------------ | ------- | ----------------------------------- | ---------------------------------------- |
| condition artifact | blocked | provider CAS/readback not connected | A / select provider and confirm revision |

## Handoff

Send COND-001 and its Authority/source refs to E. It is a reusable candidate, not an adopted TCN, CI, expected result, or execution instruction.
