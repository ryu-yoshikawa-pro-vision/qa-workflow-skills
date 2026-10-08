# Canonical usability and WCAG fixture

This static fixture exercises repository orchestration and observation contracts. It is not evidence that an external product conforms to WCAG.

## Fixed environment

- Start from the repository root with `python -m http.server 4173 --directory tests/skills/fixtures/usability-canonical`.
- Entry point: `http://127.0.0.1:4173/`.
- Browser: Chromium through the repository's existing Playwright browser path.
- Desktop viewport: 1280 × 800 CSS pixels.
- Responsive viewport: 390 × 844 CSS pixels.
- Input method: keyboard and pointer.
- Locale: `en-US`.
- Role and permissions: unauthenticated public visitor; no account, secrets, or personal data.
- Initial data: in-memory fixture state; reload resets the journey.
- Allowed side effects: local DOM state changes only. No network writes, account actions, or persistent storage.
- Cleanup: close the browser page or reload `/`; stop the static server with Ctrl+C.
- Evidence boundary: retain opaque current-document identity and browser observation refs, screenshots only when needed; never save raw URL components or environment secrets.

The same URL can show distinct in-memory states (overview, cart, details, confirmation), while the cart can also be reached by a second navigation path. `?view=alternate` renders the same information and controls with a different presentation. `/title-empty.html` provides a whitespace-only HTML title for ACT Rule 2779a5 negative observation. `/manual-limitations.html` contains intentionally unresolved gradient/background and complex focus styling for manual-fallback routing fixtures. `/ua-text-scaling-manual.html` records the browser-owned page-zoom capability outside the Playwright page owner's control surface. `/text-scale-unreadable.html` has an author-provided control that redraws visible text on canvas; the fixed probe can operate it but cannot read the canvas glyph scale. `/container-query-cases.html` provides a container size query whose declaration and computed color are identical, a style query, two named candidate containers, and an independent media query; only the media match state and boundary are executable through the fixed browser API contract.

At the responsive breakpoint, the Text size control uses settings from 100 through 150 while rendering text from 100% through 200%. Its output and accessible value text expose the rendered scale; the formal probe must measure used font sizes instead of treating the control value as the scale.
