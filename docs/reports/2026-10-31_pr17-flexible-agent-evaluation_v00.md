# PR #17 実Agent評価方式の再検討・Skill比較

## 結論

開発時のSkill比較には、現在のCodexセッションから起動する逐次サブエージェントと既存deterministic graderを使う経路が成立した。既存Codex CLIの認証storeを触らずに、`test-requirement-design`のbaseline / candidateを各2回、新しい入力2件で評価した。candidateでは、修正対象に使っていない入力で必須の空テーブルを保持し、baselineで再現した`TR-D011`違反を2回とも解消した。

これは同じAgent環境内での実動作・品質比較であり、物理的なEvaluator情報隔離、独立Judge、正式runnerの受入を証明しない。現在のSkill変更を正式採用したり、PR #17全体の品質改善を独立検証済みと扱ったりしない。

## 選択した実行方式

| 方式 | 確認結果 | 判断 |
|---|---|---|
| A. `codex exec` | 固定Linux CLIの`--help`で`--json`、`--output-schema`、`--model`、`--config`、`--sandbox`、`--output-last-message`を確認。live起動はしていない。現行launcherはrefresh永続化とprocess間競合が未解決の間、実モデル起動をfail-closedする。 | 通常WSL2で利用可能な代替でも、この共有認証storeの条件下では使わない。 |
| B. 既存Codexセッションのサブエージェント | 既存セッションから8回逐次起動。各呼び出しで`gpt-6-luna`、`max`、`fork_turns="none"`を明示し、Skill・入力・出力先をattempt別に用意した。 | 開発用比較に採用。expected / graderはAgent用directoryへ配置しなかった。 |
| C. 専用runner | launcherのfail-closedを維持。 | 正式評価の既存経路として維持し、この比較のためには起動しない。 |

固定Linux Codex CLIは`0.163.0`、binary SHA-256は`399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`。CLI versionとhelpのみ照会し、`codex exec`、login/logout、認証fileの読取・コピー、固定CLIからのモデルAPI呼出しは行っていない。実際のAgent生成にはplatform-managedなサブエージェントモデル呼出しを8回使用した。サブエージェントの実効モデルとreasoning設定は起動toolの明示引数で確認した。サブエージェント側のCodex CLI version、provider build IDは取得できない。

Agentにはattempt専用のSkill packageと入力だけを指示した。サブエージェントは親workspaceの権限を共有するため、expected・graderへの物理的read-denialは成立していない。読み取り履歴はtool側の完全な監査記録ではなく、一部Agentの自己申告である。少なくとも1つのbaseline AgentがSkill package内の不要な`runtime_v1_cutover.py`を読んだ。Evaluator正解データを読んだ証拠は得ていないが、未読の証明にもならない。

## 実行範囲と比較条件

- 開始HEAD / candidate Skill revision: `6ffe1a39b34c52f1d8368edbfd0b17421f77b6cb`
- baseline Skill指示revision: `b9aa550df8f4fe7e0a84b77fe534ed1a8426227d`
- Evaluator実装revision: `6ffe1a39b34c52f1d8368edbfd0b17421f77b6cb`。追加2 fixtureは評価入力・期待値を全Agent生成後にworking treeへ追加し、実験時のprivate期待値と照合した。
- 対象Skill: `test-requirement-design`
- Agent: `gpt-6-luna` / reasoning `max` / 新規context相当の`fork_turns="none"`。8回を逐次実行。
- 比較条件: input、モデル指定、推論設定、評価実装、実行依頼を固定。baseline / candidateで変えたものはSkill packageの指示ファイルrevision。
- 固定Codex CLIからのlive実行、Judge実行、provider buildの照合は未実施。

| Eval ID | 目的 | 入力から固定した契約 |
|---|---|---|
| `TR-OUT-004` / `priority-provisional-001` | checkout価格再検証と暫定リスク評価 | `SPEC-901`と`RISK-901`を接続。priority欄は`高`のみ、暫定評価の注記は説明欄へ置く。 |
| `TR-OUT-005` / `priority-heldout-002` | reset tokenの再利用防止 | `SPEC-902`と`RISK-902`を接続。priority欄は`中`のみ。token lifetime、UI、rate limitを作らない。空の「テスト要求を作らない上流項目」表も正規headerで維持する。 |

2入力と期待値は生成前にevaluator-privateへ固定し、baseline/candidate Agentへ渡していない。tracked inputはAgentが読んだ入力とbyte-identical、tracked expectedはprivate期待値とSHA-256一致を確認した。Agent-visible directoryにはreference、rubric、graderを置かなかったが、同じworkspaceからの読取は禁止できていない。

## 実Agent生成とgrader結果

| Eval ID | baseline | candidate | 主な確認 |
|---|---:|---:|---|
| `TR-OUT-004` | 2/2 PASS（各17/17） | 2/2 PASS（各17/17） | 両revisionとも`高`を機械可読priorityに使用。candidateでは暫定性を備考に分離。baselineの同じ挙動も正しく、priority enum改善はこの入力で再現しなかった。 |
| `TR-OUT-005` | 0/2 PASS。各出力で`TR-D011` FAIL（16/17） | 2/2 PASS（各17/17） | baselineは空の上流項目表を prose で代替。candidateはheader-only tableを出力。両revisionとも仕様根拠・リスクを接続し、token lifetime等の未指定挙動を追加しなかった。 |

`TR-OUT-005`の差は、candidate `SKILL.md`で上流項目の扱いを別表へ記録する指示が加わり、baselineにはその明示がなかった差と一致する。baselineでは表自体が欠落し、candidateは空集合のheader-only表を2/2で保持した。したがって、この出力契約違反はSkill指示の具体的な不足に対応する。graderは必要なheaderの存在を確認し、期待値を緩和していない。candidate出力には先頭空列を含む表記ゆれがあったが、required headers、Markdown table parse、Machine Runtimeと全assertionは有効だった。現状の正規契約は追加列を明示的に禁止していないため、別のgrader条件を創作して修正していない。

意味内容は入力Authorityから要求責務への追跡、risk priorityの保持、未指定値の非創作を各成果物で確認した。これは同じ親評価者による内容確認で、独立Judgeまたは人間承認ではない。Runtime gateを含むdeterministic grader assertionは各17件すべてPASSした。

## 既存46成果物の再採点

現行graderで保存済み46成果物を変更せず再採点したところ、41 PASS / 5 FAIL / 0例外だった。新しい2ケースのcandidate replicate 1を加えた48件の選択結果は43 PASS / 5 FAIL / 0例外で、欠落出力はなかった。

| Skill / Eval ID | FAIL assertion | 分類 |
|---|---|---|
| `coverage-analysis / COV-OUT-001`, `COV-OUT-002` | `RUNTIME-PAIR-…-RUNTIME-IMPLEMENTATION` | 保存済みevidenceのruntime implementation fingerprintが現行sourceと不一致。現行Skillの意味品質FAILとは判断しない。 |
| `test-analysis / RISK-OUT-001`, `RISK-OUT-002` | `RISK-D018`および3つのruntime implementation fingerprint assertion | 旧fingerprintのためfixture実行契約とgateの証拠が現行sourceで再検証できない。入力にcurrent Authority Entityがないため、失敗をSkill欠陥と断定しない。 |
| `test-execution / TEX-OUT-002` | `TEX-D005`, `TEX-D012` | 再採点対象artifactでinput identityと未実行集計が不整合。別の新規Agent artifactは15/15 PASSだった。 |

TEX結果の異同を確認した。保存batch内のartifact SHA-256 `a86ae7cc…`は13/15で、`TEX-D005`と`TEX-D012`がFAILした。一方、別attemptの新規Agent artifact SHA-256 `861bc5c0…`はgraderの15/15 PASS記録と一致した。別attemptのPASSを保存batch artifactのPASSへ読み替えていない。

## 変更と検証

- 新しいdeterministic fixtureを追加: `TR-OUT-004` / `TR-OUT-005`。期待値は出力形式・上流参照・要求IDを検証し、正答文の暗記やeval専用Skill分岐を要求しない。
- この作業ではSkill本体、grader、rubric、Reference、Judge fixture、target productを変更していない。現在PR revisionに含まれていた`test-requirement-design`のtemplate / guidance差分をbaselineと比較した。
- 48件再採点: 43 PASS / 5 FAIL / 0例外。新規2ケースはそれぞれ17/17 PASS。
- `compileall`、deterministic runner unit 19件、repository deterministic suite 356件、runtime suite 380件はPASS。repository deterministic suiteはsandbox内で一度4 failure / 1 errorとなったが、`/tmp/.git`によるtemp state拒否とlocalhost bindの`EPERM`を確認した後、既存手順どおり通常WSL2・`TMPDIR=/var/tmp`で同じsuiteを実行し356件すべてPASSした。
- formatter script test 10件、patch-whitespace test 3件、JSON parse、選択した変更fileのtrailing whitespace、`git diff --check`はPASS。
- `python scripts/format_tracked.py check`はRuff実行fileが環境にないため停止し、dprint検査まで到達しなかった。formatter/lintはGitHub Actionsで再確認する。
- 新規比較結果、Agent実行条件、artifact / grader SHA-256を含むraw recordはGit管理外の`.agent-eval-runs/pr17-flexible-agent-eval-20261031-fmojcd39/`に保存した。秘密・認証file・tokenは保存していない。
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
