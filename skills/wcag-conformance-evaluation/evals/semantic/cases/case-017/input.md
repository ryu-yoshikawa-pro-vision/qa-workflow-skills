# Case O: sampling procedure skipped

small / finite productでcomplete inventoryがあり、製品全体を評価可能。

The synthetic product has a complete, closed public-view inventory of exactly four target/state identities: `TARGET-O-HOME/home`, `TARGET-O-CATALOG/default`, `TARGET-O-CHECKOUT/review`, and `TARGET-O-CHECKOUT/confirmation`. Inventory activity `ACT-CASE-O-INVENTORY` and evidence `EVD-CASE-O-COMPLETE-INVENTORY` certify that this list covers the entire declared enclosure, with no other pages, states, languages, restricted views, third-party content, or separately hosted areas. All four identities are available for whole-product evaluation. The same evidence identifies the default checkout process: an unauthenticated visitor starts at the public home page, chooses the catalog, reviews checkout, and confirms; the confirmation state is the endpoint. A current/prior Step 4.2 packet for unchanged content and interactive states is supplied in `input-data.json`. Do not invent additional views or result facts.

The accompanying `input-data.json` contains sample identities produced by the production identity helper, the complete inventory refs, the source checkout sequence, and current/prior Step 4.2 result rows. Use the production helpers to validate the sampling skip, materialize the process, and evaluate result reuse.
