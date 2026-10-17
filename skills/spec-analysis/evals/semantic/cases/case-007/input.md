# Eval Input

## Scope A: existing report download

The user selects an already generated report and downloads it. The product does not create a new file or transform its data.

## Scope B: invoice export

The user selects invoices. The product aggregates totals by currency, creates a CSV, and then downloads it.

## Scope C: unknown export behavior

The requirements say “download the activity file” but do not say whether the product generates or transforms the file.

## Authority ownership

Project Context owns project DEC / ASM records and provides canonical `DEC-xxx` / `ASM-xxx` lifecycle. A separate ADR system owns decision record `ADR-91`; it does not provide canonical DEC / ASM identity lifecycle or stable projection.

## Request

Create the maintained UI target analysis package and record conditional file applicability and Authority ownership accurately.
