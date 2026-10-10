# Evidence and Authority

## Evidence roles

- DOM/accessibility snapshot: element structure, computed role/name, and exposed states. It does not establish the complete visual presentation or prove an interaction occurred.
- Keyboard / interaction trace: focus entry, order, containment, dismissal, return, and state transitions for the tested state. It does not establish that the behavior is consistent across unobserved states.
- Screenshot: visible bounds, hierarchy, overlap, clipping, focus indicator, and content presentation at its recorded viewport/state. It does not establish accessible name, role, or keyboard behavior.
- Saved test evidence: immutable, read-only context from `test-target-inspection` or `test-execution` only when the workflow explicitly selected UI / UX evaluation.

Each claim must link to the evidence that supports it. Keep user impact as observed only when the evidence contains it; do not turn expert interpretation into a user-research result.

## Authority positions

- Project Authority: product-specific requirements or business rules. Cite its existing Authority ref. A public source does not create project adoption.
- Normative source: requirement strength within its specification. Applicability and a project conformance target still need context.
- Informative source: authoring or interpretive guidance, including APG and WCAG Understanding documents.
- Advisory source: heuristic or Design System advice unless the project adopts it.

When two binding Authorities conflict, preserve both source links and route the conflict to the Authority owner. Do not settle it with a fixed source ranking. General guidance never changes TC PASS / FAIL or assigns Product Risk scores.
