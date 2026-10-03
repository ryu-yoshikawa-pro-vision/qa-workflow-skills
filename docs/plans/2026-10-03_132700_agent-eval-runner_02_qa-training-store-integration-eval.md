# qa-training-store固定対象の実Agent統合評価Plan

このPlanは、親Plan [`2026-10-03_132700_agent-eval-runner.md`](./2026-10-03_132700_agent-eval-runner.md) のフェーズ2として、実際のテスト対象リポジトリ `qa-training-store` を使って `qa-workflow-skills` を評価する手順と最小実装を定義します。

フェーズ1の共通ランナーが完成し、既存Eval Inputを使った実Agent生成と既存grader接続が成立してから着手します。

このフェーズの目的は「実repoで一度動かすこと」ではありません。固定したtarget revision、評価要求、Agent / model、Judge条件を使って複数Skillのworkflowを実行し、結果を保存することで、後からSkillを修正しても同じ条件で再評価できる状態を作ることです。

初回評価結果はSkill改善のbaselineとして利用できます。ただし、このフェーズで自動rankingや自動Skill修正は行いません。

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

live runの`--target-root`は、少なくとも次を満たすことをpreflightします。

- Git working treeである
- HEADがscenarioの固定source revisionと一致する
- working tree / indexがcleanである
- Evaluator repo自身ではない
- output先がtarget root内ではない

sanitized targetはworking treeのfilesystem copyではなく、固定source revisionの**tracked contentだけ**から作ります。これにより、target側のuntracked file、local secret、過去の一時成果物を入力へ混ぜません。

評価用copyでは次を記録します。

- source repository
- source revision
- preparation日時
- `qa-workflow-skills`側のrevision
- Agent commandのversionを取得できる場合はそのversion

`qa-training-store`には既存の`.agents/skills/`があります。さらに現在の`AGENTS.md`は`feature-plan`、`code-review`、`repair-loop`、`harness-improvement`、`exploratory-qa`等のrepo固有Skillへroutingする契約を持ち、`QA_AGENT.md`も`exploratory-qa`とAgentic QA Harnessを前提にします。

これらをそのまま残して`.agents/skills/`だけ除外すると、「利用を要求するSkillが存在しない」矛盾したtargetになります。また、元repo固有Skillが見える状態では今回評価したい19 Skill以外がroutingへ影響します。

そのため、初回評価では固定revisionのtracked contentからsanitized targetを作り、Agent-visibleな情報を次のように分けます。

### 除外するもの

- 元repoの`.agents/**`
- target repo固有のCodex config / hooks / agents / run artifactを含む`.codex/**`
- 元`AGENTS.md`
- `QA_AGENT.md`
- 過去Planである`docs/plans/**`
- 過去検証結果である`docs/reports/**`
- `training/agentic-qa/instructor/**`
- target repo自身のSkill評価実装である`scripts/evals/**`
- target repo自身のSkill / Agent評価専用test:
  - `tests/repository-contract/skill-semantic-output-evals.test.ts`
  - `tests/repository-contract/skill-trigger-evals.test.ts`
  - `tests/repository-contract/skill-workflow-evals.test.ts`
  - `tests/repository-contract/otel-skill-observer.test.ts`
  - `tests/repository-contract/validate-skills.test.ts`
- `qa-workflow-skills`側の`evals/**`、Reference、expected、rubric、grader

target repo固有の`.agents/**` / `.codex/**`は、今回評価するSkill集合やAgent runtime条件を上書き・追加し得るため除外します。

過去Plan / report / run、instructor情報、target repo自身のSkill evalは、実際のProduct / Specを理解するために必要な正本ではなく、評価対象Agentへ既存の結論や評価基準を漏らす可能性があるため除外します。

### 残すもの

- `docs/spec/**`
- `docs/PROJECT_CONTEXT.md`
- README等の一般的なrepo資料
- Product Code
- 既存Product Test
- Seed / Test Control
- Build / Test設定
- Checkout / Paymentの理解に必要なその他のtracked Product資料

READMEや既存Testは補助情報として参照できますが、期待動作の優先順位は`docs/spec/README.md`のOracle契約に従います。

### 評価用AGENTS.md

sanitized targetのrootにはEvaluatorが最小の評価用`AGENTS.md`を生成します。元`AGENTS.md`のrepo固有Skill routingはコピーしません。

評価用`AGENTS.md`には、今回の評価に必要な次だけを記載します。

- 対象はCheckout / PaymentのWeb範囲
- Agent-visibleなSkillはEvaluatorが配置した`qa-workflow-skills`の19 Skillだけ
- 規範仕様の優先順位は`docs/spec/README.md`に従う
- Product Code、既存Product Test、規範仕様を変更しない
- 評価成果物の書込みはEvaluatorが指定した評価出力rootだけに限定する
- commit / push / PR作成等のGit mutationを行わない
- Evaluator側のReference / expected / rubric / graderを探索しない

この`AGENTS.md`は評価条件を固定するためのHarness入力であり、製品仕様、期待するテストケース、正解となるQA判断は追加しません。

その上で、今回評価する`qa-workflow-skills`の19 Skillだけをsanitized targetの`.agents/skills/<skill-name>/`へ配置します。配置元は評価対象`qa-workflow-skills` revisionの`skills/<skill-name>/`であり、各Skillの`evals/**`はコピーしません。

フェーズ2のtaskは`qa-workflow`利用を明示するため、このrun自体をnative trigger精度の評価には使いません。`.agents/skills/`へ配置するのは、実際のCodex等で利用するときに近いSkill package形態で複数Skill workflowを実行するためです。

## source変更の扱い

分析・設計評価ではProduct Code、既存Product Test、規範仕様を変更しません。

sanitized targetの構築、評価用`AGENTS.md`、19 Skill、評価用Project Contextの配置が完了した時点を**Agent開始前baseline**とします。

baseline固定のため、sanitized targetでfresh Git repositoryを初期化し、remoteなし・固定の非個人local identityでEvaluator-owned synthetic commitを1件作成します。original Git history / remoteは引き継ぎません。

その後、Evaluator所有の評価出力root `.qa-eval-output/` を作成し、Agentへ書込み可能な永続成果物の保存先として明示します。

Agent終了後はbaseline commitとの差分を確認し、`.qa-eval-output/**`以外に変更がある場合は実行結果を有効なSkill評価へ昇格しません。AgentがGit commitを作成した場合も契約違反として扱います。

`.qa-eval-output/**`はtargetのProduct成果物ではなく、今回の評価用一時出力です。commitせず、回収後にsanitized targetと一緒に破棄します。

## 複数QA成果物の回収

フェーズ1の単一caseはAgent stdoutを`output.md`として評価できますが、フェーズ2ではspec analysis、test analysis、TR、TCN / CI、TC、coverage、adversarial review、workflow state等の複数成果物を扱います。

そのため、フェーズ2ではstdoutだけを正規成果物として扱いません。

処理を次に固定します。

```text
sanitized target
  ↓
.qa-eval-output/ をEvaluatorが作成
  ↓
実Agentが各QA成果物を個別fileとして保存
  ↓
Agent終了
  ↓
Evaluatorがoutput rootをscan
  ↓
path / symlink / sizeを検証
  ↓
各fileのSHA-256と相対pathをartifact-manifest.jsonへ記録
  ↓
.agent-eval-runs/<run>/target-artifacts/ へcopy
  ↓
source差分を確認
  ↓
sanitized targetを破棄
```

Agentの最終stdoutは実行概要として保存できますが、複数Skillの正規評価対象は回収したartifact file群とします。

Evaluatorは成果物内容を独自schemaへ変換しません。各Skillの既存Markdown / runtime evidence契約を維持したままcopyし、`artifact-manifest.json`には少なくとも次だけを保存します。

- relative path
- file size
- SHA-256
- 生成元Skillをfile配置から一意に決められる場合はそのSkill名
- runtime-enabled Skillで保存されたverifier request / resultへの相対path

symlink、output root外を指すpath、path traversal、許容上限を超えるfileは回収せずrunをexecution errorとします。

workflow state等で保存rootが必要な場合は、Evaluatorが評価用Project Contextへ`.qa-eval-output/`配下のproject-local rootを設定します。既存Skillの保存契約を変えず、評価用の保存先だけを与えます。

runtime-enabled Skillについては、Agentが最終成果物を完成扱いにする前に実行した既存`verify_runtime_evidence`等の**実際のrequest JSONとresult JSON**を、評価成果物と同じrun配下へ保存させます。Evaluator用にexpected値を作らせるのではなく、Skillが本来実行するproduction verifierの入出力を証拠として残すだけです。

Evaluatorは回収後、そのrequestの`artifact_markdown`だけを回収済みartifact本文へ差し替えたうえで同じproduction verifierを再実行し、保存済みresultとcurrent verifier結果が一致することを確認します。Agentが独自のexpected Entityやfingerprintを手組みした場合は、既存verifierがrejectする契約をそのまま使います。

`qa-workflow`については、Skill-local`verify_runtime_evidence`に加えて、実行時に使用した`workflow_runtime.py`入力 / 結果も保存・再実行対象にします。

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

## 評価scenarioと比較条件

初回scenario IDは`qa-training-store-checkout-payment-web-v1`とします。

Evaluator側にtrackedなscenario定義を置き、少なくとも次を固定します。

- target repository
- target revision
- Platform
- Feature / scope
- Agentへ渡す評価要求
- Agent-visible Skill集合
- sanitized targetから除外する評価汚染情報
- 評価出力root
- Judgeが参照する規範仕様path:
  - `docs/spec/README.md`
  - `docs/spec/product-scope.md`
  - `docs/spec/roles-and-permissions.md`
  - `docs/spec/state-and-scenarios.md`
  - `docs/spec/features/checkout-and-payment.md`
  - `docs/spec/known-deviations.md`
  - `docs/spec/unresolved-specifications.md`
- 意味評価criteria

scenario定義と評価要求からfingerprintを算出し、親Planのrun provenanceへ保存します。

Skill修正前後を比較するときは、target revision、scenario fingerprint、Agent名 / model、Judge条件を一致させます。これらが異なるrunは参考比較には使えても、Skill変更だけの効果として直接比較しません。

scenario定義は現在の`qa-training-store`初回評価を再現するための固定fixtureであり、任意repoを扱うplugin interfaceにはしません。

## 評価方法

フェーズ2では、既存のSkill-local eval datasetを`qa-training-store`向けに置き換えません。

評価を次の2層へ分けます。

### 機械判定できる部分

既存production runtime / verifier契約を再利用します。

対象は少なくとも次です。

- runtime evidenceの欠落 / extra
- stable ID / reference
- fingerprint / dependency
- freshness / currentness
- Skill-local structure state
- traceability / closure
- `qa-workflow`のworkflow state / completion

フェーズ2ではSkill-local eval datasetの`expected.json`を持たないため、dataset専用の`scripts/skills/evals/deterministic/run.py`へ架空のeval IDやexpectedを追加して評価しません。

代わりに、前節で保存したproduction verifier request / resultをEvaluatorが再実行します。これにより、Agentが生成したQA成果物が実行時と同じ既存runtime契約へ現在も適合するかを確認します。

新しい同等validatorやtarget専用runtime schemaは作りません。

### 意味判断が必要な部分

独立Judgeを使い、固定revisionの規範仕様と上記評価観点を根拠に評価します。

Judgeは評価対象Agentとは別process / 別promptで実行します。

Candidate Outputは回収済みartifactを相対path付きで束ねたEvaluator側の表現とし、Agentの最終stdoutだけを評価対象にしません。

Referenceはscenarioで固定した上記7ファイルからEvaluatorが構築します。

`docs/spec/README.md`のOracle優先順位を評価側でも維持し、Feature BR / ACを中心に、Product Scope、Role、State / Scenario、Known Deviation、Unresolvedを必要な補助根拠として扱います。`unresolved-specifications.md`の内容をExpected Behaviorへ昇格しません。

意味評価criteriaはEvaluator側`rubric.json`を使用し、評価対象Agentへ渡しません。

実装は既存の`scripts/skills/evals/semantic/prompt_builder.py`と`scripts/skills/evals/semantic/result.py`の共通処理を再利用します。Skill-local eval IDを前提とする`semantic/run.py` CLIを無理に流用せず、prompt構築・Judge response正規化・rating / verdict契約を共有します。

初回では独自の総合点を作りません。既存semantic評価と同じcriterion rating / evaluable判定から、既存result契約に従ってpass / needs_review / failを導出します。Reference不足で判定できないcriterionは既存契約に従って扱い、target-specificなscore式を追加しません。

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
2. trackedな`qa-training-store-checkout-payment-web-v1` scenario定義を確定しfingerprintを算出する
3. `qa-training-store`の固定revision `84ce165493649550832731a60cf436f8ae29c56b` のtracked contentからsanitized targetを準備する
4. 対象revisionの`docs/spec/README.md`と`docs/spec/features/checkout-and-payment.md`が存在することを確認する
5. 元repoのAgent Skill、過去run / Plan / report、instructor情報、target側Skill eval等を除外する
6. 評価用`AGENTS.md`と必要な評価用Project Contextを作成する
7. 候補`qa-workflow-skills` 19 Skillを`.agents/skills/`へ配置する
8. sanitized targetをfresh Git repositoryにし、Evaluator-owned synthetic baseline commitを作成する
9. `.qa-eval-output/`を作成し、Checkout / Payment評価要求、Agent / model、Judge条件をrun provenanceへ記録する
10. 実Agentを起動し、分析・設計workflowを実行する
11. baseline commitとの差分を確認し、`.qa-eval-output/**`以外のProduct Code / Test / Spec等に変更がないこと、追加commitがないことを確認する
12. 複数QA成果物をscanし、`artifact-manifest.json`を作成して`.agent-eval-runs/`へ回収する
13. 機械判定可能な契約を既存runtime / verifierで確認する
14. 独立Judgeで意味品質を評価する
15. workflow / traceability / semantic結果とprovenanceを同じrunへ保存する
16. runner / environment起因の失敗とSkill品質上のnon-passを分離して報告する

## 完了条件

次をすべて満たしたらフェーズ2初回評価を完了とします。

- テスト対象が`qa-training-store`であることをrun結果から特定できる
- source revisionが`84ce165493649550832731a60cf436f8ae29c56b`として固定・記録される
- 評価対象`qa-workflow-skills` revisionが記録される
- Agent-visibleなSkill集合が今回の19 Skillへ固定される
- 元`.agents/**` / `.codex/**`、`AGENTS.md` / `QA_AGENT.md`によるrepo固有Skill routing・Codex設定・hooks等が評価対象Agentへ残っていない
- 過去run / Plan / report、instructor情報、target側Skill eval、`qa-workflow-skills`のReference / expected / rubric / graderが評価対象Agentへ公開されていない
- 評価用`AGENTS.md`が評価条件だけを持ち、製品仕様や正解QA成果物を追加していない
- 評価対象19 Skillが`.agents/skills/`へ配置され、各Skillの`evals/**`が含まれていない
- Agent開始前のsanitized targetがEvaluator-owned synthetic baseline commitとして固定され、original Git history / remoteを引き継いでいない
- scenario ID / scenario fingerprint、Agent名 / model、Judge条件がrun provenanceへ保存される
- Checkout / PaymentのWeb範囲で実Agent workflowが最後まで実行される
- Product Code、既存Product Test、規範仕様に許可外変更がない
- 複数成果物が`.qa-eval-output/`から`.agent-eval-runs/`へ回収され、`artifact-manifest.json`でpath / SHA-256を追跡できる
- runtime-enabled Skillのproduction verifier request / resultが保存され、Evaluator側で再実行して一致確認できる
- `qa-workflow`の`workflow_runtime.py`も保存済み入力から再実行できる
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
