# 実Agent trigger evidence v3

- source HEAD: `d63b5588956b767c4ffac300c34ab0f30798c70a`
- Codex CLI: `0.167.0`
- 実行環境: tracked repository全体の一時copy。24 current Skill package／1,051 filesを同時登録し、package hash差分0、既存Skill名collision 0。
- 対象: `e2e-test-selection` train index 0、元dataset queryそのまま、独立fresh session 3回。
- 試行: 3/3 exit 0かつ`turn.completed`。JSONLは43／51／63 events。対象Skillの成功commandによる`SKILL.md` readは3/3、rate 1.0。positive queryの閾値`>0.5`をこのqueryに限り満たす。
- attempt 1では`qa-workflow` Skillとrouting資料のreadも記録された。attempt 2／3ではなし。これは追加routing観測として保持し、他のrouting queryと合わせて評価する。
- 応答は対象repositoryに業務アプリの根拠がないため選定をblockedとした。応答の文言やSkill名の記載は発火判定根拠にしていない。
- archive: `trigger-evidence-v3.tar.gz`、461,464 bytes、SHA-256 `2af2def2484a1c1a32c0ffb672ccaeae350a65c8775ca33d127abcb63970d21a`。credential-shaped pattern scan 0 hits。
- この結果は1 queryだけのpartial checkpointであり、dataset全体、他Skill、holdout、局所受入をPASSとはしない。

各試行の生JSONL、応答、stderr、query、dataset pointer、イベント抽出結果、全Skill package manifestはarchive内にある。前身のreduced snapshot archive v1／v2は予備評価として別に保持している。
