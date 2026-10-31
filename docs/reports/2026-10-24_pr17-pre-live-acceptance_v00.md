# PR #17 WSL2 launcher安全化修正・実Agent評価前確認

実施日: 2026-10-24（JST）\
対象branch: `feat/agent-eval-runner`\
修正commit / 固定Evaluator SHA: `aba9dbbf6983a851c5163ba50a254562b100555a`

## 判定

安全化された最終応答が未変更の証拠として扱われる不具合を、合成Codex出力で再現できる状態にし、launcherとAgent/Judge/Repair側の判定を修正した。回帰テスト、WSL2二重sandboxの合成probe、無認証Codex sandbox smoke、指定repository test suiteはPASS。

実認証、モデルAPI、live `codex exec`、実Agent/Judge品質評価は実施していない。PR #17の正式受入は未完了。

## 不具合の原因と影響

旧launcherは最終応答をsanitizeしてから`response_sha256`を計算していたが、原文との違いを`final_message_redacted`へ記録しなかった。launcherのstatusも`completed`のままになり、すでに安全化された文字列しか受け取らない`capture_codex_jsonl_trace()`からは変更を検知できなかった。

その結果、Agentが未検証の出力を完了扱いする可能性があり、Judgeが変更済み応答を独立評価の根拠として採用したり、Repairが分析結果を成功扱いしたりする経路があった。またCodexの`--output-last-message`はraw応答をAgent/Repairのhost側outputへ一時保存するため、launcherが終了前に削除しない場合やtimeoutでlauncherがkillされた場合に原文が残る可能性があった。

## 修正内容

- sanitize前後の一致を判定し、差があれば`final_message_redacted=true`、`status=evidence_unverified`、`response_sha256=null`とする。外部へ返すのは安全化後の応答だけ。
- stderrも従来どおり安全化し、raw JSONLを保存せず、要約観測のみを記録する。
- Agent/Repairの一時`--output-last-message`ファイルを通常終了時に削除する。timeout cleanup helperにも予約名の一時ファイル削除を追加し、無関係なoutputは保持する。cleanup失敗は`execution_error`へfail closedする。
- `capture_codex_jsonl_trace()`はlauncherのredaction flagと未完了statusをtraceへ伝播する。共通Agent、QTS、Judge validationはredacted/evidence-unverifiedの応答を採点根拠にせず、Repairは分析成功・patch適用へ進めない。
- grader、rubric、評価基準、改善条件、QTS deterministic verifierのDocker契約は変更していない。Judge fixtureの承認データも変更していない。

## 回帰・repository検証

秘密ではない合成文字列を使い、fake Codex JSONL、launcher出力、observations sidecar、Agent/Judge/Repair呼出し元を通して確認した。redaction時のflag/status/hash、stdout/stderr、raw final-message一時ファイル削除、persisted filesへの合成文字列残存なしを検証した。

| 検証                                                                                       | 結果                              |
| ------------------------------------------------------------------------------------------ | --------------------------------- |
| WSL2 focused launcher unit tests                                                           | PASS: 11 tests、1 skipped         |
| WSL2 full Agent evaluation suite                                                           | PASS: 114 tests、2 skipped        |
| WSL2 Agent API contract suite                                                              | PASS: 4 tests                     |
| WSL2 semantic suite                                                                        | PASS: 27 tests                    |
| WSL2 deterministic suite                                                                   | PASS: 293 tests                   |
| WSL2 formal launcher integration（Agent/Judge/Repair、FD・network・path・timeout cleanup） | PASS: 11 tests、0 skipped         |
| WSL2 `compileall`                                                                          | PASS                              |
| WSL2 `format_tracked.py check`（Ruff 0.16.8）                                              | PASS: 239 files already formatted |
| WSL2 `git diff --check HEAD^ HEAD`                                                         | PASS                              |
| Windows focused launcher tests                                                             | PASS: 11 tests、1 skipped         |
| Windows executor cleanup tests                                                             | PASS: 4 tests、1 skipped          |
| Windows `git diff --check`                                                                 | PASS                              |

全WSL2 suiteとformatterは固定SHAのclean ext4 checkoutで実行した。focused integrationでは`QAEVAL_RUN_WSL2_INTEGRATION=1`、空の`CODEX_HOME`を使い、`OPENAI_API_KEY`と`CODEX_API_KEY`をunsetした。full Agent suite中に表示されたexecution error / needs-review行はnegative contract fixtureの結果であり、unittest全体はPASS。

## 固定SHAの合成隔離evidence

evidenceと合成profileは、次のignoredローカル成果物に保存した。

- `.agent-eval-runs/pr17-prelive-redaction-20261024/profile.json`
- `.agent-eval-runs/pr17-prelive-redaction-20261024/agent-command.json`
- `.agent-eval-runs/pr17-prelive-redaction-20261024/isolation.json`

`isolation.json`はschema 2、Evaluator revision `aba9dbbf6983a851c5163ba50a254562b100555a`、profile fingerprint `sha256:c5916a232a1e6386820bb47d79f3cff22e8a4d6f475f98dea937cc26613c46b4`に結び付いている。Agent/Judge commandは`["codex"]`で、両方のcommand fingerprintは`sha256:e25eaf648dc7039953915d93cac78cc23b21b780b60f562ff1aaa53086f25364`。modeごとのeffective outer argv fingerprintは次のとおり。

| mode   | status   | effective outer argv fingerprint                                          |
| ------ | -------- | ------------------------------------------------------------------------- |
| Agent  | verified | `sha256:18ebc5c25b5ffb4402a5a869e46ac03e2c513b351c423e4db27608b59ae418ad` |
| Judge  | verified | `sha256:fa7292b15abf7c866e3f4419005d39ccad08a9783c3e4922a3360764645e9a8e` |
| Repair | verified | `sha256:24019cf1c053c85f54caeb62c2456bc89d4ede87835c24cecbd3bc9a980c97b0` |

15個のrequired checksはすべて`true`だった: `mounts_reviewed`、`timeout_cleanup`、`inherited_fd_denied`、`inner_shell_network_blocked`、`source_write_denied`、`windows_filesystem_read_denied`、`evaluator_read_denied`、`other_attempt_home_read_denied`、`agent_judge_separated`、`extra_tools_disabled`、`fresh_procfs`、`nested_namespaces`、`host_home_read_denied`、`output_write_allowed`、`symlink_escape_denied`。各mode evidenceもAgent/Judge/Repairともverifiedで、inner smoke、FD非継承、source書込拒否、output書込許可、nested namespaces、TCP/localhost/AF_UNIX/DNS/WSL interop拒否を記録した。

timeout smokeは約2.1秒でtimeoutとなり、process cleanup、Codex Home、scratch、workspace `.git` mountpoint、一時final-messageファイルの削除がすべて成功した。実行runtimeはWSL2 kernel `6.18.54.1-microsoft-standard-WSL2`、Python `3.11.17`、Codex CLI `0.163.0-linux-x64`（package SHA-512 `bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3`、binary SHA-256 `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`）、同梱bubblewrap SHA-256 `77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c`。

probe結果は`model_api_used=false`、`authentication_shell_visible_risk=true`。認証情報を一切入れていない。Codex inner sandboxはouter UTS namespaceを共有する。15 required checksのverified結果はこの境界や実認証の安全性を受入済みにするものではない。

この保存profileは`synthetic-agent-model` / `synthetic-judge-model`を含み、`verification.status=unverified`のprobe専用profileであり、実評価に使えない。次のlive profileは実際に選ばれたmodel・reasoning effort・timeout等で別途作成し、そのprofileのfingerprintに対してevidenceを再生成する必要がある。runnerはprofileの`verification.status=verified`に加えて、同じoutput root内のfresh evidence、profile fingerprint、command fingerprint、Evaluator SHAが一致しなければ実行を拒否する。

## Commit・push・CI・PR

修正commit `aba9dbbf6983a851c5163ba50a254562b100555a`を`feat/agent-eval-runner`へ通常pushした。PR #17はopen、base `main`、head branch `feat/agent-eval-runner`のまま。

このEvaluator SHAに対する5 CIはすべてSUCCESS。

| Workflow                            | Run                                                                                                 |
| ----------------------------------- | --------------------------------------------------------------------------------------------------- |
| Validate Agent Skills               | [run 1412](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40085503632) |
| Validate Deterministic Output Evals | [run 1411](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40085503634) |
| Validate Semantic Output Evals      | [run 1376](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40085503575) |
| Code Quality                        | [run 106](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40085503590)  |
| Codex Harness                       | [run 106](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40085503615)  |

このreport-only commitの後に起動する最新HEAD CIとその状態はPR本文へ別途反映する。

## 次の正式評価に必要な値と承認

現時点で確定している値:

- 固定Evaluator / Skill source revision: `aba9dbbf6983a851c5163ba50a254562b100555a`。このclean revisionで評価runnerを実行する。
- Codex runtime cache: `/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final`。CLI/package/bubblewrapは上記digestに固定する。
- 共通4ケース: `TC-OUT-001`（deterministic / `test-case-design`）、`TCN-OUT-001`（deterministic / `test-condition-design`）、`TC-SEM-001`（semantic / `test-case-design`）、`WF-SEM-003`（semantic / `qa-workflow`）。各runを個別のoutput rootで実施する。
- QTS target revision: `qa-training-store@84ce165493649550832731a60cf436f8ae29c56b`、scenario `qa-training-store-checkout-payment-web-v1`。Runnerの`--repeat 2`で独立attemptを2件作成し、target checkoutはcleanなまま維持する。deterministic verifier imageは既存の固定digestを使う。
- Judge fixtureは11件中承認済み0件。9件が`pending_human_review`、2件が`pending_deterministic_review`。人間の承認bindingは代行していない。

未確定で、推測で補完していない値・判断:

- Agent/Judgeのmodel ID、reasoning effort、各timeout上限、実評価用schema 2 profileの場所とfingerprint。
- 別途選択・承認される認証方法。launcher sandbox smokeでは`authentication_shell_visible_risk=true`が残るため、実認証のshell可視性と利用承認を確認する。
- QTS deterministic verifierの既存固定Docker image digestとclean target checkoutの絶対path。
- Judge fixture 11件の人間レビュー。fixture承認完了まではQTS fixture Judgeの正式受入へ進めない。

以下は手順確認用templateで、`PROFILE`、`AGENT_MODEL`、認証、QTS path、verifier digest等を確定するまでは実行しない。`AGENT_COMMAND_JSON`はJSON `["codex"]` を保持するファイル。live profileは値を固定した後、`verification.status=verified`と相対`evidence_path`を設定し、各runのoutput rootへprobe evidenceを書き込んでからrunする。runごとにprofile・command・runtime・Evaluator SHAの一致を再確認する。

```bash
export QAEVAL_CODEX_RUNTIME_ROOT=/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final
PROFILE=/path/to/approved-schema2-profile.json
AGENT_COMMAND_JSON=/path/to/approved-agent-command.json
AGENT_MODEL='<must match profile.agent.model>'
SKILL_SHA=aba9dbbf6983a851c5163ba50a254562b100555a
```

共通4ケースは次の各組を個別に実行する。profileのmodel、reasoning、timeout、auth設定を決めた後にprofile evidenceを再生成する。

```bash
OUT=.agent-eval-runs/TC-OUT-001
python -m scripts.skills.evals.agent.isolation_probe --profile "$PROFILE" --agent-command-json "$AGENT_COMMAND_JSON" --output-root "$OUT"
python -m scripts.skills.evals.agent.run --suite deterministic --skill test-case-design --eval-id TC-OUT-001 --skill-revision "$SKILL_SHA" --execution-profile "$PROFILE" --output-root "$OUT" --repeat 1 --agent-name codex --agent-model "$AGENT_MODEL" --agent-command codex

OUT=.agent-eval-runs/TCN-OUT-001
python -m scripts.skills.evals.agent.isolation_probe --profile "$PROFILE" --agent-command-json "$AGENT_COMMAND_JSON" --output-root "$OUT"
python -m scripts.skills.evals.agent.run --suite deterministic --skill test-condition-design --eval-id TCN-OUT-001 --skill-revision "$SKILL_SHA" --execution-profile "$PROFILE" --output-root "$OUT" --repeat 1 --agent-name codex --agent-model "$AGENT_MODEL" --agent-command codex

OUT=.agent-eval-runs/TC-SEM-001
python -m scripts.skills.evals.agent.isolation_probe --profile "$PROFILE" --agent-command-json "$AGENT_COMMAND_JSON" --output-root "$OUT"
python -m scripts.skills.evals.agent.run --suite semantic --skill test-case-design --eval-id TC-SEM-001 --skill-revision "$SKILL_SHA" --execution-profile "$PROFILE" --output-root "$OUT" --repeat 1 --agent-name codex --agent-model "$AGENT_MODEL" --agent-command codex

OUT=.agent-eval-runs/WF-SEM-003
python -m scripts.skills.evals.agent.isolation_probe --profile "$PROFILE" --agent-command-json "$AGENT_COMMAND_JSON" --output-root "$OUT"
python -m scripts.skills.evals.agent.run --suite semantic --skill qa-workflow --eval-id WF-SEM-003 --skill-revision "$SKILL_SHA" --execution-profile "$PROFILE" --output-root "$OUT" --repeat 1 --agent-name codex --agent-model "$AGENT_MODEL" --agent-command codex
```

QTSを実行する場合は、target checkoutのHEADが指定revisionでcleanであることと、verifier imageのdigestを確認してから実行する。

```bash
QTS_TARGET_ROOT=/path/to/clean/qa-training-store-at-84ce165493649550832731a60cf436f8ae29c56b
VERIFIER_IMAGE_DIGEST='<existing fixed verifier image digest>'
OUT=.agent-eval-runs/qts-baseline
python -m scripts.skills.evals.agent.isolation_probe --profile "$PROFILE" --agent-command-json "$AGENT_COMMAND_JSON" --output-root "$OUT"
python -m scripts.skills.evals.agent.qa_training_store --target-root "$QTS_TARGET_ROOT" --skill-revision "$SKILL_SHA" --execution-profile "$PROFILE" --verifier-image "$VERIFIER_IMAGE_DIGEST" --output-root "$OUT" --repeat 2
```

実認証・モデルAPIを伴う評価、QTS run、Judge fixtureの承認は本作業では実行していない。
