# 実Agent評価ランナー

このランナーは、指定した`qa-workflow-skills` Git revisionのSkill packageを一時領域へ展開し、実Agentで生成した結果を固定Evaluatorの既存grader / Judgeで評価します。評価結果と機械判定をattempt単位で保存します。既存Skillの通常実行経路やSkill packageの配置規則は変更しません。

Codex Agent / Judge / RepairはWSL2 Ubuntuの二重bubblewrap方式で起動します。実行profile、実効command、run結果は秘密情報を含めず、run単位の`.agent-eval-runs/`へ置きます。このdirectoryはGit管理対象外です。通常CIは外部LLMを呼ばず、fake Agent / Judgeの契約テストだけを実行します。QTSのCodexを使わないdeterministic verifierは既存の固定Docker image契約を維持します。

## 2026-10-25 認証更新の再調査

現行launcherは認証元の`auth.json`をattempt専用の一時`CODEX_HOME`へ複製し、その一時領域をattempt終了時に削除します。Codex CLIがattempt中にrefreshしたtokenをこの一時storeへ保存した場合、保存結果はcleanupで失われ、次のattemptは元storeのtokenから再開します。これは`refresh_token_reused`を説明し得る経路ですが、既存の失敗記録から直接原因と確定できたわけではありません。

固定Codex CLI `0.163.0`は、同一プロセス内の`AuthManager`でrefreshを直列化し、更新tokenを選択中のstorage backendへ保存します。file backendは`auth.json`を書き換えますが、CLIのfile storageには別プロセス間の排他制御がありません。したがって、attemptごとの一時copyは更新を次回へ引き継がず、同時に同じ元storeから開始したcopy同士も相互排他しません。詳細は[認証調査報告 v04](../../../../docs/reports/2026-10-25_pr17-chatgpt-auth-recovery_v04.md)を参照してください。

2026-10-25の`--auth-status-only`は固定runtime `0.163.0`でChatGPT loginを確認しました。この確認は認証方式と状態だけを返し、認証fileの内容・hashを出力せず、モデルAPIも呼びません。これは永続化・競合防止・Agent shellからの認証情報読み取り拒否を証明しません。永続専用`CODEX_HOME`はCodex自身の公式storageへ更新を保存できますが、現行の合成marker検証ではshellからの可視性が残り、同じstoreを使う外部Codex processとの競合も排除できません。`codex_wsl2_bwrap_launcher.py`はこの残留riskがtrueの間、Agent/Judge/Repair全modeを認証status確認、auth file copy、Codex起動より前に`execution_error`で停止します。安全な方法が確定するまで実認証runを停止し、`authentication_shell_visible_risk=true`を維持します。

Codex CLI `0.163.0`のauth manager sourceには`CODEX_REFRESH_TOKEN_URL_OVERRIDE`があり、未設定時は公式OAuth refresh endpointを使います。これはsource上のprocess environment overrideであり、test-onlyに制限される仕組みではありません。Codex自身のrefresh保存をsynthetic dataで試験する場合に限り、固定revisionのsource test process内でこの値をloopback mock endpointへ向け、synthetic `CODEX_HOME`だけを使い、他のnetwork egressを遮断してrefresh・store reload・次のrefreshを確認する方法があります。環境変数をproduction launcher/profileへ渡してはいけません。

固定CLIの`codex login status`は`load_auth()`で保存済みmodeを判定するだけでrefreshを呼びません。そのため既存の`--auth-status-only`は保存試験を代替しません。通常の`codex exec`からrefreshを誘発する試験はモデルrequestと切り離せないため、TC-OUT-001の承認前に実行しません。CLI本体での保存・競合検証は固定`0.163.0`のCodex source test harnessからのみ行い、現在の評価runner unit testはcopy/cleanup配線とsynthetic marker可視性だけを検査します。loopback mockを使った単一process成功は別process競合の解決を意味しません。

## CLI一覧

| Module                                       | 用途                                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------- |
| scripts.skills.evals.agent.run               | deterministic / semantic case、Skill単位、明示されたall batch                         |
| scripts.skills.evals.agent.isolation_probe   | WSL2、outer/inner bubblewrap、固定binary、mount、namespace、FD、network、evidence検証 |
| scripts.skills.evals.agent.qa_training_store | 固定qa-training-store revisionのCheckout / Payment workflow評価                       |
| scripts.skills.evals.agent.judge_validation  | 正常例・固定違反例でのJudge独立検証とレビュー用候補比較                               |
| scripts.skills.evals.agent.compare           | 条件が一致するrun間のattempt / criterion比較                                          |
| scripts.skills.evals.agent.improve           | 保存済みrunの分析、許可path限定修正、同条件での再評価                                 |

## 実行前提

- 評価ランナー本体はWSL2 Ubuntu内のclean Linux checkoutから起動します。Windows Python、Windows開発checkout、/mnt/c上のtarget checkoutは正式実行に使用しません。
- Python 3.11と既存deterministic validator用PyYAML 6.0.3、Codex CLI Linux x64 0.163.0、そのpackageに同梱されたbwrap、最小runtimeとCA bundleを使います。追加system packageや管理者権限は避けます。
- 評価開始前に、利用する既存Python環境のversionとPyYAMLを確認します。importに失敗する環境ではrun/probeを開始せず、固定依存が準備された既存環境へ切り替えます。
- Codex packageは公開npm tarball https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz を使い、package name/version `@openai/codex@0.163.0-linux-x64`とSHA-512を照合します。既知tarball SHA-512は `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3` です。launcherは実行時のCLI version、CLI binary SHA-256、同梱bwrap SHA-256も照合します。system bwrapへ暗黙に切り替えません。
- Agent、Judge、Repairは、tmpfs rootに必要最小限のruntime、sanitized workspace、attempt output、一時CODEX_HOMEだけをmountするouter bubblewrap内でCodexを起動し、Codex自身のLinux sandboxを内側で有効にします。host root、host home、Evaluator checkout、元target、Windows filesystem、Docker socket、他attemptのpathはAgent/Judgeから見えません。
- Agent/Judge/Repairごとに独立したprocess、outer namespace、workspace、cwd、一時CODEX_HOMEを作ります。JudgeへAgent workspaceをmountしません。Judge入力はstdinのみ、shell/MCP/追加Skill roots/web searchは無効にし、JSONLのtool eventがあればjudge_unverifiedにします。raw JSONLは保存しません。
- outer networkはCodex親processのモデルAPI通信に必要なため維持します。inner Codex sandboxのshellはTCP/DNS/AF_UNIX/WSL interop/localhostを使えないよう設定し、正式launcherからnegative testします。TEST-NET等の単一接続失敗を全面egress遮断の根拠にしません。
- schema 2の認証方式は、ChatGPTアカウントでサインインしたCodex CLIだけです。固定runtimeの`codex login status`が`Logged in using ChatGPT`を返し、認証fileがWSL2内の正規`auth.json`であることを確認します。API Key、未ログイン、不明・確認失敗、方式を確認できないstore、固定CLI version不一致はfail-closedです。`OPENAI_API_KEY`と`CODEX_API_KEY`は確認・起動environmentへ渡さず、API Keyへfallbackしません。Windows filesystemやrepository内の`CODEX_HOME`を探索・利用しません。
- ログイン状態だけを安全に確認するには、WSL2 clean checkoutから`python -m scripts.skills.evals.agent.tools.codex_wsl2_bwrap_launcher --auth-status-only`を実行します。固定CLI/version/digestを先に照合し、方式・成功状態・CLI version・秘密を含まないerror classだけを表示します。認証file本文やhashは表示・保存せず、モデルAPIは呼びません。このcommandはログイン操作を開始しないため、未ログインの場合は利用者自身がWSL2でChatGPT loginを完了するまで停止します。
- Codex shellは合成認証markerとAPI keyを読めた過去実測があります。formal smokeはsynthetic `auth.json`を用い、Agent/Judge/Repair shellからの`/codex-home/auth.json`読取り、host側store path、他attempt store、environment内marker、可視process FDのtargetを個別に検査し、値ではなくbooleanだけを記録します。いずれかの可視性checkがfalseならmodeとevidenceを未検証にし、実行launcherも`authentication_shell_visible_risk=true`の間は全modeをfail-closedにします。認証方式をChatGPT loginに限定しても露出リスクは解消しません。
- Codex CLI固有設定は固定profileから検証し、MCP、外部指示、global config、追加Skill、web検索を無効にします。秘密値・生認証情報・秘密hashをargv、environment、profile、provenance、raw JSONLへ保存しません。
- Codex source / 固定targetの既存ファイル・directoryはouter mountで個別にread-only bindします。Codex workspace-writeがsandbox準備で必要とするattempt-local workspace root、`.git`、`.codex`だけは一時領域として分離し、許可outputとRepair対象Skill以外の既存sourceは変更できません。実行前後manifestを比較し、単にworkspace全体をwrite可能にする方式は不適合です。
- 通常CIは外部LLM、実認証、live Codex execを呼びません。fake Agent/Judge contract testsを実行します。実Codex sandbox smokeはWSL2のformal launcher経由で無認証のsynthetic inputだけに実行します。

実効profileはJSON schema version 2です。Agent / Judge model、timeout、reasoning、sandbox、approval、network、tools、MCP、Skill rootsに加え、runtimeにはWSL2実行mode、Codex package source/version/SHA-512、Codex binaryとbwrapのSHA-256、outer/inner argv・mount・network fingerprint、probe version、evidence fingerprint、依存versionを記録します。secret自体は記録しません。認証方式はprofileから切替できず、launcherがChatGPT loginに固定します。run observationsには認証方式・確認状態・CLI versionだけを記録し、認証fileの内容やhashは記録しません。旧Docker profileは読み取り用に保持しますが、新方式と直接比較できません。

Profile verificationは同じEvaluator revision、profile、Agent/Judge/Repair mode、binary digest、実効argv・mount/network、probe versionに結び付くisolation.jsonを要求します。従来の15 required checksに、合成auth markerのinner shell read拒否を追加した16件すべてが必要です。この追加checkはstore本体、host path、他attempt path、environment、可視process FDを対象にし、秘密値は証拠に残しません。Agent/Judge/Repairそれぞれの本番`codex exec` argvもfingerprintし、attemptごとに変わる`--output-last-message`のファイル名だけを正規化します。probeは本番`codex exec`やモデル通信を実行しません。evidence欠落、旧Docker evidence、別mode evidence、fingerprint不一致、必須negative test未確認の場合はisolation_unverifiedとして起動を拒否します。

## WSL2通常ターミナルでの検証とfresh evidence

Codex開発sandbox内でWSLのAF_UNIX socket bindやrepository testが`EPERM`になる場合、隔離やHookを変更せず、通常のWSL2 Ubuntuターミナルで次を個別に実行します。利用者は前の実装revisionについてDeterministic repository suite 293件、formal launcher integration 1件、host AF_UNIX bindのPASSを報告しました。今回のformal integration再試行はCodex sandbox内のhost AF_UNIX bindで`EPERM`となり、新しい認証marker checkには到達していません。この旧PASSを追加checkを含む現在の実装の証拠として扱いません。

```bash
cd /home/sella/src/qa-workflow-skills-pr17-auth-20261025
source ~/.venvs/qa-workflow-skills/bin/activate
export QAEVAL_CODEX_RUNTIME_ROOT=/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final
python --version
python -c 'import yaml; print(yaml.__version__)'
python -m unittest discover -s tests/skills/evals/deterministic -p 'test_*.py' -q
QAEVAL_RUN_WSL2_INTEGRATION=1 python -m unittest scripts.skills.evals.agent.tests.test_codex_wsl2_bwrap_launcher.CodexWsl2LauncherIntegrationTests.test_formal_launcher_modes_fd_network_paths_and_timeout_cleanup -v
python -c 'import pathlib,socket,tempfile; d=tempfile.TemporaryDirectory(); s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); p=pathlib.Path(d.name)/"host.sock"; s.bind(str(p)); print("host AF_UNIX bind: PASS"); s.close(); d.cleanup()'
```

`host AF_UNIX bind`はWSL hostでlistenerを作れる確認です。inner shellからそのsocketへ接続できないことはformal launcher integration/probeが別途確認します。

正式probeには、commit済みでcleanなEvaluator checkout、同checkout revision用の新しいschema 2 profile、固定argv template JSONが必要です。profileは`agent.name=codex`、`agent.model=gpt-6-luna`、`agent.reasoning_effort=max`、timeout 900、Codex CLI `0.163.0`、`workspace-write`、shellのみ、MCPなし、既定のWSL2二重bubblewrap isolation契約を持ちます。Judge fieldsもschema上必要で、`judge.command_argv`は`["codex"]`、Judge sandboxは`read-only`です。deterministic runはJudgeを起動しませんが、probeは3 modeのsandbox smokeを行います。profileの`verification.evidence_path`は`isolation.json`にし、profileのほかの値は後続runで使うものと一致させます。

`agent-command.json`のJSON本文は固定の`["codex"]`です。probeが本番`codex exec`を起動する指定ではなく、Codex executable/templateの契約を照合するためのargv arrayです。新しいrun IDのoutput directoryをprobeと後続runで共用します。これによりprofileのevidence pathとrunnerが読む`<output-root>/isolation.json`が一致し、既存run/evidenceを上書きしません。

```bash
source ~/.venvs/qa-workflow-skills/bin/activate
export QAEVAL_CODEX_RUNTIME_ROOT=/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final
RUN_ID="pr17-isolation-$(git rev-parse --short HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_ROOT=".agent-eval-runs/$RUN_ID"
CONFIG_DIR="$(mktemp -d /tmp/qa-pr17-isolation-config.XXXXXX)"
git status --short --branch  # cleanであることを確認
git rev-parse HEAD           # evidence対象revisionを記録
test ! -e "$OUT_ROOT"        # 新規run IDで既存成果物を上書きしない
cat > "$CONFIG_DIR/profile.json" <<'JSON'
{"schema_version":2,"agent":{"name":"codex","model":"gpt-6-luna","timeout_seconds":900,"cli_version":"0.163.0","reasoning_effort":"max","launch_options":[],"sandbox_policy":"workspace-write","approval_policy":"never","network_policy":"codex-parent-host-network-inner-shell-denied","tools":["shell"],"mcp_servers":[],"skill_roots":["/workspace/.agents/skills"],"external_instructions":"none","global_config":"none"},"judge":{"model":"gpt-6-luna","command_argv":["codex"],"cwd":"isolated","timeout_seconds":900,"cli_version":"0.163.0","reasoning_effort":"max","launch_options":[],"sandbox_policy":"read-only","approval_policy":"never","network_policy":"codex-parent-host-network-inner-shell-denied","skill_roots":[],"global_config":"none","tools":[],"mcp_servers":[],"external_instructions":"none"},"isolation":{"method":"wsl2-dual-bubblewrap","agent_read_roots":["/workspace"],"evaluator_read_blocked":true},"verification":{"status":"verified","method":"wsl2-dual-bubblewrap","evidence_path":"isolation.json"}}
JSON
cat > "$CONFIG_DIR/agent-command.json" <<'JSON'
["codex"]
JSON
python -m scripts.skills.evals.agent.isolation_probe \
  --profile "$CONFIG_DIR/profile.json" \
  --agent-command-json "$CONFIG_DIR/agent-command.json" \
  --output-root "$OUT_ROOT"
```

実行前に固定runtime path、Codex CLI/package digest、bundled bwrap digestが`verify_runtime()`で一致することが必要です。probeは`codex sandbox`によるAgent/Judge/Repair smoke、従来の15件と追加した認証可視性checkの計16 required checks、modeごとのargv/profile fingerprintを記録します。`model_api_used=false`かつ`authentication_shell_visible_risk=true`を維持し、認証status確認・`codex exec`・モデルAPIは呼びません。evidenceの`evaluator_revision`はclean checkoutのHEADと一致し、全required checkと3 mode evidenceが`verified`でなければ実runに使えません。さらに認証可視性riskが未解消の間はlauncher自体も全modeを拒否します。profile statusだけでevidenceを承認しません。

## 合成認証データによる検証範囲

launcher unit testはsynthetic `auth.json` markerのcopy、permission、cleanup、出力redaction、ChatGPT login statusの分類を検証します。copy/delete方式でfake childがattempt側だけを更新しても次attemptに継承されないことを再現します。これはCodex CLI自身のrefresh成功を証明しません。formal smokeはsynthetic markerのread可否をAgent/Judge/Repairの正式二重sandbox経路で記録し、read可能なら必須checkがfalseとなりevidenceを拒否します。現在の`_prepare_codex_home()`はsource `auth.json`をattempt専用homeへcopyし、cleanup時にそのhomeを削除します。refresh結果がcopy側へ書かれれば次attemptへ残らないため、更新成功を次attemptで使える保証はありません。

この範囲を合成データで検証するなら、(1)固定CLIを呼ばないunit testでsource markerとattempt copyを作り、fake childがcopyだけを更新した後にcleanupと次attemptを行い、source markerが不変で更新が引き継がれないことを確認する、(2)runnerが導入する協調lockをmultiprocessで競合させ、同時refresh要求を直列化するか後続をfail-closedにすることを確認する、(3)formal launcherの同じ`/codex-home/auth.json` mountへsynthetic markerを置き、Agent/Judge/Repairのinner shellから内容を取得できないことを秘密値自体を出力せずbooleanだけで記録する、という段階を分けます。fake childによる更新試験はrunner配線のみを検証し、固定Codex CLIのOAuth refreshや外部processとの排他の証明にはなりません。実auth fileや実tokenを使う試験はしません。

固定Codex CLI `0.163.0`の公式実装ではrefreshのmutexは同一`AuthManager`内で、成功tokenは選択したstorage backendへ保存されます。file storageは`auth.json`をtruncate/write/flushしますが、CLI横断のprocess lockはありません。そのためsynthetic storeのrunner内lock testだけでは、同じstoreを使う非協調のCodex processとの競合を閉じられません。`refresh_token_reused`の直接原因も確定していません。既存のCodex shellからsynthetic auth markerが見えた実測と合わせ、専用persistent `CODEX_HOME`へ変更してもshell可視性と競合を解決できるまでは採用せず、`authentication_shell_visible_risk=true`とfail-closed条件を維持します。

launcherは既存executor.run_commandを使い、shell=False、固定argv、close_fds=True、未許可pass_fdsなし、stdin/stdout/stderr契約、timeout、POSIX process group cleanup、safe diagnosticsと一時領域cleanupを維持します。失敗時はfail-closedです。

## 共通case実行

WSL2 clean checkoutからprofileを指定し、固定Skill revisionを実行します。Codex用launcherや外側bubblewrap argvを利用者が自由入力する必要はありません。profileに指定された固定実行modeだけが利用できます。

```bash
python -c 'import sys, yaml; assert sys.version_info[:2] == (3, 11), sys.version; assert yaml.__version__ == "6.0.3", yaml.__version__; print(f"Python {sys.version.split()[0]}, PyYAML {yaml.__version__}")'

# isolation evidenceとrun成果物を同じ新規output rootに保存する。
RUN_ID="tc-out-001-isolation-$(git rev-parse --short HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_ROOT=".agent-eval-runs/$RUN_ID"
python -m scripts.skills.evals.agent.isolation_probe \
  --profile .agent-eval-runs/config/profile.json \
  --agent-command-json .agent-eval-runs/config/agent-command.json \
  --output-root "$OUT_ROOT"

python -m scripts.skills.evals.agent.run \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <40文字のSkill Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root "$OUT_ROOT" \
  --agent-name codex \
  --agent-model <model名>
```

起動前にprofileとfresh isolation evidenceを照合します。合成security testが成立しない限りCodex exec、実Agent/Judge評価へ進めません。正式方式の認証可視性は残留リスクであり、今回の方式移行承認だけを実認証承認として扱いません。

受入smoke対象はTC-OUT-001、TCN-OUT-001、TC-SEM-001、WF-SEM-003です。ケースを個別実行します。Semantic caseはJudgeを別process・別outer bubblewrapで起動し、既存semantic result normalizerで判定します。--skill allは明示時だけ使います。

## 固定qa-training-store統合評価

この評価はWSL2内のclean target checkoutで`qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`のsource treeを読み取り、Checkout / Payment Web範囲の固定scenarioを最低2 attemptで実行します。target repoへcheckout、commitその他のGit mutationを行いません。Codex Agent/JudgeだけをWSL2二重bubblewrapで起動します。Codexを起動しないproduction verifier capture/replayは固定Docker verifier imageと既存`--network none`契約を維持します。

```bash
python -m scripts.skills.evals.agent.qa_training_store \
  --target-root /home/<user>/src/qa-training-store \
  --skill-revision <40文字のqa-workflow-skills Git SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --verifier-image <固定verifier image digest> \
  --output-root .agent-eval-runs/qts-baseline \
  --repeat 2
```

Runnerはtarget用sanitized workspace、synthetic baseline、Skill / source manifest、artifact contract、runtime verifier replay、workflow runtime replay、Judge evidence、workspace integrityを保存します。Artifact Judgeはcanonical artifactsと不足placeholderのみを受け取り、routing / final stdout / machine summaryは受け取りません。Workflow Judgeはrouting / final stdoutと固定machine summaryを受け取ります。二つの判定は別process・別outer bubblewrap namespace・別cwd・別一時`CODEX_HOME`で実行します。`--verifier-image`は既存verifier contractの固定digestを指定し、Codex imageへ置き換えません。

## Judge検証とSkill改善

`judge_validation`は固定scenarioの正常・限定違反fixtureを別々にJudgeへ渡します。AI生成fixtureは承認済み扱いにせず、`--approval-file`でdataset revision、reviewer、timezone付き日時、該当fixtureの固定規範根拠を指定しない限りfixtureはreview pendingです。承認行には、実際のfixtureを確認した後にそのrunの`result.json`に出力された`cases[].approval_binding`全体を`binding`として記録してください。このbindingはfixture定義、baselineとfixture成果物の内容、Judge入力、criterionと期待判定、規範revisionと参照内容を固定します。どれかが変わると既存承認は一致せず、fixtureはreview pendingになります。`binding`を持たない旧形式の承認行は読み込めますが、`legacy_unbound`として保留されます。再承認には新しいrunの成果物を人が確認し、そのrunのbindingを承認行へ記録してください。未承認fixtureを自動承認する移行は行いません。tuning proposalはtune splitの観測だけを受け取り、independent splitの期待値・判定を受け取りません。Candidate Judgeも固定fixtureで独立評価されますが自動採用しません。

`qts-judge-fixtures-v2`の`major-violation-003`は、未確定のWeb/Native間pixel parityを確定済みCheckout oracleへ昇格し、Navigation / Typographyの完全一致をWeb Checkoutの失敗条件にする`QTS-SEM-003`違反fixtureです。共有する意味・情報順と完全な視覚的一致は区別します。このfixtureは引き続き`pending_human_review`で、v1のbindingは再利用しません。`QTS-SEM-008`には新fixtureを推測で追加せず、正式なAgent成果物が得られるまでは`judge_unverified`を維持します。

```bash
python -m scripts.skills.evals.agent.judge_validation \
  --baseline-result .agent-eval-runs/qts-baseline/result.json \
  --target-root /home/<user>/src/qa-training-store \
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
  --target-root /home/<user>/src/qa-training-store \
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
