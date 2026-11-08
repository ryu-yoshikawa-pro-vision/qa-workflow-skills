# Project Context決定論的helper契約

Python 3.11のscripts/project_context.pyは、UTF-8 JSONを標準入力から読み、JSON1件を標準出力へ返します。重複JSON key・16節欠損・DEC/ASM破損・stable key重複を拒否します。

- **inspect**：入力 = markdown, required_keys[], artifact_ref, artifact_revision；結果 = current / incomplete / blocked。既存parserで必要keyとIDを検証
- **discover**：入力 = project_name, enumeration_complete, candidates[]；結果 = existing / absent / ambiguous / unconfirmed / blocked
- **prepare-create**：入力 = project_name, enumeration_complete, candidates[]；結果 = 不存在確認済み時のみdraft
- **prepare-update**：入力 = markdown, artifact_ref, expected_revision, source_ref, source_revision, change_reason, updates；結果 = 既存stable keyだけを差分変更したdraft
- **placement**：入力 = owner, scope, target_ref, existing_policy；結果 = approval_required / reuse_candidate

discoverの各候補はrefとstatus（readable / absent / denied / unavailable）、readable時はmarkdownとrevisionを持ちます。enumeration_completeがfalseなら不存在を確定しません。候補が複数あればauto-mergeしません。既存文書の案件名はSection 1のプロジェクト欄と一致させます。

prepare-updateは既存のSection 16に存在するkeyのみ更新します。既存parserのscalar / path / ordered_text / ordered_lines型、値の意味、秘密情報の非保存を維持します。共有templateにまだ登録されていないfeature向けkeyはA担当の共有変更を待ちます。更新draftはexpected_revision、source ref/revisionを渡しますが、sourceの真正性・保存先の認可やCASそのものを証明しません。

配置方針はscope、owner、対象ref、revision、承認元refの一致だけを照合し、reuse_candidateを返します。外部サービスの信頼された承認と期限・権限の再確認なしに保存・移動を行いません。readback結果・過去revisionは案件の実providerの正本として検証します。

## DEC/ASM ID更新の候補

`operation=prepare-ids` は `markdown`、`artifact_mode=create|update`、`artifact_ref`、`expected_revision`（更新時のみ。createはnull）、`source_ref`、`source_revision`、`change_reason`、`dec_asm_owner=project-context`、`decisions[]`、`assumptions[]`を受け取ります。Section 12/13がこの案件の正本であると確認した場合にだけ使用します。既存`project_context_ids.py materialize`にstable ID割当を委譲し、元文書のDEC/ASM表だけを置換します。前後の文章、他の節、Section 14/16は維持します。旧DEC/ASMの消失、重複ID、不正な再利用はblockedです。

戻り値は `draft` と `allocated_ids`、履歴検査後の候補本文です。認証されたowner、元の保存revision、native create-if-absent／CAS、履歴と独立readbackは呼出し側の実providerで検証する必要があります。入力中の`dec_asm_owner`は呼出し側の宣言であり、それ自体は権限の証明にはなりません。

既存stable keyの更新候補は変更理由を必須とし、返すdraftにはartifact ref、expected revision、source ref/revisionと変更理由を保持します。これらの文字列を保存時の認証や元文書の現在性の証明には使いません。

更新値の安全条件：scalar/pathは単一行、pathは案件rootからの相対参照のみを受け付けます。絶対path、drive指定、`..`、URI・ホーム参照を拒否します。既存文書の読取互換性を維持するため、この制約は更新する値へ適用します。16節外の数値見出しを挿入した文書も拒否します。
