# Case N: usability-evaluation integration

An immutable, synthetic `usability-inspection` result is already available for read-only evaluation. It concerns target `TARGET-CASE-N-SEARCH`, scope `visual-integrity`, and revision `rev-3`.

| Kind | Ref | Current input-reported fact | Evidence ref |
| --- | --- | --- | --- |
| Objective observation | `OBS-CASE-N-001` | After the search query `trail`, the result count changes from 2 to 1 and the visible status announces “1 result”. | `EVD-CASE-N-SEARCH-STATUS` |
| Requirement result | `REQ-CASE-N-001` | The declared status-message check is `satisfied` for this saved inspection scope. | `EVD-CASE-N-STATUS-CHECK` |
| Measurement | `MEAS-CASE-N-001` | The supplied current measurement records 120 ms from the actual input event to the first visible result-status update, using the same page clock. | `EVD-CASE-N-SEARCH-TIMING` |

The evidence refs are immutable and belong to `INSPECTION-CASE-N rev-3`. Do not operate a browser or change the recorded requirement result. Pass the objective observation, requirement result, measurement, and refs to `usability-evaluation` without supplying a semantic UX conclusion on its behalf. These are synthetic case facts, not evidence about an external product.
