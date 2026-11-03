# PR #17 第3段階：保存成果物完全性・Dockerless verifier

## 結論

- 開始HEAD: `6a1e4e46937d220fece0234fb7eed5c67dc2e0b6`
- 調査開始時PR HEAD: `9eee33962d8d9a9b7f63ce037b1874c256df0de9`
- 対象QTS revision: `84ce165493649550832731a60cf436f8ae29c56b`
- 対象の旧開発run: `.agent-eval-runs/pr17-qts-subagent-stage2-20261103-03/`
- 今回の読み取り検査記録: `.agent-eval-runs/pr17-qts-verifier-stage3-20261103-01/`

capture後の保存コピー完全性検査を追加し、`captured-output`側だけの変更を検出する回帰を確認した。Dockerless replayはDockerに依存しない既存のsemantic比較経路へ接続済みで、`verify`と`workflow-runtime`を別々に検査する。候補PythonをEvaluator processへimportせず、root所有bubblewrapが作るuser/PID/mount/IPC/UTS namespaceで起動する。

GitHub runnerではnetwork namespaceの2方式が権限で失敗したため、現在はsealed cBPF seccompでsocket作成・通信syscall、io_uring、x32 ABIを拒否する方式を必須probeで検証する。commit `970cf6b367516a6fdd39a10da231fea934867002`のCIではbubblewrapが`setting up uid map: Permission denied`で止まり、probeは`evidence_unverified`、候補Verifierは未実行だった。Probe未確認の状態では、候補Verifierを起動しない。保存済みQTS runtime requestのDockerless replayとStage 3の正式受入は未達である。

## Stage 2証拠との照合

Run ID `d3ab14c200964233b76acbb26ef7a676`は固定target revisionを記録している。run記録のEvaluator revisionは`296e64919a61617243b22f56b3bb3edd16693244`、Skill revisionも同SHAで、現在のsourceとは一致しない。revisionの異なるEvaluatorとの比較を同条件と誤認しないため、元runに対するreplayは行っていない。

raw run rootに`evidence-index.md`はなかった。保存された`result.json`、attempt別`capture.json` / `evaluation.json`、runtime invocation、manifestを読み、次を確認した。

| Attempt                            | 既存capture / 評価                                   | captured-output完全性                                    | runtime capture                                                                                                      |
| ---------------------------------- | ---------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `d7760de6d12d4c78b45c359017b0eea6` | `captured` / `needs_review`、9 artifact              | 17 files、hash・size・file set一致、symlink/hardlinkなし | `spec-analysis`の`verify` 1件はrequest/result hashとbindingが整合。未登録runtime file 4件と他の必須capture不足が残る |
| `0ddf91f4b33046588a42eee224d40612` | `captured_needs_review` / `needs_review`、8 artifact | 23 files、hash・size・file set一致、symlink/hardlinkなし | `test-analysis`と`test-requirement-design`の`verify-001`重複を検出し、両invocationを拒否。必須capture不足も残る      |

候補runtime source manifestは読み取り検査で不整合なし。これはAgentのSkill使用やtool traceを証明しない。両attemptとも実効model/buildと元Agent tool traceは未検証である。

今回の読み取り検査metadataは`.agent-eval-runs/pr17-qts-verifier-stage3-20261103-01/evidence-index.md`と`validation.json`に保存した。raw Stage 2 evidenceは変更していない。

## 実装

- `qts_subagent_eval.py`は採点前にcapture attempt ID/fingerprint、元source file list、saved-copy file list、各`saved_sha256`・size、captured-output treeを照合する。capture後の追加・削除・変更、symlink/hardlink、redacted file、manifest不一致は`needs_review`とし、artifact validatorとruntime replayへ進まない。testでは元Agent出力を変えず、保存済み`captured-output`だけを変更して拒否されることを確認した。
- `common_runtime_checks.py`はDocker候補経路を維持しつつ、`verifier_image=None`でcandidate source、固定Evaluator source、captured resultを意味的に比較するDockerless経路を持つ。`verify`と`workflow-runtime`の両方が個別に一致しない限り全体をpassにしない。未実行・不一致・timeout・execution/environment errorはpassにならない。
- CIログの再確認で、Dockerless replayの上位結果がseccomp方式を`network: isolated_namespace`と誤記していたことを発見した。`verify`と`workflow-runtime`の記録を`blocked_by_seccomp`へ直し、実際の`network_enforcement`とpolicy SHA-256をcandidate・fixed別に保存する。これは証拠ラベルの修正で、隔離方式やPASS条件は変えていない。
- `isolated_verifier.py`は候補sourceをEvaluator processへimportしない。候補sourceの全fileをhashし、sealed memfdに固定してread-onlyでbubblewrapへ渡す。requestはstdin、環境変数はallowlist、出力は一時fileへ取得する。bubblewrapはroot-owned実行fileを要求し、user/PID/mount/IPC/UTS namespace、read-only root/source、上限付きscratch、resource limit、timeout cleanupを設定する。
- 最初の方式はbubblewrap自身にnetwork namespaceを作らせたが、CIでloopback初期化が`RTM_NEWADDR: Operation not permitted`となった。util-linux `unshare --user --map-root-user --net`による代替も`/proc/self/uid_map: Operation not permitted`となった。どちらも安全条件を弱めず停止した。
- 現方式はx86_64向けsealed cBPFをbubblewrap `--seccomp FD`へ渡す。socket/socket data syscall、socketpair、io_uring、x32 syscall ABIをEPERMで拒否し、未知のaudit architectureはkillする。FDは明示したsealed memfdのみを継承し、`close_fds=True`とする。network namespaceを作成したとは記録せず、network syscall denialとして扱う。Bubblewrap manualは`--seccomp FD`をcompiled cBPF programの適用として定義し、`--disable-userns`はsandbox内の新規user namespaceを防ぐ機能と説明する。[bubblewrap upstream manual](https://github.com/containers/bubblewrap/blob/main/bwrap.xml)
- synthetic probeはseccomp適用、IPv4/IPv6/Unix socket拒否、io_uring拒否、x32拒否、socket FD非継承、namespace分離、credential環境allowlist、Evaluator marker読取拒否、filesystem write拒否、resource limit、timeout後cleanup、source/request固定性を個別に検査する。1つでも未確認・失敗ならcandidate sourceは実行しない。
- run記録でVerifier実行と元Agent実行を分離する。独立Verifierが結果を再現しても、元Agentがそのコマンドを実行した証拠にはならない。`can_complete=false`は比較値として維持し、replay一致をworkflow完了へ読み替えない。

## 検証

### ローカル

- isolated verifier tests: 18件、15 PASS・3 SKIP（環境にbubblewrapがなく、実隔離を要するprobe・候補起動・timeout testをskip）。QTSの候補Verifier Pythonは起動していない。synthetic probe文字列のPython構文は独立に検査した。
- QTS subagent evaluator tests: 15 PASS。
- runtime trace/replay tests: 18 PASS。
- Agent evaluation tests: 245 PASS・5 SKIP。
- runtime tests: 388 PASS。
- repository Agent runner contract: 4 PASS。
- artifact graph deterministic contract: 43 PASS。通常`/tmp`では親sandboxが作成した`/tmp/.git`をSQLite safety checkが検出して3件をblockedにした。`TMPDIR=/dev/shm`へ移して同じsuiteを実行し、全件通過した。
- `compileall`: PASS。
- `dprint check`: PASS。
- `git diff --check`: PASS。
- `python scripts/format_tracked.py check`: Ruff executableがないため未実施（`could not start ruff: No such file or directory: 'ruff'`）。
- 既存Agent testsの中に意図的なfake-run出力（execution error / needs_review）があるが、test suite全体はPASSである。

### GitHub Actions

- `6e45bb1`のCode Quality必須probeは、bubblewrapのnetwork namespace loopback setupが`RTM_NEWADDR: Operation not permitted`となり失敗。
- `9eee339`のCode Quality必須probeは、util-linux `unshare`が`/proc/self/uid_map: Operation not permitted`となり失敗。candidate verifierは実行していない。他の4 workflowは成功。
- `970cf6b`のseccomp方式も、Code Quality runnerがuser namespace UID mapを作れず必須probeに失敗した。`bwrap` stderrは`setting up uid map: Permission denied`、candidate verifierは未実行。他の4 workflowは成功。Static formatting/lint stepsはprobeより後だったため、このrunでは実行されなかった。
- `0261224`では必須probeをCode Quality jobの最後へ移した。4 workflowは成功したが、Code Qualityは固定Ruff 0.16.8のformat checkで6つのPythonファイルを報告し、probeは未実行となった。指摘された6ファイルだけを同じ固定版Ruffで整形し、全tracked formatter/lint checkをローカルで再実行して成功した。
- `f23dfc4`のCIでは5 workflow中4件（Codex Harness、Agent Skills、Deterministic Output Evals、Semantic Output Evals）が成功した。Code QualityはRuff/dprint/patch whitespaceまで成功した後、必須隔離probeが`bwrap: setting up uid map: Permission denied`で失敗した。probeは`evidence_unverified`、candidateは`candidate_executed: false`であり、隔離依存の3 integration testはrequired-modeで失敗した。これはrunnerのnamespace権限不足であり、候補Verifierの失敗や品質結果ではない。候補sourceは実行されていない。
- この結果により、通常のGitHub-hosted `ubuntu-latest`では現在必要なnamespace境界を提供しないことが再確認された。Dockerless independent verifier replayは未達のまま維持し、candidate sourceの実行や安全条件の緩和は行わない。

## 未達・制約

- 現開発containerにはbubblewrapがなく、ローカルの実隔離probeは未実施。candidate sourceはfail-closedで起動していない。
- 現行GitHub-hosted runnerではbubblewrap UID mapがpermission deniedで、user namespace boundaryを利用できない。Dockerless independent verifierの安全な実行境界は`unverified`。別方式の管理者実行や通常Python processへfallbackしない。
- 保存済み第2段階runは現行Evaluator revisionと異なり、適切な固定source/requestの対応を再構成できていない。`verify` requestの独立replayは未実施。raw runに`workflow-runtime` invocationはなく、そのreplayも未実施。両経路のsemantic comparisonはunit test済みだが、実隔離下のcandidate/fixed/result比較は未達。
- QTS capture integrityの結果は両元attemptとも一致し、attemptの`needs_review`を維持した。runtime capture不足・重複invocation、Judge未実施、meaningful traceability、`can_complete=false`のQA品質判定は既存の未達として残る。
- QTS製品コード・仕様・Seed/Reset・製品test、元Stage 2 raw evidenceは変更していない。
