# テスト計画artifact契約

## Identity・version

ownerは`test-management`です。保存先発行の`artifact_ref`、不透明な`revision`、scope、計画上の対象build／環境／期間を保持します。`PLAN-001`、`ACT-001`、`CA-001`等のIDはartifact系列内だけで安定し、global ID counterを使いません。各改版は旧ref／revisionと差分を参照します。

## 計画・source inventory

計画行はplan-local ID、`<artifact_ref>#<local_id>@<revision>`形式のQA requirement／architecture ref、level／type、suite・順序、担当・見積工数・資源・開始／終了基準を持ちます。利用可能なfixtureでowner・local ID・artifact ref・revision・scopeを照合します。入力source行にはcurrentness・取得状態・必要な承認状態と証拠refを保持し、確定中の計画が参照する入力だけを検証します。無関係なscopeのstale sourceで計画全体を一律に失効させません。計画母集団と実取得を同じ行に上書きせず、次の2つの表で保持します。

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
