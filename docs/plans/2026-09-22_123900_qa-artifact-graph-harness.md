# Regression Suite / QA Activity 統合Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みの設計traceability・change impact・execution lineageを再実装せず、次の課題だけを解決する実装計画です。

- 各新規・改修セッションで作成したテスト設計を、継続Regressionへ再利用できる状態に保つ
- Regressionの基準集合と、各回のfull / selected Runを分離する
- Regression / Exploration / Investigationの活動履歴を後から追跡できるようにする
- 既存成果物の直接参照だけでは回答できない横断queryが確認された場合だけ、最小relation indexを追加する

Graphの構築自体は目的にしません。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ名は旧設計の名称を維持します。実装はPR #11 / #12 merge後の最新`main`へ追従し、両PRの実契約を再確認してから開始します。

## 前提

- PR #11のMachine Entity、stable ID、traceability、change impact、freshness / stale / `要再検証`を設計側の正本として扱う
- PR #12の`test-target-inspection`、`test-execution`、TC snapshot、execution / result / rerun契約を実行側の正本として扱う
- E2E SkillのTest Case / testware / execution契約を維持し、TCなしE2Eへ架空TCを追加しない
- PR #11 / #12の実装後に、project全体のcurrent TC集合を直接列挙できるか確認する
- 実装開始時点のSkill数・評価件数・CI構成は最新`main`から再取得する

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Cross-artifact relation index導入判定](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [決定論的補助runtime・履歴発見](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [新規・改修 / Exploration / Investigation統合](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・Run・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [既存Skill・PR #11/#12統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
7. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. PR #11をdesign identity / traceability / change impact / freshnessの正本とし、PR #13で第二のdesign graphやcurrentness state machineを作らない。
2. PR #12 / E2Eをexecution / result / evidence / rerun lineageの正本とし、PR #13でexecution schemaを複製しない。
3. Regression Suiteは「全current TCの保管庫」ではなく、**現在のRegression対象範囲を継続的に検証するための、currentかつ再利用可能なTCの基準集合**とする。
4. 各新規・改修セッションではRegression Suiteを必ず見直すが、current TCを機械的に全件加入させない。継続Regression対象か、一時的な検証かは意味判断して記録する。
5. 「全機能coverage」の母集団はSuite自身から作らない。案件コンテキスト、現在有効な仕様根拠、test level等から独立したRegression対象範囲を定め、`coverage-analysis`で既存traceabilityを使って確認する。
6. feature tagは任意の検索・抽出用metadataとし、Suite membershipやcoverageの成立条件にしない。
7. Regression Suiteの完全性とRegression Runのscopeを分離する。Runは`full`または`selected`であり、selected Runをfull完了として扱わない。
8. scope指定時はユーザー指定を優先し、次に案件コンテキストのRegression方針を使う。どちらもなければ安全側のfallbackとしてfullを使用する。
9. full scope、selected件数、executed件数、未実行 / blocked件数を分離し、未実行理由があるだけで「全件実行済み」と表現しない。
10. Suite memberは論理的なTest Caseとする。E2E testwareは実装先であり、manual / E2Eを別memberとして二重登録しない。
11. E2Eが存在するだけでmanual不要と判断しない。`coverage-analysis`（対象: `TC → E2E実装`）で検証責務が十分か確認してから、各Runのexecution routeを決める。
12. Regression / Exploration / Investigationは後から参照できる活動成果物を持つ。固定保存場所から決定論的に発見できる場合はactivity indexを追加せず、必要な場合だけ最小indexを持つ。
13. Cross-artifact relation indexは必須基盤にしない。direct refと既存runtimeで回答できないreverse / multi-hop / cross-run queryが実証された場合だけ、そのqueryに必要なrelationを追加する。
14. query結果の完全性を保証できない場合は`complete=false`相当を明示し、空集合を「影響なし」「Regression不要」と解釈しない。
15. 現在不足している探索・仮説駆動調査だけ、新規`exploratory-testing` Skillを1つ追加する。

## 対象外

- QA全体を新しいGraphへ移すこと
- Graph DB / query server / web UI
- 組織横断の恒久ナレッジ基盤
- 汎用artifact registry
- 新しい共通Feature ID体系
- feature tag hierarchy
- Regression専用Skill
- Regression Suite専用メンテナンスSkill
- PR #11 / #12 runtimeの再設計
- Regression scopeの完全自動決定
- Exploration結果の仕様Authorityへの自動昇格
- Findingの自動Defect化
