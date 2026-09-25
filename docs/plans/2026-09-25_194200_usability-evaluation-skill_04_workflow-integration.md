# UIユーザビリティ評価Skill追加Plan

## 1. 固定工程にしない

usability-evaluationを、

spec-analysis → test-analysis → usability-evaluation → test-requirement-design

のような固定工程へは置きません。

理由:

- UIを持たない対象もある
- usability評価が要求されない案件もある
- live UIがない設計段階でも利用できる
- 実対象確認・実行・探索中にも再利用したい
- 同じUIを異なる時点で評価することがある

qa-workflowが要求・scope・利用可能な証拠からroutingします。

### 1.1 起動方針

live UIと設計時で扱いを分けます。

#### live UIを観測・操作する場合

`test-target-inspection` または `test-execution` がUIを実際に観測し、UI / UX評価が案件コンテキストまたはユーザー要求で明示的に対象外ではない場合、取得済みのUI evidenceを `usability-evaluation` へ渡すことを既定とします。

この既定接続はbrowserの追加操作を意味しません。

- DOM / accessibility tree
- ARIA snapshot
- screenshot
- viewport
- before / after / intermediate state
- role / locale / permission
- 操作結果

等、owner Skillが既に取得した証拠を再利用します。

UIを持たない対象、API / DBだけの実行、UX評価が明示的に対象外のscopeでは起動しません。

#### テスト分析・設計の場合

UIが対象であり、次のいずれかが判断へ影響する場合に利用します。

- user goal / task
- interaction pattern
- usability
- accessibility
- responsive / visual quality
- error prevention / recovery
- feedback / loading / empty state
- UI構造から生じるProduct Risk候補

backend-onlyの分析・設計へ無条件に起動しません。

## 2. test-analysisから利用

### 利用する場合

- UI中心の機能でusabilityがProduct Riskへ影響する
- 新しいinteraction patternを導入する
- 主要user flowを変更する
- error / recovery / feedbackが重要
- user goal達成をUI構造が左右する
- accessibility / responsiveが対象範囲

### データフロー

~~~text
仕様 / design / project context
        ↓
usability-evaluation
        ↓
user goal
pattern / rationale
failure mode候補
確認すべきinteraction / state
        ↓
test-analysis
        ↓
Product Risk / test focus / depth
~~~

usability-evaluationはrisk scoreを付けません。

## 3. test-condition-designから利用

test-condition-designがUI固有の観点を具体化する必要がある場合、usability-evaluationのreference knowledgeを利用します。

例:

- Dialog → open / close / focus / keyboard / destructive action
- Combobox → input / popup / selection / keyboard / state
- Form → label / validation / error recovery / submission / disabled
- Search → query / clear / no results / loading / filter interaction

ただし一般patternから未定義の製品期待結果を作りません。

仕様上の期待結果が必要なのにAuthorityがない場合は既存のquestion / specification routingへ戻します。

## 4. test-target-inspectionとの統合

PR #12 merge後の実装を正本とします。

test-target-inspectionが収集する、

- target region
- UI elements
- role / accessible name
- state
- behavior
- ARIA snapshot
- screenshot
- viewport
- locale
- role / permission
- version / build

を再利用します。

~~~text
test-target-inspection
        ↓
current observation artifact
        ├→ 通常の後続QA利用
        └→ usability-evaluation
~~~

usability-evaluationのためだけに同じ画面を再scanすることを既定にしません。

必要証拠が不足する場合だけ、追加観測要求をtest-target-inspectionへ返します。

## 5. test-executionとの統合

TC実行中に各meaningful UI stateの証拠を取得できる場合、その証拠をusability-evaluationへ渡します。UI / UX評価が明示的に対象外なら渡しません。

~~~text
test-execution
  ↓ before / after / intermediate state
  ├→ TC expected result comparison
  └→ usability-evaluation
       ↓
      UX Finding
~~~

### browser所有

test-execution実行中に別Agentが同一browser / sessionへ並行操作しません。

許可するのは、

- 取得済みsnapshot
- screenshot
- immutable evidence
- ownerが明示的に提供したread-only情報

に対する評価です。

追加操作が必要ならtest-executionへ要求し、owner側の副作用・cleanup・開始状態契約に従います。

### 評価タイミング

usability-evaluationをTC操作のたびに同一sessionへ割り込ませません。

owner Skillは評価に必要なmeaningful stateのevidence refを保持し、少なくとも現在TCの状態を壊さないcheckpointでread-only評価へ渡します。

- UX評価結果が現在TCの仕様上PASS / FAIL判定条件でない場合、UX評価完了を待ってTCの仕様判定を変更しない
- immutable evidenceを評価する処理はhostが並行実行可能でも、workflow契約として真の並行実行を要求しない
- UX評価が追加観測を要求した場合はowner Skillへ戻し、勝手に同一browserを操作しない
- 同じevidence / stateを同一Activity内で理由なく重複評価しない

これにより、テスト実行の状態管理とUX評価を分離しながら、実行中に得たUI状態を失わず評価できます。

## 6. exploratory-testingとの統合

Exploration / Investigation中に、

- 使いづらさ
- 不自然なinteraction
- feedback不足
- error recovery問題
- pattern mismatch
- visual issue

をObservationとして得た場合、usability-evaluationへ渡せます。

usability-evaluationはFindingの根拠強化を担当できますが、Session lifecycleを所有しません。

評価結果はexploratory-testingのFinding / Follow-upへ戻します。

## 7. regression-testingとの統合

usability-evaluationを全Regression Runへ無条件適用しません。

次の場合に利用できます。

- Regression scopeにusability / accessibility / visual確認が明示される
- selected TCがUI状態の証拠を生成し、その評価が要求される
- 過去のUX Findingに対する再確認がRegression対象へ入っている

Regression membership判断はregression-testingのままです。

## 8. qa-knowledgeとの統合

### Skill内referenceとqa-knowledgeを分離

W3CやDesign System等の汎用UI / UX知識は usability-evaluation の references が正本です。

qa-knowledgeへ複製しません。

一方、特定projectで検証済みの、

- project独自UI convention
- 採用Design Systemのproject-specific override
- 特定user groupで確認済みの注意
- 継続的に使えるUI評価上の知見

はPR #13のqa-knowledge対象になり得ます。

既存ownerがある内容は既存ownerへroutingします。

## 9. qa-workflow

qa-workflowへ次の責務を追加します。

- UI / UX評価要求を usability-evaluation へrouting
- analysis / design / inspection / execution / explorationとの接続
- usability-evaluationが必要なscopeだけ状態管理
- Finding後のowner routing

qa-workflow自身はpattern判断やUX評価を再実装しません。

## 10. workflow state

実装開始時のPR #13 merge後契約を確認します。

usability-evaluationは同じdomain責務を異なる入力時点で実行するため、最初からMULTI_USE_SKILL_TARGETSへ複数用途を追加するとは決めません。

workflow stateで同一Skillの複数Activityを区別する既存仕組みがPR #13にある場合はそれを再利用します。

なければ、qa-workflowの既存状態表を壊さない最小の表現をStep 0で確定します。

用途名だけを増やすための独自state machineは作りません。

## 11. 「非同期」の扱い

ユーザー要求上の「非同期」は、主workflowの固定直列工程ではなく横断的に追加評価できることを意味するものとして設計します。

Agent Skills仕様やhostが真のparallel executionを保証すると仮定しません。

許容:

- immutable evidenceを別評価として処理
- 他の意味判断と独立して評価
- hostが安全に並行化できる場合のread-only評価

禁止:

- 同一browser / sessionへの競合操作
- 同一mutable artifactの無条件並行更新
- 同じtest user / dataを所有権確認なしで並行変更

## 12. project context

PR #12 / #13 merge後のtemplateを確認し、既存の非機能テスト範囲を再利用します。

少なくとも既存の、

- アクセシビリティ
- ユーザビリティ
- 対象画面
- role
- browser / device / viewport
- locale
- Design System / UI仕様に相当する情報源
- 証跡制約

を利用します。

新しい巨大なUX設定sectionは作りません。

不足する場合だけ最小項目を追加します。

候補:

- 採用Design System / version
- UX評価で明示的に適用するstandard / guideline
- 対象user / task

既存欄で表現できれば追加しません。

## 13. Finding後のrouting

- current UI観測不足 → test-target-inspection
- Product Riskへ反映が必要 → test-analysis
- テスト要求不足 → test-requirement-design
- test condition追加・更新候補 → test-condition-design
- current TCの期待結果 / 手順不足 → test-case-design
- 仕様Authority不明 → question-analysis / spec-analysis
- Exploration継続が必要 → exploratory-testing
- project固有の継続知識候補 → qa-knowledge
- 実行再確認 → test-execution / e2e-test-execution

usability-evaluation自身が他成果物を直接書き換えません。
