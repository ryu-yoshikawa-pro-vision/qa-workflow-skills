# Cross-workflow sources

Feature A: two independent specs say deleting a saved report requires a confirmation dialog. Feature B: an approved design decision says deleting a saved export also requires a confirmation dialog. Feature A is available to administrators only; Feature B allows a delegated operator with `export-delete` permission. Both apply to production builds 5.x. No source says all destructive operations in the product share this rule.

依頼: 共通条件と差異を候補化する。
