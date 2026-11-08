# feature-inventory-v1

scripts/feature_registry.pyはPython 3.11のstdinにJSON objectを受け、stdoutへJSON1件を返します。重複keyと16MiB超の入力を拒否します。

入力トップレベルはsnapshot、previous_snapshot（初回null）、observed_head_revision。snapshotはschema_version=feature-inventory-v1、project_ref、artifact_ref、artifact_revision、source_revision、previous_artifact_revision、operation_id、eventを必須とします。eventはinitial / pr_update / merge / release / external_revisionです。

| 項目 | 内容 |
| --- | --- |
| expected_source_ids | 当該分析で列挙すべきSRC ID配列 |
| sources | id, kind, ref, scope, status, revision, evidence_ref, enumeration_complete, unretrieved[], reason |
| features | id, identity, name, kind, status, parent_id, source_ids[], implementation_refs[], spec_refs[], qa_refs[] |
| candidates | id, source_ids[], evidence_ref, status, feature_id, reason, approval_ref |
| changes | id, source_id, before_revision, after_revision, locator, evidence_ref, classification, feature_ids[], reason, approval_ref |
| history | event_id, kind, revision, evidence_ref, from_ids[], to_ids[]を追記専用 |
| unknown_areas | 取得不能・発見不能な分析範囲の参照配列 |

IDはSRC-001、FEAT-001、CAND-001、DIF-001形式。featureのidentityは同一案件で同じ意味を表す安定値で、path・名称変更による再採番を防ぎます。sourceのcompleteはrevisionとevidence_ref、enumeration_complete=true、unretrieved=[]を必須とします。候補・差分の対象外には理由とapproval_refが必須ですが、承認主体の真正性は本helperでは確認しません。

結果はcomplete / incomplete / stale / idempotent / blocked。change_classificationは分類済み差分ID ÷ 全確認差分ID、observed_candidate_mappingはID対応済み・承認参照付き対象外候補 ÷ 全確認候補。分母0はrate=nullです。各率は分子・分母のIDを保存し、未取得sourceと未知領域を別に示します。all_product_features_discoveredは常にnullです。

handoffにはartifact ref/revision、source revision、feature IDs、未分類差分IDs、expected_source_idsを返します。helperのcompleteは保存済み・承認済み・全製品発見の証明ではなく、実保存先のnative CAS・history/readbackと独立照合が必要です。仕様対応率・正式設計率・QA影響評価は別のownerが決定します。
