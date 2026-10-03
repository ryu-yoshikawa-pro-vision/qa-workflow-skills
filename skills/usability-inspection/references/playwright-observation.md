# Playwright Observation Boundary

The repository's current Playwright execution path owns browser I/O. The package runtime materializes fixed requests and normalizes returned values; it does not install or select a new browser framework.

Use exact role/name, label, visible text, current-session identity, or population-index resolvers only after user-facing discovery. Re-resolve the target in the active session before each element probe. Parent scope, document/session identity, population revision, match count, and freshness determine whether the target is usable.

Perform visual discovery without an implicit locator click that scrolls an offscreen element into view. When necessary, scroll explicitly through the user-facing page, save before/after evidence, and keep automation-targeted scrolling out of discoverability evidence. Actionability wait is evidence about the automation path, not elapsed user response time.

The fixed observation catalog has exactly sixteen canonical fields and one probe owner per field. Formal WCAG machine probes use a separate typed finite catalog; the semantic observation field vocabulary does not expose formal probe selection.

## Fixed page evaluation

The `responsive-conditions`, `responsive-boundaries`, and `interaction-timing` catalog rows use the package-owned `scripts/fixed_browser_probes.js` function. The Playwright CLI loads this exact file with `run-code --filename`; do not copy its logic into an inline command. The browser owner passes only the materialized typed request through the temporary `window.__usabilityInspectionFixedProbeRequest` slot, then invokes the fixed file. The file consumes and removes that slot before dispatching a finite probe key. The transport call only assigns request data; it must not read or calculate browser observations. A readable condition inventory may be complete while a particular condition remains `not-executable`; that condition does not count as an evaluated responsive variation.

Responsive boundary collection may change the viewport through `page.setViewportSize` and restores the original viewport in a `finally` block. It does not edit DOM or stylesheet state. Interaction timing requires a current exact resolver, one fixed Playwright action, one catalogued end predicate, a timeout, and a saved evidence reference. A package-owned `MutationObserver` and animation-frame check observe the end predicate; the event start and predicate detection use the same page `performance.now()` clock. The helper does not persist action values or predicate text.
