# PR #17 WSL2二重bubblewrap実行方式移行Plan

## Goal

PR #17のAgent、Judge、改善分析・修正実行を、既存Docker内Codexの代わりにWSL2 Ubuntu上の外側bubblewrapとCodex CLI 0.163.0の内側Linux sandboxで起動する。既存のEvaluator分離、品質判定、承認binding、QTS verifier、改善条件を保ち、合成データの実効隔離試験がすべて成立するまではrunを`isolation_unverified`として正式評価を拒否する。

このPlanは利用者が2026-10-24に承認した実行方式変更を具体化する。実認証・モデルAPI利用、Judge fixture承認、候補Skill自動採用、merge、closeは含まない。

## 2026-10-26時点の状態（履歴）

最新の検証対象HEADは`a960f8728bb2e2c14e282d639170ffed6af11e9a`です。このHEADのfresh schema 2 probeは16/16 required checks true、Agent/Judge/Repairの各mode verified、profile・command・runtime fingerprint一致、`model_api_used=false`でした。synthetic auth markerのread拒否は正式二重sandbox経路で確認済みです。文書更新後に作成するcommitでは、READMEの手順に従いclean final HEADに対するprobeを再生成します。

認証refresh後の更新永続化と、非協調Codex processを含むprocess間競合は未解決です。attempt-local auth copyのrefresh結果は次attemptへ保持されず、CLI内部のlockは別processと共有されません。この2条件のいずれかが未解決なら共通launcherはAgent/Judge/Repairを認証確認・copy・Codex起動前にfail-closedにします。したがって現時点で実Agent、Judge、QTS評価を実行できません。evidence・試験環境・最新5 CIの詳細は[PR #17 現在状態報告](../reports/2026-10-26_pr17-current-status_v00.md)を参照してください。以降の日付付き実行記録は各記録の対象HEAD時点の履歴です。

## 2026-10-27 専用OS identityによる認証管理

利用者は、評価専用WSL2 OS userと永続`CODEX_HOME`を第一候補にする設計を承認した。この指示により、元Planの「OS user作成を対象外」とする記述は、本認証分離・永続化・競合防止の範囲で supersede される。OS account作成や管理者設定をCodex sandboxから実行できるとは扱わず、sudo/root操作は現環境では保留する。

実装中の共通launcherは`qa-agent-eval` identity、専用home/`.codex`、`cli_auth_credentials_store="file"`、persistent auth file bind、nonblocking cross-process `flock`、既存same-UID process scanを要求する。Codex起動前にmode 0600のuncertain markerとdirectory entryをsyncし、通常終了、temporary home cleanup、persistent auth fileとdirectoryの`fsync`が成功したときだけmarkerを消す。中断・失敗時はmarkerを残して次回を止める。各attemptのmode config/homeは一時領域で別のまま、inner named profileは`/codex-home/auth.json`をdenyする。

専用accountを作っただけではprocess競合を解消しない。非runner processが同じUIDで既に存在すればscannerが停止する。runner lockは協調processだけを直列化し、trusted root/WSL administratorはfile・process境界を越えられる。専用UIDを任意に使える主体を管理者とrunner/login入口に限定するOS policyはまだ配置されていない。Codex CLI source harnessのsynthetic refresh/persist/reloadも未実施である。したがって`authentication_shell_visible_risk=true`、`authentication_refresh_persistence_unresolved=true`、`authentication_process_concurrency_unresolved=true`を維持し、fresh formal probe・source harness・OS process-start policyの実証までは全Agent/Judge/Repairをfail-closedにする。

## 2026-10-24 ChatGPT認証限定の追加指示

後続の明示依頼により、schema 2 launcherの認証をChatGPT loginだけに限定し、固定Codex CLIの`codex login status`で状態を確認する変更を追加する。この追加指示は本Planの「認証全面変更を含まない」という除外を、ChatGPT方式確認とAPI Key fallback廃止の範囲だけ上書きする。ログイン操作、認証情報の移動・復元、実モデル/API呼び出しは許可しない。後続のnamed permissions profileとsynthetic marker試験ではshell read-denyを確認したが、実認証fileは使用していない。refresh永続化とprocess間競合は未解決で、実Agent runはfail-closedにする。

## 2026-10-26 固定CLI permissions profileによるshell read拒否

固定Codex CLI rust-v0.163.0のsourceを確認し、従来の「shellから認証fileが見えるリスク」は、内側Codex sandboxのnamed permissions profileに対する合成実測で見直す。permissions.<profile>.extendsは親builtin profileを先に解決し、child設定をmergeする。Agent/Repairは:workspace、Judgeは:read-onlyを親にし、3 modeともfilesystem."/codex-home/auth.json" = "deny"、network.enabled = falseとする。Repairだけ対象Skillをworkspace rootに追加し、外側bubblewrapのwrite mountも従来どおり当該Skillへ限定する。[profile resolver](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/config/src/permissions_toml.rs)、[permission compilation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/config/permissions.rs)、[Linux bwrap deny masks](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)を根拠とする。

固定CLIは--sandbox workspace-writeまたはread-onlyを渡すとlegacy sandbox modeを構成し、named default_permissions profileを使わない。このため本番argvから--sandboxを外し、一時CODEX_HOME/config.tomlと--config default_permissions="qa_eval_<mode>"で同じmode profileを選択する。Agent/Repairのworkspace-write、Judgeのread-only、inner shell network拒否を維持する。合成smokeはstore path、symlink alias、/proc/self/root、/proc/1/root、host path、他attempt path、environment、process FDからのread拒否をmodeごとに検査し、親process側のstore read可否も確認する。[fixed CLI permissions](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/config/permissions.rs)と[fixed bwrap](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/src/bwrap.rs)を参照する。

2026-10-26の通常WSL2 host上のformal launcher integration testはAgent/Judge/RepairすべてでPASSした。HEAD `a960f8728bb2e2c14e282d639170ffed6af11e9a`に対するfresh schema 2 full probeも別途実行し、16 checksすべてtrue、全mode verified、revision/profile/command/runtime fingerprint一致、`model_api_used=false`を確認した。これは合成marker read-denyを示すが、実認証fileやCodex親processの実モデル通信を検証していない。後続の最終commitには再度fresh evidenceを生成する。

### 認証storage modeの比較と未解決条件

固定CLIの[storage.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)および[manager.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)の契約は次のとおり。

| Mode      | Refresh後の永続性                                  | auto fallback                             | process競合とshell境界                                                                                                   | 判定                                                           |
| --------- | -------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| file      | 選択中のCODEX_HOME/auth.jsonへtruncate/write/flush | なし                                      | process間lock・atomic replaceなし。同じOS userのprocessからstoreを隔離しない                                             | attempt copyでは更新がcleanupで失われる。永続store単独も不採用 |
| keyring   | keyring backendへ保存。CODEX_HOME由来keyで識別     | なし                                      | refresh全体のprocess間lockなし。同一OS identityからのkeyring利用も分離しない。WSL outer mount内でのbackend可用性は未確認 | 直接file fallbackは避けるが競合を解決しないため不採用          |
| auto      | keyring成功時はkeyringへ保存                       | keyring load/save error時にfileへfallback | file fallbackでは平文storeと同じ可視性・競合条件                                                                         | fail-closed storeとして不適合                                  |
| ephemeral | process内memory store                              | なし                                      | Codex process終了後の次attemptへ残らない                                                                                 | 更新永続化要件に不適合                                         |

当時のattempt-local auth.json copyはCodex refresh結果を次attemptへ残さなかった。固定CLIのrefresh mutexは同じAuthManager内だけで、別attempt・runner外Codex processと共有されない。このcopy/delete方式を廃止し、2026-10-27の指示に基づき専用OS identityと永続store bindを候補実装した。専用identity単独では競合防止の証明にならず、runner lock単独も非協調processを止めない。OS user作成・root-owned runtime/source配置・許可されたprocess起動元の制限、および固定CLI source harnessのsynthetic refresh testが未達なら本番では使わず、fail-closedを維持する。

## 2026-10-25 refresh token調査の追記

現行経路は元storeの`auth.json`をattempt専用`CODEX_HOME`へ複製し、Codex終了時にその一時`CODEX_HOME`を削除する。固定CLI `0.163.0`はrefreshに成功すると選択中のauth storageへtokenを書き戻すため、一時storeでrefreshした結果は次attemptまで残らない可能性がある。次attemptが失効済みの元tokenを再利用し、`refresh_token_reused`になる筋道はあるが、過去の失敗記録を確認できていないため直接原因とは確定しない。

CLIのrefresh semaphoreは同一`AuthManager`内の排他であり、別プロセス間では共有されない。file backendにもCLI横断のlockはなく、別attemptの一時copy、または同じ元storeを指定した外部Codex processとのrefresh競合を防止できない。固定CLIの公式実装は[auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[token persistence](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[file storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)で確認する。

評価専用の永続`CODEX_HOME`をユーザーが公式Codex CLIで管理する案は、refresh結果を同じstoreに保存する点では候補となる。しかし、同storeを利用する非協調processとの競合はrunner内lockだけでは防げず、永続store単独で評価shellと外部processの安全境界を作れない。現行named permissions profileはsynthetic markerをinner shellから隠すことを実測したが、実認証を使った保存・連続attempt・process競合検証は行っていない。未検証の回避策は採用せず、二重bubblewrapを維持して実認証評価を停止する。

2026-10-25の`--auth-status-only`は固定runtimeでChatGPT loginを確認したが、refresh保存、競合防止、実認証fileのshell可視性は検証していない。詳細、現環境でのsuite結果、実行再開条件は[調査・検証報告 v04](../reports/2026-10-25_pr17-chatgpt-auth-recovery_v04.md)に記録する。古いevidenceを新しいrevisionの受入根拠に流用しない。

## 2026-10-25 通常WSL2ターミナルでの再検証とfresh evidence条件

利用者から、通常のWSL2 UbuntuターミナルでDeterministic repository suite 293件、WSL2 formal launcher integration 1件、AF_UNIX socket bindがすべてPASSし、Codex開発sandbox内の`EPERM`とDeterministic test failureは再現しなかったとの報告を受けた。以前のCodex sandbox実行で発生した4 failures / 1 errorとAF_UNIX bind EPERMはそのsandbox環境での結果として保持する。テスト条件、Hook、execpolicy、sandboxの設定は変更しない。通常WSL2の再検証はsandbox固有の障害をコード不具合と分類しない根拠になるが、fresh formal isolation evidenceの代わりにはならない。

formal probeは次の条件を満たしたclean evaluator revision上で改めて実行する。

- Commit後のclean checkoutとHEAD SHAを基準にする。working treeがdirty、profile/evidenceが別revision、またはevidenceが古い場合は使用しない。
- schema 2 profileは最終run条件に一致させ、AgentはCodex CLI `0.163.0`、`gpt-6-luna`、reasoning `max`、timeout 900秒、`workspace-write`、shellのみ、MCPなしを指定する。Judge configも必須で、`command_argv=["codex"]`、sandbox `read-only`。deterministic runのJudge disabledは保持するが、probeは隔離確認用のJudge sandbox smokeも実行する。
- agent command JSONは`["codex"]`のみ。これはtemplate fingerprint用で、本番`codex exec`やモデル通信を起動する引数ではない。
- `QAEVAL_CODEX_RUNTIME_ROOT=/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final`を指定し、Codex package/CLI/bundled bwrap digestとversionを現行launcherで再照合する。
- profileは`verification.evidence_path="isolation.json"`とし、fresh run IDのoutput rootをprobeと後続runで共用する。従来の15件と合成auth marker可視性checkを加えた16 required checks全てtrue、Agent/Judge/Repair mode evidence verified、profile/command/runtime fingerprint一致を確認する。`model_api_used=false`を必須とし、全auth read-deny check成功時のみ`authentication_shell_visible_risk=false`とする。失敗または未実行ならtrueを維持する。refresh persistenceとprocess concurrency unresolved flagsは別にtrueであり、production実行を拒否する。
- Probeはfixed runtimeの`codex sandbox` smokeとsynthetic filesystem/network sentinelを使う。実auth fileは渡さず、markerだけを持つ合成`auth.json`でinner shellのread拒否を検査する。login status、refresh、`codex exec`、モデルAPIは呼ばない。

通常WSL2でのdeterministic suite、launcher integration、host AF_UNIX bindの個別コマンド、およびfresh evidenceコマンド例はAgent READMEの「WSL2通常ターミナルでの検証とfresh evidence」に記録する。

## 合成認証検証とfail-closed条件

現行unit testのsynthetic auth markerはlogin status分類、API key environment除外、ログredaction、temporary CODEX_HOME cleanup、copy/delete方式におけるfake child更新のattempt間喪失を検査する。fake child testはrunnerのfile操作だけを検証し、Codex refresh成功や本番の直接原因を確定しない。固定Codex CLI source harnessでのrefresh/persist/reloadは未実施である。

追加したformal smokeはAgent/Judge/Repairそれぞれで合成markerを`/codex-home/auth.json`へ置き、store本体、host側store path、他attempt store、environment、可視process FDに関するread可否・存在情報を値を出さずbooleanで検査する。markerが見えればmodeと全体evidenceをverifiedにしない。非協調processを含む全store競合の方式はまだ確立していないため、runner lockだけで解決済みとは扱わない。

固定Codex CLI `0.163.0`の公式実装で確認できるrefresh mutexは同一`AuthManager`内に限られ、file backendは選択された`CODEX_HOME/auth.json`へtruncate/write/flushする。Codex CLIには`CODEX_REFRESH_TOKEN_URL_OVERRIDE`があるが、固定CLIの`login status`は保存済みmodeを判定するだけでrefreshしない。loopback mock endpointを使うCodex source testなら、synthetic tokenのrefresh・persist・reloadを外部モデル通信なしで検査できる。ただしこのoverrideはsource上でtest-onlyに制限されず、production launcherでは使わない。Codex CLIを使う外部processがrunner独自lockを取得する公式契約はない。よってrunner内lockのsynthetic testだけで非協調processとの競合を解消したと扱わない。synthetic shell marker read-denyはfresh probeでverifiedだが、更新永続化・process競合は未解決のため、launcherは全modeをfail-closedにする。根拠は[Codex 0.163.0 auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)および[file storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)。

## 2026-10-26 認証可視性checkと実行停止（HEAD 73328d4時点）

作業開始HEAD `73328d4237a5c1ab913938ed83f980ee9b5a9a37`を基準に、launcherの現行copy/cleanup経路でfake childがattempt専用`auth.json`だけを更新し、cleanup後のattempt 2が元の古いmarkerを読む回帰testを追加した。このtestはrunnerのfile操作で更新結果を失うことを示すもので、Codex CLI自身のOAuth refresh成功や既発生の`refresh_token_reused`の直接原因を証明しない。固定CLI本体のrefresh/persist/reload source harnessは本repositoryにないため実行していない。

正式な`sandbox_smoke()`は合成auth markerをattempt homeへ置き、各Agent/Judge/Repairのinner shellから`/codex-home/auth.json`、host側のstore path、他attemptのauth pathを開けないこと、markerがenvironmentに含まれないこと、可視process FDのtargetにauth storeが現れないことを値を出力せず確認する。既存15 required checksに認証可視性checkを加え、合計16件すべてをprofile evidenceの必須条件とする。marker readが可能な場合はmode evidenceと全体evidenceをverifiedにせず、`authentication_shell_visible_risk=true`を維持する。

当該HEAD時点ではshell read-denyも未解決だった。後続のnamed permissions profileとsynthetic marker試験では、全modeのshell read-denyをformal evidenceで確認した。現行launcherは`authentication_refresh_persistence_unresolved`または`authentication_process_concurrency_unresolved`のいずれかがtrueなら、Agent/Judge/Repairいずれも`_auth_material()`、auth file copy、Codex起動より前に`execution_error`で停止する。専用persistent `CODEX_HOME`、runner内だけのOS lock、file permission変更は非協調Codex processとの競合を解決しないため導入しない。refresh永続化とprocess競合が解決されるまで、TC-OUT-001を含む実モデル通信を開始しない。

probe setupでhost AF_UNIX bindが失敗したとき一時auth home、other-attempt home、outside sentinel、socketをcleanupする経路を追加し、cleanup failureを隠さず専用safe errorとして返す。HEAD `73328d4`時点のCodex開発sandboxではformal launcher integrationがAF_UNIX bind時に`EPERM`で停止したが、この失敗は通常WSL2 hostでは再現しなかった。後続HEAD `a960f87`で通常WSL2上のDeterministic repository suite 293件、formal integration 1件、fresh full probe 16/16がPASSした。これらのevidenceは各対象revisionに限る。検証環境・fresh evidence pathとfingerprintの現状は[PR #17 現在状態報告](../reports/2026-10-26_pr17-current-status_v00.md)を参照する。

当該時点の個別suiteと認証調査は[認証調査報告 v05](../reports/2026-10-26_pr17-chatgpt-auth-recovery_v05.md)および[v06](../reports/2026-10-26_pr17-chatgpt-auth-recovery_v06.md)に記録する。現在状態は[PR #17 現在状態報告](../reports/2026-10-26_pr17-current-status_v00.md)を参照する。

## 2026-10-26 HEAD e87a489のfresh WSL2合成検証

GitHub PR #17のHEAD `e87a4890514af6bff09b90bb180e4dcd9c3fddb7`に一致するclean作業treeで、Python 3.11.17、PyYAML 6.0.3、固定Codex runtime `0.163.0`と同梱bubblewrapを検証した。以下はこのrevisionで新たに実行した結果であり、過去のevidenceを流用していない。

- Deterministic repository suiteは293件PASS。Codex sandbox既定実行ではAF_UNIX `EPERM`と一時directoryが`/tmp/.git`配下になる問題が発生した。`TMPDIR=/var/tmp`にしてhost WSL実行した場合は、同じsuiteが全件PASSした。テスト条件やsandboxは変更していない。
- 固定runtimeを使うformal launcher integrationは、Codex sandbox内ではhost AF_UNIX bindの`EPERM`で失敗した。host WSL実行ではAgent/Judge/Repairのsynthetic auth marker checkまで到達し、`authentication_store_read_denied=false`のため拒否された。host AF_UNIX bind単体はPASS。
- READMEの正式手順に従い、新規run root `.agent-eval-runs/pr17-isolation-e87a489-20261025T234245Z`へfresh schema 2 evidenceを生成した。`agent-command.json=["codex"]`、`verification.evidence_path="isolation.json"`、`gpt-6-luna`、reasoning `max`、timeout 900秒、固定runtimeを使用した。evaluator revisionはHEADと一致し、profile fingerprintは`sha256:10d3a666dd26c19123cf8ed2cfff1ea4914f14f9f3f5aa15a6316e73c38175d4`、3 mode command fingerprintは`sha256:e25eaf648dc7039953915d93cac78cc23b21b780b60f562ff1aaa53086f25364`。固定runtime digest照合は成功した。
- 16 required checksのうち14件はtrue。`authentication_shell_read_denied=false`と、mode evidenceがverifiedでないことに由来する`agent_judge_separated=false`により、Agent/Judge/Repairはすべて`unverified`、evidence全体も`unverified`。model API、実認証、`codex exec`は使用していない。
- Agent suite 138 PASS / 2 SKIP、Agent repository contract 4 PASS、Semantic suite 27 PASS、Codex Harness 57 PASS / 8 SKIP、`compileall` PASS。Deterministicの293 PASSは上記の`TMPDIR=/var/tmp`を使ったhost WSL実行結果。
- Ruff 0.16.8 checkとtracked Python 239 fileのformat check、およびdprint 0.55.2による今回変更した3文書とfull tracked formatterはPASS。HEAD e87に対するCode Quality CIはSUCCESSだが、この後の文書差分を含むCI結果ではない。

このprobeは認証marker readを拒否できない実装状態を実証したので、15+1 checksの受入条件は未達である。marker値はevidence/logへ出していない。全実行modeで既存fail-closedを維持し、認証の更新・保存・競合・shell非可視性の安全な解決方式が実証されるまでは実Agent評価を停止する。

## Baseline at start of implementation

- Windows開発checkoutは`feat/agent-eval-runner`、HEAD `be574cbaf457a49d2f51a08c1cdc7838e75abd5c`。tracked差分なし。未追跡Docker調査報告2件と既存`.agent-eval-runs/`を保持する。
- GitHub PR #17本文とcommitを確認し、参照HEADが`be574cb...`、PRがopen、baseが`main`であることを確認した。同SHAの直近5 workflowは全てsuccess。Windows checkoutからの`git fetch origin`はHook指定のcanonical commandで試したが、`.git/FETCH_HEAD`への書込みがfilesystem permissionで拒否された。remote同期済みとは主張しない。
- WSL2 Ubuntuは稼働中、kernelは`6.18.54.1-microsoft-standard-WSL2`。WSLにある`/home/sella/src/qa-workflow-skills`はHEAD `2e5005865c437e9aa701504d18186071f27a0343`で変更・未追跡ファイルがあり、評価用clean checkoutとして使わない。別の既存PR17 checkoutもHEAD `34715bf...`から変更されている。
- WSLの既定Pythonは3.12.3、Python 3.11.17もある。Codexは`/mnt/c/.../npm/codex`のWindows shimに解決し、Linux Nodeがなく起動失敗。Linux `bwrap`はPATHから見つからない。PyYAML 6.0.3とCodex Linux packageの現環境での導入状態は未確認。
- 過去の合成検証では、外側bwrapのlimited mounts、user/PID/network namespace、procfs、Codex CLI 0.163.0内側`:read-only`/`:workspace`が起動した。外側`:workspace`がread-onlyのときinner sandboxの`.git`初期化が`EROFS`になった記録がある。
- 意図的にFD 4を継承させるとinner shellから`/proc/self/fd/4`および`/dev/fd/4`経由で合成sentinelを読めた。通常のexecutor起動は`close_fds=True`である。正式launcher経路でのFD negative testが必要。
- 合成auth file / API keyはCodex shellから読めた。現行の一時`CODEX_HOME`方式に同じ残留リスクがあるため、実認証を使わない。outer bwrapをnetwork unshareするとCodex API通信も失敗するため、outer/inner通信境界の実効確認が必要。
- 根拠となる既存資料: `docs/reports/2026-10-24_pr17-wsl-sandbox-investigation_v00.md`、`...nested-sandbox-investigation_v00.md`、`...fd-and-auth-boundary_v00.md`、`...docker-sandbox-compatibility_v00.md`。

## Existing contracts

- QA Skill package配置、Evaluator / Skill / targetの固定revision、canonical artifacts、`artifact-index.json`、deterministic grader、semantic rubric、Judge承認bindingと`judge_unverified`、Skill使用観測、F02/F03/F04の原因帰属・独立回帰、比較条件を維持する。
- QTS targetは`qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`、scenarioは`qa-training-store-checkout-payment-web-v1`。Codexを起動しないdeterministic verifierのDocker image、image ID、network-none契約は変更しない。
- Agent / Judgeは別process、別outer bwrap、別作業領域、別一時`CODEX_HOME`とする。Judge入力はstdinのみ、shell/MCP/web/Skill rootは無効、JSONLにtool eventがあれば`judge_unverified`を維持し、raw JSONLは保存しない。
- `executor.run_command()`のargv起動、`shell=False`、`close_fds=True`、timeout、process-tree cleanup、safe diagnostic、既存stdin/stdout/stderr契約を再利用する。
- 旧Docker結果は保持するが、新profileとの品質比較には使用しない。必須隔離条件が1つでも未確認のrunは`isolation_unverified`となり、正式評価に進めない。
- 実認証は今回の方式変更承認に含まれない。synthetic markerでinner shell read-denyは検証済みだが、実認証の保存・read boundaryは試験していない。refresh永続化とprocess競合が未解決でlauncherがfail-closedの間は、隔離probeがverifiedでも実認証評価を開始しない。

## 実行記録（2026-10-24）

### 実装と環境

- Agent、Judge、RepairのCodex起動を共通WSL2二重bubblewrap launcherへ接続した。production argvには`--no-daemon --strict-config`、固定`sandbox_policy`、tool/MCP無効化、固定model/reasoning値を含める。QTS deterministic verifierはDocker契約のまま。
- WSL2 Ubuntu kernel `6.18.54.1-microsoft-standard-WSL2`、Python `3.11.17`、Codex CLI `0.163.0`、bundled bubblewrapを使用した。package SHA-512、Codex SHA-256、bwrap SHA-256は報告書とevidenceに記録した。
- WSLでの最終実行確認に使ったclean checkoutは一時検証snapshot `60198301ae4989800a699c56e994eb2814870ac4`。これはPR branch commitではなく、同期したソースを含む隔離snapshotである。evidenceはこのsnapshot revisionに結び付けられているため、対象branchのcommit後にlive run用profile evidenceを再生成する。
- nested bwrapが起動できないためouter user namespaceの`--uid 0 --gid 0`指定を除いた。Repairのwrite rootはCodex CLI設定と外側mountの両方で選択Skillひとつに限定する。Agent/Repairはattempt workspace rootをwrite可能にし、sandbox開始時点で存在するsource childを個別read-only bind、outputとattempt-local`.git`/`.codex`を専用mountにする。
- Codex CLIのstandalone `sandbox` commandは明示的なsandbox mode overrideがない場合read-onlyへdefaultする互換動作だった。合成probeでは`--config sandbox_mode="workspace-write"`を明示し、production `codex exec --sandbox workspace-write`と一致する設定経路を検証した。[0.163.0 pinned CLI source](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/debug_sandbox.rs#L660-L664)

### 検証結果

| 検証                                               | 結果                            |
| -------------------------------------------------- | ------------------------------- |
| WSL2 Agent tests（sandbox integration有効）        | PASS、106 tests、1 skipped      |
| WSL2 Runner / Agent API                            | PASS、4 tests                   |
| WSL2 Semantic Eval                                 | PASS、27 tests                  |
| WSL2 Deterministic Eval                            | PASS、293 tests                 |
| WSL2 formal Agent/Judge/Repair sandbox integration | PASS、1 test                    |
| WSL2 `compileall`                                  | PASS                            |
| Ruff `0.16.8` `format_tracked.py check`            | PASS                            |
| Windows workspace cleanup + launcher tests         | PASS、23 tests、3 skipped       |
| WSL2/Windows `git diff --check`                    | PASS                            |
| `isolation_probe.py` formal evidence generation    | PASS、全15 required checks true |

- Formal synthetic evidence: `~/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/checkout-final/.agent-eval-runs/pr17-wsl2-synthetic-probe-20261024-02/isolation.json`。Agent、Judge、Repairの各mode evidenceも`verified`。fresh procfs、nested user/PID/mount/network/IPC namespaces、Evaluator/host/other-attempt/Windows path隔離、FD非継承、existing source entry write拒否、専用output write許可、Repair選択Skill write許可、symlink/network/socket/WSL interop拒否、timeout cleanupを記録した。内側Codex sandboxはouter UTS namespaceを共有する実測であり、他の必須inner namespaceは分離された。
- Probeは合成sentinel/profileのみを使った。`model_api_used=false`。一時`CODEX_HOME`内の実認証fileがinner shellから読めないことは確認しておらず、evidenceは`authentication_shell_visible_risk=true`を保持する。実認証、live Codex exec、Agent/Judge品質評価、Judge fixture承認、候補Skill採用は行っていない。
- `git fetch origin`は`.git/FETCH_HEAD`のfilesystem permissionで拒否された。baseline commitのCI successは今回の変更を含まない。PR headの最新CIは未確認。

詳細と残課題は[`2026-10-24_pr17-wsl2-sandbox-migration_v00.md`](../reports/2026-10-24_pr17-wsl2-sandbox-migration_v00.md)を参照。

### 完了状態

- WSL2実装、合成隔離probe、指定repository test/format/checkはPASS。
- 対象branchへのcommit/push、push後の5 CI確認、PR本文更新はこれから試行し、その成否を最終報告へ反映する。
- PR #17の正式な実Agent/Judge受入は未完了。実認証と人間承認済みJudge fixtureを別途用意するまで実評価を開始しない。

## Scope

### Included

- 4つのAgent evaluation Planと`scripts/skills/evals/agent/README.md`の現行実行契約をWSL2方式へ更新し、旧Docker実行記述を履歴・QTS verifier用途と区別する。
- 共通WSL2/bubblewrap launcher、固定profile schemaとevidence、workspace/output mount準備、既存executor連携、timeout/cleanup、provenanceと比較条件を実装する。
- `run.py`、`qa_training_store.py`のCodex Agent/Judge、`judge_validation.py`、`improve.py`のsemantic/mixed/deterministic analysis/repair/再評価全経路を共通launcherに接続する。
- `isolation_probe.py`をWSL2二重bubblewrap用に置換し、固定binary/package digest、mount/namespace/procfs、FD、path、network、Agent/Judge分離、証拠欠落/改変を検査する。
- fake contract testsと正式launcherを通る合成Linux統合testを追加する。実認証・モデルAPIなしで、Agent/Judge/Repairのprobe mode、内側Codex sandbox、読書き境界、FD、symlink、Windows sentinel、network/socket、timeout/cleanup、証拠拒否を検証する。
- 完了状態・未達項目・CIを記録した`docs/reports/2026-10-24_pr17-wsl2-sandbox-migration_v00.md`を作成する（既存なら連番を使う）。
- 選択ファイルのみstageする段階commit、通常push、最新SHAの5 CI確認、PR本文先頭の更新を行う。

### Excluded

- 新規VM/クラウド、有料利用、Docker権限緩和、Codex sandbox無効化、auth broker/proxy、認証全面変更。専用WSL2 OS identityの準備は後続明示指示でこのPlanの範囲に追加されたが、管理者認証が必要なOS変更は管理者が通常WSL terminalで実行するまで保留する。
- 実認証・モデルAPI送信、実Agent/Judge品質評価、Judge fixture承認、`QTS-SEM-008`専用fixture追加、改善候補の自動採用。
- Docker verifierの移行、既存評価結果の削除、PR base変更、merge/close、force push。

## Risks and assumptions

- 検証済み事実: outer bwrap + inner Codex sandboxのpath・namespace・procfs・通常FD close条件は既存合成記録で一部成立している。これらは新しいformal launcherの受入証拠を代替しない。
- 主要リスク: Codex親processはモデルAPI通信を必要とするが、inner shellはTCP/DNS/AF_UNIX/WSL interopを使えない必要がある。既存probeの単一TEST-NET失敗だけではegress隔離をPASSにしない。
- 主要リスク: inner `workspace-write`の一時`.git`準備要求とouter read-only source mountを両立できるか未確認。outputとCodexが必要と実測した一時場所だけをwrite可能にし、評価sourceが変更可能ならその設計を採用しない。
- 残留リスク: Codex認証fileや環境変数は同一outer namespace内のshellから読める可能性がある。broker等は追加せず、実認証は別途判断まで停止する。
- 現WSL sessionにはLinux Codex実行binaryとLinux Nodeが見つからない。固定公開package `@openai/codex-linux-x64@0.163.0`の既知SHA-512は過去報告に記録済み。必要ならユーザー権限の一時領域へ取得し、version・digest照合後のみ使う。管理者権限を要する導入が必要と判明した場合は停止する。
- WSL内に現行HEADのclean checkoutがない。既存checkoutを変更せず、固定Evaluator revisionに対応する新規clean checkoutを用意できなければ、Linux実行検証と正式移行完了は未達とする。
- `.git`はこのsessionのfilesystem policyでread-only。`fetch`は失敗した。commit/pushは実装・検証完了後、許可されたcanonical Git commandで試し、approval reviewerが拒否した場合に代替APIで迂回しない。

## Implementation order

1. 現行PR head、4 Plan、README、profile schema、Agent/Judge/Repair全callsite、既存fake tests、QTS verifier境界を固定する。
2. 本Planに沿って4 PlanとREADMEの正式実行契約を先に更新する。旧Docker Agent/Judge記述と新方式が混在しないよう、過去調査はreportsへ残し、QTS verifier Docker契約だけを明示的に維持する。
3. 既存executorを再利用する共通Linux launcherを追加する。固定argv/mode、binary version/digest、許可mount/environment/path、secure temporary roots、symlink/TOCTOU拒否、close_fds、process group、timeoutとcleanupを実装する。
4. Profile schema/provenance/comparisonへCodexとbwrap実体、digest、実効outer/inner argv、mount/network、probe/evidence、依存versionを加える。secretは記録・fingerprintしない。Docker profileは読み取り可能だが比較不可とする。
5. Agent、Judge、Repairの起動を同一launcherへ移す。modeごとに独立bwrap/workspace/CODEX_HOMEを構成し、Agent/Judge相互のmount共有を禁止する。QTS verifier Dockerを維持する。
6. Isolation probeと単体/contract testを更新し、旧Docker evidence、別modeのevidence、profile/binary/mount変更、証拠欠落/改変をfail-closedにする。
7. WSL2のclean fixed-revision checkoutと固定Codex packageを準備し、formal launcher自体を通る認証なし合成統合testを実施する。正常・拒否の各事実と終了codeを個別保存する。
8. 要求されたrepository test suites、compileall、formatter、`git diff --check`を独立実行する。Linux-only suiteはWSLで実行し、Windows専用cleanup testもWindowsで実行する。失敗は原因を修正し再実行する。
9. 自己レビューで全callsite、判定契約、QTS verifier、failure cleanup、secret/log/evidenceを確認する。最終reportで実装状態と各受入項目を個別判定する。
10. 関連テスト後に段階commitし、通常push、最新HEADの5 workflow確認、PR #17本文先頭更新を行う。merge/closeはしない。

## Validation

### Repository tests

- `python -m unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -q`
- `python -m unittest discover -s tests/skills/evals/agent -p 'test_*.py' -q`
- `python -m unittest discover -s scripts/skills/evals/semantic/tests -p 'test_*.py' -q`
- `python -m unittest discover -s tests/skills/evals/deterministic -p 'test_*.py' -q`
- `python -m compileall -q scripts/skills/evals/agent`
- `python scripts/format_tracked.py check`
- `git diff --check`

各commandの結果を個別に判定する。テスト中に外部LLMを呼ばない。

### Linux synthetic integration

新しいformal launcher/probeから実Codex CLI 0.163.0と同梱bwrapを起動する。親processがsentinel FDをopenした状態で未継承を確認する。outer/inner namespaceとfresh procfs、read-only Evaluator/source拒否、許可output write、path/symlink escape、Windows sentinel、`/proc/self/fd`・`/dev/fd`、TCP、DNS、AF_UNIX、WSL interop、localhost、追加mount/argv/profile/binary/evidence拒否、Agent/Judge独立性、timeout/cleanupを合成sentinelで検証する。各probeについて実際の観測とexit codeを記録する。Codex `sandbox` smokeはformal launcher経由、無認証でのみ行う。live `codex exec`は実行しない。

### GitHub CI

push後の最終SHAで`Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Code Quality`、`Codex Harness`をすべて確認する。過去SHAのsuccessを代用しない。

## Completion criteria

- 4つの既存PlanとREADMEがWSL2二重bubblewrapを現行方式として記述し、旧Docker Agent/Judge方式を現行の正式手順として残していない。QTS verifier Docker契約は維持する。
- 共通run、QTS Agent/Judge、fixture Judge、improveのsemantic/mixed/deterministic analysis/repair/independent regressionの全Codex経路が共通launcherに接続し、modeごとに別process/namespace/workspace/temp CODEX_HOMEを持つ。
- 固定binary、argv、mount、environment、profile、pathを検証し、不正・差替え・symlink逸脱・不明evidenceでfail-closedになる。FD非継承をformal launcher経路で実測する。
- Evaluator-only情報、Windows filesystem、host home、他attempt/Agent/Judge領域の読取拒否、source write拒否、許可output write、fresh procfs、outer/inner namespaceが新しいlauncherで合成実証される。
- Codex parentのモデルAPI必要性とinner shell通信制限が実効上分離し、全指定negative probeに結果がある。必要な境界を実証できなければ`isolation_unverified`として完了未達とする。
- Profile/evidence/provenanceに固定条件が含まれ、旧Docker profile/evidenceは新方式と比較・検証に使えない。
- 必須単体/contract suite、実Codex sandbox smoke、関連整形/CIがPASSする。fail/skip/error/not runは区別してreportに残す。
- commit、通常push、最新SHA CI、PR本文更新が完了する。これらがfilesystem/reviewer/network制約で拒否された場合は代替手段で迂回しない。
- 実Agent共通/QTS/Judge品質評価、改善実証、独立回帰、PR #17正式受入は実認証・Judge人間承認を別条件として判定し、今回の隔離移行の合否と混同しない。
