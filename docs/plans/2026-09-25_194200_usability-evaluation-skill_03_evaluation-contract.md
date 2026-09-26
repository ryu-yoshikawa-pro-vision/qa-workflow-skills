# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本契約の対象

本ファイルは `usability-evaluation` のreference-based UI / UX評価契約です。

UI pattern、principle、standard、Design System、heuristic等をevidenceへ照合して意味判断します。

live Web UIを能動操作・観測する `usability-inspection` の実行契約は `_01a_usability-inspection-scope-and-contract.md` に分離します。

`usability-evaluation` 自身はbrowser / session ownerにならず、代表ユーザーを用いたusability testingを実施したとは扱いません。

## 1. 評価の基本単位

評価は「画面全体をなんとなく見る」方式にしません。

対象を次の組合せで固定します。

- target scope
- platform
- viewport / device
- locale
- current state
- target region / flow
- relevant pattern
- evidence
- project Authority / adopted Design System / applicable standard

次は存在する場合だけ利用します。

- user / role
- user goal / task / flow
- 特定の利用者条件

taskやpersonaがないことだけを理由に評価不能にしません。

同じ画面でもdevice、state、role等の条件が変われば別評価になり得ます。

## 2. 評価手順

### Step 1: scopeと文脈を固定

確認するもの:

- どの画面 / component / flowを評価するか
- platform
- viewport / input method
- current state
- project固有Design System
- applicable standard
- accessibility scope
- usability scope
- 評価に利用可能な証拠
- user goal / task / role等が明示されている場合はその条件

対象UIの目的やuser goalをevidence / specificationから確認できない場合は、無理にpersonaやgoalを創作せず、判定可能な観点だけ継続します。

### Step 2: 観測事実を整理

観測と解釈を分離します。

観測例:

- buttonが2つある
- dialog表示後にfocusが移った
- loading中もsubmit controlが操作可能
- 320px viewportでprimary actionが画面外
- error messageが表示された
- accessible nameが取得できない

解釈例:

- 二重送信を誘発する可能性
- focus管理がpattern guidanceと不整合
- primary actionを発見しにくい

解釈だけを観測事実として書きません。

`usability-inspection` のobjective observation、requirement result、measurement、screenshot、optional task / flow result等が入力される場合も、それらをevidenceとして扱い、human user behaviorへ読み替えません。requirement resultと専門評価も混同しません。

### Step 3: pattern候補を識別

DOM role名だけでpatternを確定しません。

次を組み合わせます。

- user goal / task（存在する場合）
- target UIの目的・周辺文脈
- controlの構造
- interaction
- role / semantics
- visual presentation
- surrounding flow

複数patternが組み合わさる場合は分解します。

例:

- search form
- autocomplete / combobox
- filtering
- results collection
- empty state
- pagination

### Step 4: patternの目的と適用条件を確認

references/index.mdから該当referenceを読み、

- 何のためのpatternか
- どんな問題を解決するか
- なぜ使うか
- いつ使うか
- いつ使わないか

を確認します。

名前が似ているだけで適用しません。

### Step 5: 根拠を選択

evidence-and-authority.mdに従い、

- project requirement
- applicable standard
- platform guideline
- adopted Design System
- general pattern guidance
- heuristic

を区別します。

各source itemの `source上の位置づけ` と適用条件を確認し、project Authority、明示された適合基準、platform、採用Design System、今回の文脈を組み合わせて、今回の評価での `referenceの位置づけ` を決めます。

reference側にあるnormative / informative / advisoryという性質だけから、projectへのbindingを自動確定しません。逆に、project固有のbinding根拠を使う場合はproject Authority refを評価項目へ残します。

### Step 6: 今回評価する観点を固定

評価を始める前に、target scope、pattern候補、適用可能なreference、利用可能なevidence、明示されたuser goal / taskがある場合はその条件から、今回扱う観点を固定します。

次の上位観点をすべて「今回評価する」または「対象外」とし、対象外には理由を残します。

- 目的・理解可能性
- interaction
- feedback
- error prevention / recovery
- accessibility
- visual integrity
- cross-pattern / flow

全上位観点へ同じ詳細checklistを機械適用しません。各上位観点の中で何を確認するかは、pattern、reference、evidence、対象状態に応じて選びます。

「今回評価する」とした上位観点は、その観点で適用対象として識別した全target / concernをUI / UX評価結果へ閉じます。少なくとも1件だけ出力して残りを暗黙に省略しません。各結果は `問題を確認 / 問題なし / 判定不能 / 対象外` のいずれかへ閉じます。

deterministic validatorは「固定した観点が結果へ閉じていること」だけを検証し、その観点を選ぶべきだったか、内部でどの確認項目が必要だったかはsemantic evalで確認します。

### Step 7: strict requirement resultと専門評価を分離

`usability-inspection` 等からstandard / binding requirement resultが渡された場合、その `satisfied / not-satisfied / undetermined` をevidenceとして保持します。検査scopeとして扱わない項目の `対象外` はscope closure側で保持します。

W3C ACT Rule等のtest rule resultが渡された場合は、test rule outcomeとrequirement全体のresultを別のevidenceとして扱います。rule outcomeが `passed` であることだけを理由にrequirementを `satisfied` へ変更しません。

usability-evaluationは、

- criterionのapplicability
- evaluation scope
- population / required checksのclosure
- projectへのbinding根拠
- criterionの意味
- pattern / heuristicとの関係
- user / product impactの可能性

を評価できます。

requirementを `satisfied` とする前提が不足している場合、専門評価によって不足を補ったことにせず `undetermined` または追加確認として残します。

ただし、一般heuristicやadvisory guidanceの差異を `not-satisfied` へ変換しません。逆に、明確なbinding requirementの `not-satisfied` を単なる「好み」の問題へ弱めません。

### Step 8: 評価

対象に応じて以下から必要なものを評価します。

#### 目的・理解可能性

- UIの役割を認識できるか
- ユーザーが何をすべきか理解できるか
- 次の操作が分かるか
- wording / labelが目的を表すか
- visual hierarchyが目的を支えるか

#### interaction

- controlを発見できるか
- 操作結果が分かるか
- 状態変化が分かるか
- cancel / back / close / undo等が必要な文脈で利用できるか
- destructive actionで誤操作防止があるか
- repeated actionやdouble submit等の危険がないか
- shortcutや効率化が必要な文脈で妨げがないか

#### feedback

- loading
- progress
- success
- failure
- warning
- validation
- completion

の状態が目的に応じて理解可能かを確認します。

#### error prevention / recovery

- 誤入力予防
- 入力保持
- error location
- error explanation
- correction path
- retry
- cancellation
- undo
- irreversible action

を必要な範囲で確認します。

#### accessibility

- semantics
- role
- accessible name
- state / property
- keyboard
- focus
- reading / navigation structure
- target size
- contrast
- zoom / text spacing等

を、対象criterionと証拠に応じて確認します。

#### visual integrity

- overlap
- clipping
- overflow
- hidden action
- unexpected horizontal scroll
- text loss
- popover / dialog positioning
- responsive breakage
- hierarchy
- grouping
- alignment
- focus visibility
- status / error visibility

を確認します。

### Step 9: cross-pattern整合

component単体が妥当でもflow全体で問題になる場合があります。

例:

- dialog単体は正しいが連続dialogでtaskを阻害する
- field単体は正しいがform全体でerror recoveryが困難
- pagination単体は正しいがfilter変更時にcurrent pageが不整合
- search input単体は正しいがresults stateが分からない

必要な場合だけflow単位で再評価します。

### Step 10: UI / UX評価項目を閉じる

各評価項目は次を必須fieldとして持ちます。

`evaluation ref` は1つのusability-evaluation成果物revision内だけで一意なartifact-local refです。新しいglobal QA IDやMachine Entityにはしません。成果物自体のidentity / revisionは、実装開始時に確認したPR #11 / #12 / #13 merge後の既存artifact契約を再利用します。

同じ評価を別revisionで再実行した場合に `evaluation ref` のstable identity維持を要求しません。既存artifact-local ref規則がmerge後実装にある場合はそれを優先し、ない場合は最終出力の評価行順で `EVAL-001` から採番します。並べ替えによるref維持は要求しません。

- evaluation ref
- 対象
- user goal / task（評価条件から継承。行単位で異なる場合だけoverride）
- pattern
- 観測事実
- 適用したreference:
  - reference entry ref
  - source item ref
  - referenceの位置づけ
  - project Authority refs（project固有のbinding根拠を使う場合だけ）
- 期待される特性
- 差異
- 想定される影響
- 想定される影響の根拠
- 観測済みのユーザー影響（実際に証拠がある場合だけ）
- evidence ref
- status
- status reason / 制約・未確認
- 推奨routing
- finding ref（Findingを作成した場合だけ）

`適用したreference` は1件以上の配列として扱い、1行につき1つの `reference entry ref + source item ref` の組を持ちます。`source item ref` はそのreference entryに実際に含まれるitemでなければなりません。同じ評価項目でproject Authority、WCAG、Design System、heuristic等を併用する場合も、各source itemごとの `referenceの位置づけ` を別行で保持し、1つの値へ統合しません。`status reason / 制約・未確認` は `判定不能` / `対象外` では必須です。

### Step 11: 必要な場合だけFindingを作る

PR #13のFinding定義を再利用し、後続QA活動で扱う必要がある検出事項だけに限定します。

- `問題を確認` しfollow-upが必要 → Findingを作る
- `判定不能` で追加観測・仕様確認等のfollow-upが必要 → Findingを作る
- `問題なし` / `対象外` → Findingを作らない
- `判定不能` でもfollow-up不要で現在scopeを閉じられる → Findingを作らない

Findingを作る場合はPR #13の最低契約を満たし、評価項目からfinding refで参照します。`evaluation ref` 自体をPR #13のglobal identityやMachine Entityへ昇格しません。必要な追跡はusability-evaluation成果物ref / revisionと、その中のevaluation refの組で行います。

## 3. 判定

単一のUX総合スコアは作りません。

各評価項目を次のように閉じます。

- 問題を確認
- 問題なし
- 判定不能
- 対象外

「問題なし」は対象に必要な観測を行った場合だけ使用します。

意味は「今回のscope、利用可能なevidence、適用したreferenceの範囲で問題を確認しなかった」です。製品全体のusability、representative userのtask success、satisfaction等を保証しません。

「想定される影響」は観測事実ではなく、観測事実とreferenceから導いた評価として根拠を残します。「ユーザーが迷った」「完了率が下がった」等の実ユーザー影響は、user research、analytics、明示された観測等の証拠がある場合だけ「観測済みのユーザー影響」に記録します。

## 4. 仕様上のFAILとの境界

例:

仕様:
保存操作で保存される。

実測:
保存された。

TC:
PASS。

UX観測:
保存開始後もbuttonが操作可能で、処理中であることを示すfeedbackがない。

扱い:
TCをFAILへ変更しない。
usability-evaluation側で独立Finding候補として扱う。

一方、project仕様が「保存中はbuttonをdisabledにする」と定義している場合、その仕様不一致は通常のTC / 仕様検証側でも扱えます。

## 5. test-analysisとの境界

usability-evaluationが、

「このflowではerror recoveryが不明瞭で、入力内容を失う可能性がある」

という懸念を返しても、Product Risk IDやimpact / likelihoodを自分で確定しません。

test-analysisへ渡し、既存のリスク評価契約で判断します。

## 6. test-condition-designとの境界

pattern referenceに10個の観点があっても、すべてをTCへ展開するとは限りません。

test-condition-designが、

- current test requirement
- Product Risk
- scope
- project constraints

から採用範囲を決めます。

usability-evaluationは一般guidanceをテスト要求へ昇格しません。

## 7. accessibility判定

### WCAG

`usability-evaluation` は、取得済みのWCAG requirement result / evidenceの意味をread-onlyで評価できます。general accessibilityのlive observationは `usability-inspection`、formalなWCAG conformance evaluationは `wcag-conformance-evaluation` が担当します。requirement result / ACT semanticsは `_05d_accessibility-requirements-and-act.md` を共有します。

Success Criterion resultを扱う場合は、

- 宣言したevaluation scope
- applicable population
- required checks
- exception
- evidence
- `satisfied / not-satisfied / undetermined`

を保持します。

単一element / component / sampleだけの成功からpage / productのSuccess Criterionを `satisfied` へ昇格しません。

WCAG-EM evaluation report / evaluation statement / conformance claimは `wcag-conformance-evaluation` の成果物だけで扱います。ACT Ruleの `inapplicable` outcomeをWCAG Success Criterionのresult語彙へ流用しません。

### APG

patternの、

- keyboard
- roles
- states
- properties
- focus behavior

を評価できます。

ただしAPG exampleの具体DOM構造や実装詳細を唯一の正解として要求しません。

## 8. visual評価

画像から仕様、role、accessible nameを推測しません。

画像は主に次に使います。

- 位置
- サイズ
- overlap
- clipping
- visible hierarchy
- spacing
- viewport内可視性
- visual feedback
- focus appearance
- rendering

DOM / accessibility treeと画像の観測が矛盾する場合は、片方を無言で優先せず矛盾として保持します。

## 9. responsive評価

単一viewportだけからresponsive品質全体を確定しません。

対象viewport集合が明示されている場合は各条件を評価します。

未指定時に、Skillが無制限なdevice matrixを創作しません。

test-analysis / project contextで必要scopeを決めます。

## 10. 動的状態

静止画1枚では判断できないpatternがあります。

例:

- loading
- progressive disclosure
- dropdown
- combobox
- dialog
- toast / notification
- validation
- drag and drop
- focus management

既存ownerが取得したbefore / after / intermediate evidenceを利用します。

追加操作が必要な場合は、browserを所有するSkillへ必要な観測を要求します。

usability-evaluation自身が所有権不明のsessionへ勝手に操作を追加しません。

## 11. user researchとの境界

heuristic / expert reviewで確認できるのは、既知のprincipleやpatternとの不整合、潜在的なusability problemです。

次を観測なしで断定しません。

- 実ユーザーが迷う割合
- task completion rate
- satisfaction
- learning time
- 実際の業務効率
- preference

必要なら「user researchで確認すべき仮説」として分離します。

## 12. false positive抑制

次だけを理由にFindingを作りません。

- 自分の好みと違う
- 別Design Systemなら違う実装をする
- pattern名が完全一致しない
- visual styleが一般例と違う
- 具体的なproject contextを確認せずheuristicへ表面的に一致しない

Findingには必ず、対象の目的、適用条件、観測事実、source、影響を結び付けます。
