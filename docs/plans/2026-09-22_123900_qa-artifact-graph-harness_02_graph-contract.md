# Regression / Exploratory Testing 統合Plan

## 1. 目的

QA Artifact Graphを必須基盤にしません。

現在必要なqueryは、まず既存成果物のdirect refとActivity rootのdeterministic scanで解決します。

```text
direct ref
→ discovered artifactのdeterministic scan
→ 実測上不足する場合だけindexを検討
```

relation indexはPR #13の実装対象ではなく将来gateです。

## 2. direct refで成立させる関係

### Regression Activity

`regression-testing`は最低限次を参照します。

- baseline / Suite source ref / revision
- project context ref / revision
- selection input refs / revisions
- member snapshot refs
- selected / excluded TC refs
- auxiliary testware refs
- required execution route
- execution refs
- source execution state / result
- unresolved / blocked
- residual risk refs

selection inputは今回の判断に実際に使ったcurrent成果物だけを指します。

例:

- PR #11 impact result
- Product Risk
- Finding
- explicit user scope
- project contextのRegression方針

本文をActivityへ複製しません。

### Exploration / Investigation

`exploratory-testing`は次を直接参照できるようにします。

- session / activity ref
- source Change / Risk / Question / symptom / hypothesis
- evidence refs
- Finding refs
- follow-up refs

### execution

PR #12 / E2Eの既存契約を正本とします。

- TC / testware ref
- target snapshot ref
- source execution state / result
- evidence ref
- previous execution ref

## 3. deterministic scan

Activity rootから全Activityを発見できる場合、reverse queryはscanで回答します。

例:

- TC → 過去Regression Activity
- testware → 過去execution / Activity
- Finding → follow-up TC → 後続Regression
- Risk → そのRiskをselection inputに使ったRegression Activity

scan結果の完全性はcanonical discovery rootの完全性に依存します。

rootが不完全なら結果を完全な履歴として扱いません。

## 4. relation index gate

次のいずれかを実測した場合だけ、問題になったquery向けのindexを検討します。

- artifact数によりdeterministic scanの実測コストが運用要件を満たさない
- 保存場所が分散しcanonical rootから必要artifactを列挙できない
- 頻繁に必要なmulti-hop queryをdirect ref + scanで安定して回答できない

「reverse lookupだから」「将来便利だから」は導入理由にしません。

gateを通るまではrelation record schema、builder、query runtimeを設計・実装しません。

## 5. identity

- PR #11 stable ID / Machine Entity refを利用する
- PR #12のartifact-local ref契約を維持する
- `source_test_case_id`をglobal identityへ昇格しない
- content hashを新しいQA identityとして追加しない
- semantic matchingでIDを補完しない
- TCなしE2EへTC IDを創作しない

## 6. query completeness

Regression candidate / history queryは完全性を判断できる情報を持ちます。

`complete=false`相当:

- authoritative discovery sourceを完全列挙できない
- required artifact typeを扱えない
- dangling refがある
- PR #11 impact結果が利用不可 / 未検証
- current source stateを確認できない
- scope mappingが未解決

不完全なcandidate集合だけを根拠にscopeを狭めません。

空集合も「影響なし」「Regression不要」と解釈しません。

## 7. source state

PR #13で第二のcurrentness stateを作りません。

- design freshness / stale / `要再検証` → PR #11
- workflow state → `qa-workflow`
- Regression membership / Activity domain state → `regression-testing`
- Exploration Session state → `exploratory-testing`
- execution start / result / cleanup / rerun → PR #12 / E2E

## 8. 保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot / trace本体
- 生の個人情報
- chain-of-thought
- source artifact本文全文

## 9. 知識 / workflow provenance

PR #13では、活動履歴だけでなく継続利用するQA知識とworkflowの由来・currentnessをdirect refで追跡します。

### workflow

workflow state / Activity / Sessionから最低限次を辿れるようにします。

- workflow_ref
- 利用したQA artifact refs / revisions
- 利用したknowledge entry refs / revisions
- 利用したproject context ref / revision
- 利用したenvironment / resource条件
- 生成したActivity / Session / artifact refs
- related workflow refs（因果関係が明示できる場合だけ）

### knowledge entry

knowledge entryではprovenanceとcurrentness dependencyを分けます。

provenance:

- source artifact / inspection / Activity / Session / Finding refs
- source revisions

currentness:

- currentness dependency refs / revisions
- 適用target / environment scope refs
- 適用version / environment条件
- entry revision / content identity
- state
- 置換先ref

Activity / Finding本文をknowledgeへ複製するのではなく、由来をrefで保持します。

### historical snapshot

workflow / Activity / Sessionが当時利用したrevisionは履歴として保持します。

current knowledgeやcurrent QA artifactが更新されても、過去workflowの入力refを最新revisionへ書き換えません。

## 10. cross-workflow query

次のqueryもdirect ref + deterministic scanを優先します。

- knowledge entry → 由来となったFinding / Activity / inspection
- target / environment → 関連する有効knowledge entry
- workflow → 利用したknowledge / artifact / environment
- artifact revision → そのrevisionを利用した進行中 / 過去workflow
- workflow Aの更新 → 影響を受けるworkflow Bのdependency

query completenessはknowledge root / workflow history root / artifact discovery rootの完全性に依存します。

完全性を保証できない場合は結果を完全な影響集合として扱いません。

## 11. 並行更新とrevision

direct refには、current artifactを更新するときの競合検出に利用できるrevision / SHA / ETag / content identityを含めます。

同じbase revisionから複数workflowが共有成果物を更新した場合、自動rebase / partial updateを許可するのはowner Skillがdeterministic partial update boundaryを明示しているartifactだけです。

さらに次をすべて満たす必要があります。

- update scopeがdisjoint
- 対象scopeのupstream revision / fingerprintが不変
- cross-scope invariantを壊さないことをowner contractで確認できる
- current成果物を再読込してからscope外current内容を保持する

それ以外は自動mergeせず、最も早い責任Skillへ戻してcurrent内容を入力に再評価します。

workflow state自身も1 workflow = 1 persisted state artifactとしてstate revision / content identityを持ち、CASで更新します。

古いrevisionでの後勝ち上書きを許可しません。

この契約のために汎用transaction managerやGraph DBは追加しません。

