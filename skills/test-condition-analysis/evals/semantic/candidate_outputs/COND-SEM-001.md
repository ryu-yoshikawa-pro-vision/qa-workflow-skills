These are **draft reusable candidates** based only on your description of AUTH-001. They remain unconfirmed; no item applicability is decided.

| Draft key                           | Candidate intent                                                                                            | Kind                        | Unknowns |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------- | -------- |
| `@draft:invalid-password-threshold` | Examine the invalid-password count around the stated five-attempt lock boundary.                            | Boundary                    |          |
| `@draft:consecutive-failure-state`  | Examine how consecutive invalid-password attempts accumulate and how that sequence is interrupted or reset. | State / transition          |          |
| `@draft:timed-restoration`          | Examine the relationship between the locked state, elapsed time, and configured restoration interval.       | Recovery / timing           |          |
| `@draft:authorization-paths`        | Examine how lock state and restoration relate to the distinct API and UI authorization paths.               | Authorization / integration |          |

The first three could be reused across authentication interfaces. API and UI are candidate item kinds for later review, not applicability assignments. Their different paths do not establish whether counters, lock state, or restoration mechanisms are shared.

Evidence and revision record:

- **Authority entity:** `AUTH-001`, as described in this conversation.
- **Known statements:** five consecutive invalid passwords trigger locking; restoration follows a configured interval; API and UI use different authorization paths.
- **Unknowns:** interval value and unit, timing start point, sequence-reset rules, and state sharing between paths.
- **Evidence revision:** not supplied. Source artifact identity, provider revision, and content hash are also unavailable; “current” has not been independently verified.
- **Inventory/item context:** feature-inventory snapshot and separate analysis report are absent; finalized item IDs are unavailable.

These missing inputs prevent validated materialization and stable `COND-*` allocation through the skill’s helper. Draft keys above are temporary references, not persistent IDs. Nothing has been saved.

After item candidates arrive:

1. Obtain the exact feature-inventory snapshot and its separate analysis report, current AUTH-001 source revision/hash, retained condition ID history, and item candidate artifact.
2. Use `condition_candidates.py` to allocate or retain stable IDs and record creation/revalidation history. Both artifacts must reference the same project scope and exact feature-inventory revision.
3. Supply only explicit, evidence-backed item–condition pair proposals. Do not generate the full item × condition product.
4. Run the advisory crosscheck and report unresolved item refs, items or conditions without pair proposals, stale evidence, conflicts, and incomplete source population as review prompts.
5. When AUTH-001 changes, preserve prior evidence in history and revalidate only linked candidates. Record the resolved interval against its actual revision; do not infer a value.

Formal applicability and design remain pending `test-condition-design`. Their counts and execution counts are **not provided**, rather than zero.
