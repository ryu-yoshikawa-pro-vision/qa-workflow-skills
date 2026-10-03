# Case AA: formal conformance input unresolved

「WCAGに適合しているか確認して」とだけ依頼され、target version / level / scope等を案件contextから解決できない。

利用可能なcurrent production runtime result（`wcag-conformance-evaluation` の `initialize-evaluation`）:

```json
{
  "status": "unresolved",
  "blockers": [
    {
      "reason": "required_input_missing",
      "fields": [
        "accessibility_support_baseline",
        "artifact_ref",
        "artifact_revision",
        "browser_user_agent_baseline",
        "cleanup_scope",
        "commissioner",
        "evaluation_date",
        "evaluation_period",
        "evaluator",
        "level",
        "live_web_target",
        "product_enclosure",
        "product_scope",
        "role_permission_environment",
        "side_effect_scope",
        "wcag_version"
      ]
    }
  ],
  "evaluation_ref": null
}
```
