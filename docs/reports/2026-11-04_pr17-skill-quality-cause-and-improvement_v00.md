# PR #17：Skill品質問題の原因調査・実Agent評価・候補比較

## 判定

4 Skillsの4 deterministic Eval Inputを調査し、16件の実Agent評価attemptを準備した。9件は成果物を取得し、7件は生成前停止・実行失敗だった。要求設定は全attemptで`gpt-6-luna / max / fork_turns=none`。実効model/buildは未検証であり、共有Codex workspaceからEvaluator-only情報を物理的に読めないことも未検証である。

`test-case-design / TC-OUT-001`では、baseline 2件とも内容面では根拠のないケースを作らずblockedとした一方、grader必須のMachine Runtime Input / Result / Entitiesがなく、RT-D016に失敗した。Skillのdispatch説明には、request shapeが既知で意味内容だけ不足するblocked入力を一度実行して証拠化する手順がなかった。合成probeでは、与えられたIDだけを使う`invalid_input / blocked`結果と全runtime blockを生成でき、runtime assertions RT-D016/017/018は通過した（合成成果物全体は別の表assertionでFAIL）。この根拠からSKILL.mdだけを変える隔離candidateを1件作成した。

同じEvaluator revision、Eval Input、要求Agent設定でbaselineとcandidateを2件ずつ比較した。candidateはRT-D016を2/2件で通過したが、全体では1/2 PASS・1/2 FAIL。失敗attemptはMachine Entities schema不正でRT-D018に失敗し、Markdown table parserにも失敗した。`improve.py compare-handoff`は`comparable_development_handoff`を返し、RT-D016修復を認識した一方、`improvement_demonstrated=false`とした。候補全体の改善は未成立として不採用・レビュー待ちにし、独立回帰は実行していない。

## RT-D016の原因と修正範囲

- 固定入力はTR/TCN/CI/AuthorityのIDと一部メタデータだけを与え、本文・仕様・開始状態・操作・期待結果は明示的に欠落させている。実行可能なテストケースを作らずblockedにした内容判断は正しい。
- `evals.json`は`artifact:case_structure:all`のSkill runtime検証を必須にしており、deterministic graderのRT-D016は対象unitの3つのMachine blockを一意に要求する。runtime evidenceの欠落をgrader側で免除しない。
- SKILL.mdは「canonical normalized inputの契約が不明なら実行しない」と「最後にruntime evidenceを検証し、valid=trueの場合だけ返す」の両方を定めるが、request構造とIDが分かって意味データのみ不足する場合の扱いを説明していなかった。2件ともケース生成は適切に止めたが、runtime dispatch/evidenceが抜けた。
- 合成probeは既知IDと未完成CI行を含むcanonical requestから、`invalid_input / blocked`と空payloadを返した。三つのMachine blockを持つ合成artifactでRT-D016/017/018はPASS、全体graderはTC-D012でFAILだった。これはruntime証拠契約を示す合成検証で、実Agent成果物ではない。
- candidateはSKILL.md内の1段落だけを変更し、入力構造が既知で内容が不足する場合は与えられたID/値と必要な空collectionのみでgeneratorを1回実行し、block状態・runtime evidenceを保持してケース生成と混同しないよう指示した。RepositoryのSkill本体、Evaluator、expected、grader、他Skillは変更していない。

## 修正前後の比較

比較入力fingerprintは`sha256:bc819c56c637e1ea19f86558e296ba6b984120380a51c94b7d80e21c047d287e`。baselineとcandidateの固定Evaluator revisionは`efb58136d892943613e888357840209b40339fde`、Skill packageは修正行を除き同一。baseline側の元Agent出力は前のrunで取得済みだったため、新しいEvaluator revisionで再取込・再採点した（2回の新規baseline生成ではない）。元出力の生成時Evaluatorは`96b4e78d0a504f0cc77caecb619cdcf5122660ef`であり、入力・Skill bytes・prompt template hash・要求設定は比較対象で同一だった。実効modelは両側とも未検証。

| 条件        | Attempt                            | 結果        | 主な失敗                                                 |
| ----------- | ---------------------------------- | ----------- | -------------------------------------------------------- |
| Baseline 1  | `8ae12ba229ea4db287e5a57e247467d4` | FAIL、17/18 | RT-D016                                                  |
| Baseline 2  | `26f0904eb5c046839bd1713bd8eea939` | FAIL、0/2   | OUTPUT-MD-TABLE-001、RT-D016                             |
| Candidate 1 | `70d4c3a45b43481e935e686947b7e8a7` | FAIL、2/4   | OUTPUT-MD-TABLE-001、RT-D018（invalid Machine Entities） |
| Candidate 2 | `55fb8f39b9024a40b90bb4b04e262bef` | PASS、20/20 | なし。runtime verifier valid=true                        |

候補はRT-D016自体を2/2で満たしたが、candidate 1でRT-D018とMarkdown表の違反が発生した。baselineにもtable parserの失敗が1/2あり、単一attemptの原因をSkillへ帰属できない。全体改善・回帰なしとは判定しない。修正candidateのpatch SHA-256は`sha256:f0832cc652b9da7995497d302ec286ed4cc15fbe41d22ba28db569972ec304ca`、候補SKILL.md SHA-256は`sha256:4254fb6dcda437908d59c5c0b7a0b64e24c94857872a4df6656f856ce2c12895`。candidate packageは`.agent-eval-runs/`に保存し、正式採用していない。

独立回帰用の`TC-OUT-002`入力・expected・manifest hashはcandidate編集前に固定した。ただし、このcaseはStage 5で既に使われておりglobally unseenではない。candidateが全体FAILになったため実行を保留した。比較・候補差分・全attemptの索引はGit管理外の`.agent-eval-runs/pr17-skill-quality-20261104-01/evidence-index.md`に記録した。

## その他のSkill評価

### `test-requirement-design / TR-OUT-003`

同一input fingerprint `sha256:0571fd65fe0e12b003bdea067d4922f4101b9f6f0acfac9be6cda6e6fa7fb469`で1件は14/18 FAIL、もう1件は20/20 PASS。FAIL側は入力にある上流IDと異なる`AC-001（入力要約ID）`を出力し、TR-D013/D009/D015とruntime evidenceで失敗した。Skillは正確なstable IDを要求しており、もう一方ではhelperが`invalid_input / blocked`を記録してPASSした。1回の逸脱で再現性あるSkill欠陥とは認めず、修正しなかった。

### `test-condition-design / TCN-OUT-002`

固定input fingerprint `sha256:936d9c41ef526b96d8e8941d013242d51a1e57ee5479f793c79cd0adca6e4d45`に対し、生成物1件は最終在庫不足/Authority未解決の状態でactive CIを作り、TCN-D016/D017で失敗した。ただしもう1件は誤ったworking directoryによる`not_started`、独立した再試行も成果物なしの`execution error`であり、品質問題の再現性は確認できない。

保存済みartifactを修正後Evaluatorで再採点すると30/32 PASS、TCN-D016/D017 FAIL、runtime verifier valid=trueとなった。旧graderのRT-D018失敗は、draft keyからstable keyへ変わったpost-root runtime modelを再構成できなかったdeterministic evaluatorの欠陥だった。`runtime_validator.py`がcaptured resultの実モデルを使ってreplayする修正とintegration testをcommit `efb58136d892943613e888357840209b40339fde`に含めた。残るD016/D017は1件だけの成果物で、Skill defectとは断定していない。

### `coverage-analysis / COV-OUT-001`

固定input fingerprint `sha256:5fcfe8297aefa29c0ee515859a52222eb1b62aea295eef1c010608dca765e143`。初回2件はAgentがrepository rootからSkill相対pathを探した起動上の失敗で、修正後2件は出力を作成した。1件はcapture後に親側のseal呼び出しでartifact attempt IDを誤り、正規sealを作れなかった。原出力へ直接行った診断graderは41/41 PASSだが、有効なsealed runとして数えない。もう1件は20/22 FAILで、Agentが正規generator結果から`result_status`をMachine Runtime Resultへ転記し忘れたためschemaとRT-D018に失敗した。元の正規runtime出力はこのfieldを持ち、他attemptの直接評価は41/41だった。Skillは正確なruntime resultの保存を既に要求するため、Agent出力のばらつき/転記不備とし、Skill修正を作らなかった。seal手順を直した1件はartifact提出なしでexecution errorだった。

## 評価基盤の変更と検証

- `96b4e78d0a504f0cc77caecb619cdcf5122660ef`：`improve.py compare-handoff`と`subagent_eval.py`を堅牢化し、attempt inventory不一致、欠落/重複attempt、candidate-only failure、無効なhost execution evidenceを拒否するテストを追加。
- `efb58136d892943613e888357840209b40339fde`：TCN runtime replayのpost-root normalizationを修正し、実artifactから再現するintegration regressionを追加。
- 比較工程を`improve.py compare-handoff`で実行し、状態`comparable_development_handoff`、条件mismatchなし、formal acceptance/effective model/physical read denialは`unverified`、candidate全体の`improvement_demonstrated=false`を確認。
- Agent evaluation tests: 266 passed、6 skipped。
- Runtime tests: 388 passed。
- Deterministic evaluation tests: 28 passed。
- 対象vertical integration tests: 4 passed。
- 最初のpushでGitHub Code QualityはRuff format checkに失敗し、変更済みの2 Python fileでformatter差分を報告した。CIの差分どおり整形し、handoff tests 25件、runtime-validator tests 16件、compileall、dprint check、`git diff --check`を再実行して成功。修正後のcommit `9b540df6d18cddaa9d7187b47d35cb577581e7e5`ではGitHub Actions 5 workflowがすべて成功し、CI環境のRuff format checkも成功した。Ruffはローカル未導入。

## 最終結論

- 調査したSkill数 / input数: 4 / 4。
- 実Agent evaluation attempts: 16（準備済みの全試行を含む）。生成果物9件、生成前/実行停止7件。成果物のうち1件はseal不成立の診断gradeのみ。
- 再現した出力問題: TC-OUT-001のruntime evidence欠落2/2。候補で対象assertionは2/2通過したが、全体適合は1/2 PASS・1/2 FAIL。
- 再現性あるSkill起因候補: 1件のruntime evidence dispatch説明不足。候補は改善未確定でレビュー待ち。
- Skill修正候補: 1件。PR branchのSkill本体への採用: 0件。全体改善を実証した候補: 0件。独立回帰済み候補: 0件。
- TR-OUT-003、TCN-OUT-002、COV-OUT-001には今回の証拠だけで修正できる再現性あるSkill defectはなかった。
- 正式runner、実効model/build、Evaluator-only情報の物理隔離、Judgeによる独立意味評価は今回の開発用サブエージェント評価では検証していない。

候補を通すためのPASS再試行や期待値変更は行わない。失敗候補と証拠を保持し、正式採用は行わない。
