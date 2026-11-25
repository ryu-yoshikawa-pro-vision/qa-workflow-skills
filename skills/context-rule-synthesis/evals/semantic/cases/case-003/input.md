# Evidence and counterexample review

Candidate claim: “Every archived object remains restorable for 30 days.” Review these records:

1. Current SPEC says invoices restore for 30 days. (spec)
2. DEC says exports restore for 14 days. (decision)
3. Approved ASM says restoration is unavailable during an active legal hold. (approved_asm)
4. A user says “I think the period is always 30 days”; approval is pending. (unapproved_user_response)
5. Current UI inspection observed Restore disabled in build 5.2 while the lifecycle worker was stopped. (impl_observation)
6. An exploratory finding reports restoration failed on day 31. (exploratory_finding)

Classify counterexamples: an export within its own 14-day scope; an invoice restore failure reproduced inside its 30-day window with active entitlement; a new DEC changing invoice retention; a run with the worker stopped; source text showing the hypothesis confused archive with soft-delete; an unexplained mismatch whose class is unknown.

依頼: 全証拠をつないで候補状態を決める。
