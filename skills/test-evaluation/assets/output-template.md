# Test evaluation output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置きます。`scripts/evaluation_runtime.py`の`evaluate-axes` / `summarize-improvements` / `handoff-status` / `verify-inputs`の出力をそのまま含め、LLMが指標値・軸の状態・改善の達成数を補完・修正しません。複数指標から独自の総合点を作りません。

```json
{
  "artifact_type": "evaluation_report",
  "schema_version": "1",
  "evaluation_status": "provisional",
  "raw_results_modified": false,
  "release_decision": "not_determined_by_this_skill",
  "inputs": [
    { "ref": "report:RPT-...", "revision": "...", "content_hash": "..." }
  ],
  "input_check": {
    "status": "current",
    "stale_refs": [],
    "unverified_refs": []
  },
  "metrics": [],
  "axes": {},
  "composite_score": null,
  "claims": [],
  "rejected_claims": [],
  "improvements": [],
  "improvement_summary": { "counts": {}, "achieved": 0, "not_complete": [] },
  "handoff": { "items": [], "closed": false, "open_items": [] }
}
```

`handoff.items[]`は`{item_ref, receiver, confirmation_verified}`とし、`confirmation_verified`は`handoff-status`が承認を検証した結果です。`claims[]`は`{axis, assertion}`で、根拠のない主張は`rejected_claims[]`にも同じ`{axis, assertion}`を載せます。改善は`improvements[]`に`advance-improvement`の出力（`improvement`）をそのまま載せます。
