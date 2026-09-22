# Regression / Exploratory Testing 統合Plan

## 1. このファイルの目的

QA Artifact Graphを必須基盤にしません。

queryの解決順序を固定します。

1. source artifactが持つdirect ref
2. project context / canonical rootから発見したActivity・execution成果物のdeterministic scan
3. それでも実需を満たせないqueryだけ最小relation index

reverse lookupであることだけをrelation index導入理由にしません。

## 2. direct refで成立させる関係

### Regression Activity

`regression-testing`が次を保持します。

- baseline / Suite source ref / revision
- project context ref / revision
- selection input refs / revisions
- member snapshot refs
- selected TC refs
- auxiliary testware refs
- excluded refsと理由
- required execution route refs
- execution refs
- unresolved / blocked
- residual risk

selection input refsは今回の判断に実際に使ったcurrent成果物だけを指します。

例:

- PR #11 impact result
- Product Risk
- Finding
- explicit user scope
- project contextのRegression方針

本文をActivityへ複製しません。

### Exploration / Investigation

`exploratory-testing`は次を保持します。

- activity ref
- source Finding / Question / symptom ref
- evidence refs
- follow-up refs

### execution

PR #12 / E2Eの既存契約を正本とします。

- TC / testware ref
- target snapshot ref
- result / evidence ref
- previous execution ref

## 3. deterministic scan

Activity rootから全Activityを発見できる場合、reverse queryはまずscanで解決します。

例:

- TC → 過去Regression Activity
- testware → 過去execution / Activity
- Finding → follow-up TC → 後続Regression

scan結果の完全性はActivity discovery rootの完全性に依存します。

root / indexが不完全な場合、完全な履歴として扱いません。

## 4. relation indexを追加する条件

次を実測した場合だけ追加します。

- artifact数により毎回scanするコストが実運用上問題になる
- 保存場所が分散しcanonical rootからscanできない
- 頻繁なmulti-hop queryをdirect ref + scanで安定して回答できない

問題になったqueryに必要なrelationだけを持ちます。

## 5. 最小relation record

必要性を実証した場合だけ次の最小形から開始します。

```json
{
  "source_ref": "...",
  "relation_type": "...",
  "target_ref": "...",
  "source_artifact_ref": "..."
}
```

初期段階では以下を作りません。

- PR #11 design nodeの再定義
- 独自`graph_state`
- 独自currentness / lifecycle
- 汎用`node_key`
- 全QA成果物共通node schema

## 6. identity

- PR #11 stable ID / Machine Entity refを利用する
- PR #12の`test_case_ref`はartifact-localのまま扱う
- `source_test_case_id`をglobal identityへ昇格しない
- content hashを新しいQA identityとして追加しない
- semantic matchingでIDを補完しない
- TCなしE2EへTC IDを創作しない

## 7. query completeness

Regression candidate queryは完全性を判断できる情報を返します。

`complete=false`相当:

- authoritative discovery sourceを完全列挙できない
- unsupported artifactがある
- required relationを抽出できない
- dangling refがある
- PR #11 impact結果が利用不可 / 未検証
- current source stateを確認できない
- scope mappingが未解決

`regression-testing`は不完全なcandidate集合だけを根拠にscopeを狭めません。

空集合もRegression不要と解釈しません。

## 8. source state

PR #13で独自stateを生成しません。

- design freshness / stale / `要再検証` → PR #11
- workflow state → `qa-workflow`
- Regression Activity state / membership → `regression-testing`
- execution result / cleanup / rerun → PR #12 / E2E

補助runtimeはsource stateを検証できますが、別currentness判定を作りません。

## 9. 保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot / trace本体
- 生の個人情報
- chain-of-thought
- source artifact本文全文
