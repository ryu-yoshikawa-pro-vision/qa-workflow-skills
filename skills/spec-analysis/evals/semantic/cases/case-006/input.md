# Eval Input

## Legacy input

The team has one unversioned `spec-analysis.md` file containing a login specification and UI notes. It has no package manifest or package version. Existing references include current `SPEC-007`, current `UNK-012`, and a retired `SPEC-008` that previously described an obsolete password rule.

The document describes login by email and password, a success redirect to the dashboard, a failed-login message, and a password-reset link. It also includes a CSV export domain with rows for selected invoices, a transformation that totals tax by currency, and a download action. The tax calculation affects downstream verification.

## Request

Migrate the existing analysis into a reusable package without changing the meaning of retained identities. Decide whether a dedicated extension file is justified and keep test-relevant semantics in standard structured rows.
