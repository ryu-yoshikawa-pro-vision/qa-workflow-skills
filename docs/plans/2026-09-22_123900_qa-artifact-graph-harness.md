# QA Artifact Graph / Harness 導入Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みの設計traceability・change impact・execution lineageを再実装せず、**全機能を覆うRegression Suite、QA activity履歴、Exploration / Investigation、既存成果物を跨ぐ不足relationだけを決定論的に管理する仕組み**を追加する実装計画です。QA Artifact Graphは新しい正本や独立状態機構ではなく、既存成果物と活動履歴から再生成する薄いrelation indexとして扱います。

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
2. [Relation / Graphモデル・identity契約](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [Deterministic Harness設計](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [新規・改修 / Exploration / Investigation統合](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・機能タグ・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [既存Skill・PR #11/#12・探索Skill統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
7. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. **PR #11を設計成果物のidentity / traceability / change impact / freshnessの正本とします。** PR #13で第二のdesign impact engineやcurrentness state machineを作りません。
2. **PR #12と既存E2E Skillをexecution / result / evidence / rerun lineageの正本とします。** PR #13は実行事実を再定義しません。
3. **Regression Suiteは現在有効な全機能テストを束ねる基準集合です。** 新規・改修セッションで確定したTCは、明示的な除外理由がない限りRegression Suiteへ統合します。
4. Regression Suiteの各TCには1件以上の**機能タグ**を付けます。機能タグは整理・抽出用であり、タグが付いているだけでは機能を網羅したと判定しません。全機能網羅は`coverage-analysis`が既存の仕様根拠 → TR → TCN / CI → TCの意味上の閉鎖性で確認します。
5. ユーザーが単に「リグレッションテストを実施」と要求し、対象を絞る指示がない場合は**全件実行**として扱います。部分実行は、機能タグ、明示TC、PR #11の影響候補、Risk / history等で範囲を選ぶ場合だけ使用し、全機能Regression完了とは扱いません。
6. Regression Suiteのメンバーは論理的なTest Caseです。E2E testwareはTCの実装先として扱い、同じTCを手動用とE2E用の2メンバーへ重複登録しません。
7. Regression / Exploration / Investigationは後から参照できる活動成果物を持ち、project-localなactivity indexから発見可能にします。optionalな現在状態表だけを過去履歴の正本にしません。
8. QA Artifact Graphは既存成果物・Regression Suite・activity成果物から再生成できる**薄いrelation index**です。Graph独自の`graph_state`は持たず、source側のfreshness / lifecycle / execution stateを参照します。
9. Relation queryがunsupported / unmapped / dangling等で不完全な場合、空の候補集合を「影響なし」と扱いません。特に部分Regressionの候補抽出では`complete=false`相当を明示し、安全側のscope判断へ渡します。
10. Graph / Harnessの構造・参照・型・到達可能性検証は決定論的に行い、LLMにduplicate / dangling / cycle等を判定させません。
11. 現在不足している探索・仮説駆動調査だけ、新規`exploratory-testing` Skillを1つ追加します。既存分析Skillの責務をgeneric investigationへ移しません。
12. Neo4j等のGraph DB、外部DB、常駐server、汎用artifact registry、汎用QA ID体系は追加しません。

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
