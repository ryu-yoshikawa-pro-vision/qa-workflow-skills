# Performance and Measurement

Use exact script calculations for geometry, overflow, elapsed time, threshold comparisons, and supported numeric checks. Preserve original units and method. A project threshold requires its Authority ref. Without a threshold, report the measurement and `threshold-not-defined`.

When live page-load or performance measurement is in scope, use the package-owned fixed probes to collect applicable Navigation Timing and First Contentful Paint (FCP) values even if no provenance-bearing Core Web Vitals source exists. A missing Core Web Vitals source makes only LCP / CLS / INP unavailable; it does not suppress those independent measurements. Collect user-facing interaction timings only for an in-scope task or action with an observed input event and a fixed visible-feedback or task-ready predicate.

Start and end of user-facing interaction timing use the same page `performance.now()` clock and a fixed end predicate armed before the input. If the input event or end predicate cannot be observed, report `measurement-unavailable`. Do not include Playwright pre-action auto-wait in the user response interval.

Do not call a single interaction duration INP. Do not implement LCP, CLS, or INP locally. Accept Core Web Vitals only from an existing, provenance-bearing RUM, CrUX, web-vitals, or Lighthouse source with its environment and population metadata.
