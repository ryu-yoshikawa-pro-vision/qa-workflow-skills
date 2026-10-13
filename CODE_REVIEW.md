# Code review contract

一般的なreview workflowとfindingの出力は[`code-review Skill`](.agents/skills/code-review/SKILL.md)およびそのreferenceを正本とします。

## このrepositoryで確認すること

- 依頼、Issue、Plan、既存仕様、実装、test、CIとの適合を確認します。
- 正しさ、セキュリティとデータ保護、既存runtime・validator・QA Skill契約、回帰、test不足を優先します。
- formatterや文書変更でも、評価fixtureの意味、evaluation contract、artifact graph、runtime契約が変わっていないか確認します。
- 変更と関係のない既存問題、根拠の弱い推測、好みだけの指摘を今回のfindingに含めません。
- 明確な性能問題が変更範囲に関係する場合は確認します。過剰設計は追加観点として扱います。

## 境界

- review-onlyではコードを修正しません。修正依頼がある場合はbounded repair workflowへ切り替えます。
- 外部review serviceのfull reviewや再レビューは、ユーザーの明示指示または承認がある場合だけ起動します。
- 永続的なreview reportは、ユーザーが明示的に求めた場合だけ作成します。
