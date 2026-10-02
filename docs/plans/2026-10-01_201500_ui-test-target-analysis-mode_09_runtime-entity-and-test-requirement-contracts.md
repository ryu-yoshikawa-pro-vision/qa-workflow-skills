# UIテスト対象分析モード: runtime entity / test requirement contracts

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

関連Plan:
- 2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md
- 2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md
- 2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md

この文書は、Acceptance Criteriaをshared runtime contractへ接続し、test-requirement-designまで進むworkflowでfreshness / closureを維持するためのcross-Skill runtime契約の正本です。仕様理解packageだけを要求された場合、Acceptance Criterion Machine Entity生成までは行いますが、test-requirement-designの起動とAC→TR / Disposition closureは完了条件にしません。

## 1. 固定方針

- US / UC / Behaviorはspec-analysis内部のstructured modelであり、global Machine Entity typeへ追加しない
- 下流handoff pointであるcurrent ACだけを `spec-analysis / acceptance_criterion / AC-xxx` Machine Entityへ変換する
- Authority Entityは既存 `authority_entities.py` を正本とする
- AC Entityは `ui_target_package.py build-machine-evidence` が決定論生成する
- Machine Entity wrapper / content fingerprint / expected identity / normalized machine inputをLLMに手組みさせない
- `acceptance_criterion` / `acceptance_refs` / spec-analysis expected ACの追加はshared runtimeの意味契約変更なので、既存byte-identity対象7コピーを `runtime-v1` から `runtime-v2` へ更新する
- envelope field shape自体は変更しない
- test-requirement-designのinput schema変更は `requirement-structure-v2` として明示する
- v1とv2を同時に処理する分岐runtimeは作らない。旧v1 evidenceはcurrent evidenceとして再利用せず、current inputからv2を再実行する

## 2. shared runtime_contract.py

PR #16で更新するのは、既存repository byte-identity契約の対象である次の7 Skill-local `runtime_contract.py` です。

- skills/spec-analysis/scripts/runtime_contract.py
- skills/test-analysis/scripts/runtime_contract.py
- skills/test-requirement-design/scripts/runtime_contract.py
- skills/test-condition-design/scripts/runtime_contract.py
- skills/test-case-design/scripts/runtime_contract.py
- skills/coverage-analysis/scripts/runtime_contract.py
- skills/qa-workflow/scripts/runtime_contract.py

7コピーは同一内容で更新し、1コピーだけの変更は禁止します。

PR #14確認headには `skills/usability-inspection/scripts/runtime_contract.py` と `skills/wcag-conformance-evaluation/scripts/runtime_contract.py` も同一blobで存在しますが、既存byte-identity契約の対象外です。この2 SkillはPR #16のAC / TR処理経路で `acceptance_criterion` / `acceptance_refs` を消費しないため、PR #16では変更しません。

### 2.1 ALLOWED_ENTITY_TYPES

`acceptance_criterion` を追加します。

US / UC / Behaviorは追加しません。

### 2.2 canonicalization

共通canonicalizationへ次を追加します。

- set-like string refs: `acceptance_refs`
- record array: `acceptance_criteria` を `ac_id` でcanonical sort

duplicateをcanonicalizationで隠しません。schema validatorがduplicateを検出できる既存方針を維持します。

### 2.3 spec-analysis expected Entity

shared `_expected_entities()` の `skill == "spec-analysis"` branchを次へ拡張します。

- `normalized.get("authorities", [])` → `authority`
- `normalized.get("acceptance_criteria", [])` → `acceptance_criterion`

通常の非mode spec-analysisは従来どおり `acceptance_criteria` key省略を許可し、省略時は空集合として扱います。UI target modeの `build-machine-evidence` はcanonical outputとして必ず `acceptance_criteria` keyを出力します。

expected Entityをactual Machine Entity collectionから逆算しません。

spec-analysisはruntime unitを新設しません。expected Entity導出だけをshared runtime contractへ追加します。

### 2.4 runtime-v2へ更新

既存runtime設計では `runtime_contract_version` は意味契約変更時に更新します。今回の `acceptance_criterion` Entity type、`acceptance_refs` / `acceptance_criteria` canonicalization、spec-analysis expected Entity導出追加は意味契約変更なので、更新対象7コピーの `RUNTIME_CONTRACT_VERSION` を `runtime-v1` から `runtime-v2` へ更新します。

envelope field shapeとfreshness algorithmは維持します。v1 / v2を同時解釈するcompatibility branchは追加しません。更新対象7 Skillの旧runtime-v1 evidenceはruntime-v2 current evidenceとして読み替えず、current scriptで再実行・再検証します。runtime implementation fingerprintも既存契約どおり変わります。

PR #14確認headの `usability-inspection` / `wcag-conformance-evaluation` は既存7-copy byte-identity契約外で、PR #16のAC / TR処理経路でも新しい意味契約を消費しません。そのためPR #16だけを理由にこの2コピーを更新しません。Step 0でPR #14 merge後の実装を再確認し、もしこの2 Skillがruntime-v2の意味契約を消費する状態へ変わっていれば、その実装を正本として対象範囲を再評価します。

## 3. spec-analysis normalized machine input

`ui_target_package.py build-machine-evidence` はMarkdownから次を決定論的に生成します。

- normalized Authority rows
- normalized current AC rows
- canonical `normalized_skill_input`
- Authority Machine Entities
- Acceptance Criterion Machine Entities
- canonical `machine_entities[]`
- canonical `expected_entity_identities[]`

`normalized_skill_input` の正本shape:

```json
{
  "authorities": [{"authority_id":"SPEC-001"}],
  "acceptance_criteria": [
    {"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
  ]
}
```

`authority_refs[]` はAC / Behavior / UC / US chain全体が参照するcurrent Authority IDのunionをhelperが重複除去・昇順canonical化して生成します。Agent / LLMが同じAuthority集合を再構築しません。

qa-workflow / coverage-analysisへspec-analysis scopeを渡す場合、AgentがMarkdownからこのJSONを再構築しません。helper返却のcanonical `normalized_skill_input` をそのまま使用します。

## 4. Acceptance Criterion Machine Entity

identity:

- skill: `spec-analysis`
- entity_type: `acceptance_criterion`
- entity_ref: `AC-xxx`

current ACだけをEntity化します。blocked ACを完成済みcurrent Entityへ変換しません。

### 4.1 canonical content

AC Entity contentには次を固定projectionします。

- `ac_id`
- `acceptance_criteria`
- `behavior_id`
- `behavior_result_classification`
- `behavior_text`
- `behavior_postcondition`
- `uc_id`
- `use_case`
- `trigger`
- `preconditions`
- `success_postcondition`
- `user_stories[]`: `us_id / actor_role / goal`。`us_id`昇順で固定
- `scope_id`
- `authority_refs[]`: AC / Behavior / UC / US chain全体が参照するcurrent Authority IDのunionを重複除去して昇順
- `structure_refs[]`: AC / Behavior / UC / US chain全体の関連構造ID unionを重複除去して昇順

これによりAC本文が同じでも、親US / UC / Behaviorの意味変更でAC content fingerprintが変わります。

### 4.2 dependencies

AC Entityの `upstream_entity_dependencies[]` は、AC / Behavior / UC / US chain全体が参照するcurrent Authority Entity unionへ固定します。

US / UC / Behaviorをdependency Entityとして追加しません。親chain自体をAC contentへ含めることで、不要なglobal entity typeを増やさずfreshnessを成立させます。

## 5. test-requirement-design contract version

`requirement_structure.py` はinput schemaを変更するため、generator contractを明示的に次へ更新します。

- before: `requirement-structure-v1`
- after: `requirement-structure-v2`

shared runtime contractは `runtime-v2` を使用します。

repository内の固定contract mapping / fixture metadata / portability test / runtime test / vertical integrationで `requirement-structure-v1` を参照している箇所をcurrent v2へ同期します。

旧v1 Machine Runtime Resultをv2 current resultとして読み替えません。再利用が必要な成果物はcurrent normalized inputからv2を再実行します。

## 6. requirement_structure-v2 input

top-level required fields:

- `authorities`
- `risks`
- `acceptance_criteria`
- `test_requirements`
- `dispositions`
- `previous_tr_ids`
- `update_scope_tr_ids`

既存legacy promotion用 `legacy_tr_ids` の条件付き入力契約は維持します。

`acceptance_criteria` row:

```json
{"ac_id":"AC-001","authority_refs":["SPEC-001","DEC-002"]}
```

`authority_refs[]` はspec-analysis helperが生成したcanonical値をそのまま渡します。

- artifact modeでは、同じ `AC-xxx` Machine Entityの `upstream_entity_dependencies[]` から得られるAuthority identity集合とexact一致を要求する
- direct modeでは、top-level `authorities[]` のknown ID集合へ存在検証する
- ACが存在しないworkflowでもfield自体を省略せず `acceptance_criteria: []` とする

各 `test_requirements[]` draftへ `acceptance_refs` を必須追加します。該当ACがない横断的TRは `[]` を使用します。

## 7. requirement_structure-v2 deterministic processing

scriptは次を行います。

1. AC ID形式 / duplicate / `authority_refs[]` を検証
2. artifact modeでは `spec-analysis / acceptance_criterion / AC-xxx` current Entityへ完全解決し、input `authority_refs[]` がAC EntityのAuthority dependency identity集合とexact一致することを検証
3. direct modeではinputのknown AC集合とknown Authority集合へ存在検証
4. TR draftの `acceptance_refs` を検証
5. linked upstream集合へ `acceptance_criterion` を追加
6. closure universeへcurrent ACを追加
7. TR Entity contentへ `acceptance_refs` を保存
8. artifact modeではTR Entity `upstream_entity_dependencies[]` へ参照current AC Entityを追加する。direct modeではcurrent Machine Entityがないためdependencyを捏造せず、`acceptance_refs[]` をcontentへ保持する
9. 各参照ACの `authority_refs[]` をunionする。artifact modeでは解決できたcurrent Authority EntityをTR Entity `upstream_entity_dependencies[]` へ直接追加する。direct modeではknown Authority ID検証とcontent保持までとし、Machine Entity dependencyは作らない
10. AC linked + disposedの二重扱いを拒否
11. linkedもdisposedもされないcurrent ACをunclosedとして拒否

Authority dependencyの展開はID集合・Entity解決だけを行う決定論処理です。どのAuthorityがACを支えるかはspec-analysisでLLMが判断済みであり、test-requirement-design側で意味を再判断しません。存在しないMachine Entityをdirect modeでplaceholder生成する経路は追加しません。

LLMはACとTRの意味上の対応、TRの分割 / 統合を判断します。scriptは対応関係の意味妥当性を決めません。

## 8. AC disposition

既存共通Disposition schemaを再利用します。新しいDisposition形式は作りません。

`test-requirement-design` の許可upstream typeへ `acceptance_criterion` を追加します。

owner mapping:

- authority → spec-analysis
- product_risk → test-analysis
- acceptance_criterion → spec-analysis

ACで許可するhandlingは次の4値に固定します。

- 別テストレベル
- 残存リスク
- 対象外
- ブロック中

`acceptance_criterion` upstreamに `重複` は許可しません。Authority / Product RiskについてはPR #14後の既存Disposition handling契約を維持します。

人間向け `テスト要求を作らない上流項目` の種別へ `Acceptance Criteria` を追加します。

## 9. test-requirement output

`テスト要求一覧`:

| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

ACが存在しないworkflowでは `関連AC ID` を `-` とします。

`テスト要求を作らない上流項目` の種別:

- 仕様根拠
- プロダクトリスク
- Acceptance Criteria

## 10. deterministic output validator

`TR-OUT-003` のfixture contractを固定します。

expected keys:

- `known_acceptance_criteria`
- `required_linked_acceptance_ids`
- `expected_dispositions`

validatorはAuthority / Product Risk / Acceptance Criteriaをclosure universeとして扱い、各current ACがlinkedまたはdisposedのどちらか一方へ閉じることを検証します。

既存TR-OUT-001 / 002はACなしworkflowとして `known_acceptance_criteria=[]` 相当を確認し、従来挙動の回帰に使います。

## 11. freshness propagation

次をrepository runtime testで固定します。

| 変更 | 期待 |
| --- | --- |
| AC本文変更 | 関連TR stale |
| AC削除 | 関連TR missing dependency / stale |
| 親Behavior変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親UC変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| 親US変更、AC本文同じ | AC fingerprint変更 → 関連TR stale |
| artifact modeでAuthority変更、AC本文・親chain同じ、spec-analysis再実行済み | TRが保持する直接Authority dependency不一致 → 関連TR stale |
| 無関係UC / AC変更 | 無関係TRはcurrent |

freshness判定アルゴリズム自体は既存 `evaluate_entity_freshness` を再利用し、新しい伝播engineを作りません。

## 12. partial rerun

TRDの既存partial rerun contractを維持します。

必須regression:

1. AC-001へ依存するTR-001が存在
2. AC-001が変更
3. TR-001が今回の `update_scope_tr_ids` 外
4. previous artifactからTR-001をcarry-forward
5. carry-forward TRが旧AC fingerprintを保持
6. current AC Entityとの不一致によりTR-001がstale
7. workflow completion不可

scope外であることを理由に、changed ACへ依存するTRをcurrent扱いしません。

## 13. qa-workflow / coverage-analysis integration

shared `_expected_entities()` がspec-analysis normalized inputからAuthority + AC expected identityを決定論導出します。

qa-workflow / coverage-analysisはcurrent Entity collectionへAC Entityが存在してもextra entity扱いしません。

coverage-analysisの既存traceability graph node typeへACを追加しません。AC→TRのmachine traceabilityはTR Entity dependencyとTRD closureで保証し、Authority / Risk / TR / TCN / CI / TCの既存coverage graphを不要に拡張しません。

## 14. repository tests

次を更新 / 追加します。

- 既存byte-identity契約の7 Skill-local runtime_contract.py copies byte-identical
- `acceptance_criterion` Machine Entity valid / unknown type regression
- shared canonicalization: `acceptance_refs` / `acceptance_criteria`
- spec-analysis expected Authority + AC identity
- 通常の非mode spec-analysis normalized inputで `acceptance_criteria` key省略を空集合として扱い、既存Authority expected Entityだけを維持
- qa-workflow expected / actual Entity exact match
- coverage-analysis current Entity parse compatibility
- requirement-structure-v2 valid / invalid schema
- AC linked / disposed / unclosed / linked+disposed
- AC upstream skill/type mismatch
- AC dependency fingerprint propagation
- AC本文 / 親chain不変のままAuthority fingerprintだけ変更し、spec-analysisをcurrentへ再生成した後も未再実行TRが直接Authority dependencyによりstaleになる回帰
- partial rerun stale carry-forward
- shared runtime-v1 evidenceをruntime-v2 current resultとして扱わない

## 15. 対象外

- US / UC / Behaviorのglobal Machine Entity type追加
- 新しいfreshness engine
- coverage graphへのAC node追加
- v1 / v2の二重runtime実装
- Agent / LLMによるexpected Entity一覧の手組み
- actual Entity集合からexpected Entity集合を逆算すること

## 16. 完了条件

- 既存byte-identity契約の7 runtime_contract.pyが同一内容でacceptance_criterionを扱える
- 既存byte-identity対象7コピーがruntime-v2へ同期され、requirement-structure-v2が明示される
- helperからspec-analysis normalized_skill_inputとAuthority + AC Entityを決定論生成できる
- qa-workflowがAuthority + ACをexpectedとして内部導出できる
- test-requirement-designまで進むworkflowではcurrent ACがTRまたはDispositionへ完全に閉じる。仕様理解packageだけの要求ではこのclosureを要求しない
- AC / 親Behavior / 親UC / 親US / Authority変更が必要なTR freshnessへ伝播する
- 無関係TRを不必要にstale化しない
- partial rerunでscope外TRがchanged ACを参照したままcurrentにならない
- existing coverage graphを目的なく拡張していない
