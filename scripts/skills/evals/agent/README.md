# 実Agent評価ランナー

このランナーは、指定した`qa-workflow-skills` Git revisionのSkill packageを一時領域へ展開し、実Agentで生成した結果を固定Evaluatorの既存grader / Judgeで評価します。評価結果と機械判定をattempt単位で保存します。既存Skillの通常実行経路やSkill packageの配置規則は変更しません。

Codex Agent / Judge / RepairはWSL2 Ubuntuの二重bubblewrap方式で起動します。実行profile、実効command、run結果は秘密情報を含めず、run単位の`.agent-eval-runs/`へ置きます。このdirectoryはGit管理対象外です。通常CIは外部LLMを呼ばず、fake Agent / Judgeの契約テストだけを実行します。QTSのCodexを使わないdeterministic verifierは既存の固定Docker image契約を維持します。

## 2026-10-26 現在の認証・隔離状態

固定Codex CLI `0.163.0`のnamed permissions profileを使う正式な合成launcher経路では、Agent/Judge/Repair shellからsynthetic `auth.json` markerを直接・alias・procfs・host path・他attempt path・environment・FD経由で読めず、親Codex processからは読めることを確認しました。現行コードの`authentication_shell_visible_risk=false`はこの合成境界検証だけを示し、実認証fileを使った試験や実モデル通信の証明ではありません。

認証storeは今もattempt専用`CODEX_HOME`へcopy後、終了時にcleanupします。Codex CLIがrefresh後の状態をこのcopyへ保存しても次attemptへ引き継がれないことをsynthetic fake-child testで再現しています。固定CLIのrefresh排他は同一`AuthManager`内です。`file`にはprocess間lock・atomic replacementがなく、`keyring`もprocess横断refresh lockを提供せず、`auto`はkeyring error時fileへfallbackし、`ephemeral`はprocess終了後に残りません。専用永続`CODEX_HOME`やrunner内lockだけでは、外部の非協調Codex processとの競合を解決しません。

したがって`authentication_refresh_persistence_unresolved=true`と`authentication_process_concurrency_unresolved=true`を維持し、launcherはAgent/Judge/Repairを認証確認・copy・Codex起動前にfail-closedにします。過去の`refresh_token_reused`の直接原因は確定していません。固定CLIの保存実装は[auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)と[storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)、現状と停止条件は[調査・検証報告 v06](../../../../docs/reports/2026-10-26_pr17-chatgpt-auth-recovery_v06.md)および[PR #17 現在状態報告](../../../../docs/reports/2026-10-26_pr17-current-status_v00.md)を参照してください。

`codex login status`は保存済み認証状態を読み取るだけでrefreshを呼びません。Codex source harnessを使う合成refresh試験はまだ実施していません。通常の`codex exec`からrefreshを誘発する試験はmodel requestと切り離せないため行わず、実認証、login、モデルAPI、TC-OUT-001も安全条件と明示承認が揃うまで実施しません。

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
- 固定Codex CLI 0.163.0のinner sandboxにはmodeごとのnamed permissions profileを使います。Agent/Repairは`:workspace`、Judgeは`:read-only`を継承し、全modeで`/codex-home/auth.json`を`deny`、networkを無効にします。Repairのworkspace rootは対象Skillだけです。`codex exec --sandbox ...`はlegacy sandbox設定を優先してnamed profileを上書きするため付けず、`default_permissions=qa_eval_<mode>`を一時`config.toml`とCLI `--config`の両方で指定します。fixed CLIのprofile inheritanceとbwrap deny maskを使い、実効shellからのread拒否を確認します。[permissions resolver](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/config/src/permissions_toml.rs)と[Linux sandbox](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)を参照してください。
- formal smokeはsynthetic `auth.json`を用い、Agent/Judge/Repairそれぞれでstore path、symlink alias、`/proc/self/root`、`/proc/1/root`、host側store path、他attempt store、environment、可視process FD経由のreadを値を出さずbooleanだけで検査します。外側Codex親processからstoreを読めることも別に確認します。HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a`のfresh schema 2 evidenceでは、read拒否を含む16 required checksがすべてtrueで3 modeすべてverifiedでした。これは実認証fileの検証ではありません。
- attempt専用`CODEX_HOME`へのauth copyと終了時cleanupは維持しています。refresh後のcopy更新が次attemptへ残らないことはfake-child unit testで再現済みです。固定CLI file backendは同じ`CODEX_HOME/auth.json`へtruncate/write/flushしますが、process横断lockやatomic replacementを持たず、refresh mutexも同一`AuthManager`内です。`file`は部分更新と競合、`keyring`はprocess間refresh lock欠如、`auto`はkeyring load/save error時のfile fallback、`ephemeral`はprocess終了後の消失という制約があります。専用永続storeやkeyringへ切り替えていません。refresh永続化と非協調process競合は未解決のためproduction launchは全mode fail-closedです。詳細は[調査報告v06](../../../../docs/reports/2026-10-26_pr17-chatgpt-auth-recovery_v06.md)および[現在状態報告](../../../../docs/reports/2026-10-26_pr17-current-status_v00.md)を参照してください。
- Codex CLI固有設定は固定profileから検証し、MCP、外部指示、global config、追加Skill、web検索を無効にします。秘密値・生認証情報・秘密hashをargv、environment、profile、provenance、raw JSONLへ保存しません。
- Codex source / 固定targetの既存ファイル・directoryはouter mountで個別にread-only bindします。Codex workspace-writeがsandbox準備で必要とするattempt-local workspace root、`.git`、`.codex`だけは一時領域として分離し、許可outputとRepair対象Skill以外の既存sourceは変更できません。実行前後manifestを比較し、単にworkspace全体をwrite可能にする方式は不適合です。
- 通常CIは外部LLM、実認証、live Codex execを呼びません。fake Agent/Judge contract testsを実行します。実Codex sandbox smokeはWSL2のformal launcher経由で無認証のsynthetic inputだけに実行します。

実効profileはJSON schema version 2です。Agent / Judge model、timeout、reasoning、sandbox、approval、network、tools、MCP、Skill rootsに加え、runtimeにはWSL2実行mode、Codex package source/version/SHA-512、Codex binaryとbwrapのSHA-256、outer/inner argv・mount・network fingerprint、probe version、evidence fingerprint、依存versionを記録します。secret自体は記録しません。認証方式はprofileから切替できず、launcherがChatGPT loginに固定します。run observationsには認証方式・確認状態・CLI versionだけを記録し、認証fileの内容やhashは記録しません。旧Docker profileは読み取り用に保持しますが、新方式と直接比較できません。

Profile verificationは同じEvaluator revision、profile、Agent/Judge/Repair mode、binary digest、実効argv・mount/network、probe versionに結び付くisolation.jsonを要求します。従来の15 required checksに、合成auth markerのinner shell read拒否を追加した16件すべてが必要です。この追加checkはstore本体、host path、他attempt path、environment、可視process FDを対象にし、秘密値は証拠に残しません。Agent/Judge/Repairそれぞれの本番`codex exec` argvもfingerprintし、attemptごとに変わる`--output-last-message`のファイル名だけを正規化します。probeは本番`codex exec`やモデル通信を実行しません。evidence欠落、旧Docker evidence、別mode evidence、fingerprint不一致、必須negative test未確認の場合はisolation_unverifiedとして起動を拒否します。

## WSL2通常ターミナルでの検証とfresh evidence

Codex開発sandbox内でWSLのAF_UNIX socket bindやrepository testが`EPERM`になる場合、隔離やHookを変更せず、通常WSL2 Ubuntu hostで同じ検査を実行します。sandbox内Deterministic suiteの4 failure / 1 errorとAF_UNIX `EPERM`は環境固有で、通常WSL2での同じ293件suiteはPASSしました。HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a`ではfixed-runtime formal launcher integration 1 testもPASSし、fresh schema 2 probeは16/16 checks、3 mode verified、model API未使用でした。これは実認証やrefresh保存・非協調process競合の証明ではありません。evidence pathとfingerprintsは[PR #17 現在状態報告](../../../../docs/reports/2026-10-26_pr17-current-status_v00.md)を参照してください。文書更新後のcommitではclean final HEADに対してprobeを再生成します。

```bash
cd /home/sella/src/qa-workflow-skills-pr17-auth-20261025
source ~/.venvs/qa-workflow-skills/bin/activate
export QAEVAL_CODEX_RUNTIME_ROOT=/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final
python --version
python -c 'import yaml; print(yaml.__version__)'
TMPDIR=/var/tmp python -m unittest discover -s tests/skills/evals/deterministic -p 'test_*.py' -q
TMPDIR=/var/tmp QAEVAL_RUN_WSL2_INTEGRATION=1 python -m unittest scripts.skills.evals.agent.tests.test_codex_wsl2_bwrap_launcher.CodexWsl2LauncherIntegrationTests.test_formal_launcher_modes_fd_network_paths_and_timeout_cleanup -v
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

実行前に固定runtime path、Codex CLI/package digest、bundled bwrap digestが`verify_runtime()`で一致することが必要です。probeは`codex sandbox`によるAgent/Judge/Repair smoke、従来の15件と追加した認証可視性checkを含む16 required checks、modeごとのargv/profile fingerprintを記録します。`model_api_used=false`を確認し、認証status確認・`codex exec`・モデルAPIは呼びません。auth read拒否checkがすべてtrueの場合だけ`authentication_shell_visible_risk=false`となり、失敗または未実行ならtrueです。evidenceの`evaluator_revision`はclean checkoutのHEADと一致し、16 checksと3 mode evidenceがすべて`verified`でなければ受入に使えません。refresh永続化と非協調Codex processとの競合は別の未解決条件で、成功evidenceだけでは解消されません。

2026-10-26のHEAD `e87a4890514af6bff09b90bb180e4dcd9c3fddb7`で14/16 checks、全mode unverifiedだったprobeは、named permissions profileのauth read-deny修正前の履歴です。その後HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a`でfresh schema 2 probeを再実行し、16/16 checks true、Agent/Judge/Repairすべてverified、`model_api_used=false`を確認しました。evidenceは`.agent-eval-runs/pr17-isolation-a960-20261026T132518Z/isolation.json`にあります。後続のcommitには流用せず、最終文書commitに対して再生成します。

## 合成認証データによる検証範囲

launcher unit testはsynthetic `auth.json` markerのcopy、permission、cleanup、出力redaction、ChatGPT login statusの分類を検証します。copy/delete方式でfake childがattempt側だけを更新しても次attemptに継承されないことを再現します。これはCodex CLI自身のrefresh成功を証明しません。fresh formal evidenceではnamed profileによりsynthetic markerのread拒否をAgent/Judge/Repairの正式二重sandbox経路で検査し、read可能、alias/proc rootから到達可能、host/other-attempt path visible、environment/FD leakageのいずれかで失敗した場合はmodeをunverifiedにします。`_prepare_codex_home()`はsource `auth.json`をattempt専用homeへcopyし、cleanup時にそのhomeを削除するため、refresh後のcopy更新が次attemptへ残る保証はありません。

合成検証では、固定CLIを呼ばないunit testでsource markerとattempt copyを作り、fake childがcopyだけを更新した後のcleanupと次attemptで、source markerが不変かつ更新が引き継がれないことを再現しています。formal launcherは同じ`/codex-home/auth.json` mountのsynthetic markerを使い、Agent/Judge/Repairのinner shellからのread拒否をbooleanだけで記録します。runner内協調lockは外部の非協調Codex processを制御できないため追加していません。fake child試験はrunner file操作のみを検証し、固定Codex CLI自身のOAuth refreshやprocess間排他の証明にはなりません。実auth fileや実tokenは使いません。

固定Codex CLI `0.163.0`の公式実装ではrefreshの同期は同一`AuthManager`内で、成功tokenは選択中のstorage backendへ保存後reloadされます。file storageは`auth.json`をtruncate/write/flushし、process横断lockやatomic replacementを持ちません。keyring modeはkeyringへ保存し、`auto`はkeyring操作失敗時にfileへfallbackし、`ephemeral`はprocess内memory storeです。いずれも非協調Codex processとのrefresh競合を解決しません。attempt-local copyによる更新喪失はsynthetic runner testで確認しましたが、`refresh_token_reused`の直接原因は未確定です。named profileによるsynthetic shell read-denyはformal evidenceで確認済みです。更新永続化と全process競合が未解決なのでlauncherは全modeをfail-closedにします。

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

起動前にprofileとfresh isolation evidenceを照合します。合成security testが成立しない限りCodex exec、実Agent/Judge評価へ進めません。現在はfresh isolation checksが通過していますが、認証refresh永続化とprocess間競合が未解決のためlauncherがfail-closedです。実認証fileを使った確認と今回の方式移行承認を混同しません。

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
