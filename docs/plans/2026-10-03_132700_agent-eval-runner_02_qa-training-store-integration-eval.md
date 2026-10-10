# qa-training-store固定対象の実Agent統合評価Plan

このPlanは、親Plan [`2026-10-03_132700_agent-eval-runner.md`](./2026-10-03_132700_agent-eval-runner.md) のフェーズ2として、実際のテスト対象リポジトリ `qa-training-store` を使って `qa-workflow-skills` を評価する手順と最小実装を定義します。

フェーズ1の共通ランナーが完成し、既存Eval Inputを使った実Agent生成と既存grader接続が成立してから着手します。

このフェーズの目的は「実repoで一度動かすこと」ではありません。固定したtarget revision、評価要求、Agent / model、Judge条件を使って複数Skillのworkflowを実行し、結果を保存し、**実際に発見した品質問題を自動分析し、条件を満たすSkill単独の問題だけ隔離した修正Agentが修正・再評価して改善を検証する**ことまで含みます。初回評価はbaselineとし、改修前後の証拠を別々に保持します。

初回評価結果はSkill改善のbaselineとして利用します。分析・修正・再評価は親Planの[改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)に従い、条件を満たすものだけ自動で進めます。根拠不足や高リスクはレビュー待ちに分け、検証済み候補でも自動採用しません。比較対象は明示的に使用を要求したSkillによる**分析・設計workflowの成果物品質**です。リポジトリ内の全Skillの実環境動作、native trigger精度、ブラウザE2Eの品質まで保証したとは扱いません。

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

実行時は元の`qa-training-store` checkoutを直接変更しません。比較可能なlive runでは、親Planで指定する**固定Evaluator revision**と**独立したSkill revision**を記録し、Evaluatorの判定実装・規範仕様・Judge条件を変えずにSkillだけを差し替えます。元targetおよびEvaluatorのworking treeがdirtyな場合は有効評価を開始しません。

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

これらをそのまま残して`.agents/skills/`だけ除外すると、「利用を要求するSkillが存在しない」矛盾したtargetになります。また、元repo固有Skillが見える状態では候補revisionから取得したSkill集合以外がroutingへ影響します。

そのため、初回評価では固定revisionのtracked contentからsanitized targetを作り、Agent-visibleな情報を次のように分けます。

### 除外するもの

- 元repoの`.agents/**`
- target repo固有のCodex config / hooks / agents / run artifactを含む`.codex/**`
- 元`AGENTS.md`
- `QA_AGENT.md`
- 元`docs/PROJECT_CONTEXT.md`（除外済みの`feature-plan`、`.codex/runs/`、元repoのhooks等への運用指示と過去履歴を含む）
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
- README等の一般的なrepo資料
- Product Code
- 既存Product Test
- Seed / Test Control
- Build / Test設定
- Checkout / Paymentの理解に必要なその他のtracked Product資料

READMEや既存Testは補助情報として参照できますが、期待動作の優先順位は`docs/spec/README.md`のOracle契約に従います。

### 評価用AGENTS.md

sanitized targetのrootにはEvaluatorが最小の評価用`AGENTS.md`を生成します。元`AGENTS.md`のrepo固有Skill routingはコピーしません。元`docs/PROJECT_CONTEXT.md`もコピーせず、Evaluatorが同じpathへ評価用の最小Project Contextを生成します。これは製品仕様の正本ではなく、今回の評価対象・既存Skillが要求する保存root等の実行条件だけを持ちます。

評価用`AGENTS.md`には、今回の評価に必要な次だけを記載します。

- 対象はCheckout / PaymentのWeb範囲
- Agent-visibleなSkillはEvaluatorが配置した`qa-workflow-skills`の候補revisionから取得したSkill集合だけ
- 規範仕様の優先順位は`docs/spec/README.md`に従う
- Product Code、既存Product Test、規範仕様を変更しない
- 評価成果物の書込みはEvaluatorが指定した`.qa-eval-output/`だけに限定する（source / Skill / 評価用設定はDockerで書込み禁止）
- `artifact-index.json`の`artifacts[]`に実ファイルを、`routing[]`にSkill / scopeごとの実行・再利用・省略・blocked・未完了判断と理由を登録する形式のみ指示する。正解となるrouting一覧・期待QA成果物本文は与えない
- commit / push / PR作成等のGit mutationを行わない
- Evaluator側のReference / expected / rubric / graderを探索しない

この`AGENTS.md`は評価条件を固定するためのHarness入力であり、製品仕様、期待するテストケース、正解となるQA判断は追加しません。

評価用`docs/PROJECT_CONTEXT.md`の生成契約は次に固定します。

- `qa-workflow-skills/skills/qa-workflow/assets/project-context-template.md`にある既存stable key形式に従い、必要な`qa.workflow_state_root`等を`.qa-eval-output/`配下へ向ける。必要なkeyだけ設定し、未使用のrootや権限・能力を捏造しない。
- 対象repo名、固定revision、Web Checkout / Paymentの範囲、参照すべき`docs/spec/README.md`、成果物保存先、Product Code / Test / Specの変更禁止だけを記載する。期待QA成果物・想定テストケース・Judge基準は含めない。
- 元repoの`feature-plan`、`.codex/runs/`、hooks、元Skill発火経路、過去の結果を参照させない。生成したファイルはAgent開始前baselineへ含める。
- 実際の`artifact_graph.py`のProject Context parse / 必須key検証と、評価用rootの解決に通ることをfake Agent testで確認する。検証に失敗した場合はAgentを起動しない。

その上で、今回評価する`qa-workflow-skills`の候補revisionから取得したSkill集合だけをsanitized targetの`.agents/skills/<skill-name>/`へ配置します。配置元は評価対象`qa-workflow-skills` revisionの`skills/<skill-name>/`であり、各Skillの`evals/**`はコピーしません。固定scenarioはSkillの名前や件数を固定せず、候補revisionから取得した実際の集合をrunのmanifestへ記録します。要求成果物の担当Skillが候補revisionに存在しない場合は、該当成果物を補完せず、評価不能な範囲を明示します。必須成果物の欠落を無条件に許容するわけではありません。

フェーズ2のtaskは`qa-workflow`利用を明示するため、このrun自体をnative trigger精度の評価には使いません。`.agents/skills/`へ配置するのは、実際のCodex等で利用するときに近いSkill package形態で複数Skill workflowを実行するためです。

### Agent-visible情報・隔離の成立条件

sanitized targetは単なるファイルコピーであり、`cwd`の変更だけではEvaluator側Reference / rubricや元targetの秘密情報への読み取りを禁止できません。

- Agent subprocessはsanitized targetを`cwd`にして起動する。評価側の原本・grader・Judge資料・採点結果・元target checkoutを、Agentがアクセス可能なファイルシステム、追加のtool / MCP / mount、ネットワーク経路から隔離する。
- 親PlanのLinux Docker構成を使用し、Evaluator原本の非mountによる読み取り隔離を維持する。target workspace全体を**読み取り専用mount**にし、`.qa-eval-output/`に重ねるattempt専用mountだけを書込み可能にする。Codex自身のread-only sandboxはホスト側Evaluator隔離の代わりにしない。独自sandboxは実装しない。
- 同じ権限・mount・tool構成で、Evaluator側に置いた**非秘密の検証用sentinel**の読み取り拒否と、意図しないuser/global Skill・指示・MCPの混入がないことを実Agent smokeで確認し、根拠をrunへ記録する。fake Agentではrunnerの権限分離配線とfail-closeを検証するが、それだけで実Codexの分離成立を証明したとはしない。
- ローカルEvaluator資料のread-denial、source / Skillのwrite-denial、余分なSkill / MCP / web検索の無効化を確認できないrunは`isolation_unverified`として比較から除外する。モデルAPI通信に必要な外部アクセス可能性だけが残る場合は、profileへ条件・残留リスクを記録し、その理由だけで比較不可にしない。秘密情報はログ・provenanceへ記録しない。JudgeはAgentコンテナ外のEvaluator側で、親Planの独立した`judge.command_argv`と固定cwdで起動する。

## source変更の扱い

分析・設計評価ではProduct Code、既存Product Test、規範仕様を変更しません。

sanitized targetの構築、評価用`AGENTS.md`、候補revisionから取得したSkill集合、評価用Project Contextの配置が完了した時点を**Agent開始前baseline**とします。

baseline固定のため、sanitized targetでfresh Git repositoryを初期化し、remoteなし・固定の非個人local identityでEvaluator-owned synthetic commitを1件作成します。original Git history / remoteは引き継ぎません。

その後、Evaluatorはsanitized targetの`.qa-eval-output/`を空のmount pointとして作成し、別のattempt専用ホストディレクトリをその位置へ書込み可能mountとして重ねます。Agentへの永続書込み先はこの出力rootだけに固定し、sourceへの書込みを許可しません。

Agent実行前に、baseline commitのあるsanitized targetをDocker内で**読み取り専用**にmountします。`.qa-eval-output/`は事前に作成したmount pointへattempt専用の書込み可能rootを重ね、`/tmp`と一時`CODEX_HOME`以外の書込みを禁止します。評価用`AGENTS.md`、`docs/PROJECT_CONTEXT.md`、製品Code / Test / Spec、配置Skill、`.git/`も読み取り専用です。Agentの指示遵守や終了後の差分確認だけに不変性を依存させません。実行中に書いて元へ戻す操作もOS側で拒否します。

終了後はsynthetic baseline commitとのGit差分に加え、Agent-visible workspaceに存在する**tracked / untracked / ignored fileすべて**のrelative path・size・SHA-256・symlinkを開始前manifestと照合します。Gitの`.gitignore`にある`dist/`、`output/`、`test-results/`などを差分検査から除外せず、許可外の追加・変更・削除を検出します。`.qa-eval-output/`の内容は別の成果物回収処理で検証します。許可外変更、Git commit、Git remoteや想定外の書込みmountがあれば有効なSkill比較へ昇格せず、runに根拠を保存します。

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
実Agentが各QA成果物を個別fileとして保存し、artifact-index.jsonへ登録
  ↓
Agent終了
  ↓
Evaluatorがoutput rootをscan
  ↓
path / symlink / sizeを検証
  ↓
登録済みindexとrouting / 既存Skill出力契約を検証してQA成果物・runtime証拠・runner内部ファイルに分類
  ↓
各fileのSHA-256と相対path・分類をartifact-manifest.jsonへ記録
  ↓
.agent-eval-runs/<run>/target-artifacts/ へcopy
  ↓
source差分を確認
  ↓
sanitized targetを破棄
```

Agentの最終stdoutは、実際のrouting・完了 / blocked・次工程の宣言を含み得るため、そのまま**workflow判断の評価証拠**として別保存します。複数Skillの正規QA成果物は登録・検証済みartifact file群とし、stdoutを正規QA成果物へ昇格させません。

Evaluatorは成果物内容を独自schemaへ変換しません。各Skillの既存Markdown / runtime evidence契約を維持したままcopyし、`artifact-manifest.json`には少なくとも次だけを保存します。

- relative path
- file size
- SHA-256
- 正規Skill名（workflowで生成元が特定できないものは未確認として記録し、推測しない）
- fileの分類（`qa_artifact` / `runtime_evidence` / `runner_internal`）と分類根拠。`qa_artifact`には検証済み`artifact-index.json`の登録行、routingに基づく期待工程・成果物種類を紐付ける
- runtime対象かどうか、および既存Skill契約から必要と判定したverifier request / resultとEvaluator再実行resultへの相対path
- 各artifactのSHA-256と結び付いたverifier対象artifactの相対path。対応するrequest / resultがないときはnullと欠落理由

### 評価用QA成果物の登録契約

各Skillの既存Markdown本文・runtime保存契約は変えず、フェーズ2だけでAgentに**最小の評価用登録ファイル**`.qa-eval-output/artifact-index.json`を保存させる。root objectは`schema_version=1`、`artifacts[]`、`routing[]`の3キーとする。`artifacts[]`は実在成果物、`routing[]`はAgentが各工程について行った判断を記録する。両方は自己申告であり、Evaluatorが独立して検証する。

```json
{
  "schema_version": 1,
  "artifacts": [
    {"skill":"test-case-design","kind":"test-case","scope":"checkout-payment-web","artifact_id":"tc-design-01","path":"design/test-case-design/tc-01.md"}
  ],
  "routing": [
    {"skill":"test-case-design","scope":"checkout-payment-web","status":"executed","reason":"test-condition-designの結果から詳細TCを作成","artifact_ids":["tc-design-01"]}
  ]
}
```

- `skill`は配置済みSkill集合に含まれる正規名、`kind`は対象Skillの既存出力契約からEvaluator scenarioに固定した成果物種類、`scope`は今回要求・routingで確定した対象 / 実行範囲、`artifact_id`は同一attempt内で一意の非空ASCII識別子、`path`は`.qa-eval-output/`基準の正規化relative pathとする。上例は形式を示すものであり、すべてのTCが固定の名前になるという意味ではない。
- evaluatorはscenarioに保持する**既存Skill出力契約から導いた`skill -> kind`許可集合**と登録情報を照合する。`artifact_id`・`path`の重複、同一fileの二重登録、未知のSkill / kind / scope、出力root外path、symlink、file不存在、runtime / internal fileへの参照、cross-attempt参照を拒否する。同じSkillで複数成果物があっても`artifact_id`とpathが別なら許可する。file hash・sizeはEvaluatorが現物から算出し、Agentの申告SHAを信用しない。
### routing判断と必須成果物の判定

`routing[]`の各行は`skill` / `scope` / `status` / `reason` / `artifact_ids[]`を必須とする。`status`は`executed`、`reused`、`skipped`、`blocked`、`incomplete`のいずれかとする。Skill名は正規名、scopeは今回の要求から定めた正規値、reasonは空でない文字列、artifact_idsは上記artifactsのID（重複なし）とする。`executed`では生成した成果物のIDを紐付ける。`reused`では同一attemptで実体・鮮度・元の生成者を検証できる成果物への参照だけ許す。`skipped` / `blocked` / `incomplete`では対応scopeと理由を残し、完了を偽装しない。`qa-workflow`自体の最終判断は最終stdout / workflow runtimeを対応証拠とするため、`artifact_ids=[]`でもよい。

- 固定scenarioには、要求結果として**仕様根拠の整理、テスト分析、TR、TCN / CI、TC、カバレッジ確認、反証レビュー、最終workflow判断**の8種類と対応する正規担当Skill / scopeを定義する。`question-analysis`は実際に不明点・矛盾を解消する必要がある場合だけ要求する。E2E実装・実行や全Skillを常時必須にしない。これらの結果を作る順序・必要性の細部は既存`qa-workflow` / 工程Skill契約に従う。
- Evaluatorは固定scenarioの要求結果を起点に、各結果の存在を確認し、`routing[]`を照合する。明示されていない必須工程の行、重複`(skill, scope)`、未知status、不正ID参照、`executed`なのに実ファイルなし、`reused`だが信頼可能な既存成果物なしを検出する。`routing[]`が空でもAgentの省略判断を正しいと仮定しない。
- `skipped` / `blocked` / `incomplete`は無条件に正当化しない。省略・blocked理由が固定要求や既存Skillの条件付きrouting規則と矛盾する場合はrouting品質の非passとする。機械的に判定できない理由は`QTS-SEM-001/002`の固定Judgeへuntrustedな自己申告として渡し、根拠不足なら`needs_review` / 未完了とし、成功扱いしない。
- `artifact-index.json`自体の欠落・構文不正・routing登録不備は`evidence_unverified`（`reason=routing_record`または`artifact_classification`）として記録する。**QA成果物ファイルが実際に未生成**であることを独立確認できた場合や、必須工程を根拠なく省略したことが確認できた場合に限り品質non-passとし、単なる登録不備を成果物未生成と混同しない。
- 回収したrouting記録・Evaluator照合結果・最終回答・workflow runtime要約を同じattemptの証拠として結び付ける。routing記録はQA成果物に昇格させず、Judge入力では`QTS-SEM-001/002`の専用区分にのみ使用する。新たな汎用workflow engineやSkill本体の保存契約変更は行わない。

- EvaluatorはAgentの登録行だけからworkflow routingや必須成果物集合を決めない。上記の**固定scenarioの要求結果**から必要成果物の種類・scopeを先に確定し、申告された`routing[]` / blocked理由と照合して登録済み成果物を対応付ける。分類の裏付けは登録情報とfile実在・許可集合・workflow整合の組合せであり、filenameやMarkdown見出しの推測ではない。Agentの登録はSkillを実使用した証拠とは扱わない。
- `artifact-index.json`の欠落・schema不正・登録漏れ・分類不能は**`evidence_unverified`（`reason=artifact_classification`。Evaluatorが評価入力を確定できない状態）**として記録する。file自体の存在確認と分類不能を分け、必要なQA成果物が実際に未生成と独立確認できた場合のみSkill品質の非passとする。分類不能なfileを黙って`runner_internal`へ変換して『欠落』扱いしない。schemaが誤りでも収集可能な原fileと診断情報は保存する。分類を補うためのLLM推測・自由なpath走査による自動判定は追加しない。

Evaluatorが作る`artifact-manifest.json`は検証済みindexの各登録をpath・size・SHA-256・runtime証拠との関係へ正規化した結果であり、**Agentの自己申告indexとは別物**である。`artifact-index.json`そのものは`runner_internal`として回収し、Judgeへ正規QA成果物として渡さない。JudgeのQA成果物集合を確定できないattemptは完了PASSにしないが、既に評価可能なsemantic criterionは記録する。
### Judge投入対象と内部証拠の境界

`.qa-eval-output/`の全fileは安全なpath・size・hashを検査して**回収とmanifest記録**を行うが、Judgeへ渡すCandidate Outputは次の規則で選ぶ。拡張子やフォルダ名だけで正規QA成果物を推定しない。

| 分類 | 対象 | Judgeへの投入 |
|---|---|---|
| `qa_artifact` | routingが要求した仕様分析、テスト分析、TR、TCN / CI、TC、coverage、adversarial review等の成果物。正規Skill名・生成目的・artifact pathが確定したもの | 対象とする |
| `runtime_evidence` | `.runtime-evidence/**`のrequest / result / invocation、production verifierの入力・出力、workflow state等の機械検証用データ | 原則投入しない。runtime判定へ使用する |
| `runner_internal` | `final-message.md`、Codex診断記録、launcher状態、capture記録等の評価実行情報 | 投入しない |

- `.qa-eval-output/.runtime-evidence/**`と`.qa-eval-output/final-message.md`は**常にQA成果物から除外**する。評価用`.qa-eval-tools/**`もQA成果物ではない。`qa-workflow`のworkflow stateは機械判定用とし、Judgeには成果物上の工程・参照関係を評価させる。内部stateやverifier JSONを成果物内容の代用品にしない。
- `qa_artifact`はscenarioの要求と実際のroutingから期待される成果物単位を確定し、manifestに記録したSkill名・相対path・SHA-256・成果物種類と照合したものに限る。分類不能なfileはQA成果物へ昇格せず、`evidence_unverified`（`reason=artifact_classification`）として回収し、未生成と断定しない。必須成果物欠落も補わない。
- Judgeへ渡す際は、要求から確定した**工程順**、同工程なら**Skill名と正規化relative path昇順**で並べ、各本文にrelative path / Skill / 種類を付ける。Evaluatorが勝手に要約・補完しない。必須QA成果物が欠落した場合は`missing: <required-kind>`と機械的に明示し、stdout / runtime証拠で埋めない。Judge入力全体の選択manifest、file順序、内容fingerprintを保存して比較条件を固定する。
- 対象外の内部fileにだけ重要情報があっても、QA成果物がその内容を表現していなければ意味評価で救済しない。QA成果物の欠落は独立した機械判定でnon-passとして保存する。

symlink、output root外を指すpath、path traversal、許容上限を超えるfileは回収せずrunをexecution errorとします。

workflow state等で保存rootが必要な場合は、Evaluatorが評価用Project Contextへ`.qa-eval-output/`配下のproject-local rootを設定します。既存Skillの保存契約を変えず、評価用の保存先だけを与えます。

runtime-enabled Skillは既存Skillの指示に従って`verify_runtime_evidence`等を実行します。**request / resultを別のJSON fileとして残すことは既存Skillの義務ではない**ため、記録経路はEvaluator側が提供します。Agentの説明文や実行後に作成された自己申告JSONを実際の実行証拠とみなしません。具体的な経路は次節に固定します。

Evaluatorは回収後、候補Skill revisionの**信頼済みGit tracked content**に含まれるproduction verifier / generatorをAgentとは独立した評価側processで再実行します。保存requestの`artifact_markdown`だけを回収済みartifact本文へ差し替え、その他のnormalized input / scope / previous artifact等は変更しません。入力・生成結果のfingerprint、`valid`、`current_structure_state`、runtime unitと実際の候補sourceとの整合性を確認します。出力の機械構造とtraceabilityを比較するgrader・Judgeのcriteriaは固定Evaluatorを使い、必要なsource照合だけ候補tracked sourceに向けます。

既存`runtime_contract.py`の`_validate_runtime_pair()`は実行側`runtime_contract.py`およびgenerator sourceのhashと比較して`stale_runtime_implementation` / `stale_generator_implementation`を発生させます。そのため**固定Evaluator版production verifierを別revisionの成果物へそのまま適用しません**。固定grader側でruntime sourceを参照する処理も親Planの最小`source-root`指定に従い、候補の信頼済みsourceから照合します。これはfingerprint照合の無効化ではなく、鮮度判定の参照元を正しく固定する修正です。

両revisionで共通評価できないschema / 機械契約の部分は`evaluator_incompatible`として比較不可にし、意味品質を一律に無効とはしません。旧・新両方を受け付けるEvaluatorが必要なら、それを固定したうえで**両Skill revisionを同条件で再実行・再採点**します。候補のverifierが`valid=true`を返すだけでは品質PASSとはしません。Agentが独自のexpected Entity / fingerprintを手組みした場合は既存verifierの拒否契約を維持します。

`qa-workflow`については、Skill-local`verify_runtime_evidence`に加えて、実行時に使用した`workflow_runtime.py`入力 / 結果も保存・再実行対象にします。

### 評価用のverifier入出力取得経路

Evaluatorはsanitized target生成時に、正解情報を含まない最小の評価用CLIラッパー`scripts/skills/evals/agent/verifier_capture.py`を`.qa-eval-tools/verifier_capture.py`として配置し、synthetic baselineへ含める。このコードは評価専用であり、候補Skillの`SKILL.md`やproduction verifier本体を変更しない。評価用`AGENTS.md`とpromptには、実行時のproduction verifier / `workflow_runtime.py`を呼ぶ場合、次の経路を使うことだけを明示する。

1. Agentは既存Skill契約に必要なrequest JSONを`.qa-eval-output/.runtime-evidence/<skill>/<artifact-id>/<invocation-id>/request.json`へUTF-8として書く。`artifact-id`は同一attempt内の成果物相対pathのSHA-256で識別し、`invocation-id`は1回の試行内で一意とし、retryも別IDを使う。artifact pathとの対応をEvaluator manifestに保存する。request fileに秘密を含めない。
2. Agentは`python .qa-eval-tools/verifier_capture.py --skill <skill> --operation verify|workflow-runtime --request <request.json> --record <invocation-dir>`を実行する。ラッパーは`--skill`とoperationを許可済みのSkill-local script pathへ写像し、任意command / 任意pathを実行しない。`request.json`の**保存済みbytesそのものを**対象CLIのstdinへ渡す。対象scriptを候補Skill workspace内から呼び、stdout bytesを`result.json`、stderrを安全化した診断、exit code / request・result SHA-256を`invocation.json`へ記録する。正常終了時も`valid=false`を維持する。入出力と実行metadataの保存は一時fileからatomicに確定し、不完全なrecordを成功扱いしない。
3. `workflow_runtime.py`はruntime input envelopeを同じ方法で送信し、戻りのruntime result envelopeをそのまま保存する。`verify_runtime_evidence`の`valid`と`workflow_runtime.py`の`payload.can_complete`は別々に判定する。
4. ラッパーは記録完了後に結果をAgentへ返し、Agentは既存Skill契約どおり結果を参照して最終成果物を確定する。これによりAgentが前もってファイルを作っただけでは`invocation.json`が成立しない。ただしAgent-visible fileの自己改ざんを防ぐ暗号的監査機構ではないため、Evaluatorはbaseline差分、request / result hash、候補revisionからの独立再実行で整合性を確認する。
5. 実行後にEvaluatorは`invocation.json`を含むrecordをmanifestへ回収する。request / result / exit codeの実記録が欠落・破損した場合は`evidence_unverified`に分類する。成果物が存在し、他のgraderで採点できる場合はその判定を残すが、verifierを実行しなかったという事実が観測されない限り**Skillの品質FAILへ転記しない**。

ラッパーは評価用のプロセス入出力transportだけを担い、runtime検証アルゴリズムを再実装しない。標準ライブラリで実装し、CIのfake Agentでfile記録・再試行・欠落・不正なrequest・symlink / path traversal・atomic書込み失敗を検証する。実Codexでは記録済みJSONと`--json` tool traceの実行イベントを照合する。
### 成果物とproduction verifierの対応・判定

EvaluatorはAgentが作成したartifactだけを見て、必要な成果物や証拠が揃っていると推測しません。**固定scenarioの要求結果と既存Skillの担当契約**から必須成果物の種類・scopeを確定し、申告された`routing[]`、実成果物、最終stdout / runtime状態と照合します。自己申告だけで母集団を縮小しません。条件付きSkillの省略理由は固定ルールまたは`QTS-SEM-001/002`で検証し、根拠不足は完了と扱いません。全Skillを固定順で実行させることもしません。

- runtime-enabled Skillの各成果物について、同一attempt内で`Skill名 + artifact相対path + SHA-256 + request / result / invocation path`を対応させる。重複path・他attemptの証拠を拒否する。`qa-workflow`は`verify_runtime_evidence`と`workflow_runtime.py`のinput / resultを別々に集め、片方が欠落した場合はその観測状態を残す。
- Evaluatorのrequest置換は`artifact_markdown`のみとする。normalized input、previous artifact、scope、expected Entity等を都合よく修正しない。参照された依存成果物の所在とhashも同一attemptで照合する。
- production verifierが終了コード0でも`valid=false`なら、**契約適合した成果物とは判定しない**。`valid=true`、期待される`current_structure_state`、必要なworkflow completionをそれぞれ判定し、`workflow_runtime.py`のプロセス成功だけでworkflow完了としない。
- 正当な`blocked` / `incomplete` / `unresolved`は証拠として保存する。ただし今回の評価要求を完了したという判定とは区別する。仕様根拠不足で止まるべきケースは意味評価で妥当性を判定する。
- 必須のQA成果物が生成されなかった場合は、実行基盤が正常ならSkill品質上の非passとする。一方、**verifierのrequest / resultやtraceだけが欠落した場合は`evidence_unverified`として品質判定と分離**する。明示的なtool trace等からverifier未実行が確定した場合と、単に証拠が取得できなかった場合を混同しない。`valid=false`を完成扱いした事実が確認できた場合はSkill品質の非passとする。Evaluator側のpreparation / capture / I/O / 独立再実行障害は`runner/environment error`に区分し、Skill品質へ転嫁しない。既存verifierの判定ロジックは再実装しない。

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
- Agent-visible Skill集合の導出規則（指定`--skill-revision`のGit treeにあるtracked `skills/<skill>/SKILL.md`から取得し、runごとのmanifestで固定する）
- sanitized targetから除外する評価汚染情報
- 評価出力root
- Judgeが参照する規範仕様path:
  - `docs/spec/README.md`
  - `docs/spec/product-scope.md`
  - `docs/spec/roles-and-permissions.md`
  - `docs/spec/state-and-scenarios.md`
  - `docs/spec/ui-ux-contract.md`
  - `docs/spec/features/checkout-and-payment.md`
  - `docs/spec/features/authentication.md`（`AC-CHECKOUT-001`の再Login復帰に必要なSession・Role・Return先だけを評価対象にする）
  - `docs/spec/features/cart.md`
  - `docs/spec/features/orders.md`
  - `docs/spec/features/admin-inventory.md`
  - `docs/spec/known-deviations.md`
  - `docs/spec/unresolved-specifications.md`
- 意味評価criteria（上記`QTS-SEM-001..010`、固定した`critical`とReference対応）

scenario定義と評価要求からfingerprintを算出し、親Planのrun provenanceへ保存します。

Skill修正前後を比較するときは、target revision、Evaluator / grader revisionとReference fingerprint、scenario fingerprint、Agent / Judgeの検証済み実効設定、隔離条件、repeat条件を一致させます。これらが異なるrunは参考比較には使えても、Skill変更だけの効果として直接比較しません。

scenario定義は現在の`qa-training-store`初回評価を再現するための固定fixtureであり、任意repoを扱うplugin interfaceにはしません。

## 評価方法

フェーズ2では、既存のSkill-local eval datasetを`qa-training-store`向けに置き換えません。

評価を次の2層へ分けます。

### 機械判定できる部分

**候補Skillのproduction verifier再実行と、固定Evaluatorの共通機械判定を別の処理経路とする。** フェーズ2にはSkill-local eval datasetの`expected.json`がないため、`deterministic/run.py`へ架空eval IDを追加しない。

1. Agent実行時には既存Skillの`runtime_contract.py` / `workflow_runtime.py`呼び出しを`verifier_capture.py`で記録し、実際に使われたrequest・result・終了コードを回収する。
2. Evaluatorは親Planで指定した**別Dockerコンテナ**に候補Git tree由来のsourceを読み取り専用mountして同じrequestを再実行する。Evaluator checkoutやReferenceはmountしない。再実行は候補の鮮度・再現性の確認であり、その`valid`を固定品質基準へ代入しない。
3. **固定Evaluator**の`common_runtime_checks.py`が、回収済みartifact・同一attemptのnormalized input・Runtime Input / Result・Machine Entityを入力として固定schemaと依存・参照・graphの不変条件を検査する。再利用元は固定Evaluatorの`deterministic/runtime_validator.py`の純粋なparser / fingerprint assertionと、固定した`coverage-analysis/scripts/traceability.py`のgraph / closure規則である。候補コードをEvaluator process内でimportせず、候補`valid`を条件分岐に使わない。
4. 検査項目は、Runtime Input / Result pairのschema・identity・fingerprint再計算、runtime unit / Machine Entityの重複・欠落、stable ID一意性、既存Entity / unitへの依存参照、Authority → TR → TCN → CI → TCの到達・孤立・重複edge、coverage / 未閉鎖、`qa-workflow`の必要scopeと`can_complete`の整合とする。TCNからCIを経る場合と既存契約上の許容edgeは既存fixed graph validatorに従う。`current_structure_state`は保存値と実際のEntity / runtime状態との一致を固定基準で確認する。
5. フェーズ2の必須範囲はEvaluator側scenarioに固定した`BR-CHECKOUT-001..003`と`AC-CHECKOUT-001..003`および実際のworkflow routingとの照合で決める。Agentがnormalized inputに重要Authorityや工程を記載しなかっただけで期待集合を縮小しない。scope不足・証拠不足・正当なblockedは区別し、未完了を成功にしない。
6. 候補`valid=true`なのに固定検査FAILなら**機械品質非pass**を記録し、候補が緩くなった可能性を差分として示す。候補`valid=false`だが固定検査PASSでも候補側契約を満たさない結果として非passを残す。判定不能なschema差だけ`evaluator_incompatible`とし、両revision共通Evaluatorを更新した場合は両方新規評価する。全共通検査がPASSし、かつ必要なproduction verifier証拠と完了状態を確認できた場合のみruntimeを検証済みPASSとする。

新しいproduction verifierや同等の汎用graph engineは作らない。既存固定コードから抽出・再利用するのは上記不変条件であり、Candidate側の`valid`に依存する判定は共通Evaluator側に置かない。回帰テストでは`valid=true`を常時返すよう弱体化した候補、重複ID、存在しないedge先、欠落した必須link、runtime fingerprintのみ差し替えた互換候補を作り、候補の自己判定とは独立した検出と正常差分の許容を確認する。
### 意味判断が必要な部分

独立Judgeを使い、固定revisionの規範仕様と上記評価観点を根拠に評価します。

Judgeは評価対象Agentとは別process / 別promptで実行します。

Candidate Outputの**正規QA成果物部分**は前節のmanifestで`qa_artifact`と確認したfileだけを固定順で束ね、必須QA成果物欠落を明示する。意味評価は**2回の独立Judge呼び出し**に分割する。`QTS-SEM-001/002`は正規QA成果物に加えてworkflow用`routing[]`・最終stdout・固定機械判定要約を受け取り、`QTS-SEM-003..010`は**正規QA成果物と必須成果物欠落表示のみ**を受け取る。後者のJudge promptへ`routing[]`・最終stdout・機械判定要約を送らず、評価対象外の自己申告でQA成果物の欠陥を補完できないようにする。`runtime_evidence`、`runner_internal`を正規QA成果物の代用品にしない。

Referenceはscenarioで固定した上記規範・補助文書からEvaluatorが構築します。対象scope内でUIのキーボード操作・エラー表示・次Actionを採点するときは`ui-ux-contract.md`、Order Snapshot / Historyは`features/orders.md`、Cart再検証は`features/cart.md`、在庫減算履歴は`features/admin-inventory.md`の該当箇所を含めます。低レベルのRoute / Seed Scenario ID / Test ID等をcriteriaとして判定するときは、各Featureが指すExecutable Canonical Sources（固定target revisionのCode / Config）をEvaluator側Referenceに追加し、そのpathと内容fingerprintをscenarioに固定します。採点しない低レベル値のためにコード全体を無条件投入しません。

`docs/spec/README.md`のOracle優先順位を評価側でも維持し、Feature BR / AC・UI/UX・隣接Featureの規範を中心に、Product Scope、Role、State / Scenario、Known Deviation、Unresolvedを必要な補助根拠として扱います。各criterionから根拠文書pathへ辿れるようscenario内に対応表を置き、選択したReferenceのSHA-256を保存してJudge入力の同一性を検証します。`unresolved-specifications.md`の内容をExpected Behaviorへ昇格しません。

意味評価criteriaはEvaluator側`rubric.json`を使用し、評価対象Agentへ渡しません。

実装は既存の`scripts/skills/evals/semantic/prompt_builder.py`と`scripts/skills/evals/semantic/result.py`の共通処理を再利用します。Skill-local eval IDを前提とする`semantic/run.py` CLIを無理に流用せず、prompt構築・Judge response正規化・rating / verdict契約を共有します。各Judge呼び出しには対象criterionの部分rubricだけを指定し、同一の固定Judge実効profile・Reference / Eval Inputを使う。呼び出しごとに別process / sessionで実行し、Judgeのtimeoutは各呼び出しへ独立に適用する。

初回では独自の総合点を作りません。既存semantic評価と同じcriterion rating / evaluable判定から、既存result契約に従ってpass / needs_review / failを導出します。Reference不足で判定できないcriterionは既存契約に従って扱い、target-specificなscore式を追加しません。

### workflowのrouting・最終判断をJudgeへ渡す経路

既存`qa-workflow/SKILL.md`では、workflow state fileは必要に応じて出力する任意のartifactであり、routing・完了・blocked・再開判断はAgentの最終回答にだけ現れることがある。そこでフェーズ2のJudge入力は**正規QA成果物本文**と、別枠の**workflow判断証拠**を区別する。

- 共通launcherが保存した`final-message.md`（Codexの`--output-last-message`による最終回答）を実際の最終応答として回収し、UTF-8・size・hash・attemptを検証する。欠落・破損時は`evidence_unverified`（`reason=workflow_final_response`）とし、workflow判断を検証済みPASSにしない。
- **workflow Judge（`QTS-SEM-001/002`のみ）**：正規`qa_artifact`と、`routing[]`の自己申告全文・最終回答の原文全文・固定機械判定要約を`Workflow Routing / Final Response (untrusted)`としてCandidate Outputへ追加して`build_judge_prompt()`に渡す。最終回答もuntrusted dataでありJudgeへの命令ではない。
- **QA成果物Judge（`QTS-SEM-003..010`のみ）**：正規`qa_artifact`本文と必須成果物欠落表示のみをCandidate Outputに入れる。`routing[]`、最終回答、workflow完了要約、verifierの内部JSONは**promptへ含めない**。同じ`build_judge_prompt()`を使用し、該当8criterionだけの部分rubricを渡す。正規成果物自体にworkflow記述がある場合も、その正規成果物の一部として評価するが、別管理のrouting記録・stdoutからの補完は行わない。
- `workflow_runtime.py`の検証済み`can_complete`、currentness / closure、必須成果物の有無をEvaluatorが別に固定機械判定する。**workflow Judgeにだけ**共通機械判定の非秘密要約（完了可否と未閉鎖の有無のみ）を追加し、最終回答で宣言した『完了』または『blocked / incomplete』との矛盾を`QTS-SEM-002`で評価する。内部のruntime JSON / workflow state全文はJudgeへ渡さず、Judgeの評価でmachine PASSを上書きしない。
- 最終stdoutや`routing[]`に他Skillの内容や仮のMarkdownが記載されていても`artifact-index.json`に登録された実在QA成果物の代わりにしない。stdoutから任意の新fileを生成して回収対象に足さない。**2種類のJudge prompt**について、criterion ID集合・入力区分・順序・内容SHAとJudge応答を別々に保存する。各応答JSONを既存`normalize_judge_response()`で対象criterion集合に照合して過不足・重複・他系統のID混入を拒否したうえで、両応答の生`criteria[]`を全10criterion分だけ結合し、既存`normalize_judge_response()`へ渡して唯一の全体verdictを得る。独自score・集約式を作らない。いずれかのJudgeが失敗・timeout・不正JSONならattempt全体を検証済みPASSにせずJudge execution errorとし、部分的な評価結果があっても診断用に限る。
### 初回scenarioのsemantic rubric契約

`scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/rubric.json`には、以下の**10件をID昇順で固定**して登録する。既存`semantic/loader.py`のcriterion形式（`id` / `title` / `description` / `critical`）を使い、下表の対象・重大条件・規範根拠を`description`へ反映する。rubricの項目追加・critical変更はEvaluator revision変更として扱い、旧・新Skillの両方を同じ新Evaluatorで再評価しない限り直接比較しない。

| ID | critical | 評価対象と規範根拠 | rating 1となる重大な条件 |
|---|---|---|---|
| `QTS-SEM-001` | true | `qa-workflow`のrouting。要求に必要な分析・設計工程が選択され、不要なE2E実装・実行へ逸脱しない（`qa-workflow/SKILL.md`、固定の評価要求） | 必要な主要工程を根拠なくスキップし、最終QA成果物の意味品質が成立しない |
| `QTS-SEM-002` | true | workflowの完了判断。未閉鎖・blocked・未完成を完成扱いしない（`qa-workflow/SKILL.md`、正規QA成果物） | 必須の分析・設計成果物がない、または重大な未解決を隠して完了を宣言する |
| `QTS-SEM-003` | true | Oracle選択と規範の優先順位（`docs/spec/README.md`、`product-scope.md`、`roles-and-permissions.md`） | README / 実装観察 / Unresolvedを正式な期待動作へ昇格し、重大な誤ったテスト期待値を作る |
| `QTS-SEM-004` | true | Checkout Sessionの再開・置換・24時間期限切れ・再ログイン復帰（`BR-CHECKOUT-001` / `AC-CHECKOUT-001`、`state-and-scenarios.md`、`features/authentication.md`のSession・Role・Return先） | 同じCart / Versionの再開、Version変更時の置換、期限切れのいずれかを欠落させ、主要なテスト条件が成立しない |
| `QTS-SEM-005` | true | Order確定直前のCart Version / 価格再検証と差戻し（`BR-CHECKOUT-002` / `AC-CHECKOUT-002`、`features/cart.md`） | stale Cartまたは価格不一致でもOrder / Paymentを作ってよいとする、または両方の差戻し境界を欠落させる |
| `QTS-SEM-006` | true | Mock Payment成功・明確失敗時のOrder / Inventory / History整合（`BR-CHECKOUT-003` / `AC-CHECKOUT-003`、`features/orders.md`、`features/admin-inventory.md`） | TEST-SUCCESS以外で在庫を減らす、成功時のOrder paid・在庫減算を欠く、明確失敗で在庫を変える、購入と在庫履歴の整合を無視する |
| `QTS-SEM-007` | true | processing中のresume・retry / cancel禁止と最終在庫不足（`BR-CHECKOUT-003` / `AC-CHECKOUT-003`、`state-and-scenarios.md`） | processing中の再試行・Cancelを許容する、processing再開または最終在庫不足の重要境界を欠落させる |
| `QTS-SEM-008` | false | 分析結果からテスト条件・ケースへの具体化、開始条件・操作・観測可能な期待値（`test-analysis` / `test-condition-design` / `test-case-design`のSkill契約、上記BR / AC） | ケースが実行不能で、必要な入力・操作・PASS/FAIL条件を複数の重要ケースで特定できない |
| `QTS-SEM-009` | true | Authority → TR → TCN → Coverage Item → TCの意味的な対応と未閉鎖の扱い（各Skill契約、生成した正規QA成果物） | 重要な仕様根拠とテストが対応しない、下流成果物が別要求を根拠にする、重大な未閉鎖を根拠なく解消したと扱う |
| `QTS-SEM-010` | true | 仕様にない挙動を確定した期待値へしない（`product-scope.md`、`checkout-and-payment.md`、`known-deviations.md`、`unresolved-specifications.md`） | 外部Payment API、実provider、Server-side認可、Backend通信、存在しないToast等を現行の確定仕様として追加する |

ratingの共通尺度は既存`semantic/prompt_builder.py`に従う。`4`は要求を明確に満たす、`3`は軽微な改善余地のみ、`2`は実質的な不足・要確認、`1`は上表の重大欠落・誤りに該当する。各criterionで**欠落や誤りが局所的か、主要な要件を損なうか**を理由とQA成果物の具体的evidenceに基づいて区別する。重要な条件の部分欠落でも、上表のrating 1条件に達しないならrating 2とし、説明の好みでは下げない。

- `critical=true`のrating 1は既存`result.py`により全体`fail`。非criticalのrating 1やrating 2は`needs_review`となる。新しい点数式や独自の重み付けを作らない。
- **Candidate Outputに必須成果物・記述がないこと**は通常`evaluable=true`で評価する。該当根拠が欠落していることをevidenceへ記録し、単に記述されていないことを理由に`evaluable=false`へ逃がさない。
- `evaluable=false`を許すのは、適切に投入したReferenceにも規範根拠が存在せず、特定criterionを評価不能な場合のみ。Reference file自体の欠落・破損やscenario対応ミスはJudgeの`not_evaluable`ではなくEvaluator preparation errorにする。`evaluable=false`が残ったrunはそのcriterionの検証済みPASSではなく`needs_review`として扱う。
- `QTS-SEM-001/002`側のJudgeだけが正規QA成果物に加えて`routing[]`の申告・最終stdoutのrouting / 完了宣言と固定機械判定要約を参照する。`QTS-SEM-003..010`側のJudgeは正規QA成果物と必須成果物欠落表示だけを受け取り、`QTS-SEM-009`もそこから判断する。必要なruntime証拠・completion・stable IDの実検証は固定Evaluatorへ任せ、Judgeへ内部JSON本文を渡さない。

受入用fixtureには、(1)正常例（全criterionでrating 3以上）、(2)Payment成功・失敗の整合違反（`QTS-SEM-006`がrating 1）、(3)仕様にない外部決済APIの確定（`QTS-SEM-010`がrating 1）を含める。さらに**未検証のcritical criterion（`001/002/003/004/005/007/009`）を各1件の代表的な重大違反例で検証する**。期待するratingは各criterionの既存rubric上の重大条件から定め、人間が規範Referenceと違反根拠を確認する。重大違反例は該当criterionでrating 1・全体`fail`を期待し、Judgeが判定できない・判定が揺れる場合は検証済みと扱わず根拠を調査する。`QTS-SEM-008`は`critical=false`なので今回の7件の追加対象には含めず、既存の通常評価対象として維持する。

### 試行・使用証拠・比較可否

フェーズ2のCLIもフェーズ1と同じ`--repeat N`（既定1）を受け付け、**attemptごとにfreshなsanitized target・synthetic baseline commit・実Agent session・成果物回収・verifier再実行・Judge呼び出し**を行います。1回目の生成物を2回目へ持ち込まず、attempt番号と結果を別保存します。集計は各attemptの既存`pass / needs_review / fail / execution error`件数と根拠だけとし、独自総合点や統計的な有意差判定は作りません。

Evaluatorは候補revisionのSkill集合・ファイルSHA-256とprompt指定を投入条件として検証し、Agentの`SKILL.md`読取 / 適用に関するtraceは別に`observed` / `unverified`として残す。native injectionはOSコマンドに現れないことがあるため、未観測だけで**成果物品質比較**を無効にしない。ただし**Skill改修の効果判断**では、変更されかつ`routing[]`で対象になったSkillについて双方のrunに使用証拠が必要。観測できなければ成果物差だけ報告しSkill効果は判断不能とする。複数Skillの個別寄与も断定しない。native `description` trigger評価ではない。

異なるSkill revision間の直接比較では、**固定Evaluator SHA・grader / 固定共通機械判定・2系統のJudge入力構築規則・rubric / Reference SHA・target SHA・scenario / input fingerprint・Agent / Judge実効設定・隔離条件・繰り返し条件**の一致を必須とする。Skill数が異なる場合でも両revisionで評価可能な共通成果物・criterionは比較対象に残す。片方に必要なSkillが存在しない工程は未評価範囲として明示し、品質FAILや`evaluator_incompatible`へ読み替えない。固定scenarioの必須成果物が揃わず完了できない場合は、比較可能な部分とworkflow全体の未完了を区別して報告する。一方、**候補Skill package内のproduction verifier / generator / assetsのSHAは一致を要求しない**。候補revisionごとのsource fingerprintをprovenanceへ保存し、候補それぞれのsourceで隔離再実行して鮮度・結果再現性を検証する。互換な実装変更は比較可能とし、schema / 機械契約が固定Evaluatorと非互換な部分のみ`evaluator_incompatible`とする。観測できないmodel/backend更新や使用状況は制約として明記し、原因をSkill差分だけに帰属させない。

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

1. 親Planのフェーズ1を完了し、固定Evaluator revision、候補Skill revision、Agent / Judge実行profileと情報隔離のpreflightを確認する
2. trackedな`qa-training-store-checkout-payment-web-v1` scenario定義を確定しfingerprintを算出する
3. `qa-training-store`の固定revision `84ce165493649550832731a60cf436f8ae29c56b` のtracked contentからsanitized targetを準備する
4. 対象revisionの`docs/spec/README.md`と`docs/spec/features/checkout-and-payment.md`が存在することを確認する
5. 元repoのAgent Skill、過去run / Plan / report、instructor情報、target側Skill eval等を除外する
6. 元`docs/PROJECT_CONTEXT.md`を除外し、正規stable keyを持つ評価用`AGENTS.md`と評価用`docs/PROJECT_CONTEXT.md`を生成・検証する
7. 候補`qa-workflow-skills` revisionのSkill集合を`.agents/skills/`へ配置する
8. sanitized targetをfresh Git repositoryにし、Evaluator-owned synthetic baseline commitを作成する
9. `.qa-eval-output/`を作成し、Checkout / Payment評価要求、`artifact-index.json`の`artifacts[]` / `routing[]`契約、Agentの必須`timeout_seconds` / Judgeの独立Docker profile・timeout条件をrun provenanceへ記録する
10. 各repeatの新規target / Agent sessionで実Agentを起動し、分析・設計workflowを実行する。使用証拠の観測可否を記録する
11. 読み取り専用mountでProduct Code / Test / Spec / Skill / 評価用設定の書込みを拒否したことを検証し、終了後にtracked / untracked / ignoredを含むbaselineとの差分・追加commitを確認する
12. 固定scenarioの要求結果を基準に`artifact-index.json`の`routing[]`・`artifacts[]`を既存Skill条件と実fileに照合する。QA成果物・runtime証拠・内部fileを分類した`artifact-manifest.json`を作り、routing登録不足・分類不能と実際の未生成を区別して回収する
13. 固定要求とrouting判断・成果物を照合し、条件付き省略の正当性を検証して、捕捉済みartifact・request / result / invocationを対応付ける。候補tracked source版verifierをネットワークなしの別Docker内で再実行し、固定Evaluatorの`common_runtime_checks.py`で独立機械判定する
14. 固定Judgeを**2回独立に実行**する。`QTS-SEM-001/002`には正規QA成果物・`routing[]`・最終stdout・機械判定要約、`QTS-SEM-003..010`には正規QA成果物のみ（欠落表示を含む）を渡す。各Judge応答を対応criterion集合で検証し、結合結果を既存normalizerで全体判定する。各呼び出しのtimeout・子孫終了・追加tool排除を確認する
15. workflow / traceability / semantic結果とprovenanceを同じrunへ保存する
16. runner / environment起因の失敗、Skill品質上のnon-pass、`evidence_unverified`、隔離・実効設定未確認、部分的Evaluator非互換を分けて報告する。必須証拠が未確認ならsemantic passでもattempt `needs_review` / exit 1、Runner障害ならexit 2とする。Skillの内部使用ログだけが`unverified`なら成果物品質比較を妨げない
17. **初回runの実QA成果物**から分析Agentが固定仕様・rubricに基づく安全化された評価根拠を使って原因を分析し、修正可否を機械的に判定する。条件を満たす品質問題を1件以上選ぶ。**Evaluator-onlyの人工的な違反fixture、故意に劣化させたSkill、Judge誤判定や実行環境問題は対象にしない**。修正前Skillを同条件で2attempt以上評価し、問題と根拠を確定する
18. 親Plan「実際のSkill改善と再評価の受入検証」および改善Planに従い、**自動修正条件を満たす案件だけ修正Agentが隔離した候補Skillを最小変更**し、候補revision・patch・検証結果を保存する。条件不足・原因不明・高リスクの案件はレビュー待ちに残す。固定target / Evaluator / scenario / Judge条件は変更しない。候補変更を本PRへ自動採用・pushしない
19. 変更後の候補Skillで同条件の実Agent評価を2attempt以上実行し、各criterion・固定機械品質・runtime証拠・Skillの実使用・他の重要観点の回帰を比較する。機械的な検証条件と固定Evaluatorの判定で実質的改善が確認されたときのみ検証済み候補として保存し、最終採用は人間が決める。確認できなければ**改善実証は未達**として証拠と理由を報告する

## 完了条件

評価結果の自動分析・限定したSkill修正・再評価・レビュー待ちの受入条件は[改善Plan](./2026-10-03_132700_agent-eval-runner_03_analysis-and-improvement.md)に従います。評価結果から原因を確定できない案件をSkill品質FAILや自動修正に変換しません。

次をすべて満たしたらフェーズ2初回評価を完了とします。

- テスト対象が`qa-training-store`であることをrun結果から特定できる
- source revisionが`84ce165493649550832731a60cf436f8ae29c56b`として固定・記録される
- 評価対象`qa-workflow-skills` revisionが記録される
- Agent-visibleなSkill集合が候補revisionから検出したSkill集合に限定され、その他のuser/global Skill・指示・MCPの混入がない条件を検証・記録する
- 元`.agents/**` / `.codex/**`、`AGENTS.md` / `QA_AGENT.md`によるrepo固有Skill routing・Codex設定・hooks等が評価対象Agentへ残っていない
- 過去run / Plan / report、instructor情報、元`docs/PROJECT_CONTEXT.md`、target側Skill eval、`qa-workflow-skills`のReference / expected / rubric / graderが評価対象Agentへ公開されていないことをアクセス制御と実Agentで確認する
- 評価用`AGENTS.md`と`docs/PROJECT_CONTEXT.md`が評価条件と必要なstable keyだけを持ち、製品仕様や正解QA成果物を追加せず、既存Project Context parserが受け付ける
- 候補revisionの全Skillが`.agents/skills/`へ配置され、各Skillの`evals/**`が含まれていない
- Agent開始前のsanitized targetがEvaluator-owned synthetic baseline commitとして固定され、original Git history / remoteを引き継いでいない
- scenario ID / scenario fingerprint、Evaluator / Skill revision、実効Agent / Judge profileと検証状態、隔離条件、Judge Reference fingerprintがrun provenanceへ保存される
- Checkout / PaymentのWeb範囲で実Agent workflowが最後まで実行され、`--repeat`各attemptの独立した評価結果が保存される
- Product Code、既存Product Test、規範仕様、配置Skillと評価用設定を実行中読み取り専用mountで保護し、権限拒否を確認する。終了後の照合ではignored / untracked fileも許可外変更を見逃さない
- `artifact-index.json`の`routing[]`（skill / scope / status / reason / artifact_ids）と`artifacts[]`（skill / kind / scope / artifact_id / path）をEvaluatorが固定scenario・既存Skill契約・実fileと照合し、必須行欠落・不正な省略・blocked / incomplete・重複・cross-attempt混入を識別できる。fake Agentの`executed` / `reused` / `skipped` / `blocked` / `incomplete`、条件付き`question-analysis`、登録漏れと実際の未生成を検証する。`artifact-manifest.json`でSkill名 / path / SHA-256 / runtime証拠との一意対応と3分類を追跡し、未生成と分類不能を区別できる。Judgeの正規QA成果物部分には`qa_artifact`のみを固定順で使う
- 評価用capture CLIで実際のproduction verifier request bytes / result bytes / exit codeを保存し、候補sourceを読み取り専用・ネットワーク遮断の別Dockerで独立再実行できる。固定Evaluatorの`common_runtime_checks.py`は候補`valid`に依存せず、不正ID・依存・graph・completionを検出でき、実装fingerprintだけの互換差は許容する
- runtime実装または候補production verifierのSHAだけが変わり、schema・機械契約は互換な2 revisionを**比較器が`not_comparable`にしない**。候補sourceごとに鮮度と再現性を確認し、schema非互換は該当する項目だけ`evaluator_incompatible`として記録して固定Judgeの意味評価を残す
- verifier証拠の欠落を`evidence_unverified`とし、未観測のverifier未実行をSkill品質FAILと断定しない。capture実装自体のエラーはrunner / environment errorへ分類する
- `qa-workflow`の`workflow_runtime.py`も保存済み入力から再実行できる
- 生成成果物がrun artifactとして保存される
- workflow結果と、Skill package投入の検証済み証拠および変更対象Skillの内部読取観測（`observed` / `unverified`）を独立して保存する。内部観測不能でも同じ条件での**成果物品質比較**はできるが、**Skill改修効果**は判断不能とする。複数attemptで結果が矛盾する場合も改善・悪化・変化なしと断定しない
- **フェーズ2の実際の品質問題を分析Agentが分析し、機械的な許可条件を満たす案件について修正AgentがSkillを1件以上修正した候補revision**について、baseline / candidateを各2attempt以上で同条件評価し、特定の重要criterionまたは機械品質の実質的改善・重要観点に回帰がないこと・Skill実使用証拠を確認できる。改善が確認できない場合は、ランナー機能の成立と**実改善の実証未達**を区別して報告し、実証済みとは扱わない
- traceability / runtimeの機械判定結果が保存される
- Judge評価用の正解データをAIが作成・修正提案できる一方、確認済みの期待判定を変更するには独立の確認が必要である。未検証criterionのJudge判定から自動Skill修正を開始しない
- `QTS-SEM-001..010`の固定criterion ID / critical / Reference対応により独立Judgeを検証する。`QTS-SEM-001/002`と`QTS-SEM-003..010`を**別prompt・別process**で採点し、後者には`routing[]`・最終stdout・機械判定要約が一切含まれないことを検査する。2応答のID集合と結合後の全10件を検証し、誤ID・重複・一方のtimeout / 不正応答では全体PASSにしない。正常例・Payment整合違反例・仕様外動作例に加え、**未検証のcritical 7件それぞれの重大違反例**で期待rating・Reference根拠・Judge evidenceを確認する
- runner / environment errorとSkill品質のneeds_review / failを区別できる
- 非pass結果を隠さず保存・報告できる
- 比較条件が異なるrunと、隔離・実効設定が未確認のrunをSkill変更のみの直接比較に使わない。`agent.timeout_seconds`も一致条件とし、`--repeat 1`の結果だけでLLM品質改善の傾向を断定しない
- target-specific評価のためにSkill本体へ`qa-training-store`固有処理を追加していない

### runtime契約を変更した候補の比較

候補Skillの`runtime_contract.py` / generatorに変更がある場合も、正常なimplementation fingerprint差だけで機械評価をFAILにしない。候補verifier自身の鮮度照合に失敗した場合はその実行の問題として記録し、共通品質graderの評価とは別に扱う。

schemaやEntity表現が変更され、既存Evaluatorでは判定不能な場合は該当criteriaのみ比較不可にする。必要ならEvaluatorを両revision対応へ更新し、Evaluator SHA・rubric・Referenceを固定して旧版と新版を**両方新規実行・再採点**する。変更前の旧採点結果だけを流用しない。新たなschemaの自動変換・汎用互換性frameworkは実装しない。

### Judgeの検出能力の受入検証

Judge基準・正解データの作成と継続改善の詳細は[Judge評価・改善Plan](./2026-10-03_132700_agent-eval-runner_04_judge-evaluation-and-improvement.md)を正本とする。フェーズ2のfixtureは確認済み事例として再利用し、調整用と独立検証用の役割を区別する。Judgeの該当criterionが未検証なら、Skillの品質結果は保存してもSkill自動修正へ進めずレビュー待ちにする。

固定target revisionの正常なQA成果物を基準に、**Evaluator-only fixture**でJudgeの検出能力を確認する。従来の正常例、`QTS-SEM-006`のPayment整合違反例、`QTS-SEM-010`の仕様外動作例を維持し、未検証の**critical 7件**に対する代表的な重大違反例を追加する。

| 対象criterion | 重大違反fixtureで変更する内容 |
|---|---|
| `QTS-SEM-001` | 必須の分析・設計工程を、要求に反する根拠のない理由でroutingから除外し、workflowの意味的な成立を損なう |
| `QTS-SEM-002` | 重要な未解決・未閉鎖事項が残るのに、最終回答でworkflow完了と宣言する |
| `QTS-SEM-003` | `unresolved-specifications.md`等の未確定事項を正式なOracleへ昇格させ、重大な誤期待値を作る |
| `QTS-SEM-004` | Checkout Sessionの再開・置換・24時間期限切れのうち、主要な条件を誤るか重要なテスト条件を欠落させる |
| `QTS-SEM-005` | stale Cart Versionまたは価格不一致でも、Order / Paymentを確定してよいとする |
| `QTS-SEM-007` | Payment processing中のretry / cancel禁止やresume条件に反する操作を許容する |
| `QTS-SEM-009` | IDとedgeは形式上正しいまま、Authorityと下流TCを**別の要求の意味**で結び付け、重大なtraceability不整合を発生させる |

- 正常例を基礎に**対象の誤りだけ**を加える。入力は実際のAgent-visible targetへ配置せず、Evaluatorだけが参照する。各fixtureに対象criterion、変更箇所、期待rating、期待evidence、規範Referenceの該当箇所とその根拠を保存する。**Agentはfixture・期待判定・rubric / Referenceの初期案や改善案を作ってよい**。ただし期待判定を正解として使うには、人間による規範仕様・Skill契約との照合、または当該事実を直接確定できる決定論的検証が必要であり、Judge自身の判定を正解にしない。
- `001/002`ではworkflow Judgeへ、`003/004/005/007/009`ではQA成果物Judgeへ、該当入力区分の違反だけを渡す。既存の**2系統のJudge入力分離・全10件統合判定**の契約は維持する。各fixtureの意味評価では対象criterionを含むJudge呼び出しを中心に実行でき、配線・統合の検証まで目的なく両Judgeを毎回起動する必要はない。
- 重大違反fixtureは、**形式的なID欠落やmachine-onlyな失敗を加えただけの例にしない**。Judgeが意味上の違反を判別できる内容にする。`001/002`ではrouting判断・最終宣言と規範 / 正規成果物の矛盾を確認し、`009`では固定機械判定が構造上PASSし得る状態の意味的な誤対応を確認する。
- 正常fixtureは全criterionがrating 3以上、重大違反fixtureは**対象critical criterionがrating 1**、全体の期待判定は既存`result.py`により`fail`とする。`evaluable=false`やrating 2 / 3で重大な違反を救済した結果は受入成功としない。`QTS-SEM-008`（noncritical）の違反fixtureはこの拡充の対象外とし、通常の評価は継続する。
- **最終回答だけが正しく、正規QA成果物のPayment失敗条件が誤っているfixture**でも、`QTS-SEM-006`の成果物Judgeが最終回答で救済されないことを確認する。各fixtureで実際のJudge rating / reason / evidenceを記録し、人間確認済みの根拠と照合する。Judgeの判定が一致しない・繰り返しで重要判定が揺れる場合は、判定根拠とrubric / Referenceを調査して受入を保留する。
- AIが作成したJudge基準・fixture・期待判定の候補は、確認済みの正解データと混同せず、根拠と確認状態を記録する。Judge改善時は独立検証用事例でも回帰がないかを確認し、人間が正式採用する
- fixtureの読込み、対象criterionへの配線、結果正規化・統合は**外部LLMを呼ばないfake Judge / fake Agentの通常CI**で確認する。実際のJudgeの意味判別は既存の**実Codex smoke / Judge受入検証**で確認する。必要な修正でJudge prompt・rubric・Reference等のEvaluator基準を変更した場合は新Evaluator revisionとして固定し、旧・新Skillを同一条件で再評価する。Judgeの自動採用・自動学習基盤、新規採点式、DB、常時LLM CIは追加しない。Judgeの検証と改善候補の作成・再検証はJudge評価・改善Planで扱う。


実際のSkill修正・再評価の詳細な手順と判定条件は、親Planの「実際のSkill改善と再評価の受入検証」および改善Planを正本とする。根拠が十分な案件の隔離修正と再評価は自動化するが、改善結果の自動採用、採点基準の緩和は行わない。

## このフェーズで追加しないもの

- Native評価
- 実ブラウザ実行を伴うE2E評価
- Black-box Scored Challengeとの統合
- `qa-training-store`既存Harnessの再実装
- 複数target repo対応のplugin framework
- 安全条件を満たさない案件の自動修正・無制限な修正反復
- Skill自動採用
- baseline / candidateの自動ランキング
- 外部LLMを使う通常CI

実行系Skillの実環境評価、baseline / candidateの自動ランキング、複数target repo対応は今回追加しません。保存済みrunの条件照合、自動分析、条件付きのSkill修正と再評価、レビュー待ちへの振分けは、改善Planに従い今回の実装範囲に含みます。
