# PR #17 WSL2 sandbox調査結果 v00

実施日: 2026-10-24（JST）
対象: `feat/agent-eval-runner` / `34715bfefbd37c2a8a24dbea946e1d5fe40bceff`
PR: [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)

## 判定概要

- Codex CLI `0.163.0` の `codex sandbox --permission-profile` は、既存WSL2 Ubuntuで認証なしに実行できた。`:read-only` と `:workspace` の読み書き境界、DNS/IP接続、Unix socketを合成sentinelで確認した。
- WSL2直接実行ではworkspace外とWindows filesystem上の合成ファイルを読めた。書込み拒否は確認したが、Evaluator-only情報の読取り隔離は成立していない。この方式を正式受入環境にはしない。
- 固定QTS revisionでJudge fixture v2の11件を合成成果物から構造検査した。全参照先は存在し、承認状態は全件pendingのまま。実Judgeは起動していない。
- QTS Agentのtimeout後cleanup失敗で実行詳細がattemptから欠落する不具合を修正し、Linux fake Agent回帰testで再現・確認した。
- Linux回帰suite、Ruff、compileallは成功した。Docker内Codex shell、4つの共通Agent評価、QTS実Agent、live Judge、Skill改善は未実施であり、PR正式受入は未完了。

## 1. 検証目的・初期状態

既存Plan、PR本文、README、EVALS、既存調査レポートを参照した。開始時のbranchとremote-tracking refはどちらも`feat/agent-eval-runner`の`34715bfefbd37c2a8a24dbea946e1d5fe40bceff`だった。PR #17はopenで、開始時点の5 CIはすべてsuccessだった。

開始時の未追跡Docker報告`docs/reports/2026-10-23_local-docker-evaluation_v00.md`と`_v01.md`、既存`.agent-eval-runs/`は保持した。新しい実験ログは`.agent-eval-runs/pr17-wsl-20261024/`へ保存した。Linux検証用checkoutは固定SHAから作り、Windows側working treeを使ってテストしなかった。

## 2. 使用環境・CLI version

| 項目                  | 確認値                                                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| WSL                   | Ubuntu 24.04.4、WSL2、kernel `6.18.54.1-microsoft-standard-WSL2`                                                        |
| WSL user              | uid 1000、通常ユーザー。sudo/adminは使用していない                                                                      |
| Python                | 3.11.17                                                                                                                 |
| PyYAML                | 6.0.3                                                                                                                   |
| Codex CLI             | `codex-cli 0.163.0`                                                                                                     |
| QTS checkout          | `/home/sella/src/qa-training-store-pr17-fixed-84ce165-20261023`、HEAD `84ce165493649550832731a60cf436f8ae29c56b`、clean |
| QA evaluator checkout | `/home/sella/src/qa-workflow-skills-pr17-linux-34715bf-20261024`、開始時HEAD `34715bfefbd37c2a8a24dbea946e1d5fe40bceff` |

Codex npm公開packageのversionとsha512 integrityを照合してLinux x64実体を取得した。system `bwrap`がPATH上にないこと、Codex package内にbundled `codex-resources/bwrap`があることは`.agent-eval-runs/pr17-wsl-20261024/codex-package-install.json`に記録した。CLI version、help、実行結果は同directoryの`codex-version.*`、`codex-sandbox-help.*`、`codex-readonly-smoke.*`にある。

実ユーザーの`~/.codex`、auth file、GitHub credential、API keyは使っていない。実Agent/Judge model呼出しもない。

## 3. `codex sandbox --permission-profile` の結果

実CLIの`codex sandbox --help`で`--permission-profile`、`:read-only`、`:workspace`を確認した。`--sandbox-state-json`の内部形式は作らず、公式のprofile optionを使った。

一時HOME、CODEX_HOME、workspaceから次を実行した。

```bash
codex sandbox --permission-profile :read-only -- /bin/echo sandbox-ok
```

終了コード0、stdoutは`sandbox-ok`（末尾改行あり）、stderrは空。コマンドはmodel/API認証なしで完了した。
CLI sourceの`rust-v0.163.0`では`codex sandbox`がLinux sandbox helperへ渡り、Linux helperは既定でbubblewrapとseccompを使う。Linux sandbox READMEは、PATH上のsystem bwrapがなければCodex bundled resourceを使い、user/PID/network namespaceと新しい`/proc`を構成する流れを説明している。今回のPATHにsystem bwrapはなく、bundled resourceは存在したため、ソースとresource解決条件は一致する。

- [Codex CLI debug_sandbox.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/debug_sandbox.rs)
- [Codex Linux sandbox implementation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/sandboxing/src/landlock.rs)
- [Codex Linux sandbox README](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/README.md)

プロセスtree観測ではbwrap子processを直接捕捉できなかった。そのため「Codex commandが実行できた」ことと「tagged source上でhelperがbwrapを選ぶ」ことは確認済みだが、この観測だけをbwrap syscallの直接traceとは扱わない。

## 4. bundled bwrap・namespace・procfs・network

bundled bwrapをCodex CLI経由とは別に1回起動した。user/PID/network namespace、root read-only bind、新規`/proc`、`/tmp` tmpfsを要求した。sandbox内で`/proc/1/comm`が`bwrap`、`/proc/self`が`5`、`/tmp`書込みが成功し、root filesystem書込みは`Read-only file system`で拒否された。

この診断shellは拒否を`set -e`で処理できず終了コード2となり、TEST-NET確認行まで実行しなかった。bwrap起動、PID/procfs、tmpfs、read-onlyの事実とshell harnessの早期終了を分けて記録した。同じ直接bwrap条件を再試行していない。詳細は`bwrap-direct-smoke.json`。

Codex CLIの`:read-only` / `:workspace`内でのnetwork probeは別に実施した。

| Probe                | 結果                                                |
| -------------------- | --------------------------------------------------- |
| `getaddrinfo`        | `gaierror`, errno `-3`。DNS解決不可                 |
| `203.0.113.1:443`    | `connect_ex` errno `1` (`EPERM`)                    |
| 合成AF_UNIX listener | connectは`EPERM`、server側acceptなし                |
| Windows interop      | sandbox内からのWSL interop socket接続はできなかった |

これらは指定した宛先・経路の結果であり、全通信経路が遮断された証明ではない。外部へ秘密情報は送っていない。`.agent-eval-runs/pr17-wsl-20261024/permission-profile-boundary-probes-v2.json`に記録した。

## 5. workspace内外の読書き境界

合成ファイルを使い、`:workspace` probeのworkspace外sentinelは`/var/tmp`に置いた。`/tmp`に置いた最初の試験では`:workspace`がprofile上許可するtmp領域だったため、その結果をworkspace外write拒否の根拠にしなかった。修正版v2の結果を正式記録に使っている。

| Profile      | workspace read/write | `/var/tmp` sentinel         | Windows dummy sentinel      | symlink write |
| ------------ | -------------------- | --------------------------- | --------------------------- | ------------- |
| `:read-only` | read可、write拒否    | read可、write拒否。内容不変 | read可、write拒否。内容不変 | 拒否          |
| `:workspace` | read可、write可      | read可、write拒否。内容不変 | read可、write拒否。内容不変 | 拒否          |

`/var/tmp`とWindows側dummyが読めたため、これらのpermission profileはfilesystem write範囲を制限するが、Evaluator-onlyデータをhost上の別pathから読めなくするものではない。`:workspace`のworkspace write sentinelだけが`inside-sentinel-mutated-v2`へ変わった。

## 6. WSL2からWindowsへのアクセス

`/mnt/c/Users/sella/Documents/qa-workflow-skills/.agent-eval-runs/pr17-wsl-20261024/windows-sentinel.txt`にこの検証専用のdummy内容`wsl-windows-dummy-v1`を作った。両Codex profile内から読み取れ、writeは拒否され、内容は不変だった。実ユーザーファイルやcredentialの内容は読んでいない。

`/mnt/c/Windows/System32/cmd.exe`の存在を確認してsandbox経由起動を試した。実行はWSL interopの`UtilGetPpid`が`/proc/1/stat`の`1 (codex)`をparseできず終了code 1となった。exe pathの存在と実行成功は区別する。host側WSL interop socketは存在したが、sandbox内ではそのsocket pathが見えなかった。詳細は`wsl-windows-executable-probe.json`。

## 7. Linux環境でのテスト

Python 3.11.17とPyYAML 6.0.3を通常ユーザーのtemp venvに用意した。開始時の固定revisionで13個の検証commandを個別実行し、全てexit 0だった。

| Suite                                           |                  件数・結果 |
| ----------------------------------------------- | --------------------------: |
| Agent unit                                      |                     92 PASS |
| Agent repository contract                       |                      4 PASS |
| deterministic harness                           |                     13 PASS |
| deterministic repository                        |                    293 PASS |
| semantic validator                              | 22 skills / 163 cases、PASS |
| semantic harness                                |                     27 PASS |
| semantic repository                             |                     13 PASS |
| runtime contract                                |                    371 PASS |
| Codex harness                                   |                     55 PASS |
| agent/deterministic/semantic/runtime compileall |         4 commandすべてPASS |

以前Windows上で6件errorになったAgent suiteをLinuxで確認した。既存記録では、Linux host条件を要求するlauncher test 3件、fake Dockerの`WinError 193` 1件、Windows Pythonに`os.getuid/getgid`がないことによる2件に分類されていた。Linux Agent suiteでは92件すべてが実行され、error/skipなしでPASSした。

この後にQTS cleanup記録の回帰testを追加し、修正前testは`KeyError: 'agent_execution'`で失敗した。修正後は個別回帰testとAgent suite 92件、Agent repository contract 4件、compileallがPASSした。Ruff `0.16.8`のcheck/format checkは変更した2 Python fileでPASS、`git diff --check`もPASS。修正前後のログは`.agent-eval-runs/pr17-wsl-20261024/cleanup-*.log`、`agent-*-after-fix*.log`にある。

## 8. Judge fixture v2

QTS固定checkoutのclean revision `84ce165493649550832731a60cf436f8ae29c56b`を参照し、unit testの合成baseline生成器から11件を作ってartifact validatorを実行した。全fixtureの参照文書が固定revisionに存在する。fixture catalogue fingerprintは`sha256:b306974e68ffc710c11a0e1a4ec62957a202f6c78c7e137ae6005b29f3069e8d`、splitはtune 5件 / independent 6件。

`normal-workflow`、`normal-artifacts`、`major-violation-003`〜`007`、`009`、`010`は構造validator `pass`。`major-violation-001`はrequired test-case-design artifact/routingを外したため`needs_review`、`major-violation-002`はqa-workflow incompleteのため`needs_review`となった。これらは決定論的構造結果であり、Judgeの意味判定結果ではない。

Judgeを起動せず、人間承認も作成していない。`001`/`002`は`pending_deterministic_review`、それ以外の9件は`pending_human_review`を維持した。詳細は`judge-fixture-inventory.json`および`judge-fixture-structural-details.json`。

## 9. 決定論的に確認できた事項

- fixtureのdataset revision、split、case ID、mutation、expected outcome、approval state、参照先を読み取れる。
- `_prepare_fixture()`は各定義を合成baselineへ適用でき、artifact index validatorとmanifest生成が動作する。
- 001/002はvalidatorが実際にrouting/artifact issueを検出する。003〜007、009、010はmutation後もartifact contract上はpassし、内容の意味評価はJudgeに残る。
- QTS-SEM-008は通常の`normal-artifacts` criteriaに含まれるが、専用major-violation fixtureはない。approvalは0件。
- 実Agent生成物からのfixture再生成、各Judgeの期待rating、Judge間独立性、bindingを使った承認照合は未検証。

## 10. QTS-SEM-008 fixture追加に必要な条件

固定rubricのQTS-SEM-008（`Executable test design`）では、複数の重要caseについて必須input、action、observable pass/fail outcomeが特定できず実行不能ならrating 1となる。rubricの`critical`はfalse。

追加する場合は、実Agentの正常baseline成果物が揃った後に、実在する`test-condition-and-ci`または`test-case` artifactへ限定したmutationを適用する。複数の重要caseそれぞれで、どの必須precondition/input、操作、期待結果が欠け、実行不能になるかをartifact内の証拠で説明できる必要がある。構造validatorだけでは意味を判定できないため、normal fixtureとの分離、criterion `QTS-SEM-008`、期待`rating_1`、固定QTS reference、baseline artifact fingerprintをbindingへ含め、`pending_human_review`を維持する。通常artifactに内容のない合成テキストを足しただけのfixtureは採用根拠にしない。

人間確認後のapproval bindingが一致し、独立Judgeを規定repeatで実行して期待結果が揃うまでは`judge_unverified`のままにする。

## 11. 評価runnerのコード確認と修正

指定されたrunnerと関連testを確認した。次表の状態はコードと既存testから確認したもので、live Agent受入を意味しない。

| 確認項目                     | 現行実装で確認した扱い                                                                                                              |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Agent起動前の隔離証拠        | `run.py` / QTS runnerがprofile evidence、fingerprint、clean evaluator revisionを確認してからAgentを起動する                         |
| revision/profile一致         | evaluator・command・profile・targetのfingerprint/固定revisionを検証。比較条件が違うrunはcomparableにならない                        |
| shell実行失敗                | timeout/nonzero/cleanup errorはexecution errorとして扱い、Skill gradeのFAILに読み替えない                                           |
| Skill未使用                  | traceにSkill readがなければ`unverified`。improveはbaseline/candidateの各attemptで使用観測を要求する                                 |
| Judge未承認                  | fixture承認・bindingが不足/不一致なら`judge_unverified`。今回は全fixture pending                                                    |
| Agent symlink                | evaluator-owned書込みはatomic writeを使い、untrusted symlink outputはevidence unverified/needs reviewへ送る。Linux symlink testあり |
| 原成果物と原因確認           | repair gateは原artifactとSkill sourceのhash/quote、単一Skill attribution、未解消alternative causeなしを要求する                     |
| 独立回帰                     | `improvement_demonstrated`には独立caseと関連contract testの完全成功を要求する                                                       |
| deterministic/semantic/mixed | deterministic-onlyは固定grader経路、semantic/mixedはJudge検証経路へ分かれ、mixedの未検証をdeterministicで代替しない                 |
| 秘密情報保存                 | stderr/final outputをsanitizeし、raw Codex JSONLは保存せずtrace summaryのみ記録。redactionで内容が変わる場合はneeds review          |
| timeout/cleanup              | 共通executorとAgent runnerはtimeout/cleanup状態を保存する。QTS Agent cleanup失敗の詳細欠落を今回修正した                            |
| 比較可能性                   | evaluator revision、suite/dataset/target、Agent/Judge command、image、isolation、profile、repeatなどを比較する                      |

### 今回修正した不具合

QTS runnerでは`run_command()`が返した直後にcleanup失敗を検知すると、`agent-execution.json`作成前に例外化し、attemptには一般errorしか残らなかった。fake Agentをtimeoutかつcleanup failedにしたtestで、`agent_execution`が欠けることを修正前に再現した。

修正後は実行結果の安全なmetadata（exit code、timed out、duration、stderr status、cleanup status）を先に`agent-execution.json`へ保存し、error attemptにもその内容と相対pathを記録する。raw stdout/stderrは追加保存しない。修正対象は`qa_training_store.py`と`test_qa_training_store.py`。

前回レビュー記録にあるN02/N05/N01/F01–F03/N06に対応するsymlink、Judge normalizer/approval binding、criterion coverage、repair gate、独立regressionの検査も現HEADのtest suiteで確認した。今回新たに再現した不具合は上記QTS cleanup記録の1件。

## 12. isolation probeが証明する範囲

`isolation_probe.py`の`verified`は、固定profile/evaluator revision/command fingerprintに結び付いたDocker mount構成、同じcontainer userからのEvaluator sentinel read-denial、workspace write-denial、Agent output write許可、追加tool/MCPやmount設定の確認を表す。

このstatusだけではCodex内部sandboxの起動、Codex shellからのcredential read-denial、public egress遮断、JudgeとAgentのlive実効分離、Agentの評価品質は証明しない。実装もpublic egressを`not_verified`としている。Dockerのmount probe結果をこれらのPASSに拡張して解釈しない。

## 13. Docker内sandbox失敗との比較

`2026-10-23_local-docker-evaluation_v01.md`と既存PR履歴では、Docker通常profileでCodex/bwrapのnamespace creationが拒否され、限定診断profileではnamespace段階の後にprocfs mountが拒否された記録がある。Docker内にbuiltin seccomp/cgroup namespace制限があることと整合するが、namespace失敗の個別syscallだけをseccomp原因と断定しない。診断profileの変更は過去の記録であり、今回Docker設定を変更・再実行していない。

Codex CLI 0.163.0 sourceのLinux helperはbwrapへnamespace、procfs、filesystem、seccompの設定を渡す。今回のWSL host上ではCodex sandbox commandが成功し、bundled bwrap direct runでもnamespace/procfs/tmpfs/read-only構成まで進んだ。Docker内の失敗位置と同じ条件ではないため、WSL成功をDocker正式条件の代替にしない。fallbackでDocker制限を回避する動作も確認されていない。

## 14. 実行方式の比較と正式受入に不足する証拠

| 方式              | 今回確認した利点・制約                                                                                                         | 正式受入       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| 現行Docker        | Planに適合しmount境界を検査できる。既存記録ではCodex内bwrap namespace/procfsが起動できず、credential/egressのshell実証が未完了 | 未達           |
| WSL2 host-native  | Codex permission-profile sandbox commandは動作。Linux外部sentinelとWindows dummyをreadでき、同じWSL user/Windows mountが残る   | 不採用         |
| 専用Linux VM/host | OS user/filesystem分離の可能性はあるが、作成・費用・管理者権限・credential供給・Docker内seccomp/procfsは未検証                 | 作成していない |

正式受入には、Plan適合Docker内でCodex shellが成功し、同一条件でworkspace外read/write、credential access、network制御、cleanupがnegative testを通る証拠が必要。さらに共通4 caseのAgent評価、固定QTSの独立2 attempt、実成果物とtarget不変性、承認済みJudge fixtureの独立評価が必要。QTS-SEM-008 fixtureと人間承認も未完了である。

## 15. 正式受入再開の準備と次の判断

以下は現READMEと実CLI helpに沿った手順であり、この調査では実行していない。model、image digest、credential、approval値は取得・推測していない。

### Imageとprofile

READMEのDockerfileからCodex CLI imageを作り、build後のimmutable IDを確認する。

```bash
docker build --tag codex-agent:0.163.0 \
  --file scripts/skills/evals/agent/tools/codex-agent.Dockerfile .
docker image inspect --format '{{.Id}}' codex-agent:0.163.0
```

得られたimage IDをAgent/Judge `command_argv`へ入れ、固定profile、model ID、verifier image digest、timeout、approval/network/tool/MCP/Skill設定を確定する。`agent-command.json`はREADME例のoutput-only writable bind、read-only workspace、`--cap-drop=ALL`、`--security-opt=no-new-privileges`を使う。profile/commandを確定した後、同じoutput rootへprobe evidenceを作る。profileやcommandを変更したらevidenceを取り直す。

### 共通4 case

各`--eval-id`は固定Evaluator datasetから入力を選ぶ。

| Suite         | Skill                   | Eval ID       | 固定input                                                           |
| ------------- | ----------------------- | ------------- | ------------------------------------------------------------------- |
| deterministic | `test-case-design`      | `TC-OUT-001`  | `skills/test-case-design/evals/output/cases/case-001/input.md`      |
| deterministic | `test-condition-design` | `TCN-OUT-001` | `skills/test-condition-design/evals/output/cases/case-001/input.md` |
| semantic      | `test-case-design`      | `TC-SEM-001`  | `skills/test-case-design/evals/semantic/cases/case-001/input.md`    |
| semantic      | `qa-workflow`           | `WF-SEM-003`  | `skills/qa-workflow/evals/semantic/cases/case-003/input.md`         |

確定したAgent argvをBash array `AGENT_COMMAND`、profile内のmodel IDを`AGENT_MODEL`、現行branch revisionを`SKILL_SHA`へ設定した後、以下を4回別々の引数で実行する。`AGENT_COMMAND`は最後のoption。

```bash
run_one() {
  suite="$1"; skill="$2"; eval_id="$3"
  python -m scripts.skills.evals.agent.run \
    --suite "$suite" --skill "$skill" --eval-id "$eval_id" \
    --skill-revision "$SKILL_SHA" \
    --execution-profile .agent-eval-runs/config/profile.json \
    --output-root ".agent-eval-runs/common/$eval_id" \
    --agent-name codex --agent-model "$AGENT_MODEL" \
    --agent-command "${AGENT_COMMAND[@]}"
}
run_one deterministic test-case-design TC-OUT-001
run_one deterministic test-condition-design TCN-OUT-001
run_one semantic test-case-design TC-SEM-001
run_one semantic qa-workflow WF-SEM-003
```

### 固定QTS、Judge、改善

QTS targetは既存clean checkout `/home/sella/src/qa-training-store-pr17-fixed-84ce165-20261023`、SHA `84ce165493649550832731a60cf436f8ae29c56b`を指定する。image inspectで確認した固定verifier digestを`VERIFIER_IMAGE`へ入れ、QTS runnerを`--repeat 2`で起動する。

```bash
python -m scripts.skills.evals.agent.qa_training_store \
  --target-root /home/sella/src/qa-training-store-pr17-fixed-84ce165-20261023 \
  --skill-revision "$SKILL_SHA" \
  --execution-profile .agent-eval-runs/config/profile.json \
  --verifier-image "$VERIFIER_IMAGE" \
  --output-root .agent-eval-runs/qts-baseline --repeat 2 \
  --agent-command "${AGENT_COMMAND[@]}"
```

baselineの実成果物が揃った後、READMEの`judge_validation`を`--baseline-result .../result.json`、同target、同profile、`--max-cases 11 --max-seconds 1800 --repeat 2`で実行する。各`cases[].approval_binding`と人間が確認したapproval fileの`binding`が一致する必要がある。人間承認を作成・代行していないため、現時点で承認ファイルを追加しない。fixtureがunapprovedなら`judge_unverified`を維持する。

Judge結果と既存artifact/runtime確認が揃っても、改善前には原成果物、Skill使用trace、原因帰属、関連fixture承認を再確認する。READMEの`improve --analyze-only`は分析Agentを起動するため、この調査では実行していない。修正可能条件が満たされた後に限り、通常runで候補を隔離し、候補の同条件反復と独立regression/contract testが完了するまで採用しない。

次の判断は、Plan所定のDocker条件でCodex shellを動かす環境と、credential/egressの検証方法を用意できるかである。WSL host-native結果を正式方式へ昇格させる判断は、この報告の範囲に含めない。

## 保存した証拠

全て非秘密のログである。

- Codex CLI install/version/help/smoke: `.agent-eval-runs/pr17-wsl-20261024/codex-*`
- permission boundary/network: `.agent-eval-runs/pr17-wsl-20261024/permission-profile-boundary-probes-v2.json`
- direct bundled bwrap: `.agent-eval-runs/pr17-wsl-20261024/bwrap-direct-smoke.json`
- Windows filesystem/interop: `.agent-eval-runs/pr17-wsl-20261024/windows-sentinel.txt`, `wsl-windows-executable-probe.json`
- Linux suite: `.agent-eval-runs/pr17-wsl-20261024/linux-test-summary.json` と各suite log/exit file
- Judge fixture audit: `.agent-eval-runs/pr17-wsl-20261024/judge-fixture-inventory.json`, `judge-fixture-structural-details.json`
- cleanup修正前後: `.agent-eval-runs/pr17-wsl-20261024/cleanup-before-fix.log`, `cleanup-after-fix.log`, `cleanup-regression-final.log`
- 既存Docker失敗: `docs/reports/2026-10-23_local-docker-evaluation_v01.md` と`.agent-eval-runs/local-docker-20261023/`
