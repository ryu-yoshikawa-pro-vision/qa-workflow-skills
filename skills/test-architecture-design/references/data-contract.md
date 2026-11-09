# テストアーキテクチャartifact契約

## Identity・依存

ownerは`test-architecture-design`です。成果物は保存先発行の不透明な`artifact_ref`・`revision`・`scope`を持ち、各入力はowner/source ref・revision・scope・currentnessとともに記録します。`ARCH-001`等のassignment IDはartifact系列内のstable IDであり、global ID registryやcounterを作りません。

## Assignment

各割当は少なくとも次を持ちます。

- assignment ID、対象refと対象種別、QA requirement ref
- level、type、方式、検証分担、method責任
- environment、data、runner／tool、manual／automated、観測／測定方法
- 根拠ref・revision、選択根拠（明示指定／承認architecture／既定値／未解決）
- constraint、readiness、owner、状態、影響する下流ref

同じtargetに複数levelを割り当てられます。重複判定はartifact ref・scope内の同じtarget／level／type／responsibilityに限定します。

QA requirement refは`<artifact_ref>#<local_id>@<revision>`で固定し、単独のlocal IDだけでcurrentnessを推定しません。要求artifactが未取得・未確定なら、architecture assignmentを確定せずblocked／未確定にします。

## 状態・承認・currentness

割当／artifactの状態（草案、承認済み、要再確認、blocked、置換）を、実行stateと混ぜません。承認済みは信頼された承認元が同じartifact ref・revision・scopeを許可したときだけです。revisionが変わったら旧承認を再利用しません。source ref／revisionを再取得できなければ`unknown`、一致しなければ`stale`です。

`test-analysis`の既定レベルから別levelが承認された場合、その割当に依存するProduct Risk／TR／TCN／CI／TCだけを再確認へ戻します。無関係なcurrent成果物を失効させません。

## 保存とhandoff

保存はsource ownerまたは選択済みproviderのnative create-if-absent／CAS・履歴・独立readbackが確認できる場合だけ完了です。Aのclaim helperの存在だけで実保存・認証・承認は成立しません。未接続なら草案を返し、永続更新をblockedにします。

handoffはowner／artifact ref／revision／scope、assignment IDs、承認とsource refs、再評価対象、保持するcurrent成果物、blocked理由・resume ownerを含みます。
