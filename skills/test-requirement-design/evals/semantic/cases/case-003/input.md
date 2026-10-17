# Eval Input

## UI target artifact mode

Current package entities include:

- `AC-101`: A successful login reaches the dashboard.
- `AC-102`: A rejected login keeps the user on the login screen and presents an error.
- `AC-103`: Exact wording for the unregistered-account error is unresolved and the AC is blocked.
- Current `SPEC-101`: Authentication uses the registered email and password.
- Current `SPEC-102`: Login failure is recorded for audit.
- Product risk `RISK-101` (high): account access may be granted to the wrong user.

`AC-101` and `AC-102` reference the current login scope. `AC-103` is excluded from current AC Entity input because it is blocked.

## Request

Create artifact-mode test requirements. Preserve explicit AC links, keep Authority closure independent, and do not add concrete credentials, boundary values, or combinations absent from the package.
