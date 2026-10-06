# Case R: sample identity

The source observations, access locators, and evidence refs below are synthetic source facts. Derive state identity from the observed content and use the production sample identity registry; these source facts contain no canonical sample refs, state keys, registry rows, or fingerprints.

Target `TARGET-CASE-R-CATALOG` is in scope `SCOPE-CASE-R-CATALOG` at `https://northstar.example.invalid/catalog`; complete source evidence is `EVD-CASE-R-COMPLETE-OBSERVATIONS`, revision `rev-1`.

| Source record | Locator / observed content | Selected filter | Visible products | Evidence |
| --- | --- | --- | --- | --- |
| `OBS-CASE-R-ALL` | Open the catalog page; heading “All products”; URL `https://northstar.example.invalid/catalog` | All products | `PRODUCT-R-101`, `PRODUCT-R-102` | `EVD-CASE-R-ALL` |
| `OBS-CASE-R-TRAIL-DIRECT` | Choose Trail in the catalog category filter; heading “Trail products”; same URL | Trail | `PRODUCT-R-101`, `PRODUCT-R-103` | `EVD-CASE-R-TRAIL-DIRECT` |
| `OBS-CASE-R-TRAIL-NAV` | Open Trail products from the site navigation; heading “Trail products”; same URL | Trail | `PRODUCT-R-101`, `PRODUCT-R-103` | `EVD-CASE-R-TRAIL-NAV` |

同じURLで異なるapplication stateを持つ2 viewと、同じstateを別経路で観測した2 recordを入力する。
