# context-rule-candidate / context-synthesis-run 契約

両成果物はUTF-8 canonical JSON（sort済みkeys、compact separators、`ensure_ascii=false`、`allow_nan=false`、末尾改行なし）、`schema_version="1.0"`、top-level `artifact_ref`です。refは指定root相対の`<kind>/<lowercase SHA-256 identity>.json`です。root bindingはハーネスの実行条件と保存証拠で別に扱い、成果物本文・identityに案件IDを含めません。同じ相対refでも異なるroot間で証拠を混ぜません。

## context-rule-candidate

`candidate_identity = SHA256(canonical(identity_key))`です。identity keyは`domain`, `operation_axis`, `rule_kind`, `target_scope_kind`, `governing_conditions`, `assertion_polarity`, `normalized_assertion`です。検索tagはidentityから分離します。

必須fields: `schema_version`, `artifact_ref`, `candidate_identity`, `identity_key`, `rule_statement`, `applicability`, `related_candidate_refs`, `evidence_links`, `unobserved_ranges`, `currentness_dependencies`, `evaluation_status`, `resolution_state`, `resolution_links`, `implementation_conformance_refs`, `question_refs`, `handoff_records`, `rejection_or_deferral_detail`, `investigation_history`。optional fieldは`search_tags`だけです。

- related relation: `competing_hypothesis|alternative|replaced_by|merged_into|split_into`。自己参照不可。比較relationの相互参照は可能です。後継3種のみ循環禁止です。
- evidence link: `signal_ref`または`direct_source_ref`。候補ごとに`supports|counterexample|indeterminate|out_of_scope`で評価し、counterexampleには6分類（`unclassified`を含む）を付けます。未観察は`unobserved_ranges`です。
- currentness: `target_ref`, `dependency_content_hash`, `effective_authority_fingerprint`, `source_revision`, `dependency_freshness=current|changed|unverifiable|deleted`。
- evaluation status: `scan_completeness=complete|partial|failed`, `revalidation_required`, `revalidation_reasons`, `last_synthesis_run_ref`。
- resolution: 7状態`uninvestigated|investigating|resolved|rejected|deferred|superseded|blocked`。`resolution_links`はowner/type/ref/revision/content hash/coverageです。implementation conformanceは`conforms|confirmed_mismatch|unverified`とverified証拠refを区別します。
- question refsは既存UNKNOWNまたはnullの任意確認です。handoff statusは`pending|confirmed_by_readback|returned|blocked_unverifiable`で、確認target ref/revision/hashはreadback済みの場合のみ持ちます。`returned`だけを反映成立とみなしません。`rejected`はauthority basis、`deferred`は判断詳細、`superseded`は後継relationを必須にします。

## context-synthesis-run

`workflow_operation_id = SHA256(canonical({workflow_ref, operation_input, requested_scope}))`、`run_identity = workflow_operation_id`です。`operation_input`は`operation_type`, `input_sources[]`（artifact ref/source revision/content hash/effective Authority fingerprintの対応）, `investigation_conditions`を持ちます。source revisionは開始時readbackのprovenanceとして保持しますが、identityにはartifact ref/content hash/effective Authority fingerprintを使用するため、同じ内容・Authorityのrevision番号だけが変わってもoperation identityは変わりません。要求scope・観点・environment/versionはrunの`requested_scope`に一度だけ保存し、helperは開始時の値からidentityを再計算します。rootやproject identityは含めません。開始後にidentity算出元を変更しません。

必須fields: `schema_version`, `artifact_ref`, `run_identity`, `workflow_ref`, `workflow_operation_id`, `operation_input`, `requested_scope`, `inspected_scope`, `scan_completeness`, `snapshot`, `triage_plan`, `result_summary`。

- snapshotは`snapshot_hash`（self除外）、検索root/scope、条件、直接参照source ref/revision/content hash/authority fingerprint、取得不能一覧、除外範囲を保持します。開始時`operation_input.input_sources[]`は同じref/revision/hash/authorityをsnapshotにも持ち、開始時inputとreadbackで一対一に照合します。実行中に追加した根拠は開始時inputと分けてsnapshotへ追加し、snapshot hashだけを再計算します。target batch refは開始時input sourceとsnapshotの同一revision/hashに存在しなければなりません。
- `triage_plan.target_batch_refs`と`planned_candidate_ops`は候補全件を持ちます。各opはcandidate identity/ref、action、base hash/revision、related preconditions、operation id、planned content hash/payload、write metadata、confirmed resultを保持します。各候補payload自体もcandidate schemaでvalidateします。reuseのpayloadはnullでplanned hash=既存本文hashです。
- `result_summary.status`は`in_progress|completed|completed_zero_changes|blocked_incomplete`です。zero reasonは`no_related_candidates|existing_candidates_sufficient|all_evidence_known|empty_search`です。partial/failed scan、予定未確認、必須handoff未解決は完了できません。
- zero-change runも今回の要求・検索・readbackを証明するrunです。過去workflowのrunは今回の完了証拠になりません。

## 独立readback

helperは`project`でref/revision/hash・scope・状態・短い抜粋だけのprojectionを返し、`select_run_operations`で指定candidate identityのplanned payloadだけを返します。全runの候補payloadを常時AIへ渡しません。候補identity、本文hash、base revision/hash、関連候補のpreconditionが変われば同じ書込operation idを再使用しません。

readbackは`[{artifact_ref, revision, sha256, content, kind?, root_binding?}, ...]`です。同じrefの異なるrevisionを同時に渡せます。helperは`(artifact_ref, revision)`の組で索引し、更新前baseと更新後resultを別々に照合します。run本体のreadback revisionは`run_readback_revision`として明示し、run自身の本文に含む自己申告値で代用しません。snapshot source、target batch、候補、候補のsignal/direct evidence、resolution link、currentness dependency、質問、verified implementation evidence、confirmed handoffもそれぞれref/revision/hashを同じ実行の証拠として確認します。context artifactはroot bindingとkindを確認し、異なるrootの同じ相対refを同一成果物として扱いません。完了記録は当時の保存revisionで確認し、現在採用する候補は最新read_currentと現行Authorityでもう一度評価します。保存された自己申告だけでcompleteにしません。

`context_request`はowner scopeの`normalized_input`に含めます。Bでは`workflow_ref`、開始時`operation_input`、開始時`requested_scope`、`target_batch_refs`を正確にrun本文と一致させます。分割runではqa-workflow stateのrequest recordに開始時要求と各runの実scope対応を保持し、全要求source×scopeがrun集合で覆われるまでmappingをincompleteとします。

指定rootへの保存・列挙・読取・履歴・conditional updateは共通の`scripts/context_artifact_store.py`で行います。通常保存はOS権限と標準filesystem操作で成立し、専用認証hostは不要です。共有rootや外部owner操作の安全条件は各owner境界で別途満たします。
