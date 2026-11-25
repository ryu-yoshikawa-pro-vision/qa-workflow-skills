# context-signal-batch 契約

## 共通規則

- `schema_version`は`"1.0"`、canonical JSONはUTF-8、sort済みkey、compact separators、`ensure_ascii=false`、`allow_nan=false`、末尾改行なしです。重複keyと非有限値は拒否します。
- 成果物の唯一の参照はroot相対refです。`artifact_ref`は`context-signal-batch/<64桁lowercase SHA-256>.json`です。rootはハーネスから別に渡され、Skillは案件ID・保存先・Provider・認証方式を決めません。別rootの同じ相対refは別成果物として扱います。
- `batch_identity = SHA256(canonical({source_artifact_ref, source_content_hash, actual_inspected_range, observation_condition}))`です。意味を変える観測条件だけidentityに含みます。`requested_range`、workflow、分析観点、source revisionは含めません。
- `signal_identity = SHA256(canonical({source_artifact_ref, observation_locator, source_content_hash}))`です。`signal_content_hash`はidentity/hash欄を除くsignal bodyのcanonical SHA-256です。
- `actual_inspected_range`と`requested_range`は`{"kind":"all"}`または`{"kind":"sections|paths|...","items":[...]}`です。itemsは重複なし・昇順に正規化します。部分rangeのkindと要素はsource ownerの安定IDに合わせます。

## batch schema

必須top-level keys: `schema_version`, `artifact_ref`, `batch_identity`, `workflow_operation_id`, `source`, `scan_completeness`, `candidate_check`, `signals`。訂正時のみ`correction`を追加します。

`source`は`artifact_ref`, `source_revision`, `source_content_hash`, `requested_range`, `actual_inspected_range`, `observation_condition`を持ちます。`scan_completeness`は初回要求に対する`complete|partial`です。失敗、範囲不明、抽出失敗はbatchとして保存しません。

`candidate_check`は`status=checked_with_triggers|checked_no_conflict|not_checked`と、sort済みunique `triggered_candidate_identities`を持ちます。`signals`は観察順を維持し、signal identityの重複は禁止です。0件completeは有効な記録です。

signalは`signal_identity`, `signal_content_hash`, `observation_locator`, `evidence_type`, `fact_summary`, `independence_group`, `cross_cutting_attributes`, `environment_and_versions`を持ちます。`evidence_type`は`spec|decision|approved_asm|unapproved_user_response|impl_observation|exploratory_finding`です。未承認回答では`unapproved_response_meta`（responder role、Q ref/revision、scope、`approval_status=unapproved`）を保持し、回答全文を含めません。

訂正batchでは`correction`に`original_batch_identity`、`corrected_batch_targets[]`、`reason`、sort済みunique `source_evidence_refs[]`を記録します。各訂正対象は`batch_identity`, `artifact_ref`, 保存`revision`, `content_hash`, `source_artifact_ref`, `source_content_hash`, `actual_inspected_range`, `observation_condition`を持ちます。対象のrevision/hashは信頼済み保存境界が履歴から独立readbackします。対象間のsource/range/conditionが一つでも異なる、元通常batchが含まれない、親batchのreadbackが得られない、一次情報で誤りを確かめられない場合は訂正しません。

`corrected_batch_identity = SHA256(canonical({original_batch_identity, corrected_batch_targets, corrected_signals_hash}))`です。`corrected_batch_targets`は`artifact_ref`順のunique集合、`corrected_signals_hash`は訂正版signals配列のcanonical hashです。旧batchはimmutableです。通常抽出batch identityは変更しません。

helperは`identity`, `validate`, `project`, `select_batch_signals`, `batch_covers`, `batch_union_covers`を提供します。projectionは件数・短い事実抜粋・属性keyを返し、個別signal本文はidentityを指定して選択読取します。複数batchの和集合では訂正対象readbackを照合したactive batchだけを含め、親batchと訂正版を二重計上しません。競合訂正版や訂正元の未取得は完了根拠にしません。

## 完了証拠

初回保存本文の`scan_completeness`だけでは今回の要求完了を表しません。owner/hostは現在のsource ref/hash、今回requested range、観測条件、保存batchの実range、正常抽出、独立readbackを照合します。partial batchも今回の狭い要求を包含すれば再利用できます。複数batchの和集合はsource/hash/condition一致を確認したhost gateが照合します。root bindingとreadbackはcanonical batch本文の外で受け渡し、Skillやartifactに案件IDを記録しません。単体scopeの`execution_range`は要求rangeのcanonical JSON文字列です。
