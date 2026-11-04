# PR #17：評価基準・attempt記録・Skill評価の継続結果

## 判定

誤判定とrun recordのread-modify-write競合を修正し、再発防止テストで確認した。実Agentの新規attemptは34件を準備し、23件の成果物を保存した。21件にgrade recordがあり、11件は生成前停止、2件は`needs_review`で採点していない。過去の30 attemptと合わせたinventoryは64件である。`needs_review`、生成前停止、品質FAILは集計から除外していない。

Skill全体の改善実証は0件、Skill本体へ反映した変更も0件。`test-case-design / TC-OUT-001`のcandidateは修正対象で2/2 PASSとなったが、独立入力のcandidateは1/2 PASS・1/2 FAILである。`coverage-analysis / COV-OUT-001`は修正済みEvaluatorでcandidate 2/2 PASS、baselineは1/2 PASSであり、baselineの失敗が再現安定していない。いずれも正式採用せず、隔離patchを保持した。

要求Agent設定は全attemptで`gpt-6-luna / max / fork_turns=none`。実効model/build、Skill使用状況、共有workspaceからEvaluator-only情報への物理的読取拒否は未検証である。本評価は開発用subagent handoffで、正式な独立評価ではない。

raw evidenceの正本はGit管理外の[証拠索引](../../.agent-eval-runs/pr17-evaluation-integrity-concurrency-20261105-01/evidence-index.md)と、同索引が示す各attempt rootにある。索引SHA-256: `d71069618d2597484ea72558cfa45c23d4c4e9e5ee74111f215aa5151bec42b4`。生成物の内容、grader、request、manifestは変更していない。

## 1. COV-D003の誤判定

旧`COV-D003`は行の`状態`、`カバレッジ`、`扱い`に加え自由記述の`根拠 / ギャップ`も連結し、文字列に`ブロック中`が含まれるかで判定していた。そのため、`ブロック中ではない`という否定や説明文もblockedとして誤検出した。

`_has_explicit_blocked_status()`へ判定を分離した。正規状態列が厳密に`ブロック中`の場合、または`下流ID / 扱い`のDispositionが明示的に`ブロック中`の場合だけをblockedとする。自由記述の一部一致では状態を変えない。カバレッジの他のgap分類は変更していない。

回帰テスト`test_coverage_d003_uses_structured_dispositions_not_prose`は、否定文と説明文を通し、状態列・下流Dispositionの明示blockedを検出する。

今回の全runでcaptureされた23件の成果物hashをrecordと照合し、23/23一致を確認した。同じEvaluator revision `173aeddb831aff2b44d98e2f17918edbe4f6c89e`でCOV比較を再採点した結果:

| 比較          |                                         Baseline |                            Candidate |                                                                                                                           独立回帰 |
| ------------- | -----------------------------------------------: | -----------------------------------: | ---------------------------------------------------------------------------------------------------------------------------------: |
| `COV-OUT-001` | 1/2 PASS、1/2 FAIL（FAILはruntime evidence欠落） | 2/2 PASS、runtime verifier 2/2 valid | patch作成Agentには開示しなかった`COV-OUT-002`でbaseline 2/2、candidate 2/2 PASS。過去の利用履歴全体でglobally unseenとは主張しない |

修正済みEvaluatorでは旧candidateの`COV-D003`誤FAILは解消した。これはEvaluator修正でありSkill改善ではない。Candidateのruntime templateは必要な3 blockを2/2出力したがbaselineは1/2だけ欠落し、既存Skillの実行ばらつきを安定した欠陥とは確定できない。独立回帰で新しい失敗は観測しなかったが、比較器の`improvement_demonstrated=false`を維持し、Skill品質改善を主張しない。隔離patch SHA-256: `7da356f94bbe5a291723176d844069c4e5ee5f2adbb870d720aaee20d4949bab`。

## 2. TCN-OUT-002の入力契約

旧入力の「全有効遷移をCoverage Itemへ閉じる」は、上流Authority本文がなくても有効遷移を確定してactive Coverage Itemを作るよう読めた。一方expectedは、遷移・BVA候補を`ブロック中` dispositionで保持することを要求していた。

`case-002/input.md`は、`SPEC-001`がIDだけで本文・revision・currentnessを含まないことを明示し、遷移と境界値を入力候補として保持しつつ、current Authorityで確認できない候補を有効な製品仕様へ昇格しない業務制約へ改めた。expectedは変更していない。入力SHA-256は`332516482233b1aedec2f5da91571fc146efe06970c736cee39ea6d5d14ff724`、expected SHA-256は`2a4937a89965510b990323d132df6b8fb2543cef76a637477d8a1da6285f92ec`。

同じ新入力のbaseline成果物2件を旧Evaluatorでは各30/32（`TCN-D016/D017` FAIL）、Evaluator `645e3a2ae9baef20d8d2f4b788e7b241a9ea44b4`では各32/32 PASS、runtime evidence verifiedと再採点した。更新したvalidatorは、runtimeがtargetをmaterializeしなかったcurrent unresolved候補も入力由来の安定ID・候補Disposition・根拠で正しく評価する。これは入力・Evaluatorの整合修正でありSkill改善ではない。出力hashは維持され、expectedの変更はない。新しいcandidateを作る根拠となるSkill欠陥は確認していない。

## 3. subagent_evalの並行更新

`subagent_eval.py`はcapture、host-request、seal、grade、失敗記録などで共通`result.json`を読み、変更してからatomic replaceしていた。replace単体はatomicでも、read-modify-write全体は競合し、別attemptの更新を失い得る。

run root単位のprivate lockで全transactionを直列化した。POSIXでは`flock`、Windowsでは`msvcrt.locking`を使い、symlink component、非regular/hardlink lock、広すぎる権限、lock取得・解放・保存エラーをfail-closedに扱う。prepareは新規rootを作る初期化操作であり、既存共有recordの更新とは分けている。

追加した複数process回帰には、別attemptの同時seal、同一attemptへの競合seal、capture/seal race、二重gradeが含まれる。`test_concurrent_seals_preserve_both_attempts_and_run_summary`等を含む`test_subagent_eval` suiteを実行し、両attemptの更新保持と二重処理の拒否を確認した。

TR-OUT-003の今回の2件目は有効gradeで`RT-D016` FAILし、runtime evidence 3 blockが欠落した。1件目はraw outputのcapture後、ホスト側が誤った`artifact_attempt_id`を指定してsealし、`needs_review`となった。lock競合による更新消失ではなく、手順上のattempt ID誤りであり、recordを手編集して修復していない。別のunsealed diagnostic runは20/20 PASSだったがrun recordに結び付かないため、評価結果として数えない。2件の結果が一貫しないためSkill欠陥には帰属せず、修正候補を作っていない。

## 4. Agent起動pathと成果物保存

`host-request`はabsolute workdir、task、Skill package、submission path、attempt IDを提示し、最初にそのpathで確認するよう要求する。submission fileは起動前に存在しないのが契約なので、ファイルの事前存在ではなく親directoryを確認する文言に修正した。既存host-request testを更新した。

今回の34 attempt中11件は`not_started`で、品質gradeに数えていない。根拠のある起動障害には、package全体ではなく2ファイルだけを読むという親host指示の誤解釈、初回TCD runでsubagent toolへ渡したcwdの余分な空白、手動seal時のattempt ID取り違えがあった。前二者はagent launch前停止で、元記録を保持した。最終的なcandidate runではabsolute path確認後、2/2出力を取得した。PythonからAgentを起動するAPIは追加していない。

## 5. test-case-design候補の再比較

`TC-OUT-001`の固定入力fingerprintは`sha256:bc819c56c637e1ea19f86558e296ba6b984120380a51c94b7d80e21c047d287e`。入力はIDのみで仕様・CI canonical contentがなく、実行可能ケースを作らずblockedとするのは正しい。

Baselineは2/2で`RT-D016` FAILし、runtime Input/Result/Entitiesを欠いた。candidateは既知IDのみのdirect requestを`case_structure`へ渡し、実際に得た`invalid_input / blocked`結果と空Entity集合を添付した。canonical CI content不足を理由にgeneratorはactive caseを作らず、candidateのruntime verifierは2/2 valid。修正対象ではbaseline 0/2、candidate 2/2 PASS、`RT-D016/017/018`を含むassertionsを通過した。比較状態は`comparable_development_handoff`、条件mismatchなし、`improvement_demonstrated=false`。

この結果はruntime evidenceの欠落軽減を示す開発用観測だが、runtime verifierの`valid=true`は入力内容の充足、生成成功、workflow完了を意味しない。また、実Agent tool traceがなく、request/resultの実際の生成履歴は`unverified`である。

候補固定後の`TC-OUT-002`独立入力は、globalに未使用ではない。2件ずつを新規評価し、baseline 0/2 PASS、candidate 1/2 PASS・1/2 FAIL（FAILは`RT-D016`欠落）となった。比較は条件上comparableだったが、candidateで不安定な失敗が残り、独立回帰合格とは判定しない。candidate patch SHA-256: `c4f8b560b8dc9b652d0f1c22f4b51ea0c1ca0662dc5ad4cf551d3891a8649243`。正式採用していない。

## 6. attempt数と分類

| 範囲         | 準備attempt | 成果物capture |    初回grade PASS / FAIL |           needs_review | not_started |
| ------------ | ----------: | ------------: | -----------------------: | ---------------------: | ----------: |
| 前回報告まで |          30 |            22 |             既存報告参照 |     2件に有効gradeなし |           8 |
| 今回の追加   |          34 |            23 |                  11 / 10 |                      2 |          11 |
| 累計         |          64 |            45 | 既存報告と今回記録を合算 | 合計4件に有効gradeなし |          19 |

TCN-OUT-002の同じ2 raw outputに対する新Evaluatorの再採点は別ファイルで保管し、attempt数へ重複計上していない。今回のPASS 11 / FAIL 10はrun record上のgradeであり、COV候補比較、TCNの旧Evaluator gradeなど複数の独立案件を含む。全数値は[証拠索引](../../.agent-eval-runs/pr17-evaluation-integrity-concurrency-20261105-01/evidence-index.md)からattempt ID・出力hashへ対応する。

## 7. 検証

- Focused agent / deterministic regression: 99 passed.
- Deterministic evaluation suite: 28 passed.
- Agent evaluation suite: 276 passed, 6 skipped.
- Runtime suite: 388 passed.
- `compileall`: passed.
- Ruff 0.16.8: CI initially found formatter differences in five changed Python files. Applied the CI-indicated formatting with the existing cached Ruff binary; `ruff format --check` and `ruff check` then passed.
- `dprint check`: passed after the report was formatted.
- `git diff --check` / commit checks: passed.
- Latest focused rerun after formatting: 49 passed; full Agent evaluation suite: 276 passed, 6 skipped. The first Code Quality run failed only at Ruff format check; a new commit below will trigger the corrected CI run.

## 8. 未達と次の判断

- Skill本体へ反映した候補: 0。
- 修正対象全体で改善を観測した候補: 0件（TCDは対象caseで2/2 PASSだが独立caseで1/2 FAILし、COV baselineは1/2 PASSで基線不安定）。
- 独立回帰まで合格した候補: 0。
- 正式runner、独立Judge、実効model/build、Evaluator情報の物理的読取拒否: 未検証。
- TCN-OUT-002はbaselineのみを入力整合修正後に再採点し、Skill candidate比較は実施していない。
- TR-OUT-003は1件FAIL、1件が手順起因needs_reviewで、Skill起因の再現性は未確認。

PR branchの実装変更は`173aeddb831aff2b44d98e2f17918edbe4f6c89e`および`645e3a2ae9baef20d8d2f4b788e7b241a9ea44b4`に記録した。報告書は`e87716c6d25d13b01be24442773308bf388e292e`でpush済み。formatter修正を追加commit・pushし、CI結果をPR本文へ反映する。正式評価やSkillの改善成立とは扱わない。
