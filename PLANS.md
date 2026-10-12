# Planの保存と実装契約

一般的なrepository調査、曖昧さの扱い、Planの構成は[`feature-plan Skill`](.agents/skills/feature-plan/SKILL.md)を正本とします。

## 保存

- 合意済みPlanは`docs/plans/`へ保存します。
- ファイル名は`docs/plans/{yyyy-mm-dd}_{HHMMSS}_{plan_name}.md`とし、timestampはJST（`Asia/Tokyo`）を使います。
- 再利用可能なひな形には[`plan-template.md`](.agents/skills/feature-plan/assets/plan-template.md)を使います。
- 既存Planの重要な目的、scope、validation、完了条件を実装時の独自判断で変えません。根拠のある必要最小限の修正は、理由をPlanと実装結果に記録します。

## 実装と完了

- Plan-onlyではPlanだけを変更し、実装しません。
- 実装依頼ではPlanの順序に従い、検証結果を完了条件ごとに確認します。
- 独立したvalidationは個別に実行・判定します。1つのfailureを後段のsuccessで隠しません。
- 未実行、実行不能、失敗したvalidationはPASSと区別して記録し、Planが定めるblocked条件を維持します。
- Planの完了条件がすべて満たされた場合だけ実装完了とします。
