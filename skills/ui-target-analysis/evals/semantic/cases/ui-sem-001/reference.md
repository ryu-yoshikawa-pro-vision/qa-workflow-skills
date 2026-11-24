# 判定根拠

## Source of Truth

- Record the screenshot's page, address form, Continue control, disabled appearance, and inline message as observations with `artifact://design/checkout` / `design-r7` provenance.
- Record the requirement's delivery-address and continue-to-payment intent with `doc://checkout/requirement` / `req-12` as the separate expectation source.
- Mark postal-code validation rules, enablement timing, and invalid-submit behavior unresolved. Route those expectation decisions to `spec-analysis`; do not make the screenshot authoritative for them.
- Do not claim runtime validation or a successful submission from a static screenshot.
