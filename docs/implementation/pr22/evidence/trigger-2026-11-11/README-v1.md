# PR #27 E2E trigger evaluation evidence v1

- Source Skill package HEAD: `fc1478d2920e19daad749d305023bb16017bfe10`; current branch at capture: `8dff9c85b6dfb334652b4321c279fb37642d25f7`. Current 24 Skill packages were re-hashed against the copied snapshot; 0 mismatches.
- Codex CLI: `0.167.0`; a fresh `codex --no-daemon --strict-config exec --json --sandbox read-only --ephemeral` ran each attempt independently.
- Official E2E train: 12 cases (6 positive/6 negative); validation: 8 cases (4/4). This checkpoint contains the first 3 train cases, 9 attempts, all completed with exit 0. Positive case 1 triggered 3/3; negative cases 2 and 3 did not trigger E2E selection (0/3 each). The negative cases instead loaded `e2e-test-execution`, or `e2e-test-implementation` / `e2e-test-inspection`, consistent with their request.
- Every attempt includes query, result, JSONL, final response, and stderr. Skill firing is scored only from explicit load events or successful command events reading that Skill's `SKILL.md`; answer wording and filename listings do not count.
- Final holdout is fixed at 16 distinct queries in `holdout-queries.json`; it has 0 exact overlap with all six Skills' train/validation data and has not been executed. SHA-256 is recorded in the index.
- The evaluation snapshot was made by copying all current packages into `.agents/skills/`. The repository-owned worktree-add hook rejected `git worktree add`; no policy bypass was attempted. The original branch files were not changed by the eval runs.
- This is a partial checkpoint, not trigger acceptance. Only 3/20 E2E official queries are covered; other Skills, remaining E2E train/validation, all holdout trials and rates remain outstanding.
