# テスト計画artifact契約

## Identity・version

ownerは`test-management`です。保存先発行の`artifact_ref`、不透明な`revision`、scope、計画上の対象build／環境／期間を保持します。`PLAN-001`、`ACT-001`、`CA-001`等のIDはartifact系列内だけで安定し、global ID counterを使いません。各改版は旧ref／revisionと差分を参照します。

## 計画・source inventory

計画行はplan-local ID、`<artifact_ref>#<local_id>@<revision>`形式のQA requirement／architecture ref、level／type、suite・順序、担当・見積工数・資源・開始／終了基準を持ちます。利用可能なfixtureでowner・local ID・artifact ref・revision・scopeを照合します。入力source行にはcurrentness・取得状態・必要な承認状態と証拠refを保持し、確定中の計画が参照する入力だけを検証します。入力sourceの承認状態が`承認済み`の場合、承認証拠refに未設定・未確定・unknown等のplaceholderを認めません。無関係なscopeのstale sourceで計画全体を一律に失効させません。計画母集団と実取得を同じ行に上書きせず、次の2つの表で保持します。

- **予定母集団**: population ID、source owner、期待source ref／revision、scope、query／取得範囲、execution／evidence単位、対象build、environment、必須／任意。
- **取得readback**: population IDで予定行に対応し、実source owner・ref／revision・scope・取得範囲・execution単位・build・environment・currentness、取得状態、実行状態、結果状態、source owner readback ref、未取得／未実行理由を保持。

取得済み・部分取得・0件確認済みのreadback行には、source ownerから読戻した証拠refと実source identityを記録します。完全取得・0件確認の実identityは予定ref／revision／scope／取得範囲／unit／build／environmentと一致しなければなりません。部分取得は同じidentityのsubsetとして、取得範囲と不足理由を記録します。未取得・取得不能・取得不明でreadbackを得られない行ではactual identityとreadback refを空値（`-`）にし、推測で埋めず理由と再開条件を記録します。

取得状態は`取得済`、`部分取得`、`未取得`、`取得不能`、`0件確認済み`、`不明`です。実行状態は`実行済み`、`実行中`、`未実行`、`取消`、`実行失敗`、`結果不明`、`対象なし`です。`実行失敗`はrunner／環境等の失敗が確認できた状態で、結果状態は`判定不能`、失敗理由とreadback証拠を必要とします。これは実行済みテストの判定`FAIL`と別です。`結果不明`は開始後の状態・結果を確定できず、`実行失敗`とも`未実行`とも同一視しません。`対象なし`は同じpopulationの取得状態が`0件確認済み`の場合だけ使います。

予定sourceと取得sourceを別表にし、population IDで結び付けます。readback結果のref／revision／scope／range／unit／build／environmentが予定値と一致しなければstale／mismatchとして拒否します。raw結果はsource ownerの正本を参照し、Fはraw結果を複製しません。

## Monitoring・closure

snapshotはplan artifact ref／revision、対象build／environment、取得時点、分母と単位、source acquisition／execution／result各状態の件数、差異、未処理scopeを記録します。異なるplan revision・build・environmentのpopulationを一つのsnapshotに混ぜません。部分取得・unknown・必須の未実行・取消・実行失敗・結果不明が残る場合は全体の完了を主張しません。状態別の件数は出力できますが、reporting用aggregate pass rateは生成しません。

完了を主張する場合は、計画母集団のsource readback行がすべて存在し、必須sourceの取得完全性、必須実行の確定結果（または証拠付きの0件確認）、全終了基準の判定、対象scopeの差異・risk・action、承認・currentnessを個別に閉じた証拠が必要です。欠落readbackは0件や未実行へ推測補完しません。`取得済`の必須実行が未実行・実行中・取消・実行失敗・結果不明・判定不能／未判定のとき、またはrequired sourceが未取得・部分取得・取得不能・不明のときは完了できません。実行結果`FAIL`や終了基準`未達`の正式判定があっても、QA活動が終了したという判定とは分けます。製品のrelease可否はtest-managementの判断対象外です。取消／対象外は承認された計画改版により母集団から除かれた場合だけです。

## Risk・是正

Project riskとProduct Riskは別ID・別owner・別評価です。project risk rowは計画遂行上の事象、影響scope、根拠、対応、owner、状態を持ちます。是正actionは差異／risk ref、影響scope、action、owner、期限または`未設定`、状態、結果refを持ちます。差異はplan-local ID、scope、根拠、対応、owner、状態と処理証拠refで追跡します。`解決済み`には処理証拠ref、`受容済み`には判断証拠refと承認主体を必要とします。是正処置の`完了`には結果ref、`対応不要`には結果refと判断主体を必要とします。進行中・blocked・unknown・状態不明・証拠不足が残る対象scopeを完了扱いしません。期限・担当・Risk scoreを推測しません。

## Approval・保存・履歴

計画の承認は認証されたauthorityが対象scope・artifact ref・revisionを承認した記録と一致する必要があります。承認主体・roleと承認証拠refには有効な値を記録し、空欄、`-`、`unknown`、`未取得`、`未設定`、`未確定`、`未確認`、`取得不能`、`N/A`、`失効`、`未承認`、`不要`等のplaceholderを証拠として扱いません。revision変更時は旧承認が失効します。静的validatorは形式の一致だけを検証し、承認元の真正性を証明しません。

実保存先が未選定・未認証なら書込みをblockedにします。Aのworkflow claim、fixture、Markdown出力だけをnative CAS・revision履歴・保存後readbackとみなしません。保存後に応答が失われた場合はsource ownerが実保存状態を照合してから再開します。

## JSON正本packet（保存・検証）

保存する正本は canonical JSON（キー順ソート、区切り`,`/`:`、UTF-8、非ASCIIそのまま）のpacketです。Markdown（`assets/output-template.md`）はこのpacketから描画する表示用であり、Markdownを正本や完了証拠にしません。`scripts/management_runtime.py`は次の5つの`operation`を持ち、入力はJSON stdin、結果はJSON stdoutです。stdlibだけを使い、ファイルの読み書き、外部通信、他Skillのimportを行いません。例は`assets/plan-packet.example.json`を参照します。

### packetの項目と Markdown表の対応

| packetキー                                                        | 内容                                                                                                                                                                   | Markdown表                            |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| `schema` / `owner`                                                | `test-management-plan-v1` / `test-management`                                                                                                                          | 成果物メタデータ                      |
| `artifact_ref` / `revision` / `scope` / `plan_version` / `target` | 保存先発行のref、不透明revision、scope、計画plan version、build・environment・期間                                                                                     | 成果物メタデータ                      |
| `planned_sources[]`                                               | `source_id`（`SRC-NNN`）、owner、scope、artifact_ref、revision、content_hash。上流architecture・QA要求・source ownerを含む                                             | 入力source                            |
| `planned_populations[]`                                           | `population_id`（`POP-NNN`）、`source_id`、query範囲、execution単位、build、environment、`required`                                                                    | 予定source inventory・必要実行母集団  |
| `readbacks[]`                                                     | population単位の取得readback。`acquisition_state`、`execution_state`、`outcome`、`currentness`、`actual`（実identity or null）、`readback_ref`、`reason`、`zero_check` | source owner readback・取得／実行状態 |
| `plan_items[]`                                                    | `PLAN-NNN`、QA要求ref、architecture ref、level／type、suite・順序、担当、見積工数、resource、`source_ids`                                                              | 計画・資源                            |
| `criteria[]`                                                      | `CRIT-NNN`、開始／終了、基準、scope、evidence、判定                                                                                                                    | 開始・終了基準                        |
| `project_risks[]`                                                 | `PROJ-RISK-NNN`、risk、scope、根拠、対応、owner、状態、状態証拠、承認主体                                                                                              | Project risk                          |
| `corrective_actions[]`                                            | `CA-NNN`、差異／risk ref、scope、action、owner、期限（未設定可）、状態、結果ref、承認主体                                                                              | 是正処置                              |
| `differences[]`                                                   | `DIFF-NNN`、scope、差異、根拠、対応、owner、状態、状態証拠、承認主体                                                                                                   | 差異・未処理事項                      |
| `approval`                                                        | `state`と、承認済みの場合だけ`record`（artifact_ref、scope、revision、承認主体、role、証拠ref）                                                                        | 承認                                  |
| `history[]`                                                       | revision、置換元revision、変更理由、scope。末尾は現在のrevision                                                                                                        | 改版履歴                              |
| `monitoring`                                                      | `snapshot_ref`、測定時点、`counts`（再計算対象の全件数キー）                                                                                                           | Monitoring snapshot                   |

`readbacks`の`actual`は、`owner`、`source_ref`、`revision`、`scope`、`range`、`execution_unit`、`build`、`environment`を持ちます。取得済・0件確認済みは予定identityと完全一致し、部分取得は範囲だけが異なる（不足理由必須）ものだけを許します。未取得・取得不能・不明では`actual`、`readback_ref`、`zero_check`を`null`にし、`currentness`を`unknown`にします。

### 状態の組合せ規則

- 取得済・部分取得: 実行状態は`対象なし`以外。実行済みは結果`PASS`／`FAIL`／`判定不能`／`未判定`のいずれか（判定不能は理由必須）。実行失敗は結果`判定不能`と理由必須。結果不明は結果`-`と理由必須。実行中・未実行・取消は結果`-`。
- 0件確認済み: `zero_check`（query＝population範囲、checked_at）必須、実行状態`対象なし`、結果`-`。
- 未取得・取得不能・不明: 実行状態は`未実行`か`結果不明`、結果`-`、理由必須。
- 判定や完了の証拠: `解決済み`には状態証拠、`受容済み`には状態証拠と承認主体、`完了`には結果ref、`対応不要`には結果refと承認主体が必要です。判定済み基準には根拠refが必要です。

### 検証operation

| operation           | 入力                                                                                                                                        | 出力の主キー                                                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `validate`          | `{"operation","artifact"}`                                                                                                                  | `valid`、`status`（valid／invalid）、`counts`、`issues`                                                                                   |
| `validate_readback` | `{"operation","candidate_artifact","readback","expected_revision"}`。readbackは`owner`、`scope`、`artifact_ref`、`revision`、`content_hash` | `valid`、`status`（readback_matches／blocked）、`storage_content_sha256`、`provider_authenticity`                                         |
| `impact`            | `{"operation","artifact","current_source_refs"}`。refは`owner`、`scope`、`artifact_ref`、`revision`、`content_hash`                         | `status`（current／incomplete）、`stale_source_ids`、`unknown_source_ids`、`impacted_population_ids`、`impacted_plan_ids`、`unaffected_*` |
| `build_snapshot`    | `{"operation","artifact"}`                                                                                                                  | `counts`（再計算値）、`matches_stored`、`mismatched_count_keys`                                                                           |
| `completion_check`  | `{"operation","artifact"}`                                                                                                                  | `status`（complete／incomplete／blocked）、`complete`、`open`（未完了の理由コードとID）、`approval_authenticity`                          |

いずれも構造・必須項目・状態規則の違反、未知キー、重複key、NUL、NaN、8 MiB超の入力は`status: blocked`、`valid: false`で閉じます。

### 完了条件（completion_check）

次をすべて満たす場合だけ`complete: true`です。

- 構造検証に通り、再計算した件数（分母＝予定population、取得readbackの合計）が`monitoring.counts`と一致する。
- 必須populationのすべてについて、readbackがあり`currentness: current`で、取得済は実行済み・結果`PASS`／`FAIL`、0件確認済みは`対象なし`。
- 開始・終了基準がすべて`達成`で、終了基準が1件以上ある。
- project risk・差異は`解決済み`／`受容済み`、是正処置は`完了`／`対応不要`。
- `approval.state`が`不要`、または`承認済み`で`record`がこのartifact_ref・scope・revisionに完全に束縛され、承認主体・role・証拠refが実値である。

完了判定は必須populationだけを対象にします。任意populationの未完了は完了を妨げませんが、`readback_missing`等として件数に残ります。対象外の免除機構はないため、母集団から外す場合は承認された改版で予定母集団から除きます。`completion_check`は源sourceの現在性を再確認しないため、`impact`の結果も併せて確認します。

### 検証境界

- `validate_readback`の`content_hash`は保存本文のcanonical bytesのSHA-256を照合するだけで、保存先のprovider・CAS・読戻しの真正性は`provider_authenticity: not_established_by_this_validator`です。
- `impact`の`current_source_refs`は呼出し側の供給した証拠で、source ownerのraw結果や現在版そのものを読み直しません。供給が無い、空、形式不正、同一sourceの競合revisionは`unknown`（fail-closed）になります。
- 承認の認証主体は検証しません。承認済みの`approval_authenticity`は`not_established_by_this_validator`です。承認主体・役割・証拠refが実値であることだけを形式として確認します。
- source ownerの取得手段、承認の認証方式、保存先kindは本Skillでは未選定です。これらが定まるまで、完了の証拠は呼出し側の提供する証拠の束縛と整合性に限られます。
