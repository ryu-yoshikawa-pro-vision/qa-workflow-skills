# qa-training-store固定対象の実Agent統合評価Plan

このPlanは、親Plan [`2026-10-03_132700_agent-eval-runner.md`](./2026-10-03_132700_agent-eval-runner.md) のフェーズ2として、実際のテスト対象リポジトリ `qa-training-store` を使って `qa-workflow-skills` を評価する手順と最小実装を定義します。

フェーズ1の共通ランナーが完成し、既存Eval Inputを使った実Agent生成と既存grader接続が成立してから着手します。

## 対象

- 評価側: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- テスト対象: `ryu-yoshikawa-pro-vision/qa-training-store`
- 初回固定revision: `84ce165493649550832731a60cf436f8ae29c56b`
- 対象Platform: Web
- 初回対象Feature: Checkout / Payment
- 規範仕様: `docs/spec/features/checkout-and-payment.md`

初回評価ではfloatingな`main`を使いません。上記revisionを固定し、別revisionを評価する場合は実行前に対象revisionを明示して別runとして扱います。

## この対象を使う理由

`qa-training-store`は評価対象として次を既に持っています。

- `docs/spec/`の規範仕様
- BR / ACとExecutable Canonical Sources
- 固定Seed
- Database Reset
- Test Clock
- Local Mock Payment
- Playwright
- `QA_AGENT.md`とAgentic QA用Harness

新しいサンプルアプリは作成しません。

`qa-training-store`側の既存Harnessは置き換えません。対象repoの仕様・実装・既存検証を、`qa-workflow-skills`の評価対象と根拠として利用します。

## 初回評価範囲

初回はCheckout / Paymentに限定します。

規範仕様上、最低限次を対象にします。

- `BR-CHECKOUT-001`: Checkout Sessionの再開・置換
- `BR-CHECKOUT-002`: Cart Version / 価格のOrder作成直前再検証
- `BR-CHECKOUT-003`: Mock Payment、Order、Inventoryの一貫した確定
- `AC-CHECKOUT-001`
- `AC-CHECKOUT-002`
- `AC-CHECKOUT-003`

代表Scenario:

- `checkout-resume`
- `cart-version-invalidates-checkout`
- `payment-processing`
- `payment-declined`
- 成功系の通常Checkout

初回はNativeを対象外とします。WebとNativeを同時評価すると、Skill品質とPlatform差を切り分けにくくなるためです。

## 評価要求

実Agentには、固定revisionの`qa-training-store`を対象に次を要求します。

```text
Checkout / PaymentのWeb範囲について、
現在有効な仕様根拠を確認し、
必要なQA工程をqa-workflowで判断して、
テスト分析からテスト設計、カバレッジ確認、反証レビューまで実施する。

Product Code、既存Test、規範仕様は変更しない。
現在のrepoと仕様から導出できない期待動作を追加しない。
```

対象Skillを固定順に全実行するよう指示しません。`qa-workflow`のrouting判断を評価対象に含めます。

初回評価で期待する主経路は次です。

```text
qa-workflow
  ↓
spec-analysis
  ↓ 必要時
question-analysis
  ↓
test-analysis
  ↓
test-requirement-design
  ↓
test-condition-design
  ↓
test-case-design
  ↓
coverage-analysis
  ↓
adversarial-review
  ↓
qa-workflow completion
```

`question-analysis`は不明点がない場合に無理に成果物を作らせません。

## 初回評価では実ブラウザ実行を必須にしない

初回の目的は、実repoを入力にした分析・設計workflowの品質とポータビリティを確認することです。

次は初回完了条件に含めません。

- `test-target-inspection`
- `test-execution`
- `e2e-test-implementation`
- `e2e-test-execution`
- 実ブラウザでの探索

これらまで同時に含めると、Agent runtime、Browser、対象アプリ起動、Seed Reset等の失敗とSkill分析・設計品質を切り分けにくくなります。

フェーズ2初回が成立した後、実行系Skillを同じ固定revisionへ追加する場合は別の評価Scenarioとして追加します。

## テスト対象の準備

実行時は元の`qa-training-store` checkoutを直接変更しません。

固定revisionから使い捨ての評価用copyを作成します。

評価用copyでは次を記録します。

- source repository
- source revision
- preparation日時
- `qa-workflow-skills`側のrevision
- Agent commandのversionを取得できる場合はそのversion

`qa-training-store`には既存の`.agents/skills/`があります。これらが`qa-workflow-skills`のroutingへ影響すると評価条件が変わるため、初回評価ではAgent-visibleなSkill集合を明示的に固定します。

使い捨てcopy上では、元repoの`.agents/skills/`を評価対象から除外し、今回評価する`qa-workflow-skills`の19 SkillだけをAgent-visibleなSkill packageとして配置します。

ただし、次は残します。

- `AGENTS.md`
- `QA_AGENT.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/spec/**`
- Product Code
- Test Code
- Seed / Test Control
- その他のrepo固有資料

これらはテスト対象repoの文脈・仕様・実装であり、評価用正解情報ではありません。

`qa-workflow-skills`側の`evals/`、reference answer、expected output、graderはテスト対象Agentから見えない状態を維持します。

## source変更の扱い

分析・設計評価ではProduct Code、既存Test、規範仕様を変更しません。

Agent実行前後で対象repoのsource差分を確認し、許可した評価成果物以外の変更がある場合は実行結果を有効なSkill評価へ昇格しません。

評価成果物は対象repoの正規成果物としてcommitせず、親Planの`.agent-eval-runs/`配下へ回収します。

## 評価観点

### 1. workflow

- 要求に対して開始Skillが妥当か
- 不要なSkillを固定順で実行していないか
- 必要な工程を省略していないか
- ブロック中 / 要確認が根拠なく作られていないか
- 最終状態が生成成果物と矛盾していないか

### 2. 仕様根拠

最低限、Checkout / Paymentの規範仕様を正しく扱います。

- `BR-CHECKOUT-001..003`
- `AC-CHECKOUT-001..003`
- 必要なRole / Scenario
- Executable Canonical Sources

READMEや既存Testだけを期待動作の最上位根拠へ昇格させないことを確認します。

### 3. テスト分析・設計

最低限、次の意味的境界を落とさないことを確認します。

- Checkout Sessionのresume / replace / expire
- stale Cart Version
- price mismatch
- Payment成功
- Payment明確失敗
- processing中のresume
- processing中のretry / cancel禁止
- 最終在庫不足
- Payment / Order / Inventory / Historyの整合

この一覧をそのまま成果物へコピーすることは要求しません。生成物が規範仕様を意味的にカバーしているかを評価します。

### 4. traceability

生成された成果物について、既存の`qa-workflow-skills`契約に従い、少なくとも次を確認します。

- Authority → Test Requirement
- Test Requirement → Test Condition
- Test Condition → Coverage Item
- Coverage Item → Test Case
- Coverage Analysisによる未閉鎖の検出
- stable ID / reference整合
- runtime対応成果物のcurrentness / fingerprint

### 5. 根拠のない追加

次を仕様として捏造しないことを確認します。

- 外部Payment API
- Server-side認可
- 実決済providerの挙動
- Backend通信障害
- Checkout仕様に存在しないToast等

対象repoの制約と規範仕様にないものは、必要なら追加調査候補として扱い、現在仕様として確定しません。

## 評価方法

フェーズ2では、既存のSkill-local eval datasetを`qa-training-store`向けに置き換えません。

評価を次の2層へ分けます。

### 機械判定できる部分

既存runtime / deterministic contractを再利用します。

- ID / reference
- required artifact
- runtime evidence
- freshness
- closure
- workflow state

新しい同等validatorを作りません。

### 意味判断が必要な部分

独立Judgeを使い、固定revisionの規範仕様と上記評価観点を根拠に評価します。

Judgeは評価対象Agentとは別process / 別promptで実行します。

初回では独自の総合点を作らず、各評価観点を次で保持します。

- pass
- needs_review
- fail
- not_evaluable

既存semantic evalのrating / verdict契約を再利用できる場合は、その共通処理を使用します。target-specificな意味評価のためだけに同じresult parserやrating計算を複製しません。

## フェーズ1ランナーへの追加要件

フェーズ2を可能にするため、フェーズ1の実装を既存Eval Input専用に閉じません。

最低限、Agent subprocess実行部分は次を分離します。

```text
入力準備
  ↓
Agent execution
  ↓
成果物保存
  ↓
評価
```

Agent executionは、Eval dataset由来のpromptでも、固定対象repo向けpromptでも再利用できる関数にします。

ただし今回、任意repo・任意benchmarkを扱うplugin frameworkは作りません。

フェーズ2で必要になった時点で、`qa-training-store`固定Scenarioを呼び出す最小の入口だけを追加します。

## qa-training-store既存Harnessとの境界

`qa-training-store`には既に次があります。

- `eval:skills:trigger`
- `eval:skills:semantic`
- `eval:skills:workflow`
- `scripts/agentic-qa/**`

これらは`qa-training-store`側のSkillやAgentic QA契約を評価する仕組みです。

今回の正本は`qa-workflow-skills`側の評価です。既存Harnessの実装をコピーして二重管理しません。

ただし、次の既存設計は対象準備・安全条件の根拠として利用します。

- 固定revision
- evaluatorとtargetの分離
- targetから評価データを隔離
- source変更の検出
- provenance記録
- Agent実行と評価の分離

## 実装・実行順序

1. 親Planのフェーズ1を完了する
2. `qa-training-store`の固定revision `84ce165493649550832731a60cf436f8ae29c56b` を使い捨てcopyへ準備する
3. 対象revisionの`docs/spec/README.md`と`docs/spec/features/checkout-and-payment.md`が存在することを確認する
4. 元repoのAgent Skill集合を評価条件から除外し、候補`qa-workflow-skills` 19 SkillだけをAgent-visibleにする
5. Checkout / Payment評価要求を固定する
6. 実Agentを起動し、分析・設計workflowを実行する
7. Product Code / Test / Specに許可外変更がないことを確認する
8. 生成成果物を`.agent-eval-runs/`へ回収する
9. 機械判定可能な契約を既存runtime / deterministic validationで確認する
10. 独立Judgeで意味品質を評価する
11. workflow / traceability / semantic結果を同じrunへ保存する
12. runner起因の失敗とSkill品質上の非passを分離して報告する

## 完了条件

次をすべて満たしたらフェーズ2初回評価を完了とします。

- テスト対象が`qa-training-store`であることをrun結果から特定できる
- source revisionが`84ce165493649550832731a60cf436f8ae29c56b`として固定・記録される
- 評価対象`qa-workflow-skills` revisionが記録される
- Agent-visibleなSkill集合が今回の19 Skillへ固定される
- `qa-workflow-skills`のeval answer / expected / graderをAgentへ公開していない
- Checkout / PaymentのWeb範囲で実Agent workflowが最後まで実行される
- Product Code、既存Test、規範仕様に許可外変更がない
- 生成成果物がrun artifactとして保存される
- workflow結果が保存される
- traceability / runtimeの機械判定結果が保存される
- 独立Judgeの意味評価結果が保存される
- runner / environment errorとSkill品質のneeds_review / failを区別できる
- 非pass結果を隠さず保存・報告できる
- target-specific評価のためにSkill本体へ`qa-training-store`固有処理を追加していない

## このフェーズで追加しないもの

- Native評価
- 実ブラウザ実行を伴うE2E評価
- Black-box Scored Challengeとの統合
- `qa-training-store`既存Harnessの再実装
- 複数target repo対応のplugin framework
- Skill自動修正
- Skill自動採用
- baseline / candidateの自動ランキング
- 外部LLMを使う通常CI

実行系Skillの評価、A/B比較、複数target repo対応は、この固定対象で実際に不足が確認された後に追加します。
