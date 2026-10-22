# 実Agent評価ランナー

このランナーは、指定した`qa-workflow-skills` Git revisionのSkill packageを一時領域へ展開し、実Agentで生成した結果を固定Evaluatorの既存grader / Judgeで評価します。評価結果と機械判定をattempt単位で保存します。既存Skillの通常実行経路やSkill packageの配置規則は変更しません。

Agent実行にはLinux Docker環境と利用者が用意したAgent / Judgeコマンドが必要です。実行profile、command、run結果は秘密情報を含めず、run単位の`.agent-eval-runs/`へ置きます。このdirectoryはGit管理対象外です。通常CIは外部LLMを呼ばず、fake Agent / Judgeの契約テストだけを実行します。

## CLI一覧

| Module                                         | 用途                                                              |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `scripts.skills.evals.agent.run`               | deterministic / semantic case、Skill単位、明示された`all` batch   |
| `scripts.skills.evals.agent.isolation_probe`   | Agent / JudgeのDocker設定とAgent workspace mountの隔離検証        |
| `scripts.skills.evals.agent.qa_training_store` | 固定`qa-training-store` revisionのCheckout / Payment workflow評価 |
| `scripts.skills.evals.agent.judge_validation`  | 正常例・固定違反例でのJudge独立検証とレビュー用候補比較           |
| `scripts.skills.evals.agent.compare`           | 条件が一致するrun間のattempt / criterion比較                      |
| `scripts.skills.evals.agent.improve`           | 保存済みrunの分析、許可path限定修正、同条件での再評価             |

## 実行前提

- Python 3.11と、既存deterministic validatorが使う`PyYAML==6.0.3`を評価環境へ用意します。
- 実Codex imageは[`tools/codex-agent.Dockerfile`](tools/codex-agent.Dockerfile)から作り、Codex CLI `0.163.0`とPython 3.11を固定します。build後に得たimage IDは各launcherが照合・記録し、照合したIDで実行します。
- 実Agent / Judgeは別々のargv・cwd・実効profileで起動します。どちらも直接`docker run`し、`shell=True`は使いません。
- Agent containerはread-only root、`/workspace` read-only、`/workspace/.qa-eval-output`のみwrite可能なbind mountにします。Evaluator / Reference / graderをbind mountしません。
- Judgeは[`tools/codex_judge_docker_launcher.py`](tools/codex_judge_docker_launcher.py)でAgentとは別の使い捨てcontainerに起動します。Judge専用の一時`CODEX_HOME`だけを認証用にmountし、sanitized target・Agent workspace・Evaluator checkoutはmountしません。Judge promptはstdinだけで渡し、stdoutは最終Judge JSONだけにします。
- Judge containerではMCP、user/global設定、Skill rootを読み込まず、web searchも有効化しません。JSONLにshell等のtool eventがあればJudge出力を採点に使わず`evidence_unverified`にします。安全なevent summaryは各Judge workspaceの`launcher-observations.json`へ保存し、raw JSONLは保存しません。
- AgentのSkill rootは`/workspace/.agents/skills`だけにします。global config、追加指示、MCP、Web / browser / search toolは無効にします。
- Codex launcherは`codex exec --help`で確認した`--json`、`--model`、`--sandbox`、`--config`、`--cd`、`--output-last-message`、`--skip-git-repo-check`だけをexecへ渡します。`--no-daemon`、`--strict-config`、`--ask-for-approval never`はroot CLI optionとして`exec`より前に置きます。profileの`agent.cli_version`は`codex-cli 0.163.0`に固定します。
- Codex JudgeもCLI `0.163.0`に固定し、profileの`judge.sandbox_policy` / `approval_policy`は`read-only` / `never`、`launch_options` / `tools` / `mcp_servers` / `skill_roots`は空配列、`global_config` / `external_instructions`は`disabled`にします。Judge commandには`-i`、`--read-only`、`--cap-drop=ALL`、`--security-opt=no-new-privileges`、`--mount type=tmpfs,target=/tmp`を指定します。
- run開始前にEvaluator checkoutをcleanにします。固定対象repoもclean working treeにし、Plan記載のGit objectが存在することを確認します。
- Profile / command JSONとrun出力は異なるdirectoryに置きます。出力rootには事前検証済み`isolation.json`だけを置けます。

実効profileはJSON schema version `1`です。`agent` / `judge`には実際のmodel、version、timeout、launch option、sandbox、approval、network、tool、MCP、Skill root、global configの状態を記録します。`verification`は`status: "verified"`、`method`、`evidence_path`を設定し、probeが同profile fingerprint、Agent command fingerprint、Judge command fingerprint、Evaluator revisionに結び付いた証拠を作成します。probeが`unverified`を返した場合、そのprofileでlive runnerを起動しません。

Codex smokeはJSONLをlauncherのmemory内だけで解析します。保存する`agent-trace.json`はevent数・event type・終了code・安全化したSkill読取 / verifier実行事実だけを含み、raw command、JSONL本文、認証情報は保存しません。最終応答とstderrも秘密パターンを安全化し、安全化で内容が変わったattemptはJudgeへ渡さず`needs_review`にします。traceにSkill読取事実がない場合は`unverified`を維持し、Skill改修効果を断定しません。

秘密値をprofile・command argvへ直接記載しないでください。認証情報はAgent / Judge imageの実行環境が安全に受け取る方法で供給し、結果・stdout・stderr・provenanceへ出さないでください。

## 共通case実行

初回のみ、repository rootで固定Codex / Python imageをbuildします。実行時profileはCodex-specific optionや認証値を含めず、`docker run ... codex exec`までのargvを指定します。Agent launcherはCodex CLI引数と一時認証homeを加えます。Judge launcherも同じimageを使いますが、Agentと別container・別一時`CODEX_HOME`で実行します。

```bash
docker build --tag codex-agent:0.163.0 \
  --file scripts/skills/evals/agent/tools/codex-agent.Dockerfile .
```

build後、imageのimmutable IDを取得し、Agent / Judge両方の`command_argv`にその`sha256:...` IDを設定します。launcherはtagの差替えを許さず、profileに記録された同じIDを照合して実行します。

```bash
docker image inspect --format '{{.Id}}' codex-agent:0.163.0
```

先に`agent-command.json`へ、実際に使用する`docker run` argvをJSON arrayとして保存します。下記の`{workspace}`と`{output_root}`はprobe / runnerが各run用pathへ置換します。

```json
[
  "docker",
  "run",
  "--rm",
  "-i",
  "--read-only",
  "--cap-drop=ALL",
  "--security-opt=no-new-privileges",
  "--network",
  "bridge",
  "--workdir",
  "/workspace",
  "--mount",
  "type=bind,source={workspace},target=/workspace,readonly",
  "--mount",
  "type=bind,source={output_root},target=/workspace/.qa-eval-output",
  "--mount",
  "type=tmpfs,target=/tmp",
  "sha256:<build後に取得した64桁image ID>",
  "codex",
  "exec"
]
```

実Agent commandではtagではなく上記で得たimage IDを指定し、`--cap-drop=ALL`と`--security-opt=no-new-privileges`を含めます。Codex agent profileの`cli_version`は`codex-cli 0.163.0`、`sandbox_policy`は固定値を記録します。Codex launcherは`auth.json`を一時`CODEX_HOME`へ複製するか、`OPENAI_API_KEY`環境変数だけをcontainerへ渡し、終了時に一時領域を削除します。hostのCodex home自体はmountしません。認証値はprofile・argv・run結果へ記載しないでください。image IDとcontainer内Codex / Python versionを確認できないrunはlive評価を開始しません。

Codex Judgeの`judge.command_argv`はAgent commandと分け、stdinを接続できる`-i`を含めます。Judge launcherが認証・固定model・推論設定を加えます。

```json
[
  "docker",
  "run",
  "--rm",
  "--read-only",
  "--cap-drop=ALL",
  "--security-opt=no-new-privileges",
  "-i",
  "--network",
  "bridge",
  "--mount",
  "type=tmpfs,target=/tmp",
  "sha256:<build後に取得した64桁image ID>",
  "codex",
  "exec"
]
```

Judge launcherは一時`CODEX_HOME`、`HOME=/tmp`、read-only sandbox、approval `never`を固定し、profileのimage IDを検証します。実行結果は`launcher-observations.json`に安全化して保存します。Codex `--search` optionは渡さず、JSONLからtool eventを検出した場合は判定を未検証にします。

`profile.json`とcommand JSONを作成後、run用directoryに隔離証拠を保存します。

```bash
python -m scripts.skills.evals.agent.isolation_probe \
  --profile .agent-eval-runs/config/profile.json \
  --agent-command-json .agent-eval-runs/config/agent-command.json \
  --output-root .agent-eval-runs/TC-OUT-001
```

probeはDocker engineとAgent / Judge imageを確認し、設定済みAgent mountを使ってworkspace write-denialと評価出力rootのwrite許可を実行検査します。`isolation.json`の全required checkが`true`でない場合、`status`は`unverified`のままです。公開Web資料へのegressを制御できないprofileはその残留リスクを記録します。

実Codex smokeのCLI形:

```bash
python -m scripts.skills.evals.agent.run \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <40文字のSkill Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/TC-OUT-001 \
  --agent-name codex \
  --agent-model <model名> \
  --agent-command docker run --rm --read-only ...
```

受入smokeでは`TC-OUT-001`、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`を個別に実行します。Semantic caseはJudgeを独立起動し、既存semantic result normalizerで判定します。`--skill all`は明示時だけ使えます。対象revisionに存在しないSkill / caseは理由付きで除外記録へ残します。

## 固定qa-training-store統合評価

この評価は`qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`のsource treeを読み取り、Checkout / Payment Web範囲の固定scenarioを最低2 attemptで実行します。target repoへcheckout、commitその他のGit mutationを行いません。作業treeのHEADは異なっていても、指定revisionがGit objectとして存在し、treeがcleanなら読み取り元として使用できます。

```bash
python -m scripts.skills.evals.agent.qa_training_store \
  --target-root C:/Users/<user>/Documents/qa-training-store \
  --skill-revision <40文字のqa-workflow-skills Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --verifier-image <固定verifier image digest> \
  --output-root .agent-eval-runs/qts-baseline \
  --repeat 2 \
  --agent-command docker run --rm --read-only ...
```

Runnerはtarget用sanitized workspace、synthetic baseline、Skill / source manifest、artifact contract、runtime verifier replay、workflow runtime replay、Judge evidence、workspace integrityを保存します。Artifact Judgeはcanonical artifactsと不足placeholderのみを受け取り、routing / final stdout / machine summaryは受け取りません。Workflow Judgeはrouting / final stdoutと固定machine summaryを受け取ります。二つの判定は別container・別cwdで実行します。

## Judge検証とSkill改善

`judge_validation`は固定scenarioの正常・限定違反fixtureを別々にJudgeへ渡します。AI生成fixtureは承認済み扱いにせず、`--approval-file`でdataset revision、reviewer、timezone付き日時、該当fixtureの固定規範根拠を指定しない限りfixtureはreview pendingです。tuning proposalはtune splitの観測だけを受け取り、independent splitの期待値・判定を受け取りません。Candidate Judgeも固定fixtureで独立評価されますが自動採用しません。

```bash
python -m scripts.skills.evals.agent.judge_validation \
  --baseline-result .agent-eval-runs/qts-baseline/result.json \
  --target-root C:/Users/<user>/Documents/qa-training-store \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/judge-validation \
  --approval-file .agent-eval-runs/config/human-approvals.json \
  --max-cases 11 --max-seconds 1800 --repeat 2
```

`improve`は、2回以上再現し、既存runtime / artifact検証が通り、承認済みJudge fixtureに対応する固定critical failureだけを分析対象にします。分析Agentの自己申告だけで修正可とはしません。候補sourceは一つのSkill内の`SKILL.md` / `references/**` / `scripts/**` / `assets/**`に限定し、候補patch・package fingerprint・比較結果をrunへ保存します。RunnerはGit branch / commit / push / PRを作成せず、候補を自動採用しません。実Skill使用観測が得られない場合、品質差があってもSkill改善実証とは判定しません。

```bash
python -m scripts.skills.evals.agent.improve \
  --baseline-result .agent-eval-runs/qts-baseline/result.json \
  --judge-validation-result .agent-eval-runs/judge-validation/result.json \
  --target-root C:/Users/<user>/Documents/qa-training-store \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/improve-run \
  --verifier-image <固定verifier image digest> \
  --max-cases 10 --max-repairs 5 --max-seconds 3600 --analyze-only
```

`--analyze-only`も分析Agentの実行を伴いますが、Skillファイルは変更しません。修正が許可された通常runでは、各候補を同一target / scenario / profileで2回以上再評価します。外部Judgeの承認、実行環境、比較条件が不足している場合はreview pending / unverifiedとして残し、PASSへ読み替えません。

## CI・ローカルテスト

通常CIは外部LLM、Codex、Docker runtimeを起動しません。Fake Agent / Judgeのunit・integration testとrepository contract testを実行します。

```bash
python -m compileall -q scripts/skills/evals/agent tests/skills/evals/agent
python -m unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -v
python -m unittest discover -s tests/skills/evals/agent -p 'test_*.py' -v
```

すべての実run結果は`.agent-eval-runs/`に保存し、Gitへ追加しません。
