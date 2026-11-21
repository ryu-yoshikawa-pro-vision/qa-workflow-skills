# 仕様分析の保存契約（spec-analysis）

本書は、`assets/output-template.md` に従って作成した仕様分析文書を保存する場合の契約です。保存の実装は `scripts/spec_document.py`（検証と保存の関数）と、project-context の `scripts/artifact_host.py save-document`（ホストCLI）にあります。

## 1. 保存単位と正本

- 保存先は案件・kindごとのbranch `qa-artifacts/<project>/spec-analysis` です。1つのbranchに別kindや別案件を混ぜません（Git branchのrevisionがcommit SHAのため）。
- artifact は対象範囲（scope）ごとに1つで、`spec-analysis/<scope-id>.md` です。`scope-id` は `^[a-z0-9][a-z0-9-]{0,63}$` に一致する必要があります。
- 正本は Markdown 本文そのものです。構造化JSONの第二の正本は作りません。閲覧用の投影（`export`）は本文のバイト一致の写しです。
- 本文は `assets/output-template.md` の11見出しを、この順で完全一致させます（`/` を含む見出し名は、テンプレートの見出しをそのまま使います）。

## 2. 検証（validate）

`scripts/spec_document.py validate` は読取専用です。store に触れず、書込みも確認記録の登録もしません。

| 検査 | 理由コード（`spec_document_invalid:` を前置） |
| --- | --- |
| UTF-8、NUL を含まない、16MB 以下 | `encoding_invalid` / `too_large` |
| 11見出しの存在・重複・順序（テンプレートにない見出しは `section_unexpected`） | `section_missing:<見出し>` / `section_duplicate:<見出し>` / `section_order_invalid` / `section_unexpected:<見出し>` |
| `- 対象機能:`（空でないこと）と `- 対象外:`（行の存在） | `scope_field_missing:対象機能` / `scope_field_missing:対象外` |
| `scope-id` の形式 | `scope_id_invalid` |
| 表の有無、ヘッダ（テンプレートと完全一致）、行の列数 | `table_missing:<見出し>` / `table_unexpected:<見出し>` / `table_header_mismatch:<見出し>` / `table_row_width:<見出し>` |
| 情報源の参照ID `SRC-\d{3}` の形式と一意性 | `src_id_invalid:<id>` / `src_id_duplicate:<id>` |
| 情報源の鮮度列に `rev:<値>` があること | `src_revision_missing:<id>` |
| 情報源の参照 / 備考列が空でないこと | `src_note_missing:<id>` |
| 参照列が `file:` で始まる場合の記法（§4） | `src_locator_invalid:<id>` |
| 分析項目の項目ID（`(SPEC\|DEC\|INF\|UNK)-\d{3}`）と一意性 | `item_id_invalid:<id>` / `item_id_duplicate:<id>` |
| 分類が `SPEC` / `DECISION` / `INFERENCE` / `UNKNOWN` のいずれか、かつ接頭辞と一致 | `classification_invalid:<id>` / `classification_id_mismatch:<id>` |
| SPEC / DECISION / INFERENCE は情報源の参照が1件以上あり、情報源表に存在すること | `source_ref_missing:<id>` / `source_ref_unknown:<id>:<SRC-ID>` |
| UNKNOWN は備考が空でないこと | `unknown_reason_missing:<id>` |
| 現在有効か列が空でないこと | `currentness_missing:<id>` |
| 仕様根拠ID `AUTH-\d{3}` の形式と一意性、種別（SPEC / DECISION / 承認済みASM）、関連仕様根拠IDの参照先 | `authority_id_invalid:<id>` / `authority_id_duplicate:<id>` / `authority_type_invalid:<id>` / `authority_relation_unknown:<id>:<AUTH-ID>` |
| 業務ルール・状態/遷移・処理・制約の関連項目IDが分析項目に存在すること | `item_ref_unknown:<見出し>:<項目ID>` |
| テスト側のID（`TR-` `TC-` `TCN-` `CI-` `COND-` `ITEM-` と英数字）を含まない | `forbidden_downstream_id:<ID>` |
| `source_revision` の値が本文に現れること | `source_revision_not_in_document` |

- 検査は全件を集めて返します（先頭の1件で止めません）。
- 検証は形式だけを見ます。「SPECが権威ある根拠に支えられているか」「UNKNOWNが本当に根拠不足か」「DEC-xxxが正本一覧の既存IDか」は意味の判定であり、本Skillの自己検証が担います。
- Machine Entity ブロックは見出しの存在だけを検査し、内容は検査しません。

## 3. 保存（persist_document）

1. `validate` を実行し、不合格なら store に触れずに `blocked` を返します。
2. 確認記録（`write_confirmation_record`）を作り、ホストが store に登録します。確認記録は store の user-confirmed 認可と同じ12キーです。
3. `store.write(kind="spec-analysis", ...)` を呼びます。CAS、冪等性、独立readbackは store の挙動に従います。
4. 成功時は `analysis_status: valid` と `document_sha256` を付けて返します。

- 前回版との比較は行いません（分析は全体再生成です。版の履歴は Git commit が持ちます）。
- 更新時の `expected_revision` は、直前に `read` で取り直した `git:<sha>` です。古い値は `revision_conflict` で止まります（データは失われません）。

### 保存の理由コード（store のコードをそのまま返す）

`access_denied`、`revision_conflict`、`create_if_absent_conflict`、`independent_readback_mismatch`、`git_artifact_ref_invalid`、`artifact_project_mismatch`、`branch_checked_out`、`approval_provider_unavailable`、`git_provider_command_failed`、`git_provider_unavailable`、`artifact_content_too_large`、`unchanged_artifact_write`（同一内容の再保存は失敗として返り、「現在版と同一」と読めます）。本モジュールの `spec_scope_mismatch`（artifact_ref が `spec-analysis/<scope-id>.md` と一致しない）。

## 4. 証跡の記法

- 情報源の「鮮度 / バージョン」列: `rev:<revision>`（commit SHA、版番号、改版日のいずれか）。
- 情報源の「参照 / 備考」列:
  - 案件のrepo由来: `file:<相対path>:<line>` または `file:<相対path>:<start>-<end>`。絶対path、`..`、`\` は拒否されます。
  - 文書由来: 文書IDと節名（自由記法。非空のみ検査）。
- 分析項目の「情報源 / 正本参照」列: `SRC-001, SRC-002` のようにカンマ区切り。

## 5. 承認

- 保存は user-confirmed です。`--user-confirmed-ref` は、利用者がその文書を確認した後にだけ渡します。AIが確認前に値を作ってはなりません。
- 確認記録は呼出し元の自己申告であり、認証ではありません。
- 読取は、登録済みの案件範囲で確認記録なしに通ります（既存の挙動）。

## 6. 既知の制約

- **readback 不一致時の head（全kind共通）**: store は参照を `update-ref` で進めた後に独立readbackします。readback が一致しない場合、呼出し側には失敗（`independent_readback_mismatch`）が返りますが、head は戻りません。未検証の commit が head に残るため、`read` や `export` が未検証の内容を返しえます。呼出し側は、この失敗を成功として扱わず、head を読み直して確認してください。上流での対応（readback を参照更新の前に行う、CAS で戻す）は未決定です。
- **同一 operation_id の再利用**: 現在の head を基準にした、同じ `operation_id` で内容の違う書込みは、Git store では新しい版として保存されます（trailer の `QA-Operation-Id` が複数残ります）。`operation_id` の一意性は呼出し側の責務です。既定の `operation_id` は `spec-` と文書・expected_revision のsha256の先頭32文字です。
- **CAS の単位**: 更新の CAS は branch の HEAD 単位です。scope を並列に保存すると、古い revision のままの保存は `revision_conflict` で止まります。並列運用が必要な場合は、scopeごとのbranchを検討します（上流の判断）。
- **意味の検証は対象外**（§2）。
- **Git 参照の並行変更**: 検査と参照更新の間に別のworktreeでbranchがcheckoutされる競合は防げません（project-context の data-contract と同じ）。
