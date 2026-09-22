# Regression Suite / QA Activity 統合Plan

## 1. このファイルの目的

旧PlanではQA Artifact Graphのschemaを先に固定していましたが、本PlanではGraphを必須基盤にしません。

実装順序は次です。

1. Regression Suite / Activityをdirect refだけで成立させる。
2. 過去activityの発見経路を成立させる。
3. direct refとPR #11 / #12の既存runtimeで回答できないqueryを列挙する。
4. reverse / multi-hop / cross-run queryが必要な場合だけ、最小relation indexを追加する。

このgateを通る前に広いnode taxonomy、edge taxonomy、Graph schemaを実装しません。

## 2. direct refで先に成立させる関係

最低限、各source artifact自身が次を保持できるか確認します。

### Regression activity

- Suite / baseline revision ref
- member snapshot refs
- selected TC refs
- excluded TC refsと理由
- execution route refs
- execution refs
- unresolved / blocked
- residual risk

### Exploration / Investigation

- activity ref
- source Finding / Question ref
- evidence refs
- follow-up refs

### execution

PR #12 / E2Eの既存契約を正本とします。

- TC / testware ref
- target snapshot ref
- result / evidence ref
- previous execution ref

これらでforward queryを回答できる場合、同じ関係を別indexへ重複保存しません。

## 3. relation indexを追加する条件

次のようなqueryがdirect refだけでは実用的に回答できないことを確認した場合だけ追加します。

- `TC-xxx`が使われた過去Regression activityを逆引きする
- testwareから複数releaseのexecution / resultを横断する
- Findingから後続TCを辿り、そのTCを使用した後続Regressionまで横断する
- PR #11 impact candidateから関連する過去FAIL / Findingを逆引きする

単に「将来便利そう」という理由で追加しません。

## 4. 最小relation record

relation indexが必要と確認された場合、最初は次の最小形から開始します。

```json
{
  "source_ref": "...",
  "relation_type": "...",
  "target_ref": "...",
  "source_artifact_ref": "..."
}
```

必要な場合だけ、artifact-local refのscope情報を追加します。

初期段階では以下を作りません。

- specification / risk / requirement / condition等のPR #11 design nodeの再定義
- 独自`graph_state`
- 独自currentness
- 独自lifecycle
- 汎用`node_key`
- 全QA成果物共通のnode schema

PR #11側のentityはcanonical refとして参照し、design graph自体をPR #13へコピーしません。

## 5. relation type

relation typeもquery需要から必要なものだけ追加します。

初期候補:

- logical TC → testware
- activity → selected TC / testware
- activity → execution
- execution → result / evidence
- Finding → follow-up artifact

PR #11が所有する`depends_on`、`derived_from`、design traceability等をPR #13のschemaとして再定義しません。

## 6. identity

- PR #11 stable ID / Machine Entity refをそのまま利用する
- PR #12の`test_case_ref`はartifact-localのまま扱う
- `source_test_case_id`をglobal identityへ昇格しない
- identity不足を理由にcontent hashを追加しない
- semantic matchingでIDを補完しない
- TCなしE2EへTC IDを創作しない

relation index用の内部keyが実装上必要になった場合も、正式QA IDとして成果物へ書き戻しません。

## 7. query completeness

部分Regressionのscopeを狭めるcandidate queryは、完全性を判断できる情報を返します。

`complete=false`相当とする例:

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
- workflow block / completion → `qa-workflow`
- execution result / cleanup / rerun → PR #12 / E2E
- Regression membership → Regression Suiteの論理契約
- activity履歴 → activity artifact

補助runtimeはsource stateを表示・検証できますが、別のcurrentness判定を作りません。

## 9. 保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot / trace本体
- 生の個人情報
- chain-of-thought
- source artifact本文全文

必要なrefと最小metadataだけを扱います。
