# QA Artifact Graph / Harness 導入Plan

## 1. 目的

現在のQA workflowは、仕様分析、質問整理、リスク分析、テスト要求、テスト条件、テストケース、カバレッジ、E2E実装・実行・分析・報告までを独立Skillへ分離できています。PR #11 merge後は主要設計成果物にMachine Entity / deterministic runtimeが加わり、PR #12 merge後は実対象のcurrent情報収集と、AIによる詳細TCの手動相当実行が加わります。

不足しているのは、これらを案件・リリース・探索セッションを跨いで次の問いへ機械的に答える共通層です。

- このTCはどの仕様・Risk・Conditionから来たか
- この変更でどのTR / TCN / CI / TC / E2E / 過去Resultが再確認候補になるか
- 今回のRegressionでなぜこのTC / E2Eを選んだか
- 過去に同じ領域で何がFAIL / Findingになったか
- 探索で得たFindingがどのQuestion / Risk / Condition / TCへ反映されたか
- このPASS証拠はどの対象version / TC snapshot / executionに基づくか
- 上流変更後も過去結果をcurrent evidenceとして扱ってよいか

本Planでは、これらを**QA Artifact Graphの派生projectionと決定論的Harness**で管理します。

## 2. 実装開始時の基準

実装開始前に以下を必ず確認します。

1. PR #11がmerge済みである
2. PR #12がmerge済みである
3. 最新`main`のSkill一覧、Machine Entity schema、runtime contract、workflow state、評価件数を取得する
4. PR #11 / #12 merge時の追加修正がPlan記載より優先される場合は実契約を正本とする
5. 本PlanのGraph adapter / schemaを最新成果物契約へ合わせる

PR #11 / #12のPlan文書記載を実装時のruntime正本にはしません。merge済みコード・Skill・validator・assetを正本とします。

## 3. 現状のQA活動別能力

### 3.1 新規・改修

既存SkillとPR #11により、次が成立している前提です。

```text
仕様根拠
  ↓
Question / Decision / Assumption
  ↓
Product Risk / Change Impact
  ↓
Test Requirement
  ↓
Test Condition / Coverage model / Coverage Item
  ↓
Test Case
  ↓
Coverage / Adversarial Review
  ↓
必要時 E2E implementation / execution
```

この経路はGraph化の入力が最も揃っています。

### 3.2 Regression

既存`e2e-test-execution`はPlaywright E2E runを構造化できます。PR #12の`test-execution`で詳細TCの手動相当実行も可能になる前提です。

ただし「変更 / release → 影響候補 → Regression対象選定 → manual/E2E再利用 → execution history」の共通activity viewはありません。

本Planでは新しいRegression Skillを追加せず、Graph候補 + `test-analysis` + `coverage-analysis` + 既存execution Skillで成立させます。

### 3.3 Exploration / Investigation

既存Skillには探索的思考はありますが、Charter / Session / Observation / Finding / Evidence / Follow-upを第一級成果物として扱う責任Skillがありません。

本Planでは`exploratory-testing`を1 Skillだけ追加し、探索テストと仮説駆動の調査を同じSkillの明示modeで扱います。

- `mode=exploration`: charterに基づく探索
- `mode=investigation`: 問題 / Finding / Question / Hypothesisを起点にした調査

両modeとも実測を仕様Authorityへ昇格しません。

## 4. Graphの位置づけ

Graphは「各成果物を置き換える巨大共通schema」ではありません。

```text
Existing QA artifacts / Machine Entities / Run artifacts
                         │
                         ▼
                deterministic adapters
                         │
                         ▼
                  QA Artifact Graph
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          validation   impact     projections
                         │
                         ▼
                    qa-workflow
```

正本は引き続き担当Skillの成果物です。

Graphを削除しても、正本から再buildできることをv1の必須条件にします。

## 5. 責務境界

### Skill

意味判断を担当します。

- 仕様の意味
- Risk
- Test Requirement / Condition / Case
- Regression最終scope
- Exploration charter
- Findingの意味
- 変更が本当に下流へ影響するか
- 修正routing

### Graph Harness

意味判断をしません。

- node / edge schema validation
- identity解決
- duplicate / dangling参照
- edge source/target type検証
- explicit supersedes / deleted状態
- graph traversal
- reachability
- cycle禁止対象のcycle検出
- impact candidate列挙
- coverage / orphan候補列挙
- activity projection生成
- currentness候補伝播
- Graph JSON生成 / 再build一致

### qa-workflow

Graph Harnessの候補を入力として、既存契約どおり最も早い責任Skillへroutingします。

GraphがSkill固有ロジックを再定義しません。

## 6. 過剰設計を避ける制約

このPRでは次を追加しません。

- Graph DB
- event sourcing
- message bus
- background daemon
- generic plugin architecture
- dynamic graph schema registry
- universal artifact fingerprint
- universal QA entity ID
- graph migration framework
- graph visualization UI
- graph専用LLM agent

v1は既知Skill / 既知成果物だけを固定adapterで扱います。
