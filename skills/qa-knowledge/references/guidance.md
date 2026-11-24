# QA Knowledge guidance

## Owner routing first

| Candidate                                                 | Owner                    |
| --------------------------------------------------------- | ------------------------ |
| 期待挙動 / specification                                  | `spec-analysis`          |
| 新規Product Risk / test focus                             | `test-analysis`          |
| current UI / accessible name / live behavior              | `test-target-inspection` |
| TR / TCN / CI / TCにformalizeする判断                     | 該当design Skill         |
| execution failure原因                                     | 該当analysis Skill       |
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
- identity / scope: `identity.kind` / `identity.scope_refs`はentry直下の`kind` / `scope_refs`と値・順序まで一致させます。create / read / update / replacement / revalidation / lookupで同じ検証をし、不一致entryは自動修正・再採番・別scope流用をせず拒否して正本ownerへ戻します。
- 部分lookup: 適用範囲が確実に異なるentryの依存source取得不能で検索全体を止めません（診断情報のみ）。適用範囲を判断できないentry（identity破損・scope不明・ref重複・読取不能）とroot列挙の失敗・打切りは`incomplete`にします。
- 別session再開: `read_entry()`が返した`entry_revision`をentry本体と別に引き継ぎ、`lookup_input()`で検証用入力にします。本体へ書かず、読んでいないrevisionを作りません。再検証は`plan_revalidation()`で自entryの依存sourceが変わったentryだけを選び、更新は`update_entry()`でそのrevisionを条件にした、保存先provider自身のnative conditional writeに限ります（providerなしはblocked。ヘルパー自身のcompare-then-writeはしません）。create / updateは保存後にreadbackし、読み戻せたrevisionだけを返します。conflictはauto mergeせず、再読込して意味判断をやり直します。plan_update / plan_replacementは現・新entryを必須にし、identity検証を省略できません。
- 再利用: 分析Skillがcurrent entryを入力として読むだけならgatewayにしません。改善候補は`improvement_reference()`で参照とsource revisionだけを渡し、採否・計画改版・効果測定は各ownerが行います（Knowledge登録は完了の代用にしません）。承認済み改善からの更新は`plan_approved_improvement_update()`で承認refとsource revisionを必須にします。

## Storage safety

Create-if-absent / conditional updateのcapabilityは保存先の実際のatomic operationに結び付いている必要があります。revisionを先に読み比較してからunconditional writeする処理はCASではありません。same-entry conflictでは保存せず、current entryを読み直して意味判断をやり直します。別entry更新だけならtarget entry revisionが不変と確認できる場合に限り影響なしとします。

required deterministic helperが使えない、root listingが不完全、historical artifactを再取得できない、またはstorage conditionが提供されない場合はfail-closedにし、成功したような出力を生成しません。
