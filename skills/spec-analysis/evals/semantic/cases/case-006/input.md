# Eval Input

## Legacy input

The team has one unversioned `spec-analysis.md` file containing a login specification and UI notes. It has no package manifest or package version. The legacy text explicitly identifies `SPEC-007` as the login specification and `UNK-012` as the unresolved password-reset-link destination and resulting behavior. Existing references also identify `SPEC-008` as retired; it previously described an obsolete password rule.

The document describes login by email and password, a success redirect to the dashboard, a failed-login message, and a password-reset link whose destination and resulting behavior are unspecified. It also includes a CSV export domain with rows for selected invoices, a transformation that totals tax by currency, and a download action. The tax calculation affects downstream verification.

## Request

Migrate the existing analysis into a reusable package without changing the meaning of retained identities. Decide whether a dedicated extension file is justified and keep test-relevant semantics in standard structured rows.
