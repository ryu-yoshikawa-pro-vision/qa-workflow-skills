# PR #17 実Agent評価方式の再検討・Skill比較

## 結論

開発時のSkill比較には、現在のCodexセッションから起動する逐次サブエージェントと既存deterministic graderを使う経路が成立した。既存Codex CLIの認証storeを触らずに、`test-requirement-design`のbaseline / candidateを各2回、新しい入力2件で比較した。最初の8生成後にCIがeval datasetの入力参照契約違反を検出したため、両入力へ実際の`assets/output-template.md` pathを明記して固定し直し、8生成を再実行した。最終の固定入力ではcandidateが両ケースとも2/2 PASS、baselineは`TR-OUT-004`が2/2、`TR-OUT-005`が1/2だった。これは限定された追加比較の結果であり、PR #17全体の品質改善を独立検証済みとは扱わない。

これは同じAgent環境内での実動作・品質比較であり、物理的なEvaluator情報隔離、独立Judge、正式runnerの受入を証明しない。現在のSkill変更を正式採用したり、PR #17全体の品質改善を独立検証済みと扱ったりしない。

## 選択した実行方式

| 方式                                     | 確認結果                                                                                                                                                                                                                               | 判断                                                                    |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| A. `codex exec`                          | 固定Linux CLIの`--help`で`--json`、`--output-schema`、`--model`、`--config`、`--sandbox`、`--output-last-message`を確認。live起動はしていない。現行launcherはrefresh永続化とprocess間競合が未解決の間、実モデル起動をfail-closedする。 | 通常WSL2で利用可能な代替でも、この共有認証storeの条件下では使わない。   |
| B. 既存Codexセッションのサブエージェント | 最初の8回とCI修正後の8回を逐次起動。最終比較の各呼び出しで`gpt-6-luna`、`max`、`fork_turns="none"`を明示し、Skill・入力・出力先をattempt別に用意した。                                                                                 | 開発用比較に採用。expected / graderはAgent用directoryへ配置しなかった。 |
| C. 専用runner                            | launcherのfail-closedを維持。                                                                                                                                                                                                          | 正式評価の既存経路として維持し、この比較のためには起動しない。          |

固定Linux Codex CLIは`0.163.0`、binary SHA-256は`399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`。CLI versionとhelpのみ照会し、`codex exec`、login/logout、認証fileの読取・コピー、固定CLIからのモデルAPI呼出しは行っていない。サブエージェント生成は2バッチ計16回で、最終比較の8回はplatform-managedなmodel呼出しを使用した。サブエージェントの実効モデルとreasoning設定は起動toolの明示引数で確認した。サブエージェント側のCodex CLI version、provider build IDは取得できない。

Agentにはattempt専用のSkill packageと入力だけを指示した。サブエージェントは親workspaceの権限を共有するため、expected・graderへの物理的read-denialは成立していない。読み取り履歴はtool側の完全な監査記録ではなく、一部Agentの自己申告である。少なくとも1つのbaseline AgentがSkill package内の不要な`runtime_v1_cutover.py`を読んだ。Evaluator正解データを読んだ証拠は得ていないが、未読の証明にもならない。

## 実行範囲と比較条件

- 開始HEAD / candidate Skill revision: `6ffe1a39b34c52f1d8368edbfd0b17421f77b6cb`
- baseline Skill指示revision: `b9aa550df8f4fe7e0a84b77fe534ed1a8426227d`
- 最終比較のgrader / expected revision: `83787584cd39f26a0be952386384cc6b8bc70b8f`。deterministic grader実装は`6ffe1a39b34c52f1d8368edbfd0b17421f77b6cb`から不変。CI修正後の2入力は生成前にprivateへ固定した作業tree内容で、hashを全8 attemptで照合した。expectedとeval manifestは837 revisionの内容から変更していない。
- 対象Skill: `test-requirement-design`
- Agent: `gpt-6-luna` / reasoning `max` / 新規context相当の`fork_turns="none"`。8回を逐次実行。
- 比較条件: input、モデル指定、推論設定、評価実装、実行依頼を固定。baseline / candidateで変えたものはSkill packageの指示ファイルrevision。
- 固定Codex CLIからのlive実行、Judge実行、provider buildの照合は未実施。

| Eval ID                                   | 目的                               | 入力から固定した契約                                                                                                                                         |
| ----------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TR-OUT-004` / `priority-provisional-001` | checkout価格再検証と暫定リスク評価 | `SPEC-901`と`RISK-901`を接続。priority欄は`高`のみ、暫定評価の注記は説明欄へ置く。                                                                           |
| `TR-OUT-005` / `priority-heldout-002`     | reset tokenの再利用防止            | `SPEC-902`と`RISK-902`を接続。priority欄は`中`のみ。token lifetime、UI、rate limitを作らない。空の「テスト要求を作らない上流項目」表も正規headerで維持する。 |

2入力と期待値は生成前にevaluator-privateへ固定し、baseline/candidate Agentへ渡していない。tracked inputはAgentが読んだ入力とbyte-identical、tracked expectedはprivate期待値とSHA-256一致を確認した。Agent-visible directoryにはreference、rubric、graderを置かなかったが、同じworkspaceからの読取は禁止できていない。

## 実Agent生成とgrader結果

| Eval ID      | baseline                       | candidate           | 主な確認                                                                                                                                                                                                           |
| ------------ | ------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TR-OUT-004` | 2/2 PASS（各17/17）            | 2/2 PASS（各17/17） | 両revisionとも`高`を機械可読priorityに使用。candidateでは暫定性を備考に分離。baselineも同じ挙動で、この入力ではpriority表現の改善差は再現しなかった。                                                              |
| `TR-OUT-005` | 1/2 PASS（1件17/17、1件15/17） | 2/2 PASS（各17/17） | baselineの失敗出力は「該当なし / `-`」行を追加し、`TR-D007`と`TR-D013`がFAIL。もう一方のbaselineとcandidate両件は正規header-only tableでPASS。候補の結果は2/2で安定したが、baselineの失敗は最終入力で1/2に揺れた。 |

`TR-OUT-005`の最終入力は、CIのdataset契約が要求するliteral `output-template.md` pathを含む。CI検出前の最初の8生成ではbaseline 0/2が`TR-D011`でFAIL、candidate 2/2がPASSだったが、この比較入力は正規dataset参照を満たさず、最終比較には採用しない。修正後の固定入力に対して、baseline失敗出力の「該当なし / `-`」は許可された扱いenumに該当せず、そのIDも期待上流集合に存在しないため、`TR-D007` / `TR-D013`のFAILはvalidator契約上妥当である。baselineもう一方のheader-only表とcandidate 2件はPASSした。candidate `SKILL.md`で上流項目を別表へ記録する指示が加わったことと、candidateの2/2結果は整合するが、修正後入力でのbaseline失敗は1/2であり、再現性は限定される。期待値やgraderは変更していない。

意味内容は入力Authorityから要求責務への追跡、risk priorityの保持、未指定値の非創作を各成果物で確認した。これは同じ親評価者による内容確認で、独立Judgeまたは人間承認ではない。`TR-OUT-004` candidate replicate 2では同じ仕様の一般的な再計算責務とカート版不一致時の責務が2行へ分かれ、少し重なる。ただし、正本の別々の節を反映しており、現行の重複禁止契約への違反とは確認できなかった。最終比較の通常deterministic assertionでは7成果物が17/17、baselineの1成果物が15/17だった。

最終比較8成果物の`verify_runtime_evidence`を、各Attemptのbaseline / candidate Skill packageに含まれる同revisionの`runtime_contract.py`で親評価側から再実行した。各Artifactの唯一の`Machine Runtime Input` blockから`input` objectを取得し、full build (`partial_rerun=false`, previous artifactなし)として検証した結果、8/8 `valid=true`、issueなし、期待・実測runtime unitは各1件だった。Machine Entityはartifactごとに1～2件を検出した。これは成果物内に記録されたruntime inputとArtifactの内部整合・source fingerprintを再検証したもので、runtime inputが元のユーザー入力から生成されたことやAgentの未監査file accessを証明するものではない。また、追加2 evalの`expected.json`はruntime契約を宣言していないため、通常graderの17 assertion自体にはruntime assertionが含まれず、このruntime再検証は別記録に保存した。

## 既存46成果物の再採点

現行graderで保存済み46成果物を変更せず再採点したところ、41 PASS / 5 FAIL / 0例外だった。新しい2ケースの修正後inputに対するcandidate replicate 1を加えた48件の最終選択結果は43 PASS / 5 FAIL / 0例外で、欠落出力はなかった。初回inputのcandidate成果物を最終選択から除き、修正後inputの成果物に置き換えた。

| Skill / Eval ID                                  | FAIL assertion                                                     | 分類                                                                                                                                                |
| ------------------------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `coverage-analysis / COV-OUT-001`, `COV-OUT-002` | `RUNTIME-PAIR-…-RUNTIME-IMPLEMENTATION`                            | 保存済みevidenceのruntime implementation fingerprintが現行sourceと不一致。現行Skillの意味品質FAILとは判断しない。                                   |
| `test-analysis / RISK-OUT-001`, `RISK-OUT-002`   | `RISK-D018`および3つのruntime implementation fingerprint assertion | 旧fingerprintのためfixture実行契約とgateの証拠が現行sourceで再検証できない。入力にcurrent Authority Entityがないため、失敗をSkill欠陥と断定しない。 |
| `test-execution / TEX-OUT-002`                   | `TEX-D005`, `TEX-D012`                                             | 再採点対象artifactでinput identityと未実行集計が不整合。別の新規Agent artifactは15/15 PASSだった。                                                  |

TEX結果の異同を確認した。保存batch内のartifact SHA-256 `a86ae7cc…`は13/15で、`TEX-D005`と`TEX-D012`がFAILした。一方、別attemptの新規Agent artifact SHA-256 `861bc5c0…`はgraderの15/15 PASS記録と一致した。別attemptのPASSを保存batch artifactのPASSへ読み替えていない。

## 変更と検証

- 新しいdeterministic fixtureを追加: `TR-OUT-004` / `TR-OUT-005`。期待値は出力形式・上流参照・要求IDを検証し、正答文の暗記やeval専用Skill分岐を要求しない。
- この作業ではSkill本体、grader、rubric、Reference、Judge fixture、target productを変更していない。現在PR revisionに含まれていた`test-requirement-design`のtemplate / guidance差分をbaselineと比較した。
- CI検出: Deterministic Output Evalsが新規inputのliteral `output-template.md`参照を要求し、Code Qualityが報告書と2入力のdprint整形を要求した。期待値を変えずにinputへ`assets/output-template.md`を明記し、3ファイルをdprintでformatしてから最終比較8 attemptを再実行した。初回8 attemptはGit管理外に保持し、最終比較には混ぜていない。
- 修正後のinputで8成果物を新規生成し、各17 assertionで7件PASS / 1件FAIL、grader例外0。`TR-OUT-004`はbaseline / candidateとも2/2 PASS、`TR-OUT-005`はbaseline 1/2、candidate 2/2 PASS。
- 修正後inputのcandidate replicate 1を用いた48件選択再集計: 43 PASS / 5 FAIL / 0例外、欠落0。元46成果物の結果は41 PASS / 5 FAIL / 0例外で不変。
- 最終比較8成果物は、通常のSkill graderと別に、baseline / candidateそれぞれのsource revisionに固定したSkill-local runtime verifierで再検証し、8/8 valid、issue 0だった。
- `compileall`、deterministic runner unit 19件、repository deterministic suite 356件、runtime suite 380件はPASS。repository deterministic suiteはsandbox内で一度4 failure / 1 errorとなったが、`/tmp/.git`によるtemp state拒否とlocalhost bindの`EPERM`を確認した後、既存手順どおり通常WSL2・`TMPDIR=/var/tmp`で同じsuiteを実行し356件すべてPASSした。
- formatter script test 10件、patch-whitespace test 3件、JSON parse、選択した変更fileのtrailing whitespace、`git diff --check`はPASS。
- 最初のCode Quality CIは、dprint未整形の3ファイルで失敗した。最終3ファイルに対するdprint formatを行った。Ruff対象のPython source変更はない。最終CI実行の結果はpush後に確認する。
- 初回比較と修正後比較のraw output、入力・Skill・grader hash、Agent呼び出し条件を別attempt rootへ保存した。初回rootは`.agent-eval-runs/pr17-flexible-agent-eval-20261031-fmojcd39/`、修正後rootは`.agent-eval-runs/pr17-flexible-agent-eval-ci-corrected-20261031-r1/`。秘密・認証file・tokenは保存していない。
- この方式では候補Skillを同じ実験中にAgentが直接修正せず、既存PR revisionをcandidateとして評価した。自動修正・独立Judgeを使った正式改善判定は未実施。

## 実行方式・受入の残課題

今回確認したのは、既存Codex環境でSkillを実行し、既存deterministic evaluatorで同条件比較する開発用経路である。継続時も入力・Skill source・Evaluator・Agent設定をrevisionとhashで固定し、全attemptを保存する。候補変更を隔離する必要がある場合はcandidate Skill packageを生成Agentへ渡す前に固定し、修正用Agentへ独立回帰入力・期待値を公開しない。

次は未達のまま維持する。

- 専用runner経由の実Codex評価: refresh persistenceと非協調process競合の安全条件が未解決。
- 物理的なAgent / Evaluator情報隔離とrevision-bound isolation evidence。
- Judge fixtureの承認および独立Judge評価。
- `qa-training-store`の正式な`--repeat`統合評価。
- `improve.py`による正式な自動分析・許可判定・隔離修正・再評価ループ。
- 今回の比較は一つのSkillに限られ、22 Skill全体の新規Agent比較ではない。

したがって、開発用の比較経路と1件の実質的なdeterministic改善差は確認できたが、PR #17の正式受入と自動Skill改善の全体受入は完了していない。
