# WCAG-EM 2.0 Methodology

Use the official WCAG Evaluation Methodology (WCAG-EM) 2.0 W3C Group Note for Steps 1–5. It was published on 23 July 2026 and is informative methodology. Define a self-enclosed Web product and conformance target; explore its views, functionality, content types, technologies, and accessibility-relevant areas; select representative structured and random samples or justify sampling skip from a complete inventory; identify complete processes; evaluate all required criteria and conformance requirements; report outcomes and examples.

Scope coverage explicitly closes third-party content, language versions, responsive/device variants, separately hosted product areas, and authenticated/restricted views. Additional in-purpose evaluation requirements receive generated `ADDREQ-*` refs and affected output closure. Do not remove a requirement because a report format is inconvenient.

When sampling is used, random target count is derived by the deterministic helper from structured sample count using the Plan's ceiling rule. Structured and random samples do not overlap. A finite candidate inventory can support script-derived selection; an external random mechanism records its method and provenance. Never use a fixed seed. A skipped sampling procedure still requires complete processes and Step 4.2 process evaluation.

Evaluate each current `sample × required presentation variation × required Success Criterion` row and complete process. Step 4.3 compares normalized content type and finding group sets; the script determines whether to close or return to Steps 2–3. Repeat until no new type or finding appears under the Plan's closure conditions.
