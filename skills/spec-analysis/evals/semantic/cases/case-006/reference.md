# 判定根拠

## Source of Truth

- Treat the single unversioned analysis as a legacy package input and migrate it to v00. Preserve `SPEC-007` and `UNK-012` for the same semantic identities.
- Do not reuse retired `SPEC-008` for a new or changed rule. Retired IDs remain reserved.
- The invoice selection, tax aggregation by currency, and resulting downloadable file are test-relevant structured flow / rule semantics. An extension may be used for the distinct export domain if its responsibility and split reason are stated, but the tax rule must remain represented in a standard structured row so downstream QA can trace it.
- Preserve the source's success, failure, and reset-link behavior without adding password policy details absent from the document.

## Prohibited

- Hand-numbering replacement IDs or silently changing retained identities.
- Leaving the tax transformation only in unstructured extension prose.
- Adding a generic migration framework or a package version policy other than ui-target-v1 default.
