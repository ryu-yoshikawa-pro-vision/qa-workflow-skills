# UIユーザビリティ評価Skill追加Plan

## 1. 現状

mainでは、仕様根拠からテスト分析・設計を行うSkillと、Playwright E2Eを扱うSkillが存在します。

PR #12では次が追加予定です。

- test-target-inspection: currentな実対象UI・ふるまい・視覚状態の収集
- test-execution: 詳細TCを人間の手動テスト相当で実行し、期待結果と実測を比較

PR #13では次が追加予定です。

- exploratory-testing: Charterに基づく探索 / Investigation
- regression-testing
- qa-knowledge

これらはUIを観測または操作できますが、UIパターンの目的・rationale・一般的なinteraction原則・アクセシビリティ・視覚品質を専門的に評価するownerではありません。

## 2. 解決する問題

現状のままでは、次がAgent個々の一般知識やその場の推測へ依存します。

- そのUIが何のためのパターンか
- その場面にそのパターンを使う理由
- 代替パターンと比べた適用条件
- 期待されるinteraction
- feedbackやerror recovery
- keyboard / focus
- accessible name / role / state
- responsive時の期待
- loading / empty / disabled等の状態
- 視覚的な重なり、欠け、overflow、階層の問題
- 一般的なユーザビリティ原則との整合

この状態では、同じUIを評価してもAgentごとに判断基準が揺れます。

usability-evaluation は、これらの判断に使う参照知識と評価手順をSkill package内へ持ち、出典と適用条件に基づく再現性のある評価を行います。

## 3. 主責務

usability-evaluation の主責務は次です。

### UI / interaction patternの理解

- 対象UIを構成するcomponent / pattern候補を識別する
- 単一componentだけでなく、form、search / filter、wizard、navigation、dialog flow、empty state等の複合patternを扱う
- pattern名が確定できない場合は無理に1つへ分類せず、観測できた構造と候補を保持する
- visual similarityだけでpatternを確定せず、目的とinteractionを確認する

### 目的・ユーザー目標・rationaleの評価

各patternについて、

- 解決しようとしているユーザー課題
- ユーザーが達成しようとしていること
- そのpatternを使う理由
- 適する状況
- 適さない状況
- 認知負荷、操作負荷、誤操作防止等の観点
- 他patternとの違い

をreferenceから確認し、対象UIへ適用できるかを判断します。

### interactionの評価

必要に応じて次を確認します。

- affordance / discoverability
- controlの状態
- focus
- keyboard
- pointer / touch
- selection
- open / close
- submit / cancel
- undo / recovery
- system status
- loading
- success / failure feedback
- validation
- disabled / readonly
- empty state
- destructive action
- navigation / back
- interruption
- progressive disclosure
- search / filter / sort
- pagination / virtualized collection
- drag and drop等の代替操作

### accessibilityの評価

- WCAG 2.2の対象Success Criterion
- WAI-ARIA APGのpattern guidance
- native semanticsを優先する原則
- role / state / property
- accessible name / description
- keyboard interaction
- focus management
- reading / navigation structure
- contrast等、観測可能な視覚条件

を対象scopeに応じて確認します。

単一画面・単一componentの観測から製品全体のWCAG適合を宣言しません。

### visual integrityの評価

DOM / accessibility treeだけでは確定できない場合、画像証跡を用いて次を確認します。

- overlap
- clipping
- overflow
- text truncationによる意味欠落
- viewport外へ重要操作が隠れる状態
- modal / popover等の見切れ
- responsive collapse
- 不自然な重なり
- 意図しない横scroll
- focus indicatorの視認性
- visual hierarchy
- spacing / grouping
- alignment
- feedbackやerror表示の可視性
- zoom / text expansion時に観測できる破綻

デザインの好みだけを不具合扱いしません。

## 4. 入力の種類

同じSkillで次の入力を扱います。

### 設計時

- 現在有効な仕様根拠
- Figma等のデザイン情報
- wireframe / prototype
- UI仕様
- user flow
- project context
- 採用Design System
- platform情報

この時点ではlive UIがなくても評価できます。

実装済み挙動を観測したと偽らず、設計上確認できる範囲だけを評価します。

### 実対象確認時

- test-target-inspectionのcurrent UI情報
- DOM / accessibility tree
- ARIA snapshot
- screenshot
- viewport
- role / locale / permission
- 状態・操作反応

を利用します。

### TC実行時

- test-executionが固定したTC
- 実行中の観測
- screenshot
- 操作前後の状態
- TCの期待結果

を利用します。

TCのPASS / FAILはtest-executionの判定を維持し、UX上のFindingを別に返します。

### Exploration時

- Charter
- Observation
- Finding候補
- evidence

を受け取り、UI / UX上の懸念を参照知識へ照合します。

## 5. 出力の用途

### test-analysisへの入力

usability-evaluation はProduct Riskを採点しません。

次を返し、test-analysisが必要な場合にProduct Riskとして扱うかを判断します。

- ユーザー目標
- UI pattern
- usability上のfailure mode候補
- 根拠
- 観測可能性
- 関連するUI状態 / interaction

### test-condition-designへの入力

テスト条件を直接所有しません。

次を検証観点候補として返します。

- pattern固有のinteraction
- state
- error / recovery
- keyboard / focus
- accessibility
- responsive / visual
- feedback

test-condition-designは現在有効なテスト要求と仕様根拠の範囲で採用可否を決めます。

### 実UI評価

現在UIを評価する場合は、観測事実と参照根拠を結び付けたFindingを返します。

## 6. 担当しないこと

- Product Riskの採点
- 仕様Authorityの作成
- 一般的なbest practiceから仕様Authorityを創作すること
- 詳細TCの正本化
- TCのPASS / FAIL判定の上書き
- Regression membership / Run selection
- exploratory Sessionのowner
- user research結果の捏造
- 実ユーザーの満足度・学習容易性・業務効率を、ユーザー観測なしで事実として断定すること
- pixel-perfect visual regression frameworkの新設
- Design Systemそのものの実装
- browser automation frameworkの新設
- screenshot diff専用runtimeの新設
- 全外部Design Systemへの準拠を要求すること

## 7. 「使いやすい」の扱い

「使いやすい / 使いにくい」を無根拠な総評として出力しません。

評価可能な要素へ分解します。

例:

- 目的の操作を発見できる構造か
- 現在状態を認識できるか
- 期待する次の操作を判断できるか
- 誤操作を予防または回復できるか
- 不要な記憶負荷を要求していないか
- 一貫した概念 / controlを使っているか
- keyboard等の利用手段で操作できるか
- 視覚的に重要情報が隠れていないか

これらを観測・根拠へ結び付けたうえでFindingを作ります。

## 8. 完了の考え方

評価対象scopeについて、

- pattern候補と目的を確認した
- 適用可能なreferenceを選んだ
- 判定可能な観点を評価した
- 判定不能を理由付きで残した
- 観測事実と解釈を分離した
- sourceを追跡できる
- 必要なFindingを出した

状態になれば、その評価Activityは完了できます。

問題が0件でも完了可能です。
