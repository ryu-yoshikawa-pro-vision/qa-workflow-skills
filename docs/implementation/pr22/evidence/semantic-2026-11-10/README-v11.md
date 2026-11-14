# Semantic評価証拠 v11

- semantic manifest: 31 cases。実candidate生成とJudge完了は26/31。
- Judge verdict: pass 19、needs_review 7、fail 0、not_evaluable 0、Judge実行エラー0。
- criterion status: pass 89、needs_review 9、fail 1。
- archive SHA-256: `3945ae71615adf77f79a2107fe6390ec3ee777fbac4412b84b4f26d78b4869ae`（2,389,453 bytes）。
- Codex CLI 0.167.0。Candidate AgentとJudgeはcaseごとに別のfresh exec sessionを使った。同じ既定model familyで、model IDはtraceに露出しなかったためモデル独立性は主張しない。
- v9では各caseの評価入力・実candidate・Judge-only reference／rubric・manifest case・normalized Judge結果を同じ証拠bundleへ保存した。reference／rubricはcandidate generation package・promptへ渡していない。
- v7はTCN-SEM-008を修正後のSkill指示で再生成し、TCN-SEM-009を追加した。v8はTCN-SEM-010、v9はTCN-SEM-011、v10はTCN-SEM-012、v11はTCN-SEM-013を追加した。TCN-008 Agentはexit 0／turn.completed、91 JSONL events／41 command events、740.4秒。独立Judgeは5 criteria中4 pass／1 needs_review。SEM-TCN-002はstable child identity不明時に既存blocked／unresolvedへ保留する結果となり、needs_reviewからpassへ変わった。SEM-TCN-005はneeds_reviewのまま。TCN-009 Agentはexit 0／turn.completed、175 JSONL events／74 command events、877.2秒。独立Judgeは4/4 criteria pass。TCN-010 AgentはCodex CLI 0.167.0で105 JSONL events／48 command eventsを記録し、`turn.completed`とartifact検証commandのexit 0を確認。親CLI subprocessは1200秒でtimeoutしたためCLI exit codeは未取得だが、67,536-byte candidateを保存した。別Judge sessionは5/5 criteria pass。Judge verdictは既存`normalize_judge_response()`で正規化した。
- TCN-SEM-008の残るneeds_reviewはSEM-TCN-005。Judgeは異なるcoverage strengthのwitness間に冗長実行があると評価した。一方で現行`materialize_coverage`は実行fingerprintが異なる候補をmergeできず、runtimeは不一致を拒否する。既存rubric/referenceの契約判断が必要なため、期待値やruntime条件は変更していない。旧TCN-008結果はv6 archiveに履歴として保持。
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
| `test-condition-design`   | `TCN-SEM-008`     |         740.4 | needs_review |
| `test-condition-design`   | `TCN-SEM-009`     |         877.2 | pass         |
| `test-condition-design`   | `TCN-SEM-010`     |             — | pass         |
| `test-condition-design`   | `TCN-SEM-011`     |         659.5 | pass         |
| `test-condition-design`   | `TCN-SEM-012`     |        1044.3 | needs_review |
| `test-condition-design`   | `TCN-SEM-013`     |        1240.3 | needs_review |

TCN-SEM-012 candidateはEval Inputがcurrent target fingerprint一致を保証する一方、入力にfingerprint値がなく、candidateがnull digestをmaterializeしてblocked扱いにしたため、JudgeはSEM-TCN-002／004をneeds_reviewとした。契約違反を実runtime不具合と断定できず、Skill・rubric・referenceは変更していない。

TCN-SEM-013の初回Agentは1200秒でtimeoutしcandidateを作らなかった。fresh retryはexit 0、turn.completed、178 JSONL events／82 command events、1240.3秒でcandidateを生成。独立Judgeは5 criterion中1 pass、3 needs_review、1 fail（SEM-TCN-006）で、case verdictはneeds_review。candidateはA/Bのgrouping predicateとrole intersectionを別TCN/modelに分離し、merge union conflict時にmerged CIを拒否する既存`coverage-techniques.md`規則を反映しなかった。同reference全文をAgent traceで読んだ記録がある。これをAgent出力の意味失敗として記録し、rubric／期待値やruntimeを変更しない。

全caseの入力、candidate、Judge-only reference/rubric、JSONL、raw response、criterion根拠は`semantic-evidence-v11.tar.gz`と`evidence-index-v11.json`に保存。indexのsource HEADと各case source HEADを照合して読む。

v2/v3 archiveはTCN-SEM-002のnormalized resultが後続caseのものと誤って梱包されている。raw responseとtraceは残す。v1およびv4以降には正しいTCN-002 normalized resultがある。

v1〜v10のarchive／indexは履歴として保持する。過去版は後続評価の履歴であり、現行結果v11と区別する。

TCN-010はAgent turn完了後にCLI subprocessがtimeoutしたため正常終了exit codeはなく、candidate存在と`turn.completed`を個別検証した。
