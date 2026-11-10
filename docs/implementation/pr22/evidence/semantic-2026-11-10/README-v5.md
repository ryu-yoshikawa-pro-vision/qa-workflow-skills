# Semantic評価証拠 v5

- source HEAD: `f91f40b68cb01136b48fe953e315f418ff54547e`
- manifest: 31 cases; candidates generated and judged: 20/31
- verdicts: pass 16, needs_review 4, fail 0, Judge error 0
- criterion statuses: {"pass": 68, "needs_review": 4}
- Candidate generation and Judge used independent Codex sessions per case; both used the same default configured model family, whose identifier was not exposed.
- Source heads: agent-v2 was generated before commit 6c3 on the bda-based worktree; its included non-E2E inputs and Skill docs were hash-checked against current sources. agent-v4/v5/v6/v7 used the 6c3 Skill/input source; agent-v8 used 69ab, agent-v9 used d5, and agent-v10 used f91. Later commits after each case source did not change that case’s Skill or input files.
- E2E cases and TCN-SEM-002 were generated with a Skill copy excluding evaluation files. Earlier v2/v4 packages contained evaluation files; command traces were audited and no command targeting reference/rubric content was observed. This is a weaker isolation boundary and is called out for reviewer consideration.
- v5 adds current-input `TCN-SEM-007` from source HEAD `f91f40b`; the Judge returned pass for all four requested criteria.
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
| `test-condition-design`   | `TCN-SEM-004`     | 1102.4 s | pass         |
| `test-condition-design`   | `TCN-SEM-005`     |  744.4 s | pass         |
| `test-condition-design`   | `TCN-SEM-006`     |  897.8 s | pass         |
| `test-condition-design`   | `TCN-SEM-007`     | 1017.7 s | pass         |

The full evaluator status, criterion reasoning, exact input/output, and traces are in `semantic-evidence-v5.tar.gz` and `evidence-index-v5.json`.

Earlier v2/v3 archives contain an incorrect normalized `TCN-SEM-002/judge-result.json` copied from a later case; their raw Judge data is retained. v4 and v5 contain the correct normalized TCN-002 result, and v1 also contains the correct 16-case TCN-002 record. Prior archives are preserved.
