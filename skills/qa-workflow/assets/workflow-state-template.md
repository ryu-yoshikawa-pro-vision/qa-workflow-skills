# ワークフロー状態 出力テンプレート

必要な場合だけ使用します。ワークフロー状態はSkill実行の前提ではありません。

- ワークフロー全体状態: 未開始 / 実行中 / 部分完了（ブロック中あり） / ブロック中 / 完了
- 開始Skill:
- 開始対象 / 実行範囲: 複数用途Skillの場合は正規値
- 最終Skill:
- 最終対象 / 実行範囲: 複数用途Skillの場合は正規値

## persisted workflow state record

継続管理するworkflowは、Project Contextの`qa.workflow_state_root`配下で1 `workflow_ref` = 1 artifactにします。下記のrecordを案件全体で共有する一枚のstate fileに集約しません。

```json
{
  "workflow_ref": "opaque UUID",
  "schema_version": "1",
  "state": {
    "overall_state": "実行中",
    "started_source_refs": [],
    "knowledge_entry_refs": [],
    "project_context_ref": "",
    "project_context_revision": "",
    "used_project_context_fields": [
      {"stable_key":"qa.regression_scope","content_identity":"sha256","affected_scope":"Regression baseline","operation":"Run計画"}
    ],
    "source_dependencies": [],
    "resource_conditions": [],
    "mutable_operation_claims": [],
    "handoffs": [],
    "unresolved": []
  }
}
```

`artifact_graph.py`が保存するrecordは`workflow_ref` / `schema_version` / caller提供の`state`からなるenvelopeです。helperはenvelopeとworkflow identityを扱いますが、`state`内部のfield schemaは検証しません。このtemplateにないobjective / scope / produced refs等の固定fieldを、現在helperにない契約として追加しません。

`state_revision`は保存record内のfieldではありません。helperがcreate / read結果のmetadataとして返すexact-content tokenで、local token自体はCAS条件になりません。更新を保存済みとして扱うには、保存先のnative atomic conditional writeへexpected revisionを渡せる必要があります。read後の比較と無条件writeをCAS扱いしません。Project Context全体revisionはprovenanceとして記録できますが、currentnessは利用したstable keyだけを比較します。

| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
| spec-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| question-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-analysis | テスト分析 / E2E対象選定のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-requirement-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-condition-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-case-design |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| coverage-analysis | テスト設計 / TC → E2E実装 / E2E実装 → 実行結果のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| adversarial-review | テスト設計成果物 / E2E実装のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-implementation |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-result-analysis |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| e2e-test-reporting |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-target-inspection |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| test-execution |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| qa-workflow |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| regression-testing | baseline / membership / Run計画 / Run結果更新 / 履歴参照のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| exploratory-testing | exploration / investigation のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| qa-knowledge | triage / create / update / revalidation / lookup / history のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| usability-evaluation |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| usability-inspection | general / scoped / formal-handoff のいずれか | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |
| wcag-conformance-evaluation |  | 未開始 / 実行中 / 要再検証 / ブロック中 / 完了 / 再利用 / 省略 |  |  |

## workflow state永続化契約

- 複数workflowを扱う場合は、案件コンテキストに定義したfixed workflow state root配下で`workflow_ref`ごとに1 state artifactを保持します。
- `workflow_ref`は初回作成時にopaque UUIDとして発行し、state artifactのcanonical pathへ決定論的に解決します。
- state自身のrevisionを保存先のatomic conditional writeへ渡せない場合、更新を保存済みとして扱いません。
- 同じworkflowのmutable operationはstate更新だけで二重開始を防げません。owner側のatomic pre-start claim / idempotent startがない場合、`qa.workflow_state_root/claims/<workflow_ref + operation_refのcanonical identity digest>.json`へatomic pre-start claimを作成します。claim targetはhelperが導出し、別claim rootをProject Contextへ追加しません。claimを取得できなければ開始をblockします。
- shared resource reservationは既存の外部reservationを優先します。project-local reservationはatomic create-if-absentとlifecycleを閉じるnative atomic conditional releaseの両方がある場合だけ取得します。どちらかがない保存先では予約を作らず、状態を安全に確認できないreservation recoveryもblockします。rootは既存の`qa.reservation_root`を使います。

## runtime状態（runtime dispatch時だけ表示）

| Skill | Runtime Unit Key | Model Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated | Fallback Reason | Blocker / Issue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | supported / partial / unsupported / unknown | ready / unresolved / blocked | current / stale | ok / invalid_input / unsupported / limit_exceeded / internal_error / not_run | Yes / No | Yes / No | outside_supported_subset / python_unavailable /  |  |

runtime行は保存されたMachine Runtime Input / ResultとMachine Entityから転記し、`can_complete`や人間向け要約から推測しません。scopeが0件の場合はこの表を表示せず、runtimeをdispatchしない既存経路を維持します。
