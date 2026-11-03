# PR #17 第3段階：保存成果物完全性・Dockerless verifier

## 対象と結論

- 開始HEAD: `6a1e4e46937d220fece0234fb7eed5c67dc2e0b6`
- PR: #17、base `main`、開始時OPEN
- 対象QTS revision: `84ce165493649550832731a60cf436f8ae29c56b`
- 対象の旧開発run: `.agent-eval-runs/pr17-qts-subagent-stage2-20261103-03/`
- 今回の読み取り検査記録: `.agent-eval-runs/pr17-qts-verifier-stage3-20261103-01/`

保存済みStage 2のcopyは、今回追加したsource/copy/tree照合で両attemptとも完全性を確認できた。runtime captureとartifact/routingの問題は残っており、attemptの既存`needs_review`判定は維持する。現開発環境に`bwrap`がないため、Dockerless verifier replayは実行せず`evidence_unverified`とした。候補Verifier Pythonは実行していない。元Stage 2証拠は読み取りのみで、変更していない。

## Stage 2証拠との照合

Run ID `d3ab14c200964233b76acbb26ef7a676`は固定target revisionを記録している。run記録のEvaluator revisionは`296e64919a61617243b22f56b3bb3edd16693244`、Skill revisionも同SHAで、現在の開始HEADとは一致しない。従って保存済みruntime requestを現在のEvaluator sourceとの比較へ流用しなかった。期待値と判定基準のrevisionを合わせずに独立replayを行うことは、同条件比較にならないためである。

raw run rootに`evidence-index.md`は存在しなかった。実ファイルの`result.json`、attempt別`capture.json` / `evaluation.json`、runtime invocation、manifestを読み、次を確認した。

| Attempt                            | 既存capture / 評価                                   | captured-output完全性                                    | runtime capture                                                                                                                                   |
| ---------------------------------- | ---------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `d7760de6d12d4c78b45c359017b0eea6` | `captured` / `needs_review`、9 artifact              | 17 files、hash・size・file set一致、symlink/hardlinkなし | `spec-analysis`の`verify` 1件のrequest/result hashとbindingは整合。Question Analysis等の未登録runtime file 4件と他の必須runtime capture不足が残る |
| `0ddf91f4b33046588a42eee224d40612` | `captured_needs_review` / `needs_review`、8 artifact | 23 files、hash・size・file set一致、symlink/hardlinkなし | `test-analysis`と`test-requirement-design`の`verify-001`が重複し、2 invocationを拒否。必須runtime capture不足も残る                               |

両attemptのcandidate runtime source manifestは読み取り検査で不整合がなかった。これはSkill使用やAgentのtool traceを証明しない。両方とも実効model/buildと元Agent tool traceは未検証のまま。

今回のStage 3 metadataは`.agent-eval-runs/pr17-qts-verifier-stage3-20261103-01/evidence-index.md`と`validation.json`に新規保存した。元runには書き込んでいない。

## 実装

- `qts_subagent_eval.py`はgraderより前に、capture attempt ID/fingerprint、元source file list、saved-copy file list、各`saved_sha256`・size、現在のcaptured-output treeを照合する。capture後の追加・削除・変更、symlink/hardlink、redacted file、manifest不一致は`needs_review`とし、artifact validatorとruntime replayを呼ばない。
- `common_runtime_checks.py`は既存のDocker候補経路を維持し、`verifier_image=None`のDockerless replayを追加した。`verify`と`workflow-runtime`はcandidate、固定source、captured resultを各々比較する。どちらか未実行・不一致・timeout・execution/environment errorなら全体をpassにしない。
- `isolated_verifier.py`はroot-owned system bubblewrapを使う実行境界をprobeし、成功後だけVerifierを別processで起動する。候補sourceは各fileをhashしたsealed memfd snapshotでread-onlyに渡し、requestはstdinで固定する。sandboxではuser/PID/network/IPC/UTS namespace、read-only root/source、networkなし、bounded tmpfs、CPU/address-space/file/process/open-file/core limits、wall timeoutとtimeout cleanupを要求する。
- 起動したbubblewrap processとVerifier本体の実行証拠を分けた。bubblewrapが非ゼロ終了した場合は、namespace起動失敗とVerifierの非ゼロ終了を区別できないため、`sandbox_process_started=true`でも`verifier_executed=null`とし、実行済みと断定しない。
- candidate/fixed executionのsource fingerprint、request/result/stdout/stderr hash、exit code、時間、bounded・secret-sanitized診断、probe結果を保存する。独立replayは元Agentの実行証拠に昇格せず、`payload.can_complete=false`も変えない。
- `.github/workflows/code-quality.yml`はcheckout credential persistenceを無効化し、bubblewrapを導入して必須boundary testを実行する。`PR17_REQUIRE_VERIFIER_ISOLATION=1`によりprobeが利用できない場合はCIを失敗させ、test skipで合格扱いしない。

Bubblewrapの仕様では、`--disable-userns`はsandbox内のnested user namespace作成を抑止し、`--remount-ro`は指定mount pointに作用する。実装は`--assert-userns-disabled`、mountごとのwrite-denial probeも要求する。[upstream manual](https://github.com/containers/bubblewrap/blob/main/bwrap.xml)

## 検証

### ローカル

- QTS focused tests: 15 PASS
- runtime trace/replay tests: 18 PASS
- isolated verifier tests: 14 tests、11 PASS・3 SKIP（bwrapがない環境でcandidateを実行する境界testとtimeout testをskip）
- Agent evaluation suite: 241 PASS、5 SKIP
- Agent repository contract tests: 4 PASS
- runtime suite: 388 PASS
- `compileall`: PASS
- `dprint check`: PASS
- `git diff --check`: PASS
- Ruff: ローカル未導入のため未実施。Code Quality CIで固定versionを実行する。

この最終回帰では、Verifier候補を実行するbubblewrap processの起動記録とVerifierコード実行の証拠も分離した。非ゼロ終了だけの場合はVerifier実行を`unverified`相当として断定しない。

`bwrap`はこの開発環境で検出されなかった。従って、namespace、credentials read-denial、read-only filesystem、network遮断、資源上限、timeout後の子process終了をこの環境で実測していない。通常Python processへfallbackせず、候補Verifierを起動しなかった。

### GitHub Actions

開始HEAD `6a1e4e4`の既存5 workflowは開始時すべてSUCCESSだった。今回のcommit後のCIは未確認であり、PR HEADのworkflow runを確認してから最終状態を更新する。Code Qualityの必須bubblewrap probeが失敗した場合は、境界を緩和せず実測した阻害条件を残す。

## 未達・制約

- Stage 2 QTS raw attemptを現行Verifierで再実行していない。保存runのEvaluator revisionが現在のHEADと異なり、ローカルのboundary probeも未成立である。
- Dockerless `verify`と`workflow-runtime`の両方を、保存済みQTS requestに対して独立実行する検証は未達。今回のunit testは入力検証・fail-closed・semantic比較の処理を確認したが、実OS境界での候補実行を確認していない。
- 既存のruntime capture不足・重複invocation、Judge未実施、meaningful traceability、`can_complete=false`のQA品質判定は第2段階の未達として維持する。
- QTS製品コード・仕様・Seed/Reset・既存製品test、元Stage 2 raw evidenceは変更していない。
