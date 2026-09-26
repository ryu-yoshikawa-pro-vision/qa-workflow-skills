# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-evaluation` のworkflow統合です。

live Web UIを能動操作・観測してユーザビリティ上の問題を検査する `usability-inspection` は `_04a_usability-inspection-workflow-integration.md` を正本とします。

`test-target-inspection` / `test-execution` から既存evidenceを `usability-evaluation` へ渡すことはできますが、それらを `usability-inspection` の代わりにはしません。

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

直接発火とworkflow内呼び出しを分けます。

#### 直接発火

ユーザーがUI / UXレビュー、UI patternの妥当性、accessibilityを含むinteraction評価、Design System / standard / heuristicとの照合等を明示的に要求した場合は `usability-evaluation` を直接開始できます。

「実際に操作して使い勝手を確認」「表示崩れ・keyboard / focus・標準適合・操作後の遅さをlive targetで確認」「指定flowを実際に操作して確認」等、live UIの検査を要求する場合は `usability-inspection` を開始します。

「usabilityを確認」のように実操作の有無が曖昧な場合は、設計 / evidence reviewなのかlive task executionなのかを要求と利用可能なtargetからroutingします。

「TCを実行して」「current UIを収集して」のようにUX評価を明示しない依頼では、`usability-evaluation` を最初のSkillとして直接発火させません。

#### workflow内呼び出し

`qa-workflow` または同一Agent上のowner Skillは、UI / UX評価がユーザー要求・案件scope・workflow上で明示的に選定された場合だけ、取得済みevidenceを `usability-evaluation` へ渡します。test-target-inspection / test-executionがUIを扱ったという事実だけでは後続評価を自動追加しません。これはdirect trigger評価とは別契約です。

live UIと設計時で扱いを分けます。

#### live UIの既存evidenceを評価する場合

このsectionは `usability-inspection` のlive task executionではありません。

`test-target-inspection` または `test-execution` が取得したUI evidenceは、UI / UX評価が明示的に要求・選定された場合に `usability-evaluation` へ再利用できます。UI / UX評価が単に「対象外と明示されていない」だけでは接続しません。

このread-only evidence再利用はbrowserの追加操作を意味しません。

新しいtaskを実際に操作してusabilityを測る必要がある場合は `usability-inspection` へroutingし、test-target-inspection / test-executionのsessionへ暗黙に割り込みません。

- DOM / accessibility tree
- ARIA snapshot
- screenshot
- viewport
- before / after / intermediate state
- role / locale / permission
- 操作結果

等、owner Skillが既に取得した証拠を再利用します。

UIを持たない対象、API / DBだけの実行、UX評価が明示的に対象外のscopeでは起動しません。

#### standalone owner Skill

`qa-workflow`を介さず `test-target-inspection` / `test-execution` 等を直接利用した場合は、UI / UX評価が同じ依頼で明示されている場合だけ、owner Skill完了後または安全なcheckpointで同じAgentが `usability-evaluation` を順次読み込めます。評価要求がなければowner Skill単独で完了します。共通Skill-to-Skill APIの存在は前提にしません。

利用できない場合、UX評価が明示要求されていなければowner Skillの本来成果物は継続しUX評価未実施を必要範囲だけ明示します。UX評価が明示要求されている場合はfunctional / inspectionの判定可能範囲を継続し、UX評価scopeだけを利用不能として扱います。TCの仕様上PASS / FAILは変更しません。

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

UI / UX評価が別scopeとして選定された場合、test-target-inspectionが収集する、

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

UI / UX評価が別scopeとして明示的に選定され、TC実行中に各meaningful UI stateの証拠を取得できる場合、その証拠をusability-evaluationへ渡します。TC実行だけを理由に自動接続しません。

~~~text
test-execution
  ↓ before / after / intermediate state
  ├→ TC expected result comparison
  └→ usability-evaluation
       ↓
      UI / UX評価項目
       ↓ follow-upが必要な場合だけ
      Finding
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

Regressionではregression-testingが確定したUI / UX評価scopeだけを接続します。通常のtest-executionにもUI / UX評価の既定接続はないため、Regression外・内を問わず明示的なscope選定なしに評価を追加しません。

次の場合に利用します。

- Regression scopeにusability / accessibility / visual確認が明示される
- selected TCでUI / UX評価が必要と選定される
- 過去のUX Findingに対する再確認がRegression対象へ入っている

~~~text
通常のtest-execution
→ UI / UX評価が明示的に選定された場合だけevidenceを再利用

regression-testing配下のtest-execution
→ regression-testingが確定したUI / UX評価scopeだけevidenceを再利用
~~~

Regression membership / Run selection / UI / UX評価scopeの確定はregression-testingの責務を維持します。

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
- UI / UX評価項目と、必要な場合に作成されたFindingのowner routing

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
