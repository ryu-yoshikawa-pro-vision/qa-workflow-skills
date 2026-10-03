# Keyboard interaction trace

- Browser: Playwright CLI, repository-owned Chromium session `ue-dialog-fixture-output`.
- Initial opened-dialog snapshot: the dialog heading and description were present; `Remove API token` was the active button.
- After Tab moved beyond the dialog, the browser snapshot marked the background `Create API token` button active while the dialog remained present.
- After Escape, a fresh snapshot still showed the dialog and marked the background `Create API token` button active.
- No destructive button was activated. No external URL or account was used.

This trace records only the observed fixture interaction. It is not a WCAG pass/fail result or evidence about real user frequency.
