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
- Latest focused rerun after formatting: 49 passed; full Agent evaluation suite: 276 passed, 6 skipped. The first Code Quality run failed only at Ruff format check. Commit `a64ee084d9fe69e7c031ef3ff21fdd676e492fcd` corrected the format, and all five GitHub Actions workflows succeeded for that commit.

## 8. 未達と次の判断

- Skill本体へ反映した候補: 0。
- 修正対象全体で改善を観測した候補: 0件（TCDは対象caseで2/2 PASSだが独立caseで1/2 FAILし、COV baselineは1/2 PASSで基線不安定）。
- 独立回帰まで合格した候補: 0。
- 正式runner、独立Judge、実効model/build、Evaluator情報の物理的読取拒否: 未検証。
- TCN-OUT-002はbaselineのみを入力整合修正後に再採点し、Skill candidate比較は実施していない。
- TR-OUT-003は1件FAIL、1件が手順起因needs_reviewで、Skill起因の再現性は未確認。

PR branchには`173aeddb831aff2b44d98e2f17918edbe4f6c89e`、`645e3a2ae9baef20d8d2f4b788e7b241a9ea44b4`、報告書の`e87716c6d25d13b01be24442773308bf388e292e`、formatter修正の`a64ee084d9fe69e7c031ef3ff21fdd676e492fcd`、CI結果の追記`f60fdbe3e1bf3343f63eb13bfaf3cf7f1ed5d1a7`を通常pushした。a64とf60のGitHub Actionsは各5件すべて成功。正式評価やSkillの改善成立とは扱わない。

## 9. 継続確認（2026-11-05）

この追記は保存済みrunを再分類したもので、新しいAgent attemptやgradeを作っていない。新規attemptは0件、累計inventoryは64件のまま。raw output、grade、request、manifest、candidate patchは変更していない。

### `not_started` 11件の分類

| 件数 | 観測された原因                                                                                                         | 分類                             |
| ---: | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
|    1 | 親hostの指示がpackage全体ではなく2ファイルだけに制限し、taskを読む前に停止                                             | host起動指示の逸脱               |
|    3 | prepared absolute working directoryを使わずpreflight                                                                   | host path / 手順誤り             |
|    4 | handoff側が存在しない`skill_path` / `skill_package` keyを期待し、実際の`skill_entrypoint` / launch message契約と不一致 | host側のrequest consumer契約誤り |
|    1 | `CreateProcess`に余分な空白を含むcwdを渡した                                                                           | host起動引数誤り                 |
|    2 | attemptごとの説明記録がなく、原因を特定できない                                                                        | 証拠不足                         |

意図的に実行しなかったattemptや実行環境機能の拒否を示す根拠はない。既知9件はhost起動・preflight手順側で、Skill品質FAILではない。残り2件は未知のまま保持する。過去のschema 1 handoffには理由がないものがあり、raw記録を後から変更しない。

### Skill候補の再確認

- `coverage-analysis / COV-OUT-001`: 修正Evaluator下でbaselineは1/2 PASS・1/2 FAIL、candidateは2/2 PASS。失敗は`RT-D016`の`Machine Entities` block欠落。candidate patchはoutput templateへ、runtime unitごとの3 blockを要求し、entity 0件時は実結果の空配列を表示する指示のみを追加する。独立`COV-OUT-002`はbaseline/candidateとも2/2 PASSで新規失敗なし。patch SHA-256は`7da356f94bbe5a291723176d844069c4e5ee5f2adbb870d720aaee20d4949bab`。一方、baseline欠落は1/2だけであり、baseline自体が不安定。また実Agentのhelper実行tool traceがないため、Skill指示が欠落の原因と完全には立証されていない。候補は採用判断用に保持するが、Skill品質改善成立とはしない。
- `test-case-design / TC-OUT-001/002`: 保存済み比較では対象入力でcandidate 2/2 PASSだが、独立入力ではcandidate 1/2 PASS・1/2 FAIL。失敗attemptにはruntime Input / Result / Entitiesが一式なく、raw generator resultもhost tool traceもない。成功MarkdownのJSONだけではhelper実行を立証できず、「正しいraw resultの転記漏れ」という仮説も支持されない。原因はAgent omission・実行の揺れ・tool evidence不足から絞れないためcandidate patch SHA-256 `c4f8b560b8dc9b652d0f1c22f4b51ea0c1ca0662dc5ad4cf551d3891a8649243`をレビュー待ちで維持し、再修正しない。
- `test-condition-design / TCN-OUT-002`: inputはSPEC-001のIDしかなく、本文・revision・currentnessが提供されないことを明示する。現行Skillはcurrent Authorityがない候補をactive CIへ昇格させない。expectedは維持済みで、再採点は32/32 PASS。これは入力・Evaluator整合の解決でありSkill改善ではない。`TCN-D016/D017`はcandidateのblocked dispositionとactive CI欠如を確認する。`TCN-OUT-001`は実際のPairwise組合せ生成を求める別fixtureだが、過去の実Agent gradingにはFAILがあり、正の意味品質が確認済みという扱いにはしない。既存契約に反する新しいSkill欠陥は今回確認できず、新candidateは作らない。

### Eval Inputで確認できる範囲

`test-case-design`の2入力はどちらも上流IDのみで本文・操作・期待条件がなく、仕様を創作せずblockできるかを主に測る。`test-condition-design`にはPairwise組合せを実際に生成する`TCN-OUT-001`と、Authority欠落を扱う`TCN-OUT-002`がある。`coverage-analysis`の2入力は未接続CIと孤立TRというtraceability gapを検出する。`test-requirement-design`にはblocked入力のほか、内容のある直接設計入力`TR-OUT-004/005`がある。よってcase designの正方向生成・Test Dataと期待結果の意味品質は、現在のdeterministic inputだけでは十分に確認されない。COVのgraph診断、TCNのpairwise positive、TRの直接設計も、それぞれの意味品質全体を保証しない。新規caseは仕様・expectedを独立に確定できる根拠がないため今回は追加しない。

### 評価経路の修正

`subagent_eval.py`のhandoff manifestをschema 2へ更新した。`not_started`、`failed`、`timed_out`のsealは短いhost報告理由を必須にし、manifestとrun recordの双方に保存して一致を検証する。理由はhost申告であり、真因の独立証明ではない。理由なしは`needs_review`で停止する。保存済みschema 1 handoffの検証互換を維持し、既存evidenceは書き換えない。

`host-request`はabsolute `skill_package_root`を返し、launch messageはmanifest検証済みpackage全体（`SKILL.md`、references、scripts、assets）を縮小せず使うよう明記する。workdir、task、entrypoint、submission、attempt IDを同じrequestから使う。これはhostへの指示強化であり、親hostが従うことや物理read denialを証明するものではない。

`improve.py`のAgent起動は自動化されていない。Codex hostが手動で起動し、Pythonはprepare / host-request / capture / seal / gradeを実行し、`compare-handoff`はrun間条件とassertionを比較する。原因分析、repairの実行、独立回帰の切替え、採用判断はhost側の明示操作である。存在しないPython agent APIは追加していない。

検証結果：`test_subagent_eval` 39件、agent evaluation suite 280件（6 skip）、deterministic suite 28件、semantic suite 27件、関連runtime tests 40件、compileall、Ruff 0.16.8、dprint、`scripts/format_tracked.py check`（250 files）すべて成功。失敗した最初のformat checkは適用前のRuff整形差分だけで、整形後は成功した。新規実Agent評価は行っていない。

### 現時点の判定

- Skill candidateの正式採用: 0件。
- Skill全体の改善実証: 0件。
- 評価基盤で今回修正した問題: 非完了attempt理由の欠落と、host requestにpackage rootが明示されない点。
- run-root並行更新lock、capture/seal/grade競合対策は前HEADですでに存在し、複数processテストで保持を確認したため再実装していない。
- 実効model/build、tool trace、Evaluator-only情報の物理read denial、正式runner、Judgeは未検証。
