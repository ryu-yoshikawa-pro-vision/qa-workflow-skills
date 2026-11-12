# Eval Input

## Coverage Item

TCN-002-CI01: 51文字の名称を保存しようとしたとき、保存されず既存名称が維持されること。

## 入力するCI Machine Entity（canonical）

```json
{
  "schema_version": "entity-state-v2",
  "skill": "test-condition-design",
  "entity_type": "ci",
  "entity_ref": "TCN-002-CI01",
  "model_key": "bva-001",
  "content": {
    "authority_refs": [
      "AUTH-SETTING-002"
    ],
    "ci_id": "TCN-002-CI01",
    "covered_targets": [
      {
        "execution_fingerprint": "sha256:34661894a1a41db667a056e027743d70d5a040272f720198b05a72eec232ddd1",
        "target_content_fingerprint": "sha256:e3be6654c202f763c3c1ee04e506fcee310cc68cde9d22885905ca6e5128a0a6",
        "target_key": "bva:setting-name-length:51",
        "target_ref": "sha256:058e0fc23816453cd174a6564b2e602909eaea2dfd4013abb9af11c77578ceaa"
      }
    ],
    "execution": {
      "action": "save_setting_name",
      "input": {
        "name_length": 51
      },
      "observation": {
        "saved": false,
        "settings_list_contains": "月次レポート"
      },
      "precondition": {
        "existing_setting_name": "月次レポート"
      }
    },
    "expected_result_root": "setting-name-not-saved-existing-name-kept",
    "model_key": "bva-001",
    "priority": "中",
    "priority_override_reason": null,
    "reference_refs": [],
    "scope_refs": [],
    "semantic_item_key": null,
    "semantic_item_text": null,
    "semantic_source_targets": [],
    "source_kind": "runtime_target",
    "status": "active",
    "tcn_id": "TCN-002",
    "test_data_requirement_refs": []
  },
  "content_fingerprint": "sha256:c342c4c342337991ad569886db9c2436e38448af112cc204ae33c7313f9f885b",
  "upstream_entity_dependencies": [],
  "runtime_dependencies": []
}
```

## 入力するAuthority Machine Entity（current）

```json
[
  {
    "schema_version": "entity-state-v2",
    "skill": "spec-analysis",
    "entity_type": "authority",
    "entity_ref": "AUTH-SETTING-002",
    "model_key": null,
    "content": {
      "active_content": {
        "text": "設定名は1〜50文字。51文字以上は保存不可。保存失敗時、設定一覧へ変更を反映しない。エラーメッセージ文言、表示位置、色は仕様未確定。"
      },
      "authority_id": "AUTH-SETTING-002",
      "authority_type": "SPEC",
      "related_authority_refs": [],
      "relations": [],
      "scope": null,
      "source_refs": [
        "SRC-SETTING-SPEC@rev-3"
      ]
    },
    "content_fingerprint": "sha256:60c0de18148a5d5d290d0a46fd361f59c30a44169922b90222ba4c4fb4663cd7",
    "upstream_entity_dependencies": [],
    "runtime_dependencies": []
  }
]
```

## Authority

- 設定名は1〜50文字。
- 51文字以上は保存不可。
- 保存失敗時、設定一覧へ変更を反映しない。
- エラーメッセージ文言、表示位置、色は仕様未確定。

## 前提環境

- 対象設定の現在名は「月次レポート」。
- 更新権限を持つユーザーでログイン済み。

## 目的

境界失敗系を具体的なPASS/FAIL Oracleを持つTest Caseへする。
