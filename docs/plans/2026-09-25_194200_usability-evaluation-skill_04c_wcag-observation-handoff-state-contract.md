# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、`wcag-conformance-evaluation → qa-workflow → usability-inspection → qa-workflow → wcag-conformance-evaluation resume` のformal observation handoffについて、workflow stateへ永続化する物理契約、CAS更新順序、claim / shared resource lifecycle、再実行・重複return・stale originの扱い、resume条件を固定します。

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

## 1. owner

`wcag-conformance-evaluation` はlive observationが必要なsample / process / requirement、observation request、resume operationを確定し、formal artifact内で `HANDOFF-001` からartifact-local refを生成します。

`qa-workflow` は永続化、mutable operation identity / claim、resource reservation、returned result closure、reservation release、resume可否を所有します。

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

`claim_mutable_operation()` は自身で `workflow_ref + operation_ref` をclaim pathへ使うため、workflow refをoperation refへ重複して入れません。同じorigin revision / handoff retryでは同じoperation ref、別origin revision / artifactでは別operation refです。LLMは生成しません。

## 3. physical state

handoffは `state.handoffs` にだけ保存します。

```json
{
  "workflow_ref": "opaque UUID",
  "schema_version": "1",
  "state": {
    "handoffs": [
      {
        "handoff_ref": "HANDOFF-001",
        "handoff_kind": "wcag-observation",
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
            "process_ref": null,
            "requirement_ref": "...",
            "observation_request_ref": "..."
          }
        ],
        "returned_results": [
          {
            "observation_key": {
              "sample_ref": "...",
              "process_ref": null,
              "requirement_ref": "...",
              "observation_request_ref": "..."
            },
            "result_ref": "...",
            "result_revision": "...",
            "supersedes_result_ref": null
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

`expected_observations` はformal helperがmaterializeした集合だけを受け取ります。`returned_results.observation_key` はimmutable result本文からhelperが導出しexpected keyと照合します。raw observation / screenshot / DOMはstateへ複製しません。

status:

- `pending`: CAS保存済み、owner未開始
- `in-progress`: claim / required reservation取得済み、refsをCAS保存済み
- `returned`: result反映済みだがexpected closure / cleanup / release / origin currentnessのいずれかが未closure
- `closed`: expected-current-valid-returned、origin currentness、cleanup、required reservation releaseを閉じたstateをCAS保存済み
- `blocked`: required operation / cleanup / release / updateを安全に完了できない
- `stale`: origin revisionが変わり旧revisionへresume不可

## 4. create

1. formal helperがhandoff ref、origin、resume operation、expected集合をmaterializeする。
2. qa-workflow helperがhandoff identity / operation refを導出する。
3. current stateとstorage-provided `state_revision` を読む。
4. origin currentnessとduplicate identity conflictを検証する。
5. `state.handoffs[]` へ `pending` をnative CASで保存する。
6. CAS不可ならbrowserへ進まず `blocked`。

## 5. start / acquire

browser開始前の順序を固定します。

1. operation refでclaim取得。
2. required shared resourceを `resource_ref` canonical sort順で取得。
3. claim ref / revisionとreservation rowsを入れて `in-progress` をCAS保存。
4. ここまで完了した場合だけ最初のmutable browser action。

resource途中失敗または `in-progress` CAS失敗ではbrowserを開始しません。取得済みproject-local reservationは取得と逆順に `release_shared_resource()` へ渡し、external reservationは既存provider契約へ従います。

全reservation release確認後だけ、owner `not_started` / cleanup確認済みとして `recover_claim()` を使えます。安全に回収できなければ `blocked` とし別claimでretryしません。

## 6. return

resultはhandoff / origin、observation request、sample、process、requirement、result ref / revision、evidence、currentness dependency、owner execution state、cleanup、previous / supersedes relationを保持します。

qa-workflowはreturn時にcurrentness / identityを検証し、observation keyをscript導出してCAS反映します。

同じimmutable `result_ref + revision` はidempotent no-opにできます。同一expected observationへ複数current resultがある場合は明示 `supersedes_result_ref` で一意に閉じなければ `blocked` です。return CAS失敗ではbrowserを再実行せず、同じimmutable resultを最新stateへ再適用できる場合はそれを優先します。

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

## 9. stale origin

origin revisionが変わった旧handoffは `stale` です。owner開始済みならcurrent execution / cleanupを確認してrequired reservationを安全にreleaseし、開始前なら§5のrecoveryを使います。旧resultはhistorical evidenceとして保持できますが旧revisionへresumeしません。新revisionにはnew handoffをmaterializeします。

## 10. standalone

qa-workflowを利用できない真のstandalone環境では第二state storeを作りません。required current evidenceがない場合は該当scopeを `blocked` にします。

## 11. deterministic fixture

- outer envelope `schema_version=1` + `state.handoffs`
- template / helper physical shape一致
- same `HANDOFF-001` + different origin/revision → different operation ref
- same origin/revision/handoff retry → same operation ref
- pending CAS / missing revision / conditional write不可
- duplicate identity / origin mismatch
- claim conflict → browser未開始
- resource canonical acquisition order
- resource途中失敗 → acquired reservation逆順release → safe claim recovery
- `in-progress` CAS conflict → browser未開始 + release / recovery
- recovery不能 → blocked
- immutable result → observation key導出 / mismatch reject
- partial return → close-ready false
- exact duplicate / conflicting result / explicit supersedes
- cleanup前 / release前 → close-ready false
- normal completion → reverse release
- release failure / revision conflict → blocked
- close-ready → closed CAS → re-read → may-resume
- closed CAS failure → may-resume false、browser再実行なし
- stale origin / stale result → resume不可

## 12. 完了条件

- production helperとtemplateのphysical shapeが一致
- `state.handoffs` とouter `schema_version=1` の責務が固定
- artifact-local handoff ref単独をworkflow identity / operation refに使わない
- operation identityをscript導出
- create / start / return / release / closeがnative CAS前提
- resource acquire / rollback / normal releaseが閉じる
- started claimをnormal completionでreleaseせず、not-started recoveryだけ既存helperを使う
- result key / currentness / duplicate / supersedesをLLM判断にしない
- `close_ready → closed CAS → re-read → may_resume` 固定
- stale originへresumeしない
- CAS / recovery failureをbrowser rerunで隠さない
- standalone用第二storeを作らない
