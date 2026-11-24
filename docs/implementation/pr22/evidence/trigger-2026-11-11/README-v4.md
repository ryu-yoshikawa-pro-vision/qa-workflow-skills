# 実Agent trigger evidence v4

- source HEAD: `d63b5588956b767c4ffac300c34ab0f30798c70a`
- Codex CLI: `0.167.0`
- 実行環境: tracked repository全体の一時copy。24 current Skill package／1,051 filesを同時利用し、source package hash差分0、既存Skill名collision 0。
- 対象: `e2e-test-selection` train index 1「このTC-014を使って既存Playwright E2Eを実行してください。」をそのまま独立fresh Codex execで3回実行。
- 試行: 3/3 exit 0かつ`turn.completed`。対象`e2e-test-selection`の成功commandによる`SKILL.md` readは0/3、`e2e-test-execution`は3/3。negative queryの閾値`<0.5`をこのqueryに限り満たす。
- JSONL trace、応答、stderr、exact query、dataset pointer、全Skill package manifestは`trigger-evidence-v4.tar.gz`内に保存。
- archive: 217,546 bytes、SHA-256 `29d7ca8d66fa08369087226a930de675c04745d5a57ff1c344296acba3262292`。credential-shaped pattern scan 0 hits。
- この結果は1 negative queryだけのpartial checkpointであり、dataset全体、他Skill、holdout、局所受入をPASSとはしない。
