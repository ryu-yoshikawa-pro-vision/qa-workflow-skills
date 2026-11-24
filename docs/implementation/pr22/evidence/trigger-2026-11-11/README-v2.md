# PR #27 E2E trigger evaluation evidence v2

- Source Skill package HEAD: `fc1478d2920e19daad749d305023bb16017bfe10`; current branch at capture: `aebe13f98e668c64e0c2d4c657941ccd6fce0cce`. The 24 current packages were re-hashed against the snapshot; 0 mismatches.
- Codex CLI `0.167.0`; each query attempt uses a fresh noninteractive `codex --no-daemon --strict-config exec --json --sandbox read-only --ephemeral` process.
- 10 official E2E train attempts are captured: 9 completed with exit 0, 1 timed out after 900 seconds and did not complete its Agent turn. First three queries each have 3 completed attempts: positive query 1 triggered E2E selection 3/3; negative queries 2 and 3 triggered it 0/3. Query 4's timed-out attempt read `test-analysis`; because the turn did not complete, it is excluded from E2E non-trigger scoring.
- Skill firing is scored only from explicit load events or successful completed command events reading that Skill's `SKILL.md`; answer wording and filename listings are not evidence. All per-attempt JSONL, query, response-if-any, stderr, and result are preserved.
- Final holdout is fixed at 16 queries in `holdout-queries.json`, 0 exact overlap with the six current Skills' official train/validation data; SHA-256 is in the index. It has not been run.
- All current Skills were copied into `.agents/skills/` from the source package snapshot. A repository `git worktree add` was denied by PreToolUse; no policy bypass was attempted.
- This remains partial evidence: only 3/20 E2E official queries have 3 valid attempts; other E2E cases, all other Skills, and holdout runs remain unexecuted.
