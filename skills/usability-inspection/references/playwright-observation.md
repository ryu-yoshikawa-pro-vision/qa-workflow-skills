# Playwright Observation Boundary

The repository's current Playwright execution path owns browser I/O. The package runtime materializes fixed requests and normalizes returned values; it does not install or select a new browser framework.

Use exact role/name, label, visible text, current-session identity, or population-index resolvers only after user-facing discovery. Re-resolve the target in the active session before each element probe. Parent scope, document/session identity, population revision, match count, and freshness determine whether the target is usable.

Perform visual discovery without an implicit locator click that scrolls an offscreen element into view. When necessary, scroll explicitly through the user-facing page, save before/after evidence, and keep automation-targeted scrolling out of discoverability evidence. Actionability wait is evidence about the automation path, not elapsed user response time.

The fixed observation catalog has exactly sixteen canonical fields and one probe owner per field. Formal WCAG machine probes use a separate typed finite catalog; the semantic observation field vocabulary does not expose formal probe selection.
