# Semantic評価証拠 v1

- source HEAD: `6c3e9f1e8c1e848fdec716e7f17395a75d42bda6`
- manifest: 31 cases; candidates generated and judged: 16/31
- verdicts: pass 12, needs_review 4, fail 0, Judge error 0
- criterion statuses: {"pass": 52, "needs_review": 4}
- Candidate generation and Judge used independent Codex sessions per case; both used the same default configured model family, whose identifier was not exposed.
- Source heads: agent-v2 was generated before commit 6c3 on the bda-based worktree; its included non-E2E inputs and Skill docs were hash-checked against current sources. agent-v4/v5/v6 used the current 6c3 source.
- E2E cases and TCN-SEM-002 were generated with a Skill copy excluding evaluation files. Earlier v2/v4 packages contained evaluation files; command traces were audited and no command targeting reference/rubric content was observed. This is a weaker isolation boundary and is called out for reviewer consideration.
- Compressed evidence archive contains input, actual candidate, raw Agent response, Agent JSONL/stderr, generation metadata, normalized Judge result, raw Judge response, Judge JSONL/stderr, and source Skill file hashes.

| Skill                     | Eval ID           |    Agent | Judge        |
| ------------------------- | ----------------- | -------: | ------------ |
| `test-analysis`           | `RISK-SEM-001`    |  595.5 s | pass         |
| `test-analysis`           | `RISK-SEM-003`    |  407.5 s | pass         |
| `test-analysis`           | `RISK-SEM-004`    |  498.3 s | pass         |
| `test-analysis`           | `RISK-SEM-005`    |  574.4 s | needs_review |
| `test-analysis`           | `RISK-SEM-006`    |  487.5 s | pass         |
| `test-requirement-design` | `TR-SEM-001`      |  502.6 s | pass         |
| `test-analysis`           | `RISK-SEM-002`    |  739.2 s | needs_review |
| `test-analysis`           | `RISK-SEM-007`    |  603.0 s | pass         |
| `test-requirement-design` | `TR-SEM-002`      |  710.9 s | pass         |
| `test-requirement-design` | `TR-SEM-003`      |  554.9 s | pass         |
| `test-condition-design`   | `TCN-SEM-001`     |  889.0 s | needs_review |
| `test-condition-design`   | `TCN-SEM-003`     |  911.5 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-001` |  312.3 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-002` |  179.1 s | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-003` |  643.3 s | needs_review |
| `test-condition-design`   | `TCN-SEM-002`     | 1189.9 s | pass         |

The full evaluator status, criterion reasoning, exact input/output, and traces are in `semantic-evidence-v1.tar.gz` and `evidence-index.json`.
