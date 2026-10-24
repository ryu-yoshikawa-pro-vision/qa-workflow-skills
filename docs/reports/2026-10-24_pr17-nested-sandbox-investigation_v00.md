# PR #17 二重sandbox調査結果 v00

実施日: 2026-10-24（JST） / 対象branch: `feat/agent-eval-runner` / 調査対象revision: `cfb3d26f96e4c394b32e53b7d8ad79188192af28`

## 判定概要

**B：二重sandboxの通常起動と合成ファイルの読み取り隔離は成立したが、継承file descriptorを使った外側mountの迂回が再現した。**
親processからFDを渡さない起動（`close_fds=True`）では、外側bubblewrap内でCodex CLI `0.163.0`の`:read-only`と`:workspace`が動き、今回指定したpath・symlink・procfs・通信probeは通過できなかった。一方、outside sentinelを開いたFDを意図的に子へ渡すと、sentinelを`/proc/self/fd/4`から読めた。外側bubblewrap自体は継承FDを閉じないため、FDを必ず閉じる起動契約を含めない限り、要求された全negative testが成立したとは判定できない。

この結果は合成データだけを使った認証なし技術検証であり、正式なAgent受入ではない。現行PlanのDocker方式は変更せず、実Agent、実Judge、model/API呼出しは行っていない。

## 1. 初期状態と実験範囲

開始時のlocal HEADと`origin/feat/agent-eval-runner`はともに`cfb3d26f96e4c394b32e53b7d8ad79188192af28`だった。PR #17はopen、baseは`main`。既存の未追跡Docker報告2件と過去の`.agent-eval-runs/` evidenceは保持した。

実験では、通常ユーザーの既存WSL2 Ubuntu、Codex CLI `0.163.0`、同梱bubblewrap、一時ディレクトリ、合成workspace・auth marker・sentinelだけを使用した。実認証、API key、`codex exec`、正式評価データ、実Judge、秘密ファイル、sudo、Docker設定変更は使用していない。

## 2. 実行環境と固定revision

| 項目                  | 確認値                                                                                                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Evaluator branch/HEAD | `feat/agent-eval-runner` / `cfb3d26f96e4c394b32e53b7d8ad79188192af28`                                                              |
| WSL                   | Ubuntu 24.04.4、WSL2 kernel `6.18.54.1-microsoft-standard-WSL2`                                                                    |
| 実行ユーザー          | uid/gid `1000/1000`、通常ユーザー                                                                                                  |
| Python                | system Python `3.12.3`                                                                                                             |
| Codex CLI             | `codex-cli 0.163.0`、Linux x64 npm package                                                                                         |
| package SHA-512       | `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3` |
| bwrap                 | Codex package内の`codex-resources/bwrap`、表示名`bubblewrap built for Codex`                                                       |

packageは公開npm tarball `https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz`から取得し、上記SHA-512を照合した。実験用bundleとログはローカルの`.agent-eval-runs/pr17-nested-sandbox-20261024/`に保存した。主な記録は`nested_sandbox_probe.py`、`nested-sandbox-results.json`、`nested-sandbox-results-fd-injected.json`、`package-download.json`である。これらはgitignore対象で、認証情報を含まない。

## 3. 外側bubblewrapの構成と再現手順

外側bubblewrapは`--tmpfs /`でrootを作り、必要なbash、echo、Python、共有library、Codex CLI、同梱bwrap、probe、合成auth markerだけを明示的にbindした。`--dev /dev`、`--proc /proc`、`--tmpfs /tmp`を使い、environmentは`--clearenv`後に短いLinux専用`PATH`等だけ設定した。ホストの`/`、`/home`、`/mnt/c`、実Evaluator checkoutはmountしていない。

合成workspaceだけを`/workspace`へ書き込み可能でbindし、`input.txt`を個別にread-only bind、`.qa-eval-output`だけを書き込み可能な出力先とした。outside sentinelはWSL側`/var/tmp`、Windows sentinelはcheckout下の実験用合成ファイルに置いたが、どちらも外側へbindしていない。Codex homeには合成markerだけをread-onlyで`/tmp/codex-home/auth.json`へbindした。

外側user namespace、user+PID namespace、user+PID+network namespaceを順に起動し、各段階でmount namespaceとprocfsも確認した。全段階が成立した後に次を実行した。

```text
codex sandbox --permission-profile :read-only -- /bin/echo sandbox-ok
```

境界検査は、Codex profile内でbashと`python3 -I -S`の合成probeを起動した。保存済みone-off harnessを再実行するコマンドは次のとおり。

```powershell
wsl.exe -d Ubuntu -- /usr/bin/python3 -I -S /mnt/c/Users/sella/Documents/qa-workflow-skills/.agent-eval-runs/pr17-nested-sandbox-20261024/nested_sandbox_probe.py
```

各stageの実argv、stdout、stderr、exit code、namespace ID、mount情報は`nested-sandbox-results.json`に保存した。再実行には同じ公開packageの取得・hash照合と、一時pathだけを使うprobe環境の再作成が必要である。

## 4. 外側namespace・pathの結果

| 検査                       | 結果                                                              |
| -------------------------- | ----------------------------------------------------------------- |
| user namespace             | 成功。`uid_map`は`1000 0 1`                                       |
| PID namespace              | 成功。`/proc/1/comm`は`bwrap`                                     |
| network namespace          | 成功。外側のTEST-NET接続は`ENETUNREACH`                           |
| mount namespace / procfs   | 成功。`/proc`はprocfsとしてmountされ、`/proc/self`が現在PIDと一致 |
| root内のentry              | `bin, dev, lib, lib64, opt, proc, tmp, usr, workspace`だけ        |
| 非許可host path            | `/home`, `/root`, `/mnt`, `/var`はいずれも存在しない              |
| 合成input読取              | 成功し、期待markerと一致                                          |
| outside / Windows sentinel | 直接path・workspace内symlinkの双方で読取不可（`ENOENT`）          |
| 合成auth marker            | 外側shellから読取可能。値は合成markerのみ                         |
| output                     | 外側から書込み可能                                                |

`/proc/1/root`と外側host PIDの`/proc/<pid>/root`を使ったsentinel探索も、outside・Windowsの双方で`ENOENT`だった。実験の各stageでは禁止したhost rootが現れず、他のhost pathもroot直下に見えなかった。

## 5. 内側Codex sandboxの結果

外側namespaceが3段階すべて成立した後、正確な`:read-only` smokeはexit 0で`sandbox-ok`を出力した。続く`:read-only`と`:workspace` probeも、namespace・procfs・read/write・通信の確認を含めてexit 0だった。

| 検査                                 | `:read-only`                         | `:workspace`                         |
| ------------------------------------ | ------------------------------------ | ------------------------------------ |
| 内側user/PID/network/mount namespace | 全て外側と異なるnamespaceを作成      | 全て外側と異なるnamespaceを作成      |
| procfs                               | 成立。内側の`/proc`も確認            | 成立。内側の`/proc`も確認            |
| input read                           | 許可。合成marker一致                 | 許可。合成marker一致                 |
| input write                          | 拒否                                 | 拒否。個別read-only mountを維持      |
| 合成workspace file write             | 拒否                                 | 許可。workspace profileの範囲内      |
| output write                         | 拒否                                 | 許可                                 |
| outside/Windows/symlink/proc read    | 全て拒否（`ENOENT`）                 | 全て拒否（`ENOENT`）                 |
| 外部TCP socket作成                   | 拒否（`EPERM`、errno 1）             | 拒否（`EPERM`、errno 1）             |
| 合成AF_UNIX socket作成               | 拒否（`EPERM`、errno 1）             | 拒否（`EPERM`、errno 1）             |
| inherited outside FD                 | 明示的にFDを渡さない起動では漏出なし | 明示的にFDを渡さない起動では漏出なし |

外側と内側の両profileで`CODEX_HOME`下の合成auth markerをshellから読めた。これはこの実験で同じpathをCodex commandとsandbox childの両方に見せた結果であり、Codex CLIがmarkerをauthとして使用したことや、実認証情報の挙動を示すものではない。

## 6. 失敗した処理とFD境界

最初のnegative testではoutside sentinelを親Python processで開き、`pass_fds`を使ってFD 4を意図的にbubblewrap childへ継承した。外側のpathとしてsentinelが存在しない状態でも、probeは`/proc/self/fd/4`経由でその内容を読め、`inherited_fd_escape`でexit 20になった。この時点ではuser namespaceのみのstageで検出したため、後続PID/network stageとinner Codex testへは進んでいない。

その後、親が同じFDを保持した状態で`close_fds=True`を明示し、FDを子へ渡さない通常の安全な起動条件を測った。`/proc/self/fd`にoutside sentinelを参照するFDはなく、上記の二重sandbox検査は成功した。これは明示的なFD close契約がある場合の結果であり、bubblewrapが継承FDを自動的に閉じる証明ではない。既存`executor.py`の`subprocess.Popen`は`pass_fds`を指定していないが、外側bubblewrap launcherは現行runnerに存在しない。導入を検討するなら`close_fds=True`を明記し、FD leakage negative testを契約に含める必要がある。

初回の境界probeには、sandboxによるsocket作成拒否（`EPERM`）を捕捉しない実験コード上の不備もあった。また初回`:workspace`では外側workspace全体をread-onlyにしていたため、内側bwrapが`/workspace/.git`を用意する処理が`EROFS`で止まった。前者はsocket作成失敗を結果として記録するよう修正し、後者は合成workspaceを外側で書込み可能にしてinput fileだけを個別read-onlyにする構成へ変更した。これらはprobe構成の修正であり、production codeの不具合ではない。

## 7. Network・Unix socket

外側network namespace内から`203.0.113.1:443`への接続を試し、`ENETUNREACH`となった。Codex `:read-only` / `:workspace`内では、TCP接続以前のsocket作成が`EPERM`で拒否された。outside sentinelディレクトリ上の合成AF_UNIX listenerは、外側にpathをmountしていないため内側から到達できず、inner profileではsocket作成が`EPERM`となった。listener側に接続は到着しなかった。

これは指定した宛先とsocket種別のprobe結果であり、全てのDNS・egress・通信経路を網羅した証明ではない。実データの外部送信は行っていない。

## 8. Windows filesystemと認証情報

外側rootに`/mnt`がなく、Windows sentinelは直接path・symlink・procfs root経由の全てで読めなかった。実験は一つの合成sentinelだけを対象とし、他のWindows fileは参照していない。

合成auth markerは外側から`CODEX_HOME`のpathへread-only bindし、内側shellにも同pathを見せた。そのため両shellがmarkerを読めることを確認した。Codex本体とshellの間でこのmountを分けない構成では、shellからauth fileを隠せない。Codex runtimeが必要とする認証を親processだけに保持し、shell childのmount namespaceから隠す設計は今回の検査対象に含まれず、別途証明が必要である。実認証での確認はしていない。

## 9. Docker/Codespaces既存障害との比較

| 実行層                       | 既存記録または今回の実測                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Docker内Codex CLI            | 既存local Docker報告ではnamespace作成時に`No permissions to create a new namespace`。特定拒否syscallは確定していない      |
| Docker内procfs               | 既存の限定診断記録には、namespace通過後のprocfs mount拒否がある。通常Docker条件の再試行はしていない                       |
| Codespaces                   | 過去記録にはnamespace/clone/procfs/uid_map段階の失敗がある。ローカルDockerと同一原因とは断定していない                    |
| WSL2 host上のCodex sandbox   | 以前のWSL調査で`:read-only` echo smokeは成功したが、workspace外とWindows sentinelを読めた                                 |
| WSL2 host bubblewrap + Codex | 今回のsynthetic outer mount、閉じたFD条件ではinner `:read-only`と`:workspace`が起動。意図的なFD継承ではoutside readが成立 |

今回のWSL host namespaceが使えたことは、Docker内のnamespace/procfs制限が解消した根拠にはならない。Docker設定・権限は変更せず、障害条件も再試行していない。

## 10. 現行Planとの適合性とrunnerへの影響

現行[Agent evaluation Plan](../plans/2026-10-03_132700_agent-eval-runner.md)はLinux Docker isolationを標準にし、独自sandboxの追加を前提にしていない。また[Agent eval README](../../scripts/skills/evals/agent/README.md)はread-only root/workspace、output-only writable bind、別Judge container等を契約としている。今回の外側bubblewrapはこの構成ではないため、Plan適合の正式環境として扱わない。

| 対象                             | 現行契約                                                            | 二重bubblewrap採用を検討する場合に必要な設計・検証                           |
| -------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `isolation_probe.py`             | Docker image/mount、Evaluator sentinel、workspace/output境界をprobe | bwrap argv・実効mount・namespace・sentinel・FD closeを同じfingerprintで検証  |
| `workspace.py`                   | direct `docker run`、read-only workspace、output mount等をvalidate  | 外側bwrapの引数・全bind・inner commandのallowlistとFD条件を別契約で定義      |
| `run.py`                         | Agent/Judge command、named Docker container、timeout/evidenceを管理 | 外側process groupと子孫processのtimeout、signal、cleanup、証拠保存を追加検討 |
| `qa_training_store.py`           | 固定target、反復、attempt、cleanup/evidenceの契約を維持             | QTSのAgent/Judge起動にも同一sandbox証拠・cleanup・比較fingerprintを接続      |
| `codex_docker_launcher.py`       | Agent用一時`CODEX_HOME`、Codex runtimeとauth materialをDockerへ供給 | shellから認証fileを隠す境界とCodex親processの読取を別々に実測                |
| `codex_judge_docker_launcher.py` | Judge専用containerと別`CODEX_HOME`を用意                            | Agent/Judgeの別namespace、別home、限定入出力、独立evidenceを保つ             |

上記は必要な差分の調査であり、今回runner・Plan・trust boundaryは変更していない。Judge分離、Docker mount契約、実行後の証拠、再現性・cleanupを新方式で再設計する判断は、人間によるPlan/security reviewの対象となる。

## 11. Judge fixtureと正式受入の残課題

既存の[WSL調査報告](./2026-10-24_pr17-wsl-sandbox-investigation_v00.md)に記録済みのfixture v2監査は再実行していない。11件すべて未承認で、2件が`pending_deterministic_review`、9件が`pending_human_review`、approvedは0件。`QTS-SEM-008`専用のmajor-violation fixtureは存在しない。以前の合成baselineを今回の実Agent評価へ流用しない。

QTS-SEM-008 fixtureの追加には、固定QTS targetからの実Agent正常baseline成果物、複数の重要caseで実行不能になる欠落を説明する実artifact、通常fixtureとの分離、固定reference/baseline fingerprintを含むapproval binding、独立した人間確認が不足している。

正式受入は全て未達のまま維持する。

- 共通4 case（`TC-OUT-001`、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`）の実Agent評価は未実施。
- 固定QTS revisionの独立2 attemptとtarget不変性確認は未実施。
- 承認済みfixtureを使う独立Judge評価は未実施。
- 原成果物とSkill使用traceに基づく欠陥特定、限定Skill修正、同条件再評価、独立回帰は未実施。
- live runtimeの実効profile、認証非公開、network/tool条件のformal evidenceも未確認。

## 12. 修正・validation

production sourceや既存testに今回の調査で確定した不具合はなかったため、コード修正・新規回帰testは行っていない。修正したのはローカルone-off probeのsocket error handlingと合成mount配置だけで、`.agent-eval-runs/`に保存した。実験用ログをgitへstageしていない。

| Validation                                | 結果                                          |
| ----------------------------------------- | --------------------------------------------- |
| package version・SHA-512照合              | PASS                                          |
| outer user/PID/network namespaceとprocfs  | PASS                                          |
| Codex `:read-only` exact echo smoke       | PASS                                          |
| Codex `:read-only` boundary probe         | PASS                                          |
| Codex `:workspace` boundary probe         | PASS                                          |
| 意図的なinherited FD negative test        | FAIL。FD 4経由のoutside sentinel読取を検出    |
| production unit tests / Ruff / compileall | production codeを変更していないため今回未実行 |
| dprint `0.55.2`                           | PASS。対象報告書を固定versionで整形・check    |
| `git diff --check`                        | PASS                                          |

Codex `0.163.0`の実装は[Linux sandbox README](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/README.md)、[bwrap builder](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)、[Landlock implementation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/sandboxing/src/landlock.rs)を参照した。source確認は今回の実測を置き換えるものではない。

## 13. 次の判断

FDを閉じるlauncher契約を明示・検証し、shellからauth materialを隠す方式を別途設計すれば、今回成立したsynthetic namespace・path境界を再利用できる可能性はある。ただしその変更は現行PlanとDocker契約を変えるため、この結果だけで採用してはならない。Docker内namespace/procfs問題、Judge分離、credential isolation、run timeout/cleanupの実証も未解決である。

したがって最終判定は**B（一部成立）**。外側と内側のsandboxは通常のFD閉鎖条件で動作し、今回指定したsynthetic file・symlink・procfs・socket境界は成立したが、FD継承を使うと外側read restrictionを迂回できた。PR #17の実Agent評価、Judge評価、Skill改善を開始できる正式隔離条件が完成したとは扱わない。
