# PR #17：FD継承と認証情報境界の調査報告

作成日: 2026-10-24

## 1. 対象と制約

- 対象: `ryu-yoshikawa-pro-vision/qa-workflow-skills` PR #17、branch `feat/agent-eval-runner`
- 調査開始時HEAD: `a9eff4478a8a9de44031fdb9d47fd807d4592348`
- 調査開始時PR状態: open、base `main`、未merge
- 対象Codex CLI: 0.163.0。WSL2内のCodex同梱bubblewrapでsynthetic probeを実行
- 実認証、API key、モデル通信、実Agent、実Judgeは使用していない
- Docker方式、公式Plan、既存の未追跡Docker調査レポートおよび`.agent-eval-runs/`の既存成果物は変更していない

今回の判定は、合成ファイル、環境変数、FDを使った到達性の確認に限る。Codexの実認証処理が完了すること、認証更新が正しく動くこと、実モデル評価が成立することを証明したものではない。

## 2. FD継承の実測

### 2.1 正常起動

親が合成outside sentinelを開いた状態で、shellを介さないargv実行、`close_fds=True`、空の`pass_fds`、stdin/stdout/stderr用pipeを使って`executor.run_command`を起動した。子から`/proc/self/fd/<n>`と`/dev/fd/<n>`を調べた結果、sentinelは読めなかった。入力文字列はstdin pipeから維持され、FD 0/1/2はいずれも専用pipeだった。

WSL2内で通常のPython子プロセスでも同じ到達性を確認した。`fd-stdio-contract-results.json`には、inheritable属性を持たせた親FDが通常の`subprocess.Popen`（`close_fds=True`, `pass_fds=()`）および実executor経路に継承されなかった結果を保存した。比較用の明示`pass_fds`では合成markerを読み取れた。

### 2.2 二重bubblewrapで意図的にFDを渡した場合

外側bubblewrapの起動に`pass_fds=(4,)`を明示し、Codex CLI 0.163.0の内側sandboxからsynthetic childを起動した。FD 4は外側user/PID/network namespaceの過程を通り、内側`:read-only`と`:workspace`のshellまで到達した。両profileで`/proc/self/fd/4`と`/dev/fd/4`の双方からoutside sentinelを読み取れた。各probeのexit codeは0。

内側のshellからoutside sentinelのpathname自体は読めなかった一方、同じファイルを指すFD経由では読めた。したがって、path maskやmount境界だけでは、既に開かれたFDを防げない。

合成`CODEX_HOME/auth.json`を使った別probeでは、shellからファイルを読み取れた。FD 4のprobeと同様、実認証情報は使っていない。

### 2.3 起動契約

1. evaluatorが起動する各子プロセスでは、不要なFDを閉じる。`executor.py`は`close_fds=True`を明示し、`pass_fds`は使わない。
2. `pass_fds`による未許可FDの転送は禁止する。もし将来例外的なFD転送が必要になれば、許可するFD番号・用途・受け手を個別に定め、同じsynthetic negative testを追加する。
3. FD 0/1/2を秘密ファイルへ接続しない。既存契約どおり、promptはstdin pipe、結果とdiagnosticは別pipeまたは`DEVNULL`で扱う。Judge promptをstdinで送る場合、Judge向けに認められた内容だけをmemoryから渡し、秘密ファイルのFDを接続しない。
4. 到達性は`/proc`と`/dev/fd`を読む実子プロセスで検査する。flagやargvの確認だけでは合格としない。

Pythonの`subprocess.run`を使う現行launcher、probeの呼び出しに`pass_fds`指定はない。Pythonの既定動作に依存する箇所を一括変更していない。実際のrunner共通入口だけは、起動契約がコード上で明示されるように`close_fds=True`を設定し、inheritableなFDを開いた回帰testを追加した。

## 3. 現行コードの境界

### `executor.py`、`run.py`、`qa_training_store.py`

- `executor.py`は`Popen`へUTF-8 promptをstdin pipeで渡し、stdout/stderr pipeから回収する。`shell=False`であり、POSIXでは独立process group、Windowsでは`taskkill /T /F`を使う。
- AgentおよびJudgeの各呼び出しは、別の`run_command`実行として起動される。
- Windowsのtimeoutではprocess treeを強制終了するため、launcher内の`TemporaryDirectory` cleanup handlerだけでは一時認証HOMEの消去を保証できなかった。合成`auth.json`を持つchildをtimeoutさせるtestで、launcher相当の一時HOMEが残ることを再現した。
- 修正ではWindows上で各`run_command`専用の一時TEMP rootを親executorが作り、`TMPDIR`/`TEMP`/`TMP`としてchildへ渡す。process tree終了後、親の`TemporaryDirectory`がrootごと回収する。既存の強制終了方式は変えず、他runのtemp領域をprefix sweepしない。回帰testはsynthetic `auth.json`のHOMEがtimeout後に存在しないことを確認する。

### Agent / Judge Docker launcher

- どちらのlauncherもDocker CLIを`subprocess.run(..., shell=False)`で起動し、promptはstdin、Docker出力はstdout/stderr pipeで運ぶ。`pass_fds`指定はない。
- AgentとJudgeは別のlauncher、別のDocker container、別の一時`CODEX_HOME`を使う。親directoryを`0700`、`auth.json`と固定configを`0600`にする。
- 一時`CODEX_HOME`はCodex containerの`/codex-home`へmountされ、`CODEX_HOME=/codex-home`を設定する。通常のfile authではsource `auth.json`をcopyする。API key方式ではDockerへ`--env OPENAI_API_KEY`を追加する。
- AgentとJudgeの一時ファイル・container・cwdは分離するが、同一sourceから起動すれば、copyされた認証materialや環境API keyが別identityになるわけではない。
- Docker launcherのsubprocess既定FD closeは変更していない。対象runnerの`Popen`入口と、実Python subprocessでのFD negative testにより、今回のFD契約を検証した。

### `isolation_probe.py`

Docker control/probeを`subprocess.run`で直接起動し、標準入出力は`DEVNULL`または独立pipe。runnerの外部Agent/Judge起動契約ではないためFD設定を大量変更しない。

## 4. Codex CLI 0.163.0公式ソース

以下は[公式Codex repositoryの`rust-v0.163.0` tag](https://github.com/openai/codex/tree/rust-v0.163.0)から確認した事実。

- `CODEX_HOME`は設定されていればそのdirectoryを解決し、なければ`~/.codex`を使う。[home-dir実装](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/utils/home-dir/src/lib.rs#L6-L58)
- file authは`CODEX_HOME/auth.json`を`File::open`して読み込み、storageのsaveは同じ場所へ書き込む。Unixではsave fileに`0600`を設定する。[auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs#L175-L230)
- auth storage modeには`file`（default）、`keyring`、`auto`、`ephemeral`がある。`ephemeral`はcurrent process memoryのみのstoreとして定義され、`auto`はkeyring可否によってfileへfallbackする。[mode定義](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/config/src/types.rs#L133-L145)
- auth managerは選択storeを生成し、そのbackendの`save`を呼ぶ。[save_auth](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs#L1149-L1162) 今回はloginやtoken refreshを実行していないため、実refresh、store更新、期限切れ時の動作は未検証。
- shell tool childはCodex processから起動される。child spawnは`env_clear()`の後にrequestのenv mapを追加し、shell tool時のstdinを`/dev/null`、stdout/stderrをpipeにする。Linuxの親death signalは設定する一方、FD close helperの明示呼出しはこのsourceではmacOS条件のみ。[shell child spawn](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/spawn.rs#L52-L136)
- `NON_INHERITABLE_ENV_VARS`はCodex内部の一部token/context変数を列挙するが、そこに`OPENAI_API_KEY`や`CODEX_HOME`は含まれない。[shell environment filter](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/protocol/src/shell_environment.rs#L14-L55)
- Linux sandbox実装はfilesystem policyからunreadable rootを作り、read/write root mount後にもunreadable maskを適用する。source上はpath denyを適用する仕組みがある。[bubblewrap unreadable roots](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs#L495-L523), [mount overlayへの適用](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs#L621-L646), [nested writable rootへの再適用](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs#L775-L803)

上記sourceはruntimeの実装事実であり、現行runnerから任意のdeny pathを設定できること、CLI本体だけが認証ファイルを読めること、全auth refresh経路が隔離状態で動くことを証明しない。

## 5. 合成認証materialの到達性

### file経由

合成`CODEX_HOME/auth.json`をCodex shell sandbox内へread-only mountし、`:read-only`および`:workspace`から読み取った。directory modeやfile modeはこのsandbox内の同一UIDに対するread isolationにならない。実PlanのDocker launcherもCodex containerへ`/codex-home`をmountするため、同条件でshellから可読な実効profileになる場合、pathが分かれていても認証fileは露出する。

### environment経由

外側bubblewrapからCodex 0.163.0 `codex sandbox --permission-profile :read-only` / `:workspace`を呼び、`OPENAI_API_KEY=SYNTHETIC_ENV_MARKER_ONLY_20261024`を設定した。内側shellはmarkerを読み取れ、両profileで`synthetic_openai_api_key_present=true`だった。これは合成値の可視性だけを確認した試験で、実Agent `codex exec`の認証や通信は行っていない。

したがって、現行launcherがAPI keyを環境方式でDockerへ渡す場合、実測したCodex sandbox条件ではshell childへも値が届く。file authでも、shell childが同mountを読める場合にcredential dataへ到達できる。shellがネットワークを利用して外へ送信できるか、または許可されたmodel API経路で不正利用できるかは、今回のsandbox probeだけでは全経路を検証していない。

### cleanup

- POSIX launcherはSIGTERM時にPython cleanupを実行するhandlerを既存実装で登録している。
- Windows executorの`taskkill /T /F`はlauncherのPython cleanupを実行しない。新しい親所有TEMP rootによりtimeout後の回収を実装し、Windowsでsynthetic cleanup regression testを通した。
- 正常終了後のtemp cleanup testおよびlauncher's TemporaryDirectoryの通常終了処理は従来どおり維持した。root deletionに失敗するOS-level条件は別途監視すべきだが、今回の合成testでは残留なし。

## 6. 認証方式の比較

| 比較項目                     | 案A: 現行Planの一時`CODEX_HOME`                                                  | 案B: Codex parentとshellのfilesystem境界を分離                                                                        | 案C: 別processのauth broker/proxy                                                      |
| ---------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Plan適合                     | 高い。現行Docker設計                                                             | 現行Plan外のprofile / mount変更が必要                                                                                 | Plan外。新しいserviceと通信方式が必要                                                  |
| shellからのcredential access | auth fileがreadable mountなら可。合成file testで確認                             | deny pathが正しくshell mountへ適用されればpathname accessを防げる可能性                                               | brokerにcredential本体を隠せてもshellがbrokerを呼べる場合はauth capabilityを悪用し得る |
| FD継承                       | normal launcher起動では抑止できる。明示`pass_fds`はFD leakageを再現              | deny pathと別に不要FDを閉じる必要あり。FD path経由を測る必要あり                                                      | broker socket/pipeのFDやendpointも保護対象                                             |
| 外部通信                     | Planはmodel API通信を許可。shell egressの残留経路は別条件として検証が必要        | shell networkを別に制御。CLI親のmodel API通信は維持できる可能性がある                                                 | proxy宛通信のallowlist、認証・request policy、悪用防止が必要                           |
| Agent / Judge分離            | container・process・temp homeは別。source identityが同じならcredential自体は共通 | Agent/Judge双方にdeny profileと独立fingerprintが必要                                                                  | broker policyと各client identityの分離が必要                                           |
| 再現性・cleanup              | 実装済みでfingerprint可能。Windows timeout temp cleanupを修正                    | profile、path、FD、symlink、更新処理のnegative testを追加                                                             | service構成・secret storage・rotation・availabilityを固定し監査                        |
| 必要変更・保守               | 小さい。shellからcredentialが読める制約を明記                                    | 中〜大。launchers、sandbox設定、isolation probe、profile fingerprint、command検証、cleanup、artifact provenanceを同期 | 大。新service、protocol、network policy、運用、incident handlingを追加                 |

### 案別判断

- **A**は現行Planと最も整合する。Planは最小限の認証を使い捨て`CODEX_HOME`へコピーし、認証がAgent側processから参照可能な制約と、model APIを許可する残留外部アクセスを認識している。[Plan §9](../plans/2026-10-03_132700_agent-eval-runner.md#9-正解情報の読み取り隔離を確認) ただし今回、Codex shell childからfileおよび環境markerを読める条件を具体的に実証した。shellがcredentialを読めないことを正式受入条件に追加するなら、案Aのままでは満たさない。
- **B**を次に検証する有力候補とする。公式Linux sandbox実装にはunreadable rootをmountへ再適用する機構があるが、現行CLI profile・launcherから`/codex-home`だけをdenyし、CLI parentのload/saveを維持できるとは未確認。source-level capabilityだけで成立とは判定しない。sandbox shellがpath、symlink、`/proc/self/fd`、`/dev/fd`、環境変数経由でmarkerを得られない一方、Codex parentは読めるno-model synthetic end-to-end testが必要。任意のFD継承を許さない条件も同時に必要。
- **C**の既存Codex機能としては、file/keyring/auto/ephemeralのstore modeを確認したが、独立したcredential broker/proxyは確認できなかった。`ephemeral`はprocess memory storeの定義であり、このlauncherの現在の起動inputをそのままbrokerへ変える機能とは確認していない。新serviceは別のtrusted endpointを導入し、shellに使用権限だけを残す可能性があるため、単独で機密性を解決しない。

## 7. 正式評価環境の比較

| 方式               | 現在の根拠                                                               | 主な強み                                                                                          | 認証・FD上の未達と追加負荷                                                                                                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 現行Docker         | Plan正本。既存launcherとCI契約あり                                       | 非特権・使い捨てLinux container、read-only workspace、独立Judge container。共有CIと同じ実行モデル | auth fileとAPI keyのshell可視性を受け入れるか、案Bを実証する必要。FD起動契約を保つ                                                                                                                                                                                             |
| WSL2二重bubblewrap | Ubuntu WSL2、Codex 0.163.0でouter/inner namespaceとsynthetic probeを実測 | 二重namespace、read/write・procfs/network等のprobeが可能                                          | 意図的FD4は`/proc`/`/dev/fd`双方で内側に到達し、合成auth file/envもshellから見えた。Agent/Judge launcher、`isolation_probe`、profile fingerprint、argv verifier、auth boundary、timeout/cleanup、artifact保存をWSL向けに実装・再検証する必要。現PlanのDocker受入と同一ではない |
| 専用Linux環境      | 今回は新規作成・検証していない                                           | rootless Docker/bwrapと固定kernel・policyを一つの実行基盤へ固定できる可能性                       | 新しい環境、運用、patch/update、監視、認証・egress管理が要る。新規VM、追加費用、管理者権限なしという今回の制約のため選択・検証していない                                                                                                                                       |

WSL2を正式方式へ変更する場合は、少なくとも以下が必要になる。

1. AgentとJudgeの独立launcherをWSL/Linux実行用に定義し、outer bwrap、Codex child sandbox、auth mount、process tree cleanupを明示する。
2. `isolation_probe.py`をDocker inspectだけに依存させず、実効namespace、mount、pathname、symlink、procfs、`/proc/self/fd`、`/dev/fd`、environment、network条件を同じ権限のOS childで測る。
3. profile fingerprintにCodex CLI版、同梱bwrapのSHA-256、outer/inner argv、mount/path deny、environment allowlist、network条件を含める。
4. command verifierは許可launcher argvと固定rootだけを受け入れ、host root、追加FD、未承認mount、外部shellを拒否する。
5. 認証方式は案Aの可視性を明示的に受け入れるか、案Bのparent/shell分離をsynthetic end-to-endで成立させる。実認証を使った試験は今回の対象外。
6. timeout後にAgent/Judge process tree、bwrap child、container相当の残存物、一時auth homeを回収する。
7. artifactsは既存のEvaluator-owned保存契約に合わせ、raw secret、raw auth、不要なJSONL/stdioを残さず、evidenceは`.agent-eval-runs/`へ保存する。

これらはPlan scope・runner・launcher・検証契約・CI・受入基準へ波及する。公式Planは今回変更していない。現状の正式方式はDockerのままであり、WSL結果をDocker受入の代替にしていない。

## 8. Judge fixtureと受入残課題

既存監査を再実行せず、記録済みfixture状態を引き継ぐ。

- 11 fixtureすべて未承認: human review待ち9件、deterministic review待ち2件
- `QTS-SEM-008`専用違反fixtureは不足
- 実Agent baselineは未生成
- 承認bindingは未生成
- 人間承認の代行、synthetic approval、実Judge、Agent/Judge model呼出しは行っていない

これらには実artifact、人間レビューまたは実Agent/Judge出力が必要であり、今回の合成境界調査から進める作業はない。正式受入は未達のまま。

## 9. 修正と回帰検証

### 修正

- `scripts/skills/evals/agent/executor.py`: `close_fds=True`を明示。Windowsのtimeout後cleanupのため、各childへrun専用TEMP rootを渡し、既存のprocess tree終了後に親が削除する。
- `scripts/skills/evals/agent/tests/test_executor.py`: inheritable sentinel FDの`/proc`/`/dev/fd` negative testと、Windows synthetic auth HOME timeout cleanup testを追加。
- Windowsの強制プロセス木終了、既存stdin/stdout/stderr契約、launcher構成、Docker方式は変更していない。

### 検証結果

個別実行したLinux/WSL2 validation:

- Agent evaluation suite: 94 tests PASS、Windows専用cleanup test 1件はLinuxのためskip
- Agent repository contract: 4 tests PASS
- Agent evaluation `compileall`: PASS
- synthetic executor FD test: Linux suite内でPASS
- synthetic Windows timeout cleanup test: Windows上で単独PASS
- `git diff --check`: PASS
- Ruff 0.16.8の`check` / `format --check`: 変更したPython 2ファイルPASS。tracked Python全236ファイルのcheck / format checkもPASS
- dprint 0.55.2のcheck: tracked対象918ファイルと本レポートがPASS

native Windows上でAgent suite全体も試行したが、現行launcher/isolation probeがLinux hostを要求するため6件がWindows固有環境差（Linux専用launcher、`os.getuid`）でerrorとなった。正式runner suiteはPlanどおりLinux/WSL2上でも実行し、上記の全件PASSを確認した。Windows固有cleanup回帰testはWindows上で別途通過した。

`scripts/format_tracked.py check`はRuff portionをPASSしたが、native WindowsからPython subprocessでnpm-installedのPowerShell shim `dprint.ps1`を起動できず`WinError 2`で終了した。その後、同じtracked target集合をpinned `dprint.exe`へ直接渡してcheckし、上記918ファイルのPASSを確認した。checkでファイルは変更していない。

## 10. 証拠ファイル

合成ログはすべて`.agent-eval-runs/pr17-nested-sandbox-20261024/`配下に保存し、git管理対象にしない。

- `fd-stdio-contract-results.json`: 通常executor、通常`Popen`、明示継承のFD/stdin/stdout/stderr比較
- `nested-sandbox-results-fd-injected-inner.json`: `/proc/self/fd`でFD4がinner shellに到達するprobe
- `nested-sandbox-results-fd-injected-inner-devfd.json`: 同条件の`/dev/fd`確認結果
- `nested-sandbox-results-fd-injected-inner-env.json`: Codex shell childへのsynthetic `OPENAI_API_KEY` marker到達性
- `nested-sandbox-results.json`: 明示FD転送なしのbaseline

他の既存未追跡報告と`.agent-eval-runs/`成果物は削除・上書きしていない。新しく回帰testが生成したignored synthetic test runも保持している。

## 11. 結論と次の判断

1. 通常のrunner起動契約でFD継承は防止可能。実測と回帰testを追加した。明示`pass_fds`やinheritable FDを外側sandboxへ意図的に渡すと、Codex 0.163.0の内側shellまで到達し、path maskを回避できる。
2. 現行launcherの通常Python subprocess経路で不要FDの漏えいは再現しなかった。必要なコード修正はexecutorの`close_fds=True`明示と、Windows hard-kill後の一時credential HOME cleanupである。
3. 同一mountをshellが読める場合、合成`auth.json`を読める。合成API-key環境値も今回のCodex sandbox shellで読めた。実環境の認証や外部送信は試していない。
4. 次の設計候補は案B。ただし現行Codexの外部設定口から成立するか、parent-only readとshell-denialが両立するか未証明のため正式採用しない。案Aは現行Planに沿うが、shell可視性を残留リスクとして明記する必要がある。案Cは認証proxyとegress制御を追加するため今回は推奨しない。
5. Dockerを正式評価環境として維持する。WSL2へ変える場合はPlanと上記7領域（launcher、probe、fingerprint、verifier、auth、cleanup、artifacts）を含む受入契約の改訂が必要。
6. Judge承認、QTS-SEM-008、実Agent baseline、承認binding、正式受入は未達。Plan更新や実評価は今回行わない。
