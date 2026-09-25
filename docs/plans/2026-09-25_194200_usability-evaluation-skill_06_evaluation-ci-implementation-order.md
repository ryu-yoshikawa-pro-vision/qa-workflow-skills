# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-evaluation` の実装順序と完了条件です。

`usability-inspection` の実装順序は `_06a_usability-inspection-implementation-order.md` を正本とします。

本ファイルの完了だけではPR全体の後続実装完了とは扱いません。

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

加えて、Plan作成時のseed sourceだけで閉じず、`_02a_source-acquisition-and-coverage.md` §5のsource discoveryを順番どおり実施します。まずseed確認とQ1〜Q7のcandidate採否を閉じ、seed / query由来のadopted sourceへsource IDを付与してcross-link root setを固定します。そのroot setからだけ1-hop cross-link探索を行い、cross-link由来で新たにadoptしたsourceへ探索完了後にsource IDを付与します。candidateは `source-catalog.md` へ記録し、pendingを0にしてからadopted sourceのitem inventoryへ進みます。

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

既定は要約 + source item refとし、本文コピーを避けます。

利用条件を確認できない場合は保守的に要約またはsource-reference-onlyとします。

## 5. Step 3: reference schemaとindex

先に次を実装します。

- source-catalog.md
- source-coverage.md
- index.md
- evidence-and-authority.md
- evaluation-method.md
- reference entry共通形式
- source discovery query matrix
- reference catalog validatorの最小schema検証

この時点で大量のreference本文は作りません。

## 6. Step 4: 縦断検証

全source収録前に、最終契約を実測するための代表経路を1本成立させます。

最低限:

- Dialog pattern
- WAI-ARIA 1.2のDialogに関係するrole / state / property
- ARIA in HTMLのDialog実装に関係するauthor conformance requirement
- WAI-ARIA APGのDialog guidance
- Dialogに関係するWCAG 2.2の適用可能な項目
- official Design System 1つのDialog guidance
- usability heuristic 1つ以上
- DOM / accessibility evidence
- screenshotで確認するvisual観点

このsubsetだけを使って、次を先に実装・検証します。

- `SKILL.md` のindex参照
- root index → sub-index → referenceの読込
- output-template
- 上位観点の評価scope固定とclosure
- artifact-localなevaluation ref
- UI / UX評価項目とFindingの分離
- binding / advisoryとapplicability
- reference catalog validator
- deterministic output validator
- semantic evalの代表case
- PR #12契約と同じ形のfixture / 保存済みevidenceを入力した評価
- 同一browser / sessionを競合操作しないこと

このStepでは `test-target-inspection` / `test-execution` / `qa-workflow` 自体を先行変更しません。PR #12の入力・evidence契約と同じ形のfixtureまたは既存の保存済みevidenceを使い、usability-evaluation単体の入出力・reference読込・評価契約を検証します。実owner Skillへの接続はStep 10だけで行います。

このStepは最終収録範囲を縮小するものではありません。ここで契約を確認した後、Step 5〜7ですべてのadopted source itemを収録し、Step 8のcompleteness gateを満たすまで実装完了とは扱いません。

縦断検証でschema変更が必要になった場合は、この時点で修正してから全source収録へ進みます。

## 7. Step 5: standards / accessibilityを全件収録

次をsource inventory順に処理します。

- WCAG 2.2
- relevant Understanding
- relevant Techniques / Failures
- WAI-ARIA 1.2 Recommendation
- current ARIA in HTML Recommendation
- WAI-ARIA APG Patterns
- WAI-ARIA APG Practices

source-coverage上の対象をすべて閉じます。

## 8. Step 6: official Design Systems / platform guidanceを全件収録

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
- coverage disposition / access state / maturity / field-level coverage更新

を同じ工程で行います。

## 9. Step 7: general pattern / heuristic sourcesを全件収録

- ソシオメディア UIデザインパターン
- Nielsen Norman Groupの採用資料
- UI-Patterns.com
- Welie等、実装時に採用確定したpattern source

を処理します。

既にofficial sourceで十分定義される内容もsource provenanceとして価値があればmerged-duplicateで関係を保持できます。

本文を重複コピーしません。

### Plan作成時点で確認済みの取得上の注意

実装時に再確認しますが、Plan作成時点では少なくとも次を確認しています。

- WAI-ARIA 1.2は2023-06-06 Recommendation。WAI-ARIA 1.3はPlan確認時点で2026-06-04 Working Draftのためcurrent Recommendationと同じ強さで扱わない。
- ARIA in HTMLはPlan確認時点で2026-08-11 Recommendationで、HTML要素へのARIA利用に関するauthor conformance requirementsを定義する。
- WAI-ARIA APGはPatterns一覧とPractices一覧が公開され、patternページには目的、Keyboard Interaction、WAI-ARIA Roles / States / Propertiesを持つ。APGはinformative guidanceとして扱う。
- GOV.UK Design SystemはComponentsとPatternsを分離し、Patternsをuser-focused taskのbest practice solutionとして公開している。
- USWDSはComponents一覧とPatterns一覧を公開し、component lifecycle / statusも公開している。Plan調査時点のComponents overviewは47 componentsを表示する。
- CarbonはcoreのUniversal patternsと、core非保証のCommunity patternsを分離している。
- PrimerはComponentsとは別にUI Patternsを公開している。
- Apple HIGはDesign principles / Foundations / Patterns / Components / Inputsを分けて公開している。
- GNOME HIGはPatternsをContainers / Navigation / Controls / Feedbackに分け、GuidelinesにKeyboard、Pointer & Touch、Scaling & Adaptiveness、Accessibility等を持つ。
- ソシオメディア UIデザインパターン一覧は複数ページに分かれているため、1ページ目だけでinventoryを閉じない。
- Material Design 3の主要ページはJavaScript依存で取得手段によって本文を取得できない場合がある。公式の代替公開経路を確認し、取得できなければunavailableとする。
- 旧Polarisの一部URLは現在Shopify DeveloperのPolaris referencesへredirectする。旧URLの内容をcurrentと仮定せず現行canonical sourceを棚卸しする。

## 10. Step 8: completeness gate

source-coverage validatorを実行し、

- source-catalogのpending candidate
- Q1〜Q7のdiscovery実行記録不足 / 未完了
- cross-link root set未固定、またはroot setとseed / query由来adopted source集合の不一致
- cross-link root set内source IDのcross-link実行記録不足 / 未完了
- cross-link由来sourceを今回のroot setへ再帰追加している状態
- discovery実行記録のblocked残存
- coverage disposition未設定
- access state未設定
- includedなのにdestinationなし
- included / merged-duplicateで `available_dimensions != captured_dimensions`
- source item ref不明
- orphan reference
- broken index
- required metadata不足

を0にします。

`unavailable` / `source-reference-only` は理由があれば未達扱いにしません。maturity / lifecycleはsource自身が明示する場合だけ保持し、coverage dispositionやaccess stateへ混ぜません。

未処理の空欄は未達です。

## 11. Step 9: Skill / evalを全referenceへ拡張

Step 4で成立させた `SKILL.md`、output-template、validator、trigger / semantic evalを全referenceへ拡張します。

追加したpattern / sourceで、

- index routing
- alias
- 各source item refとsource上の位置づけ / 適用条件の対応
- 評価行の各 `適用したreference` でreference entry ref / source item ref / 今回のreferenceの位置づけが対応していること
- output contract
- false positive抑制

が崩れていないことを確認します。

さらに、`_05_skill-package.md` §10の規則でadopted sourceごとのreference spot-check fixtureを作り、原文との意味一致を確認します。

全referenceを収録しただけでSkill完成扱いにせず、Step 4で確認した実行契約が全体でも維持されることを確認します。

## 12. Step 10: workflow統合

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

test-target-inspection / test-executionの既存evidenceは、UI / UX評価が明示的に選定された場合だけread-only入力として再利用します。通常live UIにも既定接続は設けません。Regressionではregression-testingが確定したUI / UX評価scopeだけを接続します。

## 13. Step 11: repository integration

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
## 14. trigger eval

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

このnegativeはdirect triggerの評価です。

別途workflow統合caseとして、少なくとも次を追加します。

~~~text
ユーザー要求: TCを実行
→ usability-evaluationは発火せず、test-executionだけで完了

ユーザー要求: TCを実行し、そのevidenceでUI / UXも評価
→ test-executionがTCを実行してUI evidenceを取得
→ 明示されたUI / UX評価scopeに対してusability-evaluationがread-only評価
→ TCの仕様上PASS / FAILとUI / UX評価項目を分離
→ follow-upが必要な評価項目だけFindingを作る
~~~

`test-target-inspection` もstandalone / qa-workflow経由の両経路を代表caseで確認します。

Regression統合では、Regression scopeにUI / UX評価が含まれないTCについてusability-evaluationが追加実行されないこと、UI / UX評価scopeが明示された場合だけ既存evidenceを再利用することを確認します。

test-analysis統合では、少なくとも次を確認します。

~~~text
UI中心のtest-analysis
→ usability-evaluationがuser goal / pattern / failure mode候補 / 観測候補を返す
→ Product Riskの識別・impact / likelihood / score確定はtest-analysisだけが担当
→ usability-evaluationがrisk scoreを出さない
~~~

test-condition-design統合では、少なくとも次を確認します。

~~~text
UI patternを含むtest-condition-design
→ usability-evaluationがinteraction / state / accessibility / responsive等の検証観点候補を返す
→ 一般guidanceだけを製品期待結果へ昇格しない
→ current test requirement / Authority / Product Risk / scopeに基づく採否はtest-condition-designが担当
~~~

## 15. deterministic eval

最低限:

- output schema
- evaluation refの成果物revision内一意性
- 上位観点の評価scopeとclosure
- package-local source ID / source item ref / reference entry IDの形式、一意性、参照整合
- reference entry内のsource item ref / source上の位置づけ / 適用条件の対応
- 各評価項目の `適用したreference` におけるreference entry ref / source item ref / 今回のreferenceの位置づけの対応
- evidence ref
- status
- required fields
- unresolved constraints
- source catalog / cross-link root set / discovery実行記録 / coverage disposition / access state / maturity / field-level coverage
- index integrity

を検証します。

意味判断を正規表現で代替しません。

## 16. semantic eval

最低限、以下のcaseを用意します。

### Case A: Dialog

- 仕様上のTCはPASS
- focus / close / feedbackのUX問題あり
- TC FAILへ昇格しないこと
- UI / UX評価項目は問題を確認として残し、follow-upが必要な場合だけFindingを作ること
- 問題なしの評価項目へFindingを作らないこと

### Case B: Form validation

- project Authority
- WCAG
- general pattern
- heuristic

が混在し、各source itemを別々の `適用したreference` として保持し、binding / advisoryとapplicabilityを正しく分けること。複数根拠を1つのreferenceの位置づけへ潰さないこと

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

project Authority、適用standard、platform guideline、generic Design Systemで要求・推奨が異なる。

各根拠の `適用したreference` と位置づけを個別に保持し、固定順位で選ばずbinding / advisoryとapplicabilityを判定すること。binding requirement同士が競合する場合は勝手に1つへ統合せず、Authority conflictとしてroutingすること。

### Case H: no issue

一般patternから逸脱して見えるがproject context上は妥当。

false positiveを作らないこと。

### Case I: 評価scopeのclosure

Dialogの評価で、目的・interaction・feedback・accessibility・visual等の上位観点の一部を根拠なく未評価のまま完了しないこと。

対象外にする場合は理由を残し、「今回評価する」とした観点は `問題を確認 / 問題なし / 判定不能 / 対象外` のいずれかへ閉じること。

## 17. real Agent evaluation

dataset構造検証だけで実装完了にしません。

既存semantic runner + 実Judgeを使える環境で、代表caseのcandidate outputを生成・評価します。

実AgentがSkillを正しく発火し、root index → sub-index → 必要referenceの順で読み、無関係なreferenceを一括読込しないことも確認します。

外部LLM APIをCIの必須条件にはしません。

## 18. browser smoke

PR #12の実行基盤を利用できる場合、

- test-target-inspection evidence → usability-evaluation
- test-execution evidence → usability-evaluation

の代表経路を実Agentで確認します。

同一sessionへの並行操作をしないことを確認します。

環境が利用できない場合、未検証として記録し、架空の成功結果を作りません。

## 19. usability-evaluation完了条件

次をすべて満たしたとき実装完了とします。

- usability-evaluation Skill packageがAgent Skills仕様を満たす
- SKILL.mdからreferences/index.mdへ到達できる
- root indexからpatterns / accessibility / platformsのsub-indexへ到達できる
- sub-indexから対象pattern / concern / platform別referenceへ到達できる
- 通常評価で全referencesの一括読込を要求しない
- Q1〜Q7がsource-catalogのdiscovery実行記録でそれぞれ1件以上 `completed` へ閉じ、seed / query由来adopted sourceのsource ID集合とcross-link root setが一致し、そのroot set内の全source IDだけが1-hop cross-link確認で `completed` へ閉じている。cross-link由来sourceをroot setへ再帰追加せず、0件結果も確認件数 / 新規candidate件数=0として記録され、`blocked` が残っていない
- discoveryで得たcandidateがsource-catalogへ記録され、pendingが0
- 採用sourceごとのadopted scopeとitem列挙元 / 列挙方法がsource-catalogへ記録され、対象item母集団がsource-coverageへ記録されている。source全体を列挙できない場合は有限に列挙できるsubsetだけをadopted scopeとし、source全体を全件取得済みと扱わない
- 全source itemのcoverage dispositionがincluded / merged-duplicate / out-of-scope / unavailable / source-reference-onlyのいずれかへ閉じている
- access stateがcoverage dispositionと分離され、restricted sourceを取得済みと誤認しない
- source自身が明示するmaturity / lifecycleをcoverage dispositionと分離して保持している
- included / merged-duplicate itemのfield-level coverageが `available_dimensions = captured_dimensions` で閉じている
- 取得済みの関連情報を任意に除外してincluded扱いにする経路がない
- JavaScript依存、login限定、deprecated / archived、redirect等の取得制約をcurrent sourceと混同せず状態化している
- included referenceからsource item ref、source ID、canonical URLへ追跡できる
- reference entry内で各source item refにsource上の位置づけ / 適用条件が対応付いている
- 内容を収録した各adopted sourceについて最低1件のreference spot-checkを実施し、patterns / accessibility / platformsの各経路で最低1件は原文との意味一致を確認している
- 各UI / UX評価項目に1件以上の `適用したreference` があり、各行でreference entry ref / source item ref / 今回のreferenceの位置づけが対応し、project固有のbinding根拠を使う場合はその行からproject Authority refを追跡できる
- 判定不能 / 対象外のUI / UX評価項目にstatus reason / 制約・未確認が残る
- usability-evaluation成果物で上位観点ごとの今回の扱いが固定され、「今回評価する」とした観点がすべて評価結果へ閉じている
- source IDが `SRC-\d{3,}`、source item refが `<source ID>-ITEM-\d{4,}`、reference entry IDが `REF-\d{4,}` のpackage-local append-only規則に従い、削除済みIDを別identityへ再利用していない
- evaluation refは成果物revision内だけで一意なartifact-local refで、新しいglobal QA ID / Machine Entityを追加していない
- Regression配下ではregression-testingが確定したUI / UX評価scopeだけが接続され、通常live UIの暗黙接続を前提にしない
- reference catalog validator PASS
- deterministic eval PASS
- semantic dataset構造 PASS
- repository trigger / deterministic / semantic tests PASS
- skills-ref validate PASS
- qa-workflow routing tests PASS
- README / EVALS / repository Skill一覧整合
- 代表semantic caseを実Judgeで確認
- 利用可能な場合、実Agent triggerとbrowser evidence連携を確認
- TC PASS / FAILとUI / UX評価項目を分離し、後続対応が必要な評価項目だけFindingへ昇格することを確認
- test-analysis統合でProduct Riskの識別・評価・採点owner境界を確認
- test-condition-design統合で一般UI guidanceを製品期待結果へ昇格せず、検証観点候補の採否owner境界を確認
- user researchを捏造しないことを確認
- 同一browser/sessionへの並行操作を要求しない
- git diff --check PASS

## 20. 対象外

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
