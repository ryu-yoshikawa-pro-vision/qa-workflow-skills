# PR #17 Skill改善候補の比較と反映

## 結論

`test-requirement-design`のstable IDとrevision referenceを分離するSkill修正候補を、PR branchのレビュー対象として反映した。対象の`TR-OUT-013`は同一入力・固定Evaluatorでbaselineが2回とも失敗し、candidateは2回とも通過した。runtime evidenceは全4試行で有効だった。修正者の修正入力に使用していない`TR-OUT-001`でもbaseline / candidateの双方が通過し、回帰は観測されなかった。

これは共有workspaceでの開発用実動作評価である。評価用正解データへの物理的な読取拒否と実効モデルbuildは確認できていないため、正式な独立評価・正式runnerの受入・mainへの採用を意味しない。

## 対象と原因

- 開始HEAD / Evaluator revision: `61283c0061fbe9ea75bbb9548a956cf9d939b04b`
- Skill: `test-requirement-design`
- Candidate patch: `.agent-eval-runs/pr17-improvement-workflow-20261101/attempts/repair-agent-001/candidate.patch`
- Patch SHA-256: `bbb54d5a76cd9e5c29df9b206aa0fb9f1f5903297a0f505c3f18f4928871d534`
- baseline / candidate Skill SHA-256: `3f0fca0750a2cbb2cbcc81a181a1b7a9ca6a0ba51b701a07295a993c5ed2ddf0` / `f122fca97db6fc43044c186928f68070a3ef7b68b5885fd803a288f22ac0997d`
- `TR-OUT-013` input SHA-256: `c183c4cad94fbb72a08f8c0bb58a04f7d64bc6060d6e544e244f7b82ecb4ceda`
- 固定expectedのSHA-256はprivate evidenceだけに保存し、ここでは内容を開示しない。

baselineは、revision `rev-2`をstable IDと同じ人間向け上流ID欄へ結合していた。`TR-D013`、`TR-D009`、`TR-D015`はそのため上流Entity参照を正しく照合できず、各attemptで失敗した。上流項目が入力不足であることをブロック中とした判断自体は維持されていた。

candidateは`SKILL.md`だけに、上流ID欄には`entity_ref`をそのまま書き、revision/versionは必要に応じて根拠欄へ分ける規則を追加した。Machine EntityのDispositionも同じstable referenceを使う。処理スクリプト、template、grader、expected、runtime gate、他Skillは変更していない。baseline / candidate packageを照合した結果、`SKILL.md`以外の5つの実ファイルは同一hashだった（生成された`__pycache__`は除外）。

## 比較結果

| ケース                              |   baseline |  candidate | 内容・runtime判定                                                                                   |
| ----------------------------------- | ---------: | ---------: | --------------------------------------------------------------------------------------------------- |
| `TR-OUT-013` attempt 1              | 17/20 FAIL | 20/20 PASS | baselineは`TR-D013/D009/D015` FAIL。candidateは全assertion PASS。4成果物のruntime evidenceはvalid。 |
| `TR-OUT-013` attempt 2              | 17/20 FAIL | 20/20 PASS | 同じ3 assertionの失敗が再現。candidateは再度全assertion PASS、runtime valid。                       |
| `TR-OUT-001` 修正者未使用の回帰入力 | 21/21 PASS | 21/21 PASS | runtime valid。candidateでもblocked処理と有効なDispositionを保持し、回帰なし。                      |

要求されたAgent設定は各保存attemptに`gpt-6-luna / max / fork_turns=none`と記録されている。実効model/build telemetryは利用できず未検証である。Agentは親とworkspaceを共有し、物理的なexpected/grader読取拒否も未検証である。したがって、比較は開発用途の根拠であり、正式な独立評価ではない。候補生成Agentには失敗原因、対象Skill、`TR-OUT-013`の成果物が渡され、独立回帰`TR-OUT-001`は修正対象として渡されていない。ただし共有workspace上の実効アクセスを拒否できたとは主張しない。

全attemptを比較へ含めた。失敗成果物の除外や成功までの再試行は行っていない。

## 別のtemplate候補

`.agent-eval-runs/pr17-tr-stable-id-repair-20261101/candidate.patch`（SHA-256 `2570660761bbf062da8c34e703080223a1c1fb4f940db3663945ba721f60fc51`）は別のtemplate-only変更であり、本報告のSkill本文候補とは混同しない。この候補の`TR-OUT-003`生成物は現在のgraderで内容 assertion 17/17 PASSだったが、必須Machine Runtime Input / Result / Entitiesが欠落し、`RT-D016`がFAIL、runtime valid=falseだった。同じケースのbaselineは20/20 PASS、runtime validだった。この失敗attemptは保持し、候補を反映しない。欠落の直接事実は確認できるが、template変更とAgent出力ばらつきの因果は確定していない。合格成果物へ差し替える再試行は行わない。

## 停止条件とPR反映

原因不明、結果の揺れ、必須runtime evidence欠落、契約違反、独立回帰失敗は該当candidateだけをreview-pendingとする。実際の秘密漏えい、正解情報の混入、証拠と成果物の対応破損、破壊リスク、安全な実行環境の欠如は影響範囲の作業を停止する。Judge未承認、formal runnerのfail-closed、model telemetry未取得、物理的隔離未証明は正式受入を妨げるが、安全に成立する開発評価や別candidateの検証を一律停止しない。

今回のSkill本文candidateは、反復した対象改善、別入力の回帰、runtime evidence、関連契約テストを確認したため、PR branchにレビュー可能な変更として反映する。正式独立評価、Judge、正式runner、merge/main採用は引き続き未達である。runnerはGit操作を行わず、今回の反映はmaintainerによる個別のbranch更新である。

新しいdeterministic regradeとartifact hash一覧はGit管理外の`.agent-eval-runs/pr17-promotion-review-20261101/evidence-index.md`および`.json`に保存している。生成果物とgrader JSONはcommitしない。

## 検証

- `tests.skills.runtime.test_test_requirement_structure`、`tests.skills.runtime.test_runtime_contract`: 66件 PASS
- deterministic suite: 28件 PASS
- `improve.py` tests: 42件 PASS
- 6 Skillsの最終runtime evidence gate policy contract: PASS
- `compileall`: PASS
- 変更対象のdprint check: PASS
- `git diff --check`: PASS
- `python scripts/format_tracked.py check`: ローカルの`ruff` executableがなく未完了。push後のCode Quality CI（run `41292498067`）はPASS。
- push後の最終HEAD `7347194d4572e0155e83d889318cfda67e2c0188`では、5つのGitHub Actions（Code Quality `41292498067`、Validate Agent Skills `41292498060`、Validate Semantic Output Evals `41292498075`、Validate Deterministic Output Evals `41292498073`、Codex Harness `41292498080`）がすべてPASS。

合成のimprove処理テストはcandidate保存と再評価失敗時の停止を検証するが、今回の実Agent candidate生成は`improve.py`のライブrunnerを経由していない。実Agentによる原因分析とpatch作成、保存済みの全attempt、現在のdeterministic grader、Skill-local runtime verifierを組み合わせた開発用比較である。再利用工程の完全自動運転が受け入れられたとは主張しない。
