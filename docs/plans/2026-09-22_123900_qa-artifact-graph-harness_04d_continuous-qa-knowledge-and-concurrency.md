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

保存形式やファイル分割は実装前リサーチで決定します。Graph DBや汎用registryは前提にしません。

各entryは最低限次を持ちます。

- stable entry ref
- 種別: テスト対象・仕組み / テスト観点 / テスト環境
- 内容
- 適用対象 / scope refs
- 適用environment / version条件
- source artifact / Activity / Session / Finding / inspection refs
- source revisions
- 最終確認条件 / 最終確認時点
- 状態: 有効 / 要再検証 / 置換済み
- 置換先ref（置換済みの場合）
- 関連するcurrent QA成果物ref

本文をActivityやFindingから無条件にコピーしません。

## 5. 知見の反映

Activity / Session / executionで得た情報は、次の順に扱います。

1. 既存の正本へ属するか判定する。
2. 属する場合は最も早い責任Skillへroutingする。
3. 正本更新後は知識成果物へ本文を複製せずrefで接続する。
4. 既存正本へ自然に置けないが継続再利用価値がある場合だけ知識entry候補にする。
5. sourceと適用範囲を確認できない候補は`要再検証`とし、currentな事実として後続判断へ使用しない。
6. 有効化されたentryだけを後続workflowの入力として利用する。

Finding / Observationを自動的に知識へ昇格しません。

仕様Authority、Product Risk、TC等への昇格も既存責任Skillを経由します。

## 6. 知識の利用

`qa-workflow`はworkflow開始時または途中で新しい対象を扱うとき、project contextから知識成果物のrootを発見し、今回scopeに関係する有効entryだけを候補にします。

全知識を毎回LLMへ投入しません。

利用したentryはworkflow / Activity / Sessionへ次を残します。

- knowledge entry ref
- revision / content identity
- 今回どの判断で利用したか

知識成果物が後から更新されても、過去Activity / Sessionを書き換えません。

過去結果は当時利用したrevisionに対する履歴として残します。

現在のQA判断として再利用する場合はcurrent revisionと状態を確認します。

## 7. workflow identity

同時進行するworkflowを1つの共有状態表へ混在させません。

`qa-workflow`で管理する各workflowは一意な`workflow_ref`を持ちます。

workflow stateには少なくとも次を追加します。

- workflow_ref
- workflow objective / requested outcome
- scope
- started source refs / revisions
- current state
- current Skill / 対象・実行範囲
- produced artifact refs
- related Activity / Session refs
- blocked / 要再検証
- optional related workflow refs

workflow stateはworkflowごとに独立して保存します。

プロジェクト全体に「現在実行中のworkflowは1件だけ」という前提を置きません。

## 8. workflow snapshotとcurrent state

各workflowは利用した上流成果物・project context・知識・environment条件のref / revisionを固定して記録します。

進行中に別workflowがcurrent成果物を更新した場合:

- 進行中Activity / execution / Sessionの過去snapshotを途中で差し替えない
- そのworkflowの結果は固定snapshotに対する履歴として残せる
- latest current stateに対する完了・再利用を主張する前に依存revisionを再確認する
- 影響するscopeが変わっていれば`要再検証`へ戻す
- PR #11のdependency / fingerprintで影響範囲を安全に限定できる場合はその範囲だけ再検証する
- 限定できない場合は安全側に対象scopeを再評価する

これにより「実行中に別作業が入ったため過去結果自体が消える」ことと、「古い結果をcurrentと誤認する」ことを分離します。

## 9. 共有成果物の並行更新

共有するcurrent成果物を更新する場合、既存の`test-target-inspection`と同じ考え方を共通原則にします。

- 読み込んだrevision / SHA / ETag / content identityを保持する
- 保存時にcurrent revisionが変わっていないことを確認する
- 保存先が条件付き更新を提供する場合はそれを利用する
- 保存前に別workflowの更新を検出した場合は古い内容で上書きしない
- semantic contentの競合をLLMが無条件に自動mergeしない

### scopeが重ならない場合

stable ID / update scope等から変更範囲がdisjointであることを決定論的に確認できる場合だけ、current成果物を再読込したうえでscope外current内容を保持し、対象scopeを再適用できます。

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

基本方針:

- workflowごとに独立resourceを使える場合は分離する
- 同じresourceを同時変更しても互いの観測へ影響しないことを明示できる場合だけ並行実行する
- shared mutable resourceで影響を否定できない場合、明示済みproject policyに従って直列化またはblockする
- policyがなく安全性を判定できない場合、同時利用可能と推測しない
- cleanupは他workflowが作った状態を削除しない
- resource / environment変更を検出した場合、実行結果の有効性を再確認する

resource reservation / lease / lockの具体実装は、実装前リサーチで決定します。

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

次は必要性は明確ですが、現時点では最小実装を一意に決め切れません。

1. 継続QA知識を、単一project artifact、対象別artifact、既存project context拡張のどれで管理するのが最小か。
2. テスト対象の内部仕組み・運用知識・テスト観点について、どの既存Skillを有効化の責任主体にするか。既存Skillで不自然になる場合だけ新Skillを検討する。
3. shared mutable resourceを直列化する仕組みを、単なるproject policy、repository内lease artifact、外部environment管理機構のどこまで実装するか。
4. PR #11の`workflow_runtime.py` / Machine Entity stale伝播だけでcross-workflow currentnessを十分に検出できるか。追加のrepo-level coordinatorが本当に必要か。
5. workflow / knowledge historyをfixed root scanで十分扱える規模と運用条件。relation indexはこの検証後も必要な場合だけ検討する。

この5点は、実装前の外部リサーチと最新PR #11 / #12実装確認を完了してから決定します。
