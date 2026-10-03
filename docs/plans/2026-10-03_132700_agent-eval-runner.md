# 実Agent評価ランナー実装Plan

このPlanは、既存のAgent Skills評価データセットを使って実Agentから評価対象成果物を生成し、現在の決定論的出力評価・意味評価まで一括で実行できる開発用ランナーを追加するための実装計画です。

Skill本体の実行基盤は変更しません。Codex、Claude Code等のAgent runtimeは各クライアントへ任せ、今回追加するランナーはリポジトリ開発時の評価だけを担当します。

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

次の一連の処理を、1つの共通経路から再現可能に実行できるようにします。

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

これにより、Skillを変更した後に同じ評価ケースを実Agentで再実行し、既存評価基準で結果を確認できるようにします。

今回の目的はSkillを自動修正することではありません。Skill改善案の作成・採用判断は別責務とし、まず評価実行を再現可能かつ可能な範囲で自動化します。

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

実Agentとは次の外部command契約だけで接続します。

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

19 Skillすべての通常Skill Packageを配置し、`qa-workflow`等が他Skill名を前提にする場合も通常構成を維持します。

Eval Inputはファイルとして一時実行ディレクトリへコピーせず、生成promptへ埋め込みます。

Agentは`reference.md`、`expected.json`、rubric、validatorへアクセスできない状態で実行します。

### 5. 既存graderを再実装しない

新しいランナー内にdeterministic assertionやsemantic Judgeロジックを複製しません。

- deterministic: 既存`scripts/skills/evals/deterministic/run.py`を使用
- semantic: 既存`scripts/skills/evals/semantic/run.py`を使用

ランナーは、評価対象成果物の生成、保存、既存graderの呼び出し、結果収集だけを担当します。

### 6. 通常CIでは外部LLMを呼ばない

現在の方針を維持し、pull request / pushで自動実行される通常GitHub ActionsからCodex等を呼びません。

CIではfake Agent commandを使って、ランナー自体の契約・一時実行ディレクトリ・grader接続だけを検証します。

実Codex等を使う評価は、開発者が明示的に起動するローカル評価とします。

## 追加する共通ランナー

### 配置

```text
scripts/skills/evals/agent/
├── __init__.py
├── run.py
├── prompt_builder.py
├── workspace.py
├── README.md
└── tests/
```

責務は次のとおりです。

### `run.py`

- CLI引数解析
- 評価ケースの選択
- 一時実行ディレクトリ作成
- Agent command実行
- 評価対象成果物保存
- 既存grader起動
- ケース別結果保存
- 全体結果集計
- exit code決定

### `prompt_builder.py`

Agentへ渡す生成promptだけを構築します。

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

- `tempfile`で一時実行ディレクトリを作る
- 19 Skillの通常実行ファイルをコピーする
- `evals/`を除外する
- Agent実行終了後に一時ディレクトリを削除する

新しいsandbox実装は作りません。OS process / filesystem isolationはAgentクライアント側のsandboxを使用します。

## CLI契約

### 単一deterministic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --output-root .agent-eval-runs/run-001 \
  --agent-command <agent command argv...>
```

### 単一semantic case

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --eval-id TC-SEM-001 \
  --output-root .agent-eval-runs/run-001 \
  --agent-command <agent command argv...>
```

`--agent-command`はCLIの最後に置き、後続値をそのままargvとして扱います。既存semantic CLIの`--judge-command`と同じ方式にします。

### Skill単位batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite semantic \
  --skill test-case-design \
  --output-root .agent-eval-runs/run-001 \
  --agent-command <agent command argv...>
```

`--eval-id`省略時は、指定Skillの対象suiteに定義された全caseを実行します。

### 全Skill batch

```bash
python scripts/skills/evals/agent/run.py \
  --suite deterministic \
  --skill all \
  --output-root .agent-eval-runs/run-001 \
  --agent-command <agent command argv...>
```

`--skill all`は明示指定時だけ許可します。既定で全38 / 72 caseを外部LLMへ送信しません。

### 複数回実行

`--repeat N`を任意指定できるようにし、既定は1とします。

同一caseを複数回実行した場合も独自の平均点は作りません。attemptごとの既存eval結果と、pass / needs_review / fail / execution errorの件数だけを集計します。

## semantic評価時のAgent command

v1では、生成に使用した`--agent-command`を、別プロセス・別promptでsemantic Judgeにも使用します。

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

`result.json`には次を保持します。

- suite
- Skill
- eval ID
- attempt番号
- Agent commandのexit code
- graderのexit code
- deterministic statusまたはsemantic verdict
- 各保存fileの相対path
- 実行開始時のGit HEADを取得できた場合はそのSHA

環境変数、認証情報、token、Agent command全体は保存しません。

`.agent-eval-runs/`は`.gitignore`へ追加し、実Agent出力・ログ・Judge結果を通常commit対象にしません。

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
- `scripts/skills/evals/agent/run.py`
- `scripts/skills/evals/agent/prompt_builder.py`
- `scripts/skills/evals/agent/workspace.py`
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

### 一時実行ディレクトリtest

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

テスト用fake Agentは評価対象ケースの正解ロジックを実装しません。ランナーの配線確認に必要な最小固定応答だけを使用します。

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
2. `scripts/skills/evals/agent/workspace.py`で評価情報を除外した一時実行ディレクトリを作る
3. workspace unit testで`evals/`等の評価情報がAgentから見えないことを先に固定する
4. `prompt_builder.py`で生成prompt契約を実装し、Reference / expected / rubricを渡さないtestを追加する
5. `run.py`へ単一caseのAgent subprocess実行と成果物保存を実装する
6. deterministic単一caseを既存graderへ接続する
7. semantic単一caseを既存graderへ接続し、同じAgent commandを独立Judge invocationへ使用する
8. Skill単位batch、`--skill all`、`--repeat`、結果集計、exit codeを追加する
9. fake Agentを使った共通unit / repository integration testを完成させる
10. `.gitignore`、`EVALS.md`、`README.md`、`PROJECT_CONTEXT.md`を現在実装へ同期する
11. GitHub Actionsへ外部LLMを使わないcompile / testだけを追加する
12. 既存評価・runtime・trigger検証を全件実行する
13. 同branch上で実Codex smoke 4 caseを実行する
14. 実Codex結果とrunnerの保存物を確認し、runner起因の未達が0件であることを確認する

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

- 実Agent評価ランナーが追加されている
- 単一deterministic caseを「実Agent生成 → 既存grader」まで1 commandで実行できる
- 単一semantic caseを「実Agent生成 → 独立Judge → 既存semantic判定」まで1 commandで実行できる
- Skill単位batchを実行できる
- `--skill all`を明示した場合だけ全case batchを実行できる
- `--repeat`で同一caseを複数回独立実行できる
- AgentへReference / expected / rubric / validatorを公開しない一時実行ディレクトリを使用する
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
- Skill本体の通常実行経路とポータビリティを変更していない
- `git diff --check`がpassする
