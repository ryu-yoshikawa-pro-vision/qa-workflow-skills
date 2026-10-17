# Case AI: browser再観測

The current WCAG target, home-view source observation, and baseline presentation condition are in `input-data.json`. Treat those as source facts and materialize the selected sample, variation, and typed criterion probe through the production helpers before continuing the handoff.

`HANDOFF-001` でbrowserを開始済みだがreturned resultがstaleになり、同じorigin revisionで再観測が必要になる。

This fixture has an existing formal evaluation `EVAL-CASE-AI`, unchanged origin revision `rev-4`, and a browser-started observation handoff `HANDOFF-001` owned by `usability-inspection`. The immutable result `RESULT-CASE-AI-OLD` was returned for the expected sample/variation/criterion request, but its currentness check marks the result stale; the origin evaluation remains current at `rev-4`. The owner already completed the first browser operation and its cleanup. The exact existing workflow state and stale-result check are supplied as current runtime output from the test-only SQLite CAS provider. The provider is test-only and is not a production storage adapter. No new browser observation has yet been started.
