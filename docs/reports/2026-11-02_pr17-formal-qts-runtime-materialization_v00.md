# PR #17 正式受入・QTS runtime materialization追補

## 結論

開始時のPR HEADは`232f9088cdc6bd0438d35ddb0d867d3086da6660`、QTS固定sourceは`84ce165493649550832731a60cf436f8ae29c56b`。保存済みのQTS開発用2 attemptを再利用し、同じAgent評価は繰り返していない。

attempt-02で確認された`TCN-003`のmaterialization欠落は、未確定Decision Table resultを`materialize_coverage`が入口で拒否する一方、runtime evidence contractが同TCNのmaterialization unitを必須としていた、Skillだけでは解消できないruntime契約不整合だった。決定論的な合成入力で再現し、`materialize-coverage-v3`で修正した。既知のmaterializable targetはCIへ統合し、未確定targetにはCIを作らず、materialize結果とmodel completionを`unresolved`に維持する。QTSの仕様や未解決状態は変更していない。

この修正はruntime実装の回帰テストで確認した。修正後の実AgentによるQTS再評価、固定Docker imageによるproduction verifier replay、正式runner、独立Judgeは未実施である。したがって、今回の修正だけでAgent品質の改善や正式受入を認定しない。

## 使用した証拠と固定条件

- PR #17開始HEAD: `232f9088cdc6bd0438d35ddb0d867d3086da6660`
- QTS source revision: `84ce165493649550832731a60cf436f8ae29c56b`
- 保存済み開発用attempt: `.agent-eval-runs/pr17-qts-casegen-runtime-fix-20261102-r1/`
- 保存済み報告: `docs/reports/2026-11-02_pr17-qts-casegen-runtime-fix_v00.md`
- 既存2 attemptでは各9件の正規QA成果物を生成。attempt-02のTCD evidenceはTCN-003 materialize unit欠落でinvalid、双方のQTS workflowは`can_complete=false`。
- 過去attemptの要求モデルは`gpt-6-luna / max / fork_turns=none`。実効model/build telemetryは未取得。
- 今回はサブエージェントを起動していない。

raw attemptと保存済みtargetを変更していない。QTSの製品source、規範仕様、Seed/Reset、製品テスト、評価expected、grader、Judge fixtureも変更していない。

## TCN-003の原因と修正

保存済み`test-condition.md`で、`decision-004`は`runtime_status=ok / result_status=unresolved`。2件の既知targetはmaterializableで、TEST-SUCCESSと最終在庫不足の未定義assignmentはnon-materializableとして出力されていた。Agentは未解決modelを理由にTCN-003の`materialize_coverage`を実行しなかった。

現行実装を調べると、次の契約が衝突していた。

1. `runtime_contract.py::_verified_child_units()`は、active model metadataのあるTCNにmaterialization evidenceを期待する。
2. `materialize_coverage.py::_validate_model_results()`は`result_status=ready`しか受け付けない。
3. そのため、runtimeが有効な未解決resultに既知targetが含まれていても、materializerを呼ぶと`invalid_input`となる。

保存済み`decision-004`と同じ形の決定論的synthetic Decision Table入力でこの拒否を再現した。修正後はruntime-statusがokでcurrentなunresolved model resultを投影入力として受け付ける。非materializable targetをCIへ含めず、unresolved modelをcompletion済みにせず、出力へ`model_materialize_incomplete`を保持する。これによりevidence unitを生成しながら未解決状態を保つ。

変更箇所:

- `skills/test-condition-design/scripts/materialize_coverage.py`: 入力statusと不完全coverage summaryを許容し、unresolved model completionを閉じない。generator contractを`materialize-coverage-v3`へ更新。
- `skills/test-condition-design/SKILL.md`、`references/coverage-techniques.md`: current unresolved resultでもmaterializeを実行し、確定済みtargetとblocked candidateを分離する指示を追加。
- `docs/plans/2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md`: v3の契約を追記。
- runtime tests: v3の未解決model入力、既知targetだけの安定ID割当、blocked targetへのCI不発行、completion未完了を確認。

修正後の実Agent出力はまだないため、Skill指示がAgentの再実行を確実に導くかは未検証。旧attempt-02成果物を修正版として扱っていない。

## QTSの意味品質所見

保存済み2 attemptの内容は既存報告と照合した。新しい生成はしていない。

| 所見                       | 保存済み結果                                                                       | 今回の扱い                                              |
| -------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 最終在庫不足時の終端状態   | 仕様外の具体状態の確定は新しい2 attemptで再現せず、Q IDはattempt間で異なる         | 仕様未確定を維持。Skill欠陥とは認定せず修正なし         |
| TEST-SUCCESSなしの成功期待 | 成功経路自体は2 attemptともTEST-SUCCESSを含む。inventory decrementの記載が片方のみ | 成果物間で揺れ。安定したSkill原因が未確認のため修正なし |
| 24時間ちょうどの境界       | 質問・期待値がattempt間で一致せず、境界包含は固定仕様にない                        | 正解を創作せず、未確定を維持。修正なし                  |
| TCN-003 materialization    | attempt-02でmissing evidence。helper入力を合成再現すると`invalid_input`            | runtime契約の実装不整合を今回修正。Agent再評価待ち      |
| QA workflow完了            | QTS仕様の未確定事項と未完了downstreamが残り、`can_complete=false`                  | 正当な未完了状態として維持                              |

この結果は決定論的runtime契約の検証であり、意味的な品質判定は未承認Judgeの承認に依存する範囲を含む。開発用Agent成果物を正式な独立評価と扱わない。

## 正式評価・Judge・verifierの状態

### Formal runner

launcherの両安全ゲートは引き続き未解決でfail-closed。2026-10-31の保存済み合成refresh検証は合成認証状態とmock endpointを使い、実認証やmodel API通信はしていない。更新後stateを別processで読めた一方、固定Codex CLI本体を強制終了してtruncate / partial-write / fsync failureさせる検証は未実施。launcherのfake processによるmarker保持・retry拒否テストは実CLI本体の挙動証明ではない。

`flock`は協調runnerを直列化するだけで、同じUIDの非協調processやinventory検査後のprocess起動を排除しない。専用実行UID、専用認証store、同UID processの起動権限境界は構築されていない。`AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED`と`AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED`は変更していない。

### Judge

QTS fixtureは11件すべて未承認。human review待ち9件、deterministic review待ち2件の状態を変更していない。既存の人間レビュー資料を再利用可能であり、JudgeやAgentによる自己承認は行っていない。正式Judgeは未実施。

### QTS production verifier

この環境にはDocker/Podman/nerdctl/ctr実行経路とDocker socketがなく、固定image digestを指定した既存Docker contract replayは実行していない。保存済みruntime captureのPython replay記録は参照したが、Docker production replayの代替PASSとは扱わない。

`improve.py`の正式baseline→Repair→candidate再評価→独立回帰も未実施。開発用既存評価や今回のunit testをlive repair受入へ読み替えていない。

## 今回の検証

- `python -B -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`: **384 passed**
- focused runtime/integration/cutover/contract tests: **84 passed**
- deterministic `test_runtime_validator`: **16 passed**
- `compileall` (temporary pycache prefix): passed
- dprint check (変更対象ファイル): passed
- `git diff --check`: passed
- Ruff: local executable unavailable; final Code Quality GitHub Actionで確認する

上記はコード/runtime契約の検証であり、実AgentのQTS再評価、production Docker replay、正式runner、独立Judgeの成功を意味しない。

## 残る外部条件

| 未達条件                        | 必要な対応                                                                                                                                         |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 認証refreshと異常終了後の安全性 | 固定Codex CLI本体に対する安全な異常終了・復旧証拠が必要。本人のChatGPT再認証を含む回復手順を実認証状態へ適用する場合は、利用者本人の明示操作が必要 |
| 非協調process境界               | 管理者が専用UID / HOME / CODEX_HOMEを用意し、同UIDの任意process起動を制約するOS境界、runner所有権・起動権限を構築・検証する必要がある              |
| Judge 11 fixture                | reviewerが9件の規範解釈を確認し、2件のdeterministic reviewを実baseline artifactとbindingで確認して承認する必要がある。Agentの承認代行は禁止        |
| production verifier replay      | 固定image digestと既存`--network none` Docker実行契約を満たすDocker hostが必要                                                                     |
| 正式QTS repeat / model条件      | 上記の認証・隔離・fixture承認後、固定scenario・target・profileで独立attemptを実行し、実効model telemetryとprovenanceを保存する必要がある           |
| Skill自動改善の正式live経路     | 正式baselineと承認済み必要criterionを得てから`improve.py`のRepair・candidate比較・独立回帰を実行する必要がある                                     |
