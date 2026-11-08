# Eval Input: 正方向のCheckout Complete画面表示ケース

これは固定QTS revisionを根拠にした、自己完結した**合成上流QA成果物**です。以下の`TR`、`TCN`、`CI`、`SPEC` IDはこの評価入力内だけの安定IDであり、QTS repositoryが同じIDで管理する成果物だとは主張しません。

## 固定対象と仕様根拠

- Product source: `qa-training-store` revision `84ce165493649550832731a60cf436f8ae29c56b`
- Current Authority Entity: `SPEC-001`、種別`SPEC`、状態`current`
- Source: `docs/spec/features/checkout-and-payment.md`、SHA-256 `8feab2db05f6e3c46f909539bb6b5136ed7705ccdc3265c25f124f349a9ad901`
- `SCREEN-CHECKOUT-COMPLETE`（source lines 181-187）: 完了画面にPayment成功、Order番号、注文履歴への導線を表示する。

このAuthority本文は上記の固定sourceから採った仕様内容をまとめた合成評価Entityです。Riskや一般慣習を製品仕様として追加しません。

## Current upstream entities

### Test Requirement Entity

- `TR-001` (current): Checkout Complete画面にPayment成功、Order番号、注文履歴への導線が表示されることを確認する。
- Priority: `高`

### Test Condition Entity

- `TCN-001` (current): Web UI test。対象はCheckout Complete画面の表示契約。現在の仕様根拠は`SPEC-001`。Priority: `高`。Scope: `SCOPE-001`。

### Coverage Item Machine Entity

- `TCN-001-CI01` (current, active, priority `高`)
- Source kind: `semantic_item`
- Semantic item key: `checkout-complete-display`
- Semantic item: Checkout Complete画面にPayment成功、Order番号、注文履歴への導線が表示される。
- Authority refs: `SPEC-001`
- Parent TCN: `TCN-001`
- Scope: `SCOPE-001`

### Prior Test Case state

このScopeにcurrentなTest Caseはありません。前回ID、inactive ID、update scope、inactive historyはいずれも空です。Coverage Itemはactiveで、仕様根拠と観測可能な成功条件がそろっています。

## Prepared test data and start state

- Customer: `CUST-001`としてログイン済み
- 合成テストデータ: Paymentは成功状態、Orderは支払済みでOrder番号`ORD-001`を持つ
- 開始状態: Checkout Complete画面を開き、`ORD-001`の成功注文データを対象として表示を始める。表示項目は事前確認しない。
- Test level: QTS Web UI screen-contract test。開始前に画面を開いた状態とし、Checkout確定から画面へ遷移することは検査しない。合否は画面に表示される3項目だけで判断し、DB/API/ログや未記載UIを期待しない。

## Required behavior

この入力は必要な上流本文・実行条件・期待結果根拠を含む正方向ケースです。仕様から画面表示を検証する詳細ケースを設計してください。`TCN-001-CI01`を少なくとも1つの実行可能ケースまたはruntimeが根拠付きで返す扱いへ閉じてください。単一の合否条件を番号付き期待結果1として示し、output-templateの番号形式で同じAuthorityへ対応付けてください。Checkout成功から当該画面へ遷移することはこの入力の検証対象ではありません。仕様にない振る舞いを追加しないでください。

既定の`assets/output-template.md`を使用し、`case_structure.py`を実際のcanonical normalized inputで実行してください。Machine Runtime Input / Result / Entitiesを最終成果物へ含め、生成したケースのstable IDとcurrent upstream dependenciesを保ってください。

## Canonical runtime input

以下はこの評価用に固定した、runtime generatorへの入力です。`input.test_cases`は空なので、case draftを設計してからその配列へ加えて実行してください。JSON全体を変えずに実行するのではなく、設計したdraft、実際に使うscope、固定source fingerprintを反映したcanonical requestを作ります。Authority本文と期待動作の意味は上記の固定sourceだけに従います。

```json
{
  "metadata": {
    "envelope_version": "1",
    "skill": "test-case-design",
    "runtime_contract_version": "runtime-v2",
    "generator_contract_version": "case-structure-v2",
    "runtime_unit_key": "artifact:case_structure:all",
    "model_key": null,
    "model_type": null,
    "technique_slug": null,
    "selection_source": null,
    "selection_key": null,
    "scope_key": null,
    "input_mode": "artifact",
    "upstream_entities": [
      {
        "skill": "spec-analysis",
        "entity_type": "authority",
        "entity_ref": "SPEC-001",
        "content": {
          "authority_type": "SPEC",
          "status": "current",
          "source_path": "docs/spec/features/checkout-and-payment.md",
          "source_revision": "84ce165493649550832731a60cf436f8ae29c56b",
          "source_sha256": "sha256:8feab2db05f6e3c46f909539bb6b5136ed7705ccdc3265c25f124f349a9ad901",
          "body": "SCREEN-CHECKOUT-COMPLETE (lines 181-187): Payment成功、Order番号、注文履歴への導線を表示する。"
        }
      },
      {
        "skill": "test-requirement-design",
        "entity_type": "tr",
        "entity_ref": "TR-001",
        "content": {
          "status": "active",
          "priority": "高",
          "authority_refs": ["SPEC-001"],
          "scope_refs": ["SCOPE-001"],
          "statement": "Checkout Complete画面にPayment成功、Order番号、注文履歴への導線が表示されることを確認する。"
        }
      },
      {
        "skill": "test-condition-design",
        "entity_type": "tcn",
        "entity_ref": "TCN-001",
        "content": {
          "status": "active",
          "priority": "高",
          "tr_refs": ["TR-001"],
          "scope_refs": ["SCOPE-001"]
        }
      },
      {
        "skill": "test-condition-design",
        "entity_type": "ci",
        "entity_ref": "TCN-001-CI01",
        "content": {
          "tcn_id": "TCN-001",
          "model_key": "scenario-001",
          "priority": "高",
          "authority_refs": ["SPEC-001"],
          "source_kind": "semantic_item",
          "execution": null,
          "semantic_item_key": "checkout-complete-display",
          "semantic_item_text": "Checkout Complete画面にPayment成功、Order番号、注文履歴への導線が表示される。",
          "semantic_source_targets": [],
          "test_data_requirement_refs": [],
          "scope_refs": ["SCOPE-001"]
        }
      }
    ],
    "upstream_runtime_units": [],
    "static_data_versions": {
      "qts_source_revision": "84ce165493649550832731a60cf436f8ae29c56b"
    },
    "authority_refs": ["SPEC-001"],
    "reference_refs": []
  },
  "input": {
    "test_conditions": [
      {
        "tcn_id": "TCN-001",
        "tr_refs": ["TR-001"],
        "priority": "高",
        "scope_refs": ["SCOPE-001"]
      }
    ],
    "coverage_items": [
      {
        "ci_id": "TCN-001-CI01",
        "tcn_id": "TCN-001",
        "model_key": "scenario-001",
        "priority": "高",
        "authority_refs": ["SPEC-001"],
        "source_kind": "semantic_item",
        "execution": null,
        "semantic_item_key": "checkout-complete-display",
        "semantic_item_text": "Checkout Complete画面にPayment成功、Order番号、注文履歴への導線が表示される。",
        "semantic_source_targets": [],
        "test_data_requirement_refs": [],
        "scope_refs": ["SCOPE-001"]
      }
    ],
    "environment_requirements": [],
    "test_data_requirements": [],
    "test_cases": [],
    "dispositions": [],
    "previous_tc_ids": [],
    "update_scope_tc_ids": [],
    "inactive_tc_ids": [],
    "inactive_tc_history": [],
    "zero_scope_terminal": false
  }
}
```
