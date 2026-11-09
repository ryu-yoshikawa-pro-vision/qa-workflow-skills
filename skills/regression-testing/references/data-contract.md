# Regression data contract

Production helperはPR #11 ownerが解決したcurrent TCデータと保存先が返したsource revisionを入力として受け取ります。PR #11 Machine Entity、execution artifact、E2E run artifactそのもののparser / identity / freshnessは複製しません。

## Discovery snapshot input

```json
{
  "discovery_roots": ["qa/test-cases"],
  "listing_complete": true,
  "source_revisions": [
    { "source_ref": "repo:path", "revision": "opaque-token" }
  ],
  "cases": [{
    "tc_ref": "machine-entity-ref",
    "source_ref": "repo:path",
    "source_revision": "opaque-token",
    "lifecycle_status": "current",
    "content_fingerprint": "owner-produced-value"
  }]
}
```

`lifecycle_status`はownerからの`current` / `unresolved` / `stale` / `deleted` / `superseded` projectionです。helperは値を検証し、PR #11の意味を再計算しません。

## Baseline / Run / Activity input

Membership decisionには`tc_ref`, `decision` (`member`, `one_off`, `out_of_scope`, `unresolved`), `reason`、空でない一意な`source_refs`、および各source refに対応する空でない`source_ref` / `revision`を持つ`source_revisions`が必要です。両listのsource ref集合は一致し、同一source refへ複数revisionを割り当てません。Run routeは`manual`、concrete E2E testware ref付きの`e2e`、または非E2Eの`testware`のいずれかです。Activity route resultにsource artifact ref、source start state、owner execution contractが返す`actual_start_confirmed`と`result_finalized`、source outcome、evidence refsを保持します。source result stringはsource artifactの値をそのまま保持し、新しいRegression taxonomyへ変換しません。

`executed`はrequired routeのactual startだけから判定します。Activity `完了`には、全required routeのactual start確認、owner側result finalization、source result / outcomeのraw projection、必要cleanupの閉鎖、unresolvedなしを別々に確認します。result finalizationはsource contractから渡される事実であり、Regressionはresult文字列から推測しません。

`complete`はroot listingが完全、source revisionsが取得でき、discovery TCが全件lifecycle-resolved、membership判定が全件完了した場合だけtrueです。`decision == "unresolved"`のmembershipが1件でも残る場合は`complete=false`です。coverage gapは別項目です。

## 正規artifactのfield

全artifactは`artifact_type`を`baseline` / `run` / `activity`のいずれかにします。Baselineは`assets/baseline-template.json`で定義する`schema_version`も持ちます。

- **Baseline**: `assets/baseline-template.json`をfieldの一覧と初期値の正本にします。currentnessに使う`scope_identity`は空でないscope identityです。top-level `source_revisions`にはauthoritative discovery sourceと全membership decisionのsource revisionを含め、同じsource refには一つのrevisionだけを保持します。membership内の各source revisionは同じref / revisionの組でtop-levelにも存在しなければなりません。いずれかが欠落・不正・競合して照合できない場合、currentnessを`current`にしません。`memberships`にTC decision（`member` / `one_off` / `out_of_scope` / `unresolved`）を記録し、`member_tc_refs`は`lifecycle_status == "current"`かつ`decision == "member"`のref、`one_off_tc_refs`は`decision == "one_off"`のrefをそれぞれ重複なく投影します。full Run planningは`member_tc_refs`全件を使い、欠落・不正型・membershipとの不一致は使用可能なcomplete Baselineとして扱いません。`completeness_evidence`には`root_listing_complete`、`source_revisions_complete`、`lifecycle_resolved`、`membership_decisions_complete`を持たせ、current TC全件にmembership判断と有効なprovenanceがあり、4値すべてが`true`の場合だけ`complete`を`true`にします。`coverage_gaps`をinventory / lifecycle不完全と混ぜません。

`check_baseline_currentness()`のcurrent側入力は、current discovery snapshot、current Regression scopeからcallerが解決した`scope_identity`、およびsaved Baselineが依存するsource refそれぞれのcurrent revisionを組み合わせたものです。`scope_identity`はDiscovery snapshotが生成する値ではありません。current `source_revisions`にはdiscovery sourceとsaved membership decisionが依存するsourceのcurrent revisionを含めます。たとえば`current = {**snapshot, "scope_identity": resolved_scope_identity, "source_revisions": current_dependency_revisions}`として渡します。saved Baselineの`discovery_snapshot_ref`とcurrent snapshotの`snapshot_ref`を照合し、saved refの欠落・不正は`incomplete`、current refの欠落・不正は`unresolved`、ref不一致は`stale`です。saved Baselineのtop-level `source_revisions`とcurrent側の同じref / revisionも比較し、変更確認時は`stale`、current revisionを取得できないときは`unresolved`です。complete Baselineではcurrent discovery snapshotの`cases`内で`lifecycle_status == "current"`のTC ref集合とsaved Baselineの`memberships[].tc_ref`集合が完全一致しなければ`incomplete`です。current `cases`またはBaseline membershipが不正なshapeの場合はcurrentnessを確定しません。`complete=true`のBaselineに`unresolved` decision、`unresolved_tc_refs`または`undecided_tc_refs`がある場合も`incomplete`です。current scopeを解決できない場合は`unresolved`、saved Baseline側のscope identityまたはmembership dependencyが欠落・不整合の場合は`incomplete`です。scopeやrevisionを推測して補ってはいけません。

- **Run**: `run_scope`、baselineの`complete` / `currentness` / `member_tc_refs`、`selected_tc_refs`、`suite_complete`、`required_routes`、`route_contract_version`を保持します。routeは`manual`、具体的E2E testware ref付き`e2e`、または非E2Eの`testware`です。TCなし補助testwareは`auxiliary_routes`、`auxiliary_testware_refs`、`auxiliary_testware_count`に分けます。`auxiliary_testware_count`は0以上の整数（真偽値・小数・文字列は不可）で、`route_contract_version: "2"`のRunでは必須です。`auxiliary_routes`の件数（`auxiliary_testware_refs`を宣言していればその件数も）と一致しなければなりません。`e2e` routeの`e2e_testware_ref`は空でない文字列です（空白のみ・list・object・数値・未指定は不正）。`manual` / `testware` routeにこの条件は課しません。`route_contract_version: "2"`のRunでは`auxiliary_testware_refs`を省略できます。省略（フィールドなし）と空配列は区別し、省略時は`auxiliary_routes`の検証と件数の照合だけを行い、一覧との集合比較は行いません。フィールドがある場合は、list（`null`・文字列などは不正）で、重複・不正な値がなく、`auxiliary_routes`のrefと集合が一致し、件数もその長さに一致しなければなりません。旧形式（版なし）のRunではrefs一覧だけが補助の根拠で、省略は空一覧として従来どおり扱います。
- **Activity**: `activity_ref`、`snapshot_ref`、`scope_identity`、`activity_state`、`source_executions`、`route_results`、`tc_execution_state`、`counts`、`cleanup_status`、`unresolved`、`route_contract_version`を保持します。TCなし補助testwareがあれば`auxiliary_route_results`と補助件数へ分けます。各routeのactual start、result finalization、source result / outcomeのraw valueをowner sourceから投影します。

## `testware` required route（`route_contract_version: "2"`）

TCに対応する非E2Eの自動／runner実行は、`required_routes`へ`route_type: "testware"`のrouteとして追加します。`manual` / `e2e`の意味・保存形・currentnessは変更しません。

| field                     | 内容                                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `tc_ref` / `route_ref`    | 対象TCとroute identity（TC内で一意）                                                                           |
| `testware_ref`            | 実testwareへの参照（repo revision・file・test名 / 階層から解決したref）。runner内部の一時IDだけにしない        |
| `executor_owner`          | `testware-execution`（Regressionはrunnerを起動しない）                                                         |
| `implementation_revision` | 対象実装revision。ownerが返す結果の`implementation_revision`と一致しない結果（旧build）は今回Runの実行にしない |
| `selection_basis`         | 選択条件（file / test名・filter等）                                                                            |
| `execution_ref`           | Activityで`source_executions`を引くkey                                                                         |

同じTCに複数routeがある場合、全routeの実開始・結果確定・cleanupを照合します。別TCや補助testwareのPASSで未実行TCを完了にしません。

`testware` routeのsource executionは、補助と同じ`testware-execution`の契約で`attempt_ref`・`raw_capture_complete`・`cleanup_status`・`implementation_revision`を返します。Activityの`route_results`（`testware` routeのみ）はこれらに加え、Runの選定情報`testware_ref`・`executor_owner`・`selection_basis`もそのまま投影し（`manual`のrouteには追加しません）、次の場合は`完了`にしません。`e2e` routeの`route_results`には、実行対象を照合できるようRunの`e2e_testware_ref`だけを投影します（実開始・結果確定・revision・cleanupの判定規則は変更しません）。

- `cleanup_status`が無い・`未確認` / `失敗` / `一部失敗` / `進行中`などの未終了状態: 未確認として扱い、`対象なし`へ読み替えません。完了に使えるのは`成功` / `対象なし` / `意図的に残した状態`だけです。
- `attempt_ref`が空、または`raw_capture_complete`が`true`でない: `実行中`のままです。

`manual` / `e2e` routeのcleanup既定値は旧形式の互換のため変更しません。`testware-execution`の正式な返却項目は担当G（PR #29）の成果物で確定し、PR #22でこの契約と照合します。

## TCなし補助testwareの実施義務

Runの`auxiliary_routes[]`各entryは`testware_ref`、`executor_owner`（`e2e-test-execution` / `testware-execution`）、`implementation_revision`、`selection_basis`、`completion_required`（真偽値）、`execution_ref`を持ちます。

- `completion_required=true`: 利用者の明示実行指示（`selection_basis: "user_explicit"`）または有効なpolicy（`"policy"`）で今回実行する補助testwareとして選定された。
- `completion_required=false`: 参照候補・実行不要の記録（`selection_basis: "reference_only"`）。未開始でもActivity完了を妨げない。
- 選定根拠が不明なまま値を推測しません。`completion_required`を持たない旧entryと、`auxiliary_routes`に無い旧`auxiliary_testware_refs`のrefは**義務不明**です。
- TCなし補助は`tc_ref`を持たず、TC routeと`execution_ref`を共有しません。補助の件数・結果はTCのexecution / coverage分子へ加算しません。

補助routeのsource executionは、TC routeと同じ項目に加えて`attempt_ref`（実run / attempt）、`raw_capture_complete`（raw結果取得の完全性）、`cleanup_status`、`implementation_revision`を返します。Activityの`auxiliary_route_results`はこれらをそのまま投影します。補助の`cleanup_status`をsourceが返さない場合は`対象なし`へ読み替えず`未確認`として扱い、確認できるまでActivityを`完了`にしません（TC routeの旧形式の既定値は変更しません）。

`select_auxiliary_testware()`は`testware_details`（owner・実装revision）が無い呼び出しでは選定結果だけを返し、`execution_ready: false`でrouteにownerとrevisionを含めません。実行可能なRunにするにはownerとrevisionを解決して`execution_ready: true`を得てから`auxiliary_routes`を保存します。

## Activityのmachine artifact形（抜粋）

`source_executions`は`execution_ref`をkeyとするobject、`tc_execution_state`は`tc_ref`をkeyとするobjectです（配列にしません）。`route_results[]`はTC routeごと、`auxiliary_route_results[]`は補助routeごとに1要素で、ownerのsourceから投影します。

```json
{
  "artifact_type": "activity",
  "route_contract_version": "2",
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": {
    "EXEC-T-1": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "<Runの値>",
      "attempt_ref": "<attempt ref>",
      "raw_capture_complete": true,
      "cleanup_status": "対象なし"
    }
  },
  "tc_execution_state": { "TC-1": "executed" },
  "route_results": [
    {
      "tc_ref": "TC-1",
      "route_ref": "testware:TC-1",
      "route_type": "testware",
      "execution_ref": "EXEC-T-1",
      "testware_ref": "<Runの値>",
      "executor_owner": "testware-execution",
      "selection_basis": "<Runの値>",
      "executed": true
    }
  ],
  "auxiliary_route_results": [
    {
      "testware_ref": "<ref>",
      "completion_required": true,
      "execution_ref": "EXEC-A-1",
      "executed": false
    }
  ]
}
```

上は形を示す抜粋です。全項目を持つ完全な例は`evals/output/cases/reg-out-003`（Run）・`reg-out-004` / `reg-out-005`（Activity）です。

## Runとの照合

Activityの`route_results` / `auxiliary_route_results`・`completion_required`・件数は、Activity自身の申告であり、それだけでは検証済みになりません。保存済みRunを正本として、次を照合します。

- **Run自体が有効であること**。保存済みRunとして渡されたartifactの`artifact_type`は厳密に`"run"`で、`activity`・`baseline`・空文字・未指定・不正な型は拒否します（`REG-D018`と`verify_activity_against_run()`が同じ規則）。`project_activity()`は投影helperであり、`artifact_type`を省略した簡略なRun入力も従来どおり受け付けます。未知の`route_type`、`tc_ref` / `route_ref`の欠落、`e2e`の`e2e_testware_ref`の欠落・不正型、補助entryの`executor_owner` / `selection_basis`の不正型、`auxiliary_testware_count`の欠落・不正型・不一致、`testware` routeの`testware_ref` / `executor_owner`（`testware-execution`）/ `implementation_revision` / `selection_basis`の欠落・不正、不正な`execution_ref`、重複route、不正な補助entryや補助refを含むRunは、再投影がActivityと一致しても正当な実施義務として受け入れません（`REG-D008`と同じ規則を`REG-D018`が再利用します）。`route_contract_version`が無い旧Runでは、この検査のうち版に関する項目だけを免除します。
- Runの`required_routes`と`auxiliary_routes`（旧形式の`auxiliary_testware_refs`のrefを含む）の各entryが、Activityに欠落・追加・重複なく現れること。TC付き`testware` routeでは`testware_ref`・`executor_owner`・`selection_basis`も識別子として比較し、`route_ref`・`execution_ref`・revisionを維持したまま選定情報だけを変更した場合も不一致です。`e2e` routeでは`e2e_testware_ref`も識別子として比較し、同じ実行結果のまま実行対象の参照先だけが変わった場合も不一致です。
- 各補助の`completion_required`・`selection_basis`・`executor_owner`・`implementation_revision`・`execution_ref`がRunの値と一致すること。Activity側で必須補助を削除したり`completion_required`を変更したりした場合は不一致です。
- `activity_state`が、Runのrouteと実施義務・Activityのowner `source_executions`だけから独立に再計算した状態と一致すること。Activityの`executed` / `blocked` / 件数 / 申告状態は再計算に使いません。実際は完了済みのActivityを`実行中`等へ変更した場合も、未開始・blocked・結果未確定のActivityを別状態へ変更した場合も不一致です（`REG-D011`はRun無しでもActivity内のrouteとsourceから同じ再計算を行い、`REG-D018`はRunから行います）。旧形式のActivityは状態を再計算しません。

入口は`validator.py`の`validate_activity_against_run(activity, run)`と、決定論的評価の`REG-D018`（`validate(text, expected, eval_id, run=...)`の`run`引数、またはfixtureの`expected.json`の`run`）です。runtimeでは`regression_runtime.py::verify_activity_against_run(run, activity)`が、Runから`project_activity()`で再計算した投影とActivityを比較します。Runを渡せない経路では、`v2` Activityの`完了`の主張を`REG-D018`で失敗とし、それ以外の状態は警告にとどめます（Run照合済みとは扱いません）。旧形式のActivityは対象外です。保存・承認・条件付き更新による実際のRun取得は担当Aの共通契約に従い、PR #22で結合します。

## 不正入力の扱い

`execution_ref`・`testware_ref`・route配列・source等の型が不正（配列・object・空文字・非list）でも、検証は例外で中断しません。`validate_required_routes()` / `validate_auxiliary_routes()`は`valid: false`と`issues`を返し、`project_activity()`は`invalid_execution_ref:<ref>`・`invalid_required_route:<index>`・`invalid_required_route_type:<tc_ref>`・`unsupported_route_contract_version`・`source_executions_not_object`・`duplicate_required_route:<key>`等の不正な入力を`unresolved`へ追加し、Activityを`完了`にしません。`project_activity()`は、同じ検証（`validate_required_routes()` / `validate_auxiliary_routes()`）でRun自体の不正を確認してから状態を導くため、未知のroute種別を含むRunは`完了`になりません。`verify_activity_against_run()`は不正なRunを`run_contract_invalid`として`valid: false`にします。`REG-D018`は不正なRun・補助refを集合へ入れる前に型を確認して失敗とし（黙って除去しません）、例外で中断しません。`select_auxiliary_testware()`は`invalid_refs`を持つ`unresolved`を返し、決定論的validatorは不正型を失敗として扱います。

## Activity完了判定

`完了`は、今回Runの**全required TC route**と`completion_required=true`の**全補助route**について、実開始・owner側result確定・source result projection・（補助は）`raw_capture_complete`と`attempt_ref`・cleanup終了を確認でき、未解決と義務不明が無い場合だけです。両集合が空なら`完了`にしません。`completion_required=false`の候補は完了を妨げません。

| 状況                                                                | `activity_state`                                                                          |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 必須補助またはTC routeが未開始・blocked、cleanup未確認、未解決あり  | いずれかのrouteまたは必須補助が開始済み: `部分完了（ブロック中あり）`、なし: `ブロック中` |
| 義務不明の補助がある（旧Run）                                       | 上と同じ（`auxiliary_obligation_unknown:<ref>`を`unresolved`へ追加）                      |
| 実開始済みだが結果未確定・raw未取得・`attempt_ref`なし（timeout等） | `実行中`                                                                                  |
| 補助のみのRunで必須補助が全て未開始かつblockedなし                  | `未開始`                                                                                  |
| 上記以外で全義務を確認                                              | `完了`                                                                                    |

状態の判定は論理TC単位ではなくrouteの開始単位で行います（同じTCの一部のrouteだけ開始済みで残りがblockedなら`部分完了（ブロック中あり）`）。TC件数（`executed_tc_count`等）は全routeが開始済みのTCだけを数えます。`auxiliary_required_completed_count`は実開始・結果確定・raw取得・`attempt_ref`に加えてcleanup終了（`成功` / `対象なし` / `意図的に残した状態`）まで確認できた必須補助だけを数えます。

実開始前のblockを実行済みにせず、skip・未実行・runnerエラー・試行途中timeoutを`executed` / `完了`へ変換しません。retryはsourceが返す最新attemptの確定結果だけを投影します。TC route / 補助routeとも、ownerが返した`implementation_revision`がRunの値と一致しない結果は実行済みに数えず、`implementation_revision_mismatch:<ref>`を未解決へ追加します。`testware` route・`completion_required=true`の補助routeでRunの`implementation_revision`が空・欠落している場合は照合できないため実行済みに数えず、`implementation_revision_missing:<ref>`を未解決へ追加します。

## 旧Run / Activityの互換

- `route_contract_version`が無いRun / Activityは旧形式です。読取互換で保持し、保存済みの`完了`を遡って変更しません。旧Activityは従来規則（TC routeだけ）で検証します。
- 旧形式のentryに`completion_required`を付けるには`route_contract_version: "2"`が必要です（versionなしで義務だけ主張できません）。`project_activity()`と`resolve_auxiliary_obligations()`も、versionなしのRunが持つ`completion_required`を信用せず義務不明として扱い、現在の利用者指示・policyで根拠を再確認します。
- `route_contract_version`が存在するのに`"2"`以外（数値`2`・`"3"`等）の場合は、旧形式として扱わずvalidatorが拒否します。旧形式として扱えるのはfield自体が無い場合だけです。
- 旧Runを新しい実行へ再開するときは`resolve_auxiliary_obligations()`で現在の利用者指示・policy・旧選定証拠から義務を解決します。解決できない補助が残る場合は`blocked`のままです。解決後のRunは新revisionとして保存し、完了済みActivityは書き換えず新Activityを使います。
