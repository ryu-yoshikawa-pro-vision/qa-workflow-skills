# テストアーキテクチャartifact契約

## Identity・依存

ownerは`test-architecture-design`です。成果物は保存先発行の不透明な`artifact_ref`・`revision`・`scope`を持ち、各入力はowner/source ref・revision・scope・currentness・取得状態とともに記録します。必要な承認状態と承認証拠refも保持し、承認済みsourceの承認証拠refと承認済みartifactの承認主体・role／承認証拠refに未設定・未確定・unknown等のplaceholderを認めません。`ARCH-001`等のassignment IDはartifact系列内のstable IDであり、global ID registryやcounterを作りません。

## Assignment

各割当は少なくとも次を持ちます。

- assignment ID、対象refと対象種別、QA requirement ref
- level、type、方式、検証分担、method責任
- environment、data、runner／tool、manual／automated、観測／測定方法
- 根拠ref・revision、選択根拠（明示指定／承認architecture／既定値／未解決）
- constraint、readiness、owner、状態、影響する下流ref

同じtargetに複数levelを割り当てられます。重複判定はartifact ref・scope内の同じtarget／level／type／responsibilityに限定します。

QA requirement refは`<artifact_ref>#<local_id>@<revision>`で固定し、利用できるsource inventory／fixtureでlocal ID、owner、scope、revisionを照合します。単独のlocal IDだけでcurrentnessを推定しません。要求artifactがstale・unknown・未取得・未承認なら、architecture assignmentを確定せずblocked／未確定にします。

依存sourceがstale・unknown・未取得の場合は、そのsourceに依存する割当だけを未確定にします。同じtargetでも独立したcurrent sourceに基づく割当は保持し、targetごとに既定値・承認済み割当・明示指定との整合を検証します。未確定の依存割当を含むartifactは承認済みとして確定しません。

## 状態・承認・currentness

割当／artifactの状態（草案、承認済み、要再確認、blocked、置換）を、実行stateと混ぜません。承認済みは信頼された承認元が同じartifact ref・revision・scopeを許可したときだけです。revisionが変わったら旧承認を再利用しません。source ref／revisionを再取得できなければ`unknown`、一致しなければ`stale`です。

`test-analysis`の既定レベルから別levelが承認された場合、その割当に依存するProduct Risk／TR／TCN／CI／TCだけを再確認へ戻します。無関係なcurrent成果物を失効させません。

## 保存とhandoff

保存はsource ownerまたは選択済みproviderのnative create-if-absent／CAS・履歴・独立readbackが確認できる場合だけ完了です。Aのclaim helperの存在だけで実保存・認証・承認は成立しません。未接続なら草案を返し、永続更新をblockedにします。

handoffはowner／artifact ref／revision／scope、assignment IDs、承認とsource refs、再評価対象、保持するcurrent成果物、blocked理由・resume ownerを含みます。

## 保存正本: canonical JSON packet

保存するartifactの正本は、`scripts/architecture_runtime.py`で検証するcanonical JSON packetです。`assets/output-template.md`のMarkdown表は、このpacketから描画する表示用の派生物であり、検証の正本にしません。Markdown表の列・判定語・既存validatorの契約は変更しません。

- 保存本文は`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`相当のUTF-8 canonical JSONです。保存本文のexact bytesのSHA-256を読み戻しhashとして照合します。
- `content_fingerprint`は、`content_fingerprint`自身を除いたpacket本文のcanonical SHA-256です。承認証拠は、このfingerprintと保存先revisionの両方に束縛します。
- 保存先revisionはpacket本文に記録しません（保存後にしか決まらないため）。読み戻し時に呼出し側が`expected_revision`として渡し、readbackのrevisionと照合します。

### packet の構造

| packetの項目                                                      | 対応するMarkdown表                       | 内容                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `schema`・`owner`・`artifact_ref`・`scope`・`content_fingerprint` | 成果物メタデータ                         | `schema`は`test-architecture-v1`、`owner`は`test-architecture-design`。状態は保存しません（完了判定の結果から導く）。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `sources[]`                                                       | 入力source・依存                         | `source_id`（`SRC-###`）、`role`（`qa_requirement`／`test_analysis`／`formal_design`／`other`）、owner・scope・artifact_ref・revision・content_hash（現在のsourceとの照合キー）、`acquisition`（取得済／部分取得／未取得／取得不能／0件確認済み／不明）、`approval_state`、`approval_evidence_ref`、`local_id`（`qa_requirement`のみ必須）。currentnessは保存せず`impact`で導きます。                                                                                                                                                                                                                                                        |
| `requirement_coverage[]`                                          | テストアーキテクチャ割当（要求との対応） | qa_requirement sourceごとに1行。`coverage`は割当済み／未割当／対象外。`assignment_ids`は参照する割当と完全一致させます。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `assignments[]`                                                   | テストアーキテクチャ割当                 | `assignment_id`（`ARCH-###`）、`target_ref`、`target_kind`、`qa_requirement_ref`（`<artifact_ref>#<local_id>@<revision>`）、`level`、`test_type`、`method`、`verification_responsibility`、`environment`、`data`、`runner_tool`、`automation`（自動／手動／混在／未確定）、`measurement`、`selection_basis`（明示指定／承認済みarchitecture／test-analysis既定値／未確定）、`basis_source_ids`、`source_ids`（依存source。QA要求sourceを必ず含む）、`approval_id`、`disposition`（確定／未承認案／blocked／対象外）、`readiness`（準備済み／未確定／blocked）、`exclusion_reason`、`downstream_refs[]`（kind: Risk／TR／TCN／CI／TC、ref）。 |
| `level_priority[]`                                                | レベル優先・競合                         | targetごとに`explicit_levels`・`approved_levels`・`default_levels`・`levels`・`decision`・`conflict_resolution`。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `constraints[]`                                                   | 非機能・環境制約                         | `constraint_id`（`CON-###`）、対象、測定方式、`threshold_source_id`、環境・データ、`readiness`、残る制約。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `open_items[]`                                                    | 未解決・blocked                          | `open_item_id`（`OPEN-###`）、対象ref、担当owner、state（未解決／blocked／解決済み／対象外）、再開条件。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `change_impacts[]`                                                | 変更影響・handoff                        | 変更ref・revision、影響scope、再確認するref、保持するref、resume owner、理由。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `history[]`                                                       | 履歴                                     | 版のcontent_fingerprint、置換元、変更理由、影響scope、再確認する依存。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

IDは成果物系列内で安定させ、global registryやcounterを作りません。`assets/packet-example.json`は、既定値の割当と承認済み割当（同一targetの2 level）を含む例です。

### level優先の規則

targetごとに、次の順で決めます。

1. `explicit_levels`（明示指定）があれば、それを使います。
2. なければ`approved_levels`（承認済みarchitecture）を使います。
3. どちらもなければ`default_levels`（`test-analysis`既定のシステムテスト）を使います。
4. `explicit_levels`と`approved_levels`が両方あり集合が異なる場合は競合です。`decision`は`未確定`、`conflict_resolution`を必須にし、当該targetの割当を確定扱いにしません。

`levels`は決定された集合と一致させ、同じtargetの割当のlevel集合と一致させます。複数levelを残すには、すべてのlevelを割当として保持します。前版で2 level以上あったtargetから1 levelを落とす変更は、`validate`に前版`previous_artifact`を渡すと`level_collapsed`で不可になります。

### 承認と完了

- `approval_id`を持つ割当は、呼出し側が`completion_check`に渡す`approval_evidence`（`approval_id`・artifact_ref・scope・content_fingerprint・revision・assignment_ids・approver・approver_role・evidence_ref・state）と束縛します。承認が要るのは、`selection_basis`が承認済みarchitectureの割当、または既定値（`default_levels`）と異なるlevelの割当です。
- 完了に必要な束縛は、artifact_ref・scope・content_fingerprint・revision（`expected_revision`）・割当IDの一致、stateが`承認済み`、approver・approver_role・evidence_refが非placeholderであることです。
- LLM出力の`承認済み`表記だけでは承認証拠にしません。承認証拠が無い、旧revision、別artifact、別scope、別割当向けの場合は`complete: false`です。
- 未承認案（`disposition: 未承認案`）は確定割当に含めず、`unapproved_assignment_ids`として分離します。未解決（`未確定`の目標、`blocked`の割当、未解決のopen item、未割当の要求、準備未完了の確定割当）は完了を阻みます。

### 検証の境界

`validate`・`validate_readback`・`impact`・`completion_check`が確認するのは、packetの構造と内部整合、呼出し側が渡した読み戻し・現在source・承認証拠の束縛だけです。次は確立しません。

- 承認主体の本人性・権限、承認証拠の真正性（`approval_authenticity`は常に`not_established_by_this_validator`）。
- 保存先のcreate-if-absent／CAS、履歴、provider revisionの真正性（`provider_authenticity`・`provider_cas`）。
- source ownerからの現在revisionの取得手段。取得できない場合は`unknown`として扱います。

認証主体・保存先kind・承認方式は未選定であり、このcontractは決めません。

### 操作（`scripts/architecture_runtime.py`、JSON stdin → JSON stdout）

| operation           | 入力                                                                                                                    | 主な出力                                                                                                                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate`          | `artifact`、任意で`previous_artifact`                                                                                   | `valid`、`status`（valid）、`content_fingerprint`、`assignment_ids`。構造・必須項目・優先順位・複数level・要求対応・承認区別・下流参照を検査します。                                                    |
| `validate_readback` | `candidate_artifact`、`readback`（owner・scope・artifact_ref・revision・content_hash）、`expected_revision`（必須）     | `readback_matches`または`blocked`。`storage_content_sha256`、`candidate_fingerprint`、`provider_authenticity`。                                                                                         |
| `impact`            | `artifact`、`current_source_refs`（owner・scope・artifact_ref・revision・content_hash の配列。欠落・型不正は`unknown`） | `current`／`incomplete`／`unknown`。`stale_source_ids`、`unknown_source_ids`、`unconfirmed_*`、`impacted_assignment_ids`、`retained_assignment_ids`、`reconfirm_refs`。                                 |
| `completion_check`  | `artifact`、任意で`expected_revision`、`approval_evidence`（配列）                                                      | `complete`（bool）、`status`（complete／incomplete）、`confirmed_assignment_ids`、`approved_assignment_ids`、`unapproved_assignment_ids`、`blocked_assignment_ids`、`issues`、`approval_authenticity`。 |

エラーは`status: blocked`、`valid: false`と安定した`issues[].code`で返します。`completion_check`のエラーは`complete: false`です。入力は16MiB以下、各配列は500行以下、未知のキー・重複キー・NaN・NULは拒否します。scriptは外部通信とファイル書込みをしません。
