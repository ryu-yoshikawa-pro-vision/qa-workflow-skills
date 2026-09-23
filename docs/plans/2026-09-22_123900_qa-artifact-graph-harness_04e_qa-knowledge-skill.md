# Regression / Exploratory Testing 統合Plan

## 1. qa-knowledgeの目的

`qa-knowledge`は、QA活動で得た情報について、

- 既存QA正本へroutingすべきか
- 継続利用するQA知識として保存する価値があるか
- 既存knowledge entryを更新 / 再検証 / 置換すべきか
- 現在利用可能なknowledgeはどれか

を判断するuser-facing Skillです。

仕様、Risk、TC、current実対象情報そのものの正本にはなりません。

## 2. 起動する要求

単体で開始できる例:

- このFindingを今後のQA知識として残して
- 今回得た知見を今後も再利用できる形にして
- この環境知識がまだ有効か確認して
- 過去のQA知識を確認して
- このknowledge entryを更新 / 置換して
- この知見を既存正本へ入れるべきか、QA knowledgeとして残すべきか判断して
- 半年前のQA knowledgeを棚卸しして、現在利用可能なものを確認して

複数Skillを必要とする要求は`qa-workflow`がオーケストレーションします。

例:

```text
このObservationは仕様へ反映すべきか確認して
→ qa-workflow
→ qa-knowledge | triage
→ spec-analysis
→ 必要ならqa-knowledge | lifecycle update
```

## 3. routingしない要求

次は既存ownerへ直接routingします。

- 現在有効な仕様を整理して → `spec-analysis`
- この変更のProduct Riskを評価して → `test-analysis`
- 現在のUI / accessible nameを確認して → `test-target-inspection`
- Test Requirement / Condition / Caseを設計して → 各design Skill
- Regression対象を選んで → `regression-testing`
- 探索的テストをして → `exploratory-testing`
- テストを実行して → execution Skill

既存の有効knowledgeを入力として使うだけの要求も、必ずしも`qa-knowledge`から開始しません。

例:

```text
この対象について過去の有効なQA知識を使ってテスト分析して
→ qa-workflowまたはdeterministic lookup
→ relevant knowledge refs
→ test-analysis
```

knowledge lifecycle判断が不要なら`qa-knowledge`を中央gatewayにしません。

## 4. 正規の対象 / 実行範囲

workflow stateで識別する必要がある場合、次を正規値とします。

- `triage`
- `create / update`
- `revalidation`
- `lookup / history`

`qa-knowledge`を複数回使うworkflowでは、既存の`Skill + 対象 / 実行範囲`契約で区別します。

## 5. 入力

利用可能な範囲で次を使用します。

- user request
- candidate source refs / revisions
- Observation / Finding / Activity / Session
- execution result / evidence refs
- project context
- fixed knowledge root
- existing knowledge entries
- current QA artifact refs / revisions
- environment / version情報
- currentness dependency候補
- 既存entryのentry revision

入力不足を推測で補いません。

## 6. output

処理結果は次のいずれかです。

### 既存正本へのrouting

- target owner Skill
- source refs / revisions
- routing reason
- unresolved

### knowledge entry create / update / revalidation / replacement

- entry ref
- new entry revision（保存後）
- state
- scope
- applicability
- provenance refs
- currentness dependency refs
- related current QA refs
- replacement ref（必要時）
- unresolved

### lookup / history

- scope条件
- currentness確認済みentry refs / revisions
- 除外した`要再検証` / `置換済み`refs
- completeness
- unresolved

## 7. candidate triage

candidateを受けたら、最初に既存正本へ属するか判定します。

### specification候補

例:

> 保存後は即時反映される

期待挙動や仕様Authorityへ属するため、`spec-analysis`へroutingします。

`qa-knowledge`が仕様として確定しません。

### Product Risk / test focus候補

例:

> 権限境界で過去3回不具合が出た

正式なProduct Risk / test focusとして扱うべきなら`test-analysis`へroutingします。

Risk scoreを`qa-knowledge`が付けません。

### current実対象情報

例:

> 現在の画面ではaccessible nameがX

`test-target-inspection`へroutingします。

長期QA knowledgeへcurrent UI factを二重保存しません。

### design artifact候補

formalなTest Requirement / Condition / Caseへ昇格すべき場合は該当design Skillへroutingします。

### residual knowledge候補

既存正本へ自然に置けず、複数workflowで継続再利用する価値がある場合だけknowledge entry化を検討します。

例:

> stagingの外部jobは状況により数分遅延するため、即FAILにしない

## 8. knowledge entryを有効化する条件

少なくとも次を確認します。

- candidateのsourceを追跡できる
- scopeを特定できる
- environment / version applicabilityを特定できる
- currentness dependencyを特定できる
- 既存正本へ入れるべき内容ではない
- 継続して再利用する具体的な価値がある
- completeなknowledge root snapshotに対して既存entryとのidentity関係を判断できる

確認できない場合はknowledge artifactへ未検証entryを作りません。

candidateは元Finding / Activity / Follow-upに残し、必要な追加確認をroutingします。

## 9. create

new knowledge identityの場合だけ新entryを作成します。

基本契約:

- fixed knowledge root配下
- 1 entry = 1 artifact
- identity判定はcompleteなknowledge root snapshotに対して行う
- identity判定とpublishを競合検出可能な形で結び付ける
- global mutable counterなし
- central manifest更新なし
- 同一semantic identityのcurrent entryを複数作らない

保存先でsemantic identityからstableなcanonical create targetを決定できる場合は、同じidentityを同じtargetへ収束させてatomic create-if-absentします。

canonical targetへ収束させられない場合は、identity判定に利用したknowledge namespace / branch snapshotのexpected revision付きでpublishします。snapshot変更を検出した場合は新entryを保存せず、current rootを再読込して既存entryとのidentity関係から再評価します。

stable refの文字列表現は実装時に既存ID規約とportabilityを確認して決定します。同じtargetが既に存在する場合、「別refを作って再試行」する前にcurrent entryを読み、same identityならupdate / revalidationへ移ります。真のidentity collisionと確認できた場合だけ別targetを使います。

この競合制御のためにglobal semantic lock、vector DB、central manifestは追加しません。

## 10. update / revalidation

同一knowledge identityのcurrent内容やapplicabilityを更新する場合は同じentry refを維持します。

```text
KN-001 @ R1
→ revalidation
→ KN-001 @ R2
```

再検証時にcurrent factが必要なら、該当owner Skillへ観測 / 分析を委譲します。

例:

```text
qa-knowledge | revalidation
→ test-target-inspection
→ current evidence
→ qa-knowledge
→ same entry new revision
```

## 11. 要再検証

stored currentness dependencyとcurrent dependencyが一致しない場合、そのentryをcurrent判断へ使いません。

persisted stateをまだ`要再検証`へ更新できていない場合でも、dependency mismatchが確認できた時点で利用対象から除外します。

保存権限がある場合はexpected entry revisionを保存先のatomic conditional writeへ渡して更新します。競合時は保存せずcurrent entryを再読込します。

## 12. replacement

次の場合だけreplacementを使います。

- semantic identityが別物になった
- 1 entryを複数entryへ分割する
- applicabilityを別entryへ分離する
- 既存の別entryへ統合する

通常の再検証や内容更新ではnew entryを作りません。

旧entryは`置換済み`にし、replacement refを保持します。

保存先がold/new entryをatomicに更新できない場合、generic transaction managerを追加しません。安全に一括反映できないreplacementはblockし、明示的な完了手順へ回します。

## 13. lookup / history

明示的に過去knowledgeを確認する要求では`qa-knowledge`を起動できます。

fixed rootをdeterministicに列挙し、

- scope
- kind
- environment / version
- state
- currentness dependency

で絞ります。

current判断へ返すのはcurrentness確認済みの`有効`entryだけです。

`要再検証` / `置換済み`entryは履歴として提示できますが、currentな推奨根拠として混在させません。

root列挙が不完全なら`complete=false`相当を明示します。

## 14. CAS

### read

entryを読み込むとき、保存先が返すentry artifact自身のrevision tokenを取得します。

### write

既存entry更新はexpected revision付きconditional writeにします。

### conflict

同じentryが変更済みなら自動mergeしません。

```text
CAS conflict
→ current entryを再読込
→ qa-knowledgeでsemantic re-evaluation
→ 必要ならcurrent revisionをbaseに再提案
```

別entryだけが変わり、target entry revisionが不変と確認できる場合だけretryします。

repository HEADやknowledge root revisionの変更だけをsame-entry conflictと扱いません。

## 15. provenance / currentness

provenanceはentry作成理由の履歴です。

currentness dependencyは現在も有効か判断する依存です。

例:

```text
Finding F-001
→ KN-001
  provenance: F-001 / Session / evidence
  currentness dependency: job configuration / staging environment
```

configuration変更でprovenanceを書き換えません。

dependency変更を検出するとKN-001はcurrent利用不可になり、再検証対象になります。

## 16. qa-workflowとの関係

`qa-workflow`は、

- 複数Skillを必要とするknowledge lifecycle requestのrouting
- workflow state
- blocked / resume
- source / output handoff

を担当します。

次を判断しません。

- candidateがresidual knowledgeか
- entryを有効化してよいか
- existing entry updateかreplacementか
- revalidation結果でcurrent利用可能か

これらは`qa-knowledge`の責務です。

## 17. 既存Skillとの関係

### exploratory-testing

Finding / Observationを生成します。

knowledge candidateを自動有効化しません。

### regression-testing

past FAIL / Finding / current knowledgeをselection inputとして利用できます。

knowledge lifecycleは所有しません。

### test-analysis

Product Risk / test focusを正本化します。

正式化すべき候補を`qa-knowledge`から受け取れます。

### test-target-inspection

currentな実対象情報を収集・更新します。

knowledge revalidationでcurrent evidenceが必要な場合に利用します。

## 18. deterministic validation

最低限確認します。

- fixed knowledge rootを完全列挙できる
- entry ref一意性
- 1 entry = 1 artifact
- schema必須field
- provenance ref整合
- currentness dependency ref整合
- state許可値
- superseded ref整合
- `有効`entryがcurrentness確認済み
- current利用時にentry revisionを記録
- same-entry updateがCASを利用
- root / repository HEAD変更だけで無関係entryをstaleにしない
- secret実値を含まない

## 19. semantic eval

代表case:

- 「このFindingを今後のQA知識として残して」
- 「この環境知識がまだ有効か確認して」
- 「今回得た知見を再利用可能な形にして」
- 「このObservationは仕様へ反映すべきか確認して」
- 「この対象について過去のQA知識を確認して」
- specification候補をknowledgeへ複製しない
- repeated defect patternを必要なら`test-analysis`へroutingする
- current UI factを`test-target-inspection`へroutingする
- environment-specific knowledgeを全environmentへ一般化しない
- formal Test Conditionへ昇格すべき内容をheuristicのまま残さない
- source / dependency不足で有効化しない

実Agent candidate outputを既存semantic runner + 実Judgeで評価します。

## 20. 対象外

- 汎用knowledge management
- cross-project knowledge共有
- knowledge ranking / score
- vector DB
- semantic search
- Graph DB
- relation index
- generic storage adapter
- external databaseを必須化すること
- Web UI
- global knowledge ID allocator
