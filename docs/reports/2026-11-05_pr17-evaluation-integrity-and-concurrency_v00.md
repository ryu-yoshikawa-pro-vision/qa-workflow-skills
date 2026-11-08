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

## 10. Positive TCN評価の継続（2026-11-05）

固定条件はEvaluator / baseline Skill revision `22299fa635c168d37bb4a801d941891edb386cdb`、`deterministic / TCN-OUT-001`、input fingerprint `sha256:3ad18513c94852b40198c38399e05b244fdb5a223e37b1dc59ce5f8e6a4c93f5`、要求Agent設定 `gpt-6-luna / max / fork_turns=none`。実効model/build、実tool trace、Evaluator-only情報へのread denialは未検証で、開発用handoff評価である。

新規attemptは12件（過去64件と別集計、inventory累計76件）。baselineは10件中8件が`execution error`、2件が`not_started`で、採点可能な成果物は0件。candidate v1は2件中1件をcapture・採点し、1件は成果物pathの誤用による`execution error`。candidate v1のgradeは31 assertion中30 PASS、1 FAILで、`RT-D016`が`Machine Runtime Input`、`Machine Runtime Result`、`Machine Entities`の3 block欠落を検出した。pairwiseの構造・制約・網羅性assertionは通過したが、runtime evidence不足を含む成果物全体はFAILである。

baselineの実行エラー8件は、host launch pathの重複2件、`CreateProcess ENOENT` / 誤ったcwd 3件、pairwise slugの誤指定1件、親runtime inputのpriority欠落とdownstream `upstream_entities` schema不一致1件、起動後にruntime invocationも成果物も報告されなかった1件。候補attempt 2では`host-request.json`が絶対`submission_path`を返していたが、Agentが作業cwd内でrepository相対pathを再構成し`FileNotFoundError`となった。pathを返すhelperの不具合は確認されていない。全失敗理由は各attemptの`host_execution.execution_reason`に記録し、attemptを削除・置換していない。

隔離candidate patch `tcn-runtime-input-clarification.patch`（SHA-256 `dd26a17cf873bd7cb213189ad810312551d6fa5d84ed5b728f65c6ce2ca197fd`）は、runtimeのpriority field、Pairwise slugとgenerator名、上流Machine Entityのmetadata projectionを明確化した。candidate Agentからはruntime call成功の申告があったが、request / result raw dataとtool traceは保存されていないため実行証拠としては未検証。candidateの最終Markdownが既存のSkill-local output/evidence gateに従わなかったため、Skillに原因を帰属できる追加修正候補は作成していない。

`improve.py compare-handoff`はbaseline全attemptにintegrity-checked gradeがないため`not_comparable`を返し、`improvement_demonstrated=false`を維持した。対象比較も成立せず独立回帰は実施していない。COV-OUT-001の保存済みcandidate（baseline 1/2、candidate 2/2。COV-OUT-002回帰は双方2/2）は引き続き候補資料だが、baseline不安定とtool trace不足によりSkill改善実証・採用には数えない。

評価範囲の確認では、現在の`test-requirement-design`出力case-001〜003は上流本文/current Entity不足による停止を主に評価し、004/005はheld-outのまま開示していない。`test-case-design` case-001/002も上流成果物不足によるblock用で、内容のあるケース生成を評価しない。今回のTCN-OUT-001は有限因子と禁止pairからpairwise構造を生成する正方向ケースとして機械採点できたが、`SPEC-001`本文がないため、現行Authorityと製品behaviorの意味評価までは確認できない。新しいTR/TC positive fixtureは独立した仕様根拠・期待値を確定していないため作成せず、意味評価を推測で補っていない。

全12 attempt、manifest、grade、比較、隔離patchとhashはGit管理外の[証拠索引](../../.agent-eval-runs/pr17-positive-skill-eval-20261105-01/evidence-index.md)（SHA-256 `e48c3b5e7ba370cdc4595ae117482624ea313b9bd7e3cc92adbf93f65045e619`）に保存した。これらの成果からSkill全体の改善実証は0件で、candidateは隔離・未採用のままである。

## 11. COV-OUT-001の再評価と全体の改善実績（2026-11-08）

### COV-OUT-001の固定比較

目的を「runtime evidence欠落が現行baselineで再現するか、既存のtemplate候補で防止できるか」に限定し、結果を見ずに2 attempt/armを固定した。Evaluator・baseline Skill revisionはPR HEAD `0a463ef40fd347a359138503dd47e0b9a5ae1f64`、入力fingerprintは`sha256:5fcfe8297aefa29c0ee515859a52222eb1b62aea295eef1c010608dca765e143`。要求Agent設定は4 attemptすべて`gpt-6-luna / max / fork_turns=none`。実効model/build、tool trace、共有workspaceからのEvaluator-only read denialは未検証である。

run r1の4 attemptは全て実行基盤側で有効成果物の生成に至らなかった。起動前のexec失敗、補助コマンドのpath/syntax error、親hostのtask path typo、未開始を各attemptに保存した。run r2ではbaseline 2/2が41/41 PASS、Skill-local runtime verification validだった。candidate attempt 1は34/37 FAILし、`RUNTIME-UNITS-EXACT`、runtime identity、`RT-D016`で不適合となった。見出しのInput/Result identityが`artifact:traceability:all`で、baselineの`coverage-analysis::artifact:traceability:all`と一致しなかった。candidate attempt 2は初回preflightが未定義shell変数`WD`で失敗し、入力を読み込まずartifactも生成しなかった。失敗を置換する再試行はしていない。

`improve.py compare-handoff`は全attemptにintegrity-checked gradeがないため`not_comparable`、`improvement_demonstrated=false`を維持した。今回のbaselineでは過去のruntime block欠落が再現せず、candidateにもgrade FAILがあるため、新しいSkill改善は成立していない。独立回帰は実行していない。candidate patch SHA-256 `7da356f94bbe5a291723176d844069c4e5ee5f2adbb870d720aaee20d4949bab`は隔離・未採用のまま保持する。

r1/r2の全8 attempt、要求設定、sealed execution status、artifact、grade、runtime verifier、comparison、hashはGit管理外の[証拠索引](../../.agent-eval-runs/pr17-cov-causal-20261108-r2/evidence-index.md)に保存した。r2 result SHA-256はbaseline `3bdeaa76418ed6a1b4b33e514fed1f35b4dcddda6ae142064633ca7a49ceddaf`、candidate `80a79807f41049d65640bf6b27fab2ab0c672f5759518746afe3a88ef13f0051`、comparison `2bf09c39e2d1796e4f9a0af6893961160d733d6082f6b7a8f8fa195c86525fcb`。

### PR全体で既に成立したSkill改善

2026-11-01の[`test-requirement-design / TR-OUT-013`比較](2026-11-01_pr17-skill-improvement-promotion_v00.md)では、stable IDとrevision混同のSkill起因失敗がbaseline 2/2で再現し、Skill本文だけを修正したcandidateは2/2 PASS、runtime evidenceも全てvalidだった。修正作成に使っていない`TR-OUT-001`はbaseline/candidateとも21/21 PASSだった。この候補はPR branchへレビュー対象として反映済みであり、開発用評価としての改善実績は1件ある。共有workspace上の評価なので正式な独立評価ではない。

従って、今回のCOV候補の不成立は既存`TR-OUT-013`改善の証拠を取り消さない。PR本文では、開発用の改善実績1件と今回のCOV候補が未成立であることを分けて記載する。正式Judge/QTS受入、実効model/build、tool trace、物理read-denialの未検証状態は維持する。

## 12. TCN-OUT-001の正方向生成評価（2026-11-08）

固定した開発用run `pr17-positive-tcn-20261108-r1` で、`test-condition-design / TCN-OUT-001`を2 attempt実行した。Evaluator・baseline Skill revisionは`7729b9baa30b00b08fe70630dcca2dc2bbe8259c`、入力fingerprintは`sha256:3ad18513c94852b40198c38399e05b244fdb5a223e37b1dc59ce5f8e6a4c93f5`、dataset fingerprintは`sha256:65968df1198d8a7dbe97e392ee74dbea7b7391a765bc9079356ee8fc96353b4f`、Skill package fingerprintは`sha256:567956662c3ef685744765c57585036960f46e57db1d9f10a5431c66a1d6bccd`。要求設定は両attemptとも`gpt-6-luna / max / fork_turns=none`。両方ともhost-observed completed、capture・seal済み、Skill-local runtime verifier valid、grader FAILだった。実効model/build、開始時刻、実際のtool trace、物理的read-denialは未検証。

| Attempt                            | Grade      | 確認できた不適合                                                                                                                                                                                                                                              | request / output / manifest / grade SHA-256                                                                                                                                                                                                                                                                     |
| ---------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `c6e4698ba96a444d99ec59f4a5acc46f` | 31/33 FAIL | `TCN-D030`と`TCN-D015`。出力の候補表見出しがtemplateの`生成row（全因子割当）`ではなく`生成row (全因子割当)`で、ASCII括弧の差により既存parserが表を認識できなかった。blocked候補自体は記載されていた。                                                         | request `0db507ea822c6df7ff031aea469c860b1ea54d64a9476ecaaa88a25112feb5bf` / output `070330f9e7f933491eb8687f8b09887cf35db037d6da992caf792906085b3d0a` / manifest `58ae4cfdfb01857bd1a59a6fc48adaac56833bc836320a9ae84b6c39156ecf09` / grade `96d0306399745ca545d9a38ed4bc124196fb0fac2d20b542c218a7f11854c936` |
| `8c45b569d63a4b3b83c5cda90ce61008` | 32/33 FAIL | `TCN-D030`。current Authority本文がなく期待動作を確定できない入力に対し、runtime requestの`target_dispositions`が空のままmaterializeし、11件のactive CI Entityを出力した。Skillは未確定・blocked targetにCIを作らずunresolvedを保持するよう既に指示している。 | request `c5af716f8115ddc5edd0f827748edfd88dc48ae59cbcd7ac2447561210ce0b28` / output `a74f201afd782024e77cf5ee148f28903896f14e7e064900907e2452af693783` / manifest `e1367498bb046f2a59157a1d1fac38bdc40e0e374889378f396f8c66b1c1b97a` / grade `040c258f24e38fd2b9437ebf4bd1f5a10b0776cc0daeaea578dc6aef15e509f0` |

Skill contractの確認では、[SKILL.md](../../skills/test-condition-design/SKILL.md)が未確定・blocked targetのCI生成禁止とunresolved保持を明記し、[output-template.md](../../skills/test-condition-design/assets/output-template.md)が候補表の正確な見出しを定義している。従って今回の2件は、Skillの指示欠落を示す証拠ではなく、Agentが既存契約を一方では表記どおりに出力できず、他方では処理上適用しなかった結果である。違反の形が異なり、原因を変えるSkill修正の根拠は成立しなかったためcandidateは作成していない。対象assertionの修復、candidate比較、独立回帰はいずれも未実施であり、TCN Skillの改善実績には数えない。

Skill-local verifierの`valid`は提出されたruntime evidenceの契約適合を示すにとどまり、helper実行を独立したhost tool traceで証明しない。2 attemptの成果物・grade・request・manifestと要求設定の索引はGit管理外の[証拠索引](../../.agent-eval-runs/pr17-positive-tcn-20261108-r1/evidence-index.md)にある。同索引SHA-256は`5af890e395cea9b8572ac1e8d47d573b70dd2532d31f8ee6335eddd70dc19f48`、run result SHA-256は`a4768b3360ac25ef0c6ee78317e8dc5385049fa14e6fb7a19d46ec776ff52b7e`。

## 13. TR-OUT-004の正方向baseline評価（2026-11-08）

内容のある要求設計を検査するため、held-outだった`test-requirement-design / TR-OUT-004`を原因分析・修正Agentへ渡さず、独立した生成用サブエージェント2件だけでbaseline評価した。Evaluator・baseline Skill revisionは`7729b9baa30b00b08fe70630dcca2dc2bbe8259c`、入力fingerprintは`sha256:75c6fc8ddcb5c42dea4980bfee4d8a735c6724f3c29802a2df0d73dfec22b738`、dataset fingerprintは`sha256:1eb396b331dde5ac6adc8c27f780973357d39e2d70215504f87928b9760de7f3`、Skill package fingerprintは`sha256:4b96082bc668f2181c63d223cff938b07751323d2fec407b944de287b4d168da`。要求設定は2 attemptとも`gpt-6-luna / max / fork_turns=none`。親hostの観測では両方completed、capture・seal済みで、既存deterministic graderは各20/20 PASS、Skill-local runtime verifierはvalidだった。実効model/build、開始時刻、tool trace、Evaluator-only情報への物理read-denialは未検証。

| Attempt                            | request / output / manifest / grade SHA-256                                                                                                                                                                                                                                                                     |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `8cd2c787074a4092b52684a2217d0df8` | request `d6838f5dfd37f16477c933d51004381bae7493b87d7d820a638e0b2efcb725a9` / output `4628c62aa73cbe4b791befd2aaee7a5d4dd78f9a4731c3e026ea51f9c79a5566` / manifest `8a22810747520715142acf78ccce80992cb44d38eb9f4be421008b4437c7027c` / grade `fa80f3629c3c93a517d0021e9e4d902443ab5cabe8c5e325125d4a3f2e39e7d1` |
| `12b02c6314a941929f9e9164707e08e5` | request `752f3fb64dacc3bda5c85f4c7f54556ccce14aefff6b5894d12e98e4f24fcc0a` / output `2501a63210c064ebac5d570f04cbc89f98a5766a10ee9eca79e8970adbdd4318` / manifest `6c775ac0938f0502136bf91e7464afdc622754dbc94dc980148209f9ca264703` / grade `fa80f3629c3c93a517d0021e9e4d902443ab5cabe8c5e325125d4a3f2e39e7d1` |

この結果は正方向のテスト要求成果物が今回のdeterministic契約を満たしたbaseline評価であり、修正前後比較ではない。従って、新たなSkill改善候補・改善実証は0件。意味的な要求の妥当性を承認済みJudgeまたは人間が独立に確認した結果でもない。TR-OUT-004は今回の生成評価に使用済みであり、今後のcandidate用の未使用回帰入力とは扱わない。`TR-OUT-005`は今回の生成・分析・修正作業に使用していない。

2 attemptの成果物・grade・request・manifestと要求設定はGit管理外の[証拠索引](../../.agent-eval-runs/pr17-positive-tr-20261108-r1/evidence-index.md)に保存した。同索引SHA-256は`1298473a0060ecec24fdd0aeab717445f0e710f026a48c153b7a86b6ca15feb8`、run result SHA-256は`dfbee7cc675ce54e7ac936c87e1b833a5c5b2fe28c0058c76dfda36393f7094a`。

### 今回の評価数と判断

前節に記載したinventory累計76件へCOVの8 attemptと今回のTCN/TR各2 attemptを加え、この作業で追跡できる累計は88 attemptである。直近の4 attemptはいずれもhost-observed completed、成果物取得済み、採点済みで、PASS 2件（TR-OUT-004）、FAIL 2件（TCN-OUT-001）、生成前停止0件。既存の開発用改善実績は`test-requirement-design / TR-OUT-013`の1件で、新たなSkill修正candidateと新規改善実証は0件。TCNの失敗は既存Skill契約に対する異なる2種の逸脱であり、Skill欠陥へ帰属できる一貫した原因を示さない。TR positive評価はbaselineのみで改善の証拠ではない。

今回の実測から、同一handoffで要求設定を指定した別サブエージェントを起動し、既存`prepare / host-request / capture / seal / grade`の経路で出力を保存・採点する開発用評価は実行可能と確認できた。これはCodexホスト上のサブエージェントによる開発用動作評価である。正式runner、Judge承認、実効model/build、tool trace、共有workspaceの物理read-denial、正式QTS評価は未達のままである。
