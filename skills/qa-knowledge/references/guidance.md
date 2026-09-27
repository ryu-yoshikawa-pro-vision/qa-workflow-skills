# QA Knowledge guidance

## Owner routing first

| Candidate | Owner |
| --- | --- |
| 期待挙動 / specification | `spec-analysis` |
| 新規Product Risk / test focus | `test-analysis` |
| current UI / accessible name / live behavior | `test-target-inspection` |
| TR / TCN / CI / TCにformalizeする判断 | 該当design Skill |
| execution failure原因 | 該当analysis Skill |
| 既存ownerへ自然に置けず、複数workflowに継続再利用する知識 | `qa-knowledge` entry候補 |

Finding / Observationの存在だけでentryを作りません。source、scope、適用environment / version、currentness dependency、再利用価値、existing entryとのidentity関係を確認できない場合はcandidateを元artifact / Follow-upに残します。

## Entry lifecycle

Entry bodyは1ファイル / 1独立revisionのproject-local artifactです。body fieldは`entry_ref`, `identity`, `kind`, `content`, `scope_refs`, `applicability`, `provenance`, `currentness_dependencies`, `last_verified`, `state`, `replacement_ref`, `related_qa_refs`です。`replacement_ref`は置換済みentryで使い、それ以外はnullにします。templateの`schema_version`も維持します。secret値を含めません。

`entry_revision`はbody fieldではなく、保存先 / helperが返すstorage metadataです。callerはworkflow / Activity側で保持し、update / revalidationのexpected revisionや、保存先が対応する場合のhistorical readに使います。entry templateへ書き込みません。

`provenance`は知識を得たsource refs / revisions、`currentness_dependencies`は今後の再利用前に変化を確認すべきrefs / revisionsです。2種類のrefは別々に保持します。

- 新規create: completeなroot snapshotでidentityを比較し、canonical stable targetへatomic create-if-absentします。同じtargetがあれば現entryを読み、同一identityなら同entryのupdate / revalidationへ進みます。
- 同一identityのupdate / revalidation: same `entry_ref`を保ち、entry artifact自身のexpected revisionでnative conditional updateします。
- dependency mismatch: 保存状態がまだ`要再検証`に更新されていなくても、current判断から除外します。保存できる場合だけentry revisionを条件に更新します。
- replacement: semantic identity変更、分割、適用範囲分離、既存entry統合に限ります。old/newを一括安全に反映できない保存先ではblockします。
- lookup / history: fixed rootをdeterministicに列挙し、scope / kind / environment / version / state / currentnessで絞ります。listing incompleteならcompletenessをfalseにします。`有効`かつcurrentなentryだけがcurrent recommendationです。

## Storage safety

Create-if-absent / conditional updateのcapabilityは保存先の実際のatomic operationに結び付いている必要があります。revisionを先に読み比較してからunconditional writeする処理はCASではありません。same-entry conflictでは保存せず、current entryを読み直して意味判断をやり直します。別entry更新だけならtarget entry revisionが不変と確認できる場合に限り影響なしとします。

required deterministic helperが使えない、root listingが不完全、historical artifactを再取得できない、またはstorage conditionが提供されない場合はfail-closedにし、成功したような出力を生成しません。
