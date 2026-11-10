# Semantic評価証拠 v6

- semantic manifest: 31 cases。実candidate生成とJudge完了は21/31。
- Judge verdict: pass 16、needs_review 5、fail 0、not_evaluable 0、Judge実行エラー0。
- criterion status: pass 71、needs_review 6。
- archive SHA-256: `eac3d3dd1f571903b4518c5c2f00a29a164c76774cdfa4c62cee40a86d19da4d`（1,884,874 bytes）。
- Codex CLI 0.167.0。Candidate AgentとJudgeはcaseごとに別のfresh exec sessionを使った。同じ既定model familyで、model IDはtraceに露出しなかったためモデル独立性は主張しない。
- v6では各caseの評価入力・実candidate・Judge-only reference／rubric・manifest case・normalized Judge結果を同じ証拠bundleへ保存した。reference／rubricはcandidate generation package・promptへ渡していない。
- v6はTCN-SEM-008を追加した。Agentはexit 0／turn.completed、110 JSONL events／48 command events、911.2秒。実candidateは299,128 bytes。独立Judgeは5 criteria中3 pass／2 needs_review、verdict needs_review。`run.py` exit 1はneeds_review verdictを反映し、Judge adapter failureではない。
- TCN-SEM-008のneeds_review: SEM-TCN-002はinputが既存comb childを要求するのに、実candidateが`identity_action=new`で新規childを作成した。inputに既存childのretrievable identityがなく、正しい再利用対象を推測できない。SEM-TCN-005はrow witness重複を冗長な実行と判定したが、既存`materialize_coverage`契約の実行fingerprintは異なり、CI merge診断も拒否された。fixture／reference／契約判断が必要なため未修正。
- 生成側skill packageには`evals/`、`tests/`、`__pycache__`を含めない。v6のreference／rubricはJudge監査用の保存物であり、生成入力から分離している。
- v2/v3 archiveにTCN-SEM-002の誤ったnormalized resultが含まれていた件は履歴として保持し、v4以降で正しい結果を記録。過去archiveは削除・上書きしていない。

| Skill                     | Eval ID           | Agent seconds | Judge        |
| ------------------------- | ----------------- | ------------: | ------------ |
| `test-analysis`           | `RISK-SEM-001`    |         595.5 | pass         |
| `test-analysis`           | `RISK-SEM-003`    |         407.5 | pass         |
| `test-analysis`           | `RISK-SEM-004`    |         498.3 | pass         |
| `test-analysis`           | `RISK-SEM-005`    |         574.4 | needs_review |
| `test-analysis`           | `RISK-SEM-006`    |         487.5 | pass         |
| `test-requirement-design` | `TR-SEM-001`      |         502.6 | pass         |
| `test-analysis`           | `RISK-SEM-002`    |         739.2 | needs_review |
| `test-analysis`           | `RISK-SEM-007`    |         603.0 | pass         |
| `test-requirement-design` | `TR-SEM-002`      |         710.9 | pass         |
| `test-requirement-design` | `TR-SEM-003`      |         554.9 | pass         |
| `test-condition-design`   | `TCN-SEM-001`     |         889.0 | needs_review |
| `test-condition-design`   | `TCN-SEM-003`     |         911.5 | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-001` |         312.3 | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-002` |         179.1 | pass         |
| `e2e-test-selection`      | `E2E-SEL-SEM-003` |         643.3 | needs_review |
| `test-condition-design`   | `TCN-SEM-002`     |        1189.9 | pass         |
| `test-condition-design`   | `TCN-SEM-004`     |        1102.4 | pass         |
| `test-condition-design`   | `TCN-SEM-005`     |         744.4 | pass         |
| `test-condition-design`   | `TCN-SEM-006`     |         897.8 | pass         |
| `test-condition-design`   | `TCN-SEM-007`     |        1017.7 | pass         |
| `test-condition-design`   | `TCN-SEM-008`     |         911.2 | needs_review |

全caseの入力、candidate、Judge-only reference/rubric、JSONL、raw response、criterion根拠は`semantic-evidence-v6.tar.gz`と`evidence-index-v6.json`に保存。indexのsource HEADと各case source HEADを照合して読む。

v2/v3 archiveはTCN-SEM-002のnormalized resultが後続caseのものと誤って梱包されている。raw responseとtraceは残す。v1およびv4以降には正しいTCN-002 normalized resultがある。
