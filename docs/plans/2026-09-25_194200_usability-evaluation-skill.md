# UI/UX評価・ユーザビリティ検査Skill追加Plan

このPlanは、Web UIについて公開根拠と取得済みevidenceから専門評価を行う `usability-evaluation`、生きたWeb UIを操作・観測してobjective observation、measurement、applicable requirement / supported test rule resultを得る `usability-inspection`、formalなWCAG conformance evaluationをWCAG-EM 2.0で実施する `wcag-conformance-evaluation` の3 Skillを追加する実装計画です。目的は、観測事実・標準上の判定・専門評価・formal conformance methodologyを責務分離したまま既存QA workflowへ接続できるようにすることです。UI / UX資料の網羅収集基盤、独自accessibility testing engine、performance testing platform、人間を用いたusability studyは作りません。task / user contextがない場合はUI品質上の観測・懸念を扱い、製品全体のusabilityやhuman task successを確定したとは扱いません。

## 対象ブランチ

feat/usability-evaluation-skill

このブランチは main@3510e6ffce87ba8c025ebde22f9947dbb6074f9c から作成しました。2026-09-26にPR #11がmainへmergeされ、このbranchにもmainを取り込み済みです。本Plan revisionではPR #11の実装済みruntime契約を正本として扱います。

実装開始時はPR #12 / #13がmainへmerge済みであることを前提とし、merge後の実装、Skill数、評価契約、workflow state、browser safety契約を再確認してから実装へ進みます。

現在の依存関係:

- PR #11: merge済み。決定論的runtime、Machine Entity、traceability / freshness
- PR #12: test-target-inspection、test-execution、実対象観測、画像確認、browser safety
- PR #13: exploratory-testing、regression-testing、qa-knowledge、複数workflowのrouting / concurrency

3 Skillはこれらを再実装しません。`usability-evaluation` はreference knowledgeによる専門評価、`usability-inspection` はlive Web UIの操作・観測・測定とgeneral accessibility inspection、`wcag-conformance-evaluation` はWeb targetに対するWCAG-EM 2.0 methodology / sampling / evaluation closure / reportに責務を限定します。

## 目的

現在のQA workflowには、仕様根拠に基づくテスト分析・設計、実対象のUI情報収集、TCの実行、探索的テストを担当するSkillがあります。

一方、次の責務は明示的なownerがありません。

- 観測したUIがどのUIパターンに相当するかを判断する
- そのパターンが解決するユーザー課題と目的を理解する
- その場面でそのパターンを使うことが妥当かを確認する
- 一般に期待されるinteraction、feedback、状態遷移、keyboard / focus、semanticsを確認する
- viewportや状態変化を含め、重なり、欠け、overflow、重要操作の見切れ等の視覚的な問題を確認する
- 仕様上のPASS / FAILとは分離して、ユーザビリティ上の懸念を根拠付きで示す
- テスト分析・設計時に、UIパターンの目的からUX上のリスク候補や確認観点を提供する

この不足のうち、UI pattern / standard / Design System / heuristic等の知識に基づく専門評価を `usability-evaluation` が担当します。

加えて、次の責務も既存Skillにはありません。

- 実対象を操作し、interaction、feedback、error recovery、keyboard / focus、accessibility、visual / responsive上の問題を観測する
- target size、contrast、focus、reflow等、標準・明示基準で判定可能な項目をcriterion単位で検査する
- visual breakage、clipping、overflow、見切れ等を画像証拠と条件付きで確認する
- user-facing responsivenessやperformanceを、測定条件と数値を保持して実測する
- 客観的な観測事実・標準判定・数値と、AIによる専門評価を分離する
- task / flowが明示された場合は、そのflowも実際に操作してユーザビリティ上の問題を確認する

これを別Skillの `usability-inspection` が担当します。

`usability-inspection` は代表ユーザーを用いたUX researchの代替ではありません。AIエージェントによる実対象検査として扱い、人間のsatisfaction、task completion rate、human task time等を捏造しません。personaやtaskは既定の必須入力にせず、ユーザーまたは案件が明示した場合だけ利用します。

formalなWCAG conformance evaluationはgeneral inspectionと分離し、`wcag-conformance-evaluation` がWCAG-EM 2.0のscope / exploration / sampling / evaluation / reportを所有します。複数Skillが必要なlive評価は `qa-workflow` が直列にオーケストレーションし、`wcag-conformance-evaluation` がsibling Skillのscriptを直接実行しません。

## Input / Function / Output

### usability-evaluation

**Input**

- target scope
- design artifactまたは取得済みevidence
- platform / viewport / state
- project Authority / adopted Design System / applicable standard
- user / role / task / flow等が明示されている場合はそのcontext

**Function**

1. target contextを固定する
2. UI pattern / principle候補とapplicabilityを判断する
3. applicable referenceと要求の位置づけを解決する
4. 観測事実、strict requirement result、advisory guidanceを分離する
5. UI / UX上の差異・想定影響を専門評価する
6. follow-upが必要な項目だけFindingへroutingする

**Output**

- evaluation条件
- UI / UX評価項目
- applied reference refs
- evidence refs
- strict requirement resultとの対応
- status / status reason
- Finding refs

### usability-inspection

**Input**

- live Web target / entry point
- requested inspection scope
- environment / origin
- viewport / device profile / input method
- role / permissionが必要な場合はその条件
- side-effect / cleanup scope
- project Authority / standard / threshold
- task / flowが明示されている場合だけその条件

**Function**

1. preflightとinspection scopeを固定する
2. live UIを操作・観測する
3. machine-readableな事実・測定値を取得する
4. ref採番、scope closure、数値計算、threshold比較、対応済みdeterministic test ruleをSkill runtime scriptへ渡す
5. strict requirement resultと専門評価を分離する
6. usability-evaluationへimmutable evidenceを渡す
7. cleanupとscope closureを完了する

**Output**

- inspection header
- inspection scope closure
- objective observations
- test rule results
- standard / binding requirement checks
- measurements
- 必要なPlaywright action trace
- optional task / flow result
- usability-evaluation refs
- Finding refs
- limitation / cleanup result

### wcag-conformance-evaluation

**Input**

- live Web target / entry point
- evaluation commissioner / self-evaluation responsibility
- target WCAG 2 version
- target conformance level
- digital product scope / excluded scope
- accessibility support baseline
- browser / assistive technology / environment条件
- side-effect / cleanup scope
- project Authority / release gate（存在する場合）

**Function**

1. WCAG-EM 2.0 Step 1でscope / target / accessibility support baselineを固定する
2. Step 2でtargetを探索する
3. Step 3.1でstructured sampleを選定する
4. Step 3.2でstructured sample数の10%以上となるrandom sampleを選定し、selection methodを記録する
5. Step 3.3でcomplete processをsample setへ追加する
6. Step 4.1 / 4.2でsample / complete processを評価する
7. Step 4.3でstructured / random sampleを比較し、新content type / findingがあればStep 2 / 3へ戻る
8. live observationが必要なsample / requirementについてnormalized handoffを出し、`qa-workflow` が `usability-inspection` を直列実行してimmutable evidenceを戻す
9. Step 5でevaluation reportを作成する
10. 条件を満たす場合だけoptional evaluation statementを作成する

**Output**

- evaluation header / revision
- accessibility support baseline
- target exploration
- structured sample set
- random sample set / selection method
- complete process set
- sample requirement results / evidence refs
- structured / random comparison iteration
- WCAG-EM evaluation report
- optional evaluation statement
- conformance claim（WCAG側のclaim条件を別途満たす場合だけ）
- Finding refs
- limitation / blocked reason

random sampleの選択自体はpredictable fixed patternにしません。10%件数計算、duplicate / overlap、cross-reference、Step closure、report構造はSkill-local scriptで機械処理します。

browser操作は `usability-inspection`、inspectionのmachine計算はruntime script、意味判断はLLM / `usability-evaluation` が担当し、同じ判断を複数箇所で再計算しません。formal WCAG評価では `wcag-conformance-evaluation` がmethodology / sample set / reportを所有し、個別sampleのlive observationが必要な場合はhandoff requirementを出します。`qa-workflow` が `usability-inspection` を直列実行し、immutable resultをformal評価へ戻します。

## workflow上の位置づけ

どちらも通常フローの固定工程にはしません。

`usability-evaluation` は設計資料または既存evidenceをreference knowledgeへ照合する横断的な評価Skillです。

`usability-inspection` はlive Web UIを実際に操作・観測してユーザビリティ上の問題を確認する要求がある場合に起動する独立Activityです。

`wcag-conformance-evaluation` は「WCAG 2.2 AAへ適合しているか評価」のようなformal conformance要求で起動し、WCAG-EM 2.0の評価methodologyを所有します。

~~~text
live Web UI
    ↓
usability-inspection
    ├→ objective observation / measurement
    ├→ applicable standard / binding requirement check
    └→ optional task / flow execution
             ↓
      immutable evidence
             ↓
UI pattern / standard / Design System knowledge
             ↓
      usability-evaluation
             ↓
      expert UI / UX evaluation
             ↓
      follow-upが必要な場合だけFinding
~~~

`test-target-inspection` / `test-execution` から既存evidenceを `usability-evaluation` へ渡すことはできますが、`usability-inspection` をそれらの追加処理として実行しません。

3 Skillは他Skillのowner責務を置き換えません。

- Product Riskの識別・評価・採点 → test-analysis
- テスト条件 / カバレッジ項目 → test-condition-design
- 仕様上の期待結果を持つ詳細TC → test-case-design
- current UI情報の収集・更新 → test-target-inspection
- TCの実操作・PASS / FAIL → test-execution
- Exploration / Investigation → exploratory-testing
- routing / common workflow state → qa-workflow
- live Web UIのユーザビリティ検査・測定 / general accessibility inspection → usability-inspection
- formal WCAG conformance evaluation → wcag-conformance-evaluation
- UI pattern / standard / heuristicによる意味判断 → usability-evaluation

## 仕様上の期待結果とUIガイダンスの分離

現在の test-case-design は、一般慣習だけから製品の期待結果を確定しません。この契約を維持します。

usability-evaluation がW3C、Design System、UIパターン集、一般的なheuristic等から得た知識は、プロジェクトの仕様Authorityへ自動昇格しません。

結果は少なくとも次を区別します。

- プロジェクトが採用した仕様 / Design System / 適合基準との不一致
- testableな標準要件への不適合候補
- UIパターンの目的・一般的なガイダンスに照らしたユーザビリティ上の懸念
- 実測した視覚崩れ
- 根拠不足または適用条件不足で判定できない項目

一般的なheuristicや第三者Design Systemとの差異だけを製品不具合、仕様違反、TC FAILとして扱いません。

## referenceの方針

今回の代表パターンだけを収録する方式にはしません。

bundled reference corpusは公開情報だけを対象とします。`references/source-catalog.md` に既知sourceと追加調査で確認したsourceの公式URL、publisher、category、status、access、checked_at、採用状態を保持します。normalized reference本文は、Planで定義した有限な評価能力coverageを満たすために実際に採用したsource itemだけを構造化します。source catalogへ載せたsource全体の全pageを複製・全件収録することは完成条件にしません。非公開・認証必須・有料本文を推測・迂回取得してcorpusへ含めません。

SKILL.mdには個別パターンの詳細を大量に持たせません。

~~~text
SKILL.md
  ↓
references/index.md
  ├→ 評価方法
  ├→ 根拠の適用性・要求の強さ
  ├→ UIパターン索引
  ├→ 横断的なUX原則
  ├→ アクセシビリティ
  ├→ 視覚・レイアウト
  ├→ 状態・feedback・error
  └→ platform / Design System別補足
~~~

Agentは index.md から現在の対象に必要なreferenceだけを追加で読みます。

## 構成

1. 目的・現状・責務境界  
   2026-09-25_194200_usability-evaluation-skill_01_scope-and-responsibilities.md
1a. usability-inspectionの責務・live inspection契約  
   2026-09-25_194200_usability-evaluation-skill_01a_usability-inspection-scope-and-contract.md
1b. wcag-conformance-evaluationの責務・WCAG-EM契約  
   2026-09-25_194200_usability-evaluation-skill_01b_wcag-conformance-evaluation-scope-and-contract.md
2. 情報源・reference構造・網羅性契約  
   2026-09-25_194200_usability-evaluation-skill_02_reference-knowledge.md
2a. 情報源探索・収集・網羅性ゲート  
   2026-09-25_194200_usability-evaluation-skill_02a_source-acquisition-and-coverage.md
2b. reference統合・採用item意味検証・完全性  
   2026-09-25_194200_usability-evaluation-skill_02b_reference-validation-and-completeness.md
2c. seed source catalog・公式URL  
   2026-09-25_194200_usability-evaluation-skill_02c_seed-source-catalog.md
2d. reference artifactの機械可読Markdown schema  
   2026-09-25_194200_usability-evaluation-skill_02d_reference-artifact-schema.md
3. UI / UX評価方法・証拠・判定境界  
   2026-09-25_194200_usability-evaluation-skill_03_evaluation-contract.md
4. 既存Skill / workflow統合  
   2026-09-25_194200_usability-evaluation-skill_04_workflow-integration.md
4a. usability-inspectionのworkflow統合  
   2026-09-25_194200_usability-evaluation-skill_04a_usability-inspection-workflow-integration.md
4b. wcag-conformance-evaluationのworkflow統合  
   2026-09-25_194200_usability-evaluation-skill_04b_wcag-conformance-evaluation-workflow-integration.md
5. Skill package・成果物・validator  
   2026-09-25_194200_usability-evaluation-skill_05_skill-package.md
5a. usability-inspection package・成果物・評価  
   2026-09-25_194200_usability-evaluation-skill_05a_usability-inspection-package-and-evaluation.md
5b. usability-inspectionの決定論的runtime契約  
   2026-09-25_194200_usability-evaluation-skill_05b_usability-inspection-deterministic-runtime.md
5c. Web inspectionの実行条件・responsive / mobile・E2E  
   2026-09-25_194200_usability-evaluation-skill_05c_usability-inspection-coverage.md
5d. general accessibility・WCAG requirement semantics・ARIA / ACT  
   2026-09-25_194200_usability-evaluation-skill_05d_accessibility-requirements-and-act.md
5e. performance / responsiveness measurement  
   2026-09-25_194200_usability-evaluation-skill_05e_performance-measurement.md
5f. wcag-conformance-evaluation package / sampling / runtime  
   2026-09-25_194200_usability-evaluation-skill_05f_wcag-conformance-evaluation-package-and-runtime.md
6. 評価・CI・実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06_evaluation-ci-implementation-order.md
6a. usability-inspectionの実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06a_usability-inspection-implementation-order.md
6b. wcag-conformance-evaluationの実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06b_wcag-conformance-evaluation-implementation-order.md
6c. 3 Skill共通のcanonical live validation・外部実対象検証境界  
   2026-09-25_194200_usability-evaluation-skill_06c_canonical-live-validation.md

## 今回の完成範囲

- live inspectionはWeb UIだけを対象とする。native app向けlive automationは対象外として完結させる。
- bundled reference corpusは公開情報だけを対象とする。認証必須・有料・非公開本文はcorpusへ取り込まない。
- human participantへtaskを依頼して成功率・所要時間・satisfaction等を測定するusability studyは対象外とする。AIによるexpert evaluation / Web live inspectionの結果をhuman studyの結果へ読み替えない。
- 現時点で把握している公開sourceは `_02c_seed-source-catalog.md` に公式URL付きで保持する。実装完了の必須確認対象はcurrent capability coverageに必要なcore sourceと、project / platform条件またはcoverage gapにより実際に採用するsourceに限定する。
- source discoveryは固定件数で打ち切らない一方、公開Web上のsourceを再帰的に無制限探索することも完成条件にしない。定義済みの有限な評価能力coverageを全row closureする。
- normalized corpusへ `included / merged-duplicate` としたsource itemは全件をsource原文と意味照合する。catalogへ載せただけのsource全pageをsemantic validation対象にはしない。
- general accessibility inspectionとformal WCAG conformance evaluationを別Skillへ分離する。formal評価は `wcag-conformance-evaluation` がWCAG-EM 2.0をmethodologyとして使用する。
- ACT Rulesはinformative testing methodとして利用し、全formal / proposed ruleの実装を完成条件にしない。supported ruleだけを実装し、ACT Rules Format 1.1 §4.14.1のconsistencyを検証する。
- general live inspectionでは定義済み上位観点をすべてapplicability判定し、未選択のまま残さない。
- repository implementationの完了には `_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureでAgent / browser E2Eを1本以上PASSさせる。外部実対象・実アカウント・特定assistive technologyを必要とするacceptanceは別ゲートとし、それらが提供されていないことだけでrepository implementationを未完了にしない。
- formal WCAG conformance evaluationは `wcag-conformance-evaluation` でWCAG-EM 2.0 Step 1〜5、accessibility support baseline、structured / random sample、complete process、Step 4.3再sampling loop、reportまで閉じる。

## 固定方針

1. usability-evaluation は横断的な専門評価Skillとし、通常の設計フローへ無条件に追加しない。
2. test-target-inspection / test-executionの成果物は、UI / UX評価がユーザー要求・案件scope・qa-workflowで明示的に選定された場合にread-only入力として再利用できる。ただし、それらの実行だけを理由にusability-evaluation / usability-inspectionを既定起動しない。分析・設計ではUIが対象で、user goal / interaction / usability / accessibility / visual qualityが判断へ影響する場合にusability-evaluationを利用する。
3. Skill自身がProduct Risk、TC、Regression membership等を所有しない。
4. 仕様上のPASS / FAILとUI / UX評価結果を分離する。UI / UX評価項目は問題なし・判定不能・対象外も保持できるが、PR #13のFindingは後続QA活動で扱う必要がある項目だけに作成する。
5. UIパターン名だけからチェックリストを機械適用せず、target purpose、利用文脈、適用条件を先に確認する。user goal / taskが明示・確認できる場合は追加contextとして利用し、存在しない場合に創作しない。
6. プロジェクト固有仕様 / 採用Design System / platform要件を一般的なheuristicより優先する。
7. 同じ観測事実を再取得するためにbrowserを重複操作せず、PR #12で得られるDOM、accessibility tree、ARIA snapshot、screenshot、状態、操作結果を優先して再利用する。
8. test-execution等がbrowser / sessionを所有している最中に、別Agentが同じ実対象を並行操作することを前提にしない。
9. immutableまたは変更されない証拠snapshotに対する評価は、hostが安全に並行実行できる場合のみ独立実行を許容するが、workflow契約として真の並行実行を要求しない。
10. visual defect判定ではDOMと画像の役割を分け、画像でしか確認できない重なり、欠け、overflow、配置、視覚階層等はscreenshot等を使う。
11. アクセシビリティはWCAG適合全体を推測せず、観測・確認したSuccess Criterionやpattern単位で判定する。role / state / propertyやHTML上のARIA利用を評価する場合は、適用可能なWAI-ARIA 1.2 / ARIA in HTMLのcurrent Recommendationを規範的根拠として区別する。
12. WAI-ARIA APGはinformative guidanceとして扱い、example実装を唯一の正解やproduction要件として扱わない。
13. Nielsen等のheuristicは一般原則として扱い、仕様Authorityへ昇格しない。
14. 外部資料本文を丸ごと転載しない。referencesには構造化した要約、評価観点、適用条件、source item refを保持する。
15. source-catalogは既知sourceとcandidateの公式URL・位置づけ・状態を追跡する索引とし、source全page一覧にはしない。normalized referenceへ実際に採用したsource itemだけをincluded / merged-duplicate / reference-only / unavailable / out-of-scopeへ閉じる。
16. `_02c_seed-source-catalog.md` のうちcurrent capability coverageに必要なcore sourceを再確認し、Q1〜Q7を実行する。Design System / platform / pattern library等の条件付きseedは、projectで採用されている、target platformへ直接適用する、または能力coverage gapを埋める場合だけ確認・採否を閉じる。Plan側で検索件数・page数を恣意的に制限せず、「新しいsourceが見つからなくなるまで」の再帰探索も完成条件にしない。
17. 「今回すべて対応する」は、今回定義した評価能力・実行経路・成果物契約・検証を閉じることを意味する。公開sourceの全pageや全Design Systemの内容を複製することは意味しない。
18. 実装時に情報源ごとの利用条件・ライセンスを確認し、許容範囲を超える複製をしない。
19. runtime時の外部Webアクセスを必須にしない。Skill package単独で参照知識を利用可能にする。
20. sourceの更新可能性を隠さず、referenceには出典URLと取得・確認時点を保持する。
21. UX総合点や単一スコアを正本にしない。観測事実、適用根拠、期待される特性、差異、想定される影響とその根拠、sourceを保持する。実ユーザー影響を観測していない場合は観測済み事実として書かない。
22. user researchの代替とは扱わない。heuristic evaluationで分かることと、実ユーザーでしか確認できないことを区別する。
23. 評価開始時に上位観点ごとの今回の扱いを固定し、「今回評価する」とした観点をすべて評価結果へ閉じる。上位観点を選ぶ妥当性はsemantic eval、closureはdeterministic validatorで確認する。
24. `evaluation ref` はusability-evaluation成果物revision内だけで一意なartifact-local refとし、新しいglobal QA ID / Machine Entityを追加しない。
25. 複数source itemを1つのreferenceへ統合しても、各source itemの位置づけと適用条件を保持する。normalized corpusへ `included / merged-duplicate` とした全source itemを原文と意味照合し、samplingだけでその採用itemの検証を完了扱いにしない。
26. UI / UX評価項目で複数根拠を使う場合は、各 `reference entry ref + source item ref` ごとに今回のreferenceの位置づけを保持し、binding / advisory等を1つの値へ統合しない。
27. source discoveryではseedとQ1〜Q7、能力coverage gapから追加したqueryのcandidateをcanonical URLで重複排除し、採否を閉じる。cross-linkはnormative dependency、current version / successor、coverage gap解消、意味理解に必要な公式関連documentへ限定し、再帰探索の固定点を完成条件にしない。
28. source ID / source item ref / reference entry IDはusability-evaluation package内のappend-only IDとし、並べ替えや名称変更で振り直さず、削除済みIDを別identityへ再利用しない。
29. usability-evaluationはUI pattern knowledgeによる専門評価を主責務とし、代表ユーザーを用いたusability studyを実施したとは扱わない。
30. usability-evaluationの「問題なし」は今回のscope / evidence / referenceの範囲で問題を確認しなかったことを意味し、製品全体のusabilityを保証しない。
31. usability-inspectionはtask / personaを必須入力にせず、対象scopeからapplicableなinteraction、feedback、general accessibility、visual / responsive、standard criterion、performanceを検査する。task / flowは明示された場合だけ追加で扱う。formal WCAG conformance evaluationは担当しない。
32. usability-inspectionでは製品固有の正解手順、test id、hidden DOM、source code、backend state等をUI発見shortcutとして使わない。特別な利用者条件はユーザーまたは案件が明示した場合だけ適用する。
33. 観測事実、measurement、standard / binding requirement result、usability-evaluationによる専門評価を成果物上で分離する。
34. 明確なstandard / binding requirementはrequirement単位で `satisfied / not-satisfied / undetermined` へ閉じ、applicability、exception、観測事実 / 値、evidence、必要なAuthorityを保持する。WCAG Success Criterionを `passed / failed / inapplicable` とは表現しない。今回のscopeについて必要なapplicable populationとrequired checksを閉じ、requirement全体を満たす根拠が揃った場合だけ `satisfied` とする。検査scopeとして扱わない項目はrequirement resultではなくscope closure側の `対象外` とする。
35. 一般heuristic、ISO interaction principles、第三者Design System等のadvisory guidanceをstrictな仕様FAILへ自動変換しない。
36. 単一component / 単一画面のrequirement `satisfied` から製品全体のWCAG conformance等を宣言しない。formalなWCAG評価要求は `wcag-conformance-evaluation` へroutingする。
37. usability-evaluationのsource確認は、current capability coverageに必要なcore sourceと、実際に採用する条件付きsourceへ限定する。seed一覧に存在するだけの未使用Design System / platform guidanceまで実装完了のために全件再確認しない。採用したsourceでも全本文をadoptせず、能力coverageまたはAuthority / provenance上必要なsource itemだけnormalized corpusへ採用する。
38. usability-inspectionのlive実行対象は既存Playwright経路で到達できるWeb UIに固定する。desktop Web、responsive viewport inspection、touch-capable inspection、mobile device emulationを区別する。mobile device emulationでは実際のdevice profile / viewport / screen / userAgent / deviceScaleFactor / hasTouch / isMobileを記録する。native iOS / Android / desktop appの能動操作は本Skillの対象外とする。
39. usability-inspectionがbrowser / session ownerとなり、usability-evaluationはimmutable evidenceをread-onlyで評価する。同一sessionを並行操作しない。
40. Playwrightのimplicit auto-scrollをvisual / pointer上のdiscoverability成功として扱わず、必要なscrollはuser actionとして観測する。
41. Playwrightのactionability auto-waitを操作後のsystem responsivenessへ混ぜない。pre-action waitとactual input後のresponseを分離する。
42. performance measurementはmetric source、method、start / end、clock domain、value / unit、environment / device profile、threshold Authorityを保持し、project thresholdがなければ任意の仕様FAIL thresholdを創作しない。
43. Navigation Timing、FCP、定義済みuser-facing interaction timingはbrowser/sessionから取得できる範囲で測定する。LCP / CLS / INPは本Skill独自algorithmで再実装せず、project既存のRUM / CrUX / web-vitals instrumentation / Lighthouse等、provenanceを確認できるmeasurement sourceがある場合だけCore Web Vitalsとして扱う。
44. task / flowが明示された場合は実操作できるが、詳細TCの忠実実行と仕様上のPASS / FAILはtest-executionへroutingする。
45. Agent / tool capabilityの失敗だけをproduct usability問題へ自動変換しない。
46. Cognitive Walkthroughはlearnability等を重点確認する入力条件で使用するinspection techniqueとし、起動条件・4つの確認質問・step単位のevidence / result契約を今回実装する。通常inspectionへ無条件には適用せず、独立Skillにはしない。
47. usability-inspectionはtest-target-inspection / test-executionの既定後処理にはしない。ただし既存成果物はpreflight / evidenceとしてread-only再利用できる。
48. 「ユーザビリティテストして」等の依頼はusability-inspectionのtrigger aliasとして受けられるが、成果物ではhuman participantを用いる正式なusability testingを実施したとは表現しない。
49. 「usabilityを確認」「UIの使いやすさを見て」等の実操作有無が不明な依頼はtrigger boundaryとして扱い、live Web UIを操作して検査するならusability-inspection、design artifact / screenshot / 取得済みevidenceのreference-based評価ならusability-evaluationへroutingする。
50. usability-inspectionでref採番、scope closure、数値計算、threshold比較、supported machine-decidable test rule等をLLMへ手計算させず、PR #11のcurrent Skill runtime contractを使って決定論的scriptへ移す。usability-evaluationのevaluation ref / closure / cross-referenceも `evaluation_structure.py` へ移し、Agentへ手採番させない。`test-rule-catalog.json` はsupported ACT / project test ruleのmetadataだけを保持し、structure / geometry / elapsed / threshold helperは `inspection_structure.py` / `measurement.py` に置く。generic rule DSL / plugin systemは追加しない。
51. W3C ACT Rulesはinformative testing methodとして利用する。全ruleの実装は要求せず、live Web scopeで忠実に実装でき、required evidenceを取得でき、official examplesでconsistency検証できるruleだけsupportedとする。supported ACT RuleのoutcomeはACT Rules Format 1.1の `inapplicable / passed / failed / cantTell / untested` を使用する。`untested` はsupported ruleが今回scopeへ選定されたがtest subjectを評価していない場合だけ、`cantTell` は評価を開始したがapplicabilityまたはexpectationを完全に判定できない場合に使用し、rule status、requirements mapping、execution modeと分離する。
52. general accessibility inspectionとformal WCAG conformance evaluationを別Skillへ分離する。formal評価ではtarget WCAG version / level / self-enclosedなdigital product scope / accessibility support baselineを事前に確定し、WCAG-EM 2.0へ従う。supported test ruleがrequirementの一部だけを評価する場合、rule outcomeが `passed` でもrequirementを `satisfied` にしない。
53. screenshot、DOM、accessibility tree、raw snapshot等はsecret・個人データ・機密情報を含み得るため、PR #12のevidence安全契約を再利用して必要最小限だけ取得・保存し、raw evidenceを成果物の必須条件にしない。
54. deterministic runtime、deterministic validator、semantic evalを分離し、同じ実装で生成と検証を行わない。