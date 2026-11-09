# feature-inventory-v1

scripts/feature_registry.pyはPython 3.11のstdinにJSON objectを受け、stdoutへJSON1件を返します。重複keyと16MiB超の入力を拒否します。

入力トップレベルはsnapshot、previous_snapshot（初回null）、observed_head_revision。snapshotはschema_version=feature-inventory-v1、project_ref、artifact_ref、artifact_revision、source_revision、previous_artifact_revision、operation_id、eventを必須とします。eventはinitial / pr_update / merge / release / external_revisionです。

- **expected_source_ids**：内容 = 当該分析で列挙すべきSRC ID配列
- **sources**：内容 = id, kind, ref, scope, status, revision, evidence_ref, enumeration_complete, unretrieved[], reason
- **features**：内容 = id, identity, name, kind, status, parent_id, source_ids[], implementation_refs[], spec_refs[], qa_refs[]
- **candidates**：内容 = id, source_ids[], evidence_ref, status, feature_id, reason, approval_ref
- **changes**：内容 = id, source_id, before_revision, after_revision, locator, evidence_ref, classification, feature_ids[], reason, approval_ref。分類を後から訂正する新規DIFにはsupersedes_id、approval_revisionを追加する。
- **history**：内容 = event_id, kind, revision, evidence_ref, from_ids[], to_ids[]を追記専用
- **unknown_areas**：内容 = 取得不能・発見不能な分析範囲の参照配列

IDはSRC-001、FEAT-001、CAND-001、DIF-001形式。featureのidentityは同一案件で同じ意味を表す安定値で、path・名称変更による再採番を防ぎます。sourceのcompleteはrevisionとevidence_ref、enumeration_complete=true、unretrieved=[]を必須とします。候補・差分の対象外には理由とapproval_refが必須ですが、承認主体の真正性は本helperでは確認しません。

結果はcomplete / incomplete / stale / idempotent / blocked。change_classificationは**今回イベントで確認する有効DIF**の分類済みID ÷ 今回イベントの有効DIF IDであり、履歴として残す旧PRのDIFを分母・分子へ混ぜない。analysis_updateでは現在のsource revisionに対応する有効DIFと今回追加した訂正DIFを対象とする。observed_candidate_mappingは機能ID対応済み候補のみ ÷ 全確認候補。承認参照付きの対象外候補は`excluded_candidate_ids`に記録し、対応済みの分子には含めません。分母0はrate=nullです。各率は分子・分母のIDを保存し、未取得sourceと未知領域を別に示します。all_product_features_discoveredは常にnullです。 unknown_areasが残る場合はsource_boundary_complete=falseとし、取得母集団が完全であると報告しません。

handoffにはartifact ref/revision、source revision、feature IDs、未分類差分IDs、expected_source_idsを返します。helperのcompleteは保存済み・承認済み・全製品発見の証明ではなく、実保存先のnative CAS・history/readbackと独立照合が必要です。仕様対応率・正式設計率・QA影響評価は別のownerが決定します。

## ローカルGit列挙契約

`scripts/git_source_inventory.py` はPython 3.11／Git CLIで `repository_root`、`authorized_root`、`base_sha`（初回null）、`head_sha` のJSONを受けます。2つのrootは正規化後に同一である必要があり、SHAはfull 40／64 hex commit IDです。read-onlyで `git ls-tree -r -z` によりHEAD全ファイル、baseがあれば `git diff --name-status -z --find-renames` で変更pathとrename元/先を列挙します。

出力 `git-source-snapshot-v1` 相当の `files[]`（path、mode、kind、object_sha）、`changes[]`（status、before_path、after_path）、base/head SHA、complete_file_listing、complete_change_listing、unretrieved、feature_count=nullを、実際に取得できた範囲だけ返します。Gitの列挙結果は意味上の機能ID・全資料の発見を証明しません。Git以外のsourceと併せた正規化・対応付けはfeature_registry.pyの入力側で実施します。

追加の機械検証：更新operationでは同一artifact_revisionの再利用を拒否します。分割は複数の派生ID、統合は複数の元IDが必要です。`handoff.snapshot_sha256`は候補snapshotのcanonical JSONのSHA-256、`handoff.source_inventory[]`はsource別のref・状態・revision・未取得の照合情報です。保存済みartifactの内容hash・認証済み承認の証明ではありません。

## Git差分母集団との照合

`scripts/reconcile_git_coverage.py`は`git_inventory`（同じ案件のgit_source_inventory.pyの結果）、`registry_request`（feature_registry.pyへの検証入力）、`source_id`（code種別、expected_source_idsに所属）のJSONを受け取ります。先にregistryのschema・ID・履歴を検証し、Git側のHEAD full SHAとsource revisionが一致し、変更一覧が完全な場合のみ、全Git変更ファイルの`after_path`と当該sourceの`changes[].locator`を照合します。renameは新pathに対応付け、旧pathはGit列挙結果の`before_path`に残します。未登録path、Gitにない差分ID、base/head改版不一致、未分類path、source不完全・旧HEADを判別します。

結果は`coverage.git_change_paths`、`registered_paths`、`missing_git_paths`、`unmatched_registry_change_ids`、`unclassified_git_paths`、`rate`、候補snapshot SHA-256を含みます。ファイルpathの網羅は機能・hunk・Issue・仕様の網羅ではありません。Git一覧そのものの真正性と実providerへの保存・承認は別途確認します。

同一artifactの更新では、前回のsource IDのkind/ref/scope、候補IDのsource_ids/evidence_ref、差分IDのsource_id/before_revision/after_revision/locatorを同じIDのまま別の意味に変更できません。既存DIFの分類・理由・機能ID・承認refを含め、保存済みDIFの全フィールドの上書き・削除は禁止します。再分類には新しいDIF ID、supersedes_id、独立根拠、承認ref／revisionを付けて履歴を維持します。未解決候補の判定状態の更新は既存契約に従います。正式なsource移設・diff改版時はIDを再利用せず新規登録と履歴の参照を保持します。

既存機能のname変更には`renamed`または`changed`、実装参照・status・親・仕様／QA参照等の変更には`changed`の追記履歴（対象IDをfrom_ids/to_idsへ記録し、今回source_revisionを付ける）が必要です。廃止は従来どおりretired等の履歴を要求します。`no_impact`も`out_of_scope`と同様に理由と承認refが必要で、実認証・承認scopeの真正性は別途確認します。

同じローカル保存先を明示選択した案件では`feature_registry.persist_snapshot(store,request,expected_revision,approval_ref,approval_revision,change_reason)`が既存保存済みsnapshotの独立再取得後にnative CASで保存します。元snapshotの意味上の一致・provider revision・snapshot hashを別に検証し、未解決項目があれば`analysis_status=incomplete`を維持します。外部保存providerの選択・認証は信頼済み呼出し元の責務です。

## 変更イベントの入力検証

`event=initial`以外のsnapshotには`event_basis`が必須です。`pr_update`にはbase_sha／head_sha／previous_head_sha、`rebase`にはさらにprevious_base_sha、`merge`にはmerge_commit_sha／target_ref／previous_head_sha、`release`にはcommit_sha／build_ref／target_ref、`external_revision`にはdocument_ref／before_revision／after_revision／evidence_refを指定します。Git commitは省略SHAやbranch名ではなくfull SHAを使用し、source_revision・コードsource revision・前回snapshotのrevisionと一致させます。外部資料のみの改版は資料refと旧／新revisionを直接比較し、コードPRがないことを変更なしと扱いません。

PR更新・rebase時のGit差分照合には`previous_head_git_inventory`を別途要求します。これは前回PR head→今回headの完全なGit差分で、通常の`git_inventory`は今回base→今回headを示します。両方のbase/head SHAを`event_basis`に照合し、二つの変更path集合の和集合を台帳の差分IDで分類します。二つ目の差分が欠ける場合は`incomplete`であり、片方だけの分類率100%を完了扱いにしません。

Git CLI入口では信頼済みの呼出し元が環境変数`QA_FEATURE_AUTHORIZED_ROOT`へ許可済みcheckout rootを渡します。入力JSONだけに記載された`authorized_root`ではread権限を主張できません。Pythonから直接`handle`を使う場合は呼出し側が認証済みの対象rootを固定する責任を負います。

下流のC・D・E担当へ渡す`handoff.feature_refs[]`は、機能ID／kind／status／parent ID、source／implementation／spec／QA refsを含む読取専用のprojectionです。`impacted_feature_ids`は差分がimpactと分類された機能ID、`approval_required_change_ids`は影響なし／対象外に分類された差分IDで、後続の認証済み承認確認を省略できません。`unknown_areas`を下流でも保持し、unknownを影響なしへ推測変換しません。

継続分析でsource revisionを変更しない内容修正は`event=analysis_update`と`event_basis={source_revision,evidence_ref}`を必須とします。これは初回処理とは別の更新イベントです。前回snapshotが存在するときは`event=initial`による新しいsnapshot作成を拒否します。ただし完全に同一のsnapshotとoperation_idの再送は従来どおり冪等に処理します。

`reconcile_git_coverage`は各DIFのpathが今回base→HEAD／前回HEAD→今回HEADのどちらに出現したかに応じて旧revisionを照合します。片方の差分だけに出現したpathに別の基準SHAを強制しません。

同一pathがPR base→headと前回head→現在headの両方に含まれ、旧SHAが異なる場合、`reconcile_git_coverage`は`(before_revision, path, after_revision)`の組ごとにDIFを要求します。いずれかの旧revisionが未分類なら`missing_git_revision_pairs`と`git_change_revision_pairs_not_registered`を返し、網羅率の分母からその組を除きません。同一の旧SHA・pathが両diffに現れる場合は重複計上しません。

Gitのgitlink（submodule）は親repositoryの`ls-tree`で確認できるentryですが、内部ファイルは列挙できていません。`git_source_inventory`は`status=incomplete`、`complete_file_listing=false`、`unretrieved=[gitlink:path@commit]`を返し、submoduleを検証済みの別情報源へ登録するまで完全取得とみなしません。PR差分一覧の取得完了は`complete_change_listing`で別途表します。

Git保存時の`authorize`には`approval_ref`だけでなく`approval_revision`、`source_ref`／`source_revision`、`operation_id`、`change_reason`、内容hashが渡されます。認証済み承認のscopeとrevisionの検証は信頼済みproviderの責務です。未確認の承認revisionでは書込みを拒否します。

`feature_registry.handle`は新規DIFの`after_revision`を同じ`source_id`の現在revisionと照合し、PR更新／rebaseでは`before_revision`をbase SHAまたは前回head SHAへ限定します。前回snapshotから保存済みの旧DIFは当時のrevisionを保持でき、今回のsource SHAへ書き換えることはありません。source未取得時は`change_source_incomplete`を残し、completeを返しません。

## 保存前のGit現在性確認

`persist_snapshot`はcode sourceを含む機能台帳を保存する際に`git_inventory_requests[]`を必須にします。各entryは`source_id,repository_root,authorized_root,base_sha,head_sha`を持ち、PR更新・rebase時は`previous_head_base_sha`も必要です。repository rootと許可rootは信頼済み呼出し元が指定し、Skillは`git_source_inventory`で実際のGit tree／diffを再取得し、`reconcile_git_coverage`で差分母集団・各revisionとの照合を再実行します。submoduleなど取得未完了、未分類Git path、未照合旧revision、source HEAD不一致の場合は保存をblockedにします。初回でbase SHAがない場合は、Git tree列挙のみ認め、コードDIFを列挙済みとみなして保存しません。非コードsourceの機能台帳は既存の保存経路を維持します。

## 継続PRのDIF履歴と複数repository

`feature-inventory-v1`の`changes[]`は履歴を含む追記型です。前回snapshotに存在するDIF IDの全フィールドは改変・削除しません。再分類する場合は別のDIF IDに`supersedes_id`（前回DIF ID）、新しい`evidence_ref`、`reason`、`approval_ref`、`approval_revision`を指定します。対象のsource ID・前後revision・locatorは一致する必要があります。旧行は履歴として残し、現在の分類率・未分類ID・下流影響は置換された行を除外します。

`persist_snapshot`は再分類を新しい成果物として保存する前に、保存providerへ`operation=reclassify`、旧・新classification、承認ref／revision、対象DIF IDと置換元ID、根拠・source revision・保存先expected revisionを渡して認可します。文字列の`approval_ref`だけでは許可しません。認可されなければ旧版を維持して保存をblockedにします。

PR更新・rebaseでGit差分を照合する際、前回snapshotにあるDIFは履歴として残し、**今回の差分母集団には新しく追加したDIFのみ**照合します。同一HEADでの`analysis_update`では現在有効なDIFを再利用できます。過去のDIFの旧／新revisionを現在HEADへ書き換えず、今回のbase→headと前回head→headの両差分で必要な組を登録します。

複数製品repositoryでは、`snapshot.source_revision`と`event_basis`のSHAは主たるイベントrevisionを表します。各`sources[].revision`がrepository別のHEADです。`persist_snapshot`の`git_inventory_requests`にはsource IDごとに実Gitのroot・base/head SHA、PR更新時は各sourceの前回HEADを指定します。主たるsourceはイベントbase/head、他のsourceは保存済み前回source revisionと独立Git差分で照合し、別repositoryのcommitを主repositoryのSHAに揃えません。保存先・Git root・承認元の選択は信頼済み呼出し元の責務です。

## 現在の差分と過去の履歴の分離（PR #34追補）

過去のDIFは削除せず、PR更新・rebase・merge・release・外部資料改版では今回新規の有効DIFだけを`metrics.change_classification`と`handoff.impacted_feature_ids`／`approval_required_change_ids`／`unclassified_change_ids`へ渡します。初回分析は全有効DIF、同じsource revisionの`analysis_update`は現在source revisionに対応する有効DIFと今回追加された分類訂正DIFを対象とします。過去の未分類履歴は別途`reasons`で未解決のまま維持され、無根拠に成功へ格上げしません。

同じ`source_id`、旧revision、新revision、`locator`に対して、複数の**有効な**DIFを記録できません。訂正は既存DIFを`supersedes_id`で置換し、両行を履歴に残します。Git path単位の差分照合で別hunkを独立に分類したい場合は、区別できるlocator／根拠が必要です。同じ識別子のまま異なる判定を併存させません。

再分類の保存前認可`operation=reclassify`には旧・新`feature_ids`、対象`source_id`／実際の`source_ref`／`source_scope`、旧／新revision、locator、旧／新evidence ref、旧／新classification、承認ref／revision、操作IDと保存先expected revisionを渡します。認可側が承認した機能範囲と一致しなければ保存を拒否します。単なる文字列の承認refでは許可したとみなしません。

PR更新・rebase・merge・releaseの主たる情報源は、イベントの`event_basis.primary_source_id`で明示できます。複数code sourceのHEADが同じSHAの場合は**必須**です。一意なcode sourceだけがイベントHEADに一致する従来データは、互換性のためそのsourceを使用します。主sourceのbase／前回HEADはイベントのSHAで検証し、他sourceのbase／前回HEADは各sourceの保存済みrevisionと実Git差分で独立検証します。同じSHAを持つ別repositoryをSHAだけで主sourceと誤判定しません。
