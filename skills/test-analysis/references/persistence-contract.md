# テスト分析の保存契約（test-analysis）

本書は、`assets/output-template.md` に従って作成したテスト分析文書を保存する場合の契約です。保存の実装は `scripts/test_analysis_document.py`（検証と保存の関数）と、project-context の `scripts/artifact_host.py save-document --kind test-analysis`（ホストCLI）にあります。

## 1. 保存単位と正本

- 保存先は案件・kindごとのbranch `qa-artifacts/<project>/test-analysis` です。1つのbranchに別kindや別案件を混ぜません（Git branchのrevisionがcommit SHAのため）。
- artifact は対象範囲（scope）ごとに1つで、`test-analysis/<scope-id>.md` です。`scope-id` は `^[a-z0-9][a-z0-9-]{0,63}$` に一致する必要があります。
- 正本は Markdown 本文そのものです。構造化JSONの第二の正本は作りません。閲覧用の投影（`export`）は本文のバイト一致の写しです。
- 本文は `assets/output-template.md` の必須見出し（`テスト分析範囲`・`変更 / 影響マップ`・`プロダクトリスク一覧`・`テスト重点`・`選択したテスト技法`・`テスト可能性 / テストレベル判断`・`残存リスク`・`Machine Runtime / Entity（機械証拠）`）をそれぞれ1回含みます。テンプレートにない見出し（作業メモなど）は許容し、見出しの順序は検査しません。
- 文書は手組みです。テンプレートの表と箇条書きを本文に書きます。runtimeが生成するのは `Machine Runtime / Entity（機械証拠）` 節の固定ブロックだけで、そのブロックは `runtime_contract.py` の `render_*` の出力をそのまま置きます。

## 2. 検証（validate）

`scripts/test_analysis_document.py validate` は読取専用です。store に触れず、書込みも確認記録の登録もしません。

| 検査 | 理由コード（`test_analysis_document_invalid:` を前置） |
| --- | --- |
| UTF-8、NUL を含まない、16MB 以下 | `encoding_invalid` / `too_large` |
| 必須見出しの存在と重複 | `section_missing:<見出し>` / `section_duplicate:<見出し>` |
| `scope-id` の形式 | `scope_id_invalid` |
| `source_revision` の値が本文に現れること | `source_revision_not_in_document` |
| テスト分析範囲の項目（対象機能 / 変更、テストレベル、対象外、ブロッカーは非空。案件固有のテスト目的 / 重点、環境制約、対象 / 実行範囲は存在） | `scope_field_missing:<項目>` / `scope_field_empty:<項目>` |
| 表の有無、ヘッダ（テンプレートと完全一致）、行の列数、プロダクトリスク一覧・テスト重点・テスト可能性の表は1行以上 | `table_missing:<見出し>` / `table_unexpected:<見出し>` / `table_header_mismatch:<見出し>` / `table_row_width:<見出し>` / `table_empty:<見出し>` |
| リスクID `RISK-\d{3}` の形式と一意性 | `risk_id_invalid:<id>` / `risk_id_duplicate:<id>` |
| 影響度・発生可能性が 1〜4、レベルが 高・中・低 のいずれか、レベルが標準マトリクスと一致 | `risk_impact_invalid:<id>` / `risk_likelihood_invalid:<id>` / `risk_level_invalid:<id>` / `risk_level_mismatch:<id>` |
| 製品上のリスク、根拠・関連仕様根拠、根拠の理由が空でないこと | `risk_text_missing:<id>` / `risk_basis_missing:<id>` / `risk_reason_missing:<id>` |
| 根拠欄に UNKNOWN（`UNK-\d{3}`・語 UNKNOWN）と INFERENCE（`INF-\d{3}`・語 INFERENCE）を含まないこと（リスク、重点、技法の根拠すべて） | `non_basis_reference:<行>:<token>` |
| 変更種別が 新規・変更・削除・回帰影響・参考 のいずれか | `change_kind_invalid:<行>` |
| 優先度が 高・中・低 のいずれか、重点の根拠が空でないこと | `priority_invalid:<行>` / `emphasis_basis_missing:<行>` |
| 技法名・技法の根拠が空でないこと | `technique_missing:<行>` / `technique_basis_missing:<行>` |
| 操作可能か・観測可能か・合否判定可能かが 可・不可・一部 のいずれか、選択テストレベルが空でないこと | `feasibility_invalid:<項目>:<行>` / `test_level_missing:<行>` |
| 重点・技法・残存リスクに現れる RISK ID が、リスク一覧に存在すること | `risk_ref_missing:<id>` |
| すべてのリスクが、テスト重点・選択技法・残存リスクのいずれかに現れること（無言の削除を防ぐ） | `risk_unplaced:<id>` |
| 機械証拠節の `### Machine ...: test-analysis` ブロックの形式と JSON（機械証拠の中身は検査しない） | `machine_block_invalid` / `machine_block_json_missing` / `machine_block_json_invalid` |
| 実値の混入: メールアドレス、ローカル絶対パス | `email_address_present` / `local_path_present` |

- 検査は全件を集めて返します（先頭の1件で止めません）。
- 検証は形式だけを見ます。リスク評価の妥当性、技法の選択が問題構造に合うか、根拠の仕様が実在するか（別の成果物にある SPEC / DEC / ASM は本文だけでは確認できません）は意味の判定であり、本Skillの自己検証と runtime の最終証拠ゲート（`verify_runtime_evidence`）が担います。
- 下流のテスト側ID（TR・TC・TCN・CI・COND・ITEM）は禁止しません。テスト分析はテスト要求設計の入力だからです。
- 標準マトリクス（guidance.md）と一致しないレベルは `risk_level_mismatch` になります。案件固有のリスク評価方式を採用する文書は、現状の検証器では保存できません（§5）。

## 3. 保存（persist_document）

1. `validate` を実行し、不合格なら store に触れずに `blocked` を返します。
2. 確認記録（`write_confirmation_record`）を作り、ホストが store に登録します。確認記録は store の user-confirmed 認可と同じ12キーです。
3. `store.write(kind="test-analysis", ...)` を呼びます。CAS、冪等性、独立readbackは store の挙動に従います。
4. 成功時は `analysis_status: valid` と `document_sha256` を付けて返します。

- 前回版との比較は行いません（分析は全体再生成です。版の履歴は Git commit が持ちます）。
- 更新時の `expected_revision` は、直前に `read` で取り直した `git:<sha>` です。古い値は `revision_conflict` で止まります（データは失われません）。

### 保存の理由コード（store のコードをそのまま返す）

`access_denied`、`revision_conflict`、`create_if_absent_conflict`、`independent_readback_mismatch`、`git_artifact_ref_invalid`、`artifact_project_mismatch`、`branch_checked_out`、`approval_provider_unavailable`、`git_provider_command_failed`、`git_provider_unavailable`、`artifact_content_too_large`、`unchanged_artifact_write`（同一内容の再保存は失敗として返り、「現在版と同一」と読めます）。本モジュールの `test_scope_mismatch`（artifact_ref が `test-analysis/<scope-id>.md` と一致しない）。

## 4. 承認

- 保存は user-confirmed です。`--user-confirmed-ref` は、利用者がその文書を確認した後にだけ渡します。AIが確認前に値を作ってはなりません。
- 確認記録は呼出し元の自己申告であり、認証ではありません。
- 読取は、登録済みの案件範囲で確認記録なしに通ります（既存の挙動）。
- gated モードでは、各文書の保存を利用者が都度確認した結果を承認として扱います。

## 5. 入力 revision と既知の制約

### 入力 revision の記録

- `--source-revision` は、文書が依拠した入力の revision を1つの文字列にまとめた値です。本文にはその文字列を verbatim で含めます（検証が本文への出現を検査します）。
- 推奨の形式: `spec:<spec-analysis の保存 revision>;question:<question-analysis の保存 revision>;context:<project-context の保存 revision>;product:<製品 repository の commit SHA>`。使わない入力は省略せず `none` と書きます。
- 本文の記録場所は「テスト分析範囲」の `- 入力 revision: <同じ文字列>` の行を推奨します（追加の見出しを作らなくてもよい）。
- `--source-ref` には、テスト分析の依頼元や仕様の参照（例: `issue/<番号>`）を入れます。製品リポジトリの URL やローカルパスは入れません。

### 既知の制約

- **readback 不一致時の head（全kind共通）**: store は参照を `update-ref` で進めた後に独立readbackします。readback が一致しない場合、呼出し側には失敗（`independent_readback_mismatch`）が返りますが、head は戻りません。未検証の commit が head に残るため、`read` や `export` が未検証の内容を返しえます。呼出し側は、この失敗を成功として扱わず、head を読み直して確認してください。
- **同一 operation_id の再利用**: 現在の head を基準にした、同じ `operation_id` で内容の違う書込みは、Git store では新しい版として保存されます。`operation_id` の一意性は呼出し側の責務です。既定の `operation_id` は `test-` と文書・expected_revision のsha256の先頭32文字です。
- **CAS の単位**: 更新の CAS は branch の HEAD 単位です。scope を並列に保存すると、古い revision のままの保存は `revision_conflict` で止まります。
- **標準マトリクス固定**: 検証器は guidance.md の標準リスクマトリクスだけを照合します。案件固有のリスク評価方式を採用する場合、その方式のレベルは `risk_level_mismatch` として保存を拒否されます。方式の扱いは上流の判断です。
- **分類・表記の固定**: 重点の優先度、リスクのレベル、変更種別、操作可否は表に示した値だけを受けます。修飾付きの表記は拒否されます。
- **見出しの順序と追加の見出し**: テンプレートの順序は検査せず、追加の見出しも許容します。
- **意味の検証は対象外**（§2）。
- **機械証拠の内容は検査しない**: 機械証拠節のブロックは形式だけを検査します。内容の正しさは runtime の最終証拠ゲートで検証します（§6）。

## 6. runtime の起動と最終証拠ゲート

文書の `Machine Runtime / Entity（機械証拠）` 節は、runtime の出力をそのまま置きます。runtime は Python 3.11 標準ライブラリだけで動き、stdin の JSON object（`metadata` と `input`）を受けて stdout に1つの JSON envelope を返します。

```
python3 scripts/analysis_entities.py < request.json > envelope.json
```

- `request.json` の `metadata` には `skill`（`test-analysis`）・`runtime_contract_version`・`generator_contract_version`・`runtime_unit_key`（`artifact:analysis_entities:all`）・`input_mode` などを置きます。`input` の形式は `analysis_entities.py` が検証します（テストの fixture `tests/skills/runtime/test_test_analysis_entities.py` の `valid_input` が汎用例です）。
- envelope の `result_status` と `runtime_status` を確認してから、render 関数（`runtime_contract.py` の `render_runtime_input` / `render_runtime_result` / `render_machine_entities`）の出力を機械証拠節へ置きます。
- 最終成果物を返す直前に、`runtime_contract.py` へ `{"operation": "verify_runtime_evidence", "skill": "test-analysis", "normalized_skill_input": <実際に使った正規化入力>, "artifact_markdown": <候補の全文>, "previous_artifact_markdown": null, "partial_rerun": false}` を stdin で渡します。`valid` が `true` の場合だけ完成として扱い、`false` なら局所修正の契約へ戻し、未解決なら完成扱いしません。
- 保存の前に `test_analysis_document.py validate` と上記の証拠ゲートの両方を通過させます。validate は形式、証拠ゲートは機械証拠の整合を見ます。
