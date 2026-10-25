# PR #17 ChatGPT認証refresh・WSL2実行・Hook再調査

- **確認日:** 2026-10-25
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **作業branch:** `work/pr17-auth-wsl-20261025`
- **PR branch:** `feat/agent-eval-runner`
- **開始・確認時HEAD:** `dddfdea6c633418bd6f81afdbcdaddbcb2d75339`
- **前回報告:** [`2026-10-25_pr17-chatgpt-auth-recovery_v03.md`](2026-10-25_pr17-chatgpt-auth-recovery_v03.md)

## 状態と実行環境

作業開始時のworktreeはcleanで、作業branchとPR branchは異なる。PR #17のremote HEADは作業開始時HEADと一致し、PRはopenだった。作業対象外の`/home/sella/src/qa-workflow-skills`にはアクセスしていない。

WSL2 Ubuntu kernel `6.18.54.1-microsoft-standard-WSL2`、Python `3.11.17`、PyYAML `6.0.3`を使用した。固定runtimeは`/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final`で、同梱Codex CLIは`0.163.0`。依存関係の再インストールはしていない。

固定runtime rootを指定した`--auth-status-only`は、`authentication_method=chatgpt_login`、`runtime_digest_status=verified`、`codex_cli_version=0.163.0`を返した。これは評価ランナーの選択storeに対するstatus確認であり、開発用Codexのlogin成功だけを根拠にしたものではない。status確認は認証file本文・hashを出力せず、モデルAPI、login、logout、refreshを実行しない。実Agentの認証更新・隔離を受け入れた意味にはならない。

## `refresh_token_reused`の原因分析

現行launcherの経路は次のとおり。

1. `_auth_material()`は`CODEX_HOME`環境変数、未指定なら`~/.codex`を認証元として選び、Windows path、symlink、repo内storeを拒否する。
2. 固定Codex CLIで`codex login status`を実行し、ChatGPT login以外を拒否する。
3. `_prepare_codex_home()`は認証元の`auth.json`をmodeごとのattempt専用一時`CODEX_HOME`へ複製する。
4. Codex `exec`は一時`CODEX_HOME`を使う。refreshが必要になるとCodexはそこでtokenを更新・保存する。
5. `cleanup_codex_home()`はattempt終了時に一時`CODEX_HOME`を削除する。次attemptは元storeから読み直すため、前attemptで保存したrefresh結果を引き継げない可能性がある。

この経路は`refresh_token_reused`のもっとも具体的な候補原因だが、記録された失敗時のrefresh・storage診断を確認できていないため、直接原因と断定しない。

固定CLI `0.163.0`の公式実装では、refreshは同一`AuthManager`内のsemaphoreで直列化し、成功後のtokenは選択中の`AuthStorageBackend`へ保存する。[auth manager refresh](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[token persistence](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)

file backendは`auth.json`をcreate/write/truncateで保存し、write・flush失敗はエラーにするが、別プロセスで共有するlockやatomic replaceを提供しない。[file auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs) 従って、別attemptが各自のtemporary copyで同じ元refresh tokenを使う競合、または元storeを明示的に共有する別Codex processとの競合は、CLI内部のsemaphoreでは防げない。`refresh_token_reused`はCLI内でrefresh tokenがexhaustedと分類される。[failure classification](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)

## 安全な修正方法の判断

評価専用の永続`CODEX_HOME`をユーザーが公式Codex CLIで直接管理すれば、Codexがrefresh後のtokenを同じstorage backendへ保存できる。独自token抽出・同期やAPI Keyへの切替は不要である。ただし、これは永続化候補であって安全な修正として確定できていない。

- 現行の合成auth marker検証ではCodex shellからmarkerを読み取れた。永続storeを同じAgent outer namespaceへmountしても、Agent shellからの可視性は解決しない。書込み可能storeなら更新・破損リスクも増える。
- runnerの排他lockはrunner管理下のattempt同士にしか適用できない。専用storeを指定した外部Codex processはそのlockを取らない可能性があり、全利用者を協調させるCLI横断lockの契約もない。
- read-only auth fileでは更新結果を永続化できず、同じnamespaceのshellにread権限を残したままなので、現時点の制約を満たす設計にならない。

更新結果の永続化、同一storeの全プロセス競合防止、refresh失敗時の停止、Agent shellからの認証情報非可視性を同時に実証できる方法を確定できなかった。このためlauncher、認証方式、profile/evidence、grader、rubricは変更していない。合成testの条件を弱めず、auth broker、token proxy、独自認証frameworkも追加しない。`authentication_shell_visible_risk=true`、Agent/Judge/Repairの二重bubblewrap、ChatGPT login限定を維持する。

追加の公式source確認で、0.163.0のauth managerは`CODEX_REFRESH_TOKEN_URL_OVERRIDE`を読み、未設定時には公式OAuth token endpointを使うことが分かった。このoverrideはsource上でtest-onlyに制限されていない。固定CLIの`codex login status`は`load_auth()`で保存済み認証modeを表示し、refreshを行わない。そのためloopback mock endpointを使う真のrefresh/persistence検証は、固定Codex source test harness内のsynthetic AuthManager/FileAuthStorage testとして設計できるが、現行repositoryにはそのCodex test harnessがなく、固定CLIにrefresh-only subcommandもない。環境変数をrunnerやproduction profileに追加せず、Codex source testを実行していないため、refreshのend-to-end persistenceは未検証のままである。[0.163.0 auth manager source](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[0.163.0 login status source](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs)

Codex `0.163.0`の既存`auth_tests.rs`にはsynthetic auth fileに対する`persist_tokens()`のunit testがあるが、OAuth refresh endpointへのrequestや次processからの再読込は検査しない。[0.163.0 auth tests](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/auth_tests.rs) source-levelで足す試験では、(a) loopback endpointへのrefresh requestだけを許し、synthetic rotation後に同じFileAuthStorageを再生成して次attemptのmarkerを確認、(b) endpoint error時に保存値が部分更新されずCLIが失敗することを確認、(c)別processをbarrierで同時に起動して同一synthetic store/refresh markerが使われる競合を再現し、runnerのlockがある場合は片方の直列化またはfail-closedを確認、(d)Agent/Judge/Repair formal launcherで同じsynthetic fileのreadを試し出力はread可否booleanだけにする、の4系統に分ける。単一processの成功試験はprocess間lockやAgent shell非可視性の証明にはならない。

## Suite・隔離・品質検証

全コマンドは個別に実行した。ここでは外部LLMを呼んでいない。

| 検証 | 結果 |
| --- | --- |
| Agent suite | PASS: 135 tests、2 skipped |
| Agent repository contract | PASS: 4 tests |
| WSL2 launcher unit tests | PASS: 21 tests、1 skipped |
| Runtime trace capture | PASS: 11 tests |
| Executor tests | PASS: 4 tests、1 skipped |
| Semantic runner tests | PASS: 27 tests |
| Semantic repository tests | PASS: 13 tests |
| Deterministic runner unit tests | PASS: 13 tests |
| Deterministic repository suite | PASS: 293 tests（通常WSL2ターミナルでの利用者報告）。Codex sandbox内の先行実行では4 failures・1 errorだったが通常WSL2では再現しなかった |
| WSL2 formal launcher integration | PASS: 1 test（通常WSL2ターミナルでの利用者報告）。Codex sandbox内の先行実行ではAF_UNIX bindがEPERMだった |
| Host AF_UNIX socket bind | PASS（通常WSL2ターミナルでの利用者報告）。inner shellからの接続拒否とは別の検査 |
| Codex Hook tests | PASS: 32 tests |
| Codex execpolicy CLI tests | PASS: 8 tests using the fixed runtime CLI `0.163.0`; the first invocation resolved the Windows npm shim and failed before test setup, then passed after prepending the fixed runtime binary directory to `PATH` |
| Codex config tests | PASS: 5 tests |
| README内profile / command JSON schema check | PASS: schema 2 profileと`["codex"]`が現行validatorに適合 |
| Hook JavaScript syntax | PASS: `node --check .codex/hooks/pre_tool_use_policy.mjs` |
| `compileall` (Agent scripts/tests) | PASS |
| Ruff check/format | BLOCKED: `format_tracked.py check`を実行したが`ruff` executableがなく起動できない。依存追加なし |
| `dprint check` | BLOCKED: optional Linux binary未導入。取得はDNS失敗と`sandbox`の`spawnSync curl EPERM`で完了せず、再インストールなし |
| `git diff --check` | PASS: tracked文書差分。新規reportも`git diff --no-index --check`で空白errorなし |

先行するCodex開発sandbox内のDeterministic suiteでは、SQLite workflow testの一時rootが`/tmp`に作られ、その親`/tmp/.git` markerを`artifact_graph._local_sqlite_path()`がGit worktree判定して拒否する4 failureと、static server testのsocket bind EPERMによる1 errorが発生した。別のCodex sandbox実行ではformal launcher integrationの`sandbox_smoke()`がhost AF_UNIX bind時にEPERMとなった。これらの実行結果はそのsandbox環境内の制約を示す。

今回、利用者が通常のWSL2 Ubuntuターミナルから同じDeterministic repository suite 293件、formal launcher integration 1件、host AF_UNIX bindを実行し、すべてPASSしたと共有した。Codex sandbox内での`.git` marker由来failureおよびsocket EPERMは通常WSL2では再現しなかった。従ってこれらを現行実装の不具合として扱わず、通常WSL2でのPASSを新しい環境結果として記録する。元のsandbox内の失敗記録は削除していない。検証条件や安全設定も変更していない。

このworktreeには既存の合成`isolation.json`があり、`evaluator_revision`は開始時HEADと一致し、15 required checksとAgent/Judge/Repair mode evidenceが`verified`、`model_api_used=false`、`authentication_shell_visible_risk=true`だった。これは今回の実行で再生成したものではないため、今回のprofile/実装受入証拠としては使わない。

今回の作業treeにはprobe入力用のexecution profile JSONがありません。文書・Hook修正を含みdirtyなため、probeが要求するclean evaluator checkout条件も満たしません。したがってfresh formal probe/evidenceは未生成です。formal launcher integrationの先行Codex sandbox EPERMは、通常WSL2ターミナルで1件PASSしたとの利用者報告により環境差と判明しましたが、fresh probeが未実行という状態は変わりません。

既存の`.agent-eval-runs/pr17-auth-wsl2-synthetic-20261025/isolation.json`は作業開始時HEAD `dddfdea6c633418bd6f81afdbcdaddbcb2d75339`に結び付いたartifactとして保持し、新しいrevisionの根拠に流用しない。

## Fresh isolation evidenceの入力条件

`isolation_probe.py`はschema 2 profileとagent command JSONを必須引数として読み、`verify_runtime()`で`QAEVAL_CODEX_RUNTIME_ROOT`の固定package/runtimeを照合する。profileは最終run条件へ一致させる。Agentは`codex`、`gpt-6-luna`、reasoning `max`、timeout 900秒、CLI `0.163.0`、`workspace-write`、shellのみ、MCPなし、WSL2 dual bubblewrapを指定する。Judge fieldsもschema上必要で、commandは`["codex"]`、sandboxは`read-only`。deterministic runではJudgeを実行しないが、probeはAgent/Judge/Repairのsandbox smokeを個別に行う。

`agent-command.json`の内容は固定JSON argv `["codex"]`。これは本番`codex exec`の自由指定ではなく、launcher command templateのfingerprint入力である。profileの`verification.evidence_path`を`isolation.json`とし、新規run IDのoutput rootをprobeと後続runで共用する。probe前にEvaluator checkoutはcleanであり、HEAD revision、profile fingerprint、agent command fingerprint、固定runtime digestが記録される必要がある。出力は15件すべてtrue、3 mode evidenceがverified、`model_api_used=false`、`authentication_shell_visible_risk=true`であることを確認する。probe自体は`codex sandbox`のみを実行し、auth status、real `codex exec`、モデルAPIは呼ばない。実行コマンドはAgent READMEの「WSL2通常ターミナルでの検証とfresh evidence」を参照。

## 合成認証データによる検証方針

現行launcherのunit testsは合成markerをsource `auth.json`に置き、ChatGPT login status判定、secret-free observations/log、API key environment除外、attempt homeのcleanupを確認する。一方、Codex subprocessとlogin statusはmockであり、refresh後の保存、attempt間引継ぎ、process間競合、inner shell marker read-denialは確認していない。formal `sandbox_smoke()`は認証fileを渡さず、二重bubblewrapとinner shellの境界を検査する。

追加の合成検証は役割を分ける。まずfake childがattempt copyだけを書き換えるunit testで、現行copy/delete方式の更新喪失を検出する。将来lockを実装する場合は、共有するOS lockを使う複数runner processをbarrierで同時起動し、直列化またはfail-closedを確認する。ただし、Codex CLI 0.163.0自身はCLI全体で共有するlockを提供しないため、このテストは非協調の外部Codex processを排除した証拠にはならない。実装でこの範囲を満たせない場合は修正とrunを止める。

shell可視性は、synthetic markerのみを入れたauth fileを正式launcherと同じ`/codex-home/auth.json` mountに置き、Agent/Judge/Repairのinner shellからreadできるかをmarkerを出力せずbooleanで判定する。期待値はread-deniedであり、可視なら残留riskとしてfail-closedにする。過去にsynthetic auth markerをCodex shellから読めた観測があるため、成功を前提にしない。固定Codex CLIのsourceは同一`AuthManager`内のrefresh mutexと、選択中storage backendへの保存を示すが、別process mutexは示さない。[Codex auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[Codex file auth storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)。

synthetic fileへのfake writeはrunnerの保存経路を検査するだけで、公式CLIのOAuth refresh成功は証明しない。固定source内の`CODEX_REFRESH_TOKEN_URL_OVERRIDE`をloopback mockへ向けるsource-level testは実token・外部auth通信なしで構成できるが、固定CLI `login status`はrefreshを行わず、CLIにmodel requestなしでrefreshだけを起動するsubcommandはない。従ってこの検証はCodex source test harnessを使う必要があり、本repositoryでは未実施である。実tokenの読み取り・操作、外部auth endpointへの呼出しは行わない。

## 実行再開条件と未完了項目

実Agent評価（deterministic / `test-case-design` / `TC-OUT-001` / `codex` / `gpt-6-luna` / reasoning `max` / repeat 1 / timeout 900秒 / Judge disabled）は未実行である。実モデル通信の前に次が必要。

1. Codex公式storageを使う認証更新の永続化と連続attemptを、実tokenを読まず合成storeで検証する。
2. 同一認証storeを使うrunner内外のプロセス競合を防ぐか、競合を検出してfail-closedにする方式を確定する。
3. Agent/Judge/Repair shellが合成認証markerへアクセスできないことを、二重bubblewrapの正式経路で確認する。実auth fileは試験に使わない。
4. 固定runtime・現在profileに対して15件のrequired isolation checksと必要な追加認証negative testを再実行し、fresh evidenceを作る。
5. 合成検証環境のsocket制約を承認済みの実行環境で解消し、正式launcher integrationを通す。保護条件を弱めない。
6. 現行のCodex embedded/non-shared runtimeで`PreToolUse`とexecpolicyの受入を完了する。通常Hookが不許可Git操作を止めたことと、execpolicyの`git push --force`拒否は確認したが、fresh `codex --no-daemon --strict-config` runtime acceptanceは未実施。
7. 実認証のshell可視性という残留risk、およびChatGPT利用枠への影響に対する利用者の明示承認を確認する。

開発作業用の`--auth-status-only`成功はこれらの代わりにならない。モデル・reasoning値を変更せず、認証条件が揃うまでは実Agent/Judge/Repairを停止する。

## Git Hookの`show-ref`誤判定修正

Git公式マニュアルは`git show-ref`をローカル参照の一覧・存在確認コマンドとして説明し、`--verify --quiet`は参照の存在を出力なしで調べ、`--head`はHEAD参照を表示するオプションとしている。[git-show-ref](https://git-scm.com/docs/git-show-ref) これに対し`git update-ref`は参照のOIDを書き換えたり、`-d`で削除したりする。[git-update-ref](https://git-scm.com/docs/git-update-ref)

`.codex/hooks/pre_tool_use_policy.mjs`の`readOnlyGit()`に`show-ref`を読み取り専用コマンドとして一項目追加した。変更前の回帰testは通常の`git show-ref`をcanonical root指定不足として拒否することを再現し、変更後は通常形、`--verify --quiet`、`--head`、branch/tag指定、PowerShell `git.exe`を含む32件のHook suiteがPASSした。`git show-ref --verify --quiet refs/heads/work/pr17-auth-wsl-20261025`も現在のHook経由でexit 0を確認した。

同じHook testで非canonicalな`git update-ref`、`clean`、`rm`、force pushの拒否を確認し、canonicalな`update-ref` / `clean` / `rm`は既存のexecpolicyへ渡る境界を確認した。固定Codex CLI `0.163.0`のexecpolicy tests 8件は`update-ref`、`clean`、`rm`、force push等を引き続き`forbidden`と判定した。Codex config tests 5件もPASS。`.codex/rules/*.rules`とexecpolicy設定は変更していない。

## GitHub / Git反映

確認時、PR #17はopenでPR branch headは`dddfdea6c633418bd6f81afdbcdaddbcb2d75339`。同SHAでは5つの既存CI workflowがsuccessと確認された。これらは本再調査の新しいcommitに対するCIではない。

この報告作成後、Hook修正・回帰test・README・Plan・本報告の5ファイルを作業branchのindexへstageした。通常commitはGit author nameが空のため失敗した。`git -c user.name=... commit`はrepository PreToolUse Hookがglobal option形式を拒否したため中止し、Hook/execpolicyを迂回していない。作業元のdirty worktreeと共有`.git/config`へ影響するidentity変更も行っていない。commit/pushは未実施で、PR headは引き続き`dddfdea6c633418bd6f81afdbcdaddbcb2d75339`、CIはその既存SHAの5件successだけである。安全にcommitするには、このworktreeに適用されるGit author identityをユーザー側で設定し、通常commitを再試行する必要がある。
