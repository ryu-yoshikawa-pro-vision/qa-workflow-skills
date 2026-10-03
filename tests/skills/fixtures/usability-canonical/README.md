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
- Evidence boundary: retain fixture URL, browser observation refs, screenshots only when needed; do not capture environment secrets.

The same URL can show distinct in-memory states (overview, cart, details, confirmation), while the cart can also be reached by a second navigation path. `?view=alternate` renders the same information and controls with a different presentation. `/manual-limitations.html` contains intentionally unresolved gradient/background and complex focus styling for manual-fallback routing fixtures.
