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

継続QA知識の意味上のlifecycleは新規`qa-knowledge`が担当します。

Graph DB、汎用knowledge management framework、汎用artifact registryは追加しません。

## 2. 現在の正本を優先する

再利用したい情報が既存の正本へ属する場合、QA knowledgeへ第二の正本として複製しません。

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

`qa-knowledge`へ保存するのは、複数session / workflowで再利用する価値があり、上記正本へそのまま入れると責務が不自然になる情報だけです。

`qa-knowledge`は仕様Authority、Product Risk、TR / TCN / CI / TC、current実対象情報の内容を自身で確定しません。これらに属する候補を識別した時点で正本ownerへroutingします。

## 3. 継続利用する知識

### テスト対象・関連する仕組み

例:

- feature間・service間の依存
- 非同期jobや外部連携の成立条件
- 状態伝播やcache等、テスト時に理解しておく必要がある仕組み
- 実対象を確認するときの既知の注意点

仕様Authorityではありません。期待挙動を確定する必要がある内容は`spec-analysis`へ戻します。

### テスト観点

例:

- 過去に繰り返し問題になった境界
- 変更時に確認価値が高かった観点
- Explorationで有効だった観測観点
- 特定条件で見落としやすい組合せ

Product Risk / test focusや正式なTest Conditionへ昇格すべき内容は`test-analysis` / design Skillへ戻します。

### テスト環境

例:

- environment / version / configurationの特徴
- test user / roleの利用条件
- test data準備・cleanup上の注意
- 外部service / accountの制約
- 並行利用可否
- 既知の環境依存挙動

secret実値は保存しません。

## 4. 保存形式

project contextからproject-localなfixed knowledge rootを一意に発見できるようにします。

canonicalな物理単位は次です。

```text
<knowledge-root>/
├─ <entry-ref-1>.md
├─ <entry-ref-2>.md
└─ <entry-ref-3>.md
```

**1 knowledge entry = 1 independently versioned artifact** とします。

次を固定します。

- project contextにはknowledge本文を埋め込まずrootだけを保持する
- 1つの巨大なproject knowledge artifactへ全entryを格納しない
- central manifest / indexを必須にしない
- entry追加のためのglobal mutable counterを作らない
- fixed rootをdeterministicに列挙してdiscoveryする
- root全体のrevisionやrepository HEADをentry revisionとして使わない
- directory shardingは実測上必要になるまで設計しない
- relation indexは実測上必要になるまで設計しない

Markdown本文のmachine-readable block等、entry artifact内部のserialization詳細はPR #11 / #12 merge後の既存artifact/parser実装を確認して決定します。

## 5. knowledge entry契約

各entryは最低限次を持ちます。

- stable `entry_ref`
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

### entry revision

`entry_revision`はentry artifact自身のstorage revision tokenです。

`entry_revision`は読み込んだartifact versionを識別するtokenであり、それ単体をatomic writeの実装とはみなしません。existing entryを保存するときは、保存先が提供する実際のatomic conditional writeへexpected revisionとして渡せるtokenまたはそれと対応するstorage conditionを使います。

GitHub Contents API等で対象pathのblob SHAをconditionとして更新できる場合はその機構を使います。native Gitで共有branchへpublishする場合は、blob SHAの事前比較だけで済ませず、共有mutable pointであるbranch / refをexpected old commitで条件付き更新し、競合後にtarget entryを再確認します。採用する保存経路ごとのatomic primitiveはStep 0でPR #11 / #12 merge後の実装と照合して固定します。

entry本文へ自分自身のstorage SHAを書き込むことは要求しません。workflow / Activity / Sessionは利用した`entry_ref + entry_revision`を保持し、historical provenanceへ使うrevision tokenは実装時に当時のartifact内容を再取得できることも確認します。

### content identity

storage revisionだけでは後続QA判断へ影響する意味変更とmetadata-only変更を区別できない場合、PR #11のcontent fingerprintと同じ考え方でsemantic fieldから決定論的な`content_identity`を持たせます。

保存先のrevision tokenが必要な意味同一性を十分に表現できる場合、追加hash layerを重複実装しません。

### provenanceとcurrentness

`provenance source`は「どこからその知識を得たか」を表します。

`currentness dependency`は「何が変わったら、その知識をcurrentとして再利用する前に再確認が必要か」を表します。

同じrefである必要はありません。

## 6. qa-knowledgeによるlifecycle

Activity / Session / executionで得た情報は、次の順に扱います。

1. Finding / Observation / Activity上でknowledge候補として残す。
2. `qa-knowledge`が既存正本へ属するか分類する。
3. 既存正本へ属する場合は、そのowner Skillへroutingする。
4. 既存正本へ自然に置けない場合だけ、継続再利用価値を評価する。
5. scope、environment / version applicability、provenance、currentness dependencyを確認する。
6. 条件を満たす場合だけknowledge entryを作成 / 更新する。
7. dependency変更でcurrentnessを確認できなくなったentryはcurrent判断へ使わず、`要再検証`として扱う。
8. 再検証後、同一knowledge identityなら同じentryを新revisionへ更新する。
9. semantic identityを別entryとして扱う必要がある場合だけ旧entryを`置換済み`にしてreplacement refを持たせる。

未検証candidateをknowledge成果物へ蓄積するための追加stateは作りません。candidateは元のActivity / Finding / Follow-upに残します。

Finding / Observationを自動的にknowledgeへ昇格しません。

## 7. qa-knowledgeが担当しないこと

`qa-knowledge`は次を担当しません。

- specification Authority確定
- Product Risk / test focusの新規識別・採点
- TR / TCN / CI / TC設計
- current実対象の観測そのもの
- test execution
- Findingの原因分析
- Regression membership / selection
- Exploration Sessionの実行
- workflow orchestration

例えば「これは仕様として正しいか」は`spec-analysis`が判断します。

`qa-knowledge`が判断するのは、「これは仕様正本へroutingすべき候補であり、residual knowledgeとして第二の正本を作るべきではない」ところまでです。

## 8. knowledgeの利用

workflowがcurrentなknowledgeを利用するだけの場合、必ずしも`qa-knowledge`を起動しません。

`qa-workflow`またはdomain Skillはproject contextからknowledge rootを発見し、scope / 種別 / environment / version / stateでdeterministicに候補を絞ります。

各候補について、

- entry revision
- state
- currentness dependency
- applicability

をcurrent値と照合し、利用可能なentryだけをAgent入力候補にします。

全knowledgeを毎回LLMへ投入しません。

利用したentryはworkflow / Activity / Sessionへ次を残します。

- knowledge entry ref
- entry revision
- content identity（採用する場合）
- 今回どの判断で利用したか

knowledge entryが後から更新されても、過去Activity / Sessionを書き換えません。

## 9. entry作成・更新のCAS

### 新規entry

new knowledge identityの場合だけ新規entryを作成します。

新規作成は、`qa-knowledge`がidentity関係を判断した**completeなknowledge root snapshot**とpublishを競合検出可能な形で結び付けます。同じcandidateを並行処理する2 workflowが、それぞれ別`entry_ref`へcurrent entryを作れる状態を許可しません。

保存先では次のどちらかを使用します。

1. semantic identityからowner contractでstableなcanonical identity materialを確定でき、同一identityを同じcreate targetへ決定論的に解決できる場合、そのtargetへatomic create-if-absentする。
2. 同一targetへ収束させられない場合、identity判定に使用したknowledge namespace / branch snapshotのexpected revision付きでpublishする。publish前にsnapshotが変わっていれば新entryを保存せずcurrent rootを再読込し、既存entryとのidentity関係を最初から再評価する。

`entry_ref`の具体文字列表現は実装時に既存ID規約とportabilityを確認して決定します。global mutable counter、central manifest、global semantic lock、vector DBは追加しません。

同じcreate targetに別identityのartifactが存在することを確認した場合だけ真のidentity collisionとして扱い、別targetを使用します。「同じrefが存在した」という理由だけで別refを生成してsemantic identity判定を迂回しません。

### 既存entry更新

```text
read entry @ revision R1
→ qa-knowledgeが新内容を確定
→ expected revision = R1 を保存先のatomic conditional writeへ渡す
```

currentがR1のままなら成功します。

currentが変更済みなら保存しません。

### CAS conflict

同じentryが別workflowにより変更されている場合はsemantic auto-mergeしません。

```text
CAS conflict
→ current entryを再読込
→ qa-knowledgeがsource / applicability / dependencies / current contentを再評価
→ 必要ならcurrent revisionをbaseに新しい提案を作成
```

別entryだけが変更され、target entryのexpected revisionが変わっていないことを機械確認できる場合はsemantic mergeなしでretryできます。

## 10. update / replacement

通常の再検証や内容更新は同じ`entry_ref`の新revisionにします。

新entryへのreplacementは次のような場合だけです。

- semantic identityが別物になった
- 1 entryを複数entryへ分割する
- applicabilityを独立entryへ分離する
- 既存の別entryへ統合する

旧entryとnew entryを同時に更新する必要がある場合、保存先がatomicなmulti-file / multi-record更新を提供するなら利用します。

提供しない場合、このまれなreplacementのためだけにgeneric transaction managerを作りません。安全に一括反映できない場合は当該replacementをblockし、明示的な完了手順へ回します。

## 11. workflow identity

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

`qa-workflow`が複数sessionへ跨いで継続管理するworkflowは、project contextから一意に発見できるproject-local fixed workflow state root配下で1 workflow = 1 persisted state artifactとします。

同じ`workflow_ref`は必ず同じstate artifactへ決定論的に解決します。初回保存はatomic create-if-absentとし、同じ`workflow_ref`で別state artifactを並行作成しません。

各state artifactはstate revision / content identityを持ち、更新時はそのartifactのexpected revisionを保存先のatomic conditional writeへ渡します。競合時はcurrent stateを再読込し、stale stateを保存しません。

単発のstandalone Skill利用にまでpersisted workflow stateを強制しません。

## 12. workflow snapshotとcurrent state

各workflowは利用した上流成果物・knowledge・environment条件のref / revisionを固定して記録します。

project contextは次を分けて保持します。

- project context全体のref / revision: workflow開始時のprovenance snapshot
- currentness判定へ実際に利用した項目: stable locator + content identityまたは正規化値

project context全体のrevision差だけでworkflow全体を`要再検証`へ戻しません。whole revisionが変わった場合はcurrent contextを再読込し、保存済みの利用項目だけを比較します。未使用項目だけの変更ならcurrentのまま継続し、利用項目を安全に再解決できない場合はcurrent完了をblockします。

進行中に別workflowがcurrent成果物を更新しても、進行中Activity / execution / Sessionの過去snapshotを途中で差し替えません。

currentnessはイベント駆動の即時通知ではなく、次のcheckpointでdeterministically再確認します。

- workflow / Run開始時
- resume時
- まだ開始していない新しいexecution / side-effect等のmutable operationを開始する直前
- latest current stateに対する完了を主張する直前
- 過去成果物をcurrentとして再利用する直前

確認対象:

- PR #11 Machine Entity / fingerprint / dependency
- project context全体のref / revisionと、利用したproject context項目のstable locator + content identityまたは正規化値
- knowledge entry ref / revision / currentness dependency
- test-target-inspection等のcurrent artifact ref / revision
- environment / shared resource condition

影響するscopeが変わっていれば`要再検証`へ戻します。

既に開始済みの操作を一律に中断しません。安全に完了できる場合は固定snapshotに対するhistorical resultとして閉じます。ただし変更後のcurrent stateに対する結果とは扱いません。

## 13. 共有成果物の並行更新

共有するcurrent成果物を更新する場合、既存の`test-target-inspection`と同じ考え方を共通原則にします。

- 読み込んだrevision / SHA / ETag / content identityを保持する
- 保存時にcurrent revisionが変わっていないことを確認する
- 保存先が条件付き更新を提供する場合はそれを利用する
- 保存前に別workflowの更新を検出した場合は古い内容で上書きしない
- semantic contentの競合をLLMが無条件に自動mergeしない

自動rebase / partial updateを許可するのは、owner Skillがdeterministic partial update boundaryを明示的に定義しているartifactだけです。

さらに次をすべて満たす場合に限定します。

- update scopeがdisjoint
- 対象scopeが依存するupstream revision / fingerprintが変わっていない
- cross-scope invariantを壊さないことをowner contractで確認できる
- current成果物を再読込してからscope外current内容を保持し、対象scopeを再適用する

scopeが重なる、または判定できない場合はcurrent成果物を再読込し、最も早い責任Skillで該当scopeを再評価します。

## 14. cross-workflow stale伝播

workflow Aが利用しているcurrent Entity / knowledge / project context / environment conditionをworkflow Bが更新した場合、checkpointでAの影響範囲を判定します。

- historical Activity / execution / Sessionは書き換えない
- 進行中workflowがlatest current stateとして完了する前に影響scopeを再確認する
- PR #11対象Entityはdependency / fingerprintを利用する
- knowledgeは利用したentry revision / content identityとcurrentness dependencyを確認する
- project contextはwhole revision差を検出した後、workflowが利用した項目だけのcontent identityまたは正規化値をcurrent値と比較する
- 未使用project context項目だけの変更ではworkflowをstaleにしない
- 無関係なworkflowまで一律に再実行しない
- 利用dependencyを安全に再解決できず影響範囲を限定できない場合はcurrent完了をblockする

中央coordinator / event busは追加しません。

## 15. 共有テスト環境・データ

複数workflowが同時に実対象を操作すると、test user / test data / tenant / external account等の状態競合が起こり得ます。

実操作を行うActivity / Session / executionは利用するshared mutable resourceを可能な範囲で明示します。

基本方針は次の優先順位で固定します。

1. workflowごとに独立resourceを使える場合は分離する。
2. 分離できず既存の外部reservation / exclusive ownership機構がある場合はそれを利用する。
3. 外部機構がなく、保存先がatomicなCASを保証できる場合だけproject-local reservation recordを利用する。
4. いずれも利用できずshared mutable resourceへの相互影響を否定できない場合は、自動並行実行を開始せずblockする。

同じresourceでもread-only / parallel-safeで相互影響がないことを明示できる用途はreservation不要です。

project-local reservationを使う場合、同じshared mutable `resource_ref`を扱う全workflowが必ず同じcanonical reservation targetへ競合するようにします。resourceごとに別writer用recordを作る方式は許可しません。

reservationは最低限、resource ref、workflow ref、関連Activity / Session ref、予約状態、reservation revisionを持ちます。

- 未予約をrecord absenceで表す場合、初回acquireはcanonical targetへのatomic create-if-absentとする
- persistent recordを使う場合、acquireはexpected revision付き`available → reserved` CASとする
- releaseはcurrent owner / workflowとexpected reservation revisionが一致する場合だけ成功する
- read → file存在確認 → 通常writeを排他保証として扱わない

workflow異常終了時は安全側にreservationを残します。recoveryでは時間経過だけを根拠に解放せず、current reservation revisionを再読込し、owner workflow / Activity / Sessionの状態と必要cleanupを確認します。ownerがactiveか不明、cleanupが失敗 / 未確認 / 一部失敗、または安全な解放を機械判定できない場合は自動releaseせず明示的な確認へblockします。recoveryによるrelease自体もexpected revision付きCASで行います。

自動expiry付きlease、distributed lock service、environment managerはv1では追加しません。

cleanupは自workflowが所有または予約したresource範囲だけを対象にします。

## 16. Graph / provenanceとして保持する関係

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
├ depends on → currentness dependency revisions
├ applies to → target / environment scope
└ superseded by → newer knowledge entry
```

実装上は既存のref / revision fieldを優先し、上記の関係名を汎用Graph schemaとして新設することは必須にしません。

queryはdirect ref + deterministic scanを優先します。

## 17. project contextへの追加

project contextはknowledge本文の保管庫にしません。

入口として次を追加します。

- fixed knowledge root
- fixed workflow state root
- workflow history root
- Activity / Session history root
- shared environment / resource policy

既存のenvironment設定、test user、cleanup等の案件固有値は引き続きproject contextへ保持します。

project context自体を汎用artifact registryにしません。

## 18. 必須評価

### qa-knowledge

- Finding / Observationを無条件にknowledgeへ昇格しない
- specification候補を`spec-analysis`へroutingする
- Product Risk / test focus候補を`test-analysis`へroutingする
- current UI factを`test-target-inspection`へroutingする
- formal Test Conditionへ昇格すべき候補をdesign Skillへroutingできる
- 既存正本へ置けない再利用knowledgeだけentry化する
- environment-specific knowledgeを他environmentへ一般化しない
- source / dependency不足でentryを有効化しない
- `要再検証` / `置換済み`entryをcurrentとして返さない
- same identityの再検証を同じentryのnew revisionへ更新する
- identity変更時だけreplacementを使う

### storage / concurrency

- fixed knowledge rootを完全列挙できる
- 1 entry = 1 artifact
- 別entry更新で無関係entryのrevisionが変わらない
- root / repository HEAD変更だけで全knowledge利用workflowをstaleにしない
- same-entry concurrent updateでは1 writerだけatomic conditional writeが成功する
- CAS conflict後にsame entryをsemantic auto-mergeしない
- 同じsemantic identityを2 workflowが同時createしてもcurrent entryは1件に収束する
- identity判定後にknowledge snapshotが変わった場合、新entryをそのままpublishせずcurrent rootでidentity判定からやり直す
- 異なるsemantic identityの並行createは、一時競合しても再評価後に両方を保存できる
- new entry create時にglobal counter / central manifestを要求しない
- replacementをatomicに閉じられない場合は安全にblockする

### 複数workflow

- 2 workflowが独立した`workflow_ref`を持つ
- 同時進行してもstateを上書きしない
- project contextからfixed workflow state rootを一意に発見できる
- 同じ`workflow_ref`の初回state作成が1つのcanonical state artifactへ収束する
- workflow state自身をatomic conditional writeで更新する
- workflow A開始後にBがAのdependencyを更新するとcheckpointでAの影響scopeを検出する
- workflowが利用したproject context項目を変更すると関係scopeを`要再検証`へ戻す
- workflowが利用していないproject context項目だけを変更してもstaleにしない
- Bの変更がAへ無関係ならA全体を再実行しない
- historical resultをcurrent resultとして扱わない

### 共有環境

- 同じtest user / dataを2 workflowが変更し観測へ影響するfixtureで、並行実行を許可しない
- workflow別に分離されたresourceなら並行実行できる
- 同じresource refが同じcanonical reservation targetへ解決される
- reservation acquire競合で1 workflowだけ成功する
- stale revisionからのrelease / recoveryを拒否する
- owner active状態またはcleanup状態を確認できないrecoveryをblockする
- cleanupが別workflowのresourceを削除しない
- shared resource policy / CASが不足する場合はblockする

## 19. 実装開始条件

継続QA知識について追加Architecture調査は不要です。

実装前に必要なのは、PR #11 / #12がmergeされたlatest `main`で次を再確認することです。

- PR #11のstable identity / content fingerprint / dependency / partial updateの実契約
- PR #12のSHA / revision / ETagベース更新契約
- current artifact parser / validator / project-local artifact保存規約

この再確認で本Planと不整合があれば、既存実装へ無条件に合わせず不整合として解消してから実装します。
