# PR #17 Stage 5：Skill評価・改善サイクルの実動作結果

## 結論

開発用サブエージェントhandoffを既存deterministic graderへ接続し、baseline/candidateと独立回帰を実際の成果物で評価できた。`test-case-design`候補は対象`TC-OUT-001`で2/2回`RT-D016`に失敗し、改善は成立していない。candidateの独立`TC-OUT-002`も2/2回同じ必須runtime assertionに失敗した。候補は隔離patchとして保存し、Skill本体へ採用していない。

結果は開発用評価であり、formal runnerや独立評価ではない。requested model設定は記録したが、実効model/build、Agentの完全なtool履歴、共有workspaceからEvaluator-onlyファイルを読めないことは検証していない。

## 開始状態と固定条件

- PR #17はOPEN、base `main`、head `feat/agent-eval-runner`。作業開始時のGitHub HEADは`118b26a718dcd75a910fc1c0613f28bf339e0dcb`で、ローカルとも一致した。
- 開発用handoff比較の実装をcommit `11ef736ef6927715e871021dfdf1d2b65b3b91b5`へ固定した後、実Agent比較用runを準備した。
- Candidate比較時のEvaluator revisionと親Skill revisionは同じ`11ef736ef6927715e871021dfdf1d2b65b3b91b5`。Evaluator、入力、生成prompt、requested settingsを各比較内で固定した。
- 全Agent実行要求は`model=gpt-6-luna`、`reasoning_effort=max`、`fork_turns=none`。run recordとhandoff manifestでも要求値を確認した。実効値を示すtelemetryはなく、全attemptでeffective model/buildは`unverified`。
- baseline Skill package fingerprintは`sha256:98aea2798671eeb721de1da5210b5e2b5d2c47bd5ea9cfa8f5460df10146d23e`。candidateは`sha256:e2d2399a64a722d0363405827b4c1584c9e58e19229bb65d97ff452991d591a7`。
- 修正Agentへ渡したのは`test-case-design`の失敗根拠と許可pathだけで、expected、grader、Judge fixture、`TC-OUT-002`の内容・expectedを渡していない。共有workspaceの物理的読取拒否は証明していない。

## 既存ケースの確認

| 対象                                   | 実行記録                                                                 | 結果と分類                                                                                                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test-requirement-design / TR-OUT-001` | `pr17-subagent-handoff-154d05f-01/`, `pr17-subagent-handoff-154d05f-02/` | 既存結果を再利用。各runの1件が21/21 PASS。これらはEvaluator/Skill revision `154d05f…`の結果であり、今回の`11ef736…`と同条件の再比較ではない。                                       |
| `test-requirement-design / TR-OUT-002` | `attempt-TR-OUT-002-corrected/`                                          | 2/2が21/21 PASS。先行runはrelative Skill path誤りで停止し、実評価に数えない。二つの出力は同一のblocked/未解決判断を保っている。                                                     |
| `test-requirement-design / TR-OUT-003` | `attempt-TR-OUT-003-final/`                                              | 有効な2件のうち1件は20/20 PASS、1件は17/18 FAIL。失敗は`RT-D016`のMachine Entities欠落。その他のhelper起動・seal失敗attemptは実行/証拠エラーとして保存し、品質gradeへ混ぜていない。 |

`TR-OUT-003`では同一入力で一方が空Entityを含み、他方がMachine Entitiesを欠いた。Skillにはruntime evidence gateが既にあり、保存された記録だけではSkillの指示違反、Agentの出力揺れ、helper要求の不明確さを分離できないため、Skill欠陥とは認定せず修正しなかった。`TR-OUT-004/005`のinput/expected fingerprintはcandidate修正前にlockした。これらは`test-requirement-design`ケースであり、`test-case-design`候補の独立回帰へ流用していない。

## `test-case-design / TC-OUT-001` 対象評価

この入力はTR/TCN/CIのIDと参照だけを含み、上流本文や実行条件はない。baseline・candidateともケース表をheader-onlyにし、上流項目を個別にblockedとして扱った。仕様の不足を埋める架空のtest caseは確認されなかった。

| 側        | Grade可能なattempt                 | 結果                                                                                                                             |
| --------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Baseline  | `c51e2bb1644849eabe4581ceb0dd156e` | 17/18。唯一のFAILは`RT-D016`。Machine Runtime Input、Result、Entitiesの全blockが欠落。                                           |
| Baseline  | `88dc26754dd449d7af9056845deee3b2` | 0/2。`OUTPUT-MD-TABLE-001`と`RT-D016`がFAIL。                                                                                    |
| Candidate | `0c5de5c3cfcb40e799b2c91803ab089d` | 17/18。`RT-D016`で3 blockすべて欠落。                                                                                            |
| Candidate | `69d16f7366304f44b56c871c47ad7e28` | 17/18。Input/Resultは含むがMachine Entitiesが欠落し、`RT-D016`がFAIL。runtime verifierの有効性も固定graderでは確認されなかった。 |

Baseline結果は二つのrun rootに分かれ、各rootのもう一方のattemptは`not_started`だった。このため`improve.py compare-handoff`のtarget比較は両runとも`not_comparable`。2つのGrade可能baseline出力は個別に照合できるが、toolはrun rootを跨いでattemptを集約しないため、再現性あるtarget比較が完了したとは扱わない。Candidate側は2件ともGrade可能だが、どちらも対象assertionを通過していない。

### 失敗原因の分類

1. **評価入力**：上流本文の欠落により実行可能なcaseは作れない。これは正当なblocked理由である。
2. **runtime契約/evidence**：固定graderの`RT-D016`は、Skillが要求するMachine Runtime evidenceがない場合の不適合を検出した。graderやexpectedは変更していない。
3. **Skill候補**：candidateは、schemaと意味が分かる場合に提供済み値だけでgeneratorを呼ぶこと、未解決結果を完了へ読み替えないこと、`valid=true`をgenerator成功と同一視しないことを明確化した。しかし、request自体を構成できない分岐のevidence gateを通す方法、およびempty Machine Entities blockの出力契約を十分明確にできなかった。
4. **Agentの実行差**：candidateの1件目はruntime blocksを出力せず、2件目はgeneratorの`invalid_input / blocked`結果を記録したがEntities blockを出さなかった。効果は揺れ、対象assertionは0/2でPASSしない。
5. **評価データ/表**：baselineの表解析FAILは1/2、candidateは0/2だった。既存templateには列数が揃った正規形式があり、patchは表形式を変更していないため、Skill改善効果とは判断しない。

## Candidateと独立回帰

Candidate patchは`.agent-eval-runs/pr17-stage5-20261103-01/candidate-test-case-design.patch`、SHA-256 `e68ce13247f7a8327336b2d37730541fadffdcd1c2566da4eb02d19e2c6c7c38`。変更範囲は隔離package内の`skills/test-case-design/SKILL.md`だけで、repositoryのSkill本体、grader、expected、dataset、他Skillは変更していない。candidate file SHA-256は`b1624cf1b1e6cc25057b0bc6f29a6699ab6828853f7bdb07e7e71be8f507ea3d`。

修正Agent完了後、`test-case-design / TC-OUT-002`をrepair-cycle heldoutとしてbaseline/candidate各2回実行した。`improve.py compare-handoff`の出力は`comparable_development_handoff`、条件差なし、baseline共通FAILは`RT-D016`、candidateが修復した共通FAILは0件、各pairで新規assertion FAILは0件。baselineとcandidateは全件非PASSであり、これは「独立回帰PASS」や「改善成立」ではなく、追加の決定論的回帰を検出しなかったという結果である。caseは過去評価履歴があり、今回のrepair agentには内容を開示していないが、globally unseenな入力ではない。

`TC-OUT-001`対象では修正効果が固定graderで成立せず、`improvement_demonstrated=false`。Candidateはreview-pending相当として保存し、PR branchのSkill本体には反映しない。`TC-OUT-002`のno-new-failure結果を使って対象caseの失敗を相殺していない。

## `improve.py`との接続範囲

commit `11ef736ef6927715e871021dfdf1d2b65b3b91b5`で以下を実装した。

- `subagent_eval.prepare --skill-package-root`により、指定Skillだけの候補packageを固定Evaluator用runへ取り込む。許可Skill package検査を使い、`evals/`とexpectedをagent-visibleへ含めない。
- `improve.py compare-handoff`はhandoff/request/package/output/grade hash、attempt ID、要求条件、candidate package差分を確認し、既存固定deterministic graderを再実行してbaseline/candidateを比較する。
- 旧formal runner、schema 2 profile、隔離証拠を開発用runへ偽装していない。旧formal `improve.py`経路とlauncherのfail-closedは維持する。
- PythonからAgentを起動する処理はない。Agent起動、原因分類、許可path内での修正はCodexホスト側。比較・grade再検証・記録はPython側。
- `compare-handoff`は`TC-OUT-002`の実baseline/candidate runで動作した。Target結果はattemptが複数rootへ分かれた場合に集約できず`not_comparable`となった。自動分析・修正・独立回帰・PR採用を一括実行する機能、effective model検証、formal acceptanceは未完成。

## 試行全体と保存先

Current-revisionの5 run groupには合計10 attempt recordがある。8件はAgent artifactを取り込み、すべて固定graderでFAIL。2件は`not_started`で品質評価に含めていない。加えて短縮SHAによる生成前停止、candidate package path誤りによる生成前停止、formal launcher停止の誤認、attempt-local Skill pathの誤認を別々に記録した。失敗した試行を削除・置換していない。

全attempt ID、hash、run root、旧TR評価、heldout lock、比較JSONはGit管理外の`.agent-eval-runs/pr17-stage5-20261103-01/evidence-index.md`とその配下にある。raw Agent出力、expected、private lock、credential関連情報はcommitしない。

## 検証と評価の限界

- Agent evaluation tests: 263 passed、6 skipped。
- `test_case_structure`: 9 passed。
- deterministic evaluation tests: 10 passed。
- `compileall`: passed。
- dprint check、`git diff --check`: passed。
- ローカルRuffは未導入。初回Code Qualityで検出された2箇所のRuff format違反をcommit `8522c3e`で修正し、同HEADのCode Qualityを含むGitHub Actions 5件がすべてsuccessとなった。
- Codexホストのsubagent callとrequested settingsを記録したが、実効model/build telemetryは取得していない。
- expected等をtask/packageから分けたが、共有workspaceの物理的な読取拒否は未検証。これはformal/independent evaluationではない。
- 独立Judge、formal runner、semantic evaluationは使用していない。固定QTS workflowやその未解決仕様は今回の対象ではない。

## 判定

1. 開発用Agent評価・固定grader取込・決定論的比較は、単一Eval Inputおよび同一run内2-attempt比較で実動作した。
2. `test-case-design`の`TC-OUT-001`で再現する品質上の不適合はruntime evidence `RT-D016`の欠落である。
3. Candidateはruntime evidence不適合を解消せず、改善成立ではない。
4. `TC-OUT-002`で新規assertion悪化は検出されなかったが、baseline/candidateとも非PASS。独立回帰通過とはしない。
5. Candidate patchは未採用・隔離保存。formal runner、effective model、物理隔離、Judgeは未達のまま維持する。

Stage 5で実装した比較経路と、今回確認した非PASS結果をもって、このStageの改善受入条件は未達と判定する。追加生成でPASSを得るまで繰り返さない。
