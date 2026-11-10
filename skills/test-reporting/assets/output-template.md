# Test reporting output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置きます。`scripts/reporting_runtime.py build-snapshot`の出力（`report_snapshot`）をそのまま含め、LLMが件数・率・完了判定を補完・修正しません。人間向けの要約は、JSON blockの外に、`complete`・取得未完了のsourceと不足・単位別の率・終了判定・次の判断先を、JSONと矛盾しない範囲で書きます。

```json
{
  "artifact_type": "report_snapshot",
  "schema_version": "1",
  "snapshot_ref": "RPT-...",
  "population_basis": "planned",
  "plan_ref": "plan:...",
  "plan_revision": "...",
  "sources": [],
  "by_unit": {},
  "overall": { "complete": false, "population_known": true, "pass_rate": null },
  "exit_criteria": [],
  "exit_judgement": "undetermined",
  "defect_projection": { "count": 0, "issue_refs": [], "read_only": true },
  "release_decision": "not_determined_by_this_skill",
  "issues": []
}
```
