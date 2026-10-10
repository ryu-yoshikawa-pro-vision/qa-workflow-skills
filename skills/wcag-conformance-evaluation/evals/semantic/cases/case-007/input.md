# Case F: no unique random candidate

complete finite inventoryまたはscope-wide exhaustionを証明できる外部mechanismで、新しいunique sampleが存在しない。

The complete finite inventory evidence `EVD-CASE-F-COMPLETE-INVENTORY` contains exactly three target/state identities: `TARGET-F-HOME/default`, `TARGET-F-CATALOG/default`, and `TARGET-F-CHECKOUT/review`. All three are already in the structured sample refs `STRUCT-F-001`, `STRUCT-F-002`, and `STRUCT-F-003`, respectively. The inventory source `ACT-CASE-F-INVENTORY` is complete for the full declared product enclosure; no other target/state identity exists in scope. This is a synthetic case-local inventory and does not assert an external product result.

The current Step 3 evaluation still requires the already-requested random sample; that request has not been cancelled or marked not applicable. The complete inventory has no eligible target/state identity outside the structured refs, so no new identity is available for selection.
