# 実Agent trigger evidence v7

- source Skill snapshot HEADは`d63b5588956b767c4ffac300c34ab0f30798c70a`。Codex CLI `0.167.0`、24 current Skill／1,051 package filesを同時利用できるfull tracked repository copyで実施した。
- E2E train index 3「E2E対象選定ではなく、変更のProduct Riskとテスト重点を分析して。」を、freshなread-only `codex exec`でattempt 1・2として各900秒実行した。いずれもtimeoutし、Agent turn／`turn.completed`／最終responseはなかった。
- attempt 1は124 JSONL events／50 command starts。`test-analysis/SKILL.md`読取を観測し、`e2e-test-selection/SKILL.md`読取はなかった。
- attempt 2は124 JSONL events／54 command starts。`test-analysis/SKILL.md`に加え、event 113で成功したcommandによる`e2e-test-selection/SKILL.md`読取を観測した。Agent turn未完了のため、これは診断的観測に留め、trigger rateには算入しない。
- attempt 3はdriverが開始を表示した直後、ユーザー指定のcheckpointで中断した。query／dataset pointer以外のtraceやresultは生成されず、採点しない。
- このqueryの有効な完了試行は0/3で、発火率は判定できない。先行query 1〜3の9完了試行は有効記録として維持する。
- `trigger-evidence-v7.tar.gz`は696,013 bytes、SHA-256 `08f15eb7e1c4617a6750e185a3b299b0672bb73731727bbecea269a0081ee01c`。archive integrityとcredential-shaped pattern scanを確認し、検出0件。
- 次回は最新HEADに対応するSkill hashを確認したfresh full-tree snapshotからこのqueryの3回の有効完了試行をそろえてから続行する。既存timeout／中断を成功試行へ読み替えない。
