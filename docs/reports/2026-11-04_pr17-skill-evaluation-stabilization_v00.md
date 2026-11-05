# PR #17：実Agent評価の安定化・Skill候補の比較結果

## 概要

この報告は、[前回の原因調査報告](2026-11-04_pr17-skill-quality-cause-and-improvement_v00.md)の後に実施した評価を記録する。評価基盤とSkill品質は別々に判定した。

- 評価対象: `test-case-design / TC-OUT-001`、`test-condition-design / TCN-OUT-002`、`coverage-analysis / COV-OUT-001`、`test-requirement-design / TR-OUT-003`。
- 固定Evaluator・baseline Skill revision: `f56d00b5d6beb5d95415411f5dc7ef9eb3c1eb54`。
- 要求Agent設定: `gpt-6-luna / max / fork_turns=none`。全attemptで要求値を保存した。実効model/build telemetryは未取得であり、実効値は未検証。
- 実行方式: Codex host subagent handoff。Evaluator-only情報への共有workspace物理読取拒否は未検証であり、正式な独立評価ではない。
- 元のraw成果物、grader、request、全attempt、candidate patchはGit管理外の`.agent-eval-runs/pr17-stability-20261104-02/`に保存した。[evidence-index.md](../../.agent-eval-runs/pr17-stability-20261104-02/evidence-index.md)（SHA-256: `d47372d4491250014ace9cf2bf1b6a363ef39a66229fba2a8e6fd4776d409eac`）。

## 全attemptの集計

以前のStage 5の16 attemptに、今回の14 attemptを加え、計30 attemptを準備・実行した。

- 生成物を取得: 22 attempt。
- 出力なし: 8 attempt（旧記録の7件と今回のTest Case Design candidate 1件）。
- 取得物を既存graderで検証: 20 attempt。
- 取得物はあるが有効なgrader記録がない: 2 attempt。旧COVのseal失敗1件と、今回のTRで同一run rootへのseal並行実行により状態更新を失った1件。

前回の失敗7件は、詳細証拠がある5件のうち4件がworking directoryまたはattempt-local Skill pathの誤り、1件がhandoff intake前の別path参照だった。残る2件はexecution errorの詳細が保存されていない。今回のabsolute-path `host-request`経路では13/14 attemptから出力を取得したが、Test Case Design candidateの1 attemptではhost subagentがSkill packageを相対pathで探して停止した。親側のpreflightではSkill fileがlaunch直前・失敗後とも存在していた。Agent実行前のpath逸脱として記録し、品質FAILには数えていない。

TR-OUT-003の2番目の出力は取得されmanifestも作られたが、2つの`seal`操作を同一run rootへ並行して行ったことで、共有`result.json`の更新が競合した。行は`awaiting_agent`のまま残り、gradeはない。raw evidenceとstateを手編集で合わせず、未採点の実行記録として保持した。以後、同一run rootのcapture / seal / gradeは直列で処理した。

## ケース別の評価

| Skill / input                          | Baseline                                                                                      | Candidate                                                                       | 判定                                                                                                                   |
| -------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `test-case-design / TC-OUT-001`        | 2/2 FAIL。根拠のないcase生成は避けたが、必須runtime evidence欠落で`RT-D016` FAIL。            | 2 attempt中1件はhost停止、出力1件も`RT-D016` FAIL。比較結果は`not_comparable`。 | runtime evidenceの改善なし。candidateは不採用・レビュー待ち。独立回帰なし。                                            |
| `test-condition-design / TCN-OUT-002`  | 2/2 FAIL、30/32。`TCN-D016/D017`。                                                            | 2/2 FAIL、30/32。同じassertion。runtime evidenceは4/4 valid。                   | 改善なし。candidate不採用。入力とexpectedに矛盾があり、Skill欠陥とは確定しない。                                       |
| `coverage-analysis / COV-OUT-001`      | 1/2 PASS、1/2 FAIL。FAILは`RT-D016`の`Machine Entities`欠落。                                 | 0/2 PASS。2/2ともruntime evidenceはvalidだが`COV-D003` FAIL。                   | 出力のruntime block欠落は候補2件で観測されなかった一方、新たなgrader失敗が両方に出た。全体改善は不成立。独立回帰なし。 |
| `test-requirement-design / TR-OUT-003` | 1件は17/18 FAILで、内容assertionはPASS、runtime evidence 3 blockすべて欠落。もう1件は未採点。 | 候補なし。                                                                      | runtime契約の単発不適合を確認。安定したSkill欠陥とは確定しない。                                                       |

### Test Case Design：`TC-OUT-001`

入力は上流IDのみで、仕様本文、状態、操作、期待結果の情報を持たない。実行可能なcaseを創作せず停止した内容判断は適切だった。一方、固定graderはSkillの`artifact:case_structure:all`に`Machine Runtime Input / Result / Entities`を要求し、baseline 2件とも欠落した。前回candidateはこの状況でのruntime dispatchを説明する段落を追加したが、今回の隔離candidateでも有効出力1件は同じ`RT-D016`に失敗した。もう1件は相対pathでSkill packageを探して生成前に停止した。

この比較では対象assertionの改善も全体改善も示されなかった。前回の失敗出力で見られたMachine Entities schema不正とMarkdown table列数不一致は、1件だけの候補に由来し、baselineにもtable assertionの単発失敗がある。generatorのraw output証拠がなく、転記ミスかgenerator入力・結果の問題か判別できないため、追加修正を行わない。candidate patchは同じ評価で使った非採用資料として保持し、独立回帰は行わなかった。

### Test Condition Design：`TCN-OUT-002`

2 baselineの一方は、blocked targetのruntime候補自体は出したが、候補 dispositionとの正規target-key結合がなく`TCN-D016/D017`に失敗した。もう一方とcandidate 2件は、最終在庫不足/Authority未解決の入力でactive Coverage Itemを生成し、同じ2 assertionに失敗した。4件すべてのruntime evidenceはvalidだった。

既存Skillは、current Authorityが未解決ならcandidateをblockedとし、blocked targetへCI IDやactive CI Entityを作らないよう明記している。今回の結果だけでは指示不足よりAgentの実行逸脱が考えられるが、固定Eval Inputは有効遷移を「Coverage Itemへ閉じる」と要求する一方、非公開expectedはその遷移をblocked dispositionにする。製品仕様本文も提示されていない。評価入力とexpectedの衝突を除外できないため、Skill defectと認定せず、expectedも変更しない。candidate templateの修正は2/2で失敗を解消しなかった。修正に使った候補入力は増やさない。

### Coverage Analysis：`COV-OUT-001`

baselineでは2件中1件が完全PASS、残り1件は本文でEntityなしと説明していたが`Machine Entities` blockを出さず`RT-D016`に失敗した。candidateは実結果にEntityがない場合も`entities: []`としてblockを出し、証拠を創作しないようoutput templateだけを変更した。candidate 2件はいずれも3 runtime blockを出し、runtime verifierは`valid=true`だった。

しかし両candidateは`COV-D003`でFAILした。matrix rationaleに「ブロック中ではない」と書いても、validatorが部分文字列`ブロック中`の有無だけを見てblocked分類とした。これは否定文を区別しないdeterministic graderの制約と整合する。grader・expectedを変えず、このcandidateはPASSへ昇格させない。採点上の不一致のため全体改善は成立せず、独立回帰も行わなかった。baselineとcandidateの比較は`comparable_development_handoff`、`improvement_demonstrated=false`。

### Test Requirement Design：`TR-OUT-003`

新規grade可能な1件は17/18で、content statusはPASS、`RT-D016`だけが`Machine Runtime Input / Result / Entities`の全欠落を報告した。Eval InputはIDと要約を現行Entityとして扱わずblockするよう明記し、Skillは最終gateでruntime verifierを必須にしている。従って成果物は契約不適合だが、既存指示は明確で、前の評価には同条件でのPASSも存在する。現時点では再現性あるSkill defectではなく、Agentによるruntime evidence省略の揺れとして扱う。2件目は上述のseal競合で未採点のため、比較には数えない。

## Candidate patchと改善判断

今回作成した隔離candidateは3件。いずれもPR branchのSkill本体へ反映していない。

- `test-case-design`: `tcd-candidate.patch`, SHA-256 `458ec7a665c50a453585cc30ffc625052253bea07e5027daa38a96a38616aecf`。今回の比較は1出力だけで`not_comparable`。
- `test-condition-design`: `tcn-candidate.patch`, SHA-256 `68402322b196c71d561594ccc53dd563ede7acbad7685765175eb937963c26a7`。2/2で対象失敗が継続。
- `coverage-analysis`: `cov-candidate.patch`, SHA-256 `7da356f94bbe5a291723176d844069c4e5ee5f2adbb870d720aaee20d4949bab`。2/2でruntime blocksは有効だが、2/2で新たな`COV-D003`不適合。

対象assertionの再現安定した改善: 0件。成果物全体の改善: 0件。独立回帰まで確認した候補: 0件。Skill品質改善の実証: 0件。候補を修正して成功を積み上げる再試行は行わなかった。

## 評価基盤・安全性

- `subagent_eval host-request`は固定absolute workdir、task、Skill package、submission path、attempt IDを返し、packageやsubmissionの事前状態を検査する。今回14 attemptのうち13件で出力を取得できた。1件の相対path停止は残っており、実効モデル情報もhost telemetryで確認できない。
- 既存`capture → seal → grade`で20件の結果を採点できた。run-root内の同時sealはこの作業で一度競合させた。結果を手修正せず、今後は同一rootで直列処理する。
- `improve.py compare-handoff`: TCDはcandidate attemptのgrade欠落を検出して`not_comparable`、TCNとCOVは比較条件一致の`comparable_development_handoff`を返し、いずれも`improvement_demonstrated=false`とした。
- expected、grader、rubric、独立回帰fixtureは変更していない。実行中のsubagentへ期待値を渡さないよう指示したが、共有workspaceによる物理的な読取拒否は証明していない。
- Candidate修正subagentの要求設定は`gpt-6-luna / max / none`。実効model/buildは未検証。TC-OUT-001 candidate patchは修正Agentを起動できず、親側で隔離作成した。
- 正式runner、独立Judge、formal isolation、実効model/build telemetryはこの開発評価では未達のまま。

## 検証・Git状況

この報告作成前の`f56d00b5d6beb5d95415411f5dc7ef9eb3c1eb54`では、agent evaluation tests 270 passed / 6 skipped、runtime tests 388 passed、deterministic runner tests 28 passed、semantic tests 13 passed、`compileall`、Ruff 0.16.8 format/check、dprint 0.55.2、`git diff --check`が成功している。広範なdeterministic suiteではsandboxのTCP bind `EPERM`、`/tmp/.git`のためのSQLiteテスト失敗、WCAG state-root setup失敗が残った。

今回の継続確認ではagent evaluation tests 270 passed / 6 skipped、runtime tests 388 passed、deterministic helper tests 28 passed、semantic evaluator tests 27 passed。`compileall`、対象報告書のdprint check、`git diff --check`も成功した。現在のshellにはRuffがなく、`ruff: command not found`でローカルlint / format検査は実行できなかった。push後のCode Quality CIで確認する。

この続きで新たなPythonコードは変更していない。PR branchへのSkill candidate採用はしない。
