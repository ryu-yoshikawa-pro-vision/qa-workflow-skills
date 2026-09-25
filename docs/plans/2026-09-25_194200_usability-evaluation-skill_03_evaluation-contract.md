# UIユーザビリティ評価Skill追加Plan

## 1. 評価の基本単位

評価は「画面全体をなんとなく見る」方式にしません。

対象を次の組合せで固定します。

- user / role
- user goal / task
- platform
- viewport / device
- locale
- current state
- target region / flow
- relevant pattern
- evidence

同じ画面でもrole、device、stateが変われば別評価になり得ます。

## 2. 評価手順

### Step 1: scopeと文脈を固定

確認するもの:

- 誰が使うか
- 何を達成しようとしているか
- どの画面 / flowか
- platform
- viewport / input method
- project固有Design System
- accessibility scope
- usability scope
- 評価に利用可能な証拠

不足しても判定可能な部分は継続します。

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

### Step 3: pattern候補を識別

DOM role名だけでpatternを確定しません。

次を組み合わせます。

- user goal
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

### Step 6: 評価

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

### Step 7: cross-pattern整合

component単体が妥当でもflow全体で問題になる場合があります。

例:

- dialog単体は正しいが連続dialogでtaskを阻害する
- field単体は正しいがform全体でerror recoveryが困難
- pagination単体は正しいがfilter変更時にcurrent pageが不整合
- search input単体は正しいがresults stateが分からない

必要な場合だけflow単位で再評価します。

### Step 8: UI / UX評価項目を閉じる

各評価項目は最低限次を持ちます。

- evaluation ref
- 対象
- user goal / task
- pattern
- 観測事実
- 適用したreference
- referenceの位置づけ
- 期待される特性
- 差異
- 想定される影響
- 想定される影響の根拠
- 観測済みのユーザー影響（実際に証拠がある場合だけ）
- evidence
- 判定
- 制約 / 未確認
- 推奨routing
- finding ref（Findingを作成した場合だけ）

### Step 9: 必要な場合だけFindingを作る

PR #13のFinding定義を再利用し、後続QA活動で扱う必要がある検出事項だけに限定します。

- `問題を確認` しfollow-upが必要 → Findingを作る
- `判定不能` で追加観測・仕様確認等のfollow-upが必要 → Findingを作る
- `問題なし` / `対象外` → Findingを作らない
- `判定不能` でもfollow-up不要で現在scopeを閉じられる → Findingを作らない

Findingを作る場合はPR #13の最低契約を満たし、評価項目からfinding refで参照します。

## 3. 判定

単一のUX総合スコアは作りません。

各評価項目を次のように閉じます。

- 問題を確認
- 問題なし
- 判定不能
- 対象外

「問題なし」は対象に必要な観測を行った場合だけ使用します。

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

Success Criterion単位で、

- applicableか
- 必要な証拠を取得できたか
- observed pass / observed failure / unable to determine

を扱います。

ページ全体・process全体の適合が必要なcriterionをcomponentの一観測だけで完了扱いにしません。

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
