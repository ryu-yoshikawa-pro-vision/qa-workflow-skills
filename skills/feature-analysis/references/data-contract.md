# feature-inventory-v1

scripts/feature_registry.pyはPython 3.11のstdinにJSON objectを受け、stdoutへJSON1件を返します。重複keyと16MiB超の入力を拒否します。

入力トップレベルはsnapshot、previous_snapshot（初回null）、observed_head_revision。snapshotはschema_version=feature-inventory-v1、project_ref、artifact_ref、artifact_revision、source_revision、previous_artifact_revision、operation_id、eventを必須とします。eventはinitial / pr_update / merge / release / external_revisionです。

- **expected_source_ids**：内容 = 当該分析で列挙すべきSRC ID配列
- **sources**：内容 = id, kind, ref, scope, status, revision, evidence_ref, enumeration_complete, unretrieved[], reason
- **features**：内容 = id, identity, name, kind, status, parent_id, source_ids[], implementation_refs[], spec_refs[], qa_refs[]
- **candidates**：内容 = id, source_ids[], evidence_ref, status, feature_id, reason, approval_ref
- **changes**：内容 = id, source_id, before_revision, after_revision, locator, evidence_ref, classification, feature_ids[], reason, approval_ref
- **history**：内容 = event_id, kind, revision, evidence_ref, from_ids[], to_ids[]を追記専用
- **unknown_areas**：内容 = 取得不能・発見不能な分析範囲の参照配列

IDはSRC-001、FEAT-001、CAND-001、DIF-001形式。featureのidentityは同一案件で同じ意味を表す安定値で、path・名称変更による再採番を防ぎます。sourceのcompleteはrevisionとevidence_ref、enumeration_complete=true、unretrieved=[]を必須とします。候補・差分の対象外には理由とapproval_refが必須ですが、承認主体の真正性は本helperでは確認しません。

結果はcomplete / incomplete / stale / idempotent / blocked。change_classificationは分類済み差分ID ÷ 全確認差分ID、observed_candidate_mappingは機能ID対応済み候補のみ ÷ 全確認候補。承認参照付きの対象外候補は`excluded_candidate_ids`に記録し、対応済みの分子には含めません。分母0はrate=nullです。各率は分子・分母のIDを保存し、未取得sourceと未知領域を別に示します。all_product_features_discoveredは常にnullです。 unknown_areasが残る場合はsource_boundary_complete=falseとし、取得母集団が完全であると報告しません。

handoffにはartifact ref/revision、source revision、feature IDs、未分類差分IDs、expected_source_idsを返します。helperのcompleteは保存済み・承認済み・全製品発見の証明ではなく、実保存先のnative CAS・history/readbackと独立照合が必要です。仕様対応率・正式設計率・QA影響評価は別のownerが決定します。

## ローカルGit列挙契約

`scripts/git_source_inventory.py` はPython 3.11／Git CLIで `repository_root`、`authorized_root`、`base_sha`（初回null）、`head_sha` のJSONを受けます。2つのrootは正規化後に同一である必要があり、SHAはfull 40／64 hex commit IDです。read-onlyで `git ls-tree -r -z` によりHEAD全ファイル、baseがあれば `git diff --name-status -z --find-renames` で変更pathとrename元/先を列挙します。

出力 `git-source-snapshot-v1` 相当の `files[]`（path、mode、kind、object_sha）、`changes[]`（status、before_path、after_path）、base/head SHA、complete_file_listing、complete_change_listing、unretrieved、feature_count=nullを、実際に取得できた範囲だけ返します。Gitの列挙結果は意味上の機能ID・全資料の発見を証明しません。Git以外のsourceと併せた正規化・対応付けはfeature_registry.pyの入力側で実施します。

追加の機械検証：更新operationでは同一artifact_revisionの再利用を拒否します。分割は複数の派生ID、統合は複数の元IDが必要です。`handoff.snapshot_sha256`は候補snapshotのcanonical JSONのSHA-256、`handoff.source_inventory[]`はsource別のref・状態・revision・未取得の照合情報です。保存済みartifactの内容hash・認証済み承認の証明ではありません。

## Git差分母集団との照合

`scripts/reconcile_git_coverage.py`は`git_inventory`（同じ案件のgit_source_inventory.pyの結果）、`registry_request`（feature_registry.pyへの検証入力）、`source_id`（code種別、expected_source_idsに所属）のJSONを受け取ります。先にregistryのschema・ID・履歴を検証し、Git側のHEAD full SHAとsource revisionが一致し、変更一覧が完全な場合のみ、全Git変更ファイルの`after_path`と当該sourceの`changes[].locator`を照合します。renameは新pathに対応付け、旧pathはGit列挙結果の`before_path`に残します。未登録path、Gitにない差分ID、未分類path、source不完全・旧HEADを判別します。

結果は`coverage.git_change_paths`、`registered_paths`、`missing_git_paths`、`unmatched_registry_change_ids`、`unclassified_git_paths`、`rate`、候補snapshot SHA-256を含みます。ファイルpathの網羅は機能・hunk・Issue・仕様の網羅ではありません。Git一覧そのものの真正性と実providerへの保存・承認は別途確認します。
