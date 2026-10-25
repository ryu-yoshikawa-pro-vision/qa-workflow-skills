# PR #17 ChatGPT認証更新・WSL2復旧調査

- **確認日:** 2026-10-25
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **Branch:** `feat/agent-eval-runner`
- **確認したHEAD:** `47626f6d644044dba7ff12dd6780176efab08647`
- **Base:** `main` (`cd51794d464a9a142bdfcf04992bc7b0bb463696`)

作業開始時、local branchは`origin/feat/agent-eval-runner`と一致し、tracked working treeはcleanだった。既存の未追跡`.wsl2-migration-transfer/`と2件の評価レポートは保持した。

## 要約

この実行環境からWSL distributionを列挙できず、`wsl --status`と`wsl --list --verbose`は`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`で終了した。現在のプロセストークンは`MYCOMPUTER\codexsandboxoffline`であり、環境変数の`USERNAME=sella`とは一致しない。WSLサービス自体の故障とは判定できず、Codex実行環境の制限されたWindows identityがWSLのdistribution列挙を許可されていない可能性が高い。通常のユーザーPowerShellからの比較が必要である。

認証コード経路では、固定Codex CLIがrefresh後の情報を、そのプロセスの`CODEX_HOME/auth.json`へ保存する。一方、現行launcherは永続homeから`auth.json`をattempt専用homeへ複製し、終了時にattempt専用homeを削除する。したがってrefreshが成功しても更新を次のattemptへ保持できない可能性がある。これは`refresh_token_reused`の起こり得る要因だが、今回の発生原因そのものは確定していない。

attempt間の排他は実装されていない。Codexのrefresh semaphoreは各`AuthManager` instanceに属するため、独立したCodex process同士を排他しない。runner管理のprocess lockを追加しても、通常のCodex CLIや別app-serverはそのlockを取得しない。

第一候補の専用永続`CODEX_HOME`は、refresh後の永続化と通常利用ストアとの分離に役立つ。しかし現行outer bwrapはCodex home全体をread-write bindし、以前の合成検証では内側shellから合成認証markerを読めた。専用homeを有効にするとcredentialの可視期間と改変影響が長くなる。`chmod 600`は同じ実行identityのshellに対する境界にならないため、shellからの読み取り拒否を実測できる設計が成立するまで採用・実装しない。

## WSL2診断

実行環境はWindows 10 Home 22H2、build `19045.7807`、PowerShell `7.6.8`である。`whoami`は`mycomputer\codexsandboxoffline`、`whoami /groups`にはmedium integrity labelが示された。`USERNAME`と`USERPROFILE`環境変数はそれぞれ`sella`と`C:\Users\sella`だった。

- `wsl.exe --version`: exit 0。WSL `3.0.3.0`、kernel `6.18.54.1-1`、WSLg `1.0.79`。
- `wsl.exe --status`: exit 1。`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`。
- `wsl.exe --list --verbose`: exit 1。同じ`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`。
- `WslService`: Running。`LxssManager`: Stopped。これらの状態だけからdistributionの健全性やエラー原因は判断していない。
- distribution名を一覧結果から得られなかったため、distribution内の`/bin/true`は実行していない。固定runtime、checkout、WSL内認証状態も確認していない。
- `wsl --shutdown`、`--terminate`、サービス変更、管理者修復、distribution変更は行っていない。

確認できたのは「このCodex実行環境ではdistribution列挙が拒否される」ことまでである。Windowsユーザー`sella`の通常PowerShellから同じコマンドを実行した結果がないため、WSLサービス障害とCodex token制限の切り分けは未完了である。

## 認証更新経路

現行コードの経路は次のとおり。

1. `launch()`が`verify_runtime()`を呼び、`_auth_material()`が明示`CODEX_HOME`または`~/.codex`を選ぶ。
2. 固定CLIの`codex login status`でChatGPT loginを確認する。認証file本文・hashは読み出していない。
3. `_prepare_codex_home()`がattempt専用homeを作り、`shutil.copyfile()`で`auth.json`を複製する。
4. `_mount_tree()`はそのhome全体をouter bwrap内の`/codex-home`へread-write bindし、Codex CLIへ`CODEX_HOME=/codex-home`を設定する。
5. launcherの`finally`で`cleanup_codex_home()`がattempt専用homeを削除する。launcherは元のstoreへrefresh結果を同期しない。

Codex CLI `0.163.0`の公式実装では、`persist_tokens()`が現在のstorageから認証状態を読み、新tokenを反映し、`storage.save()`を呼ぶ。`FileAuthStorage`は`CODEX_HOME/auth.json`へ保存する。現在のlauncher経路では保存先はattempt専用コピーであり、cleanupにより消える。

CLIの`refresh_token_reused`応答は`RefreshTokenFailedReason::Exhausted`として分類される。古いrefresh tokenが再利用される要因として、別processとの同時refreshや、一時homeで更新後その更新を破棄して次attemptが古いstoreを再利用する経路が考えられる。どちらが今回起きたかを示すtoken・server記録・同時process証拠は取得していない。

Codexの`AuthManager`はinstance内のsemaphoreでrefreshを直列化するが、独立process間の排他ではない。現runnerにもauth storeを守るOS file lockはない。また、別のCodex CLI、app-server、手動loginがrunner lockに参加する保証はない。

参照:

- [Codex CLI 0.163.0 auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs#L1600-L1623)
- [Codex CLI 0.163.0 refresh lock and error classification](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs#L1680-L1708)
- [Codex CLI 0.163.0 AuthManager refresh semaphore](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs#L2043-L2216)
- [Codex CLI 0.163.0 auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs#L162-L231)
- [Codex CLI 0.163.0 login status](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs)
- [OpenAI Codex authentication documentation](https://learn.chatgpt.com/docs/auth)

## 設計判断と残る安全条件

専用永続`CODEX_HOME`とOSのprocess lockは候補として残す。採用する場合は、以下をすべて確認してからにする。

- ユーザーが通常利用用`~/.codex`と分けた専用storeへ、公式固定CLIでChatGPT loginする。
- Agent/Judge/Repairとrunnerが管理する別runを一つの認証store単位で直列化する。
- 専用storeを他のCodex processや手動loginから使用しない運用を定める。runner lockが外部processまで排他しない制約を明記する。
- refresh成功後のstoreが次processでも利用できることを、実認証を使わずCodex公式保存経路の合成testで確認する。
- 合成markerを使い、実際のmount namespaceと実行identityのもとでAgent shell、Judge shell、Repair shellからstoreを読めないことをnegative testする。
- Agent/Judge/Repair、Windows filesystem、FD、network、timeout/cleanupを含む15件の既存required isolation checksを維持する。

現在の`/codex-home` read-write bindと過去に確認されたshell可視性のままでは、永続storeをCodex processとAgent shellの間で安全に共有できない。`chmod 600`やstoreを専用directoryへ移すだけでは解決しない。Codex shell subprocessにcredential mountを見せない仕組みはまだ実証されておらず、追加bwrap、別UID、Codex内部sandbox設定のいずれもここでは検証していない。安全な代替方式を確定できていないため、認証経路は変更しない。

## ローカル検証

このWindows環境のPythonは3.11.9だが、PyYAMLが未導入である。RuffとdprintもPATHに存在しない。依存追加やglobal tool installは行っていない。Code Quality workflowではRuff `0.16.8`とdprint `0.55.2`をinstallして`python scripts/format_tracked.py check`を実行する。Deterministic workflowはPyYAML `6.0.3`をinstallする。

- `test_codex_wsl2_bwrap_launcher.py`: 20 PASS、WSL2 integration 1 SKIP。
- Agent suite: 135 tests、4 errors、11 SKIP。3件はDocker launcherのLinux host必須、1件はLinux image probe用binaryをWindowsで起動した`WinError 193`。WSL2 integrationは走っていない。
- Agent repository contract: 4 PASS。
- Semantic repository tests: 12 PASS、1 SKIP。
- Deterministic script tests: 13 PASS。
- Deterministic repository tests: 206 tests、24 errors、1 failure。PyYAML未導入によるimport/runtime失敗が主因で、CLI integrationもvalidator import時のPyYAML欠落で失敗した。
- Runtime tests: 371 PASS、2 SKIP。
- `compileall`: PASS。
- Ruff check/formatとdprint: 未実行。対象CLIがない。

Agent suiteは合成runner testから一時的な`.agent-eval-runs`記録を出力した。既存・今回生成を問わず評価記録を削除していない。これらは合成test記録であり、実Agentの結果ではない。

WSL2 launcher integration、fresh isolation evidence、固定runtime検証、15/15 isolation checks、Agent/Judge/Repairの本番mode実証は未実施である。`git diff --check`と最新PR headのCIは、この報告を追加するcommitの前後で別途確認する。

## 認証・実評価の状態

- ChatGPT login状態: 今回は未確認。WSLへアクセスできず、`codex login status`を実行していない。
- 対象store: 今回は選定・変更していない。通常利用用または専用のいずれも使っていない。
- 認証file、refresh token、credential hash: 読み出し・複製・編集なし。
- logout、再login、認証状態変更: なし。
- OpenAI API Key、従量課金、追加credits: 使用なし。
- Agent、Judge、Repairの実起動、model API、評価profile/evidence/run: なし。
- `authentication_shell_visible_risk=true`: 維持。

## 次に必要な対応

まずユーザーの通常のWindows PowerShellから、現在のCodex実行環境と同じPC・ユーザーで次を実行し、各コマンド直後の終了コードと`whoami`を確認する。distribution名は実際の`--list --verbose`出力からのみ取得し、一覧が成功したときにその名前を使って`/bin/true`を実行する。`wsl --shutdown`やサービス設定変更は行わない。

```powershell
wsl.exe --version
"exit=$LASTEXITCODE"
wsl.exe --status
"exit=$LASTEXITCODE"
wsl.exe --list --verbose
"exit=$LASTEXITCODE"
whoami.exe
```

通常PowerShellで成功する場合はWSL service故障とみなさず、Codex実行tokenと認可済み実行modeの差を調べる。Codex sandbox/Hook/execpolicyを弱めて迂回しない。WSLアクセスが戻った後にのみ`verify_runtime()`で固定runtimeを検証し、実認証なしの合成mount testで専用storeのshell読み取り拒否とprocess lockを実測する。その安全性が確認され、実際の専用`CODEX_HOME`が確定してから、ユーザー自身の公式Codex loginを案内する。ログインは現時点では求めない。

この調査による変更は本レポートだけで、評価仕様、launcher、認証、Plan、profile、evidenceは変更しない。安全な認証設計とWSL2復旧が未達のため、実Agent評価再開条件は成立していない。
