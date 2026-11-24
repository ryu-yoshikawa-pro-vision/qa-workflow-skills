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

保存の承認方式は`approval_source`引数で選びます。未指定（`None`）の場合は、`authorize`を渡していなければ既定の`user-confirmed`、渡していれば`trusted-callback`になります。`trusted-callback`は従来どおり、信頼済み`authorize`callbackが各操作を判定し、callbackがなければ`trusted_authorizer_required`で停止します。`trusted-callback`は、信頼済みhostが承認サービスを注入する場合の追加検証（より強い承認）で、任意です。`user-confirmed`は、ユーザーが当該成果物を明示的に確認した後にホストが`record_user_confirmation(...)`で登録した確認記録と完全一致する書込み・再分類だけを許可します。既定の承認はユーザー確認の自己申告であり、認証ではありません。確認記録の要求形は`trusted-callback`のcallbackへ渡される要求と同じキーを持ち、writeでは`operation_id`と`change_reason`も含みます（reclassifyはfeature_registryが`authorize`へ渡す決定dictそのもの）。ホストはユーザーが当該成果物を明示的に確認した後にだけ呼ぶこと。AIが確認前に呼んではなりません。確認記録はプロセス内にだけ保持され、永続化されません。取消し（失効）の機能はありません。ユーザー確認は呼出し元による自己申告であり、認証ではありません。不正な`approval_source`値（大文字小文字・空白の違いを含む。`None`は未指定として扱う）は`approval_source_invalid`、`user-confirmed`と`authorize`の併用は`approval_source_conflict`、`trusted-callback`で`authorize`がない場合は`trusted_authorizer_required`で拒否します。SQLiteのスキーマは変更せず、モードは永続化しません。

`persist_prepared(store,preparation,project_ref,operation_id,approval_ref,approval_revision)`は、同じhelperの準備操作から作った候補だけを保存します。ホストCLIの`save-prepared`も、この`persist_prepared`だけを経由します（任意の本文を直接書く保存経路はありません）。既存更新では元の保存本文とexpected revisionを再取得して照合し、競合・未承認・readback不一致を拒否します。返す保存先revisionは候補のローカル論理revisionと別に保持します。初回作成時も根拠のsource ref/revisionと変更理由が必要です。

### 初回配置・編集方針の記録

`prepare-placement`は、既存Project Contextの`markdown`、`dec_asm_owner=project-context`、`artifact_ref`、`expected_revision`、`source_ref`／`source_revision`、`change_reason`、`policy`を受け取ります。`policy`の必須keyは`owner`、`scope`、`target_ref`、`revision`、`approval_ref`、`approval_revision`、`editable_scope`、`feature_index_ref`です。既存DEC/ASMがある場合は`existing_decisions`／`existing_assumptions`へ保存済み行を含め、既存helperの履歴検証に通します。

初回または方針変更時は、既存Section 12のDECとSection 14の参照を同一draftに記録します。同一方針は`existing_policy`との一致で`reuse_candidate`を返し、不要なrevisionを作りません。この段階の`approval_ref`は自己申告値です。`persist_prepared`から実保存する際には承認が必要です。`trusted-callback`では承認scope・revisionを外部認証した`authorize`callbackが必要で、既定の`user-confirmed`では完全一致する確認記録が必要です。

`prepare-sections`は、根拠source・revision、変更理由、元文書ref／revisionを必須にし、既存文書の1〜11節と15節の本文だけを差分更新します。DEC/ASMの12/13節、成果物参照の14節、stable keyの16節はそれぞれ専用の更新操作へ委譲します。`prepare-create`にも任意の`section_updates`を指定でき、取得できた案件情報だけで既定templateを初期化します。いずれも保存済み正本への変更ではなく、実書込みには`persist_prepared`と認証済み承認を必要とします。

配置方針の変更では、Section 12とSection 14に記録された現在有効なDECを照合し、旧DECの状態を`置換済み`、`置換先ID`を新DECに更新したうえで新方針を保存します。既存方針の`existing_policy.decision_id`と文書上のDECが不一致の場合はblockedとし、別の有効DECを並立させません。同一方針の再利用は、保存済みSection 12/14と方針のref・scope・revisionが一致する場合だけ可能です。

正本が既存のGit管理Markdownである場合は、`scripts/git_artifact_store.py`の`GitArtifactStore`を明示選択できます。対象Git branchの`docs/PROJECT_CONTEXT.md`等を正本とし、Git commit SHAをexpected revisionに使う`update-ref`のnative CASで同一pathを更新します。履歴はGit commitから独立読戻しします。選択したbranchのGit objectが正本であり、未checkoutの作業ディレクトリを現行文書とは扱いません。ローカルSQLiteは別の案件でSQLiteを正本に選択した場合にのみ利用します。

`trusted-callback`では、読み取りにも信頼済みhostから注入された`authorize`による案件scopeの権限確認を行います。operation再送時も権限を再評価します。両保存providerは認証済み呼出し元を仮定し、権限を自己申告するJSON CLIからは呼び出しません。
`user-confirmed`では、読取は登録済みの案件scope内であれば確認記録なしで許可されます（CASのための読取を含む）。ここでの「登録済みの案件scope」とは、いずれかの確認記録（read / write / reclassify）が登録された案件を指します。write／reclassifyの確認記録も、その案件の別artifactを含む読取scopeを開きます（書込み後の独立readbackはこの挙動に依存します）。read記録だけの案件では書込みは許可されず、`access_denied`で拒否します。確認記録を登録していない案件（他案件を含む）の読取は拒否します。この緩和により、`user-confirmed`では案件内の読取ごとの承認と、登録後の読取の取消しは行いません。これらの防止は`trusted-callback`のみの保証です。

Git providerは許可済みrepository rootの外にGit metadataを保存するworktree／外部Git dirを拒否します。対象branchの履歴・objectが許可外rootへ暗黙に作成されないようにするためです。

Git providerは既存pathを最後に変更したcommitの件名（`qa artifact: <kind> <path>`）と`QA-Project-Ref` trailerが、呼出しのkindと案件に一致しない場合、読出し・書込みともに`artifact_project_mismatch`で拒否します。trailerの無いcommitも案件を証明できないため拒否します。書込みは参照更新の前に拒否されます。commit messageに入る値は改行として扱われる文字を含められません。
`user-confirmed`で書込んだcommitには`QA-Approval-Source: user-confirmed`のtrailerを付けます。`trusted-callback`のcommitには付けません。`_assert_owner`は件名と`QA-Project-Ref`だけを参照するため、trailer付きcommitも従来どおり読取れます。旧版の`QA-Approval-Mode`のtrailerを持つcommitも同じ理由で読取れます（後方互換）。trailer `QA-Approval-Source` は監査用の表示であり、承認の証跡ではありません（読取時に検証されません）。

`GitArtifactStore`は、対象branchが主ワークツリーまたは任意のlinked worktreeでcheckoutされている場合は`branch_checked_out`で構築を拒否します（`symbolic-ref -q HEAD`と`worktree list --porcelain`の両方で判定）。

`scripts/artifact_host.py` は、`GitArtifactStore`を`user-confirmed`で使うホストCLIです（JSON 1行、エラーは`{"status":"blocked","reason":...}`と非ゼロ終了）。`init-branch`は空treeのroot commitをplumbingで作り、HEAD・index・作業ツリーに触れません。source repositoryのhookは実行させず（空のhooksPath）、author名・emailは`GitArtifactStore`と同じ検査（制御文字・改行の拒否、emailに`@`）を受けます。

`save-prepared`は、`project_context.py`の`prepare-*`の要求JSON（`operation`、`artifact_ref`、`source_ref`、`source_revision`、`change_reason`、更新時は`markdown`と`expected_revision`）を`--prepared-file`で受け取り、`persist_prepared`で保存します。任意の本文は受け取りません。16節構造、案件名と`--project-ref`の一致、既存版本文の照合、DEC/ASM検証は`persist_prepared`が行い、失敗時は何も書きません。`--user-confirmed-ref`（単一行・1024文字以内・制御文字と改行類（U+2028・U+2029を含む）なしの参照）は、ホストがこのプロセス内で`persist_prepared`が`store.write`へ渡す要求と同じキー・値の確認記録として登録してから書込みます。`--operation-id`を省略すると`prepared-<preparedファイルのsha256>`を使います。`approval_revision`は`sha256:<内容のsha256>`です（placementの草案では草案の承認revisionを使う）。`feature-inventory`は`save-prepared`では`unsupported_kind_for_now`で拒否します（hintで`save-snapshot`を案内します）。`save`（生の本文を書く旧コマンド）は削除されています。

`save-snapshot`は`feature-inventory`を`feature_registry.persist_snapshot`経由で保存します（Git証跡、再分類の認可、previous_snapshot照合を迂回しません）。必須: `--snapshot-file`（snapshot本体のJSON）、`--git-inventory-requests-file`（git_inventory_requestsの配列。コードsourceが無ければnull。各`authorized_root`は信頼済みの環境変数`QA_FEATURE_AUTHORIZED_ROOT`の実パスと一致する必要があり、入力JSONだけでは読取りを主張できません。保存先（store）は、読取り元のsource repoの`.git`へ書き込みうる配置なら`store_repo_is_source_repo`で拒否します。拒否するのは、(a) storeとsourceが同一のGitリポジトリ（`git rev-parse --git-common-dir`／`--absolute-git-dir`の実パス、symlink解決後が一致。linked worktreeを含む）、または(b) storeのtoplevelがsourceのtoplevelの配下（storeがsourceの作業ツリー内にある）の場合だけです。sourceが保存先の配下にあっても、sourceが自分自身のtoplevelと独自の`.git`を持つ独立したリポジトリなら許可します（保存先の作業ツリーの単なるサブディレクトリは(a)で拒否）。判定は`GIT_OPTIONAL_LOCKS=0`の読取り専用gitで行い、判定に失敗した場合（repoでない・パスが解決できない・gitの失敗）は`store_source_relation_unverifiable`で拒否します（fail closed）。、`--expected-revision`（`none`または`git:<sha>`。初回は`none`）、`--observed-head-revision`（呼出し元が観測したhead。snapshotの`source_revision`と一致しなければ`stale`。これはsnapshotの`source_revision`との自己整合の検査であり、code sourceが無いsnapshot（`--git-inventory-requests-file`がnull）ではHEADの独立照合はありません）、`--change-reason`、`--user-confirmed-ref`。任意: `--previous-snapshot-file`（初回は省略）、`--operation-id`（snapshotの`operation_id`と一致する場合だけ）、`--hold-source-refs`（既定では無効。指定時はソースrepoの`.git`へlockfileを一時的に作る）。ホストは保存の直前に、このプロセス内だけで、`persist_snapshot`が`store.write`へ渡す要求と同じキー・同じ値の確認記録を登録します。`approval_ref`は`--user-confirmed-ref`、`approval_revision`は`sha256:<snapshot正規化JSONのsha256>`です。再分類は`feature_registry.reclassification_decisions`が返す決定dictを対象にします。任意の`--confirmed-reclassifications-file <json>`は、利用者が確認した再分類ごとの承認参照とrevisionの表で、形式は`[{"change_id": "...", "approval_ref": "...", "approval_revision": "..."}, ...]`です（各値は単一行・1024文字以内・制御文字なし。change_idは重複不可）。ホストは、snapshotの再分類のうち、この表の`change_id`・`approval_ref`・`approval_revision`が**完全一致**するものだけを確認記録として登録します。表に無い再分類、または承認参照・revisionが不一致の再分類を含むsnapshotは保存せず、`reason: reclassification_not_confirmed`と`unconfirmed`（`change_id`と理由`not_listed`／`approval_ref_mismatch`／`approval_revision_mismatch`）を返します。再分類が無いsnapshot（初回）では表は不要です（指定されても形式は検査しますが、内容は使いません）。この表も利用者の確認を示す自己申告であり、認証ではありません。確認記録が一致しない再分類は`change_reclassification_approval_unverified`で、なお拒否されます。出力はJSON1行（`status`、`revision`、`sha256`、`analysis_status`、`snapshot_sha256`、`reasons`）で、`stored`または`idempotent`のときだけ終了コード0です。`reasons`は分析の残課題の理由コード（空配列も可）です。書込みの後にソースHEADが動いた場合は保存を取り消さず、`status: stored`に`warnings: ["source_head_changed_after_write"]`を付けます。書込み前の検査の失敗は`blocked`です。`blocked`の出力は`reason`（理由コード）と、ある場合は`detail`（原因の要約）を持ちます。snapshotの形式エラーは`snapshot_invalid:<code>`で返し、例えば`artifact_ref`が相対パスで末尾`.md`か`.json`でない場合は`snapshot_invalid:git_artifact_ref_invalid`と`detail`（artifact_ref は相対パスで末尾が .md か .json）を返します。`--user-confirmed-ref`は自己申告であり認証ではありません。AIは利用者が当該snapshotを確認する前に渡してはなりません。

`read`・`export`・`verify-projection`も、同じプロセスで案件の読取確認を登録するため`--user-confirmed-ref`が必要です。`export`は現在の内容をバイト一致で投影ファイルへ書き出す読取専用の写しで、一時ファイルとrenameで書き、途中失敗で壊れたファイルを残しません。手編集は正本に反映されず、`verify-projection`が`drifted`で検出します。既存の`--out`が存在し内容がstoreの現在内容と一致しない（手編集されている）場合、`export`は`projection_drifted`で拒否し、上書きしません。`--force`を明示したときだけ上書きし、出力JSONに`"overwrote_drifted": true`を含めます。投影の0444の権限は目安であり保護ではありません（共有ファイルシステムや権限を変えられる利用者からは防げません）。`project_context.py`のJSON CLIは引き続き保存しません。

`GitArtifactStore`の確認後の書込みは、構築時に加えて`update-ref`の直前にも保存先branchのcheckout検査を再実行します。ただし検査と`update-ref`の間に別worktreeでcheckoutされる競合は防げず、この限界は残ります。

`operation_id`の冪等性（git store）は、同一の`expected_revision`（直前版）と同一内容の再送に対するものです。現在のheadを`expected_revision`とする新しい書込みで既存の`operation_id`を再利用した場合、storeはそれを新規操作として保存し、commit trailerに同じ`QA-Operation-Id`が複数残ります（SQLite版は`operation_id_reused`で拒否します）。`operation_id`の一意性は呼出し側の責務です。

branchは案件とkindごとに分けます（例: `qa-artifacts/<project>/<kind>`）。Git branchのrevisionはcommit SHAのため、1つのbranchに複数のkindや案件を置くと、CAS revisionが無関係な成果物にまで及びます。

### 保存済み配置方針の再利用条件

`prepare-placement`はSection 12の有効DECの備考・決定根拠とSection 14の同一scopeの行から方針を再構成し、owner、scope、target_ref、policy revision、approval_ref、approval_revision、editable_scope、feature_index_ref、DEC IDを照合します。入力`existing_policy`の値だけでは再利用と判定しません。承認revisionは新規記録時にDEC備考とSection 14備考の双方に保存します。旧文書に承認revisionがない場合、承認revisionを推測せず、同一方針の再利用は行いません。既存DECを置換するときは、記録済み内容を維持したまま旧DECを置換済みにします。

### spec-analysis の保存（追記）

`spec-analysis` は `save-document` で保存します（`scripts/artifact_host.py`）。`save-document` は `../spec-analysis/scripts/spec_document.py` の `validate` で形式を検証し、通過した文書だけを確認記録の登録後に `persist_document` で保存します。保存先は `qa-artifacts/<project>/spec-analysis` のbranchの `spec-analysis/<scope-id>.md` です。`save-prepared` と `save-snapshot` は spec-analysis を受け付けません（`unsupported_kind_for_now`）。`read`・`export`・`verify-projection` は `--kind spec-analysis` で同じ規則により読みます。保存の理由コード、証跡記法、既知の制約（readback 不一致時に未検証 commit が head に残ること、同一 operation_id の再利用）は `../spec-analysis/references/persistence-contract.md` に従います。

### question-analysis の保存（追記）

`question-analysis` は `save-document --kind question-analysis` で保存します（`scripts/artifact_host.py`）。`save-document` は `../question-analysis/scripts/question_document.py` の `validate` で形式を検証し、通過した文書だけを確認記録の登録後に `persist_document` で保存します。保存先は `qa-artifacts/<project>/question-analysis` のbranchの `question-analysis/<scope-id>.md` です。`save-prepared` と `save-snapshot` は question-analysis を受け付けません（`unsupported_kind_for_now`）。`read`・`export`・`verify-projection` は `--kind question-analysis` で同じ規則により読みます。

### test-analysis の保存（追記）

`test-analysis` は `save-document --kind test-analysis` で保存します（`scripts/artifact_host.py`）。`save-document` は `../test-analysis/scripts/test_analysis_document.py` の `validate` で形式を検証し、通過した文書だけを確認記録の登録後に `persist_document` で保存します。保存先は `qa-artifacts/<project>/test-analysis` のbranchの `test-analysis/<scope-id>.md` です。`save-prepared` と `save-snapshot` は test-analysis を受け付けません（`unsupported_kind_for_now`）。`read`・`export`・`verify-projection` は `--kind test-analysis` で同じ規則により読みます。保存の理由コード、入力 revision の記録、既知の制約は `../test-analysis/references/persistence-contract.md` に従います。
