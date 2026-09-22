# Regression Suite / QA Activity 統合Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みの設計traceability・change impact・execution lineageを再実装せず、継続RegressionとQA activity履歴に残る課題だけを解決する実装計画です。

Graphの構築自体は目的にしません。Regression / Exploration / Investigationの主経路はrelation indexなしで成立させ、実際のquery需要をdirect refとdeterministic scanで満たせない場合だけ最小relation indexを追加します。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ名とファイル名は旧設計の名称を維持します。実装はPR #11 / #12 merge後の最新`main`へ追従し、両PRの実契約を再確認してから開始します。

## 前提

- PR #11のMachine Entity、stable ID、traceability、change impact、freshness / stale / `要再検証`を設計側の正本として扱う
- PR #12の`test-target-inspection`、`test-execution`、TC snapshot、execution / result / rerun契約を実行側の正本として扱う
- E2E SkillのTest Case / testware / execution契約を維持し、TCなしE2Eへ架空TCを追加しない
- project contextを案件固有のscope / policy / 既存QA成果物を発見する既存入口として再利用し、汎用artifact registryは追加しない
- 実装開始時点のSkill数・評価件数・CI構成は最新`main`から再取得する

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Cross-artifact relation index導入判定](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [決定論的補助runtime・履歴発見](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [新規・改修 / Regression / Exploration / Investigation統合](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・Run・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [既存Skill・PR #11/#12統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
7. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. PR #11をdesign identity / traceability / change impact / freshnessの正本とし、PR #13で第二のdesign graphやcurrentness state machineを作らない。
2. PR #12 / E2Eをexecution / result / evidence / rerun lineageの正本とし、PR #13でexecution schemaを複製しない。
3. Regression Suiteは「全current TCの保管庫」ではなく、**現在のRegression対象範囲を継続的に検証するための、currentかつ再利用可能な論理TCの基準集合**とする。
4. 初回導入時はcurrent Regression対象範囲に対してproject-wideなTC discoveryとmembership reconciliationを行う。全TCを漏れなく列挙できる根拠がない場合、baselineを完全なfull基準集合として確定しない。
5. 各新規・改修セッションではSuiteを見直すが、current TCを機械的に全件加入させない。継続Regression対象か、一時的な検証かは`test-analysis`で意味判断する。
6. membershipはTC内容だけで決めない。TC lifecycle / content、Regression対象範囲、案件方針、関連Risk / test objective等のmembership入力が変わった場合に影響memberを再評価する。影響範囲を安全に限定できない場合はcurrent TC全体を再確認する。
7. 「全機能coverage」の母集団はSuite自身から作らない。`project-context-template.md`のテスト範囲・非機能テスト範囲・対象外、current仕様根拠、Product Risk等からcurrent Regression対象範囲を定め、`coverage-analysis`で確認する。
8. feature tagは任意の検索・抽出用metadataとし、Suite membershipやcoverageの成立条件にしない。
9. Regression Suiteの完全性、Run scope、actual executionを分離する。Runは`full`または`selected`であり、selected RunをSuite全体のRegression完了として扱わない。
10. Run scopeはユーザー明示 → 案件コンテキストのRegression方針 → 未定義時のfull fallbackの順で決定する。
11. selected logical TCごとに今回必要なexecution routeを固定する。E2Eが存在するだけでmanual不要と判断せず、`coverage-analysis`（`TC → E2E実装`）を入力にする。
12. logical TCをexecutedとして数えるのは、今回requiredとしたrouteがすべてexecution結果または明示的な未実行 / blocked状態へ閉じた後とする。PASS / FAIL等の結果判定と「実行したか」は分離する。
13. TCなしE2EはTC-based coverageへ算入しない。Regressionへ含める場合はユーザー明示または案件コンテキストの方針で補助testwareとして指定し、TC memberのselected / executed件数とは分離する。
14. Regression Activityはselectionの判断入力ref / revision、baseline / scope ref、execution route、execution refs、未実行 / blockedを保持し、当時の判断を後から再現できるようにする。
15. Activityの状態は既存`qa-workflow`の状態語彙を再利用する。進行中は更新可能、scope / snapshot不変の再開は同じactivity、scope / snapshot変更時は別activity / version、完了後はimmutableとする。
16. Activityは固定保存場所から決定論的に発見できる形を優先する。indexが必要な場合はproject contextの「既存QA成果物」から一意に発見できる単一indexとし、Activity保存とindex登録が両方成功するまで保存完了扱いにしない。
17. `test-target-inspection`はcurrentな実対象情報・UI構造・既知範囲のふるまい収集を担当し、未確定問題をcharter内で仮説検証する場合だけ`exploratory-testing(mode=investigation)`を使う。
18. Cross-artifact relation indexは必須基盤にしない。direct ref → 発見済みartifactのdeterministic scanまで試し、それでも実需を満たさないreverse / multi-hop / cross-run queryだけをindex化する。
19. query結果の完全性を保証できない場合は`complete=false`相当を明示し、空集合を「影響なし」「Regression不要」と解釈しない。

## 対象外

- QA全体を新しいGraphへ移すこと
- Graph DB / query server / web UI
- 組織横断の恒久ナレッジ基盤
- 汎用artifact registry
- 新しい共通Feature ID体系 / feature hierarchy
- Regression専用Skill / Suite maintenance専用Skill
- PR #11 / #12 runtimeの再設計
- PR #13独自のfreshness / currentness state
- TCなしE2Eの自動TC化
- 全既存E2Eを暗黙にRegressionへ加入させること
- Regression scopeの完全自動決定
- Exploration結果の仕様Authorityへの自動昇格
- Findingの自動Defect化
