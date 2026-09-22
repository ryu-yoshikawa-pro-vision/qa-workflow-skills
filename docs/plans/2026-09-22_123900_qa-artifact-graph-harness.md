# QA Artifact Graph / Harness 導入Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、既存QA成果物を壊さずに **新規・改修、リグレッション、探索、調査を1つのQA Artifact Graphで追跡・変更影響分析できるHarness** を追加する実装計画です。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ自体は2026-09-22時点の`main`から作成しています。実装はPR #11 / #12 merge後の最新`main`へ追従して開始し、両PRの実契約を再確認してから着手します。

## 前提

- PR #11のMachine Entity、runtime、stable ID、change impact graph、traceability契約を既存基盤として扱う
- PR #12の`test-target-inspection`、`test-execution`、TC snapshot、`test_case_ref / source_test_case_id`、再実行・副作用・cleanup・Playwright実行境界を既存基盤として扱う
- PR #11 / #12のidentity / fingerprint / runtime契約を本Plan都合で置換・汎用化しない
- 実装開始時点の正規Skill数はPR #12 merge後の16 Skillを基準とし、本Planで`exploratory-testing`を追加して17 Skillとする。trigger / semantic / deterministicの件数は実装開始時の正本から再計算する

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Graphモデル・identity・currentness契約](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [Deterministic Graph Harness設計](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [新規・改修 / Regression / Exploration / Investigation統合](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [既存Skill・PR #11/#12・探索Skill統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
6. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. **既存QA成果物を正本のまま維持し、Graphを新しい正本にしません。** Graphは既存成果物・Machine Entity・実行結果から再生成可能な派生インデックスです。
2. Neo4j、RDF、Graph DB、外部DB、常駐server、artifact registryを追加しません。v1はfile-based JSONと決定論的Python Harnessで成立させます。
3. 新しい汎用QA ID体系を作りません。既存`SPEC / DEC / ASM / TR / TCN / CI / TC`、PR #11のMachine Entity identity、PR #12のartifact-local ref、E2E既存identityをそのまま利用します。
4. Graph内部だけで必要な参照は`artifact_ref + local_ref`を決定論的にエンコードした内部`node_key`を使用し、正式QA IDとして成果物へ書き戻しません。入力identityがないことを理由にcontent hashを新設しません。
5. PR #11の`test-analysis` change impact graphは置換しません。局所的な意味graphとして保持し、QA Artifact Graphへprojection可能な入力として扱います。
6. Graph traversalは**影響候補、未接続、参照欠落、履歴関係等の機械的候補生成**だけを担当します。意味変更の有無、テスト範囲の最終選択、PASS / FAIL、仕様解釈をGraph Harnessが決めません。
7. 新規・改修、Regression、Exploration、Investigationで別Graphを作りません。`qa_activity`の`activity_type`で活動種別を表し、同じTest Case / Risk / Finding等を再利用します。
8. Regression専用Skillは追加しません。変更影響候補はHarness、意味的な範囲選定は既存`test-analysis`、妥当性確認は`coverage-analysis`、実行は`test-execution / e2e-test-execution`を使用します。
9. 現在不足している探索・仮説駆動調査だけ、新規`exploratory-testing` Skillを1つ追加します。browser backendを新設せず、PR #12で確立したPlaywright系実行方針と案件コンテキストの副作用制約を再利用します。
10. 過去のResult / Findingを削除・上書きしません。Graph上ではhistoricalとして保持し、current evidenceかどうかを別状態で表現します。
11. 上流変更だけで下流を機械的に「誤り」「削除」「FAIL」へしません。`revalidation_required`候補として伝播し、責任Skillが再検証します。
12. Graph Harnessの構造・参照・型・到達可能性検証は決定論的に行います。LLMにGraph JSONの整合性確認、cycle検出、dangling参照検出を任せません。

## 対象外

- Graph DB / query server / web UI
- 組織横断の恒久ナレッジ基盤
- Jira等の外部テスト管理システム同期
- すべてのMarkdownを自由文semantic parserでGraph化すること
- PR #11 runtimeの再設計
- PR #12 execution runtimeの再設計
- Regressionを自動で最終選定して無人release判定する仕組み
- Explorationで発見した内容を自動的に仕様Authorityへ昇格する仕組み
- 全Findingを自動でDefect化する仕組み
