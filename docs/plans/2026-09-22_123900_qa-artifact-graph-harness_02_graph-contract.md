# Regression Suite / QA Activity 統合Plan

## 1. このファイルの目的

旧PlanではQA Artifact Graphのschemaを先に固定していましたが、本PlanではGraphを必須基盤にしません。

queryの解決順序を固定します。

1. source artifactが持つdirect refを使う
2. project context / canonical rootから発見済みのActivity・execution成果物をdeterministicにscanする
3. それでも実需を満たせないqueryだけ、最小relation indexを検討する

reverse lookupであることだけをrelation index導入理由にしません。

## 2. direct refで成立させる関係

### Regression activity

最低限、次を保持します。

- baseline / Suite source ref / revision
- project context ref / revision
- selection input refs / revisions
- member snapshot refs
- selected TC refs
- auxiliary testware refs（利用時）
- excluded refsと理由
- execution route refs
- execution refs
- unresolved / blocked
- residual risk

selection input refsには、今回のselectionに実際に使ったものだけを保持します。

例:

- PR #11 impact result
- Product Risk
- Finding
- explicit user scope
- project contextのRegression方針

本文をActivityへ複製しません。

### Exploration / Investigation

- activity ref
- source Finding / Question / symptom ref
- evidence refs
- follow-up refs

completed activityの本文を後続成果物作成のたびに書き換える必要はありません。後続成果物側がsource Finding等へback-referenceできる場合はそれを利用します。

### execution

PR #12 / E2Eの既存契約を正本とします。

- TC / testware ref
- target snapshot ref
- result / evidence ref
- previous execution ref

## 3. deterministic scan

Activity rootから全activityを発見できる場合、reverse queryはまずscanで解決します。

例:

- TC → 過去Regression activity
- testware → 過去execution / activity
- Finding → follow-up TC → 後続Regression

scan結果の完全性は、Activity discovery root自体の完全性に依存します。

root / indexの完全性が保証できない場合、結果を完全な履歴として扱いません。

## 4. relation indexを追加する条件

次のいずれかを実測で確認した場合だけ追加します。

- artifact数により毎回scanするコストが実運用上問題になる
- 保存場所が分散し、canonical discovery rootからscanできない
- 頻繁に使うmulti-hop queryをdirect ref + scanで安定して回答できない

追加する場合も、問題になったqueryに必要なrelationだけを持ちます。

単に「将来便利」「Graphなら拡張しやすい」という理由で追加しません。

## 5. 最小relation record

必要性を実証した場合だけ、次のような最小recordから開始します。

```json
{
  "source_ref": "...",
  "relation_type": "...",
  "target_ref": "...",
  "source_artifact_ref": "..."
}
```

必要な場合だけartifact-local refのscope情報を追加します。

初期段階では以下を作りません。

- specification / risk / requirement / condition等のPR #11 design nodeの再定義
- 独自`graph_state`
- 独自currentness / lifecycle
- 汎用`node_key`
- 全QA成果物共通のnode schema

## 6. identity

- PR #11 stable ID / Machine Entity refをそのまま利用する
- PR #12の`test_case_ref`はartifact-localのまま扱う
- `source_test_case_id`をglobal identityへ昇格しない
- identity不足を理由にcontent hashを追加しない
- semantic matchingでIDを補完しない
- TCなしE2EへTC IDを創作しない

## 7. query completeness

部分Regressionのcandidate queryは、完全性を判断できる情報を返します。

`complete=false`相当:

- authoritative discovery sourceを完全に列挙できない
- unsupported artifactがある
- required relationを抽出できない
- dangling refがある
- PR #11 impact結果が利用不可 / 未検証
- current source stateを確認できない
- 対象scopeとのmappingが未解決

不完全なcandidate集合だけを根拠にscopeを狭めません。

空集合も「影響なし」「Regression不要」と解釈しません。

## 8. source state

PR #13で独自stateを生成しません。

- design freshness / stale / `要再検証` → PR #11
- workflow / activity state → `qa-workflow`
- execution result / cleanup / rerun → PR #12 / E2E
- Regression membership → Regression Suite契約

補助runtimeはsource stateを参照・検証できますが、別のcurrentness判定を作りません。

## 9. 保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot / trace本体
- 生の個人情報
- chain-of-thought
- source artifact本文全文
