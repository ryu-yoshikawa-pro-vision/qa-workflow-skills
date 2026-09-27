# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、`wcag-conformance-evaluation → qa-workflow → usability-inspection → qa-workflow → wcag-conformance-evaluation resume` のformal observation handoffについて、workflow stateへ永続化する物理契約、CAS更新順序、再実行・重複return・stale originの扱い、resume条件を固定します。

`wcag-conformance-evaluation` のmethodology / sample owner境界は `_04b_wcag-conformance-evaluation-workflow-integration.md`、PR #13のworkflow state / concurrency基盤はmerge後のcurrent `skills/qa-workflow/assets/workflow-state-template.md` と `skills/qa-workflow/scripts/artifact_graph.py` を正本とします。

PR #13のPlan時点の抽象論へ依存せず、2026-09-27確認時点のPR #13 head `5d491b4ec75f941eea2f173d8363039f83250a27` が持つ次の既存契約を再利用します。

- `workflow_ref`ごとのstate artifact
- storage-provided `state_revision` とnative atomic conditional write
- `claim_mutable_operation()` によるpre-start claim
- shared resource reservation
- claim / reservation recovery時のowner execution / cleanup確認

新しいworkflow store、lock service、queue、汎用orchestration frameworkは追加しません。

## 1. handoff owner

`wcag-conformance-evaluation` は、live observationが必要なsample / process / requirementとresume operationを確定し、handoff artifact-local refを生成します。

`qa-workflow` はhandoff recordの永続化、mutable operation claim、必要なresource reservation、returned result closure、formal evaluationへのresume可否を所有します。

`usability-inspection` はbrowser / session ownerとして、handoffで要求されたscopeだけを観測し、immutable resultを返します。sample追加、target WCAG version / level変更、formal requirement universe変更は行いません。

## 2. workflow stateへ追加するfield

PR #13 merge後のworkflow state recordへ、次のlogical fieldを追加します。current implementationの外側の名称変更があっても、ここで固定する意味とrequired fieldは落としません。

```json
{
  "handoffs": [
    {
      "handoff_ref": "HND-001",
      "handoff_kind": "wcag-observation",
      "origin": {
        "skill": "wcag-conformance-evaluation",
        "artifact_ref": "...",
        "artifact_revision": "...",
        "resume_operation": "..."
      },
      "owner_skill": "usability-inspection",
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
          "result_ref": "...",
          "result_revision": "...",
          "supersedes_result_ref": null
        }
      ],
      "operation_claim_ref": null,
      "resource_reservation_refs": [],
      "status": "pending",
      "blocked_reason": null
    }
  ]
}
```

`handoff_ref` はformal evaluation artifact内のartifact-local refです。`qa-workflow` が別IDへ変換しません。

`expected_observations` は `wcag-conformance-evaluation` のproduction helperがsample / process / requirement / observation requestからmaterializeした集合だけを受け取ります。LLMがworkflow state用に期待集合を再構築しません。

`returned_results` はimmutable result refを保持します。観測本文やraw screenshot / DOMをworkflow stateへ複製しません。

status:

- `pending`: handoff recordをCASで保存済み、owner未開始
- `in-progress`: mutable operation claim / 必要なresource reservationを取得し、owner開始をstateへCAS保存済み
- `returned`: 1件以上のimmutable resultを受領したが、expected-returned closureまたはcurrentnessが未closure
- `closed`: currentなexpected observation集合をcurrent valid returned result集合が完全に満たし、origin revisionもcurrent
- `blocked`: required operation / result / cleanup / state updateを安全に完了できない
- `stale`: originating evaluation / revisionが変わり、このhandoffから元revisionへresumeできない

## 3. handoff作成

1. `wcag-conformance-evaluation` のproduction helperが `handoff_ref`、origin artifact / revision、resume operation、expected observation集合をmaterializeする。
2. `qa-workflow` はcurrent workflow stateと `state_revision` を読む。
3. origin artifact / revisionがcurrentで、同じ `handoff_ref` の矛盾したrecordがないことを確認する。
4. handoff recordを `pending` としてnative atomic conditional writeで保存する。
5. conditional writeを利用できない場合はbrowser操作へ進まず `blocked` にする。read後比較 + 無条件writeをCAS扱いしない。

formal Skillがhandoff artifactを作っただけではbrowser操作を開始しません。workflow stateへの `pending` 永続化が完了してからowner開始準備へ進みます。

## 4. owner開始と二重実行防止

`qa-workflow` はhandoffごとに、browser操作開始前にPR #13の既存coordination helperを使用します。

1. `operation_ref = handoff_ref` としてmutable operation claimを取得する。
2. browser / test account / test data等がshared resourceなら、既存external reservationまたはPR #13のresource reservationを取得する。
3. claim / reservation refを含めてhandoffを `in-progress` へCAS更新する。
4. ここまで完了した場合だけ `usability-inspection` の最初のmutable browser actionを許可する。

claim取得後にstate CASが競合した場合はbrowserを開始しません。owner未開始とcleanupを確認したうえでPR #13のconditional release / recovery契約を使います。安全なreleaseを確認できなければ該当handoffをblockedにします。

既存claimがある場合、`operation_already_claimed` を「前回は失敗したはず」と推測して再実行しません。owner execution state、既存immutable result、cleanupを確認できるまでblockします。

## 5. returned result契約

`usability-inspection` resultは少なくとも次を保持します。

- `handoff_ref`
- originating evaluation artifact ref / revision
- observation request ref
- sample ref
- process ref（存在する場合）
- requirement ref
- result artifact ref / revision
- evidence refs
- environment / target / currentnessに必要なdependency
- cleanup result
- rerunの場合のprevious result ref / supersedes relation

`qa-workflow` はreturnを受けた時点で、PR #11 / #12のcurrentness契約とhandoff identityを検証してからworkflow stateへCAS反映します。

同じimmutable `result_ref + revision` の再送はidempotent no-opとして扱えます。

同一expected observationに複数のcurrent resultが存在する場合、明示的な `supersedes_result_ref` で一意なcurrent lineageへ閉じられなければ `blocked` とします。LLMが「新しい方」を時刻や並び順から推測して選びません。

return後のworkflow state CASが失敗しても、browserを直ちに再実行しません。同じimmutable result refを再適用できる場合はそれを優先し、previous execution / cleanup / result有無を確認できない場合はblockします。

## 6. expected-returned closure

`artifact_graph.py` の既存責務へ最小のdeterministic helperを追加し、別orchestration frameworkを作りません。

helperは少なくとも次を行います。

- expected observation keyのcanonicalization / deterministic sort
- returned result identity / supersedes lineage検証
- duplicate exact returnの除外
- expected set - current valid returned setの集合差分
- unexpected returned key検出
- origin artifact / revision一致確認
- returned result currentness確認
- cleanup未完了 / blocked result検出
- `may_resume` boolean導出

`may_resume=true` の条件はすべて必須です。

- handoff statusがclosure可能
- originating evaluation artifact / revisionがhandoff作成時と一致してcurrent
- expected observation集合の未充足が0
- unexpected current resultが0
- result lineage ambiguityが0
- required cleanupが成功または対象なし
- current workflow state updateがCASで保存済み

LLMは「全部返った」「同じevaluationへ戻れる」を判断しません。

## 7. origin revisionが変わった場合

handoff作成後にoriginating `wcag-conformance-evaluation` revisionが変わった場合、旧handoffは `stale` とします。

- 旧handoffのresultを旧revisionへresumeしない
- 旧resultはhistorical evidenceとして保持できる
- 新revisionが同じevidenceを再利用できるかはPR #11 freshnessと新しいformal evaluationのproduction helperで判定する
- 新revisionがobservationを必要とする場合はnew handoff refをmaterializeする

旧handoff recordを書き換えて新revisionのhandoffとして再利用しません。

## 8. standalone環境

`qa-workflow` を利用できない真のstandalone環境では、このworkflow state / CAS契約を代替する独自storeを `wcag-conformance-evaluation` 内へ作りません。

required current evidenceがInputにない場合はhandoff requirementを成果物へ出し、formal evaluationの該当scopeを `blocked` にします。

## 9. deterministic fixture

少なくとも次を固定fixtureで検証します。

- pending handoff作成
- missing state revision → blocked
- native conditional writeなし → blocked
- duplicate handoff ref / origin不一致拒否
- operation claim競合時にbrowser未開始
- claim後state CAS競合時の安全なrelease判断
- partial returnではresume不可
- expected集合完全returnでresume可
- exact duplicate returnのidempotent処理
- conflicting current return + supersedesなし → blocked
- explicit supersedesでcurrent result一意化
- stale origin revision → resume不可
- returned result stale → resume不可
- cleanup失敗 / 未確認 → resume不可
- state CAS失敗後にbrowserを自動再実行しない

## 10. 完了条件

- formal observation handoffの物理state schemaが一意
- handoff create / start / return / closeがnative CASを前提にする
- browser mutable operationの二重開始をexisting claimで防ぐ
- shared resourceはexisting reservation契約を再利用する
- expected-returned closureをdeterministic helperが導出する
- duplicate / conflicting returnをLLM判断にしない
- stale origin revisionへresumeしない
- CAS failureやrecovery不能をbrowser rerunで隠さない
- standalone用の第二のorchestration storeを作らない

