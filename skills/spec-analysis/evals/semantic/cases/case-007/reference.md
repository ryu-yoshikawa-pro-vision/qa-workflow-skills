# 判定根拠

## Source of Truth

- Scope A is simple download only; do not require the export / transformation file. Its user-visible download belongs in the download responsibility.
- Scope B generates and transforms a file before download; the flow / data file and the download / external interaction file are both applicable.
- Scope C has an unknown conditional trigger. Keep the trigger as undetermined and attach an UNKNOWN that blocks the affected scope; do not mark the file not applicable.
- Project Context DEC / ASM IDs may be represented through its owner-provided canonical lifecycle. Preserve the `DEC-xxx` / `ASM-xxx` form.
- ADR-91 is an external record identifier and cannot be copied into `authority_id` as a DEC or ASM. Because its owner has no canonical lifecycle or stable projection, do not register it as a current Authority in this package.

## Prohibited

- Requiring every conditional file for all three scopes.
- Marking Scope C's trigger not applicable by assumption.
- Promoting an external identifier into a canonical DEC / ASM slot.
