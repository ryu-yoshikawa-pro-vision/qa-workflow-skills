# PR #17 WSL2二重bubblewrap実行方式移行Plan

## Goal

PR #17のAgent、Judge、改善分析・修正実行を、既存Docker内Codexの代わりにWSL2 Ubuntu上の外側bubblewrapとCodex CLI 0.163.0の内側Linux sandboxで起動する。既存のEvaluator分離、品質判定、承認binding、QTS verifier、改善条件を保ち、合成データの実効隔離試験がすべて成立するまではrunを`isolation_unverified`として正式評価を拒否する。

このPlanは利用者が2026-10-24に承認した実行方式変更を具体化する。実認証・モデルAPI利用、Judge fixture承認、候補Skill自動採用、merge、closeは含まない。

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
- 実認証は今回の方式変更承認に含まれない。合成markerで実認証の安全性を推定しない。認証がshellから見える残留リスクを記録し、隔離受入が成立しても実認証評価を開始しない。

## 実行記録（2026-10-24）

### 実装と環境

- Agent、Judge、RepairのCodex起動を共通WSL2二重bubblewrap launcherへ接続した。production argvには`--no-daemon --strict-config`、固定`sandbox_policy`、tool/MCP無効化、固定model/reasoning値を含める。QTS deterministic verifierはDocker契約のまま。
- WSL2 Ubuntu kernel `6.18.54.1-microsoft-standard-WSL2`、Python `3.11.17`、Codex CLI `0.163.0`、bundled bubblewrapを使用した。package SHA-512、Codex SHA-256、bwrap SHA-256は報告書とevidenceに記録した。
- WSLでの最終実行確認に使ったclean checkoutは一時検証snapshot `60198301ae4989800a699c56e994eb2814870ac4`。これはPR branch commitではなく、同期したソースを含む隔離snapshotである。evidenceはこのsnapshot revisionに結び付けられているため、対象branchのcommit後にlive run用profile evidenceを再生成する。
- nested bwrapが起動できないためouter user namespaceの`--uid 0 --gid 0`指定を除いた。Repairのwrite rootはCodex CLI設定と外側mountの両方で選択Skillひとつに限定する。Agent/Repairはattempt workspace rootをwrite可能にし、sandbox開始時点で存在するsource childを個別read-only bind、outputとattempt-local`.git`/`.codex`を専用mountにする。
- Codex CLIのstandalone `sandbox` commandは明示的なsandbox mode overrideがない場合read-onlyへdefaultする互換動作だった。合成probeでは`--config sandbox_mode="workspace-write"`を明示し、production `codex exec --sandbox workspace-write`と一致する設定経路を検証した。[0.163.0 pinned CLI source](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/debug_sandbox.rs#L660-L664)

### 検証結果

| 検証                                                 | 結果                            |
| -------------------------------------------------- | ----------------------------- |
| WSL2 Agent tests（sandbox integration有効）            | PASS、106 tests、1 skipped      |
| WSL2 Runner / Agent API                            | PASS、4 tests                  |
| WSL2 Semantic Eval                                 | PASS、27 tests                 |
| WSL2 Deterministic Eval                            | PASS、293 tests                |
| WSL2 formal Agent/Judge/Repair sandbox integration | PASS、1 test                   |
| WSL2 `compileall`                                  | PASS                          |
| Ruff `0.16.8` `format_tracked.py check`            | PASS                          |
| Windows workspace cleanup + launcher tests         | PASS、23 tests、3 skipped       |
| WSL2/Windows `git diff --check`                    | PASS                          |
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

- 管理者権限やOS設定変更、新規VM/クラウド、有料利用、Docker権限緩和、Codex sandbox無効化、auth broker/proxy、認証全面変更。
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
