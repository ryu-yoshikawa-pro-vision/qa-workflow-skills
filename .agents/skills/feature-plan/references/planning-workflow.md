# Planning workflow

1. Read the request and identify the intended outcome, constraints, and explicitly excluded actions.
2. Inspect the current branch and diff, relevant plans, repository instructions, implementation, tests, and CI. Consult the issue or pull request when it defines scope.
3. Record verified facts with file or command evidence. Label assumptions, unresolved decisions, and risks.
4. Define the smallest scope that satisfies the request. Name existing behavior and contracts that must stay stable.
5. Order implementation steps by dependency. Give every validation a concrete command or observable acceptance result. Keep independent validations separate and state how failures or unavailable environments affect completion.
6. Confirm every completion condition maps to a planned change and validation, and every change supports the requested goal.
7. Save only an agreed plan under docs/plans/using PLANS.md. Do not start implementation from a plan-only request.
