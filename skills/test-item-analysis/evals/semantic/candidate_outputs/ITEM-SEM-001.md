This is a **provisional, narrative-only candidate list**, not a validated `test-item-candidates-v1` artifact. No stable IDs are allocated.

| Provisional candidate | Kind     | Narrative-supported status                                 | Relationship evidence                                                |
| --------------------- | -------- | ---------------------------------------------------------- | -------------------------------------------------------------------- |
| Checkout workflow     | Workflow | Confirmed as a workflow; implementation status unspecified | Relationship to individual UI/API/batch items remains unverified     |
| Checkout UI           | UI       | Planned; not implemented                                   | Associated with checkout in the narrative                            |
| Existing search API   | API      | Implemented                                                | Supports checkout and refund; retain as one shared candidate         |
| Nightly batch         | Batch    | Planned; implementation not confirmed                      | Consumes API output; producer–consumer linkage requires verification |

These names are descriptive labels, not identities. No parent/child hierarchy, formal feature references, or source currentness is established. Refund is a supported feature association in the narrative; that alone does not establish a separate refund item.

The reviewer-supplied older item must remain separate:

| Older record | Preserved information                          | Unresolved identity                                                                                                                                                |
| ------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| “Checkout”   | Reviewer supplied an older item with this name | Its ID, kind, implementation status, history, and currentness are unavailable. Whether it represents the checkout UI, workflow, or another element is unconfirmed. |

Do not merge, reuse, rename, retire, or replace that older record based on its name.

Missing inputs and recheck conditions:

| Missing input                                                   | Recheck condition                                                                                                                               |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Exact B feature-inventory snapshot and separate analysis report | Obtain the exact paired objects; verify their identity, consistency, boundary, and accepted analysis status before using the feature population |
| Source references, revisions, and hashes                        | Obtain traceable evidence for each candidate and association before assessing currentness                                                       |
| Prior D item artifact and full ID/history records               | Validate retained identities and history before allocating or reusing stable IDs                                                                |
| Evidence identifying older “Checkout”                           | Compare meaning and source evidence before deciding whether it matches any candidate                                                            |
| Verified structural and dependency evidence                     | Confirm hierarchy separately from workflow association and API-output consumption                                                               |
| Provider revision and storage context                           | Establish the appropriate create/CAS precondition and independently verify readback before claiming persistence                                 |

Feature-to-item identification rates are **not calculable**: the confirmed feature population and its completeness/currentness are unavailable. Unrepresented known features likewise cannot be determined; this is an evidence gap, not a zero-gap result.

Stable-ID history, candidate fingerprint, validator result, and persistence remain unestablished. No formal test conditions or expected results are created.
