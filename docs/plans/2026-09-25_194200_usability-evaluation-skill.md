# UIユーザビリティ評価Skill追加Plan

このPlanは、AIエージェントがテスト分析・設計・実対象確認・テスト実行・探索的テストでUIを扱う際に、UI要素や画面構造を単に観測するだけでなく、そのUIパターンの目的、ユーザーが達成しようとしていること、なぜその構造・interactionが採用されるのかを理解したうえで、ユーザビリティ・アクセシビリティ・視覚的な問題を根拠付きで評価するための新規 usability-evaluation Skillを追加する実装計画です。

## 対象ブランチ

feat/usability-evaluation-skill

このブランチは main@3510e6ffce87ba8c025ebde22f9947dbb6074f9c から作成しています。

実装開始時はPR #11 / #12 / #13がmainへmerge済みであることを前提とし、merge後の実装、Skill数、評価契約、workflow state、browser safety契約を再確認してから本Planを最新mainへ追従させます。

現在の依存関係:

- PR #11: 決定論的runtime、Machine Entity、traceability / freshness
- PR #12: test-target-inspection、test-execution、実対象観測、画像確認、browser safety
- PR #13: exploratory-testing、regression-testing、qa-knowledge、複数workflowのrouting / concurrency

本Skillはこれらを再実装せず、UI / UX評価の専門責務だけを追加します。

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

この不足を usability-evaluation が担当します。

## workflow上の位置づけ

本Skillを通常フローの固定工程にはしません。

UIを扱う既存Skillから必要な時点で利用する横断的な評価Skillとします。

~~~text
                        ┌→ test-analysis
                        │   UX上のリスク候補・重点の入力
                        │
                        ├→ test-condition-design
                        │   検証観点候補の入力
                        │
UI pattern knowledge ──→ usability-evaluation
purpose / rationale     │
guidance / standard     ├← test-target-inspection
                        │   current UIの観測
                        │
                        ├← test-execution
                        │   TC実行中のUI状態・証跡
                        │
                        └← exploratory-testing
                            Observation / Finding
~~~

usability-evaluation は他Skillのowner責務を置き換えません。

- Product Riskの識別・評価・採点 → test-analysis
- テスト条件 / カバレッジ項目 → test-condition-design
- 仕様上の期待結果を持つ詳細TC → test-case-design
- current UI情報の収集・更新 → test-target-inspection
- TCの実操作・PASS / FAIL → test-execution
- Exploration / Investigation → exploratory-testing
- routing / common workflow state → qa-workflow

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
  ├→ 根拠の優先順位
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
2. 情報源・reference構造・網羅性契約  
   2026-09-25_194200_usability-evaluation-skill_02_reference-knowledge.md
2a. 情報源探索・収集・網羅性ゲート  
   2026-09-25_194200_usability-evaluation-skill_02a_source-acquisition-and-coverage.md
3. UI / UX評価方法・証拠・判定境界  
   2026-09-25_194200_usability-evaluation-skill_03_evaluation-contract.md
4. 既存Skill / workflow統合  
   2026-09-25_194200_usability-evaluation-skill_04_workflow-integration.md
5. Skill package・成果物・validator  
   2026-09-25_194200_usability-evaluation-skill_05_skill-package.md
6. 評価・CI・実装順序・完了条件  
   2026-09-25_194200_usability-evaluation-skill_06_evaluation-ci-implementation-order.md

## 固定方針

1. usability-evaluation は横断的な専門評価Skillとし、通常の設計フローへ無条件に追加しない。
2. live UIを扱うtest-target-inspection / test-executionでは、UI / UX評価が明示的に対象外でない限り、取得済み証拠を使うread-only評価を既定で接続する。分析・設計ではUIが対象で、user goal / interaction / usability / accessibility / visual qualityが判断へ影響する場合に利用する。
3. Skill自身がProduct Risk、TC、Regression membership等を所有しない。
4. 仕様上のPASS / FAILとUI / UX評価結果を分離する。UI / UX評価項目は問題なし・判定不能・対象外も保持できるが、PR #13のFindingは後続QA活動で扱う必要がある項目だけに作成する。
5. UIパターン名だけからチェックリストを機械適用せず、ユーザー目的、利用文脈、適用条件を先に確認する。
6. プロジェクト固有仕様 / 採用Design System / platform要件を一般的なheuristicより優先する。
7. 同じ観測事実を再取得するためにbrowserを重複操作せず、PR #12で得られるDOM、accessibility tree、ARIA snapshot、screenshot、状態、操作結果を優先して再利用する。
8. test-execution等がbrowser / sessionを所有している最中に、別Agentが同じ実対象を並行操作することを前提にしない。
9. immutableまたは変更されない証拠snapshotに対する評価は、hostが安全に並行実行できる場合のみ独立実行を許容するが、workflow契約として真の並行実行を要求しない。
10. visual defect判定ではDOMと画像の役割を分け、画像でしか確認できない重なり、欠け、overflow、配置、視覚階層等はscreenshot等を使う。
11. アクセシビリティはWCAG適合全体を推測せず、観測・確認したSuccess Criterionやpattern単位で判定する。
12. WAI-ARIA APGのexample実装を唯一の正解やproduction要件として扱わない。
13. Nielsen等のheuristicは一般原則として扱い、仕様Authorityへ昇格しない。
14. 外部資料本文を丸ごと転載しない。referencesには構造化した要約、評価観点、適用条件、source refを保持する。
15. 採用した情報源の対象ページはcoverage dispositionで収録済み / 重複統合済み / 対象外 / 取得不能 / source参照のみへ閉じる。アクセス状態とsource自身のmaturity / lifecycleは別軸で保持し、代表例だけで網羅済みとしない。
16. seed sourceだけで探索を止めず、標準化団体、platform HIG、公式Design System、体系化されたUI pattern library、usability evaluation資料を所定のsource discoveryで追加調査し、採否をsource inventoryへ残す。
17. 「取得できるすべて」は、採用したsourceのUX評価に関係する公開情報をitem単位で閉じることを意味し、無関係なAPI reference、install手順、code sample全文まで複製することは意味しない。
18. 実装時に情報源ごとの利用条件・ライセンスを確認し、許容範囲を超える複製をしない。
19. runtime時の外部Webアクセスを必須にしない。Skill package単独で参照知識を利用可能にする。
20. sourceの更新可能性を隠さず、referenceには出典URLと取得・確認時点を保持する。
21. UX総合点や単一スコアを正本にしない。観測事実、適用根拠、期待される特性、差異、想定される影響とその根拠、sourceを保持する。実ユーザー影響を観測していない場合は観測済み事実として書かない。
22. user researchの代替とは扱わない。heuristic evaluationで分かることと、実ユーザーでしか確認できないことを区別する。
