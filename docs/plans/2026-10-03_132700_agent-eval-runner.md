# 実Agent評価ランナー実装Plan

このPlanは、既存のAgent Skills評価データセットを使って実Agentから評価対象成果物を生成し、現在の決定論的出力評価・意味評価まで一括で実行できる開発用ランナーを追加し、その後に固定テスト対象 `qa-training-store` で実Agent統合評価まで行うための実装計画です。

Skill本体の実行基盤は変更しません。Codex、Claude Code等のAgent runtimeは各クライアントへ任せ、今回追加するランナーはリポジトリ開発時の評価だけを担当します。固定テスト対象での評価もSkill本体へ対象repo固有処理を入れず、評価側から実行します。

## 対象ブランチ

`feat/agent-eval-runner`

## 基準

- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- 基準branch: `main`
- 基準commit: `dec3f7c764db2869dc24eb3d6f154712a6677068`
- 正規Skill数: 19
- trigger dataset: 428 query
- deterministic output dataset: 38 case
- semantic dataset: 72 case
- `qa-workflow` routing fixture: 61件

現在の評価契約では、決定論的出力評価と意味評価はいずれも保存済みの評価対象出力を評価し、Agent実行と評価対象出力の生成は責務外です。

PR #11の検証では`codex exec`で評価対象成果物を生成し、既存の`semantic/run.py`へ渡して外部Judgeで評価した実績があります。ただし、評価対象成果物の生成は一時batch scriptで行っており、現在のリポジトリには共通の実Agent実行ランナーがありません。

## 目的

### 最終目的

このPlanの最終目的は、`qa-workflow-skills`を変更したときに、単発の手動確認や印象ではなく、**同じ条件で実Agent評価を再実行し、変更前後のSkill品質の改善・悪化・変化なしを根拠付きで確認できる状態を作ること**です。

今回作るものはSkillを実行する新しいAgent runtimeではありません。Codex、Claude Code等が持つAgent runtimeをそのまま使い、`qa-workflow-skills`側にはQA Skillの評価に必要な最小の実行・記録経路だけを追加します。

また、現在すでに存在するdeterministic / semantic / trigger / routing / runtime評価を置き換えません。今回不足している「実Agentで評価対象成果物を生成する前段」と「同じ条件で再評価できる記録」を追加し、既存評価へ接続します。

完成後は、少なくとも次の改善ループを同じ仕組みで繰り返せる状態にします。

```text
現在のSkill
  ↓
固定した評価条件で実Agent実行
  ↓
既存評価 + 固定テスト対象評価
  ↓
結果と失敗根拠を保存
  ↓
Skillを修正
  ↓
同じ評価条件で再実行
  ↓
変更前後を比較して改善判断
```

自動A/BランキングやSkillの自動書き換え・自動採用は今回作りません。比較に必要な実行条件と評価結果を保存し、人間または別Agentが**条件の一致を検証できたrun同士**を比較できる状態までを今回の目的に含めます。対象は明示的なSkill利用による既存Eval Inputの出力品質と、固定repo上の分析・設計workflow品質です。19 Skillすべての実環境動作、ブラウザE2E、native Skill trigger精度まで測定できたとは扱いません。

### フェーズ1で実現すること

既存Eval Inputを使い、次の一連の処理を1つの共通経路から再現可能に実行できるようにします。

```text
既存Eval Input
  ↓
実Agentを独立プロセスで実行
  ↓
評価対象成果物を保存
  ↓
既存deterministic / semantic evalを実行
  ↓
ケース別結果と実行全体の結果を保存
```

Skillを変更した後に同じ評価ケースを実Agentで再実行し、既存評価基準で結果を確認できるようにします。

### フェーズ2で実現すること

固定revisionの`qa-training-store`を実際のテスト対象として、`qa-workflow-skills`の複数Skillを使う分析・設計workflowを実Agentで動かします。

単一SkillのEval Inputだけでは確認できない、次を評価できる状態にします。

- 実repoから正しい仕様根拠を選べるか
- `qa-workflow`が必要な工程だけを適切にroutingできるか
- 複数Skillの成果物chainが追跡可能な状態で閉じるか
- stable ID / runtime evidence / currentness等の既存契約を維持できるか
- 規範仕様にない期待動作を追加しないか
- 同じtarget revisionと評価要求でSkill修正前後を再評価できるか

### このPlanのレビューで維持する前提

今後別セッションでPlanをレビュー・修正する場合も、次はこのPlanの目的上の前提として維持します。

- Agent loop、context管理、sandbox、subagent等はCodex / Claude Code等のruntimeへ任せ、独自Agent runtimeを作らない
- 既存deterministic / semantic graderを再実装しない
- Skill本体から評価ランナーへ依存させない
- Codex固有実装をSkill契約へ入れず、Agent commandは外部から注入する
- 評価対象AgentへReference / expected / rubric / grader等の評価正解情報を公開しない
- `qa-training-store`固有処理をSkill本体へ入れない
- 現在必要な1つの固定targetを評価するためだけに、汎用plugin framework、DB、MCP、LangGraph等を追加しない
- 自動Skill修正・自動採用は行わず、評価結果から改善候補を作成し、修正後に同条件で再評価できるところまでを対象とする
- `description`による実Agent上のnative Skill発火評価は、クライアント固有の観測が必要なため今回の出力品質・workflow評価とは分離する。既存trigger datasetは維持し、今回のPlanだけでlive trigger最適化まで達成したとは扱わない

## フェーズ構成

### フェーズ1: 既存Eval Inputで実Agent生成を自動化する

本Plan本文の共通ランナーを実装し、既存deterministic / semantic caseを実Agentで生成して現在のgraderへ接続します。

ここでは新しい評価基準を作らず、既存の評価データセットとgraderを再利用します。

### フェーズ2: qa-training-storeを固定テスト対象として評価する

フェーズ1完了後、`ryu-yoshikawa-pro-vision/qa-training-store`を固定revisionで使い、実repoを入力にした分析・設計workflowを評価します。

詳細は [`qa-training-store固定対象の実Agent統合評価Plan`](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md) を正本とします。

初回対象は次で固定します。

- target repo: `ryu-yoshikawa-pro-vision/qa-training-store`
- target revision: `84ce165493649550832731a60cf436f8ae29c56b`
- Platform: Web
- Feature: Checkout / Payment

フェーズ2は新しい汎用benchmark frameworkを作るものではありません。まず1つの固定repo・固定revision・固定Featureで実行し、追加の抽象化が必要かは実測後に判断します。

## 現在確認できている不足

### 1. 評価対象成果物の生成が共通化されていない

`scripts/skills/evals/deterministic/run.py`と`scripts/skills/evals/semantic/run.py`は保存済み出力を受け取ります。

一方、実AgentへEval Inputを渡し、出力を所定の場所へ保存する共通処理はありません。

### 2. 実Agent実行と既存評価を一括で回せない

現在は次を個別に行う必要があります。

1. Agentへ評価ケースを渡す
2. 最終出力を保存する
3. deterministicまたはsemantic evalを起動する
4. 結果を収集する

同じSkillを繰り返し改善する場合、この手作業が評価の再現性と実行量の妨げになります。

### 3. 評価対象Agentから評価用正解情報を隔離する共通処理がない

`skills/<skill>/evals/`には次が存在します。

- deterministicの`expected.json`
- semanticの`reference.md`
- semanticの`rubric.json`
- validator

リポジトリrootをそのままAgentの作業ディレクトリにすると、Agentがこれらを検索・参照できてしまいます。

評価対象Agentへ渡す情報と、評価側だけが使う情報を物理的に分離する必要があります。

## 設計方針

### 1. Skill本体からランナーへ依存させない

依存方向は次に固定します。

```text
実Agent評価ランナー
  ↓
Skill Package
  ↓
Skill-local scripts
```

次は禁止します。

```text
SKILL.md
  ↓
実Agent評価ランナー
```

`SKILL.md`、`references/`、`scripts/`、`assets/`の通常実行契約へ、今回の評価ランナー固有のcommand、path、状態を追加しません。

### 2. Agentクライアント固有処理を実装しない

ランナーは特定AgentのSDKやCLIをimportしません。

実Agentとは次の外部command契約だけで接続します。Agent subprocessの`cwd`はフェーズ1ではSkill-only workspace、フェーズ2ではsanitized targetに固定します。ただし`cwd`自体に情報の読み取り制限はありません。隔離は後述の実行条件で保証します。

```text
stdin:  Agentへ渡す評価用prompt UTF-8
stdout: Agentの最終成果物のみ UTF-8
stderr: Agentの進行・診断ログを許可
exit 0: Agent実行成功
non-zero: Agent実行失敗
```

commandはargvとして受け取り、`shell=True`を使いません。

Codex、Claude Code等の起動方法はランナーの実装へ固定しません。

OpenAI公式のCodex eval例でも、`codex exec`は自動実行向けに最終結果をstdout、進行をstderrへ出す用途として案内されています。この性質を利用できますが、Codex固有flagはランナーへ埋め込みません。

参考:
- https://developers.openai.com/blog/eval-skills

### 3. 出力品質評価とSkill発火評価を分離する

今回のランナーは、対象Skillを明示して出力品質を評価します。

生成promptでは対象Skill名と一時実行ディレクトリ内の`skills/<skill>/SKILL.md`を明示し、そのSkillを使用するよう指示します。

これは`description`による自動発火を評価するものではありません。

既存のtrigger datasetと、実Agent上でのnative Skill発火評価は別契約として維持します。AgentクライアントごとのSkill読み込み観測を今回の共通ランナーへ混ぜません。

### 4. 評価用正解情報をAgentから隔離する

各Agent実行前に一時実行ディレクトリを作成します。

一時実行ディレクトリへは、現在branchの19 Skillから通常実行に必要なファイルだけをコピーします。

コピー対象:

```text
skills/<skill>/SKILL.md
skills/<skill>/references/**
skills/<skill>/scripts/**
skills/<skill>/assets/**
```

コピーしないもの:

```text
skills/<skill>/evals/**
scripts/skills/evals/**
docs/**
.git/**
```

19 Skillすべての通常Skill Packageを配置し、`qa-workflow`等が他Skill名を前提にする場合も通常構成を維持します。配置元はworking treeではなく、明示した`--skill-revision`のGit treeのtracked contentだけとします。

Eval Inputはファイルとして一時実行ディレクトリへコピーせず、生成promptへ埋め込みます。

Agent-visible workspaceには`reference.md`、`expected.json`、rubric、validatorを配置しません。**このコピー条件だけでは元Evaluatorへのアクセス禁止を保証しない**ため、実行開始前に後述の隔離preflightを満たす必要があります。

### 5. 既存graderを再実装しない

新しいランナー内にdeterministic assertionやsemantic Judgeロジックを複製しません。

- deterministic: 既存`scripts/skills/evals/deterministic/run.py`を使用
- semantic: 既存`scripts/skills/evals/semantic/run.py`を使用

ランナーは、評価対象成果物の生成、保存、既存graderの呼び出し、結果収集だけを担当します。

### 6. 通常CIでは外部LLMを呼ばない

現在の方針を維持し、pull request / pushで自動実行される通常GitHub ActionsからCodex等を呼びません。

CIではfake Agent commandを使って、ランナー自体の契約・一時実行ディレクトリ・grader接続だけを検証します。

実Codex等を使う評価は、開発者が明示的に起動するローカル評価とします。

### 7. 評価対象Skillと採点基準のrevisionを分離する

ランナーと既存graderは**固定Evaluator revision**のcleanなcheckoutから実行する。評価対象のSkill packageだけは別の`--skill-revision <40文字Git SHA>`で選択する。

1. Evaluator側の`HEAD`、working tree・indexがcleanであることをlive runのpreflightで検証し、Evaluator SHAを保存する。dirty状態では実行しない。
2. `--skill-revision`で指したGit commitのtracked contentを`git archive`等で取得し、19 Skillの`SKILL.md` / `references/**` / `scripts/**` / `assets/**`だけを配置する。未コミット変更、候補側`evals/**`、Evaluatorのworking treeのSkillを混ぜない。
3. 配置した各Skill fileの相対path / size / SHA-256からmanifestとSkill package fingerprintを生成し、指定Git treeとの一致を検証する。存在しないcommitや不一致はAgent実行前のerrorにする。
4. deterministic graderは固定Evaluator側`scripts/skills/evals/deterministic/run.py`と`skills/*/evals/deterministic/validator.py`を使用する。semantic grader、Reference、rubric、Judge prompt / response正規化、および独立判定に使うproduction verifierも固定Evaluator側の実装を使う。
5. Evaluator SHA、graderの内容fingerprint、dataset / rubric / Referenceのfingerprintをprovenanceへ保存する。候補Skill側のeval実装を採点側へimportしない。

Skill-local verifierはSkill本体にも含まれるため、Agentが候補版で実行したinput / resultも実行証拠として保存する。**独立した評価では固定Evaluator版verifierを再実行**し、候補版だけの`valid=true`を採点に使わない。固定版と候補成果物の契約が互換でなく判定不能なら`evaluator_incompatible`として比較不可にする。

main / candidate比較は、**同じEvaluator checkoutを起動したまま**`--skill-revision`だけを変更して2 runを生成する。checkout全体を入れ替えてgraderが変わる方式を採らない。

### 8. Agent / Judgeの実効実行条件を固定する

Live CLIへ`--execution-profile <path/to/execution-profile.json>`を必須追加する。これはEvaluator側にのみ置く**秘密を含まないJSON**で、比較に影響する実効設定とその確認状態を保持する。fake Agentテストでは固定fixtureを使う。

最低限、次を記録する。

- `schema_version`、Agent名・model・CLI version、推論設定、実行オプション、sandbox / approval / networkの方針
- Agentが利用できるSkill・tool・MCPの集合、user/globalの設定・指示の扱い、読み取り可能なmount・ファイル範囲、隔離方式
- 候補Agentと独立Judgeそれぞれの非秘密の起動設定fingerprint、Judge model / version / 推論・tool・指示条件
- 実効設定の照合方法、根拠への相対path、検証状態（`verified`または`unverified`）。提供側のmodel更新等を確認できなければ不確実性として記載する。

`--agent-name` / `--agent-model`とprofileの宣言を照合し、実際のlauncher / CLIで観測できる設定と矛盾した場合は停止する。汎用subprocessだけでuser/global config等を完全に解析できると仮定しない。profileの自己申告だけで`verified`にせず、確認根拠がなければ結果は保存しても`not_comparable`とする。比較対象runではprofileの非秘密fingerprintと実効設定検証結果を一致させる。

環境変数、secret実値、認証用argv、設定ファイルの秘密は保存もhash化もしない。生argvに秘密を含めず、Agent別SDKや新たなAgent config parserは作らない。Judgeは生成とは別process / 別prompt / 別sessionで起動する。フェーズ1で同じAgent commandをJudgeに使う場合もJudge側の実効条件を独立して記録する。

### 9. 正解情報の読み取り隔離を確認する

EvaluatorとAgentの間に、ディレクトリ分割だけでなく**OS等による実効読み取り禁止境界**を設ける。Agent subprocessの`cwd`だけでは成立しない。

- Agentが利用できるファイル・mount・tool / MCP・ネットワーク経路に、Evaluator原本のexpected、Reference、rubric、grader、結果、元target checkoutを公開しない。既存OSアクセス権、隔離コンテナ・VM等で制限し、独自sandboxは実装しない。
- user/global指示・設定・Skill・MCPを固定された評価条件以外から混入させない。認証情報は必要最小限の別経路で渡し、provenanceに書かない。
- preflightではEvaluator-only領域の**非秘密sentinel**を、Agentと同一権限・mount・tool構成から読めないことを確認する。fake Agentはrunnerの失敗時動作を検査し、実Codex smokeでは実際の読み取り拒否と余分な設定の混入防止を確認する。
- 拒否境界や実効設定を確認できないrunは`isolation_unverified`として保持しても、比較可能な品質評価にはしない。stderr等は秘密混入を想定し、出力上限・安全化を行い、安全なログとして保存できない生内容は保存しない。

### 10. Skillの実使用を確認できた範囲で記録する

Skill pathをpromptで指定しても実際に`SKILL.md`等を読んだ証拠にはならない。Agentクライアントのtrace / tool log等で読み取りを観測できた場合のみ、Skill名・file path・証拠相対pathを`observed`として記録し、それ以外は`unverified`とする。観測不能なSkillについても生成成果物の品質判定は保持するが、結果の変化をSkill修正の効果と断言しない。native `description` trigger精度の評価や専用adapterの追加はしない。

## 追加する評価実行コード

### 配置

```text
scripts/skills/evals/agent/
├── __init__.py
├── executor.py
├── run.py
├── prompt_builder.py
├── workspace.py
├── qa_training_store.py
├── target_workspace.py
├── scenarios/
│   └── qa-training-store-checkout-payment-web-v1/
│       ├── scenario.json
│       ├── task.md
│       └── rubric.json
├── README.md
└── tests/
```

`executor.py`だけをフェーズ1 / フェーズ2の共通Agent subprocess境界にします。任意target向けのplugin interfaceは作りません。

### `executor.py`

- 外部Agent commandへUTF-8 promptをstdinで渡し、Agent-visible workspaceを`cwd`に固定する
- stdout / stderr / exit codeを返す
- `shell=True`を使わない
- timeout / process failureを共通のexecution errorへ正規化する
- Agent SDKやCodex固有flagを持たない

### `run.py`

既存Eval Inputを扱うフェーズ1の入口です。

- CLI引数解析
- deterministic / semantic評価ケースの選択
- 固定Evaluator SHAのpreflight、`--skill-revision`のGit treeからSkill-only workspace作成、execution profile / 隔離preflight
- `executor.py`でAgent command実行
- 評価対象成果物保存
- 既存grader起動
- ケース別結果保存
- 全体結果集計
- exit code決定

### `prompt_builder.py`

フェーズ1でAgentへ渡す生成promptだけを構築します。

promptに含めるもの:

- 対象Skill名
- 一時実行ディレクトリ内のSkill path
- 「対象Skillを使用する」という明示指示
- Eval Input全文
- 最終成果物だけを回答する指示

promptに含めないもの:

- `expected.json`
- `reference.md`
- rubric
- validatorの判定内容
- 期待rating / pass条件

### `workspace.py`

フェーズ1用のSkill-only workspaceを作ります。

- `tempfile`で一時実行ディレクトリを作る
- 候補Skill commitのtracked contentから19 Skillの通常実行ファイルだけをコピーし、内容manifestを照合する
- `evals/`を除外する
- Agent実行終了後に一時ディレクトリを削除する

### `qa_training_store.py`

フェーズ2の`qa-training-store`固定対象評価だけを担当します。

- tracked scenario `qa-training-store-checkout-payment-web-v1`を読み込む
- `--target-root`のrevision / clean state、Evaluator / Skill revisionとprofile / 隔離条件をpreflightする
- `target_workspace.py`でsanitized targetを作る
- `executor.py`で実Agentを実行する
- `.qa-eval-output/`から複数成果物を回収する
- artifact manifestを作る
- 候補側production runtime証拠と固定Evaluator側verifierの独立判定、成果物との対応・completionを確認する
- 既存semantic評価のprompt構築 / result正規化処理を再利用して独立Judgeを実行する
- provenanceと評価結果を保存する

### `target_workspace.py`

フェーズ2の固定target preparationだけを担当します。

- 指定された`qa-training-store` source revisionのtracked contentだけからsanitized targetを作る
- target固有`.agents/**` / `.codex/**`、過去Plan / report、instructor情報、target側Skill evalを除外する
- 評価用`AGENTS.md`と、元repoの運用指示を含まない評価用`docs/PROJECT_CONTEXT.md`を生成する
- 19 SkillだけをAgent-visibleに配置する
- `.qa-eval-output/`と必要な評価用Project Context rootを準備する
- Agent終了後にsource差分・symlink / path境界を検証する
- 回収後にsanitized targetを削除する

### tracked scenario

`scenarios/qa-training-store-checkout-payment-web-v1/`は、フェーズ2初回評価を同条件で再実行するためのEvaluator側fixtureです。

- `scenario.json`: target repo / revision、Platform、Feature、除外対象、参照する規範仕様path等
- `task.md`: Agentへ渡す固定評価要求
- `rubric.json`: workflow / 仕様根拠 / 分析設計 / traceability / 根拠のない追加を評価するcriteria

これらはEvaluator側にのみ存在します。`rubric.json`は評価対象Agentへ渡しません。`task.md`には期待するQA成果物の正解を含めません。

新しいsandbox実装は作りません。OS process / filesystem isolationはAgentクライアント側のsandboxを使用します。

## CLI契約

### 単一deterministic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

### 単一semantic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--agent-command`はCLIの最後に置き、後続値をそのままargvとして扱います。live実行では`--skill-revision`に存在するfull commit SHA、`--execution-profile`にEvaluator-onlyの非秘密設定JSONを指定します。`--agent-name` / `--agent-model`はprofileと実効設定照合結果に一致する必要があります。既存semantic CLIの`--judge-command`と同じ方式にします。

### Skill単位batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--eval-id`省略時は、指定Skillの対象suiteに定義された全caseを実行します。

### 全Skill batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill all \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --output-root .agent-eval-runs/run-001 \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--skill all`は明示指定時だけ許可します。既定で全38 / 72 caseを外部LLMへ送信しません。

### 複数回実行

`--repeat N`を任意指定できるようにし、既定は1とします。

同一caseを複数回実行した場合も独自の平均点は作りません。attemptごとの既存eval結果と、pass / needs_review / fail / execution errorの件数だけを集計します。

### 実Agent metadata

実Agentを起動するcommandでは、`--agent-command`より前に少なくとも次を明示します。

```text
--agent-name <agent name>
--agent-model <model identifier>
```

`--agent-version`は任意です。安全に取得できる場合だけ指定または記録します。

### qa-training-store固定scenario

フェーズ2は同じ`executor.py`を使いますが、既存Eval datasetとは別入口にします。`--repeat N`（既定1）を受け付け、各attemptで独立したsanitized target / Agent session / verifier / Judgeを使用します。

```bash
python scripts/skills/evals/agent/qa_training_store.py \
  --scenario qa-training-store-checkout-payment-web-v1 \
  --skill-revision <40-char-skill-commit> \
  --execution-profile path/to/execution-profile.json \
  --repeat 2 \
  --target-root ../qa-training-store-eval-target \
  --output-root .agent-eval-runs/qa-training-store-baseline \
  --agent-name <agent name> \
  --agent-model <model identifier> \
  --agent-command <agent command argv...>
```

`--target-root`は指定revisionをcheckoutしたcleanなGit working treeを要求します。Evaluator checkoutもcleanで、skill packageは別の`--skill-revision`のtracked contentから配置します。Evaluatorはそのworking treeを直接変更せず、指定revisionのtracked contentからsanitized targetを作ります。

この入口は`qa-training-store`の初回scenario専用です。任意repoを動的に登録するplugin機構は作りません。

## semantic評価時のAgent command

v1では、生成に使用した`--agent-command`を、別プロセス・別promptでsemantic Judgeにも使用します。ただしJudgeはEvaluator側で実行し、Agent-visible workspaceの権限・cwd・設定を無条件に継承させません。生成とJudgeの実効条件をprofile内で分け、Judgeに渡すReference / rubricが生成側に読めないことを確認します。

処理は次の2回の独立実行です。

```text
Agent invocation 1
  Eval Input + target Skill
  ↓
評価対象成果物

Agent invocation 2
  既存semantic Judge prompt
  ↓
Judge JSON
```

生成側へReference / Rubricを渡しません。

別モデル・別commandをJudgeに使用したい場合は、保存済み成果物に対して既存`scripts/skills/evals/semantic/run.py --judge-command ...`を直接実行できます。

今回のランナーに、2種類の任意commandを同時指定する新しい設定形式は追加しません。実際に別Judgeの一括実行が必要になった場合に追加を検討します。

## 結果保存

`--output-root`配下へ、少なくとも次を保存します。

```text
<output-root>/
├── result.json
└── <suite>/
    └── <skill>/
        └── <eval-id>/
            └── attempt-01/
                ├── output.md
                ├── agent.stderr.log
                ├── grade.json
                └── grader.stderr.log
```

`result.json`には、評価結果に加えて変更前後を同条件で比較できる非秘密のprovenanceを保持します。

最低限、次を保存します。

- suite
- Skill
- eval IDまたはscenario ID
- attempt番号
- 評価対象`qa-workflow-skills` Skill commit SHAと配置したSkill package fingerprint
- 評価基準であるEvaluator commit SHAとgrader / verifier / Judge prompt・dataset / rubric / Referenceのfingerprint
- 評価データセットまたはscenario定義のfingerprint
- 評価入力のfingerprint
- target repoを使う場合はrepository名とsource revision
- Agent名
- Agent model
- Agent / Judgeの非秘密実効設定profile fingerprintと検証結果、隔離preflight結果、Tool / MCP / user-global指示の扱い
- 対象Skillの実使用観測（`observed` / `unverified`）と根拠path
- Agent versionを安全に取得できる場合はそのversion
- semantic評価ではJudgeの実行方式。フェーズ1の既定は「同じAgent commandを別process / 別promptで使用」
- Agent commandのexit code
- graderのexit code
- deterministic statusまたはsemantic verdict
- 各保存fileの相対path
- 実行日時

`--agent-name`と`--agent-model`は実Agent runでcallerが明示し、profileと照合した結果へ保存します。Agent / Judgeの実効構成、隔離の検証根拠、未確認要素も同時に保存します。`--agent-version`はcaller指定または安全に取得できる場合だけ保存します。Agent command全文からmodelやversionを推測しません。

評価データセットのfingerprintは、選択caseの**固定Evaluator revision**にある入力・期待値 / Reference・rubric等、評価判定に影響する内容からEvaluator側で算出します。採点に使うvalidator / prompt builder / result normalizer等のソースはEvaluator SHAと別に内容fingerprintも持ちます。fingerprintだけをrun結果へ保存し、Reference / expected本文をAgent-visible workspaceへコピーしません。

環境変数、認証情報、token、Agent command全体は保存しません。stdout / stderr等の保存対象はサイズ・内容を検査し、秘密を含む可能性のある生ログを無条件に永続化しません。必要な診断が安全に残せない場合はログ欠落理由を記録します。

### 比較可能性の条件

Skill修正前後を比較するときは、少なくとも次が一致するrunを同条件として扱います。

- target repo / target revision、または同じEval case
- 評価入力fingerprint
- 評価データセット / scenario fingerprint
- Agent名 / modelと検証済み実効実行profile（推論設定、CLI version、tools / MCP / 指示、sandbox等）
- 評価側Evaluator SHA・grader / verifier / Judge prompt・rubric / Reference fingerprint
- Judge実効条件とその検証結果
- 情報隔離の成立条件と検証結果
- 実行回数の扱い

比較対象として変えるのはSkill packageのrevisionとその内容fingerprintだけです。EvaluatorのSHAと採点基準は変えません。いずれかの設定が違う、未検証、またはSkill packageが同一なら、Skill変更による改善・悪化とは断定しません。provider側の隠れたmodel更新やSkill読み取りが観測不能な場合も限界を明記します。

今回、比較結果の自動rankingや独自総合scoreは作りません。保存済みrun同士を人間または別Agentが比較できれば目的を満たします。

`.agent-eval-runs/`は`.gitignore`へ追加し、実Agent出力・ログ・Judge結果を通常commit対象にしません。

### 判定結果と比較可否の分離

既存graderの`pass / needs_review / fail`、Agent / grader execution error、および今回の`isolation_unverified` / `not_comparable` / `evaluator_incompatible`は別の軸で記録する。比較不可のrunも診断目的で保存できるが、品質の`pass`を意味しない。フェーズ2の必須artifact・verifier証拠の欠落はAgent処理が正常終了したならSkill品質の非passに分類し、Evaluator自身のpreparation失敗・I/O失敗とは区別する。

Run同士の比較成立確認は**2つの保存済みrunの共通条件の照合**で行い、ファイル名や同じmodel名だけから同条件と判断しない。repeatの各attemptと対象Skill使用観測の状態も比較表示に残す。

## exit code

既存評価ランタイムと意味を揃えます。

```text
0: 選択した全attemptがpass
1: 評価自体は完了したがneeds_review / failが1件以上
2: dataset / workspace / Agent execution / grader execution等の実行エラー
```

Agent commandがnon-zeroの場合、そのattemptではgraderを実行せずexecution errorとして記録します。

batchは途中1件が失敗しても残りcaseを実行し、最後に全体結果を返します。ただし一時実行ディレクトリの作成失敗等、後続caseも実行不能な初期化エラーでは即時終了します。

## 変更対象

### 新規

- `scripts/skills/evals/agent/__init__.py`
- `scripts/skills/evals/agent/executor.py`
- `scripts/skills/evals/agent/run.py`
- `scripts/skills/evals/agent/prompt_builder.py`
- `scripts/skills/evals/agent/workspace.py`
- `scripts/skills/evals/agent/qa_training_store.py`
- `scripts/skills/evals/agent/target_workspace.py`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/scenario.json`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/task.md`
- `scripts/skills/evals/agent/scenarios/qa-training-store-checkout-payment-web-v1/rubric.json`
- `scripts/skills/evals/agent/README.md`
- `scripts/skills/evals/agent/tests/`
- `tests/skills/evals/agent/`

### 更新

- `.gitignore`
  - `.agent-eval-runs/`を追加
- `EVALS.md`
  - 「Agent実行はgraderの責務外」という既存境界を維持したまま、別層の実Agent評価ランナーを追加したことを記載
  - CLI、情報隔離、実Agent評価とtrigger評価の境界を記載
- `README.md`
  - 現在の「Agent実行と評価対象出力の生成は評価ランタイムの責務外」という説明を、deterministic / semantic grader単体の責務として維持
  - 実Agent評価を行う場合の入口として新ランナーを案内
- `docs/PROJECT_CONTEXT.md`
  - 現在の評価・検証欄へ、実Agent評価ランナーの責務と通常CIでは外部LLMを呼ばない境界を追記
- `.github/workflows/deterministic-output-evals.yml`
  - 新ランナーのcompileとfake Agent unit / repository integration testだけを追加
  - 実Codex等は起動しない

`semantic-output-evals.yml`へ外部LLM実行は追加しません。

## テスト

### 共通ランナーunit test

fake Agent subprocessを使って少なくとも次を検証します。

- 固定Evaluator SHAと候補Skill SHAを独立に指定でき、dirty Evaluatorを拒否し、候補Git treeから実ファイルを選択する
- execution profileの必須項目・宣言と実効設定の不一致・検証不能時の比較不可を確認する
- Evaluator-only sentinelのread-denial preflightをfake Agentで検証し、`cwd`変更だけでは合格させない
- Eval Inputがstdin promptへ含まれる
- 対象Skill名とSkill pathがpromptへ含まれる
- Reference / expected / rubricがpromptへ含まれない
- Agent stdoutを`output.md`へUTF-8で保存する
- Agent stderrを診断ログとして保存する
- non-zero exitをexecution errorとして扱う
- `shell=True`を使用しない
- `--agent-command`後続argvを順序どおり渡す
- batchで1件失敗しても残りcaseを継続する
- `--repeat`でattemptを独立保存する
- 異なるSkill revisionを同じ固定graderで採点し、比較条件が異なる結果は`not_comparable`にする
- 秘密を含み得るargv・環境変数・生ログがprovenanceに残らない

### 一時実行ディレクトリtest

- 指定SHAのtracked fileだけがmanifestと一致し、dirty working treeのSkillが混入しない
- 19 Skillの`SKILL.md`が存在する
- `references/` / `scripts/` / `assets/`が存在する場合はコピーされる
- どのSkillにも`evals/`が存在しない
- `scripts/skills/evals/`が存在しない
- `docs/`、`.git/`が存在しない
- 元repositoryのSkill fileを変更しない
- 終了後に一時実行ディレクトリを削除する

### grader接続integration test

repositoryの既存caseを使い、fake Agentで次を自動検証します。

1. deterministic caseを生成し、既存`deterministic/run.py`が実行される
2. semantic caseを生成し、既存`semantic/run.py`が実行される
3. `grade.json`へ既存graderの結果が保存される
4. batch結果が`result.json`へ集計される
5. dataset / input fingerprintとAgent metadataが`result.json`へ保存される

テスト用fake Agentは評価対象ケースの正解ロジックを実装しません。ランナーの配線確認に必要な最小固定応答だけを使用します。

### qa-training-store scenario integration test

外部LLMは起動せず、fake Agentと一時Git repositoryを使って次を検証します。

- source revisionのtracked contentだけからsanitized targetを作る
- 元`docs/PROJECT_CONTEXT.md`を除外し、stable keyを維持する最小Project Contextを生成して既存parser / root解決に通す
- フェーズ2の各`--repeat`で新規target / Agent session / Judgeを作り、前attemptの成果物を再利用しない
- 元`.agents/**` / `.codex/**`、元`AGENTS.md` / `QA_AGENT.md`、過去Plan / report、instructor情報、target側Skill evalをAgent-visible targetへ残さない
- 評価用`AGENTS.md`へ製品仕様や正解QA成果物を混ぜない
- 19 SkillだけをAgent-visibleにする。user/global追加Skill・指示・MCPが有効なrunは比較可能として扱わない
- `.qa-eval-output/**`だけを書込み許可範囲として扱う
- 複数artifactを回収し、相対path / size / SHA-256をmanifestへ保存する
- symlink / path traversal / output root外参照をrejectする
- output root外にsource変更があるrunを有効評価へ昇格しない
- target revision / scenario fingerprint / Skill・Evaluator revision / Judge Reference fingerprint / Agent・Judge profileをprovenanceへ保存する
- artifact / verifier request / result / rerun resultの一意対応、欠落・参照差し替えを検出する
- `valid=false`同士の再実行一致をPASSにしない。`workflow_runtime.py`の実行成功とcompletionを区別する
- 元repoの`docs/PROJECT_CONTEXT.md`等をAgent-visible環境から読み取れないことを実環境の隔離検証で確認する
- cleanup後にsanitized targetが残らない

### 追加の比較・隔離検証

fake Agentで、指定候補SHAの内容と配置manifestの一致、Evaluatorと候補の分離、Judge / grader固定、profile不一致時の拒否、必要な隔離証拠がないrunの比較不可、異なる2つの保存runの比較条件判定を検証する。変更されたSkill packageと同一packageの別Git SHAを区別し、後者を改善検出実績に数えない。

live Codexでは、実効設定の確認とEvaluator-onlyの非秘密sentinel読み取り拒否を含めて検証する。2つの異なるSkill package revisionを同じEvaluator / dataset / profileで実行して比較可能なprovenanceを保存する。実Agentが意図するSkillを読み取ったか観測できない場合はその制約を報告し、成功扱いしない。

## このブランチで行う実Agent検証

実装後、同じ`feat/agent-eval-runner` branch上で実Codexを使ったsmokeを実施します。

実行前にローカル`codex exec --help`で非対話・stdin・sandboxの現在利用可能なflagを確認します。ランナー実装へそのflagを埋め込まず、`--agent-command`へ渡します。

最低限、次の4 caseを実行します。

### 1. `TC-OUT-001`

- suite: deterministic
- Skill: `test-case-design`
- 目的: 単純な正規出力生成 → deterministic grader接続を確認

### 2. `TCN-OUT-001`

- suite: deterministic
- Skill: `test-condition-design`
- 目的: Pairwise制約を含むケースで、Skill指示・Skill-local決定論処理を利用できる状態から生成し、既存validatorで評価できることを確認

### 3. `TC-SEM-001`

- suite: semantic
- Skill: `test-case-design`
- 目的: 実Agent生成 → 独立Judge invocation → semantic verdict保存まで確認

### 4. `WF-SEM-003`

- suite: semantic
- Skill: `qa-workflow`
- 目的: 単一成果物だけでなくworkflow routing責務を持つSkillでも共通ランナーが機能することを確認

実Agent smokeの結果は`.agent-eval-runs/`へ保存し、commitしません。

実Agentのsemantic結果が`needs_review` / `fail`になった場合、ランナーが正常に生成・評価・保存できていればランナー実装失敗とは扱いません。ただし結果を無視せず、Skill / Eval Input / Reference / Judgeのどこに原因があるかを別途確認できる状態で報告します。

## フェーズ2: qa-training-store固定対象の統合評価

フェーズ1の実Codex smokeが完了した後、同branch上で `qa-training-store` の固定revisionを対象に実Agent統合評価を実施します。

詳細な対象準備、Checkout / Paymentの評価範囲、既存 `.agents/skills/` との分離、source変更検出、workflow / traceability / semantic評価条件は [`2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md`](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md) に従います。

フェーズ1のランナーは、このフェーズを見越して「入力準備」「Agent execution」「成果物保存」「評価」を分離します。ただし任意repo向けplugin frameworkは作りません。

## 既存検証

実装後は少なくとも次を実行します。

```bash
python -m compileall -q scripts/skills/evals/agent
python -m unittest discover -s scripts/skills/evals/agent/tests -v
python -m unittest discover -s tests/skills/evals/agent -v

python -m unittest discover -s scripts/skills/evals/deterministic/tests -v
python -m unittest discover -s tests/skills/evals/deterministic -v
python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v

python scripts/skills/evals/semantic/validate.py
python -m unittest discover -s scripts/skills/evals/semantic/tests -v
python -m unittest discover -s tests/skills/evals/semantic -v
python -m unittest discover -s tests/skills/evals/trigger -v

git diff --check
```

既存Skill仕様適合検証も実行します。

## 実装順序

1. branch開始時点が基準`main`から意図しない差分を持たないことを確認する
2. 固定Evaluator checkoutのclean状態・grader / Judge条件を確定し、候補Skill revisionのtracked contentから一時実行ディレクトリを作る
3. workspaceと実効OS境界のread-denial、余分なuser / global設定・Skill / MCPを排除するpreflightを定義し、fake Agentで失敗時の分類を固定する
4. `prompt_builder.py`で生成prompt契約を実装し、Reference / expected / rubricを渡さないtestを追加する
5. `run.py`へ単一caseのAgent subprocess実行と成果物保存を実装する
6. deterministic単一caseを既存graderへ接続する
7. semantic単一caseを固定Evaluator側graderへ接続し、同じAgent commandを独立Judge invocationへ使用する。両stageの実効設定を記録する
8. Skill単位batch、`--skill all`、`--repeat`、結果集計、exit codeと、Evaluator固定・Skill SHA・実効設定profile・隔離preflightによる比較可否判定を追加する
9. fake Agentを使った共通unit / repository integration testを完成させる
10. `.gitignore`、`EVALS.md`、`README.md`、`PROJECT_CONTEXT.md`を現在実装へ同期する
11. GitHub Actionsへ外部LLMを使わないcompile / testだけを追加する
12. 既存評価・runtime・trigger検証を全件実行する
13. 同branch上で実Codex smoke 4 caseを実行する
14. 実Codex結果とrunnerの保存物を確認し、runner起因の未達が0件であることを確認する
15. フェーズ2補助Planに従い、`qa-training-store`固定revisionから元Project Contextを除いた使い捨て評価対象を準備し、評価用`AGENTS.md`とProject Contextを生成する
16. 対象repo固有のAgent Skill集合を評価条件から除外し、今回の19 SkillだけをAgent-visibleにする
17. Checkout / PaymentのWeb範囲で実Agent分析・設計workflowをattemptごとに実行し、source無変更、runtime証拠と成果物の対応、traceability、workflow状態、固定Referenceでの意味品質を評価する
18. フェーズ1 / フェーズ2の結果を分離して保存し、runner起因の失敗とSkill品質上の非passを区別して報告する

## 対象外

今回追加しません。

- 新しいAgent Skill
- Skill自動修正
- Skill変更候補の自動採用
- 自動branch作成 / commit / PR作成
- Skillなし / Skillありの自動A/B比較
- mainとbranchの自動ランキング
- 独自総合スコア
- 外部LLMを使う通常CI job
- scheduled Agent eval
- MCP server
- SQLite / PostgreSQL
- 独自Agent runtime
- LangGraph等のworkflow framework
- Codex / Claude Code専用SDK依存
- Codex固有flagのハードコード
- native Skill trigger観測のクライアント別adapter
- 新しいサンプルアプリ
- `qa-training-store`以外を含む複数target repo向けplugin framework
- フェーズ2初回でのNative / 実ブラウザE2E評価

Skillなし / Skillあり比較やmain / candidate比較は、今回保存するcase単位結果を使って2回のrunを比較すれば手動で実施できます。比較作業が継続的なボトルネックになった場合に、比較専用処理を追加します。

native trigger評価は、Skill activationを観測する方法がAgentクライアントごとに異なるため今回の共通ランナーへ含めません。既存trigger datasetとvalidationを維持し、実クライアントでの発火自動測定は別の課題として扱います。

## ポータビリティ条件

次をすべて満たすことを必須とします。

- 通常のSkill実行に`agent`評価ランナーが不要
- `SKILL.md`へCodex / Claude Code等の評価用commandを追加しない
- Skill-local scriptから評価ランナーをimportしない
- Agent固有SDKを共通評価ランナーへ追加しない
- Agent commandは外部argvとして注入する
- 評価対象成果物は既存Markdown契約のまま
- deterministic / semantic graderの正規契約を変更しない
- 1 Skillだけを移植する既存ポータビリティtestを壊さない

## 完了条件

次をすべて満たしたら、この実装を完了とします。

- 固定Evaluatorのclean checkoutから異なるSkill revisionを選択でき、候補Git treeの配置内容とmanifestが一致する
- 候補Skillのevalを独立判定に使わず、grader / Judge / verifierを同一Evaluator revisionへ固定できる
- Agent / Judgeの非秘密実効profile・隔離結果を確認できないrunを比較可能としない
- 実Agent評価ランナーが追加されている
- 単一deterministic caseを「実Agent生成 → 既存grader」まで1 commandで実行できる
- 単一semantic caseを「実Agent生成 → 独立Judge → 既存semantic判定」まで1 commandで実行できる
- Skill単位batchを実行できる
- `--skill all`を明示した場合だけ全case batchを実行できる
- `--repeat`で同一caseを複数回独立実行できる
- AgentへReference / expected / rubric / validatorを公開しない一時実行ディレクトリと、読み取り禁止が実証された隔離境界を使用する
- 一時実行ディレクトリに19 Skillの通常実行ファイルが存在する
- 実Agent commandを特定プロバイダーへ固定していない
- `shell=True`を使用していない
- Agent出力、stderr、grader結果、全体結果を保存できる
- 認証情報や環境変数を結果fileへ保存していない
- `.agent-eval-runs/`がgit管理対象外になっている
- fake Agentを使うrunner unit / integration testがpassする
- 既存deterministic / runtime / semantic / trigger testがpassする
- 通常GitHub Actionsで外部LLMを呼ばない
- `TC-OUT-001`、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`を実Codexで同branch上から実行し、生成・保存・grader起動・結果集計まで完了する
- 実Codex smokeでrunner起因の未処理エラーが0件
- 実Codexの非pass結果がある場合、その結果を隠さず保存・報告できる
- 各live runにSkill revision、評価入力 / scenario fingerprint、Agent名 / model等の比較に必要なprovenanceが保存される
- 2つの実runでEvaluator・入力・Judge・実効Agent profile・隔離・repeatの一致を確認し、異なるSkill package revisionだけを比較する。Skill使用が未観測なら効果の帰属を未確認と明示する
- `qa-training-store`固定revision `84ce165493649550832731a60cf436f8ae29c56b` を対象にフェーズ2初回評価と独立したrepeat試行を実行している
- Checkout / PaymentのWeb範囲で実Agentによる分析・設計workflowが完了し、成果物・workflow・traceability・意味評価結果が保存されている
- `qa-training-store`のProduct Code、既存Test、規範仕様に許可外変更がない
- 対象repo既存Skillではなく今回の19 SkillだけをAgent-visibleにし、元`PROJECT_CONTEXT.md`を最小評価用内容へ置換した条件を記録している
- フェーズ2のrunner / environment errorとSkill品質上のneeds_review / fail、`valid=false`、比較不可・Evaluator非互換を区別している
- Skill本体の通常実行経路とポータビリティを変更していない
- `git diff --check`がpassする
