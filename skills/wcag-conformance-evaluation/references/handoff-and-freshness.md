# Browser Handoff and Freshness

`wcag-conformance-evaluation` owns the formal evaluation and its required observation set. `qa-workflow` owns persisted handoff state, operation identity, claim/reservation lifecycle, return validation, closure, and resume. `usability-inspection` owns the browser and executes the typed scope.

The physical workflow state is the current PR #15 envelope with additive `state.handoffs`. An origin identity contains artifact ref, artifact revision, and local handoff ref. Operation refs are script-derived. Create `pending` by native CAS before owner start; acquire claim and shared resources; CAS `in-progress`; only then start the browser. The owner returns immutable result refs, evidence, currentness dependencies, execution state, and cleanup.

Production local filesystems do not provide CAS. A document hash is not a conditional-write token. If the provider lacks native atomic conditional write or release, do not start or resume. Repository canonical E2E uses a test-only SQLite CAS provider; it is never packaged as a production provider.

An exact duplicate immutable result can be reapplied idempotently without browser execution. Conflicting current returns require explicit supersedes lineage. After a started handoff, a new observation requires a new handoff ref linked with `retry_of_handoff_ref` and a new operation ref. Resume requires current origin and results, complete expected result closure, unambiguous lineage, successful cleanup and released reservations, then `closed` CAS, state reread, and a fresh resume decision.
