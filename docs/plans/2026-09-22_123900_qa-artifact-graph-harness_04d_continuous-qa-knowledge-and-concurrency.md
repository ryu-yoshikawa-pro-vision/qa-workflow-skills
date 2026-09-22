# Regression / Exploratory Testing 統合Plan

## 1. 目的

PR #13では個々のQA workflowを実行できるだけでなく、複数のQA活動が同時進行しても成果物・知識・環境が混線せず、活動を重ねるほど再利用可能な知見が蓄積されることを要件にします。

対象は次です。

- テスト対象や関連する仕組みについて継続利用する知識
- 繰り返し有効だったテスト観点
- テスト環境、test user、test data、外部依存、cleanup等の運用知識
- Activity / Session / executionから得た知見の再利用
- 複数workflowの独立状態
- 共有QA成果物の並行更新
- 共有テスト環境・データを複数workflowが同時利用する場合の安全性

Graph DBや汎用knowledge management frameworkは追加しません。

## 2. 現在の正本を優先する

再利用したい情報が既存の正本へ属する場合、新しい知識成果物へ複製しません。

| 情報 | 優先する正本 |
| --- | --- |
| currentな仕様・期待挙動 | `spec-analysis` / Authority |
| Product Risk / test objective / test focus | `test-analysis` |
| TR / TCN / CI / TC | 各design Skill |
| currentなUI情報・実対象で確認したふるまい | `test-target-inspection` |
| execution / result / evidence | PR #12 / E2E |
| Regression履歴 | Regression Activity |
| Exploration履歴 | Exploratory Session |
| 案件固有の実行条件・方針 | project context |

新しい知識成果物へ保存するのは、複数session / workflowで再利用する価値があり、上記の正本へそのまま入れると責務が不自然になる情報だけです。

## 3. 継続利用する知識

想定する内容:

### テスト対象・関連する仕組み

- feature間・service間の依存
- 非同期jobや外部連携の成立条件
- 状態伝播やcache等、テスト時に理解しておく必要がある仕組み
- 実対象を確認するときの既知の注意点

仕様Authorityではありません。期待挙動を確定する必要がある内容は`spec-analysis`へ戻します。

### テスト観点

- 過去に繰り返し問題になった境界
- 変更時に確認価値が高かった観点
- Explorationで有効だった観測観点
- 特定条件で見落としやすい組合せ

Product Riskや正式なtest conditionへ昇格すべき内容は`test-analysis` / design Skillへ戻します。

### テスト環境

- environment / version / configurationの特徴
- test user / roleの利用条件
- test data準備・cleanup上の注意
- 外部service / accountの制約
- 並行利用可否
- 既知の環境依存挙動

secret実値は保存しません。

## 4. 知識成果物の最小契約

project-localな知識成果物を、project contextの「既存QA成果物」から一意に発見できるようにします。

Graph DBや汎用registryは前提にしません。knowledge entryの論理契約はこのPlanで固定し、物理保存形式だけを実装前の未確定事項として残します。

各entryは最低限次を持ちます。

- stable entry ref
- entry revision / content identity
- 種別: テスト対象・仕組み / テスト観点 / テスト環境
- 内容
- 適用対象 / scope refs
- 適用environment / version条件
- provenance source refs / revisions
- currentness dependency refs / revisions
- 最終確認条件 / 最終確認時点
- 状態: 有効 / 要再検証 / 置換済み
- 置換先ref（置換済みの場合）
- 関連するcurrent QA成果物ref

`provenance source`は「どこからその知識を得たか」を表します。`currentness dependency`は「何が変わったら、その知識をcurrentとして再利用する前に再確認が必要か」を表します。同じrefである必要はありません。

knowledge artifact全体のrevisionだけを全entryのrevisionとして扱いません。無関係なentry更新だけで全knowledge利用workflowをstaleにしないため、論理上はentry単位でrevision / content identityを持ちます。

本文をActivityやFindingから無条件にコピーしません。

## 5. 知見の反映

Activity / Session / executionで得た情報は、次の順に扱います。

1. 既存の正本へ属するか判定する。
2. 属する場合は最も早い責任Skillへroutingする。
3. 正本更新後は知識成果物へ本文を複製せずrefで接続する。
4. 既存正本へ自然に置けないが継続再利用価値がある場合だけ、Activity / Session / Finding上でknowledge候補としてfollow-upする。
5. source、適用scope、environment / version条件、currentness dependency、再利用価値を確認できるまでknowledge成果物へcurrent entryとして追加しない。
6. 検証済みのentryだけを`有効`として追加する。
7. 一度`有効`だったentryがcurrentness dependency変更により再確認を必要とする場合だけ`要再検証`へ遷移する。
8. `有効`entryだけを後続workflowの入力として利用する。

未検証candidateをknowledge成果物へ蓄積するための追加stateは作りません。candidateは元のActivity / Finding / Follow-upに残します。

Finding / Observationを自動的に知識へ昇格しません。

仕様Authority、Product Risk、TC等への昇格も既存責任Skillを経由します。

knowledge候補を意味上`有効`にする責任主体は未確定です。`qa-workflow`へdomain判断を持たせる案は採用しません。既存Skillへ分散するか、専用Skillを1件追加するかは追加リサーチで決定します。

## 6. 知識の利用

`qa-workflow`はworkflow開始時または途中で新しい対象を扱うとき、project contextからknowledge rootを発見し、今回scopeに関係するentryだけを候補にします。

全知識を毎回LLMへ投入しません。

候補をscope / 種別 / environment / version / stateでdeterministicに絞り、各候補のcurrentness dependencyがcurrentか確認してからAgentへ渡します。dependency revisionが一致しない、またはcurrentnessを確認できないentryは`要再検証`としてcurrent判断へ使用しません。

利用したentryはworkflow / Activity / Sessionへ次を残します。

- knowledge entry ref
- entry revision / content identity
- 今回どの判断で利用したか

knowledge成果物が後から更新されても、過去Activity / Sessionを書き換えません。

過去結果は当時利用したentry revisionに対する履歴として残します。

現在のQA判断として再利用する場合はcurrent entry revision、state、currentness dependencyを確認します。

## 7. workflow identity

同時進行するworkflowを1つの共有状態表へ混在させません。

`qa-workflow`で継続管理する各workflowは一意な`workflow_ref`を持ちます。

workflow stateには少なくとも次を追加します。

- workflow_ref
- workflow objective / requested outcome
- scope
- started source refs / revisions
- current state
- current Skill / 対象・実行範囲
- used knowledge refs / revisions
- used environment / shared resource refs
- produced artifact refs
- related Activity / Session refs
- blocked / 要再検証
- optional related workflow refs

`qa-workflow`が複数sessionへ跨いで継続管理するworkflowは、1 workflow = 1 persisted state artifactとします。

各state artifactはstate revision / content identityを持ち、更新時は保存先が提供するSHA / revision / ETag等によるCASを使用します。読み込み時revisionとcurrent revisionが一致しない場合は古いstateで上書きせず、current stateを再読込して再評価します。

単発のstandalone Skill利用にまでpersisted workflow stateを強制しません。

プロジェクト全体に「現在実行中のworkflowは1件だけ」という前提を置きません。

## 8. workflow snapshotとcurrent state

各workflowは利用した上流成果物・project context・knowledge・environment条件のref / revisionを固定して記録します。

進行中に別workflowがcurrent成果物を更新しても、進行中Activity / execution / Sessionの過去snapshotを途中で差し替えません。

currentnessはイベント駆動の即時通知ではなく、次のcheckpointでdeterministically再確認します。

- workflow / Run開始時
- resume時
- まだ開始していない新しいexecution / side-effect等のmutable operationを開始する直前
- latest current stateに対する完了を主張する直前
- 過去成果物をcurrentとして再利用する直前

確認対象:

- PR #11 Machine Entity / fingerprint / dependency
- project context ref / revision
- knowledge entry ref / revision / currentness dependency
- test-target-inspection等のcurrent artifact ref / revision
- environment / shared resource condition

影響するscopeが変わっていれば`要再検証`へ戻します。PR #11のdependency / fingerprintで影響範囲を安全に限定できる場合はその範囲だけ再検証し、限定できない場合は安全側に対象scopeを再評価します。

既に開始済みの操作を一律に中断しません。安全に完了できる場合は固定snapshotに対するhistorical resultとして閉じます。ただし変更後のcurrent stateに対する結果とは扱いません。

これにより「実行中に別作業が入ったため過去結果自体が消える」ことと、「古い結果をcurrentと誤認する」ことを分離します。

## 9. 共有成果物の並行更新

共有するcurrent成果物を更新する場合、既存の`test-target-inspection`と同じ考え方を共通原則にします。

- 読み込んだrevision / SHA / ETag / content identityを保持する
- 保存時にcurrent revisionが変わっていないことを確認する
- 保存先が条件付き更新を提供する場合はそれを利用する
- 保存前に別workflowの更新を検出した場合は古い内容で上書きしない
- semantic contentの競合をLLMが無条件に自動mergeしない

### scopeが重ならない場合

自動rebase / partial updateを許可するのは、owner Skillがdeterministic partial update boundaryを明示的に定義しているartifactだけです。

さらに次をすべて満たす場合に限定します。

- update scopeがdisjoint
- 対象scopeが依存するupstream revision / fingerprintが変わっていない
- cross-scope invariantを壊さないことをowner contractで確認できる
- current成果物を再読込してからscope外current内容を保持し、対象scopeを再適用する

stable IDが異なる、または見た目上別featureであることだけでは自動merge可能と判断しません。

### scopeが重なる、または判定できない場合

current成果物を再読込し、最も早い責任Skillで該当scopeを再評価します。

「最後に保存したworkflowが勝つ」という規則は採用しません。

## 10. cross-workflow stale伝播

workflow Aが利用しているcurrent Entityをworkflow Bが更新した場合、PR #11のcurrent Entity / fingerprint / dependency契約を利用してAの影響範囲を判定します。

- workflow Aのhistorical Activity / execution結果は書き換えない
- Aがまだ進行中で、変更がAの完了判断へ影響する場合は該当scopeを`要再検証`
- Aがすでに完了している場合は過去結果として保持し、latest current state向けの再利用時にstaleを検出する
- 無関係なworkflowまで一律に再実行しない

workflow同士を直接依存させるのではなく、共有したEntity / artifact revisionを介して影響を判定します。

## 11. 共有テスト環境・データ

複数workflowが同時に実対象を操作すると、成果物の競合だけでなくtest user / test data / tenant / external account等の状態競合が起こり得ます。

実操作を行うActivity / Session / executionは、利用する共有mutable resourceを可能な範囲で明示します。

例:

- environment
- tenant / workspace
- test user / role
- test data namespace / record
- external account
- side-effect対象

基本方針は次の優先順位で固定します。

1. workflowごとに独立resourceを使える場合は分離する。
2. 分離できず既存の外部reservation / exclusive ownership機構がある場合はそれを利用する。
3. 外部機構がなく、保存先がatomicなCASを保証できる場合だけproject-local reservation recordを利用する。
4. いずれも利用できずshared mutable resourceへの相互影響を否定できない場合は、自動並行実行を開始せずblockする。

同じresourceでもread-only / parallel-safeで相互影響がないことを明示できる用途はreservation不要です。

project-local reservationを使う場合は最低限、resource ref、workflow ref、関連Activity / Session ref、予約状態、reservation revisionを持ち、acquire / releaseともCASで競合を検出します。単なるMarkdownの存在確認をlockとして扱いません。

自動expiry付きlease、distributed lock service、environment managerはv1では追加しません。workflow異常終了時は安全側に予約を残し、明示的なrecoveryで解放します。

cleanupは自workflowが所有または予約したresource範囲だけを対象にし、他workflowが作った状態を削除しません。

resource / environment変更を検出した場合、実行結果の有効性を再確認します。

## 12. Graph / provenanceとして保持する関係

Graph DBは追加しません。

最低限、direct refで次を追えるようにします。

```text
workflow
├ used → QA artifact revision
├ used → knowledge entry revision
├ used → environment / resource condition
└ produced → Activity / Session / artifact

Activity / Session
├ used → TC / Risk / knowledge / environment
├ generated → Observation / Finding / Result
└ informed → follow-up workflow / artifact

knowledge entry
├ derived from → Activity / Finding / inspection / existing artifact
├ applies to → target / environment scope
└ superseded by → newer knowledge entry
```

実装上は既存のref / revision fieldを優先し、上記の関係名を汎用Graph schemaとして新設することは必須にしません。

queryはdirect ref + deterministic scanを優先します。

## 13. project contextへの追加

project contextは知識本文の保管庫にしません。

入口として次を追加する予定です。

- 継続利用するQA知識成果物の場所
- 共有テスト環境 / resource利用方針の場所
- workflow / Activity history root

既存のenvironment設定、test user、cleanup等の案件固有値は引き続きproject contextへ保持します。

## 14. 必須評価

### 知識

- Observation / Findingを無条件に有効知識へ昇格しない
- 仕様に属する知識は`spec-analysis`へ戻る
- Risk / test focusに属する知識は`test-analysis`へ戻る
- currentな実対象情報は`test-target-inspection`を正本にする
- 既存正本へ置けない再利用知識だけ知識成果物へ残る
- source ref / revisionなしのentryを有効扱いしない
- 適用version / environment外のentryをcurrent判断へ使わない
- 置換済みentryをcurrentとして利用しない
- 利用したknowledge revisionをworkflow / Activityから追える
- secret実値を保存しない

### 複数workflow

- 2 workflowが独立した`workflow_ref`を持つ
- 同時進行してもstateを上書きしない
- disjointなartifact scope更新は既存current内容を失わず成立する
- 同一scopeを同じbase revisionから更新した場合、後勝ち上書きをしない
- workflow A開始後にBがAの依存Entityを更新すると、Aの影響scopeが完了前に`要再検証`になる
- Bの変更がAへ無関係ならA全体を再実行しない
- Regressionがsnapshot v1で実行中にv2が作られても、Run v1の履歴は保持する
- Run v1をv2のcurrent結果として扱わない

### 共有環境

- 同じtest user / dataを2 workflowが変更し観測へ影響するfixtureで、並行実行を許可しない
- workflow別に分離されたresourceなら並行実行できる
- cleanupが別workflowのresourceを削除しない
- shared resource policy不明時に同時利用可と推測しない

## 15. 実装前に追加調査が必要な点

確定していない設計判断は次の2点だけとします。

1. 継続QA知識の意味上のlifecycleを誰が所有するか。既存Skillへ分散するか、継続QA知識専用Skillを1件追加するかを決定する。`qa-workflow`へdomain判断を持たせる案は採用しない。
2. knowledge entryの論理的なentry revision / CAS要件を満たす物理保存形式。単一project artifact内のentry管理にするか、fixed root配下のentry別artifactにするかは、保存先のCAS粒度・portability・競合頻度を踏まえて決定する。

次は方針を確定済みです。

- cross-workflow currentnessは中央coordinator / event busではなくcheckpointで検出する
- shared mutable resourceはisolation → 既存reservation → CAS付きproject-local reservation → blockの順で扱う
- relation indexはfixed root scanの実測不足が確認された場合だけ検討する

PR #11 / #12はまだPlan段階のため、実装開始時にはmerge後の実契約を再確認し、上記契約を満たさない差分があればPR #13側を調整します。

