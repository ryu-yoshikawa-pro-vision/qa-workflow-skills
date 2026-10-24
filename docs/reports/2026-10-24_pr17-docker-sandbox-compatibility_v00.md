# PR #17 Docker内Codex sandbox互換性調査 v00

- **調査日:** 2026-10-24（JST）
- **対象:** `ryu-yoshikawa-pro-vision/qa-workflow-skills` PR #17 / `feat/agent-eval-runner`
- **調査開始時HEAD:** `35ea3b274d22f0d47104c6fbaa777303d9090281`
- **判定:** 既存Docker設定のまま正式起動できるとは確認できない。namespace syscallを限定許可するseccompは診断候補になるが、procfs条件とAgent shellへの権限波及が解消されず、現行Agent/Judge用profileには採用しない。

## 1. 要約

Linux Dockerを正式方式として維持する。今回の記録調査では、Docker内Codex CLI `0.163.0`の起動障害は一つの拒否で説明できず、環境ごとに少なくとも次の段階が記録されている。

1. 2026-10-23のDocker Desktop / WSL2では、CodexはAPI応答まで到達したがshell commandの起動を拒否し、診断時のbubblewrap出力は`No permissions to create a new namespace`だった。**この環境の拒否syscallは記録されていない**。同じWSL host上の`unshare --user --map-root-user true`は成功しているが、hostの成功はDocker内の成功を意味しない。
2. 以前のCodespaces Docker診断では、Docker built-in seccompが有効な条件で`clone(CLONE_NEWNS|CLONE_NEWIPC|CLONE_NEWUSER|CLONE_NEWPID|CLONE_NEWNET|SIGCHLD)`が`EPERM`となった記録がある。限定診断profileではnamespaceとtmpfs mountを通過した後、procfs mountが`EPERM`となった。これは別環境の記録であり、2026-10-23のローカルDocker原因へそのまま一般化しない。
3. Docker `systempaths=unconfined`はmasked pathsとread-only pathsの両方のconfinementを解除する。procfs回避の設定として採用すると、Dockerに与えているsystem pathの保護を広く外すため、今回の正式Agent/Judge条件には不適合と判断する。

Docker標準seccompを維持したままの起動は未達である。標準profileを基にした限定seccomp案は、namespace syscallを試験する**合成データだけの診断用container**に限れば評価候補だが、実Agentに適用できる安全な解決としては未確定である。seccompはcontainer内の全processと子孫に継承され、bwrapの初期化時だけ許可してshell起動後に取り消す制御ではない。加えて、過去の限定profileではprocfs mount自体も失敗しており、seccomp変更だけではPlanの要求を満たさない。

今回Docker設定、Agent/Judge command、Docker Desktop/daemon、capability、profile、sandbox modeは変更していない。実Agent、Judge、credential、API/model通信も使っていない。

## 2. 作業範囲と確認資料

- 作業開始時は`feat/agent-eval-runner`、HEAD `35ea3b274d22f0d47104c6fbaa777303d9090281`、tracked差分なし。既存の未追跡Docker報告2件は保持した。
- PR #17はopen、base `main`、head `feat/agent-eval-runner`。merge・close・base変更は行っていない。
- `PLANS.md`、README、[実Agent評価ランナー実装Plan](../plans/2026-10-03_132700_agent-eval-runner.md)と以下の記録を確認した。
  - [ローカルDocker評価 v01](2026-10-23_local-docker-evaluation_v01.md)
  - [WSL2 sandbox調査](2026-10-24_pr17-wsl-sandbox-investigation_v00.md)
  - [二重sandbox調査](2026-10-24_pr17-nested-sandbox-investigation_v00.md)
  - [FD・認証境界調査](2026-10-24_pr17-fd-and-auth-boundary_v00.md)
- 既存のDocker再現実験は繰り返していない。ignored `.agent-eval-runs`配下のraw診断ファイルはこのcheckoutで見つからず、以下のsyscall詳細は既存レポートとPR履歴に保存された記録から引用した。再解釈できない点は未確定のまま記録する。
- Dockerfile、launcher、probe、workspace、executorの現行経路と関連testを静的に確認した。既存修正に新たな欠陥は見つけていない。

## 3. Docker障害の証拠と確定範囲

| 環境・条件                                                                                                 | 記録されている結果                                                                                                                                  | 確定できること                                                                                 | 確定できないこと                                                                                      |
| ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Docker Desktop 4.96.2 / Engine 29.9.2、Ubuntu 24.04.4 WSL2、Codex 0.163.0                                  | API応答後、Codex shellが起動前に拒否。bubblewrapは`No permissions to create a new namespace`。WSL hostの`unshare --user --map-root-user true`は成功 | host kernel上のuser namespace機能自体は利用可能。Docker container内ではsandbox起動できなかった | この実行で拒否された個別syscall、seccomp以外の寄与、AppArmor等の実効LSM状態                           |
| Codespaces Docker Engine 29.8.0-1、built-in seccomp、`--cap-drop=ALL`、`no-new-privileges`、read-only root | namespace flag付き`clone`が`EPERM`。限定profileでnamespace・tmpfs mount後、procfs mountも`EPERM`                                                    | namespace cloneとprocfs mountの両方に別の障害段階があった                                      | CodespacesとDocker Desktopのローカル実行が同じ原因であること。procfs拒否が全Docker hostで再現すること |
| WSL2 host-native Codex/bwrap                                                                               | user/PID/network namespace、procfs mountが成功した過去記録あり                                                                                      | WSL2 host側でのbwrap起動条件                                                                   | Dockerのcontainer seccomp、mount mask、UID/GID mappingを通過できること                                |

当該traceに保存されたprocfs mount syscallは次のとおり。

```text
mount("proc", "/newroot/proc", "proc", MS_NOSUID|MS_NODEV|MS_NOEXEC, NULL) = EPERM
```

2026-10-23ローカルDockerの実行はmodel API応答とsandboxed shell実行を区別している。API応答だけをCodex shell成功や隔離成立とは扱わない。既存isolation probeのsentinel・mount結果もDocker mount境界の証拠であり、Codex内bwrapの証拠ではない。

Codespaces診断では`/proc/self/mountinfo`に`/proc/acpi`、`/proc/interrupts`、`/proc/kcore`等のDocker system-path mask/overmountが見えた記録がある。Linux `/proc`資料と整合する要素だが、今回の記録だけで、それが個別の`mount(proc)`拒否の唯一の原因と断定しない。Docker built-in seccompを一部変更してもprocfs mountが成功しなかった、というのが確定範囲である。

## 4. Codex CLI 0.163.0の実行要求

Codex公式tag [`rust-v0.163.0`の`bwrap.rs`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)では、filesystem-restricted profile用bwrap argvを組み立てる。読取制限・workspace-write時のsourceでは次の構成が確認できる。

- 新しいuser namespaceを明示し、その内側でmount・他namespaceを設定する。Codex sourceのcommentは、container outer namespaceのambient `CAP_SYS_ADMIN`なしで残りのnamespaceを作る目的を記載する。
- PID namespaceは通常作成する。信頼済み起動設定でPID namespace継承を選んだ場合だけ省かれる。IPC namespaceは作成する。
- network namespaceは実効network policyがisolationを要求する場合に作成する。実際に必要なflagは固定したprofileの値で確認し、`workspace-write`という名前から決めつけない。
- restricted filesystemでは新しいtmpfs root、`/dev`、許可rootのbind/ro-bind、deny-path mask、`/proc` mountを組み立てる。bwrap自身はmount namespaceを使う。
- sandbox command側ではcapabilityをdropする。

Codex公式tag [`linux_run_main.rs`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/linux_run_main.rs)にはproc mount preflightがある。bwrapの`Can't mount proc on /newroot/proc`とpermission系errorを認識すると、`mount_proc=false`にして再実行する経路がある。このfallbackがshell commandを動かしても、今回の受入条件である**新procfs mountの成立**は満たさず、同じprofileの合格証拠にはできない。Docker namespaceの最初の失敗を解決するものでもない。

### syscallの確認範囲

| syscall / 操作                     | 記録・sourceから分かること                                                                                                                              | 判定                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `clone`                            | Codespaces診断で複数の`CLONE_NEW*`を含む呼出しと`EPERM`を記録。Codex sourceのbwrap argvはuser/IPC/PIDとpolicy依存network namespaceを要求                | そのCodespaces実行では拒否確認。ローカルDockerの拒否syscallとしては未確定       |
| `clone3`                           | Docker標準profileは、capability条件に応じて`ENOSYS`を返しglibc等の`clone` fallbackを可能にする仕様がある                                                | 対象smokeでの実呼出し・拒否は記録されていない。今回の原因とは断定しない         |
| `unshare`                          | userns/namespaceを組み立てる機能上の関連はあるが、対象Codex実行の拒否syscallとして記録されていない。hostの`unshare`成功とcontainer内のbwrap syscallは別 | 必要性・拒否は未確定。traceなしに許可対象へ加えない                             |
| `mount`                            | 限定profileの診断にtmpfs mount成功とprocfs mount `EPERM`の記録。Codex sourceはtmpfs・bind・ro-bind・proc・maskを要求                                    | mount系permissionが必要。ただしDocker seccomp変更だけでprocfsが直る証拠はない   |
| `umount2`、`setns`、`pivot_root`等 | 既存ログに該当する失敗の記録なし                                                                                                                        | 必要とも拒否原因とも断定しない。追加するなら新しい診断実行で実syscallを記録する |

## 5. Docker制約との照合

- Docker seccompは既定でallowlistであり、未許可callは`SCMP_ACT_ERRNO`となる。Docker文書は`clone`のnamespace flag、`unshare`、`mount`、`umount2`などを制限対象として説明する。[Docker seccomp仕様](https://docs.docker.com/engine/security/seccomp/)
- Mobyのdefault profileでは、namespace flagのない`clone`と`clone3`の互換挙動を区別し、mount関連syscallを`CAP_SYS_ADMIN`条件へ結び付ける。実際の`builtin`内容はDocker Engine/runtimeの版に対応させて記録する必要がある。[Moby default profile](https://github.com/moby/moby/blob/master/vendor/github.com/moby/profiles/seccomp/default.json)、[Docker Engine 23.0 release note（clone3 fallback）](https://docs.docker.com/engine/release-notes/23.0/)
- Planの`--cap-drop=ALL`を保つ。Codex sourceの設計上は、新しいuser namespace内に閉じたcapabilityで残りのsandbox mountを行う想定で、outer containerへ`CAP_SYS_ADMIN`を追加する根拠はない。実環境のuserns・UID/GID mapping・kernel policyがその操作を許すかは別途確認が要る。
- `--security-opt=no-new-privileges`は維持する。Linux kernel資料によれば、これは`execve()`によるsetuid/setgid/file capability等のprivilege gainを止める継承属性で、namespace・mount拒否の原因としては確認されていない。これを外す根拠はない。[Linux kernel no_new_privs](https://docs.kernel.org/userspace-api/no_new_privs.html)
- Dockerの`--read-only` rootは維持する。Codex bwrapは自身のnamespaceにtmpfs root、bind mount等を作るためmount syscallとnamespace能力が必要だが、外側rootfsをread-writeにする変更は要件上不要であり、診断証拠にもない。
- Agent launcherは`--user <host uid>:<host gid>`を付け、mount ownershipとoutput専用bindの書込可否を保つ。Docker daemonのuserns-remap/rootless設定が異なるとcontainer内UID/GIDの見え方が変わるため、profile変更時は`id`、`/proc/self/uid_map`・`gid_map`とoutput mountの実効ownerを合成データで記録する。既存source workspaceをchownしない。
- Docker system-path maskについて、CLI文書の`systempaths=unconfined`はmasked pathsおよびread-only pathsのconfinementを一括で解除すると説明する。[Docker CLI `systempaths`](https://docs.docker.com/reference/cli/docker/container/run/#security-opt)。既存Docker containerで確認されたmaskを広範囲に外すため採用しない。AppArmorについて、Codespaces旧記録では実効`unconfined`・deny証拠なしだが、ローカルDocker Desktopの実効LSM/audit状態は確認されておらず未確定とする。

## 6. 限定seccomp profileの成立性

### 技術的には診断候補を作れる

正確な対象Engineのbuiltin profileを基礎にし、少なくとも次を個別に評価するprofileが候補となる。

1. `clone`について、実測で必要となったnamespace bitだけをmasked-argument条件で許可する。Codex実効policyが`CLONE_NEWNET`を要求しない場合は加えない。
2. `unshare`はCodex/bwrap実traceで必要性とflagが確認されたときだけ追加する。
3. bwrapのtmpfs・bind/ro-bind・maskの初期化に必要と確認したmount操作を評価する。`clone3`のflag pointer構造をseccompが読み取れないため、無条件allowにはせず、まずdefaultの`ENOSYS` fallbackが実際のCLIで成立するか確認する。
4. `mount`のsource/target/typeはpointer文字列であり、通常のseccomp argument filterでは`"proc"`や`/newroot/proc`を読み取って限定できない。flag値を制約してもfilesystem typeやmount先の文字列は限定されない。

これはsyscall名が数個だから安全、とは言えない。mount・namespace syscallは最終的にbwrapの初期化だけでなく、同じcontainerにいるCodex parent、shell child、孫processに適用される。Seccomp BPFはprocess treeへ継承され、filterを追加して狭めることはできても、既存filterの許可をchildだけで取り消すことはできない。[Linux kernel seccomp filter](https://docs.kernel.org/5.3/userspace-api/seccomp_filter.html) Codex 0.163.0のbwrap argvでは`--disable-userns`を渡しておらず、Codex内seccomp sourceは主にnetwork制御用で、mount操作だけをshellから除去する根拠は確認できない。

### procfs条件が別に残る

過去の限定profileはnamespaceとtmpfsまで進んだ一方、procfs mountを通さなかった。Codexのno-proc fallbackは実行開始の可能性を残すだけで、新しいprocfsを要求する本検証条件は満たさない。Docker CLIの既知の`systempaths=unconfined` workaroundは、必要な箇所だけを選択的に外す指定ではなく、masked pathsとread-only pathsをまとめて無効化する。

したがって、**限定seccompだけで現行受入条件を満たせるとは判定できない**。seccomp変更を適用するだけのテストは、実Agent受入ではなく、認証・Evaluator資料・実targetを一切渡さない合成診断containerに限定すべきである。実Agent profileとして採用するには、namespace/mount capabilityをshell childからどう制限するか、およびDockerのprocfs maskを安全に保ったままfresh procfsを作れるかの両方を先に解決する必要がある。

## 7. 設定案と安全性判定

### 今回の判断

- `seccomp=unconfined`、`--privileged`、`--cap-add=SYS_ADMIN`、sandbox bypassは候補外。
- `no-new-privileges`、`cap-drop=ALL`、read-only root、workspace/output/homeのmount境界は維持する。
- `systempaths=unconfined`はmasked/readonly system pathを一括解除するため不採用。
- Dockerのdaemon既定profileやAppArmor、uid mappingは変更しない。
- 現行Agent/Judge containerに限定profileを適用しない。今回はprofile JSONも作成しない。

### 後日、承認された場合だけ調べる診断案

セキュリティ審査が許可した場合、固定したDocker Engineのbuiltin profileから差分を生成し、profile SHA-256、対象Engine、architecture、Codex CLI版、実効Codex設定をprovenanceへ固定する。Agent専用の**synthetic diagnostics** containerに限って適用し、`--cap-drop=ALL`、`no-new-privileges`、`--read-only`、`--network=none`、synthetic `/tmp`以外のhost bindなしを維持する。初期段階で実auth、Agent/Judge command、Evaluator sentinel、QTS targetは渡さない。

診断でfresh procfsが成立しない、shell childがnested userns/mountを使って境界を変えられる、mount/write/credential/path/FD/network negative testのいずれかが失敗する場合は、そのprofileをAgent/Judgeに適用せず停止する。Docker CLIの標準`docker run` interfaceでsystem-path maskの一部だけを変更できると仮定しない。別のdaemon/API設定が必要なら、設定差分を示して管理者・ユーザーの明示承認を得る。

## 8. 変更対象と現行修正の確認

現headでコード変更が必要な不具合は見つけていない。以下の対象ファイルは今回変更しない。

| ファイル                         | 今回     | 後日seccomp診断を正式化する場合の確認点                                                                                                                              |
| -------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `codex-agent.Dockerfile`         | 変更なし | image内容とCLI versionは不変。seccomp profileはDocker実行時条件なのでimageへ埋め込まない                                                                             |
| `codex_docker_launcher.py`       | 変更なし | Agent commandだけへ承認済みprofileを加えるなら、profile path/hashと`--security-opt`の許可値を厳密照合。秘密や任意profile pathをargvへ受け入れない                    |
| `codex_judge_docker_launcher.py` | 変更なし | Judgeはtools/shell無効契約。Agent向けのnamespace/mount拡張をJudgeに共有しない。Judge実行にbwrapが不要なことを実証できなければ、標準profile維持のまま別途停止判断する |
| `isolation_probe.py`             | 変更なし | 承認済みprofile hash、Engine、seccomp/capability/NNP、namespace/procfsと既存mount negative testを同一command fingerprintへ結び付ける                                 |
| `workspace.py`                   | 変更なし | 今は`cap-drop=ALL`、NNP、read-only、mount集合をstrictに検証する。将来も既知profileだけ許可し、`unconfined`やsystempaths解除を拒否する                                |
| `executor.py`                    | 変更なし | `close_fds=True`、空の`pass_fds`、POSIX process group、Windows run専用TEMP root cleanupを維持                                                                        |
| `README.md`                      | 変更なし | security review後に正式採用となる場合だけ、profile hash・必要Engine条件・Agent/Judge差を記述                                                                         |

既存修正の関連経路を静的に再確認した。

- `executor.py`の`Popen`は`shell=False`、`close_fds=True`、専用stdin/stdout/stderr pipeで起動し、暗黙の`pass_fds`はない。`test_executor.py`には未指定FD sentinelのnegative testとWindows timeout後auth HOME回収testがある。
- Windows timeoutはprocess tree終了後にexecutor所有のrun-specific temporary rootを親がcleanupする。既存cleanup testは合成認証markerのみを使用する。
- QTS Agentは実行metadataを`agent-execution.json`へ先に保存し、cleanup失敗を含むattemptにも参照path/statusを保存する。`test_qa_training_store.py`のcleanup failure回帰testがその記録を照合する。
- AgentとJudgeは別command、独立process/containerと別の一時`CODEX_HOME`を使う。Judge専用launcherはtool/MCP/Skillを空にするprofileを検証し、Agent用のseccomp案を共有していない。
- RunnerはAgent non-zero/timeout/cleanup failureをexecution errorとして保存し、Judgeを起動しない。Skill品質FAILとは区別する。

これらに対する修正追加は不要と判断したため、今回テストを再実行・追加していない。

## 9. 次回の段階的検証手順

以下はDocker設定変更の安全性審査と明示承認が得られた場合の**準備手順**であり、今回実行した手順ではない。image ID、Docker Engine/runtime、profile hash、model ID、credentialを推測で埋めない。

1. **合成containerのpreflight:** 実行直前に対象daemonのEngine/client/kernel、builtin seccomp状態、AppArmor/LSM実効値、userns状態、`CapEff`、`NoNewPrivs`、UID/GID mapping、mountinfoを記録する。固定Docker imageのimmutable IDをその時点で取得し、使うprofile hashと紐付ける。
2. **namespace/procfsの最小確認:** synthetic sentinelだけの読み取り専用rootで、必要なuser/mount/PID/IPCと実効network policyのnamespaceを確認し、Codex指定のprocfs mount、`/proc/self`とnamespace PIDの対応を確認する。exit codeだけで合格にしない。
3. **Codex 0.163.0認証不要sandbox smoke:** model/API authなしで`codex sandbox`のecho smokeを行い、実行したsandbox profileとbwrap path/versionを記録する。自動no-proc fallbackへ進んだ場合は新procfs必須条件で失敗扱いにする。
4. **negative test:** synthetic sentinelのoutside/Evaluator-only read、source write、output-only write、symlink、`/proc/self/fd`・`/dev/fd`、余分なFD、未許可mount、nested namespace、process visibility、network経路を個別に確認する。拒否証拠、mountinfo/namespace inode、FD一覧、container inspectを照合し、shell childが追加namespace/mountを作れる場合はprofileを却下する。
5. **isolation probe:** 同じprofile/command/image fingerprintで既存probeを実行し、Docker inspect mount集合、read-only root、cap-drop、NNP、Evaluator sentinel拒否、workspace/output境界が一致することを確認する。
6. **Agent/Judge条件固定:** Agent用profileとJudge用標準profileを分離し、profile JSON hashを含む非秘密runtime fingerprintを固定する。Agent/Judge双方のtimeout/cleanup、`close_fds=True`、profile/tool/network条件を再照合する。
7. **実Agent認証/API通信:** 前段の全negative testが受入され、別途承認された場合だけ実認証とAPI通信を確認する。秘密内容・hash・raw環境を保存しない。
8. **共通4ケース:** `TC-OUT-001`、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`を個別runとして実施する。
9. **QTS独立2 attempt:** 固定target revisionで別々の実行環境・output・provenanceを使い2 attemptを行う。
10. **fixture準備・承認:** 実生成物に対応するfixtureを準備し、承認者が対象artifact・criterion・mutation・splitとのbindingを確認する。自動的に承認済みへ変更しない。
11. **Judge独立評価:** 承認済みfixtureだけを、Agentと別process/containerのJudgeで検証する。shell toolを有効化せず、結果をfixture bindingへ紐付ける。
12. **条件が成立した場合だけSkill改善:** 同一条件比較、再現性、原因帰属、承認済みJudge根拠、独立回帰が揃ったcaseだけ改善・再評価する。

## 10. Planとの差分、受入残課題、承認事項

### Planとの差分

現行PlanのLinux Docker、read-only root、`cap-drop=ALL`、`no-new-privileges`、固定image、限定mount、FD非継承、Agent/Judge分離は変更しない。PlanとREADMEは今回編集していない。

もし将来seccomp profileを使うなら、seccomp profile SHA-256・Docker Engine/architecture・有効syscall条件・`clone3` fallback・procfs方式を実効profile fingerprintと受入Planへ追加する必要がある。`systempaths=unconfined`またはprocfsを諦めるfallbackを正式条件にする変更は、現行のsystem path保護/procfs検証条件からの差分であり、Planの明示改訂とレビューが必要である。

### 正式受入に残る条件

- Plan適合のDocker内Codex sandbox起動・fresh procfs mount
- 同じAgent権限でのEvaluator-only read拒否、source write拒否、output-only write、symlink/FD経路、禁止mount、process visibility、network policyのnegative test
- Docker socket、host home、元target、Evaluator資料がcontainerにmountされないこと
- Codex CLI 0.163.0の実Agent shell実行とprofile fingerprint
- 共通4ケース、QTS独立2 attempt、実生成物に基づくJudge fixture承認・独立Judge検証
- fixture承認11件と`QTS-SEM-008`専用違反fixture、実Agent baseline、承認binding。人間承認や実Agent/Judgeは今回実行していない

### ユーザー承認が必要な操作

- Agent containerにカスタムseccompを適用すること
- Docker CLI/daemon/APIで`maskedPaths` / `readonlyPaths`、procfs、userns/UID mapping、AppArmor/LSM、capability条件を変えること
- Docker Desktop/WSL2やdaemon/runtimeの設定変更
- 変更profileで実Agent containerを起動すること
- 実credential・実model APIを使う正式Agent/Judge評価

## 11. 最終結論

既存Docker標準条件のCodex shellはnamespace初期化段階で失敗する。過去の別Docker環境ではnamespace flag付き`clone`拒否を特定し、診断profileでそこを越えてもprocfs mountが`EPERM`となった。従って、通常profileの再試行や`clone`だけの許可では解決しない。

限定seccomp profileは診断の入口になり得るが、procfsとsystem-path maskが残り、許可したmount/namespace syscallはbwrapだけでなくAgent shellにも継承される。Dockerの`systempaths=unconfined`は影響範囲が広く、採用しない。**現在確認できる範囲で、現行受入条件を保ったまま安全に適用できるDocker設定案は未確定である。** 専用の per-container system-path調整やshell側のmount syscall制御などを前提にするなら、それは現行Docker launcherだけの小修正ではなく、Planとセキュリティ境界の審査が必要となる。

安全性審査で認められた新しい設定条件が用意されるまでは、同じDocker条件でのCodex smokeを繰り返さず、実Agent/Judge評価を開始しない。
