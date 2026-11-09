# Test condition analysis guidance

## Owner boundary

`test-condition-analysis` owns common condition candidate identity, intent, source/Authority refs, reusable scope, lifecycle, candidate history, revision impact, and advisory candidate crosschecks. It does not own formal item-condition adoption, applicability/disposition, formal TCN, CI, expected-result candidates, or execution. Those stay with `test-condition-design` and the execution owner.

Candidate source may be incomplete. A condition without confirmed Authority must remain `unconfirmed` or `blocked` and include an explicit unknown or blocker. General testing techniques and catalogs are prompts to search, not evidence that a condition applies to a product.

## Identity and lifecycle

- IDs use `COND-001`, `COND-002`, … and are allocated from retained `id_history`; new IDs are not user supplied.
- `candidate_key` and `@draft:<key>` are invocation-local only.
- `reuse` cites an existing condition with the same meaning. `split` and `merge` allocate a new ID and cite related IDs and rationale. A merge does not retire the original IDs automatically.
- Explicit retirement records evidence and leaves the retired ID in `id_history` permanently.
- Similar display names do not force an ID merge. Meaning equivalence requires owner judgment and a recorded decision.

## Advisory crosscheck

`crosscheck` reads a validated item artifact and condition artifact from the same project scope and the exact same feature inventory revision. It accepts only explicit `{item_id, condition_id, status, rationale, evidence_refs}` suggestions with status `proposed`, `unconfirmed`, or `blocked`. Formal adoption, exclusion, duplicate, not-applicable, TCN, CI, and expected-result states are rejected.

The helper reports known feature candidates without an active item, items and conditions without pair proposals, and a candidate identification rate only when the source boundary is complete and the confirmed active feature denominator is nonzero and current. A condition without a pair proposal is not automatically inapplicable; an item without one is not automatically missing a condition.

## Source impact

Each evidence ref contains `owner`, `scope`, `artifact_ref`, provider `revision`, and lowercase SHA-256 `content_hash`. A change at the same source identity but a different revision/hash marks only linked candidates stale. A missing current source makes its dependent candidate unknown. Preserve old evidence in history until the owner revalidates it.
