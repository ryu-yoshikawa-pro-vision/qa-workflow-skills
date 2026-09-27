# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、`wcag-conformance-evaluation → qa-workflow → usability-inspection → qa-workflow → wcag-conformance-evaluation resume` のformal observation handoffについて、workflow stateへ永続化する物理契約、CAS更新順序、claim / shared resource lifecycle、再観測、重複return、stale origin、resume条件を固定します。

workflow state / concurrency基盤はPR #13 merge後current mainの `skills/qa-workflow/scripts/artifact_graph.py`、`assets/workflow-state-template.md`、`references/guidance.md` を正本とします。

production helperが実際に扱うpersisted documentは次です。

```json
{
  "workflow_ref": "<uuid>",
  "schema_version": "1",
  "state": {
    "...": "workflow payload"
  }
}
```

`state_revision` は保存先 / read結果が返すconditional write tokenであり、このdocument内へ複製しません。

current `workflow-state-template.md` は説明例でpayload fieldをtop-levelに示しているため、PR #14実装時はhandoff追加前にtemplateをproduction helperのshapeへ同期します。今回の追加は既存 `schema_version="1"` の `state` payloadへ `handoffs` を追加するadditive extensionとし、outer envelopeを変更しません。別state version、store、lock service、queue、汎用orchestration frameworkは追加しません。

既存の `claim_mutable_operation()`、`recover_claim()`、`reserve_shared_resource()`、`release_shared_resource()` を再利用します。

### canonical E2Eで使うtest-only CAS provider

current `artifact_graph.py` のlocal filesystem経路はinitial create-if-absentまでを提供し、`state_revision` はCAS conditionではありません。したがってrepository-controlled canonical E2Eでhandoffを `pending → in-progress → returned → closed` まで通すために、test harnessだけで使う `tests/skills/evals/deterministic/wcag_handoff_cas_provider.py` を追加します。

このproviderはPython標準ライブラリの `sqlite3` だけを使い、一時DB内で次を提供します。

- workflow state initial create: `workflow_ref` unique keyへのtransactional insert
- workflow state read: current state + provider revision token取得
- workflow state conditional write: transaction内でcurrent revision一致を確認して更新し、一致しない場合はconflict。read → 比較 → 無条件writeをCASとして扱わない
- canonical E2E用external reservation acquire: `resource_ref` unique key、owner workflow ref、provider revisionをtransactionalに保存
- external reservation conditional release: owner / expected provider revision一致を同一transactionで確認してrelease
- concurrent writer fixtureで同じexpected revisionから成功するworkflow state writeが1件だけになること
- stale expected revision / wrong owner / duplicate reservationを明示conflictへ閉じること

provider revisionはtest provider内部の単調増加revisionまたは同等のtransaction内更新tokenを使い、productionのlocal exact-content SHAをCAS tokenへ読み替えません。

canonical E2EではSQLite reservationを既存 `reserve_shared_resource()` のexternal reservation経路へ渡します。そのためPR #14では同helperへoptional `external_reservation_revision` を1引数だけ追加し、`external_reservation + external_reservation_acquired=true` の場合は非空revisionを必須としてreturned reservation rowへそのまま保持します。project-local reservation経路、claim path、public storage abstractionは変更しません。正常release時は既存 `release_shared_resource()` がowner / expected revision / cleanupを検証して `conditional_release_required` を返した後、test providerがそのexpected revisionで実releaseします。

このproviderはcanonical E2E / deterministic test専用です。production Skill package、Project Context、routingへSQLite adapterやgeneric storage interfaceを追加しません。`artifact_graph.py` の変更は上記external reservation revisionの伝播だけです。productionでは従来どおりworkflow state / external reservationの保存先がnative atomic conditional write / releaseを提供する場合だけ更新・解放を実行し、提供しない場合はfail-closedにします。

`claim_mutable_operation()` はcurrent mainどおりlocal filesystem create-if-absentを使い、test-only SQLite providerへ移しません。current local claim storageにはnative atomic conditional releaseがないため、`recover_claim()` の成功をcanonical E2Eの要件にしません。pre-start failureでclaim release能力がない場合は `atomic_claim_release_unavailable` で安全にblockedとなることを負系fixtureで確認します。normal completionではstarted claimを履歴として残す既存契約のため、この制約はhappy-path closureを妨げません。

## 1. owner

`wcag-conformance-evaluation` はlive observationが必要なsample / variation / process / requirement、observation request、resume operationを確定し、formal artifact内で `HANDOFF-001` からartifact-local refを生成します。

`qa-workflow` は永続化、mutable operation identity / claim、resource reservation、returned result closure、reservation release、再観測handoff lineage、resume可否を所有します。

`usability-inspection` はbrowser / session ownerとしてhandoff scopeだけを観測し、immutable resultを返します。

## 2. handoff identity

`handoff_ref` はartifact-localです。同一workflow内の別evaluation / revisionで同じ `HANDOFF-001` が発生し得るため、単独でworkflow-level identityやoperation identityにしません。

handoff identity:

```text
(origin.artifact_ref, origin.artifact_revision, handoff_ref)
```

`artifact_graph.py` へ追加するhelperが次を導出します。

```text
operation_ref =
  "wcag-observation:" +
  sha256(canonical_json({
    origin_artifact_ref,
    origin_artifact_revision,
    handoff_ref
  }))
```

`claim_mutable_operation()` は自身で `workflow_ref + operation_ref` をclaim pathへ使うため、workflow refをoperation refへ重複して入れません。

同じhandoff identityについて、CAS再試行、同じimmutable resultの再適用、resume判定の再実行は同じ `operation_ref` を使います。**browserを一度開始したhandoffを同じidentityで再実行しません。**

browser再観測が必要な場合は§9の再観測契約に従って新しい `handoff_ref` をmaterializeし、新しい `operation_ref` を導出します。LLMはhandoff ref / operation refを手作成しません。

## 3. physical state

handoffは `state.handoffs` にだけ保存します。

```json
{
  "workflow_ref": "opaque UUID",
  "schema_version": "1",
  "state": {
    "handoffs": [
      {
        "handoff_ref": "HANDOFF-002",
        "handoff_kind": "wcag-observation",
        "retry_of_handoff_ref": "HANDOFF-001",
        "origin": {
          "skill": "wcag-conformance-evaluation",
          "artifact_ref": "...",
          "artifact_revision": "...",
          "resume_operation": "..."
        },
        "owner_skill": "usability-inspection",
        "operation_ref": "wcag-observation:sha256...",
        "expected_observations": [
          {
            "sample_ref": "...",
            "variation_ref": "...",
            "process_ref": null,
            "requirement_ref": "...",
            "request_kind": "wcag-machine-probe | semantic-observation",
            "observation_request_ref": "..."
          }
        ],
        "returned_results": [
          {
            "observation_key": {
              "sample_ref": "...",
              "variation_ref": "...",
              "process_ref": null,
              "requirement_ref": "...",
              "request_kind": "wcag-machine-probe | semantic-observation",
              "observation_request_ref": "..."
            },
            "result_ref": "...",
            "result_revision": "...",
            "previous_result_ref": "...",
            "supersedes_result_ref": "..."
          }
        ],
        "operation_claim_ref": null,
        "operation_claim_revision": null,
        "resource_reservations": [
          {
            "resource_ref": "...",
            "reservation_ref": "...",
            "provider": "existing-external-reservation | project-local",
            "reservation_revision": null,
            "status": "reserved | released"
          }
        ],
        "status": "pending",
        "blocked_reason": null
      }
    ]
  }
}
```

初回handoffの `retry_of_handoff_ref` は `null` です。

`expected_observations` はformal helperがmaterializeした集合だけを受け取ります。`request_kind=wcag-machine-probe` の `observation_request_ref` はformal artifact内のtyped requestへ解決し、そこに `machine_probe_key` とtarget / population identity inputを保持します。stateへprobe payloadやbrowser instructionを複製しません。`returned_results.observation_key` はimmutable result本文からhelperが導出し、request kindを含めてexpected keyと照合します。raw observation / screenshot / DOMはstateへ複製しません。

status:

- `pending`: CAS保存済み、owner未開始
- `in-progress`: claim / required reservation取得済み、refsをCAS保存済み
- `returned`: result反映済みだがexpected closure / cleanup / release / origin currentnessのいずれかが未closure
- `closed`: expected-current-valid-returned、origin currentness、cleanup、required reservation releaseを閉じたstateをCAS保存済み
- `blocked`: required operation / cleanup / release / updateを安全に完了できない
- `stale`: origin revisionが変わり旧revisionへresume不可

## 4. create

1. formal helperがhandoff ref、origin、resume operation、expected集合、必要なら `retry_of_handoff_ref` をmaterializeする。
2. qa-workflow helperがhandoff identity / operation refを導出する。
3. current stateとstorage-provided `state_revision` を読む。
4. origin currentness、duplicate identity conflict、retry lineageを検証する。
5. `state.handoffs[]` へ `pending` をnative CASで保存する。
6. CAS不可ならbrowserへ進まず `blocked`。

## 5. start / acquire

browser開始前の順序を固定します。

1. operation refでclaim取得。
2. required shared resourceを `resource_ref` canonical sort順で取得。
3. claim ref / revisionとreservation rowsを入れて `in-progress` をCAS保存。
4. ここまで完了した場合だけ最初のmutable browser action。

resource途中失敗または `in-progress` CAS失敗ではbrowserを開始しません。取得済みreservationは取得と逆順にreleaseします。project-local reservationはcurrent helper契約、external reservationはprovider revision付きで `release_shared_resource()` のdecisionを通した後にprovider-native conditional releaseを実行します。

全reservation release確認後だけ、owner `not_started` / cleanup確認済みとして `recover_claim()` を呼びます。claim保存先がnative atomic conditional releaseを提供する場合だけreturned expected revisionで実releaseできます。current local claim storageは提供しないため `recover_claim()` は `atomic_claim_release_unavailable` でblockedとなり、browser未開始の安全な停止として扱います。canonical negative fixtureはこのblockedをPASS条件とし、成功するclaim recoveryを捏造しません。

## 6. return

resultはhandoff / origin、observation request、sample、variation、process、requirement、result ref / revision、evidence、currentness dependency、owner execution state、cleanup、previous / supersedes relationを保持します。

qa-workflowはreturn時にcurrentness / identityを検証し、observation keyをscript導出してCAS反映します。

同じimmutable `result_ref + revision` の再送はidempotent no-opにできます。これはbrowser再観測ではありません。

同一expected observationに複数current resultがある場合は明示 `supersedes_result_ref` で一意に閉じなければ `blocked` です。return CAS失敗ではbrowserを再実行せず、同じimmutable resultを最新stateへ再適用できる場合はそれを優先します。

## 7. normal release

owner executionが `complete` かつrequired cleanup成功 / 対象なしの後にresourceを解放します。

1. 最新state再読込。
2. current reservation rows取得。
3. project-local reservationを取得の逆順で `release_shared_resource()`。
4. external reservationはprovider既存release契約。
5. release成功を `status=released` としてCAS保存。
6. required reservationに `reserved` が残る、release revision競合、owner / cleanup未確認なら `blocked`。

実際にownerが開始されたclaimは正常完了後も二重開始防止履歴として残します。`recover_claim()` はowner `not_started` の開始前失敗だけです。

## 8. closure / resume

`artifact_graph.py` へ追加するhelperはhandoff identity / operation ref、expected / returned key、result identity / supersedes、duplicate、set difference、unexpected result、origin / result currentness、cleanup、required reservation releaseから `close_ready` を導出します。

`close_ready=true` にはorigin current、未充足0、unexpected 0、lineage ambiguity 0、cleanup成功 / 対象なし、required reservation全release / 不要が必要です。

順序:

1. 最新state / revisionから `close_ready` 計算。
2. `closed` stateをnative CAS保存。
3. CAS成功後にstate再読込。
4. `handoff_resume_decision` がsame identityのclosed、origin / result lineage current、cleanup / release closureを再検証。
5. 全条件成立時だけ `may_resume=true`。
6. may_resume時だけorigin artifact / revision / resume operationへresult refsを返す。

`may_resume` をclosed CAS前のstateへ保存する設計にはしません。

## 9. browser再観測

一度 `in-progress` へ入りbrowserを開始したhandoffは、同じhandoff identityで再実行しません。started claimを残す既存PR #13契約と矛盾させないためです。

再観測が必要になる例:

- returned resultがfreshness検証でstale
- evidenceが不足し、同じ対象へ追加または再観測が必要
- previous resultをsupersedeする新しい観測が必要
- browser開始後にowner executionが失敗し、安全なcleanupは完了したが結果を再取得する必要がある

再観測時:

1. old handoff / claim / resultを履歴として保持する。
2. formal helperが同じorigin revision内で次のartifact-local handoff refを決定論的に採番する。
3. new handoffへ `retry_of_handoff_ref=<old handoff ref>` を設定する。
4. 必要なexpected observationだけをnew handoffへmaterializeする。
5. new handoff refを含むidentityからnew operation refを導出する。
6. §4〜§8を新しいclaim / reservationで実行する。
7. new resultがold current resultを置き換える場合はresult側の `previous_result_ref / supersedes_result_ref` でlineageを閉じる。

同じold handoffから同じ目的の再観測handoffを複数作らないよう、helperは `retry_of_handoff_ref + expected observation set + origin revision` のcurrent open lineageを検証します。既にcurrentなpending / in-progress / returned再観測handoffがある場合、新しいhandoffを追加せずその状態を返します。

## 10. stale origin

origin revisionが変わった旧handoffは `stale` です。owner開始済みならcurrent execution / cleanupを確認してrequired reservationを安全にreleaseし、開始前なら§5のrecoveryを使います。旧resultはhistorical evidenceとして保持できますが旧revisionへresumeしません。

新origin revisionで観測が必要なら、旧handoffをretryせず新revisionの通常handoffとしてmaterializeします。

## 11. standalone

qa-workflowを利用できない真のstandalone環境では第二state storeを作りません。required current evidenceがない場合は該当scopeを `blocked` にします。

## 12. deterministic fixture

- outer envelope `schema_version=1` + `state.handoffs`
- template / helper physical shape一致
- same `HANDOFF-001` + different origin/revision → different operation ref
- same handoff identityのCAS retry / immutable result再適用 → same operation ref、browser再開始なし
- started `HANDOFF-001` の再観測 → `HANDOFF-002` + new operation ref
- `retry_of_handoff_ref` lineage / duplicate current rerun抑止
- test-only SQLite providerでworkflow state initial create / successful CAS / stale revision conflict / concurrent same-revision writer 1件成功
- test-only SQLite external reservationでacquire / owner+revision付きconditional release / stale revision・wrong owner conflict
- `reserve_shared_resource()` external pathがprovider revisionを保持し、`release_shared_resource()` decision後にprovider-native releaseできること
- production local filesystemだけのpending CAS / missing revision / conditional write不可
- duplicate identity / origin mismatch
- claim conflict → browser未開始
- resource canonical acquisition order
- resource途中失敗 → acquired reservation逆順release → current local claim recoveryは `atomic_claim_release_unavailable` でblocked、browser未開始
- `in-progress` CAS conflict → browser未開始 + reservation release → current local claim recovery unavailableでblocked
- native claim conditional releaseを持たない環境で成功recoveryを仮定しない
- immutable result → observation key導出 / variation含むkey mismatch reject
- partial return → close-ready false
- exact duplicate return → idempotent no-op / browser再実行なし
- conflicting result / explicit supersedes
- cleanup前 / release前 → close-ready false
- normal completion → reverse release
- release failure / revision conflict → blocked
- close-ready → closed CAS → re-read → may-resume
- closed CAS failure → may-resume false、browser再実行なし
- stale result → new handoffで再観測
- stale origin →旧revisionへresume不可

## 13. 完了条件

- production helperとtemplateのphysical shapeが一致
- `state.handoffs` とouter `schema_version=1` の責務が固定
- artifact-local handoff ref単独をworkflow identity / operation refに使わない
- operation identityをscript導出
- browser開始済みhandoffを同じclaim identityで再実行せず、再観測はnew handoff lineageへ分離
- exact duplicate result再送とbrowser再観測を混同しない
- create / start / return / release / closeがnative CAS前提
- canonical E2Eはtest-only SQLite providerで実CASを通し、productionへtest provider / generic storage abstractionを持ち込まない
- resource acquire / reservation rollback / normal releaseが閉じる。canonical happy pathはtest-only external reservation providerで実releaseする
- started claimをnormal completionでreleaseしない。not-started recoveryは既存helperで能力判定し、current local claim storageでは安全にblockedとなることを確認する
- result key / currentness / duplicate / supersedesをLLM判断にしない
- `close_ready → closed CAS → re-read → may_resume` 固定
- stale originへresumeしない
- CAS / recovery failureをbrowser rerunで隠さない
- standalone用第二storeを作らない
