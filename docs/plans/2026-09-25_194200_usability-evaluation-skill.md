# UI/UX評価・ユーザビリティ検査Skill追加Plan

このPlanは、UIパターンの目的・rationale・standard・Design System等の知識からUI / UXを根拠付きで評価する `usability-evaluation` と、生きたWeb UIを実際に操作・観測してユーザビリティ上の問題を検出し、標準・明示基準で判定可能な項目は客観的に判定する `usability-inspection` の2 Skillを追加する実装計画です。

## 対象ブランチ

feat/usability-evaluation-skill

このブランチは main@3510e6ffce87ba8c025ebde22f9947dbb6074f9c から作成しています。

実装開始時はPR #11 / #12 / #13がmainへmerge済みであることを前提とし、merge後の実装、Skill数、評価契約、workflow state、browser safety契約を再確認してから本Planを最新mainへ追従させます。

現在の依存関係:

- PR #11: 決定論的runtime、Machine Entity、traceability / freshness
- PR #12: test-target-inspection、test-execution、実対象観測、画像確認、browser safety
- PR #13: exploratory-testing、regression-testing、qa-knowledge、複数workflowのrouting / concurrency

両Skillはこれらを再実装しません。`usability-evaluation` はreference knowledgeによる専門評価、`usability-inspection` はlive Web UIの操作・観測・測定と適用可能な標準判定に責務を限定します。

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

## workflow上の位置づけ

どちらも通常フローの固定工程にはしません。

`usability-evaluation` は設計資料または既存evidenceをreference knowledgeへ照合する横断的な評価Skillです。

`usability-inspection` はlive Web UIを実際に操作・観測してユーザビリティ上の問題を確認する要求がある場合に起動する独立Activityです。

~~~text
live Web UI
    ↓
usability-inspection
    ├→ objective observation / measurement
    ├→ applicable standard / binding criterion check
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

両Skillは他Skillのowner責務を置き換えません。

- Product Riskの識別・評価・採点 → test-analysis
- テスト条件 / カバレッジ項目 → test-condition-design
- 仕様上の期待結果を持つ詳細TC → test-case-design
- current UI情報の収集・更新 → test-target-inspection
- TCの実操作・PASS / FAIL → test-execution
- Exploration / Investigation → exploratory-testing
- routing / common workflow state → qa-workflow
- live Web UIのユーザビリティ検査・測定 → usability-inspection
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

初版の代表パターンだけを収録する方式にはしません。

実装時に採用する情報源について、公開かつ取得可能で本Skillの対象に該当する情報を棚卸しし、取得できたUI / UX知識を構造化して references 配下へ収録します。

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
2. 情報源・reference構造・網羅性契約  
   2026-09-25_194200_usability-evaluation-skill_02_reference-knowledge.md
2a. 情報源探索・収集・網羅性ゲート  
   2026-09-25_194200_usability-evaluation-skill_02a_source-acquisition-and-coverage.md
3. UI / UX評価方法・証拠・判定境界  
   2026-09-25_194200_usability-evaluation-skill_03_evaluation-contract.md
4. 既存Skill / workflow統合  
   2026-09-25_194200_usability-evaluation-skill_04_workflow-integration.md
4a. usability-inspectionのworkflow統合  
   2026-09-25_194200_usability-evaluation-skill_04a_usability-inspection-workflow-integration.md
5. Skill package・成果物・validator  
   2026-09-25_194200_usability-evaluation-skill_05_skill-package.md
5a. usability-inspection package・成果物・評価  
   2026-09-25_194200_usability-evaluation-skill_05a_usability-inspection-package-and-evaluation.md
5b. usability-inspectionの決定論的runtime契約  
   2026-09-25_194200_usability-evaluation-skill_05b_usability-inspection-deterministic-runtime.md
6. 評価・CI・実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06_evaluation-ci-implementation-order.md
6a. usability-inspectionの実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06a_usability-inspection-implementation-order.md

## 固定方針

1. usability-evaluation は横断的な専門評価Skillとし、通常の設計フローへ無条件に追加しない。
2. test-target-inspection / test-executionの成果物は、UI / UX評価がユーザー要求・案件scope・qa-workflowで明示的に選定された場合にread-only入力として再利用できる。ただし、それらの実行だけを理由にusability-evaluation / usability-inspectionを既定起動しない。分析・設計ではUIが対象で、user goal / interaction / usability / accessibility / visual qualityが判断へ影響する場合にusability-evaluationを利用する。
3. Skill自身がProduct Risk、TC、Regression membership等を所有しない。
4. 仕様上のPASS / FAILとUI / UX評価結果を分離する。UI / UX評価項目は問題なし・判定不能・対象外も保持できるが、PR #13のFindingは後続QA活動で扱う必要がある項目だけに作成する。
5. UIパターン名だけからチェックリストを機械適用せず、ユーザー目的、利用文脈、適用条件を先に確認する。
6. プロジェクト固有仕様 / 採用Design System / platform要件を一般的なheuristicより優先する。
7. 同じ観測事実を再取得するためにbrowserを重複操作せず、PR #12で得られるDOM、accessibility tree、ARIA snapshot、screenshot、状態、操作結果を優先して再利用する。
8. test-execution等がbrowser / sessionを所有している最中に、別Agentが同じ実対象を並行操作することを前提にしない。
9. immutableまたは変更されない証拠snapshotに対する評価は、hostが安全に並行実行できる場合のみ独立実行を許容するが、workflow契約として真の並行実行を要求しない。
10. visual defect判定ではDOMと画像の役割を分け、画像でしか確認できない重なり、欠け、overflow、配置、視覚階層等はscreenshot等を使う。
11. アクセシビリティはWCAG適合全体を推測せず、観測・確認したSuccess Criterionやpattern単位で判定する。role / state / propertyやHTML上のARIA利用を評価する場合は、適用可能なWAI-ARIA 1.2 / ARIA in HTMLのcurrent Recommendationを規範的根拠として区別する。
12. WAI-ARIA APGはinformative guidanceとして扱い、example実装を唯一の正解やproduction要件として扱わない。
13. Nielsen等のheuristicは一般原則として扱い、仕様Authorityへ昇格しない。
14. 外部資料本文を丸ごと転載しない。referencesには構造化した要約、評価観点、適用条件、source item refを保持する。
15. 採用した情報源の対象ページはcoverage dispositionで収録済み / 重複統合済み / 対象外 / 取得不能 / source参照のみへ閉じる。アクセス状態とsource自身のmaturity / lifecycleは別軸で保持し、代表例だけで網羅済みとしない。
16. seed sourceだけで探索を止めず、標準化団体、platform HIG、公式Design System、体系化されたUI pattern library、usability evaluation資料を所定のsource discoveryで追加調査し、採否をsource inventoryへ残す。
17. 「取得できるすべて」は、採用したsourceのUX評価に関係する公開情報をitem単位で閉じることを意味し、無関係なAPI reference、install手順、code sample全文まで複製することは意味しない。
18. 実装時に情報源ごとの利用条件・ライセンスを確認し、許容範囲を超える複製をしない。
19. runtime時の外部Webアクセスを必須にしない。Skill package単独で参照知識を利用可能にする。
20. sourceの更新可能性を隠さず、referenceには出典URLと取得・確認時点を保持する。
21. UX総合点や単一スコアを正本にしない。観測事実、適用根拠、期待される特性、差異、想定される影響とその根拠、sourceを保持する。実ユーザー影響を観測していない場合は観測済み事実として書かない。
22. user researchの代替とは扱わない。heuristic evaluationで分かることと、実ユーザーでしか確認できないことを区別する。
23. 評価開始時に上位観点ごとの今回の扱いを固定し、「今回評価する」とした観点をすべて評価結果へ閉じる。上位観点を選ぶ妥当性はsemantic eval、closureはdeterministic validatorで確認する。
24. `evaluation ref` はusability-evaluation成果物revision内だけで一意なartifact-local refとし、新しいglobal QA ID / Machine Entityを追加しない。
25. 複数source itemを1つのreferenceへ統合しても、各source itemの位置づけと適用条件を保持する。内容を収録した各adopted sourceは最低1件を原文とspot-checkする。
26. UI / UX評価項目で複数根拠を使う場合は、各 `reference entry ref + source item ref` ごとに今回のreferenceの位置づけを保持し、binding / advisory等を1つの値へ統合しない。
27. cross-link探索はseed / Q1〜Q7の採否後に固定したcross-link root setからだけ1-hop行い、cross-link由来sourceを今回の探索起点へ再帰追加しない。
28. source ID / source item ref / reference entry IDはusability-evaluation package内のappend-only IDとし、並べ替えや名称変更で振り直さず、削除済みIDを別identityへ再利用しない。
29. usability-evaluationはUI pattern knowledgeによる専門評価を主責務とし、代表ユーザーを用いたusability studyを実施したとは扱わない。
30. usability-evaluationの「問題なし」は今回のscope / evidence / referenceの範囲で問題を確認しなかったことを意味し、製品全体のusabilityを保証しない。
31. usability-inspectionはtask / personaを必須入力にせず、対象scopeからapplicableなinteraction、feedback、accessibility、visual / responsive、standard criterion、performanceを検査する。task / flowは明示された場合だけ追加で扱う。
32. usability-inspectionでは製品固有の正解手順、test id、hidden DOM、source code、backend state等をUI発見shortcutとして使わない。特別な利用者条件はユーザーまたは案件が明示した場合だけ適用する。
33. 観測事実、measurement、standard / binding criterion result、usability-evaluationによる専門評価を成果物上で分離する。
34. 明確なstandard / binding requirementはcriterion単位でPASS / FAIL / 判定不能 / 対象外へ閉じ、applicability、exception、観測事実 / 値、evidence、必要なAuthorityを保持する。FAILは適用可能な違反を確認できた場合に記録できるが、PASSは今回宣言したscopeについて必要なapplicable populationとrequired checksを閉じられた場合だけ記録する。
35. 一般heuristic、ISO interaction principles、第三者Design System等のadvisory guidanceをstrictな仕様FAILへ自動変換しない。
36. 単一component / 単一画面のcriterion PASSから製品全体のWCAG conformance等を宣言しない。
37. usability-evaluationのseed sourceは自動採用しない。既存adopted sourceにない明確な評価価値を確認してadoptし、一度adoptしたsourceはadopted scope内の関連情報を従来どおり全件closureする。
38. usability-inspectionのlive実行対象は初版では既存Playwright経路で到達できるWeb UIに限定する。mobileはresponsive Web viewportを意味し、native mobile appの能動操作は対象外とする。
39. usability-inspectionがbrowser / session ownerとなり、usability-evaluationはimmutable evidenceをread-onlyで評価する。同一sessionを並行操作しない。
40. Playwrightのimplicit auto-scrollをvisual / pointer上のdiscoverability成功として扱わず、必要なscrollはuser actionとして観測する。
41. Playwrightのactionability auto-waitを操作後のsystem responsivenessへ混ぜない。pre-action waitとactual input後のresponseを分離する。
42. performance measurementはmeasurement method、start / end、value / unit、environment、threshold Authorityの有無を保持し、project thresholdがなければ任意の仕様FAIL thresholdを創作しない。
43. metricの定義・測定条件を満たさない値を既存metric名へ読み替えない。単一Playwright runからfield percentileを要求するCore Web Vitals達成等を断定しない。
44. task / flowが明示された場合は実操作できるが、詳細TCの忠実実行と仕様上のPASS / FAILはtest-executionへroutingする。
45. Agent / tool capabilityの失敗だけをproduct usability問題へ自動変換しない。
46. Cognitive Walkthroughはlearnability等を重点確認する場合の任意技法とし、通常inspectionの固定工程や独立Skillにはしない。
47. usability-inspectionはtest-target-inspection / test-executionの既定後処理にはしない。ただし既存成果物はpreflight / evidenceとしてread-only再利用できる。
48. 「ユーザビリティテストして」等の依頼はusability-inspectionのtrigger aliasとして受けられるが、成果物ではhuman participantを用いる正式なusability testingを実施したとは表現しない。
49. 「usabilityを確認」「UIの使いやすさを見て」等の実操作有無が不明な依頼はtrigger boundaryとして扱い、live Web UIを操作して検査するならusability-inspection、design artifact / screenshot / 取得済みevidenceのreference-based評価ならusability-evaluationへroutingする。
50. usability-inspectionでref採番、scope closure、数値計算、threshold比較、完全にmachine-decidableなtest rule等をLLMへ手計算させず、PR #11 merge後のcurrent Skill runtime contractを使って決定論的scriptへ移す。
51. W3C ACT Rulesはaccessibility test methodのinformative sourceとして利用できるが、ACT Rule resultをWCAG / ARIA requirement全体のconformance resultへ無条件に読み替えない。formal / proposed等のsource statusを保持する。
52. deterministic checkがrequirementの一部だけを評価する場合、rule PASSだけでcriterion PASSにしない。population / exception / manual checkを閉じられない場合はcriterionを判定不能として、確認済みrule resultをevidenceとして残す。
53. screenshot、DOM、accessibility tree、raw snapshot等はsecret・個人データ・機密情報を含み得るため、PR #12のevidence安全契約を再利用して必要最小限だけ取得・保存し、raw evidenceを成果物の必須条件にしない。
54. deterministic runtime、deterministic validator、semantic evalを分離し、同じ実装で生成と検証を行わない。