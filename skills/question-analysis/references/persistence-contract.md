# 不明点・矛盾分析の保存契約（question-analysis）

本書は、`assets/output-template.md` に従って作成した不明点・矛盾分析文書を保存する場合の契約です。保存の実装は `scripts/question_document.py`（検証と保存の関数）と、project-context の `scripts/artifact_host.py save-document --kind question-analysis`（ホストCLI）にあります。

## 1. 保存単位と正本

- 保存先は案件・kindごとのbranch `qa-artifacts/<project>/question-analysis` です。1つのbranchに別kindや別案件を混ぜません（Git branchのrevisionがcommit SHAのため）。
- artifact は対象範囲（scope。領域など）ごとに1つで、`question-analysis/<scope-id>.md` です。`scope-id` は `^[a-z0-9][a-z0-9-]{0,63}$` に一致する必要があります。
- 正本は Markdown 本文そのものです。構造化JSONの第二の正本は作りません。閲覧用の投影（`export`）は本文のバイト一致の写しです。
- 本文は `assets/output-template.md` の必須見出し（`概要`・`不明点 / 質問一覧`・`質問ID履歴`・`仮定候補`・`ブロック中範囲`）をそれぞれ1回含みます。テンプレートにない見出し（作業メモなど）は許容し、見出しの順序は検査しません。

## 2. 検証（validate）

`scripts/question_document.py validate` は読取専用です。store に触れず、書込みも確認記録の登録もしません。

| 検査 | 理由コード（`question_document_invalid:` を前置） |
| --- | --- |
| UTF-8、NUL を含まない、16MB 以下 | `encoding_invalid` / `too_large` |
| 必須見出しの存在と重複 | `section_missing:<見出し>` / `section_duplicate:<見出し>` |
| `scope-id` の形式 | `scope_id_invalid` |
| 表の有無、ヘッダ（テンプレートと完全一致）、行の列数（不明点 / 質問一覧は15列、質問ID履歴、仮定候補、ブロック中範囲） | `table_missing:<見出し>` / `table_unexpected:<見出し>` / `table_header_mismatch:<見出し>` / `table_row_width:<見出し>` |
| 質問ID `Q-\d{3}` の形式と一意性 | `question_id_invalid:<id>` / `question_id_duplicate:<id>` |
| 問題 / 質問が空でないこと | `question_text_missing:<id>` |
| 分類が `ブロッカー` / `要確認` / `仮定可能` / `提案・任意` のいずれか | `classification_invalid:<id>` |
| 根拠・影響範囲 / 成果物・回答なしの場合の扱いが空でないこと | `basis_missing:<id>` / `impact_missing:<id>` / `unanswered_handling_missing:<id>` |
| 関連UNKNOWN ID が `UNK-\d{3}` の形式（`<br>` 区切り）で、同一行に重複しないこと | `unknown_ref_invalid:<id>:<token>` / `unknown_ref_duplicate:<id>:<token>` |
| 質問ID履歴の形式（`Q-\d{3}`）と昇順・一意 | `history_id_invalid:<id>` / `history_order_invalid` |
| 不明点 / 質問一覧の各質問が質問ID履歴に含まれること | `history_missing_question:<id>` |
| テスト側のID（`TR-` `TC-` `TCN-` `CI-` `COND-` `ITEM-` と英数字）を含まない | `forbidden_downstream_id:<ID>` |
| `source_revision` の値が本文に現れること | `source_revision_not_in_document` |

- 検査は全件を集めて返します（先頭の1件で止めません）。
- 検証は形式だけを見ます。分類の妥当性、質問の必要性、関連UNKNOWNが実在の UNK かどうか（別の成果物にある UNK は本文だけでは確認できません）、ブロック中範囲と分類の整合は意味の判定であり、本Skillの自己検証と `question_ids.py` の既存検証が担います。
- 関連UNKNOWN ID と質問ID の対応表（`question_ids.py validate-links`）は、保存前に current UNK 集合を渡して別途確認できます。

## 3. 保存（persist_document）

1. `validate` を実行し、不合格なら store に触れずに `blocked` を返します。
2. 確認記録（`write_confirmation_record`）を作り、ホストが store に登録します。確認記録は store の user-confirmed 認可と同じ12キーです。
3. `store.write(kind="question-analysis", ...)` を呼びます。CAS、冪等性、独立readbackは store の挙動に従います。
4. 成功時は `analysis_status: valid` と `document_sha256` を付けて返します。

- 前回版との比較は行いません（分析は全体再生成です。版の履歴は Git commit が持ちます）。
- 更新時の `expected_revision` は、直前に `read` で取り直した `git:<sha>` です。古い値は `revision_conflict` で止まります（データは失われません）。

### 保存の理由コード（store のコードをそのまま返す）

`access_denied`、`revision_conflict`、`create_if_absent_conflict`、`independent_readback_mismatch`、`git_artifact_ref_invalid`、`artifact_project_mismatch`、`branch_checked_out`、`approval_provider_unavailable`、`git_provider_command_failed`、`git_provider_unavailable`、`artifact_content_too_large`、`unchanged_artifact_write`（同一内容の再保存は失敗として返り、「現在版と同一」と読めます）。本モジュールの `question_scope_mismatch`（artifact_ref が `question-analysis/<scope-id>.md` と一致しない）。

## 4. 承認

- 保存は user-confirmed です。`--user-confirmed-ref` は、利用者がその文書を確認した後にだけ渡します。AIが確認前に値を作ってはなりません。
- 確認記録は呼出し元の自己申告であり、認証ではありません。
- 読取は、登録済みの案件範囲で確認記録なしに通ります（既存の挙動）。

## 5. 既知の制約

- **readback 不一致時の head（全kind共通）**: store は参照を `update-ref` で進めた後に独立readbackします。readback が一致しない場合、呼出し側には失敗（`independent_readback_mismatch`）が返りますが、head は戻りません。未検証の commit が head に残るため、`read` や `export` が未検証の内容を返しえます。呼出し側は、この失敗を成功として扱わず、head を読み直して確認してください。
- **同一 operation_id の再利用**: 現在の head を基準にした、同じ `operation_id` で内容の違う書込みは、Git store では新しい版として保存されます。`operation_id` の一意性は呼出し側の責務です。既定の `operation_id` は `question-` と文書・expected_revision のsha256の先頭32文字です。
- **CAS の単位**: 更新の CAS は branch の HEAD 単位です。scope を並列に保存すると、古い revision のままの保存は `revision_conflict` で止まります。
- **分類の表記**: 検証は分類を4値に限定します。`仮定可能（提案）` のような修飾付きの表記は `classification_invalid` になります。表記を許すかは上流の判断です。
- **見出しの順序と追加の見出し**: テンプレートの順序は検査せず、追加の見出しも許容します（spec-analysis は順序と追加見出しを検査します）。
- **意味の検証は対象外**（§2）。
