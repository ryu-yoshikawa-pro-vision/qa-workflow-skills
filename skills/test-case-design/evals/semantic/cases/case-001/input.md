# Eval Input
## Coverage Item
TCN-001-CI01: 有効な新名称を保存したとき、保存成功後の設定一覧に新名称が表示されること。

## 入力するCI Machine Entity（canonical）
```json
{
  "schema_version": "entity-state-v1",
  "skill": "test-condition-design",
  "entity_type": "ci",
  "entity_ref": "TCN-001-CI01",
  "model_key": "ep-001",
  "content": {
    "ci_id": "TCN-001-CI01",
    "tcn_id": "TCN-001",
    "model_key": "ep-001",
    "source_kind": "runtime_target",
    "covered_targets": [{
      "target_key": "ep:setting-name:valid",
      "target_ref": "sha256:22d41468991f1882b0a1d1573279e27cf2822d64ef1509f73da4e95d25e2c0af",
      "target_content_fingerprint": "sha256:447422553fd4116ca4f8b26e66ebcdc0de048a68dbf70a19011b22e88f963579",
      "execution_fingerprint": "sha256:1d8effe1feb499b0eeb51481c282e5e0f22f50d0308d06febbbb8b6e3b87285b"
    }],
    "execution": {
      "action": "save_setting_name",
      "precondition": {"existing_setting_name": "週次レポート"},
      "input": {"name": "年次レポート"},
      "observation": {"settings_list_contains": "年次レポート"}
    },
    "expected_result_root": "settings-list-contains-new-name",
    "priority": "中",
    "priority_override_reason": null,
    "authority_refs": ["AUTH-SETTING-001"],
    "reference_refs": [],
    "test_data_requirement_refs": ["data:setting-name-valid"],
    "semantic_item_key": null,
    "semantic_item_text": null,
    "semantic_source_targets": [],
    "status": "active"
  },
  "content_fingerprint": "sha256:479e6ff6d93ba5b8d7c25fc972ae33ec135a1e4a43b1cbe4a0967bf59a2cede9",
  "upstream_entity_dependencies": [],
  "runtime_dependencies": []
}
```

## Authority
- 設定名は1〜50文字。
- 有効な名称の保存成功時、設定一覧へ新しい名称が表示される。
- 保存前は設定編集画面に対象設定が存在する。
- 保存成功時のトースト表示は仕様にない。

## 前提環境
- `ENV-CHROME-EDITOR`: Chromeで、更新権限を持つ編集者としてログインできる。
- 対象設定「週次レポート」が存在する。

## Current Test Data Requirement
- `data:setting-name-valid`: `setting_name` は文字列「年次レポート」を使用する。

## 目的
初見実施者が実行できるLow-Level Test Caseを作る。
