# 判定根拠

## Source of Truth

- Scope A is a direct download of an already generated report: represent it as a UI operation / Behavior and delivery in 05; do not create a 04 business-flow row for it. 04 is not applicable.
- Scope B generates and transforms a file before download; 04 and the download / external-interaction file 05 are both applicable.
- Scope C's download interaction is specified, so 05 is applicable. Whether the product first generates or transforms the activity file is unknown, so 04's trigger is undetermined / blocked and has an UNKNOWN that blocks the affected scope. Do not mark 04 not applicable or required by assuming production behavior.
- Represent each specified download delivery as an INTERACT row in 05. For Scope C, record only the known user-visible download request; do not invent a generated-file source, transformation, or 04 FLOW identity.
- Project Context DEC / ASM IDs may be represented through its owner-provided canonical lifecycle. Preserve the `DEC-xxx` / `ASM-xxx` form.
- ADR-91 is an external record identifier and cannot be copied into `authority_id` as a DEC or ASM. Because its owner has no canonical lifecycle or stable projection, do not register it as a current Authority in this package.

## Prohibited

- Requiring every conditional file for all three scopes.
- Marking Scope C's trigger not applicable by assumption.
- Promoting an external identifier into a canonical DEC / ASM slot.
