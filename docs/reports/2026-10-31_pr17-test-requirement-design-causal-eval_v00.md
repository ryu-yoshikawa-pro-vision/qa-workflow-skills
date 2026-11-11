# PR #17 `test-requirement-design` 因果評価・改善候補

## 概要

開始HEADは`55869f870f48ebdbc89575d249373c8ecbcccfcb`です。対象Skillの比較baselineは`b9aa550df8f4fe7e0a84b77fe534ed1a8426227d`、現candidateは`55869f870f48ebdbc89575d249373c8ecbcccfcb`です。

今回確認した問題は、テスト要求があるのに「テスト要求を作らない上流項目」表へ架空の`該当なし / - / -`行を出力することです。行の`-`が正規enumでなく、`該当なし`もcurrent上流IDでないため、固定deterministic graderは`TR-D007`と`TR-D013`で正しくFAILにします。

現candidateの`SKILL.md`は「要求一覧が空ならヘッダーだけにする」と指示しますが、これは別の表に関する指示です。現candidateの`assets/output-template.md`にも、扱い表のplaceholder rowが残っています。`TR-OUT-005`のFAIL行は要求一覧ではなく扱い表にあり、このheader-only指示が原因でFAILしたとはいえません。直接の誘因は、扱い表テンプレートに例示データのような空行が残っており、モデルがそれを実在データとして補完したことです。

## 固定条件と方法

- Skill: `test-requirement-design`
- Agent設定: 各dispatchで`gpt-6-luna`、推論`max`、`fork_turns="none"`を明示
- 比較grader: repositoryの`deterministic/run.py`とSkill deterministic validator
- Runtime検証: 各attemptに配布した同一packageの`runtime_contract.py`を実行し、親側でも再実行
- Judge: 未承認fixtureは使わず、deterministic判定と入力・成果物の直接照合を実施
- `codex exec`、CLI version、provider build: 今回は未取得。サブエージェントdispatchのモデル指定記録があるが、provider buildと実効CLI telemetryはない
- 情報分離: Agent-visible treeにSkill package、入力、出力先のみを配置し、expected/graderは別ディレクトリに保管。全Agentは同一workspace権限を継承するため物理的read-denialは未証明。正式な独立評価ではなく実動作検証として扱う

held-out入力`TR-OUT-012`は修正候補を固定した後、生成前に入力・expected・dataset manifestを固定しました。入力はworkspace billing exportの権限境界とworkspace間データ分離を扱い、`SPEC-830`と`RISK-830`の両方を要求へ追跡できる構成です。入力SHA-256は`2b9c6abd09d75b2a33e136dc4e9d3074c2449def5155bb43d2de1c9864b551e4`、expected SHA-256は`ee29a4c4ab86b41ad9981072f73c7e947baaecec26ce0aefc7b3f3dbe524532f`です。

比較したcandidateは、baseline Skill packageに対して`assets/output-template.md`だけを修正した隔離版です。扱い表の例示placeholder行を除き、「実在する未接続上流項目だけを記載し、該当しなければヘッダーだけを残す」と明記しました。baselineからのpatch SHA-256は`4be619109b8e1f4327020a7102425a0d0d651b0fe31899c3fac5168077cf27bc`です。このcandidateはGit管理下のSkill本体へ採用していません。

## Agent評価結果

| Input                                     | Package                                                  | PASS | FAIL |                         assertion | 内容                                                                               |
| ----------------------------------------- | -------------------------------------------------------- | ---: | ---: | --------------------------------: | ---------------------------------------------------------------------------------- |
| `TR-OUT-005`                              | baseline                                                 |  1/2 |  1/2 |      FAIL時は`TR-D007`, `TR-D013` | password reset要求自体は妥当。1回で扱い表に`該当なし / - / -`を生成                |
| `TR-OUT-005`                              | current candidate / header-only等                        |  2/2 |  0/2 |                             17/17 | ただし扱い表placeholderは残ったままでもPASSした。header-only指示の因果証拠ではない |
| `TR-OUT-006` no source items              | baseline / disposition candidate                         |  2/2 |  0/2 |                             18/18 | 仕様を補わず、要求なし・未解決として扱うケースで回帰なし                           |
| `TR-OUT-007` risk only, no Authority / AC | baseline                                                 |  1/2 |  1/2 |                 FAIL時は`TR-D013` | riskだけから製品挙動を作らないが、1回で未知ID dispositionを生成                    |
| `TR-OUT-007` risk only, no Authority / AC | disposition candidate                                    |  2/2 |  0/2 |                             18/18 | 未確定のretry挙動を正規仕様へ昇格せず処理                                          |
| `TR-OUT-009` normal Authority + Risk      | baseline / disposition candidate / header-only candidate |  2/2 |  0/2 |                             17/17 | 正常に要求化できる入力で隣接回帰なし                                               |
| `TR-OUT-010`                              | baseline                                                 |  0/2 |  2/2 |     各15/17、`TR-D007`, `TR-D013` | account deactivationの要求は妥当。両方で架空disposition rowを生成                  |
| `TR-OUT-010`                              | isolated disposition-only candidate                      |  2/2 |  0/2 |                           各17/17 | baselineとの差は扱い表のtemplate patchのみ。両方で空のdisposition表を維持          |
| `TR-OUT-011`                              | baseline                                                 |  2/2 |  0/2 |                           各19/19 | 仕様不足を要求へ変換せず、実在するSPEC/RISKを`ブロック中`として保持                |
| `TR-OUT-011`                              | isolated disposition-only candidate                      |  2/2 |  0/2 |                           各19/19 | 正当な実在disposition行とblocked判断に回帰なし                                     |
| `TR-OUT-012` held-out                     | baseline                                                 |  1/2 |  1/2 | FAILは15/17、`TR-D007`, `TR-D013` | 初回は通過、2回目で`該当なし / - / -`を生成                                        |
| `TR-OUT-012` held-out                     | isolated disposition-only candidate                      |  2/2 |  0/2 |                           各17/17 | 両方でdisposition表をheader-onlyにし、上流項目を2要求へ接続                        |

`TR-OUT-012`のcandidate成果物は、権限確認とworkspace所属確認を別々の検証責務として`TR-001/002`へ分離し、両方を`SPEC-830`、高リスク`RISK-830`へ追跡しました。具体的なexport形式、保持期間、UI挙動は追加していません。4つのheld-out attemptは、Agent側と親側でのSkill-local runtime evidence verifierがいずれも`valid=true`となり、deterministic runtime fingerprintは配布packageの`runtime_contract.py`と一致しました。

baselineは同じ入力で出力が揺れましたが、失敗は既存`TR-OUT-005`、別入力`TR-OUT-010`、生成前固定の`TR-OUT-012`で同じ2 assertionに再現しています。扱い表だけを修正したcandidateは`TR-OUT-010`と`TR-OUT-012`の4 attemptすべてを通し、`TR-OUT-011`の実在disposition/blocked表現も維持しました。したがって、観測した不具合の修正効果は候補内で再現しています。ただし、試行数は小さく、これを全Skill・全入力に対する一般的な成功率として解釈しません。

別の揺れとして、`TR-OUT-008`では`SPEC-772 (rev-2)`をstable ID欄へ含めた出力がbaselineで1/2回発生し、`TR-D013`, `TR-D009`, `TR-D015`がFAILしました。header-only candidateでも同じ問題が1/2回あり、ID欄とrevision欄を分離する別candidateでは同じケースが2/2 PASSでした。ただし、このcandidateは既に改善作業で使ったケース上の結果であり、未使用入力による確認がありません。今回のdisposition-template改善とは別にし、Skill欠陥が確定したとは扱いません。

## 評価コードの再利用

未登録のheld-out単一ケースを既存graderへ接続するため、`deterministic/run.py`に`--expected-json`を追加しました。入力・expectedを生成前に固定し、生成完了後にだけEvaluatorがexpected JSONを読み込み、通常のSkill validatorで採点します。`--skill all`との併用、読めない/不正JSON、非object JSONは拒否します。`test-requirement-design` validatorには、fixtureが要求なしを明示した場合に要求行がないことを確認する`TR-D019`を追加しました。対応する肯定・否定テストを追加しました。

この開発手順は、対象Skill packageとprivate expectedを指定することで他Skillにも適用できます。物理的な情報隔離や正式Agent runnerの代替にはならず、Agent実行自体をCLIで自動化する変更でもありません。Agent-visible / evaluator-privateの実効read-denialが必要な正式受入は未成立のままです。

## 残る検証上の注意

- あるattemptでは自由記述scopeから`SCOPE-001`をMachine Runtime inputへ生成し、別attemptではscope参照を空にしました。runtime verifierはその入力と成果物内の整合を確認しますが、自由記述から生成したscope IDの外部的な正当性は今回のexpectedでは検査していません。今回のdisposition修正の効果とは切り離し、scope IDの出所を確認できる契約が必要かは別課題として残します。
- サブエージェントは同一workspace権限であり、expected/graderの物理的read-denial、完全なtool履歴、provider build、CLI versionは確認できていません。評価結果は独立性を証明するものではありません。
- 1つのcandidate artifactは保存時にMachine Runtime blockを欠きました。deterministic assertionの結果だけでは完全なSkill contract successとせず、比較対象から除外しました。
- evaluator情報を含むpackage、割当外のpath列挙、入力を読めなかったattemptなどは比較から除外し、理由をGit管理外の`evaluator-private/excluded-attempts.json`に残しています。
- Judge評価、正式`codex exec`、正式runner、候補Skillの採用は行っていません。launcherのfail-closedは変更していません。

## 検証

- `python -m unittest tests.skills.evals.deterministic.test_false_pass_regressions -v`: 59 tests passed
- `python -m unittest scripts.skills.evals.deterministic.tests.test_markdown_parser -v`: 7 tests passed
- `python -m unittest discover -s scripts/skills/evals/deterministic/tests -p 'test_*.py' -v`: 20 tests passed
- `compileall`: 対象deterministic runner、Skill validator、テストで成功
- deterministic suiteは制限sandboxでは4件のSQLite testが`/tmp/.git`祖先検査、1件がlocalhost bind `EPERM`でblockedしました。通常WSL2環境で`TMPDIR=/var/tmp`を使った再実行は357/357 passed
- Ruffはローカル環境に実行binaryがなく未実施。repositoryのpinned Ruffを実行する`format_tracked.py check`も同じ理由で停止
- dprint checkと`git diff --check`は成功。最終GitHub CI状態はPR本文と最終報告に記録します

生Agent成果物、grader JSON、expected、runtime request/result、attempt別hashは、Git管理外の`.agent-eval-runs/pr17-tr-causal-20261031-r1/`に保存しています。この報告書には正解JSONやraw成果物を含めていません。
