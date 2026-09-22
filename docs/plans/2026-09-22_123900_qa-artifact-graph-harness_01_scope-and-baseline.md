# QA Artifact Graph / Harness 導入Plan

## 1. 目的

PR #11 / #12後に残る課題だけを本Planの対象とします。

- 新規・改修ごとに設計したTest Caseを、次回以降も再利用できる全機能Regression Suiteへ統合する
- Regression Suiteを機能タグで整理し、全件実行と部分実行の意味を明確に分ける
- 今回のRegressionで選択 / 除外したTCと理由、実行結果を活動単位で後から辿れるようにする
- 過去Result / Findingをrelease / sessionを跨いで発見できるようにする
- Exploration / InvestigationのCharter / Session / Finding / Follow-upを第一級成果物として管理する
- PR #11の設計traceabilityとPR #12 / E2Eのexecution lineageを跨ぐ、不足relationだけを決定論的に検索できるようにする

次はPR #13固有の課題として再実装しません。

- SPEC → TR → TCN → CI → TCのdesign traceability
- 設計成果物のchange impact / freshness / stale伝播
- TC snapshot、execution、result、rerunの正本

これらはPR #11 / #12のmerge後実装を正本として利用します。QA Artifact Graphはその上に新しいQA状態を作るものではなく、必要なcross-artifact queryを支える派生relation indexです。

## 2. 実装開始時の基準

実装開始前に以下を必ず確認します。

1. PR #11 / #12がmerge済みである
2. 最新`main`のMachine Entity、traceability、change impact、freshness、execution、rerunの実契約を取得する
3. 実成果物で次のqueryを試し、PR #11 / #12だけで回答できるものをPR #13から除外する
   - current TC → 仕様根拠 / Risk / TCN / CI
   - changed specification / Risk → affected current TC
   - execution → TC snapshot / target version / previous execution
4. 次の残課題だけが未解決であることを確認する
   - Regression Suiteと機能タグ
   - Regression activityの選択 / 除外理由
   - cross-run Result / Finding discovery
   - Exploration / Investigation
   - PR #11とexecution/historyを跨ぐ不足relation
5. 4の残課題を、Regression Suite成果物 + activity成果物 + 最小relation indexで解けるかを先に検証する

5までで目的を満たせる場合、現在Planに記載されたより広いGraph node / edgeを実装しません。Graph拡張は未解決queryが具体的に確認できた場合だけ行います。

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

Regressionは、各セッションで設計した機能別TCを継続的に統合した**全機能Regression Suite**を基準にします。

- Suite自体は現在有効な全機能を網羅する
- 各TCは1件以上の機能タグを持つ
- 新規・改修セッションで確定したTCはSuiteへ追加 / 更新する
- 削除・置換されたTCはcurrent Suiteから外し、過去runのsnapshotは変更しない
- E2E化されたTCも論理TCとして1件だけSuiteへ保持する

実行は2種類に分けます。

- **全件実行**: current Suiteの全memberを対象にする。ユーザーが単にRegression実施を要求し、絞り込みを指定しない場合はこれを既定とする
- **部分実行**: 機能タグ、明示TC、変更影響、Risk / history等でmemberを抽出する。選択理由と除外理由をactivity成果物へ保存し、全機能Regression完了とは扱わない

機能タグは抽出単位です。全機能網羅の判定は件数ではなく、`coverage-analysis`が各機能の現在有効な仕様根拠 / Risk / TR / TCN / CIがSuite member TCへ意味上閉じていることを確認します。

Regression専用Skillは追加しません。Suite管理と実行routingは`qa-workflow`、意味上の部分選定は`test-analysis`、全機能 / 選択範囲のカバレッジ確認は`coverage-analysis`、実行は`test-execution / e2e-test-execution`を利用します。詳細契約は`_04a_regression-suite.md`を正本とします。

### 3.3 Exploration / Investigation

既存Skillには探索的思考はありますが、Charter / Session / Observation / Finding / Evidence / Follow-upを第一級成果物として扱う責任Skillがありません。

本Planでは`exploratory-testing`を1 Skillだけ追加し、探索テストと仮説駆動の調査を同じSkillの明示modeで扱います。

- `mode=exploration`: charterに基づく探索
- `mode=investigation`: 問題 / Finding / Question / Hypothesisを起点にした調査

両modeとも実測を仕様Authorityへ昇格しません。

## 4. Relation index / Graphの位置づけ

Graphは既存成果物を置き換える共通domain modelではありません。

```text
PR #11 Machine Entities / traceability
PR #12 execution artifacts / E2E artifacts
Regression Suite / QA activity / Exploration artifacts
                         │
                         ▼
                 deterministic adapters
                         │
                         ▼
                thin relation index
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          validation   query     activity view
```

設計側のimpact / freshnessはPR #11、execution stateはPR #12 / E2Eを正本とします。Relation indexはそれらを再判定せず、明示relationの逆探索・複数hop query・履歴参照を支えます。

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

### Harness

- relation schema validation
- identity / artifact-local scope解決
- duplicate / dangling参照
- relation source/target type検証
- 明示relationのquery / reachability
- Regression Suite構造検査
- activity index / history参照
- query完全性の判定
- canonical JSON生成 / 再build一致

設計成果物のsemantic impact、freshness、Regression最終scope、PASS / FAILは判断しません。

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
