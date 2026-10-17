# 判定根拠

## Source of Truth

- Treat the single unversioned analysis as a legacy package input and migrate it to v00. The legacy text identifies `SPEC-007` as the login specification and `UNK-012` as the unresolved password-reset-link destination / behavior; preserve each identity for that same meaning.
- Do not reuse retired `SPEC-008` for a new or changed rule. Retired IDs remain reserved. Preserve the exact identity in the generated CHANGELOG stable-ID history as `SPEC-008 | retired`; current Authority rows should not retain it as active.
- The invoice selection, tax aggregation by currency, and resulting downloadable file are test-relevant structured flow / rule semantics. An extension may be used for the distinct export domain if its responsibility and split reason are stated, but the tax rule must remain represented in a standard structured row so downstream QA can trace it.
- Preserve the source's success, failure, and reset-link behavior without adding password policy details absent from the document.

## Prohibited

- Hand-numbering replacement IDs or silently changing retained identities.
- Leaving the tax transformation only in unstructured extension prose.
- Adding a generic migration framework or a package version policy other than ui-target-v1 default.
