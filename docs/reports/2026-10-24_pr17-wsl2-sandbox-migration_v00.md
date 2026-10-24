# PR #17 WSL2二重bubblewrap移行・合成検証報告

作成日: 2026-10-24
対象branch: `feat/agent-eval-runner`
実装開始時HEAD: `be574cbaf457a49d2f51a08c1cdc7838e75abd5c`

## 結果

Agent、Judge、RepairをWSL2 Ubuntuの外側bubblewrapとCodex CLI Linux sandboxの内側bubblewrapで起動する実装を追加し、認証情報・モデルAPIを使わない合成隔離検証を通した。QTS deterministic verifierのDocker契約は維持した。

この結果はsandbox移行の合成受入であり、実Agent/Judge品質評価やPR #17全体の正式受入ではない。実認証、live `codex exec`、Judge fixture承認、改善候補の採用は行っていない。

## 実装内容

- 共通launcherと固定Codex runtime準備処理を追加し、Agent/Judge/Repairのargv、profile、mount、Codex Home、cleanupをmode別に固定した。production argvは`--no-daemon --strict-config`を含む。
- outer bubblewrapはattempt workspace rootを作業領域として公開し、実行前から存在するsource childをread-only bindする。`.qa-eval-output`、attempt-local `.git`/`.codex`、Repair対象Skillひとつだけを明示的なwrite対象にする。
- schema 2 profileとisolation evidenceを固定Codex CLI `0.163.0` / pinned package digestへ結び付けた。旧Docker evidenceで新profileを検証済みにできない。
- READMEと4つのAgent PlanをWSL2方式へ更新した。QTSのCodexを使わない固定Docker verifier記述は維持した。

## WSL2 runtime

| 項目                       | 実測                                                                                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OS / kernel                | Ubuntu on WSL2 / `6.18.54.1-microsoft-standard-WSL2`                                                                                                            |
| Python                     | `3.11.17`                                                                                                                                                       |
| Codex                      | `codex-cli 0.163.0`                                                                                                                                             |
| Codex package              | `0.163.0-linux-x64`, SHA-512 `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3` |
| Codex binary SHA-256       | `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`                                                                                              |
| bundled bubblewrap SHA-256 | `77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c`                                                                                              |
| Ruff                       | `0.16.8` (repository CI pin)                                                                                                                                    |

WSL2の隔離検証は一時clean checkout `60198301ae4989800a699c56e994eb2814870ac4`上で実施した。このrevisionは検証用snapshotでPR branch commitではないため、対象branchにcommitした後はlive run用profile evidenceを新しいrevisionに対して作り直す。

## Formal synthetic isolation evidence

`isolation_probe.py`を固定profileと固定`["codex"]` commandで実行し、evidence全体が`verified`になった。保存先は一時WSL checkout内の以下のrun directoryで、利用者側の既存`.agent-eval-runs`は変更していない。

`~/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/checkout-final/.agent-eval-runs/pr17-wsl2-synthetic-probe-20261024-02/isolation.json`

15個のrequired checksはすべて`true`。Agent、Judge、Repairの各mode evidenceも`verified`だった。観測した内容:

- Evaluator checkout、Evaluator sentinel、host home、他attempt、Windows interop領域、Docker socketをmountせず、各 sentinelの読取を拒否。
- AgentとRepairで既存source entriesへのwriteを拒否し、attempt workspace root内の新規作業領域と専用outputへのwriteを許可。Repairでは選択した`synthetic-skill`だけを追加のsource write rootにする。
- 親processの合成FD markerがinner sandboxへ継承されず、symlink経由の外部sentinel読取を拒否。fresh procfsとtimeout後のCodex Home / scratch cleanupを確認。
- outer/innerでuser、PID、mount、network、IPC namespaceが異なる。Codex CLI 0.163.0のinner sandboxはouter UTS namespaceを共有した。
- inner TCP、localhost、AF_UNIX接続を拒否し、DNS lookupを失敗させ、WSL interop経由のWindows commandを拒否。outer Codex parent側のnetwork namespaceはhostと同じで、モデルAPIを呼び出せる構成だが、この検証では一切呼び出していない。

Repair write拒否はCodex設定の追加writable rootが適用されないprofile経路が原因だった。CLIのstandalone `sandbox`は従来互換のためsandbox mode overrideがなければread-onlyへdefaultする。合成probeは固定`workspace-write` modeを明示してproduction `codex exec --sandbox workspace-write`の設定経路を確認した。[Codex CLI 0.163.0の実装](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/debug_sandbox.rs#L660-L664)

一時`CODEX_HOME`へ実認証情報を入れず、inner shellから実認証が見えないことも検証していない。evidenceは`authentication_shell_visible_risk=true`として残し、認証境界を合成markerだけで受入済みにしていない。

## Repository validation

すべて個別に実行・判定した。

| Command / suite                                                                                   | 結果                                     |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| WSL2 `unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -q`（integration有効） | PASS: 106 tests、1 skipped               |
| WSL2 `unittest discover -s tests/skills/evals/agent -p 'test_*.py' -q`                            | PASS: 4 tests                            |
| WSL2 `unittest discover -s scripts/skills/evals/semantic/tests -p 'test_*.py' -q`                 | PASS: 27 tests                           |
| WSL2 `unittest discover -s tests/skills/evals/deterministic -p 'test_*.py' -q`                    | PASS: 293 tests                          |
| WSL2 explicit formal Agent/Judge/Repair launcher integration                                      | PASS: 1 test                             |
| WSL2 `python -m compileall -q scripts/skills/evals/agent`                                         | PASS                                     |
| WSL2 `python scripts/format_tracked.py check`                                                     | PASS with Ruff 0.16.8                    |
| WSL2 `git diff --check`                                                                           | PASS                                     |
| Windows workspace cleanup + WSL2 launcher unit tests                                              | PASS: 23 tests、3 skipped                |
| Windows `git diff --check`                                                                        | PASS（GitはREADMEのCRLF/LFについて警告） |

最初のformatter実行は一時venvにRuffがなく起動できなかった。CI指定の`ruff==0.16.8`をその一時venvへ導入後、checkを再実行してPASSを得た。

## 最終commit・push・CI

実装と文書整形の最終検証対象HEADは`39a08482bf8bbd179b0188c540a00a31943e677b`。以下のcommitを`feat/agent-eval-runner`へ通常pushした。

- `40a3462bd593e38027117570ed900e6e9f504c66`
- `1250cac9325fc39a1e8409948fbeebf3f9075557`
- `ccc63e516d23086bd3110ea4eaca90a16eb442df`
- `2c3b2fc681ac2f4db426db5615b57e3ffd177025`
- `fb5945d1ddda2020b3605799c303f1cd2a2d2c56`
- `7f88133a9d5c602c4db91b21957eab85e8cb648f`
- `39a08482bf8bbd179b0188c540a00a31943e677b`
- `9dc7939ad9f4962a5b126b56ff57a5f75a1c63ac`（最終レポート更新）

同HEADに対する指定CIは5件すべてSUCCESS。

- [Validate Agent Skills (run 1409)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40079618996)
- [Validate Deterministic Output Evals (run 1408)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40079618991)
- [Validate Semantic Output Evals (run 1373)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40079618983)
- [Code Quality (run 103)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40079619000)
- [Codex Harness (run 103)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40079618986)

最終レポート更新commit `9dc7939ad9f4962a5b126b56ff57a5f75a1c63ac`に対する指定CIも5件すべてSUCCESS:

- [Validate Agent Skills (run 1410)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40080039657)
- [Validate Deterministic Output Evals (run 1409)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40080039420)
- [Validate Semantic Output Evals (run 1374)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40080039374)
- [Code Quality (run 104)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40080039394)
- [Codex Harness (run 104)](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40080039373)

初回の`git fetch origin`はWindows checkoutの`.git/FETCH_HEAD`権限で失敗したが、後続の通常pushはGitHubに受理され、上記CIはpush済みHEADに対して実行された。PR #17はopen、base `main`、head branch `feat/agent-eval-runner`のままであり、merge・close・base変更はしていない。

## 受入判定

- WSL2二重bubblewrap方式への実装・4つのAgent evaluation Plan・README更新: **PASS**。
- Agent/Judge/Repair起動経路、QTS Agent接続、固定Docker deterministic verifier契約の維持: **PASS**。
- 単体・repository contract・semantic・deterministic・Windows launcher関連テスト、compileall、formatter、diff check: **PASS**。上記の件数と個別結果はRepository validationを参照。
- 合成環境の隔離検証: **PASS**。15 required checks、Agent/Judge/Repair evidenceがすべてverified。
- 実Codex CLI 0.163.0のsandbox smoke: **PASS**。合成データで起動し、認証・モデルAPIは使用していない。
- 実Agent共通品質評価、QTS live Agent評価、独立Judge評価、Skill改善実証、改善後の独立回帰: **未実施**。
- PR #17全体の実Agent正式受入: **未完了**。実認証/APIを使う評価の別承認とJudge fixture承認が残っている。

## 残る判断・実行条件

- Synthetic probeのevidenceは独立clean checkout snapshot `60198301ae4989800a699c56e994eb2814870ac4`に固定されている。live runを行う場合は、対象の固定Evaluator revisionに対してprofileとevidenceを新規生成し、source revision bindingを再確認する。
- Probeは`model_api_used=false`。実認証fileのinner shell可視性は検証しておらず、`authentication_shell_visible_risk=true`を残している。実認証・モデルAPI通信を伴う評価は未実施。
- Judge fixture候補11件は承認済み0件。2件は決定論的レビュー待ち、9件は人間レビュー待ち。
- 実Agent共通評価、QTSの独立attempt、Judgeの承認済みfixture評価、改善候補の修正・再評価・採用は行っていない。Judge承認と実認証/API利用について必要な判断を得てから実施する。

## 結論

承認されたWSL2二重bubblewrapへの実装移行と合成環境の隔離検証は完了した。指定suiteとpush済み実装HEADの5 CIもすべてPASSした。認証・人間承認を要する実Agent/Judge品質評価は未実施であり、PR #17全体の正式受入とは区別する。
