# テスト観点・条件 / カバレッジ項目

## 観点範囲

- 対象テスト要求: 入力にテスト要求IDは提供されていない。対象は`SPEC-CRUD-001`のentity × function × operation matrixおよびlifecycle sequence（CRUD Coverage Itemの作成依頼）。
- テストレベル: 未提供
- 対象外: 入力に記載なし
- 仮定 / 未解決事項:
  - `SPEC-CRUD-001`を入力どおり現在有効な仕様根拠として扱う。現在有効性の照合は行っていない。
  - 関連テスト要求ID、優先度、プロダクトリスクは未提供のため、優先度は未決とする。
  - sequenceのpostconditionにあるInventoryReservationの全量release、BillingBalanceのplace前残高への復帰は、`SPEC-CRUD-001`がOrder操作（place / amend / cancel）との対応を明示していない。本成果物はこの因果対応を創作せず、sequenceの期待状態関係として保持する。

## テスト条件へ展開しないテスト要求

テスト要求IDが入力に無いため、テスト要求単位の閉鎖は実施できない。

| テスト要求ID | 扱い | 理由 / 根拠            |
| ------------ | ---- | ---------------------- |
|              |      | 入力にテスト要求IDなし |

## テスト観点・条件一覧

テスト観点IDはTR未提供のため未採番とする。CRUD技法の条件は次の2件とする。

| 観点ID | テスト要求ID | テスト観点 / 条件                                                                                                      | カテゴリ          | テスト技法 / 根拠            | カバレッジ基準                                                                          | 関連仕様根拠 / プロダクトリスク | 優先度 | 備考                                                 |
| ------ | ------------ | ---------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------- | --------------------------------------------------------------------------------------- | ------------------------------- | ------ | ---------------------------------------------------- |
| 未採番 | 未提供       | `order-lifecycle`のentity × operation matrixの全セルが、CRUD操作項目またはAuthority付きnot_applicableで閉じている      | CRUD completeness | CRUD Testing（completeness） | entity × function × operation の全12セルを、操作項目8件またはnot_applicable 4件で閉じる | SPEC-CRUD-001                   | 未決   | 機械証拠: crud-completeness                          |
| 未採番 | 未提供       | Orderの`place → amend → cancel`実行後、Order=cancelled、InventoryReservation=全量release済、BillingBalance=place前残高 | CRUD consistency  | CRUD Testing（consistency）  | 指定sequenceを実行した後の状態関係を確認する                                            | SPEC-CRUD-001                   | 未決   | 機械証拠: crud-consistency。cross-entity因果は未定義 |

## カバレッジ項目一覧

カバレッジ項目IDは`TCN-NNN-CINN`形式の採番前のため、runtime target keyで示す。個別操作の期待結果は`SPEC-CRUD-001`に定義がないため記載しない。

| カバレッジ項目（runtime target key）              | 観点ID | カバレッジ項目                                          | 導出元の技法 / 基準 | 期待挙動の根拠                         | 優先度 | 備考                                                       |
| ------------------------------------------------- | ------ | ------------------------------------------------------- | ------------------- | -------------------------------------- | ------ | ---------------------------------------------------------- |
| `crud:op:order:order-lifecycle:C`                 | 未採番 | Order × create（`place`）                               | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:order:order-lifecycle:R`                 | 未採番 | Order × read（`get`）                                   | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:order:order-lifecycle:U`                 | 未採番 | Order × update（`amend`, `cancel`）                     | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:inventory-reservation:order-lifecycle:C` | 未採番 | InventoryReservation × create（`reserve`）              | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:inventory-reservation:order-lifecycle:U` | 未採番 | InventoryReservation × update（`adjust`）               | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:inventory-reservation:order-lifecycle:D` | 未採番 | InventoryReservation × delete（`release`）              | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:billing-balance:order-lifecycle:R`       | 未採番 | BillingBalance × read（`get`）                          | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:op:billing-balance:order-lifecycle:U`       | 未採番 | BillingBalance × update（`charge`, `adjust`, `refund`） | CRUD completeness   | SPEC-CRUD-001のcell（操作名のみ）      | 未決   |                                                            |
| `crud:seq:order-place-amend-cancel`               | 未採番 | Order lifecycle `place → amend → cancel` と後状態       | CRUD consistency    | SPEC-CRUD-001のsequenceとpostcondition | 未決   | 後状態はOrder / InventoryReservation / BillingBalanceの3件 |

## カバレッジ候補の扱い

| 候補                                   | 導出元                                    | 扱い                            | 理由 / 根拠                            | カバー先 |
| -------------------------------------- | ----------------------------------------- | ------------------------------- | -------------------------------------- | -------- |
| `crud:missing:order:D`                 | SPEC-CRUD-001 Order × delete              | not_applicable（Authority付き） | matrixでOrder deleteは`not_applicable` | なし     |
| `crud:missing:inventory-reservation:R` | SPEC-CRUD-001 InventoryReservation × read | not_applicable（Authority付き） | matrixでread は`not_applicable`        | なし     |
| `crud:missing:billing-balance:C`       | SPEC-CRUD-001 BillingBalance × create     | not_applicable（Authority付き） | matrixでcreate は`not_applicable`      | なし     |
| `crud:missing:billing-balance:D`       | SPEC-CRUD-001 BillingBalance × delete     | not_applicable（Authority付き） | matrixでdelete は`not_applicable`      | なし     |

## 未解決の契約上の制約

- 最終runtime evidence gate（`verify_runtime_evidence`）は`valid=false`。親unit `artifact:condition_structure:all`の結果とMachine Entitiesが無いため。親runtimeにはテスト要求ID（TR）と技法の上流入力が必要で、本入力には含まれない。そのため、本成果物は完成済みとして扱わない。
- 採番済みTCN / CI IDは未付与。TR提供後に`condition_structure`と`materialize_coverage`で採番する。
- 個別操作の期待結果、sequenceの因果対応は`SPEC-CRUD-001`の追加定義が必要。

## Machine Runtime / Entity / Target mapping（機械証拠）

### Machine Runtime Input: test-condition-design::model:crud-001

```json
{
  "input": {
    "cells": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "function_key": "order-lifecycle",
        "operations": ["C", "R", "U"]
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "function_key": "order-lifecycle",
        "operations": ["C", "U", "D"]
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "function_key": "order-lifecycle",
        "operations": ["R", "U"]
      }
    ],
    "consistency_sequences": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "kind": "lifecycle",
        "sequence_key": "order-place-amend-cancel",
        "steps": [
          { "function_key": "order-lifecycle", "operation": "C" },
          { "function_key": "order-lifecycle", "operation": "U" },
          { "function_key": "order-lifecycle", "operation": "U" }
        ]
      }
    ],
    "entities": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "label": "Order"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "label": "InventoryReservation"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "label": "BillingBalance"
      }
    ],
    "functions": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "function_key": "order-lifecycle",
        "label": "order-lifecycle"
      }
    ],
    "operation_dispositions": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "handling": "not_applicable",
        "operation": "D",
        "reason": "SPEC-CRUD-001のOrder delete列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "handling": "not_applicable",
        "operation": "R",
        "reason": "SPEC-CRUD-001のInventoryReservation read列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "handling": "not_applicable",
        "operation": "C",
        "reason": "SPEC-CRUD-001のBillingBalance create列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "handling": "not_applicable",
        "operation": "D",
        "reason": "SPEC-CRUD-001のBillingBalance delete列はnot_applicable"
      }
    ]
  },
  "metadata": {
    "authority_refs": ["SPEC-CRUD-001"],
    "envelope_version": "1",
    "generator_contract_version": "crud-matrix-v1",
    "input_mode": "direct",
    "model_key": "crud-001",
    "model_type": "crud",
    "reference_refs": [],
    "runtime_contract_version": "runtime-v2",
    "runtime_unit_key": "model:crud-001",
    "scope_key": null,
    "selection_key": null,
    "selection_source": "user",
    "skill": "test-condition-design",
    "static_data_versions": {},
    "technique_slug": "crud",
    "upstream_entities": [],
    "upstream_runtime_units": []
  }
}
```

### Machine Runtime Result: test-condition-design::model:crud-001

```json
{
  "deterministic_generated": true,
  "envelope_version": "1",
  "fallback_reason": null,
  "generation_fingerprint": "sha256:1ad72426d79c9b41d704ddf20bf045e481a4867e8c2ef5e19421691e18f9ce71",
  "generator": "crud_matrix",
  "generator_contract_version": "crud-matrix-v1",
  "generator_implementation_fingerprint": "sha256:32b1ac1a0644e90cb2ea1490edf13830f957ab31999f547361fdfe063a8882e7",
  "input_fingerprint": "sha256:c5d7cec3426cc9016e7b58db0c70ff86b7709dc428c70822c91394d375611b97",
  "issues": [],
  "model_fingerprint": "sha256:381dae1bfcda7813956be93d691a9887c1a68e6853612513144598813820eac2",
  "model_key": "crud-001",
  "payload": {
    "cells": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "function_key": "order-lifecycle",
        "operations": ["R", "U"]
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "function_key": "order-lifecycle",
        "operations": ["C", "D", "U"]
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "function_key": "order-lifecycle",
        "operations": ["C", "R", "U"]
      }
    ],
    "consistency_sequences": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "entity_label": "Order",
        "kind": "lifecycle",
        "sequence_key": "order-place-amend-cancel",
        "steps": [
          {
            "function_key": "order-lifecycle",
            "function_label": "order-lifecycle",
            "operation": "C"
          },
          {
            "function_key": "order-lifecycle",
            "function_label": "order-lifecycle",
            "operation": "U"
          },
          {
            "function_key": "order-lifecycle",
            "function_label": "order-lifecycle",
            "operation": "U"
          }
        ]
      }
    ],
    "coverage_summary": {
      "complete": true,
      "completeness": {
        "complete": true,
        "covered": 12,
        "criterion": "crud-completeness",
        "required": 12
      },
      "consistency": {
        "complete": true,
        "covered": 1,
        "criterion": "crud-consistency",
        "required": 1
      }
    },
    "entities": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "label": "BillingBalance"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "label": "InventoryReservation"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "label": "Order"
      }
    ],
    "functions": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "function_key": "order-lifecycle",
        "label": "order-lifecycle"
      }
    ],
    "missing_operations": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "handling": "not_applicable",
          "operation": "C",
          "reason": "SPEC-CRUD-001のBillingBalance create列はnot_applicable"
        },
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": null,
        "materializable": false,
        "operation": "C",
        "target_key": "crud:missing:billing-balance:C"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "handling": "not_applicable",
          "operation": "D",
          "reason": "SPEC-CRUD-001のBillingBalance delete列はnot_applicable"
        },
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": null,
        "materializable": false,
        "operation": "D",
        "target_key": "crud:missing:billing-balance:D"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "inventory-reservation",
          "handling": "not_applicable",
          "operation": "R",
          "reason": "SPEC-CRUD-001のInventoryReservation read列はnot_applicable"
        },
        "entity_key": "inventory-reservation",
        "entity_label": "InventoryReservation",
        "execution": null,
        "materializable": false,
        "operation": "R",
        "target_key": "crud:missing:inventory-reservation:R"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "handling": "not_applicable",
          "operation": "D",
          "reason": "SPEC-CRUD-001のOrder delete列はnot_applicable"
        },
        "entity_key": "order",
        "entity_label": "Order",
        "execution": null,
        "materializable": false,
        "operation": "D",
        "target_key": "crud:missing:order:D"
      }
    ],
    "operation_dispositions": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "handling": "not_applicable",
        "operation": "C",
        "reason": "SPEC-CRUD-001のBillingBalance create列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "handling": "not_applicable",
        "operation": "D",
        "reason": "SPEC-CRUD-001のBillingBalance delete列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "handling": "not_applicable",
        "operation": "R",
        "reason": "SPEC-CRUD-001のInventoryReservation read列はnot_applicable"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "handling": "not_applicable",
        "operation": "D",
        "reason": "SPEC-CRUD-001のOrder delete列はnot_applicable"
      }
    ],
    "targets": [
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "entity_label": "BillingBalance",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "R"
        },
        "execution_fingerprint": "sha256:516d6af57699198d950ddb2d9ef5fc479fe5f6f957a6cc391feb61ab50f2e602",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "R",
        "target_content_fingerprint": "sha256:21ed18124934867a27d28e15e8cc7b4721806e648e93741eac2b76d1649c7bbb",
        "target_key": "crud:op:billing-balance:order-lifecycle:R",
        "target_ref": "sha256:998e15e7762299c6eabc423352cbc2e12355bbf7862b8bfb00d058dcdab54f95"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "entity_label": "BillingBalance",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "U"
        },
        "execution_fingerprint": "sha256:340d36e3a7ee7b776467d67dda5cdca666bbf34c6e22ce05fac052c0f846f37d",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "U",
        "target_content_fingerprint": "sha256:d88d2e6b52cdd42a815edb5c8973b17bc07969d1aafeb42c6143307d218dfaff",
        "target_key": "crud:op:billing-balance:order-lifecycle:U",
        "target_ref": "sha256:35dbba916959fdc0b1f4cbc2286e289b1701b4614bc10296b34333f4c8e62365"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "entity_label": "InventoryReservation",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "inventory-reservation",
          "entity_label": "InventoryReservation",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "C"
        },
        "execution_fingerprint": "sha256:9cbf0d28132317a337172e7c0145d03c7cb9b7e21746308b5b1aad0062807ab3",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "C",
        "target_content_fingerprint": "sha256:83a8b116185abe486996976f6805d41f105fa58b4a043d3ec3bb5ad888c28263",
        "target_key": "crud:op:inventory-reservation:order-lifecycle:C",
        "target_ref": "sha256:3fa9893924cc8e31ab9fc9a56412c6134377656b98f3cd4d6de2e0b318166850"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "entity_label": "InventoryReservation",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "inventory-reservation",
          "entity_label": "InventoryReservation",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "D"
        },
        "execution_fingerprint": "sha256:72ec11b1968f0270f3d1a6cd58d9227d20b0e8cfb1fa219aba23b5940daf67b5",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "D",
        "target_content_fingerprint": "sha256:766875420a9d3a5cca1717040589d402d53d131b2868086daed142f44ed35aef",
        "target_key": "crud:op:inventory-reservation:order-lifecycle:D",
        "target_ref": "sha256:fa5bdffce1cc8d388e9164669ac3efeb1dbac604db3efecf215db8fce6d203a5"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "inventory-reservation",
        "entity_label": "InventoryReservation",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "inventory-reservation",
          "entity_label": "InventoryReservation",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "U"
        },
        "execution_fingerprint": "sha256:4d52528a82de9d3127454ee6bccefa5553ec8565339cdbda1f97aba1e3e2e465",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "U",
        "target_content_fingerprint": "sha256:dd42c019eb121dd6c5be56d062ce6eaeb1bac8e6fe9eca33bfdfbfd2a640ce31",
        "target_key": "crud:op:inventory-reservation:order-lifecycle:U",
        "target_ref": "sha256:bb7a9addc200fcccd98a2aae95881da08b33dd793200e55c70f4176fb8fa5404"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "entity_label": "Order",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "entity_label": "Order",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "C"
        },
        "execution_fingerprint": "sha256:8f756f6a6a6bc6ccf6ab31825d0104338ac2f486c00c76c1c3b8ce4b87d25a25",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "C",
        "target_content_fingerprint": "sha256:14cac57e3cf8a59e3125acc6a73e29f98da2083bb463388af8449f6479410d09",
        "target_key": "crud:op:order:order-lifecycle:C",
        "target_ref": "sha256:01894275ef5ce10aaa9c3bb2ae923d21dcdbfbf9e8ef7eeb4f02038673898af6"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "entity_label": "Order",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "entity_label": "Order",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "R"
        },
        "execution_fingerprint": "sha256:8e8271dc6b42dc5fa7c24db70c3c1b542f4877e3e8cef9901bf199476a8fa29d",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "R",
        "target_content_fingerprint": "sha256:4f8021367f3ec16247c5820a23d37a4ff36f516a6d9aacdaaf14c3633322809b",
        "target_key": "crud:op:order:order-lifecycle:R",
        "target_ref": "sha256:473d3e6d4cd69ee6bd1ca83dba45494e217f590de53f6a1847da7b3802c5fe82"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "entity_label": "Order",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "entity_label": "Order",
          "function_key": "order-lifecycle",
          "function_label": "order-lifecycle",
          "operation": "U"
        },
        "execution_fingerprint": "sha256:6f12375c920f45f4a56012e6b27026896b6d81357220b3b85d37179dff6885c5",
        "function_key": "order-lifecycle",
        "function_label": "order-lifecycle",
        "materializable": true,
        "operation": "U",
        "target_content_fingerprint": "sha256:576c903aa46e880aaae3c114bb195bbd154f84c7de55395f5dab9f0f4038f4f1",
        "target_key": "crud:op:order:order-lifecycle:U",
        "target_ref": "sha256:0b010343ee50c70e0cbcbf500fb13f5d89e15cae746ac42651a1d149a21e41d8"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "handling": "not_applicable",
          "operation": "C",
          "reason": "SPEC-CRUD-001のBillingBalance create列はnot_applicable"
        },
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": null,
        "execution_fingerprint": null,
        "materializable": false,
        "operation": "C",
        "target_content_fingerprint": "sha256:02528a7673d65fc85ba43dd1d265c90dc1a2599d4a8449173ab77c5c4d1667f3",
        "target_key": "crud:missing:billing-balance:C",
        "target_ref": "sha256:a18d66902840a3499e991e53fa1b22ad6de73e55a2290a452dfa5a1e5d40fdba"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "billing-balance",
          "handling": "not_applicable",
          "operation": "D",
          "reason": "SPEC-CRUD-001のBillingBalance delete列はnot_applicable"
        },
        "entity_key": "billing-balance",
        "entity_label": "BillingBalance",
        "execution": null,
        "execution_fingerprint": null,
        "materializable": false,
        "operation": "D",
        "target_content_fingerprint": "sha256:7ea675664f5e985ed00eb45bd62e58c51a970b8c51f7f60a72d43f54660d63c8",
        "target_key": "crud:missing:billing-balance:D",
        "target_ref": "sha256:436bc7662c36e0b2e877d08752302973d6f2da99c2678fdf3ca350959b2c4f3e"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "inventory-reservation",
          "handling": "not_applicable",
          "operation": "R",
          "reason": "SPEC-CRUD-001のInventoryReservation read列はnot_applicable"
        },
        "entity_key": "inventory-reservation",
        "entity_label": "InventoryReservation",
        "execution": null,
        "execution_fingerprint": null,
        "materializable": false,
        "operation": "R",
        "target_content_fingerprint": "sha256:f5682ec358c128eeb3965ff74a862a6c7e52a3964056fff652c7fc29e1401130",
        "target_key": "crud:missing:inventory-reservation:R",
        "target_ref": "sha256:0e201d419d3d2c65355c23f3aa6c9ae697b1d64b739c90d3d2c42983a5390d0d"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "disposition": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "handling": "not_applicable",
          "operation": "D",
          "reason": "SPEC-CRUD-001のOrder delete列はnot_applicable"
        },
        "entity_key": "order",
        "entity_label": "Order",
        "execution": null,
        "execution_fingerprint": null,
        "materializable": false,
        "operation": "D",
        "target_content_fingerprint": "sha256:bb20ebbe154f9670afb8442ad7720e3905c16f0e26e2232466ae3cd860957704",
        "target_key": "crud:missing:order:D",
        "target_ref": "sha256:c672f4f7e1605ce852d44162f5ad10d0feab37482a6bd4704012bf81b4bf3f0a"
      },
      {
        "authority_refs": ["SPEC-CRUD-001"],
        "entity_key": "order",
        "execution": {
          "authority_refs": ["SPEC-CRUD-001"],
          "entity_key": "order",
          "entity_label": "Order",
          "kind": "lifecycle",
          "sequence_key": "order-place-amend-cancel",
          "steps": [
            {
              "function_key": "order-lifecycle",
              "function_label": "order-lifecycle",
              "operation": "C"
            },
            {
              "function_key": "order-lifecycle",
              "function_label": "order-lifecycle",
              "operation": "U"
            },
            {
              "function_key": "order-lifecycle",
              "function_label": "order-lifecycle",
              "operation": "U"
            }
          ]
        },
        "execution_fingerprint": "sha256:747019af495b3a18ff70fbde7dcdb3ebd57655baa2169796235e27cb4376c57b",
        "kind": "lifecycle",
        "materializable": true,
        "sequence_key": "order-place-amend-cancel",
        "target_content_fingerprint": "sha256:e11885ef0ecbd407c2405431e45e29cb880db0f610189fe7dca2e0e6ee3648b4",
        "target_key": "crud:seq:order-place-amend-cancel",
        "target_ref": "sha256:7ca3214896a4821f9145a27a009cf1ba80b575c2189ff8f6a9489d5e715c119a"
      }
    ]
  },
  "result_status": "ready",
  "runtime_contract_version": "runtime-v2",
  "runtime_implementation_fingerprint": "sha256:3ebf23f33c1641ba68362d1d06d7922f3ed64d360f04b15d792390092e3f0ce2",
  "runtime_required": true,
  "runtime_status": "ok",
  "runtime_unit_key": "model:crud-001",
  "skill": "test-condition-design",
  "static_data_versions": {},
  "support_status": "supported",
  "upstream_entity_fingerprints": [],
  "upstream_runtime_units": []
}
```
