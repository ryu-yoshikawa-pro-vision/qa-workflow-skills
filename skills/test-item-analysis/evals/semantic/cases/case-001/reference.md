# 判定根拠

## 必須判断

- `feature-analysis` feature IDs and `test-item-analysis` item IDs are separate stable namespaces.
- The implemented search API can map to both checkout and refund feature IDs without duplicating its item ID by test level.
- The planned UI and planned batch remain planned; no observation or implementation assumption changes their status.
- A parent/child relation is shown only when source evidence supports it. The same display name "Checkout" does not justify reusing an ID without identity evidence.
- A possible split or merge preserves prior IDs and records an explicit relationship and reason. Retired IDs remain reserved.
- The older revision is stale or requires revalidation; the skill does not silently update it to current.
- Partial or unconfirmed feature inventory is shown as incomplete; no product-wide discovery rate is claimed.
- Formal item-condition applicability, TCN/CI, expected results, and execution remain with their owners.
