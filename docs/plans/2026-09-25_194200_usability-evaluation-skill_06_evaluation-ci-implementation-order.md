# UIユーザビリティ評価Skill追加Plan

## 1. 実装開始条件

実装開始前に最新状態を再確認します。

最低限:

- PR #11のmerge状態とmain実装
- PR #12のmerge状態と test-target-inspection / test-execution 実装
- PR #13のmerge状態と exploratory-testing / qa-knowledge / qa-workflow 実装
- 最新main SHA
- Skill一覧
- CANONICAL_SKILLS
- MULTI_USE_SKILL_TARGETS
- workflow-state-template
- project-context-template
- EVALS.md
- validate-skills.yml
- trigger / deterministic / semantic dataset件数
- browser / side-effect / concurrency契約

PR #11 / #12 / #13がPlanから変更されて実装された場合、実装をPlanの古い仮定へ合わせません。

## 2. Step 0: merge後baseline固定

最新mainから本branchを更新し、実装開始commitを記録します。

確認結果によりPlanの責務境界だけ最小修正します。

既存Skillで今回責務が既に実装済みなら重複Skillを作らず再評価します。

## 3. Step 1: source inventory

reference本文を書く前にsource母集団を固定します。

各採用sourceについて、

- index / sitemap / category pages
- 公開pattern一覧
- 公開component一覧
- accessibility guidance
- interaction / layout / content guidance
- source status
- terms / license

を確認します。

加えて、Plan作成時のseed sourceだけで閉じず、標準化団体、platform vendor、公開Design System、UI pattern library、usability評価資料を追加調査します。本Skillの対象に直接使える新しいsourceを採用した場合は、そのsourceも同じsource inventory / coverage契約へ追加します。

source-coverageの初期母集団を作ります。

この時点では代表patternだけ先に完成扱いにしません。

## 4. Step 2: source利用条件確認

情報源ごとに、

- attribution要件
- document / code licenseの違い
- content利用条件
- 長文複製可否
- code exampleの扱い

を確認します。

既定は要約 + source refとし、本文コピーを避けます。

利用条件を確認できない場合は保守的に要約またはsource-reference-onlyとします。

## 5. Step 3: reference schemaとindex

先に次を実装します。

- source-catalog.md
- source-coverage.md
- index.md
- evidence-and-authority.md
- evaluation-method.md
- reference entry共通形式

その後に個別patternを収録します。

これにより、追加中でも何が未収録か分かる状態を維持します。

## 6. Step 4: standards / accessibility

次を先に収録します。

- WCAG 2.2
- relevant Understanding
- relevant Techniques / Failures
- WAI-ARIA APG Patterns
- WAI-ARIA APG Practices

理由は、複数Design Systemがこれらを前提にするためです。

source-coverage上の対象をすべて閉じます。

## 7. Step 5: official Design Systems / platform guidance

情報源ごとに全公開対象をinventory順に処理します。

順序自体は実装効率のためであり、重要度ランキングではありません。

候補順:

1. GOV.UK Design System
2. USWDS
3. Carbon
4. Fluent 2
5. Atlassian Design System
6. Adobe Spectrum
7. GitHub Primer
8. Salesforce Lightning Design System
9. SAP Fiori
10. GNOME Human Interface Guidelines
11. Apple Human Interface Guidelines
12. Material Design
13. Shopify Polaris

各sourceで、

- source item取得
- common entryへ統合可能か確認
- source固有差分をplatform fileへ記録
- coverage status更新

を同じ工程で行います。

## 8. Step 6: general pattern / heuristic sources

- ソシオメディア UIデザインパターン
- Nielsen Norman Groupの採用資料
- UI-Patterns.com
- Welie等、実装時に採用確定したpattern source

を処理します。

既にofficial sourceで十分定義される内容もsource provenanceとして価値があればmerged-duplicateで関係を保持できます。

本文を重複コピーしません。

## 8.1 Plan作成時点で確認済みの取得上の注意

実装時に再確認しますが、Plan作成時点では少なくとも次を確認しています。

- WAI-ARIA APGはPatterns一覧とPractices一覧が公開され、patternページには目的、Keyboard Interaction、WAI-ARIA Roles / States / Propertiesを持つ。
- GOV.UK Design SystemはComponentsとPatternsを分離し、Patternsをuser-focused taskのbest practice solutionとして公開している。
- USWDSはComponents一覧とPatterns一覧を公開し、component lifecycle / statusも公開している。Plan調査時点のComponents overviewは47 componentsを表示する。
- CarbonはcoreのUniversal patternsと、core非保証のCommunity patternsを分離している。
- PrimerはComponentsとは別にUI Patternsを公開している。
- Apple HIGはDesign principles / Foundations / Patterns / Components / Inputsを分けて公開している。
- GNOME HIGはPatternsをContainers / Navigation / Controls / Feedbackに分け、GuidelinesにKeyboard、Pointer & Touch、Scaling & Adaptiveness、Accessibility等を持つ。
- ソシオメディア UIデザインパターン一覧は複数ページに分かれているため、1ページ目だけでinventoryを閉じない。
- Material Design 3の主要ページはJavaScript依存で取得手段によって本文を取得できない場合がある。公式の代替公開経路を確認し、取得できなければunavailableとする。
- 旧Polarisの一部URLは現在Shopify DeveloperのPolaris referencesへredirectする。旧URLの内容をcurrentと仮定せず現行canonical sourceを棚卸しする。

## 9. Step 7: completeness gate

source-coverage validatorを実行し、

- status未設定
- includedなのにdestinationなし
- source ref不明
- orphan reference
- broken index
- required metadata不足

を0にします。

unavailable / source-reference-onlyは理由があれば未達扱いにしません。

未処理の空欄は未達です。

## 10. Step 8: usability-evaluation Skill本体

reference inventoryが利用可能になった後に、

- SKILL.md
- output-template
- deterministic validator
- trigger eval
- semantic rubric / cases

を実装します。

Skill本体を先に作り、後から知識を少しずつ足して完成扱いにはしません。

## 11. Step 9: workflow統合

PR #12 / #13 merge後実装へ合わせて、

- qa-workflow
- test-analysis
- test-condition-design
- test-target-inspection
- test-execution
- exploratory-testing
- 必要ならregression-testing
- 必要ならqa-knowledge
- project context
- workflow state

のtrigger / routing / guidanceを最小変更します。

各owner Skillへusability固有ロジックを複製しません。

各Skill側には「いつusability-evaluationを利用するか」「結果をどう受け取るか」の境界だけ追加します。

## 12. Step 10: repository integration

最新mainを基準に更新します。

少なくとも:

- CANONICAL_SKILLS
- 必要なMULTI_USE_SKILL_TARGETS
- qa-workflow validator
- routing fixtures
- .github/workflows/validate-skills.yml
- README.md
- EVALS.md
- ASSERTIONS等、実装時に存在するSkill一覧 / 評価資料
- repository tests

Skill件数・query件数は実装開始時の正本から再計算し、現在Plan記載値をハードコードしません。

## 13. trigger eval

既存repository標準件数を維持します。

境界を重点的に含めます。

positive例:

- このDialogが一般的なUI patternとaccessibilityに沿っているか評価
- テスト分析前にこのUIの使いづらさのリスク候補を洗い出す
- 実行中に取得したscreenshotとARIA snapshotからUX上の問題を確認
- このFormのvalidation / error recoveryをbest practiceと照合

negative例:

- TCを実行してPASS / FAILだけ返す
- Product Riskを採点
- E2Eコードを実装
- current UI inventoryだけ更新
- pixel diffだけ実施

## 14. deterministic eval

最低限:

- output schema
- source ref
- evidence ref
- status
- required fields
- unresolved constraints
- source catalog / coverage
- index integrity

を検証します。

意味判断を正規表現で代替しません。

## 15. semantic eval

最低限、以下のcaseを用意します。

### Case A: Dialog

- 仕様上のTCはPASS
- focus / close / feedbackのUX問題あり
- TC FAILへ昇格しないこと

### Case B: Form validation

- project Authority
- WCAG
- general pattern
- heuristic

が混在し、根拠の強さを正しく分けること

### Case C: responsive visual issue

DOM上は存在するがmobile screenshotでprimary actionが欠ける。

画像証拠を適切に使うこと。

### Case D: pattern applicability

Accordionに見えるUIだがuser goal / content構造から別patternが妥当な可能性がある。

見た目だけで機械適用しないこと。

### Case E: design stage

Figma / specificationだけを入力し、live behaviorを観測したと偽らないこと。

### Case F: Exploration

Observationを一般heuristicへ照合するが、ユーザーが実際に困る割合を捏造しないこと。

### Case G: source conflict

platform guidelineとgeneric Design Systemで推奨が異なる。

対象platform / project採用規約を優先すること。

### Case H: no issue

一般patternから逸脱して見えるがproject context上は妥当。

false positiveを作らないこと。

## 16. real Agent evaluation

dataset構造検証だけで実装完了にしません。

既存semantic runner + 実Judgeを使える環境で、代表caseのcandidate outputを生成・評価します。

実AgentがSkillを正しく発火し、root index → sub-index → 必要referenceの順で読み、無関係なreferenceを一括読込しないことも確認します。

外部LLM APIをCIの必須条件にはしません。

## 17. browser smoke

PR #12の実行基盤を利用できる場合、

- test-target-inspection evidence → usability-evaluation
- test-execution evidence → usability-evaluation

の代表経路を実Agentで確認します。

同一sessionへの並行操作をしないことを確認します。

環境が利用できない場合、未検証として記録し、架空の成功結果を作りません。

## 18. 完了条件

次をすべて満たしたとき実装完了とします。

- usability-evaluation Skill packageがAgent Skills仕様を満たす
- SKILL.mdからreferences/index.mdへ到達できる
- root indexからpatterns / accessibility / platformsのsub-indexへ到達できる
- sub-indexから対象pattern / concern / platform別referenceへ到達できる
- 通常評価で全referencesの一括読込を要求しない
- source discovery対象categoryと候補sourceの採否がsource inventoryへ記録されている
- 採用sourceの対象母集団がsource-coverageへ記録されている
- 全source itemがincluded / merged-duplicate / out-of-scope / unavailable / source-reference-onlyのいずれかへ閉じている
- JavaScript依存、login限定、deprecated / archived、redirect等の取得制約をcurrent sourceと混同せず状態化している
- included referenceのsource追跡が可能
- reference catalog validator PASS
- deterministic eval PASS
- semantic dataset構造 PASS
- repository trigger / deterministic / semantic tests PASS
- skills-ref validate PASS
- qa-workflow routing tests PASS
- README / EVALS / repository Skill一覧整合
- 代表semantic caseを実Judgeで確認
- 利用可能な場合、実Agent triggerとbrowser evidence連携を確認
- TC PASS / FAILとUX Findingの分離を確認
- Product Risk owner境界を確認
- user researchを捏造しないことを確認
- 同一browser/sessionへの並行操作を要求しない
- git diff --check PASS

## 19. 対象外

今回追加しません。

- 定期source crawler
- 自動Web更新service
- vector DB / RAG server
- graph DB
- browser automation framework
- screenshot pixel-diff engine
- Design System implementation framework
- UX総合score
- 自動user research
- session replay分析基盤
- analytics収集基盤
- 全画面を常時評価するbackground daemon
- 一般guidanceから仕様Authorityを自動生成する仕組み
