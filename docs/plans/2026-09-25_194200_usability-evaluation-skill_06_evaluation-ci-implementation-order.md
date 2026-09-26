# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-evaluation` の実装順序と完了条件です。

`usability-inspection` の実装順序は `_06a_usability-inspection-implementation-order.md` を正本とします。

本ファイルの完了だけではPR全体の後続実装完了とは扱いません。

## 1. 実装開始条件

実装開始前に最新状態を再確認します。

次をすべて確認します。

- PR #11 merge済みのlatest main実装とcurrent runtime contract
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

## 3. Step 1: seed source catalog / capability coverage

reference本文を書く前に `_02c_seed-source-catalog.md` の既知sourceを全件再確認します。

各seedで、

- canonical URL / redirect
- publisher / owner
- source category
- publication / lifecycle status
- public access
- checked_at
- license / terms上の扱い
- adopted / reference-only / replaced / unavailable / rejected

を `references/source-catalog.md` へ記録します。

同時に `_02a_source-acquisition-and-coverage.md` §3のcapability coverageを `source-coverage.md` に作成します。

Q1〜Q7はすべて実行し、検索手段が到達できるresult boundaryを記録します。capability coverageにgapがある場合だけ追加queryを作り、candidateの採否を閉じます。

Plan側の任意件数で検索を打ち切りません。一方、「新しいsourceが見つからなくなるまで」cross-linkを再帰探索することも完了条件にしません。

normative dependency、successor / current version、coverage gap解消、意味理解に必要な公式関連documentだけをcross-link確認します。

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
- `scripts/reference_catalog.py` のcanonical URL / ID / coverage生成fixture
- reference catalog validatorの最小schema検証

この時点で大量のreference本文は作りません。

## 6. Step 4: 縦断検証

全source収録前に、最終契約を実測するための縦断経路を1本成立させます。縦断経路には次を含めます。

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
- semantic evalの縦断case
- PR #12契約と同じ形のfixture / 保存済みevidenceを入力した評価
- 同一browser / sessionを競合操作しないこと

このStepでは `test-target-inspection` / `test-execution` / `qa-workflow` 自体を先行変更しません。PR #12の入力・evidence契約と同じ形のfixtureまたは既存の保存済みevidenceを使い、usability-evaluation単体の入出力・reference読込・評価契約を検証します。実owner Skillへの接続はStep 10だけで行います。

このStepは最終能力coverageを縮小するものではありません。ここで契約を確認した後、Step 5〜7で各coverage axisに必要なnormalized referenceを実装し、Step 8のcompleteness gateを満たすまで実装完了とは扱いません。

縦断検証でschema変更が必要になった場合は、この時点で修正してから全source収録へ進みます。

## 7. Step 5: standards / accessibility reference

次をsource catalogでcurrentな公式sourceへ解決し、必要なnormalized referenceを実装します。

- WCAG 2.2
- relevant Understanding / Techniques / Failures
- WCAG-EM 2.0
- WAI-ARIA 1.2
- current ARIA in HTML
- WAI-ARIA APG
- ACT Rules Format 1.1 / All ACT Rules

WCAG / ARIAのbinding / normative requirement、informative guidance、ACT testing methodを混同しません。

All ACT RulesのURL / rule一覧はcatalogから辿れるようにしますが、全ruleを本Skillのsupported implementationへすることは要求しません。

## 8. Step 6: Design System / platform source catalog

`_02c_seed-source-catalog.md` に列挙したGOV.UK、USWDS、Carbon、Fluent 2、Atlassian、Spectrum、Primer、SLDS、SAP Fiori、GNOME HIG、Apple HIG、Material 3、Shopify Polarisをsource catalogへ登録・再確認します。

各sourceの全公開pageをnormalized corpusへ複製しません。

次の場合にsource item / reference entryを作ります。

- capability coverageに必要
- target platform固有のguidanceを保持する必要がある
- projectがDesign Systemを採用している
- common patternへ統合できないsource固有差分がある

## 9. Step 7: general pattern / heuristic reference

seed catalogの、

- ソシオメディア UIデザインパターン
- Nielsen Norman Group
- UI-Patterns.com
- Welie

を再確認します。

capability coverageに必要なpattern / heuristic / methodologyだけnormalized referenceへ取り込みます。

同じ意味を別sourceから重複コピーせず、provenance価値がある場合はmerged-duplicateとしてsource item関係を保持します。

### Plan作成時点で確認済みの取得上の注意

実装時に再確認しますが、Plan作成時点では少なくとも次を確認しています。

- WAI-ARIA 1.2は2023-06-06 Recommendation。WAI-ARIA 1.3はPlan確認時点で2026-06-04 Working Draftのためcurrent Recommendationと同じ強さで扱わない。
- ARIA in HTMLはPlan確認時点で2026-08-11 Recommendationで、HTML要素へのARIA利用に関するauthor conformance requirementsを定義する。
- WAI-ARIA APGはPatterns一覧とPractices一覧が公開され、patternページには目的、Keyboard Interaction、WAI-ARIA Roles / States / Propertiesを持つ。APGはinformative guidanceとして扱う。
- ACT Rulesはtesting methodのinformative ruleとして扱い、WCAG / ARIA requirementそのもののnormative basisへ昇格しない。formal / proposed ruleのapplicability / expectation / requirements mapping / outcome mappingをACT Rule coverageとcheck catalogへ反映する。
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

`reference_catalog.py` と独立validatorを実行し、次を閉じます。

- seed catalogの未確認source
- Q1〜Q7 / gap queryの未完了
- retrieval boundary未記録
- capability coverageの未closure / blocked
- pending candidate
- canonical URL duplicate
- source / item / reference ID不整合
- included / merged-duplicateなのにreference destinationなし
- included / merged-duplicateで `available_dimensions != captured_dimensions`
- semantic validation fail / 未実施
- orphan reference / broken index
- required metadata不足

を0にします。

reference-only / unavailableは理由があれば未達扱いにしません。

catalogへ載せたsource全pageをitem化・意味検証することは要求しません。normalized corpusへ採用した全itemはsemantic validationをPASSさせます。

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

さらに、`_02b_reference-validation-and-completeness.md` の規則で `included / merged-duplicate` の全source itemを原文と意味照合し、`unavailable / source-reference-only` の全itemでdisposition / access state / canonical URLを確認します。samplingだけで完了扱いにしません。

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

boundary caseとして次を追加します。

~~~text
ユーザー要求: usabilityを確認して
live targetを実際に操作する意図あり
→ usability-inspection

ユーザー要求: UIの使いやすさを見て
screenshot / Figma / specification / 取得済みevidenceだけをreference knowledgeへ照合
→ usability-evaluation

ユーザー要求: 表示崩れを確認して
live browserでviewportを変えて実操作・観測
→ usability-inspection

ユーザー要求: このscreenshotの表示崩れを評価して
→ usability-evaluation
~~~

曖昧queryを文字列だけでusability-evaluationへ固定しません。

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

`test-target-inspection` はstandalone / qa-workflow経由の両経路をそれぞれ確認します。

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

次をすべて検証します。

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
- source catalog / seed確認 / discovery実行記録 / retrieval boundary / capability coverage / source item disposition / field-level coverage
- `reference_catalog.py` のcanonical URL / ID / summary生成とvalidatorの独立検証
- index integrity

を検証します。

意味判断を正規表現で代替しません。

## 16. semantic eval

以下のcaseをすべて用意し、実Judgeで評価します。

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

既存semantic runner + 実Judgeを使い、Planで定義した全semantic caseのcandidate outputを生成・評価します。

実AgentがSkillを正しく発火し、root index → sub-index → 必要referenceの順で読み、無関係なreferenceを一括読込しないことも確認します。

外部LLM APIをCIの必須条件にはしません。

## 18. browser smoke

PR #12 / #13 merge後の実行基盤を使い、

- test-target-inspection evidence → usability-evaluation
- test-execution evidence → usability-evaluation
- live Web target → usability-inspection → usability-evaluation

のcanonical経路を実Agentで確認します。環境が利用できなければblockedであり、実装完了にはしません。

同一sessionへの並行操作をしないことを確認します。

環境が利用できない場合、未検証として記録し、架空の成功結果を作りません。

## 19. usability-evaluation完了条件

次をすべて満たしたとき実装完了とします。

- usability-evaluation Skill packageがAgent Skills仕様を満たす
- SKILL.mdからreferences/index.mdへ到達できる
- root indexからpatterns / accessibility / platformsのsub-indexへ到達できる
- sub-indexから対象pattern / concern / platform別referenceへ到達できる
- 通常評価で全referencesの一括読込を要求しない
- `_02c_seed-source-catalog.md` の全seedがsource-catalogへ確認結果・canonical URL・checked_at付きで記録されている
- Q1〜Q7とcapability gapから追加したqueryがcompletedで、retrieval boundaryが記録されている
- capability coverageの全rowがcovered / not-applicableへ閉じ、blockedが0
- source candidateのpendingが0
- cross-linkはnormative dependency / successor / coverage gap / 必要な公式関連documentだけを閉じている
- source status / access state / adoption stateを分離して保持している
- normalized corpusへ使う全source itemがincluded / merged-duplicate / reference-only / unavailable / out-of-scopeへ閉じている
- included / merged-duplicate itemのfield-level coverageが `available_dimensions = captured_dimensions`
- included / merged-duplicate全itemのsemantic validation PASS
- included referenceからsource item ref、source ID、canonical URLへ追跡できる
- reference entry内で各source item refにsource上の位置づけ / 適用条件が対応付いている
- catalogへ載せただけのsource全pageを収録済み・意味検証済みとは主張していない
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
- Planで定義した全semantic caseを実Judgeで確認
- canonical real Agent trigger、browser evidence連携、live Web inspection E2Eを確認。実行環境が利用できない場合はblockedとして実装未完了
- TC PASS / FAILとUI / UX評価項目を分離し、追加QA活動が必要な評価項目だけFindingへ昇格することを確認
- test-analysis統合でProduct Riskの識別・評価・採点owner境界を確認
- test-condition-design統合で一般UI guidanceを製品期待結果へ昇格せず、検証観点候補の採否owner境界を確認
- user researchを捏造しないことを確認
- 同一browser/sessionへの並行操作を要求しない
- git diff --check PASS

### 完全性に関する追加ゲート

- `_02a_source-acquisition-and-coverage.md` のcapability coverageをPASS
- `_02b_reference-validation-and-completeness.md` のmerge / splitと全included item semantic validationをPASS
- `_02c_seed-source-catalog.md` のknown sourceを公式URL付きでcatalogから辿れる
- source discoveryで未知のWeb sourceが存在しないとは主張しない
- normalized corpusへ採用したitemの意味検証ではsamplingを使わない

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
