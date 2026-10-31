# PR #17 Agent評価ランナー認証・隔離検証 v06

- 確認日: 2026-10-26
- Repository: ryu-yoshikawa-pro-vision/qa-workflow-skills
- PR: [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- PR branch: feat/agent-eval-runner
- 作業branch: work/pr17-auth-wsl-20261025
- PR確認HEAD: e87a4890514af6bff09b90bb180e4dcd9c3fddb7
- 作業branch基準HEAD: 6782994746e81eda61331d9312e349740bb4c694
- 対象: 上記作業HEADに対するlocal code changesと本報告・README・Planの更新

> この報告のtest resultsは作業treeの実装差分を対象とし、PR remote HEAD e87a489のCI結果と混同しない。正式full isolation evidenceはcleanでcommit済みの最終HEADに結び付けて生成する必要がある。v05の結果は履歴として保持する。

## 実施した変更

- 固定Codex CLIにmodeごとのnamed permissions profileを生成する。AgentとRepairは:workspace、Judgeは:read-onlyを継承し、すべてで/codex-home/auth.jsonをdeny、inner networkを無効にする。Repair profileには対象Skillだけをworkspace rootとして加える。
- 固定CLIへsandbox mode optionを渡すとlegacy sandbox modeがnamed permissions profileを無効にするため、本番exec argvから--sandboxを除いた。profileは一時config.tomlと--config default_permissionsの両方で選択し、Agent/Repairのworkspace-write、Judgeのread-onlyを保持する。
- formal synthetic smokeにauth.jsonのdirect path、symlink alias、/proc/self/root、/proc/1/root、host store path、other-attempt store、environment、process FDの検査を追加した。秘密markerの値は結果やログへ出さない。外側Codex親processからsynthetic storeを読めることも確認する。
- sandbox smokeで名前違いのpermission profileを指定できない検証を追加した。invalid named profileをCLIがrejectすることも正式launcher integrationで検査する。
- fresh probeは開始前にauthentication_shell_visible_risk=trueとし、auth read-deny test成功後だけfalseに更新する。refresh永続化およびprocess concurrencyは未解決状態のまま保持し、production launchを全modeでfail-closedにする。

## 固定Codex CLI sourceに基づく判断

固定sourceの[permissions profile resolver](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/config/src/permissions_toml.rs)は親profileを先に解決し、childの項目をmergeする。[:workspace / :read-only permission compilation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/config/permissions.rs)と[Linux bwrap実装](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)はdeny pathをunreadable mount maskにする。fixed CLIがnamed profileを選択する設定経路を[debug sandbox command](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/debug_sandbox.rs)で確認し、固定runtimeのcodex sandbox smokeで実効挙動を試した。

### 認証storage mode

| Mode      | Save/reload                                                             | Process間競合                                | shellからの境界                                                                    | 判定                                             |
| --------- | ----------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------ |
| file      | auth.jsonをtruncate/write/flush。Codexは選択中storageへのsave後にreload | CLI横断lockもatomic replacementもない        | 同じOS identityのprocessからのreadを防ぐ仕組みではない                             | attempt copyではrefresh結果が次attemptへ残らない |
| keyring   | CODEX_HOME由来のkeyでkeyringへ保存                                      | refresh transactionを囲うprocess間lockはない | 同一OS identityで使うprocessを隔離しない。WSL outer bwrapでbackend利用可能か未確認 | refresh競合を解決しない                          |
| auto      | keyring成功時はkeyring                                                  | keyring load/save error時にfileへfallback    | fallbackはfileと同じpath可視性になる                                               | 必須条件に不適合                                 |
| ephemeral | process内global memory store                                            | processをまたがない                          | filesystem credentialを避けてもattempt間で消える                                   | refresh更新の連続attempt利用に不適合             |

[auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)と[auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)では、refresh mutexは同一AuthManager内であり、別Codex processと共有されない。file backendはtruncate後のwrite/flushが失敗しても旧内容をatomicに保つ契約を持たない。専用persistent CODEX_HOMEやkeyringは更新永続化の候補にはなっても、非協調processとの競合を閉じない。専用OS identityやbrokerは既存Plan外の運用・権限設計を必要とするため実装していない。

attempt-local copyがcleanupで失われる問題はsynthetic fake-child testで再現した。これはrunner file operationの検証であり、Codex CLI自身のrefresh successを証明しない。公式source test harnessのloopback endpointを使ったrefresh requestから別process reloadまでのtestは実行していない。過去のrefresh_token_reusedの直接原因も確定していない。

## 検証結果

環境はWSL2 Ubuntu host、Python 3.11.17、PyYAML 6.0.3、固定Codex CLI 0.163.0と同梱bubblewrap runtime。

| 検証                                      | 結果                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Agent implementation suite                | PASS: 140 tests、2 skipped                                                                                    |
| Agent repository contract                 | PASS: 4 tests                                                                                                 |
| Semantic implementation suite             | PASS: 27 tests                                                                                                |
| Semantic repository suite                 | PASS: 13 tests                                                                                                |
| Deterministic repository suite            | PASS: 293 tests、通常WSL2 host、TMPDIR=/var/tmp                                                               |
| Deterministic implementation suite        | PASS: 13 tests                                                                                                |
| Codex Harness                             | PASS: 57 tests、8 skipped。PATHに固定Codex runtimeを指定                                                      |
| 認証・refresh・profile focused tests      | PASS: 4 tests                                                                                                 |
| workspace evidence contract               | PASS: 14 tests                                                                                                |
| fixed-runtime formal launcher integration | PASS: 1 test。Agent/Judge/Repair mode、FD、network、path、write、timeout、cleanup、auth read-deny smokeを確認 |
| compileall                                | PASS                                                                                                          |
| git diff --check                          | PASS                                                                                                          |
| dprint 0.55.2 / 全tracked formatter       | PASS: format_tracked.py check、239 tracked files。新規v06 reportにもdprint 0.55.2を個別適用                   |
| Ruff 0.16.8 / tracked lint+format         | PASS: tracked lintとformat check。2つの変更Python filesをruff format後に全体check                             |
| schema 2 fresh full isolation probe       | 未実行。commit済みclean final HEADでのみ実行する。過去evidenceは流用しない                                    |

Codex development sandboxでEPERMになるAF_UNIX依存testは、通常WSL2 hostから再実行した。Deterministic repository suiteは293件すべてPASS。Codex Harness内のbranch switchingメッセージは一時test repository内で出た。対象worktree branchは変更していない。

正式launcher integrationは3 modeすべてに対するsynthetic smoke testでPASSしたが、これはfull isolation evidenceではない。schema 2 probeの16 required checks、aggregate Agent/Judge separation、mode fingerprints、evaluator revision/profile/runtime fingerprintsはまだ未取得である。

## 認証・実Agentの状態

実token内容を読まず、実認証、Codex login status、refresh通信、モデルAPI、codex exec、TC-OUT-001は実行していない。synthetic markerのlauncher smokeではinner shell read-denyを検査できた一方、Codex親processの実認証利用、refresh結果の永続化、非協調Codex processとの競合は未検証である。

launcherは以下を未解決として持ち、Agent/Judge/Repairの本番処理を認証照会前に拒否する。

- authentication_refresh_persistence_unresolved=true
- authentication_process_concurrency_unresolved=true

したがってauthentication shell visibility checkが成功しても、実Agent評価を開始できない。fresh evidence成功だけでもこの2条件は解消されない。

## GitHub / Git

作業開始時のPR branch HEADはe87a4890514af6bff09b90bb180e4dcd9c3fddb7で、PRはopen、base main。e87a489に対する現行5 workflowはすべてSUCCESS: Validate Agent Skills, Validate Deterministic Output Evals, Validate Semantic Output Evals, Code Quality, Codex Harness。これらは今回local変更を含むCIではない。

作業開始時のlocal HEADは6782994746e81eda61331d9312e349740bb4c694で、c764a2aと6782994の未push文書commitを含む。今回のcode/doc changesはこの報告作成時点でuncommitted。push/PR本文更新は未実施で、新HEADのCIは未確認である。既存Hook、execpolicy、canonical-root policyを確認して通常のstage/commit/pushを試行し、拒否された場合は迂回しない。

## 残る受入条件

1. cleanでcommit済みのfinal evaluator HEADに対するfresh schema 2 probeを生成し、16/16 checks、Agent/Judge/Repair verified、fingerprintsとrevision一致、model_api_used=falseを確認する。
2. refresh後の状態を次attemptと別Codex processが安全に読む、process横断競合のないstorage/lock条件を実証する。固定CLIの現行file/keyring/auto/ephemeral modeにその契約は確認できていない。
3. 合成auth markerがshellからread-denyになるsynthetic smokeと、実認証fileの安全性の証明を混同しない。TC-OUT-001は上記条件成立後、さらに実モデル利用の明示承認が得られるまで実行しない。
4. final commit SHAをPR branchへ反映できた場合は、そのSHAの5 workflowすべてSUCCESSを確認する。作業branchとPR branchが異なるため、既存Hookが宛先を拒否する場合は停止する。
