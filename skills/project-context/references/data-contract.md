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

## 明示選択されたローカル保存先での永続化

`scripts/artifact_store.py` の `LocalArtifactStore` は、許可されたローカルroot内に所有者限定SQLiteを設け、`project-context`／`feature-inventory`のnative transactionによる新規作成・revision CAS・immutable履歴・独立読戻しを行います。遠隔providerの代替ではありません。Pythonの信頼済み呼出し元は`authorize(request)`を渡して認証済み承認のscope／revision／許可を保存直前に検証します。JSONの`approval_ref`単独では権限を証明できません。

`persist_prepared(store,preparation,project_ref,operation_id,approval_ref,approval_revision)`は、同じhelperの準備操作から作った候補だけを保存します。既存更新では元の保存本文とexpected revisionを再取得して照合し、競合・未承認・readback不一致を拒否します。返す保存先revisionは候補のローカル論理revisionと別に保持します。初回作成時も根拠のsource ref/revisionと変更理由が必要です。

### 初回配置・編集方針の記録

`prepare-placement`は、既存Project Contextの`markdown`、`dec_asm_owner=project-context`、`artifact_ref`、`expected_revision`、`source_ref`／`source_revision`、`change_reason`、`policy`を受け取ります。`policy`の必須keyは`owner`、`scope`、`target_ref`、`revision`、`approval_ref`、`approval_revision`、`editable_scope`、`feature_index_ref`です。既存DEC/ASMがある場合は`existing_decisions`／`existing_assumptions`へ保存済み行を含め、既存helperの履歴検証に通します。

初回または方針変更時は、既存Section 12のDECとSection 14の参照を同一draftに記録します。同一方針は`existing_policy`との一致で`reuse_candidate`を返し、不要なrevisionを作りません。この段階の`approval_ref`は自己申告値です。`persist_prepared`から実保存する際には、承認scope・revisionを外部認証した`authorize`callbackが必要です。

`prepare-sections`は、根拠source・revision、変更理由、元文書ref／revisionを必須にし、既存文書の1〜11節と15節の本文だけを差分更新します。DEC/ASMの12/13節、成果物参照の14節、stable keyの16節はそれぞれ専用の更新操作へ委譲します。`prepare-create`にも任意の`section_updates`を指定でき、取得できた案件情報だけで既定templateを初期化します。いずれも保存済み正本への変更ではなく、実書込みには`persist_prepared`と認証済み承認を必要とします。

配置方針の変更では、Section 12とSection 14に記録された現在有効なDECを照合し、旧DECの状態を`置換済み`、`置換先ID`を新DECに更新したうえで新方針を保存します。既存方針の`existing_policy.decision_id`と文書上のDECが不一致の場合はblockedとし、別の有効DECを並立させません。同一方針の再利用は、保存済みSection 12/14と方針のref・scope・revisionが一致する場合だけ可能です。

正本が既存のGit管理Markdownである場合は、`scripts/git_artifact_store.py`の`GitArtifactStore`を明示選択できます。対象Git branchの`docs/PROJECT_CONTEXT.md`等を正本とし、Git commit SHAをexpected revisionに使う`update-ref`のnative CASで同一pathを更新します。履歴はGit commitから独立読戻しします。選択したbranchのGit objectが正本であり、未checkoutの作業ディレクトリを現行文書とは扱いません。ローカルSQLiteは別の案件でSQLiteを正本に選択した場合にのみ利用します。

読み取りにも信頼済みhostから注入された`authorize`による案件scopeの権限確認を行います。operation再送時も権限を再評価します。両保存providerは認証済み呼出し元を仮定し、権限を自己申告するJSON CLIからは呼び出しません。

Git providerは許可済みrepository rootの外にGit metadataを保存するworktree／外部Git dirを拒否します。対象branchの履歴・objectが許可外rootへ暗黙に作成されないようにするためです。
